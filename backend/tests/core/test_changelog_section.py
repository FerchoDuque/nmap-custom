"""Tests for the release-notes extractor used by the release workflow."""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "changelog_section.py"

spec = importlib.util.spec_from_file_location("changelog_section", SCRIPT)
changelog_section = importlib.util.module_from_spec(spec)
spec.loader.exec_module(changelog_section)

SAMPLE = """# Changelog

## [Unreleased]

### Added
- futuro

## [0.2.0] — 2026-12-01

### Added
- nueva cosa

## [0.1.0] — 2026-11-14

### Fixed
- algo
"""


class TestExtractSection:
    def test_returns_only_the_requested_section(self):
        notes = changelog_section.extract_section(SAMPLE, "0.1.0")

        assert notes.startswith("## 0.1.0")
        assert "- algo" in notes
        assert "nueva cosa" not in notes
        assert "futuro" not in notes

    def test_accepts_v_prefixed_tag(self):
        assert changelog_section.extract_section(SAMPLE, "v0.2.0") == (
            changelog_section.extract_section(SAMPLE, "0.2.0")
        )

    def test_unknown_version_raises(self):
        with pytest.raises(LookupError, match="no section for version '9.9.9'"):
            changelog_section.extract_section(SAMPLE, "9.9.9")

    def test_empty_section_raises(self):
        text = "## [0.3.0] — 2026-12-02\n\n## [0.2.0] — 2026-12-01\n- x\n"

        with pytest.raises(LookupError, match="is empty"):
            changelog_section.extract_section(text, "0.3.0")


class TestCli:
    def test_writes_notes_and_exits_zero(self, tmp_path, capsys):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(SAMPLE, encoding="utf-8")

        assert changelog_section.main(["v0.1.0", "--changelog", str(changelog)]) == 0
        assert capsys.readouterr().out.startswith("## 0.1.0")

    def test_missing_version_exits_two(self, tmp_path, capsys):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(SAMPLE, encoding="utf-8")

        assert changelog_section.main(["v9.9.9", "--changelog", str(changelog)]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "no section" in captured.err


def test_real_changelog_covers_the_project_version():
    import tomllib

    with (REPO_ROOT / "backend" / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]

    notes = changelog_section.extract_section(
        (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version
    )

    assert notes.startswith(f"## {version}")
