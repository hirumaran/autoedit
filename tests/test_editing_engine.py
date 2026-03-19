"""
Tests for backend/editing_engine.py — MoviePyEngine and MoviePyAudioEngine.

Strategy: tests use unittest.mock and work regardless of whether MoviePy is
installed in the test environment.  When the module-level try/except skips the
real MoviePy imports (because MoviePy isn't installed), the tests inject
mocks directly onto the module and the engine instance so the logic paths
are still exercised.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from unittest.mock import MagicMock, patch, call, ANY

import pytest


# ---------------------------------------------------------------------------
# Helper to build a realistic mock VideoFileClip
# ---------------------------------------------------------------------------

def _make_mock_clip(duration: float = 10.0, size=(1920, 1080), fps: float = 30.0):
    clip = MagicMock()
    clip.duration = duration
    clip.size = size
    clip.fps = fps
    sub = MagicMock()
    sub.duration = duration
    sub.fps = fps
    sub.size = size
    clip.subclip.return_value = sub
    return clip


def _make_mock_audio(duration: float = 120.0):
    audio = MagicMock()
    audio.duration = duration
    sub = MagicMock()
    sub.duration = duration
    audio.subclip.return_value = sub
    return audio


# ---------------------------------------------------------------------------
# MoviePyEngine — trim
# ---------------------------------------------------------------------------

class TestMoviePyEngineTrim:
    """trim() calls subclip + write_videofile with correct arguments."""

    def test_trim_calls_subclip_with_correct_times(self):
        import editing_engine as ee
        mock_clip = _make_mock_clip(duration=10.0)  # clip is 10s long

        with patch.object(ee, "MOVIEPY_AVAILABLE", True):
            engine = ee.MoviePyEngine.__new__(ee.MoviePyEngine)
            engine.video_path = "/fake/input.mp4"
            engine._clip = mock_clip

            # end=30 is clamped to clip.duration (10s) inside trim()
            engine.trim(5.0, 30.0, "/fake/output.mp4", use_ffmpeg_fallback=False)

        # Engine clamps end to min(30.0, 10.0) == 10.0
        mock_clip.subclip.assert_called_once_with(5.0, 10.0)
        mock_clip.subclip.return_value.write_videofile.assert_called_once()

    def test_export_codec_is_libx264_aac(self):
        import editing_engine as ee
        mock_clip = _make_mock_clip()

        engine = ee.MoviePyEngine.__new__(ee.MoviePyEngine)
        engine.video_path = "/fake/input.mp4"
        engine._clip = mock_clip

        engine.trim(0.0, 10.0, "/fake/out.mp4", use_ffmpeg_fallback=False)

        _, kwargs = mock_clip.subclip.return_value.write_videofile.call_args
        assert kwargs.get("codec") == "libx264"
        assert kwargs.get("audio_codec") == "aac"

    @patch("editing_engine.subprocess.run")
    def test_trim_ffmpeg_fallback_uses_copy(self, mock_run):
        """The private _ffmpeg_trim helper issues ffmpeg -c copy."""
        import editing_engine as ee

        engine = ee.MoviePyEngine.__new__(ee.MoviePyEngine)
        engine.video_path = "/fake/input.mp4"
        engine._clip = None

        engine._ffmpeg_trim(2.0, 8.0, "/fake/out.mp4")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-c" in cmd
        assert "copy" in cmd
        assert "-ss" in cmd


# ---------------------------------------------------------------------------
# MoviePyEngine — subtitles
# ---------------------------------------------------------------------------

class TestMoviePyEngineSubtitles:
    """add_subtitles builds one TextClip per non-empty segment."""

    def test_subtitle_clips_created_per_segment(self):
        import editing_engine as ee

        mock_clip = _make_mock_clip()
        mock_txt = MagicMock()
        mock_txt.set_position.return_value = mock_txt
        mock_txt.set_start.return_value = mock_txt
        mock_txt.set_duration.return_value = mock_txt

        mock_composite = MagicMock()
        mock_composite.write_videofile = MagicMock()

        engine = ee.MoviePyEngine.__new__(ee.MoviePyEngine)
        engine.video_path = "/fake/input.mp4"
        engine._clip = mock_clip

        segments = [
            {"text": "Hello", "start": 0.0, "end": 2.0},
            {"text": "World", "start": 3.0, "end": 5.0},
            {"text": "",      "start": 6.0, "end": 7.0},  # empty → skipped
        ]

        # Ensure module-level symbols exist even without MoviePy installed
        if not hasattr(ee, "TextClip"):
            ee.TextClip = MagicMock()
        if not hasattr(ee, "CompositeVideoClip"):
            ee.CompositeVideoClip = MagicMock()

        with (
            patch.object(ee, "TextClip", return_value=mock_txt) as mock_TextClip,
            patch.object(ee, "CompositeVideoClip", return_value=mock_composite),
        ):
            engine.add_subtitles(segments, "/fake/out.mp4", style_preset="meme")

        # Only 2 non-empty segments → 2 TextClips
        assert mock_TextClip.call_count == 2
        mock_composite.write_videofile.assert_called_once()

    @patch("editing_engine.shutil.copy")
    def test_no_clip_falls_back_to_copy(self, mock_copy):
        import editing_engine as ee

        engine = ee.MoviePyEngine.__new__(ee.MoviePyEngine)
        engine.video_path = "/fake/input.mp4"
        engine._clip = None  # MoviePy unavailable

        engine.add_subtitles([{"text": "Hi", "start": 0, "end": 1}], "/fake/out.mp4")
        mock_copy.assert_called_once_with("/fake/input.mp4", "/fake/out.mp4")


# ---------------------------------------------------------------------------
# MoviePyAudioEngine — fade
# ---------------------------------------------------------------------------

class TestMoviePyAudioEngineFade:
    """add_fade applies audio_fadein then audio_fadeout."""

    def test_fade_in_and_out_applied_in_order(self):
        import editing_engine as ee

        mock_audio = _make_mock_audio()
        mock_faded = MagicMock()
        mock_faded.write_audiofile = MagicMock()

        engine = ee.MoviePyAudioEngine.__new__(ee.MoviePyAudioEngine)
        engine.audio_path = "/fake/music.mp3"
        engine._clip = mock_audio

        def fake_fadein(clip, t):
            assert clip is mock_audio
            assert t == 1.5
            return mock_faded

        def fake_fadeout(clip, t):
            assert clip is mock_faded
            assert t == 3.0
            return mock_faded

        # Stub symbols on module if MoviePy isn't installed
        if not hasattr(ee, "audio_fadein"):
            ee.audio_fadein = MagicMock()
        if not hasattr(ee, "audio_fadeout"):
            ee.audio_fadeout = MagicMock()

        with (
            patch.object(ee, "audio_fadein", side_effect=fake_fadein),
            patch.object(ee, "audio_fadeout", side_effect=fake_fadeout),
        ):
            engine.add_fade("/fake/faded.mp3", fade_in=1.5, fade_out=3.0)

        mock_faded.write_audiofile.assert_called_once_with("/fake/faded.mp3", logger=None)


# ---------------------------------------------------------------------------
# MoviePyAudioEngine — trim
# ---------------------------------------------------------------------------

class TestMoviePyAudioEngineTrim:
    """trim() calls subclip with the correct time range."""

    def test_trim_subclip_called(self):
        import editing_engine as ee

        mock_audio = _make_mock_audio(duration=180.0)

        engine = ee.MoviePyAudioEngine.__new__(ee.MoviePyAudioEngine)
        engine.audio_path = "/fake/music.mp3"
        engine._clip = mock_audio

        engine.trim(10.0, 60.0, "/fake/trimmed.mp3")

        mock_audio.subclip.assert_called_once_with(10.0, 60.0)
        mock_audio.subclip.return_value.write_audiofile.assert_called_once_with(
            "/fake/trimmed.mp3", logger=None
        )


# ---------------------------------------------------------------------------
# FFmpeg fallback path (no MoviePy, _clip = None)
# ---------------------------------------------------------------------------

class TestFallbackOnImportError:
    """The private _ffmpeg_* helpers issue correct subprocess calls."""

    @patch("editing_engine.subprocess.run")
    def test_ffmpeg_trim_flags(self, mock_run):
        import editing_engine as ee

        engine = ee.MoviePyEngine.__new__(ee.MoviePyEngine)
        engine.video_path = "/fake/input.mp4"
        engine._clip = None

        engine._ffmpeg_trim(0.0, 5.0, "/fake/out.mp4")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-ss" in cmd
        assert "-t" in cmd
        assert "/fake/out.mp4" in cmd

    @patch("editing_engine.subprocess.run")
    def test_ffmpeg_audio_trim_flags(self, mock_run):
        import editing_engine as ee

        engine = ee.MoviePyAudioEngine.__new__(ee.MoviePyAudioEngine)
        engine.audio_path = "/fake/music.mp3"
        engine._clip = None

        engine._ffmpeg_audio_trim(5.0, 30.0, "/fake/out.mp3")

        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "/fake/out.mp3" in cmd
