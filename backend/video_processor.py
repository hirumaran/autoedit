import ffmpeg
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import math

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

# MoviePy engine — provides clean Python API over FFmpeg
try:
    from editing_engine import MoviePyEngine, MoviePyAudioEngine  # type: ignore

    _MOVIEPY_ENGINE_AVAILABLE = True
except ImportError:
    _MOVIEPY_ENGINE_AVAILABLE = False

SUBTITLE_STYLE_MAP = {
    "meme": {
        "FontName": "Impact",
        "FontSize": "32",
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BorderStyle": "3",
        "Outline": "3",
        "Shadow": "0",
        "Alignment": "2",
        "MarginV": "40",
        "Bold": "-1",
    },
    "minimal": {
        "FontName": "Arial",
        "FontSize": "24",
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BorderStyle": "3",
        "Outline": "2",
        "Shadow": "1",
        "Alignment": "2",
        "MarginV": "30",
        "Bold": "0",
    },
    "bold": {
        "FontName": "Arial",
        "FontSize": "28",
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BorderStyle": "3",
        "Outline": "2",
        "Shadow": "1",
        "Alignment": "2",
        "MarginV": "35",
        "Bold": "-1",
    },
    "elegant": {
        "FontName": "Georgia",
        "FontSize": "26",
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BorderStyle": "3",
        "Outline": "2",
        "Shadow": "2",
        "Alignment": "2",
        "MarginV": "35",
        "Bold": "0",
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
        "Bold": "-1",
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
        "Bold": "0",
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
        "Bold": "-1",
    },
}


class VideoProcessor:
    def __init__(self, video_path: str):
        self.video_path = video_path
        try:
            self.probe = ffmpeg.probe(video_path)
            self.duration = float(self.probe["format"]["duration"])
        except Exception as e:
            print(f"⚠️ Warning: Could not probe video: {e}")
            self.duration = 0

    def get_video_info(self) -> Dict:
        """Extract video metadata"""
        try:
            video_stream = next(
                (s for s in self.probe["streams"] if s["codec_type"] == "video"), None
            )
            audio_stream = next(
                (s for s in self.probe["streams"] if s["codec_type"] == "audio"), None
            )
            return {
                "duration": self.duration,
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "has_audio": audio_stream is not None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _video_dimensions(self) -> Tuple[int, int]:
        """Return source video width/height if available."""
        try:
            stream = next(
                (
                    s
                    for s in self.probe.get("streams", [])
                    if s.get("codec_type") == "video"
                ),
                None,
            )
            if not stream:
                return 0, 0
            return int(stream.get("width", 0)), int(stream.get("height", 0))
        except Exception:
            return 0, 0

    def _rotation_and_flip_filters(
        self, rotation: int, flip_horizontal: bool
    ) -> List[str]:
        filters: List[str] = []
        if rotation == 90:
            filters.append("transpose=1")
        elif rotation == 180:
            filters.extend(["transpose=1", "transpose=1"])
        elif rotation == 270:
            filters.append("transpose=2")
        if flip_horizontal:
            filters.append("hflip")
        return filters

    def _compress_tracking_points(
        self, points: List[Tuple[float, int]], max_points: int = 45
    ) -> List[Tuple[float, int]]:
        if len(points) <= max_points:
            return points
        step = max(1, math.ceil((len(points) - 1) / (max_points - 1)))
        reduced = [points[0]]
        idx = step
        while idx < len(points) - 1:
            reduced.append(points[idx])
            idx += step
        reduced.append(points[-1])
        return reduced

    def _extract_head_tracking_points(
        self, crop_w: int, sample_interval: float = 0.5
    ) -> List[Tuple[float, int]]:
        """
        Detect face/head centers over time and return (t, crop_x) keypoints.
        Falls back to center when detection is unavailable.
        """
        src_w, src_h = self._video_dimensions()
        fallback_x = max((src_w - crop_w) // 2, 0)
        if src_w <= 0 or src_h <= 0 or cv2 is None:
            return [(0.0, fallback_x)]

        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if cascade.empty():
            return [(0.0, fallback_x)]

        capture = cv2.VideoCapture(self.video_path)
        if not capture.isOpened():
            return [(0.0, fallback_x)]

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        duration = self.duration or ((frame_count / fps) if fps > 0 else 0.0)
        min_face_side = max(int(min(src_w, src_h) * 0.08), 24)

        points: List[Tuple[float, int]] = []
        next_sample_at = 0.0
        smoothed_x = float(fallback_x)
        smoothing_alpha = 0.35
        frame_idx = 0

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            t = (frame_idx / fps) if fps > 0 else 0.0
            frame_idx += 1

            if t + 1e-6 < next_sample_at:
                continue
            next_sample_at += sample_interval

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(min_face_side, min_face_side),
            )

            target_x = int(round(smoothed_x))
            if len(faces) > 0:
                x, _, w, _ = max(faces, key=lambda f: f[2] * f[3])
                center_x = x + (w / 2.0)
                target_x = int(round(center_x - (crop_w / 2.0)))

            target_x = max(0, min(target_x, max(src_w - crop_w, 0)))
            smoothed_x = (smoothing_alpha * target_x) + (
                (1.0 - smoothing_alpha) * smoothed_x
            )
            tracked_x = int(round(smoothed_x))

            if not points or abs(points[-1][1] - tracked_x) >= 6:
                points.append((round(t, 3), tracked_x))

        capture.release()

        if not points:
            points = [(0.0, fallback_x)]

        if duration > 0 and points[-1][0] < duration:
            points.append((round(duration, 3), points[-1][1]))

        return self._compress_tracking_points(points)

    def _build_piecewise_x_expr(self, points: List[Tuple[float, int]]) -> str:
        """Build FFmpeg crop x-expression from tracking keypoints."""
        if not points:
            return "0"
        if len(points) == 1:
            return str(points[0][1])

        expr = str(points[-1][1])
        for idx in range(len(points) - 2, -1, -1):
            t0, x0 = points[idx]
            t1, x1 = points[idx + 1]

            if t1 <= t0:
                segment = str(x1)
            elif x0 == x1:
                segment = str(x0)
            else:
                dt = t1 - t0
                segment = f"({x0}+({x1}-{x0})*(t-{t0:.3f})/{dt:.3f})"

            expr = f"if(lt(t\\,{t1:.3f})\\,{segment}\\,{expr})"

        return f"trunc({expr})"

    def _build_smart_crop_filter(self, target_w: int, target_h: int) -> str:
        """
        Build a head-tracked crop filter that follows subject horizontally.
        For non-horizontal mismatches, it falls back to center crop behavior.
        """
        src_w, src_h = self._video_dimensions()
        if src_w <= 0 or src_h <= 0 or target_w <= 0 or target_h <= 0:
            return (
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h},setsar=1"
            )

        target_ar = target_w / target_h
        src_ar = src_w / src_h

        crop_w = src_w
        crop_h = src_h
        if src_ar > target_ar:
            crop_w = min(src_w, max(2, int(round(src_h * target_ar))))
        elif src_ar < target_ar:
            crop_h = min(src_h, max(2, int(round(src_w / target_ar))))

        x_expr = f"(iw-{crop_w})/2"
        y_expr = f"(ih-{crop_h})/2"

        # Head tracking is most useful when trimming left/right from wide footage.
        if crop_w < src_w:
            points = self._extract_head_tracking_points(crop_w)
            x_expr = self._build_piecewise_x_expr(points)
            y_expr = "0"

        return f"crop={crop_w}:{crop_h}:{x_expr}:{y_expr},scale={target_w}:{target_h},setsar=1"

    def _transform_with_fit_blur(
        self,
        output_path: str,
        target_w: int,
        target_h: int,
        post_filters: Optional[List[str]] = None,
    ) -> str:
        """Compose a blurred-fill background with centered foreground."""
        post_filters = post_filters or []
        post_chain = ",".join(post_filters + ["setsar=1"])
        filter_complex = (
            f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},boxblur=35:12[bg];"
            f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"
            f"[base]{post_chain}[outv]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            self.video_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-map",
            "0:a?",
            "-c:a",
            "copy",
            "-preset",
            "fast",
            output_path,
        ]
        print(f"🎬 Transform (fit_blur): {target_w}x{target_h}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Transform FFmpeg error: {result.stderr[-500:]}")
            raise RuntimeError(f"FFmpeg transform failed: {result.stderr[-200:]}")
        print(f"✅ Transformed video → {output_path}")
        return output_path

    def trim_video(self, start: float, end: float, output_path: str):
        """Cut video between start and end timestamps.

        Tries MoviePy first for clean re-encoding; falls back to the original
        ffmpeg -c copy fast path if MoviePy is unavailable or fails.
        """
        # --- MoviePy path ---
        if _MOVIEPY_ENGINE_AVAILABLE:
            try:
                with MoviePyEngine(self.video_path) as engine:
                    engine.trim(start, end, output_path, use_ffmpeg_fallback=False)
                print(f"✂️ MoviePy trimmed: {start}s to {end}s")
                return output_path
            except Exception as e:
                print(f"⚠️ MoviePy trim failed ({e}); using FFmpeg fallback")

        # --- FFmpeg fallback (fast stream copy, no re-encode) ---
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(start),
                "-i",
                self.video_path,
                "-t",
                str(end - start),
                "-c",
                "copy",
                output_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✂️ FFmpeg trimmed: {start}s to {end}s")
            return output_path
        except Exception as e:
            print(f"❌ Trim failed: {e}")
            raise

    def add_subtitles(
        self,
        subtitle_file: str,
        output_path: str,
        style: Dict = None,
        style_preset: str = "sleek",
        subtitle_data: List[Dict] = None,
        video_width: int = 1080,
        video_height: int = 1920,
    ):
        """Burn subtitles into video using FFmpeg."""

        # --- If we have subtitle data but no file, generate an SRT ---
        if subtitle_data and not subtitle_file:
            subtitle_file = self._generate_srt(subtitle_data)

        if not subtitle_file or not Path(subtitle_file).exists():
            print(f"❌ No subtitle file available")
            import shutil

            shutil.copy(self.video_path, output_path)
            return output_path

        # --- FFmpeg subtitle burn ---
        try:
            # Use absolute path and escape for FFmpeg subtitles filter
            srt_path = str(Path(subtitle_file).resolve())
            # Escape special characters for FFmpeg filter
            srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

            style = style or SUBTITLE_STYLE_MAP.get(
                style_preset, SUBTITLE_STYLE_MAP.get("minimal")
            )
            style_parts = [f"{key}={value}" for key, value in style.items()]
            force_style = ",".join(style_parts)

            vf = f"subtitles='{srt_escaped}':force_style='{force_style}'"

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                self.video_path,
                "-vf",
                vf,
                "-c:a",
                "copy",
                output_path,
            ]
            print(f"💬 Subtitle FFmpeg: {vf}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ FFmpeg subtitle error: {result.stderr[-500:]}")
                # Fallback: try without escaping
                vf2 = f"subtitles={srt_path}:force_style='{force_style}'"
                cmd2 = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    self.video_path,
                    "-vf",
                    vf2,
                    "-c:a",
                    "copy",
                    output_path,
                ]
                subprocess.run(cmd2, check=True, capture_output=True)
            print(f"💬 Added subtitles from {subtitle_file}")
            return output_path
        except Exception as e:
            print(f"❌ Subtitle addition failed: {e}")
            import shutil

            shutil.copy(self.video_path, output_path)
            return output_path

    def _generate_srt(self, subtitle_data: List[Dict]) -> str:
        """Generate an SRT file from subtitle segment data."""
        import tempfile

        def format_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        srt_path = str(
            Path(tempfile.gettempdir()) / f"subs_{Path(self.video_path).stem}.srt"
        )
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(subtitle_data, 1):
                text = seg.get("text", "").strip()
                if not text:
                    continue
                start = format_time(seg.get("start", 0))
                end = format_time(seg.get("end", 0))
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
        print(f"📝 Generated SRT: {srt_path}")
        return srt_path

    def add_overlay(self, overlay_image: str, position: str, output_path: str):
        """Add logo/watermark overlay.

        Tries MoviePy CompositeVideoClip; falls back to ffmpeg-python overlay.
        """
        # Pixel-offset positions for MoviePy (relative to frame edges)
        moviepy_positions = {
            "top-left": (10, 10),
            "top-right": lambda w, h, ow, oh: (w - ow - 10, 10),
            "bottom-left": lambda w, h, ow, oh: (10, h - oh - 10),
            "bottom-right": lambda w, h, ow, oh: (w - ow - 10, h - oh - 10),
            "center": "center",
        }

        # --- MoviePy path ---
        if _MOVIEPY_ENGINE_AVAILABLE:
            try:
                from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip  # type: ignore

                base = VideoFileClip(self.video_path)
                logo = ImageClip(overlay_image).set_duration(base.duration)
                pos_key = moviepy_positions.get(position, (10, 10))
                if callable(pos_key):
                    bw, bh = base.size
                    lw, lh = logo.size
                    pos_val = pos_key(bw, bh, lw, lh)
                else:
                    pos_val = pos_key
                composed = CompositeVideoClip([base, logo.set_position(pos_val)])
                composed.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    preset="fast",
                    logger=None,
                    threads=2,
                )
                base.close()
                print(f"🖼️ MoviePy overlay ({position}) → {output_path}")
                return output_path
            except Exception as e:
                print(f"⚠️ MoviePy overlay failed ({e}); ffmpeg-python fallback")

        # --- ffmpeg-python fallback ---
        ffmpeg_positions = {
            "top-left": "10:10",
            "top-right": "W-w-10:10",
            "bottom-left": "10:H-h-10",
            "bottom-right": "W-w-10:H-h-10",
            "center": "(W-w)/2:(H-h)/2",
        }
        try:
            (
                ffmpeg.input(self.video_path)
                .overlay(
                    ffmpeg.input(overlay_image),
                    x=ffmpeg_positions.get(position, "10:10"),
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
        """Resize video for social media while preserving full frame by default."""
        sizes = {
            "instagram-reel": "1080:1920",
            "tiktok": "1080:1920",
            "youtube-short": "1080:1920",
            "instagram-post": "1080:1080",
        }
        size = sizes.get(platform, "1080:1920")
        target_w, target_h = size.split(":")
        return self.transform_video(
            output_path,
            aspect_ratio=f"{target_w}:{target_h}",
            resolution=f"{target_w}x{target_h}",
        )

    def transform_video(
        self,
        output_path: str,
        aspect_ratio: str = None,
        resolution: str = None,
        rotation: int = 0,
        flip_horizontal: bool = False,
        resize_mode: str = "fit",
    ):
        """
        Apply resize, rotation, and flip in a single FFmpeg pass.
        - aspect_ratio: e.g. "9:16", "1:1", "16:9"
        - resolution: e.g. "1080x1920"
        - rotation: 0, 90, 180, 270
        - flip_horizontal: True to mirror horizontally
        - resize_mode:
            "fit"        -> preserve full frame with padding
            "crop"       -> center-crop fill
            "smart_crop" -> head-tracked crop
            "fit_blur"   -> blurred background + centered foreground
        """
        try:
            filters = []
            post_filters = self._rotation_and_flip_filters(rotation, flip_horizontal)

            tw: Optional[int] = None
            th: Optional[int] = None
            if resolution:
                res_parts = resolution.split("x")
                if len(res_parts) == 2:
                    tw, th = int(res_parts[0]), int(res_parts[1])
                    if resize_mode == "fit_blur":
                        return self._transform_with_fit_blur(
                            output_path, tw, th, post_filters
                        )

                    if resize_mode == "smart_crop":
                        filters.append(self._build_smart_crop_filter(tw, th))
                    elif resize_mode == "crop":
                        if aspect_ratio:
                            parts = aspect_ratio.split(":")
                            if len(parts) == 2:
                                ar_w, ar_h = int(parts[0]), int(parts[1])
                            else:
                                ar_w, ar_h = tw, th
                        else:
                            ar_w, ar_h = tw, th

                        # Center-crop to target aspect ratio (fills frame).
                        filters.append(
                            f"crop=if(gt(iw/ih\\,{ar_w}/{ar_h})\\,ih*{ar_w}/{ar_h}\\,iw)"
                            f":if(gt(iw/ih\\,{ar_w}/{ar_h})\\,ih\\,iw*{ar_h}/{ar_w})"
                        )
                        filters.append(f"scale={tw}:{th}")
                    else:
                        # Preserve entire frame; pad to target canvas.
                        filters.append(
                            f"scale={tw}:{th}:force_original_aspect_ratio=decrease"
                        )
                        filters.append(
                            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=0x101010"
                        )
                        filters.append("setsar=1")
            elif aspect_ratio:
                # Fallback for requests with aspect ratio only and no explicit resolution.
                parts = aspect_ratio.split(":")
                if len(parts) == 2:
                    ar_w, ar_h = int(parts[0]), int(parts[1])
                    filters.append(
                        f"crop=if(gt(iw/ih\\,{ar_w}/{ar_h})\\,ih*{ar_w}/{ar_h}\\,iw)"
                        f":if(gt(iw/ih\\,{ar_w}/{ar_h})\\,ih\\,iw*{ar_h}/{ar_w})"
                    )

            filters.extend(post_filters)

            if not filters:
                # Nothing to do, just copy
                import shutil

                shutil.copy(self.video_path, output_path)
                return output_path

            vf = ",".join(filters)
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                self.video_path,
                "-vf",
                vf,
                "-c:a",
                "copy",
                "-preset",
                "fast",
                output_path,
            ]
            print(f"🎬 Transform: ffmpeg -vf '{vf}'")
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✅ Transformed video → {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ Transform failed: {e}")
            raise
