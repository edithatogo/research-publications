"""Offline DoRA metadata page and chunk proof from the retained commit validator.

Only the existing DoRA DAX templates are qualified here. PubMed projection,
manifest generation and native commit operations remain with shared owners.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE_PAGE_SIZE = 100
METADATA_CHUNK_SIZE = 20000


def page_query(table, cursor=None):
    """Render one exact generated source-page DAX query for its prior cursor."""
    if table not in ("DoraPublications", "DoraMetadataChunks"):
        raise ValueError("Only retained DoRA metadata page tables are qualified")
    path = ROOT / "config" / f"source-{table}-page.dax"
    query = path.read_text(encoding="utf-8")
    arity = {
        "PubMedPublications": 1,
        "PubMedMetadataChunks": 2,
        "PubMedAuthorEvidence": 3,
        "DoraSourceObservations": 1,
        "DoraPublications": 1,
        "DoraMetadataChunks": 2,
    }[table]
    values = ['""', "-1", "-1"][:arity]
    if cursor is not None:
        if len(cursor) != arity:
            raise ValueError(
                f"{table} page cursor must contain {arity} ordered key fields"
            )
        if not isinstance(cursor[0], str):
            raise ValueError(f"{table} page cursor first key must be text")
        values[0] = '"' + cursor[0].replace('"', '""') + '"'
        for index in range(1, arity):
            if type(cursor[index]) is not int:
                raise ValueError(f"{table} page cursor numeric fields must be integers")
            values[index] = str(cursor[index])
    variables = tuple(f"After{i}" for i in range(arity))
    for variable, value in zip(variables, values):
        pattern = rf"(?m)^VAR {variable} = .*?$"
        query, count = re.subn(pattern, f"VAR {variable} = {value}", query, count=1)
        if count != 1:
            raise ValueError(
                "Generated page query does not contain its declared cursor variables"
            )
    return query


def _page_rows(source, table, key_fields):
    expected_keys = {
        "DoraPublications": ("DORAKey",),
        "DoraMetadataChunks": ("DORAKey", "ChunkIndex"),
    }
    if table not in expected_keys or key_fields != expected_keys[table]:
        raise ValueError("Exact qualified DoRA table key fields required")
    pages = source.get("pages") if isinstance(source, dict) else None
    if (
        not isinstance(source, dict)
        or source.get("page_size") != NATIVE_PAGE_SIZE
        or not isinstance(pages, list)
        or not pages
    ):
        raise ValueError(f"{table} requires a page sequence and a terminal empty page")
    rows = []
    cursor = None
    empty_seen = False
    for number, page in enumerate(pages):
        if (
            not isinstance(page, dict)
            or type(page.get("page_number")) is not int
            or page.get("page_number") != number
            or page.get("http") != 200
        ):
            raise ValueError(f"{table} page ordering or HTTP result is incomplete")
        query = page_query(table, cursor)
        if (
            page.get("query") != query
            or page.get("query_sha256") != hashlib.sha256(query.encode()).hexdigest()
        ):
            raise ValueError(
                f"{table} page query/cursor fingerprint does not match the generated extractor"
            )
        body = page.get("body")
        if not isinstance(body, dict) or "error" in body or body.get("errors"):
            raise ValueError(f"{table} page response is malformed or contains an error")
        results = body.get("results")
        if isinstance(results, list) and any(
            isinstance(result, dict) and ("error" in result or result.get("errors"))
            for result in results
        ):
            raise ValueError(f"{table} result contains an error")
        tables = (
            results[0].get("tables")
            if isinstance(results, list)
            and len(results) == 1
            and isinstance(results[0], dict)
            else None
        )
        if isinstance(tables, list) and any(
            isinstance(result, dict) and ("error" in result or result.get("errors"))
            for result in tables
        ):
            raise ValueError(f"{table} table contains an error")
        page_rows = (
            tables[0].get("rows")
            if isinstance(tables, list)
            and len(tables) == 1
            and isinstance(tables[0], dict)
            else None
        )
        if not isinstance(page_rows, list) or len(page_rows) > NATIVE_PAGE_SIZE:
            raise ValueError(
                f"{table} page rows are missing or exceed the native page size"
            )
        if not page_rows:
            if number != len(pages) - 1 or empty_seen:
                raise ValueError(f"{table} has an early or repeated empty page")
            empty_seen = True
            continue
        if empty_seen:
            raise ValueError(f"{table} contains data after its terminal empty page")
        keys = []
        for row in page_rows:
            if not isinstance(row, dict):
                raise ValueError(  # noqa: TRY004 - retained validator ValueError contract
                    f"{table} page contains a missing or invalid key tuple"
                )
            if any(
                (
                    type(row.get(f"[{key}]")) is not int
                    if key in ("ChunkIndex", "AuthorIndex", "AffiliationIndex")
                    else not isinstance(row.get(f"[{key}]"), str)
                )
                for key in key_fields
            ):
                raise ValueError(
                    f"{table} page contains a missing or invalid key tuple"
                )
            key = tuple(row[f"[{field}]"] for field in key_fields)
            if key_fields[0] in ("PMID",) and (
                not str(key[0]).isascii() or not str(key[0]).isdecimal()
            ):
                raise ValueError(f"{table} page contains an invalid PubMed PMID")
            keys.append(key)
        if keys != sorted(keys) or (cursor is not None and keys[0] <= tuple(cursor)):
            raise ValueError(
                f"{table} page keys are not strictly ordered after the prior cursor"
            )
        rows.extend(page_rows)
        cursor = keys[-1]
    if not empty_seen:
        raise ValueError(f"{table} export lacks a complete terminal-page proof")
    all_keys = [tuple(row[f"[{field}]"] for field in key_fields) for row in rows]
    if len(set(all_keys)) != len(all_keys):
        raise ValueError(f"{table} export contains duplicate page keys")
    return rows, len(pages) - 1


def reconstruct_metadata_rows(chunks, key_column):
    """Reuse exact chunk/count/UTF-8/JSON validation for either publication source."""
    grouped = {}
    for row in chunks:
        pmid = row[f"[{key_column}]"]
        index, declared_count = row.get("[ChunkIndex]"), row.get("[ChunkCount]")
        declared_chars, value, encoding = (
            row.get("[MetadataCharacters]"),
            row.get("[MetadataChunk]"),
            row.get("[Encoding]"),
        )
        if (
            type(index) is not int
            or type(declared_count) is not int
            or declared_count <= 0
            or type(declared_chars) is not int
            or declared_chars <= 0
            or not isinstance(value, str)
            or len(value) > METADATA_CHUNK_SIZE
            or encoding != "UTF8-HEX"
            or re.fullmatch(r"[0-9a-fA-F]*", value) is None
        ):
            raise ValueError(
                "Metadata page has invalid chunk types, length, or encoding"
            )
        grouped.setdefault(pmid, []).append(row)
    documents = {}
    payload_entries = []
    payload_characters = 0
    for pmid, pmid_rows in sorted(grouped.items()):
        pmid_rows.sort(key=lambda row: row["[ChunkIndex]"])
        declared_counts = {row["[ChunkCount]"] for row in pmid_rows}
        declared_chars = {row["[MetadataCharacters]"] for row in pmid_rows}
        expected_chunks = pmid_rows[0]["[ChunkCount]"]
        joined = "".join(row["[MetadataChunk]"] for row in pmid_rows)
        if (
            declared_counts != {expected_chunks}
            or len(declared_chars) != 1
            or [row["[ChunkIndex]"] for row in pmid_rows]
            != list(range(expected_chunks))
            or len(pmid_rows) != expected_chunks
            or sum(len(row["[MetadataChunk]"]) for row in pmid_rows)
            != pmid_rows[0]["[MetadataCharacters]"]
            or expected_chunks
            != (pmid_rows[0]["[MetadataCharacters]"] + METADATA_CHUNK_SIZE - 1)
            // METADATA_CHUNK_SIZE
            or len(joined) % 2
        ):
            raise ValueError(
                "Metadata chunks are incomplete or their declared lengths/counts drift"
            )
        try:
            payload = bytes.fromhex(joined)
            payload.decode("utf-8")
            json.loads(payload)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "Reconstructed metadata payload is invalid UTF-8 JSON"
            ) from exc
        documents[pmid] = payload.decode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        payload_entries.append([pmid, digest])
        payload_characters += pmid_rows[0]["[MetadataCharacters]"]
    return documents, payload_entries, payload_characters


OFFICIAL_HANDLE = re.compile(
    r"https://dora\.health\.qld\.gov\.au/qldresearchjspui/handle/[1-9][0-9]*/[1-9][0-9]*\Z"
)
