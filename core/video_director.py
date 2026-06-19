# -*- coding: utf-8 -*-
"""
Video Director - Timeline and Editing Decisions
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class CutStyle(Enum):
    """Video cut/editing style"""
    RAPID_FIRE = "rapid_fire"       # Quick cuts on beats
    RHYTHMIC = "rhythmic"           # Cuts every 2-4 beats
    FLOW = "flow"                   # Natural transitions
    SLOW_REVEAL = "slow_reveal"     # Long intro-like
    HOLD_DRIFT = "hold_and_drift"   # Held shots with subtle movement
    FADE_OUT = "fade_out"           # Fade to black/silence


class TransitionType(Enum):
    """Video transition effect"""
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    ZOOM = "zoom"
    GLITCH = "glitch"


@dataclass
class TimelineSegment:
    """Single segment in video timeline"""
    start_time: float
    end_time: float
    clip_path: str
    clip_offset: float
    cut_style: CutStyle
    transition: TransitionType
    audio_marker: Optional[str]  # beat, drop, build, etc.
    metadata: Dict


class Director:
    """Video editing decision engine"""
    
    def __init__(self):
        self.segments: List[TimelineSegment] = []
        
        # Preset mappings
        self.style_rules = {
            'chorus': (CutStyle.RAPID_FIRE, 0.5),      # Energy-dependent
            'verse': (CutStyle.RHYTHMIC, 2.0),
            'intro': (CutStyle.SLOW_REVEAL, 8.0),
            'outro': (CutStyle.FADE_OUT, 4.0),
            'bridge': (CutStyle.HOLD_DRIFT, 6.0)
        }
    
    def create_timeline(
        self,
        audio_features,
        beats: List[float],
        markers: List,
        clips_available: List
    ) -> List[TimelineSegment]:
        """Generate video timeline based on audio features"""
        
        timeline = []
        clip_idx = 0
        
        # Process each section
        for section in audio_features.sections:
            section_name = section['name']
            section_start = section['start']
            section_end = section['end']
            section_beats = [b for b in beats if section_start <= b < section_end]
            
            # Determine cut style
            cut_style, segment_duration = self._select_cut_style(
                section_name,
                audio_features.mood_vector,
                np.mean(audio_features.rms_energy)
            )
            
            # Create segments within this section
            current_time = section_start
            segment_num = 0
            
            while current_time < section_end:
                segment_end = min(current_time + segment_duration, section_end)
                
                # Select a clip
                if len(clips_available) > 0:
                    clip = clips_available[clip_idx % len(clips_available)]
                    clip_idx += 1
                else:
                    continue
                
                # Find associated markers
                associated_markers = [
                    m for m in markers
                    if current_time <= m.time < segment_end
                ]
                
                marker_type = associated_markers[0].marker_type if associated_markers else None
                
                # Select transition
                transition = self._select_transition(cut_style, segment_num)
                
                segment = TimelineSegment(
                    start_time=current_time,
                    end_time=segment_end,
                    clip_path=clip.path,
                    clip_offset=0.0,
                    cut_style=cut_style,
                    transition=transition,
                    audio_marker=marker_type,
                    metadata={
                        'section': section_name,
                        'segment_num': segment_num,
                        'associated_markers': len(associated_markers)
                    }
                )
                
                timeline.append(segment)
                current_time = segment_end
                segment_num += 1
        
        self.segments = timeline
        return timeline
    
    def _select_cut_style(self, section: str, mood_vector: np.ndarray, energy: float) -> tuple:
        """Select cutting style based on section and energy"""
        
        if section not in self.style_rules:
            section = 'verse'
        
        base_style, base_duration = self.style_rules[section]
        
        # Adjust duration based on energy
        # High energy -> shorter segments, low energy -> longer segments
        duration = base_duration * (1.0 - energy * 0.5)  # Energy 0.0-1.0
        
        return base_style, max(0.5, duration)  # Min 0.5 sec
    
    def _select_transition(self, cut_style: CutStyle, segment_num: int) -> TransitionType:
        """Select transition effect"""
        
        transition_map = {
            CutStyle.RAPID_FIRE: TransitionType.CUT,
            CutStyle.RHYTHMIC: TransitionType.DISSOLVE,
            CutStyle.FLOW: TransitionType.FADE,
            CutStyle.SLOW_REVEAL: TransitionType.FADE,
            CutStyle.HOLD_DRIFT: TransitionType.ZOOM,
            CutStyle.FADE_OUT: TransitionType.FADE
        }
        
        return transition_map.get(cut_style, TransitionType.CUT)
    
    def export_edl(self, output_path: str):
        """Export timeline as EDL (Edit Decision List)"""
        
        edl_lines = [
            "TITLE: AI Music Video",
            f"FCM: DROP FRAME\n"
        ]
        
        for i, segment in enumerate(self.segments, 1):
            hours = int(segment.start_time // 3600)
            minutes = int((segment.start_time % 3600) // 60)
            seconds = int(segment.start_time % 60)
            frames = int((segment.start_time % 1) * 24)
            
            edl_line = (
                f"000{i:02d}  AX       V     C        {hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
            )
            edl_lines.append(edl_line)
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(edl_lines))
