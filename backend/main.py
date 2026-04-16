from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Logging setup ─────────────────────────────────────────────────────────────
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s \u2014 %(message)s",
        datefmt="%H:%M:%S",
        # Do NOT pass style= here; default % style is correct and avoids KeyError
    )
)
logging.root.setLevel(logging.INFO)
logging.root.handlers = [_handler]
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent  # project root
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"  # React build output


# ── Optional dependency checks ────────────────────────────────────────────────
def _check_moviepy() -> str:
    try:
        try:
            import moviepy.editor  # noqa: F401
        except ImportError:
            import moviepy  # type: ignore # noqa: F401

        return "✅ MoviePy available"
    except ImportError:
        return "⚠️  MoviePy not found — using FFmpeg subprocess fallback"


def _check_ffmpeg() -> str:
    return "✅ FFmpeg found" if shutil.which("ffmpeg") else "⚠️  FFmpeg not in PATH"


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Video Editor starting up…")
    logger.info(f"   Python    : {sys.version.split()[0]}")
    logger.info(f"   {_check_moviepy()}")
    logger.info(f"   {_check_ffmpeg()}")
    logger.info("   Florence-2: lazy (loads on first video analysis request)")
    if FRONTEND_DIST.is_dir():
        logger.info(f"   🖥️  Serving React UI from {FRONTEND_DIST}")
    else:
        logger.info("   🖥️  React build not found — JSON welcome served at /")
    logger.info("   🟢 Server ready — http://0.0.0.0:8000")

    try:
        yield
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("🛑 Shutting down cleanly…")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Video Editor",
    version="1.0.0",
    description="AI-powered video editing API — Florence-2 vision model",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health endpoint (always available, no auth) ───────────────────────────────
@app.get("/health", tags=["system"], summary="Health check")
async def health():
    """
    Returns server status and key runtime flags.
    Used by load balancers, Docker health checks, and run.sh.
    """
    return {
        "status": "ok",
        "python": sys.version.split()[0],
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "florence_offline": os.environ.get("HF_HUB_OFFLINE", "0") == "1",
        "florence_local_path": os.environ.get("FLORENCE_LOCAL_PATH") or None,
        "frontend_built": FRONTEND_DIST.is_dir(),
    }


# ── Root route — JSON welcome (only shown when React build is absent) ─────────
@app.get("/api", tags=["system"], summary="API welcome")
async def api_welcome():
    """Friendly API index — links to docs and key endpoints."""
    return JSONResponse(
        {
            "app": "AI Video Editor",
            "version": "1.0.0",
            "status": "running",
            "docs": "http://localhost:8000/docs",
            "health": "http://localhost:8000/health",
            "endpoints": {
                "upload": "/api/upload",
                "video": "/api/video",
                "edit": "/api/edit",
                "analysis": "/api/analysis",
                "export": "/api/export",
                "music": "/api/music",
                "download": "/api/download",
            },
            "tip": "Open /docs for the interactive API explorer.",
        }
    )


# ── Routers ───────────────────────────────────────────────────────────────────
try:
    from backend.routers import analysis, export, video, upload, edit, music, download  # noqa: E402

    app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
    app.include_router(video.router, prefix="/api/video", tags=["video"])
    app.include_router(edit.router, prefix="/api", tags=["edit"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])
    app.include_router(music.router, prefix="/api/music", tags=["music"])
    app.include_router(download.router, prefix="/api/download", tags=["download"])
    logger.info("✅ All routers loaded successfully")
    # Log edit router routes for debugging
    for route in edit.router.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            logger.info(f"   Edit route: {route.methods} /api{route.path}")
except ImportError as exc:
    logger.error("❌ Router import FAILED: %s", exc, exc_info=True)


# ── Debug: list all registered routes ─────────────────────────────────────────
@app.get("/debug/routes", tags=["system"], summary="List all routes")
async def debug_routes():
    routes = []
    for r in app.routes:
        if hasattr(r, "path") and hasattr(r, "methods"):
            routes.append({"methods": list(r.methods), "path": r.path})
    return sorted(routes, key=lambda x: x["path"])


# ── WebSocket progress endpoint ───────────────────────────────────────────────
from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"status": "ok", "echo": data})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── Static frontend (mount LAST so API routes take priority) ──────────────────
if FRONTEND_DIST.is_dir():
    # Serve index.html for all unknown paths (SPA client-side routing)
    @app.get("/", include_in_schema=False)
    async def serve_spa_root():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        For any path that isn't an API route, try to serve the static file.
        Fall back to index.html so React Router handles it client-side.
        """
        target = FRONTEND_DIST / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")

    # Also mount /assets so JS/CSS/images load correctly
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

else:
    # No React build yet — serve the JSON welcome at /
    @app.get("/", tags=["system"], summary="Welcome")
    async def root():
        return JSONResponse(
            {
                "app": "AI Video Editor API",
                "message": "Backend is running. No React build found yet.",
                "docs": "http://localhost:8000/docs",
                "health": "http://localhost:8000/health",
                "api": "http://localhost:8000/api",
                "build_frontend": "cd frontend && npm install && npm run build",
            }
        )


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend"],
        log_level="info",
    )
