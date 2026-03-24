import json
import pytest
from unittest.mock import patch, MagicMock

MOCK_FORM = {
    "fields": [
        {"name": "first_name", "type": "text", "id": "first_name", "placeholder": ""},
        {"name": "email", "type": "email", "id": "email", "placeholder": ""},
    ],
    "url": "https://acme.com/apply",
    "title": "Apply at Acme",
}

MOCK_TAILORED = "John Doe\nSenior Python Engineer\nTailored for Acme role"


def _end_turn(text):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_run_applicator_returns_result():
    with patch("backend.agents.applicator.litellm.completion") as mock_completion, \
         patch("backend.agents.applicator.fetch_application_form", return_value=MOCK_FORM), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        payload = json.dumps({"first_name": "John", "email": "john@example.com"})
        mock_completion.return_value = _end_turn(payload)
        from backend.agents.applicator import run_applicator
        result = run_applicator(
            job_id=1,
            job_url="https://acme.com/apply",
            job_description="Senior Python Engineer",
            resume_path="uploads/resume.txt",
        )
    assert result["status"] == "ready"
    assert "form_payload" in result
    assert "tailored_resume" in result


def test_run_applicator_returns_manual_required_on_form_failure():
    with patch("backend.agents.applicator.fetch_application_form",
               return_value={"status": "manual_required", "url": "https://acme.com/apply"}), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        from backend.agents.applicator import run_applicator
        result = run_applicator(1, "https://acme.com/apply", "JD", "uploads/resume.txt")
    assert result["status"] == "manual_required"


def test_run_applicator_handles_invalid_json_from_llm():
    """Agent should still return ready status even if LLM returns malformed JSON."""
    with patch("backend.agents.applicator.litellm.completion") as mock_completion, \
         patch("backend.agents.applicator.fetch_application_form", return_value=MOCK_FORM), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        mock_completion.return_value = _end_turn("not valid json at all")
        from backend.agents.applicator import run_applicator
        result = run_applicator(1, "https://acme.com/apply", "JD", "uploads/resume.txt")
    assert result["status"] == "ready"
    assert result["form_payload"] == {}
