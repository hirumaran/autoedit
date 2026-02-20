import json
import sqlite3
from pathlib import Path
from typing import Dict


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            video_id TEXT PRIMARY KEY,
            data TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS music_cache (
            track_id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            duration REAL,
            temperature REAL, -- Popularity/Trend score 0-100
            mood_tags TEXT,
            local_path TEXT,
            metadata TEXT, -- Full JSON metadata
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS trends_cache (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL, -- 'video' or 'audio'
            data TEXT NOT NULL, -- JSON data
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    return conn


def load_jobs(conn: sqlite3.Connection) -> Dict[str, Dict]:
    jobs: Dict[str, Dict] = {}
    try:
        for video_id, data in conn.execute("SELECT video_id, data FROM jobs"):
            try:
                jobs[video_id] = json.loads(data)
            except Exception:
                continue
    except Exception:
        pass
    return jobs


def save_job(conn: sqlite3.Connection, video_id: str, job: Dict):
    payload = json.dumps(job)
    conn.execute(
        "INSERT INTO jobs(video_id, data) VALUES(?, ?) ON CONFLICT(video_id) DO UPDATE SET data=excluded.data",
        (video_id, payload),
    )
    conn.commit()
