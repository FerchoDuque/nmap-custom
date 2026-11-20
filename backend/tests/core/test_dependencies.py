"""Guards that runtime/dev requirements stay fully pinned.

`requirements*.txt` are generated from `uv.lock` with
`uv export --frozen --format requirements-txt`; a stray `>=` means someone
edited them by hand or the export was done without the lock.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIREMENTS = [
    REPO_ROOT / "backend" / "requirements.txt",
    REPO_ROOT / "backend" / "requirements-dev.txt",
]

PINNED = re.compile(r"^[A-Za-z0-9_.\-]+(\[[^\]]+\])?==[^\s;]+")


def _requirements_lines(path: Path):
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("--hash"):
            continue
        yield line.removesuffix("\\").strip()


def test_requirements_files_exist():
    for path in REQUIREMENTS:
        assert path.is_file(), f"missing {path}"


def test_requirements_are_exactly_pinned():
    for path in REQUIREMENTS:
        for line in _requirements_lines(path):
            assert ">=" not in line and "~=" not in line, f"{path.name}: {line}"
            assert PINNED.match(line), f"{path.name}: not a pin: {line}"


def test_runtime_requirements_exclude_dev_tools():
    names = {
        line.split("==")[0].split("[")[0].strip().lower()
        for line in _requirements_lines(REPO_ROOT / "backend" / "requirements.txt")
    }

    # Note: pyyaml arrives transitively via uvicorn[standard], so it is not dev-only.
    assert not names & {"pytest", "pytest-asyncio", "pytest-cov", "httpx"}
