import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import preferences, resume, jobs, applications, auth, outreach, webhook
from backend.scheduler import run_poll

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    threading.Thread(target=run_poll, daemon=True).start()
    yield


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
app.include_router(applications.router)
app.include_router(auth.router)
app.include_router(outreach.router)
app.include_router(webhook.router)


@app.get("/health")
def health():
    return {"status": "ok"}
