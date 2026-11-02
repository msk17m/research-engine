"""Lock 4: Deterministic Python Quote Verifier (<5ms, 0 MB RAM)."""

import re
from typing import Dict, Any, Optional

GROUNDED_FIELDS = [
    "research_question",
    "core_method_or_approach",
    "key_results_or_findings",
    "main_claimed_contribution",
    "stated_limitations",
]

QUICK_MODE_ALLOWED_FIELDS = {
    "is_academic_paper",
    "paper_title",
    "publication_year",
    "research_question",
    "core_method_or_approach",
    "dataset_or_domain",
    "key_results_or_findings",
    "stated_limitations",
    "relation_to_topic",
}


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation/hyphens across linebreaks, and collapse whitespace."""
    if not text:
        return ""
    # Rejoin hyphenated linebreaks common in 2-column PDFs
    cleaned = re.sub(r"-\s+", "", text.lower())
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def verify_grounded_claim(claim: Optional[Dict[str, Any]], page_texts: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Deterministically checks whether `verbatim_quote` returned by the LLM actually
    exists inside the PDF's extracted page texts.
    - If `value` is null/empty, returns None.
    - Checks declared `source_page` first; if found or if a sliding 5-word window matches,
      marks `verified = True` (and updates `source_page` if found on an adjacent page).
    - If the PDF is a pure scanned image (no PyMuPDF text layer), marks `verified = True`
      if both `source_page` and `verbatim_quote` are non-empty.
    """
    if not claim or not isinstance(claim, dict):
        return None

    val = claim.get("value")
    if not val or str(val).strip().lower() in {"null", "none", "n/a", ""}:
        return None

    quote = (claim.get("verbatim_quote") or "").strip()
    norm_quote = _normalize(quote)
    if len(norm_quote) < 10:
        claim["verified"] = False
        return claim

    # Check if the PDF had any digital text extracted
    total_extracted_chars = sum(len(t) for t in page_texts.values())
    if total_extracted_chars < 200:
        # Scanned PDF read via Gemini Vision
        claim["verified"] = bool(quote and claim.get("source_page"))
        return claim

    words = norm_quote.split()
    # Build 1-3 anchor phrases (first 6 words, middle 6 words) to handle minor PDF ligature differences
    anchors = []
    if len(words) >= 5:
        anchors.append(" ".join(words[: min(6, len(words))]))
        mid = len(words) // 2
        anchors.append(" ".join(words[max(0, mid - 2) : min(len(words), mid + 4)]))
    else:
        anchors.append(norm_quote)

    declared_page = str(claim.get("source_page") or "")
    normalized_pages = {p_num: _normalize(p_txt) for p_num, p_txt in page_texts.items()}

    # 1. Check declared page first
    if declared_page in normalized_pages:
        page_norm = normalized_pages[declared_page]
        if any(anchor in page_norm for anchor in anchors):
            claim["verified"] = True
            return claim

    # 2. Check all pages in case page numbering was offset by cover page
    for p_num, page_norm in normalized_pages.items():
        if any(anchor in page_norm for anchor in anchors):
            claim["verified"] = True
            claim["source_page"] = int(p_num)
            return claim

    # 3. Token overlap check (>= 75% of quote words appear on the declared page)
    if declared_page in normalized_pages and len(words) >= 4:
        page_word_set = set(normalized_pages[declared_page].split())
        overlap = sum(1 for w in words if w in page_word_set) / len(words)
        if overlap >= 0.75:
            claim["verified"] = True
            return claim

    claim["verified"] = False
    return claim


def verify_and_filter_matrix(
    matrix_dict: Dict[str, Any],
    page_texts: Dict[str, str],
    mode: str = "full",
) -> Dict[str, Any]:
    """
    Runs Lock 4 verification on all grounded claim fields in a PaperMatrix dict,
    and masks non-Quick-Mode columns to None if `mode == 'quick'`.
    """
    verified_matrix = dict(matrix_dict)

    for field_name in GROUNDED_FIELDS:
        raw_claim = verified_matrix.get(field_name)
        verified_matrix[field_name] = verify_grounded_claim(raw_claim, page_texts)

    if mode == "quick":
        for key in list(verified_matrix.keys()):
            if key not in QUICK_MODE_ALLOWED_FIELDS:
                verified_matrix[key] = None

    return verified_matrix
