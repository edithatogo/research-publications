"""Check workflow action references locally without a private repository dependency."""
import re
from pathlib import Path

import yaml


def check(root: Path) -> list[str]:
    issues = []

    def inspect(value, path):
        if isinstance(value, list):
            for item in value:
                inspect(item, path)
        elif isinstance(value, dict):
            for name, item in value.items():
                if name != "uses":
                    inspect(item, path)
                    continue
                pinned = isinstance(item, str) and (
                    re.fullmatch(r"(?:\./|\$/)\S+", item)
                    or re.fullmatch(r"[^\s@]+@[a-f0-9]{40}", item)
                    or re.fullmatch(r"docker://[^\s@]+@sha256:[a-f0-9]{64}", item)
                )
                if not pinned:
                    issues.append(f"{path}: action reference must use an immutable commit/digest or a local path")

    for path in sorted((root / ".github/workflows").glob("*")):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        inspect(yaml.safe_load(path.read_text()), path.relative_to(root))
    return issues


if __name__ == "__main__":
    errors = check(Path("."))
    if errors:
        raise SystemExit("\n".join(errors))
    print("Workflow action references are immutable or local.")
