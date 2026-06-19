"""WE.ED.IT Core Module - Audio & Video Analysis Engine"""
__version__ = "2.0.0"
__author__ = "Dex / d4u5ab33t"

from .audio_analyzer import AudioAnalyzer, AudioFeatures
from .clip_pool import ClipPool, ClipMetadata
from .video_director import Director, TimelineSegment
from .beat_sync import BeatSyncEngine
from .db_manager import DatabaseManager

__all__ = [
    'AudioAnalyzer',
    'AudioFeatures',
    'ClipPool',
    'ClipMetadata',
    'Director',
    'TimelineSegment',
    'BeatSyncEngine',
    'DatabaseManager',
]
