"""Session creation, PDF upload with Smart Pre-Filtering, and paper removal endpoints."""

import json
import uuid
from typing import List, Literal
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import (
    DEFAULT_FULL_MODE_RERUNS,
    MAX_FILE_SIZE_MB,
    MAX_PAPERS_FULL,
    MAX_PAPERS_QUICK,
    PROMO_PRICE_INR,
    REGULAR_PRICE_INR,
    UPLOAD_DIR,
)
from backend.database import get_db
from backend.models import PaperModel, SessionModel
from backend.services.pdf_service import process_and_trim_pdf

router = APIRouter(prefix="/api", tags=["session"])


class CreateSessionRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=300)
    mode: Literal["quick", "full"] = Field(default="full")


@router.post("/session")
def create_session(req: CreateSessionRequest, db: Session = Depends(get_db)):
    """Creates a new research session with selected mode (quick=free 3 papers, full=paid 20 papers)."""
    session_id = str(uuid.uuid4())
    reruns = DEFAULT_FULL_MODE_RERUNS if req.mode == "full" else 0
    max_papers = MAX_PAPERS_FULL if req.mode == "full" else MAX_PAPERS_QUICK

    new_session = SessionModel(
        id=session_id,
        topic=req.topic.strip(),
        mode=req.mode,
        status="pending",
        reruns_remaining=reruns,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "session_id": session_id,
        "topic": new_session.topic,
        "mode": new_session.mode,
        "max_papers": max_papers,
        "reruns_remaining": new_session.reruns_remaining,
        "pricing": {
            "promo_inr": PROMO_PRICE_INR if req.mode == "full" else 0,
            "regular_inr": REGULAR_PRICE_INR if req.mode == "full" else 0,
        },
    }


@router.post("/{session_id}/upload")
async def upload_papers(
    session_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Uploads PDFs to a session, enforces paper cap (3 for Quick, 20 for Full),
    runs the <5ms Academic Gate, trims trailing Reference/Bibliography pages,
    and indexes page texts for Lock 4 quote verification.
    """
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    max_allowed = MAX_PAPERS_FULL if session_obj.mode == "full" else MAX_PAPERS_QUICK
    existing_count = len(session_obj.papers)

    if existing_count + len(files) > max_allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Maximum {max_allowed} papers allowed in '{session_obj.mode.upper()}' mode. "
                f"Currently uploaded: {existing_count}, attempted to add: {len(files)}."
            ),
        )

    session_upload_dir = UPLOAD_DIR / session_id
    session_upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded_records = []
    next_order = existing_count + 1

    for upload in files:
        fname = upload.filename or f"paper_{next_order}.pdf"
        if not fname.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"'{fname}' is not a PDF file. Only PDF files are accepted.")

        content = await upload.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"'{fname}' exceeds maximum file size of {MAX_FILE_SIZE_MB} MB.",
            )

        raw_path = session_upload_dir / f"raw_{next_order}_{fname}"
        trimmed_path = session_upload_dir / f"trimmed_{next_order}_{fname}"
        raw_path.write_bytes(content)

        try:
            pdf_info = process_and_trim_pdf(raw_path, trimmed_path)
        except ValueError as exc:
            raw_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"{fname}: {exc}") from exc

        paper_row = PaperModel(
            session_id=session_id,
            filename=fname,
            trimmed_pdf_path=str(trimmed_path),
            pages_kept=pdf_info["pages_kept"],
            pages_trimmed=pdf_info["pages_trimmed"],
            page_texts_json=json.dumps(pdf_info["page_texts"]),
            upload_order=next_order,
        )
        db.add(paper_row)
        db.flush()

        uploaded_records.append({
            "id": paper_row.id,
            "filename": paper_row.filename,
            "pages_kept": paper_row.pages_kept,
            "pages_trimmed": paper_row.pages_trimmed,
            "total_pages": pdf_info["total_pages"],
            "status": "ready",
        })
        next_order += 1

    db.commit()
    total_papers = db.query(PaperModel).filter(PaperModel.session_id == session_id).count()

    return {
        "session_id": session_id,
        "uploaded": uploaded_records,
        "total_papers": total_papers,
        "max_papers": max_allowed,
    }


@router.delete("/{session_id}/paper/{paper_id}")
def delete_paper(session_id: str, paper_id: int, db: Session = Depends(get_db)):
    """Removes an uploaded paper from the session."""
    paper = (
        db.query(PaperModel)
        .filter(PaperModel.session_id == session_id, PaperModel.id == paper_id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in this session.")

    db.delete(paper)
    db.commit()
    return {"ok": True, "deleted_paper_id": paper_id}
