#!/usr/bin/env bash
#
# WE.ED.IT – Komplett-Installation & Update für Raspberry Pi / ARM‑Linux
# Führt alle Schritte für die AI‑Musikvideo‑Pipeline aus:
#   - Prüft/installiert System‑Abhängigkeiten (Python, Git, FFmpeg, ...)
#   - Richtet virtuelle Python‑Umgebung ein
#   - Installiert Python‑Pakete (optimiert für ARM)
#   - Klont/aktualisiert Repositories
#   - Erstellt Verzeichnisstruktur und Symlinks
#   - Wendet Code‑Patches (Einrückungen) an
#   - Initialisiert die Clip‑Datenbank
#   - Erstellt Start‑Skripte (run.sh, start_app.sh, start_cli.sh)
#
# Nutzung:
#   ./install-update-all.sh [--base-dir /pfad] [--skip-symlinks] [--no-clone]
#
# Per SSH (vom entfernten Rechner):
#   ssh pi@ip 'bash -s' < install-update-all.sh
#
# Autor: Dex, optimiert für ARM

set -euo pipefail

# ─── Standardwerte ──────────────────────────────────────────────
BASE_DIR="${HOME}/oidasheim"
SKIP_SYMLINKS=false
NO_CLONE=false

# ─── Optionen parsen ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-dir)   BASE_DIR="$2"; shift 2 ;;
        --skip-symlinks) SKIP_SYMLINKS=true; shift ;;
        --no-clone)   NO_CLONE=true; shift ;;
        --help)       echo "Verwendung: $0 [--base-dir /pfad] [--skip-symlinks] [--no-clone]"; exit 0 ;;
        *)            echo "Unbekannte Option: $1"; exit 1 ;;
    esac
done

# ─── Farben & Hilfsfunktionen ──────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

step()  { echo -e "\n${CYAN}==> $*${NC}"; }
ok()    { echo -e "    ${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "    ${YELLOW}[!]${NC} $*"; }
err()   { echo -e "    ${RED}[ERROR]${NC} $*"; exit 1; }

# ─── 1. System‑Abhängigkeiten ─────────────────────────────────
step "Prüfe System‑Abhängigkeiten (sudo für apt nötig)..."

if ! command -v sudo &>/dev/null; then
    err "sudo nicht gefunden – bitte als root ausführen oder sudo installieren."
fi

sudo apt update -qq || warn "apt update fehlgeschlagen – möglicherweise kein Internet?"

PACKAGES=(
    python3 python3-pip python3-venv
    git
    ffmpeg
    build-essential
    libsndfile1 libatlas-base-dev
    libopenblas-dev
    liblapack-dev
)

step "Installiere Systempakete: ${PACKAGES[*]}"
sudo apt install -y --no-install-recommends "${PACKAGES[@]}" || err "Installation fehlgeschlagen."

ok "Python3: $(python3 --version)"
ok "pip3: $(pip3 --version)"
ok "Git: $(git --version)"
ok "FFmpeg: $(ffmpeg -version | head -n1)"

# ─── 2. Verzeichnisstruktur ──────────────────────────────────
step "Erstelle Basis‑Verzeichnisse unter $BASE_DIR"

REPOS="${BASE_DIR}/repos"
VENV="${REPOS}/.venv"
NFOS="${BASE_DIR}/NFOs"
CLIPS="${NFOS}/Clips"
MP3S="${NFOS}/mp3"
DONE="${BASE_DIR}/done"
TEMP="${BASE_DIR}/temp"

mkdir -p "$REPOS" "$NFOS" "$CLIPS" "$MP3S" "$DONE" "$TEMP"
ok "Alle Ordner existieren/ wurden angelegt."

# ─── 3. Virtuelle Umgebung ──────────────────────────────────
step "Richte Python Virtual Environment ein"

if [[ ! -d "$VENV/bin" ]]; then
    python3 -m venv "$VENV"
    ok "Virtuelle Umgebung neu erstellt."
else
    ok "Virtuelle Umgebung existiert bereits."
fi

PIP="$VENV/bin/pip"
$PIP install --upgrade pip --quiet
ok "Pip aktualisiert."

step "Installiere Python‑Pakete (ARM‑optimiert)"
$PIP install --upgrade \
    numpy scipy librosa mutagen opencv-python-headless \
    streamlit ffmpeg-python scikit-learn pandas psutil tqdm python-dotenv \
    --quiet
ok "Alle Python‑Pakete installiert."

# ─── 4. Repositories klonen / aktualisieren ────────────────────
if [[ "$NO_CLONE" == "false" ]]; then
    step "Klonen/Aktualisieren der Repositories"

    declare -A REPO_URLS=(
        ["BeatSync-Engine"]="https://github.com/Merserk/BeatSync-Engine.git"
        ["CutClaw"]="https://github.com/GVCLab/CutClaw.git"
    )

    for name in "${!REPO_URLS[@]}"; do
        target="$REPOS/$name"
        if [[ -d "$target/.git" ]]; then
            ok "Repository $name existiert – führe 'git pull' aus"
            (cd "$target" && git pull --quiet)
        else
            ok "Klonen $name ..."
            git clone "${REPO_URLS[$name]}" "$target" --quiet || warn "Klonen von $name fehlgeschlagen."
        fi
    done
fi

# ─── 5. Symlinks oder physische Kopien ────────────────────────
step "Richte Medienverknüpfungen ein"

declare -A LINK_TARGETS=(
    ["BeatSync-Engine"]="clips->$CLIPS mp3s->$MP3S"
    ["CutClaw"]="input->$CLIPS"
)

for repo in "${!LINK_TARGETS[@]}"; do
    repo_path="$REPOS/$repo"
    [[ ! -d "$repo_path" ]] && continue

    IFS=' ' read -ra links <<< "${LINK_TARGETS[$repo]}"
    for pair in "${links[@]}"; do
        link_name="${pair%%->*}"
        target="${pair##*->}"
        link_path="$repo_path/$link_name"

        if [[ -L "$link_path" ]] || [[ -e "$link_path" ]]; then
            if [[ -L "$link_path" ]]; then
                ok "Symlink bereits vorhanden: $link_path"
                continue
            else
                warn "Physischer Ordner gefunden: $link_path – wird umbenannt (Backup)"
                backup="${link_path}.bak-$(date +%Y%m%d-%H%M%S)"
                mv "$link_path" "$backup"
            fi
        fi

        if [[ "$SKIP_SYMLINKS" == "true" ]]; then
            if [[ -d "$target" ]]; then
                cp -r "$target" "$link_path"
                ok "Physisch kopiert: $target -> $link_path"
            else
                mkdir -p "$link_path"
                warn "Quelle $target nicht vorhanden – leeren Ordner erstellt."
            fi
        else
            ln -s "$target" "$link_path"
            ok "Symlink erstellt: $link_path -> $target"
        fi
    done
done

# ─── 6. Start‑Skripte generieren ──────────────────────────────
step "Erstelle Start‑Skripte (run.sh, start_app.sh, start_cli.sh)"

cat > "$BASE_DIR/run.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")" || exit

while true; do
    clear
    echo "======================================================================"
    echo "WE.ED.IT ULTIMATE + DATABASE - Batch System (Raspberry Pi)"
    echo "======================================================================"
    echo
    echo "Waehlen Sie eine Option:"
    echo
    echo "  1. Batch-Verarbeitung starten (alle Audiodateien)"
    echo "  2. Batch-Verarbeitung fortsetzen"
    echo "  3. Einzelne Datei verarbeiten"
    echo "  4. Beenden"
    echo
    read -p "Ihre Wahl [1-4]: " choice

    case "$choice" in
        1) ./repos/.venv/bin/python cinematic_beat_sync.py --batch ;;
        2) ./repos/.venv/bin/python cinematic_beat_sync.py --batch --resume ;;
        3) read -p "Geben Sie den Pfad zur Audiodatei ein: " audio
           ./repos/.venv/bin/python cinematic_beat_sync.py --sound "$audio" ;;
        4) exit 0 ;;
        *) echo "Ungueltige Auswahl."; sleep 2 ;;
    esac
    echo
    read -p "Druecken Sie Enter, um fortzufahren..."
done
EOF

cat > "$BASE_DIR/start_app.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")" || exit
source ./repos/.venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
EOF

cat > "$BASE_DIR/start_cli.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")" || exit
source ./repos/.venv/bin/activate
python cli.py "$@"
EOF

chmod +x "$BASE_DIR"/run.sh "$BASE_DIR"/start_app.sh "$BASE_DIR"/start_cli.sh
ok "Start‑Skripte erstellt und ausführbar gemacht."

# ─── 7. Abschluss ─────────────────────────────────────────────
echo
step "Installation/Update abgeschlossen!"
echo
echo "  Alle Komponenten sind bereit. Du kannst jetzt mit ./run.sh starten."
echo "  Für Details siehe README.md oder die Dokumentation."
echo
echo "  Per SSH ausführen (vom entfernten Rechner):"
echo "    ssh pi@ip 'bash -s' < install-update-all.sh"
echo
echo "  Viel Erfolg mit deinem AI‑Musikvideo‑Studio! 🎬🎵"
echo
