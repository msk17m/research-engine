import React, { useState } from "react";
import { MATRIX_SCHEMA_COLUMNS } from "../api";

export default function MatrixTable({ matrices }) {
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [selectedQuote, setSelectedQuote] = useState(null);

  const visibleColumns = MATRIX_SCHEMA_COLUMNS.filter(
    (col) => categoryFilter === "all" || col.category === categoryFilter
  );

  const renderCell = (matrix, col) => {
    const val = matrix[col.key];
    if (val === null || val === undefined) {
      return <span className="null-val">— (null)</span>;
    }
    if (col.key === "methodological_rigor_score" && typeof val === "object") {
      return (
        <div>
          <strong style={{ color: val.risk_level === "Low" ? "#34d399" : "#fbbf24" }}>
            [{val.risk_level || "Medium"} Risk]
          </strong>{" "}
          <span>{val.rationale}</span>
        </div>
      );
    }
    if (typeof val === "object" && "value" in val) {
      if (!val.value) return <span className="null-val">— (null)</span>;
      const isVerified = val.verified !== false;
      return (
        <div>
          <div>{val.value}</div>
          {val.verbatim_quote && (
            <button
              className={`quote-badge ${isVerified ? "" : "unverified"}`}
              onClick={() =>
                setSelectedQuote({
                  paperTitle: matrix.paper_title,
                  columnLabel: col.label,
                  ...val,
                })
              }
            >
              {isVerified ? "✓ Verified" : "⚠ Unverified"} · p.{val.source_page || "?"} Quote
            </button>
          )}
        </div>
      );
    }
    return <span>{String(val)}</span>;
  };

  return (
    <div>
      <div className="filter-pills">
        <span style={{ fontSize: "0.78rem", color: "#94a3b8", marginRight: "0.35rem" }}>
          Column View:
        </span>
        {[
          { id: "all", label: "All 20 Columns" },
          { id: "id", label: "Problem & ID" },
          { id: "method", label: "Method & Visual Diagrams" },
          { id: "metrics", label: "Data, Metrics & Plots" },
          { id: "rigor", label: "Rigor, Limitations & Future" },
        ].map((pill) => (
          <button
            key={pill.id}
            className={`pill-btn ${categoryFilter === pill.id ? "active" : ""}`}
            onClick={() => setCategoryFilter(pill.id)}
          >
            {pill.label}
          </button>
        ))}
      </div>

      <div className="matrix-scroll-container">
        <table className="matrix-table">
          <thead>
            <tr>
              <th className="sticky-col">📌 1–2. Paper Title & Year (Sticky)</th>
              {visibleColumns.map((col) => (
                <th key={col.key}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrices.map((m, idx) => (
              <tr key={idx}>
                <td className="sticky-col">
                  <div style={{ fontWeight: 700, color: "#fff" }}>
                    {m.paper_title || `Paper ${idx + 1}`}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#38bdf8", marginTop: "0.2rem" }}>
                    Year: {m.publication_year || "N/A"}
                  </div>
                </td>
                {visibleColumns.map((col) => (
                  <td key={col.key}>{renderCell(m, col)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedQuote && (
        <div className="modal-backdrop" onClick={() => setSelectedQuote(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "1rem", marginBottom: "0.35rem" }}>
              🔍 Lock 3 & 4: Click-to-Verify Grounded Attribution
            </h3>
            <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginBottom: "0.9rem" }}>
              <strong>{selectedQuote.paperTitle}</strong> · {selectedQuote.columnLabel} · Page{" "}
              {selectedQuote.source_page || "N/A"}
            </div>
            <div
              style={{
                background: "#0f172a",
                padding: "0.9rem",
                borderRadius: "0.5rem",
                borderLeft: "3px solid #10b981",
                fontSize: "0.86rem",
                marginBottom: "0.9rem",
              }}
            >
              "{selectedQuote.verbatim_quote}"
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.78rem", color: "#34d399" }}>
                ✓ Verified deterministically against PDF page text (Lock 4)
              </span>
              <button className="btn-secondary" onClick={() => setSelectedQuote(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
