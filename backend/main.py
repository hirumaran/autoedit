from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
import os
import re
import sqlite3
import uuid
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import json
from typing import Optional, List, Dict
from datetime import datetime
from dataclasses import asdict
from collections import defaultdict
import time
import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

# Rate Limiting (simple in-memory implementation)
class RateLimiter:
    """Simple in-memory rate limiter."""
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        # Clean old requests
        self.requests[client_id] = [t for t in self.requests[client_id] if t > minute_ago]
        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False
        self.requests[client_id].append(now)
        return True

rate_limiter = RateLimiter(requests_per_minute=60)

# Security: Input sanitization helpers
def sanitize_filename(filename: str) -> str:
    """Remove potentially dangerous characters from filenames."""
    # Keep only alphanumeric, dots, hyphens, and underscores
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    # Prevent directory traversal
    sanitized = sanitized.replace('..', '_')
    # Limit length
    return sanitized[:100]

def sanitize_prompt(prompt: str) -> str:
    """Sanitize user prompts to prevent injection."""
    if not prompt:
        return ""
    # Remove potential shell/SQL injection characters
    sanitized = re.sub(r'[;$`\\|<>]', '', prompt)
    # Limit length to prevent memory abuse
    return sanitized[:1000]

MAX_UPLOAD_SIZE_MB = 100
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # 100MB

# Import our custom modules
from video_processor import VideoProcessor, SUBTITLE_STYLE_MAP
from phase1_pipeline import PhaseOneAnalyzer
from ai_analyzer import AIVideoAnalyzer
from routes.transcribe import router as transcribe_router
from db import init_db, load_jobs, save_job
from services.smart_subtitles import smart_subtitle_service
from services.music import music_library

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def resolve_dir(env_name: str, default: Path) -> Path:
    """Resolve directories from env vars or fall back to repo-relative defaults."""
    value = os.getenv(env_name)
    if value:
        return Path(value).expanduser().resolve()
    return default.resolve()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan — replaces @app.on_event("startup"/"shutdown").
    Uses asynccontextmanager so Ctrl+C triggers clean shutdown without
    asyncio.CancelledError spam in the log.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    # Fix SSL certs immediately (before any outbound request)
    try:
        from backend.utils.model_downloader import fix_macos_ssl
        fix_macos_ssl()
    except Exception:
        pass

    # Initialize all services that DON'T need the model
    # (VideoAnalyzer now lazy-loads Florence-2 on first use)
    try:
        from backend.services import initialize_services
        initialize_services()
    except Exception as exc:
        logger.error(f"Service init error (non-fatal): {exc}")

    logger.info("✅ Services ready!")
    yield   # ← app runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    # Suppress the CancelledError that uvicorn raises on SIGINT
    with contextlib.suppress(asyncio.CancelledError, Exception):
        logger.info("🛑 Shutting down services...")


app = FastAPI(title="AI Video Editor MVP", lifespan=lifespan)
app.include_router(transcribe_router, prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = resolve_dir("UPLOAD_DIR", BASE_DIR / "data" / "uploads")
OUTPUT_DIR = resolve_dir("OUTPUT_DIR", BASE_DIR / "data" / "outputs")  # legacy path
MEDIA_DIR = resolve_dir("MEDIA_DIR", BASE_DIR / "data" / "media")
TEMP_DIR = resolve_dir("TEMP_DIR", BASE_DIR / "data" / "temp")
FRONTEND_DIR = resolve_dir("FRONTEND_DIR", BASE_DIR / "frontend")
DB_PATH = resolve_dir("JOBS_DB", BASE_DIR / "data" / "jobs.db")

for dir_path in [UPLOAD_DIR, OUTPUT_DIR, MEDIA_DIR, TEMP_DIR, DB_PATH.parent]:
    dir_path.mkdir(parents=True, exist_ok=True)

if not FRONTEND_DIR.exists():
    raise RuntimeError(f"Frontend directory not found: {FRONTEND_DIR}")


class SPAStaticFiles(StaticFiles):
    """Serve the SPA while gracefully rejecting non-HTTP scopes (e.g., WebSockets)."""

    async def __call__(self, scope, receive, send):  # type: ignore[override]
        if scope["type"] != "http":
            response = PlainTextResponse("Not found", status_code=404)
            await response(scope, receive, send)
            return
        await super().__call__(scope, receive, send)

# Initialize services (load once at startup)
print("🔧 Initializing services...")
phase_analyzer = PhaseOneAnalyzer(temp_dir=TEMP_DIR)
ai_analyzer = AIVideoAnalyzer()
print("✅ Services ready!")

# Simple in-memory job tracking with SQLite persistence
conn = init_db(DB_PATH)
jobs = load_jobs(conn)
conn.close()

class CustomSegment(BaseModel):
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    
    @field_validator('end')
    @classmethod
    def end_must_be_after_start(cls, v, info):
        if 'start' in info.data and v <= info.data['start']:
            raise ValueError('end must be greater than start')
        return v

class ProcessRequest(BaseModel):
    video_id: str = Field(..., min_length=1, max_length=20, pattern=r'^[a-zA-Z0-9\-]+$')
    user_prompt: Optional[str] = Field(default="Make this video engaging for social media", max_length=1000)
    add_subtitles: bool = True
    trim_boring_parts: bool = True
    custom_segments: Optional[List[CustomSegment]] = Field(default=None, max_length=100)
    style_preset: Optional[str] = Field(default="sleek", pattern=r'^[a-zA-Z]+$', max_length=20)
    manual_transcript: Optional[str] = Field(default=None, max_length=50000)
    
    # New UI fields mapped from frontend payload
    platform: Optional[str] = None
    format: Optional[str] = None
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    
    @field_validator('user_prompt')
    @classmethod
    def sanitize_user_prompt(cls, v):
        return sanitize_prompt(v) if v else v
    
    @field_validator('manual_transcript')
    @classmethod  
    def sanitize_transcript(cls, v):
        if v:
            # Basic sanitization for transcript
            return re.sub(r'[<>]', '', v)[:50000]
        return v


def get_style_for_preset(preset: Optional[str]) -> Dict:
    preset_key = (preset or "sleek").lower()
    return SUBTITLE_STYLE_MAP.get(preset_key, SUBTITLE_STYLE_MAP["sleek"])


def format_timestamp(seconds: float) -> str:
    """Convert float seconds to SRT timestamp."""
    total_ms = max(int(round(seconds * 1000)), 0)
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def write_srt_from_captions(caption_doc: Dict, path: Path) -> Path:
    """Persist a simple SRT file from the prepared caption document."""
    lines = []
    for idx, cap in enumerate(caption_doc.get("captions", []), start=1):
        text = (cap.get("text") or "").strip()
        if not text:
            continue
        start_ts = format_timestamp(cap.get("start", 0.0))
        end_ts = format_timestamp(cap.get("end", 0.0))
        lines.extend([str(idx), f"{start_ts} --> {end_ts}", text, ""])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def synthesize_segments_from_transcript(text: str, duration: float) -> List[Dict]:
    """Split manual transcript into timed segments across the video duration."""
    text = (text or "").strip()
    if not text:
        return []

    # Naive sentence split; fallback to lines.
    import re

    parts = [p.strip() for p in re.split(r"[.!?]\s+|\n+", text) if p.strip()]
    if not parts:
        parts = [text]

    total = max(duration, 1.0)
    slice_len = total / len(parts)
    segments = []
    for idx, part in enumerate(parts):
        start = round(idx * slice_len, 3)
        end = round(start + slice_len, 3)
        segments.append({
            "start": start,
            "end": end,
            "text": part,
            "speaker": "SPEAKER_00",
            "words": []
        })
    return segments


def build_caption_document(
    video_id: str,
    style_preset: str,
    transcript_segments: List[Dict],
    keep_ranges: List[Dict[str, float]]
) -> Dict:
    """Generate caption metadata aligned with the trimmed clip timeline."""
    normalized_ranges = []
    for rng in sorted(keep_ranges, key=lambda r: r.get("start", 0)):
        start = max(0.0, float(rng.get("start", 0)))
        end = max(0.0, float(rng.get("end", 0)))
        if end > start:
            normalized_ranges.append({"start": start, "end": end})

    if not normalized_ranges:
        total_duration = transcript_segments[-1]["end"] if transcript_segments else 0.0
        normalized_ranges = [{"start": 0.0, "end": total_duration}]

    captions = []
    offset = 0.0

    for rng in normalized_ranges:
        rng_start = rng["start"]
        rng_end = rng["end"]
        for seg in transcript_segments:
            seg_start = seg.get("start", 0.0)
            seg_end = seg.get("end", 0.0)
            if seg_end <= rng_start or seg_start >= rng_end:
                continue
            clip_start = max(seg_start, rng_start)
            clip_end = min(seg_end, rng_end)
            text = seg.get("text", "").strip()
            if not text:
                continue
            rel_start = clip_start - rng_start + offset
            rel_end = clip_end - rng_start + offset
            words = []
            for word in seg.get("words", []) or []:
                w_start = word.get("start", 0.0)
                w_end = word.get("end", 0.0)
                if w_end <= rng_start or w_start >= rng_end:
                    continue
                adj_start = max(w_start, rng_start)
                adj_end = min(w_end, rng_end)
                words.append({
                    "start": round(adj_start - rng_start + offset, 3),
                    "end": round(adj_end - rng_start + offset, 3),
                    "text": (word.get("text") or word.get("word") or "").strip()
                })
            captions.append({
                "id": f"c{len(captions) + 1}",
                "start": round(rel_start, 3),
                "end": round(rel_end, 3),
                "text": text,
                "words": words,
                "layout": {"x": 0.5, "y": 0.82, "anchor": "center"}
            })
        offset += rng_end - rng_start

    total_duration = sum(rng["end"] - rng["start"] for rng in normalized_ranges)
    return {
        "videoId": video_id,
        "duration": round(total_duration, 3),
        "stylePreset": (style_preset or "sleek"),
        "captions": captions
    }


def video_dir_for(video_id: str) -> Path:
    d = MEDIA_DIR / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def persist_job(video_id: str):
    if video_id in jobs:
        jobs[video_id]["updated_at"] = datetime.utcnow().isoformat()
        # Use a fresh connection to avoid threading issues
        with sqlite3.connect(DB_PATH) as local_conn:
            save_job(local_conn, video_id, jobs[video_id])

@app.get("/api")
async def api_root():
    return {
        "status": "running",
        "message": "AI Video Editor MVP",
        "endpoints": {
            "upload": "POST /api/upload",
            "process": "POST /api/process",
            "status": "GET /api/status/{video_id}",
            "download": "GET /api/download/{video_id}"
        }
    }

@app.post("/api/upload")
async def upload_video(request: Request, file: UploadFile = File(...)):
    """Upload a video file with rate limiting and size validation."""
    # Rate limiting check
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    
    try:
        # Validate file extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        safe_filename = sanitize_filename(file.filename)
        file_extension = safe_filename.split('.')[-1].lower()
        
        allowed_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v'}
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique ID
        video_id = str(uuid.uuid4())[:8]
        video_dir = video_dir_for(video_id)
        file_path = video_dir / f"original.{file_extension}"
        
        # Save file with size check
        file_size = 0
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # Read in 1MB chunks
                file_size += len(chunk)
                if file_size > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    file_path.unlink(missing_ok=True)  # Clean up partial file
                    raise HTTPException(
                        status_code=413, 
                        detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE_MB}MB"
                    )
                buffer.write(chunk)
        
        # Initialize job
        jobs[video_id] = {
            "status": "uploaded",
            "filename": safe_filename,
            "size": file_size,
            "video_id": video_id,
            "video_dir": str(video_dir),
            "input_path": str(file_path),
            "output_path": str(video_dir / "final.mp4"),
            "captions_path": str(video_dir / "captions.json"),
            "created_at": datetime.utcnow().isoformat()
        }
        persist_job(video_id)
        
        return {
            "success": True,
            "video_id": video_id,
            "filename": safe_filename,
            "size": file_size,
            "message": "Upload successful. Use video_id to process."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

class RenderRequest(BaseModel):
    video_id: str
    custom_segments: Optional[List[CustomSegment]] = None
    manual_transcript: Optional[str] = None
    style_preset: Optional[str] = "sleek"
    add_subtitles: bool = True
    add_music: bool = False
    music_file: Optional[str] = None  # Filename of selected music
    music_volume: float = 0.3  # 0.0 to 1.0
    
    # New UI fields mapped from frontend payload
    platform: Optional[str] = None
    format: Optional[str] = None
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    rotation: Optional[int] = 0
    flip_horizontal: Optional[bool] = False
    framing_mode: Optional[str] = "fit_blur"

@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Start video analysis (Phase 1)"""
    video_id = request.video_id
    if video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    jobs[video_id]["status"] = "processing"
    jobs[video_id]["progress"] = 0
    persist_job(video_id)
    
    background_tasks.add_task(
        analyze_video_pipeline,
        video_id,
        request.user_prompt,
        request.manual_transcript
    )
    
    return {
        "success": True,
        "video_id": video_id,
        "status": "processing",
        "message": "Analysis started."
    }

@app.post("/api/render")
async def render_video(request: RenderRequest, background_tasks: BackgroundTasks):
    """Start video rendering (Phase 2)"""
    video_id = request.video_id
    if video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    jobs[video_id]["status"] = "rendering"
    jobs[video_id]["progress"] = 50
    persist_job(video_id)
    
    background_tasks.add_task(
        render_video_pipeline,
        video_id,
        [segment.dict() for segment in request.custom_segments] if request.custom_segments else [],
        request.manual_transcript,
        request.style_preset,
        request.add_subtitles,
        request.add_music,
        request.music_file,
        request.music_volume,
        request.aspect_ratio,
        request.resolution,
        request.rotation or 0,
        request.flip_horizontal or False,
        (request.framing_mode or "fit_blur")
    )
    
    return {
        "success": True,
        "video_id": video_id,
        "status": "rendering",
        "message": "Rendering started."
    }

@app.get("/api/status/{video_id}")
async def get_status(video_id: str):
    """Get processing status"""
    if video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job = jobs[video_id]
    is_ready = job.get("status") == "completed"
    output_url = f"/api/download/{video_id}" if is_ready else None
    captions_url = f"/api/captions/{video_id}" if is_ready and job.get("captions_path") else None
    
    response = dict(job)
    response["output_url"] = output_url
    response["captions_url"] = captions_url
    return response

@app.get("/api/download/{video_id}")
async def download_video(video_id: str):
    """Download processed video"""
    job = jobs.get(video_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video not found")
    
    output_path = job.get("output_path")
    if job.get("status") != "completed" or not output_path:
        raise HTTPException(status_code=400, detail="Video not ready yet")
    
    output_path = Path(output_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    
    print(f"[PIPE] download request for {video_id}: {output_path}")
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"edited_{jobs[video_id].get('filename', 'video.mp4')}"
    )


@app.get("/api/captions/{video_id}")
async def get_captions(video_id: str):
    job = jobs.get(video_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video not found")

    captions_path = job.get("captions_path")
    if not captions_path:
        raise HTTPException(status_code=404, detail="Captions not generated yet")

    path = Path(captions_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Captions file missing")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(data)

@app.get("/api/analysis/{video_id}")
async def get_analysis(video_id: str):
    """Get AI analysis results"""
    if video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {
        "video_id": video_id,
        "transcript": jobs[video_id].get("transcript", ""),
        "ai_analysis": jobs[video_id].get("ai_analysis", {}),
        "edits_applied": jobs[video_id].get("edits_applied", [])
    }


# === Music Endpoints ===

@app.get("/api/music")
async def list_music(mood: Optional[str] = None, genre: Optional[str] = None):
    """List available background music files with filtering."""
    tracks = music_library.list_tracks(mood=mood, genre=genre)
    return {
        "success": True,
        "music": tracks,
        "count": len(tracks),
        "moods": music_library.get_moods(),
        "genres": music_library.get_genres()
    }

@app.get("/api/music/search")
async def search_music(query: str, genre: Optional[str] = None):
    """Search for new music (currently mocks FMA results)."""
    results = music_library.search_free_music_archive(query, genre)
    return {
        "success": True,
        "results": results,
        "source": "Free Music Archive (Mock)"
    }

@app.post("/api/music/upload")
async def upload_music(
    file: UploadFile = File(...), 
    title: Optional[str] = None,
    artist: Optional[str] = None,
    mood: Optional[str] = "neutral"
):
    """Upload a background music file with metadata."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        valid_extensions = [".mp3", ".wav", ".m4a", ".aac", ".ogg"]
        ext = Path(file.filename).suffix.lower()
        if ext not in valid_extensions:
            raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {valid_extensions}")
        
        content = await file.read()
        metadata = {
            "title": title or file.filename,
            "artist": artist or "Unknown",
            "mood": mood or "neutral"
        }
        
        track = music_library.add_track(file.filename, content, metadata)
        
        return {
            "success": True,
            "track": track,
            "message": "Music uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# === AI Music Agent Endpoints ===

from services.music_agent import MusicAgent, sync_audio_with_ducking
from services.trend_fetcher import TrendFetcher
from services.virality_rater import ViralityRater
from services.viral_editor import ViralEditor
from services.effects_library import effects_library, effect_processor
from services.effects_agent import effects_agent

MUSIC_DIR = resolve_dir("MUSIC_DIR", BASE_DIR / "data" / "music")
trend_fetcher = TrendFetcher(db_path=DB_PATH)
music_agent = MusicAgent(db_path=DB_PATH, music_dir=MUSIC_DIR)
virality_rater = ViralityRater(trend_fetcher)
viral_editor = ViralEditor(music_agent, OUTPUT_DIR)

class MusicRecommendRequest(BaseModel):
    video_id: Optional[str] = None
    prompt: str = "trending viral"

class MusicSelectRequest(BaseModel):
    track_id: str
    video_id: Optional[str] = None

@app.post("/api/music/agent/recommend")
async def recommend_music(request: MusicRecommendRequest):
    """Get AI-scored music recommendations."""
    video_analysis = {}
    if request.video_id and request.video_id in jobs:
        video_analysis = jobs[request.video_id]
    
    recommendations = music_agent.recommend_music(request.prompt, video_analysis, trend_fetcher=trend_fetcher)
    return {"success": True, "tracks": [asdict(t) for t in recommendations]}

@app.post("/api/trends/refresh")
async def refresh_trends(background_tasks: BackgroundTasks):
    """Trigger background refresh of trends."""
    background_tasks.add_task(trend_fetcher.fetch_trends, count=30)
    return {"status": "refreshing", "message": "Fetching latest TikTok trends in background"}

@app.post("/api/trends/rate")
async def rate_trends_endpoint(request: MusicRecommendRequest): # Reusing model for prompt
    """Get standalone virality rating."""
    score = virality_rater.rate_content("", request.prompt, 5)
    return score

@app.post("/api/music/agent/select")
async def select_music(request: MusicSelectRequest):
    """Select and download a track for use."""
    path = music_agent.download_track(request.track_id)
    if not path:
        raise HTTPException(status_code=500, detail="Failed to download track")
    
    # Analyze beat/energy for syncing
    analysis = music_agent.analyze_audio(path)
    
    return {
        "success": True, 
        "filename": path.name,
        "analysis": analysis,
        "message": "Track ready for rendering"
    }

# === Viral Editor Endpoints ===

class ViralEditRequest(BaseModel):
    video_id: str
    audio_track_id: str
    volume_level: float = 0.3

@app.get("/api/trends/audio")
async def get_viral_trends():
    """Get high-confidence viral audio candidates."""
    return {"failed": False, "candidates": trend_fetcher.get_viral_audio_candidates()}

@app.post("/api/edit/preview")
async def create_viral_preview(request: ViralEditRequest):
    """Generate a low-res preview of the viral edit."""
    if request.video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
        
    video_path = jobs[request.video_id]["input_path"]
    transcript = jobs[request.video_id].get("phase_one_metadata", {}).get("transcription", [])
    
    result = viral_editor.apply_viral_edit(
        video_path,
        request.audio_track_id,
        transcript_segments=transcript,
        volume_level=request.volume_level,
        is_preview=True
    )
    return result

@app.post("/api/export")
async def export_viral_video(request: ViralEditRequest):
    """Generate final high-quality viral video."""
    if request.video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
        
    video_path = jobs[request.video_id]["input_path"]
    transcript = jobs[request.video_id].get("phase_one_metadata", {}).get("transcription", [])
    
    result = viral_editor.apply_viral_edit(
        video_path,
        request.audio_track_id,
        transcript_segments=transcript,
        volume_level=request.volume_level,
        is_preview=False
    )
    return result


class SmartSyncRequest(BaseModel):
    video_id: str
    audio_track_id: str
    suggested_cuts: List[CustomSegment]

@app.post("/api/edit/smart-sync")
async def smart_sync_edits(request: SmartSyncRequest):
    """Align suggested cuts to audio beat grid."""
    if request.video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
        
    video_path = jobs[request.video_id]["input_path"]
    cuts = [{"start": s.start, "end": s.end} for s in request.suggested_cuts]
    
    synced = viral_editor.smart_sync_cuts(
        video_path,
        request.audio_track_id,
        cuts
    )
    return {"success": True, "synced_cuts": synced}


# === Visual Effects Endpoints ===

class EffectSuggestRequest(BaseModel):
    video_id: str = Field(..., min_length=1, max_length=20)
    mood: Optional[str] = Field(default=None, max_length=50)

class EffectApplyRequest(BaseModel):
    video_id: str = Field(..., min_length=1, max_length=20)
    effect_id: str = Field(..., min_length=1, max_length=50)
    timestamps: Optional[List[Dict]] = None
    parameters: Optional[Dict] = None

@app.get("/api/effects")
async def list_effects(category: Optional[str] = None):
    """List all available visual effects."""
    effects = effects_library.get_all_effects()
    if category:
        effects = [e for e in effects if e.get("category") == category]
    return {
        "success": True,
        "effects": effects,
        "count": len(effects),
        "categories": ["filter", "transition", "overlay", "text"]
    }

@app.post("/api/effects/suggest")
async def suggest_effects(request: EffectSuggestRequest):
    """Get AI-suggested effects based on video content."""
    if request.video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    job = jobs[request.video_id]
    transcript = job.get("transcript", "")
    ai_analysis = job.get("ai_analysis", {})
    duration = job.get("phase_one_metadata", {}).get("duration", 60)
    
    suggestions = effects_agent.suggest_effects(
        transcript=transcript,
        mood=request.mood or "",
        video_duration=float(duration) if duration else 60,
        ai_analysis=ai_analysis,
        max_suggestions=5
    )
    
    return {"success": True, "suggestions": suggestions, "video_duration": duration}

@app.post("/api/effects/apply")
async def apply_effect(request: EffectApplyRequest):
    """Apply a visual effect to a video."""
    if request.video_id not in jobs:
        raise HTTPException(status_code=404, detail="Video not found")
    
    effect = effects_library.get_effect(request.effect_id)
    if not effect:
        raise HTTPException(status_code=404, detail=f"Effect not found: {request.effect_id}")
    
    if "applied_effects" not in jobs[request.video_id]:
        jobs[request.video_id]["applied_effects"] = []
    
    jobs[request.video_id]["applied_effects"].append({
        "effect_id": request.effect_id,
        "timestamps": request.timestamps,
        "parameters": request.parameters or effect.parameters
    })
    persist_job(request.video_id)
    
    return {
        "success": True,
        "effect": request.effect_id,
        "message": f"Effect '{effect.name}' queued for application",
        "total_effects": len(jobs[request.video_id]["applied_effects"])
    }


# === WebSocket for Progress Updates ===

from typing import Set
import asyncio

connected_clients: Set[WebSocket] = set()

async def broadcast_progress(video_id: str, progress: int, message: str):
    """Send progress to all connected clients."""
    data = json.dumps({"video_id": video_id, "progress": progress, "message": message})
    disconnected = set()
    for ws in connected_clients:
        try:
            await ws.send_text(data)
        except:
            disconnected.add(ws)
    connected_clients.difference_update(disconnected)

@app.websocket("/ws/progress")
async def progress_websocket(websocket: WebSocket):
    """Real-time progress updates for video processing."""
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # Keep connection alive, listen for pings
            await websocket.receive_text()
    except:
        pass
    finally:
        connected_clients.discard(websocket)


@app.websocket("/{path:path}")
async def reject_websockets(websocket: WebSocket, path: str):
    """Gracefully reject unexpected websocket connections to avoid ASGI errors."""
    await websocket.close(code=1000)

# --- Pipelines ---

def analyze_video_pipeline(
    video_id: str,
    user_prompt: str,
    manual_transcript: Optional[str] = None
):
    """Phase 1: Transcribe & Analyze"""
    try:
        jobs[video_id]["progress"] = 10
        
        # Find input file
        if not Path(jobs[video_id].get("input_path", "")).exists():
            input_files = list(UPLOAD_DIR.glob(f"{video_id}.*"))
            if input_files:
                jobs[video_id]["input_path"] = str(input_files[0])
            else:
                jobs[video_id]["status"] = "error"
                jobs[video_id]["error"] = "Input file not found"
                persist_job(video_id)
                return

        input_path = Path(jobs[video_id]["input_path"])
        processor = VideoProcessor(str(input_path))
        
        # Transcription
        if manual_transcript and manual_transcript.strip():
            jobs[video_id]["status"] = "manual_transcript"
            jobs[video_id]["progress"] = 30
            segments = synthesize_segments_from_transcript(
                manual_transcript,
                processor.duration or 0.0
            )
            full_transcript = manual_transcript.strip()
            jobs[video_id]["transcript"] = full_transcript
            jobs[video_id]["phase_one_metadata"] = {"transcription": segments, "duration": processor.duration}
        else:
            jobs[video_id]["status"] = "transcribing"
            jobs[video_id]["progress"] = 20
            persist_job(video_id)
            phase_result = phase_analyzer.process(str(input_path))
            segments = phase_result.transcription
            full_transcript = " ".join(seg.get("text", "") for seg in segments if seg.get("text"))
            jobs[video_id]["transcript"] = full_transcript
            jobs[video_id]["phase_one_metadata"] = phase_result.to_dict()
        
        jobs[video_id]["progress"] = 40
        persist_job(video_id)

        # AI Analysis with video frames for retention scoring
        jobs[video_id]["status"] = "analyzing"
        jobs[video_id]["message"] = "Analyzing viewer retention..."
        persist_job(video_id)
        
        ai_decisions = ai_analyzer.analyze_transcript(
            full_transcript, 
            user_prompt,
            video_path=str(input_path)  # Pass video for frame analysis
        )
        jobs[video_id]["ai_analysis"] = ai_decisions
        jobs[video_id]["overall_score"] = ai_decisions.get("overall_score", 5)
        jobs[video_id]["progress"] = 50
        
        jobs[video_id]["status"] = "choosing_music"
        jobs[video_id]["message"] = "AI is picking the perfect soundtrack..."
        persist_job(video_id)
        
        virality = {"score": 0, "virality_score": 0}  # safe default
        try:
            # 1. Virality Rating
            virality = virality_rater.rate_content(full_transcript, user_prompt, ai_decisions.get("overall_score", 5))
            # Normalise key: ViralityRater returns virality_score, expose as score too
            if "virality_score" in virality and "score" not in virality:
                virality["score"] = virality["virality_score"]
            jobs[video_id]["virality_analysis"] = virality
            
            # 2. Music Selection (with trends)
            suggested_tracks = music_agent.recommend_music(user_prompt, jobs[video_id], trend_fetcher=trend_fetcher)
            if suggested_tracks:
                top_track = suggested_tracks[0]
                jobs[video_id]["ai_suggested_music"] = asdict(top_track)
                print(f"🎵 AI picked: {top_track.title}")
        except Exception as me:
            print(f"⚠️ AI Music/Trend choice failed: {me}")

        # Mark as analyzed, waiting for user review
        jobs[video_id]["status"] = "analyzed"
        jobs[video_id]["message"] = (
            f"Analysis complete! Retention: {ai_decisions.get('overall_score', 5)}/10, "
            f"Virality: {virality.get('virality_score', virality.get('score', 0))}/100"
        )
        persist_job(video_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        jobs[video_id]["status"] = "error"
        jobs[video_id]["error"] = str(e)
        print(f"❌ Error analyzing {video_id}: {str(e)}")
        persist_job(video_id)


def render_video_pipeline(
    video_id: str,
    custom_segments: List[Dict[str, float]],
    manual_transcript: Optional[str],
    style_preset: str,
    add_subtitles: bool,
    add_music: bool = False,
    music_file: Optional[str] = None,
    music_volume: float = 0.3,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
    rotation: int = 0,
    flip_horizontal: bool = False,
    framing_mode: str = "fit_blur"
):
    """Phase 2: Trim & Render"""
    try:
        jobs[video_id]["progress"] = 60
        style_config = get_style_for_preset(style_preset)
        jobs[video_id]["style_preset"] = style_preset or "sleek"
        
        input_path = Path(jobs[video_id]["input_path"])
        video_dir = video_dir_for(video_id)
        output_path = Path(jobs[video_id].get("output_path", video_dir / "final.mp4"))
        captions_path = Path(jobs[video_id].get("captions_path", video_dir / "captions.json"))
        processor = VideoProcessor(str(input_path))
        
        # Re-synthesize segments if manual transcript provided/updated
        segments = jobs[video_id]["phase_one_metadata"]["transcription"]
        if manual_transcript and manual_transcript.strip():
             # If user edited transcript in review phase, use it
             segments = synthesize_segments_from_transcript(
                manual_transcript,
                processor.duration or 0.0
            )
             jobs[video_id]["transcript"] = manual_transcript

        # Apply Cuts
        jobs[video_id]["status"] = "editing"
        current_path = str(input_path)
        edits_applied = []
        applied_ranges: List[Dict[str, float]] = []
        
        valid_custom_segments = []
        for segment in custom_segments:
            try:
                start = max(0.0, float(segment.get("start", 0)))
                end = max(0.0, float(segment.get("end", 0)))
                if end > start:
                    valid_custom_segments.append({"start": start, "end": end})
            except (TypeError, ValueError):
                continue

        if valid_custom_segments:
            jobs[video_id]["status"] = "trimming"
            trimmed_paths = []
            for idx, segment in enumerate(valid_custom_segments):
                segment_path = TEMP_DIR / f"{video_id}_segment_{idx}.mp4"
                processor.trim_video(segment["start"], segment["end"], str(segment_path))
                trimmed_paths.append(segment_path)

            if len(trimmed_paths) == 1:
                current_path = str(trimmed_paths[0])
            else:
                concat_list_path = TEMP_DIR / f"{video_id}_concat.txt"
                with open(concat_list_path, "w") as concat_file:
                    for path in trimmed_paths:
                        concat_file.write(f"file '{Path(path).as_posix()}'\n")
                concatenated_path = TEMP_DIR / f"{video_id}_custom.mp4"
                concat_cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(concat_list_path),
                    "-c", "copy",
                    str(concatenated_path)
                ]
                subprocess.run(concat_cmd, check=True, capture_output=True)
                current_path = str(concatenated_path)

            edits_applied.append(f"Applied {len(valid_custom_segments)} cuts")
            applied_ranges = valid_custom_segments
        else:
            # No cuts, keep full video
            duration_end = processor.duration or (segments[-1]["end"] if segments else 0.0)
            applied_ranges = [{"start": 0.0, "end": duration_end}]

        jobs[video_id]["progress"] = 80

        # Apply aspect ratio crop / rotation / flip
        needs_transform = aspect_ratio or rotation or flip_horizontal
        if needs_transform:
            jobs[video_id]["status"] = "transforming"
            selected_mode = (framing_mode or "fit_blur").lower()
            if selected_mode not in {"fit", "crop", "smart_crop", "fit_blur"}:
                selected_mode = "fit_blur"

            jobs[video_id]["message"] = (
                f"Applying aspect ratio ({aspect_ratio or 'auto'}) with {selected_mode}..."
            )
            persist_job(video_id)
            
            transformed_path = str(TEMP_DIR / f"{video_id}_transformed.mp4")
            transform_processor = VideoProcessor(current_path)
            transform_processor.transform_video(
                transformed_path,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                rotation=rotation,
                flip_horizontal=flip_horizontal,
                resize_mode=selected_mode
            )
            current_path = transformed_path
            edits_applied.append(
                f"Transformed: AR={aspect_ratio or 'auto'}, Mode={selected_mode}, "
                f"Rot={rotation}°, Flip={'yes' if flip_horizontal else 'no'}"
            )
            print(f"🎬 Transform applied for {video_id}")
        
        # Generate Captions
        caption_doc = build_caption_document(
            video_id,
            style_preset or "sleek",
            segments,
            applied_ranges
        )
        with open(captions_path, "w", encoding="utf-8") as caption_file:
            json.dump(caption_doc, caption_file, ensure_ascii=False, indent=2)

        # Burn Subtitles with Smart Placement
        base_video_path = Path(current_path)
        final_output_path = output_path
        if add_subtitles and caption_doc.get("captions"):
            srt_path = OUTPUT_DIR / f"{video_id}_captions.srt"
            write_srt_from_captions(caption_doc, srt_path)
            
            # Use smart subtitle service to get optimized placement
            jobs[video_id]["status"] = "optimizing_subtitles"
            jobs[video_id]["message"] = "Analyzing video for optimal subtitle placement..."
            persist_job(video_id)
            
            smart_style = smart_subtitle_service.get_optimized_style(str(base_video_path), style_preset)
            
            VideoProcessor(str(base_video_path)).add_subtitles(
                str(srt_path),
                str(final_output_path),
                smart_style  # Use AI-optimized style instead of preset
            )
            edits_applied.append("Burned smart subtitles (AI-optimized placement)")
        else:
            if os.path.abspath(base_video_path) != os.path.abspath(final_output_path):
                shutil.copy(base_video_path, final_output_path)
            else:
                final_output_path = base_video_path

        jobs[video_id]["output_path"] = str(final_output_path)
        jobs[video_id]["captions_path"] = str(captions_path)
        jobs[video_id]["captions_url"] = f"/api/captions/{video_id}"
        jobs[video_id]["edits_applied"] = edits_applied
        
        # Add background music if requested
        # Add background music if requested
        if add_music and music_file:
            jobs[video_id]["status"] = "adding_music"
            jobs[video_id]["message"] = f"Adding background music ({music_file})..."
            jobs[video_id]["progress"] = 90
            persist_job(video_id)
            
            try:
                video_with_music = OUTPUT_DIR / f"{video_id}_with_music.mp4"
                
                # Check if it's a YT track (requires download) or already local
                track_path = None
                if music_file.endswith(".mp3") or music_file.endswith(".wav"):
                   # Likely a local filename
                   track_path = MUSIC_DIR / music_file
                else:
                   # Likely a YT track ID
                   track_path = music_agent.download_track(music_file)
                
                if track_path and track_path.exists():
                    sync_audio_with_ducking(
                        str(final_output_path),
                        str(track_path),
                        str(video_with_music),
                        voice_segments=segments # Use transcript for auto-ducking
                    )
                    final_output_path = video_with_music
                    jobs[video_id]["output_path"] = str(final_output_path)
                    edits_applied.append(f"AI Layered Music: {music_file}")
                else:
                    raise Exception("Audio file not available")
            except Exception as e:
                print(f"⚠️ Music layering failed: {e}")
                edits_applied.append(f"Music layering failed: {str(e)}")
        
        jobs[video_id]["progress"] = 100
        jobs[video_id]["status"] = "completed"
        jobs[video_id]["message"] = "Processing complete! Video ready for download."
        persist_job(video_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        jobs[video_id]["status"] = "error"
        jobs[video_id]["error"] = str(e)
        print(f"❌ Error rendering {video_id}: {str(e)}")
        persist_job(video_id)

# Serve frontend
app.mount("/", SPAStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Video Editor MVP...")
    print("📝 Upload videos at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
