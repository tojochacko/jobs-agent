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
