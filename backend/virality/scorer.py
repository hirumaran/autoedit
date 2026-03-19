"""
Virality Scorer — Orchestrator
==============================
Combines the three independent modules into a final Virality Score (0–100).

Final formula (all modules available):
  Virality = (0.40·C + 0.35·T + 0.25·E) × 100

Graceful reweighting when trend module fails:
  Virality = ((0.40·C + 0.25·E) / 0.65) × 100
  — keeps scores honest; never inflates with hardcoded fallbacks.

Output schema:
  {
    "virality_score"   : float,   # 0–100
    "content_score"    : float,   # 0–1
    "trend_score"      : float,   # 0–1  (or null if unavailable)
    "engagement_score" : float,   # 0–1
    "matched_trends"   : [...],
    "suggestions"      : [...],
    "module_weights"   : {...},
    "signals"          : {...},   # all raw sub-signals
  }
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from .content_quality import score_content_quality
from .trend_alignment import score_trend_alignment
from .engagement_mechanics import score_engagement_mechanics

logger = logging.getLogger(__name__)


# ── Suggestion Engine ─────────────────────────────────────────────────────────

def _generate_suggestions(
    content: Dict,
    trend: Dict,
    engagement: Dict,
) -> List[str]:
    """
    Produce actionable editing suggestions based on low-scoring signals.
    All thresholds are explicit and derived from the scoring formulas.
    """
    suggestions: List[str] = []

    # Content quality
    if content.get("motion", 0) < 0.3:
        suggestions.append(
            "🎬 Add more dynamic camera movement or B-roll — motion score is low (< 0.3)."
        )
    if content.get("cut_density", 0) < 0.3:
        suggestions.append(
            "✂️  Increase cut frequency to ≥1 cut/sec — pacing is too slow for short-form."
        )
    if content.get("face_presence", 0) < 0.4:
        suggestions.append(
            "😊 Include more face-forward shots — face presence drives emotional engagement."
        )
    if content.get("lighting_variance", 0) < 0.3:
        suggestions.append(
            "💡 Improve lighting contrast and colour saturation — visual quality score is low."
        )

    # Trend alignment
    if trend.get("trend_available") and trend.get("trend_score", 0) < 0.3:
        matched = trend.get("matched_trends", [])
        if matched:
            suggestions.append(
                f"📈 Incorporate trending topics in your caption/script: {', '.join(matched[:3])}."
            )
        else:
            suggestions.append(
                "📈 Content doesn't align with current trends — consider adding trending hashtags."
            )

    # Engagement mechanics
    if engagement.get("hook_strength", 0) < 0.4:
        suggestions.append(
            "⚡ Strengthen your hook — add motion, text, or a scene cut within the first 3 seconds."
        )
    if engagement.get("duration_score", 0) < 0.7:
        suggestions.append(
            "⏱  Adjust video length to 12–25 seconds for maximum completion rate."
        )
    if engagement.get("caption_density", 0) < 0.5:
        suggestions.append(
            "📝 Add subtitles/captions — 80% of viewers watch short-form video with sound off."
        )
    if engagement.get("speech_pacing", 0) < 0.5:
        suggestions.append(
            "🗣  Adjust speech pacing to 2–4 words/second for optimal viewer retention."
        )

    return suggestions


# ── Main Scorer ───────────────────────────────────────────────────────────────

def compute_virality_score(
    video_path: str,
    transcript: str,
    duration_seconds: float,
    prompt: str = "",
    subtitle_data: Optional[List[Dict]] = None,
    force_trend_refresh: bool = False,
) -> Dict:
    """
    Full virality scoring pipeline.

    Parameters
    ----------
    video_path        : Absolute path to the video file.
    transcript        : Full Whisper transcript text.
    duration_seconds  : Video duration in seconds.
    prompt            : Optional user editing prompt (adds context to trend match).
    subtitle_data     : Optional Whisper segment list for fast caption density.
    force_trend_refresh: Bypass trend cache and re-fetch from APIs.

    Returns
    -------
    Full result dict — see module docstring for schema.
    """
    t0 = time.time()
    logger.info(f"🚀 Starting virality scoring for: {video_path}")

    # ── Module A: Content Quality ─────────────────────────────────────────────
    content = score_content_quality(video_path)
    C = content["content_score"]

    # ── Module B: Trend Alignment ─────────────────────────────────────────────
    trend = score_trend_alignment(
        transcript=transcript,
        prompt=prompt,
        force_refresh=force_trend_refresh,
    )
    T = trend["trend_score"]
    trend_available = trend["trend_available"]

    # ── Module C: Engagement Mechanics ────────────────────────────────────────
    engagement = score_engagement_mechanics(
        video_path=video_path,
        transcript=transcript,
        duration_seconds=duration_seconds,
        subtitle_data=subtitle_data,
    )
    E = engagement["engagement_score"]

    # ── Final Score with Graceful Reweighting ─────────────────────────────────
    if trend_available:
        # Full formula: V = 0.40·C + 0.35·T + 0.25·E
        raw_score = 0.40 * C + 0.35 * T + 0.25 * E
        weights_used = {"content": 0.40, "trend": 0.35, "engagement": 0.25}
    else:
        # Reweight: V = (0.40·C + 0.25·E) / 0.65
        # Preserves relative importance of C and E without inflating score
        raw_score = (0.40 * C + 0.25 * E) / 0.65
        weights_used = {"content": 0.40 / 0.65, "trend": 0.0, "engagement": 0.25 / 0.65}
        logger.warning("⚠️  Trend module unavailable — reweighting C and E")

    virality_score = round(min(100.0, max(0.0, raw_score * 100)), 2)

    # ── Suggestions ───────────────────────────────────────────────────────────
    suggestions = _generate_suggestions(content, trend, engagement)

    elapsed = round(time.time() - t0, 2)
    logger.info(f"✅ Virality score: {virality_score}/100 (computed in {elapsed}s)")

    return {
        "virality_score": virality_score,
        "content_score": round(C, 4),
        "trend_score": round(T, 4) if trend_available else None,
        "engagement_score": round(E, 4),
        "matched_trends": trend.get("matched_trends", []),
        "suggestions": suggestions,
        "module_weights": weights_used,
        "trend_sources_used": trend.get("sources_used", []),
        "computation_time_s": elapsed,
        "signals": {
            "content": {k: v for k, v in content.items() if k != "content_score"},
            "trend": {
                "semantic_similarity": trend.get("semantic_similarity"),
                "keyword_match_ratio": trend.get("keyword_match_ratio"),
            },
            "engagement": {k: v for k, v in engagement.items() if k != "engagement_score"},
        },
    }
