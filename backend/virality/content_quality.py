"""
Module A: Content Quality Scorer (weight 0.4)
=============================================
Deterministic visual analytics using OpenCV and MediaPipe.

Signals:
  - Motion intensity    : Farneback optical flow magnitude (avg per frame)
  - Cut density         : Scene changes per second (frame diff threshold)
  - Face presence       : % frames containing ≥1 detected face
  - Lighting/color var  : Std-dev of HSV value + saturation channels

All metrics are independently normalised to [0, 1] before combining.

References:
  - OpenCV optical flow : https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html
  - MediaPipe face det. : https://mediapipe.dev/solutions/face_detection
  - Farneback paper     : Farneback (2003), "Two-frame motion estimation based on polynomial expansion"
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Optional heavy imports ────────────────────────────────────────────────────
try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("⚠️  OpenCV not available — content quality will be zero")

try:
    import mediapipe as mp
    import mediapipe.python.solutions.face_detection as mp_face

    _mp_face = mp.solutions.face_detection if hasattr(mp, "solutions") else mp_face
    MEDIAPIPE_AVAILABLE = True
except (ImportError, AttributeError) as e:
    MEDIAPIPE_AVAILABLE = False
    logger.warning(f"⚠️  MediaPipe not available ({e}) — face presence will be zero")


# ── Constants ─────────────────────────────────────────────────────────────────
# Sample every N-th frame to stay within ~1–2 s runtime for short-form video.
SAMPLE_EVERY_N_FRAMES = 5
# Pixel diff threshold between consecutive frames to count as a scene cut.
# Empirically chosen for 720p content; adjust for lower-res input.
SCENE_CUT_THRESHOLD = 30.0
# Optical-flow magnitude considered "high motion" for normalisation ceiling.
# Typical walking-talking video ≈ 2–5; extreme action ≈ 10–20.
MOTION_HIGH_WATERMARK = 15.0


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_frames(
    video_path: str, sample_every: int = SAMPLE_EVERY_N_FRAMES
) -> Tuple[List[np.ndarray], float]:
    """
    Read sampled BGR frames from video.  Returns (frames, fps).
    Raises RuntimeError if cv2 unavailable or file cannot be opened.
    """
    if not CV2_AVAILABLE:
        raise RuntimeError("OpenCV not available")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps: float = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames: List[np.ndarray] = []
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % sample_every == 0:
            frames.append(frame)
        idx += 1

    cap.release()
    return frames, fps


# ── Signal: Motion Intensity ──────────────────────────────────────────────────


def compute_motion_intensity(frames: List[np.ndarray]) -> float:
    """
    Compute average optical-flow magnitude across consecutive sampled frame pairs.

    Algorithm (Farneback dense optical flow):
      1. Convert each frame to grayscale.
      2. Call cv2.calcOpticalFlowFarneback(prev, curr, ...) → flow field (H×W×2).
      3. Compute per-pixel magnitude: mag = sqrt(flow_x² + flow_y²).
      4. Average magnitude across all pixels and all frame pairs.
      5. Normalise to [0,1] by dividing by MOTION_HIGH_WATERMARK and clamping.

    Returns: float in [0, 1].  0 = static, 1 = maximum expected motion.
    """
    if not CV2_AVAILABLE or len(frames) < 2:
        return 0.0

    magnitudes: List[float] = []
    prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

    for frame in frames[1:]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Farneback params: pyr_scale=0.5, levels=3, winsize=15,
        #   iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        # Magnitude of (u, v) flow vectors
        mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        magnitudes.append(float(mag.mean()))
        prev_gray = curr_gray

    if not magnitudes:
        return 0.0

    avg_mag = float(np.mean(magnitudes))
    # Clamp and normalise: score = avg_mag / MOTION_HIGH_WATERMARK
    return min(1.0, avg_mag / MOTION_HIGH_WATERMARK)


# ── Signal: Scene Cut Density ─────────────────────────────────────────────────


def compute_cut_density(
    frames: List[np.ndarray], fps: float, sample_every: int = SAMPLE_EVERY_N_FRAMES
) -> float:
    """
    Estimate scene cuts per second.

    Algorithm:
      1. Convert consecutive frame pairs to grayscale.
      2. Compute mean absolute pixel difference.
      3. If diff > SCENE_CUT_THRESHOLD → count as cut.
      4. cuts_per_second = n_cuts / video_duration_seconds.
      5. Normalise: ideal short-form pacing ≈ 1–4 cuts/sec.
         score = clamp(cuts_per_second / 4.0, 0, 1).

    Returns: float in [0, 1].
    """
    if not CV2_AVAILABLE or len(frames) < 2:
        return 0.0

    cuts = 0
    prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(float)

    for frame in frames[1:]:
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(float)
        diff = float(np.abs(curr_gray - prev_gray).mean())
        if diff > SCENE_CUT_THRESHOLD:
            cuts += 1
        prev_gray = curr_gray

    # Convert sampled frame count back to real duration
    total_real_frames = len(frames) * sample_every
    duration_s = total_real_frames / fps if fps > 0 else 1.0

    cuts_per_sec = cuts / duration_s
    # Normalise: 4 cuts/sec = ideal upper bound for short-form virality
    return min(1.0, cuts_per_sec / 4.0)


# ── Signal: Face Presence ─────────────────────────────────────────────────────


def compute_face_presence(frames: List[np.ndarray]) -> float:
    """
    Fraction of sampled frames that contain ≥1 detected face.

    Uses MediaPipe FaceDetection (short-range model, confidence ≥ 0.5).
    Reference: https://mediapipe.dev/solutions/face_detection

    Returns: float in [0, 1].  1 = face in every sampled frame.
    """
    if not MEDIAPIPE_AVAILABLE or not CV2_AVAILABLE or not frames:
        return 0.0

    face_count = 0
    with _mp_face.FaceDetection(
        model_selection=0,  # 0 = short-range (≤2 m), 1 = full-range
        min_detection_confidence=0.5,
    ) as detector:
        for frame in frames:
            # MediaPipe expects RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = detector.process(rgb)
            if results.detections:
                face_count += 1

    return face_count / len(frames)


# ── Signal: Lighting / Color Variance ────────────────────────────────────────


def compute_lighting_variance(frames: List[np.ndarray]) -> float:
    """
    Measure visual richness via HSV value-channel std-dev and saturation mean.

    Algorithm:
      1. Convert each frame to HSV.
      2. V channel (brightness) std-dev → captures dynamic range / contrast.
      3. S channel (saturation) mean → captures colour richness.
      4. Combined score = 0.5 * norm(V_std) + 0.5 * norm(S_mean).
         Normalisation: V_std in [0, 80], S_mean in [0, 255].

    Returns: float in [0, 1].
    """
    if not CV2_AVAILABLE or not frames:
        return 0.0

    v_stds: List[float] = []
    s_means: List[float] = []

    for frame in frames:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # H=0, S=1, V=2
        v_stds.append(float(hsv[:, :, 2].std()))
        s_means.append(float(hsv[:, :, 1].mean()))

    avg_v_std = float(np.mean(v_stds))
    avg_s_mean = float(np.mean(s_means))

    # Normalise: V std ≈ 80 for high-contrast content; S mean ≈ 255 max
    norm_v = min(1.0, avg_v_std / 80.0)
    norm_s = min(1.0, avg_s_mean / 255.0)

    return 0.5 * norm_v + 0.5 * norm_s


# ── Module Entry Point ────────────────────────────────────────────────────────


def score_content_quality(video_path: str) -> Dict[str, float]:
    """
    Compute Content Quality score C ∈ [0, 1].

    Weights (chosen to reflect short-form virality drivers):
      motion      : 0.30  — dynamic visuals drive watch-through
      cut_density : 0.25  — fast cuts maintain attention
      face        : 0.25  — faces increase emotional engagement (Nielsen, 2021)
      lighting    : 0.20  — visual production quality

    Formula:
      C = 0.30·motion + 0.25·cuts + 0.25·faces + 0.20·lighting

    Returns dict with individual signals + combined score.
    """
    result: Dict[str, float] = {
        "motion": 0.0,
        "cut_density": 0.0,
        "face_presence": 0.0,
        "lighting_variance": 0.0,
        "content_score": 0.0,
    }

    try:
        frames, fps = _load_frames(video_path)
    except Exception as exc:
        logger.warning(f"⚠️  Could not load frames for content scoring: {exc}")
        return result

    if not frames:
        return result

    result["motion"] = compute_motion_intensity(frames)
    result["cut_density"] = compute_cut_density(frames, fps)
    result["face_presence"] = compute_face_presence(frames)
    result["lighting_variance"] = compute_lighting_variance(frames)

    # Weighted combination — formula explicit above
    C = (
        0.30 * result["motion"]
        + 0.25 * result["cut_density"]
        + 0.25 * result["face_presence"]
        + 0.20 * result["lighting_variance"]
    )
    result["content_score"] = round(min(1.0, max(0.0, C)), 4)

    logger.info(
        f"📊 Content Quality: motion={result['motion']:.3f} "
        f"cuts={result['cut_density']:.3f} "
        f"faces={result['face_presence']:.3f} "
        f"lighting={result['lighting_variance']:.3f} "
        f"→ C={result['content_score']:.3f}"
    )
    return result
