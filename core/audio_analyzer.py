# -*- coding: utf-8 -*-
"""
Audio Analyzer Module - Beat & Feature Detection
Uses librosa for audio analysis, optimized for Raspberry Pi
"""

import librosa
import numpy as np
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import os

PI_MODE = os.getenv("PI_MODE", "0") == "1"


@dataclass
class AudioFeatures:
    """Audio feature analysis result"""
    file_path: str
    duration: float
    tempo: float
    beats: List[float]
    beat_frames: np.ndarray
    onset_env: np.ndarray
    rms_energy: np.ndarray
    spectral_centroid: np.ndarray
    mfcc: np.ndarray
    chroma: np.ndarray
    sections: List[Dict]
    key: str
    genre_tags: List[str]
    mood_vector: np.ndarray


class AudioAnalyzer:
    """Main audio analysis engine"""
    
    def __init__(self, sr: int = 22050, n_fft: int = 2048, hop_length: int = 512):
        self.sr = sr
        self.n_fft = n_fft
        self.hop_length = hop_length
        
    def analyze(self, audio_path: str) -> AudioFeatures:
        """Comprehensive audio analysis"""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Load audio
        y, sr = librosa.load(str(audio_path), sr=self.sr, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Beat tracking
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
        beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        
        # Onset detection
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Energy features
        rms = librosa.feature.rms(y=y, frame_length=self.n_fft, hop_length=self.hop_length)[0]
        
        # Spectral features
        spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)[0]
        
        # MFCC (Mel-frequency cepstral coefficients)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=self.hop_length)
        
        # Chroma features
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=self.hop_length)
        
        # Structural analysis
        sections = self._segment_audio(y, sr, beat_frames)
        
        # Key detection (simplified)
        key = self._detect_key(chroma)
        
        # Genre tags
        genre_tags = self._classify_genre(tempo, spec_cent, rms)
        
        # Mood vector
        mood_vector = self._compute_mood_vector(rms, spec_cent, tempo)
        
        return AudioFeatures(
            file_path=str(audio_path),
            duration=duration,
            tempo=float(tempo),
            beats=beats,
            beat_frames=beat_frames,
            onset_env=onset_env,
            rms_energy=rms,
            spectral_centroid=spec_cent,
            mfcc=mfcc,
            chroma=chroma,
            sections=sections,
            key=key,
            genre_tags=genre_tags,
            mood_vector=mood_vector
        )
    
    def _segment_audio(self, y: np.ndarray, sr: int, beat_frames: np.ndarray) -> List[Dict]:
        """Segment audio into structural parts (intro, verse, chorus, etc.)"""
        sections = []
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Simple segmentation based on duration
        section_names = ['intro', 'verse', 'chorus', 'verse', 'chorus', 'bridge', 'chorus', 'outro']
        num_sections = min(8, max(2, len(beat_frames) // 8))
        
        for i in range(num_sections):
            start_time = (duration / num_sections) * i
            end_time = (duration / num_sections) * (i + 1)
            
            sections.append({
                'name': section_names[i % len(section_names)],
                'start': start_time,
                'end': end_time,
                'duration': end_time - start_time,
                'beats': [t for t in beat_times if start_time <= t < end_time]
            })
        
        return sections
    
    def _detect_key(self, chroma: np.ndarray) -> str:
        """Detect musical key from chroma features"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        chroma_mean = np.mean(chroma, axis=1)
        key_idx = np.argmax(chroma_mean)
        return notes[key_idx]
    
    def _classify_genre(self, tempo: float, spectral_cent: np.ndarray, rms: np.ndarray) -> List[str]:
        """Classify genre based on features"""
        tags = []
        
        # Tempo-based
        if tempo < 90:
            tags.append('slow')
        elif tempo < 120:
            tags.append('moderate')
        elif tempo < 140:
            tags.append('fast')
        else:
            tags.append('very_fast')
        
        # Energy-based
        if np.mean(rms) > 0.7:
            tags.append('high_energy')
        elif np.mean(rms) < 0.3:
            tags.append('low_energy')
        else:
            tags.append('medium_energy')
        
        # Spectral-based
        sc_mean = np.mean(spectral_cent)
        if sc_mean > 4000:
            tags.append('bright')
        elif sc_mean < 2000:
            tags.append('dark')
        else:
            tags.append('balanced')
        
        return tags
    
    def _compute_mood_vector(self, rms: np.ndarray, spectral_cent: np.ndarray, tempo: float) -> np.ndarray:
        """Compute mood vector (9D: energy, brightness, tempo, dynamic, warmth, aggression, melancholy, complexity, genre_affinity)"""
        vector = np.zeros(9, dtype=np.float32)
        
        vector[0] = np.mean(rms)  # energy
        vector[1] = np.mean(spectral_cent) / 11025.0  # brightness (normalized)
        vector[2] = min(tempo / 200.0, 1.0)  # tempo
        vector[3] = np.std(rms) / (np.mean(rms) + 1e-8)  # dynamic range
        vector[4] = 1.0 - (np.mean(spectral_cent) / 11025.0)  # warmth (inverse brightness)
        vector[5] = max(0, vector[0] - 0.5) * 2  # aggression
        vector[6] = 1.0 - vector[0]  # melancholy
        vector[7] = np.std(spectral_cent) / (np.mean(spectral_cent) + 1e-8) * 0.5  # complexity
        vector[8] = 0.5  # genre_affinity (placeholder)
        
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
