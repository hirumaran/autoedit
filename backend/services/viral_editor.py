
import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

# MoviePy audio engine — primary mixing path with FFmpeg fallback inside
try:
    from editing_engine import MoviePyAudioEngine  # type: ignore
    _AUDIO_ENGINE_AVAILABLE = True
except ImportError:
    _AUDIO_ENGINE_AVAILABLE = False

from services.music_agent import MusicAgent
from services.trend_fetcher import TrendFetcher
from video_processor import VideoProcessor

logger = logging.getLogger(__name__)

class ViralEditor:
    """
    Orchestrates the application of viral audio to videos.
    Handles previews, auto-ducking, and final export.
    """
    def __init__(self, music_agent: MusicAgent, output_dir: Path):
        self.music_agent = music_agent
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def smart_sync_cuts(
        self,
        video_path: str,
        audio_track_id: str,
        suggested_cuts: List[Dict]
    ) -> List[Dict]:
        """
        Adjusts suggested cut points to align with beat grid of the selected audio.
        Returns a list of adjusted cuts.
        """
        # 1. Download or locate audio
        audio_path = self.music_agent.download_track(audio_track_id)
        if not audio_path:
            logger.warning("Could not download audio for beat analysis, returning original cuts.")
            return suggested_cuts

        # 2. Analyze audio for beat times
        analysis = self.music_agent.analyze_audio(audio_path)
        beat_times = analysis.get("beat_times", [])

        if not beat_times:
            logger.warning("No beat times found, returning original cuts.")
            return suggested_cuts

        logger.info(f"🎵 Smart Sync: Found {len(beat_times)} beats. BPM: {analysis.get('bpm')}")

        # 3. Snap each cut point to the nearest beat
        def find_nearest_beat(time_val: float) -> float:
            if not beat_times:
                return time_val
            # Binary search or simple min
            return min(beat_times, key=lambda b: abs(b - time_val))

        synced_cuts = []
        for cut in suggested_cuts:
            start = cut.get("start", 0)
            end = cut.get("end", 0)
            
            synced_start = find_nearest_beat(start)
            synced_end = find_nearest_beat(end)
            
            # Ensure end > start after snapping
            if synced_end <= synced_start:
                synced_end = synced_start + 0.5 # Min segment duration

            synced_cuts.append({
                **cut,
                "start": round(synced_start, 3),
                "end": round(synced_end, 3),
                "synced": True
            })

        logger.info(f"✅ Smart Sync adjusted {len(synced_cuts)} cuts.")
        return synced_cuts

    def apply_viral_edit(
        self, 
        video_path: str, 
        audio_track_id: str, 
        transcript_segments: List[Dict] = None,
        volume_level: float = 0.3,
        is_preview: bool = False
    ) -> Dict:
        """
        Main entry point to apply viral audio.
        If is_preview is True, returns a low-res short snippet.
        
        Uses MoviePyAudioEngine (with speech ducking) as primary path;
        falls back to _render_with_ffmpeg for maximum compatibility.
        """
        try:
            # 1. Prepare Audio
            audio_path = self.music_agent.download_track(audio_track_id)
            if not audio_path:
                raise ValueError(f"Could not download audio: {audio_track_id}")

            # 2. Prepare Output Path
            suffix = "_preview.mp4" if is_preview else "_viral.mp4"
            filename = Path(video_path).stem + suffix
            output_path = self.output_dir / filename

            # 3. Apply Edit — MoviePy primary, FFmpeg fallback
            self._render_with_moviepy(
                str(video_path),
                str(audio_path),
                str(output_path),
                transcript_segments or [],
                volume_level,
                is_preview,
            )
            
            return {
                "success": True, 
                "output_path": str(output_path),
                "is_preview": is_preview
            }

        except Exception as e:
            logger.error(f"Viral edit failed: {e}")
            return {"success": False, "error": str(e)}

    def _render_with_moviepy(
        self,
        video_in: str,
        audio_in: str,
        video_out: str,
        segments: List[Dict],
        bg_volume: float,
        is_preview: bool,
    ):
        """
        Primary render path using MoviePyAudioEngine for smart ducking.
        Delegates to _render_with_ffmpeg if engine unavailable or fails.
        """
        if _AUDIO_ENGINE_AVAILABLE:
            try:
                with MoviePyAudioEngine(audio_in) as engine:
                    engine.mix_with_ducking(
                        video_path=video_in,
                        output_path=video_out,
                        speech_segments=segments,
                        bg_volume=bg_volume,
                        is_preview=is_preview,
                    )
                logger.info(f"✅ MoviePy render complete → {video_out}")
                return
            except Exception as exc:
                logger.warning(f"⚠️  MoviePy render failed ({exc}); FFmpeg fallback")

        self._render_with_ffmpeg(video_in, audio_in, video_out, segments, bg_volume, is_preview)

    def _render_with_ffmpeg(
        self, 
        video_in: str, 
        audio_in: str, 
        video_out: str, 
        segments: List[Dict], 
        bg_volume: float,
        is_preview: bool
    ):
        """
        Robust FFmpeg wrapper with Auto-Ducking support via complex filters.
        """
        # Duration check
        if is_preview:
            duration_flag = ["-t", "15"] # 15s preview
        else:
            duration_flag = []

        volume_filter = f"volume={bg_volume}"
        
        if segments:
            ducks = "+".join([f"between(t,{s['start']},{s['end']})" for s in segments])
            volume_filter = f"volume='if({ducks}, {bg_volume * 0.3}, {bg_volume})':eval=frame"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_in,
            "-stream_loop", "-1", "-i", audio_in,
            "-filter_complex", 
            f"[1:a]{volume_filter}[mus];[0:a][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "ultrafast" if is_preview else "medium",
            "-c:a", "aac", 
            "-shortest"
        ] + duration_flag + [video_out]

        if is_preview:
            cmd.insert(-1, "-vf")
            cmd.insert(-1, "scale=-2:480")

        logger.info(f"FFmpeg render: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)
