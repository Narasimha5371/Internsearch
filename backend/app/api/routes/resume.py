from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limiter import enforce_rate_limit
from app.api.deps.auth import CurrentUser, get_current_user
from app.db.deps import get_db
from app.db.models import ParsedResume
from app.schemas.candidate import CandidateProfile
from app.services.resume_parser import extract_text_from_pdf_bytes, parse_candidate_profile
from app.services.users import get_or_create_user

router = APIRouter(prefix="/resume", tags=["resume"])
ALLOWED_PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


@router.post("/upload", response_model=CandidateProfile, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    enforce_rate_limit(
        key=f"resume-upload:{current_user.user_id}",
        max_requests=settings.resume_upload_rate_limit_count,
        window_seconds=settings.resume_upload_rate_limit_window_seconds,
    )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    if file.content_type and file.content_type.lower() not in ALLOWED_PDF_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file content type.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    max_bytes = settings.max_resume_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Resume exceeds {settings.max_resume_size_mb}MB limit.",
        )

    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")

    storage_root = Path(settings.resume_storage_dir)
    storage_root.mkdir(parents=True, exist_ok=True)

    user_dir = storage_root / current_user.user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.pdf"
    stored_path = user_dir / safe_name
    stored_path.write_bytes(file_bytes)

    raw_text = await run_in_threadpool(extract_text_from_pdf_bytes, file_bytes)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No extractable text found in PDF.")

    try:
        candidate_profile = await parse_candidate_profile(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    user = get_or_create_user(db, current_user.user_id, current_user.email or candidate_profile.email)

    record = ParsedResume(
        user_id=user.id,
        source_filename=file.filename,
        file_path=str(stored_path),
        raw_text=raw_text if settings.store_resume_raw_text else None,
        parsed_json=candidate_profile.model_dump(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return candidate_profile


@router.get("/latest", response_model=CandidateProfile)
def get_latest_resume(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email)
    resume = (
        db.query(ParsedResume)
        .filter(ParsedResume.user_id == user.id)
        .order_by(ParsedResume.created_at.desc())
        .first()
    )
    if not resume or not resume.parsed_json:
        raise HTTPException(status_code=404, detail="No parsed resume found.")

    return CandidateProfile.model_validate(resume.parsed_json)


@router.patch("/latest", response_model=CandidateProfile)
def update_latest_resume(
    payload: CandidateProfile,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    user = get_or_create_user(db, current_user.user_id, current_user.email or payload.email)
    resume = (
        db.query(ParsedResume)
        .filter(ParsedResume.user_id == user.id)
        .order_by(ParsedResume.created_at.desc())
        .first()
    )

    if resume:
        resume.parsed_json = payload.model_dump()
        db.add(resume)
    else:
        db.add(
            ParsedResume(
                user_id=user.id,
                source_filename="manual",
                file_path=None,
                raw_text=None,
                parsed_json=payload.model_dump(),
            )
        )

    db.commit()
    return payload
