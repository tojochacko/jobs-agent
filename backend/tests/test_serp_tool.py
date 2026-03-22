import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "serp_response.json").read_text()
)


@pytest.fixture
def mock_requests():
    with patch("backend.tools.serp.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = FIXTURE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        yield mock_get


def test_search_jobs_returns_list(mock_requests):
    from backend.tools.serp import search_jobs
    results = search_jobs(query="Python Engineer", location="Remote")
    assert isinstance(results, list)
    assert len(results) == 2


def test_search_jobs_maps_fields(mock_requests):
    from backend.tools.serp import search_jobs
    results = search_jobs(query="Python Engineer", location="Remote")
    job = results[0]
    assert job["title"] == "Senior Python Engineer"
    assert job["company"] == "Acme Corp"
    assert job["location"] == "Remote"
    assert job["url"] == "https://acme.com/careers/senior-python-engineer"
    assert "description" in job


def test_search_jobs_raises_on_api_error():
    from backend.tools.serp import search_jobs
    with patch("backend.tools.serp.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.side_effect = Exception("quota exceeded")
        with pytest.raises(Exception, match="quota exceeded"):
            search_jobs(query="Engineer")
