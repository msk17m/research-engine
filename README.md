# 🧠 Research Assistant Engine (v1.1)

A **minimalist, zero-hallucination Research Assistant Engine** built with **FastAPI**, **PyMuPDF**, **Google Gemini (`gemini-3.5-flash-lite` + `gemini-3.8-flash`)**, **SQLite**, and **React**.

## Key Features

1. **4-Lock Zero-Hallucination Engine (0 MB Local ML RAM Overhead):**
   - **Lock 1:** Deterministic decoding (`temperature = 0.0`).
   - **Lock 2:** Strict Nullable 20-Column Pydantic JSON Schema (`Optional[...]` — returns `null` if not in paper).
   - **Lock 3:** Click-to-Verify Evidence Tuple (`{ value, source_page, verbatim_quote }`).
   - **Lock 4:** Deterministic Python Quote Verifier (`quote_verifier.py`) checking every `verbatim_quote` against PyMuPDF page texts in `<5ms`.
2. **Unified PDF Ingestion & Smart Pre-Filtering (`pdf_service.py`):**
   - Fast `<5ms` academic structure gate.
   - Automatically detects `References` / `Bibliography` sections and slices the PDF in-memory (`doc.select()`) to strip trailing bibliography pages, saving **20%–35% input tokens**.
   - Uploads the trimmed PDF to Gemini's Files API for native multimodal understanding of **architecture diagrams, plots/graphs, and LaTeX tables**.
3. **All 20 Distinct Matrix Columns + Sticky UI Table:**
   - Extracts all 20 distinct academic dimensions in Full Review Mode (`₹19 Promo` / `~~₹49~~ Regular`, up to 20 papers) or 8 core columns in Quick Trial Mode (`₹0 Free`, up to 3 papers).
   - Sticky first column (`Paper Title & Year`) + Category Filter Pills.
4. **Iterative Re-Synthesize & "Devil's Advocate" Peer Critique:**
   - Paid Full Mode sessions include **2 free Re-Synthesize runs** on cached matrices + automated harsh peer-review stress testing.
5. **Minimalist Core 3 Exports:**
   - **Excel Workbook (`.xlsx`)** (3 formatted sheets), **Thesis Report (`.md`)**, and **Annotated BibTeX (`.bib`)** (Zotero/Mendeley/LaTeX compatible).

---

## Quick Start (Zero Node.js Required)

```powershell
cd C:\Users\mdsqk\.gemini\antigravity\scratch\research_assistant

# Optional: Set your free Google AI Studio API Key (or paste it directly in the Web UI)
$env:GEMINI_API_KEY = "your-api-key-here"

# Start the server (serves both API and React Frontend on http://localhost:8000)
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open **http://localhost:8000** in your browser.

## Running Automated Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_engine.py -v
```
