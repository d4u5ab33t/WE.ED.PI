#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WE.ED.IT Command Line Interface
"""

import click
import sys
from pathlib import Path
from datetime import datetime

from core.audio_analyzer import AudioAnalyzer
from core.beat_sync import BeatSyncEngine
from core.clip_pool import ClipPool
from core.video_director import Director
from core.db_manager import DatabaseManager


@click.group()
def cli():
    """WE.ED.IT - AI Music Video Generation Engine"""
    pass


@cli.command()
@click.option('--audio', '-a', required=True, help='Audio file path')
@click.option('--output', '-o', default='output', help='Output directory')
@click.option('--clips', '-c', default='clip_pool', help='Clip pool directory')
@click.option('--sr', default=22050, help='Sample rate')
def analyze(audio, output, clips, sr):
    """Analyze audio and extract beats"""
    
    click.echo(f"\n🎵 Analyzing: {audio}")
    
    try:
        # Audio analysis
        analyzer = AudioAnalyzer(sr=sr)
        features = analyzer.analyze(audio)
        
        click.echo(f"   Duration: {features.duration:.2f}s")
        click.echo(f"   Tempo: {features.tempo:.2f} BPM")
        click.echo(f"   Beats: {len(features.beats)}")
        click.echo(f"   Key: {features.key}")
        click.echo(f"   Tags: {', '.join(features.genre_tags)}")
        
        # Beat extraction
        beat_sync = BeatSyncEngine(sr=sr)
        beats = beat_sync.extract_beats(audio)
        
        # Save beats
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        audio_name = Path(audio).stem
        beats_json = output_path / f"{audio_name}_beats.json"
        
        beat_sync.save_beats_json(beats, str(beats_json))
        click.echo(f"\n✅ Beats saved to: {beats_json}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--audio', '-a', required=True, help='Audio file path')
@click.option('--clips', '-c', default='clip_pool', help='Clip pool directory')
@click.option('--output', '-o', default='output', help='Output directory')
@click.option('--db', default='project.db', help='Database file')
def generate(audio, clips, output, db):
    """Generate complete music video"""
    
    click.echo(f"\n🎬 Generating video: {audio}")
    
    try:
        # Initialize
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        db_manager = DatabaseManager(db)
        
        # Analyze audio
        analyzer = AudioAnalyzer()
        features = analyzer.analyze(audio)
        
        # Extract beats
        beat_sync = BeatSyncEngine()
        beats = beat_sync.extract_beats(audio)
        beat_times = [b.timestamp for b in beats]
        
        # Detect markers
        markers = beat_sync.detect_markers(audio)
        
        # Load clip pool
        clip_pool = ClipPool([clips])
        
        # Create timeline
        director = Director()
        timeline = director.create_timeline(features, beat_times, markers, clip_pool.clips)
        
        # Save to database
        audio_name = Path(audio).stem
        output_video = output_path / f"{audio_name}_output.mp4"
        
        render_id = db_manager.add_render(str(audio), str(output_video), features.duration)
        db_manager.update_render_status(render_id, 'processing')
        
        # Add timeline segments
        timeline_data = [
            {
                'clip_path': seg.clip_path,
                'start_time': seg.start_time,
                'end_time': seg.end_time,
                'cut_style': seg.cut_style.value,
                'transition': seg.transition.value,
                'audio_marker': seg.audio_marker,
                'metadata': seg.metadata
            }
            for seg in timeline
        ]
        
        db_manager.add_timeline_segments(render_id, timeline_data)
        
        # Add beats
        beat_data = [
            {'timestamp': b.timestamp, 'confidence': b.confidence, 'strength': b.strength}
            for b in beats
        ]
        db_manager.add_beats(render_id, beat_data)
        
        click.echo(f"\n✅ Timeline created with {len(timeline)} segments")
        click.echo(f"   Render ID: {render_id}")
        click.echo(f"   Output: {output_video}")
        
        db_manager.close()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--clips', '-c', default='clip_pool', help='Clip pool directory')
@click.option('--db', default='clips.json', help='Database file')
def index(clips, db):
    """Index clip pool"""
    
    click.echo(f"\n📹 Indexing clips: {clips}")
    
    try:
        clip_pool = ClipPool([clips], db_path=db)
        clip_pool.save_database()
        
        click.echo(f"\n✅ Indexed {len(clip_pool.clips)} clips")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--db', default='project.db', help='Database file')
def status(db):
    """Show project status"""
    
    try:
        db_manager = DatabaseManager(db)
        renders = db_manager.get_all_renders()
        
        click.echo(f"\n📊 Project Status")
        click.echo(f"   Total renders: {len(renders)}")
        
        for render in renders[:10]:  # Show last 10
            click.echo(f"\n   {render['id']}: {Path(render['mp3_path']).name}")
            click.echo(f"      Status: {render['status']}")
            click.echo(f"      Created: {render['created_at']}")
        
        db_manager.close()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def version():
    """Show version"""
    click.echo("WE.ED.IT v2.0.0")


if __name__ == '__main__':
    cli()
