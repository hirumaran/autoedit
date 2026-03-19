"""
Virality scoring package.
Usage:
    from backend.virality.scorer import compute_virality_score
    result = compute_virality_score(video_path, transcript, duration_seconds)
"""
from .scorer import compute_virality_score

__all__ = ["compute_virality_score"]
