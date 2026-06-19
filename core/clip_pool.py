# -*- coding: utf-8 -*-
"""
Clip Pool Manager - Video Clip Library with Semantic Search
Supports Pi-optimized analysis with caching
"""

import os
import cv2
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from collections import deque

PI_MODE = os.getenv("PI_MODE", "0") == "1"
VECTOR_DIM = 9  # Same as AudioFeatures mood_vector


@dataclass
class ClipMetadata:
    """Video clip metadata"""
    path: str
    duration: float
    width: int = 0
    height: int = 0
    fps: float = 24.0
    shot_type: str = "medium"  # wide, medium, close, extreme_close
    movement: str = "static"   # static, pan, zoom, dolly, handheld
    lighting: str = "neutral"  # bright, dark, warm, cool, contrasty
    dominant_colors: List[Tuple[int, int, int]] = field(default_factory=list)
    motion_score: float = 0.5  # 0.0-1.0
    brightness: float = 127.0  # 0-255
    saturation: float = 0.5    # 0.0-1.0
    vector: np.ndarray = field(default_factory=lambda: np.zeros(VECTOR_DIM, dtype=np.float32))
    use_count: int = 0
    rating: float = 0.5  # 0.0-1.0
    tags: List[str] = field(default_factory=list)


class ClipPool:
    """Clip library manager with semantic search"""
    
    def __init__(self, pool_dirs: List[str], db_path: Optional[str] = None, cache_path: Optional[str] = None):
        self.pool_dirs = [Path(d) for d in pool_dirs]
        self.db_path = Path(db_path) if db_path else None
        self.cache_path = Path(cache_path) if cache_path else None
        
        self.clips: List[ClipMetadata] = []
        self._recently_used: deque = deque(maxlen=50)
        self.db_cache: Dict[str, dict] = {}
        
        if self.db_path and self.db_path.exists():
            self._load_database()
        
        self._scan_pool()
    
    def _load_database(self):
        """Load clip metadata from database"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            raw_items = data if isinstance(data, list) else list(data.values())
            for entry in raw_items:
                path = entry.get('path', '')
                if path:
                    norm_key = str(Path(path).resolve())
                    self.db_cache[norm_key] = entry
            
            print(f"✅ Loaded {len(raw_items)} clips from database")
        except Exception as e:
            print(f"⚠️  Database load error: {e}")
    
    def _scan_pool(self):
        """Scan pool directories for video files"""
        EXTS = {'.mp4', '.mkv', '.webm', '.mov', '.avi'}
        
        for pool_dir in self.pool_dirs:
            if not pool_dir.exists():
                continue
            
            for p in pool_dir.rglob('*'):
                if p.suffix.lower() in EXTS:
                    self._load_and_analyze(p)
        
        print(f"✅ Indexed {len(self.clips)} clips")
    
    def _load_and_analyze(self, path: Path):
        """Load and analyze a video clip"""
        try:
            resolved = path.resolve()
            
            # Try cache first
            resolved_key = str(resolved)
            if resolved_key in self.db_cache:
                entry = self.db_cache[resolved_key]
                vec = np.array(entry.get('vector', [0.0] * VECTOR_DIM), dtype=np.float32)
                meta = ClipMetadata(
                    path=str(resolved),
                    duration=entry.get('duration', 0.0),
                    width=entry.get('width', 0),
                    height=entry.get('height', 0),
                    fps=entry.get('fps', 24.0),
                    shot_type=entry.get('shot_type', 'medium'),
                    motion_score=entry.get('motion_score', 0.5),
                    brightness=entry.get('brightness', 127.0),
                    vector=vec,
                    tags=entry.get('tags', [])
                )
                self.clips.append(meta)
                return
            
            if PI_MODE:
                # On Pi, skip analysis for uncached clips
                return
            
            # Full OpenCV analysis
            cap = cv2.VideoCapture(str(resolved))
            if not cap.isOpened():
                return
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            n_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = n_frames / fps if fps > 0 else 0.0
            
            # Sample frames for analysis
            brightness_vals = []
            motion_vals = []
            prev_gray = None
            sample_rate = max(1, int(fps // 2))
            
            for i in range(0, int(n_frames), sample_rate):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if not ret:
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness_vals.append(float(np.mean(gray)))
                
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    motion_vals.append(float(np.mean(diff)))
                
                prev_gray = gray
            
            cap.release()
            
            brightness = np.mean(brightness_vals) if brightness_vals else 127.0
            motion = np.mean(motion_vals) if motion_vals else 0.0
            motion_01 = min(motion / 50.0, 1.0)
            
            # Create vector (simplified)
            vec = np.zeros(VECTOR_DIM, dtype=np.float32)
            vec[0] = motion_01  # energy
            vec[1] = brightness / 255.0  # brightness
            vec[2] = 0.5  # placeholder
            
            meta = ClipMetadata(
                path=str(resolved),
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                brightness=brightness,
                motion_score=motion_01,
                vector=vec
            )
            self.clips.append(meta)
        
        except Exception as e:
            print(f"⚠️  Error analyzing {path.name}: {e}")
    
    def select_best_clip(
        self,
        min_duration: float,
        query_vector: np.ndarray,
        avoid_reuse: bool = True,
        cooldown: int = 5
    ) -> Optional[ClipMetadata]:
        """Select best clip based on query vector (semantic search)"""
        cooldown = min(cooldown, max(1, len(self.clips) // 2))
        recent_set = set(list(self._recently_used)[-cooldown:])
        
        candidates = [
            c for c in self.clips
            if c.duration >= min_duration
            and (not avoid_reuse or c.path not in recent_set)
        ]
        
        if not candidates:
            candidates = [c for c in self.clips if c.duration >= min_duration]
        if not candidates:
            return None
        
        # Compute similarities
        scores = np.array([
            self._cosine_similarity(query_vector, c.vector)
            for c in candidates
        ], dtype=np.float32)
        
        chosen = candidates[int(np.argmax(scores))]
        self._recently_used.append(chosen.path)
        chosen.use_count += 1
        
        return chosen
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between vectors"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def save_database(self):
        """Save clip metadata to database"""
        if not self.db_path:
            return
        
        try:
            data = [
                {
                    **asdict(clip),
                    'vector': clip.vector.tolist()
                }
                for clip in self.clips
            ]
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved {len(self.clips)} clips to database")
        except Exception as e:
            print(f"⚠️  Database save error: {e}")
