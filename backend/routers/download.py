"""
Download Router
===============
Handles downloading processed videos and checking job status.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = ROOT_DIR / "data" / "uploads"
OUTPUTS_DIR = ROOT_DIR / "data" / "outputs"
DB_PATH = ROOT_DIR / "data" / "jobs.db"


@router.get("/{filename}", summary="Download a processed video")
async def download_file(filename: str):
    """
    Serve a processed video file for download.

    Checks both outputs and uploads directories.
    """
    # Check outputs first, then uploads
    for directory in [OUTPUTS_DIR, UPLOADS_DIR]:
        file_path = directory / filename
        if file_path.exists():
            return FileResponse(
                str(file_path),
                media_type="video/mp4",
                filename=filename,
            )

    raise HTTPException(status_code=404, detail=f"File not found: {filename}")


@router.get("/status/{video_id}", summary="Check processing status")
async def get_status(video_id: str):
    """
    Check the status of a video processing job.

    Returns job progress, current step, and output path when complete.
    """
    try:
        from backend.db import init_db

        conn = init_db(DB_PATH)
        cursor = conn.execute("SELECT data FROM jobs WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return JSONResponse(
                {
                    "video_id": video_id,
                    "status": "not_found",
                    "message": "No job found for this video ID",
                }
            )

        job = json.loads(row[0])
        return JSONResponse(
            {
                "video_id": video_id,
                "status": job.get("status", "unknown"),
                "progress": job.get("progress", 0),
                "current_step": job.get("current_step", ""),
                "output_path": job.get("output_path"),
                "output_url": job.get("output_url"),
                "error": job.get("error"),
            }
        )

    except Exception as exc:
        logger.error(f"Status check failed: {exc}")
        return JSONResponse(
            {
                "video_id": video_id,
                "status": "error",
                "error": str(exc),
            }
        )


@router.post("/status/{video_id}", summary="Update job status")
async def update_status(video_id: str, status_data: dict):
    """
    Update the status of a video processing job.
    Internal use — called by processing workers.
    """
    try:
        from backend.db import init_db, save_job

        conn = init_db(DB_PATH)

        # Load existing job or create new
        cursor = conn.execute("SELECT data FROM jobs WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        if row:
            job = json.loads(row[0])
            job.update(status_data)
        else:
            job = {"video_id": video_id, **status_data}

        save_job(conn, video_id, job)
        conn.close()

        return JSONResponse({"success": True, "video_id": video_id})

    except Exception as exc:
        logger.error(f"Status update failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
