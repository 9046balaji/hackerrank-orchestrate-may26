"""
config.py — All constants and configuration for the triage agent.
Nothing is hardcoded anywhere else.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
TICKETS_DIR = REPO_ROOT / "support_tickets"
INPUT_CSV = TICKETS_DIR / "support_tickets.csv"
OUTPUT_CSV = TICKETS_DIR / "output.csv"

# ── Model ────────────────────────────────────────────────────────────────────
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
OLLAMA_MODEL = "gemma4:e4b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MAX_RESPONSE_TOKENS = 600
TEMPERATURE = 0
MIN_RETRIEVAL_SCORE = 0.5
TOP_K_ARTICLES = 5

# ── Company Keywords (for routing when company == "None") ────────────────────
COMPANY_KEYWORDS = {
    "hackerrank": [
        "hackerrank", "hacker rank", "assessment", "test", "candidate",
        "recruiter", "mock interview", "resume builder", "certificate",
        "hackerrank.com", "coding test", "hiring", "interviewer",
        "screen share", "inactivity", "apply tab", "submissions",
        "practice", "challenges", "skillup", "codepair"
    ],
    "claude": [
        "claude", "anthropic", "bedrock", "claude.ai", "conversation",
        "api key", "console", "claude api", "prompt", "claude code",
        "lti", "crawling", "crawl", "data use", "model training",
        "anthropic's", "claude team", "workspace"
    ],
    "visa": [
        "visa", "visa card", "merchant", "dispute", "stolen card",
        "identity theft", "transaction", "issuer", "cardholder",
        "traveller", "cheque", "blocked card", "lost card",
        "visa india", "visa global", "minimum spend", "carte visa"
    ],
}

# ── Product Area Taxonomy (per company) ──────────────────────────────────────
PRODUCT_AREAS = {
    "hackerrank": {
        "screen": [
            "test", "assessment", "invite", "variant", "expiry", "candidates",
            "submissions", "apply tab", "practice", "taking the test",
            "test score", "score", "grading", "certificate", "resume builder",
            "resume", "infosec", "hiring"
        ],
        "interviews": [
            "mock interview", "inactivity", "interviewer", "screen share",
            "codepair", "zoom", "compatibility check", "interview"
        ],
        "billing": [
            "refund", "payment", "subscription", "invoice", "pause",
            "cancel", "billing", "order id", "money"
        ],
        "account": [
            "remove user", "add user", "permissions", "email change",
            "delete account", "remove interviewer", "remove employee",
            "hiring account"
        ],
    },
    "claude": {
        "conversation_management": [
            "delete chat", "rename", "share", "private", "conversation",
            "temporary chat"
        ],
        "account_access": [
            "workspace", "team", "console", "org", "access", "seat",
            "admin", "restore", "lost access"
        ],
        "prompt_design": [
            "prompt", "response length", "better answers"
        ],
        "usage_limits": [
            "context window", "tier", "rate limit", "credits", "limit"
        ],
        "api": [
            "bedrock", "aws", "regions", "amazon", "aws bedrock", "api",
            "all requests", "failing"
        ],
        "education": [
            "lti", "students", "researcher", "government", "professor",
            "college", "education"
        ],
        "data_privacy": [
            "crawl", "data use", "training data", "privacy", "opt out",
            "website crawling", "data duration", "improve the models"
        ],
        "general_support": [
            "not responding", "error", "failing", "broken", "not working",
            "stopped working", "claude code"
        ],
    },
    "visa": {
        "card_support": [
            "lost card", "stolen card", "blocked card", "replacement",
            "emergency cash", "card blocked", "carte", "urgent cash"
        ],
        "disputes_fraud": [
            "dispute", "identity theft", "unauthorized", "fraud",
            "charge dispute", "wrong product", "refund", "identity stolen"
        ],
        "travel_support": [
            "traveller", "cheque", "emergency cash", "travel",
            "travellers cheques"
        ],
        "merchant": [
            "minimum spend", "merchant", "payment acceptance",
            "merchant restriction", "seller", "10$"
        ],
    },
    "unknown": {
        "general_support": ["help", "issue", "problem"],
        "out_of_scope": ["iron man", "actor", "delete files", "weather"],
    },
}

# ── Escalation Keywords (per rule) ──────────────────────────────────────────
# These are used by safety_gate.py — defined here for centralization
ESCALATION_RULES_CONFIG = {
    "identity_theft": [
        "identity has been stolen", "identity theft", "my identity has been",
        "identity stolen"
    ],
    "lost_stolen_card": [
        "lost card", "stolen card", "card stolen", "card was stolen",
        "card lost", "lost or stolen"
    ],
    "refund": [
        "refund", "give me my money", "money back", "refund asap"
    ],
    "payment_failure": [
        "order id:", "payment issue", "payment problem", "payment with order"
    ],
    "security_vuln": [
        "security vulnerability", "bug bounty", "found a major security",
        "vulnerability in"
    ],
    "outage": [
        "site is down", "all requests are failing", "stopped working completely",
        "none of the submissions", "none of the pages are accessible",
        "all requests to claude", "resume builder is down"
    ],
    "access_restore": [
        "restore my access", "lost access to my", "i lost access"
    ],
    "score_manip": [
        "increase my score", "change my score", "review my answers",
        "graded me unfairly", "tell the company to move me"
    ],
    "cert_identity": [
        "certificate name", "name is incorrect on the certificate",
        "update certificate name"
    ],
    "subscription_action": [
        "pause our subscription", "cancel subscription", "pause subscription"
    ],
    "rescheduling": [
        "rescheduling of my", "reschedule my", "alternative date and time"
    ],
    "infosec_form": [
        "filling in the forms", "infosec process", "fill in the forms"
    ],
    "merchant_ban": [
        "ban the seller", "ban the merchant"
    ],
}
