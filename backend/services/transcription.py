"""
Transcription Service - Uses LOCAL Whisper for fast, offline transcription.
No network needed - bypasses school throttling completely.
"""
import os
from pathlib import Path
from typing import Any, Dict

import ffmpeg

# Try to import local whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
    print("✅ Local Whisper available (offline mode)")
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ Local Whisper not available, will try Groq API")


class TranscriptionService:
    """Transcription using LOCAL Whisper for speed (no network throttling)."""

    def __init__(self):
        self.model = None
        self.groq_client = None
        
        if WHISPER_AVAILABLE:
            print("🔧 Transcription config: Local Whisper (FAST, offline)")
        else:
            print("🔧 Transcription config: Groq Whisper API (network)")

    def _ensure_model(self):
        """Load local Whisper model (lazy load)."""
        if self.model is None and WHISPER_AVAILABLE:
            print("🔄 Loading Whisper model (first time may download ~150MB)...")
            # Use 'base' for speed, 'small' for better accuracy
            self.model = whisper.load_model("base")
            print("✅ Whisper 'base' model loaded (fast mode)")

    def _extract_audio(self, video_path: str, out_path: str) -> str:
        """Extract audio from video."""
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(stream, out_path, acodec="pcm_s16le", ar="16000", ac=1, loglevel="quiet")
        ffmpeg.run(stream, overwrite_output=True)
        return out_path

    def transcribe(self, video_path: str) -> Dict[str, Any]:
        """Transcribe using LOCAL Whisper (fast, no network)."""
        audio_path = self._extract_audio(video_path, "temp_audio.wav")
        
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"📁 Audio file size: {file_size_mb:.2f} MB")
        
        if WHISPER_AVAILABLE:
            return self._transcribe_local(audio_path)
        else:
            return self._transcribe_groq(audio_path)

    def _transcribe_local(self, audio_path: str) -> Dict[str, Any]:
        """Use local Whisper - FAST, no network needed."""
        self._ensure_model()
        
        print("🎙️ Running LOCAL transcription (no network, fast)...")
        try:
            # Transcribe with word timestamps
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False
            )
            
            # Format segments
            formatted_segments = []
            for seg in result.get("segments", []):
                words = []
                for w in seg.get("words", []):
                    words.append({
                        "word": w.get("word", "").strip(),
                        "start": w.get("start", 0),
                        "end": w.get("end", 0),
                        "confidence": w.get("probability", 1.0)
                    })
                
                formatted_segments.append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", "").strip(),
                    "speaker": "SPEAKER_00",
                    "words": words
                })
            
            language = result.get("language", "en")
            print(f"✅ Local transcription complete: {language.upper()}")
            
            # Cleanup
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                "language": language,
                "segments": formatted_segments
            }
            
        except Exception as exc:
            print(f"❌ Local transcription failed: {exc}")
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise RuntimeError(f"Local Whisper failed: {exc}")

    def _transcribe_groq(self, audio_path: str) -> Dict[str, Any]:
        """Fallback to Groq API if local Whisper unavailable."""
        from groq import Groq
        
        if self.groq_client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY not found and local Whisper unavailable")
            self.groq_client = Groq(api_key=api_key, timeout=300.0)
            print("✅ Groq client initialized (fallback)")
        
        # Check file size
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if file_size_mb > 25:
            os.remove(audio_path)
            raise RuntimeError(f"Audio too large ({file_size_mb:.1f}MB). Max is 25MB.")
        
        print("🎙️ Running Groq transcription (network - may be slow)...")
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.groq_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"]
                )
            
            formatted_segments = []
            for seg in transcript.segments:
                words = []
                if hasattr(seg, 'words') and seg.words:
                    for w in seg.words:
                        words.append({
                            "word": getattr(w, 'word', '').strip(),
                            "start": getattr(w, 'start', 0),
                            "end": getattr(w, 'end', 0),
                            "confidence": 1.0
                        })
                
                formatted_segments.append({
                    "start": getattr(seg, 'start', 0),
                    "end": getattr(seg, 'end', 0),
                    "text": getattr(seg, 'text', '').strip(),
                    "speaker": "SPEAKER_00",
                    "words": words
                })
            
            language = getattr(transcript, 'language', 'en')
            print(f"✅ Groq transcription complete: {language.upper()}")
            
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                "language": language,
                "segments": formatted_segments
            }
            
        except Exception as exc:
            print(f"❌ Groq transcription failed: {exc}")
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise RuntimeError(f"Groq Whisper API failed: {exc}")


transcription_service = TranscriptionService()
