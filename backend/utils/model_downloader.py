"""
Florence-2 offline-first model downloader.
All env vars (HF_ENDPOINT, HF_HUB_TIMEOUT) must already be set by run.sh
before this module is imported — which they will be.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

FLORENCE_MODEL_ID = "microsoft/Florence-2-base"

# Respect HF_HOME; default to ~/.cache/huggingface
_HF_HOME = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface"))
_APP_CACHE = Path(os.getenv("MODEL_CACHE_DIR",
                             Path.home() / ".cache" / "ai_video_editor" / "florence2"))

# Can be overridden to point at a local copy
FLORENCE_LOCAL_PATH = os.getenv("FLORENCE_LOCAL_PATH", "")


def _is_valid_model_dir(path: Path) -> bool:
    """Check directory has config + at least one weight file."""
    return (
        path.is_dir()
        and (path / "config.json").exists()
        and (any(path.glob("*.safetensors")) or any(path.glob("*.bin")))
    )


def find_cached_model() -> Optional[Path]:
    """
    Return path to an already-downloaded Florence-2 model, or None.
    Checks (in order):
      1. FLORENCE_LOCAL_PATH env var
      2. App-specific cache
      3. System HF hub snapshot cache
    Zero network calls.
    """
    # 1. Explicit override
    if FLORENCE_LOCAL_PATH and _is_valid_model_dir(Path(FLORENCE_LOCAL_PATH)):
        return Path(FLORENCE_LOCAL_PATH)

    # 2. App cache
    if _is_valid_model_dir(_APP_CACHE):
        return _APP_CACHE

    # 3. HF hub snapshot layout: ~/.cache/huggingface/hub/models--microsoft--Florence-2-base/snapshots/*
    snapshot_base = _HF_HOME / "hub" / "models--microsoft--Florence-2-base" / "snapshots"
    if snapshot_base.exists():
        snapshots = sorted(snapshot_base.iterdir(),
                           key=lambda p: p.stat().st_mtime, reverse=True)
        for snap in snapshots:
            if _is_valid_model_dir(snap):
                logger.info(f"📁 Found cached model: {snap}")
                return snap

    # 4. Ask huggingface_hub (reads its own cache, no network)
    try:
        from huggingface_hub import snapshot_download
        path = snapshot_download(
            repo_id=FLORENCE_MODEL_ID,
            local_files_only=True,   # ← no network
        )
        if _is_valid_model_dir(Path(path)):
            return Path(path)
    except Exception:
        pass

    return None


def download_and_cache_florence(target: Optional[Path] = None) -> Path:
    """
    Download Florence-2 to target (default: _APP_CACHE).

    HF_ENDPOINT is already set in the environment by run.sh, so
    snapshot_download will automatically use the mirror.
    """
    dest = target or _APP_CACHE
    dest.mkdir(parents=True, exist_ok=True)

    # HF_ENDPOINT env var is read by huggingface_hub at import time —
    # since run.sh exported it before Python started, the mirror is active.
    endpoint = os.environ.get("HF_ENDPOINT")
    print(
        f"\n📥  Downloading microsoft/Florence-2-base (~1.5 GB)\n"
        f"    Mirror : {endpoint or 'https://huggingface.co'}\n"
        f"    Dest   : {dest}\n"
        f"    This only happens once — please wait...\n",
        flush=True,
    )

    from huggingface_hub import snapshot_download

    try:
        path = snapshot_download(
            repo_id=FLORENCE_MODEL_ID,
            local_dir=str(dest),
            local_dir_use_symlinks=False,
            max_workers=4,
            # endpoint is picked up automatically from HF_ENDPOINT env var
        )
        logger.info(f"✅ Florence-2 downloaded to: {path}")
        return Path(path)
    except Exception as primary_exc:
        # If mirror fails, try original HF
        if endpoint and "huggingface.co" not in endpoint:
            logger.warning(f"Mirror failed ({primary_exc}), trying huggingface.co...")
            try:
                path = snapshot_download(
                    repo_id=FLORENCE_MODEL_ID,
                    local_dir=str(dest),
                    local_dir_use_symlinks=False,
                    endpoint="https://huggingface.co",
                )
                return Path(path)
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"Download failed on both mirror and huggingface.co.\n"
                    f"Mirror error   : {primary_exc}\n"
                    f"HF.co error    : {fallback_exc}\n\n"
                    f"Set FLORENCE_LOCAL_PATH=/path/to/model to use an existing download."
                ) from fallback_exc
        raise RuntimeError(f"Download failed: {primary_exc}") from primary_exc


def ensure_florence_model() -> Path:
    """
    Return local model path, downloading only if not already cached.
    This is the main entry point called by VideoAnalyzer.
    """
    cached = find_cached_model()
    if cached:
        logger.info(f"✅ Using cached Florence-2: {cached}")
        return cached

    if os.getenv("FLORENCE_OFFLINE", "").lower() in ("1", "true"):
        raise RuntimeError(
            "FLORENCE_OFFLINE=true but no local model found.\n"
            "Run: ./run.sh setup-models"
        )

    return download_and_cache_florence()


def load_florence_model(device: str = "cpu") -> Tuple:
    """
    Load (AutoProcessor, AutoModelForCausalLM) from local cache only.
    Always uses local_files_only=True — never hits the network.
    """
    import torch
    from transformers import AutoProcessor, AutoModelForCausalLM

    model_path = str(ensure_florence_model())
    logger.info(f"🔄 Loading Florence-2 from local cache: {model_path}")
    t0 = time.time()

    processor = AutoProcessor.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )

    dtype = torch.float16 if device in ("cuda", "mps") else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=dtype,
        trust_remote_code=True,
        local_files_only=True,
    ).to(device)
    model.eval()

    logger.info(f"✅ Florence-2 loaded in {time.time() - t0:.1f}s on {device}")
    return processor, model
