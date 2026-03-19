import logging
import os
import torch

from model_manager import ModelManager as _ModelManager

logger = logging.getLogger(__name__)

# Lazy import — model only loads when first video is processed
_florence_loaded = False
_florence_processor = None
_florence_model     = None


def _get_florence(device: str):
    """
    Lazy loader: returns (processor, model), downloading on first call only.
    Thread-safe for single-worker Uvicorn (default). Add a Lock if using workers>1.
    """
    global _florence_loaded, _florence_processor, _florence_model

    if _florence_loaded:
        return _florence_processor, _florence_model

    try:
        from backend.utils.model_downloader import load_florence_model
        _florence_processor, _florence_model = load_florence_model(device=device)
        _florence_loaded = True
    except Exception as exc:
        logger.error(
            f"❌ Florence-2 unavailable: {exc}\n"
            "   Run `python -m backend.setup_models` to pre-download the model."
        )
        _florence_loaded = True   # prevent retry on every request
        _florence_processor = None
        _florence_model     = None

    return _florence_processor, _florence_model


class VideoAnalyzer:
    """Video analysis service using Florence-2 (lazy-loaded)."""

    def __init__(self):
        # Detect device once at init — do NOT load model here
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        logger.info(f"🔧 Video analyzer initialized (device: {self.device})")
        # Model loads lazily on first analyze() call — server starts instantly

    @property
    def processor(self):
        return _get_florence(self.device)[0]

    @property
    def model(self):
        return _get_florence(self.device)[1]

    # ...existing code (analyze, detect_objects, etc.) — unchanged...