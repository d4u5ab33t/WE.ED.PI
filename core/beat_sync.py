# -*- coding: utf-8 -*-
"""
BeatSync Engine - Extract beats and sync to video timeline
"""

import json
import librosa
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime


@dataclass
class BeatInfo:
    """Beat information"""
    timestamp: float
    confidence: float
    strength: float


@dataclass
class TimelineMarker:
    """Timeline marker for editing decisions"""
    time: float
    marker_type: str  # beat, drop, build, stab, silence, transient
    confidence: float
    metadata: Dict


class BeatSyncEngine:
    """Main beat synchronization engine"""
    
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sr = sr
        self.hop_length = hop_length
    
    def extract_beats(self, audio_path: str) -> List[BeatInfo]:
        """Extract beat timestamps from audio"""
        y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        
        # Beat tracking
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # Onset detection for confidence
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units='frames')
        
        # Create beat info with confidence scores
        beats = []
        for beat_time in beat_times:
            frame = librosa.time_to_frames(beat_time, sr=sr, hop_length=self.hop_length)
            
            # Confidence based on proximity to onsets
            confidence = self._compute_confidence(frame, onset_frames)
            strength = self._compute_strength(y, beat_time, sr)
            
            beats.append(BeatInfo(
                timestamp=float(beat_time),
                confidence=float(confidence),
                strength=float(strength)
            ))
        
        return beats
    
    def detect_markers(self, audio_path: str) -> List[TimelineMarker]:
        """Detect important timeline markers (drops, builds, transients, etc.)"""
        y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        
        markers = []
        
        # Detect onsets (transients)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env, sr=sr, backtrack=True, units='frames'
        )
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        for onset_time in onset_times:
            markers.append(TimelineMarker(
                time=float(onset_time),
                marker_type='transient',
                confidence=0.7,
                metadata={'strength': 1.0}
            ))
        
        # Detect energy changes (drops/builds)
        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=self.hop_length)
        
        # Find significant energy drops
        rms_delta = np.diff(rms, prepend=rms[0])
        drop_threshold = np.percentile(rms_delta, 10)
        build_threshold = np.percentile(rms_delta, 90)
        
        for i, delta in enumerate(rms_delta):
            if delta < drop_threshold:
                markers.append(TimelineMarker(
                    time=float(rms_times[i]),
                    marker_type='drop',
                    confidence=abs(delta / drop_threshold),
                    metadata={'drop_strength': float(abs(delta))}
                ))
            elif delta > build_threshold:
                markers.append(TimelineMarker(
                    time=float(rms_times[i]),
                    marker_type='build',
                    confidence=abs(delta / build_threshold),
                    metadata={'build_strength': float(delta)}
                ))
        
        # Detect silences
        silence_threshold = np.mean(rms) * 0.1
        for i, energy in enumerate(rms):
            if energy < silence_threshold:
                markers.append(TimelineMarker(
                    time=float(rms_times[i]),
                    marker_type='silence',
                    confidence=0.5,
                    metadata={'energy': float(energy)}
                ))
        
        # Sort by time
        markers.sort(key=lambda m: m.time)
        return markers
    
    def save_beats_json(self, beats: List[BeatInfo], output_path: str):
        """Save beats to JSON file"""
        data = {
            'version': '2.0',
            'timestamp': datetime.now().isoformat(),
            'beats': [
                {
                    'time': beat.timestamp,
                    'confidence': beat.confidence,
                    'strength': beat.strength
                }
                for beat in beats
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _compute_confidence(self, beat_frame: int, onset_frames: np.ndarray) -> float:
        """Compute confidence score based on proximity to onsets"""
        if len(onset_frames) == 0:
            return 0.5
        
        distances = np.abs(onset_frames - beat_frame)
        min_distance = np.min(distances)
        
        # Confidence decreases with distance
        confidence = max(0.0, 1.0 - (min_distance / 100.0))
        return confidence
    
    def _compute_strength(self, y: np.ndarray, time: float, sr: int) -> float:
        """Compute beat strength based on local energy"""
        frame = librosa.time_to_frames(time, sr=sr, hop_length=self.hop_length)
        window = 10  # frames
        
        start = max(0, frame - window)
        end = min(len(y), frame + window)
        
        if start >= end:
            return 0.5
        
        # RMS energy in local window
        local_rms = np.sqrt(np.mean(y[start:end] ** 2))
        strength = min(1.0, local_rms * 2.0)
        
        return strength
