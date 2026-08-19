import pytest

from panganlens.cloud_config import validate_cloud_variables

VALID_PROJECT_ID = "panganlens-demo"
VALID_PROVIDER = (
    "projects/123456789012/locations/global/"
    "workloadIdentityPools/panganlens-github/providers/panganlens-repo"
)


def test_cloud_variables_accept_reviewed_resource_shape():
    validate_cloud_variables(VALID_PROJECT_ID, VALID_PROVIDER)


@pytest.mark.parametrize(
    "project_id",
    [
        "Bad Project",
        "UPPERCASE",
        "abcd",
        "-panganlens",
    ],
)
def test_cloud_variables_reject_invalid_project_id(project_id):
    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        validate_cloud_variables(project_id, VALID_PROVIDER)


@pytest.mark.parametrize(
    "provider",
    [
        "projects/project-name/locations/global/workloadIdentityPools/panganlens-github/providers/panganlens-repo",
        "projects/123456789012/locations/us-central1/workloadIdentityPools/panganlens-github/providers/panganlens-repo",
        "projects/123456789012/locations/global/workloadIdentityPools/other/providers/panganlens-repo",
        "projects/123456789012/locations/global/workloadIdentityPools/panganlens-github/providers/other",
        "projects/123456789012/locations/global/workloadIdentityPools/panganlens-github",
    ],
)
def test_cloud_variables_reject_unreviewed_wif_provider(provider):
    with pytest.raises(ValueError, match="GCP_WIF_PROVIDER"):
        validate_cloud_variables(VALID_PROJECT_ID, provider)
