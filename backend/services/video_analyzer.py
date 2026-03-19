from __future__ import annotations

import logging
import os
import torch

logger = logging.getLogger(__name__)

# ── Module-level lazy state ───────────────────────────────────────────────────
_load_attempted: bool = False
_processor = None
_model = None


def _lazy_load_florence(device: str):
    """
    Load Florence-2 exactly once (on first analyze() call, NOT at startup).
    Thread-safe enough for single-process uvicorn with --workers 1.
    """
    global _load_attempted, _processor, _model
    if _load_attempted:
        return _processor, _model

    _load_attempted = True  # prevent retry storms
    try:
        from backend.utils.model_manager import load_florence_model

        _processor, _model = load_florence_model(device=device)
    except RuntimeError as exc:
        # model_manager already printed detailed instructions
        logger.warning(f"⚠️  Florence-2 unavailable: {exc}")
        logger.warning("   Video analysis features disabled. See instructions above.")
        _processor = None
        _model = None
    except Exception as exc:
        logger.error(f"❌ Unexpected error loading Florence-2: {exc}", exc_info=True)
        _processor = None
        _model = None

    return _processor, _model


class VideoAnalyzer:
    """
    Video analysis service.

    Florence-2 is loaded lazily on the FIRST call to any analysis method,
    not at server startup. The server boots instantly even with no internet.
    """

    def __init__(self):
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        logger.info(f"🔧 VideoAnalyzer ready (device={self.device}, model=lazy)")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def processor(self):
        return _lazy_load_florence(self.device)[0]

    @property
    def model(self):
        return _lazy_load_florence(self.device)[1]

    @property
    def florence_ready(self) -> bool:
        """True only after successful model load."""
        return self.model is not None

    # ── Public API ─────────────────────────────────────────────────────────────

    def analyze_frame(self, image, task: str = "<CAPTION>") -> dict:
        """
        Run Florence-2 on a single PIL image.
        Returns {} with a warning if model unavailable.
        """
        if not self.florence_ready:
            logger.debug("analyze_frame called but Florence-2 not loaded — skipping")
            return {"error": "Florence-2 model not available", "result": None}

        try:
            inputs = self.processor(
                text=task,
                images=image,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    num_beams=3,
                )

            result = self.processor.batch_decode(
                generated_ids, skip_special_tokens=False
            )[0]
            parsed = self.processor.post_process_generation(
                result,
                task=task,
                image_size=(image.width, image.height),
            )
            return {"result": parsed, "error": None}

        except Exception as exc:
            logger.error(f"analyze_frame error: {exc}", exc_info=True)
            return {"error": str(exc), "result": None}

    def caption_frame(self, image) -> str:
        """Return a plain-text caption or empty string."""
        out = self.analyze_frame(image, task="<CAPTION>")
        if out["error"] or out["result"] is None:
            return ""
        cap = out["result"].get("<CAPTION>", "")
        return cap.strip() if isinstance(cap, str) else ""

    def detect_objects(self, image) -> list:
        """Return list of detected object dicts or [] if unavailable."""
        out = self.analyze_frame(image, task="<OD>")
        if out["error"] or out["result"] is None:
            return []
        od = out["result"].get("<OD>", {})
        bboxes = od.get("bboxes", [])
        labels = od.get("labels", [])
        return [
            {"label": lbl, "bbox": box}
            for lbl, box in zip(labels, bboxes)
        ]