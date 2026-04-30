"""
Edit Router
===========
Handles video editing operations:
- POST /preview  — low-res fast preview of edits
- POST /render   — full-quality final render
- POST /process  — apply effects, trims, subtitles, music
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = ROOT_DIR / "data" / "uploads"
OUTPUTS_DIR = ROOT_DIR / "data" / "outputs"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Request Models ────────────────────────────────────────────────────────────


class TrimRequest(BaseModel):
    video_path: str
    start: float = Field(ge=0, description="Start time in seconds")
    end: float = Field(gt=0, description="End time in seconds")


class EffectRequest(BaseModel):
    video_path: str
    effect_id: str
    params: Optional[Dict] = None


class SubtitleSegment(BaseModel):
    text: str
    start: float
    end: float


class SubtitleRequest(BaseModel):
    video_path: str
    segments: List[SubtitleSegment]
    style_preset: str = "sleek"


class ConcatenateRequest(BaseModel):
    video_path: str
    segments: List[Dict] = Field(description="List of {start, end} dicts")
    transition: str = "none"


class MusicMixRequest(BaseModel):
    video_path: str
    audio_path: str
    bg_volume: float = 0.3
    duck_volume: float = 0.08
    fade_in: float = 1.0
    fade_out: float = 2.0


class EditPreviewRequest(BaseModel):
    video_path: str
    effects: Optional[List[str]] = None
    music_id: Optional[str] = None
    subtitles: Optional[List[SubtitleSegment]] = None
    trim: Optional[Dict] = None


class RenderRequest(BaseModel):
    video_path: Optional[str] = None
    video_id: Optional[str] = None
    custom_segments: Optional[List[Dict]] = None
    manual_transcript: Optional[str] = None
    effects: Optional[List[Dict]] = None
    music_path: Optional[str] = None
    music_file: Optional[str] = None
    music_volume: Optional[float] = 0.3
    subtitles: Optional[List[Dict]] = None
    add_subtitles: Optional[bool] = False
    add_music: Optional[bool] = False
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    style_preset: str = "sleek"
    resolution: Optional[str] = None
    platform: Optional[str] = None
    format: Optional[str] = None
    aspect_ratio: Optional[str] = None


class ProcessRequest(BaseModel):
    # Fields the frontend actually sends
    video_id: Optional[str] = None
    style_preset: Optional[str] = "sleek"
    add_subtitles: Optional[bool] = False
    trim_boring_parts: Optional[bool] = False
    user_prompt: Optional[str] = None
    platform: Optional[str] = None
    format: Optional[str] = None
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    # Also accept the original names for API compatibility
    video_path: Optional[str] = None
    instruction: Optional[str] = None
    effects: Optional[List[str]] = None
    music_id: Optional[str] = None
    subtitles: Optional[List[Dict]] = None
    trim: Optional[Dict] = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _output_path(suffix: str = ".mp4") -> str:
    return str(OUTPUTS_DIR / f"{uuid.uuid4().hex}{suffix}")


def _resolve_video_path(video_path: str) -> str:
    """Resolve video path — check uploads dir if relative path given."""
    p = Path(video_path)
    if p.is_absolute() and p.exists():
        return str(p)
    # Try in uploads dir (exact match)
    candidate = UPLOADS_DIR / p.name
    if candidate.exists():
        return str(candidate)
    # Try with common video extensions (video_id without extension)
    for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
        candidate = UPLOADS_DIR / f"{p.stem}{ext}"
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"Video not found: {video_path}")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/preview", summary="Generate a low-res preview of edits")
async def edit_preview(req: EditPreviewRequest):
    """
    Generate a fast 15-second low-res preview of the requested edits.

    This uses the MoviePy engine with FFmpeg fallback for quick iteration.
    Returns a path to the preview video.
    """
    try:
        video_path = _resolve_video_path(req.video_path)
        output = _output_path()

        from backend.video_processor import VideoProcessor

        # For preview, just trim first 15s and apply one effect if specified
        vp = VideoProcessor(video_path)

        if req.trim:
            start = req.trim.get("start", 0)
            end = min(req.trim.get("end", 15), 15)
            output = vp.trim_video(start, end, output)
        else:
            # Default: just copy with optional effect
            if req.effects and len(req.effects) > 0:
                effect_id = req.effects[0]
                from backend.editing_engine import MoviePyEngine

                with MoviePyEngine(video_path) as engine:
                    engine.apply_effect(output, effect_id)
            else:
                import shutil

                shutil.copy(video_path, output)

        logger.info(f"👁️ Preview generated: {output}")
        return JSONResponse(
            {
                "success": True,
                "output_path": output,
                "is_preview": True,
            }
        )

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Preview failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {exc}")


@router.post("/render", summary="Full-quality final render")
async def render_video(req: RenderRequest):
    """
    Render the final edited video with cuts, aspect ratio, subtitles, and music.
    """
    from backend.db import init_db, save_job
    import json
    import subprocess

    DB_PATH = ROOT_DIR / "data" / "jobs.db"

    try:
        raw_path = req.video_path or req.video_id
        if not raw_path:
            raise HTTPException(
                status_code=400, detail="video_id or video_path is required"
            )
        video_path = _resolve_video_path(raw_path)
        video_id = req.video_id or Path(video_path).stem

        # Update status to rendering — preserve existing job data
        conn = init_db(DB_PATH)
        cursor = conn.execute("SELECT data FROM jobs WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        existing_job = json.loads(row[0]) if row else {}
        existing_job.update({"status": "rendering", "progress": 80})
        save_job(conn, video_id, existing_job)
        conn.close()

        # Get video duration for segment calculations
        from backend.video_processor import VideoProcessor

        vp_info = VideoProcessor(video_path)
        duration = vp_info.duration

        current_path = video_path

        # ── Step 1: Cut out selected segments (keep the rest) ──────────
        logger.info(
            f"🎬 Render start: video_id={video_id}, custom_segments={req.custom_segments}, aspect_ratio={req.aspect_ratio}, add_subtitles={req.add_subtitles}, add_music={req.add_music}"
        )
        if req.custom_segments and len(req.custom_segments) > 0:
            # custom_segments are the ranges to REMOVE
            # Build the ranges to KEEP (inverse of cuts)
            cuts = sorted(req.custom_segments, key=lambda s: s.get("start", 0))
            keep_ranges = []
            cursor = 0.0
            for cut in cuts:
                cut_start = float(cut.get("start", 0))
                cut_end = float(cut.get("end", 0))
                if cut_start > cursor:
                    keep_ranges.append((cursor, cut_start))
                cursor = max(cursor, cut_end)
            if cursor < duration:
                keep_ranges.append((cursor, duration))

            if keep_ranges:
                # Trim each kept segment and concatenate
                kept_files = []
                for i, (start, end) in enumerate(keep_ranges):
                    if end - start < 0.1:  # Skip tiny segments
                        continue
                    seg_output = _output_path()
                    vp = VideoProcessor(current_path)
                    vp.trim_video(start, end, seg_output)
                    kept_files.append(seg_output)

                if len(kept_files) > 1:
                    # Concatenate segments with ffmpeg
                    concat_list = ROOT_DIR / "data" / "temp" / f"{video_id}_concat.txt"
                    concat_list.parent.mkdir(parents=True, exist_ok=True)
                    with open(concat_list, "w") as f:
                        for fpath in kept_files:
                            f.write(f"file '{fpath}'\n")
                    concat_output = _output_path()
                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(concat_list),
                        "-c",
                        "copy",
                        concat_output,
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    current_path = concat_output
                    concat_list.unlink(missing_ok=True)
                elif len(kept_files) == 1:
                    current_path = kept_files[0]

        # ── Step 2: Apply aspect ratio / platform resize ───────────────
        aspect = req.aspect_ratio
        if req.platform and not aspect:
            # Map platform to aspect ratio
            platform_map = {
                "tiktok": "9:16",
                "instagram-reel": "9:16",
                "youtube-short": "9:16",
                "instagram-post": "1:1",
            }
            aspect = platform_map.get(req.platform, "9:16")

        if aspect:
            try:
                transform_output = _output_path()
                vp = VideoProcessor(current_path)
                # Parse aspect ratio to resolution
                res_map = {
                    "9:16": "1080:1920",
                    "16:9": "1920:1080",
                    "1:1": "1080:1080",
                    "4:5": "1080:1350",
                }
                res = res_map.get(aspect, "1080:1920")
                logger.info(
                    f"📐 Transforming to aspect_ratio={aspect}, resolution={res}"
                )
                vp.transform_video(
                    transform_output,
                    aspect_ratio=aspect,
                    resolution=res,
                    resize_mode="fit_blur",
                )
                current_path = transform_output
                logger.info(f"📐 Transform done: {current_path}")
            except Exception as exc:
                logger.error(f"📐 Transform FAILED: {exc}")
        else:
            logger.info(f"📐 No aspect ratio to apply (aspect={aspect})")

        # ── Step 3: Add subtitles if requested ─────────────────────────
        if req.add_subtitles:
            # Get segments from the job database
            conn = init_db(DB_PATH)
            cursor = conn.execute(
                "SELECT data FROM jobs WHERE video_id = ?", (video_id,)
            )
            row = cursor.fetchone()

            subtitle_segments = []
            if row:
                job = json.loads(row[0])
                subtitle_segments = job.get("segments", [])

            conn.close()

            logger.info(
                f"📝 Subtitles: add_subtitles={req.add_subtitles}, segments_found={len(subtitle_segments)}"
            )
            if subtitle_segments:
                try:
                    # Adjust subtitle timestamps for cuts
                    if req.custom_segments and len(req.custom_segments) > 0:
                        cuts = sorted(
                            req.custom_segments, key=lambda s: s.get("start", 0)
                        )
                        # Build list of surviving (kept) time ranges
                        kept_ranges = []
                        cursor = 0.0
                        for cut in cuts:
                            cs = float(cut.get("start", 0))
                            ce = float(cut.get("end", 0))
                            if cs > cursor:
                                kept_ranges.append((cursor, cs))
                            cursor = max(cursor, ce)
                        if cursor < duration:
                            kept_ranges.append((cursor, duration))

                        # For each subtitle, clip it against kept ranges
                        # and shift timestamps to remove cut gaps
                        adjusted = []
                        for seg in subtitle_segments:
                            seg_start = float(seg.get("start", 0))
                            seg_end = float(seg.get("end", 0))
                            for kstart, kend in kept_ranges:
                                # Find overlap between subtitle and this kept range
                                ov_start = max(seg_start, kstart)
                                ov_end = min(seg_end, kend)
                                if ov_start >= ov_end:
                                    continue
                                # Calculate offset: total cut duration before kstart
                                offset = 0.0
                                for c in cuts:
                                    c_start = float(c.get("start", 0))
                                    c_end = float(c.get("end", 0))
                                    if c_end <= kstart:
                                        offset += c_end - c_start
                                new_seg = dict(seg)
                                new_seg["start"] = max(0, ov_start - offset)
                                new_seg["end"] = max(0, ov_end - offset)
                                if new_seg["end"] > new_seg["start"]:
                                    adjusted.append(new_seg)
                        # Drop tiny fragments created by boundary clipping
                        # (e.g., 0.02s subtitles are effectively invisible).
                        subtitle_segments = [
                            s
                            for s in adjusted
                            if float(s.get("end", 0)) - float(s.get("start", 0)) >= 0.2
                        ]
                        logger.info(
                            f"📝 Adjusted {len(subtitle_segments)} subtitle segments for cuts"
                        )
                        if subtitle_segments:
                            preview = ", ".join(
                                f"{float(s.get('start', 0)):.2f}-{float(s.get('end', 0)):.2f}:{(s.get('text', '') or '').strip()[:20]}"
                                for s in subtitle_segments[:3]
                            )
                            logger.info(f"📝 Subtitle timeline preview: {preview}")

                    sub_output = _output_path()
                    vp = VideoProcessor(current_path)
                    info = vp.get_video_info()
                    vp.add_subtitles(
                        subtitle_file="",
                        output_path=sub_output,
                        style_preset=req.style_preset or "sleek",
                        subtitle_data=subtitle_segments,
                        video_width=info.get("width", 1080),
                        video_height=info.get("height", 1920),
                    )
                    current_path = sub_output
                    logger.info(f"📝 Subtitles done: {current_path}")
                except Exception as exc:
                    logger.error(f"📝 Subtitles FAILED: {exc}")
            else:
                logger.warning(f"📝 No subtitle segments found in DB for {video_id}")
        else:
            logger.info(f"📝 Subtitles skipped (add_subtitles={req.add_subtitles})")

        # ── Step 4: Mix music if requested ─────────────────────────────
        logger.info(f"🎵 Music: add_music={req.add_music}, music_file={req.music_file}")
        if req.add_music and req.music_file:
            music_path = req.music_file

            # Try direct path first
            if not Path(music_path).exists():
                # Look up in music directory
                music_dir = ROOT_DIR / "data" / "music"
                candidate = music_dir / Path(music_path).name
                if candidate.exists():
                    music_path = str(candidate)
                else:
                    # Look up by track_id in database
                    try:
                        conn = init_db(DB_PATH)
                        cursor = conn.execute(
                            "SELECT local_path FROM music_cache WHERE track_id = ?",
                            (music_path,),
                        )
                        row = cursor.fetchone()
                        conn.close()
                        if row and Path(row[0]).exists():
                            music_path = row[0]
                    except Exception:
                        pass

            logger.info(
                f"🎵 Music resolved path: {music_path}, exists={Path(music_path).exists() if music_path else False}"
            )
            if music_path and Path(music_path).exists():
                try:
                    music_output = _output_path()
                    vol = req.music_volume or 0.3

                    # FFmpeg: mix original audio with background music
                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        current_path,
                        "-i",
                        music_path,
                        "-filter_complex",
                        f"[1:a]volume={vol}[bg];[0:a][bg]amix=inputs=2:duration=shortest:dropout_transition=2[outa]",
                        "-map",
                        "0:v",
                        "-map",
                        "[outa]",
                        "-c:v",
                        "copy",
                        "-preset",
                        "fast",
                        music_output,
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    current_path = music_output
                    logger.info(f"🎵 Music done: {current_path}")
                except Exception as exc:
                    logger.error(f"🎵 Music FAILED: {exc}")
            else:
                logger.warning(f"🎵 Music file not found: {music_path}")
        else:
            logger.info(f"🎵 Music skipped")

        # ── Step 5: Copy to final output ───────────────────────────────
        output = _output_path()
        import shutil

        if current_path != output:
            shutil.copy(current_path, output)

        output_url = f"/api/download/{Path(output).name}"

        # Save completed status — preserve existing job data (segments, transcript, etc.)
        conn = init_db(DB_PATH)
        cursor = conn.execute("SELECT data FROM jobs WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        existing_job = json.loads(row[0]) if row else {}
        existing_job.update(
            {
                "status": "completed",
                "progress": 100,
                "output_path": output,
                "output_url": output_url,
            }
        )
        save_job(conn, video_id, existing_job)
        conn.close()

        logger.info(f"🎬 Render complete: {output}")
        return JSONResponse(
            {
                "success": True,
                "output_path": output,
                "output_url": output_url,
                "is_preview": False,
            }
        )

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Render failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Render failed: {exc}")


@router.post("/process", summary="Process video with AI agent or manual edits")
async def process_video(req: ProcessRequest):
    """
    Process a video: run full analysis (transcription, virality, Phase 1),
    then apply any manual edits. Sets status to 'analyzed' so the frontend
    can show the review UI.
    """
    from backend.db import init_db, save_job

    DB_PATH = ROOT_DIR / "data" / "jobs.db"

    try:
        # Resolve video path from either field
        raw_path = req.video_path or req.video_id
        if not raw_path:
            raise HTTPException(
                status_code=400, detail="video_id or video_path is required"
            )
        video_path = _resolve_video_path(raw_path)
        video_id = req.video_id or Path(video_path).stem

        # ── Step 1: Transcription ───────────────────────────────────────────
        conn = init_db(DB_PATH)
        save_job(conn, video_id, {"status": "transcribing", "progress": 15})
        conn.close()

        transcript_text = ""
        segments = []
        try:
            from backend.services.transcription import transcription_service

            transcription = transcription_service.transcribe(video_path)
            segments = transcription.get("segments", [])
            # Build full transcript text from segments
            transcript_text = " ".join(
                seg.get("text", "").strip()
                for seg in segments
                if seg.get("text", "").strip()
            )
        except Exception as exc:
            logger.warning(f"Transcription failed: {exc}")

        # ── Step 2: Virality scoring ────────────────────────────────────────
        conn = init_db(DB_PATH)
        save_job(conn, video_id, {"status": "analyzing", "progress": 40})
        conn.close()

        virality = {}
        try:
            from backend.virality.scorer import compute_virality_score
            from backend.video_processor import VideoProcessor

            vp = VideoProcessor(video_path)
            virality = compute_virality_score(
                video_path=video_path,
                transcript=transcript_text,
                duration_seconds=vp.duration,
                prompt=req.user_prompt or "",
                subtitle_data=segments,
            )
        except Exception as exc:
            logger.warning(f"Virality scoring failed: {exc}")

        # ── Step 3: Phase 1 analysis (OCR, faces, logos) ───────────────────
        conn = init_db(DB_PATH)
        save_job(conn, video_id, {"status": "enriching", "progress": 60})
        conn.close()

        phase1 = {}
        duration = 0.0
        try:
            from backend.phase1_pipeline import PhaseOneAnalyzer

            analyzer = PhaseOneAnalyzer(temp_dir=ROOT_DIR / "data" / "temp")
            result = analyzer.process(video_path)
            phase1 = result.to_dict()
            duration = result.duration
        except Exception as exc:
            logger.warning(f"Phase 1 analysis failed: {exc}")
            try:
                from backend.video_processor import VideoProcessor

                vp = VideoProcessor(video_path)
                duration = vp.duration
            except Exception:
                pass

        # ── Step 4: AI-powered visual analysis per segment ─────────────────
        # Initialize Florence-2 analyzer once for all segments
        from backend.ai_analyzer import AIVideoAnalyzer

        ai_analyzer = AIVideoAnalyzer()

        suggestions = virality.get("suggestions", [])

        # Build suggested cuts: extract frames at each segment's timestamps,
        # run through Florence-2 (or heuristic fallback), and derive scores
        # from actual visual content rather than text-length heuristics.
        suggested_cuts = []
        segment_scores = []

        for seg in segments:
            seg_start = float(seg.get("start", 0))
            seg_end = float(seg.get("end", 0))
            seg_duration = seg_end - seg_start

            # Sample 1 frame at segment midpoint (free-tier rate limit: ~10 req/min)
            seg_mid = (seg_start + seg_end) / 2
            timestamp = seg_mid if seg_duration > 0 else seg_start

            frame_path = None
            try:
                fd, frame_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                # Extract a single frame at segment midpoint via ffmpeg seek
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-ss", str(timestamp),
                        "-i", video_path, "-vframes", "1", "-q:v", "3",
                        frame_path,
                    ],
                    check=True,
                    capture_output=True,
                    timeout=15,
                )

                # Run through Groq Llama 4 Scout vision; falls back to heuristic
                # if GROQ_API_KEY is missing or the API call fails.
                analysis = ai_analyzer._analyze_frame_with_model(frame_path)
                if analysis is None:
                    analysis = ai_analyzer._analyze_frame_heuristic(frame_path)

                # Respect Groq free-tier rate limit (~10 req/min)
                time.sleep(1.0)

                score = analysis.get("score", 5)
                description = analysis.get("description", "")
            except Exception as exc:
                logger.warning(
                    "Frame analysis failed for segment [%.1f–%.1f]: %s",
                    seg_start, seg_end, exc,
                )
                score = 5  # neutral fallback
                description = ""
            finally:
                if frame_path and os.path.exists(frame_path):
                    try:
                        os.unlink(frame_path)
                    except OSError:
                        pass

            segment_scores.append(score)

            suggested_cuts.append(
                {
                    "start": round(seg_start, 1),
                    "end": round(seg_end, 1),
                    "text": seg.get("text", ""),
                    "score": score,
                    "recommendation": "cut" if score <= 4 else "keep",
                    "reason": description[:200] if description else "Content segment",
                }
            )

        # Derive overall score: 70% AI segment visual quality + 30% virality signal.
        # This ensures the overall score correlates with the per-segment scores
        # the user sees in the list, while still rewarding viral potential.
        if segment_scores:
            segment_avg = sum(segment_scores) / len(segment_scores)
            virality_score = virality.get("virality_score", 50)
            overall_score = round(
                0.7 * segment_avg + 0.3 * (virality_score / 10)
            )
        else:
            overall_score = round(virality.get("virality_score", 50) / 10)

        low_score_count = sum(1 for s in segment_scores if s <= 4)
        summary = (
            f"Video analyzed: {len(segments)} segments, "
            f"{low_score_count} flagged for low visual engagement."
        )
        if suggestions:
            summary += f" {len(suggestions)} improvement suggestions found."

        ai_analysis = {
            "overall_score": overall_score,
            "summary": summary,
            "suggested_cuts": suggested_cuts,
            "virality": virality,
            "suggestions": suggestions,
        }

        # ── Step 5: Save analyzed job ──────────────────────────────────────
        conn = init_db(DB_PATH)
        save_job(
            conn,
            video_id,
            {
                "status": "analyzed",
                "progress": 75,
                "video_path": video_path,
                "transcript": transcript_text,
                "segments": segments,
                "ai_analysis": ai_analysis,
                "phase_one_metadata": phase1,
                "duration": duration,
            },
        )
        conn.close()

        return JSONResponse(
            {
                "success": True,
                "video_id": video_id,
                "status": "analyzed",
                "message": "Analysis complete. Review your video.",
            }
        )

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Process failed: {exc}")
        try:
            video_id = req.video_id or "unknown"
            conn = init_db(DB_PATH)
            save_job(conn, video_id, {"status": "error", "error": str(exc)})
            conn.close()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Process failed: {exc}")


@router.post("/trim", summary="Trim a video")
async def trim_video(req: TrimRequest):
    """Trim video to [start, end] seconds."""
    try:
        video_path = _resolve_video_path(req.video_path)
        output = _output_path()

        from backend.video_processor import VideoProcessor

        vp = VideoProcessor(video_path)
        result = vp.trim_video(req.start, req.end, output)

        return JSONResponse(
            {
                "success": True,
                "output_path": result,
                "output_url": f"/api/download/{Path(result).name}",
                "start": req.start,
                "end": req.end,
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/effect", summary="Apply a visual effect")
async def apply_effect(req: EffectRequest):
    """Apply a visual effect to a video."""
    try:
        video_path = _resolve_video_path(req.video_path)
        output = _output_path()

        from backend.editing_engine import MoviePyEngine

        with MoviePyEngine(video_path) as engine:
            engine.apply_effect(output, req.effect_id, req.params or {})

        return JSONResponse(
            {
                "success": True,
                "output_path": output,
                "output_url": f"/api/download/{Path(output).name}",
                "effect_id": req.effect_id,
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/subtitles", summary="Add subtitles to a video")
async def add_subtitles(req: SubtitleRequest):
    """Burn subtitles into a video."""
    try:
        video_path = _resolve_video_path(req.video_path)
        output = _output_path()

        from backend.video_processor import VideoProcessor

        vp = VideoProcessor(video_path)
        subtitle_data = [s.dict() for s in req.segments]
        vp.add_subtitles(
            subtitle_file="",
            output_path=output,
            style_preset=req.style_preset,
            subtitle_data=subtitle_data,
        )

        return JSONResponse(
            {
                "success": True,
                "output_path": output,
                "output_url": f"/api/download/{Path(output).name}",
                "subtitle_count": len(req.segments),
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/concatenate", summary="Concatenate video segments")
async def concatenate_segments(req: ConcatenateRequest):
    """Concatenate multiple time segments from one video."""
    try:
        video_path = _resolve_video_path(req.video_path)
        output = _output_path()

        from backend.editing_engine import MoviePyEngine

        segments = [(s["start"], s["end"]) for s in req.segments]
        with MoviePyEngine(video_path) as engine:
            engine.concatenate(segments, output, transition=req.transition)

        return JSONResponse(
            {
                "success": True,
                "output_path": output,
                "output_url": f"/api/download/{Path(output).name}",
                "segment_count": len(req.segments),
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
