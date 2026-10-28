"""Prepare a manual first-batch commit writer from the verified native export.

This is an operator-assisted bootstrap, not unattended batch acceptance. The
operator must independently correlate the supplied batch with its completed
refresh and successful extraction run. Native validation tables must be loaded
before this flow can pass. Packages and batch identifiers remain private.
"""
import argparse
import copy
import json
import uuid
import zipfile
from pathlib import Path

if __package__:
    from .build_native_retention_package import ROOT, after, compose
else:
    from build_native_retention_package import ROOT, after, compose


def build(baseline, output, batch):
    if not isinstance(batch, str):
        raise ValueError('batch must be a UUID string')
    try:
        batch = str(uuid.UUID(batch))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError('batch must be a UUID string') from exc
    if not output.resolve().is_relative_to((ROOT / 'private').resolve()):
        raise ValueError('Package contains private connection references.')
    with zipfile.ZipFile(baseline) as z:
        files = {n: z.read(n) for n in z.namelist()}
    name = next(n for n in files if n.endswith('/definition.json'))
    document = json.loads(files[name])
    definition = document['properties']['definition']
    if list(definition['triggers']) != ['manual']:
        raise ValueError('Require a manual native baseline.')
    definition['triggers']['manual']['inputs']['schema'] = {
        'type': 'object', 'properties': {'text': {'title': 'Validated manifest',
        'type': 'string', 'x-ms-content-hint': 'TEXT', 'x-ms-dynamically-added': True}},
        'required': ['text']}
    old = definition['actions']
    query = copy.deepcopy(old['Run_a_query_against_a_dataset'])
    query['runAfter'] = {}
    query['inputs']['parameters']['specification/query'] = '''EVALUATE
ROW("Tests",COUNTROWS(RetentionValidation),
"Failed",COALESCE(COUNTROWS(FILTER(RetentionValidation,NOT(RetentionValidation[Passed] == TRUE()))),0),
"VerifiedSources",COUNTROWS(FILTER(StoredMetadataValidation,
StoredMetadataValidation[KeysMatch] == TRUE() && StoredMetadataValidation[MetadataValid] == TRUE() && StoredMetadataValidation[PayloadIdentitiesMatch] == TRUE() &&
((StoredMetadataValidation[Source] = "PubMed" && StoredMetadataValidation[ExpectedRecords] = 1261 && StoredMetadataValidation[ReconstructedRecords] = 1261 && StoredMetadataValidation[MetadataCharacters] = 32289819) ||
(StoredMetadataValidation[Source] = "DORA" && StoredMetadataValidation[ExpectedRecords] = 709 && StoredMetadataValidation[ReconstructedRecords] = 709 && StoredMetadataValidation[MetadataCharacters] = 2603915)))))'''
    actions = {'Read_native_validation': query,
               'Manifest': compose("@json(triggerBody()['text'])", 'Read_native_validation')}
    result = "body('Read_native_validation')['results'][0]['tables'][0]['rows'][0]"
    m = "outputs('Manifest')"
    checks = [f"equals({result}['[Tests]'],10)",
              f"equals(coalesce({result}['[Failed]'],0),0)",
              f"equals({result}['[VerifiedSources]'],2)",
              f"equals({m}['BatchID'],'{batch}')", f"equals({m}['SchemaVersion'],1)",
              f"equals({m}['Status'],'committed')", f"equals(length({m}['Sources']),2)",
              f"equals({m}['Validation']['Keysets'],true)",
              f"equals({m}['Validation']['Metadata'],true)",
              f"equals({m}['Validation']['RefreshGeneration'],true)"]
    for i, source, count, pages in [(0, 'PubMed', 1261, 39), (1, 'DORA', 709, 8)]:
        s = f"{m}['Sources'][{i}]"
        publication_table, publication_pages, chunk_table, key = (
            ('PubMedPublications', 13, 'PubMedMetadataChunks', 'PMID') if source == 'PubMed'
            else ('DoraPublications', 8, 'DoraMetadataChunks', 'DORAKey'))
        checks += [f"equals({s}['Source'],'{source}')", f"equals({s}['ExpectedRecords'],{count})",
                   f"equals({s}['PublicationTable'],'{publication_table}')",
                   f"equals({s}['PublicationPageCount'],{publication_pages})",
                   f"equals({s}['ChunkTable'],'{chunk_table}')", f"equals({s}['KeyColumn'],'{key}')",
                   f"equals({s}['PageCount'],{pages})", f"equals(length({s}['ExpectedKeys']),{count})",
                   f"equals(length(union({s}['ExpectedKeys'],{s}['ExpectedKeys'])),{count})"]
    # Power Automate expressions are dynamically typed here.  Failure markers
    # are deliberately text; wrapping them in int() causes the flow to fail
    # while evaluating the failure branch instead of returning a diagnostic.
    actions['Require_validation'] = compose("@if(and(" + ','.join(checks) + "),'VERIFIED','COMMIT_VALIDATION_FAILED')", 'Manifest')
    write = copy.deepcopy(old['Create_file'])
    write['runAfter'] = after('Require_validation')
    write['inputs']['parameters'] = {'folderPath': '/CHHHS Research System - DEV/01 Source archive',
        'name': f'commit-{batch}.json', 'body': "@string(outputs('Manifest'))"}
    actions['Create_file'] = write
    actions['Get_file_content_using_path'] = copy.deepcopy(old['Get_file_content_using_path'])
    actions['Verify_commit_readback'] = compose(
        "@if(equals(base64ToString(body('Get_file_content_using_path')['$content']),string(outputs('Manifest'))),'COMMIT_READBACK_VERIFIED','COMMIT_READBACK_FAILED')",
        'Get_file_content_using_path')
    definition['actions'] = actions
    title = 'CHHHS Publications - DEV validated first history commit'
    document['properties']['displayName'] = title
    files[name] = json.dumps(document).encode()
    manifest = json.loads(files['manifest.json'])
    manifest['details']['displayName'] = title
    for resource in manifest['resources'].values():
        if resource['type'] == 'Microsoft.Flow/flows':
            resource['suggestedCreationType'] = 'New'
            resource['details']['displayName'] = title
    files['manifest.json'] = json.dumps(manifest).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, content in files.items():
            z.writestr(n, content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    build(args.baseline, args.output, args.batch)
    print('Prepared manual bootstrap package; native import and validation pending.')


def reconstruct_metadata_rows(chunks, key_column):
    """Offline chunk proof; preserves the existing native package builder above."""
    from scripts.publication_source_metadata_contract import (
        reconstruct_metadata_rows as reconstruct,
    )

    return reconstruct(chunks, key_column)


def validate_retained_typed_archive(commit, receipt, source_pages_bytes, files):
    """Recheck frozen consumed PubMed bytes without creating a native manifest.

    The saved capture hash, committed batch, exact three-table contents, keysets
    and full payload digest must agree. This is no new native acceptance.
    """
    import hashlib
    from collections import defaultdict
    from scripts.verify_retained_canary_metadata_values import _child, _text

    if not all(
        isinstance(value, dict) for value in (commit, receipt, files)
    ) or not isinstance(source_pages_bytes, bytes):
        raise ValueError("Structured retained archive and exact capture bytes required")
    if (
        commit.get("Status") != "committed"
        or receipt.get("batch_id") != commit.get("BatchID")
        or receipt.get("reconstruction_equal") is not True
    ):
        raise ValueError(
            "Exact consumed committed batch and reconstruction proof required"
        )
    if hashlib.sha256(source_pages_bytes).hexdigest() != receipt.get("capture_sha256"):
        raise ValueError("Retained source-page capture hash mismatch")
    pages = json.loads(source_pages_bytes)
    if (
        pages.get("generation") != commit.get("Generation")
        or pages.get("model_id") != commit.get("ModelID")
        or pages.get("request_id") != commit.get("RefreshRequestID")
    ):
        raise ValueError("Consumed source-page generation/model/request mismatch")
    table_rows, names = defaultdict(list), set()
    entries = receipt.get("files")
    if (
        not isinstance(entries, list)
        or not entries
        or type(receipt.get("file_count")) is not int
        or receipt["file_count"] != len(entries)
    ):
        raise ValueError("Complete retained archive inventory required")
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("name"), str)
            or Path(entry["name"]).name != entry["name"]
            or entry["name"] in names
        ):
            raise ValueError("Unique safe retained file names required")
        name = entry["name"]
        names.add(name)
        content = files.get(name)
        if (
            not isinstance(content, bytes)
            or type(entry.get("bytes")) is not int
            or len(content) != entry["bytes"]
            or hashlib.sha256(content).hexdigest() != entry.get("sha256")
        ):
            raise ValueError("Retained typed file byte proof mismatch")
        rows = json.loads(content)
        if (
            not isinstance(rows, list)
            or any(not isinstance(row, dict) for row in rows)
            or type(entry.get("rows")) is not int
            or len(rows) != entry["rows"]
        ):
            raise ValueError("Retained typed file row count mismatch")
        table_rows[entry["table"]].extend(rows)
    if names != set(files) or {
        table: len(rows) for table, rows in table_rows.items()
    } != receipt.get("totals"):
        raise ValueError("Retained typed archive coverage mismatch")
    fields = {
        "PubMedPublications": ("PMID",),
        "PubMedMetadataChunks": ("PMID", "ChunkIndex"),
        "PubMedAuthorEvidence": ("PMID", "AuthorIndex", "AffiliationIndex"),
    }
    for table, keys in fields.items():
        source = pages.get("sources", {}).get(table)
        exported = []
        sequence = source.get("pages") if isinstance(source, dict) else None
        if (
            not isinstance(sequence, list)
            or not sequence
            or type(source.get("page_size")) is not int
            or source["page_size"] != 100
        ):
            raise ValueError("Complete retained source pages required")
        prior = None
        for number, page in enumerate(sequence):
            if (
                not isinstance(page, dict)
                or type(page.get("page_number")) is not int
                or page["page_number"] != number
                or page.get("http") != 200
            ):
                raise ValueError("Retained source page order/HTTP mismatch")
            if "partial" in page and page["partial"] is not False:
                raise ValueError("Partial retained source page rejected")
            query = page.get("query")
            if not isinstance(query, str) or hashlib.sha256(
                query.encode()
            ).hexdigest() != page.get("query_sha256"):
                raise ValueError("Retained source query hash mismatch")
            body = page.get("body")
            results = body.get("results") if isinstance(body, dict) else None
            result = (
                results[0] if isinstance(results, list) and len(results) == 1 else None
            )
            tables = result.get("tables") if isinstance(result, dict) else None
            result_table = (
                tables[0] if isinstance(tables, list) and len(tables) == 1 else None
            )
            if any(
                not isinstance(node, dict)
                or "error" in node
                or node.get("errors")
                or ("partial" in node and node["partial"] is not False)
                for node in (body, result, result_table)
            ):
                raise ValueError("Successful retained source query envelope required")
            rows = result_table.get("rows")
            if (
                not isinstance(rows, list)
                or any(not isinstance(row, dict) for row in rows)
                or len(rows) > 100
                or (not rows) != (number == len(sequence) - 1)
            ):
                raise ValueError(
                    "Retained source pages lack a unique terminal empty page"
                )
            row_keys = [tuple(row.get("[" + key + "]") for key in keys) for row in rows]
            if any(
                not isinstance(key[0], str)
                or not key[0].isascii()
                or not key[0].isdecimal()
                or key[0].startswith("0")
                or any(type(value) is not int or value < 0 for value in key[1:])
                for key in row_keys
            ):
                raise ValueError("Retained source row key types mismatch")
            if row_keys != sorted(set(row_keys)) or (
                row_keys and prior is not None and row_keys[0] <= prior
            ):
                raise ValueError("Retained source keys duplicate or unordered")
            if row_keys:
                prior = row_keys[-1]
            exported.extend(rows)
        sorter = lambda row: tuple(row["[" + key + "]"] for key in keys)
        if sorted(exported, key=sorter) != sorted(table_rows[table], key=sorter):
            raise ValueError("Retained typed archive differs from exact source pages")
    summaries = {row["[PMID]"]: row for row in table_rows["PubMedPublications"]}
    if len(summaries) != len(table_rows["PubMedPublications"]):
        raise ValueError("Duplicate retained typed publication identity")
    sources = commit.get("Sources")
    selected = (
        [
            item
            for item in sources
            if isinstance(item, dict) and item.get("Source") == "PubMed"
        ]
        if isinstance(sources, list)
        else []
    )
    documents, payload_entries, characters = reconstruct_metadata_rows(
        table_rows["PubMedMetadataChunks"], "PMID"
    )
    if (
        len(selected) != 1
        or set(summaries) != set(selected[0].get("ExpectedKeys", []))
        or len(summaries) != selected[0].get("ExpectedRecords")
        or set(documents) != set(summaries)
    ):
        raise ValueError("Consumed summary/full-metadata keyset mismatch")
    payload_digest = hashlib.sha256(
        json.dumps(payload_entries, separators=(",", ":")).encode()
    ).hexdigest()
    extraction = commit.get("SourceExtraction", {})
    if payload_digest != extraction.get(
        "MetadataPayloadSHA256"
    ) or characters != extraction.get("MetadataPayloadCharacters"):
        raise ValueError("Full retained metadata payload differs from committed digest")
    author_keys = sorted(
        (row["[PMID]"], row["[AuthorIndex]"], row["[AffiliationIndex]"])
        for row in table_rows["PubMedAuthorEvidence"]
    )
    expected_counts = {
        "MetadataChunkCount": len(table_rows["PubMedMetadataChunks"]),
        "AuthorEvidenceRowCount": len(author_keys),
    }
    if any(
        type(extraction.get(name)) is not int or extraction[name] != count
        for name, count in expected_counts.items()
    ):
        raise ValueError(
            "Committed chunk/author evidence count differs from retained rows"
        )
    key_digest = hashlib.sha256(
        json.dumps(sorted(summaries), separators=(",", ":")).encode()
    ).hexdigest()
    author_digest = hashlib.sha256(
        json.dumps(author_keys, separators=(",", ":")).encode()
    ).hexdigest()
    if (
        extraction.get("PublicationKeySHA256") != key_digest
        or extraction.get("MetadataKeySHA256") != key_digest
        or extraction.get("AuthorEvidenceKeySHA256") != author_digest
    ):
        raise ValueError("Committed typed source/author key digest mismatch")
    metadata = {key: json.loads(value) for key, value in documents.items()}
    for key, tree in metadata.items():
        if _text(_child(_child(tree, "MedlineCitation"), "PMID")) != key:
            raise ValueError("Retained full-metadata PMID drift")
    return {
        "summaries": summaries,
        "metadata": metadata,
        "authors": table_rows["PubMedAuthorEvidence"],
        "receipt": {
            "status": "PASS_FROZEN_TYPED_ARCHIVE",
            "records": len(summaries),
            "metadata_chunks": len(table_rows["PubMedMetadataChunks"]),
            "author_evidence_rows": len(table_rows["PubMedAuthorEvidence"]),
            "metadata_payload_sha256": payload_digest,
            "native_operation_submitted": False,
        },
    }
