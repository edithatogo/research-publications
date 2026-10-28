# SPDX-License-Identifier: Apache-2.0
"""Offline candidate references from complete, pinned NIH RePORTER PMID pages.

No provider transport or persistence adapter. RePORTER includes non-NIH awards;
a core-project reference is not an admitted award or institutional funding fact.
"""

from __future__ import annotations

import copy
import hashlib
import re

from scripts.award_identifier_crosswalks import exact_text, governing_envelope
from scripts.plan_publication_stub_restore import strict_json_loads, utc
from scripts.source_relationship_evidence import fingerprint

ENDPOINT = "https://api.reporter.nih.gov/v2/publications/search"


def _pin(value, expected):
    if not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected):
        raise ValueError("Independent exact SHA256 pin required")
    if fingerprint(value) != expected:
        raise ValueError("Pinned input changed")


def _count(value, expected=None):
    if (
        type(value) is not int
        or value < 0
        or expected is not None
        and value != expected
    ):
        raise ValueError("Exact actual-integer count required")
    return value


def _pmid(value):
    if (
        not isinstance(value, str)
        or not re.fullmatch("[1-9][0-9]*", value)
        or int(value) > 2147483647
    ):
        raise ValueError("Exact positive int32 PMID text required")
    return value


def _complete(value):
    governing_envelope(value)
    if value.get("complete") is not True or value.get("next_links") != []:
        raise ValueError("Complete independently bound input required")


def project(
    pages,
    scope,
    publications,
    generation,
    *,
    expected_pages_sha256,
    expected_scope_sha256,
    expected_generation_sha256,
):
    """Validate every supplied raw page before returning any candidate assertions.

    Each query contains exactly one PMID, preventing wildcard or broadening
    ambiguity. The documented offset ceiling is explicit: larger scopes need
    a separately qualified source profile, never truncation.
    """
    _pin(pages, expected_pages_sha256)
    _pin(scope, expected_scope_sha256)
    _pin(generation, expected_generation_sha256)
    pages, scope, publications, generation = copy.deepcopy(
        (pages, scope, publications, generation)
    )
    if not isinstance(pages, list) or not isinstance(publications, list):
        raise ValueError("Explicit page and canonical arrays required")  # noqa: TRY004 - malformed evidence contract
    _complete(scope)
    if scope.get("kind") != "nih_reporter_publication_scope_v1":
        raise ValueError("Explicit NIH RePORTER publication scope required")
    snapshot = exact_text(scope.get("source_snapshot_id"))
    pmids = scope.get("pmids")
    if not isinstance(pmids, list) or not pmids or len(pmids) > 50000:
        raise ValueError("Nonempty bounded exact PMID scope required")
    for value in pmids:
        _pmid(value)
    if pmids != sorted(set(pmids), key=int):
        raise ValueError("Unique numerically ordered PMID scope required")
    _complete(generation)
    if (
        generation.get("kind") != "nih_reporter_publication_generation_v1"
        or generation.get("source_snapshot_id") != snapshot
        or generation.get("scope_sha256") != expected_scope_sha256
        or generation.get("pages_sha256") != expected_pages_sha256
        or generation.get("publications_sha256") != fingerprint(publications)
    ):
        raise ValueError("Source/canonical generation binding differs")
    for field in ("generation_id", "canonical_snapshot_id"):
        exact_text(generation.get(field))
    _count(generation.get("publication_count"), len(publications))
    _count(generation.get("page_count"), len(pages))
    canonical = {}
    canonical_keys = set()
    for record in publications:
        if not isinstance(record, dict):
            raise ValueError("Structured canonical publication required")  # noqa: TRY004 - malformed evidence contract
        key = exact_text(record.get("CanonicalKey"))
        if key.casefold() in canonical_keys:
            raise ValueError("Duplicate canonical identity")
        canonical_keys.add(key.casefold())
        if record.get("PMID") not in (None, ""):
            canonical.setdefault(_pmid(record["PMID"]), []).append(key)

    queries = {pmid: [] for pmid in pmids}
    file_names = set()
    for page in pages:
        _complete(page)
        if (
            page.get("url") != ENDPOINT
            or page.get("method") != "POST"
            or type(page.get("http_status")) is not int
            or page["http_status"] != 200
        ):
            raise ValueError("Exact successful publication-search response required")
        name = exact_text(page.get("name"))
        if (
            name in file_names
            or any(c in name for c in ("/", "\\"))
            or name in (".", "..")
        ):
            raise ValueError("Unique leaf evidence name required")
        file_names.add(name)
        if "observed_utc" not in page:
            raise ValueError("Explicit observation or unknown null required")
        if page["observed_utc"] is not None:
            utc(page["observed_utc"])
        raw = page.get("raw")
        if not isinstance(raw, bytes) or len(raw) > 16000000:
            raise ValueError("Bounded exact raw response bytes required")
        _count(page.get("bytes"), len(raw))
        if hashlib.sha256(raw).hexdigest() != page.get("sha256"):
            raise ValueError("Raw page hash differs")
        request = page.get("request")
        if not isinstance(request, dict) or set(request) != {
            "criteria",
            "offset",
            "limit",
            "sort_field",
            "sort_order",
        }:
            raise ValueError("Exact bounded search request profile required")
        criteria = request["criteria"]
        if (
            not isinstance(criteria, dict)
            or set(criteria) != {"pmids"}
            or not isinstance(criteria["pmids"], list)
            or len(criteria["pmids"]) != 1
        ):
            raise ValueError("Exactly one explicit PMID per query required")
        native_pmid = criteria["pmids"][0]
        if (
            type(native_pmid) is not int
            or native_pmid <= 0
            or str(native_pmid) not in queries
        ):
            raise ValueError("Request PMID outside pinned scope")
        offset = _count(request["offset"])
        limit = _count(request["limit"])
        if (
            offset > 9999
            or not 1 <= limit <= 500
            or request["sort_field"] != "core_project_nums"
            or request["sort_order"] != "asc"
        ):
            raise ValueError("Unsupported offset, limit or sort profile")
        doc = strict_json_loads(raw)
        governing_envelope(doc)
        meta = doc.get("meta")
        governing_envelope(meta)
        results = doc.get("results")
        total = _count(meta.get("total"))
        if (
            total > 10000
            or not isinstance(results, list)
            or meta.get("sort_field") != request["sort_field"]
            or meta.get("sort_order") != request["sort_order"]
        ):
            raise ValueError("Unqualified response coverage/sort")
        _count(meta.get("offset"), offset)
        _count(meta.get("limit"), limit)
        if offset > total or len(results) != min(limit, max(total - offset, 0)):
            raise ValueError("Partial or contradictory response length")
        if any(
            meta.get(k) not in (None, [], "")
            for k in ("next", "next_link", "next_cursor")
        ):
            raise ValueError("Unexpected continuation profile")
        queries[str(native_pmid)].append((offset, limit, total, page, results))

    rows = []
    coverage = []
    revision = fingerprint(
        [expected_scope_sha256, expected_pages_sha256, expected_generation_sha256]
    )
    for pmid in pmids:
        group = sorted(queries[pmid], key=lambda item: item[0])
        if not group:
            raise ValueError("Missing PMID query; not zero coverage")
        total, limit = group[0][2], group[0][1]
        expected_offsets = list(range(0, total, limit)) if total else [0]
        if [p[0] for p in group] != expected_offsets or any(
            p[1:3] != (limit, total) for p in group
        ):
            raise ValueError("Incomplete, duplicated or drifting pagination")
        seen_projects = set()
        ordered_projects = []
        for offset, _, _, page, results in group:
            for index, record in enumerate(results):
                governing_envelope(record)
                if type(record.get("pmid")) is not int or str(record["pmid"]) != pmid:
                    raise ValueError("Returned PMID differs from exact query")
                project_id = exact_text(record.get("coreproject"))
                if not re.fullmatch("[A-Za-z0-9][A-Za-z0-9.-]{0,99}", project_id):
                    raise ValueError("Unsupported literal core-project identity")
                if project_id in seen_projects:
                    raise ValueError("Duplicate/conflicting latest project reference")
                seen_projects.add(project_id)
                ordered_projects.append(project_id)
                if "applid" not in record:
                    raise ValueError(
                        "Explicit latest application value or unknown null required"
                    )
                app_id = record.get("applid")
                if app_id is not None and (
                    type(app_id) is not int or not 1 <= app_id <= 2147483647
                ):
                    raise ValueError(
                        "Latest application ID must be int32 or unknown null"
                    )
                matches = sorted(canonical.get(pmid, []))
                rows.append(
                    {
                        "EvidenceKey": "nih-reporter:publication:"
                        + pmid
                        + "|core-project:"
                        + project_id,
                        "RelationshipKind": "publication_reporter_core_project_reference",
                        "FromKey": "pmid:" + pmid,
                        "ToKey": "nih-reporter:core-project:" + project_id,
                        "PublicationPMID": pmid,
                        "CoreProjectNumber": project_id,
                        "LatestApplicationID": app_id,
                        "CanonicalKey": matches[0] if len(matches) == 1 else "",
                        "CanonicalCandidates": matches,
                        "CanonicalMatchCount": len(matches),
                        "Diagnostic": None
                        if len(matches) == 1
                        else "canonical_identity_unresolved",
                        "SourceURL": ENDPOINT,
                        "RawSHA256": page["sha256"],
                        "ObservedUTC": page["observed_utc"],
                        "SourcePaths": [page["name"] + ":/results/" + str(index)],
                        "SourceRecord": copy.deepcopy(record),
                        "Request": copy.deepcopy(page["request"]),
                        "SourceSnapshotID": snapshot,
                        "GenerationID": generation["generation_id"],
                        "CanonicalSnapshotID": generation["canonical_snapshot_id"],
                        "ProjectionRevisionSHA256": revision,
                        "SourceInputSHA256": expected_pages_sha256,
                        "ReviewState": "Not reviewed",
                        "Confidence": "candidate",
                        "IdentityQualified": False,
                        "CanonicalAdmission": False,
                        "NativeG06Admission": False,
                        "MutationAuthorized": False,
                        "AwardIdentityQualified": False,
                        "FundingAttribution": None,
                    }
                )
        if ordered_projects != sorted(ordered_projects):
            raise ValueError("Page ordering contradicts requested stable sort")
        coverage.append(
            {
                "PMID": pmid,
                "complete": True,
                "returned_references": total,
                "interpretation": "no returned references"
                if total == 0
                else "source references only",
            }
        )
    return {
        "kind": "nih_reporter_publication_candidates_v1",
        "native_acceptance": False,
        "source_authority_qualified": False,
        "mutation_authorized": False,
        "complete_supplied_scope": True,
        "coverage": coverage,
        "rows": rows,
        "canonical_publication_count": len(publications),
        "projection_revision_sha256": revision,
        "source_pages_sha256": expected_pages_sha256,
        "scope_sha256": expected_scope_sha256,
        "generation_sha256": expected_generation_sha256,
    }
