"""Phase 1 pipeline that combines WhisperX transcription with OCR/faces/logos."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from backend.services.transcription import transcription_service

try:
    from transformers import pipeline as hf_pipeline

    GLM_OCR_AVAILABLE = True
except Exception:  # pragma: no cover
    hf_pipeline = None  # type: ignore
    GLM_OCR_AVAILABLE = False

try:
    from insightface.app import FaceAnalysis  # type: ignore
except Exception:  # pragma: no cover
    FaceAnalysis = None  # type: ignore

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None  # type: ignore

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


@dataclass
class PhaseOneResult:
    transcription: List[Dict]
    on_screen_text: List[Dict]
    faces: List[Dict]
    logos: List[Dict]
    language: str
    duration: float

    def to_dict(self) -> Dict:
        return {
            "transcription": self.transcription,
            "on_screen_text": self.on_screen_text,
            "faces": self.faces,
            "logos": self.logos,
            "language": self.language,
            "duration": self.duration,
        }


class PhaseOneAnalyzer:
    """Runs enriching metadata extraction for the uploaded clip."""

    def __init__(self, temp_dir: Path, frames_per_second: int = 1):
        self.temp_dir = Path(temp_dir)
        self.frames_per_second = max(frames_per_second, 1)
        # Disable heavy detectors by default to keep processing fast and reliable.
        self.enable_ocr = os.getenv("ENABLE_OCR", "0") == "1"
        self.enable_faces = os.getenv("ENABLE_FACES", "0") == "1"
        self.enable_logos = os.getenv("ENABLE_LOGOS", "0") == "1"
        self._ocr_model = None
        self._face_app = None
        self._logo_model = None

    def process(self, video_path: str) -> PhaseOneResult:
        video = Path(video_path)
        scratch = Path(tempfile.mkdtemp(prefix="phase1_", dir=self.temp_dir))
        frames_dir = scratch / "frames"

        # Check if we need frames
        enrichment_needed = self.enable_ocr or self.enable_faces or self.enable_logos

        if enrichment_needed:
            frames_dir.mkdir(parents=True, exist_ok=True)
            duration = self._extract_frames(video, frames_dir)
        else:
            duration = self._probe_duration(video)

        transcription = transcription_service.transcribe(str(video))
        segments = transcription["segments"]
        language = transcription.get("language", "en")

        ocr_entries = self._run_ocr(frames_dir) if self.enable_ocr else []
        face_entries = self._run_face_detection(frames_dir) if self.enable_faces else []
        logo_entries = self._run_logo_detection(frames_dir) if self.enable_logos else []

        if enrichment_needed:
            shutil.rmtree(frames_dir, ignore_errors=True)
        else:
            shutil.rmtree(scratch, ignore_errors=True)

        return PhaseOneResult(
            transcription=segments,
            on_screen_text=ocr_entries,
            faces=face_entries,
            logos=logo_entries,
            language=language,
            duration=duration,
        )

    def _run_ocr(self, frames_dir: Path) -> List[Dict]:
        """Run OCR using GLM-4.6V vision model from HuggingFace."""
        if not GLM_OCR_AVAILABLE or hf_pipeline is None:
            print("⚠️ GLM-4.6V OCR unavailable (transformers not installed)")
            return []

        if self._ocr_model is None:
            try:
                print("🔄 Loading GLM-4.6V model for OCR (this may take a while)...")
                self._ocr_model = hf_pipeline(
                    "image-text-to-text",
                    model="zai-org/GLM-4.6V",
                    device_map="auto",  # Use GPU if available
                )
                print("✅ GLM-4.6V OCR model loaded")
            except Exception as e:
                print(f"⚠️ Failed to load GLM-4.6V: {e}")
                return []

        entries: List[Dict] = []
        for idx, frame in enumerate(sorted(frames_dir.glob("*.jpg"))):
            timestamp = idx / self.frames_per_second
            try:
                # Use GLM-4.6V to extract text from image
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "url": f"file://{str(frame)}"},
                            {
                                "type": "text",
                                "text": "Extract ALL visible text from this image. Return only the text, nothing else.",
                            },
                        ],
                    }
                ]
                result = self._ocr_model(text=messages)

                # Parse the result
                if result and isinstance(result, list) and len(result) > 0:
                    text = result[0].get("generated_text", "").strip()
                    if text:
                        entries.append(
                            {
                                "frame": frame.name,
                                "timestamp": timestamp,
                                "blocks": [{"text": text, "confidence": 1.0}],
                            }
                        )
            except Exception as e:
                print(f"⚠️ OCR failed for frame {frame.name}: {e}")
                continue

        return entries

    def _run_face_detection(self, frames_dir: Path) -> List[Dict]:
        if FaceAnalysis is None or cv2 is None:
            return []
        if self._face_app is None:
            try:
                self._face_app = FaceAnalysis(name="buffalo_l")
                self._face_app.prepare(ctx_id=-1)
            except Exception:
                return []
        faces: List[Dict] = []
        for idx, frame in enumerate(sorted(frames_dir.glob("*.jpg"))):
            timestamp = idx / self.frames_per_second
            image = cv2.imread(str(frame))
            if image is None:
                continue
            try:
                detections = self._face_app.get(image)
            except Exception:
                continue
            for det in detections or []:
                faces.append(
                    {
                        "frame": frame.name,
                        "timestamp": timestamp,
                        "bbox": det.bbox.tolist() if hasattr(det, "bbox") else [],
                        "embedding": det.embedding.tolist()
                        if hasattr(det, "embedding")
                        else [],
                    }
                )
        return faces

    def _run_logo_detection(self, frames_dir: Path) -> List[Dict]:
        if YOLO is None:
            return []
        if self._logo_model is None:
            try:
                self._logo_model = YOLO("yolov11n-openlogo.pt")
            except Exception:
                return []
        logos: List[Dict] = []
        for idx, frame in enumerate(sorted(frames_dir.glob("*.jpg"))):
            timestamp = idx / self.frames_per_second
            try:
                predictions = self._logo_model(str(frame), verbose=False)
            except Exception:
                continue
            for pred in predictions or []:
                boxes = getattr(pred, "boxes", None)
                if boxes is None:
                    continue
                for box in boxes:
                    logos.append(
                        {
                            "frame": frame.name,
                            "timestamp": timestamp,
                            "class_id": int(box.cls[0]),
                            "confidence": float(box.conf[0]),
                            "bbox": box.xyxy[0].tolist(),
                        }
                    )
        return logos

    def _extract_frames(self, video_path: Path, frames_dir: Path) -> float:
        duration = self._probe_duration(video_path)
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps={self.frames_per_second}",
            str(frames_dir / "%05d.jpg"),
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            pass
        return duration

    def _probe_duration(self, video_path: Path) -> float:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0
