# -*- coding: utf-8 -*-
"""
Database Manager - SQLite + JSON caching
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


class DatabaseManager:
    """Manage project database (SQLite)"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Renders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS renders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mp3_path TEXT NOT NULL,
                output_path TEXT,
                status TEXT DEFAULT 'planned',
                created_at TEXT,
                finished_at TEXT,
                duration REAL,
                frames INTEGER,
                fps REAL DEFAULT 24.0,
                notes TEXT
            )
        ''')
        
        # Timeline segments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                render_id INTEGER REFERENCES renders(id),
                position INTEGER,
                clip_path TEXT,
                start_time REAL,
                end_time REAL,
                cut_style TEXT,
                transition TEXT,
                audio_marker TEXT,
                metadata TEXT
            )
        ''')
        
        # Clips
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                duration REAL,
                width INTEGER,
                height INTEGER,
                fps REAL,
                use_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.5,
                tags TEXT,
                metadata TEXT,
                created_at TEXT
            )
        ''')
        
        # Beat data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS beat_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                render_id INTEGER REFERENCES renders(id),
                timestamp REAL,
                confidence REAL,
                strength REAL
            )
        ''')
        
        self.conn.commit()
    
    def add_render(self, mp3_path: str, output_path: str, duration: float) -> int:
        """Add render job"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO renders (mp3_path, output_path, status, created_at, duration)
            VALUES (?, ?, 'planned', ?, ?)
        ''', (mp3_path, output_path, datetime.now().isoformat(), duration))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_render_status(self, render_id: int, status: str):
        """Update render status"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE renders SET status = ?, finished_at = ? WHERE id = ?
        ''', (status, datetime.now().isoformat() if status == 'done' else None, render_id))
        self.conn.commit()
    
    def add_timeline_segments(self, render_id: int, segments: List[Dict]):
        """Add timeline segments"""
        cursor = self.conn.cursor()
        
        for i, seg in enumerate(segments):
            cursor.execute('''
                INSERT INTO timeline 
                (render_id, position, clip_path, start_time, end_time, cut_style, transition, audio_marker, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                render_id,
                i,
                seg['clip_path'],
                seg['start_time'],
                seg['end_time'],
                seg.get('cut_style', 'flow'),
                seg.get('transition', 'cut'),
                seg.get('audio_marker'),
                json.dumps(seg.get('metadata', {}))
            ))
        
        self.conn.commit()
    
    def add_beats(self, render_id: int, beats: List[Dict]):
        """Add beat data"""
        cursor = self.conn.cursor()
        
        for beat in beats:
            cursor.execute('''
                INSERT INTO beat_data (render_id, timestamp, confidence, strength)
                VALUES (?, ?, ?, ?)
            ''', (render_id, beat['timestamp'], beat['confidence'], beat['strength']))
        
        self.conn.commit()
    
    def get_render(self, render_id: int) -> Optional[Dict]:
        """Get render info"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM renders WHERE id = ?', (render_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_renders(self) -> List[Dict]:
        """Get all renders"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM renders ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
