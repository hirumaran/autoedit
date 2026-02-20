import ffmpeg
from pathlib import Path
from typing import Dict
import subprocess

SUBTITLE_STYLE_MAP = {
    "meme": {
        "FontName": "Impact",
        "FontSize": "48",
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H000000",
        "BorderStyle": "3",
        "Outline": "4",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": "80",
        "Bold": "-1"
    },
    "minimal": {
        "FontName": "Helvetica Neue",
        "FontSize": "38",
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H66000000",
        "BorderStyle": "4",
        "Outline": "1",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": "120",
        "Bold": "0"
    },
    "bold": {
        "FontName": "Gotham Bold",
        "FontSize": "44",
        "PrimaryColour": "&H0000FFFF",
        "OutlineColour": "&H00000000",
        "BorderStyle": "4",
        "Outline": "2",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": "90",
        "Bold": "-1"
    },
    "elegant": {
        "FontName": "Georgia",
        "FontSize": "42",
        "PrimaryColour": "&H00F5E6CC",
        "OutlineColour": "&H00000000",
        "BorderStyle": "4",
        "Outline": "1",
        "Shadow": "2",
        "Alignment": "2",
        "MarginV": "110",
        "Bold": "0"
    },
    "retro": {
        "FontName": "Futura",
        "FontSize": "46",
        "PrimaryColour": "&H0037FFEB",
        "OutlineColour": "&H00000000",
        "BorderStyle": "3",
        "Outline": "3",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": "85",
        "Bold": "-1"
    },
    "sleek": {
        "FontName": "SF Pro Display",
        "FontSize": "40",
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H66000000",
        "BorderStyle": "4",
        "Outline": "1",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": "130",
        "Bold": "0"
    },
    "neon": {
        "FontName": "Courier New",
        "FontSize": "40",
        "PrimaryColour": "&H004DE0F4",
        "OutlineColour": "&H00000000",
        "BorderStyle": "4",
        "Outline": "2",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": "120",
        "Bold": "-1"
    }
}


class VideoProcessor:
    def __init__(self, video_path: str):
        self.video_path = video_path
        try:
            self.probe = ffmpeg.probe(video_path)
            self.duration = float(self.probe['format']['duration'])
        except Exception as e:
            print(f"⚠️ Warning: Could not probe video: {e}")
            self.duration = 0

    def get_video_info(self) -> Dict:
        """Extract video metadata"""
        try:
            video_stream = next(
                (s for s in self.probe['streams'] if s['codec_type'] == 'video'),
                None
            )
            audio_stream = next(
                (s for s in self.probe['streams'] if s['codec_type'] == 'audio'),
                None
            )
            return {
                "duration": self.duration,
                "width": int(video_stream.get('width', 0)),
                "height": int(video_stream.get('height', 0)),
                "has_audio": audio_stream is not None
            }
        except Exception as e:
            return {"error": str(e)}

    def trim_video(self, start: float, end: float, output_path: str):
        """Cut video between start and end timestamps"""
        try:
            # Use simple ffmpeg command for reliability
            cmd = [
                'ffmpeg', '-y',  # Overwrite output
                '-ss', str(start),
                '-i', self.video_path,
                '-t', str(end - start),
                '-c', 'copy',  # Fast copy without re-encoding
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✂️ Trimmed video: {start}s to {end}s")
            return output_path
        except Exception as e:
            print(f"❌ Trim failed: {e}")
            raise

    def add_subtitles(self, subtitle_file: str, output_path: str, style: Dict = None):
        """Burn subtitles into video"""
        try:
            # Escape subtitle path for FFmpeg
            subtitle_file = subtitle_file.replace('\\', '/').replace(':', '\\\\:')
            style = style or SUBTITLE_STYLE_MAP.get("sleek")
            style_parts = [f"{key}={value}" for key, value in style.items()]
            force_style = ",".join(style_parts)
            cmd = [
                'ffmpeg', '-y',
                '-i', self.video_path,
                '-vf', f"subtitles={subtitle_file}:force_style='{force_style}'",
                '-c:a', 'copy',  # Copy audio without re-encoding
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"💬 Added subtitles from {subtitle_file}")
            return output_path
        except Exception as e:
            print(f"❌ Subtitle addition failed: {e}")
            # Fallback: just copy the video
            import shutil
            shutil.copy(self.video_path, output_path)
            return output_path

    def add_overlay(self, overlay_image: str, position: str, output_path: str):
        """Add logo/watermark overlay"""
        positions = {
            "top-left": "10:10",
            "top-right": "W-w-10:10",
            "bottom-left": "10:H-h-10",
            "bottom-right": "W-w-10:H-h-10",
            "center": "(W-w)/2:(H-h)/2"
        }
        try:
            (
                ffmpeg
                .input(self.video_path)
                .overlay(
                    ffmpeg.input(overlay_image),
                    x=positions.get(position, "10:10")
                )
                .output(output_path)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return output_path
        except Exception as e:
            print(f"❌ Overlay failed: {e}")
            raise

    def resize_for_platform(self, platform: str, output_path: str):
        """Resize video for social media"""
        sizes = {
            "instagram-reel": "1080:1920",
            "tiktok": "1080:1920",
            "youtube-short": "1080:1920",
            "instagram-post": "1080:1080",
        }
        size = sizes.get(platform, "1080:1920")
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', self.video_path,
                '-vf', f'scale={size}:force_original_aspect_ratio=decrease,pad={size}:(ow-iw)/2:(oh-ih)/2',
                '-c:a', 'copy',
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except Exception as e:
            print(f"❌ Resize failed: {e}")
            raise
