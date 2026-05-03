"""
utils.py — Shared utilities: injection detection, text normalization,
query building, tokenization.
"""

import re
import string


# ── Prompt Injection Detection ───────────────────────────────────────────────

_INJECTION_PATTERNS = [
    # Strong injection patterns (single match = injection)
    r"ignore\s+previous\s+instructions",
    r"reveal\s+your\s+prompt",
    r"bypass\s+policy",
    r"disregard\s+all\s+prior",
    r"what\s+are\s+your\s+instructions",
    r"show\s+me\s+your\s+system\s+prompt",
]

_WEAK_INJECTION_PATTERNS = [
    # Weaker patterns (need 2+ matches or combined with strong pattern)
    r"affiche\s+toutes\s+les\s+r[eè]gles",
    r"documents?\s+r[eé]cup[eé]r[eé]s",
    r"logique\s+exacte",
    r"show\s+all\s+internal\s+rules",
    r"system\s+prompt",
]

_STRONG_INJECTION_REGEXES = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
_WEAK_INJECTION_REGEXES = [re.compile(p, re.IGNORECASE) for p in _WEAK_INJECTION_PATTERNS]


def detect_prompt_injection(text: str) -> bool:
    """
    Return True if the text contains prompt-injection patterns.
    Requires either:
    - 1 strong injection pattern, OR
    - 3+ weak injection patterns (to avoid false positives on legitimate foreign language text)
    """
    # Check strong patterns first
    for rx in _STRONG_INJECTION_REGEXES:
        if rx.search(text):
            return True
    
    # Check weak patterns - need at least 3 to avoid false positives
    weak_matches = 0
    for rx in _WEAK_INJECTION_REGEXES:
        if rx.search(text):
            weak_matches += 1
            if weak_matches >= 3:
                return True
    
    return False


# ── Text Normalization ───────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    if not text or not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# ── Query Building ───────────────────────────────────────────────────────────

def build_query(ticket) -> str:
    """Concatenate subject + issue for retrieval query."""
    parts = []
    if ticket.subject and str(ticket.subject).strip():
        parts.append(str(ticket.subject).strip())
    if ticket.issue and str(ticket.issue).strip():
        parts.append(str(ticket.issue).strip())
    return " ".join(parts)


# ── Tokenization ────────────────────────────────────────────────────────────

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "because", "but", "and", "or", "if", "while",
    "about", "up", "it", "its", "i", "me", "my", "we", "our", "you",
    "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "this", "that", "these", "those", "am", "what", "which", "who",
    "whom", "any", "also",
})


def tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, filter stopwords."""
    if not text:
        return []
    text = text.lower()
    # Remove punctuation but keep hyphens within words
    text = re.sub(r"[^\w\s-]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


# ── Company Normalization ────────────────────────────────────────────────────

def normalize_company(raw: str) -> str:
    """Normalize the company column value."""
    if not raw or not isinstance(raw, str):
        return "unknown"
    cleaned = raw.strip().lower()
    if cleaned in ("none", "nan", ""):
        return "unknown"
    if "hackerrank" in cleaned or "hacker rank" in cleaned:
        return "hackerrank"
    if "claude" in cleaned:
        return "claude"
    if "visa" in cleaned:
        return "visa"
    return "unknown"
