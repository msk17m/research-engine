"""Comprehensive automated test suite for the Research Assistant Engine."""

from pathlib import Path
import fitz  # PyMuPDF
import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import init_db
from backend.services.pdf_service import process_and_trim_pdf
from backend.services.quote_verifier import verify_grounded_claim

init_db()
client = TestClient(app)


def _create_sample_academic_pdf(path: Path, title: str, year: int = 2025, ref_pages: int = 2) -> bytes:
    """Creates a realistic multi-page academic PDF with body sections and trailing References pages."""
    doc = fitz.open()

    # Page 1: Title, Abstract, Introduction, Research Question
    p1 = doc.new_page()
    p1.insert_text(
        (50, 60),
        f"{title}\nPublished in {year}\n\n"
        "Abstract\n"
        "In this study, we investigate the problem of robust multi-modal representation learning under severe domain shift.\n"
        "Introduction\n"
        "Recent deep learning architectures struggle when deployed in clinical environments et al. (2024). "
        "Figure 1 illustrates our dual-stream encoder-decoder pipeline with cross-attention gating.",
    )

    # Page 2: Methodology, Dataset, Baselines
    p2 = doc.new_page()
    p2.insert_text(
        (50, 60),
        "2. Methodology and Theoretical Framework\n"
        "We propose a novel variational graph information bottleneck algorithm grounded in Bayesian diffusion theory.\n"
        "We assume that node neighborhoods satisfy local Markov independence under bounded noise.\n"
        "3. Experimental Setup and Dataset\n"
        "We evaluate on the MIMIC-IV benchmark dataset comprising N = 14,500 patient records compared to ResNet-50 and GraphSAGE baselines.",
    )

    # Page 3: Results, Metrics, Plots
    p3 = doc.new_page()
    p3.insert_text(
        (50, 60),
        "4. Empirical Results and Discussion\n"
        "As shown in Table 1, our model achieves 94.2% F1-score and 0.961 AUC-ROC, outperforming all prior state-of-the-art baselines (p < 0.001).\n"
        "Figure 2 plot demonstrates that inference latency scales linearly and Pareto efficiency holds up to batch size 64.\n"
        "Our main contribution is the first zero-leakage spectral regularizer for clinical time-series.\n"
        "Code and weights are available at https://github.com/example-lab/clinical-gnn",
    )

    # Page 4: Limitations, Negative Results, Future Work
    p4 = doc.new_page()
    p4.insert_text(
        (50, 60),
        "5. Limitations and Conclusion\n"
        "A primary limitation of our approach is its reliance on synchronized timestamp annotations during pre-training.\n"
        "In error analysis, the model degrades when more than 60% of sensor channels are missing.\n"
        "In future work, we plan to extend this framework to asynchronous federated learning across hospitals.",
    )

    # Trailing Reference pages (Pages 5..4+ref_pages)
    for r in range(ref_pages):
        pr = doc.new_page()
        header = "References\n" if r == 0 else "References (Continued)\n"
        refs = "\n".join([f"[{i}] Author et al., Journal of Machine Learning, 202{i % 5}, doi:10.1000/{i}" for i in range(1, 25)])
        pr.insert_text((50, 60), header + refs)

    pdf_bytes = doc.tobytes()
    doc.close()
    path.write_bytes(pdf_bytes)
    return pdf_bytes


def _create_non_academic_pdf(path: Path) -> bytes:
    """Creates a 2-page non-academic PDF (e.g., restaurant menu) to test rejection gate."""
    doc = fitz.open()
    for i in range(2):
        p = doc.new_page()
        p.insert_text((50, 60), f"Downtown Pizza Menu Page {i+1}\nCheese Pizza $12\nGarlic Bread $5\nSoda $2\nThank you for dining with us!" * 8)
    pdf_bytes = doc.tobytes()
    doc.close()
    path.write_bytes(pdf_bytes)
    return pdf_bytes


def test_pdf_service_academic_gate_and_reference_trimming(tmp_path: Path):
    """Tests that PyMuPDF keeps analytical pages, strips Reference pages, and rejects non-academic PDFs."""
    raw_pdf = tmp_path / "sample_paper.pdf"
    trimmed_pdf = tmp_path / "trimmed_paper.pdf"
    _create_sample_academic_pdf(raw_pdf, "Adaptive Clinical Graph Networks", year=2025, ref_pages=2)

    info = process_and_trim_pdf(raw_pdf, trimmed_pdf)
    assert info["total_pages"] == 6
    assert info["pages_kept"] == 4
    assert info["pages_trimmed"] == 2
    assert trimmed_pdf.exists()

    # Reject non-academic PDF
    bad_pdf = tmp_path / "menu.pdf"
    _create_non_academic_pdf(bad_pdf)
    with pytest.raises(ValueError, match="does not appear to be an academic"):
        process_and_trim_pdf(bad_pdf, tmp_path / "out_bad.pdf")


def test_lock4_quote_verifier():
    """Tests that Lock 4 deterministically verifies real quotes and flags hallucinated quotes."""
    page_texts = {
        "1": "In this study, we investigate the problem of robust multi-modal representation learning under severe domain shift.",
        "2": "As shown in Table 1, our model achieves 94.2% F1-score and 0.961 AUC-ROC, outperforming all prior state-of-the-art baselines.",
    }

    real_claim = {
        "value": "Achieves 94.2% F1-score and 0.961 AUC-ROC",
        "source_page": 2,
        "verbatim_quote": "our model achieves 94.2% F1-score and 0.961 AUC-ROC, outperforming all prior state-of-the-art baselines.",
    }
    verified_real = verify_grounded_claim(real_claim, page_texts)
    assert verified_real is not None
    assert verified_real["verified"] is True

    fake_claim = {
        "value": "Tested on 1 million quantum qubits on Mars",
        "source_page": 1,
        "verbatim_quote": "We deployed 1 million superconducting quantum qubits on the Martian surface.",
    }
    verified_fake = verify_grounded_claim(fake_claim, page_texts)
    assert verified_fake is not None
    assert verified_fake["verified"] is False

    # Null claim returns None (Zero fabrication)
    assert verify_grounded_claim({"value": None, "source_page": None, "verbatim_quote": None}, page_texts) is None


def test_end_to_end_session_20_columns_reruns_and_exports(tmp_path: Path):
    """Tests full API lifecycle: session creation, cap checks, 20-col matrix, 2 free re-runs, stress-test, and 3 exports."""
    # 1. Create a Full Mode session
    resp = client.post("/api/session", json={"topic": "Robust Clinical Graph Neural Networks", "mode": "full"})
    assert resp.status_code == 200
    session_data = resp.json()
    sid = session_data["session_id"]
    assert session_data["max_papers"] == 20
    assert session_data["reruns_remaining"] == 2

    # 2. Upload 1 paper first -> verify single-paper analysis is blocked (min 2 papers required)
    p1_bytes = _create_sample_academic_pdf(tmp_path / "p1.pdf", "Spectral Graph Networks in ICU Forecasting", 2024)
    up1 = client.post(
        f"/api/{sid}/upload",
        files=[("files", ("paper1.pdf", p1_bytes, "application/pdf"))],
    )
    assert up1.status_code == 200
    assert up1.json()["uploaded"][0]["pages_trimmed"] == 2

    single_analyze = client.post(f"/api/{sid}/analyze", json={"run_stress_test": True})
    assert single_analyze.status_code == 400
    assert "At least 2 papers" in single_analyze.json()["detail"]

    # 3. Upload 2nd paper and run full analysis
    p2_bytes = _create_sample_academic_pdf(tmp_path / "p2.pdf", "Variational Diffusion for Electronic Health Records", 2025)
    up2 = client.post(
        f"/api/{sid}/upload",
        files=[("files", ("paper2.pdf", p2_bytes, "application/pdf"))],
    )
    assert up2.status_code == 200
    assert up2.json()["total_papers"] == 2

    an_resp = client.post(f"/api/{sid}/analyze", json={"run_stress_test": True})
    assert an_resp.status_code == 200
    results = an_resp.json()

    assert results["status"] == "done"
    assert len(results["matrices"]) == 2
    assert results["token_savings"]["pages_trimmed"] == 4

    # Verify all 20 distinct columns exist in extracted matrix
    first_matrix = results["matrices"][0]
    expected_20_keys = {
        "paper_title", "publication_year", "study_type", "research_question",
        "core_method_or_approach", "theoretical_framework", "visual_architecture_summary",
        "dataset_or_domain", "evaluation_metrics", "baselines_compared",
        "key_results_or_findings", "key_graph_trends", "main_claimed_contribution",
        "key_assumptions", "negative_results_or_failures", "stated_limitations",
        "methodological_rigor_score", "author_future_work", "artifact_urls", "relation_to_topic",
    }
    assert expected_20_keys.issubset(set(first_matrix.keys()))
    assert first_matrix["key_results_or_findings"]["verified"] is True

    # Verify synthesis, hypothesis & stress-test
    assert len(results["synthesis"]["clusters"]) >= 1
    assert len(results["synthesis"]["disagreements"]) >= 1
    assert len(results["synthesis"]["gaps"]) >= 1
    assert results["hypothesis"]["tentative_hypothesis"]
    assert len(results["stress_test"]["confounding_pitfalls"]) == 3

    # 4. Test the 2 Free Re-Synthesize runs on cached matrices
    re1 = client.post(f"/api/{sid}/resynthesize", json={"topic": "Federated Clinical GNNs under Missing Sensors"})
    assert re1.status_code == 200
    assert re1.json()["reruns_remaining"] == 1

    re2 = client.post(f"/api/{sid}/resynthesize", json={"topic": "Privacy-Preserving ICU Graph Learning"})
    assert re2.status_code == 200
    assert re2.json()["reruns_remaining"] == 0

    # 3rd re-run should be blocked
    re3 = client.post(f"/api/{sid}/resynthesize", json={"topic": "Third Re-Run Attempt"})
    assert re3.status_code == 400

    # 5. Test the 3 Core Exports (Excel, Markdown, BibTeX)
    xl_resp = client.get(f"/api/{sid}/export/excel")
    assert xl_resp.status_code == 200
    xl_file = tmp_path / "export.xlsx"
    xl_file.write_bytes(xl_resp.content)
    wb = openpyxl.load_workbook(xl_file)
    assert wb.sheetnames == ["Study Matrix (20 Cols)", "Cross-Synthesis", "Hypothesis & Stress-Test"]
    assert wb["Study Matrix (20 Cols)"].max_column == 20

    md_resp = client.get(f"/api/{sid}/export/markdown")
    assert md_resp.status_code == 200
    assert "Systematic Literature Review & Synthesis Report" in md_resp.text

    bib_resp = client.get(f"/api/{sid}/export/bibtex")
    assert bib_resp.status_code == 200
    assert "@article{" in bib_resp.text
    assert "annote =" in bib_resp.text
