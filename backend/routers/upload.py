"""
Upload Router
=============
Handles video file uploads via multipart form data.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = ROOT_DIR / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Allowed video extensions
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB


@router.post("/", summary="Upload a video file")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file for processing.

    Accepts: MP4, MOV, AVI, MKV, WEBM, FLV, WMV
    Max size: 500 MB

    Returns the video_id and file path for subsequent API calls.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Generate unique video ID
    video_id = uuid.uuid4().hex[:12]
    safe_filename = f"{video_id}{ext}"
    dest_path = UPLOADS_DIR / safe_filename

    try:
        # Stream file to disk
        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                buffer.write(chunk)

        file_size = dest_path.stat().st_size
        logger.info(
            f"📥 Uploaded {file.filename} → {dest_path} ({file_size / 1e6:.1f} MB)"
        )

        return JSONResponse(
            {
                "success": True,
                "video_id": video_id,
                "filename": file.filename,
                "path": str(dest_path),
                "size_bytes": file_size,
            }
        )

    except Exception as exc:
        logger.error(f"Upload failed: {exc}")
        # Clean up partial file
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")
