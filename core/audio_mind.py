# -*- coding: utf-8 -*-
import librosa
import numpy as np
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime

try:
    from mutagen.id3 import ID3
    from mutagen.mp3 import MP3
except ImportError:
    ID3 = None
    MP3 = None


@dataclass
class SongMask:
    """Complete analysis of an audio track."""
    path: str
    title: str
    artist: str
    genre: str
    bpm_global: float
    duration: float
    beat_times: List[float]
    rms_envelope: List[float]
    sections: List[Dict]
    turntable_events: List[Dict]
    mood_vector: Dict[str, float]
    drop_markers: List[float]
    build_markers: List[float]


class AudioMind:
    """AI analysis engine for music features and structure."""
    
    def analyze(self, mp3_path: Path) -> SongMask:
        """Complete analysis of an MP3 file."""
        y, sr = librosa.load(str(mp3_path), sr=22050, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Beat detection
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        
        # Energy envelope
        rms = librosa.feature.rms(y=y)[0]
        rms_norm = (rms / (rms.max() + 1e-8)).tolist()
        
        # Sections
        sections = self._build_sections(y, sr, beat_times, tempo, duration, rms_norm)
        
        # Turntablism events
        tt_events = self._detect_turntablism(y, sr)
        
        # Energy events
        drops, builds = self._detect_energy_events(rms_norm, sr, duration)
        
        # Metadata
        meta = self._read_mp3tags(mp3_path) if ID3 else {'title': mp3_path.stem, 'artist': 'Unknown', 'genre': 'Unknown'}
        
        # Mood
        mood = self._compute_mood(meta)
        
        return SongMask(
            path=str(mp3_path),
            title=meta.get('title', mp3_path.stem),
            artist=meta.get('artist', 'Unknown'),
            genre=meta.get('genre', 'Unknown'),
            bpm_global=float(tempo),
            duration=duration,
            beat_times=beat_times,
            rms_envelope=rms_norm,
            sections=sections,
            turntable_events=tt_events,
            mood_vector=mood,
            drop_markers=drops,
            build_markers=builds
        )
    
    def _build_sections(self, y, sr, beat_times, bpm, duration, rms_norm) -> List[Dict]:
        """Divide song into semantic sections."""
        sections = []
        section_names = ['intro', 'verse', 'chorus', 'verse', 'chorus', 'bridge', 'chorus', 'outro']
        
        num_sections = 8
        section_duration = duration / num_sections
        
        for i in range(num_sections):
            start = i * section_duration
            end = (i + 1) * section_duration
            
            local_beats = [b for b in beat_times if start <= b < end]
            local_bpm = bpm if len(local_beats) < 2 else 60.0 / np.mean(np.diff(local_beats))
            
            # Energy
            rms_times = np.linspace(0, duration, len(rms_norm))
            mask = (rms_times >= start) & (rms_times < end)
            avg_energy = float(np.mean(np.array(rms_norm)[mask])) if mask.any() else 0.5
            
            sections.append({
                'name': section_names[i % len(section_names)],
                'index': i,
                'start': round(start, 3),
                'end': round(end, 3),
                'bpm': round(local_bpm, 1),
                'energy': round(avg_energy, 3),
                'beats_count': len(local_beats)
            })
        
        return sections
    
    def _detect_turntablism(self, y, sr) -> List[Dict]:
        """Detect scratching and turntable effects."""
        events = []
        hop = 512
        
        stft = np.abs(librosa.stft(y, hop_length=hop))
        times = librosa.frames_to_time(np.arange(stft.shape[1]), sr=sr, hop_length=hop)
        freq_bins = librosa.fft_frequencies(sr=sr)
        
        # High-freq energy for scratches
        hi_mask = (freq_bins >= 4000) & (freq_bins <= 12000)
        hi_energy = stft[hi_mask, :].mean(axis=0)
        hi_var = np.abs(np.diff(hi_energy, prepend=hi_energy[0]))
        
        thresh = np.percentile(hi_var, 92)
        i = 0
        while i < len(hi_var):
            if hi_var[i] > thresh:
                j = i
                while j < len(hi_var) and hi_var[j] > thresh * 0.6:
                    j += 1
                if j - i >= 2:
                    events.append({
                        'type': 'scratch',
                        'start': round(float(times[min(i, len(times)-1)]), 3),
                        'end': round(float(times[min(j, len(times)-1)]), 3)
                    })
                i = j
            else:
                i += 1
        
        return events
    
    def _detect_energy_events(self, rms_norm, sr, duration) -> tuple:
        """Detect drops and build-ups."""
        rms = np.array(rms_norm)
        delta = np.diff(rms, prepend=rms[0])
        
        times = np.linspace(0, duration, len(rms))
        drops = times[delta < -0.15].tolist()
        builds = times[delta > 0.08].tolist()
        
        return drops, builds
    
    def _read_mp3tags(self, path: Path) -> Dict:
        """Extract metadata from MP3."""
        meta = {'title': path.stem, 'artist': 'Unknown', 'genre': 'Unknown'}
        
        if ID3 is None:
            return meta
        
        try:
            tags = ID3(str(path))
            if 'TIT2' in tags:
                meta['title'] = str(tags['TIT2'])
            if 'TPE1' in tags:
                meta['artist'] = str(tags['TPE1'])
            if 'TCON' in tags:
                meta['genre'] = str(tags['TCON'])
        except:
            pass
        
        return meta
    
    def _compute_mood(self, meta: Dict) -> Dict:
        """Infer mood from metadata."""
        genre = meta.get('genre', '').lower()
        
        mood = {
            'energy': 0.5,
            'darkness': 0.5,
            'speed': 0.5
        }
        
        if 'trap' in genre or 'drum' in genre:
            mood['energy'] = 0.8
        if 'dark' in genre or 'death' in genre:
            mood['darkness'] = 0.8
        if 'fast' in genre or 'punk' in genre:
            mood['speed'] = 0.8
        
        return mood
