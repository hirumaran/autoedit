"""
Export Router
=============
Handles video export — final rendering and format conversion.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = ROOT_DIR / "data" / "uploads"
OUTPUTS_DIR = ROOT_DIR / "data" / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Request Models ────────────────────────────────────────────────────────────


class ExportRequest(BaseModel):
    video_path: str
    format: str = "mp4"
    quality: str = "high"  # low, medium, high
    resolution: Optional[str] = None  # e.g., "1080x1920"
    fps: Optional[float] = None
    include_audio: bool = True


class ViralExportRequest(BaseModel):
    video_path: str
    music_id: Optional[str] = None
    music_path: Optional[str] = None
    style_preset: str = "sleek"
    volume_level: float = 0.3
    is_preview: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_video_path(video_path: str) -> str:
    p = Path(video_path)
    if p.is_absolute() and p.exists():
        return str(p)
    candidate = UPLOADS_DIR / Path(video_path).name
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError(f"Video not found: {video_path}")


def _output_path(ext: str = ".mp4") -> str:
    return str(OUTPUTS_DIR / f"{uuid.uuid4().hex}{ext}")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/", summary="Export endpoint status")
async def export_index():
    return {"status": "ok", "router": "export", "endpoints": ["render", "viral"]}


@router.post("/render", summary="Render/export video")
async def render_video(req: ExportRequest):
    """
    Export/render a video with specified format and quality settings.
    """
    try:
        video_path = _resolve_video_path(req.video_path)
        output = _output_path(f".{req.format}")

        # Quality presets
        presets = {
            "low": {"preset": "ultrafast", "crf": "28"},
            "medium": {"preset": "fast", "crf": "23"},
            "high": {"preset": "medium", "crf": "18"},
        }
        quality = presets.get(req.quality, presets["high"])

        import subprocess

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-c:v",
            "libx264",
            "-preset",
            quality["preset"],
            "-crf",
            quality["crf"],
        ]

        if req.resolution:
            w, h = req.resolution.split("x")
            cmd.extend(["-vf", f"scale={w}:{h}"])

        if req.fps:
            cmd.extend(["-r", str(req.fps)])

        if req.include_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.extend(["-an"])

        cmd.append(output)
        subprocess.run(cmd, check=True, capture_output=True)

        logger.info(f"📤 Exported: {output}")
        return JSONResponse(
            {
                "success": True,
                "output_path": output,
                "output_url": f"/api/download/{Path(output).name}",
                "format": req.format,
                "quality": req.quality,
            }
        )

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Export failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/viral", summary="Export video with viral audio edit")
async def export_viral(req: ViralExportRequest):
    """
    Export a video with viral audio editing (background music + ducking).

    Uses the ViralEditor service to add background music with smart ducking
    around speech segments.
    """
    try:
        video_path = _resolve_video_path(req.video_path)

        audio_path = None
        if req.music_path:
            audio_path = _resolve_video_path(req.music_path)
        elif req.music_id:
            from backend.services.music_agent import MusicAgent

            agent = MusicAgent(
                db_path=ROOT_DIR / "data" / "jobs.db",
                music_dir=ROOT_DIR / "data" / "music",
            )
            audio_path = agent.download_track(req.music_id)
            if audio_path:
                audio_path = str(audio_path)

        if not audio_path:
            raise HTTPException(
                status_code=400, detail="No music provided. Set music_id or music_path."
            )

        # Get transcription segments for ducking
        transcript_segments = []
        try:
            from backend.services.transcription import transcription_service

            result = transcription_service.transcribe(video_path)
            transcript_segments = result.get("segments", [])
        except Exception:
            pass

        # Use viral editor
        from backend.services.viral_editor import ViralEditor
        from backend.services.music_agent import MusicAgent

        music_agent = MusicAgent(
            db_path=ROOT_DIR / "data" / "jobs.db",
            music_dir=ROOT_DIR / "data" / "music",
        )
        editor = ViralEditor(music_agent=music_agent, output_dir=OUTPUTS_DIR)

        result = editor.apply_viral_edit(
            video_path=video_path,
            audio_track_id=req.music_id or "custom",
            transcript_segments=transcript_segments,
            volume_level=req.volume_level,
            is_preview=req.is_preview,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Viral edit failed")
            )

        output_path = result["output_path"]
        return JSONResponse(
            {
                "success": True,
                "output_path": output_path,
                "output_url": f"/api/download/{Path(output_path).name}",
                "is_preview": req.is_preview,
            }
        )

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Viral export failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
