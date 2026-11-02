"""Export router for downloading Excel (.xlsx), Markdown (.md), and BibTeX (.bib) files."""

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SessionModel
from backend.services.export_service import (
    export_to_bibtex,
    export_to_excel,
    export_to_markdown,
)

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/{session_id}/export/{fmt}")
def export_session(session_id: str, fmt: str, db: Session = Depends(get_db)):
    """Exports session results into Excel (.xlsx), Markdown (.md), or BibTeX (.bib)."""
    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    matrices = [json.loads(p.matrix_json) for p in session_obj.papers if p.matrix_json]
    if not matrices:
        raise HTTPException(status_code=400, detail="No extracted matrices available to export.")

    synthesis = {
        "clusters": json.loads(session_obj.clusters_json) if session_obj.clusters_json else [],
        "disagreements": json.loads(session_obj.disagreements_json) if session_obj.disagreements_json else [],
        "gaps": json.loads(session_obj.gaps_json) if session_obj.gaps_json else [],
    }
    hypothesis = json.loads(session_obj.hypothesis_json) if session_obj.hypothesis_json else {}
    stress_test = json.loads(session_obj.stress_test_json) if session_obj.stress_test_json else None

    fmt_clean = fmt.lower().strip()
    if fmt_clean in {"excel", "xlsx"}:
        path = export_to_excel(session_id, session_obj.topic, matrices, synthesis, hypothesis, stress_test)
        return FileResponse(
            path=str(path),
            filename=f"study_matrix_{session_id[:8]}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    elif fmt_clean in {"markdown", "md"}:
        path = export_to_markdown(session_id, session_obj.topic, matrices, synthesis, hypothesis, stress_test)
        return FileResponse(
            path=str(path),
            filename=f"literature_review_{session_id[:8]}.md",
            media_type="text/markdown; charset=utf-8",
        )
    elif fmt_clean in {"bibtex", "bib"}:
        path = export_to_bibtex(session_id, matrices)
        return FileResponse(
            path=str(path),
            filename=f"citations_{session_id[:8]}.bib",
            media_type="application/x-bibtex; charset=utf-8",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export format '{fmt}'. Supported formats: excel, markdown, bibtex.",
        )
