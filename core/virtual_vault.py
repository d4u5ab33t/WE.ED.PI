# -*- coding: utf-8 -*-
import sqlite3
import json
import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

DB_VERSION = 2


@dataclass
class VClip:
    """Video clip metadata and performance metrics."""
    path: str
    duration: float
    shot_scale: str = ""
    movement: str = ""
    vibe: str = ""
    use_count: int = 0
    positive_uses: int = 0
    negative_uses: int = 0
    last_used: Optional[str] = None


class VirtualVault:
    """Persistent database for clip metadata and learning."""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path('./cache/weedit_vault.db')
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema."""
        self._conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS meta(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        INSERT OR IGNORE INTO meta VALUES('db_version', '{DB_VERSION}');
        
        CREATE TABLE IF NOT EXISTS clips(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            duration REAL,
            shot_scale TEXT DEFAULT '',
            movement TEXT DEFAULT '',
            vibe TEXT DEFAULT '',
            use_count INTEGER DEFAULT 0,
            positive_uses INTEGER DEFAULT 0,
            negative_uses INTEGER DEFAULT 0,
            last_used TEXT
        );
        
        CREATE TABLE IF NOT EXISTS renders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mp3_path TEXT NOT NULL,
            output_path TEXT NOT NULL,
            bpm REAL,
            duration REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            finished_at TEXT
        );
        
        CREATE INDEX IF NOT EXISTS ix_clips_path ON clips(path);
        CREATE INDEX IF NOT EXISTS ix_renders_status ON renders(status);
        """)
        self._conn.commit()
    
    def register_clip(self, clip: VClip) -> int:
        """Register or update a clip."""
        row = asdict(clip)
        cols = ', '.join(row.keys())
        placeholders = ', '.join('?' * len(row))
        
        self._conn.execute(
            f"INSERT OR REPLACE INTO clips({cols}) VALUES({placeholders})",
            list(row.values())
        )
        self._conn.commit()
        
        return self._conn.execute(
            "SELECT id FROM clips WHERE path=?",
            (clip.path,)
        ).fetchone()['id']
    
    def get_clip(self, path: str) -> Optional[Dict]:
        """Get clip metadata."""
        r = self._conn.execute(
            "SELECT * FROM clips WHERE path=?",
            (path,)
        ).fetchone()
        return dict(r) if r else None
    
    def all_clips(self) -> List[Dict]:
        """Get all clips."""
        rows = self._conn.execute("SELECT * FROM clips").fetchall()
        return [dict(r) for r in rows]
    
    def update_use(self, path: str, positive: bool = True):
        """Update clip usage statistics."""
        ts = datetime.datetime.now().isoformat()
        col = 'positive_uses' if positive else 'negative_uses'
        self._conn.execute(
            f"UPDATE clips SET use_count=use_count+1, {col}={col}+1, last_used=? WHERE path=?",
            (ts, path)
        )
        self._conn.commit()
    
    def create_render(self, mp3_path: str, output_path: str, bpm: float, duration: float) -> int:
        """Create render record."""
        ts = datetime.datetime.now().isoformat()
        cur = self._conn.execute(
            "INSERT INTO renders(mp3_path, output_path, bpm, duration, created_at) VALUES(?, ?, ?, ?, ?)",
            (mp3_path, output_path, bpm, duration, ts)
        )
        self._conn.commit()
        return cur.lastrowid
    
    def set_render_status(self, render_id: int, status: str):
        """Update render status."""
        ts = datetime.datetime.now().isoformat() if status in ('done', 'failed') else None
        self._conn.execute(
            "UPDATE renders SET status=?, finished_at=? WHERE id=?",
            (status, ts, render_id)
        )
        self._conn.commit()
    
    def close(self):
        """Close database connection."""
        self._conn.close()
