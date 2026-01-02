"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from . import resume_storage
from . import profile_storage
from .packs import build_profile_pack
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .resume import run_resume_council

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


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
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


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
    uvicorn.run(app, host="0.0.0.0", port=8001)
