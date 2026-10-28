"""Offline PubMed element capture and explicit XML-shaped JSON profile.

Source XML bytes stay authoritative. Normalized mixed-content comparison is an
explicit representation profile, never a licence to edit stored metadata.
"""

import copy
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET

PROFILE = "pubmed-xml-document-offline-v2"


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _name(tag):
    if tag.startswith("{"):
        namespace, name = tag[1:].split("}", 1)
        return name, namespace
    return tag, ""


def _inner(element):
    return html.escape(element.text or "", quote=False) + "".join(
        ET.tostring(child, encoding="unicode") for child in element
    )


def xml_node(element):
    name, namespace = _name(element.tag)
    mixed = bool(
        len(element)
        and (
            element.text
            and element.text.strip()
            or any(child.tail and child.tail.strip() for child in element)
            or all(
                _name(child.tag)[0] in {"i", "b", "em", "strong", "sub", "sup"}
                for child in element
            )
        )
    )
    value = (
        _inner(element)
        if mixed
        else [xml_node(child) for child in element]
        if len(element)
        else html.escape(element.text, quote=False)
        if element.text is not None
        else []
    )
    attributes = [
        {"Name": _name(key)[0], "Namespace": _name(key)[1], "Value": value}
        for key, value in element.attrib.items()
    ]
    return {
        "Name": name,
        "Namespace": namespace,
        "Value": value,
        "Attributes": attributes,
    }


def canonical_nodes(nodes, *, mixed_content=False):
    if not isinstance(nodes, list):
        raise ValueError("XML-shaped metadata nodes must be a list")  # noqa: TRY004 - validator contract
    result = []
    for node in nodes:
        if (
            not isinstance(node, dict)
            or set(node) != {"Name", "Namespace", "Value", "Attributes"}
            or not isinstance(node["Name"], str)
            or not node["Name"]
            or not isinstance(node["Namespace"], str)
        ):
            raise ValueError("Exact named XML metadata node required")
        attrs = node["Attributes"]
        if not isinstance(attrs, list) or any(
            not isinstance(a, dict)
            or set(a) != {"Name", "Namespace", "Value"}
            or any(not isinstance(a[key], str) for key in a)
            for a in attrs
        ):
            raise ValueError("Exact XML attribute text required")
        attributes = sorted((a["Namespace"], a["Name"], a["Value"]) for a in attrs)
        if len({(a[0], a[1]) for a in attributes}) != len(attributes):
            raise ValueError("Duplicate XML attributes")
        value = node["Value"]
        if isinstance(value, list):
            content = ["nodes", canonical_nodes(value, mixed_content=mixed_content)]
            if mixed_content and not value:
                content = ["content", []]
        elif isinstance(value, str):
            content = ["text", value]
            if mixed_content:
                # Interpret one XML serialization layer, preserving encoded
                # literal tags as text and actual inline tags as elements.
                safe = re.sub(
                    r"&(?!amp;|lt;|gt;|quot;|apos;|#[0-9]+;|#x[0-9a-fA-F]+;)",
                    "&amp;",
                    value,
                )
                try:
                    fragment = ET.fromstring("<fragment>" + safe + "</fragment>")
                except ET.ParseError:
                    pass
                else:
                    content = ["content", _xml_content(fragment)]
        else:
            raise ValueError("XML metadata value must be text or child nodes")  # noqa: TRY004 - validator contract
        result.append([node["Namespace"], node["Name"], attributes, content])
    return result


def _xml_content(element):
    parts = []
    if element.text:
        parts.append(["text", element.text])
    for child in element:
        name, namespace = _name(child.tag)
        attrs = sorted(
            (*_name(key)[::-1], value) for key, value in child.attrib.items()
        )
        parts.append(["element", namespace, name, attrs, _xml_content(child)])
        if child.tail:
            parts.append(["text", child.tail])
    return parts


def metadata_paths(nodes, prefix=""):
    canonical_nodes(nodes)  # Reject unsupported nodes before flattening.
    values, occurrences = {}, {}
    for node in nodes:
        identity = (node["Namespace"], node["Name"])
        occurrences[identity] = occurrences.get(identity, 0) + 1
        path = (
            f"{prefix}/{{{node['Namespace']}}}{node['Name']}[{occurrences[identity]}]"
        )
        values[path + "/#node"] = (
            "children" if isinstance(node["Value"], list) else "text"
        )
        for attribute in node["Attributes"]:
            values[path + f"/@{{{attribute['Namespace']}}}{attribute['Name']}"] = (
                attribute["Value"]
            )
        if isinstance(node["Value"], list):
            values.update(metadata_paths(node["Value"], path))
        else:
            values[path + "/#value"] = node["Value"]
    return values


def compare_metadata(previous, current):
    a, b = canonical_nodes(previous), canonical_nodes(current)
    if a == b:
        return {"kind": "exact_values_and_order", "differences": []}
    before, after = metadata_paths(previous), metadata_paths(current)
    differences = [
        {
            "path": path,
            "previous_present": path in before,
            "current_present": path in after,
            "previous": before.get(path),
            "current": after.get(path),
        }
        for path in sorted(set(before) | set(after))
        if (path in before) != (path in after) or before.get(path) != after.get(path)
    ]
    equivalent = canonical_nodes(previous, mixed_content=True) == canonical_nodes(
        current, mixed_content=True
    )
    return {
        "kind": "xml_serialization_representation_only"
        if equivalent
        else "metadata_difference_preserved",
        "differences": differences,
        "order_or_structure_changed_without_leaf_delta": not differences,
    }


def article_metadata(article):
    if article.tag != "PubmedArticle":
        raise ValueError("Supported PubMed article required")
    # Keep complete article XML including root attributes and unknown elements.
    clone = copy.deepcopy(article)
    clone.tail = None
    xml = ET.tostring(clone, encoding="unicode")
    nodes = [xml_node(child) for child in article]
    canonical_nodes(nodes)
    return {
        "MetadataJSON": json.dumps(nodes, ensure_ascii=False, separators=(",", ":")),
        "ArticleXML": xml,
        "ArticleXMLSHA256": hashlib.sha256(xml.encode()).hexdigest(),
        "MetadataProfile": PROFILE,
    }
