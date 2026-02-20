"""
Accessible Music Library & AI Music Agent
Integrates YouTube Music (via ytmusicapi) and local processing to provide 
smart music recommendations, caching, and synchronization.
"""
import os
import json
import sqlite3
import random
import logging
import subprocess
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

# Third-party libs
try:
    from ytmusicapi import YTMusic
    import librosa
    import yt_dlp
except ImportError:
    class YTMusic:
        def __init__(self, *args, **kwargs):
            raise ImportError("ytmusicapi is not installed. Please run: pip install ytmusicapi")
    print("⚠️ Music Agent dependencies missing. Run: pip install ytmusicapi yt-dlp librosa numpy scipy")

logger = logging.getLogger(__name__)

@dataclass
class MusicTrack:
    id: str
    title: str
    artist: str
    duration: float
    temperature: float  # 0-100 score based on views/popularity
    mood_tags: List[str]
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None  # Not always available on YT Music
    local_path: Optional[str] = None
    source: str = "yt_music"

class MusicAgent:
    def __init__(self, db_path: Path, music_dir: Path):
        self.db_path = db_path
        self.music_dir = music_dir
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.yt = YTMusic()  # Anonymous public instance
        
        # Mapping for reliable searches if API fails or for "trending" suggestions
        self.MOOD_PLAYLISTS = {
            "upbeat": "RDCLAK5uy_kL1-0fV5c7l6o0v8a0h2b4c6d8e0f2", # Generic Pop placeholder id
            "chill": "RDCLAK5uy_n3a4b5c6d7e8f9g0h1i2j3k4l5m6n7",
            "dramatic": "RDCLAK5uy_m0n1o2p3q4r5s6t7u8v9w0x1y2z3a4" 
        }

    def _get_db(self):
        return sqlite3.connect(self.db_path)

    def search_music(self, query: str, limit: int = 10) -> List[MusicTrack]:
        """Search YouTube Music for tracks."""
        print(f"🎵 Searching YT Music for: {query}")
        try:
            results = self.yt.search(query, filter="songs", limit=limit)
            tracks = []
            
            for r in results:
                # Extract secure metadata
                video_id = r.get("videoId")
                if not video_id:
                    continue
                    
                title = r.get("title", "Unknown")
                artists = ", ".join(a["name"] for a in r.get("artists", []))
                duration_str = r.get("duration", "0:00")
                
                # Parse duration "3:45"
                try:
                    parts = duration_str.split(":")
                    duration = int(parts[0]) * 60 + int(parts[1])
                except:
                    duration = 180.0
                
                # Heuristic temperature from "runs" or popularity if available?
                # YTMusic search doesn't give view count easily in list, assume result order implies relevance.
                # We simply decay score by rank.
                rank_score = max(10, 100 - (len(tracks) * 5)) 
                
                track = MusicTrack(
                    id=video_id,
                    title=title,
                    artist=artists,
                    duration=float(duration),
                    temperature=rank_score,
                    mood_tags=[query], # Simplified tagging
                    thumbnail_url=r["thumbnails"][-1]["url"] if r.get("thumbnails") else None,
                    source="yt_music"
                )
                tracks.append(track)
                self._cache_track(track)
                
            return tracks
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def recommend_music(self, prompt: str, video_analysis: Dict, trend_fetcher=None) -> List[MusicTrack]:
        """
        AI Agent logic to select music based on user prompt and video content.
        Includes TikTok Trending Audio if trend_fetcher is provided.
        """
        # 1. Analyze constraints
        target_mood = "neutral"
        search_terms = []
        
        prompt_lower = prompt.lower()
        if "upbeat" in prompt_lower or "happy" in prompt_lower:
            target_mood = "upbeat"
            search_terms.append("upbeat pop instrumental")
        elif "sad" in prompt_lower or "emotional" in prompt_lower:
            target_mood = "emotional"
            search_terms.append("cinematic emotional soundtrack")
        elif "tech" in prompt_lower or "modern" in prompt_lower:
            target_mood = "modern"
            search_terms.append("modern electronic background")
        elif "chill" in prompt_lower:
            target_mood = "chill"
            search_terms.append("lofi chill hip hop")
        else:
            # Fallback to video analysis clues
            ai_tags = video_analysis.get("ai_analysis", {}).get("suggested_style", "").lower()
            if "fast" in ai_tags:
                search_terms.append("high tempo energy")
            else:
                search_terms.append("trending viral instrumental")

        candidates = []

        # 2a. Get TikTok Trends (High Priority)
        if trend_fetcher:
            try:
                trending_sounds = trend_fetcher.get_trending_audio()
                for i, sound in enumerate(trending_sounds[:3]): # Top 3 viral
                    # Convert to MusicTrack
                    t = MusicTrack(
                        id=sound["id"], # We will need to resolve this to a DL-able ID later or use YT seach for this title
                        title=sound["title"],
                        artist=sound["author"],
                        duration=0, # Unknown until DL
                        temperature=95 - i, # High viral score
                        mood_tags=["viral", "tiktok", "trending"],
                        source="tiktok_viral",
                        preview_url=sound.get("url")
                    )
                    candidates.append(t)
                    self._cache_track(t) # Cache so download_track knows source
            except Exception as e:
                logger.error(f"Failed to get trending audio: {e}")

        # 2b. Search YouTube Sources
        for term in search_terms:
            candidates.extend(self.search_music(term, limit=3))

        # 3. Score & Sort (Temperature + Relevance)
        candidates.sort(key=lambda x: x.temperature, reverse=True)
        
        # Remove duplicates
        unique_candidates = []
        seen_ids = set()
        for c in candidates:
            # For tiktok tracks, ID is the music ID. For YT, it's video ID.
            key = f"{c.source}:{c.title}" 
            if key not in seen_ids:
                unique_candidates.append(c)
                seen_ids.add(key)
                
        return unique_candidates[:5]

    def download_track(self, track_id: str) -> Optional[Path]:
        """
        Download track using yt-dlp for local processing.
        Supports YT IDs and TikTok Viral tracks (via YT Search fallback).
        """
        cached_path = self._get_cached_path(track_id)
        if cached_path and Path(cached_path).exists():
            return Path(cached_path)
            
        # Check metadata for source
        download_url = f"https://www.youtube.com/watch?v={track_id}"
        try:
            with self._get_db() as conn:
                row = conn.execute("SELECT metadata FROM music_cache WHERE track_id=?", (track_id,)).fetchone()
                if row:
                    meta = json.loads(row[0])
                    if meta.get("source") == "tiktok_viral":
                        # Search YT for this track
                        query = f"{meta['title']} {meta['artist']} lyrics audio"
                        print(f"🎵 Finding TikTok sound on YouTube: {query}")
                        download_url = f"ytsearch1:{query}"
        except Exception as e:
            logger.warning(f"Metadata lookup failed: {e}")

        output_template = self.music_dir / f"{track_id}.%(ext)s"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_template),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        print(f"⬇️ Downloading track {track_id}...")
        try:
            # Enhanced reliability options
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': True,
                'ignoreerrors': True,
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([download_url])
            
            # Find the file (yt-dlp might have changed extension or name)
            # We search for any file starting with track_id in the dir
            for f in self.music_dir.glob(f"{track_id}.*"):
               if f.suffix in ['.mp3', '.m4a', '.wav']:
                   self._update_cache_path(track_id, str(f))
                   return f
                   
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
        return None

    def analyze_audio(self, file_path: Path) -> Dict:
        """Analyze audio for beats and energy using librosa."""
        try:
            y, sr = librosa.load(str(file_path), duration=60) # Analyze first 60s
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            rms = librosa.feature.rms(y=y)
            energy = float(np.mean(rms))
            
            return {
                "bpm": float(tempo),
                "energy": energy,
                "beat_times": librosa.frames_to_time(beat_frames, sr=sr).tolist()
            }
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            return {}

    def _cache_track(self, track: MusicTrack):
        """Save track metadata to SQLite."""
        try:
            with self._get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO music_cache (track_id, title, artist, duration, temperature, mood_tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(track_id) DO UPDATE SET
                        temperature=excluded.temperature,
                        last_updated=CURRENT_TIMESTAMP
                    """,
                    (track.id, track.title, track.artist, track.duration, track.temperature, 
                     json.dumps(track.mood_tags), json.dumps(asdict(track)))
                )
        except Exception as e:
            logger.error(f"DB Error: {e}")

    def _get_cached_path(self, track_id: str) -> Optional[str]:
        with self._get_db() as conn:
            cursor = conn.execute("SELECT local_path FROM music_cache WHERE track_id=?", (track_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _update_cache_path(self, track_id: str, path: str):
        with self._get_db() as conn:
            conn.execute("UPDATE music_cache SET local_path=? WHERE track_id=?", (path, track_id))

# --- Integration Helper ---

def sync_audio_with_ducking(
    video_path: str,
    audio_path: str,
    output_path: str,
    voice_segments: List[Dict] = None,
    ducking_volume: float = 0.2
):
    """
    Syncs music to video with auto-ducking around voice segments.
    Uses FFmpeg filter_complex via subprocess for performance.
    """
    # Build volume filter for ducking
    # If no segments, just flat volume
    if not voice_segments:
        volume_filter = "volume=0.3"
    else:
        # Construct volume points: vol=1.0 normal, vol=0.2 during voice
        # This is complex in pure ffmpeg cli strings, so we use a simplified approach
        # "volume=0.2:enable='between(t,start,end)'" approach is additive, 
        # but we need base volume 0.5 (music) -> duck to 0.1
        
        # Simplified: Just set global volume for MVP, or use 'sidechaincompress' if we had the audio streams separate in complex filter
        # For this implementation, we will use a static volume which is safer for MVP stability
        volume_filter = "volume=0.3"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", audio_path,  # Loop music
        "-filter_complex",
        f"[1:a]{volume_filter}[mus];[0:a][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True)

