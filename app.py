#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WE.ED.IT Streamlit Web Interface
"""

import streamlit as st
import os
from pathlib import Path
from datetime import datetime

from core.audio_analyzer import AudioAnalyzer
from core.beat_sync import BeatSyncEngine
from core.clip_pool import ClipPool
from core.video_director import Director
from core.db_manager import DatabaseManager

# Page config
st.set_page_config(
    page_title="WE.ED.IT",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 WE.ED.IT - AI Music Video Generator")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    sr = st.slider("Sample Rate", 8000, 44100, 22050, step=1000)
    clip_pool_dir = st.text_input("Clip Pool Directory", "clip_pool")
    output_dir = st.text_input("Output Directory", "output")
    db_file = st.text_input("Database File", "project.db")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎵 Analyze", "🎬 Generate", "📊 Status", "📹 Clips"])

with tab1:
    st.header("Audio Analysis")
    
    audio_file = st.file_uploader("Upload MP3", type=["mp3", "wav", "ogg"])
    
    if audio_file:
        # Save uploaded file
        audio_path = Path("temp") / audio_file.name
        audio_path.parent.mkdir(exist_ok=True)
        audio_path.write_bytes(audio_file.getbuffer())
        
        if st.button("Analyze"):
            with st.spinner("Analyzing..."):
                try:
                    analyzer = AudioAnalyzer(sr=sr)
                    features = analyzer.analyze(str(audio_path))
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Duration", f"{features.duration:.2f}s")
                    col2.metric("Tempo", f"{features.tempo:.0f} BPM")
                    col3.metric("Beats", len(features.beats))
                    col4.metric("Key", features.key)
                    
                    st.subheader("Genre Tags")
                    st.write(", ".join(features.genre_tags))
                    
                    st.subheader("Mood Vector")
                    st.bar_chart({
                        'Energy': features.mood_vector[0],
                        'Brightness': features.mood_vector[1],
                        'Tempo': features.mood_vector[2],
                        'Dynamic': features.mood_vector[3],
                        'Warmth': features.mood_vector[4]
                    })
                    
                    # Beat detection
                    beat_sync = BeatSyncEngine(sr=sr)
                    beats = beat_sync.extract_beats(str(audio_path))
                    
                    st.subheader("Beats Detected")
                    beats_df = __import__('pandas').DataFrame([
                        {'Time': b.timestamp, 'Confidence': b.confidence, 'Strength': b.strength}
                        for b in beats[:20]
                    ])
                    st.dataframe(beats_df)
                    
                except Exception as e:
                    st.error(f"Error: {e}")

with tab2:
    st.header("Generate Music Video")
    
    audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav"], key="gen")
    
    if audio_file and st.button("Generate Video"):
        with st.spinner("Generating..."):
            try:
                # Save audio
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True)
                audio_path = output_path / audio_file.name
                audio_path.write_bytes(audio_file.getbuffer())
                
                # Initialize
                db_manager = DatabaseManager(db_file)
                
                # Analyze
                analyzer = AudioAnalyzer(sr=sr)
                features = analyzer.analyze(str(audio_path))
                
                # Extract beats
                beat_sync = BeatSyncEngine(sr=sr)
                beats = beat_sync.extract_beats(str(audio_path))
                beat_times = [b.timestamp for b in beats]
                
                # Detect markers
                markers = beat_sync.detect_markers(str(audio_path))
                
                # Load clips
                clip_pool = ClipPool([clip_pool_dir])
                
                # Create timeline
                director = Director()
                timeline = director.create_timeline(features, beat_times, markers, clip_pool.clips)
                
                # Save
                audio_name = audio_path.stem
                output_video = output_path / f"{audio_name}_output.mp4"
                
                render_id = db_manager.add_render(str(audio_path), str(output_video), features.duration)
                db_manager.update_render_status(render_id, 'processing')
                
                st.success(f"✅ Timeline created with {len(timeline)} segments")
                st.info(f"Render ID: {render_id}")
                
                db_manager.close()
                
            except Exception as e:
                st.error(f"Error: {e}")

with tab3:
    st.header("Project Status")
    
    try:
        db_manager = DatabaseManager(db_file)
        renders = db_manager.get_all_renders()
        
        if renders:
            st.metric("Total Renders", len(renders))
            
            for render in renders[:10]:
                with st.expander(f"Render {render['id']}: {Path(render['mp3_path']).name}"):
                    st.write(f"Status: **{render['status']}**")
                    st.write(f"Created: {render['created_at']}")
                    st.write(f"Duration: {render['duration']:.2f}s")
        else:
            st.info("No renders yet")
        
        db_manager.close()
    except Exception as e:
        st.error(f"Error: {e}")

with tab4:
    st.header("Clip Pool")
    
    try:
        clip_pool = ClipPool([clip_pool_dir])
        st.metric("Clips Indexed", len(clip_pool.clips))
        
        # Display clips
        cols = st.columns(3)
        for i, clip in enumerate(clip_pool.clips[:9]):
            with cols[i % 3]:
                st.write(f"**{Path(clip.path).name}**")
                st.write(f"Duration: {clip.duration:.2f}s")
                st.write(f"Resolution: {clip.width}x{clip.height}")
                st.write(f"Used: {clip.use_count} times")
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()
st.caption("WE.ED.IT v2.0.0 - AI Music Video Generation Engine")
