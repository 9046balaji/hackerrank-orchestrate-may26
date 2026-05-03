"""
classifier.py — Request type and product area classification.
Deterministic, rule-based — no LLM calls.
"""

from models import Ticket, ArticleMatch
from utils import normalize_text
from config import PRODUCT_AREAS


# ── Request Type Keywords ────────────────────────────────────────────────────

BUG_KEYWORDS = [
    "not working", "broken", "error", "failing", "failed", "down",
    "bug", "stopped working", "not responding", "submissions not working",
    "all requests", "no submissions", "resume builder is down",
    "unable to", "can not able"
]

FEATURE_REQUEST_KEYWORDS = [
    "can you add", "would like to request", "please add",
    "new feature", "feature request"
]

_INVALID_SAFETY_RULES = frozenset({
    "destructive_code", "ood_celebrity", "chit_chat",
    "prompt_injection", "score_manip"
})


def classify_request_type(ticket: Ticket, safety_rule: str | None) -> str:
    """
    Classify the request type.
    Returns one of: "product_issue", "feature_request", "bug", "invalid"
    """
    # Invalid tickets based on safety rule
    if safety_rule and safety_rule in _INVALID_SAFETY_RULES:
        return "invalid"

    combined = normalize_text(f"{ticket.subject} {ticket.issue}")

    # Bug check first (more specific than feature request)
    for kw in BUG_KEYWORDS:
        if kw in combined:
            return "bug"

    # Feature request check
    for kw in FEATURE_REQUEST_KEYWORDS:
        if kw in combined:
            return "feature_request"

    # Default - most tickets are product issues
    return "product_issue"


def classify_product_area(
    company: str,
    ticket: Ticket,
    top_articles: list[ArticleMatch],
    safety_rule: str | None,
) -> str:
    """
    Classify the product area based on company taxonomy.
    Uses top retrieved articles if available, else keyword matching.
    """
    # Invalid / out-of-scope tickets
    if safety_rule and safety_rule in {"destructive_code", "ood_celebrity", "prompt_injection"}:
        return "out_of_scope"

    # If we have high-scoring articles, use the top article's product_area
    if top_articles and top_articles[0].score > 1.0:
        return top_articles[0].article.product_area

    # Keyword-based classification against company taxonomy
    combined = normalize_text(f"{ticket.subject} {ticket.issue}")

    company_areas = PRODUCT_AREAS.get(company, {})
    best_area = "general_support"
    best_score = 0

    for area, keywords in company_areas.items():
        score = 0
        for kw in keywords:
            if kw.lower() in combined:
                score += 1
        if score > best_score:
            best_score = score
            best_area = area

    return best_area
