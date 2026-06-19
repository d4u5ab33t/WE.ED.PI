#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
██╗    ██╗███████╗   ███████╗██████╗   ██╗████████╗
██║    ██║██╔════╝   ██╔════╝██╔══██╗  ██║╚══██╔══╝
██║ █╗ ██║█████╗     █████╗  ██║  ██║  ██║   ██║
██║███╗██║██╔══╝     ██╔══╝  ██║  ██║  ██║   ██║
╚███╔███╝███████╗   ███████╗██████╔╝  ██║   ██║
 ╚══╝╚══╝ ╚══════╝   ╚══════╝╚═════╝   ╚═╝   ╚═╝

WE.ED.IT — CINEMATIC BEAT SYNC ENGINE
Automatisch Musikvideos aus MP3 + Clips generieren
Arch_V3: Volle FFmpeg Filtergraph VFX Integration
"""

import os
import sys
import argparse
import subprocess
import random
import tempfile
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

import numpy as np
try:
    import librosa
except ImportError:
    print("[!] librosa nicht installiert. Bitte ausführen: pip install librosa")
    sys.exit(1)

# ==========================================
# CONFIGURATION
# ==========================================
DEFAULT_CONFIG = {
    'finish_dir': Path('./done'),
    'songs_dir': Path('./Sound'),
    'clip_pools': [Path('./Clips')],
    'cache_dir': Path('./cache'),
    'log_file': Path('./weedit_log.json'),
    'video_exts': {'.mp4', '.mkv', '.mov', '.avi', '.webm'},
    'audio_exts': {'.mp3', '.wav', '.flac', '.m4a'},
}

# VFX PRESETS – Cinematography-inspired filtergraph chains
VFX_PRESETS = {
    # --- GRADING & COLOR ---
    "Vintage": "curves=vintage,noise=alls=20:allf=t",
    "Night Vision": "curves=g='0/0 0.5/1 1/1',noise=alls=40:allf=t",
    "Thermal": "hue=s=0,curves=r='0/0 0.4/1 0.6/0 1/1':g='0/0 0.5/0 0.8/1 1/0':b='0/1 1/0'",
    "X-Ray": "hue=s=0,curves=negative,unsharp=5:5:1.5",
    "Silhouette": "curves='0/0 0.1/0 0.2/1 1/1',eq=contrast=1.5",
    "Dreamcore": "gblur=sigma=0.5,hue=H=2*PI*t/10",
    "Dystopian": "curves=preset=darker,eq=saturation=0.3,noise=alls=15",
    "Halation": "gblur=sigma=4,curves=m='0/0 0.5/0.7 1/1'",
    "Haze": "gblur=sigma=2,eq=brightness=0.1:saturation=0.8",
    "Color Shift": "hue=H=2*PI*t/5",
    "Weirdcore": "curves=preset=color_negative,noise=alls=40,hue=H=PI",
    
    # --- LENS & OPTICAL ---
    "Fisheye": "lenscorrection=0.5:0.5:0.5:0.8",
    "Vignette": "vignette=PI/4",
    "Shallow Focus": "smartblur=lr=3:ls=0.5:lt=-4",
    "Tilt Shift": "smartblur=lr=5:ls=1:lt=-4",
    "Pixel Art": "scale=iw/8:-1:flags=neighbor,scale=1920:1080:flags=neighbor",
    
    # --- GLITCH & ABSTRACT ---
    "Datamosh": "tblend=all_mode=difference128,noise=alls=30",
    "Distortions": "noise=alls=50:allf=t,hue=H=2*PI*t",
    "Echo Print": "tblend=all_mode=average",
    "Glitch": "noise=alls=80:allf=t,curves=vintage",
    "Altered State": "hue=H=2*PI*t/3,gblur=sigma=1,eq=saturation=2",
    "Infinite Loop": "tblend=all_mode=grainmerge",
    
    # --- CAMERA MOVES (Simulated) ---
    "Dolly Zoom": "zoompan=z='if(eq(on,1),1.5,zoom-0.005)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30",
    "Fast Zoom": "zoompan=z='min(zoom+0.01,2.0)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30",
    "Slow Dolly": "zoompan=z='min(zoom+0.0015,1.2)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30",
}

# ==========================================
# LOGGING
# ==========================================
class Logger:
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.entries = []
        self.load()
    
    def load(self):
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    self.entries = json.load(f)
            except:
                self.entries = []
    
    def add(self, event: str, status: str, details: Dict = None):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'status': status,
            'details': details or {}
        }
        self.entries.append(entry)
        self.save()
    
    def save(self):
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, 'w') as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def get_media_files(directory: Path, extensions: set) -> List[Path]:
    files = []
    if not directory.exists():
        return files
    for ext in extensions:
        files.extend(directory.rglob(f"*{ext}"))
    return sorted(files)

def get_probe_duration(filepath: Path) -> float:
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', str(filepath)]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               text=True, check=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def get_next_version(base_path: Path) -> Path:
    """Return versioned filename (e.g., song_v1.mp4, song_v2.mp4)"""
    if not base_path.exists():
        return base_path
    
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    
    version = 1
    while True:
        new_name = f"{stem}_v{version}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        version += 1

# ==========================================
# BEAT DETECTION ENGINE
# ==========================================
def detect_beats(mp3_path: Path) -> Tuple[np.ndarray, np.ndarray]:
    print(f"  [*] Analyzing audio: {mp3_path.name}")
    try:
        y, sr = librosa.load(str(mp3_path), sr=None, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        intervals = np.diff(beat_times)
        print(f"  [+] Detected {len(beat_times)} beats @ {tempo:.1f} BPM")
        return beat_times, intervals
    except Exception as e:
        print(f"  [!] Beat detection failed: {e}")
        return np.array([]), np.array([])

# ==========================================
# FFMPEG FILTERGRAPH BUILDER
# ==========================================
def build_and_execute(video_clips: List[Tuple[Path, float]], 
                      beat_times: np.ndarray, 
                      intervals: np.ndarray,
                      mp3_path: Path,
                      output_path: Path,
                      logger: Logger):
    
    if len(video_clips) == 0:
        print("  [!] No video clips to process.")
        logger.add('render', 'failed', {'reason': 'No clips available'})
        return False
    
    if len(intervals) == 0:
        print("  [!] No beat intervals detected.")
        logger.add('render', 'failed', {'reason': 'No beats detected'})
        return False
    
    inputs = []
    filter_parts = []
    concat_inputs = ""
    vfx_list = list(VFX_PRESETS.keys())
    n_clips = len(video_clips)
    
    print(f"  [*] Building filtergraph for {n_clips} clips...")
    
    for i, (clip_path, duration) in enumerate(video_clips):
        inputs.extend(['-i', str(clip_path)])
        
        target_dur = float(intervals[i] if i < len(intervals) else 1.0)
        if target_dur < 0.1:
            target_dur = 0.1
        if target_dur > duration:
            target_dur = duration
        
        # Random VFX preset
        chosen_vfx_name = random.choice(vfx_list)
        vfx_chain = VFX_PRESETS[chosen_vfx_name]
        
        # Build filter for this clip
        if "zoompan" in vfx_chain:
            base_chain = f"[{i}:v]trim=0:{target_dur},setpts=PTS-STARTPTS,"
            filt = f"{base_chain}{vfx_chain},format=yuv420p[v{i}];"
        else:
            base_chain = (
                f"[{i}:v]trim=0:{target_dur},setpts=PTS-STARTPTS,"
                f"scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,"
                f"fps=30,format=yuv420p,"
            )
            filt = f"{base_chain}{vfx_chain}[v{i}];"
        
        filter_parts.append(filt)
        concat_inputs += f"[v{i}]"
        print(f"    • Clip {i+1}: {clip_path.name[:30]:30s} | VFX: {chosen_vfx_name}")
    
    # Concatenate all videos
    concat_filter = f"{concat_inputs}concat=n={n_clips}:v=1:a=0[outv]"
    filter_parts.append(concat_filter)
    
    filter_complex = "".join(filter_parts)
    
    # Write filtergraph to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(filter_complex)
        filter_script_path = f.name
    
    try:
        # Build FFmpeg command
        cmd = ['ffmpeg', '-y']
        cmd.extend(inputs)
        cmd.extend(['-i', str(mp3_path)])
        cmd.extend([
            '-filter_complex_script', filter_script_path,
            '-map', '[outv]',
            '-map', f'{n_clips}:a',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            str(output_path)
        ])
        
        print(f"  [*] Rendering...")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  [+] ✅ Video saved: {output_path}")
        logger.add('render', 'success', {'output': str(output_path), 'vfx_count': n_clips})
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"  [!] FFmpeg failed: {e}")
        logger.add('render', 'failed', {'error': str(e)})
        return False
    
    finally:
        try:
            os.unlink(filter_script_path)
        except:
            pass

# ==========================================
# MAIN PIPELINE
# ==========================================
def process_song(song_path: Path, config: Dict, logger: Logger) -> bool:
    print(f"\n{'='*60}")
    print(f"  📁 Processing: {song_path.name}")
    print(f"{'='*60}")
    
    output_name = f"{song_path.stem}_BEATSYNC.mp4"
    output_path = config['finish_dir'] / output_name
    output_path = get_next_version(output_path)
    
    # Detect beats
    beat_times, intervals = detect_beats(song_path)
    if len(intervals) == 0:
        print(f"  [!] Skipping {song_path.name}: No beats detected.")
        logger.add('process_song', 'failed', {'reason': 'No beats detected'})
        return False
    
    # Select clips
    num_clips_needed = len(intervals)
    all_clips = []
    for pool in config['clip_pools']:
        all_clips.extend(get_media_files(pool, config['video_exts']))
    
    if not all_clips:
        print(f"  [!] No clips found in pools.")
        logger.add('process_song', 'failed', {'reason': 'No clips in pool'})
        return False
    
    random.shuffle(all_clips)
    selected_clips = []
    clip_idx = 0
    
    while len(selected_clips) < num_clips_needed:
        clip_path = all_clips[clip_idx % len(all_clips)]
        duration = get_probe_duration(clip_path)
        if duration > 0:
            selected_clips.append((clip_path, duration))
        clip_idx += 1
    
    print(f"  [*] Selected {len(selected_clips)} clips for sync.")
    
    # Render
    config['finish_dir'].mkdir(parents=True, exist_ok=True)
    success = build_and_execute(selected_clips, beat_times, intervals, song_path, output_path, logger)
    
    if success:
        logger.add('process_song', 'success', {'song': song_path.name, 'output': output_path.name})
    
    return success

def main():
    parser = argparse.ArgumentParser(description='WE.ED.IT — Cinematic Beat Sync Engine')
    parser.add_argument('--sound', type=Path, help='Sound/MP3 directory', default=None)
    parser.add_argument('--clips', type=Path, help='Clip pool directory', default=None)
    parser.add_argument('--out', type=Path, help='Output directory', default=None)
    parser.add_argument('--batch', action='store_true', help='Batch mode: process all MP3s')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--version', action='store_true', help='Show version')
    
    args = parser.parse_args()
    
    if args.version:
        print("WE.ED.IT v3.0 — Cinematic Beat Sync Engine")
        return
    
    # Build config
    config = DEFAULT_CONFIG.copy()
    if args.sound:
        config['songs_dir'] = args.sound
    if args.clips:
        config['clip_pools'] = [args.clips]
    if args.out:
        config['finish_dir'] = args.out
    
    # Ensure directories exist
    config['finish_dir'].mkdir(parents=True, exist_ok=True)
    config['cache_dir'].mkdir(parents=True, exist_ok=True)
    
    logger = Logger(config['log_file'])
    
    print("\n" + "="*60)
    print("  🎬 WE.ED.IT — CINEMATIC BEAT SYNC ENGINE")
    print("  Automatic Music Video Generator")
    print("="*60)
    print(f"  🎵 Sound Dir: {config['songs_dir']}")
    print(f"  🎬 Clip Pools: {config['clip_pools']}")
    print(f"  💾 Output Dir: {config['finish_dir']}")
    print(f"  📊 VFX Presets: {len(VFX_PRESETS)}")
    print("="*60)
    
    # Get songs
    songs = get_media_files(config['songs_dir'], config['audio_exts'])
    if not songs:
        print(f"\n[!] No MP3 files found in {config['songs_dir']}")
        return
    
    print(f"\n[+] Found {len(songs)} song(s)\n")
    
    # Check clip pools
    all_clips_count = sum(len(get_media_files(pool, config['video_exts'])) 
                          for pool in config['clip_pools'])
    print(f"[+] Found {all_clips_count} clip(s) in pool(s)\n")
    
    if all_clips_count == 0:
        print("[!] No clips found. Please add video files to clip directories.")
        return
    
    # Process songs
    success_count = 0
    for i, song in enumerate(songs, 1):
        print(f"\n[{i}/{len(songs)}]", end=" ")
        if process_song(song, config, logger):
            success_count += 1
    
    print(f"\n\n{'='*60}")
    print(f"  🏁 Finished: {success_count}/{len(songs)} videos created")
    print(f"  📁 Output: {config['finish_dir']}")
    print(f"  📋 Log: {config['log_file']}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
