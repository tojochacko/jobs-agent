import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Preference

router = APIRouter()


class PreferenceRequest(BaseModel):
    job_titles: list[str]
    location: str = ""
    remote_hybrid: str = "any"
    experience_level: str = ""
    domain: str = ""
    company_size: list[str] = []
    industry: list[str] = []


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_titles: list[str]
    location: str
    remote_hybrid: str
    experience_level: str
    domain: str
    company_size: list[str]
    industry: list[str]


def _deserialize(pref: Preference) -> Preference:
    pref.job_titles = json.loads(pref.job_titles)
    pref.company_size = json.loads(pref.company_size or "[]")
    pref.industry = json.loads(pref.industry or "[]")
    return pref


@router.get("/preferences", response_model=PreferenceResponse | None)
def get_preferences(db: Session = Depends(get_db)):
    pref = db.query(Preference).first()
    return _deserialize(pref) if pref else None


@router.post("/preferences", response_model=PreferenceResponse)
def save_preferences(payload: PreferenceRequest, db: Session = Depends(get_db)):
    pref = db.query(Preference).first()
    if pref:
        db.delete(pref)
        db.commit()
    pref = Preference(
        job_titles=json.dumps(payload.job_titles),
        location=payload.location,
        remote_hybrid=payload.remote_hybrid,
        experience_level=payload.experience_level,
        domain=payload.domain,
        company_size=json.dumps(payload.company_size),
        industry=json.dumps(payload.industry),
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return _deserialize(pref)
