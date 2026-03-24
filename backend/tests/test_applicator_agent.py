# backend/tests/test_applicator_agent.py
import json
import pytest
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall

MOCK_FORM = {
    "fields": [
        {"name": "first_name", "type": "text", "id": "first_name", "placeholder": ""},
        {"name": "email", "type": "email", "id": "email", "placeholder": ""},
    ],
    "url": "https://acme.com/apply",
    "title": "Apply at Acme",
}

MOCK_TAILORED = "John Doe\nSenior Python Engineer\nTailored for Acme role"


def test_run_applicator_returns_result():
    from backend.agents.applicator import run_applicator
    payload = json.dumps({"first_name": "John", "email": "john@example.com"})
    with patch("backend.agents.applicator.llm.complete") as mock_complete, \
         patch("backend.agents.applicator.fetch_application_form", return_value=MOCK_FORM), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        mock_complete.return_value = LLMResponse(content=payload)
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
    from backend.agents.applicator import run_applicator
    with patch("backend.agents.applicator.fetch_application_form",
               return_value={"status": "manual_required", "url": "https://acme.com/apply"}), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        result = run_applicator(1, "https://acme.com/apply", "JD", "uploads/resume.txt")
    assert result["status"] == "manual_required"


def test_run_applicator_handles_invalid_json_from_llm():
    from backend.agents.applicator import run_applicator
    with patch("backend.agents.applicator.llm.complete") as mock_complete, \
         patch("backend.agents.applicator.fetch_application_form", return_value=MOCK_FORM), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        mock_complete.return_value = LLMResponse(content="not valid json at all")
        result = run_applicator(1, "https://acme.com/apply", "JD", "uploads/resume.txt")
    assert result["status"] == "ready"
    assert result["form_payload"] == {}
