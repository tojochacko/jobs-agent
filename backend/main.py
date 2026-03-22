import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import preferences, resume, jobs
from backend.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    global _scheduler
    _scheduler = start_scheduler(poll_interval_hrs=6)
    yield
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()


app = FastAPI(title="JobApplierAgent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(preferences.router)
app.include_router(resume.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}
