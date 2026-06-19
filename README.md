# 🎬 WE.ED.IT - AI Music Video Generation Engine

**Version 2.0.0** | Professional AI-powered automatic music video creation system

## Features

✨ **Audio Analysis**
- Beat and tempo detection using librosa
- Onset detection and transient analysis
- Spectral feature extraction (MFCC, chroma, centroid)
- Automatic genre and mood classification
- Section detection (intro, verse, chorus, etc.)

🎬 **Video Generation**
- Intelligent clip selection based on audio features
- Adaptive cutting styles (rapid-fire, rhythmic, flow)
- Timeline construction with beat synchronization
- Transition effect automation
- Multi-format output support

📹 **Clip Pool Management**
- Semantic vector search for video matching
- Metadata caching for performance
- Raspberry Pi optimized (headless OpenCV)
- JSON + SQLite database integration

🎵 **Beat Synchronization**
- Confidence-weighted beat extraction
- Drop/build detection
- Silence and transient marker identification
- EDL export for professional editing

💾 **Database Integration**
- SQLite project management
- Render history and status tracking
- Timeline segment persistence
- Clip rating and usage analytics

🌐 **User Interfaces**
- Command-line interface (CLI)
- Web UI (Streamlit)
- Batch processing capabilities
- Real-time status monitoring

## Installation

### Quick Start (Windows)

```bash
# Run setup script
setup.bat

# Start the app
start_app.bat
```

### Linux / Raspberry Pi

```bash
# Run installation script
bash install-update-all.sh

# Or with options
bash install-update-all.sh --base-dir /home/pi/oidasheim --enable-accents
```

### Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p clip_pool output temp
```

## Usage

### Web Interface (Recommended)

```bash
streamlit run app.py
# Open http://localhost:8501
```

### Command Line

```bash
# Analyze audio
python cli.py analyze --audio song.mp3 --sr 22050

# Generate video
python cli.py generate --audio song.mp3 --clips clip_pool --output output

# Index clips
python cli.py index --clips clip_pool --db clips.json

# Show status
python cli.py status --db project.db
```

### Batch Processing

```bash
# Windows
run.bat

# Linux
bash run.sh
```

## Project Structure

```
WE.ED.IT/
├── core/
│   ├── __init__.py
│   ├── audio_analyzer.py      # Audio feature extraction
│   ├── beat_sync.py           # Beat detection & synchronization
│   ├── clip_pool.py           # Video clip library management
│   ├── video_director.py      # Editing decision engine
│   └── db_manager.py          # Database operations
├── clip_pool/                 # Video clips directory
│   ├── action/
│   ├── landscape/
│   ├── abstract/
│   └── ...
├── output/                    # Generated videos
├── temp/                      # Temporary files
├── models/                    # ML models (optional)
├── cli.py                     # Command-line interface
├── app.py                     # Streamlit web interface
├── requirements.txt           # Python dependencies
├── setup.bat                  # Windows installation
├── setup.sh                   # Linux installation
├── start_app.bat              # Windows launcher
├── start_cli.bat              # Windows CLI launcher
└── README.md                  # This file
```

## Configuration

### Audio Processing

```python
from core.audio_analyzer import AudioAnalyzer

analyzer = AudioAnalyzer(
    sr=22050,          # Sample rate
    n_fft=2048,        # FFT window size
    hop_length=512     # Hop length
)

features = analyzer.analyze('song.mp3')
print(f"Tempo: {features.tempo} BPM")
print(f"Key: {features.key}")
print(f"Tags: {features.genre_tags}")
```

### Clip Pool

```python
from core.clip_pool import ClipPool

clip_pool = ClipPool(
    pool_dirs=['clip_pool/action', 'clip_pool/landscape'],
    db_path='clips.json',
    cache_path='cache/'
)

# Select clip based on audio mood
clip = clip_pool.select_best_clip(
    min_duration=1.0,
    query_vector=audio_features.mood_vector,
    avoid_reuse=True,
    cooldown=5
)
```

### Video Director

```python
from core.video_director import Director

director = Director()

timeline = director.create_timeline(
    audio_features=features,
    beats=beat_times,
    markers=timeline_markers,
    clips_available=clip_pool.clips
)

# Export as EDL
director.export_edl('timeline.edl')
```

## Platform Support

- ✅ Windows 10/11 (x64)
- ✅ Linux (Ubuntu 20.04+, Debian)
- ✅ Raspberry Pi (4GB+ RAM, Pi 4/5)
- ✅ macOS (Intel/Apple Silicon)

## Performance

| Operation | Time (Pi 4) | Time (Desktop) |
|-----------|-----------|----------------|
| Audio analysis (3 min) | ~15s | ~3s |
| Beat extraction | ~5s | ~1s |
| Clip indexing (100 clips) | ~30s | ~5s |
| Timeline generation | ~2s | <1s |
| Video rendering (3 min) | ~5min | ~1min |

## Troubleshooting

### FFmpeg not found
```bash
# Windows
winget install ffmpeg

# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### ImportError: librosa not found
```bash
pip install librosa
```

### Database locked
```bash
# Close any open database connections
# Delete *.db-journal files
rm project.db-journal
```

### Out of memory on Raspberry Pi
```bash
# Enable swap
sudo dphys-swapfile swapon

# Reduce sample rate
python cli.py analyze --audio song.mp3 --sr 16000
```

## Development

### Adding Custom Effects

```python
from core.video_director import TransitionType

class CustomTransition(TransitionType):
    CUSTOM = "custom"
    
    # Add your effect logic
```

### Extending Audio Analysis

```python
class CustomAnalyzer(AudioAnalyzer):
    def _custom_feature(self, y, sr):
        # Your analysis code
        pass
```

## API Documentation

See [API.md](API.md) for complete API reference.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See LICENSE file

## Credits

Built with:
- [librosa](https://librosa.org/) - Audio analysis
- [moviepy](https://zulko.github.io/moviepy/) - Video processing
- [OpenCV](https://opencv.org/) - Computer vision
- [Streamlit](https://streamlit.io/) - Web interface

## Support

- 📧 Email: support@example.com
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions

---

**Made with ❤️ for music video creators**
