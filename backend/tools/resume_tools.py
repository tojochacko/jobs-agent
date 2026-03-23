import anthropic
from pathlib import Path
from typing import Literal
from fpdf import FPDF
from backend.config import settings


def _read_resume(filepath: str) -> str:
    """Read resume file content as plain text. Supports .txt, .pdf, .docx."""
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pdfminer.high_level import extract_text
        return extract_text(str(path))
    elif suffix in (".docx", ".doc"):
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return path.read_text(errors="ignore")


def _write_pdf(text: str, output_path: str) -> None:
    """Write plain text as a simple PDF file."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.split("\n"):
        pdf.multi_cell(0, 6, line)
    pdf.output(output_path)


TAILOR_SYSTEM = """You are a professional resume writer. Given a job description and a master resume,
rewrite the resume to highlight the most relevant experience and skills for this specific role.
Keep it truthful — do not invent experience. Return ONLY the tailored resume text, no commentary."""


def tailor_resume(
    job_description: str,
    master_resume_path: str,
    output_format: Literal["text", "pdf"],
    output_path: str,
) -> str:
    """
    Tailor the master resume for a specific job.

    output_format="text": returns tailored resume as a plain text string (output_path ignored)
    output_format="pdf": writes PDF to output_path and returns output_path
    """
    resume_content = _read_resume(master_resume_path)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.APPLICATOR_MODEL,
        max_tokens=2048,
        system=TAILOR_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Job Description:\n{job_description}\n\nMaster Resume:\n{resume_content}\n\nTailor the resume for this role.",
            }
        ],
    )
    tailored_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            tailored_text = block.text
            break

    if output_format == "text":
        return tailored_text
    else:
        _write_pdf(tailored_text, output_path)
        return output_path
