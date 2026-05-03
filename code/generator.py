"""
generator.py — Response generation using Ollama API (for replied tickets)
and deterministic templates (for escalated/invalid tickets).
"""

import os
import time
import json
from openai import OpenAI

from models import Ticket, ArticleMatch
from config import USE_OLLAMA, OLLAMA_MODEL, OLLAMA_BASE_URL, MAX_RESPONSE_TOKENS, TEMPERATURE


# ── OpenAI API Client (lazy init) ───────────────────────────────────────────
_client = None


def _get_client():
    """Lazy-initialize the OpenAI client pointing to Ollama."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama", # required but ignored
        )
    return _client


# ── System Prompt Template ──────────────────────────────────────────────────
REPLY_SYSTEM_PROMPT = """You are a support agent for {company}. Answer the user's question using ONLY the support articles below. Do NOT invent phone numbers, URLs, policies, or steps not in the articles. Be concise and actionable.

ARTICLES:
{article_context}

You must respond in valid JSON format with exactly two keys:
1. "response": The user-facing answer grounded in the support articles.
2. "justification": Concise explanation of why this response was given.

Example format:
{{
  "response": "Here is the information you requested...",
  "justification": "I provided the steps from the article regarding..."
}}
"""


# ── Escalation Templates ────────────────────────────────────────────────────
ESCALATION_TEMPLATES = {
    "identity_theft": (
        "Your report of identity theft has been escalated to our fraud and security team. "
        "Please contact your bank and card issuers immediately to report all compromised accounts. "
        "File a police report and alert credit bureaus. A specialist will follow up with you shortly.",
        "Identity theft is a high-risk, time-sensitive issue requiring immediate human intervention "
        "and coordination with financial institutions and law enforcement."
    ),
    "lost_stolen_card": (
        "Your report of a lost or stolen card has been escalated to our card support team. "
        "Please call Visa's Global Customer Assistance Service at +1 303 967 1090 (available 24/7) "
        "to block your card immediately and arrange a replacement.",
        "Lost/stolen card reports require immediate action to prevent unauthorized transactions."
    ),
    "refund": (
        "Your refund request has been escalated to our billing team for review. "
        "A specialist will review your case and contact you with next steps.",
        "Refund requests require billing team review and cannot be processed through automated support."
    ),
    "payment_failure": (
        "Your payment issue has been escalated to our billing team. "
        "Please provide your order ID and payment details when a specialist contacts you.",
        "Payment failures require billing team investigation with access to payment systems."
    ),
    "security_vuln": (
        "Thank you for reporting this security concern. Your report has been escalated to our "
        "security team for investigation. If this is a vulnerability disclosure, please follow "
        "responsible disclosure practices and avoid sharing details publicly.",
        "Security vulnerability reports require review by the security team and follow responsible disclosure protocols."
    ),
    "outage": (
        "We're aware of the service disruption you're experiencing. Your report has been escalated "
        "to our engineering team. We are investigating and will provide updates as they become available.",
        "Service outage reports are escalated to engineering for investigation and resolution."
    ),
    "score_manip": (
        "We are unable to modify test scores or influence hiring decisions. "
        "Test results are evaluated by the hiring company, and HackerRank does not intervene in their assessment process. "
        "If you believe there was a technical issue during your test, please provide specific details.",
        "Score manipulation requests cannot be fulfilled. Test evaluation is the hiring company's responsibility."
    ),
    "subscription_action": (
        "Your subscription change request has been escalated to our account management team. "
        "A specialist will contact you to process your request.",
        "Subscription changes (pause, cancel, modify) require account management team action."
    ),
    "cert_identity": (
        "Your certificate name correction request has been escalated to our support team. "
        "To update the name on your certificate, you will need to provide proof of identity. "
        "A specialist will contact you with the verification process.",
        "Certificate name changes require identity verification and cannot be processed automatically."
    ),
    "rescheduling": (
        "Assessment rescheduling requests must be handled by the hiring company that sent you the assessment. "
        "Please contact the recruiter or HR representative from the company directly to request a new assessment date.",
        "HackerRank cannot reschedule assessments — this is controlled by the hiring company's recruiter."
    ),
    "infosec_form": (
        "Your request to have HackerRank assist with your company's InfoSec process has been noted. "
        "This falls outside our standard support scope. Please contact your Customer Success Manager "
        "or our sales team for assistance with security questionnaires and compliance documentation.",
        "InfoSec form filling is outside standard support scope and requires CSM or sales team engagement."
    ),
    "merchant_ban": (
        "Your request to take action against the merchant has been escalated. "
        "Please contact your card-issuing bank to initiate a formal dispute. "
        "Your bank (not Visa directly) handles merchant disputes on your behalf.",
        "Merchant bans require a formal dispute process through the card-issuing bank."
    ),
    "access_restore": (
        "Your access restoration request has been escalated to the appropriate team. "
        "Please note that workspace access is managed by your organization's admin. "
        "Contact your IT admin or workspace owner to request re-provisioning of your seat.",
        "Access restoration requires admin-level action and cannot be processed through automated support."
    ),
}


# ── Invalid Ticket Templates ────────────────────────────────────────────────
INVALID_TEMPLATES = {
    "destructive_code": (
        "I'm unable to assist with requests to delete files or execute destructive commands. "
        "This falls outside the scope of support I can provide.",
        "Request involves destructive code execution — flagged as invalid."
    ),
    "ood_celebrity": (
        "I'm sorry, this question is outside the scope of my capabilities as a support agent. "
        "I can only assist with support-related inquiries.",
        "Out-of-domain request (not related to any supported product)."
    ),
    "prompt_injection": (
        "I'm unable to process this request. I can only assist with legitimate support inquiries "
        "related to our products and services.",
        "Prompt injection attempt detected — request flagged as invalid."
    ),
    "chit_chat": (
        "Happy to help! If you have any support questions in the future, feel free to reach out.",
        "Chit-chat / thank-you message with no actionable support question."
    ),
    "vague_no_company": (
        "Your issue has been escalated to our support team. Could you please provide more details "
        "about what you're experiencing and which product or service this relates to?",
        "Ticket is too vague to classify — no company identified and insufficient detail."
    ),
    "score_manip": (
        "We are unable to modify test scores or influence hiring decisions. "
        "Test results are evaluated by the hiring company, and HackerRank does not intervene in their assessment process.",
        "Score manipulation request — cannot be fulfilled."
    ),
}


# ── API Call with Retry ─────────────────────────────────────────────────────

def call_ollama_with_retry(messages, system, max_retries=3):
    """
    Call Ollama API with exponential backoff.
    Always uses temperature=0 and JSON format.
    """
    client = _get_client()

    # Prepend system prompt to messages
    full_messages = [{"role": "system", "content": system}] + messages

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=full_messages,
                max_tokens=MAX_RESPONSE_TOKENS,
                temperature=TEMPERATURE,
                response_format={"type": "json_object"}
            )
            return response

        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  API error: {e}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


# ── Article Formatting ──────────────────────────────────────────────────────

def format_articles(articles: list[ArticleMatch]) -> str:
    """Format top articles as numbered sections for the prompt."""
    sections = []
    for i, match in enumerate(articles, 1):
        art = match.article
        body_truncated = art.body[:1500]
        if len(art.body) > 1500:
            body_truncated += "\n[...truncated...]"

        section = f"--- Article {i} ---\nTitle: {art.title}\nProduct Area: {art.product_area}\n\n{body_truncated}"
        sections.append(section)

    return "\n\n".join(sections)


# ── Response Generation Functions ────────────────────────────────────────────

def generate_reply_response(ticket: Ticket, articles: list[ArticleMatch]) -> tuple[str, str]:
    """
    Generate a corpus-grounded reply using Ollama API with JSON output.
    If USE_OLLAMA is False, uses deterministic fallback.
    Returns (response, justification).
    """
    # Deterministic fallback when Ollama is not available
    if not USE_OLLAMA:
        if not articles:
            return (
                "We couldn't find relevant documentation for your issue. "
                "Your query has been escalated to our support team.",
                "No articles retrieved — deterministic fallback."
            )
        
        # Use the top article's content - extract meaningful text
        top_article = articles[0].article
        body_text = top_article.body.strip()
        
        # Extract first 500 chars of meaningful content
        if len(body_text) > 500:
            body_excerpt = body_text[:500].rsplit(' ', 1)[0] + "..."
        else:
            body_excerpt = body_text
        
        response = (
            f"Based on our support documentation:\n\n"
            f"{body_excerpt}\n\n"
            f"For complete details, please refer to our article: {top_article.title}"
        )
        justification = f"Deterministic response using top article '{top_article.title}' (score: {articles[0].score:.2f})"
        return (response, justification)

    # Ollama API path
    article_context = format_articles(articles)
    company_name = ticket.company.title() if ticket.company else "Support"

    system = REPLY_SYSTEM_PROMPT.format(
        company=company_name,
        article_context=article_context
    )

    messages = [
        {
            "role": "user",
            "content": f"Subject: {ticket.subject}\n\nIssue: {ticket.issue}"
        }
    ]

    try:
        response = call_ollama_with_retry(
            messages=messages,
            system=system,
        )

        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
            return (
                parsed.get("response", "Please contact our support team for further assistance."),
                parsed.get("justification", "Generated from corpus.")
            )
        except json.JSONDecodeError:
            # Fallback: use the raw content as response if JSON parsing fails
            if content and len(content.strip()) > 10:
                return (
                    content,
                    "Raw model output (JSON parse failed)."
                )
            else:
                # If content is too short or empty, use article fallback
                if articles:
                    top_article = articles[0].article
                    body_excerpt = top_article.body[:400].rsplit(' ', 1)[0] + "..."
                    return (
                        f"Based on our support documentation:\n\n{body_excerpt}\n\nFor complete details, please refer to: {top_article.title}",
                        f"JSON parse failed, using article fallback (score: {articles[0].score:.2f})"
                    )
                return (
                    "Please contact our support team for further assistance.",
                    "Failed to parse JSON response and no articles available."
                )

    except Exception as e:
        print(f"  WARNING: Ollama API call failed: {e}")
        # Use article fallback on API failure
        if articles:
            top_article = articles[0].article
            body_excerpt = top_article.body[:400].rsplit(' ', 1)[0] + "..."
            return (
                f"Based on our support documentation:\n\n{body_excerpt}\n\nFor complete details, please refer to: {top_article.title}",
                f"API call failed, using article fallback: {str(e)[:100]}"
            )
        return (
            "We encountered an issue generating a response. Your query has been noted "
            "and a support specialist will follow up.",
            f"API call failed: {str(e)[:100]}. No articles available for fallback."
        )


def generate_escalation_response(
    ticket: Ticket, reason: str, rule: str
) -> tuple[str, str]:
    """
    Generate an escalation response using templates (no API call).
    Returns (response, justification).
    """
    # Check templates first
    if rule in ESCALATION_TEMPLATES:
        return ESCALATION_TEMPLATES[rule]

    # Generic escalation fallback
    return (
        "Your issue has been escalated to our support team for review. "
        "A specialist will contact you shortly to assist with your request.",
        f"Escalation triggered by rule: {rule}. {reason}"
    )


def generate_invalid_response(
    ticket: Ticket, rule: str
) -> tuple[str, str]:
    """
    Generate a response for invalid tickets using templates (no API call).
    Returns (response, justification).
    """
    if rule in INVALID_TEMPLATES:
        return INVALID_TEMPLATES[rule]

    # Generic invalid fallback
    return (
        "I'm unable to assist with this request as it falls outside the scope of support.",
        f"Invalid ticket detected by rule: {rule}."
    )

