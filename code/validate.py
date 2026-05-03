"""
validate.py — Validates agent output against sample_support_tickets.csv.
Compares status and request_type columns, prints accuracy.
"""

import sys
import pandas as pd
from pathlib import Path

from config import TICKETS_DIR
from utils import normalize_text


def main():
    sample_path = TICKETS_DIR / "sample_support_tickets.csv"
    output_path = TICKETS_DIR / "output.csv"

    if not sample_path.exists():
        print(f"ERROR: {sample_path} not found.")
        sys.exit(1)
    if not output_path.exists():
        print(f"ERROR: {output_path} not found. Run main.py first.")
        sys.exit(1)

    sample = pd.read_csv(sample_path, keep_default_na=False)
    output = pd.read_csv(output_path, keep_default_na=False)

    print(f"Sample tickets: {len(sample)}")
    print(f"Output tickets: {len(output)}")
    print()

    # Match rows by normalized issue text
    status_matches = 0
    request_type_matches = 0
    total_matched = 0

    for _, s_row in sample.iterrows():
        s_issue = normalize_text(str(s_row.get("Issue", "")))

        # Find matching output row
        best_match = None
        for _, o_row in output.iterrows():
            o_issue = normalize_text(str(o_row.get("issue", "")))
            if s_issue and o_issue and (s_issue == o_issue or s_issue in o_issue or o_issue in s_issue):
                best_match = o_row
                break

        if best_match is None:
            s_subject = normalize_text(str(s_row.get("Subject", "")))
            for _, o_row in output.iterrows():
                o_subject = normalize_text(str(o_row.get("subject", "")))
                if s_subject and o_subject and s_subject == o_subject:
                    best_match = o_row
                    break

        if best_match is None:
            print(f"  NO MATCH: {s_issue[:60]}...")
            continue

        total_matched += 1

        expected_status = str(s_row.get("Status", "")).strip().lower()
        predicted_status = str(best_match.get("status", "")).strip().lower()

        expected_type = str(s_row.get("Request Type", "")).strip().lower()
        predicted_type = str(best_match.get("request_type", "")).strip().lower()

        status_ok = expected_status == predicted_status
        type_ok = expected_type == predicted_type

        if status_ok:
            status_matches += 1
        if type_ok:
            request_type_matches += 1

        if not status_ok or not type_ok:
            print(f"  MISMATCH: {s_issue[:50]}...")
            if not status_ok:
                print(f"    status: expected={expected_status}, got={predicted_status}")
            if not type_ok:
                print(f"    request_type: expected={expected_type}, got={predicted_type}")

    print()
    print(f"{'=' * 50}")
    print(f"Matched {total_matched}/{len(sample)} sample tickets in output")
    if total_matched > 0:
        status_acc = status_matches / total_matched * 100
        type_acc = request_type_matches / total_matched * 100
        print(f"  Status accuracy:       {status_matches}/{total_matched} ({status_acc:.0f}%)")
        print(f"  Request type accuracy: {request_type_matches}/{total_matched} ({type_acc:.0f}%)")
        print(f"{'=' * 50}")

        if status_acc >= 70:
            print("PASS — Status accuracy >= 70%")
            sys.exit(0)
        else:
            print("FAIL — Status accuracy < 70%")
            sys.exit(1)
    else:
        print("FAIL — No matched tickets found")
        sys.exit(1)


if __name__ == "__main__":
    main()
