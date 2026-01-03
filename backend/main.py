"""FastAPI backend for Resume Council."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pydantic import BaseModel
import pyotp

from . import resume_storage
from . import profile_storage
from .packs import build_profile_pack
from .resume import run_resume_council

def _auth_config() -> dict[str, str]:
    return {
        "email": (os.getenv("APP_AUTH_EMAIL") or "").strip(),
        "password": (os.getenv("APP_AUTH_PASSWORD") or "").strip(),
        "totp_secret": (os.getenv("APP_AUTH_TOTP_SECRET") or "").strip(),
        "token_secret": (os.getenv("APP_AUTH_TOKEN_SECRET") or "").strip(),
    }


def _get_token_secret(config: dict[str, str]) -> str:
    return config["token_secret"] or config["password"]


def _encode_token(email: str, secret: str, ttl_seconds: int = 60 * 60 * 12) -> str:
    payload = {"email": email, "exp": int(time.time()) + ttl_seconds}
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def _decode_token(token: str, secret: str) -> dict[str, object] | None:
    if "." not in token:
        return None
    payload_b64, sig_b64 = token.split(".", 1)
    expected_sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    try:
        provided_sig = base64.urlsafe_b64decode(sig_b64 + "==")
    except Exception:
        return None
    if not secrets.compare_digest(expected_sig, provided_sig):
        return None
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None
    return payload


def _require_auth(request: Request) -> None:
    config = _auth_config()
    if not config["email"] or not config["password"] or not config["totp_secret"]:
        raise HTTPException(status_code=500, detail="Auth not configured")
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    token = auth_header.replace("Bearer ", "", 1).strip()
    secret = _get_token_secret(config)
    if not secret:
        raise HTTPException(status_code=500, detail="Auth not configured")
    payload = _decode_token(token, secret)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


app = FastAPI(title="Resume Council API")
router = APIRouter(dependencies=[Depends(_require_auth)])


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


class LoginRequest(BaseModel):
    email: str
    password: str
    totp: str


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    config = _auth_config()
    if not config["email"] or not config["password"] or not config["totp_secret"]:
        raise HTTPException(status_code=500, detail="Auth not configured")

    email_match = secrets.compare_digest(request.email.strip().lower(), config["email"].lower())
    password_match = secrets.compare_digest(request.password, config["password"])
    if not (email_match and password_match):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    totp = pyotp.TOTP(config["totp_secret"])
    if not totp.verify(request.totp, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    token_secret = _get_token_secret(config)
    token = _encode_token(config["email"], token_secret)
    return {"token": token, "expires_in": 60 * 60 * 12}


@router.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Resume Council API"}


@router.post("/api/resume/run")
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


@router.get("/api/profiles")
async def list_profiles():
    """List saved master profiles (metadata only)."""
    return profile_storage.list_profiles()


@router.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    prof = profile_storage.get_profile(profile_id)
    if prof is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return prof


@router.post("/api/profiles")
async def create_profile(request: CreateProfileRequest):
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text is required")
    profile_id = str(uuid.uuid4())
    compact = build_profile_pack(request.raw_text)
    prof = profile_storage.create_profile(profile_id, request.name or "Master Profile", request.raw_text, compact)
    return {"id": prof["id"], "name": prof["name"], "created_at": prof["created_at"]}


@router.get("/api/resumes")
async def list_resumes():
    """List resume runs (metadata only)."""
    return resume_storage.list_resume_runs()


@router.get("/api/resumes/{resume_id}")
async def get_resume(resume_id: str):
    """Get a saved resume run with inputs + results."""
    record = resume_storage.get_resume_run(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume run not found")
    return record


app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
