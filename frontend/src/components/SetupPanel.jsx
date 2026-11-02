import React from "react";

export default function SetupPanel({
  mode,
  setMode,
  topic,
  setTopic,
  apiKey,
  setApiKey,
  papers,
  maxPapers,
  onUploadFiles,
  onDeletePaper,
  onRunAnalysis,
  isProcessing,
  progress,
  errorMsg,
}) {
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onUploadFiles(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  return (
    <aside className="setup-sidebar">
      <div>
        <span className="section-label">1. Select Review Tier</span>
        <div className="mode-cards">
          <div
            className={`mode-card ${mode === "full" ? "active" : ""}`}
            onClick={() => !isProcessing && setMode("full")}
          >
            <div className="mode-card-title">
              <span>Full Review</span>
              <span>
                <span className="price-tag">₹19</span>
                <span className="price-strike">₹49</span>
              </span>
            </div>
            <div className="mode-card-desc">
              Up to 20 papers · All 20 columns · Diagrams & Graphs · 2 Free Re-Runs · Stress-Test
            </div>
          </div>

          <div
            className={`mode-card ${mode === "quick" ? "active" : ""}`}
            onClick={() => !isProcessing && setMode("quick")}
          >
            <div className="mode-card-title">
              <span>Quick Trial</span>
              <span className="price-tag">₹0</span>
            </div>
            <div className="mode-card-desc">
              Up to 3 papers · 8 core columns · Basic synthesis preview
            </div>
          </div>
        </div>
      </div>

      <div>
        <span className="section-label">2. Proposed Research Topic / Title</span>
        <textarea
          className="textarea-input"
          rows={3}
          maxLength={300}
          placeholder="e.g., Adaptive Graph Neural Networks for Low-Resource Clinical Time-Series Forecasting"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={isProcessing}
        />
      </div>

      <div>
        <span className="section-label">
          3. Upload PDFs ({papers.length} / {maxPapers} papers)
        </span>
        <label className={`dropzone ${papers.length >= maxPapers || isProcessing ? "disabled" : ""}`}>
          <input
            type="file"
            accept="application/pdf"
            multiple
            style={{ display: "none" }}
            disabled={papers.length >= maxPapers || isProcessing}
            onChange={handleFileChange}
          />
          <div style={{ fontWeight: 600, fontSize: "0.86rem" }}>
            {papers.length >= maxPapers
              ? `Maximum ${maxPapers} papers reached`
              : "📄 Drop research PDFs here or click to browse"}
          </div>
          <div style={{ fontSize: "0.73rem", color: "#94a3b8", marginTop: "0.25rem" }}>
            Min 2 · Max {maxPapers} PDFs · Auto-trims Reference pages
          </div>
        </label>

        {papers.length > 0 && (
          <div className="paper-list" style={{ marginTop: "0.65rem" }}>
            {papers.map((p) => (
              <div key={p.id} className="paper-item">
                <div className="paper-meta">
                  <span className="paper-name" title={p.filename}>
                    {p.filename}
                  </span>
                  <span className="paper-sub">
                    ✓ {p.pages_kept}p kept
                    {p.pages_trimmed > 0 ? ` (−${p.pages_trimmed} ref pages trimmed)` : ""}
                  </span>
                </div>
                <button
                  className="btn-secondary"
                  style={{ padding: "0.2rem 0.5rem", fontSize: "0.72rem" }}
                  onClick={() => onDeletePaper(p.id)}
                  disabled={isProcessing}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <span className="section-label">Gemini API Key (Optional if set in .env)</span>
        <input
          type="password"
          className="text-input"
          placeholder="AIzaSy... (leave blank for local deterministic mode)"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          disabled={isProcessing}
        />
      </div>

      <button
        className="btn-primary"
        disabled={isProcessing || papers.length < 2 || topic.trim().length < 3}
        onClick={onRunAnalysis}
      >
        {isProcessing
          ? "⏳ Analyzing Papers..."
          : `▶ Synthesize ${papers.length} Papers (${mode === "full" ? "20 Cols" : "8 Cols"})`}
      </button>

      {progress && isProcessing && (
        <div style={{ fontSize: "0.78rem", color: "#38bdf8" }}>
          <div>{progress.message}</div>
        </div>
      )}

      {errorMsg && (
        <div
          style={{
            background: "rgba(244, 63, 94, 0.14)",
            border: "1px solid rgba(244, 63, 94, 0.4)",
            color: "#fda4af",
            padding: "0.65rem",
            borderRadius: "0.5rem",
            fontSize: "0.78rem",
          }}
        >
          ⚠ {errorMsg}
        </div>
      )}
    </aside>
  );
}
