"""Configuration settings for the Research Assistant Engine."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'research_engine.db'}")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Two-Model Split for Margin & Quality Engineering
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "gemini-3.5-flash-lite")
SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "gemini-3.5-flash")

# Commercial Mode Limits
MIN_PAPERS = 2
MAX_PAPERS_QUICK = 3
MAX_PAPERS_FULL = 20
MAX_FILE_SIZE_MB = 50
DEFAULT_FULL_MODE_RERUNS = 2

# Pricing Metadata (INR)
PROMO_PRICE_INR = 19
REGULAR_PRICE_INR = 49
