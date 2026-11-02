import React from "react";

export default function HypothesisPanel({
  hypothesis,
  stressTest,
  rerunsRemaining,
  onResynthesize,
  onRunStressTest,
  isProcessing,
}) {
  if (!hypothesis) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="info-card" style={{ borderColor: "#38bdf8" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: "0.76rem", color: "#38bdf8", fontWeight: 700 }}>
            GROUNDED TENTATIVE HYPOTHESIS
          </span>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              className="btn-secondary"
              disabled={isProcessing || rerunsRemaining <= 0}
              onClick={onResynthesize}
            >
              🔄 Re-Synthesize on Cached Matrices ({rerunsRemaining} free left)
            </button>
            <button className="btn-secondary" disabled={isProcessing} onClick={onRunStressTest}>
              🔥 Refresh Devil's Advocate Critique
            </button>
          </div>
        </div>
        <h2 style={{ fontSize: "1.1rem", color: "#fff", lineHeight: 1.45 }}>
          "{hypothesis.tentative_hypothesis}"
        </h2>
        <p style={{ fontSize: "0.84rem", color: "#94a3b8" }}>
          <strong>Evidence Rationale:</strong> {hypothesis.rationale}
        </p>

        <div style={{ marginTop: "0.5rem" }}>
          <div style={{ fontSize: "0.8rem", fontWeight: 700, marginBottom: "0.4rem" }}>
            Actionable Research Objectives:
          </div>
          <ul style={{ paddingLeft: "1.2rem", fontSize: "0.85rem", color: "#e2e8f0" }}>
            {(hypothesis.research_objectives || []).map((obj, i) => (
              <li key={i} style={{ marginBottom: "0.3rem" }}>
                {obj}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {stressTest && (
        <div className="info-card" style={{ borderColor: "#f43f5e" }}>
          <div style={{ fontSize: "0.76rem", color: "#fda4af", fontWeight: 700 }}>
            🔥 "DEVIL'S ADVOCATE" PEER-REVIEW STRESS-TEST
          </div>
          <p style={{ fontSize: "0.88rem", color: "#f8fafc" }}>
            <strong>Reviewer Verdict:</strong> {stressTest.overall_peer_review_verdict}
          </p>
          <div className="cards-grid" style={{ marginTop: "0.4rem" }}>
            {(stressTest.confounding_pitfalls || []).map((p, idx) => (
              <div
                key={idx}
                style={{
                  background: "#0f172a",
                  padding: "0.85rem",
                  borderRadius: "0.5rem",
                  border: "1px solid #334155",
                }}
              >
                <div style={{ fontSize: "0.74rem", color: "#fbbf24", fontWeight: 700 }}>
                  [{p.severity} Risk] Pitfall #{idx + 1}
                </div>
                <div style={{ fontWeight: 700, fontSize: "0.9rem", margin: "0.2rem 0" }}>
                  {p.title}
                </div>
                <div style={{ fontSize: "0.8rem", color: "#cbd5e1", marginBottom: "0.4rem" }}>
                  {p.critique}
                </div>
                <div style={{ fontSize: "0.78rem", color: "#34d399" }}>
                  <strong>✓ Defense / Mitigation:</strong> {p.mitigation_strategy}
                </div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: "0.82rem", color: "#38bdf8", marginTop: "0.4rem" }}>
            <strong>🧪 Decisive Falsification Experiment:</strong> {stressTest.falsification_test}
          </div>
        </div>
      )}
    </div>
  );
}
