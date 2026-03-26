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
    video_path: str
    effects: Optional[List[Dict]] = None
    music_path: Optional[str] = None
    subtitles: Optional[List[Dict]] = None
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    style_preset: str = "sleek"
    resolution: Optional[str] = None


class ProcessRequest(BaseModel):
    video_path: str
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
    # Try in uploads dir
    candidate = UPLOADS_DIR / Path(video_path).name
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
    Render the final edited video with all effects, music, subtitles applied.
    This produces the full-quality output for download/sharing.
    """
    try:
        video_path = _resolve_video_path(req.video_path)
        output = _output_path()

        from backend.video_processor import VideoProcessor

        # Step 1: Trim if requested
        current_path = video_path
        if req.trim_start is not None and req.trim_end is not None:
            trim_output = _output_path()
            vp = VideoProcessor(current_path)
            current_path = vp.trim_video(req.trim_start, req.trim_end, trim_output)

        # Step 2: Apply effects chain
        if req.effects:
            from backend.services.effects_library import moviepy_effect_processor

            for eff in req.effects:
                effect_output = _output_path()
                eff_id = eff.get("id", "")
                eff_params = eff.get("params", {})
                moviepy_effect_processor.apply_effect_to_file(
                    current_path, effect_output, eff_id, eff_params
                )
                current_path = effect_output

        # Step 3: Add subtitles
        if req.subtitles:
            sub_output = _output_path()
            vp = VideoProcessor(current_path)
            subtitle_data = [
                s if isinstance(s, dict) else s.dict() for s in req.subtitles
            ]
            current_path = vp.add_subtitles(
                subtitle_file="",  # Not used when subtitle_data provided
                output_path=sub_output,
                style_preset=req.style_preset,
                subtitle_data=subtitle_data,
            )

        # Step 4: Mix music
        if req.music_path:
            music_output = _output_path()
            from backend.editing_engine import MoviePyAudioEngine

            with MoviePyAudioEngine(req.music_path) as aeng:
                aeng.mix_with_ducking(
                    video_path=current_path,
                    output_path=music_output,
                    is_preview=False,
                )
            current_path = music_output

        # Step 5: Copy final output
        import shutil

        if current_path != output:
            shutil.copy(current_path, output)

        logger.info(f"🎬 Render complete: {output}")
        return JSONResponse(
            {
                "success": True,
                "output_path": output,
                "output_url": f"/api/download/{Path(output).name}",
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
    Process a video either with an AI instruction or manual edit parameters.

    If `instruction` is provided, uses the VideoEditingAgent to interpret it.
    Otherwise applies the specified effects/subtitles/music directly.
    """
    try:
        video_path = _resolve_video_path(req.video_path)

        if req.instruction:
            # Use AI agent
            from backend.video_agent import VideoEditingAgent

            agent = VideoEditingAgent()
            result = agent.run(
                video_path=video_path,
                instruction=req.instruction,
                subtitle_data=req.subtitles,
                audio_path=None,
            )
            return JSONResponse(result)

        # Manual processing — chain operations
        current_path = video_path

        # Apply trim
        if req.trim:
            trim_output = _output_path()
            from backend.video_processor import VideoProcessor

            vp = VideoProcessor(current_path)
            start = req.trim.get("start", 0)
            end = req.trim.get("end", vp.duration)
            current_path = vp.trim_video(start, end, trim_output)

        # Apply effects
        if req.effects:
            from backend.services.effects_library import moviepy_effect_processor

            for eff_id in req.effects:
                effect_output = _output_path()
                moviepy_effect_processor.apply_effect_to_file(
                    current_path, effect_output, eff_id
                )
                current_path = effect_output

        # Add subtitles
        if req.subtitles:
            sub_output = _output_path()
            from backend.video_processor import VideoProcessor

            vp = VideoProcessor(current_path)
            current_path = vp.add_subtitles(
                subtitle_file="",
                output_path=sub_output,
                subtitle_data=req.subtitles,
            )

        return JSONResponse(
            {
                "success": True,
                "output_path": current_path,
                "output_url": f"/api/download/{Path(current_path).name}",
            }
        )

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Process failed: {exc}")
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
