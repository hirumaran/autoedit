"""
Smart Subtitle Placement Service
Uses heuristic video analysis to determine optimal subtitle placement.
Optimized for both horizontal and vertical (TikTok/Reels) videos.
No cloud APIs required - runs locally.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple


class SmartSubtitleService:
    """Analyzes video to find optimal subtitle placement using local heuristics."""

    def __init__(self):
        print("✅ Smart subtitle service initialized (local mode)")

    def extract_sample_frame(self, video_path: str, timestamp: float = 1.0) -> Optional[str]:
        """Extract a single frame from the video for analysis."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            output_path = tmp.name
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except Exception as e:
            print(f"⚠️ Frame extraction failed: {e}")
            return None

    def get_video_dimensions(self, video_path: str) -> Tuple[int, int]:
        """Get video width and height."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0:s=x",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            w, h = result.stdout.strip().split("x")
            return int(w), int(h)
        except Exception:
            return 1920, 1080  # Default to HD

    def get_optimized_style(self, video_path: str, style_preset: str = "sleek") -> Dict:
        """Get optimized subtitle style based on video dimensions."""
        width, height = self.get_video_dimensions(video_path)
        aspect_ratio = width / height if height > 0 else 16/9
        
        # Determine if vertical (TikTok/Reels) or horizontal
        is_vertical = aspect_ratio < 1.0
        
        # Base styles
        styles = {
            "sleek": {
                "font_name": "Inter-Bold",
                "font_size": 28 if is_vertical else 24,
                "primary_color": "&HFFFFFF",
                "outline_color": "&H000000",
                "outline_width": 2,
                "shadow": 1,
                "margin_v": 80 if is_vertical else 50,
                "alignment": 2  # Bottom center
            },
            "minimal": {
                "font_name": "JetBrains Mono",
                "font_size": 20 if is_vertical else 18,
                "primary_color": "&HFFFFFF",
                "outline_color": "&H000000",
                "outline_width": 1,
                "shadow": 0,
                "margin_v": 60 if is_vertical else 40,
                "alignment": 2
            },
            "meme": {
                "font_name": "Impact",
                "font_size": 36 if is_vertical else 32,
                "primary_color": "&HFFFFFF",
                "outline_color": "&H000000",
                "outline_width": 3,
                "shadow": 2,
                "margin_v": 100 if is_vertical else 60,
                "alignment": 2
            },
            "neon": {
                "font_name": "Courier New",
                "font_size": 24 if is_vertical else 22,
                "primary_color": "&H4DE0F4",
                "outline_color": "&H000000",
                "outline_width": 2,
                "shadow": 1,
                "margin_v": 70 if is_vertical else 50,
                "alignment": 2
            }
        }
        
        style = styles.get(style_preset.lower(), styles["sleek"])
        
        # Adjust for vertical videos - move subtitles up to avoid being covered by UI
        if is_vertical:
            style["margin_v"] = max(style["margin_v"], 120)
        
        print(f"📐 Video: {width}x{height} ({'vertical' if is_vertical else 'horizontal'})")
        
        return style


# Global instance
smart_subtitle_service = SmartSubtitleService()
