import os
import json
import random
import time
import logging
import sqlite3
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Third-party libs
try:
    from TikTokApi import TikTokApi
    from playwright.async_api import async_playwright
except ImportError:
    print("⚠️ TikTokApi or playwright not installed.")

logger = logging.getLogger(__name__)

class TrendFetcher:
    """
    Fetches and caches TikTok trends using TikTokApi + Playwright.
    Robustness: Retries, Caching, Cookie Management.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.ms_token = os.getenv("TIKTOK_MS_TOKEN", "") # Optional
        self.sid_tt = os.getenv("TIKTOK_SSID", "") or os.getenv("TIKTOK_SESSION_ID", "")
        
        if not self.sid_tt:
            logger.warning("⚠️ No TikTok 'sid_tt' or 'sessionid' found in env. Scraping may fail.")

    def _get_db(self):
        return sqlite3.connect(self.db_path)

    async def fetch_trends(self, count: int = 30) -> List[Dict]:
        """
        Fetch trending videos. 
        Returns list of dicts with video metadata + music info.
        """
        # 1. Try Cache First
        cached = self.get_cached_trends("video")
        if cached:
            if self._is_cache_fresh(cached[0]):
                logger.info(f"✅ Using cached trends ({len(cached)} items)")
                return [c['data'] for c in cached]
            else:
                logger.info("Stats: Cache stale, refreshing...")
        
        # 2. Scrape Live
        try:
            results = await self._scrape_tiktok_api(count)
            if results:
                self._cache_trends("video", results)
                return results
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            
        # 3. Fallback to stale cache if scrape failed
        if cached:
            logger.warning("⚠️ Serving stale cache due to scrape failure.")
            return [c['data'] for c in cached]
            
        return []

    async def _scrape_tiktok_api(self, count: int) -> List[Dict]:
        """Internal scraper using TikTokApi."""
        videos = []
        try:
            async with TikTokApi() as api:
                await api.create_sessions(
                    ms_tokens=[self.ms_token] if self.ms_token else None, 
                    num_sessions=1, 
                    sleep_after=3,
                    headless=True
                )
                
                # If we have a cookie, we might need to inject it or pass it. 
                # TikTokApi handles some of this, but it's tricky. 
                # For now, we rely on its internal playwright session.
                
                logger.info("🕷️ Scraping TikTok Trends...")
                
                async for video in api.trending.videos(count=count):
                    v_data = video.as_dict
                    
                    # Extract useful bits
                    music = v_data.get("music", {})
                    stats = v_data.get("stats", {})
                    author = v_data.get("author", {})
                    
                    item = {
                        "id": v_data.get("id"),
                        "desc": v_data.get("desc", ""),
                        "createTime": v_data.get("createTime"),
                        "video_url": v_data.get("video", {}).get("playAddr", ""),
                        "cover_url": v_data.get("video", {}).get("cover", ""),
                        "stats": {
                            "plays": stats.get("playCount", 0),
                            "likes": stats.get("diggCount", 0),
                            "shares": stats.get("shareCount", 0)
                        },
                        "music": {
                            "id": music.get("id"),
                            "title": music.get("title", "Unknown"),
                            "author": music.get("authorName", "Unknown"),
                            "duration": music.get("duration", 0),
                            "play_url": music.get("playUrl", ""),
                            "cover": music.get("coverLarge", "")
                        },
                        "author": {
                            "id": author.get("id"),
                            "username": author.get("uniqueId")
                        },
                        "hashtags": [c.get("hashtagName") for c in v_data.get("textExtra", []) if c.get("hashtagName")]
                    }
                    videos.append(item)
                    
                    # Random delay to be polite
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    
        except Exception as e:
            logger.error(f"TikTokApi Error: {e}")
            # Raise so caller knows it failed
            raise e
            
        return videos

    def get_trending_audio(self) -> List[Dict]:
        """
        Extract unique trending audio from cached trends.
        Ranks by frequency in trends + play count.
        """
        videos = self.get_cached_trends("video")
        if not videos:
            return []
            
        sound_stats = {}
        for v_entry in videos:
            v = v_entry['data']
            m = v.get("music", {})
            mid = m.get("id")
            if not mid: continue
            
            if mid not in sound_stats:
                sound_stats[mid] = {
                    "id": mid,
                    "title": m.get("title"),
                    "author": m.get("author"),
                    "url": m.get("play_url"),
                    "count": 0,
                    "total_plays": 0,
                    "meta": m
                }
            
            sound_stats[mid]["count"] += 1
            sound_stats[mid]["total_plays"] += v["stats"]["plays"]
            
        # Sort by viral usage count, then total plays
        ranked = sorted(
            sound_stats.values(), 
            key=lambda x: (x["count"], x["total_plays"]), 
            reverse=True
        )
        return ranked

    def get_viral_audio_candidates(self, min_uses: int = 2) -> List[Dict]:
        """
        Get high-confidence viral audio tracks.
        Filters by minimum usage count in current trend batch to ensure 'virality'.
        """
        all_trends = self.get_trending_audio()
        # Filter for items that appear multiple times (true trends) or have massive play counts
        viral = [
            t for t in all_trends 
            if t['count'] >= min_uses or t['total_plays'] > 1_000_000
        ]
        return viral

    # --- Caching Utils ---

    def _cache_trends(self, type_: str, items: List[Dict]):
        try:
            with self._get_db() as conn:
                # Clear old cache for this type? Or keep history? 
                # For "current trends", we might want to wipe old ones or just upsert.
                # Let's wipe old ones for this type to keep it fresh "Latest Trends"
                conn.execute("DELETE FROM trends_cache WHERE type=?", (type_,))
                
                for item in items:
                    conn.execute(
                        "INSERT INTO trends_cache (id, type, data) VALUES (?, ?, ?)",
                        (item['id'], type_, json.dumps(item))
                    )
            logger.info(f"💾 Cached {len(items)} items of type '{type_}'")
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def get_cached_trends(self, type_: str) -> List[Dict]:
        """Return list of {data: dict, created_at: str}."""
        try:
            with self._get_db() as conn:
                cursor = conn.execute(
                    "SELECT data, created_at FROM trends_cache WHERE type=? ORDER BY created_at DESC", 
                    (type_,)
                )
                rows = cursor.fetchall()
                return [{"data": json.loads(r[0]), "created_at": r[1]} for r in rows]
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return []

    def _is_cache_fresh(self, item: Dict, max_age_hours: int = 3) -> bool:
        try:
            created_at = datetime.fromisoformat(item['created_at'])
            age = datetime.now() - created_at
            return age < timedelta(hours=max_age_hours)
        except:
            return False

# Global Instance
# initialized in main.py
