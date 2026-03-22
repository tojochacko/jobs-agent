from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File
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


@router.post("/resume", response_model=ResumeResponse)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / file.filename
    with open(filepath, "wb") as f:
        f.write(file.file.read())
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
