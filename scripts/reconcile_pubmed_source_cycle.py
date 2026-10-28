"""Build a complete offline source candidate from frozen PubMed XML evidence.

This pure closure excludes live/native generation receipts, authentication,
refresh, registry admission, report changes and reviewer decision generation.
"""

import hashlib
import html
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from scripts.build_native_commit_package import validate_retained_typed_archive
from scripts.capture_report_bound_source_union import (
    _xml_text,
    project_current_pubmed_efetch,
)
from scripts.publication_current_generation_gap import reconcile
from scripts.publication_source_metadata_contract import (
    METADATA_CHUNK_SIZE,
    reconstruct_metadata_rows,
)
from scripts.publication_xml_metadata import article_metadata, compare_metadata, digest

EVIDENCE_KIND = (
    "PubMed XML author affiliation; institutional scope not automatically approved"
)


def prepare_offline_typed_candidate(
    manifest,
    raw_readback,
    commit,
    raw_files,
    typed_receipt,
    source_pages_bytes,
    typed_files,
):
    """Return candidate plus complete comparison; never writes its inputs."""
    coverage = reconcile(manifest, raw_readback, commit, raw_files)
    previous = validate_retained_typed_archive(
        commit, typed_receipt, source_pages_bytes, typed_files
    )
    source_rows, chunks, authors, records, changed = [], [], [], {}, []
    prior_authors = defaultdict(list)
    for row in previous["authors"]:
        prior_authors[row["[PMID]"]].append(
            {key.strip("[]"): value for key, value in row.items()}
        )
    comparisons = Counter()
    for name, content in sorted(raw_files.items()):
        projected = project_current_pubmed_efetch(content)
        root = ET.fromstring(content)
        file_hash = hashlib.sha256(content).hexdigest()
        for article in root:
            key = article.findtext("MedlineCitation/PMID")
            if key in records:
                raise ValueError("Duplicate current XML source identity")
            captured = article_metadata(article)
            metadata = json.loads(captured["MetadataJSON"])
            article_node = article.find("MedlineCitation/Article")
            source = dict(
                projected[key],
                PMID=key,
                PubMedURL=f"https://pubmed.ncbi.nlm.nih.gov/{key}/",
            )
            dois = sorted(
                {
                    _xml_text(node).strip().lower()
                    for node in article.findall("PubmedData/ArticleIdList/ArticleId")
                    if node.get("IdType") == "doi" and _xml_text(node).strip()
                }
            )
            source["DOIValues"] = dois
            source["DOI"] = dois[0] if len(dois) == 1 else None
            source["PublicationTypes"] = "; ".join(
                _xml_text(node)
                for node in article_node.findall("PublicationTypeList/PublicationType")
            )
            author_rows = []
            for i, author in enumerate(article_node.findall("AuthorList/Author"), 1):
                collective = _xml_text(author.find("CollectiveName"))
                person = " ".join(
                    part.strip()
                    for part in (
                        _xml_text(author.find("ForeName"))
                        or _xml_text(author.find("Initials")),
                        _xml_text(author.find("LastName")),
                        _xml_text(author.find("Suffix")),
                    )
                    if part.strip()
                )
                author_name = collective or person
                affiliations = [
                    _xml_text(info.find("Affiliation"))
                    for info in author.findall("AffiliationInfo")
                ]
                for j, affiliation in enumerate(affiliations or [None], 1):
                    author_rows.append(
                        {
                            "PMID": key,
                            "AuthorIndex": i,
                            "AuthorName": author_name,
                            "AffiliationIndex": j,
                            "AffiliationText": affiliation,
                            "EvidenceKind": EVIDENCE_KIND,
                        }
                    )
            source["AuthorCount"] = len(article_node.findall("AuthorList/Author"))
            authors.extend(author_rows)
            source_rows.append(source)
            wire = captured["MetadataJSON"].encode().hex().upper()
            count = (len(wire) + METADATA_CHUNK_SIZE - 1) // METADATA_CHUNK_SIZE
            for index in range(count):
                chunks.append(
                    {
                        "[PMID]": key,
                        "[ChunkIndex]": index,
                        "[ChunkCount]": count,
                        "[MetadataCharacters]": len(wire),
                        "[Encoding]": "UTF8-HEX",
                        "[MetadataChunk]": wire[
                            index * METADATA_CHUNK_SIZE : (index + 1)
                            * METADATA_CHUNK_SIZE
                        ],
                    }
                )
            records[key] = dict(
                captured,
                SourceFile=name,
                SourceFileSHA256=file_hash,
                PreservedPriorSummaryContext=previous["summaries"].get(key),
                RegistryReviewFieldsRead=False,
                NativeAdmissionAccepted=False,
            )
            if key not in previous["metadata"]:
                comparisons["new_source_identity"] += 1
                changed.append(
                    {
                        "PMID": key,
                        "kind": "new_source_identity",
                        "full_metadata_retained": True,
                    }
                )
            else:
                delta = compare_metadata(previous["metadata"][key], metadata)
                comparisons[delta["kind"]] += 1
                old_fields = previous["summaries"][key]
                fields = [
                    {
                        "field": field,
                        "previous": old_fields.get("[" + field + "]"),
                        "current": value,
                        "kind": "entity_representation_only"
                        if isinstance(old_fields.get("[" + field + "]"), str)
                        and isinstance(value, str)
                        and html.unescape(old_fields["[" + field + "]"])
                        == html.unescape(value)
                        else "source_value_difference_preserved",
                    }
                    for field, value in source.items()
                    if "[" + field + "]" in old_fields
                    and old_fields["[" + field + "]"] != value
                ]
                author_changed = prior_authors[key] != author_rows
                if (
                    delta["kind"] != "exact_values_and_order"
                    or fields
                    or author_changed
                ):
                    changed.append(
                        dict(  # noqa: C408 - explicit record field names
                            PMID=key,
                            metadata=delta,
                            source_field_differences=fields,
                            author_evidence_changed=author_changed,
                            previous_author_evidence=prior_authors[key]
                            if author_changed
                            else [],
                            current_author_evidence=author_rows
                            if author_changed
                            else [],
                        )
                    )
    reconstructed, _, characters = reconstruct_metadata_rows(chunks, "PMID")
    if set(reconstructed) != set(records) or any(
        reconstructed[key] != records[key]["MetadataJSON"] for key in records
    ):
        raise ValueError("Offline typed metadata chunk roundtrip mismatch")
    if set(records) != set(manifest["pmids"]):
        raise ValueError("Offline typed candidate lost a retained XML identity")
    generation = digest(
        {
            "raw_file_hashes": {
                name: hashlib.sha256(value).hexdigest()
                for name, value in sorted(raw_files.items())
            },
            "metadata_profile": next(iter(records.values()))["MetadataProfile"],
        }
    )
    candidate = {
        "kind": "pubmed_offline_typed_source_candidate_v1",
        "generation_sha256": generation,
        "source_rows": sorted(source_rows, key=lambda row: row["PMID"]),
        "metadata_chunks": sorted(
            chunks, key=lambda row: (row["[PMID]"], row["[ChunkIndex]"])
        ),
        "author_evidence": sorted(
            authors,
            key=lambda row: (row["PMID"], row["AuthorIndex"], row["AffiliationIndex"]),
        ),
        "records": records,
        "native_schema_parity_accepted": False,
        "native_model_generation_created": False,
        "registry_reviews_changed": False,
    }
    receipt = {
        "kind": "pubmed_offline_typed_comparison_v1",
        "status": "PASS_OFFLINE_CANDIDATE_ONLY",
        "coverage": coverage,
        "previous_typed_archive": previous["receipt"],
        "counts": {
            "source_rows": len(source_rows),
            "metadata_chunks": len(chunks),
            "metadata_hex_characters": characters,
            "author_evidence_rows": len(authors),
            "comparison_records": len(records),
            "records_with_any_difference": len(changed),
            "metadata_kinds": dict(sorted(comparisons.items())),
        },
        "candidate_generation_sha256": generation,
        "native_commit_created": False,
        "native_admission_accepted": False,
        "registry_review_values_modified": False,
        "boundary": "Complete frozen XML and typed candidate comparison only. Prior summary context is preserved verbatim. Facility/clinical classification, reviewed values, native schema/engine parity and admission remain unqualified.",
    }
    return candidate, receipt, changed
