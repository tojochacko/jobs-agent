# backend/tests/test_hr_finder.py
import pytest
from unittest.mock import patch, MagicMock


MOCK_SEARCH_RESULTS = [
    {
        "title": "Jane Smith - Recruiter at Acme Corp | LinkedIn",
        "link": "https://linkedin.com/in/jane-smith",
        "snippet": "Jane Smith is a Technical Recruiter at Acme Corp. Email: j.smith@acme.com"
    }
]


def test_find_hr_contact_returns_dict():
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = '{"hr_name": "Jane Smith", "hr_email": "j.smith@acme.com", "hr_confidence": "search_result"}'
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("backend.tools.hr_finder.search_people", return_value=MOCK_SEARCH_RESULTS), \
         patch("backend.tools.hr_finder.anthropic.Anthropic", return_value=mock_client):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Acme Corp", job_title="Python Engineer")
    assert isinstance(result, dict)
    assert "hr_name" in result
    assert "hr_email" in result
    assert "hr_confidence" in result


def test_find_hr_contact_returns_unknown_when_no_results():
    with patch("backend.tools.hr_finder.search_people", return_value=[]):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Unknown Co", job_title="Engineer")
    assert result["hr_confidence"] == "unknown"
    assert result["hr_email"] == ""


def test_find_hr_contact_handles_search_failure():
    with patch("backend.tools.hr_finder.search_people", side_effect=Exception("API error")):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Acme", job_title="Engineer")
    assert result["hr_confidence"] == "unknown"
