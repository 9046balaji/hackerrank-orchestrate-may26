"""
router.py — Determines which company a support ticket belongs to.
Uses explicit company column first, then keyword scoring.
"""

from models import Ticket
from utils import normalize_text, normalize_company
from config import COMPANY_KEYWORDS


def route_company(ticket: Ticket) -> str:
    """
    Determine the company for a ticket.
    Returns: "hackerrank" | "claude" | "visa" | "unknown"

    Priority order:
    1. If ticket.company (normalized) is a known company → use it
    2. Else run keyword scoring over subject+issue text
    3. Return company with highest keyword score
    4. If all scores == 0 → return "unknown"
    """
    # Step 1: Use explicit company if valid
    normalized = normalize_company(ticket.company)
    if normalized in ("hackerrank", "claude", "visa"):
        return normalized

    # Step 2: Keyword scoring
    combined = normalize_text(f"{ticket.subject} {ticket.issue}")

    scores = {}
    for company, keywords in COMPANY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in combined:
                # Longer keywords get higher scores (more specific)
                score += len(kw.split())
        scores[company] = score

    # Step 3: Return highest scorer
    best_company = max(scores, key=scores.get)
    if scores[best_company] > 0:
        return best_company

    # Step 4: No match
    return "unknown"
