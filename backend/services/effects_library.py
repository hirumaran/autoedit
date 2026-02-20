"""
Effects Library - Manages visual effects, filters, and overlays.
Provides a catalog of built-in effects and integration with trending effects.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json
import cv2
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class Effect:
    """Represents a visual effect."""
    id: str
    name: str
    category: str  # 'filter', 'transition', 'overlay', 'text'
    description: str
    parameters: Dict  # Default parameters
    is_trending: bool = False
    virality_boost: int = 0  # Score boost when applied

# Built-in effects library
BUILTIN_EFFECTS: List[Effect] = [
    # Filters
    Effect("glitch", "Glitch", "filter", "RGB shift and noise for edgy feel", 
           {"intensity": 0.5, "noise": 0.3}, virality_boost=15),
    Effect("vignette", "Vignette", "filter", "Dark corners for cinematic look",
           {"strength": 0.4}, virality_boost=5),
    Effect("color_grade_warm", "Warm Tones", "filter", "Orange/yellow color grading",
           {"temperature": 30, "saturation": 1.2}, virality_boost=10),
    Effect("color_grade_cool", "Cool Tones", "filter", "Blue/teal color grading",
           {"temperature": -30, "saturation": 1.1}, virality_boost=10),
    Effect("high_contrast", "High Contrast", "filter", "Punchy, bold look",
           {"contrast": 1.4, "brightness": 1.05}, virality_boost=8),
    Effect("blur_bg", "Background Blur", "filter", "Soft background focus",
           {"blur_radius": 15}, virality_boost=12),
    
    # Transitions
    Effect("speed_ramp", "Speed Ramp", "transition", "Dramatic slow-mo to fast transition",
           {"slow_factor": 0.5, "fast_factor": 2.0, "duration": 1.0}, virality_boost=20),
    Effect("zoom_in", "Zoom In", "transition", "Quick zoom effect",
           {"scale": 1.3, "duration": 0.5}, virality_boost=12),
    Effect("flash", "Flash", "transition", "White flash between cuts",
           {"intensity": 1.0, "duration": 0.1}, virality_boost=8),
    Effect("shake", "Camera Shake", "transition", "Impact shake effect",
           {"intensity": 10, "duration": 0.3}, virality_boost=10),
    
    # Overlays
    Effect("text_pop", "Pop Text", "overlay", "Animated text that pops in",
           {"font_size": 48, "animation": "pop", "color": "#FFFFFF"}, virality_boost=15),
    Effect("text_typewriter", "Typewriter", "overlay", "Character-by-character reveal",
           {"font_size": 36, "speed": 0.05, "color": "#FFFFFF"}, virality_boost=12),
    Effect("emoji_burst", "Emoji Burst", "overlay", "Flying emoji particles",
           {"emoji": "🔥", "count": 10, "duration": 1.0}, virality_boost=18),
]


class EffectsLibrary:
    """Manages the catalog of visual effects."""
    
    def __init__(self, assets_dir: Path = None):
        self.assets_dir = assets_dir or Path(__file__).parent.parent.parent / "data" / "effects"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self._effects: Dict[str, Effect] = {e.id: e for e in BUILTIN_EFFECTS}
        self._trending_effects: List[Dict] = []
    
    def get_all_effects(self) -> List[Dict]:
        """Get all available effects as dicts."""
        return [asdict(e) for e in self._effects.values()]
    
    def get_effect(self, effect_id: str) -> Optional[Effect]:
        """Get a specific effect by ID."""
        return self._effects.get(effect_id)
    
    def get_by_category(self, category: str) -> List[Effect]:
        """Get effects filtered by category."""
        return [e for e in self._effects.values() if e.category == category]
    
    def get_trending(self) -> List[Effect]:
        """Get effects marked as trending."""
        return [e for e in self._effects.values() if e.is_trending]
    
    def add_trending_effect(self, effect_data: Dict):
        """Add a scraped trending effect to the library."""
        effect = Effect(
            id=effect_data.get('id', f"trend_{len(self._trending_effects)}"),
            name=effect_data.get('name', 'Unknown Effect'),
            category=effect_data.get('category', 'filter'),
            description=effect_data.get('description', ''),
            parameters=effect_data.get('parameters', {}),
            is_trending=True,
            virality_boost=effect_data.get('virality_boost', 20)
        )
        self._effects[effect.id] = effect
        self._trending_effects.append(effect_data)
        logger.info(f"✨ Added trending effect: {effect.name}")


class EffectProcessor:
    """Applies visual effects to video frames using OpenCV."""
    
    @staticmethod
    def apply_glitch(frame: np.ndarray, intensity: float = 0.5, noise: float = 0.3) -> np.ndarray:
        """Apply glitch effect with RGB shift and noise."""
        h, w = frame.shape[:2]
        shift = int(w * intensity * 0.02)
        
        # RGB channel shift
        result = frame.copy()
        result[:, shift:, 2] = frame[:, :-shift, 2]  # Red shift right
        result[:, :-shift, 0] = frame[:, shift:, 0]  # Blue shift left
        
        # Add noise
        if noise > 0:
            noise_overlay = np.random.randint(0, int(255 * noise), frame.shape, dtype=np.uint8)
            result = cv2.addWeighted(result, 1 - noise * 0.3, noise_overlay, noise * 0.3, 0)
        
        return result
    
    @staticmethod
    def apply_vignette(frame: np.ndarray, strength: float = 0.4) -> np.ndarray:
        """Apply vignette (dark corners) effect."""
        h, w = frame.shape[:2]
        
        # Create radial gradient
        x = np.linspace(-1, 1, w)
        y = np.linspace(-1, 1, h)
        X, Y = np.meshgrid(x, y)
        radius = np.sqrt(X**2 + Y**2)
        
        # Create vignette mask
        vignette = 1 - np.clip(radius * strength, 0, 1)
        vignette = np.dstack([vignette] * 3)
        
        return (frame * vignette).astype(np.uint8)
    
    @staticmethod
    def apply_color_grade(frame: np.ndarray, temperature: float = 0, saturation: float = 1.0) -> np.ndarray:
        """Apply color grading with temperature and saturation adjustments."""
        # Convert to HSV for saturation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        # Temperature adjustment (warm = +, cool = -)
        if temperature != 0:
            result = result.astype(np.float32)
            if temperature > 0:  # Warm
                result[:, :, 2] = np.clip(result[:, :, 2] + temperature, 0, 255)  # More red
                result[:, :, 0] = np.clip(result[:, :, 0] - temperature * 0.5, 0, 255)  # Less blue
            else:  # Cool
                result[:, :, 0] = np.clip(result[:, :, 0] - temperature, 0, 255)  # More blue
                result[:, :, 2] = np.clip(result[:, :, 2] + temperature * 0.5, 0, 255)  # Less red
            result = result.astype(np.uint8)
        
        return result
    
    @staticmethod
    def apply_high_contrast(frame: np.ndarray, contrast: float = 1.4, brightness: float = 1.05) -> np.ndarray:
        """Apply high contrast effect."""
        result = frame.astype(np.float32)
        result = result * contrast * brightness
        return np.clip(result, 0, 255).astype(np.uint8)
    
    @staticmethod
    def apply_shake(frame: np.ndarray, intensity: int = 10) -> np.ndarray:
        """Apply camera shake by translating the frame."""
        h, w = frame.shape[:2]
        dx = np.random.randint(-intensity, intensity)
        dy = np.random.randint(-intensity, intensity)
        
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(frame, M, (w, h))
    
    def apply_effect(self, frame: np.ndarray, effect: Effect) -> np.ndarray:
        """Apply an effect to a frame based on effect type."""
        params = effect.parameters
        
        if effect.id == "glitch":
            return self.apply_glitch(frame, params.get("intensity", 0.5), params.get("noise", 0.3))
        elif effect.id == "vignette":
            return self.apply_vignette(frame, params.get("strength", 0.4))
        elif effect.id in ["color_grade_warm", "color_grade_cool"]:
            return self.apply_color_grade(frame, params.get("temperature", 0), params.get("saturation", 1.0))
        elif effect.id == "high_contrast":
            return self.apply_high_contrast(frame, params.get("contrast", 1.4), params.get("brightness", 1.05))
        elif effect.id == "shake":
            return self.apply_shake(frame, params.get("intensity", 10))
        else:
            logger.warning(f"Unknown effect: {effect.id}, returning original frame")
            return frame


# Module-level instance
effects_library = EffectsLibrary()
effect_processor = EffectProcessor()
