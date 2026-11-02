import React from "react";

export default function SynthesisPanel({ synthesis, subTab }) {
  const clusters = synthesis?.clusters || [];
  const disagreements = synthesis?.disagreements || [];
  const gaps = synthesis?.gaps || [];

  if (subTab === "clusters") {
    return (
      <div className="cards-grid">
        {clusters.map((c, idx) => (
          <div key={idx} className="info-card">
            <div style={{ fontSize: "0.75rem", color: "#38bdf8", fontWeight: 700 }}>
              CLUSTER {idx + 1} · {c.shared_theme}
            </div>
            <h3 style={{ fontSize: "1rem" }}>{c.cluster_name}</h3>
            <p style={{ fontSize: "0.84rem", color: "#cbd5e1" }}>{c.description}</p>
            <div style={{ fontSize: "0.76rem", color: "#94a3b8", marginTop: "0.35rem" }}>
              <strong>Papers ({c.paper_titles?.length || 0}):</strong>{" "}
              {(c.paper_titles || []).join(" · ")}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (subTab === "disagreements") {
    return (
      <div className="cards-grid">
        {disagreements.map((d, idx) => (
          <div key={idx} className="info-card">
            <div style={{ fontSize: "0.75rem", color: "#f59e0b", fontWeight: 700 }}>
              CONFLICT DIMENSION: {d.dimension}
            </div>
            <h3 style={{ fontSize: "0.95rem" }}>
              ⚡ {d.paper_a} <span style={{ color: "#94a3b8" }}>vs.</span> {d.paper_b}
            </h3>
            <p style={{ fontSize: "0.84rem", color: "#cbd5e1" }}>{d.conflict_description}</p>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="cards-grid">
      {gaps.map((g, idx) => (
        <div key={idx} className="info-card">
          <div style={{ fontSize: "0.75rem", color: "#34d399", fontWeight: 700 }}>
            UNANSWERED RESEARCH GAP #{idx + 1}
          </div>
          <h3 style={{ fontSize: "1rem" }}>{g.gap_title}</h3>
          <p style={{ fontSize: "0.85rem", color: "#f8fafc" }}>{g.gap_description}</p>
          <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>
            <strong>Supporting Matrix Evidence:</strong> {g.supporting_evidence}
          </div>
          <div
            style={{
              fontSize: "0.8rem",
              color: "#38bdf8",
              background: "rgba(56, 189, 248, 0.08)",
              padding: "0.55rem",
              borderRadius: "0.4rem",
            }}
          >
            <strong>→ Direction for Hypothesis:</strong> {g.direction_for_hypothesis}
          </div>
        </div>
      ))}
    </div>
  );
}
