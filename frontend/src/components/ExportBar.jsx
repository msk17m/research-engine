import React from "react";

export default function ExportBar({ sessionId }) {
  if (!sessionId) return null;

  return (
    <div className="info-card">
      <div style={{ fontSize: "0.78rem", color: "#38bdf8", fontWeight: 700 }}>
        MINIMALIST ACADEMIC EXPORT SUITE (THE CORE 3)
      </div>
      <p style={{ fontSize: "0.84rem", color: "#94a3b8" }}>
        Download your complete 20-column grounded study matrix, cross-synthesis, hypothesis, and citation annotations:
      </p>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginTop: "0.4rem" }}>
        <a
          href={`/api/${sessionId}/export/excel`}
          className="btn-secondary"
          style={{ textDecoration: "none" }}
        >
          📊 Download Excel Workbook (.xlsx — 3 Sheets)
        </a>
        <a
          href={`/api/${sessionId}/export/markdown`}
          className="btn-secondary"
          style={{ textDecoration: "none" }}
        >
          📝 Download Thesis Report (.md — Word/Notion/LaTeX)
        </a>
        <a
          href={`/api/${sessionId}/export/bibtex`}
          className="btn-secondary"
          style={{ textDecoration: "none" }}
        >
          📚 Download Annotated BibTeX (.bib — Zotero/Mendeley)
        </a>
      </div>
    </div>
  );
}
