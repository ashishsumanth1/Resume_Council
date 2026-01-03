"""FastAPI backend for Resume Council."""

import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import resume_storage
from . import profile_storage
from .packs import build_profile_pack
from .resume import run_resume_council

app = FastAPI(title="Resume Council API")


def _cors_origins() -> list[str]:
    raw = (os.getenv("CORS_ORIGINS") or "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"]

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResumeRequest(BaseModel):
    """Request body for resume tailoring."""
    job_description: str
    master_profile: str | None = ""
    profile_id: str | None = None
    company_details: str | None = ""
    use_peer_ranking: bool | None = None


class CreateProfileRequest(BaseModel):
    name: str | None = "Master Profile"
    raw_text: str


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Resume Council API"}


@app.post("/api/resume/run")
async def run_resume(request: ResumeRequest):
    """Run resume-tailoring council flow and persist results."""
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="job_description is required")

    master_profile_text = (request.master_profile or "").strip()
    if request.profile_id:
        prof = profile_storage.get_profile(request.profile_id)
        if prof is None:
            raise HTTPException(status_code=404, detail="profile_id not found")
        # For resume generation quality, prefer the full raw text as truth source.
        master_profile_text = (prof.get("raw_text") or prof.get("compact_text") or "").strip()

    if not master_profile_text:
        raise HTTPException(status_code=400, detail="master_profile or profile_id is required")

    stage1_results, stage2_results, stage3_result, metadata, docx_info = await run_resume_council(
        master_profile_text,
        request.job_description,
        request.company_details or "",
        use_peer_ranking=request.use_peer_ranking,
    )

    payload = {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata,
        "docx": docx_info,
    }

    resume_id = str(uuid.uuid4())
    record = resume_storage.create_resume_run(
        resume_id=resume_id,
        job_description=request.job_description,
        master_profile=master_profile_text,
        company_details=request.company_details or "",
        use_peer_ranking=request.use_peer_ranking,
        result_payload=payload,
    )

    return record


@app.get("/api/profiles")
async def list_profiles():
    """List saved master profiles (metadata only)."""
    return profile_storage.list_profiles()


@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    prof = profile_storage.get_profile(profile_id)
    if prof is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return prof


@app.post("/api/profiles")
async def create_profile(request: CreateProfileRequest):
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text is required")
    profile_id = str(uuid.uuid4())
    compact = build_profile_pack(request.raw_text)
    prof = profile_storage.create_profile(profile_id, request.name or "Master Profile", request.raw_text, compact)
    return {"id": prof["id"], "name": prof["name"], "created_at": prof["created_at"]}


@app.get("/api/resumes")
async def list_resumes():
    """List resume runs (metadata only)."""
    return resume_storage.list_resume_runs()


@app.get("/api/resumes/{resume_id}")
async def get_resume(resume_id: str):
    """Get a saved resume run with inputs + results."""
    record = resume_storage.get_resume_run(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume run not found")
    return record


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
