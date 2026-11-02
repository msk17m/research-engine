"""Database ORM models (2-table minimalist design) and Pydantic schemas for the 20-column Study Matrix."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


# =====================================================================
# SQLAlchemy ORM Models (Minimalist 2-Table Architecture)
# =====================================================================

class SessionModel(Base):
    """Stores research session state, synthesis, hypothesis, and stress-test outputs."""

    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True, index=True)
    topic = Column(String(300), nullable=False)
    mode = Column(String(16), nullable=False, default="full")  # "quick" | "full"
    status = Column(String(32), nullable=False, default="pending")  # pending | processing | done | error
    error_message = Column(Text, nullable=True)
    reruns_remaining = Column(Integer, nullable=False, default=2)

    # Session-level synthesis & hypothesis outputs (1-to-1 with session)
    clusters_json = Column(Text, nullable=True)
    disagreements_json = Column(Text, nullable=True)
    gaps_json = Column(Text, nullable=True)
    hypothesis_json = Column(Text, nullable=True)
    stress_test_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    papers = relationship(
        "PaperModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PaperModel.upload_order",
    )


class PaperModel(Base):
    """Stores individual uploaded papers, pre-filtering stats, page texts, and 20-col matrix."""

    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    trimmed_pdf_path = Column(String(512), nullable=True)
    pages_kept = Column(Integer, nullable=False, default=0)
    pages_trimmed = Column(Integer, nullable=False, default=0)
    page_texts_json = Column(Text, nullable=True)  # {page_num: text} for Lock 4 verification
    matrix_json = Column(Text, nullable=True)      # Serialized 20-column PaperMatrix
    upload_order = Column(Integer, nullable=False, default=1)

    session = relationship("SessionModel", back_populates="papers")


# =====================================================================
# Lock 2 & Lock 3: Strict Nullable Pydantic Schemas (20-Column Matrix)
# =====================================================================

class GroundedClaim(BaseModel):
    """Lock 3: Mandatory Evidence Tuple for Click-to-Verify Grounding."""

    value: Optional[str] = Field(
        default=None,
        description="The extracted claim or finding. Must be null if not explicitly in the paper.",
    )
    source_page: Optional[int] = Field(
        default=None,
        description="1-based page number where this claim appears in the PDF.",
    )
    verbatim_quote: Optional[str] = Field(
        default=None,
        description="Exact word-for-word sentence or excerpt from the paper supporting this value.",
    )
    verified: Optional[bool] = Field(
        default=None,
        description="Populated post-extraction by Lock 4 Python Deterministic Quote Verifier.",
    )


class MethodologicalRigor(BaseModel):
    """Risk-of-bias and methodological soundness evaluation."""

    risk_level: Optional[Literal["Low", "Medium", "High"]] = Field(
        default=None,
        description="Risk-of-bias concern level based on sample validity, splits, and significance testing.",
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Grounded explanation covering sample size validity, data splits, statistical tests, and compute realism.",
    )


class PaperMatrix(BaseModel):
    """Comprehensive 20-Column Study Matrix Schema (Zero Hallucination)."""

    is_academic_paper: bool = Field(
        default=True,
        description="True if the document is a genuine academic/scientific paper or technical report; False otherwise.",
    )
    # 1. Paper Title
    paper_title: Optional[str] = Field(default=None, description="Official title of the paper, or null if not found.")
    # 2. Publication Year
    publication_year: Optional[int] = Field(default=None, description="4-digit year of publication, or null if not stated.")
    # 3. Study Type
    study_type: Optional[str] = Field(
        default=None,
        description="Empirical, Theoretical, Benchmark, Case Study, Survey, or Meta-Analysis.",
    )
    # 4. Research Question (Grounded Tuple)
    research_question: Optional[GroundedClaim] = Field(
        default=None,
        description="Core research question or problem statement with page number and verbatim quote.",
    )
    # 5. Core Method or Approach (Grounded Tuple)
    core_method_or_approach: Optional[GroundedClaim] = Field(
        default=None,
        description="Primary technical methodology, algorithm, or experimental design with page and verbatim quote.",
    )
    # 6. Theoretical Framework
    theoretical_framework: Optional[str] = Field(
        default=None,
        description="Underlying mathematical, physical, or conceptual theory (or null if not stated).",
    )
    # 7. Visual Architecture Summary
    visual_architecture_summary: Optional[str] = Field(
        default=None,
        description="Summary of system pipeline, flowchart, or architecture schematic (e.g., Figure 1), or null if no diagram.",
    )
    # 8. Dataset or Domain
    dataset_or_domain: Optional[str] = Field(
        default=None,
        description="Datasets used, sample sizes (N), and application domain, or null if not mentioned.",
    )
    # 9. Evaluation Metrics
    evaluation_metrics: Optional[str] = Field(
        default=None,
        description="Quantitative metrics and exact numerical scores reported in tables or text, or null.",
    )
    # 10. Baselines Compared
    baselines_compared: Optional[str] = Field(
        default=None,
        description="Prior SOTA models or baseline methods compared against, or null if none.",
    )
    # 11. Key Results or Findings (Grounded Tuple)
    key_results_or_findings: Optional[GroundedClaim] = Field(
        default=None,
        description="Main empirical findings and quantitative outcomes with page number and verbatim quote.",
    )
    # 12. Key Graph Trends
    key_graph_trends: Optional[str] = Field(
        default=None,
        description="Scaling behavior, Pareto frontiers, or ablation trajectories read from benchmark plots/charts, or null.",
    )
    # 13. Main Claimed Contribution (Grounded Tuple)
    main_claimed_contribution: Optional[GroundedClaim] = Field(
        default=None,
        description="What the authors explicitly claim as their primary novel contribution, with page and verbatim quote.",
    )
    # 14. Key Assumptions
    key_assumptions: Optional[str] = Field(
        default=None,
        description="Boundary conditions and assumptions required for the method to hold, or null if not stated.",
    )
    # 15. Negative Results or Failures
    negative_results_or_failures: Optional[str] = Field(
        default=None,
        description="Scenarios, edge cases, or ablations where the method degrades or fails, or null if not reported.",
    )
    # 16. Stated Limitations (Grounded Tuple)
    stated_limitations: Optional[GroundedClaim] = Field(
        default=None,
        description="Limitations explicitly acknowledged by the authors with page number and verbatim quote, or null.",
    )
    # 17. Methodological Rigor Score
    methodological_rigor_score: Optional[MethodologicalRigor] = Field(
        default=None,
        description="Risk-of-bias rating (Low/Medium/High) and soundness audit rationale.",
    )
    # 18. Author Future Work
    author_future_work: Optional[str] = Field(
        default=None,
        description="Next steps and open directions explicitly recommended by the authors, or null.",
    )
    # 19. Artifact URLs
    artifact_urls: Optional[str] = Field(
        default=None,
        description="GitHub, HuggingFace, Zenodo, or dataset URLs explicitly printed in the paper, or null.",
    )
    # 20. Relation to Topic
    relation_to_topic: Optional[str] = Field(
        default=None,
        description="How this paper relates to the user's proposed research topic based strictly on the paper's content.",
    )


# =====================================================================
# Cross-Synthesis, Hypothesis & Stress-Test Schemas
# =====================================================================

class Cluster(BaseModel):
    cluster_name: str = Field(description="Concise descriptive name for this cluster.")
    shared_theme: str = Field(description="Shared method, theoretical framework, or domain angle.")
    paper_titles: List[str] = Field(description="List of paper titles belonging to this cluster.")
    description: str = Field(description="Detailed synthesis of how these papers align.")


class Disagreement(BaseModel):
    paper_a: str = Field(description="Title of the first paper in conflict.")
    paper_b: str = Field(description="Title of the second paper (or group of papers) in conflict.")
    dimension: str = Field(description="Dimension of conflict: Methodology, Empirical Findings, Assumptions, or Interpretation.")
    conflict_description: str = Field(description="Precise explanation of the contradiction based on the extracted matrices.")


class Gap(BaseModel):
    gap_title: str = Field(description="Short title of the unanswered research gap.")
    gap_description: str = Field(description="Detailed formulation of the question no uploaded paper answers.")
    supporting_evidence: str = Field(description="Which papers' limitations, assumptions, or future work point to this gap.")
    direction_for_hypothesis: str = Field(description="How this gap directly informs the user's proposed research topic.")


class CrossSynthesis(BaseModel):
    clusters: List[Cluster]
    disagreements: List[Disagreement]
    gaps: List[Gap]


class HypothesisOutput(BaseModel):
    tentative_hypothesis: str = Field(description="Testable, falsifiable research hypothesis grounded in the identified gaps.")
    rationale: str = Field(description="Evidence-backed justification linking specific paper matrices, conflicts, and gaps.")
    research_objectives: List[str] = Field(description="3 to 5 specific, measurable, and actionable research objectives.")


class PitfallItem(BaseModel):
    title: str = Field(description="Name of the confounding variable, methodological flaw, or invalidation risk.")
    severity: Literal["Critical", "High", "Moderate"] = Field(description="Severity of the threat to validity.")
    critique: str = Field(description="Harsh peer-reviewer explanation of how this could invalidate the proposed hypothesis.")
    mitigation_strategy: str = Field(description="Concrete experimental control or design adjustment to defend against this critique.")


class DevilAdvocateCritique(BaseModel):
    overall_peer_review_verdict: str = Field(description="Executive summary of the hypothesis's vulnerability from a skeptical reviewer's lens.")
    confounding_pitfalls: List[PitfallItem] = Field(description="Top 3 confounding variables or experimental pitfalls.")
    falsification_test: str = Field(description="The single decisive experiment that would falsify or prove the hypothesis.")
