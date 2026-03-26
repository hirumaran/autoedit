"""
Music Router
============
Handles music search, recommendations, download, and selection.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MUSIC_DIR = ROOT_DIR / "data" / "music"
DB_PATH = ROOT_DIR / "data" / "jobs.db"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)


# ── Request Models ────────────────────────────────────────────────────────────


class MusicSearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Search query")
    limit: int = Field(default=10, ge=1, le=50)


class MusicRecommendRequest(BaseModel):
    prompt: str = Field(description="Description of desired music style/mood")
    video_analysis: Optional[dict] = None


class MusicSelectRequest(BaseModel):
    track_id: str = Field(description="Track ID to download/select")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", summary="List available music tracks")
async def list_music():
    """List all cached/downloaded music tracks."""
    try:
        from backend.db import init_db, load_jobs

        conn = init_db(DB_PATH)

        tracks = []
        cursor = conn.execute(
            "SELECT track_id, title, artist, duration, temperature, mood_tags, local_path FROM music_cache"
        )
        for row in cursor.fetchall():
            tracks.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "artist": row[2],
                    "duration": row[3],
                    "temperature": row[4],
                    "mood_tags": row[5],
                    "local_path": row[6],
                    "downloaded": row[6] is not None and Path(row[6]).exists()
                    if row[6]
                    else False,
                }
            )
        conn.close()

        return JSONResponse({"tracks": tracks, "count": len(tracks)})

    except Exception as exc:
        logger.error(f"List music failed: {exc}")
        return JSONResponse({"tracks": [], "count": 0})


@router.post("/search", summary="Search for music")
async def search_music(req: MusicSearchRequest):
    """Search YouTube Music for tracks matching the query."""
    try:
        from backend.services.music_agent import MusicAgent

        agent = MusicAgent(db_path=DB_PATH, music_dir=MUSIC_DIR)
        results = agent.search_music(req.query, limit=req.limit)

        return JSONResponse(
            {
                "success": True,
                "results": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "artist": t.artist,
                        "duration": t.duration,
                        "temperature": t.temperature,
                        "mood_tags": t.mood_tags,
                        "thumbnail_url": t.thumbnail_url,
                        "source": t.source,
                    }
                    for t in results
                ],
                "count": len(results),
            }
        )

    except Exception as exc:
        logger.error(f"Music search failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}")


@router.post("/recommend", summary="Get AI music recommendations")
async def recommend_music(req: MusicRecommendRequest):
    """Get AI-powered music recommendations based on prompt and video analysis."""
    try:
        from backend.services.music_agent import MusicAgent

        agent = MusicAgent(db_path=DB_PATH, music_dir=MUSIC_DIR)
        results = agent.recommend_music(
            prompt=req.prompt,
            video_analysis=req.video_analysis or {},
        )

        return JSONResponse(
            {
                "success": True,
                "recommendations": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "artist": t.artist,
                        "duration": t.duration,
                        "temperature": t.temperature,
                        "mood_tags": t.mood_tags,
                        "thumbnail_url": t.thumbnail_url,
                        "source": t.source,
                    }
                    for t in results
                ],
                "count": len(results),
            }
        )

    except Exception as exc:
        logger.error(f"Music recommendation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {exc}")


@router.post("/select", summary="Select and download a music track")
async def select_music(req: MusicSelectRequest):
    """Download a track by ID and return its local path."""
    try:
        from backend.services.music_agent import MusicAgent

        agent = MusicAgent(db_path=DB_PATH, music_dir=MUSIC_DIR)
        local_path = agent.download_track(req.track_id)

        if local_path is None:
            raise HTTPException(
                status_code=404, detail=f"Could not download track: {req.track_id}"
            )

        return JSONResponse(
            {
                "success": True,
                "track_id": req.track_id,
                "local_path": str(local_path),
                "download_url": f"/api/music/file/{local_path.name}",
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Music select failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Select failed: {exc}")


@router.post("/upload", summary="Upload a custom music file")
async def upload_music(file: UploadFile = File(...)):
    """Upload a custom audio file (MP3, WAV, M4A) for use as background music."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type '{ext}'. Allowed: .mp3, .wav, .m4a, .ogg, .flac",
        )

    import uuid

    track_id = uuid.uuid4().hex[:12]
    safe_filename = f"custom_{track_id}{ext}"
    dest_path = MUSIC_DIR / safe_filename

    try:
        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)

        # Cache in DB
        from backend.db import init_db

        conn = init_db(DB_PATH)
        conn.execute(
            """INSERT INTO music_cache (track_id, title, artist, duration, temperature, mood_tags, local_path, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(track_id) DO UPDATE SET local_path=excluded.local_path""",
            (
                track_id,
                file.filename,
                "Custom Upload",
                0,
                0,
                "[]",
                str(dest_path),
                "{}",
            ),
        )
        conn.commit()
        conn.close()

        logger.info(f"🎵 Uploaded music: {file.filename} → {dest_path}")
        return JSONResponse(
            {
                "success": True,
                "track_id": track_id,
                "filename": file.filename,
                "local_path": str(dest_path),
                "download_url": f"/api/music/file/{dest_path.name}",
            }
        )

    except Exception as exc:
        logger.error(f"Music upload failed: {exc}")
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")


@router.get("/file/{filename}", summary="Stream a music file")
async def get_music_file(filename: str):
    """Serve a music file from the music directory."""
    file_path = MUSIC_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Music file not found")
    return FileResponse(str(file_path))


@router.post("/agent/recommend", summary="AI agent music recommendation")
async def agent_recommend(req: MusicRecommendRequest):
    """Alias for /recommend — used by frontend agent workflow."""
    return await recommend_music(req)


@router.post("/agent/select", summary="AI agent music selection")
async def agent_select(req: MusicSelectRequest):
    """Alias for /select — used by frontend agent workflow."""
    return await select_music(req)
