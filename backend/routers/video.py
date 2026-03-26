"""
Video Router
============
Handles video metadata, info, and transform operations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = ROOT_DIR / "data" / "uploads"
OUTPUTS_DIR = ROOT_DIR / "data" / "outputs"


# ── Request Models ────────────────────────────────────────────────────────────


class VideoTransformRequest(BaseModel):
    video_path: str
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    rotation: int = 0
    flip_horizontal: bool = False
    resize_mode: str = "fit"


class VideoResizeRequest(BaseModel):
    video_path: str
    platform: str = Field(
        description="Target platform: instagram-reel, tiktok, youtube-short, instagram-post"
    )


class VideoInfoRequest(BaseModel):
    video_path: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_video_path(video_path: str) -> str:
    """Resolve video path — check uploads dir if relative path given."""
    p = Path(video_path)
    if p.is_absolute() and p.exists():
        return str(p)
    candidate = UPLOADS_DIR / Path(video_path).name
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError(f"Video not found: {video_path}")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", summary="Video endpoint status")
async def video_index():
    return {
        "status": "ok",
        "router": "video",
        "endpoints": ["info", "transform", "resize"],
    }


@router.get("/info", summary="Get video metadata from path query param")
async def get_video_info_query(path: str):
    """Get video metadata (GET with query param)."""
    try:
        video_path = _resolve_video_path(path)
        from backend.video_processor import VideoProcessor

        vp = VideoProcessor(video_path)
        info = vp.get_video_info()
        return JSONResponse({"success": True, **info})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/info", summary="Get video metadata")
async def get_video_info(req: VideoInfoRequest):
    """Get video metadata including duration, resolution, codecs."""
    try:
        video_path = _resolve_video_path(req.video_path)
        from backend.video_processor import VideoProcessor

        vp = VideoProcessor(video_path)
        info = vp.get_video_info()
        return JSONResponse({"success": True, **info})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transform", summary="Transform video (resize, rotate, flip)")
async def transform_video(req: VideoTransformRequest):
    """
    Apply resize, rotation, and flip transformations to a video.

    resize_mode options:
      - "fit"       — preserve full frame with padding
      - "crop"      — center-crop fill
      - "smart_crop" — head-tracked crop
      - "fit_blur"  — blurred background + centered foreground
    """
    try:
        video_path = _resolve_video_path(req.video_path)
        import uuid

        output = str(OUTPUTS_DIR / f"{uuid.uuid4().hex}.mp4")

        from backend.video_processor import VideoProcessor

        vp = VideoProcessor(video_path)
        result = vp.transform_video(
            output_path=output,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
            rotation=req.rotation,
            flip_horizontal=req.flip_horizontal,
            resize_mode=req.resize_mode,
        )

        return JSONResponse(
            {
                "success": True,
                "output_path": result,
                "output_url": f"/api/download/{Path(result).name}",
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Transform failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/resize", summary="Resize video for social media platform")
async def resize_for_platform(req: VideoResizeRequest):
    """
    Resize video for a specific social media platform.

    Supported platforms:
      - instagram-reel (1080x1920)
      - tiktok (1080x1920)
      - youtube-short (1080x1920)
      - instagram-post (1080x1080)
    """
    try:
        video_path = _resolve_video_path(req.video_path)
        import uuid

        output = str(OUTPUTS_DIR / f"{uuid.uuid4().hex}.mp4")

        from backend.video_processor import VideoProcessor

        vp = VideoProcessor(video_path)
        result = vp.resize_for_platform(req.platform, output)

        return JSONResponse(
            {
                "success": True,
                "output_path": result,
                "output_url": f"/api/download/{Path(result).name}",
                "platform": req.platform,
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
