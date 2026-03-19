"""
Video Editing AI Agent
=======================
An OpenAI-powered agent that accepts a plain-English editing instruction
and autonomously calls MoviePy engine tools to produce an edited video.

Usage::

    from backend.video_agent import VideoEditingAgent

    agent = VideoEditingAgent()
    result = agent.run(
        video_path="/tmp/clip.mp4",
        instruction="Trim the first 5 seconds, add warm color grade, then burn subtitles in bold style",
        subtitle_data=[{"text": "Hello world", "start": 0, "end": 2}],
    )
    print(result["output_path"])
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ openai package not installed. VideoEditingAgent will use rule-based fallback.")

from .agent_tools import TOOLS, dispatch_tool, get_openai_tool_schemas

_SYSTEM_PROMPT = """
You are an expert AI video editor. The user gives you a video file path and a plain-English editing instruction.
You have access to a set of video editing tools powered by MoviePy. Your job is to:

1. Analyse the instruction carefully.
2. Call the appropriate tools in the correct order (e.g. trim first, then add effects, then add music).
3. Always use the output_path from one tool as the video_path input for the next tool in the chain.
4. When finished, return ONLY a JSON object: {"final_output": "<absolute_path_to_final_video>", "steps": [...list of tool names called...]}

Available tools: trim_video, concatenate_segments, add_subtitles, apply_effect, mix_music, audio_fade, trim_audio, get_video_info.

Rules:
- Never fabricate file paths; always use output_path returned from the previous tool.
- If the instruction is ambiguous, pick the most sensible reasonable defaults.
- Keep the editing pipeline as short as possible (no redundant steps).
""".strip()


class VideoEditingAgent:
    """
    LLM-powered agent that translates natural-language editing instructions
    into sequential MoviePy tool calls.
    """

    def __init__(self, model: str = "gpt-4o-mini", max_iterations: int = 10):
        self.model = model
        self.max_iterations = max_iterations
        self._client: Optional["OpenAI"] = None

        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                self._client = OpenAI(api_key=api_key)
                logger.info(f"🤖 VideoEditingAgent ready (model={model})")
            else:
                logger.warning("⚠️ OPENAI_API_KEY not set — agent will use rule-based fallback")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        video_path: str,
        instruction: str,
        subtitle_data: Optional[List[Dict]] = None,
        audio_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an editing instruction against *video_path*.

        Returns::

            {
                "success": True,
                "final_output": "/tmp/agent_edits/abc123.mp4",
                "steps": ["trim_video", "apply_effect", "add_subtitles"],
                "tool_results": [...],
            }
        """
        extra_context = {
            "video_path": video_path,
            "subtitle_data": subtitle_data or [],
            "audio_path": audio_path or "",
            **(context or {}),
        }

        if self._client is not None:
            return self._llm_run(video_path, instruction, extra_context)
        else:
            return self._rule_based_run(video_path, instruction, subtitle_data, audio_path)

    # ------------------------------------------------------------------
    # LLM agent loop
    # ------------------------------------------------------------------

    def _llm_run(
        self, video_path: str, instruction: str, context: Dict
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Video file: {video_path}\n"
                    f"Extra context: {json.dumps(context, default=str)}\n\n"
                    f"Instruction: {instruction}"
                ),
            },
        ]

        tool_schemas = get_openai_tool_schemas()
        tool_results: List[Dict] = []
        steps: List[str] = []
        current_video = video_path

        for iteration in range(self.max_iterations):
            logger.info(f"🔄 Agent iteration {iteration + 1}/{self.max_iterations}")
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tool_schemas,
                tool_choice="auto",
            )

            choice = response.choices[0]

            # Agent finished — parse final answer
            if choice.finish_reason == "stop":
                content = choice.message.content or ""
                try:
                    # Try to parse JSON from the response
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end > start:
                        data = json.loads(content[start:end])
                        final_out = data.get("final_output", current_video)
                        return {
                            "success": True,
                            "final_output": final_out,
                            "steps": steps,
                            "tool_results": tool_results,
                        }
                except Exception:
                    pass
                return {
                    "success": True,
                    "final_output": current_video,
                    "steps": steps,
                    "tool_results": tool_results,
                }

            # Agent made tool calls
            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append(choice.message)

                for tc in choice.message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    # Always thread current_video through as video_path if not overridden
                    if "video_path" in [
                        p for t in TOOLS if t["name"] == tool_name
                        for p in t["parameters"].get("properties", {})
                    ] and "video_path" not in args:
                        args["video_path"] = current_video

                    result = dispatch_tool(tool_name, args)
                    tool_results.append({"tool": tool_name, "args": args, "result": result})
                    steps.append(tool_name)

                    if result.get("success") and result.get("output_path"):
                        current_video = result["output_path"]

                    # Feed result back to LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    })

        logger.warning("⚠️ Agent hit max iterations")
        return {
            "success": True,
            "final_output": current_video,
            "steps": steps,
            "tool_results": tool_results,
            "warning": "max_iterations_reached",
        }

    # ------------------------------------------------------------------
    # Rule-based fallback (no LLM key)
    # ------------------------------------------------------------------

    def _rule_based_run(
        self,
        video_path: str,
        instruction: str,
        subtitle_data: Optional[List[Dict]],
        audio_path: Optional[str],
    ) -> Dict[str, Any]:
        """
        Simple keyword-based pipeline when no LLM is available.
        Covers the most common editing patterns deterministically.
        """
        logger.info("🔧 Rule-based agent fallback active")
        instr = instruction.lower()
        current = video_path
        steps: List[str] = []
        tool_results: List[Dict] = []

        def _run(name, **kwargs):
            nonlocal current
            r = dispatch_tool(name, {"video_path": current, **kwargs})
            tool_results.append({"tool": name, "result": r})
            steps.append(name)
            if r.get("output_path"):
                current = r["output_path"]
            return r

        # Trim keywords
        if "trim" in instr or "cut" in instr or "shorten" in instr:
            _run("trim_video", start=0.0, end=30.0)

        # Effect keywords
        if "warm" in instr or "golden" in instr:
            _run("apply_effect", effect_id="color_grade_warm", params={"temperature": 40})
        if "cool" in instr or "cold" in instr or "blue" in instr:
            _run("apply_effect", effect_id="color_grade_cool", params={"temperature": 30})
        if "contrast" in instr or "dramatic" in instr:
            _run("apply_effect", effect_id="high_contrast", params={"contrast": 1.5})
        if "speed" in instr or "fast" in instr:
            _run("apply_effect", effect_id="speed_ramp", params={"fast_factor": 1.5})
        if "zoom" in instr:
            _run("apply_effect", effect_id="zoom_in", params={"scale": 1.2})
        if "mirror" in instr or "flip" in instr:
            _run("apply_effect", effect_id="mirror")
        if "flash" in instr:
            _run("apply_effect", effect_id="flash", params={"duration": 0.15})

        # Subtitles
        if subtitle_data and ("subtitle" in instr or "caption" in instr or "text" in instr):
            style = "bold" if "bold" in instr else "meme" if "meme" in instr else "sleek"
            _run("add_subtitles", subtitle_data=subtitle_data, style_preset=style)

        # Music
        if audio_path and ("music" in instr or "audio" in instr or "sound" in instr):
            _run("mix_music", audio_path=audio_path, bg_volume=0.3)

        return {
            "success": True,
            "final_output": current,
            "steps": steps,
            "tool_results": tool_results,
        }
