"""
models.py — Pure dataclass models for the triage pipeline.
No Pydantic — simple, fast, zero-dep.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Ticket:
    """A single support ticket from the input CSV."""
    issue: str
    subject: str
    company: str
    raw_index: int = 0


@dataclass
class Article:
    """A single support article from the corpus."""
    id: str
    title: str
    company: str
    product_area: str
    breadcrumbs: list[str] = field(default_factory=list)
    body: str = ""
    source_url: str = ""


@dataclass
class ArticleMatch:
    """A BM25 retrieval match."""
    article: Article
    score: float


@dataclass
class EscalationDecision:
    """Result of the safety gate check."""
    should_escalate: bool
    rule_triggered: Optional[str] = None
    reason: str = "No escalation rules triggered."


@dataclass
class TriageResult:
    """Final output for a single ticket."""
    status: str                 # "replied" | "escalated"
    product_area: str
    response: str
    justification: str
    request_type: str           # "product_issue" | "feature_request" | "bug" | "invalid"
