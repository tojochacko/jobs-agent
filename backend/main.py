from fastapi import FastAPI
from backend.database import get_db
from backend.routers import preferences, resume, jobs

app = FastAPI(title="JobApplierAgent")
app.include_router(preferences.router)
app.include_router(resume.router)
app.include_router(jobs.router)

@app.get("/health")
def health():
    return {"status": "ok"}
