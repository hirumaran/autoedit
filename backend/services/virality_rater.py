import os
import logging
import random
from typing import Dict, List, Any
from .trend_fetcher import TrendFetcher

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False
    print("⚠️ sentence-transformers not available. Virality scoring will be heuristic.")

logger = logging.getLogger(__name__)

class ViralityRater:
    """
    Rates video viral potential compared to current TikTok trends.
    Uses semantic similarity on text (transcript vs trending hashtags/desc).
    """

    def __init__(self, trend_fetcher: TrendFetcher):
        self.trend_fetcher = trend_fetcher
        self.model = None
        self._load_model()

    def _load_model(self):
        if TRANSFORMER_AVAILABLE:
            try:
                print("⏳ Loading Virality Model (this may take a moment)...")
                # Use a small, fast model
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Virality Model loaded.")
            except Exception as e:
                logger.error(f"⚠️ Failed to load virality model (network issue?): {e}")
                print("⚠️ Virality Rater running in HEURISTIC mode (no AI model).")
                
    def rate_content(self, transcript: str, prompt: str, visual_score: int) -> Dict[str, Any]:
        """
        Calculate virality score (0-100).
        Combined of:
        - 40% Trend Relevance (text similarity)
        - 30% Visual Engagement (from Phase 1 analysis)
        - 30% Topic Freshness (hashtag match)
        """
        trends = self.trend_fetcher.get_cached_trends("video")
        
        # If no trends or model, return generic good score
        if not trends:
            return {
                "score": 75, 
                "reason": "Trends data unavailable. Score based on general best practices.",
                "suggestions": ["Use high-energy music", "Add captions"]
            }

        # extracting text from trends
        trend_texts = []
        trend_tags = set()
        for t in trends:
            data = t['data']
            text = f"{data.get('desc', '')} {' '.join(data.get('hashtags', []))}"
            trend_texts.append(text)
            for tag in data.get('hashtags', []):
                trend_tags.add(tag.lower())

        # 1. Trend Relevance Score (Text embedding similarity)
        relevance_score = 50 # Default
        if self.model and (transcript or prompt):
            user_text = f"{prompt} {transcript}"
            try:
                # Encode
                user_emb = self.model.encode([user_text])
                trend_embs = self.model.encode(trend_texts)
                
                # Compare
                similarities = cosine_similarity(user_emb, trend_embs)[0]
                # Take top 5 matches average
                top_matches = sorted(similarities, reverse=True)[:5]
                avg_sim = sum(top_matches) / len(top_matches)
                # Scale cosine (-1 to 1) to 0-100 roughly
                relevance_score = max(0, min(100, int(avg_sim * 100 * 1.5))) # Boost score
            except Exception as e:
                logger.error(f"Scoring error: {e}")

        # 2. Topic/Freshness (Heuristic tag match)
        freshness_score = 40
        user_words = set((transcript + " " + prompt).lower().split())
        match_count = sum(1 for tag in trend_tags if tag in user_words)
        if match_count > 0:
            freshness_score += min(60, match_count * 10)

        # 3. Visual Score (passed from Phase 1)
        # Scale 1-10 to 0-100
        visual_component = visual_score * 10

        # Weighted Total
        final_score = int(
            (relevance_score * 0.4) +
            (freshness_score * 0.3) + 
            (visual_component * 0.3)
        )
        
        # Generate Suggestions
        suggestions = []
        if relevance_score < 50:
            suggestions.append("Topic doesn't match top current trends heavily. Consider connecting to trending hashtags.")
        if visual_score < 6:
            suggestions.append("Visuals seem static. Use more cuts or motion.")
        if not suggestions:
            suggestions.append("Content looks very relevant to current trends!")
            
        # Top trending hashtags to use
        top_tags = list(trend_tags)[:5]
            
        return {
            "score": final_score,
            "relevance": relevance_score,
            "freshness": freshness_score,
            "trending_hashtags": top_tags,
            "suggestions": suggestions,
            "top_trend_matches": [t['data']['desc'][:50] for t in trends[:3]]
        }
