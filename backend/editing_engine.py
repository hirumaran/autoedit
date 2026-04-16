"""
MoviePy Editing Engine
======================
Built for MoviePy 2.x with safe import discovery.
Falls back to FFmpeg subprocess if MoviePy is unavailable.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MOVIEPY_AVAILABLE = False

# ── Safe MoviePy 2.x imports with discovery ──────────────────────────────────
# MoviePy 2.x changed effect class names between minor versions.
# We try multiple known names for each effect to be version-resilient.

VideoFileClip = None
AudioFileClip = None
TextClip = None
CompositeVideoClip = None
CompositeAudioClip = None
concatenate_videoclips = None
ImageClip = None

# Effect classes — set to None if unavailable
_AudioFadeIn = None
_AudioFadeOut = None
_AudioLoop = None
_MultiplyVolume = None
_MultiplySpeed = None
_FadeIn = None
_FadeOut = None
_Crop = None
_MirrorX = None
_Resize = None
_CrossFadeIn = None
_CrossFadeOut = None

try:
    from moviepy import (
        VideoFileClip,
        AudioFileClip,
        TextClip,
        CompositeVideoClip,
        CompositeAudioClip,
        concatenate_videoclips,
        ImageClip,
    )

    # ── Audio effects ─────────────────────────────────────────────────────
    try:
        from moviepy.audio.fx import AudioFadeIn as _AudioFadeIn
    except ImportError:
        pass
    try:
        from moviepy.audio.fx import AudioFadeOut as _AudioFadeOut
    except ImportError:
        pass
    try:
        from moviepy.audio.fx import AudioLoop as _AudioLoop
    except ImportError:
        pass
    try:
        from moviepy.audio.fx import MultiplyVolume as _MultiplyVolume
    except ImportError:
        pass

    # ── Video effects — try multiple known names per effect ───────────────
    # FadeIn / CrossFadeIn
    for _name in ("FadeIn", "CrossFadeIn"):
        try:
            _FadeIn = getattr(__import__("moviepy.video.fx", fromlist=[_name]), _name)
            break
        except (ImportError, AttributeError):
            continue

    # FadeOut / CrossFadeOut
    for _name in ("FadeOut", "CrossFadeOut"):
        try:
            _FadeOut = getattr(__import__("moviepy.video.fx", fromlist=[_name]), _name)
            break
        except (ImportError, AttributeError):
            continue

    # Crop
    try:
        from moviepy.video.fx import Crop as _Crop
    except ImportError:
        pass

    # MirrorX
    try:
        from moviepy.video.fx import MirrorX as _MirrorX
    except ImportError:
        pass

    # Resize
    try:
        from moviepy.video.fx import Resize as _Resize
    except ImportError:
        pass

    # MultiplySpeed / SpeedX
    for _name in ("MultiplySpeed", "SpeedX"):
        try:
            _MultiplySpeed = getattr(
                __import__("moviepy.video.fx", fromlist=[_name]), _name
            )
            break
        except (ImportError, AttributeError):
            continue

    MOVIEPY_AVAILABLE = True

    # Log what we found
    _found = [
        n
        for n, v in [
            ("FadeIn", _FadeIn),
            ("FadeOut", _FadeOut),
            ("Crop", _Crop),
            ("MirrorX", _MirrorX),
            ("Resize", _Resize),
            ("MultiplySpeed", _MultiplySpeed),
            ("AudioFadeIn", _AudioFadeIn),
            ("AudioFadeOut", _AudioFadeOut),
            ("AudioLoop", _AudioLoop),
            ("MultiplyVolume", _MultiplyVolume),
        ]
        if v is not None
    ]
    _missing = [
        n
        for n, v in [
            ("FadeIn", _FadeIn),
            ("FadeOut", _FadeOut),
            ("Crop", _Crop),
            ("MirrorX", _MirrorX),
            ("Resize", _Resize),
            ("MultiplySpeed", _MultiplySpeed),
        ]
        if v is None
    ]

    logger.info(f"✅ MoviePy 2.x loaded — effects available: {', '.join(_found)}")
    if _missing:
        logger.warning(
            f"⚠️  MoviePy effects missing (will use FFmpeg): {', '.join(_missing)}"
        )

except ImportError as e:
    MOVIEPY_AVAILABLE = False
    logger.warning(
        f"⚠️  MoviePy not available ({e}) — all operations fall back to FFmpeg subprocess"
    )
except Exception as e:
    MOVIEPY_AVAILABLE = False
    logger.warning(
        f"⚠️  MoviePy load error ({e}) — all operations fall back to FFmpeg subprocess"
    )


# ── Helpers: apply effect or skip ─────────────────────────────────────────────


def _apply_effects(clip, effects_list):
    """Apply a list of effect instances, skipping any that are None."""
    valid = [e for e in effects_list if e is not None]
    if valid:
        return clip.with_effects(valid)
    return clip


def _make_effect(cls, *args, **kwargs):
    """Instantiate an effect class, returning None if class is unavailable."""
    if cls is None:
        return None
    try:
        return cls(*args, **kwargs)
    except Exception as exc:
        logger.debug(f"Effect instantiation failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def _write_videofile(
    clip, output_path: str, preset: str = "fast", threads: int = 2
) -> None:
    clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        preset=preset,
        threads=threads,
        logger=None,
    )


def _write_audiofile(clip, output_path: str) -> None:
    clip.write_audiofile(output_path, fps=44100, logger=None)


# ---------------------------------------------------------------------------
# Subtitle style presets
# ---------------------------------------------------------------------------

SUBTITLE_STYLE_MOVIEPY: Dict[str, Dict] = {
    "meme": {
        "font": "Impact",
        "font_size": 64,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 4,
        "position": ("center", 0.85),
    },
    "minimal": {
        "font": "Helvetica-Neue",
        "font_size": 44,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 1,
        "position": ("center", 0.88),
    },
    "bold": {
        "font": "Arial-Bold",
        "font_size": 52,
        "color": "#FFFF00",
        "stroke_color": "black",
        "stroke_width": 2,
        "position": ("center", 0.87),
    },
    "elegant": {
        "font": "Georgia",
        "font_size": 48,
        "color": "#F5E6CC",
        "stroke_color": "black",
        "stroke_width": 1,
        "position": ("center", 0.86),
    },
    "retro": {
        "font": "Arial-Bold",
        "font_size": 54,
        "color": "#37FFEB",
        "stroke_color": "black",
        "stroke_width": 3,
        "position": ("center", 0.85),
    },
    "sleek": {
        "font": "Arial",
        "font_size": 46,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 1,
        "position": ("center", 0.88),
    },
    "neon": {
        "font": "Courier-Bold",
        "font_size": 46,
        "color": "#4DE0F4",
        "stroke_color": "black",
        "stroke_width": 2,
        "position": ("center", 0.87),
    },
}


# ---------------------------------------------------------------------------
# MoviePyEngine
# ---------------------------------------------------------------------------


class MoviePyEngine:
    """High-level video editing engine for MoviePy 2.x."""

    def __init__(self, video_path: str):
        self.video_path = video_path
        self._clip = None
        if MOVIEPY_AVAILABLE:
            try:
                self._clip = VideoFileClip(video_path)
                logger.info(
                    f"🎬 MoviePyEngine loaded: {video_path} ({self._clip.duration:.1f}s)"
                )
            except Exception as exc:
                logger.warning(
                    f"⚠️  Could not load clip ({exc}); FFmpeg fallback active"
                )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._clip is not None:
            try:
                self._clip.close()
            except Exception:
                pass
            self._clip = None

    @property
    def duration(self) -> float:
        return self._clip.duration if self._clip is not None else self._probe_duration()

    @property
    def fps(self) -> float:
        return (self._clip.fps or 30.0) if self._clip is not None else 30.0

    @property
    def size(self) -> Tuple[int, int]:
        return self._clip.size if self._clip is not None else (0, 0)

    def get_frame_at(self, t: float):
        if self._clip is None:
            raise RuntimeError(
                "MoviePy clip not available; use cv2.VideoCapture instead"
            )
        return self._clip.get_frame(t)

    def trim(
        self,
        start: float,
        end: float,
        output_path: str,
        *,
        use_ffmpeg_fallback: bool = True,
    ) -> str:
        if self._clip is not None:
            try:
                sub = self._clip.subclipped(start, min(end, self._clip.duration))
                _write_videofile(sub, output_path, preset="fast")
                logger.info(f"✂️  Trimmed {start}→{end}s → {output_path}")
                return output_path
            except Exception as exc:
                logger.warning(f"⚠️  MoviePy trim failed ({exc}); FFmpeg fallback")

        if use_ffmpeg_fallback:
            return self._ffmpeg_trim(start, end, output_path)
        raise RuntimeError("trim failed")

    def concatenate(
        self,
        segments: List[Tuple[float, float]],
        output_path: str,
        transition: str = "none",
    ) -> str:
        if self._clip is None:
            return self._ffmpeg_concat(segments, output_path)
        try:
            subclips = [
                self._clip.subclipped(s, min(e, self._clip.duration))
                for s, e in segments
            ]
            if transition == "fade" and _FadeIn and _FadeOut:
                XFADE = 0.25
                faded = []
                for i, sub in enumerate(subclips):
                    effects = []
                    if i > 0:
                        effects.append(_make_effect(_FadeIn, XFADE))
                    if i < len(subclips) - 1:
                        effects.append(_make_effect(_FadeOut, XFADE))
                    sub = _apply_effects(sub, effects)
                    faded.append(sub)
                subclips = faded
            final = concatenate_videoclips(subclips, method="compose")
            _write_videofile(final, output_path, preset="fast")
            logger.info(f"🔗 Concatenated {len(segments)} segments → {output_path}")
            return output_path
        except Exception as exc:
            logger.warning(f"⚠️  MoviePy concatenate failed ({exc}); FFmpeg fallback")
            return self._ffmpeg_concat(segments, output_path)

    def add_subtitles(
        self,
        subtitle_data: List[Dict],
        output_path: str,
        style_preset: str = "sleek",
        video_width: int = 1080,
        video_height: int = 1920,
    ) -> str:
        if self._clip is None:
            shutil.copy(self.video_path, output_path)
            return output_path

        style = SUBTITLE_STYLE_MOVIEPY.get(
            style_preset, SUBTITLE_STYLE_MOVIEPY["sleek"]
        )
        try:
            txt_clips = []
            for seg in subtitle_data:
                text = seg.get("text", "").strip()
                if not text:
                    continue
                start = float(seg.get("start", 0))
                end = float(seg.get("end", start + 2))
                duration = max(end - start, 0.1)

                tc = TextClip(
                    text=text,
                    font=style["font"],
                    font_size=style["font_size"],
                    color=style["color"],
                    stroke_color=style["stroke_color"],
                    stroke_width=style["stroke_width"],
                    method="label",
                    text_align="center",
                )
                pos = style["position"]
                if isinstance(pos[1], float):
                    pos = (pos[0], int(video_height * pos[1]))

                tc = tc.with_start(start).with_duration(duration).with_position(pos)
                txt_clips.append(tc)

            composed = CompositeVideoClip([self._clip] + txt_clips)
            _write_videofile(composed, output_path, preset="fast")
            logger.info(f"💬 Burned {len(txt_clips)} subtitle clips → {output_path}")
            return output_path
        except Exception as exc:
            logger.warning(f"⚠️  Subtitle burn failed ({exc}); copying source")
            shutil.copy(self.video_path, output_path)
            return output_path

    def apply_effect(
        self, output_path: str, effect_id: str, params: Optional[Dict] = None
    ) -> str:
        if self._clip is None:
            return self._ffmpeg_effect(output_path, effect_id, params)

        params = params or {}
        try:
            clip = self._clip

            if effect_id in ("color_grade_warm", "color_grade_cool", "high_contrast"):
                # No ColorX in MoviePy 2.x — use FFmpeg for color grading
                return self._ffmpeg_effect(output_path, effect_id, params)

            elif effect_id == "speed_ramp" and _MultiplySpeed:
                clip = _apply_effects(
                    clip, [_make_effect(_MultiplySpeed, params.get("fast_factor", 1.5))]
                )

            elif effect_id == "zoom_in" and _Resize and _Crop:
                scale = params.get("scale", 1.3)
                w, h = clip.size
                clip = _apply_effects(
                    clip,
                    [
                        _make_effect(_Resize, newsize=(int(w * scale), int(h * scale))),
                        _make_effect(
                            _Crop,
                            width=w,
                            height=h,
                            x_center=int(w * scale) // 2,
                            y_center=int(h * scale) // 2,
                        ),
                    ],
                )

            elif effect_id == "flash" and _FadeIn and _FadeOut:
                dur = params.get("duration", 0.1)
                clip = _apply_effects(
                    clip,
                    [
                        _make_effect(_FadeIn, dur),
                        _make_effect(_FadeOut, dur),
                    ],
                )

            elif effect_id == "mirror" and _MirrorX:
                clip = _apply_effects(clip, [_make_effect(_MirrorX)])

            else:
                logger.info(
                    f"Effect '{effect_id}' not available in MoviePy; using FFmpeg"
                )
                return self._ffmpeg_effect(output_path, effect_id, params)

            _write_videofile(clip, output_path, preset="fast")
            logger.info(f"✨ Applied '{effect_id}' → {output_path}")
            return output_path

        except Exception as exc:
            logger.warning(f"⚠️  Effect '{effect_id}' failed ({exc}); FFmpeg fallback")
            return self._ffmpeg_effect(output_path, effect_id, params)

    def export(
        self,
        output_path: str,
        clip=None,
        preset: str = "medium",
        threads: int = 2,
        fps: Optional[float] = None,
    ) -> str:
        target = clip if clip is not None else self._clip
        if target is None:
            shutil.copy(self.video_path, output_path)
            return output_path
        try:
            _write_videofile(target, output_path, preset=preset, threads=threads)
            return output_path
        except Exception as exc:
            logger.error(f"❌ Export failed: {exc}")
            raise

    # ------------------------------------------------------------------
    # FFmpeg fallbacks
    # ------------------------------------------------------------------

    def _ffmpeg_trim(self, start: float, end: float, output_path: str) -> str:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(start),
                "-i",
                self.video_path,
                "-t",
                str(end - start),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-avoid_negative_ts",
                "make_zero",
                output_path,
            ],
            check=True,
            capture_output=True,
        )
        logger.info(f"✂️  FFmpeg trim {start}→{end}s → {output_path}")
        return output_path

    def _ffmpeg_concat(
        self, segments: List[Tuple[float, float]], output_path: str
    ) -> str:
        import tempfile

        tmp_dir = Path(tempfile.mkdtemp(prefix="concat_"))
        try:
            segment_files = []
            for i, (s, e) in enumerate(segments):
                seg_path = str(tmp_dir / f"seg_{i:04d}.mp4")
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        str(s),
                        "-i",
                        self.video_path,
                        "-t",
                        str(e - s),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "fast",
                        "-crf",
                        "18",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-avoid_negative_ts",
                        "make_zero",
                        seg_path,
                    ],
                    check=True,
                    capture_output=True,
                )
                segment_files.append(seg_path)
            list_file = tmp_dir / "concat.txt"
            list_file.write_text("\n".join(f"file '{p}'" for p in segment_files))
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    output_path,
                ],
                check=True,
                capture_output=True,
            )
            return output_path
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _ffmpeg_effect(
        self, output_path: str, effect_id: str, params: Optional[Dict] = None
    ) -> str:
        """Apply effects purely via FFmpeg filter_complex."""
        params = params or {}
        vf_filters: List[str] = []

        if effect_id == "color_grade_warm":
            temp = params.get("temperature", 30)
            vf_filters.append(f"colorbalance=rs={temp / 200}:gs=0:bs=-{temp / 300}")
        elif effect_id == "color_grade_cool":
            temp = abs(params.get("temperature", 30))
            vf_filters.append(f"colorbalance=rs=-{temp / 300}:gs=0:bs={temp / 200}")
        elif effect_id == "high_contrast":
            contrast = params.get("contrast", 1.4)
            vf_filters.append(f"eq=contrast={contrast}")
        elif effect_id == "speed_ramp":
            factor = params.get("fast_factor", 1.5)
            vf_filters.append(f"setpts={1 / factor}*PTS")
        elif effect_id == "zoom_in":
            scale = params.get("scale", 1.3)
            vf_filters.append(f"scale=iw*{scale}:ih*{scale},crop=iw/{scale}:ih/{scale}")
        elif effect_id == "flash":
            dur = params.get("duration", 0.1)
            vf_filters.append(f"fade=in:st=0:d={dur},fade=out:st=0:d={dur}")
        elif effect_id == "mirror":
            vf_filters.append("hflip")
        else:
            logger.warning(f"Unknown effect '{effect_id}'; copying source")
            shutil.copy(self.video_path, output_path)
            return output_path

        vf = ",".join(vf_filters)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            self.video_path,
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-c:a",
            "copy",
            output_path,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"✨ FFmpeg effect '{effect_id}' → {output_path}")
        except subprocess.CalledProcessError as exc:
            logger.warning(f"⚠️  FFmpeg effect failed ({exc}); copying source")
            shutil.copy(self.video_path, output_path)
        return output_path

    def _probe_duration(self) -> float:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    self.video_path,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# MoviePyAudioEngine
# ---------------------------------------------------------------------------


class MoviePyAudioEngine:
    """High-level audio editing engine for MoviePy 2.x."""

    def __init__(self, audio_path: str):
        self.audio_path = audio_path
        self._clip = None
        if MOVIEPY_AVAILABLE:
            try:
                self._clip = AudioFileClip(audio_path)
                logger.info(
                    f"🎵 MoviePyAudioEngine loaded: {audio_path} ({self._clip.duration:.1f}s)"
                )
            except Exception as exc:
                logger.warning(f"⚠️  Could not load audio ({exc})")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._clip is not None:
            try:
                self._clip.close()
            except Exception:
                pass
            self._clip = None

    @property
    def duration(self) -> float:
        return self._clip.duration if self._clip is not None else 0.0

    def add_fade(
        self, output_path: str, fade_in: float = 1.0, fade_out: float = 2.0
    ) -> str:
        if self._clip is not None and _AudioFadeIn and _AudioFadeOut:
            try:
                clip = _apply_effects(
                    self._clip,
                    [
                        _make_effect(_AudioFadeIn, fade_in),
                        _make_effect(_AudioFadeOut, fade_out),
                    ],
                )
                _write_audiofile(clip, output_path)
                logger.info(f"🎵 Audio fade → {output_path}")
                return output_path
            except Exception as exc:
                logger.warning(f"⚠️  MoviePy audio fade failed ({exc}); FFmpeg fallback")
        return self._ffmpeg_fade(output_path, fade_in, fade_out)

    def trim(self, start: float, end: float, output_path: str) -> str:
        if self._clip is not None:
            try:
                sub = self._clip.subclipped(start, min(end, self._clip.duration))
                _write_audiofile(sub, output_path)
                logger.info(f"✂️  Audio trimmed {start}→{end}s → {output_path}")
                return output_path
            except Exception as exc:
                logger.warning(f"⚠️  MoviePy audio trim failed ({exc}); FFmpeg fallback")
        return self._ffmpeg_audio_trim(start, end, output_path)

    def loop_to_duration(self, target_duration: float):
        if self._clip is None or _AudioLoop is None:
            return None
        try:
            return _apply_effects(
                self._clip, [_make_effect(_AudioLoop, duration=target_duration)]
            )
        except Exception as exc:
            logger.warning(f"⚠️  Audio loop failed: {exc}")
            return None

    def mix_with_ducking(
        self,
        video_path: str,
        output_path: str,
        speech_segments: Optional[List[Dict]] = None,
        bg_volume: float = 0.3,
        duck_volume: float = 0.08,
        fade_in: float = 1.0,
        fade_out: float = 2.0,
        is_preview: bool = False,
    ) -> str:
        if MOVIEPY_AVAILABLE and self._clip is not None:
            try:
                return self._moviepy_mix(
                    video_path,
                    output_path,
                    speech_segments or [],
                    bg_volume,
                    duck_volume,
                    fade_in,
                    fade_out,
                    is_preview,
                )
            except Exception as exc:
                logger.warning(f"⚠️  MoviePy mix failed ({exc}); FFmpeg fallback")
        return self._ffmpeg_mix(
            video_path,
            output_path,
            speech_segments or [],
            bg_volume,
            is_preview,
            duck_volume=duck_volume,
        )

    def _moviepy_mix(
        self,
        video_path: str,
        output_path: str,
        speech_segments: List[Dict],
        bg_volume: float,
        duck_volume: float,
        fade_in: float,
        fade_out: float,
        is_preview: bool,
    ) -> str:
        video_clip = VideoFileClip(video_path)
        if is_preview:
            video_clip = video_clip.subclipped(0, min(15, video_clip.duration))
            if _Resize:
                new_w = int(video_clip.w * 480 / video_clip.h)
                video_clip = _apply_effects(
                    video_clip, [_make_effect(_Resize, newsize=(new_w, 480))]
                )

        vduration = video_clip.duration
        music = self._clip

        if music.duration < vduration and _AudioLoop:
            try:
                music = _apply_effects(
                    music, [_make_effect(_AudioLoop, duration=vduration)]
                )
            except Exception:
                music = music.subclipped(0, min(music.duration, vduration))
        else:
            music = music.subclipped(0, vduration)

        fade_effects = []
        if _AudioFadeIn:
            fade_effects.append(_make_effect(_AudioFadeIn, fade_in))
        if _AudioFadeOut:
            fade_effects.append(_make_effect(_AudioFadeOut, fade_out))
        music = _apply_effects(music, fade_effects)

        def make_volume_fn(segments, hi, lo):
            def vol_fn(t):
                for seg in segments:
                    s, e = seg.get("start", -1), seg.get("end", -1)
                    if s - 0.3 <= t <= e + 0.3:
                        if t < s:
                            return hi - ((t - (s - 0.3)) / 0.3) * (hi - lo)
                        elif t > e:
                            return lo + ((t - e) / 0.3) * (hi - lo)
                        return lo
                return hi

            return vol_fn

        if speech_segments:
            vol_fn = make_volume_fn(speech_segments, bg_volume, duck_volume)
            music = music.fl(lambda gf, t: gf(t) * vol_fn(t))
        elif _MultiplyVolume:
            music = _apply_effects(music, [_make_effect(_MultiplyVolume, bg_volume)])

        final_audio = (
            CompositeAudioClip([video_clip.audio, music])
            if video_clip.audio is not None
            else music
        )
        final_video = video_clip.with_audio(final_audio)
        _write_videofile(
            final_video, output_path, preset="ultrafast" if is_preview else "medium"
        )
        video_clip.close()
        logger.info(f"🎬 MoviePy mix with ducking → {output_path}")
        return output_path

    def _ffmpeg_mix(
        self,
        video_path,
        output_path,
        speech_segments,
        bg_volume,
        is_preview,
        duck_volume=0.08,
    ):
        duration_flag = ["-t", "15"] if is_preview else []

        if speech_segments:
            ducks = "+".join(
                f"between(t,{s['start']},{s['end']})" for s in speech_segments
            )
            volume_filter = f"volume='if({ducks}, {round(duck_volume, 10)}, {bg_volume})':eval=frame"
        else:
            volume_filter = f"volume={bg_volume}"

        filter_complex = (
            f"[1:a]{volume_filter}[mus];"
            f"[0:a][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-stream_loop",
            "-1",
            "-i",
            self.audio_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast" if is_preview else "medium",
            "-c:a",
            "aac",
            "-shortest",
        ] + duration_flag
        if is_preview:
            cmd += ["-vf", "scale=-2:480"]
        cmd.append(output_path)
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"🎬 FFmpeg mix with ducking → {output_path}")
        return output_path

    def _ffmpeg_fade(self, output_path, fade_in, fade_out):
        try:
            fade_out_start = max(0, self.duration - fade_out)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    self.audio_path,
                    "-af",
                    f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}",
                    output_path,
                ],
                check=True,
                capture_output=True,
            )
            return output_path
        except Exception as exc:
            logger.error(f"❌ FFmpeg audio fade failed: {exc}")
            shutil.copy(self.audio_path, output_path)
            return output_path

    def _ffmpeg_audio_trim(self, start, end, output_path):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                self.audio_path,
                "-ss",
                str(start),
                "-to",
                str(end),
                "-c",
                "copy",
                output_path,
            ],
            check=True,
            capture_output=True,
        )
        return output_path
