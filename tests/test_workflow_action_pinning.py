import re
from pathlib import Path

WORKFLOW_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
USES_PATTERN = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)

PINNED_ACTIONS = {
    "actions/checkout": {
        "d23441a48e516b6c34aea4fa41551a30e30af803",
        "3d3c42e5aac5ba805825da76410c181273ba90b1",
    },
    "actions/setup-python": {"ece7cb06caefa5fff74198d8649806c4678c61a1"},
    "actions/upload-artifact": {"ea165f8d65b6e75b540449e92b4886f43607fa02"},
    "actions/configure-pages": {"983d7736d9b0ae728b81ab479565c72886d7745b"},
    "actions/upload-pages-artifact": {"7b1f4a764d45c48632c6b24a0339c27f5614fb0b"},
    "actions/deploy-pages": {"d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e"},
    "google-github-actions/auth": {"7c6bc770dae815cd3e89ee6cdf493a5fab2cc093"},
}


def _workflow_action_refs() -> list[tuple[Path, str]]:
    refs = []
    for workflow in sorted(WORKFLOW_DIR.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        refs.extend((workflow, match) for match in USES_PATTERN.findall(text))
    return refs


def test_external_workflow_actions_are_allowlisted_and_sha_pinned():
    refs = _workflow_action_refs()
    assert refs

    for workflow, ref in refs:
        if ref.startswith("./") or ref.startswith("docker://"):
            continue
        action, separator, revision = ref.rpartition("@")
        assert separator == "@", f"missing action revision in {workflow.name}: {ref}"
        assert SHA_PATTERN.fullmatch(revision), (
            f"external action is not pinned to a commit SHA in {workflow.name}: {ref}"
        )
        assert action in PINNED_ACTIONS, (
            f"external action requires explicit review before use in {workflow.name}: {action}"
        )
        assert revision in PINNED_ACTIONS[action], (
            f"unreviewed action SHA in {workflow.name}: {ref}"
        )


def test_workflows_do_not_use_moving_major_tags():
    for workflow in sorted(WORKFLOW_DIR.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        for ref in USES_PATTERN.findall(text):
            assert not re.search(r"@v\d+(?:\.|$)", ref), (
                f"moving action tag found in {workflow.name}: {ref}"
            )
