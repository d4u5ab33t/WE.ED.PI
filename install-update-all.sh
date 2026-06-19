#!/usr/bin/env bash
# WE.ED.IT Complete Installation & Update Script for Raspberry Pi / ARM Linux
# Usage: bash install-update-all.sh [--base-dir /path] [--skip-symlinks] [--enable-accents]

set -euo pipefail

BASE_DIR="${HOME}/oidasheim"
SKIP_SYMLINKS=false
ENABLE_ACCENTS=false
NO_CLONE=false

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-dir) BASE_DIR="$2"; shift 2 ;;
        --skip-symlinks) SKIP_SYMLINKS=true; shift ;;
        --enable-accents) ENABLE_ACCENTS=true; shift ;;
        --no-clone) NO_CLONE=true; shift ;;
        --help) echo "Usage: $0 [--base-dir /path] [--skip-symlinks] [--enable-accents]"; exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

step()  { echo -e "\n${CYAN}==> $*${NC}"; }
ok()    { echo -e "    ${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "    ${YELLOW}[!]${NC} $*"; }
err()   { echo -e "    ${RED}[ERROR]${NC} $*"; exit 1; }

# 1. System Dependencies
step "Checking system dependencies..."

sudo apt update -qq || warn "apt update failed"

PACKAGES=(
    python3 python3-pip python3-venv
    git ffmpeg build-essential
    libsndfile1 libatlas-base-dev libopenblas-dev liblapack-dev
)

sudo apt install -y --no-install-recommends "${PACKAGES[@]}" || err "Installation failed"

ok "Python: $(python3 --version)"
ok "FFmpeg: $(ffmpeg -version | head -n1)"
ok "Git: $(git --version)"

# 2. Directory Structure
step "Creating directory structure..."

REPOS="${BASE_DIR}/repos"
VENV="${REPOS}/.venv"
NFOS="${BASE_DIR}/NFOs"
CLIPS="${NFOS}/Clips"
MP3S="${NFOS}/mp3"

mkdir -p "$REPOS" "$NFOS" "$CLIPS" "$MP3S" "${BASE_DIR}/done" "${BASE_DIR}/temp"
ok "Directories created"

# 3. Virtual Environment
step "Setting up Python virtual environment..."

if [[ ! -d "${VENV}/bin" ]]; then
    python3 -m venv "$VENV"
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi

PIP="${VENV}/bin/pip"
"$PIP" install --upgrade pip --quiet
ok "pip updated"

# 4. Install Python Packages
step "Installing Python packages (ARM-optimized)..."

"$PIP" install --upgrade \
    numpy scipy librosa mutagen opencv-python-headless \
    streamlit ffmpeg-python scikit-learn pandas psutil tqdm python-dotenv \
    --quiet

ok "Python packages installed"

# 5. Clone/Update Repositories
if [[ "$NO_CLONE" == "false" ]]; then
    step "Cloning/updating repositories..."
    
    declare -A REPOS_MAP=(
        ["BeatSync-Engine"]="https://github.com/Merserk/BeatSync-Engine.git"
        ["CutClaw"]="https://github.com/GVCLab/CutClaw.git"
    )
    
    for name in "${!REPOS_MAP[@]}"; do
        target="${REPOS}/${name}"
        if [[ -d "${target}/.git" ]]; then
            ok "${name} exists - pulling updates"
            (cd "$target" && git pull --quiet)
        else
            ok "Cloning ${name}..."
            git clone "${REPOS_MAP[$name]}" "$target" --quiet || warn "Clone failed: $name"
        fi
    done
fi

# 6. Create Launch Scripts
step "Creating launch scripts..."

cat > "${BASE_DIR}/run.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")" || exit
while true; do
    clear
    echo "======================================================================"
    echo "WE.ED.IT Music Video Generator - Main Menu"
    echo "======================================================================"
    echo
    echo "1. Batch process all audio files"
    echo "2. Continue batch processing"
    echo "3. Process single audio file"
    echo "4. Index clip pool"
    echo "5. Web UI"
    echo "6. Exit"
    echo
    read -p "Choose [1-6]: " choice
    
    case "$choice" in
        1) "${REPOS}/.venv/bin/python3" cli.py batch --all ;;
        3) read -p "Audio file: " audio; "${REPOS}/.venv/bin/python3" cli.py generate --audio "$audio" ;;
        4) "${REPOS}/.venv/bin/python3" cli.py index ;;
        5) "${REPOS}/.venv/bin/streamlit" run app.py ;;
        6) exit 0 ;;
        *) echo "Invalid option"; sleep 1 ;;
    esac
done
EOF

chmod +x "${BASE_DIR}/run.sh"
ok "Launch scripts created"

# 7. Final Summary
echo
step "Installation complete!"
echo
echo "  To start: ${BASE_DIR}/run.sh"
echo "  Or: source ${REPOS}/.venv/bin/activate"
echo "      python cli.py --help"
echo
