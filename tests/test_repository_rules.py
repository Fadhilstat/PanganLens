from pathlib import Path


def test_python_files_do_not_contain_em_dash():
    root = Path(__file__).resolve().parents[1]
    offenders = []

    for path in root.rglob("*.py"):
        if chr(0x2014) in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(root)))

    assert offenders == []
