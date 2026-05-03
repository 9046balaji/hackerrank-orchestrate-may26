"""
main.py — Multi-Domain Support Triage Agent
Entry point: reads support_tickets.csv, processes each ticket through the
triage pipeline, writes output.csv.
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Load environment variables FIRST, before importing config
load_dotenv()

from models import Ticket
from config import INPUT_CSV, OUTPUT_CSV, MIN_RETRIEVAL_SCORE, USE_OLLAMA
from corpus_loader import load_corpus
from router import route_company
from retriever import retrieve
from safety_gate import check_safety_gate, is_invalid_ticket
from classifier import classify_request_type, classify_product_area
from generator import (
    generate_reply_response,
    generate_escalation_response,
    generate_invalid_response,
)


def process_ticket(ticket: Ticket, corpus: dict) -> dict:
    """
    Process a single ticket through the full triage pipeline.
    Returns a dict with all output columns.
    """
    # Step 1: Route to company
    company = route_company(ticket)

    # Step 2: Retrieve relevant articles
    articles = retrieve(ticket, company, corpus, top_k=5)
    max_score = articles[0].score if articles else 0.0

    # Step 3: Safety gate check
    escalation = check_safety_gate(ticket)
    invalid = is_invalid_ticket(ticket)

    # Step 4: Get the rule that fired (if any)
    rule = escalation.rule_triggered

    # Step 5: Classify request type and product area
    request_type = classify_request_type(ticket, rule)
    product_area = classify_product_area(company, ticket, articles, rule)

    # Step 6: Decision logic (strict order)
    if invalid:
        # a. Invalid ticket
        if rule in ("ood_celebrity", "chit_chat"):
            status = "replied"
        else:
            status = "escalated"
        response, justification = generate_invalid_response(ticket, rule)
        request_type = "invalid"

    elif escalation.should_escalate:
        # b. Escalation triggered
        status = "escalated"
        response, justification = generate_escalation_response(
            ticket, escalation.reason, rule
        )

    elif max_score < MIN_RETRIEVAL_SCORE or not articles:
        # c. No corpus match
        status = "escalated"
        response = (
            "Your issue has been escalated to our support team as we could not "
            "find relevant documentation to assist you directly."
        )
        justification = (
            f"No corpus match (max score: {max_score:.2f}). "
            "Escalating to prevent unsupported claims."
        )

    else:
        # d. Reply with corpus-grounded response
        status = "replied"
        response, justification = generate_reply_response(ticket, articles)

    return {
        "issue": ticket.issue,
        "subject": ticket.subject,
        "company": ticket.company,
        "response": response,
        "product_area": product_area,
        "status": status,
        "request_type": request_type,
        "justification": justification,
    }


def main():
    """Main entry point — process all tickets and write output CSV."""
    print("=" * 60)
    print("Multi-Domain Support Triage Agent (Ollama)")
    print("=" * 60)
    
    # Debug: Check if Ollama is enabled
    print(f"\nUSE_OLLAMA: {USE_OLLAMA}")
    if USE_OLLAMA:
        print("✓ Ollama API enabled")
    else:
        print("✗ Using deterministic fallback (set USE_OLLAMA=true in .env)")

    # Load corpus
    print("\nLoading corpus...")
    corpus = load_corpus()
    total_articles = sum(len(v) for v in corpus.values())
    print(f"Total articles loaded: {total_articles}")

    # Read input CSV
    print(f"\nReading {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV, keep_default_na=False)
    total = len(df)
    print(f"Found {total} tickets to process.\n")

    # Process each ticket
    results = []
    replied_count = 0
    escalated_count = 0

    for i, row in df.iterrows():
        ticket = Ticket(
            issue=str(row.get("Issue", "")).strip(),
            subject=str(row.get("Subject", "")).strip(),
            company=str(row.get("Company", "")).strip(),
            raw_index=int(i),
        )

        try:
            result = process_ticket(ticket, corpus)
            results.append(result)

            if result["status"] == "replied":
                replied_count += 1
            else:
                escalated_count += 1

            # Progress output
            display = (ticket.subject or ticket.issue)[:50]
            print(f"  [{i+1}/{total}] {display}... -> {result['status']}")

        except Exception as e:
            print(f"  [{i+1}/{total}] ERROR: {e}")
            # Write an escalated row on error
            results.append({
                "issue": ticket.issue,
                "subject": ticket.subject,
                "company": ticket.company,
                "response": (
                    "An error occurred processing your request. "
                    "Your issue has been escalated to our support team."
                ),
                "product_area": "general_support",
                "status": "escalated",
                "request_type": "product_issue",
                "justification": f"Processing error: {str(e)[:200]}",
            })
            escalated_count += 1

    # Write output CSV
    output_df = pd.DataFrame(results, columns=[
        "issue", "subject", "company",
        "response", "product_area", "status", "request_type", "justification"
    ])
    output_df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n{'=' * 60}")
    print(f"DONE — {total} tickets processed")
    print(f"  Replied:   {replied_count}")
    print(f"  Escalated: {escalated_count}")
    print(f"  Output:    {OUTPUT_CSV}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
