from pathlib import Path
from typing import Literal
from fpdf import FPDF
from backend import llm
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
    response = llm.complete(
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
    tailored_text = response.content

    if not tailored_text:
        raise RuntimeError("LLM returned no text content for resume tailoring")

    if output_format == "text":
        return tailored_text
    else:
        _write_pdf(tailored_text, output_path)
        return output_path
