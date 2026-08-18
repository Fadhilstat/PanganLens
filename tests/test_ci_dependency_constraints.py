from pathlib import Path

CONSTRAINTS = Path(__file__).resolve().parents[1] / "constraints" / "ci.txt"
PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
WORKFLOW_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"

EXPECTED_DIRECT_CONSTRAINTS = {
    "google-cloud-bigquery==3.43.0",
    "requests==2.34.2",
    "pytest==9.1.1",
    "ruff==0.16.3",
}


def test_ci_constraints_pin_reviewed_direct_dependencies():
    lines = {
        line.strip()
        for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert lines == EXPECTED_DIRECT_CONSTRAINTS


def test_package_metadata_keeps_compatible_version_ranges():
    text = PYPROJECT.read_text(encoding="utf-8")

    assert '"google-cloud-bigquery>=3.42,<4"' in text
    assert '"requests>=2.32,<3"' in text
    assert '"pytest>=8"' in text
    assert '"ruff>=0.12"' in text


def test_every_workflow_pip_install_uses_reviewed_constraints():
    installs = []
    for workflow in sorted(WORKFLOW_DIR.glob("*.yml")):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if "python -m pip install" in line:
                installs.append((workflow.name, line.strip()))

    assert installs
    for workflow_name, command in installs:
        assert "-c constraints/ci.txt" in command, (
            f"workflow pip install bypasses reviewed constraints in {workflow_name}: {command}"
        )
