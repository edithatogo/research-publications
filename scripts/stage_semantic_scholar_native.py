# SPDX-License-Identifier: Apache-2.0
"""Prepare complete cached Semantic Scholar evidence for the existing native readers.

This command performs no network calls and no native writes. Deferred collections
require an explicit quota-limited bootstrap mode and retained HTTP 429 evidence.
"""

import argparse
import base64
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from collect_semantic_scholar_publications import FIELDS, lookup_id, matches
from enrich_europe_pmc import clean_pmid
from export_publication_register import key_hash
from publication_source_pass import field_paths


def read(path):
    return json.loads(path.read_bytes())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stage(args):
    canonical = read(args.canonical)
    coverage = read(args.coverage)
    rows = canonical["records"]
    keys = {r["CanonicalKey"] for r in rows}
    expected = canonical["expected_canonical_count"]
    if len(rows) != len(keys) or len(keys) != expected:
        raise ValueError("Canonical identity count drift")
    if key_hash(rows) != canonical["expected_key_sha256"]:
        raise ValueError("Canonical key hash drift")
    if coverage["canonical_key_sha256"] != canonical["expected_key_sha256"]:
        raise ValueError("Collection uses a different frozen key set")
    manifest = coverage["manifest"]
    if len(manifest) != expected or {r["key"] for r in manifest} != keys:
        raise ValueError("Collection key set differs from canonical bibliography")
    counts = Counter(r["status"] for r in manifest)
    quota_bootstrap = (
        getattr(args, "quota_bootstrap", False)
        and (coverage.get("stopped") or {}).get("status") == 429
        and counts.get("matched", 0) > 0
    )
    allowed = {"matched", "no match", "missing identifier", "ambiguous"}
    if quota_bootstrap:
        allowed.add("deferred")
    if (counts.get("deferred") and not quota_bootstrap) or any(
        s not in allowed
        for s in counts
    ):
        raise ValueError("Collection incomplete; no native generation admitted")
    if dict(counts) != coverage["counts"]:
        raise ValueError("Coverage disposition counts drift")
    canonical_by_key = {r["CanonicalKey"]: r for r in rows}
    staged = []
    fields = Counter()
    for item in manifest:
        if item["source"] != "Semantic Scholar":
            raise ValueError("Unexpected source")
        identifier = lookup_id(canonical_by_key[item["key"]])
        if identifier != item["identifier"]:
            raise ValueError("Lookup identifier drift")
        record = dict(item, versions=[])
        observation = coverage["observations"].get(item["observation"])
        if observation:
            archive = Path(observation["archive"])
            if not archive.is_absolute():
                archive = args.coverage.parent / archive
            raw = archive.read_bytes()
            if "scope" in (receipt := json.loads(raw)):
                raw = base64.b64decode(receipt["raw"], validate=True)
                scope = json.loads(receipt["scope"])
                if scope != {"ids": [identifier], "fields": FIELDS, "transport": "single"}:
                    raise ValueError("Unexpected cache scope")
                if digest(raw) != receipt["sha256"] or receipt["httpStatus"] != 200:
                    raise ValueError("Cache integrity failure")
            if json.loads(raw) != observation["record"]:
                raise ValueError("Cached response differs from projected record")
            record["versions"] = [observation]
            record["requestEvidence"] = {
                "httpStatus": 200, "sha256": digest(raw),
                "rawBase64": base64.b64encode(raw).decode(),
            }
            if item["status"] == "matched":
                if not matches(identifier, observation["record"]):
                    raise ValueError("Unverified identifier admitted as matched")
                returned_pmid = (observation["record"].get("externalIds") or {}).get("PubMed")
                canonical_pmid = clean_pmid(canonical_by_key[item["key"]].get("PMID"))
                if returned_pmid and canonical_pmid and str(returned_pmid) != canonical_pmid:
                    raise ValueError("Conflicting PMID admitted as matched")
                fields.update(set(field_paths(observation["record"])))
        elif item["status"] == "no match":
            scope = json.dumps({"ids": [identifier], "fields": FIELDS, "transport": "single"}, sort_keys=True)
            receipt = read(args.coverage.parent / (digest(scope.encode()) + ".json"))
            raw = base64.b64decode(receipt["raw"], validate=True)
            if receipt["scope"] != scope or receipt["httpStatus"] != 404 or digest(raw) != receipt["sha256"]:
                raise ValueError("No-match cache integrity failure")
            if "not found" not in json.loads(raw).get("error", "").lower():
                raise ValueError("No-match response lacks explicit not-found evidence")
            record["requestEvidence"] = receipt
        elif item["status"] == "deferred" and quota_bootstrap and identifier:
            record["deferralEvidence"] = {"httpStatus": 429, "reason": "Provider quota stop; identifier not yet resolved"}
        elif item["status"] != "missing identifier" or identifier is not None:
            raise ValueError("Disposition lacks retained evidence")
        staged.append(record)
    if dict(fields) != coverage["field_presence"]:
        raise ValueError("Field coverage differs from retained responses")

    previous = read(args.upload_manifest)
    old_files = [f for f in previous["files"] if not f["name"].endswith("manifest.json")]
    for f in old_files:
        if digest(Path(f["path"]).read_bytes()) != f["sha256"]:
            raise ValueError("Prior accepted archive has changed")
    definition = read(args.definition)
    candidate = copy.deepcopy(definition)
    args.output.mkdir(parents=True, exist_ok=False)
    files = []
    for start in range(0, len(staged), 50):
        raw = json.dumps(staged[start:start + 50], ensure_ascii=False, sort_keys=True).encode()
        name = f"semantic-scholar-{coverage['canonical_key_sha256'][:12]}-{start // 50:03d}-{digest(raw)[:12]}.json"
        path = args.output / name
        path.write_bytes(raw)
        files.append({"name": name, "path": str(path.resolve()), "sha256": digest(raw)})
    names = [f["name"] for f in old_files + files]
    affected = {"PublicationSourceEvidence", "PublicationSourceRecordChunks", "PublicationSourceArchiveChunks", "PublicationSourceFields"}
    changed = set()
    for part in candidate["definition"]["parts"]:
        if part["path"] not in {"definition/tables/" + n + ".tmdl" for n in affected}:
            continue
        text = base64.b64decode(part["payload"]).decode()
        text, n = re.subn(r"Names=\{[^\n]+\}", "Names={" + ",".join(json.dumps(v) for v in names) + "}", text)
        if n != 1:
            raise ValueError("Unexpected native reader shape")
        text = text.replace(f"Table.RowCount(Selected)={len(old_files)} ", f"Table.RowCount(Selected)={len(names)} ")
        text = text.replace("=2688 ", f"={expected * 3} ")
        text = text.replace("Result=Table.FromRecords(Rows),", "Result=Table.FromRecords(Rows, null, MissingField.UseNull),")
        part["payload"] = base64.b64encode(text.encode()).decode()
        changed.add(part["path"].rsplit("/", 1)[-1][:-5])
    if changed != affected:
        raise ValueError("Missing native source reader")
    report = {"canonical": expected, "counts": dict(counts), "field_presence": dict(fields),
              "coverage": "quota-limited native bootstrap; collection incomplete" if counts.get("deferred") else "complete frozen lookup set",
              "requestedFieldCoverage": {name: {"present": fields[name], "absentFromMatchedResponses": counts["matched"] - fields[name]} for name in FIELDS.split(",")},
              "uniqueSourcePublicationPairs": expected * 3,
              "newFiles": len(files), "allFiles": len(names), "nativeWrites": 0, "providerRequests": 0}
    outputs = {"upload-manifest.json": {**previous, "files": files},
               "combined-upload-manifest.json": {**previous, "files": old_files + files},
               "model-candidate.json": candidate, "stage-report.json": report}
    for name, value in outputs.items():
        (args.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quota-bootstrap", action="store_true", help="Stage an explicitly incomplete HTTP-429-limited native bootstrap")
    for name in ["canonical", "coverage", "upload-manifest", "definition", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(stage(parser.parse_args())))
