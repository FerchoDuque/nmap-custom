"""Guards that GitHub Actions workflows stay valid YAML.

A broken workflow fails in ~0 s and silently leaves the repository without CI,
which is how `.github/workflows/ci.yml` shipped with an unquoted
``sqlite:///:memory:`` value.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))


def test_at_least_one_workflow_exists():
    assert WORKFLOWS, "no GitHub Actions workflow found"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_is_valid_yaml(path):
    # `yaml.safe_load` raises on the classic `key: sqlite:///:memory:` mistake.
    document = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert isinstance(document, dict), "workflow must be a YAML mapping"
    assert document.get("jobs"), "workflow must declare at least one job"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_steps_declare_a_command(path):
    document = yaml.safe_load(path.read_text(encoding="utf-8"))

    for job_name, job in document["jobs"].items():
        for index, step in enumerate(job.get("steps", [])):
            assert "uses" in step or "run" in step, (
                f"{path.name}:{job_name} step {index} has neither `uses` nor `run`"
            )


def _load(name: str) -> dict:
    return yaml.safe_load((REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def test_release_workflow_does_not_grant_write_to_the_called_ci():
    """Only the job publishing the release may write repository contents.

    A workflow-level `contents: write` leaks that permission into the whole
    `ci` job (and any action it runs), which is unnecessary attack surface.
    """
    document = _load("release.yml")

    assert document["permissions"]["contents"] == "read"
    assert document["jobs"]["ci"]["permissions"]["contents"] == "read"
    assert document["jobs"]["release"]["permissions"]["contents"] == "write"


def test_docker_workflow_can_push_but_not_write_source():
    document = _load("docker.yml")

    assert document["permissions"]["packages"] == "write"
    assert document["permissions"]["contents"] == "read"
