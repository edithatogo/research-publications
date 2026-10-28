"""Review-only Dataset/Software assertions from a pinned complete DataCite archive.

SPDX-License-Identifier: Apache-2.0
No provider/native transport. Explicit profiles read reviewed exact-DOI captures
or independently byte-pinned native cursor snapshots, without reacquisition.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

if __package__:
    from scripts import datacite_source as collector
    from scripts.award_identifier_crosswalks import governing_envelope
    from scripts.plan_publication_stub_restore import utc
    from scripts.source_capture_receipt import (
        json_bytes,
        private_directory,
        scope_sha256,
        strict_json,
        validate_response_entry,
        write_verified,
    )
    from scripts.source_http_retry import (
        MAX_RAW_BYTES,
        TRANSIENT_HTTP_STATUSES,
        validate_attempts,
    )
    from scripts.source_relationship_evidence import fingerprint, normalise_doi
else:
    import datacite_source as collector
    from award_identifier_crosswalks import governing_envelope
    from plan_publication_stub_restore import utc
    from source_capture_receipt import (
        json_bytes,
        private_directory,
        scope_sha256,
        strict_json,
        validate_response_entry,
        write_verified,
    )
    from source_http_retry import (
        MAX_RAW_BYTES,
        TRANSIENT_HTTP_STATUSES,
        validate_attempts,
    )
    from source_relationship_evidence import fingerprint, normalise_doi

FORMAT = "rims-datacite-output-relationships-v1"
SCOPE = "complete_related_identifier_queries_for_exact_publication_dois"


def _text(value):
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or re.search(r"[\x00-\x1f\x7f]", value)
    ):
        raise ValueError("Exact nonempty unpadded text required")
    return value


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise ValueError("Independent SHA256 required")
    return value


def _count(value, expected):
    if type(value) is not int or value < 0 or value != expected:
        raise ValueError("Exact integer count required")


def _doi(value):
    _text(value)
    result = normalise_doi(value)
    collector.validate_dois([result])
    return result


class _Archive:
    """One immutable byte buffer per selected regular file; no second proof read."""

    def __init__(self, folder):
        self.folder = Path(folder)
        if self.folder.is_symlink() or not self.folder.is_dir():
            raise ValueError("Contained regular capture directory required")
        self.root = self.folder.resolve()
        self.buffers = {}

    def read(self, name):
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]+\.(?:json|bin)", name
        ):
            raise ValueError("Safe flat archive filename required")
        if name not in self.buffers:
            path = self.root / name
            if (
                path.is_symlink()
                or not path.is_file()
                or path.resolve().parent != self.root
                or path.stat().st_size > MAX_RAW_BYTES
            ):
                raise ValueError("Missing, unsafe or oversized archive file")
            raw = path.read_bytes()
            if len(raw) > MAX_RAW_BYTES:
                raise ValueError("Archive file grew beyond byte limit")
            self.buffers[name] = raw
        return self.buffers[name]


def _canonical(publications, generation, manifest, pin):
    if not isinstance(publications, list) or not isinstance(generation, dict):
        raise ValueError("Independent complete canonical generation required")  # noqa: TRY004 - malformed evidence uses ValueError
    governing_envelope(generation)
    for key in ("generation_id", "canonical_snapshot_id", "source_snapshot_id"):
        _text(generation.get(key))
    if (
        generation.get("source") != "datacite"
        or generation.get("complete") is not True
        or generation.get("next_links") != []
        or generation.get("manifest_sha256") != pin
        or generation.get("source_snapshot_id") != manifest["generation_id"]
        or generation.get("source_scope_sha256") != manifest["scope_sha256"]
        or generation.get("publications_sha256") != fingerprint(publications)
    ):
        raise ValueError("Unbound or incomplete canonical/source generation")
    _count(generation.get("publication_count"), len(publications))
    _count(generation.get("query_count"), len(manifest["queries"]))
    keys = set()
    index = {}
    for row in publications:
        if not isinstance(row, dict):
            raise ValueError("Structured canonical publication required")  # noqa: TRY004 - malformed evidence uses ValueError
        key = _text(row.get("CanonicalKey"))
        if key in keys:
            raise ValueError("Duplicate canonical publication identity")
        keys.add(key)
        pmid = row.get("PMID")
        if pmid not in (None, "") and (
            not isinstance(pmid, str) or not re.fullmatch("[1-9][0-9]*", pmid)
        ):
            raise ValueError("Exact positive ASCII PMID text required")
        if row.get("DOI") not in (None, ""):
            index.setdefault(_doi(row["DOI"]), set()).add(key)
    return index, keys


def _capture(archive, pin):
    raw = archive.read("manifest.json")
    if hashlib.sha256(raw).hexdigest() != _sha(pin):
        raise ValueError("Independent manifest pin mismatch")
    manifest = strict_json(raw)
    governing_envelope(manifest)
    if (
        manifest.get("source") != "datacite"
        or manifest.get("scope") != SCOPE
        or manifest.get("complete") is not True
        or manifest.get("accepted") is not False
    ):
        raise ValueError(
            "Complete reviewed exact-DOI collector archive required; native cursor format unsupported"
        )
    _text(manifest.get("generation_id"))
    utc(_text(manifest.get("captured_utc")))
    ids = collector.validate_dois(manifest.get("requested_publication_dois"))
    if manifest.get("scope_sha256") != scope_sha256(
        {"kind": SCOPE, "requested_publication_dois": ids}
    ):
        raise ValueError("Collector exact scope hash mismatch")
    validate_attempts(manifest.get("max_read_attempts"))
    files = manifest.get("files")
    queries = manifest.get("queries")
    if not isinstance(files, list) or not isinstance(queries, list):
        raise ValueError("Complete query and file inventories required")  # noqa: TRY004 - malformed evidence uses ValueError
    if [q.get("publication_doi") for q in queries if isinstance(q, dict)] != ids or len(
        queries
    ) != len(ids):
        raise ValueError("Exact ordered query scope required")
    entries = {}
    responses = {}
    errors = {}
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("Structured raw-file inventory required")  # noqa: TRY004 - malformed evidence uses ValueError
        name = entry.get("name")
        if name in entries or name in (
            "manifest.json",
            "related-outputs.json",
            "failed-generation.json",
        ):
            raise ValueError("Duplicate or reserved raw filename")
        captured = archive.read(name)
        _count(entry.get("bytes"), len(captured))
        if hashlib.sha256(captured).hexdigest() != _sha(entry.get("sha256")):
            raise ValueError("Raw file hash drift")
        target = entry.get("publication_doi")
        page = entry.get("page")
        if target not in ids or type(page) is not int or not 1 <= page <= 100:
            raise ValueError("Raw file outside exact query/page scope")
        url = collector._query_url(target, page)
        validate_response_entry(entry, url, collector._page_name(target, page))
        if type(entry.get("http")) is not int:
            raise ValueError("Explicit integer HTTP status required")
        count = entry.get("attempt_count")
        if type(count) is not int or not 1 <= count <= 4:
            raise ValueError("Explicit bounded attempt count required")
        if "request_attempts" in entry:
            _count(entry["request_attempts"], count)
        if entry.get("response_date") is not None and not isinstance(
            entry["response_date"], str
        ):
            raise ValueError("Provider Date is raw text or unknown null")
        key = (target, page)
        if entry.get("kind") == "response":
            if entry["http"] != 200 or key in responses:
                raise ValueError("Duplicate or unsuccessful response page")
            responses[key] = entry
        elif entry.get("kind") == "http_error":
            if entry["http"] not in TRANSIENT_HTTP_STATUSES:
                raise ValueError("Completed capture contains permanent HTTP failure")
            errors.setdefault(key, []).append(entry)
        else:
            raise ValueError("Explicit response/error kind required")
        entries[name] = entry
    _retry_lineage(manifest, ids, responses, errors)
    if {p.name for p in archive.root.iterdir()} != set(entries) | {
        "manifest.json",
        "related-outputs.json",
    }:
        raise ValueError("Failed, missing or unlisted capture files")
    return manifest, ids, responses


def _retry_lineage(manifest, ids, responses, errors):
    attempts = manifest.get("request_attempts")
    if not isinstance(attempts, list):
        raise ValueError("Explicit request attempt evidence required")  # noqa: TRY004 - malformed evidence uses ValueError
    ledger = {}
    for entry in attempts:
        if not isinstance(entry, dict):
            raise ValueError("Structured request attempt evidence required")  # noqa: TRY004 - malformed evidence uses ValueError
        utc(_text(entry.get("observed_at_utc")))
        _text(entry.get("error_type"))
        number = entry.get("attempt")
        digest = _sha(entry.get("request_sha256"))
        if (
            type(number) is not int
            or not 1 <= number < manifest["max_read_attempts"]
            or entry.get("retryable") is not True
        ):
            raise ValueError(
                "Complete generation has contradictory failed-attempt evidence"
            )
        status = entry.get("http_status")
        if status is not None and (
            type(status) is not int or status not in TRANSIENT_HTTP_STATUSES
        ):
            raise ValueError("Unclassified completed HTTP retry")
        if (digest, number) in ledger:
            raise ValueError("Duplicate failed request attempt")
        ledger[(digest, number)] = entry
    prior = manifest.get("resumed_from")
    prefix = []
    prior_sha = None
    if prior is not None:
        if not isinstance(prior, dict):
            raise ValueError("Structured retained resume lineage required")
        prior_sha = _sha(prior.get("sha256"))
        _text(prior.get("path"))
        prefix = prior.get("completed_ids")
        if (
            not isinstance(prefix, list)
            or prefix != ids[: len(prefix)]
            or len(prefix) > len(ids)
        ):
            raise ValueError("Exact retained complete query prefix required")
    used = set()
    for key, response in responses.items():
        url = collector._query_url(*key)
        digest = hashlib.sha256(url.encode()).hexdigest()
        count = response["attempt_count"]
        if key[0] in prefix:
            if (
                response.get("reused_from_failure_receipt") != prior_sha
                or key in errors
            ):
                raise ValueError("Complete reused query lineage mismatch")
            continue
        if (
            "reused_from_failure_receipt" in response
            or count > manifest["max_read_attempts"]
        ):
            raise ValueError("Unbound reused response or retry budget")
        for number in range(1, count):
            if (digest, number) not in ledger:
                raise ValueError("Missing first-failure/attempt history")
            used.add((digest, number))
        for error in errors.get(key, []):
            item = ledger.get((digest, error["attempt_count"]))
            if (
                item is None
                or item.get("http_status") != error["http"]
                or error["attempt_count"] >= count
            ):
                raise ValueError(
                    "Retained HTTP error not bound to successful read history"
                )
            if item.get("available_response_bytes") is not None:
                _count(item["available_response_bytes"], error["bytes"])
    if set(errors) - set(responses) or used != set(ledger):
        raise ValueError("Unfinished or unreferenced request history")


def _emit(archive, manifest, ids, views, publications, generation, pin, profile):
    index, canonical_keys = _canonical(publications, generation, manifest, pin)
    expected_manifest_sha256 = pin
    rows = {}
    diagnostics = {}
    record_hashes = {}
    selected = {"Dataset": set(), "Software": set()}
    all_records = set()
    other_types = set()
    revision = fingerprint([FORMAT, profile, pin, generation])

    def add(container, record, target, relation, paths, reason=None):
        raw_id = record["id"]
        attrs = record["attributes"]
        output_doi = _doi(attrs["doi"])
        target_doi = _doi(target) if target is not None else None
        matches = sorted(index.get(target_doi, set()))
        kind = "datacite_output_diagnostic" if reason else "datacite_output_reference"
        relation = relation or {}
        key = "datacite-output:" + fingerprint(
            [
                kind,
                output_doi,
                target_doi,
                attrs.get("version"),
                relation.get("relatedIdentifier"),
                relation.get("relatedIdentifierType"),
                relation.get("relationType"),
                reason,
            ]
        )
        row = {
            "EvidenceKey": key,
            "RelationshipKind": kind,
            "FromKey": "datacite:" + output_doi,
            "ToKey": "doi:" + target_doi if target_doi else "",
            "RecordIDRaw": raw_id,
            "OutputDOIRaw": attrs["doi"],
            "PublicationMatchLiteral": target,
            "RelatedIdentifierRaw": relation.get("relatedIdentifier"),
            "RelatedIdentifierTypeRaw": relation.get("relatedIdentifierType"),
            "RelationTypeRaw": relation.get("relationType"),
            "ResourceTypeGeneralRaw": attrs.get("types", {}).get("resourceTypeGeneral")
            if isinstance(attrs.get("types"), dict)
            else None,
            "VersionRaw": attrs.get("version"),
            "SourceRecord": copy.deepcopy(record),
            "DiagnosticReason": reason,
            "CanonicalKey": matches[0] if len(matches) == 1 else "",
            "CanonicalMatchCount": len(matches),
            "CanonicalKeys": matches,
            "AdmissionState": "Ambiguous publication"
            if len(matches) > 1
            else "Unmapped publication"
            if not matches
            else "Candidate only",
            "ReviewState": "Not reviewed",
            "Confidence": "candidate",
            "IdentityQualified": False,
            "CanonicalAdmission": False,
            "MutationAuthorized": False,
            "NativeG06Admission": False,
            "SourceManifestSHA256": expected_manifest_sha256,
            "SourceSnapshotID": manifest["generation_id"],
            "SourceCapturedUTC": manifest["captured_utc"],
            "GenerationID": generation["generation_id"],
            "CanonicalSnapshotID": generation["canonical_snapshot_id"],
            "CanonicalInputSHA256": generation["publications_sha256"],
            "ProjectionRevisionSHA256": revision,
        }
        if key in container:
            if {k: v for k, v in container[key].items() if k != "SourcePaths"} != row:
                raise ValueError("Conflicting repeated source assertion")
            container[key]["SourcePaths"].extend(paths)
        else:
            container[key] = {**row, "SourcePaths": paths}

    for view in views:
        entry = view["entry"]
        targets = {v.casefold(): v for v in view["targets"]}
        if entry.get("query_kind") == "institutional":
            for doi in index:
                targets.setdefault(doi, None)
        for record_index, source in enumerate(view["records"]):
            identity = _doi(source["id"])
            digest = fingerprint(source)
            if identity in record_hashes and record_hashes[identity] != digest:
                raise ValueError("Conflicting repeated DataCite record across queries")
            record_hashes[identity] = digest
            all_records.add(identity)
            attrs = source["attributes"]
            types = attrs.get("types")
            kind = types.get("resourceTypeGeneral") if isinstance(types, dict) else None
            path = {
                "file": entry["name"],
                "record_path": view["data_path"] + "/" + str(record_index),
                "relation_path": None,
                "sha256": entry["sha256"],
                "bytes": entry["bytes"],
                "page": view["page"],
                "request_url": entry["source_url"],
                "request_parameters": entry.get("parameters"),
                "query_key": entry.get("query_key"),
                "native_archive_folder": entry.get("archive_folder"),
                "ProviderResponseDateRaw": entry.get("response_date"),
                "PriorFailureReceiptSHA256": entry.get("reused_from_failure_receipt"),
                "query_target_dois": copy.deepcopy(view["targets"])
                if entry.get("query_kind", "related") == "related"
                else [],
                "RequestedPublicationDOIRaw": view["targets"][0]
                if len(view["targets"]) == 1
                and entry.get("query_kind", "related") == "related"
                else None,
            }
            matches = {}
            for i, relation in enumerate(attrs.get("relatedIdentifiers", [])):
                value = relation.get("relatedIdentifier")
                if (
                    relation.get("relatedIdentifierType") == "DOI"
                    and isinstance(value, str)
                    and value.casefold() in targets
                ):
                    matches.setdefault(targets[value.casefold()] or value, []).append(
                        (i, relation)
                    )
            selected_type = isinstance(kind, str) and kind in selected
            if selected_type:
                selected[kind].add(identity)
            else:
                other_types.add(identity)
            reason = (
                None
                if selected_type
                else "unknown_resource_type"
                if not isinstance(kind, str) or not kind
                else "outside_selected_output_types"
            )
            if not matches:
                target = (
                    view["targets"][0]
                    if len(view["targets"]) == 1
                    and entry.get("query_kind", "related") == "related"
                    else None
                )
                add(
                    diagnostics,
                    source,
                    target,
                    None,
                    [path],
                    reason or "no_exact_relationship_to_query_target",
                )
            for target, relations in matches.items():
                for i, relation in relations:
                    location = {
                        **path,
                        "relation_path": path["record_path"]
                        + "/attributes/relatedIdentifiers/"
                        + str(i),
                        "RequestedPublicationDOIRaw": next(
                            (
                                v
                                for v in view["targets"]
                                if v.casefold() == target.casefold()
                            ),
                            None,
                        )
                        if entry.get("query_kind", "related") == "related"
                        else None,
                    }
                    value = relation.get("relationType")
                    problem = reason
                    if problem is None and (
                        not isinstance(value, str)
                        or not value
                        or value != value.strip()
                    ):
                        problem = "missing_or_invalid_relation_type"
                    add(
                        diagnostics if problem else rows,
                        source,
                        target,
                        relation,
                        [location],
                        problem,
                    )
    values = sorted(rows.values(), key=lambda r: r["EvidenceKey"])
    exceptions = sorted(diagnostics.values(), key=lambda r: r["EvidenceKey"])
    resolved = {r["CanonicalKey"] for r in values if r["CanonicalKey"]}
    if not resolved <= canonical_keys:
        raise ValueError("Projection created a canonical identity")
    queried = {key for target in ids for key in index.get(_doi(target), set())}
    return {
        "format": FORMAT,
        "ArchiveProfile": profile,
        "ProjectionRevisionSHA256": revision,
        "SourceManifestSHA256": pin,
        "Generation": generation,
        "rows": values,
        "diagnostics": exceptions,
        "coverage": {
            "available": True,
            "complete": True,
            "scope": manifest.get("consumer_scope", SCOPE),
            "requested_publication_dois": ids,
            "query_count": len(manifest["queries"]),
            "returned_unique_output_dois": len(all_records),
            "dataset_record_count": len(selected["Dataset"]),
            "software_record_count": len(selected["Software"]),
            "unselected_or_unknown_type_record_count": len(other_types),
            "type_count_basis": "Exact literal Dataset/Software labels only; other or absent types are not inferred",
            "dataset_assertion_count": sum(
                r["ResourceTypeGeneralRaw"] == "Dataset" for r in values
            ),
            "software_assertion_count": sum(
                r["ResourceTypeGeneralRaw"] == "Software" for r in values
            ),
            "canonical_publication_count": len(canonical_keys),
            "resolved_canonical_publication_count": len(resolved),
            "queried_canonical_publication_count": len(queried),
            "unqueried_canonical_publication_count": len(canonical_keys - queried),
            "canonical_key_set_sha256": fingerprint(sorted(canonical_keys)),
            "source_invalid_publication_value_count": manifest.get(
                "invalid_publication_value_count", 0
            ),
        },
        "source_files": {
            name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            for name, raw in sorted(archive.buffers.items())
        },
        "SourceCutoffUTC": manifest.get("until"),
        "CanonicalAdmission": False,
        "MutationAuthorized": False,
        "NativeG06Admission": False,
        "IdentityQualified": False,
        "ReviewState": "Not reviewed",
        "Confidence": "candidate",
        "history_policy": "New immutable source revision only; absence is not withdrawal authority; no human reviews changed",
    }


def prepare(
    folder,
    publications,
    *,
    expected_manifest_sha256,
    generation,
    profile="exact_doi",
    native_receipt=None,
    expected_receipt_sha256=None,
    prior_manifest=None,
    expected_prior_sha256=None,
):
    """Caller pins bind trusted frozen evidence, not freshly self-certified folders."""
    publications, generation = copy.deepcopy((publications, generation))
    archive = _Archive(folder)
    if profile == "native_cursor":
        manifest, ids, views = _native(
            archive,
            expected_manifest_sha256,
            generation,
            native_receipt,
            expected_receipt_sha256,
            prior_manifest,
            expected_prior_sha256,
        )
        return _emit(
            archive,
            manifest,
            ids,
            views,
            publications,
            generation,
            expected_manifest_sha256,
            profile,
        )
    if profile != "exact_doi" or any(
        v is not None
        for v in (
            native_receipt,
            expected_receipt_sha256,
            prior_manifest,
            expected_prior_sha256,
        )
    ):
        raise ValueError(
            "Explicit supported archive profile and matching proof arguments required"
        )
    manifest, ids, responses = _capture(archive, expected_manifest_sha256)
    views = []
    recomputed = []
    used = set()
    for query in manifest["queries"]:
        governing_envelope(query)
        target = query["publication_doi"]
        total = query.get("returned_records")
        pages = query.get("pages")
        if (
            type(total) is not int
            or not 0 <= total <= 2500
            or type(pages) is not int
            or pages != max(1, (total + 24) // 25)
        ):
            raise ValueError("Exact bounded declared query coverage required")
        keys = set()
        for page in range(1, pages + 1):
            key = (target, page)
            if key not in responses:
                raise ValueError("Missing complete query page")
            used.add(key)
            entry = responses[key]
            raw = archive.read(entry["name"])
            page_total, page_count, page_ids, projected = collector._validated_page(
                raw, target, page, total
            )
            if (
                page_total != total
                or page_count != pages
                or keys.intersection(page_ids)
            ):
                raise ValueError("Query count or duplicate identity drift")
            keys.update(page_ids)
            recomputed.extend(projected)
            payload = strict_json(raw)
            governing_envelope(payload)
            governing_envelope(payload["meta"])
            views.append(
                {
                    "entry": entry,
                    "targets": [target],
                    "records": payload["data"],
                    "data_path": "/data",
                    "page": page,
                }
            )
        _count(len(keys), total)
    if used != set(responses):
        raise ValueError("Unreferenced source response pages")
    raw = archive.read("related-outputs.json")
    if hashlib.sha256(raw).hexdigest() != _sha(manifest.get("projection_sha256")):
        raise ValueError("Collector projection hash mismatch")
    saved = strict_json(raw)
    if not isinstance(saved, list) or fingerprint(saved) != fingerprint(recomputed):
        raise ValueError("Complete collector projection differs from raw source pages")
    _count(manifest.get("relationship_assertions"), len(recomputed))
    return _emit(
        archive,
        manifest,
        ids,
        views,
        publications,
        generation,
        expected_manifest_sha256,
        profile,
    )


def _pinned_json(raw, pin):
    if (
        not isinstance(raw, bytes)
        or len(raw) > MAX_RAW_BYTES
        or hashlib.sha256(raw).hexdigest() != _sha(pin)
    ):
        raise ValueError("Independent exact-byte proof input required")
    value = strict_json(raw)
    governing_envelope(value)
    return value


def _native(archive, pin, generation, receipt_raw, receipt_pin, prior_raw, prior_pin):
    if not isinstance(generation, dict):
        raise ValueError("Independent native/canonical generation required")  # noqa: TRY004 - malformed evidence uses ValueError
    receipt = _pinned_json(receipt_raw, receipt_pin)
    if generation.get("native_receipt_sha256") != receipt_pin:
        raise ValueError("Native byte receipt not bound to independent generation")
    raw = archive.read("manifest.json")
    if hashlib.sha256(raw).hexdigest() != _sha(pin):
        raise ValueError("Independent native manifest pin mismatch")
    manifest = strict_json(raw)
    governing_envelope(manifest)
    if (
        manifest.get("source") != "datacite"
        or manifest.get("format") != "rims-datacite-discovery-v1"
        or manifest.get("complete") is not True
        or manifest.get("downstream_selection_applied") is not False
    ):
        raise ValueError("Complete unfiltered native discovery-v1 archive required")
    run = _text(manifest.get("capture_run"))
    folder = _text(manifest.get("archive_folder"))
    if receipt.get("run") != run or not isinstance(receipt.get("files"), dict):
        raise ValueError("Exact native run and downloaded-file inventory required")
    evidence = receipt["files"]
    actual = {p.name for p in archive.root.iterdir()}
    if actual != set(evidence) or any("failed" in name.casefold() for name in actual):
        raise ValueError("Failed, missing or unlisted native archive files")
    for name, entry in evidence.items():
        if not isinstance(entry, dict):
            raise ValueError("Structured independent native file proof required")  # noqa: TRY004 - malformed evidence uses ValueError
        value = archive.read(name)
        _count(entry.get("bytes"), len(value))
        if hashlib.sha256(value).hexdigest() != _sha(entry.get("sha256")):
            raise ValueError("Independent native file byte proof mismatch")
    used = {"manifest.json"}

    def read(name):
        if name not in evidence:
            raise ValueError("Missing independently pinned native artifact")
        used.add(name)
        return strict_json(archive.read(name))

    marker = "datacite-discovery-complete-" + run + ".json"
    if fingerprint(read(marker)) != fingerprint(manifest):
        raise ValueError("Native completion marker differs from manifest")
    scope = read("scope.json")
    inputs = read("publication-doi-source.json")
    governing_envelope(scope)
    governing_envelope(inputs)
    if scope.get("scope_sha256") != manifest.get("scope_sha256") or not isinstance(
        manifest.get("scope_sha256"), str
    ):
        raise ValueError("Native independent scope binding mismatch")
    _sha(manifest["scope_sha256"])
    options = {"detail": "true", "affiliation": "true", "publisher": "true"}
    if fingerprint(scope.get("full_metadata_options")) != fingerprint(
        options
    ) or fingerprint(manifest.get("full_metadata_options")) != fingerprint(options):
        raise ValueError("Complete native metadata options required")
    size = scope.get("rows_per_page")
    batch = scope.get("related_dois_per_query")
    if (
        type(size) is not int
        or not 1 <= size <= 1000
        or type(batch) is not int
        or not 1 <= batch <= 100
    ):
        raise ValueError("Bounded native page/query sizing required")
    ids = inputs.get("publication_dois")
    if not isinstance(ids, list):
        raise ValueError("Native publication DOI population required")  # noqa: TRY004 - malformed evidence uses ValueError
    if ids:
        collector.validate_dois(ids)
    if (
        manifest.get("publication_dois") != ids
        or manifest.get("publication_doi_snapshot") != "publication-doi-source.json"
    ):
        raise ValueError("Native publication snapshot identity mismatch")
    if not isinstance(inputs.get("rows"), list) or not isinstance(
        inputs.get("invalid_values"), list
    ):
        raise ValueError(  # noqa: TRY004 - malformed evidence uses ValueError
            "Retained native publication rows and invalid diagnostics required"
        )
    _count(inputs.get("source_count"), len(inputs["rows"]))
    _text(manifest.get("publication_doi_population_kind"))
    _text(inputs.get("population_kind"))
    if manifest.get("publication_doi_population_kind") != inputs.get("population_kind"):
        raise ValueError("Native publication population kind mismatch")
    full = manifest.get("full_reconciliation")
    if type(full) is not bool:
        raise ValueError("Explicit native reconciliation kind required")
    cutoff = _text(manifest.get("until"))
    utc(cutoff)
    baseline = _text(manifest.get("baseline_completed_at"))
    utc(baseline)
    if full:
        if baseline != cutoff or prior_raw is not None or prior_pin is not None:
            raise ValueError("Full baseline must carry its own exact cutoff")
        overlap = None
    else:
        prior = _pinned_json(prior_raw, prior_pin)
        if (
            prior.get("format") != "rims-datacite-discovery-v1"
            or prior.get("downstream_selection_applied") is not False
            or type(prior.get("full_reconciliation")) is not bool
            or generation.get("prior_manifest_sha256") != prior_pin
            or prior.get("source") != "datacite"
            or prior.get("complete") is not True
            or prior.get("scope_sha256") != manifest["scope_sha256"]
            or prior.get("baseline_completed_at") != baseline
        ):
            raise ValueError(
                "Pinned accepted prior baseline/window required for overlap update"
            )
        previous = _text(prior.get("until"))
        utc(previous)
        old = datetime.fromisoformat(previous)
        new = datetime.fromisoformat(cutoff)
        if new <= old:
            raise ValueError("Native update cutoff must advance prior cutoff")
        previous_ids = prior.get("publication_dois")
        if not isinstance(previous_ids, list):
            raise ValueError("Prior publication DOI array required")
        if previous_ids:
            collector.validate_dois(previous_ids)
        if not set(previous_ids) <= set(ids):
            raise ValueError("Native update lost prior publication query population")
        overlap = (old.astimezone(UTC) - timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    institutional = scope.get("institutional_queries")
    if not isinstance(institutional, list):
        raise ValueError("Native institutional query policy required")  # noqa: TRY004 - malformed evidence uses ValueError
    expected = {}
    for item in institutional:
        governing_envelope(item)
        key = _text(item.get("key"))
        query = _text(item.get("query"))
        if (
            not re.fullmatch("[A-Za-z0-9_-]+", key)
            or key in expected
            or item.get("kind") != "institutional"
        ):
            raise ValueError("Unique safe institutional query key required")
        expected[key] = {"kind": "institutional", "query": query, "targets": ids}
    for offset in range(0, len(ids), batch):
        key = "related-" + str(offset // batch)
        if key in expected:
            raise ValueError("Native query key collision")
        targets = ids[offset : offset + batch]
        quoted = [
            '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"' for v in targets
        ]
        expected[key] = {
            "kind": "related",
            "query": "relatedIdentifiers.relatedIdentifier:("
            + " OR ".join(quoted)
            + ")",
            "targets": targets,
        }
    queries = manifest.get("queries")
    snapshot = inputs.get("queries")
    if (
        not isinstance(queries, list)
        or not queries
        or len(queries) != len(expected)
        or not isinstance(snapshot, list)
        or len(snapshot) != len(expected)
    ):
        raise ValueError("Complete native query scope required")
    snapshot_keys = set()
    for item in snapshot:
        governing_envelope(item)
        key = item.get("key")
        if (
            not isinstance(key, str)
            or key in snapshot_keys
            or key not in expected
            or item.get("kind") != expected[key]["kind"]
            or item.get("query") != expected[key]["query"]
        ):
            raise ValueError("Native publication query snapshot differs from policy")
        snapshot_keys.add(key)
    query_keys = set()
    views = []
    for query in queries:
        governing_envelope(query)
        key = query.get("key")
        if not isinstance(key, str) or key in query_keys or key not in expected:
            raise ValueError("Duplicate or missing native query identity")
        query_keys.add(key)
        spec = expected[key]
        if query.get("kind") != spec["kind"] or query.get("complete") is not True:
            raise ValueError("Native query purpose/completeness mismatch")
        window = (
            'created:[* TO "' + cutoff + '"]'
            if full or spec["kind"] == "related"
            else 'updated:["' + overlap + '" TO "' + cutoff + '"]'
        )
        wanted = "(" + spec["query"] + ") AND " + window
        if query.get("query") != wanted:
            raise ValueError("Native query/window differs from pinned source scope")
        if fingerprint(read(key + "-complete.json")) != fingerprint(query):
            raise ValueError("Native query completion receipt mismatch")
        if (
            "scope_sha256" in query
            and query["scope_sha256"] != manifest["scope_sha256"]
        ):
            raise ValueError("Native query scope drift")
        pages = query.get("pages")
        total = query.get("provider_total")
        if (
            not isinstance(pages, list)
            or not 1 <= len(pages) <= 5000
            or type(total) is not int
            or not 0 <= total <= 5000 * size
        ):
            raise ValueError("Bounded complete native pages/count required")
        cursor = "1"
        cursors = {"1"}
        keys = set()
        received = 0
        pointer = query.get("archive_folder", folder)
        _text(pointer)
        for page_index, entry in enumerate(pages):
            governing_envelope(entry)
            name = key + "-page-" + str(page_index) + ".json"
            if (
                entry.get("file") != name
                or entry.get("saved_content_equal") is not True
                or entry.get("archive_folder", pointer) != pointer
            ):
                raise ValueError("Exact native saved page receipt required")
            raw = archive.read(name)
            page = read(name)
            governing_envelope(page)
            if "sha256" in entry and entry["sha256"] != evidence[name]["sha256"]:
                raise ValueError("Native page receipt hash mismatch")
            if "bytes" in entry:
                _count(entry["bytes"], len(raw))
            params = page.get("parameters")
            body = page.get("body")
            url = urlsplit(_text(page.get("uri")))
            if (
                type(page.get("http_status")) is not int
                or page["http_status"] != 200
                or not isinstance(params, dict)
                or not isinstance(body, dict)
            ):
                raise ValueError("Successful native page envelope required")
            if (
                url.scheme != "https"
                or url.netloc != "api.datacite.org"
                or url.path != "/dois"
                or url.fragment
            ):
                raise ValueError("Exact native DataCite endpoint required")
            if (
                params.get("query") != wanted
                or params.get("page[cursor]") != cursor
                or type(params.get("page[size]")) not in (str, int)
                or str(params["page[size]"]) != str(size)
                or any(params.get(k) != v for k, v in options.items())
                or "page[number]" in params
            ):
                raise ValueError("Native request parameters/cursor drift")
            if url.query and any(
                k not in params or values != [str(params[k])]
                for k, values in parse_qs(url.query, keep_blank_values=True).items()
            ):
                raise ValueError("Native URI contradicts saved request parameters")
            governing_envelope(body)
            meta = body.get("meta")
            records = body.get("data")
            links = body.get("links")
            if (
                not isinstance(meta, dict)
                or not isinstance(records, list)
                or not isinstance(links, dict)
            ):
                raise ValueError("Native DataCite metadata/data/links required")  # noqa: TRY004 - malformed evidence uses ValueError
            governing_envelope(meta)
            _count(meta.get("total"), total)
            _count(entry.get("rows"), len(records))
            tp = meta.get("totalPages")
            if (
                type(tp) is not int
                or tp
                not in ({0, 1} if total == 0 else {max(1, (total + size - 1) // size)})
                or len(pages) != max(1, (total + size - 1) // size)
                or len(records) > size
            ):
                raise ValueError("Native page totals/row bounds contradict coverage")
            for record in records:
                # Reuse the qualified pure source identity/related-array validator.
                if not isinstance(record, dict) or not isinstance(
                    record.get("attributes"), dict
                ):
                    raise ValueError("Native source record object required")  # noqa: TRY004 - malformed evidence uses ValueError
                collector.project(record, record["attributes"].get("doi"))
                identity = _doi(record.get("id"))
                if identity in keys:
                    raise ValueError("Repeated native record across pages")
                if (
                    not isinstance(record["attributes"].get("xml"), str)
                    or not record["attributes"]["xml"]
                ):
                    raise ValueError("Full retained native XML metadata required")
                keys.add(identity)
            received += len(records)
            next_link = links.get("next")
            if page_index == len(pages) - 1:
                if next_link not in (None, ""):
                    raise ValueError("Terminal native page advertises continuation")
            else:
                link = urlsplit(_text(next_link))
                values = parse_qs(link.query, keep_blank_values=True)
                tokens = values.get("page[cursor]", [])
                if (
                    link.scheme != "https"
                    or link.netloc != "api.datacite.org"
                    or link.path != "/dois"
                    or link.fragment
                    or len(tokens) != 1
                    or not tokens[0]
                    or tokens[0] in cursors
                ):
                    raise ValueError("Unsafe or cycling native cursor continuation")
                if any(
                    k != "page[cursor]" and (k not in params or v != [str(params[k])])
                    for k, v in values.items()
                ):
                    raise ValueError("Native continuation changes query scope")
                cursor = tokens[0]
                cursors.add(cursor)
            headers = page.get("headers", {})
            if not isinstance(headers, dict):
                raise ValueError("Native HTTP headers object required")  # noqa: TRY004 - malformed evidence uses ValueError
            date = headers.get("Date", headers.get("date"))
            if date is not None and not isinstance(date, str):
                raise ValueError("Native provider Date must remain raw text or null")
            views.append(
                {
                    "targets": spec["targets"],
                    "records": records,
                    "data_path": "/body/data",
                    "page": page_index,
                    "entry": {
                        "name": name,
                        **evidence[name],
                        "source_url": page["uri"],
                        "parameters": copy.deepcopy(params),
                        "query_key": key,
                        "query_kind": spec["kind"],
                        "archive_folder": pointer,
                        "response_date": date,
                    },
                }
            )
        _count(query.get("received"), received)
        _count(query.get("unique_dois"), len(keys))
        _count(received, total)
    if query_keys != set(expected) or used != set(evidence):
        raise ValueError("Incomplete/unreferenced native query/file inventory")
    context = {
        "generation_id": run,
        "scope_sha256": manifest["scope_sha256"],
        "queries": queries,
        "captured_utc": manifest.get("captured_utc"),
        "until": cutoff,
        "consumer_scope": "native_full_baseline" if full else "native_overlap_update",
        "invalid_publication_value_count": len(inputs["invalid_values"]),
    }
    if context["captured_utc"] is not None:
        utc(_text(context["captured_utc"]))
    return context, ids, views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "publications", "generation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument(
        "--profile", choices=("exact_doi", "native_cursor"), default="exact_doi"
    )
    parser.add_argument("--native-receipt", type=Path)
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--prior-manifest", type=Path)
    parser.add_argument("--prior-sha256")
    args = parser.parse_args()
    parent = private_directory(args.output.parent)
    if args.output.resolve().is_relative_to(args.capture.resolve()):
        raise ValueError("Derived output must remain outside immutable archive")
    publications = strict_json(args.publications.read_bytes())
    generation = strict_json(args.generation.read_bytes())
    result = prepare(
        args.capture,
        publications,
        expected_manifest_sha256=args.manifest_sha256,
        generation=generation,
        profile=args.profile,
        native_receipt=args.native_receipt.read_bytes()
        if args.native_receipt
        else None,
        expected_receipt_sha256=args.receipt_sha256,
        prior_manifest=args.prior_manifest.read_bytes()
        if args.prior_manifest
        else None,
        expected_prior_sha256=args.prior_sha256,
    )
    raw = json_bytes(result)
    parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    write_verified(parent, args.output.name, raw)
    print("Prepared candidate DataCite relationship review; no native admission")


if __name__ == "__main__":
    main()
