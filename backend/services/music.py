"""
Music Discovery & Library Service
Integrates free music sources with discovery, metadata, and editing features.
"""
import os
import json
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import requests


@dataclass
class MusicTrack:
    """Music track metadata."""
    id: str
    title: str
    artist: str
    genre: str
    mood: str
    bpm: int
    duration: float
    filename: str
    source: str  # 'local', 'fma', 'youtube_audio_library'
    preview_url: Optional[str] = None
    license: str = "Unknown"


class MusicLibraryService:
    """
    Complete music service with:
    - Local library management
    - Free Music Archive integration
    - Track metadata and discovery
    - Audio editing (trim, fade)
    """

    def __init__(self, music_dir: Path = None):
        self.music_dir = music_dir or Path(__file__).parent.parent / "data" / "music"
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.music_dir / "library.json"
        self.library: Dict[str, MusicTrack] = {}
        self._load_library()
        print(f"🎵 Music Library initialized ({len(self.library)} tracks)")

    def _load_library(self):
        """Load library metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    for track_id, track_data in data.items():
                        self.library[track_id] = MusicTrack(**track_data)
            except Exception as e:
                print(f"⚠️ Error loading library: {e}")
        
        # Scan for new files
        self._scan_local_files()

    def _save_library(self):
        """Save library metadata to disk."""
        data = {track_id: asdict(track) for track_id, track in self.library.items()}
        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)

    def _scan_local_files(self):
        """Scan music directory for new files and add to library."""
        for ext in ["*.mp3", "*.wav", "*.m4a", "*.aac", "*.ogg"]:
            for filepath in self.music_dir.glob(ext):
                track_id = self._generate_id(filepath.name)
                if track_id not in self.library:
                    # Auto-detect metadata from filename
                    name = filepath.stem
                    parts = name.replace("_", " ").replace("-", " ").split()
                    
                    # Get duration using ffprobe
                    duration = self._get_duration(str(filepath))
                    
                    # Guess genre/mood from filename
                    mood = "neutral"
                    genre = "unknown"
                    for keyword in ["upbeat", "happy", "energetic"]:
                        if keyword in name.lower():
                            mood = "upbeat"
                            break
                    for keyword in ["chill", "ambient", "calm", "relax"]:
                        if keyword in name.lower():
                            mood = "chill"
                            break
                    
                    self.library[track_id] = MusicTrack(
                        id=track_id,
                        title=name.replace("_", " ").title(),
                        artist="Unknown Artist",
                        genre=genre,
                        mood=mood,
                        bpm=120,  # Default BPM
                        duration=duration,
                        filename=filepath.name,
                        source="local",
                        license="Unknown - User Uploaded"
                    )
        self._save_library()

    def _generate_id(self, name: str) -> str:
        """Generate a unique ID from filename."""
        return hashlib.md5(name.encode()).hexdigest()[:12]

    def _get_duration(self, filepath: str) -> float:
        """Get audio duration using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 0.0

    def list_tracks(self, mood: str = None, genre: str = None) -> List[Dict]:
        """List all tracks, optionally filtered by mood or genre."""
        tracks = []
        for track in self.library.values():
            if mood and track.mood != mood:
                continue
            if genre and track.genre != genre:
                continue
            tracks.append(asdict(track))
        return tracks

    def get_track(self, track_id: str) -> Optional[Dict]:
        """Get a specific track by ID."""
        track = self.library.get(track_id)
        return asdict(track) if track else None

    def add_track(self, filename: str, content: bytes, metadata: Dict = None) -> Dict:
        """Add a new track to the library."""
        # Save file
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
        filepath = self.music_dir / safe_name
        filepath.write_bytes(content)
        
        # Create track entry
        track_id = self._generate_id(safe_name)
        duration = self._get_duration(str(filepath))
        
        track = MusicTrack(
            id=track_id,
            title=metadata.get("title", filepath.stem.replace("_", " ").title()),
            artist=metadata.get("artist", "Unknown Artist"),
            genre=metadata.get("genre", "unknown"),
            mood=metadata.get("mood", "neutral"),
            bpm=metadata.get("bpm", 120),
            duration=duration,
            filename=safe_name,
            source="local",
            license="User Uploaded"
        )
        
        self.library[track_id] = track
        self._save_library()
        
        return asdict(track)

    def search_free_music_archive(self, query: str = "", genre: str = "") -> List[Dict]:
        """
        Search Free Music Archive for Creative Commons music.
        Note: FMA API might be slow/unavailable on school networks.
        """
        try:
            # FMA doesn't have a public API anymore, so we'll return sample data
            # In production, you'd integrate with a real API
            sample_results = [
                {
                    "id": "fma_001",
                    "title": "Inspiring Acoustic",
                    "artist": "Scott Holmes",
                    "genre": "acoustic",
                    "mood": "uplifting",
                    "bpm": 110,
                    "duration": 180.0,
                    "source": "fma",
                    "license": "CC BY-NC",
                    "preview_url": None
                },
                {
                    "id": "fma_002",
                    "title": "Corporate Motivation",
                    "artist": "AShamaluev Music",
                    "genre": "corporate",
                    "mood": "upbeat",
                    "bpm": 125,
                    "duration": 150.0,
                    "source": "fma",
                    "license": "CC BY",
                    "preview_url": None
                },
                {
                    "id": "fma_003",
                    "title": "Chill Lo-Fi Beat",
                    "artist": "Lofi Vibes",
                    "genre": "lofi",
                    "mood": "chill",
                    "bpm": 85,
                    "duration": 200.0,
                    "source": "fma",
                    "license": "CC0",
                    "preview_url": None
                }
            ]
            return sample_results
        except Exception as e:
            print(f"⚠️ FMA search failed: {e}")
            return []

    def get_moods(self) -> List[str]:
        """Get list of available moods."""
        moods = set()
        for track in self.library.values():
            if track.mood:
                moods.add(track.mood)
        return sorted(list(moods)) or ["upbeat", "chill", "neutral", "dramatic", "romantic"]

    def get_genres(self) -> List[str]:
        """Get list of available genres."""
        genres = set()
        for track in self.library.values():
            if track.genre and track.genre != "unknown":
                genres.add(track.genre)
        return sorted(list(genres)) or ["pop", "rock", "electronic", "acoustic", "lofi", "corporate"]

    # === Audio Editing Functions ===

    def trim_audio(
        self, 
        track_id: str, 
        start: float, 
        end: float, 
        output_name: str = None
    ) -> str:
        """Trim audio to specified start/end times."""
        track = self.library.get(track_id)
        if not track:
            raise ValueError(f"Track not found: {track_id}")
        
        input_path = self.music_dir / track.filename
        output_name = output_name or f"trimmed_{track.filename}"
        output_path = self.music_dir / output_name
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return str(output_path)

    def add_fade(
        self,
        track_id: str,
        fade_in: float = 1.0,
        fade_out: float = 2.0,
        output_name: str = None
    ) -> str:
        """Add fade in/out to audio."""
        track = self.library.get(track_id)
        if not track:
            raise ValueError(f"Track not found: {track_id}")
        
        input_path = self.music_dir / track.filename
        output_name = output_name or f"faded_{track.filename}"
        output_path = self.music_dir / output_name
        
        fade_out_start = max(0, track.duration - fade_out)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}",
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return str(output_path)

    def add_music_to_video(
        self,
        video_path: str,
        track_id: str,
        output_path: str,
        volume: float = 0.3,
        fade_in: float = 1.0,
        fade_out: float = 2.0,
        loop: bool = True
    ) -> str:
        """Add background music to video with mixing and fading."""
        track = self.library.get(track_id)
        if not track:
            # Try to find by filename
            for t in self.library.values():
                if t.filename == track_id:
                    track = t
                    break
        
        if not track:
            raise ValueError(f"Track not found: {track_id}")
        
        music_path = self.music_dir / track.filename
        if not music_path.exists():
            raise FileNotFoundError(f"Music file not found: {music_path}")
        
        # Get video duration
        video_duration = self._get_duration(video_path)
        
        # Build filter
        if loop:
            music_filter = f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{video_duration},"
        else:
            music_filter = "[1:a]"
        
        music_filter += f"volume={volume},"
        music_filter += f"afade=t=in:st=0:d={fade_in},"
        music_filter += f"afade=t=out:st={max(0, video_duration - fade_out)}:d={fade_out}"
        music_filter += "[music];"
        music_filter += "[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", str(music_path),
            "-filter_complex", music_filter,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✅ Music added: {track.title}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg error: {e.stderr.decode()}")
            # Fallback to simpler mix
            return self._simple_mix(video_path, str(music_path), output_path, volume)

    def _simple_mix(self, video_path: str, music_path: str, output_path: str, volume: float) -> str:
        """Simple fallback mixing."""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={volume}[m];[0:a][m]amix=inputs=2:duration=first[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path


# Global instance
music_library = MusicLibraryService()
