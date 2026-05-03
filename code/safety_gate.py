"""
safety_gate.py — Escalation rules and invalid ticket detection.
Runs BEFORE any Claude API call to intercept risky tickets.
"""

from models import Ticket, EscalationDecision
from utils import detect_prompt_injection, normalize_text
from config import ESCALATION_RULES_CONFIG


# ── Invalid-triggering rules ────────────────────────────────────────────────
_INVALID_RULES = frozenset({
    "destructive_code", "ood_celebrity", "chit_chat",
    "prompt_injection", "score_manip"
})

# ── Hardcoded keyword sets not in config ────────────────────────────────────
_DESTRUCTIVE_KEYWORDS = [
    "delete all files", "rm -rf", "drop table", "format c:"
]

_OOD_KEYWORDS = [
    "iron man", "actor in", "what is the weather", "basketball player"
]

_CHIT_CHAT_KEYWORDS = [
    "thank you for helping me", "thanks for helping"
]


def check_safety_gate(ticket: Ticket) -> EscalationDecision:
    """
    Apply escalation rules in strict order (first match wins).
    Returns EscalationDecision with should_escalate, rule_triggered, reason.
    """
    combined = normalize_text(f"{ticket.subject} {ticket.issue}")

    # ── Rule 0: Check for legitimate blocked/lost card first ────────────────
    # This prevents false positives on foreign language card issues
    card_keywords = ["carte", "card", "bloquée", "blocked", "lost", "stolen", "perdu", "volé"]
    has_card_issue = any(kw in combined for kw in card_keywords)
    
    # ── Rule 1: Prompt Injection (but not if it's a card issue) ─────────────
    if detect_prompt_injection(combined) and not has_card_issue:
        return EscalationDecision(
            should_escalate=True,
            rule_triggered="prompt_injection",
            reason="Prompt injection detected in ticket text."
        )

    # ── Rule 2: Destructive Code ─────────────────────────────────────────
    for kw in _DESTRUCTIVE_KEYWORDS:
        if kw in combined:
            return EscalationDecision(
                should_escalate=True,
                rule_triggered="destructive_code",
                reason=f"Destructive code request detected: '{kw}'"
            )

    # ── Rule 3: Out-of-Domain / Celebrity ────────────────────────────────
    for kw in _OOD_KEYWORDS:
        if kw in combined:
            return EscalationDecision(
                should_escalate=True,
                rule_triggered="ood_celebrity",
                reason=f"Out-of-domain request detected: '{kw}'"
            )

    # ── Rule 4: Chit-Chat ────────────────────────────────────────────────
    for kw in _CHIT_CHAT_KEYWORDS:
        if kw in combined:
            return EscalationDecision(
                should_escalate=True,
                rule_triggered="chit_chat",
                reason="Chit-chat / thank-you message with no support question."
            )

    # ── Rules 5–17: Config-driven escalation rules ───────────────────────
    # These are applied in the exact order defined in config
    rule_order = [
        "identity_theft",
        "refund",
        "payment_failure",
        "security_vuln",
        "outage",
        "access_restore",
        "score_manip",
        "cert_identity",
        "subscription_action",
        "rescheduling",
        "infosec_form",
        "merchant_ban",
    ]

    rule_reasons = {
        "identity_theft": "Identity theft reported — escalating to fraud team.",
        "lost_stolen_card": "Lost or stolen card reported — escalating for immediate action.",
        "refund": "Refund request — requires billing team action.",
        "payment_failure": "Payment failure reported — requires billing investigation.",
        "security_vuln": "Security vulnerability reported — escalating to security team.",
        "outage": "Service outage reported — escalating to engineering.",
        "access_restore": "Access restoration request — requires admin action.",
        "score_manip": "Score/grade manipulation request — cannot be fulfilled.",
        "cert_identity": "Certificate name correction — requires identity verification.",
        "subscription_action": "Subscription change request — requires account management.",
        "rescheduling": "Assessment rescheduling — requires recruiter action.",
        "infosec_form": "InfoSec form filling request — outside support scope.",
        "merchant_ban": "Merchant ban request — requires escalation to disputes team.",
    }

    for rule_name in rule_order:
        keywords = ESCALATION_RULES_CONFIG.get(rule_name, [])
        for kw in keywords:
            if kw.lower() in combined:
                return EscalationDecision(
                    should_escalate=True,
                    rule_triggered=rule_name,
                    reason=rule_reasons.get(rule_name, f"Escalation rule '{rule_name}' triggered.")
                )

    # ── Rule 18: Vague + No Company ──────────────────────────────────────
    issue_text = normalize_text(ticket.issue)
    company_norm = normalize_text(ticket.company)
    is_unknown_company = company_norm in ("none", "nan", "", "unknown")

    if len(issue_text.split()) < 6 and is_unknown_company:
        return EscalationDecision(
            should_escalate=True,
            rule_triggered="vague_no_company",
            reason="Ticket is too vague and has no identified company."
        )

    # ── No rule fired ────────────────────────────────────────────────────
    return EscalationDecision(
        should_escalate=False,
        rule_triggered=None,
        reason="No escalation rules triggered."
    )


def is_invalid_ticket(ticket: Ticket) -> bool:
    """
    Returns True if the ticket's safety-gate rule implies it's invalid
    (destructive_code, ood_celebrity, chit_chat, prompt_injection,
     score_manip, vague_no_company).
    """
    decision = check_safety_gate(ticket)
    if decision.rule_triggered and decision.rule_triggered in _INVALID_RULES:
        return True
    return False
