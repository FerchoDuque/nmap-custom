"""Guards that every version source agrees before a release is tagged."""

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND = REPO_ROOT / "backend"
FRONTEND = REPO_ROOT / "frontend"


def _pyproject_version() -> str:
    with (BACKEND / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def _package_json_version() -> str:
    return json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))["version"]


def _fastapi_version() -> str:
    source = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    match = re.search(r"FastAPI\((?:[^)]*?)version=\"([^\"]+)\"", source, re.DOTALL)
    assert match, "FastAPI(version=...) not found in app/main.py"
    return match.group(1)


def test_backend_and_frontend_versions_match():
    assert _pyproject_version() == _package_json_version()


def test_api_reports_the_same_version():
    assert _fastapi_version() == _pyproject_version()
