"""
Florence-2 Model Downloader & Offline Loader
=============================================
Fixes permanently:
  - ConnectTimeoutError / MaxRetryError on huggingface.co (10s timeout)
  - macOS Python framework SSL CERTIFICATE_VERIFY_FAILED
  - No offline-first loading after first download

Priority chain:
  1. FLORENCE_LOCAL_PATH env var  → skip all discovery
  2. App cache ~/.cache/ai_video_editor/florence2
  3. System HF cache (snapshot layout)
  4. Network download with 120s timeout + progress bar
  5. Graceful failure with manual instructions
"""

from __future__ import annotations

import logging
import os
import ssl
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── Model identifiers ─────────────────────────────────────────────────────────
FLORENCE_MODEL_ID = "microsoft/Florence-2-base"
FLORENCE_REVISION  = "main"

# ── Cache directory ───────────────────────────────────────────────────────────
_HF_HOME      = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface"))
APP_CACHE_DIR = Path(os.getenv("MODEL_CACHE_DIR",
                               Path.home() / ".cache" / "ai_video_editor" / "florence2"))

# ── Env overrides ─────────────────────────────────────────────────────────────
FLORENCE_LOCAL_PATH = os.getenv("FLORENCE_LOCAL_PATH", "")
FLORENCE_OFFLINE    = os.getenv("FLORENCE_OFFLINE", "").lower() in ("1", "true", "yes")
HF_ENDPOINT         = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
CONNECT_TIMEOUT     = int(os.getenv("HF_HUB_DOWNLOAD_TIMEOUT", "120"))

# ── Set global HF timeout BEFORE any huggingface_hub import ──────────────────
os.environ.setdefault("HF_HUB_TIMEOUT", str(CONNECT_TIMEOUT))
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", str(CONNECT_TIMEOUT))


# ── Step 1: Fix macOS SSL certificate error permanently ───────────────────────

def fix_macos_ssl() -> None:
    """
    Fix the macOS Python framework SSL error:
      'certificate verify failed: unable to get local issuer certificate'

    The standard Python.org macOS installer ships without system CA certs.
    This sets SSL_CERT_FILE to the certifi bundle which always works.
    Reference: https://bugs.python.org/issue29480
    """
    # Already set externally — trust it
    if os.environ.get("SSL_CERT_FILE"):
        return

    try:
        import certifi
        cert_path = certifi.where()
        os.environ["SSL_CERT_FILE"]  = cert_path
        os.environ["REQUESTS_CA_BUNDLE"] = cert_path
        # Monkey-patch the default SSL context used by urllib3 / requests
        ssl._create_default_https_context = ssl.create_default_context  # type: ignore[attr-defined]
        logger.debug(f"🔒 SSL certs fixed via certifi: {cert_path}")
    except ImportError:
        # certifi not installed — try the macOS system bundle
        system_bundle = "/etc/ssl/cert.pem"
        if Path(system_bundle).exists():
            os.environ["SSL_CERT_FILE"] = system_bundle
            logger.debug(f"🔒 SSL certs fixed via system bundle: {system_bundle}")
        else:
            logger.warning(
                "⚠️  certifi not installed and no system CA bundle found. "
                "Install with: pip install certifi"
            )


# ── Step 2: Build a robust requests session ───────────────────────────────────

def _build_robust_session():
    """
    Return a requests.Session with 120s timeout and 5-retry exponential backoff.
    Called once; injected into huggingface_hub via configure_http_backend.
    """
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=2,          # 2, 4, 8, 16, 32 seconds
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Pick up system proxy settings automatically
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            val = os.environ.get(key, "")
            if val:
                session.proxies[key.lower().replace("_proxy", "")] = val

        return session
    except ImportError:
        return None


def _inject_robust_session() -> None:
    """Patch huggingface_hub's HTTP backend with our robust session (once)."""
    try:
        from huggingface_hub import configure_http_backend
        session_factory = _build_robust_session
        if session_factory() is not None:
            configure_http_backend(backend_factory=_build_robust_session)
            logger.debug("✅ Injected 120s-timeout HTTP session into huggingface_hub")
    except Exception as exc:
        logger.debug(f"configure_http_backend skipped: {exc}")


# ── Step 3: Local model discovery ─────────────────────────────────────────────

def _is_valid_model_dir(path: Path) -> bool:
    """A valid Florence-2 directory must have config.json + at least one weight file."""
    if not path.is_dir():
        return False
    return (path / "config.json").exists() and (
        any(path.glob("*.safetensors")) or any(path.glob("*.bin"))
    )


def find_local_model() -> Optional[Path]:
    """
    Search for an already-downloaded model in priority order.
    Returns Path if found, None otherwise.
    """
    candidates: list[Path] = []

    # 0. Explicit env var — user pinned a specific dir
    if FLORENCE_LOCAL_PATH:
        candidates.append(Path(FLORENCE_LOCAL_PATH))

    # 1. PyInstaller bundle (frozen app)
    if getattr(sys, "frozen", False):
        bundle = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        candidates.append(bundle / "models" / "florence2")

    # 2. App-specific cache
    candidates.append(APP_CACHE_DIR)

    # 3. System HF snapshot cache
    snapshot_base = (
        _HF_HOME / "hub"
        / f"models--{FLORENCE_MODEL_ID.replace('/', '--')}"
        / "snapshots"
    )
    if snapshot_base.exists():
        snapshots = sorted(
            snapshot_base.iterdir(),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        candidates.extend(snapshots)

    for path in candidates:
        if _is_valid_model_dir(path):
            logger.info(f"📁 Found local Florence-2 model: {path}")
            return path

    return None


def _hf_offline_cache() -> Optional[Path]:
    """Ask huggingface_hub for a cached snapshot — zero network I/O."""
    try:
        from huggingface_hub import snapshot_download
        path = snapshot_download(
            repo_id=FLORENCE_MODEL_ID,
            revision=FLORENCE_REVISION,
            local_files_only=True,   # ← key: never hits network
        )
        return Path(path)
    except Exception:
        return None


# ── Step 4: Download with progress bar ────────────────────────────────────────

def _print_manual_instructions() -> None:
    print(
        "\n╔══════════════════════════════════════════════════════════╗\n"
        "║  MANUAL DOWNLOAD — run ONE of these commands:           ║\n"
        "║                                                          ║\n"
        "║  A)  python -m backend.setup_models                     ║\n"
        "║                                                          ║\n"
        "║  B)  huggingface-cli download microsoft/Florence-2-base ║\n"
        f"║        --local-dir {str(APP_CACHE_DIR)[:38]:<38}║\n"
        "║                                                          ║\n"
        "║  C)  Set env var to skip download:                      ║\n"
        "║      export FLORENCE_LOCAL_PATH=/your/model/path        ║\n"
        "║                                                          ║\n"
        "║  D)  Use mirror if HF blocked:                          ║\n"
        "║      export HF_ENDPOINT=https://hf-mirror.com           ║\n"
        "╚══════════════════════════════════════════════════════════╝\n",
        flush=True,
    )


def download_florence_model(target_dir: Optional[Path] = None) -> Path:
    """
    Download Florence-2-base to target_dir (default: APP_CACHE_DIR).
    Shows progress and raises RuntimeError with instructions on failure.
    """
    target = target_dir or APP_CACHE_DIR
    target.mkdir(parents=True, exist_ok=True)

    _inject_robust_session()

    print(
        f"\n📥  Downloading microsoft/Florence-2-base (~1.5 GB)\n"
        f"    Destination: {target}\n"
        f"    This only happens once. Please wait...\n",
        flush=True,
    )

    endpoint = HF_ENDPOINT if HF_ENDPOINT != "https://huggingface.co" else None

    try:
        from huggingface_hub import snapshot_download

        # hf_transfer gives ~5× faster downloads when installed
        if os.getenv("HF_HUB_ENABLE_HF_TRANSFER", "0") == "0":
            try:
                import hf_transfer  # noqa: F401
                os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
                logger.info("⚡ hf_transfer enabled for faster download")
            except ImportError:
                pass

        downloaded = snapshot_download(
            repo_id=FLORENCE_MODEL_ID,
            revision=FLORENCE_REVISION,
            local_dir=str(target),
            local_dir_use_symlinks=False,   # full copy — works in bundles
            endpoint=endpoint,
            max_workers=4,
        )
        print(f"✅  Download complete: {downloaded}", flush=True)
        return Path(downloaded)

    except KeyboardInterrupt:
        print("\n⚠️  Download cancelled.", flush=True)
        raise

    except Exception as exc:
        logger.error(f"Download failed: {exc}")
        _print_manual_instructions()
        raise RuntimeError(
            f"Florence-2 download failed: {exc}"
        ) from exc


# ── Step 5: Main public API ───────────────────────────────────────────────────

def ensure_florence_model() -> Path:
    """
    Guarantee the model is available locally. Returns its directory path.

    Call this once at startup (or lazily on first use).
    Never makes a network call if the model is already cached.
    """
    # Fix SSL before any network attempt
    fix_macos_ssl()

    # Try local first (zero network)
    local = find_local_model() or _hf_offline_cache()
    if local:
        return local

    if FLORENCE_OFFLINE:
        _print_manual_instructions()
        raise RuntimeError(
            "FLORENCE_OFFLINE=true but no local model found. "
            "Run: python -m backend.setup_models"
        )

    # Download
    return download_florence_model()


def load_florence_model(device: str = "cpu") -> Tuple:
    """
    Load AutoProcessor + AutoModelForCausalLM from local cache.
    Returns (processor, model). Raises RuntimeError if model unavailable.

    Usage::
        processor, model = load_florence_model(device="mps")
    """
    import torch
    from transformers import AutoProcessor, AutoModelForCausalLM

    model_path = ensure_florence_model()
    path_str   = str(model_path)

    logger.info(f"🔄 Loading Florence-2 from {path_str} on {device}...")
    t0 = time.time()

    processor = AutoProcessor.from_pretrained(
        path_str,
        trust_remote_code=True,
        local_files_only=True,   # never hit network once we have files
    )

    dtype = torch.float16 if device in ("cuda", "mps") else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        path_str,
        torch_dtype=dtype,
        trust_remote_code=True,
        local_files_only=True,
    ).to(device)
    model.eval()

    elapsed = round(time.time() - t0, 1)
    logger.info(f"✅ Florence-2 ready in {elapsed}s on {device}")
    return processor, model
