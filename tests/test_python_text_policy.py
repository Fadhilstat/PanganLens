from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOTS = ("src", "scripts", "tests")
EM_DASH = "\u2014"


def test_python_files_do_not_contain_em_dash():
    violations = []

    for root_name in PYTHON_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            if EM_DASH in text:
                violations.append(str(path.relative_to(REPO_ROOT)))

    assert violations == [], "em dash found in Python files: " + ", ".join(violations)
