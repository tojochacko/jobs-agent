# backend/tests/test_resume_tools.py
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall
from backend.tools.resume_tools import tailor_resume, _read_resume


@pytest.fixture
def sample_resume(tmp_path):
    f = tmp_path / "resume.txt"
    f.write_text("John Doe\nSenior Python Engineer\nExperience: FastAPI, PostgreSQL, Docker")
    return str(f)


def test_tailor_resume_text_returns_string(sample_resume):
    with patch("backend.tools.resume_tools.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="Tailored resume text for Python role")
        result = tailor_resume(
            job_description="Senior Python Engineer at Acme",
            master_resume_path=sample_resume,
            output_format="text",
            output_path="",
        )
    assert isinstance(result, str)
    assert "Tailored" in result


def test_tailor_resume_pdf_writes_file(sample_resume, tmp_path):
    output_path = str(tmp_path / "tailored.pdf")
    with patch("backend.tools.resume_tools.llm.complete") as mock_complete, \
         patch("backend.tools.resume_tools._write_pdf") as mock_pdf:
        mock_complete.return_value = LLMResponse(content="Tailored resume content")
        result = tailor_resume(
            job_description="Senior Python Engineer at Acme",
            master_resume_path=sample_resume,
            output_format="pdf",
            output_path=output_path,
        )
    assert result == output_path
    mock_pdf.assert_called_once_with("Tailored resume content", output_path)


def test_tailor_resume_reads_resume_content(sample_resume):
    content = _read_resume(sample_resume)
    assert "Senior Python Engineer" in content
