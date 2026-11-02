"""Analysis, Re-Synthesize (2 free re-runs), Devil's Advocate Stress-Test, and SSE progress endpoints."""

import asyncio
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import MIN_PAPERS
from backend.database import SessionLocal, get_db
from backend.models import PaperModel, SessionModel
from backend.services.gemini_service import (
    extract_paper_matrix,
    generate_hypothesis,
    stress_test_hypothesis,
    synthesize_papers,
)

router = APIRouter(prefix="/api", tags=["analysis"])

# In-memory SSE progress state per session
PROGRESS_STATE: Dict[str, Dict[str, Any]] = {}


class AnalyzeRequest(BaseModel):
    run_stress_test: bool = Field(default=True, description="Automatically run Devil's Advocate critique in Full mode.")
    async_mode: bool = Field(default=False, description="Run pipeline asynchronously in background to prevent browser timeouts.")
    topic: Optional[str] = Field(default=None, max_length=300, description="Optional updated research topic/title.")


class ResynthesizeRequest(BaseModel):
    topic: Optional[str] = Field(default=None, max_length=300, description="Optional updated research topic/title.")


def _serialize_session_results(session_obj: SessionModel) -> Dict[str, Any]:
    """Formats the complete 2-table session state into a structured JSON response."""
    papers_out = []
    matrices = []
    total_pages_kept = 0
    total_pages_trimmed = 0

    for p in session_obj.papers:
        m = json.loads(p.matrix_json) if p.matrix_json else None
        if m:
            matrices.append(m)
        total_pages_kept += p.pages_kept or 0
        total_pages_trimmed += p.pages_trimmed or 0
        papers_out.append({
            "id": p.id,
            "filename": p.filename,
            "pages_kept": p.pages_kept,
            "pages_trimmed": p.pages_trimmed,
            "upload_order": p.upload_order,
            "matrix": m,
        })

    total_pages_all = total_pages_kept + total_pages_trimmed
    pct_saved = round((total_pages_trimmed / total_pages_all) * 100, 1) if total_pages_all > 0 else 0.0

    return {
        "session_id": session_obj.id,
        "topic": session_obj.topic,
        "mode": session_obj.mode,
        "status": session_obj.status,
        "error_message": session_obj.error_message,
        "reruns_remaining": session_obj.reruns_remaining,
        "progress": PROGRESS_STATE.get(session_obj.id, {}),
        "token_savings": {
            "pages_kept": total_pages_kept,
            "pages_trimmed": total_pages_trimmed,
            "percent_saved": pct_saved,
        },
        "papers": papers_out,
        "matrices": matrices,
        "synthesis": {
            "clusters": json.loads(session_obj.clusters_json) if session_obj.clusters_json else [],
            "disagreements": json.loads(session_obj.disagreements_json) if session_obj.disagreements_json else [],
            "gaps": json.loads(session_obj.gaps_json) if session_obj.gaps_json else [],
        },
        "hypothesis": json.loads(session_obj.hypothesis_json) if session_obj.hypothesis_json else None,
        "stress_test": json.loads(session_obj.stress_test_json) if session_obj.stress_test_json else None,
    }


async def _run_pipeline_task(
    session_id: str,
    run_stress_test: bool,
    x_gemini_api_key: Optional[str],
) -> Dict[str, Any]:
    """Runs the 3-stage pipeline with SQLite matrix cache reuse and 3x parallel extraction."""
    db = SessionLocal()
    try:
        session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session_obj:
            raise ValueError("Session not found.")

        papers = list(session_obj.papers)
        total = len(papers)
        completed_count = 0
        sem = asyncio.Semaphore(3)

        # Pre-populate any cached matrices from previous runs of identical files
        for paper in papers:
            if not paper.matrix_json:
                cached_paper = (
                    db.query(PaperModel)
                    .filter(
                        PaperModel.filename == paper.filename,
                        PaperModel.pages_kept == paper.pages_kept,
                        PaperModel.matrix_json.isnot(None),
                    )
                    .first()
                )
                if cached_paper and cached_paper.matrix_json:
                    paper.matrix_json = cached_paper.matrix_json
        db.commit()

        session_topic = session_obj.topic
        session_mode = session_obj.mode

        async def _extract_one(idx: int, paper_id: int):
            nonlocal completed_count
            async with sem:
                sub_db = SessionLocal()
                try:
                    p_row = sub_db.query(PaperModel).filter(PaperModel.id == paper_id).first()
                    if p_row.matrix_json:
                        completed_count += 1
                        PROGRESS_STATE[session_id] = {
                            "event": "progress",
                            "step": "matrix",
                            "paper": completed_count,
                            "total": total,
                            "percent": int(completed_count / (total + 2) * 100),
                            "message": f"Loaded cached 20-col matrix for paper {completed_count} of {total} ({p_row.filename})...",
                        }
                        return json.loads(p_row.matrix_json)

                    PROGRESS_STATE[session_id] = {
                        "event": "progress",
                        "step": "matrix",
                        "paper": completed_count + 1,
                        "total": total,
                        "percent": int(completed_count / (total + 2) * 100),
                        "message": f"Extracting 20-column matrix & verifying quotes ({completed_count + 1}/{total}: {p_row.filename})...",
                    }
                    page_texts = json.loads(p_row.page_texts_json) if p_row.page_texts_json else {}
                    trimmed_path = p_row.trimmed_pdf_path or ""
                    fname = p_row.filename
                finally:
                    sub_db.close()

                matrix_dict = await extract_paper_matrix(
                    trimmed_pdf_path=trimmed_path,
                    filename=fname,
                    page_texts=page_texts,
                    topic=session_topic,
                    mode=session_mode,
                    api_key_override=x_gemini_api_key,
                )

                write_db = SessionLocal()
                try:
                    p_row = write_db.query(PaperModel).filter(PaperModel.id == paper_id).first()
                    if p_row:
                        p_row.matrix_json = json.dumps(matrix_dict)
                        write_db.commit()
                finally:
                    write_db.close()

                completed_count += 1
                PROGRESS_STATE[session_id] = {
                    "event": "progress",
                    "step": "matrix",
                    "paper": completed_count,
                    "total": total,
                    "percent": int(completed_count / (total + 2) * 100),
                    "message": f"Completed matrix {completed_count} of {total} ({fname})...",
                }
                return matrix_dict

        matrices = await asyncio.gather(
            *[_extract_one(idx, p.id) for idx, p in enumerate(papers, start=1)]
        )
        matrices = list(matrices)

        PROGRESS_STATE[session_id] = {
            "event": "progress",
            "step": "synthesis",
            "paper": total,
            "total": total,
            "percent": int(total / (total + 2) * 100),
            "message": f"Cross-synthesizing {total} papers into Clusters, Disagreements, and Research Gaps...",
        }
        synthesis_dict = await synthesize_papers(
            matrices=matrices,
            topic=session_obj.topic,
            api_key_override=x_gemini_api_key,
        )
        session_obj.clusters_json = json.dumps(synthesis_dict.get("clusters", []))
        session_obj.disagreements_json = json.dumps(synthesis_dict.get("disagreements", []))
        session_obj.gaps_json = json.dumps(synthesis_dict.get("gaps", []))
        db.commit()

        PROGRESS_STATE[session_id] = {
            "event": "progress",
            "step": "hypothesis",
            "paper": total,
            "total": total,
            "percent": int((total + 1) / (total + 2) * 100),
            "message": "Formulating Tentative Hypothesis and measurable Research Objectives...",
        }
        hypothesis_dict = await generate_hypothesis(
            matrices=matrices,
            synthesis=synthesis_dict,
            topic=session_obj.topic,
            api_key_override=x_gemini_api_key,
        )
        session_obj.hypothesis_json = json.dumps(hypothesis_dict)

        if session_obj.mode == "full" and run_stress_test:
            PROGRESS_STATE[session_id] = {
                "event": "progress",
                "step": "stress_test",
                "paper": total,
                "total": total,
                "percent": 95,
                "message": "Running 'Devil's Advocate' peer-review stress test...",
            }
            stress_dict = await stress_test_hypothesis(
                matrices=matrices,
                synthesis=synthesis_dict,
                hypothesis=hypothesis_dict,
                topic=session_obj.topic,
                api_key_override=x_gemini_api_key,
            )
            session_obj.stress_test_json = json.dumps(stress_dict)

        session_obj.status = "done"
        session_obj.error_message = None
        db.commit()
        db.refresh(session_obj)

        PROGRESS_STATE[session_id] = {
            "event": "complete",
            "step": "done",
            "percent": 100,
            "message": "Analysis complete.",
        }
        return _serialize_session_results(session_obj)

    except Exception as exc:
        session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session_obj:
            session_obj.status = "error"
            session_obj.error_message = str(exc)
            db.commit()
        PROGRESS_STATE[session_id] = {
            "event": "error",
            "step": "error",
            "percent": 0,
            "message": str(exc),
        }
        raise
    finally:
        db.close()


@router.post("/{session_id}/analyze")
async def analyze_session(
    session_id: str,
    req: AnalyzeRequest = AnalyzeRequest(),
    x_gemini_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Executes the full pipeline:
    1. Enforces minimum 2 papers.
    2. Extracts the 20-column Study Matrix per paper (or 8 columns in Quick Mode) + Lock 4 Quote Verification.
    3. Runs Cross-Paper Synthesis (Clusters, Disagreements, Gaps).
    4. Generates Tentative Hypothesis & Research Objectives (+ Devil's Advocate Stress-Test in Full Mode).
    """
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    papers = session_obj.papers
    if len(papers) < MIN_PAPERS:
        raise HTTPException(
            status_code=400,
            detail=f"At least {MIN_PAPERS} papers are required for cross-synthesis and hypothesis generation. Currently uploaded: {len(papers)}.",
        )

    if req.topic and req.topic.strip():
        session_obj.topic = req.topic.strip()

    # If all papers and synthesis/hypothesis are already completed in SQLite, return immediately
    if session_obj.clusters_json and session_obj.hypothesis_json and all(p.matrix_json for p in papers):
        session_obj.status = "done"
        session_obj.error_message = None
        db.commit()
        PROGRESS_STATE[session_id] = {
            "event": "complete",
            "step": "done",
            "percent": 100,
            "message": "Analysis complete.",
        }
        return _serialize_session_results(session_obj)

    session_obj.status = "processing"
    session_obj.error_message = None
    db.commit()

    if req.async_mode:
        PROGRESS_STATE[session_id] = {
            "event": "progress",
            "step": "starting",
            "paper": 0,
            "total": len(papers),
            "percent": 2,
            "message": f"Starting parallel extraction across {len(papers)} papers...",
        }
        asyncio.create_task(_run_pipeline_task(session_id, req.run_stress_test, x_gemini_api_key))
        return _serialize_session_results(session_obj)

    try:
        return await _run_pipeline_task(session_id, req.run_stress_test, x_gemini_api_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/resynthesize")
async def resynthesize_session(
    session_id: str,
    req: ResynthesizeRequest,
    x_gemini_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Uses one of the 2 free re-runs in Full Mode to re-run Cross-Synthesis and Hypothesis
    on the cached paper matrices (after topic tweak or paper removal) without re-extracting PDFs.
    """
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session_obj.reruns_remaining <= 0:
        raise HTTPException(
            status_code=400,
            detail="No free re-synthesis runs remaining for this session.",
        )

    papers = session_obj.papers
    if len(papers) < MIN_PAPERS:
        raise HTTPException(
            status_code=400,
            detail=f"At least {MIN_PAPERS} papers must remain in the session to re-synthesize.",
        )

    matrices = [json.loads(p.matrix_json) for p in papers if p.matrix_json]
    if len(matrices) < MIN_PAPERS:
        raise HTTPException(
            status_code=400,
            detail="Cached paper matrices not found. Run initial analysis first.",
        )

    if req.topic and req.topic.strip():
        session_obj.topic = req.topic.strip()

    synthesis_dict = await synthesize_papers(
        matrices=matrices,
        topic=session_obj.topic,
        api_key_override=x_gemini_api_key,
    )
    hypothesis_dict = await generate_hypothesis(
        matrices=matrices,
        synthesis=synthesis_dict,
        topic=session_obj.topic,
        api_key_override=x_gemini_api_key,
    )

    session_obj.clusters_json = json.dumps(synthesis_dict.get("clusters", []))
    session_obj.disagreements_json = json.dumps(synthesis_dict.get("disagreements", []))
    session_obj.gaps_json = json.dumps(synthesis_dict.get("gaps", []))
    session_obj.hypothesis_json = json.dumps(hypothesis_dict)
    session_obj.reruns_remaining -= 1
    session_obj.status = "done"
    db.commit()
    db.refresh(session_obj)

    return _serialize_session_results(session_obj)


@router.post("/{session_id}/stress-test")
async def run_stress_test_endpoint(
    session_id: str,
    x_gemini_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """Triggers or refreshes the 'Devil's Advocate' hypothesis stress-test."""
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    if not session_obj.hypothesis_json:
        raise HTTPException(status_code=400, detail="Generate a hypothesis before running the stress-test.")

    matrices = [json.loads(p.matrix_json) for p in session_obj.papers if p.matrix_json]
    synthesis = {
        "clusters": json.loads(session_obj.clusters_json) if session_obj.clusters_json else [],
        "disagreements": json.loads(session_obj.disagreements_json) if session_obj.disagreements_json else [],
        "gaps": json.loads(session_obj.gaps_json) if session_obj.gaps_json else [],
    }
    hypothesis = json.loads(session_obj.hypothesis_json)

    stress_dict = await stress_test_hypothesis(
        matrices=matrices,
        synthesis=synthesis,
        hypothesis=hypothesis,
        topic=session_obj.topic,
        api_key_override=x_gemini_api_key,
    )
    session_obj.stress_test_json = json.dumps(stress_dict)
    db.commit()
    db.refresh(session_obj)

    return {"session_id": session_id, "stress_test": stress_dict}


@router.get("/latest-session")
def get_latest_session(db: Session = Depends(get_db)):
    """Returns the most recent session with uploaded papers so a browser refresh restores state."""
    sessions = db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
    for s in sessions:
        if len(s.papers) >= 2:
            return _serialize_session_results(s)
    raise HTTPException(status_code=404, detail="No active session found.")


@router.get("/{session_id}/results")
def get_session_results(session_id: str, db: Session = Depends(get_db)):
    """Returns full session results including 20-col matrices, synthesis, hypothesis, and stress-test."""
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")
    return _serialize_session_results(session_obj)


@router.get("/{session_id}/status")
async def stream_session_status(session_id: str):
    """Server-Sent Events (SSE) progress endpoint."""
    async def event_generator():
        last_sent = None
        for _ in range(600):
            state = PROGRESS_STATE.get(session_id, {"event": "idle", "percent": 0, "message": "Waiting..."})
            payload = json.dumps(state)
            if payload != last_sent:
                yield f"data: {payload}\n\n"
                last_sent = payload
            if state.get("event") in {"complete", "error"}:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
