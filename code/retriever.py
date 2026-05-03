"""
retriever.py — BM25-based article retrieval with title-match boosting.
Caches BM25 models per company for reuse across tickets.
Falls back to simple keyword matching if rank_bm25 is unavailable.
"""

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

from models import Ticket, Article, ArticleMatch
from utils import build_query, tokenize
from config import TOP_K_ARTICLES


# ── Module-level cache ───────────────────────────────────────────────────────
_bm25_cache: dict[str, tuple[BM25Okapi, list[Article]]] = {}


def _build_bm25_index(articles: list[Article]) -> BM25Okapi:
    """Build a BM25 index over article bodies + titles."""
    tokenized_docs = []
    for art in articles:
        # Combine title and body for indexing
        doc_text = f"{art.title} {art.body}"
        tokens = tokenize(doc_text)
        tokenized_docs.append(tokens)

    # Handle empty corpus edge case
    if not tokenized_docs:
        tokenized_docs = [[""]]

    return BM25Okapi(tokenized_docs)


def retrieve(
    ticket: Ticket,
    company: str,
    corpus: dict[str, list[Article]],
    top_k: int = TOP_K_ARTICLES,
) -> list[ArticleMatch]:
    """
    Retrieve the top-K most relevant articles for a ticket.

    - Filter corpus to company articles
    - Tokenize subject+issue as query
    - Get BM25 scores (or fallback to keyword matching)
    - Apply 1.8× boost for articles where token overlap with title > 30%
    - Sort descending by score, break ties by article.id (stable sort)
    - Return only matches with score > 0
    """
    articles = corpus.get(company, [])
    if not articles:
        return []

    # Build query from ticket
    query_text = build_query(ticket)
    query_tokens = tokenize(query_text)
    if not query_tokens:
        return []

    # Use BM25 if available, otherwise fallback to keyword matching
    if HAS_BM25:
        # Build or retrieve cached BM25 model
        if company not in _bm25_cache:
            bm25 = _build_bm25_index(articles)
            _bm25_cache[company] = (bm25, articles)
        else:
            bm25, cached_articles = _bm25_cache[company]
            # Verify cache is still valid
            if cached_articles is not articles:
                bm25 = _build_bm25_index(articles)
                _bm25_cache[company] = (bm25, articles)

        bm25, _ = _bm25_cache[company]
        scores = bm25.get_scores(query_tokens)
    else:
        # Fallback: simple keyword matching
        scores = _keyword_match_scores(articles, query_tokens)

    # Apply title-match boosting
    query_token_set = set(query_tokens)
    for i, art in enumerate(articles):
        title_tokens = set(tokenize(art.title))
        if not title_tokens:
            continue
        overlap = len(query_token_set & title_tokens) / len(title_tokens)
        if overlap > 0.3:
            scores[i] *= 1.8

    # Build scored matches
    matches = []
    for i, score in enumerate(scores):
        if score > 0:
            matches.append(ArticleMatch(article=articles[i], score=float(score)))

    # Sort descending by score, break ties by article.id for determinism
    matches.sort(key=lambda m: (-m.score, m.article.id))

    return matches[:top_k]


def _keyword_match_scores(articles: list[Article], query_tokens: list[str]) -> list[float]:
    """
    Fallback scoring when BM25 is unavailable.
    Returns a score for each article based on keyword overlap.
    """
    query_set = set(query_tokens)
    scores = []
    
    for art in articles:
        doc_text = f"{art.title} {art.body}"
        doc_tokens = set(tokenize(doc_text))
        
        if not doc_tokens:
            scores.append(0.0)
            continue
        
        # Simple overlap score
        overlap = len(query_set & doc_tokens)
        score = float(overlap) / max(len(query_set), 1)
        scores.append(score * 10.0)  # Scale to be comparable to BM25 scores
    
    return scores
