# LiteLLM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Anthropic SDK with LiteLLM across all agents so the LLM provider can be changed via environment variable without touching code.

**Architecture:** Direct `litellm.completion()` calls in each of the 5 files that currently use `anthropic.Anthropic()`. The tool use agentic loop in `job_scout.py` is rewritten from Anthropic's format to OpenAI function calling format, which LiteLLM uses universally across providers. Tests are updated to mock `litellm.completion` instead of `anthropic.Anthropic`.

**Tech Stack:** `litellm>=1.40.0` (replaces `anthropic>=0.40.0`). All commands run inside the Docker container: `docker compose exec backend <cmd>`.

**Spec:** `docs/superpowers/specs/2026-03-24-litellm-migration-design.md`

---

## File Map

| File | Action | Notes |
|---|---|---|
| `backend/requirements.txt` | Modify | Remove `anthropic`, add `litellm` |
| `backend/config.py` | Modify | Prefix model defaults, add optional provider key fields |
| `backend/agents/orchestrator.py` | Modify | Simple pattern swap |
| `backend/agents/applicator.py` | Modify | Simple pattern swap |
| `backend/agents/outreach.py` | Modify | Simple pattern swap |
| `backend/tools/resume_tools.py` | Modify | Simple pattern swap |
| `backend/agents/job_scout.py` | Modify | Full tool use loop rewrite |
| `backend/tests/test_orchestrator.py` | Modify | New mock shape + patch target |
| `backend/tests/test_applicator_agent.py` | Modify | New mock shape + patch target |
| `backend/tests/test_outreach_agent.py` | Modify | Add `generate_cover_letter` test |
| `backend/tests/test_resume_tools.py` | Modify | New mock shape + patch target |
| `backend/tests/test_job_scout_agent.py` | Modify | Rewrite all 3 tests + helpers |

---

## Task 1: Swap Dependency and Update Config Defaults

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config.py`

No tests for this task — these are pure config changes.

- [ ] **Step 1: Update requirements.txt**

Replace the anthropic line with litellm:

```
# backend/requirements.txt
# Remove:
anthropic>=0.40.0
# Add:
litellm>=1.40.0
```

The final relevant lines should look like:
```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
pydantic-settings==2.6.1
python-multipart==0.0.12
litellm>=1.40.0
requests==2.32.3
...
```

- [ ] **Step 2: Update config.py model defaults and add optional provider keys**

```python
# backend/config.py
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ORCHESTRATOR_MODEL: str = "anthropic/claude-haiku-4-5"
    SCOUT_MODEL: str = "anthropic/claude-haiku-4-5"
    APPLICATOR_MODEL: str = "anthropic/claude-haiku-4-5"
    OUTREACH_MODEL: str = "anthropic/claude-haiku-4-5"

    SERP_API_KEY: str = ""
    JOB_MATCH_THRESHOLD: float = 0.6
    WEBHOOK_BYPASS_THRESHOLD: bool = False

    EMAIL_PROVIDER: str = "gmail"
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    OUTLOOK_CLIENT_ID: str = ""
    OUTLOOK_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/email/callback"

    WEBHOOK_SECRET: str = ""

    DATABASE_URL: str = "sqlite:///./jobapplier.db"
    UPLOAD_DIR: str = "uploads"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

Key changes: `ANTHROPIC_API_KEY` is now optional (default `""`), model defaults are prefixed with `anthropic/`, `OPENAI_API_KEY` and `GEMINI_API_KEY` added as optional anchors.

- [ ] **Step 3: Update test_config.py default value assertion**

`test_default_values` in `backend/tests/test_config.py` asserts the exact default for `SCOUT_MODEL`. Update line 39 to reflect the new prefixed default:

```python
# backend/tests/test_config.py — test_default_values function
# Change:
assert s.SCOUT_MODEL == "claude-haiku-4-5"
# To:
assert s.SCOUT_MODEL == "anthropic/claude-haiku-4-5"
```

Leave `test_settings_load_from_env` unchanged — it explicitly sets `SCOUT_MODEL` to `"claude-haiku-4-5"` as an env override, so the assertion `s.SCOUT_MODEL == "claude-haiku-4-5"` remains correct (env vars override defaults).

- [ ] **Step 4: Run config tests to verify they pass**

```bash
docker compose exec backend pytest backend/tests/test_config.py -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/config.py backend/tests/test_config.py
git commit -m "feat(litellm): swap anthropic for litellm, prefix model defaults"
```

---

## Task 2: Migrate orchestrator.py (TDD)

**Files:**
- Modify: `backend/agents/orchestrator.py`
- Modify: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: Update tests to expect LiteLLM response shape**

Replace the entire content of `backend/tests/test_orchestrator.py`:

```python
from unittest.mock import patch, MagicMock

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domain": "backend",
    "company_size": ["startup"],
}

HIGH_MATCH_JOB = {
    "title": "Senior Python Engineer",
    "company": "Startup Co",
    "location": "Remote",
    "description": "FastAPI, PostgreSQL, Docker, fully remote senior backend role",
    "url": "https://startup.com/jobs/1",
}

LOW_MATCH_JOB = {
    "title": "Junior Marketing Analyst",
    "company": "Big Corp",
    "location": "New York",
    "description": "Excel, PowerPoint, marketing campaigns",
    "url": "https://bigcorp.com/jobs/2",
}


def _mock_score_response(score: float):
    msg = MagicMock()
    msg.content = str(score)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_score_job_returns_float():
    with patch("backend.agents.orchestrator.litellm.completion") as mock_completion:
        mock_completion.return_value = _mock_score_response(0.92)
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert score == 0.92


def test_score_job_handles_malformed_response():
    """If agent returns non-numeric text, return 0.0 safely."""
    msg = MagicMock()
    msg.content = "I cannot score this job."
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    with patch("backend.agents.orchestrator.litellm.completion") as mock_completion:
        mock_completion.return_value = resp
        from backend.agents.orchestrator import score_job
        score = score_job(LOW_MATCH_JOB, PREFERENCES)
    assert score == 0.0


def test_score_job_clamps_to_valid_range():
    """Scores outside 0.0–1.0 are clamped."""
    with patch("backend.agents.orchestrator.litellm.completion") as mock_completion:
        mock_completion.return_value = _mock_score_response(1.5)
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert score == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest backend/tests/test_orchestrator.py -v
```

Expected: 3 FAILED — `ImportError` or `AttributeError` because the code still uses `anthropic`.

- [ ] **Step 3: Update orchestrator.py**

Replace the entire content of `backend/agents/orchestrator.py`:

```python
import json
import logging
import litellm
from backend.config import settings

logger = logging.getLogger(__name__)

SCORE_SYSTEM = """You are a job relevance scorer. Given a job posting and user preferences, return ONLY a single decimal number between 0.0 and 1.0 representing how well the job matches the preferences.

Scoring weights:
- Job title match: 35%
- Remote/location match: 30%
- Experience level match: 20%
- Domain/tech stack match: 10%
- Company size match: 5%

Return ONLY the number. Example: 0.87"""


def score_job(job_data: dict, preferences: dict) -> float:
    """
    Score a single job against user preferences.
    Returns a float 0.0–1.0. Returns 0.0 on any error.
    """
    prompt = (
        f"User Preferences:\n{json.dumps(preferences, indent=2)}\n\n"
        f"Job Posting:\nTitle: {job_data.get('title', '')}\n"
        f"Company: {job_data.get('company', '')}\n"
        f"Location: {job_data.get('location', '')}\n"
        f"Description: {job_data.get('description', '')[:500]}\n\n"
        f"Score this job (0.0–1.0):"
    )
    try:
        response = litellm.completion(
            model=settings.ORCHESTRATOR_MODEL,
            max_tokens=16,
            messages=[
                {"role": "system", "content": SCORE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content.strip()
        score = float(raw)
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning("score_job failed: %s", e)
    return 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest backend/tests/test_orchestrator.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat(litellm): migrate orchestrator to litellm"
```

---

## Task 3: Migrate resume_tools.py (TDD)

**Files:**
- Modify: `backend/tools/resume_tools.py`
- Modify: `backend/tests/test_resume_tools.py`

- [ ] **Step 1: Update tests to expect LiteLLM response shape**

Replace the entire content of `backend/tests/test_resume_tools.py`:

```python
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_resume(tmp_path):
    """Write a plain-text .txt file as a stand-in for resume parsing."""
    f = tmp_path / "resume.txt"
    f.write_text("John Doe\nSenior Python Engineer\nExperience: FastAPI, PostgreSQL, Docker")
    return str(f)


def _mock_llm_response(text: str):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_tailor_resume_text_returns_string(sample_resume):
    with patch("backend.tools.resume_tools.litellm.completion") as mock_completion:
        mock_completion.return_value = _mock_llm_response("Tailored resume text for Python role")
        from backend.tools.resume_tools import tailor_resume
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
    with patch("backend.tools.resume_tools.litellm.completion") as mock_completion, \
         patch("backend.tools.resume_tools._write_pdf") as mock_pdf:
        mock_completion.return_value = _mock_llm_response("Tailored resume content")
        from backend.tools.resume_tools import tailor_resume
        result = tailor_resume(
            job_description="Senior Python Engineer at Acme",
            master_resume_path=sample_resume,
            output_format="pdf",
            output_path=output_path,
        )
    assert result == output_path
    mock_pdf.assert_called_once_with("Tailored resume content", output_path)


def test_tailor_resume_reads_resume_content(sample_resume):
    with patch("backend.tools.resume_tools.litellm.completion") as mock_completion:
        mock_completion.return_value = _mock_llm_response("output")
        from backend.tools.resume_tools import tailor_resume, _read_resume
        content = _read_resume(sample_resume)
        assert "Senior Python Engineer" in content
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest backend/tests/test_resume_tools.py -v
```

Expected: FAILED — patch target `backend.tools.resume_tools.litellm.completion` not found.

- [ ] **Step 3: Update resume_tools.py**

Replace the entire content of `backend/tools/resume_tools.py`:

```python
import litellm
from pathlib import Path
from typing import Literal
from fpdf import FPDF
from backend.config import settings


def _read_resume(filepath: str) -> str:
    """Read resume file content as plain text. Supports .txt, .pdf, .docx."""
    try:
        path = Path(filepath)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            from pdfminer.high_level import extract_text
            return extract_text(str(path))
        elif suffix == ".docx":
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        elif suffix == ".doc":
            raise ValueError("Legacy .doc format is not supported. Please convert to .docx or PDF.")
        else:
            return path.read_text(errors="ignore")
    except (FileNotFoundError, OSError) as e:
        raise RuntimeError(f"Could not read resume file: {filepath} — {e}")


def _write_pdf(text: str, output_path: str) -> None:
    """Write plain text as a simple PDF file."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.split("\n"):
        safe_line = line.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 6, safe_line)
    pdf.output(output_path)


TAILOR_SYSTEM = """You are a professional resume writer. Given a job description and a master resume,
rewrite the resume to highlight the most relevant experience and skills for this specific role.
Keep it truthful — do not invent experience. Return ONLY the tailored resume text, no commentary."""


def tailor_resume(
    job_description: str,
    master_resume_path: str,
    output_format: Literal["text", "pdf"],
    output_path: str = "",
    model: str | None = None,
) -> str:
    """
    Tailor the master resume for a specific job.

    output_format="text": returns tailored resume as a plain text string (output_path ignored)
    output_format="pdf": writes PDF to output_path and returns output_path
    model: optional model override (e.g. pass settings.OUTREACH_MODEL from the Outreach agent).
           Defaults to settings.APPLICATOR_MODEL if not provided.
    """
    resume_content = _read_resume(master_resume_path)
    response = litellm.completion(
        model=model or settings.APPLICATOR_MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": TAILOR_SYSTEM},
            {
                "role": "user",
                "content": f"Job Description:\n{job_description}\n\nMaster Resume:\n{resume_content}\n\nTailor the resume for this role.",
            },
        ],
    )
    tailored_text = response.choices[0].message.content

    if not tailored_text:
        raise RuntimeError("LLM returned no text content for resume tailoring")

    if output_format == "text":
        return tailored_text
    else:
        _write_pdf(tailored_text, output_path)
        return output_path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest backend/tests/test_resume_tools.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/resume_tools.py backend/tests/test_resume_tools.py
git commit -m "feat(litellm): migrate resume_tools to litellm"
```

---

## Task 4: Migrate applicator.py (TDD)

**Files:**
- Modify: `backend/agents/applicator.py`
- Modify: `backend/tests/test_applicator_agent.py`

- [ ] **Step 1: Update tests to expect LiteLLM response shape**

Replace the entire content of `backend/tests/test_applicator_agent.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest backend/tests/test_applicator_agent.py -v
```

Expected: FAILED — patch target `backend.agents.applicator.litellm.completion` not found.

- [ ] **Step 3: Update applicator.py**

Replace the entire content of `backend/agents/applicator.py`:

```python
import json
import logging
import litellm
from backend.config import settings
from backend.tools.playwright_tools import fetch_application_form
from backend.tools.resume_tools import tailor_resume

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an application form assistant. Given form fields and a tailored resume, produce a JSON object mapping each field name to its value from the resume. Use only information present in the resume. Return ONLY valid JSON with no markdown or commentary."""


def run_applicator(job_id: int, job_url: str, job_description: str, resume_path: str) -> dict:
    """
    Run the Applicator agent for a given job.

    Returns:
        {"status": "ready", "form_payload": {...}, "tailored_resume": "...", "form_fields": [...], "url": str}
        or {"status": "manual_required", "url": str}
    """
    # Step 1: Scrape the application form
    form_result = fetch_application_form(job_url)
    if "fields" not in form_result:
        logger.info(f"Form scraping returned manual_required for job {job_id}: {job_url}")
        return {"status": "manual_required", "url": job_url}

    # Step 2: Tailor resume as text for form field population
    try:
        tailored = tailor_resume(
            job_description=job_description,
            master_resume_path=resume_path,
            output_format="text",
            model=settings.APPLICATOR_MODEL,
        )
    except Exception as e:
        logger.warning(f"Resume tailoring failed for job {job_id}: {e}")
        return {"status": "manual_required", "url": job_url}

    # Step 3: Use LLM to map resume data to form fields
    try:
        response = litellm.completion(
            model=settings.APPLICATOR_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Form fields:\n{json.dumps(form_result.get('fields', []), indent=2)}\n\n"
                        f"Tailored Resume:\n{tailored}\n\n"
                        "Return a JSON object mapping each field name to its value."
                    ),
                },
            ],
        )
    except Exception as e:
        logger.warning(f"LLM field mapping failed for job {job_id}: {e}")
        return {"status": "manual_required", "url": job_url}

    payload = {}
    try:
        payload = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"LLM returned non-JSON payload for job {job_id}: {response.choices[0].message.content[:100]}")
        payload = {}

    return {
        "status": "ready",
        "form_payload": payload,
        "tailored_resume": tailored,
        "form_fields": form_result.get("fields", []),
        "url": job_url,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest backend/tests/test_applicator_agent.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/applicator.py backend/tests/test_applicator_agent.py
git commit -m "feat(litellm): migrate applicator to litellm"
```

---

## Task 5: Migrate outreach.py (TDD)

**Files:**
- Modify: `backend/agents/outreach.py`
- Modify: `backend/tests/test_outreach_agent.py`

Note: existing `test_outreach_agent.py` mocks `generate_cover_letter` wholesale — it does not test the LLM call inside it. This task adds one direct test for `generate_cover_letter` to ensure the litellm migration is covered.

- [ ] **Step 1: Add generate_cover_letter test to test_outreach_agent.py**

Append to `backend/tests/test_outreach_agent.py` (keep existing tests, add at the bottom):

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec backend pytest backend/tests/test_outreach_agent.py::test_generate_cover_letter_returns_string -v
```

Expected: FAILED — `litellm` not importable in `outreach.py` yet.

- [ ] **Step 3: Update outreach.py**

Replace the entire content of `backend/agents/outreach.py`:

```python
import os
import litellm
from backend.config import settings
from backend.tools.hr_finder import find_hr_contact
from backend.tools.resume_tools import tailor_resume

COVER_LETTER_SYSTEM = """You are a professional cover letter writer. Write a concise, personalized cover letter for a job application.
Use the applicant's resume and the job description. Address the hiring manager by name if provided.
Tone: professional, enthusiastic, specific. Length: 3-4 short paragraphs. Return ONLY the cover letter text."""


def generate_cover_letter(
    job_description: str,
    resume_path: str,
    company: str,
    hr_name: str = "",
) -> str:
    from backend.tools.resume_tools import _read_resume

    resume_content = _read_resume(resume_path)
    greeting = f"Dear {hr_name}," if hr_name else "Dear Hiring Manager,"
    response = litellm.completion(
        model=settings.OUTREACH_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": COVER_LETTER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Company: {company}\n\n"
                    f"Job Description:\n{job_description}\n\n"
                    f"Resume:\n{resume_content}\n\n"
                    f"Salutation: {greeting}\n\n"
                    "Write the cover letter."
                ),
            },
        ],
    )
    return response.choices[0].message.content or ""


def run_outreach(
    job_id: int,
    company: str,
    job_description: str,
    resume_path: str,
    output_dir: str,
) -> dict:
    """
    Run the Outreach agent.
    Returns a dict with hr_name, hr_email, hr_confidence, cover_letter, resume_version_path.
    """
    hr = find_hr_contact(company=company, job_title=job_description[:80])

    cover_letter = generate_cover_letter(
        job_description=job_description,
        resume_path=resume_path,
        company=company,
        hr_name=hr.get("hr_name", ""),
    )

    tailored_path = tailor_resume(
        job_description=job_description,
        master_resume_path=resume_path,
        output_format="pdf",
        output_path=os.path.join(output_dir, f"tailored_outreach_{job_id}.pdf"),
    )

    return {
        "hr_name": hr.get("hr_name", ""),
        "hr_email": hr.get("hr_email", ""),
        "hr_confidence": hr.get("hr_confidence", "unknown"),
        "cover_letter": cover_letter,
        "resume_version_path": tailored_path,
    }
```

- [ ] **Step 4: Run all outreach tests to verify they pass**

```bash
docker compose exec backend pytest backend/tests/test_outreach_agent.py -v
```

Expected: 3 PASSED (2 existing + 1 new).

- [ ] **Step 5: Commit**

```bash
git add backend/agents/outreach.py backend/tests/test_outreach_agent.py
git commit -m "feat(litellm): migrate outreach to litellm, add generate_cover_letter test"
```

---

## Task 6: Migrate job_scout.py (TDD — tool use loop rewrite)

**Files:**
- Modify: `backend/agents/job_scout.py`
- Modify: `backend/tests/test_job_scout_agent.py`

This is the most significant change. The Anthropic tool use loop (stop_reason, tool_result content blocks) is replaced with OpenAI function calling format (finish_reason, tool_calls list, role: "tool" messages).

- [ ] **Step 1: Rewrite test helpers and all 3 tests**

Replace the entire content of `backend/tests/test_job_scout_agent.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domain": "backend",
    "company_size": ["startup"],
}

MOCK_SERP_RESULTS = [
    {
        "title": "Senior Python Engineer",
        "company": "Acme",
        "location": "Remote",
        "description": "Build APIs",
        "url": "https://acme.com/jobs/1",
    }
]


def _tool_use_response(tool_id, tool_input):
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = "search_jobs"
    tc.function.arguments = json.dumps(tool_input)
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = None
    choice = MagicMock()
    choice.finish_reason = "tool_calls"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _end_turn_response(scored_jobs):
    msg = MagicMock()
    msg.content = json.dumps(scored_jobs)
    msg.tool_calls = None
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_run_job_scout_returns_scored_jobs():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.litellm.completion") as mock_completion, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_completion.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert len(result) == 1
    assert result[0]["match_score"] == 0.9


def test_run_job_scout_filters_below_threshold():
    low_scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.3}]
    with patch("backend.agents.job_scout.litellm.completion") as mock_completion, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "anthropic/claude-haiku-4-5"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        mock_completion.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(low_scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []


def test_run_job_scout_handles_malformed_response():
    """Agent returns non-JSON text — should return empty list gracefully."""
    msg = MagicMock()
    msg.content = "Sorry, I could not find any jobs."
    msg.tool_calls = None
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    with patch("backend.agents.job_scout.litellm.completion") as mock_completion, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_completion.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer"}),
            resp,
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend pytest backend/tests/test_job_scout_agent.py -v
```

Expected: 3 FAILED — patch target `backend.agents.job_scout.litellm.completion` not found.

- [ ] **Step 3: Rewrite job_scout.py**

Replace the entire content of `backend/agents/job_scout.py`:

```python
import json
import litellm
from backend.config import settings
from backend.tools.serp import search_jobs

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Search for job listings using SerpAPI Google Jobs. Call once per job title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Job title + keywords, e.g. 'Senior Python Engineer remote'"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location filter, e.g. 'Remote' or 'New York, NY'"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to fetch (max 20)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a job search assistant.
1. Use search_jobs to find jobs for each job title in the user's preferences.
2. Score each result 0.0–1.0 based on how well it matches the criteria.
3. Return ONLY a valid JSON array. No other text.

Scoring weights: title match (high), remote/location match (high), experience level (medium), domain (medium), company size (low).

Output format:
[{"title": "...", "company": "...", "location": "...", "description": "...", "url": "...", "match_score": 0.85}]"""


def _execute_tool(name: str, tool_input: dict) -> str:
    if name == "search_jobs":
        results = search_jobs(
            query=tool_input["query"],
            location=tool_input.get("location", ""),
            num_results=tool_input.get("num_results", 10),
        )
        return json.dumps(results)
    raise ValueError(f"Unknown tool: {name}")


def run_job_scout(preferences: dict) -> list[dict]:
    """Run the JobScout agentic loop. Returns jobs scoring >= JOB_MATCH_THRESHOLD."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Find and score jobs for these preferences:\n{json.dumps(preferences, indent=2)}\n\nSearch each job title. Return a JSON array of scored jobs.",
        },
    ]

    while True:
        response = litellm.completion(
            model=settings.SCOUT_MODEL,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            msg = choice.message
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in (msg.tool_calls or [])
                ],
            })
            for tc in (msg.tool_calls or []):
                result = _execute_tool(tc.function.name, json.loads(tc.function.arguments))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result,
                })
            continue

        # end_turn / stop — parse final JSON output
        content = choice.message.content
        if content:
            try:
                jobs = json.loads(content)
                return [j for j in jobs if j.get("match_score", 0) >= settings.JOB_MATCH_THRESHOLD]
            except (json.JSONDecodeError, TypeError):
                return []
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend pytest backend/tests/test_job_scout_agent.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/job_scout.py backend/tests/test_job_scout_agent.py
git commit -m "feat(litellm): migrate job_scout tool use loop to litellm/OpenAI format"
```

---

## Task 7: Full Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

```bash
docker compose exec backend pytest -v
```

Expected: all tests pass (74+ tests). If any fail, investigate — most likely cause is a stale import cache from `anthropic` still being importable; check that `requirements.txt` change took effect inside the container.

- [ ] **Step 2: If import errors occur, rebuild the container**

```bash
docker compose build backend
docker compose exec backend pytest -v
```

- [ ] **Step 3: Run frontend tests to verify nothing was affected**

```bash
docker compose exec frontend npm run test:run
```

Expected: all frontend tests pass (18 tests).

- [ ] **Step 4: Final commit (if any fixes were needed in Step 2)**

```bash
git add -p  # stage only relevant changes
git commit -m "fix(litellm): resolve post-migration import issues"
```

If no fixes were needed, skip this step.
