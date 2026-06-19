# WE.ED.IT — Cinematic Beat Sync Video Editor

**Transform your music into stunning AI-generated music videos in seconds.**

> 1-Click: **MP3 + Video Clips → Epic Music Video** 🎬🎵

## Features

✨ **Automatic Music Video Generation**
- Beat detection from MP3 files
- Smart clip selection and sequencing
- Dynamic transitions and effects

🎨 **30+ Cinematic VFX Presets**
- Grading: Vintage, Night Vision, Thermal, X-Ray, Dreamcore, Dystopian
- Optical: Fisheye, Vignette, Shallow Focus, Tilt Shift, Pixel Art
- Abstract: Datamosh, Glitch, Distortions, Altered State
- Camera Moves: Dolly Zoom, Fast Zoom, Slow Dolly

🧠 **AI-Powered Intelligence**
- Automatic turntablism detection (scratches, rewinds, stops)
- Energy event markers (drops, build-ups)
- Semantic song structure analysis
- Clip pool learning (positive/negative feedback)

💾 **Persistent Learning**
- SQLite vault for clip metadata
- Usage statistics and win/loss tracking
- Render history and logging

🚀 **Production-Ready**
- H.264/H.265 encoding
- 1920x1080 @ 30fps standard
- Version auto-increment (no overwrites)
- Batch processing mode

---

## Installation

### Windows (1-Click)

```bash
PowerShell -ExecutionPolicy Bypass -File INSTALL_WEEDIT.ps1
```

Then:
```bash
.\run_weedit.ps1
```

### Linux / Raspberry Pi

```bash
bash install-update-all.sh --base-dir ~/oidasheim
```

Then:
```bash
~/oidasheim/run.sh
```

### Manual Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (if not present)
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: winget install Gyan.FFmpeg
```

---

## Quick Start

### Structure

```
project/
├── Sound/              # Place MP3 files here
├── Clips/              # Place video clips here (mp4, mkv, avi, mov, webm)
├── done/               # Output videos
├── cinematic_beat_sync.py
├── run_weedit.ps1      # Windows launcher
└── requirements.txt
```

### Usage

#### Option A: Launcher (Windows)
```bash
.\run_weedit.ps1
```

#### Option B: Command Line
```bash
python cinematic_beat_sync.py --sound ./Sound --clips ./Clips --out ./done
```

#### Option C: Batch Mode
```bash
python cinematic_beat_sync.py --batch
```

#### Option D: With Custom Paths
```bash
python cinematic_beat_sync.py \
  --sound "D:\My Music" \
  --clips "D:\Video Clips" \
  --out "D:\Finished Videos"
```

---

## Architecture

### Core Modules

**`cinematic_beat_sync.py`** (Main Engine)
- Beat detection via librosa
- Clip selection algorithm
- FFmpeg filtergraph generation
- Batch processing

**`core/audio_mind.py`** (Audio Analysis)
- MP3 tag parsing
- BPM detection
- Turntablism event detection
- Energy envelope analysis
- Mood inference

**`core/virtual_vault.py`** (Learning Database)
- Clip metadata persistence
- Usage statistics
- Render history
- Win/loss tracking for learning

### VFX System

Each preset is an FFmpeg filtergraph chain:

```python
VFX_PRESETS = {
    "Vintage": "curves=vintage,noise=alls=20:allf=t",
    "Glitch": "noise=alls=80:allf=t,curves=vintage",
    "Dolly Zoom": "zoompan=z='if(eq(on,1),1.5,zoom-0.005)':d=1:...",
    # ... 30+ more presets
}
```

Each clip randomly receives one VFX treatment.

---

## Configuration

Edit `cinematic_beat_sync.py` to customize:

```python
DEFAULT_CONFIG = {
    'finish_dir': Path('./done'),
    'songs_dir': Path('./Sound'),
    'clip_pools': [Path('./Clips')],
    'cache_dir': Path('./cache'),
}
```

---

## Performance

| Hardware | 3-Min Video | Quality |
|----------|-------------|----------|
| Intel i7 / GTX 1070 | ~5 min | 1080p/30fps, CRF 18 |
| Raspberry Pi 4 | ~45 min | 1080p/30fps, CRF 23 |
| AWS t3.medium | ~3 min | 1080p/30fps, CRF 18 |

Use `--crf 23` (lower quality) for faster rendering.

---

## Advanced Usage

### Using Your Own VFX

Add to `VFX_PRESETS`:

```python
VFX_PRESETS['My Custom FX'] = "gblur=sigma=2,eq=contrast=1.2"
```

### Database Inspection

```bash
sqlite3 cache/weedit_vault.db
SELECT path, use_count, positive_uses FROM clips ORDER BY use_count DESC;
```

### Disable Random VFX

Edit `build_and_execute()` and replace:
```python
chosen_vfx_name = random.choice(vfx_list)
```
with:
```python
chosen_vfx_name = 'Vintage'  # Fixed preset
```

---

## Troubleshooting

### "No beats detected"

The audio file may be too quiet or have unusual structure.
- Try a different MP3
- Adjust librosa parameters in `audio_mind.py`

### "No clips found"

Ensure clip files are in the correct format (.mp4, .mkv, .avi, .mov, .webm) and readable by FFprobe.

```bash
ffprobe "Clips/myclip.mp4"
```

### FFmpeg errors

Check that FFmpeg is installed and in PATH:

```bash
ffmpeg -version
ffprobe -version
```

### Slow rendering

Try lower quality (higher CRF):
```bash
# Edit cinematic_beat_sync.py, change:
# '-crf', '18'  →  '-crf', '23'
```

---

## Roadmap

- [ ] GPU acceleration (NVIDIA NVENC)
- [ ] Multi-GPU support
- [ ] Real-time preview mode
- [ ] Web UI (Streamlit)
- [ ] Automatic subtitle generation
- [ ] Music sync fine-tuning API

---

## License

MIT — Feel free to fork and extend!

---

## Support

📧 Email: support@weedit.dev  
🐛 Issues: [GitHub Issues](https://github.com/d4u5ab33t/WE.ED.PI/issues)  
💬 Discussions: [GitHub Discussions](https://github.com/d4u5ab33t/WE.ED.PI/discussions)

---

**Made with 🎬 and ❤️ by the WE.ED.IT Team**
