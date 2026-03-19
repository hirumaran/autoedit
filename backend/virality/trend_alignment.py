"""
Module B: Trend Alignment Scorer (weight 0.35)
===============================================
Fetches public trend signals and measures how well the video content
aligns with what is currently trending.

Data sources (all public, no auth required except YouTube):
  - Google Trends daily trending searches (via pytrends)
      https://pypi.org/project/pytrends/
      https://trends.google.com/trends/trendingsearches/daily?geo=US
  - Reddit r/popular and r/memes rising posts
      https://www.reddit.com/r/popular.json
      https://www.reddit.com/r/memes.json
  - YouTube Data API v3 — Shorts trending by viewCount
      https://developers.google.com/youtube/v3/docs/search/list

Scoring formula:
  T = 0.7 · semantic_similarity + 0.3 · keyword_match_ratio

  semantic_similarity : cosine similarity between transcript embedding
                        and the centroid of trend keyword embeddings.
  keyword_match_ratio : fraction of trend keywords that appear literally
                        in the transcript (capped at 1.0).

Embedding model: sentence-transformers/all-MiniLM-L6-v2
  https://www.sbert.net/docs/pretrained_models.html
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ── Optional imports ───────────────────────────────────────────────────────────
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logger.warning("⚠️  sentence-transformers not available — semantic scoring disabled")

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    logger.warning("⚠️  pytrends not available — Google Trends disabled")

# ── Config ────────────────────────────────────────────────────────────────────
# Cache trends for 1 hour to avoid hammering public APIs
_CACHE_TTL_SECONDS = 3600
_CACHE_PATH = Path("/tmp/virality_trend_cache.json")

# YouTube Data API v3 key (optional — set in environment)
# https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Reddit public JSON API — no auth needed, rate limit 60 req/min
REDDIT_HEADERS = {"User-Agent": "virality-scorer/1.0 (public research)"}

# Sentence-transformer model — loaded once, shared across calls
_MODEL: Optional["SentenceTransformer"] = None


def _get_model() -> Optional["SentenceTransformer"]:
    """Lazy-load the MiniLM embedding model (download once, cache in memory)."""
    global _MODEL
    if not SEMANTIC_AVAILABLE:
        return None
    if _MODEL is None:
        try:
            # Model card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Loaded sentence-transformers/all-MiniLM-L6-v2")
        except Exception as exc:
            logger.warning(f"⚠️  Could not load embedding model: {exc}")
    return _MODEL


# ── Trend Cache ───────────────────────────────────────────────────────────────

def _load_cache() -> Optional[Dict]:
    """Return cached trend data if fresher than _CACHE_TTL_SECONDS, else None."""
    if not _CACHE_PATH.exists():
        return None
    try:
        data = json.loads(_CACHE_PATH.read_text())
        if time.time() - data.get("_ts", 0) < _CACHE_TTL_SECONDS:
            logger.info("📦 Using cached trend data")
            return data
    except Exception:
        pass
    return None


def _save_cache(data: Dict) -> None:
    data["_ts"] = time.time()
    try:
        _CACHE_PATH.write_text(json.dumps(data))
    except Exception as exc:
        logger.warning(f"⚠️  Could not save trend cache: {exc}")


# ── Source A: Google Trends ───────────────────────────────────────────────────

def fetch_google_trends(geo: str = "US", n: int = 20) -> List[str]:
    """
    Fetch today's trending search topics from Google Trends via pytrends.

    API: TrendReq.trending_searches(pn=geo)
    Reference: https://pypi.org/project/pytrends/

    Returns: list of trending search strings (lowercased).
    """
    if not PYTRENDS_AVAILABLE:
        return []
    try:
        pt = TrendReq(hl="en-US", tz=360, timeout=(5, 15), retries=2)
        df = pt.trending_searches(pn=geo)
        # df is a single-column DataFrame with trending search terms
        keywords = df[0].dropna().tolist()[:n]
        logger.info(f"🔍 Google Trends: {len(keywords)} topics fetched")
        return [str(k).lower().strip() for k in keywords]
    except Exception as exc:
        logger.warning(f"⚠️  Google Trends fetch failed: {exc}")
        return []


# ── Source B: Reddit Public API ───────────────────────────────────────────────

def fetch_reddit_trends(subreddits: Optional[List[str]] = None, limit: int = 25) -> List[str]:
    """
    Fetch rising/hot post titles from Reddit public JSON endpoints.

    No authentication needed — public JSON API.
    Reference: https://www.reddit.com/dev/api/

    Subreddits: r/popular (broad), r/memes (entertainment), r/technology
    Returns: list of lowercased post title words/phrases.
    """
    if subreddits is None:
        subreddits = ["popular", "memes", "technology"]

    keywords: List[str] = []
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/rising.json?limit={limit}"
        try:
            resp = requests.get(url, headers=REDDIT_HEADERS, timeout=5)
            resp.raise_for_status()
            posts = resp.json().get("data", {}).get("children", [])
            for post in posts:
                title: str = post.get("data", {}).get("title", "")
                # Extract meaningful words (≥4 chars, alpha only)
                words = re.findall(r"\b[a-zA-Z]{4,}\b", title.lower())
                keywords.extend(words)
        except Exception as exc:
            logger.warning(f"⚠️  Reddit r/{sub} fetch failed: {exc}")

    # Deduplicate while preserving order
    seen: set = set()
    unique = [w for w in keywords if not (w in seen or seen.add(w))]  # type: ignore
    logger.info(f"📰 Reddit trends: {len(unique)} unique keywords")
    return unique


# ── Source C: YouTube Shorts Trending ─────────────────────────────────────────

def fetch_youtube_shorts_trends(max_results: int = 20) -> List[str]:
    """
    Fetch trending YouTube Shorts titles using YouTube Data API v3.

    Endpoint: GET https://www.googleapis.com/youtube/v3/search
    Params: part=snippet, type=video, videoDuration=short,
            order=viewCount, regionCode=US

    Reference: https://developers.google.com/youtube/v3/docs/search/list

    Requires YOUTUBE_API_KEY env var. Silently skipped if not set.
    Returns: list of lowercased keywords from video titles/descriptions.
    """
    if not YOUTUBE_API_KEY:
        logger.info("ℹ️  YOUTUBE_API_KEY not set — skipping YouTube trends")
        return []

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "type": "video",
        "videoDuration": "short",   # ≤4 min; Shorts are typically ≤60 s
        "order": "viewCount",
        "regionCode": "US",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        keywords: List[str] = []
        for item in items:
            snippet = item.get("snippet", {})
            title = snippet.get("title", "")
            desc = snippet.get("description", "")[:200]
            words = re.findall(r"\b[a-zA-Z]{4,}\b", (title + " " + desc).lower())
            keywords.extend(words)

        seen: set = set()
        unique = [w for w in keywords if not (w in seen or seen.add(w))]  # type: ignore
        logger.info(f"▶️  YouTube trends: {len(unique)} keywords")
        return unique
    except Exception as exc:
        logger.warning(f"⚠️  YouTube Shorts fetch failed: {exc}")
        return []


# ── Aggregated Trend Ingestion ────────────────────────────────────────────────

def fetch_all_trends(force_refresh: bool = False) -> Dict[str, List[str]]:
    """
    Aggregate trends from all sources with 1-hour disk cache.

    Returns dict with keys:
      google   : List[str]
      reddit   : List[str]
      youtube  : List[str]
      combined : List[str]  (deduplicated union)
    """
    if not force_refresh:
        cached = _load_cache()
        if cached:
            return cached

    google = fetch_google_trends()
    reddit = fetch_reddit_trends()
    youtube = fetch_youtube_shorts_trends()

    # Deduplicated union — preserving source ordering
    seen: set = set()
    combined: List[str] = []
    for w in google + reddit + youtube:
        if w not in seen:
            seen.add(w)
            combined.append(w)

    result = {
        "google": google,
        "reddit": reddit,
        "youtube": youtube,
        "combined": combined,
    }
    _save_cache(result)
    return result


# ── Embedding & Similarity ────────────────────────────────────────────────────

def embed_texts(texts: List[str]) -> Optional["np.ndarray"]:
    """
    Encode a list of strings into L2-normalised sentence embeddings.

    Model: all-MiniLM-L6-v2 (384-dim)
    Reference: https://www.sbert.net/docs/pretrained_models.html

    Returns: (N, 384) float32 array, or None if model unavailable.
    """
    model = _get_model()
    if model is None or not texts:
        return None
    try:
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(embeddings)
    except Exception as exc:
        logger.warning(f"⚠️  Embedding failed: {exc}")
        return None


def compute_semantic_similarity(
    transcript: str,
    trend_keywords: List[str],
) -> Tuple[float, List[str]]:
    """
    Measure semantic alignment between transcript and trend keywords.

    Algorithm:
      1. Encode transcript → query vector q (1×384).
      2. Encode each trend keyword → key matrix K (N×384).
      3. Compute cosine similarities: sims = K @ q.T  (already L2-normalised).
      4. Take top-5 matches and average their similarity as the score.
         Using top-5 (not all) avoids dilution from irrelevant keywords.

    Returns: (similarity_score: float in [0,1], matched_trends: List[str])
    """
    if not SEMANTIC_AVAILABLE or not NUMPY_AVAILABLE:
        return 0.0, []

    if not transcript.strip() or not trend_keywords:
        return 0.0, []

    q_emb = embed_texts([transcript])        # shape (1, 384)
    k_emb = embed_texts(trend_keywords)      # shape (N, 384)

    if q_emb is None or k_emb is None:
        return 0.0, []

    # cosine_similarity returns (1, N) matrix; flatten to (N,)
    sims: np.ndarray = cosine_similarity(q_emb, k_emb).flatten()

    # Top-5 most similar trends
    top_k = min(5, len(sims))
    top_indices = np.argsort(sims)[::-1][:top_k]
    top_score = float(sims[top_indices].mean())
    matched = [trend_keywords[i] for i in top_indices if sims[i] > 0.15]

    return min(1.0, max(0.0, top_score)), matched


def compute_keyword_match_ratio(transcript: str, trend_keywords: List[str]) -> float:
    """
    Literal keyword match ratio.

    Formula:
      ratio = (# trend keywords found in transcript) / len(trend_keywords)
      Capped at 1.0.

    Matching is case-insensitive whole-word.
    """
    if not transcript or not trend_keywords:
        return 0.0

    transcript_lower = transcript.lower()
    matches = sum(
        1 for kw in trend_keywords
        if re.search(r"\b" + re.escape(kw) + r"\b", transcript_lower)
    )
    return min(1.0, matches / len(trend_keywords))


# ── Module Entry Point ────────────────────────────────────────────────────────

def score_trend_alignment(
    transcript: str,
    prompt: str = "",
    force_refresh: bool = False,
) -> Dict:
    """
    Compute Trend Alignment score T ∈ [0, 1].

    Formula:
      T = 0.7 · semantic_similarity + 0.3 · keyword_match_ratio

    Returns dict with score, sub-scores, and matched trend keywords.
    Returns trend_available=False if all APIs failed (caller reweights).
    """
    result: Dict = {
        "trend_score": 0.0,
        "semantic_similarity": 0.0,
        "keyword_match_ratio": 0.0,
        "matched_trends": [],
        "trend_available": False,
        "sources_used": [],
    }

    trends = fetch_all_trends(force_refresh=force_refresh)
    combined_keywords = trends.get("combined", [])

    if not combined_keywords:
        logger.warning("⚠️  No trend keywords available — trend module unavailable")
        return result

    result["trend_available"] = True
    result["sources_used"] = (
        (["google"] if trends.get("google") else [])
        + (["reddit"] if trends.get("reddit") else [])
        + (["youtube"] if trends.get("youtube") else [])
    )

    # Combine transcript + optional editing prompt for richer context
    query_text = f"{transcript} {prompt}".strip()

    sem_sim, matched = compute_semantic_similarity(query_text, combined_keywords)
    kw_ratio = compute_keyword_match_ratio(query_text, combined_keywords)

    # Formula: T = 0.7·semantic + 0.3·keyword
    T = 0.7 * sem_sim + 0.3 * kw_ratio

    result["semantic_similarity"] = round(sem_sim, 4)
    result["keyword_match_ratio"] = round(kw_ratio, 4)
    result["trend_score"] = round(min(1.0, max(0.0, T)), 4)
    result["matched_trends"] = matched[:10]  # return top 10

    logger.info(
        f"📈 Trend Alignment: semantic={sem_sim:.3f} "
        f"kw_ratio={kw_ratio:.3f} → T={result['trend_score']:.3f} "
        f"(sources: {result['sources_used']})"
    )
    return result
