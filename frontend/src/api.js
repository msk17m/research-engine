"""Frontend API client helper module."""

export const MATRIX_SCHEMA_COLUMNS = [
  { key: "study_type", label: "3. Study Type", category: "id" },
  { key: "research_question", label: "4. Research Question", category: "id", grounded: true },
  { key: "core_method_or_approach", label: "5. Core Method / Approach", category: "method", grounded: true },
  { key: "theoretical_framework", label: "6. Theoretical Framework", category: "method" },
  { key: "visual_architecture_summary", label: "7. Visual Architecture (Diagrams)", category: "method" },
  { key: "dataset_or_domain", label: "8. Dataset / Domain", category: "metrics" },
  { key: "evaluation_metrics", label: "9. Evaluation Metrics", category: "metrics" },
  { key: "baselines_compared", label: "10. Baselines Compared", category: "metrics" },
  { key: "key_results_or_findings", label: "11. Key Results / Findings", category: "metrics", grounded: true },
  { key: "key_graph_trends", label: "12. Key Graph Trends (Plots)", category: "metrics" },
  { key: "main_claimed_contribution", label: "13. Main Claimed Contribution", category: "id", grounded: true },
  { key: "key_assumptions", label: "14. Key Assumptions", category: "rigor" },
  { key: "negative_results_or_failures", label: "15. Negative Results / Failures", category: "rigor" },
  { key: "stated_limitations", label: "16. Stated Limitations", category: "rigor", grounded: true },
  { key: "methodological_rigor_score", label: "17. Methodological Rigor Score", category: "rigor" },
  { key: "author_future_work", label: "18. Author Future Work", category: "rigor" },
  { key: "artifact_urls", label: "19. Artifact URLs (Code/Data)", category: "id" },
  { key: "relation_to_topic", label: "20. Relation to My Topic", category: "id" },
];
