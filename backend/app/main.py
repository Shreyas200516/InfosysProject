"""SupportPilot API. Run:  uvicorn app.main:app --reload --port 8000   (from the backend/ folder)"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.repo import get_repo
from .routers import admin, auth, knowledge, ops, tickets
from .services.classifier import get_classifier
from .services.knowledge import get_knowledge
from .services.triage import get_triage


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_repo(), get_classifier(), get_triage(), get_knowledge()  # warm models at startup
    yield


app = FastAPI(title=settings.app_name, version="0.3.0", lifespan=lifespan,
              description="AI-powered IT support: classification, priority/severity, RAG resolution, multi-agent workflow, Jira + email.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, admin.router, tickets.router, knowledge.router, ops.router):
    app.include_router(r)


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/v1/health"}
