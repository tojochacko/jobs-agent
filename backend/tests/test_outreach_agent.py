import pytest
from unittest.mock import patch, MagicMock

MOCK_HR = {"hr_name": "Jane Smith", "hr_email": "jane@acme.com", "hr_confidence": "search_result"}
MOCK_COVER = "Dear Jane,\n\nI am excited to apply for the Python Engineer role at Acme..."
MOCK_RESUME_PATH = "uploads/tailored_1.pdf"


def test_run_outreach_returns_draft():
    with patch("backend.agents.outreach.find_hr_contact", return_value=MOCK_HR), \
         patch("backend.agents.outreach.generate_cover_letter", return_value=MOCK_COVER), \
         patch("backend.agents.outreach.tailor_resume", return_value=MOCK_RESUME_PATH):
        from backend.agents.outreach import run_outreach
        result = run_outreach(
            job_id=1,
            company="Acme",
            job_description="Python Engineer at Acme",
            resume_path="uploads/master.pdf",
            output_dir="uploads",
        )
    assert result["hr_email"] == "jane@acme.com"
    assert result["cover_letter"] == MOCK_COVER
    assert result["resume_version_path"] == MOCK_RESUME_PATH
    assert result["hr_confidence"] == "search_result"


def test_run_outreach_proceeds_with_unknown_contact():
    """Outreach still generates cover letter even if HR contact is unknown."""
    unknown_hr = {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}
    with patch("backend.agents.outreach.find_hr_contact", return_value=unknown_hr), \
         patch("backend.agents.outreach.generate_cover_letter", return_value="Cover letter"), \
         patch("backend.agents.outreach.tailor_resume", return_value="uploads/t.pdf"):
        from backend.agents.outreach import run_outreach
        result = run_outreach(1, "Acme", "JD", "uploads/master.pdf", "uploads")
    assert result["hr_confidence"] == "unknown"
    assert result["cover_letter"] == "Cover letter"


def test_generate_cover_letter_returns_string():
    msg = MagicMock()
    msg.content = "Dear Jane,\n\nI am excited to apply for the Python Engineer role at Acme."
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    with patch("backend.agents.outreach.litellm.completion") as mock_completion, \
         patch("backend.tools.resume_tools._read_resume", return_value="Resume content"):
        mock_completion.return_value = resp
        from backend.agents.outreach import generate_cover_letter
        result = generate_cover_letter(
            job_description="Python Engineer at Acme",
            resume_path="uploads/resume.txt",
            company="Acme",
            hr_name="Jane Smith",
        )
    assert isinstance(result, str)
    assert "Jane" in result
