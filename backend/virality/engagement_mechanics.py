"""
Module C: Engagement Mechanics Scorer (weight 0.25)
====================================================
Predicts viewer retention and engagement from structural video properties.

Signals:
  - Hook strength    : motion + scene-change density in first 3 seconds
  - Duration score   : closeness to the viral sweet-spot (12–25 seconds)
  - Caption density  : fraction of frames with visible text (OCR-based)
  - Speech pacing    : words/sec from transcript (ideal 2–4 wps)

Formula:
  E = 0.4·hook + 0.3·duration + 0.2·captions + 0.1·pacing

References:
  - Hook science  : https://buffer.com/resources/video-engagement/
  - Duration data : TikTok Creator Portal (2022) — 12–25 s optimal for completion rate
  - Caption value : Verizon Media (2019) — 80% watch with sound off
  - Pacing        : National Center for Voice and Speech — comfortable 2–4 wps
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Optional: Tesseract OCR for caption detection
# pip install pytesseract; brew install tesseract
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("⚠️  pytesseract not available — caption score will be zero")


# ── Constants ─────────────────────────────────────────────────────────────────
HOOK_WINDOW_SECONDS = 3.0       # Analyse first N seconds for hook strength
IDEAL_DURATION_MIN = 12.0       # Seconds — below this loses interest
IDEAL_DURATION_MAX = 25.0       # Seconds — above this drops completion rate
IDEAL_PACING_MIN = 2.0          # Words per second
IDEAL_PACING_MAX = 4.0          # Words per second
SCENE_CUT_THRESHOLD = 30.0      # Pixel diff threshold (same as content_quality)
MOTION_HIGH_WATERMARK = 15.0    # (same as content_quality)


# ── Signal: Hook Strength ─────────────────────────────────────────────────────

def compute_hook_strength(video_path: str) -> float:
    """
    Measure how grabbing the first HOOK_WINDOW_SECONDS are.

    Algorithm:
      1. Read only frames within the first HOOK_WINDOW_SECONDS.
      2. Compute average optical flow magnitude (motion).
      3. Count scene cuts (pixel diff > SCENE_CUT_THRESHOLD).
      4. hook = 0.6·norm_motion + 0.4·norm_cuts
         norm_motion: clamp(avg_mag / MOTION_HIGH_WATERMARK, 0, 1)
         norm_cuts  : clamp(n_cuts / (fps * hook_window * 0.5), 0, 1)
           — 0.5 cut/sec is minimum interesting; 1 cut/sec = max score

    Returns: float in [0, 1].
    """
    if not CV2_AVAILABLE:
        return 0.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0.0

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    max_frame = int(fps * HOOK_WINDOW_SECONDS)

    hook_frames: List[np.ndarray] = []
    for _ in range(max_frame):
        ret, frame = cap.read()
        if not ret:
            break
        hook_frames.append(frame)
    cap.release()

    if len(hook_frames) < 2:
        return 0.0

    # Motion (Farneback optical flow)
    magnitudes: List[float] = []
    cuts = 0
    prev_gray = cv2.cvtColor(hook_frames[0], cv2.COLOR_BGR2GRAY)

    for frame in hook_frames[1:]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        mag = float(np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean())
        magnitudes.append(mag)

        # Scene cut detection
        diff = float(np.abs(curr_gray.astype(float) - prev_gray.astype(float)).mean())
        if diff > SCENE_CUT_THRESHOLD:
            cuts += 1
        prev_gray = curr_gray

    avg_motion = float(np.mean(magnitudes)) if magnitudes else 0.0
    norm_motion = min(1.0, avg_motion / MOTION_HIGH_WATERMARK)

    # Normalise cuts: 1 cut per second in hook window = max score
    expected_max_cuts = fps * HOOK_WINDOW_SECONDS * 1.0
    norm_cuts = min(1.0, cuts / max(1, expected_max_cuts))

    hook = 0.6 * norm_motion + 0.4 * norm_cuts
    return round(min(1.0, hook), 4)


# ── Signal: Duration Score ────────────────────────────────────────────────────

def compute_duration_score(duration_seconds: float) -> float:
    """
    Score how close the video duration is to the viral sweet-spot.

    Piecewise linear function:
      - < IDEAL_DURATION_MIN  : score rises linearly from 0 at 0 s to 1 at 12 s
      - IDEAL_DURATION_MIN .. IDEAL_DURATION_MAX : score = 1.0 (perfect)
      - > IDEAL_DURATION_MAX  : score decays linearly from 1 at 25 s to 0 at 60 s

    Returns: float in [0, 1].
    """
    d = duration_seconds
    if d <= 0:
        return 0.0
    if d < IDEAL_DURATION_MIN:
        # Linear ramp: 0 → 1 as duration goes 0 → 12 s
        return round(d / IDEAL_DURATION_MIN, 4)
    if d <= IDEAL_DURATION_MAX:
        return 1.0
    # Linear decay: 1 → 0 as duration goes 25 s → 60 s
    decay_end = 60.0
    score = 1.0 - (d - IDEAL_DURATION_MAX) / (decay_end - IDEAL_DURATION_MAX)
    return round(max(0.0, score), 4)


# ── Signal: Caption Density ───────────────────────────────────────────────────

def compute_caption_density(video_path: str, sample_every: int = 30) -> float:
    """
    Fraction of sampled frames that contain visible text (subtitles/captions).

    Algorithm:
      1. Sample every 30th frame.
      2. Crop the bottom 25% of the frame (where captions typically appear).
      3. Run Tesseract OCR; if output has ≥5 non-space characters → text present.

    Fallback: if OCR unavailable, return 0.0 (conservative — no inflation).

    Returns: float in [0, 1].
    """
    if not OCR_AVAILABLE or not CV2_AVAILABLE:
        return 0.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0.0

    total = 0
    with_text = 0
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % sample_every == 0:
            total += 1
            h = frame.shape[0]
            # Crop bottom 25% — caption zone
            caption_zone = frame[int(h * 0.75):, :]
            rgb = cv2.cvtColor(caption_zone, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            try:
                text = pytesseract.image_to_string(pil_img, config="--psm 6")
                if len(text.replace(" ", "").replace("\n", "")) >= 5:
                    with_text += 1
            except Exception:
                pass
        idx += 1

    cap.release()
    if total == 0:
        return 0.0
    return round(with_text / total, 4)


# ── Signal: Speech Pacing ─────────────────────────────────────────────────────

def compute_speech_pacing(transcript: str, duration_seconds: float) -> float:
    """
    Score speech pacing based on words-per-second from transcript.

    Optimal range (IDEAL_PACING_MIN–IDEAL_PACING_MAX wps):
      - Too slow (< 2 wps): loses attention.
      - Sweet spot (2–4 wps): natural conversational pace.
      - Too fast (> 4 wps): hard to follow.

    Algorithm (triangle/tent function):
      mid = (IDEAL_PACING_MIN + IDEAL_PACING_MAX) / 2  = 3.0 wps
      half_width = (IDEAL_PACING_MAX - IDEAL_PACING_MIN) / 2 = 1.0
      score = max(0, 1 - |wps - mid| / half_width)

    Returns: float in [0, 1].
    """
    if not transcript or duration_seconds <= 0:
        return 0.0

    word_count = len(re.findall(r"\b\w+\b", transcript))
    wps = word_count / duration_seconds

    mid = (IDEAL_PACING_MIN + IDEAL_PACING_MAX) / 2.0   # 3.0
    half_width = (IDEAL_PACING_MAX - IDEAL_PACING_MIN) / 2.0  # 1.0

    score = max(0.0, 1.0 - abs(wps - mid) / half_width)
    return round(min(1.0, score), 4)


# ── Module Entry Point ────────────────────────────────────────────────────────

def score_engagement_mechanics(
    video_path: str,
    transcript: str,
    duration_seconds: float,
    subtitle_data: Optional[List[Dict]] = None,
) -> Dict[str, float]:
    """
    Compute Engagement Mechanics score E ∈ [0, 1].

    Formula:
      E = 0.4·hook + 0.3·duration + 0.2·captions + 0.1·pacing

    If subtitle_data is provided (from Whisper output), use segment count /
    duration as a faster proxy for caption density (avoids running OCR).

    Returns dict with individual signal scores + combined E.
    """
    result: Dict[str, float] = {
        "hook_strength": 0.0,
        "duration_score": 0.0,
        "caption_density": 0.0,
        "speech_pacing": 0.0,
        "engagement_score": 0.0,
    }

    # Hook
    try:
        result["hook_strength"] = compute_hook_strength(video_path)
    except Exception as exc:
        logger.warning(f"⚠️  Hook strength failed: {exc}")

    # Duration
    result["duration_score"] = compute_duration_score(duration_seconds)

    # Captions — fast proxy if subtitle_data available
    if subtitle_data is not None:
        # Proxy: segments that overlap with video / total time ≈ coverage fraction
        covered = sum(
            min(s.get("end", 0), duration_seconds) - max(s.get("start", 0), 0)
            for s in subtitle_data
            if s.get("end", 0) > s.get("start", 0)
        )
        result["caption_density"] = round(
            min(1.0, covered / duration_seconds) if duration_seconds > 0 else 0.0, 4
        )
    else:
        # Full OCR path (slower; ~1–2 s)
        try:
            result["caption_density"] = compute_caption_density(video_path)
        except Exception as exc:
            logger.warning(f"⚠️  Caption density failed: {exc}")

    # Pacing
    result["speech_pacing"] = compute_speech_pacing(transcript, duration_seconds)

    # Weighted combination
    E = (
        0.4 * result["hook_strength"]
        + 0.3 * result["duration_score"]
        + 0.2 * result["caption_density"]
        + 0.1 * result["speech_pacing"]
    )
    result["engagement_score"] = round(min(1.0, max(0.0, E)), 4)

    logger.info(
        f"🎯 Engagement: hook={result['hook_strength']:.3f} "
        f"dur={result['duration_score']:.3f} "
        f"captions={result['caption_density']:.3f} "
        f"pacing={result['speech_pacing']:.3f} "
        f"→ E={result['engagement_score']:.3f}"
    )
    return result
