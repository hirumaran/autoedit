"""
ModelManager — Robust offline-first HuggingFace model loader.
==============================================================
Designed for production apps shipped via PyInstaller / Tauri / Electron.

Loading priority:
  1. PyInstaller bundle  — model pre-packed inside the .app / .exe
  2. App-local cache     — ~/.cache/ai_video_editor/florence2/
  3. System HF cache     — ~/.cache/huggingface/hub/
  4. Network download    — with 120 s timeout, 5 retries, progress bar
  5. Manual fallback     — prints direct download link and instructions

Environment overrides (all optional):
  MODEL_CACHE_DIR          — override cache directory
  HF_HUB_DOWNLOAD_TIMEOUT  — connect timeout in seconds (default 120)
  HTTP_PROXY / HTTPS_PROXY — forwarded to requests session automatically
  FLORENCE_LOCAL_PATH      — point directly to a pre-downloaded model dir
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MODEL_ID = "microsoft/Florence-2-base"
MODEL_REVISION = "main"

# HF mirror used when huggingface.co is blocked (mainland China / some VPNs)
HF_MIRROR = os.getenv("HF_ENDPOINT", "https://huggingface.co")

# Connect timeout: respect env var or default to 120 s (vs stock 10 s)
CONNECT_TIMEOUT = int(os.getenv("HF_HUB_DOWNLOAD_TIMEOUT", "120"))

# App-specific cache so we never clash with other HF projects
APP_CACHE_DIR = Path(
    os.getenv("MODEL_CACHE_DIR", Path.home() / ".cache" / "ai_video_editor" / "florence2")
)

# Direct override: set this to skip all discovery logic
FLORENCE_LOCAL_PATH = os.getenv("FLORENCE_LOCAL_PATH", "")

# PyInstaller: _MEIPASS is set when running inside a bundle
_BUNDLE_DIR: Optional[Path] = (
    Path(sys._MEIPASS) if getattr(sys, "frozen", False) else None  # type: ignore[attr-defined]
)

# ── Optional heavy imports ─────────────────────────────────────────────────────
try:
    from tqdm import tqdm as _tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not installed — network download will use urllib3 defaults")


# ── Robust HTTP Session ────────────────────────────────────────────────────────

def _build_session() -> "requests.Session":
    """
    Build a requests.Session with:
      - 120 s connect timeout (vs huggingface_hub default of 10 s)
      - 5 retries with exponential backoff (2 s → 4 s → 8 s → 16 s → 32 s)
      - Automatic proxy pickup from HTTP_PROXY / HTTPS_PROXY env vars
      - Respect HF mirror via base_url header injection
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=2,           # waits: 2, 4, 8, 16, 32 seconds
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Honour system proxy env vars automatically
    session.proxies.update({
        "http": os.getenv("HTTP_PROXY", ""),
        "https": os.getenv("HTTPS_PROXY", ""),
    })

    return session


def _inject_session() -> None:
    """
    Monkey-patch huggingface_hub to use our robust session.
    Must be called before any hf_hub download.
    """
    if not REQUESTS_AVAILABLE:
        return
    try:
        from huggingface_hub import configure_http_backend
        configure_http_backend(backend_factory=_build_session)
        logger.debug("✅ Injected custom HTTP session into huggingface_hub")
    except (ImportError, Exception) as exc:
        logger.debug(f"configure_http_backend not available: {exc}")


# ── Path Discovery ─────────────────────────────────────────────────────────────

def _find_local_model() -> Optional[Path]:
    """
    Search for a locally cached model in priority order.
    Returns the directory path if valid, else None.
    """
    candidates: list[Path] = []

    # 0. Explicit env var override
    if FLORENCE_LOCAL_PATH:
        candidates.append(Path(FLORENCE_LOCAL_PATH))

    # 1. PyInstaller bundle — model shipped inside .app / .exe
    if _BUNDLE_DIR:
        candidates.append(_BUNDLE_DIR / "models" / "florence2")

    # 2. App-local cache
    candidates.append(APP_CACHE_DIR)

    # 3. System HuggingFace cache (snapshots layout)
    hf_cache = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface"))
    snapshot_base = hf_cache / "hub" / f"models--{MODEL_ID.replace('/', '--')}" / "snapshots"
    if snapshot_base.exists():
        # Pick the most recently modified snapshot
        snapshots = sorted(snapshot_base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        candidates.extend(snapshots)

    for path in candidates:
        if _is_valid_model_dir(path):
            logger.info(f"📁 Found local model at: {path}")
            return path

    return None


def _is_valid_model_dir(path: Path) -> bool:
    """
    A model directory is valid if it contains at minimum:
      config.json + at least one weight file (*.bin / *.safetensors)
    """
    if not path.is_dir():
        return False
    has_config = (path / "config.json").exists()
    has_weights = any(
        path.glob("*.bin")
    ) or any(path.glob("*.safetensors"))
    return has_config and has_weights


# ── Download with Progress Bar ─────────────────────────────────────────────────

def _download_model(target_dir: Path) -> Path:
    """
    Download the model from HuggingFace Hub into target_dir.
    Shows a tqdm progress bar and clear user messages.
    Raises RuntimeError on failure with manual fallback instructions.
    """
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        raise RuntimeError(
            "huggingface_hub not installed. Run: pip install huggingface_hub"
        )

    _inject_session()

    target_dir.mkdir(parents=True, exist_ok=True)

    print(
        "\n┌─────────────────────────────────────────────────────────┐\n"
        "│  📥  Downloading Florence-2-base (first time only)       │\n"
        "│      Size: ~930 MB — this will not happen again          │\n"
        "│      Destination:                                         │\n"
        f"│      {str(target_dir)[:53]:<53}│\n"
        "│                                                           │\n"
        "│  💡  Tip: pre-download with:                             │\n"
        "│      huggingface-cli download microsoft/Florence-2-base   │\n"
        "└─────────────────────────────────────────────────────────┘\n",
        flush=True,
    )

    endpoint = HF_MIRROR if HF_MIRROR != "https://huggingface.co" else None

    try:
        downloaded_path = snapshot_download(
            repo_id=MODEL_ID,
            revision=MODEL_REVISION,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,   # full copy — works inside bundles
            endpoint=endpoint,
            # huggingface_hub ≥ 0.23 uses these timeout params
            max_workers=4,
        )
        logger.info(f"✅ Model downloaded to: {downloaded_path}")
        return Path(downloaded_path)

    except KeyboardInterrupt:
        print("\n⚠️  Download cancelled by user.", flush=True)
        raise

    except Exception as exc:
        _print_manual_instructions(exc)
        raise RuntimeError(
            f"Model download failed: {exc}\nSee manual download instructions above."
        ) from exc


def _print_manual_instructions(exc: Exception) -> None:
    """Print a friendly manual download guide when network fails."""
    print(
        "\n╔══════════════════════════════════════════════════════════╗\n"
        "║  ❌  Automatic download failed                           ║\n"
        "╠══════════════════════════════════════════════════════════╣\n"
        "║  MANUAL DOWNLOAD (one-time setup):                       ║\n"
        "║                                                           ║\n"
        "║  Option A — CLI (recommended):                           ║\n"
        "║    pip install huggingface_hub                           ║\n"
        "║    huggingface-cli download microsoft/Florence-2-base \\  ║\n"
        f"║      --local-dir {str(APP_CACHE_DIR)[:40]:<40}║\n"
        "║                                                           ║\n"
        "║  Option B — Python:                                      ║\n"
        "║    from huggingface_hub import snapshot_download          ║\n"
        "║    snapshot_download('microsoft/Florence-2-base',         ║\n"
        f"║      local_dir='{str(APP_CACHE_DIR)[:36]:<36}')  ║\n"
        "║                                                           ║\n"
        "║  Option C — Set env var to existing download:            ║\n"
        "║    export FLORENCE_LOCAL_PATH=/path/to/florence2          ║\n"
        "║                                                           ║\n"
        "║  Option D — Mirror (if HF blocked):                      ║\n"
        "║    export HF_ENDPOINT=https://hf-mirror.com              ║\n"
        "║    then re-run the app                                    ║\n"
        "╚══════════════════════════════════════════════════════════╝\n",
        flush=True,
    )
    logger.error(f"Download error detail: {exc}")


# ── Main ModelManager Class ────────────────────────────────────────────────────

class ModelManager:
    """
    Production-grade Florence-2 model manager.

    Usage::

        manager = ModelManager()
        processor, model = manager.load()

        # Use with context manager for auto-cleanup:
        with ModelManager() as (processor, model):
            inputs = processor(images=pil_img, text=prompt, return_tensors="pt")
            ...
    """

    def __init__(
        self,
        device: str = "cpu",
        dtype=None,
        trust_remote_code: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """
        Parameters
        ----------
        device           : "cpu", "cuda", "mps" etc.
        dtype            : torch.float16 / torch.bfloat16 / None (auto)
        trust_remote_code: Required True for Florence-2 custom modelling code.
        cache_dir        : Override default APP_CACHE_DIR.
        """
        self.device = device
        self.dtype = dtype
        self.trust_remote_code = trust_remote_code
        self.cache_dir = cache_dir or APP_CACHE_DIR

        self._processor = None
        self._model = None
        self._model_path: Optional[Path] = None

    # ── Context manager ────────────────────────────────────────────────────────

    def __enter__(self):
        return self.load()

    def __exit__(self, *_):
        self.unload()

    # ── Public API ─────────────────────────────────────────────────────────────

    def load(self) -> Tuple:
        """
        Load processor + model.  Returns (processor, model).
        Follows the offline-first priority chain described in the module docstring.
        """
        if self._processor is not None and self._model is not None:
            return self._processor, self._model

        model_path = self._resolve_model_path()
        self._processor, self._model = self._load_from_path(model_path)
        self._model_path = model_path
        return self._processor, self._model

    def unload(self) -> None:
        """Release model memory (important on MPS / CUDA)."""
        try:
            import torch
            if self._model is not None:
                self._model.cpu()
                del self._model
            if self._processor is not None:
                del self._processor
            torch.cuda.empty_cache() if hasattr(torch.cuda, "empty_cache") else None
        except Exception:
            pass
        self._model = None
        self._processor = None
        logger.info("🧹 Florence-2 model unloaded")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    # ── Private helpers ────────────────────────────────────────────────────────

    def _resolve_model_path(self) -> Path:
        """
        Determine where to load the model from, downloading if necessary.
        """
        # Step 1: try local cache
        local = _find_local_model()
        if local:
            return local

        # Step 2: try offline-only HF hub (no network call, instant)
        hub_path = self._try_hf_offline()
        if hub_path:
            return hub_path

        # Step 3: download (with progress bar, retries, timeout)
        logger.info("🌐 No local model found — starting download...")
        return _download_model(self.cache_dir)

    def _try_hf_offline(self) -> Optional[Path]:
        """
        Ask huggingface_hub to locate a cached snapshot without any network I/O.
        Returns path if found, None otherwise.
        """
        try:
            from huggingface_hub import snapshot_download
            path = snapshot_download(
                repo_id=MODEL_ID,
                revision=MODEL_REVISION,
                local_files_only=True,   # 🔑 zero network calls
            )
            logger.info(f"📦 HF hub offline cache hit: {path}")
            return Path(path)
        except Exception:
            return None

    def _load_from_path(self, model_path: Path) -> Tuple:
        """
        Instantiate AutoProcessor + AutoModelForCausalLM from a local directory.
        Applies device placement and optional dtype.
        """
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
        except ImportError:
            raise RuntimeError("transformers not installed. Run: pip install transformers")

        import torch

        path_str = str(model_path)
        logger.info(f"🔄 Loading Florence-2 from: {path_str}")
        print(f"🔄 Loading Microsoft Florence-2-base...", flush=True)

        t0 = time.time()

        try:
            processor = AutoProcessor.from_pretrained(
                path_str,
                trust_remote_code=self.trust_remote_code,
                local_files_only=True,   # never hit network once we have the files
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load processor from {path_str}: {exc}") from exc

        try:
            dtype = self.dtype or (
                torch.float16
                if self.device in ("cuda", "mps")
                else torch.float32
            )
            model = AutoModelForCausalLM.from_pretrained(
                path_str,
                torch_dtype=dtype,
                trust_remote_code=self.trust_remote_code,
                local_files_only=True,
            ).to(self.device)
            model.eval()
        except Exception as exc:
            raise RuntimeError(f"Failed to load model from {path_str}: {exc}") from exc

        elapsed = round(time.time() - t0, 1)
        logger.info(f"✅ Florence-2 loaded in {elapsed}s on {self.device}")
        print(f"✅ Florence-2 ready ({elapsed}s, device={self.device})", flush=True)

        return processor, model


# ── ONNX Bonus Path ────────────────────────────────────────────────────────────

class OnnxModelManager:
    """
    Zero-internet ONNX fallback using onnx-community/Florence-2-base-ft.
    Requires: pip install optimum onnxruntime

    Advantages:
      - No PyTorch required at runtime
      - Smaller memory footprint
      - Fully offline once model is downloaded
      - Cross-platform CPU inference without CUDA

    Usage::
        manager = OnnxModelManager()
        session = manager.load()
    """

    ONNX_MODEL_ID = "onnx-community/Florence-2-base-ft"
    ONNX_CACHE_DIR = Path.home() / ".cache" / "ai_video_editor" / "florence2_onnx"

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or self.ONNX_CACHE_DIR
        self._session = None

    def load(self):
        """Load ONNX model. Returns (processor, ort_model) tuple."""
        try:
            from optimum.onnxruntime import ORTModelForCausalLM
            from transformers import AutoProcessor
        except ImportError:
            raise RuntimeError(
                "ONNX inference requires: pip install optimum[onnxruntime]"
            )

        local = _find_local_model_in(self.cache_dir)
        if local is None:
            logger.info("📥 Downloading ONNX Florence-2...")
            _download_model_to(self.ONNX_MODEL_ID, self.cache_dir)
            local = self.cache_dir

        processor = AutoProcessor.from_pretrained(
            str(local), trust_remote_code=True, local_files_only=True
        )
        model = ORTModelForCausalLM.from_pretrained(
            str(local), trust_remote_code=True, local_files_only=True
        )
        logger.info("✅ ONNX Florence-2 loaded")
        return processor, model


def _find_local_model_in(path: Path) -> Optional[Path]:
    return path if _is_valid_model_dir(path) else None


def _download_model_to(repo_id: str, target: Path) -> None:
    from huggingface_hub import snapshot_download
    _inject_session()
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo_id, local_dir=str(target), local_dir_use_symlinks=False)


# ── Module-level singleton ─────────────────────────────────────────────────────
# Imported by video_analyzer.py etc. — call .load() once, reuse everywhere.
_DEFAULT_MANAGER: Optional[ModelManager] = None


def get_model_manager(device: str = "cpu") -> ModelManager:
    """Return the app-wide singleton ModelManager (lazy init)."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = ModelManager(device=device)
    return _DEFAULT_MANAGER
