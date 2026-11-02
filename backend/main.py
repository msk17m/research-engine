"""FastAPI main application entrypoint for the Research Assistant Engine."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_DIR, EXTRACTION_MODEL, PROMO_PRICE_INR, REGULAR_PRICE_INR, SYNTHESIS_MODEL
from backend.database import init_db
from backend.routers import analysis, export, session

FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize SQLite tables on server startup."""
    init_db()
    yield


app = FastAPI(
    title="Research Assistant Engine",
    description=(
        "Zero-Hallucination Literature Review Matrix (20 Distinct Columns), "
        "Cross-Synthesis, Hypothesis Formulation & Devil's Advocate Stress-Testing."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router)
app.include_router(analysis.router)
app.include_router(export.router)


@app.get("/api/health")
def health_check():
    """Health and architecture metadata endpoint."""
    return {
        "status": "ok",
        "version": "1.1.0",
        "models": {
            "stage1_extraction": EXTRACTION_MODEL,
            "stage2_3_synthesis_hypothesis": SYNTHESIS_MODEL,
        },
        "zero_hallucination_locks": [
            "Lock 1: Deterministic Decoding (temperature=0.0)",
            "Lock 2: Nullable 20-Column Pydantic JSON Schema",
            "Lock 3: Click-to-Verify Evidence Tuple (value, source_page, verbatim_quote)",
            "Lock 4: Python Deterministic Quote Verifier (<5ms, 0 MB RAM)",
        ],
        "pricing_inr": {
            "quick_mode": 0,
            "full_mode_promo": PROMO_PRICE_INR,
            "full_mode_regular": REGULAR_PRICE_INR,
        },
    }


if (FRONTEND_DIR / "src").exists():
    app.mount("/src", StaticFiles(directory=str(FRONTEND_DIR / "src")), name="src")


@app.get("/")
def serve_frontend():
    """Serves the React SPA directly so no separate Node build step is required on the user's laptop."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Research Assistant Engine API is running. Visit /docs for Swagger UI."}
