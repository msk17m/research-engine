"""Minimalist Export Service generating the Big 3 academic formats: Excel (.xlsx), Markdown (.md), and BibTeX (.bib)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from backend.config import EXPORT_DIR

MATRIX_COLUMNS = [
    ("paper_title", "1. Paper Title"),
    ("publication_year", "2. Year"),
    ("study_type", "3. Study Type"),
    ("research_question", "4. Research Question (Grounded)"),
    ("core_method_or_approach", "5. Core Method / Approach (Grounded)"),
    ("theoretical_framework", "6. Theoretical Framework"),
    ("visual_architecture_summary", "7. Visual Architecture Summary"),
    ("dataset_or_domain", "8. Dataset / Domain"),
    ("evaluation_metrics", "9. Evaluation Metrics"),
    ("baselines_compared", "10. Baselines Compared"),
    ("key_results_or_findings", "11. Key Results / Findings (Grounded)"),
    ("key_graph_trends", "12. Key Graph Trends"),
    ("main_claimed_contribution", "13. Main Claimed Contribution (Grounded)"),
    ("key_assumptions", "14. Key Assumptions"),
    ("negative_results_or_failures", "15. Negative Results / Failures"),
    ("stated_limitations", "16. Stated Limitations (Grounded)"),
    ("methodological_rigor_score", "17. Methodological Rigor & Risk-of-Bias"),
    ("author_future_work", "18. Author Future Work"),
    ("artifact_urls", "19. Artifact URLs (Code/Data)"),
    ("relation_to_topic", "20. Relation to My Topic"),
]


def _format_cell_value(val: Any) -> str:
    """Formats plain values, GroundedClaim dicts, or MethodologicalRigor dicts into readable text."""
    if val is None:
        return "—"
    if isinstance(val, dict):
        if "risk_level" in val:
            lvl = val.get("risk_level") or "—"
            rat = val.get("rationale") or ""
            return f"[{lvl} Risk] {rat}".strip()
        claim_val = val.get("value")
        if not claim_val:
            return "—"
        page = val.get("source_page")
        quote = val.get("verbatim_quote")
        verified = val.get("verified")
        badge = "✓ Verified" if verified else ("⚠ Unverified" if verified is False else "")
        page_str = f"p.{page}" if page else ""
        meta = " ".join(p for p in [badge, page_str] if p)
        if quote:
            return f"{claim_val}\n[{meta} Quote: \"{quote}\"]"
        return f"{claim_val} [{meta}]".strip()
    return str(val)


def export_to_excel(
    session_id: str,
    topic: str,
    matrices: List[Dict[str, Any]],
    synthesis: Dict[str, Any],
    hypothesis: Dict[str, Any],
    stress_test: Dict[str, Any] | None = None,
) -> Path:
    """Generates a 3-sheet formatted Excel workbook (.xlsx)."""
    wb = openpyxl.Workbook()

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    wrap_align = Alignment(wrap_text=True, vertical="top")

    # Sheet 1: 20-Column Study Matrix
    ws_matrix = wb.active
    ws_matrix.title = "Study Matrix (20 Cols)"

    headers = [col_label for _, col_label in MATRIX_COLUMNS]
    ws_matrix.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws_matrix.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = wrap_align
        ws_matrix.column_dimensions[get_column_letter(col_idx)].width = 32

    for row_idx, matrix in enumerate(matrices, start=2):
        row_vals = [_format_cell_value(matrix.get(key)) for key, _ in MATRIX_COLUMNS]
        ws_matrix.append(row_vals)
        for col_idx in range(1, len(headers) + 1):
            ws_matrix.cell(row=row_idx, column=col_idx).alignment = wrap_align

    ws_matrix.freeze_panes = "B2"

    # Sheet 2: Cross-Synthesis (Clusters, Disagreements, Gaps)
    ws_syn = wb.create_sheet(title="Cross-Synthesis")
    ws_syn.append(["Category", "Title / Dimension", "Papers / Evidence", "Synthesis Description"])
    for col_idx in range(1, 5):
        cell = ws_syn.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        ws_syn.column_dimensions[get_column_letter(col_idx)].width = 38

    for c in synthesis.get("clusters", []):
        ws_syn.append([
            "CLUSTER",
            f"{c.get('cluster_name', '')} ({c.get('shared_theme', '')})",
            ", ".join(c.get("paper_titles", [])),
            c.get("description", ""),
        ])
    for d in synthesis.get("disagreements", []):
        ws_syn.append([
            "DISAGREEMENT",
            d.get("dimension", ""),
            f"{d.get('paper_a', '')} vs. {d.get('paper_b', '')}",
            d.get("conflict_description", ""),
        ])
    for g in synthesis.get("gaps", []):
        ws_syn.append([
            "RESEARCH GAP",
            g.get("gap_title", ""),
            g.get("supporting_evidence", ""),
            f"{g.get('gap_description', '')}\nDirection: {g.get('direction_for_hypothesis', '')}",
        ])
    for row in ws_syn.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap_align

    # Sheet 3: Hypothesis, Objectives & Devil's Advocate Stress-Test
    ws_hyp = wb.create_sheet(title="Hypothesis & Stress-Test")
    ws_hyp.append(["Section", "Content"])
    for col_idx in (1, 2):
        cell = ws_hyp.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
    ws_hyp.column_dimensions["A"].width = 30
    ws_hyp.column_dimensions["B"].width = 85

    ws_hyp.append(["Proposed Topic", topic])
    ws_hyp.append(["Tentative Hypothesis", hypothesis.get("tentative_hypothesis", "—")])
    ws_hyp.append(["Evidence Rationale", hypothesis.get("rationale", "—")])
    for idx, obj in enumerate(hypothesis.get("research_objectives", []), start=1):
        ws_hyp.append([f"Objective {idx}", obj])

    if stress_test:
        ws_hyp.append(["Devil's Advocate Verdict", stress_test.get("overall_peer_review_verdict", "—")])
        for p in stress_test.get("confounding_pitfalls", []):
            ws_hyp.append([
                f"Pitfall ({p.get('severity', 'High')}): {p.get('title', '')}",
                f"Critique: {p.get('critique', '')}\nMitigation: {p.get('mitigation_strategy', '')}",
            ])
        ws_hyp.append(["Decisive Falsification Test", stress_test.get("falsification_test", "—")])

    for row in ws_hyp.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap_align

    out_path = EXPORT_DIR / f"research_matrix_{session_id}.xlsx"
    wb.save(str(out_path))
    return out_path


def export_to_markdown(
    session_id: str,
    topic: str,
    matrices: List[Dict[str, Any]],
    synthesis: Dict[str, Any],
    hypothesis: Dict[str, Any],
    stress_test: Dict[str, Any] | None = None,
) -> Path:
    """Generates a comprehensive thesis-ready Markdown literature review report (.md)."""
    lines = [
        f"# Systematic Literature Review & Synthesis Report",
        f"**Proposed Research Topic:** {topic}",
        f"**Papers Analyzed:** {len(matrices)}",
        "",
        "---",
        "",
        "## 1. Study Matrix (Per-Paper Grounded Analysis)",
        "",
    ]

    for idx, m in enumerate(matrices, start=1):
        title = m.get("paper_title") or f"Paper {idx}"
        year = m.get("publication_year") or "N/A"
        lines.append(f"### {idx}. {title} ({year})")
        for key, label in MATRIX_COLUMNS[2:]:
            formatted = _format_cell_value(m.get(key)).replace("\n", " ")
            lines.append(f"- **{label}:** {formatted}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 2. Cross-Paper Synthesis",
        "",
        "### 2.1 Thematic & Methodological Clusters",
    ])
    for c in synthesis.get("clusters", []):
        lines.append(f"- **{c.get('cluster_name')}** (*{c.get('shared_theme')}*)")
        lines.append(f"  - **Papers:** {', '.join(c.get('paper_titles', []))}")
        lines.append(f"  - **Synthesis:** {c.get('description')}")

    lines.extend(["", "### 2.2 Cross-Paper Disagreements & Conflicts"])
    for d in synthesis.get("disagreements", []):
        lines.append(f"- **{d.get('paper_a')} vs. {d.get('paper_b')}** [{d.get('dimension')}]")
        lines.append(f"  - {d.get('conflict_description')}")

    lines.extend(["", "### 2.3 Identified Research Gaps"])
    for g in synthesis.get("gaps", []):
        lines.append(f"- **{g.get('gap_title')}**")
        lines.append(f"  - **Unanswered Question:** {g.get('gap_description')}")
        lines.append(f"  - **Supporting Evidence:** {g.get('supporting_evidence')}")
        lines.append(f"  - **Hypothesis Direction:** {g.get('direction_for_hypothesis')}")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Tentative Hypothesis & Research Objectives",
        "",
        f"### Tentative Hypothesis",
        f"> {hypothesis.get('tentative_hypothesis', '—')}",
        "",
        f"**Grounded Rationale:** {hypothesis.get('rationale', '—')}",
        "",
        "### Research Objectives",
    ])
    for obj in hypothesis.get("research_objectives", []):
        lines.append(f"- {obj}")

    if stress_test:
        lines.extend([
            "",
            "---",
            "",
            "## 4. 'Devil's Advocate' Peer-Review Stress-Test",
            "",
            f"**Overall Verdict:** {stress_test.get('overall_peer_review_verdict', '—')}",
            "",
        ])
        for p in stress_test.get("confounding_pitfalls", []):
            lines.append(f"- **[{p.get('severity')}] {p.get('title')}**")
            lines.append(f"  - *Critique:* {p.get('critique')}")
            lines.append(f"  - *Mitigation:* {p.get('mitigation_strategy')}")
        lines.append(f"\n**Decisive Falsification Test:** {stress_test.get('falsification_test', '—')}")

    out_path = EXPORT_DIR / f"research_report_{session_id}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def export_to_bibtex(
    session_id: str,
    matrices: List[Dict[str, Any]],
) -> Path:
    """Generates a BibTeX (.bib) file with grounded matrix notes embedded in the `annote` field."""
    entries = []
    for idx, m in enumerate(matrices, start=1):
        title = m.get("paper_title") or f"Uploaded Paper {idx}"
        year = m.get("publication_year") or 2026
        slug = re.sub(r"[^a-z0-9]", "", title.lower())[:14] or f"paper{idx}"
        cite_key = f"{slug}{year}_{idx}"

        method_str = _format_cell_value(m.get("core_method_or_approach")).replace("\n", " ")
        results_str = _format_cell_value(m.get("key_results_or_findings")).replace("\n", " ")
        limits_str = _format_cell_value(m.get("stated_limitations")).replace("\n", " ")
        annote = f"Method: {method_str} | Key Findings: {results_str} | Limitations: {limits_str}"
        annote_escaped = annote.replace("{", "(").replace("}", ")")
        title_escaped = title.replace("{", "").replace("}", "")

        entry = (
            f"@article{{{cite_key},\n"
            f"  title = {{{title_escaped}}},\n"
            f"  year = {{{year}}},\n"
            f"  note = {{Study Type: {m.get('study_type') or 'Empirical'}}},\n"
            f"  annote = {{{annote_escaped}}}\n"
            f"}}"
        )
        entries.append(entry)

    out_path = EXPORT_DIR / f"citations_{session_id}.bib"
    out_path.write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    return out_path
