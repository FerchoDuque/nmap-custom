#!/usr/bin/env python3
"""Extract the CHANGELOG section for a release tag.

Used by `.github/workflows/release.yml` to build the GitHub Release notes
straight from `CHANGELOG.md` (single source of truth).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.md"

SECTION = re.compile(r"^##\s+\[(?P<version>[^\]]+)\][^\n]*$", re.MULTILINE)


def normalize_version(value: str) -> str:
    return value.strip().lstrip("vV")


def extract_section(text: str, version: str) -> str:
    """Return the changelog section for ``version`` as release notes."""
    wanted = normalize_version(version)
    matches = list(SECTION.finditer(text))

    for index, match in enumerate(matches):
        if normalize_version(match.group("version")) != wanted:
            continue

        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        if not body:
            raise LookupError(f"section for {wanted!r} is empty")
        return f"## {wanted}\n\n{body}\n"

    raise LookupError(f"no section for version {wanted!r} in CHANGELOG.md")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="tag or version, e.g. v0.1.0 or 0.1.0")
    parser.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG,
        help="path to CHANGELOG.md",
    )
    args = parser.parse_args(argv)

    try:
        notes = extract_section(args.changelog.read_text(encoding="utf-8"), args.version)
    except (LookupError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
