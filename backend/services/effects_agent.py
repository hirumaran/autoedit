"""
Effects Agent - AI-driven effect suggestions based on video content and trends.
Uses semantic matching to recommend effects that boost virality.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import asdict

from .effects_library import effects_library, Effect

logger = logging.getLogger(__name__)

SEMANTIC_AVAILABLE = False


class EffectsAgent:
    """AI agent that suggests visual effects based on video content."""
    
    def __init__(self):
        self.model = None
        if SEMANTIC_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("🤖 EffectsAgent initialized with semantic model")
            except Exception as e:
                logger.warning(f"Could not load semantic model: {e}")
    
    def suggest_effects(
        self,
        transcript: str = "",
        mood: str = "",
        video_duration: float = 0,
        ai_analysis: Dict = None,
        max_suggestions: int = 5
    ) -> List[Dict]:
        """
        Suggest effects based on video content and mood.
        
        Args:
            transcript: Video transcript text
            mood: Detected or user-specified mood (e.g., "energetic", "calm")
            video_duration: Length of video in seconds
            ai_analysis: AI analysis results (scene types, objects, etc.)
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of effect suggestions with scores and reasoning
        """
        suggestions = []
        all_effects = effects_library.get_all_effects()
        
        # Build context string
        context = self._build_context(transcript, mood, ai_analysis)
        
        if self.model and context:
            # Semantic matching
            suggestions = self._semantic_match(context, all_effects, max_suggestions)
        else:
            # Keyword fallback
            suggestions = self._keyword_match(context, all_effects, max_suggestions)
        
        # Adjust based on video duration
        suggestions = self._adjust_for_duration(suggestions, video_duration)
        
        # Cap effects for short videos
        if video_duration < 15:
            suggestions = suggestions[:2]  # Max 2 effects for short clips
        elif video_duration < 30:
            suggestions = suggestions[:3]
        
        logger.info(f"✨ Suggested {len(suggestions)} effects for video")
        return suggestions
    
    def _build_context(self, transcript: str, mood: str, ai_analysis: Dict) -> str:
        """Build a context string from all available information."""
        parts = []
        
        if transcript:
            parts.append(transcript[:500])  # Limit length
        
        if mood:
            parts.append(f"mood: {mood}")
        
        if ai_analysis:
            if "summary" in ai_analysis:
                parts.append(ai_analysis["summary"][:200])
            if "detected_scenes" in ai_analysis:
                parts.append(f"scenes: {', '.join(ai_analysis['detected_scenes'][:5])}")
        
        return " ".join(parts)
    
    def _semantic_match(self, context: str, effects: List[Dict], limit: int) -> List[Dict]:
        """Use semantic similarity to match effects to context."""
        if not self.model:
            return self._keyword_match(context, effects, limit)
        
        # Create embeddings
        effect_texts = [f"{e['name']} {e['description']}" for e in effects]
        context_embedding = self.model.encode(context, convert_to_tensor=True)
        effect_embeddings = self.model.encode(effect_texts, convert_to_tensor=True)
        
        # Calculate similarities
        similarities = util.cos_sim(context_embedding, effect_embeddings)[0]
        
        # Rank and return top matches
        ranked = []
        for i, score in enumerate(similarities):
            effect = effects[i]
            total_score = float(score) * 100 + effect.get('virality_boost', 0)
            ranked.append({
                **effect,
                "match_score": round(float(score) * 100, 1),
                "total_score": round(total_score, 1),
                "reason": self._generate_reason(effect, context)
            })
        
        ranked.sort(key=lambda x: x["total_score"], reverse=True)
        return ranked[:limit]
    
    def _keyword_match(self, context: str, effects: List[Dict], limit: int) -> List[Dict]:
        """Simple keyword-based matching fallback."""
        context_lower = context.lower()
        
        # Keyword associations
        keyword_map = {
            "glitch": ["edgy", "tech", "futuristic", "intense", "gaming"],
            "color_grade_warm": ["happy", "sunny", "warm", "friendly", "cozy"],
            "color_grade_cool": ["calm", "professional", "night", "mysterious"],
            "speed_ramp": ["action", "dramatic", "sports", "dance", "fast"],
            "vignette": ["cinematic", "dramatic", "focus", "artistic"],
            "text_pop": ["funny", "reaction", "highlight", "emphasis"],
            "emoji_burst": ["celebration", "excited", "happy", "party", "fun"],
            "shake": ["impact", "action", "dramatic", "intense"],
            "high_contrast": ["bold", "punchy", "vibrant", "stand out"],
        }
        
        ranked = []
        for effect in effects:
            score = effect.get('virality_boost', 0)
            keywords = keyword_map.get(effect['id'], [])
            
            # Check keyword matches
            matches = sum(1 for kw in keywords if kw in context_lower)
            score += matches * 15
            
            ranked.append({
                **effect,
                "match_score": matches * 15,
                "total_score": score,
                "reason": f"Matches your content style" if matches > 0 else "Popular effect"
            })
        
        ranked.sort(key=lambda x: x["total_score"], reverse=True)
        return ranked[:limit]
    
    def _adjust_for_duration(self, suggestions: List[Dict], duration: float) -> List[Dict]:
        """Adjust suggestions based on video duration."""
        if duration <= 0:
            return suggestions
        
        adjusted = []
        for s in suggestions:
            # Avoid complex transitions in very short videos
            if duration < 10 and s.get('category') == 'transition':
                s['total_score'] *= 0.5
                s['reason'] = f"{s.get('reason', '')} (may be too complex for short video)"
            adjusted.append(s)
        
        adjusted.sort(key=lambda x: x["total_score"], reverse=True)
        return adjusted
    
    def _generate_reason(self, effect: Dict, context: str) -> str:
        """Generate a human-readable reason for the suggestion."""
        name = effect.get('name', 'Effect')
        category = effect.get('category', 'effect')
        
        reasons = {
            "filter": f"{name} enhances the visual mood of your content",
            "transition": f"{name} adds dynamic energy between scenes",
            "overlay": f"{name} emphasizes key moments in your video",
            "text": f"{name} helps convey your message effectively"
        }
        
        return reasons.get(category, f"{name} boosts engagement")
    
    def get_suggested_timestamps(
        self,
        effect_id: str,
        video_duration: float,
        beat_times: List[float] = None
    ) -> List[Dict]:
        """
        Suggest optimal timestamps to apply an effect.
        
        Args:
            effect_id: The effect to apply
            video_duration: Total video duration
            beat_times: Audio beat timestamps (from librosa)
            
        Returns:
            List of {start, end, reason} dicts
        """
        effect = effects_library.get_effect(effect_id)
        if not effect:
            return []
        
        timestamps = []
        
        if effect.category == "transition":
            # Apply at beat drops or evenly spaced
            if beat_times and len(beat_times) > 4:
                # Pick strong beats (every 4th beat for emphasis)
                for i in range(4, len(beat_times), 8):
                    timestamps.append({
                        "start": beat_times[i],
                        "end": beat_times[i] + effect.parameters.get("duration", 0.5),
                        "reason": "Synced to beat"
                    })
            else:
                # Default: apply at 25% and 75% of video
                timestamps.extend([
                    {"start": video_duration * 0.25, "end": video_duration * 0.25 + 0.5, "reason": "Early hook"},
                    {"start": video_duration * 0.75, "end": video_duration * 0.75 + 0.5, "reason": "Climax moment"}
                ])
        
        elif effect.category == "filter":
            # Filters often apply to entire video or specific sections
            timestamps.append({
                "start": 0,
                "end": video_duration,
                "reason": "Applied to full video"
            })
        
        elif effect.category == "overlay":
            # Overlays at key moments
            if video_duration > 5:
                timestamps.append({
                    "start": video_duration * 0.1,
                    "end": video_duration * 0.3,
                    "reason": "Opening emphasis"
                })
        
        return timestamps[:5]  # Max 5 timestamps per effect


# Module-level instance
effects_agent = EffectsAgent()
