"""Declared publication notices and directional source links; no adjudication.

Policy: retain and label. Source declarations remain candidate evidence until
exact identity, authoritative linkage and native consumer acceptance are proven.
Titles, abstracts and arbitrary source prose never create notice decisions.
"""

import copy
import hashlib
import json
import re

# Pinned NLM output RefType vocabulary and directional role, not title matching.
# https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-CommentsCorrections.html
RELATIONS = {
    "RetractionIn": ("retraction-notice", "subject-record", "notice-record"),
    "RetractionOf": ("retraction-notice", "notice-record", "subject-record"),
    "ErratumIn": ("correction-notice", "subject-record", "notice-record"),
    "ErratumFor": ("correction-notice", "notice-record", "subject-record"),
    "CorrectedandRepublishedIn": (
        "correction-notice",
        "original-record",
        "corrected-version",
    ),
    "CorrectedandRepublishedFrom": (
        "correction-notice",
        "corrected-version",
        "original-record",
    ),
    "RetractedandRepublishedIn": (
        "retraction-notice",
        "retracted-original",
        "republished-version",
    ),
    "RetractedandRepublishedFrom": (
        "correction-notice",
        "republished-version",
        "retracted-original",
    ),
}
OTHER_REF_TYPES = {
    "AssociatedDataset",
    "AssociatedPublication",
    "CommentIn",
    "CommentOn",
    "ExpressionOfConcernIn",
    "ExpressionOfConcernFor",
    "RepublishedIn",
    "RepublishedFrom",
    "UpdateIn",
    "UpdateOf",
    "SummaryForPatientsIn",
    "OriginalReportIn",
    "ReprintIn",
    "ReprintOf",
    "Cites",
}
DECLARATIONS = {
    "retraction": "retraction-notice",
    "retracted": "retraction-notice",
    "retraction notice": "retraction-notice",
    "retraction of publication": "retraction-notice",
    "retracted publication": "retraction-notice",
    "correction": "correction-notice",
    "corrected": "correction-notice",
    "published erratum": "correction-notice",
    "erratum": "correction-notice",
    "corrected and republished article": "correction-notice",
}
FREE_TEXT = {
    "title",
    "articletitle",
    "fulltitle",
    "abstract",
    "abstracttext",
    "coistatement",
    "description",
    "refsource",
    "note",
}
TYPE_FIELDS = {"publicationnotice", "publicationtypes", "publicationtype", "notice"}


def _pmid(value):
    return (
        value
        if isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value)
        else None
    )


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _text(value.get("#text", value.get("Value")))
    if isinstance(value, list):
        return "".join(
            _text(item.get("Value")) for item in value if isinstance(item, dict)
        )
    return ""


def _identity_value(value):
    if isinstance(value, dict) and "#text" in value:
        return _identity_value(value["#text"])
    if isinstance(value, dict) and "Value" in value:
        return _identity_value(value["Value"])
    return copy.deepcopy(value)


def _child(nodes, name):
    return (
        next(
            (
                item.get("Value")
                for item in nodes
                if isinstance(item, dict) and item.get("Name") == name
            ),
            None,
        )
        if isinstance(nodes, list)
        else None
    )


def collect_notice_evidence(record, *, source_key=None, snapshot_revision=None):
    if not isinstance(record, dict):
        raise ValueError("Publication record must be an object")  # noqa: TRY004 - validator contract
    if source_key is not None and (
        not isinstance(source_key, str)
        or not source_key.startswith("pubmed:")
        or _pmid(source_key[7:]) is None
    ):
        raise ValueError("Exact PubMed source key required for notice binding")
    if snapshot_revision is not None and (
        not isinstance(snapshot_revision, str)
        or not snapshot_revision.strip()
        or snapshot_revision != snapshot_revision.strip()
    ):
        raise ValueError("Exact snapshot revision required")
    signals, links, issues, metadata_pmids = [], [], [], []

    def signal(value, path, *, ref_type=False):
        if not isinstance(value, str):
            issues.append({"path": path, "reason": "notice declaration must be text"})
            return None
        if ref_type:
            relation = RELATIONS.get(value)
            if relation is None and value in OTHER_REF_TYPES:
                return None
            if relation is None:
                issues.append(
                    {
                        "path": path,
                        "reason": "unqualified reference type",
                        "value": value,
                    }
                )
                return None
            flag = relation[0]
        else:
            normalized = " ".join(value.split()).casefold()
            relation = RELATIONS.get(value)
            flag = relation[0] if relation else DECLARATIONS.get(normalized)
        if flag:
            signals.append({"path": path, "value": value, "flag": flag})
        return flag

    def relation(ref_type, pmid, ref_source, note, path):
        flag = signal(ref_type, path + "/RefType", ref_type=True)
        qualified = RELATIONS.get(ref_type) if isinstance(ref_type, str) else None
        related = _pmid(pmid)
        if pmid not in (None, "") and related is None:
            issues.append(
                {
                    "path": path + "/PMID",
                    "reason": "related PMID is not canonical positive text",
                }
            )
        links.append(
            {
                "path": path,
                "ref_type": copy.deepcopy(ref_type),
                "related_pmid_raw": copy.deepcopy(pmid),
                "related_pmid": related,
                "related_ref_source": copy.deepcopy(ref_source),
                "related_note": copy.deepcopy(note),
                "flag": flag,
                "current_record_role": qualified[1] if qualified else "unqualified",
                "related_record_role": qualified[2] if qualified else "unqualified",
                "authoritative_linkage_verified": False,
                "consumer_accepted": False,
            }
        )

    def type_value(value, path):
        if isinstance(value, list):
            for index, item in enumerate(value):
                type_value(item, f"{path}/{index}")
        elif isinstance(value, dict):
            if "#text" in value:
                type_value(value["#text"], path + "/#text")
            elif value.get("Name") == "PublicationType":
                type_value(value.get("Value"), path + "/Value")
            elif "PublicationType" in value:
                type_value(value["PublicationType"], path + "/PublicationType")
            else:
                issues.append(
                    {"path": path, "reason": "unqualified publication type shape"}
                )
        elif isinstance(value, str):
            for token in value.split(";"):
                signal(token.strip(), path)
        else:
            issues.append(
                {"path": path, "reason": "publication type must be declared text"}
            )

    def visit(value, path):
        if isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}/{index}")
            return
        if not isinstance(value, dict):
            return
        name = value.get("Name")
        if isinstance(name, str):
            if name in (
                "MedlineCitation",
                "PublicationType",
                "CommentsCorrections",
            ) and value.get("Namespace") not in (None, ""):
                issues.append(
                    {
                        "path": path,
                        "reason": "unqualified XML namespace for notice declaration",
                    }
                )
                return
            if name.casefold() in FREE_TEXT:
                return
            children = value.get("Value")
            if name in ("MedlineCitation",):
                identities = (
                    [
                        item.get("Value")
                        for item in children
                        if isinstance(item, dict) and item.get("Name") == "PMID"
                    ]
                    if isinstance(children, list)
                    else []
                )
                for identity in identities:
                    candidate = _text(identity)
                    if candidate:
                        metadata_pmids.append(candidate)
                    else:
                        issues.append(
                            {"path": path, "reason": "source PMID is not declared text"}
                        )
            if name == "PublicationType":
                type_value(children, path + "/Value")
                return
            if name == "CommentsCorrections":
                attrs = value.get("Attributes")
                refs = (
                    [
                        a.get("Value")
                        for a in attrs
                        if isinstance(a, dict)
                        and a.get("Name") == "RefType"
                        and a.get("Namespace") in (None, "")
                    ]
                    if isinstance(attrs, list)
                    else []
                )
                if len(refs) != 1:
                    issues.append(
                        {
                            "path": path,
                            "reason": "exactly one reference type attribute required",
                        }
                    )
                else:
                    related = _child(children, "PMID")
                    relation(
                        refs[0],
                        _identity_value(related),
                        _text(_child(children, "RefSource")),
                        _text(_child(children, "Note")),
                        path,
                    )
                return
            visit(children, path + "/Value")
            return
        if "MedlineCitation" in value and isinstance(value["MedlineCitation"], dict):
            candidate = _text(value["MedlineCitation"].get("PMID"))
            if candidate:
                metadata_pmids.append(candidate)
        refs = [(key, value[key]) for key in ("@RefType", "RefType") if key in value]
        if refs:
            if len(refs) != 1:
                issues.append(
                    {"path": path, "reason": "ambiguous reference type attributes"}
                )
            else:
                relation(
                    refs[0][1],
                    _identity_value(value.get("PMID")),
                    value.get("RefSource"),
                    value.get("Note"),
                    path,
                )
        for key, child in value.items():
            lowered = key.casefold() if isinstance(key, str) else ""
            if lowered in FREE_TEXT or key in ("@RefType", "RefType", "MetadataJSON"):
                continue
            if lowered in TYPE_FIELDS:
                type_value(child, path + "/" + key)
            else:
                visit(child, path + "/" + str(key))

    visit(record, "record")
    for key, flag in [
        ("Retraction", "retraction-notice"),
        ("IsRetracted", "retraction-notice"),
        ("Correction", "correction-notice"),
        ("IsCorrected", "correction-notice"),
    ]:
        if record.get(key) is True:
            signals.append({"path": "record/" + key, "value": True, "flag": flag})
    raw = record.get("MetadataJSON")
    if raw is not None:
        if not isinstance(raw, str):
            issues.append(
                {"path": "MetadataJSON", "reason": "metadata JSON must remain text"}
            )
        else:
            try:
                metadata = json.loads(raw)
            except (ValueError, TypeError):
                issues.append(
                    {
                        "path": "MetadataJSON",
                        "reason": "invalid JSON; original value preserved",
                    }
                )
            else:
                if not isinstance(metadata, (dict, list)):
                    issues.append(
                        {"path": "MetadataJSON", "reason": "unsupported metadata shape"}
                    )
                else:
                    visit(metadata, "MetadataJSON")
    bound = source_key is not None and metadata_pmids == [source_key[7:]]
    if source_key is not None and metadata_pmids and not bound:
        issues.append(
            {
                "path": "MetadataJSON",
                "reason": "source PMID and notice metadata identity differ or repeat",
            }
        )
    labelable_signals = [
        item
        for item in signals
        if not (
            source_key is not None
            and metadata_pmids
            and not bound
            and item["path"].startswith("MetadataJSON")
        )
    ]
    for link in links:
        link["source_identity_bound"] = bound
        link["candidate_only"] = True
    return {
        "kind": "publication_notice_evidence_v1",
        "source_key": source_key,
        "snapshot_revision": snapshot_revision,
        "input_record_sha256": hashlib.sha256(
            json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest(),
        "flags": sorted({item["flag"] for item in labelable_signals}),
        "signals": signals,
        "links": links,
        "issues": issues,
        "source_identity_bound": bound,
        "candidate_only": True,
        "correction_authorized": False,
        "authoritative_linkage_verified": False,
        "consumer_accepted": False,
    }
