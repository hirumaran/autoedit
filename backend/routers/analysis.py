"""
Analysis Router
===============
Handles video analysis — transcription, AI vision, virality scoring.
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
DB_PATH = ROOT_DIR / "data" / "jobs.db"


# ── Request Models ────────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    video_path: str
    prompt: str = ""
    include_virality: bool = True
    include_transcription: bool = True


class ViralityRequest(BaseModel):
    video_path: str
    transcript: str
    duration_seconds: float
    prompt: str = ""


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


@router.get("/", summary="Analysis endpoint status")
async def analysis_index():
    return {
        "status": "ok",
        "router": "analysis",
        "endpoints": ["analyze", "virality", "transcribe"],
    }


@router.post("/analyze", summary="Full video analysis")
async def analyze_video(req: AnalyzeRequest):
    """
    Run full video analysis including:
    - Transcription (WhisperX)
    - Phase 1 enrichment (OCR, faces, logos)
    - Virality scoring
    - AI content analysis (Florence-2)
    """
    try:
        video_path = _resolve_video_path(req.video_path)

        result = {}

        # Transcription
        if req.include_transcription:
            try:
                from backend.services.transcription import transcription_service

                transcription = transcription_service.transcribe(video_path)
                result["transcription"] = transcription
            except Exception as exc:
                logger.warning(f"Transcription failed: {exc}")
                result["transcription"] = {"error": str(exc)}

        # Virality scoring
        if req.include_virality and "transcription" in result:
            try:
                from backend.virality.scorer import compute_virality_score

                transcript_text = result["transcription"].get("text", "")
                segments = result["transcription"].get("segments", [])

                from backend.video_processor import VideoProcessor

                vp = VideoProcessor(video_path)
                duration = vp.duration

                virality = compute_virality_score(
                    video_path=video_path,
                    transcript=transcript_text,
                    duration_seconds=duration,
                    prompt=req.prompt,
                    subtitle_data=segments,
                )
                result["virality"] = virality
            except Exception as exc:
                logger.warning(f"Virality scoring failed: {exc}")
                result["virality"] = {"error": str(exc)}

        # Phase 1 analysis
        try:
            from backend.phase1_pipeline import PhaseOneAnalyzer
            from pathlib import Path as P

            analyzer = PhaseOneAnalyzer(temp_dir=P(ROOT_DIR / "data" / "temp"))
            phase1 = analyzer.process(video_path)
            result["phase1"] = phase1.to_dict()
        except Exception as exc:
            logger.warning(f"Phase 1 analysis failed: {exc}")
            result["phase1"] = {"error": str(exc)}

        return JSONResponse({"success": True, **result})

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Analysis failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{video_id}", summary="Get analysis results for a video ID")
async def get_analysis(video_id: str):
    """Retrieve cached analysis results for a video."""
    try:
        from backend.db import init_db
        import json

        conn = init_db(DB_PATH)
        cursor = conn.execute("SELECT data FROM jobs WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            raise HTTPException(
                status_code=404, detail=f"No analysis found for video: {video_id}"
            )

        job = json.loads(row[0])
        return JSONResponse(
            {
                "video_id": video_id,
                "analysis": job.get("analysis", {}),
                "status": job.get("status", "unknown"),
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/virality", summary="Score video virality")
async def score_virality(req: ViralityRequest):
    """
    Calculate virality score for a video based on content, trends, and engagement signals.
    """
    try:
        video_path = _resolve_video_path(req.video_path)

        from backend.virality.scorer import compute_virality_score

        result = compute_virality_score(
            video_path=video_path,
            transcript=req.transcript,
            duration_seconds=req.duration_seconds,
            prompt=req.prompt,
        )

        return JSONResponse({"success": True, **result})

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Virality scoring failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transcribe", summary="Transcribe a video")
async def transcribe_video(req: AnalyzeRequest):
    """Transcribe video audio to text with timestamps."""
    try:
        video_path = _resolve_video_path(req.video_path)

        from backend.services.transcription import transcription_service

        result = transcription_service.transcribe(video_path)

        return JSONResponse({"success": True, "transcription": result})

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Transcription failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
