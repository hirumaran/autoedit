"""
AI Agent Video Editing Tools
=============================
Wraps MoviePyEngine and MoviePyAudioEngine as structured, LLM-callable tools.

Each tool is a plain function with a well-typed schema dict so any agent
framework (LangChain, CrewAI, AutoGen, raw OpenAI function-calling) can
discover and invoke them.

Usage (agent loop)::

    from backend.agent_tools import TOOLS, dispatch_tool

    # Give TOOLS to the LLM as its function/tool list.
    # When the LLM returns a tool_call, execute it:
    result = dispatch_tool(tool_name, arguments_dict)
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .editing_engine import MoviePyEngine, MoviePyAudioEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OUTPUT_DIR = Path("/tmp/agent_edits")
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _out(suffix: str = ".mp4") -> str:
    return str(_OUTPUT_DIR / f"{uuid.uuid4().hex}{suffix}")


# ---------------------------------------------------------------------------
# Individual tool functions
# ---------------------------------------------------------------------------

def tool_trim_video(video_path: str, start: float, end: float) -> Dict[str, Any]:
    """Trim a video to [start, end] seconds."""
    output = _out()
    with MoviePyEngine(video_path) as eng:
        eng.trim(start, end, output)
    return {"output_path": output, "start": start, "end": end}


def tool_concatenate_segments(
    video_path: str,
    segments: List[Dict[str, float]],
    transition: str = "none",
) -> Dict[str, Any]:
    """
    Concatenate multiple time segments from one video.

    segments format: [{"start": 0, "end": 5}, {"start": 10, "end": 20}]
    transition: "none" | "fade"
    """
    output = _out()
    seg_tuples = [(s["start"], s["end"]) for s in segments]
    with MoviePyEngine(video_path) as eng:
        eng.concatenate(seg_tuples, output, transition=transition)
    return {"output_path": output, "segments": segments, "transition": transition}


def tool_add_subtitles(
    video_path: str,
    subtitle_data: List[Dict],
    style_preset: str = "sleek",
) -> Dict[str, Any]:
    """
    Burn subtitles into a video.

    subtitle_data format: [{"text": "Hello", "start": 1.0, "end": 3.0}, ...]
    style_preset: meme | minimal | bold | elegant | retro | sleek | neon
    """
    output = _out()
    with MoviePyEngine(video_path) as eng:
        eng.add_subtitles(subtitle_data, output, style_preset=style_preset)
    return {"output_path": output, "style_preset": style_preset, "subtitle_count": len(subtitle_data)}


def tool_apply_effect(
    video_path: str,
    effect_id: str,
    params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Apply a visual effect to a video.

    effect_id options:
      color_grade_warm  — warm color grade (params: temperature 0-100)
      color_grade_cool  — cool color grade (params: temperature 0-100)
      high_contrast     — boost contrast   (params: contrast 1.0-2.0)
      speed_ramp        — speed up clip    (params: fast_factor 1.0-4.0)
      zoom_in           — zoom in effect   (params: scale 1.1-2.0)
      flash             — flash cut        (params: duration 0.05-0.5)
      mirror            — mirror horizontally
    """
    output = _out()
    with MoviePyEngine(video_path) as eng:
        eng.apply_effect(output, effect_id, params or {})
    return {"output_path": output, "effect_id": effect_id, "params": params}


def tool_mix_music(
    video_path: str,
    audio_path: str,
    bg_volume: float = 0.3,
    duck_volume: float = 0.08,
    speech_segments: Optional[List[Dict]] = None,
    fade_in: float = 1.0,
    fade_out: float = 2.0,
    is_preview: bool = False,
) -> Dict[str, Any]:
    """
    Mix background music into a video with smart speech ducking.

    speech_segments format: [{"start": 1.0, "end": 3.5}, ...]
    bg_volume: background music volume (0.0-1.0)
    duck_volume: music volume during speech (0.0-1.0)
    """
    output = _out()
    with MoviePyAudioEngine(audio_path) as aeng:
        aeng.mix_with_ducking(
            video_path=video_path,
            output_path=output,
            speech_segments=speech_segments or [],
            bg_volume=bg_volume,
            duck_volume=duck_volume,
            fade_in=fade_in,
            fade_out=fade_out,
            is_preview=is_preview,
        )
    return {"output_path": output, "bg_volume": bg_volume, "duck_volume": duck_volume}


def tool_audio_fade(
    audio_path: str,
    fade_in: float = 1.0,
    fade_out: float = 2.0,
) -> Dict[str, Any]:
    """Apply fade-in and fade-out to an audio file."""
    output = _out(".mp3")
    with MoviePyAudioEngine(audio_path) as aeng:
        aeng.add_fade(output, fade_in=fade_in, fade_out=fade_out)
    return {"output_path": output, "fade_in": fade_in, "fade_out": fade_out}


def tool_trim_audio(audio_path: str, start: float, end: float) -> Dict[str, Any]:
    """Trim an audio file to [start, end] seconds."""
    output = _out(".mp3")
    with MoviePyAudioEngine(audio_path) as aeng:
        aeng.trim(start, end, output)
    return {"output_path": output, "start": start, "end": end}


def tool_get_video_info(video_path: str) -> Dict[str, Any]:
    """Return duration, fps, and size (width x height) of a video."""
    with MoviePyEngine(video_path) as eng:
        return {
            "duration": eng.duration,
            "fps": eng.fps,
            "width": eng.size[0],
            "height": eng.size[1],
        }


# ---------------------------------------------------------------------------
# Tool registry — OpenAI / LangChain compatible schema
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "trim_video",
        "description": "Trim a video clip to a specific start and end time in seconds.",
        "function": tool_trim_video,
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Absolute path to the source video file."},
                "start": {"type": "number", "description": "Start time in seconds."},
                "end": {"type": "number", "description": "End time in seconds."},
            },
            "required": ["video_path", "start", "end"],
        },
    },
    {
        "name": "concatenate_segments",
        "description": "Concatenate multiple time-range segments from one video into a single output clip.",
        "function": tool_concatenate_segments,
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "number"},
                            "end": {"type": "number"},
                        },
                        "required": ["start", "end"],
                    },
                    "description": "List of {start, end} dicts in seconds.",
                },
                "transition": {
                    "type": "string",
                    "enum": ["none", "fade"],
                    "description": "Transition between segments.",
                },
            },
            "required": ["video_path", "segments"],
        },
    },
    {
        "name": "add_subtitles",
        "description": "Burn subtitle text into a video at specified timestamps.",
        "function": tool_add_subtitles,
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "subtitle_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "start": {"type": "number"},
                            "end": {"type": "number"},
                        },
                        "required": ["text", "start", "end"],
                    },
                },
                "style_preset": {
                    "type": "string",
                    "enum": ["meme", "minimal", "bold", "elegant", "retro", "sleek", "neon"],
                },
            },
            "required": ["video_path", "subtitle_data"],
        },
    },
    {
        "name": "apply_effect",
        "description": (
            "Apply a visual effect to a video. "
            "Available effects: color_grade_warm, color_grade_cool, high_contrast, "
            "speed_ramp, zoom_in, flash, mirror."
        ),
        "function": tool_apply_effect,
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "effect_id": {
                    "type": "string",
                    "enum": [
                        "color_grade_warm", "color_grade_cool", "high_contrast",
                        "speed_ramp", "zoom_in", "flash", "mirror",
                    ],
                },
                "params": {
                    "type": "object",
                    "description": "Effect-specific parameters (e.g. temperature, contrast, scale, fast_factor, duration).",
                },
            },
            "required": ["video_path", "effect_id"],
        },
    },
    {
        "name": "mix_music",
        "description": "Mix background music into a video with automatic volume ducking during speech.",
        "function": tool_mix_music,
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "audio_path": {"type": "string", "description": "Path to the background music file."},
                "bg_volume": {"type": "number", "description": "Background music volume 0.0-1.0 (default 0.3)."},
                "duck_volume": {"type": "number", "description": "Music volume during speech 0.0-1.0 (default 0.08)."},
                "speech_segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "number"},
                            "end": {"type": "number"},
                        },
                    },
                    "description": "Timestamps where speech occurs — music will duck here.",
                },
                "fade_in": {"type": "number", "description": "Music fade-in duration in seconds."},
                "fade_out": {"type": "number", "description": "Music fade-out duration in seconds."},
                "is_preview": {"type": "boolean", "description": "If true, renders a fast low-res 15s preview."},
            },
            "required": ["video_path", "audio_path"],
        },
    },
    {
        "name": "audio_fade",
        "description": "Apply fade-in and fade-out to an audio file.",
        "function": tool_audio_fade,
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {"type": "string"},
                "fade_in": {"type": "number"},
                "fade_out": {"type": "number"},
            },
            "required": ["audio_path"],
        },
    },
    {
        "name": "trim_audio",
        "description": "Trim an audio file to [start, end] seconds.",
        "function": tool_trim_audio,
        "parameters": {
            "type": "object",
            "properties": {
                "audio_path": {"type": "string"},
                "start": {"type": "number"},
                "end": {"type": "number"},
            },
            "required": ["audio_path", "start", "end"],
        },
    },
    {
        "name": "get_video_info",
        "description": "Get metadata about a video: duration (seconds), fps, width, height.",
        "function": tool_get_video_info,
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
            },
            "required": ["video_path"],
        },
    },
]

# Fast lookup by name
_TOOL_MAP: Dict[str, Dict] = {t["name"]: t for t in TOOLS}


# ---------------------------------------------------------------------------
# Dispatcher — call this from your agent loop
# ---------------------------------------------------------------------------

def dispatch_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a registered tool by name with the given arguments dict.

    Returns a result dict always containing at least ``{"success": bool}``.
    On error, also contains ``{"error": str}``.

    Example (inside an agent loop)::

        tool_call = llm_response.tool_calls[0]
        result = dispatch_tool(tool_call.name, tool_call.arguments)
    """
    tool = _TOOL_MAP.get(tool_name)
    if tool is None:
        available = list(_TOOL_MAP.keys())
        logger.error(f"Unknown tool '{tool_name}'. Available: {available}")
        return {"success": False, "error": f"Unknown tool '{tool_name}'", "available_tools": available}

    try:
        logger.info(f"🤖 Agent dispatching tool '{tool_name}' with args: {arguments}")
        result = tool["function"](**arguments)
        result["success"] = True
        logger.info(f"✅ Tool '{tool_name}' completed: {result}")
        return result
    except Exception as exc:
        logger.exception(f"❌ Tool '{tool_name}' failed: {exc}")
        return {"success": False, "error": str(exc), "tool": tool_name}


def get_openai_tool_schemas() -> List[Dict[str, Any]]:
    """
    Return tool schemas in OpenAI function-calling format.
    Pass this to ``client.chat.completions.create(tools=...)``
    """
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in TOOLS
    ]
