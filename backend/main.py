import logging
import os
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.chat_service import ChatService
from services.claude_service import ClaudeService, ClaudeServiceError
from services.compare_service import compare_resumes
from services.interview_service import InterviewService
from services.job_compare_service import JobCompareService
from services import ocr_service
from services.ocr_service import (
    OCR_SUCCESS_MESSAGE,
    get_resume_text,
    probe_ocr_runtime,
)
from services.resume_parser import ResumeParseError
from services.rewrite_service import RewriteService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Parsed resume text keyed by upload id. Temp files are deleted after parsing;
# Vercel serverless cannot persist project-local upload directories.
_RESUME_TEXT_CACHE: dict[str, str] = {}

claude_service = ClaudeService()
rewrite_service = RewriteService()
chat_service = ChatService()
interview_service = InterviewService()
job_compare_service = JobCompareService(claude_service)


class AnalyzeRequest(BaseModel):
    filename: str
    job_description: str = Field(default="")


class RewriteRequest(BaseModel):
    filename: str
    job_description: str = Field(default="")
    section: str = Field(default="")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    filename: str
    job_description: str = Field(default="")
    history: list[ChatMessage] = Field(default_factory=list)
    message: str
    analysis: dict = Field(default_factory=dict)
    rewrite: dict = Field(default_factory=dict)


class CompareRequest(BaseModel):
    filename: str
    rewrite: dict = Field(default_factory=dict)


class InterviewStartRequest(BaseModel):
    filename: str
    job_description: str = Field(default="")


class InterviewHistoryItem(BaseModel):
    role: str = Field(default="")
    content: str = Field(default="")
    question: str = Field(default="")
    answer: str = Field(default="")
    score: int | None = None


class InterviewAnswerRequest(BaseModel):
    history: list[InterviewHistoryItem] = Field(default_factory=list)
    question: str
    answer: str = Field(default="")


class InterviewSummaryRequest(BaseModel):
    filename: str
    job_description: str = Field(default="")
    turns: list[dict] = Field(default_factory=list)


class JobCompareItem(BaseModel):
    company: str = Field(default="")
    job_description: str = Field(default="")


class CompareJobsRequest(BaseModel):
    filename: str
    jobs: list[JobCompareItem] = Field(default_factory=list)


def _resolve_resume_text(filename: str) -> tuple[str, str]:
    safe_name = Path(filename).name
    resume_text = _RESUME_TEXT_CACHE.get(safe_name)

    if not resume_text:
        raise HTTPException(status_code=404, detail="Uploaded file not found.")

    return safe_name, resume_text


def _store_upload_temporarily(content: bytes, extension: str) -> str:
    """Write bytes to the OS temp dir and return the path. Caller must delete."""
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension,
        dir=tempfile.gettempdir(),
        prefix="resume_",
    ) as tmp:
        tmp.write(content)
        return tmp.name


@app.get("/")
def home():
    return {
        "message": "AI Resume Assistant Backend Running!",
        "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "local")[:12],
        "ocr_service": "services.ocr_service",
    }


@app.get("/ocr-status")
def ocr_status():
    """Deploy proof: whether this runtime has OCR code + paddleocr available."""
    runtime = probe_ocr_runtime()
    return {
        "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "local"),
        "ocr_service_file": "services/ocr_service.py",
        "get_resume_text": callable(get_resume_text),
        **runtime,
    }


@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume, extract/OCR text in a temp file, then discard the file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF, DOCX, PNG, JPG, and JPEG are allowed.",
        )

    content = await file.read()
    size = len(content)

    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File exceeds maximum size of 10 MB.",
        )

    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    temp_path = None
    used_ocr = False

    try:
        temp_path = _store_upload_temporarily(content, extension)
        logging.info(
            "Upload received name=%s extension=%s size=%s temp=%s",
            original_name,
            extension,
            size,
            temp_path,
        )
        resume_text, used_ocr = get_resume_text(temp_path)
        logging.info(
            "Upload text ready name=%s ocr_used=%s chars=%s",
            original_name,
            used_ocr,
            len(resume_text or ""),
        )
    except ResumeParseError as exc:
        logging.error("Upload text extraction failed:\n%s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Unexpected upload failure")
        import traceback as _tb

        raise HTTPException(
            status_code=500,
            detail=(
                f"Upload processing failed: {type(exc).__name__}: {exc}\n\n"
                f"{_tb.format_exc()}"
            ),
        ) from exc
    finally:
        if temp_path:
            with suppress(OSError):
                os.unlink(temp_path)

    _RESUME_TEXT_CACHE[stored_name] = resume_text

    response = {
        "filename": stored_name,
        "original_filename": original_name,
        "size": size,
        "status": "success",
        "ocr_used": used_ocr,
        "ocr_attempted": used_ocr,
        "ocr_backend": ocr_service._ocr_backend,
        "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "local")[:12],
    }
    if used_ocr:
        response["message"] = OCR_SUCCESS_MESSAGE

    return response


@app.post("/analyze")
async def analyze_resume(payload: AnalyzeRequest):
    """Analyze an uploaded resume with Claude using extracted text + JD."""
    safe_name, resume_text = _resolve_resume_text(payload.filename)

    try:
        analysis = claude_service.analyze_resume(
            resume_text=resume_text,
            job_description=payload.job_description,
        )
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "filename": safe_name,
        "analysis": analysis,
    }


@app.post("/rewrite")
async def rewrite_resume(payload: RewriteRequest):
    """Rewrite an uploaded resume with Claude for the target job description."""
    if not payload.job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description is required for rewrite.",
        )

    _, resume_text = _resolve_resume_text(payload.filename)

    try:
        rewrite = rewrite_service.rewrite_resume(
            resume_text=resume_text,
            job_description=payload.job_description,
            focus_section=payload.section or None,
        )
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return rewrite


@app.post("/chat")
async def career_coach_chat(payload: ChatRequest):
    """Multi-turn career coach chat with resume/analysis/rewrite memory."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Chat message is required.")

    _, resume_text = _resolve_resume_text(payload.filename)

    try:
        reply = chat_service.chat(
            resume_text=resume_text,
            job_description=payload.job_description,
            message=payload.message,
            history=[item.model_dump() for item in payload.history],
            analysis=payload.analysis or None,
            rewrite=payload.rewrite or None,
        )
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "reply": reply,
    }


@app.post("/compare")
async def compare_resume_versions(payload: CompareRequest):
    """Compare original parsed resume text with an existing rewrite result."""
    if not payload.rewrite:
        raise HTTPException(
            status_code=400,
            detail="Rewrite result is required for compare.",
        )

    _, resume_text = _resolve_resume_text(payload.filename)

    return compare_resumes(resume_text, payload.rewrite)


@app.post("/interview/start")
async def interview_start(payload: InterviewStartRequest):
    """Generate 8–10 interview questions from resume + job description."""
    safe_name, resume_text = _resolve_resume_text(payload.filename)

    try:
        result = interview_service.start_interview(
            resume_text=resume_text,
            job_description=payload.job_description,
        )
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "filename": safe_name,
        **result,
    }


@app.post("/interview/answer")
async def interview_answer(payload: InterviewAnswerRequest):
    """Evaluate one interview answer and return coaching + follow-up."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Interview question is required.")

    history = []
    for item in payload.history:
        entry = item.model_dump()
        # Keep compact history for the evaluator prompt.
        cleaned = {
            key: value
            for key, value in entry.items()
            if value not in ("", None, [])
        }
        if cleaned:
            history.append(cleaned)

    try:
        result = interview_service.evaluate_answer(
            question=payload.question,
            answer=payload.answer,
            history=history,
        )
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return result


@app.post("/interview/summary")
async def interview_summary(payload: InterviewSummaryRequest):
    """Generate the final interview report after all questions."""
    if not payload.turns:
        raise HTTPException(
            status_code=400,
            detail="Interview turns are required for summary.",
        )

    safe_name, resume_text = _resolve_resume_text(payload.filename)

    try:
        result = interview_service.summarize_interview(
            resume_text=resume_text,
            job_description=payload.job_description,
            turns=payload.turns,
        )
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "filename": safe_name,
        **result,
    }


@app.post("/compare-jobs")
async def compare_jobs(payload: CompareJobsRequest):
    """Compare one resume against up to five job descriptions via ATS analysis."""
    if not payload.jobs:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one job description to compare.",
        )

    if len(payload.jobs) > JobCompareService.MAX_JOBS:
        raise HTTPException(
            status_code=400,
            detail=f"Compare up to {JobCompareService.MAX_JOBS} jobs at a time.",
        )

    safe_name, resume_text = _resolve_resume_text(payload.filename)

    try:
        result = job_compare_service.compare_jobs(
            resume_text=resume_text,
            jobs=[job.model_dump() for job in payload.jobs],
        )
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "filename": safe_name,
        **result,
    }


