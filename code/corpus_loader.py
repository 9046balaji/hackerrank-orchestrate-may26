"""
corpus_loader.py — Loads all markdown articles from data/{company}/ into
a searchable in-memory index, organized by company.
"""

import os
import re
import hashlib
from pathlib import Path
from typing import Optional

from models import Article
from config import DATA_DIR


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Extract YAML-like frontmatter from markdown content.
    Returns (metadata_dict, body_text).
    """
    metadata = {}
    body = content

    # Check for YAML frontmatter delimiters
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_block = parts[1].strip()
            body = parts[2].strip()

            for line in fm_block.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip().lower()
                    value = value.strip().strip('"').strip("'")
                    if value:
                        metadata[key] = value

    return metadata, body


def _extract_title_from_body(body: str) -> str:
    """Extract title from first H1 heading in body."""
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("# ") and not line.startswith("##"):
            return line[2:].strip()
    return ""


def _infer_product_area(filepath: Path, body: str, company: str) -> str:
    """Infer product_area from file path and content keywords."""
    path_str = str(filepath).lower()

    if company == "hackerrank":
        if "screen" in path_str or "assessment" in path_str or "test" in path_str:
            return "screen"
        if "interview" in path_str or "codepair" in path_str:
            return "interviews"
        if "billing" in path_str or "subscription" in path_str:
            return "billing"
        if "account" in path_str or "setting" in path_str:
            return "account"
        if "artifact" in path_str or "certificate" in path_str or "resume" in path_str:
            return "artifacts"
        if "library" in path_str or "question" in path_str:
            return "library"
        if "skillup" in path_str:
            return "skillup"
        if "community" in path_str:
            return "community"
        if "engage" in path_str:
            return "engage"
        if "integrations" in path_str:
            return "integrations"
        if "chakra" in path_str:
            return "chakra"
        return "general_support"

    if company == "claude":
        if "bedrock" in path_str or "amazon" in path_str:
            return "bedrock"
        if "privacy" in path_str or "legal" in path_str:
            return "data_privacy"
        if "desktop" in path_str:
            return "claude_desktop"
        if "mobile" in path_str:
            return "claude_mobile"
        if "api" in path_str or "console" in path_str:
            return "api_console"
        if "education" in path_str:
            return "education"
        if "code" in path_str:
            return "claude_code"
        if "safeguard" in path_str:
            return "safeguards"
        if "identity" in path_str or "sso" in path_str:
            return "identity_management"
        if "plan" in path_str or "pro" in path_str or "max" in path_str:
            return "plans"
        if "team" in path_str or "enterprise" in path_str:
            return "team_enterprise"
        if "connector" in path_str:
            return "connectors"
        if "chrome" in path_str:
            return "claude_chrome"
        if "government" in path_str:
            return "government"
        if "nonprofit" in path_str:
            return "nonprofits"
        return "general_support"

    if company == "visa":
        if "card" in path_str or "lost" in path_str or "stolen" in path_str:
            return "card_support"
        if "dispute" in path_str or "fraud" in path_str or "identity" in path_str:
            return "disputes_fraud"
        if "travel" in path_str or "cheque" in path_str:
            return "travel_support"
        if "merchant" in path_str or "small-business" in path_str:
            return "merchant"
        if "consumer" in path_str:
            return "consumer"
        return "general_support"

    return "general_support"


def _extract_breadcrumbs(filepath: Path, data_dir: Path) -> list[str]:
    """Build breadcrumbs from the file path relative to data_dir."""
    rel = filepath.relative_to(data_dir)
    parts = list(rel.parts)
    # Remove the company dir and the filename
    if len(parts) > 2:
        return [p.replace("-", " ").title() for p in parts[1:-1]]
    return []


def _extract_source_url(metadata: dict, body: str) -> str:
    """Extract source_url from metadata or first URL in body."""
    if "source_url" in metadata:
        return metadata["source_url"]
    if "url" in metadata:
        return metadata["url"]

    # Try to find a URL in the body
    url_match = re.search(r"https?://\S+", body)
    if url_match:
        return url_match.group(0).rstrip(")")
    return ""


def _generate_article_id(filepath: Path) -> str:
    """Generate a stable, deterministic article ID from filepath."""
    return hashlib.md5(str(filepath).encode()).hexdigest()[:12]


def load_corpus(data_dir: Optional[Path] = None) -> dict[str, list[Article]]:
    """
    Walk all .md files under data/{company}/ recursively.
    Skip index.md files.
    Parse YAML frontmatter to extract metadata.
    Return dict: {"hackerrank": [...], "claude": [...], "visa": [...]}.
    """
    if data_dir is None:
        data_dir = DATA_DIR

    corpus: dict[str, list[Article]] = {
        "hackerrank": [],
        "claude": [],
        "visa": [],
    }

    for company_name in corpus.keys():
        company_dir = data_dir / company_name
        if not company_dir.exists():
            print(f"  WARNING: {company_dir} does not exist, skipping.")
            continue

        for md_file in sorted(company_dir.rglob("*.md")):
            # Skip index files
            if md_file.name == "index.md":
                continue

            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  WARNING: Could not read {md_file}: {e}")
                continue

            metadata, body = _parse_frontmatter(content)

            title = metadata.get("title", "") or _extract_title_from_body(body)
            if not title:
                title = md_file.stem.replace("-", " ").title()

            product_area = metadata.get("product_area", "")
            if not product_area:
                product_area = _infer_product_area(md_file, body, company_name)

            breadcrumbs = _extract_breadcrumbs(md_file, data_dir)
            source_url = _extract_source_url(metadata, body)
            article_id = _generate_article_id(md_file)

            article = Article(
                id=article_id,
                title=title,
                company=company_name,
                product_area=product_area,
                breadcrumbs=breadcrumbs,
                body=body,
                source_url=source_url,
            )
            corpus[company_name].append(article)

    # Print loading summary
    for co, arts in corpus.items():
        print(f"  Loaded {co}: {len(arts)} articles")

    return corpus


# ── Smoke Test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Loading corpus...")
    c = load_corpus()
    for co, arts in c.items():
        print(f"  {co}: {len(arts)} articles")
        if arts:
            print(f"    Sample: {arts[0].title[:80]}")
    assert all(len(v) > 0 for v in c.values()), \
        "ERROR: empty corpus for at least one company"
    print("All companies loaded successfully!")
