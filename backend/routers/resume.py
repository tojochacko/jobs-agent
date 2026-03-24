from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models import Resume

router = APIRouter()


class ResumeResponse(BaseModel):
    id: int
    filename: str
    filepath: str

    model_config = ConfigDict(from_attributes=True)


MAX_RESUME_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/resume", response_model=ResumeResponse)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    content = file.file.read()
    if len(content) > MAX_RESUME_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds the 50 MB size limit.")
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / file.filename
    with open(filepath, "wb") as f:
        f.write(content)
    existing = db.query(Resume).first()
    if existing:
        db.delete(existing)
        db.commit()
    resume = Resume(filename=file.filename, filepath=str(filepath))
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/resume", response_model=ResumeResponse | None)
def get_resume(db: Session = Depends(get_db)):
    return db.query(Resume).first()
