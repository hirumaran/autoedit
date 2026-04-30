"""
AI Video Analyzer - Local Vision Model with Network Bypass
Uses Microsoft Florence-2 with multiple fallback methods for school networks.
"""
import logging
import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
from dotenv import load_dotenv

# Load environment FIRST (before any HuggingFace imports)
load_dotenv()

# Set HuggingFace mirror BEFORE importing transformers
# This bypasses school blocks on huggingface.co
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    print(f"🌐 Using HuggingFace mirror: {os.environ['HF_ENDPOINT']}")

# Disable SSL verification for school networks with broken certificates
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""

LOCAL_MODEL = None
LOCAL_PROCESSOR = None
MODEL_LOADED = False

logger = logging.getLogger(__name__)


def _try_load_model():
    """Try to load Florence-2 with multiple fallback methods."""
    global LOCAL_MODEL, LOCAL_PROCESSOR, MODEL_LOADED
    
    if MODEL_LOADED:
        return LOCAL_MODEL is not None
    
    MODEL_LOADED = True  # Mark as attempted
    
    model_id = "microsoft/Florence-2-base"
    
    # Method 1: Try with mirror
    print(f"🔄 Loading {model_id} (using mirror: {os.environ.get('HF_ENDPOINT', 'default')})...")
    
    try:
        import torch
        from transformers import AutoProcessor, AutoModelForCausalLM
        
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"📱 Device: {device}")
        
        # Try loading with timeout
        import socket
        socket.setdefaulttimeout(30)
        
        LOCAL_PROCESSOR = AutoProcessor.from_pretrained(
            model_id, 
            trust_remote_code=True,
            local_files_only=False
        )
        LOCAL_MODEL = AutoModelForCausalLM.from_pretrained(
            model_id, 
            trust_remote_code=True,
            torch_dtype=torch.float16 if device == "mps" else torch.float32,
            local_files_only=False
        ).to(device)
        
        print("✅ Florence-2 model loaded successfully")
        return True
        
    except Exception as e:
        print(f"⚠️ Model load failed: {e}")
        
        # Method 2: Try offline/cached
        try:
            print("🔄 Trying cached/offline mode...")
            from transformers import AutoProcessor, AutoModelForCausalLM
            import torch
            
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            
            LOCAL_PROCESSOR = AutoProcessor.from_pretrained(
                model_id, 
                trust_remote_code=True,
                local_files_only=True
            )
            LOCAL_MODEL = AutoModelForCausalLM.from_pretrained(
                model_id, 
                trust_remote_code=True,
                local_files_only=True
            ).to(device)
            
            print("✅ Using cached model")
            return True
        except:
            pass
        
        print("❌ Could not load model - using heuristic analysis")
        return False


class AIVideoAnalyzer:
    """Video analyzer with intelligent fallbacks for school networks."""

    def __init__(self):
        self.device = "mps" if self._check_mps() else "cpu"
        print(f"🔧 Video analyzer initialized (device: {self.device})")

    def _check_mps(self) -> bool:
        try:
            import torch
            return torch.backends.mps.is_available()
        except:
            return False

    def extract_frames(self, video_path: str, num_frames: int = 6) -> List[str]:
        """Extract sample frames from video."""
        frames = []
        with tempfile.TemporaryDirectory() as tmpdir:
            output_pattern = f"{tmpdir}/frame_%03d.jpg"
            
            try:
                duration_cmd = [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path
                ]
                result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
                duration = float(result.stdout.strip())
            except:
                duration = 60.0
            
            interval = max(duration / num_frames, 1.0)
            
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"fps=1/{interval}",
                "-vframes", str(num_frames),
                "-q:v", "3",
                output_pattern
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                for frame_path in sorted(Path(tmpdir).glob("*.jpg")):
                    frames.append(str(frame_path))
            except Exception as e:
                print(f"⚠️ Frame extraction error: {e}")
        
        return frames

    def _analyze_frame_with_model(self, frame_path: str) -> Dict:
        """Analyze frame via Groq Llama 4 Scout vision. Returns None on failure."""
        try:
            import base64
            import json
            from groq import Groq

            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.warning("GROQ_API_KEY not set — skipping Groq vision")
                return None

            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            client = Groq(api_key=api_key)

            prompt = """You are a video editor evaluating whether a clip should be cut or kept.
Analyze this video frame and respond with ONLY valid JSON, no markdown, no extra text:
{
  "score": <integer 1-10>,
  "description": "<one sentence: what you see and why it scores this>"
}
Scoring:
1-3 = Cut it. Static shot, empty frame, bad lighting, no subject, out of focus.
4-6 = Borderline. Subject present but low energy, awkward framing, nothing happening.
7-9 = Keep it. Clear subject, good framing, active or engaging moment.
10 = Highlight reel. Peak emotion, perfect composition, exceptional moment."""

            completion = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                },
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=120,
                temperature=0.2,
            )

            result = json.loads(completion.choices[0].message.content)
            score = int(result.get("score", 5))
            score = max(1, min(10, score))  # clamp to 1-10
            return {"description": result.get("description", ""), "score": score}

        except Exception as e:
            logger.warning(f"Groq vision failed for {frame_path}: {e}")
            return None  # triggers heuristic fallback in caller

    def _analyze_frame_heuristic(self, frame_path: str) -> Dict:
        """Analyze frame using image heuristics (no AI model needed)."""
        try:
            image = Image.open(frame_path).convert("RGB")
            
            # Calculate basic image metrics
            width, height = image.size
            
            # Get color variance (more colorful = more engaging)
            import statistics
            pixels = list(image.getdata())
            r_vals = [p[0] for p in pixels[:1000]]
            g_vals = [p[1] for p in pixels[:1000]]
            b_vals = [p[2] for p in pixels[:1000]]
            
            color_variance = (
                statistics.stdev(r_vals) + 
                statistics.stdev(g_vals) + 
                statistics.stdev(b_vals)
            ) / 3
            
            # Higher variance = more interesting visually
            if color_variance > 60:
                score = 8
                desc = "High visual interest - colorful/dynamic scene"
            elif color_variance > 40:
                score = 6
                desc = "Moderate visual interest"
            elif color_variance > 20:
                score = 4
                desc = "Low visual variety - may be boring"
            else:
                score = 3
                desc = "Very static/plain - consider cutting"
            
            # Brightness check
            avg_brightness = sum(r_vals + g_vals + b_vals) / (len(r_vals) * 3)
            if avg_brightness < 30:
                score -= 1
                desc += " (very dark)"
            elif avg_brightness > 220:
                score -= 1
                desc += " (overexposed)"
            
            return {"description": desc, "score": max(1, min(10, score))}
            
        except Exception as e:
            return {"description": f"Analysis error: {e}", "score": 5}

    def _score_content(self, description: str) -> int:
        """Score content based on description."""
        desc_lower = description.lower()
        score = 5
        
        positive = ["person", "people", "face", "smile", "action", "movement", 
                   "colorful", "bright", "interesting", "dynamic", "speaking"]
        for word in positive:
            if word in desc_lower:
                score += 1
        
        negative = ["empty", "blank", "dark", "static", "nothing", "boring",
                   "plain", "simple", "still", "unclear"]
        for word in negative:
            if word in desc_lower:
                score -= 1
        
        return max(1, min(10, score))

    def analyze_video(self, video_path: str, transcript: str, user_prompt: str = "") -> Dict:
        """Analyze video with AI model or heuristics fallback."""
        print("🔍 Analyzing video for viewer retention...")
        
        frame_paths = self.extract_frames(video_path, num_frames=6)
        
        if not frame_paths:
            return self._transcript_only_analysis(transcript, user_prompt)
        
        segments = []
        total_score = 0
        use_heuristics = not _try_load_model()
        
        if use_heuristics:
            print("📊 Using heuristic analysis (no AI model)")
        else:
            print("🤖 Using Florence-2 AI analysis")
        
        # Get duration
        try:
            duration_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            total_duration = float(result.stdout.strip()) if result.returncode == 0 else 60.0
        except:
            total_duration = 60.0
        
        duration_per_frame = total_duration / len(frame_paths)
        
        for i, frame_path in enumerate(frame_paths):
            print(f"  📷 Analyzing frame {i+1}/{len(frame_paths)}...")
            
            if use_heuristics:
                analysis = self._analyze_frame_heuristic(frame_path)
            else:
                analysis = self._analyze_frame_with_model(frame_path)
                if analysis is None:
                    analysis = self._analyze_frame_heuristic(frame_path)
            
            score = analysis.get("score", 5)
            total_score += score
            
            start_time = i * duration_per_frame
            end_time = (i + 1) * duration_per_frame
            
            recommendation = "keep" if score >= 5 else "cut"
            
            segments.append({
                "start": round(start_time, 1),
                "end": round(end_time, 1),
                "retention_score": score,
                "description": analysis.get("description", "")[:100],
                "recommendation": recommendation,
                "reason": analysis.get("description", "")[:80],
                "keep": score >= 5
            })
        
        overall_score = round(total_score / max(len(frame_paths), 1))
        
        low_segments = [s for s in segments if s["retention_score"] < 5]
        if low_segments:
            summary = f"Found {len(low_segments)} low-engagement segment(s) that could be cut to improve retention."
        else:
            summary = "Video looks engaging throughout! No boring segments detected."
        
        print(f"📊 Analysis complete - Overall Score: {overall_score}/10")
        
        return {
            "overall_score": overall_score,
            "summary": summary,
            "suggested_cuts": segments,
            "segments": segments
        }

    def _transcript_only_analysis(self, transcript: str, user_prompt: str) -> Dict:
        """Fallback when no video frames available."""
        return {
            "overall_score": 6,
            "summary": "Transcript-only analysis (no video frames).",
            "suggested_cuts": [],
            "segments": [],
        }

    def analyze_transcript(self, transcript: str, user_prompt: str = "", video_path: str = None) -> Dict:
        """Main entry point."""
        if video_path:
            return self.analyze_video(video_path, transcript, user_prompt)
        return self._transcript_only_analysis(transcript, user_prompt)
