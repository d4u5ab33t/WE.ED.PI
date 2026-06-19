<#
  WE.ED.IT — 1-Click Installer
  Speichern als: INSTALL_WEEDIT.ps1
  Ausführen:     Rechtsklick → "Mit PowerShell ausführen"
                 ODER: pwsh -ExecutionPolicy Bypass -File .\INSTALL_WEEDIT.ps1
#>

$ErrorActionPreference = "Stop"
Clear-Host

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   WE.ED.IT — Cinematic Beat-Sync Installer           " -ForegroundColor Cyan
Write-Host "   BeatSync-Engine × CutClaw hybrid pipeline          " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# ── Arbeitsverzeichnis = Skript-Verzeichnis ──────────────────────────────────
Set-Location $PSScriptRoot

# ── 1. Python prüfen ─────────────────────────────────────────────────────────
Write-Host "[1/6] Prüfe Python..." -ForegroundColor Yellow
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pyCmd) {
    Write-Host "  [FEHLER] Python nicht gefunden." -ForegroundColor Red
    Write-Host "  Bitte installiere Python 3.10+ von https://python.org" -ForegroundColor Red
    Write-Host "  Wichtig: Haken bei 'Add Python to PATH' setzen!" -ForegroundColor Red
    Read-Host "  Drücke ENTER zum Beenden"
    exit 1
}
$pyVersion = & $pyCmd.Source --version 2>&1
Write-Host "  [OK] $pyVersion" -ForegroundColor Green

# ── 2. FFmpeg prüfen ─────────────────────────────────────────────────────────
Write-Host "[2/6] Prüfe FFmpeg + FFprobe..." -ForegroundColor Yellow
$ffmpegOk  = Get-Command ffmpeg  -ErrorAction SilentlyContinue
$ffprobeOk = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $ffmpegOk -or -not $ffprobeOk) {
    Write-Host "  [WARNUNG] FFmpeg/FFprobe nicht im PATH." -ForegroundColor Red
    Write-Host "  Schnellinstall via Winget:" -ForegroundColor Yellow
    Write-Host "    winget install Gyan.FFmpeg" -ForegroundColor White
    Write-Host "  Oder manuell: https://ffmpeg.org/download.html" -ForegroundColor White
    Write-Host "  Dann PATH neu laden und diesen Installer nochmal ausführen." -ForegroundColor White
    $cont = Read-Host "  Trotzdem fortfahren? (j/N)"
    if ($cont -ne "j" -and $cont -ne "J") { exit 1 }
} else {
    $ffVer = & ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host "  [OK] $ffVer" -ForegroundColor Green
}

# ── 3. Virtuelle Umgebung anlegen ────────────────────────────────────────────
Write-Host "[3/6] Virtuelle Umgebung (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".\.venv")) {
    & $pyCmd.Source -m venv .venv
    Write-Host "  [OK] .venv angelegt" -ForegroundColor Green
} else {
    Write-Host "  [OK] .venv bereits vorhanden" -ForegroundColor Green
}

$pip    = ".\.venv\Scripts\pip.exe"
$python = ".\.venv\Scripts\python.exe"

# ── 4. Pip upgraden & Pakete installieren ────────────────────────────────────
Write-Host "[4/6] Installiere Python-Pakete..." -ForegroundColor Yellow

& $pip install --upgrade pip --quiet

$packages = @(
    "numpy",
    "scipy",
    "librosa",
    "mutagen",
    "scikit-learn",
    "tqdm",
    "audioop-lts",
    "ffmpeg-python",
    "opencv-python",
    "moviepy",
    "streamlit",
    "requests"
)

foreach ($pkg in $packages) {
    Write-Host "    pip install $pkg ..." -NoNewline
    try {
        & $pip install $pkg --quiet 2>$null
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " WARNUNG (nicht kritisch)" -ForegroundColor Yellow
    }
}

Write-Host "    Prüfe numpy-Kompatibilität..." -NoNewline
$npCheck = & $python -c "import numpy; print(numpy.__version__)" 2>&1
Write-Host " numpy $npCheck" -ForegroundColor Green

# ── 5. Verzeichnisse anlegen ─────────────────────────────────────────────────
Write-Host "[5/6] Verzeichnisstruktur anlegen..." -ForegroundColor Yellow
$dirs = @("Sound", "Clips", "done", "proxies", "core", "render", "cache")
foreach ($d in $dirs) {
    if (-not (Test-Path ".\$d")) {
        New-Item -ItemType Directory -Path ".\$d" | Out-Null
        Write-Host "  [+] .\$d angelegt" -ForegroundColor DarkGray
    } else {
        Write-Host "  [~] .\$d bereits vorhanden" -ForegroundColor DarkGray
    }
}

# ── 6. run_weedit.ps1 Launcher schreiben ─────────────────────────────────────
Write-Host "[6/6] Erstelle Launcher run_weedit.ps1..." -ForegroundColor Yellow

$launcherContent = @'
<#
  WE.ED.IT — Launcher
  Legt automatisch deine Pfade fest und startet weedit.py in der venv.
  Passe SOUND_DIR / CLIP_DIR / OUTPUT_DIR unten nach Bedarf an.
#>

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

# ── Pfade konfigurieren ──────────────────────────────────────────────────────
$SOUND_DIR  = ".\Sound"
$CLIP_DIR   = ".\Clips"
$OUTPUT_DIR = ".\done"

# ── Starten ──────────────────────────────────────────────────────────────────
Write-Host "Starte WE.ED.IT..." -ForegroundColor Cyan
Write-Host "Sound : $SOUND_DIR" -ForegroundColor DarkGray
Write-Host "Clips : $CLIP_DIR"  -ForegroundColor DarkGray
Write-Host "Output: $OUTPUT_DIR" -ForegroundColor DarkGray
Write-Host ""

& ".\.venv\Scripts\python.exe" ".\cinematic_beat_sync.py" `
    --sound "$SOUND_DIR" `
    --clips "$CLIP_DIR"  `
    --out   "$OUTPUT_DIR"

Write-Host ""
Write-Host "Fertig. Ergebnisse in: $OUTPUT_DIR" -ForegroundColor Green
Read-Host "Drücke ENTER zum Schließen"
'@

$launcherContent | Out-File -FilePath ".\run_weedit.ps1" -Encoding utf8
Write-Host "  [OK] run_weedit.ps1 erstellt" -ForegroundColor Green

# ── Erfolgs-Banner ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "   INSTALLATION ERFOLGREICH ABGESCHLOSSEN!            " -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  So startest du WE.ED.IT:" -ForegroundColor White
Write-Host ""
Write-Host "  OPTION A — Launcher (empfohlen):" -ForegroundColor Cyan
Write-Host "    .\run_weedit.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  OPTION B — Direkt mit eigenen Pfaden:" -ForegroundColor Cyan
Write-Host "    .\.venv\Scripts\python.exe .\cinematic_beat_sync.py \" -ForegroundColor White
Write-Host "        --sound D:\Oidasheim\NFOs\mp3s \" -ForegroundColor White
Write-Host "        --clips D:\Oidasheim\NFOs\Clips \" -ForegroundColor White
Write-Host "        --out   D:\Oidasheim\NFOs\done"  -ForegroundColor White
Write-Host ""
Write-Host "  OPTION C — Alle Optionen anzeigen:" -ForegroundColor Cyan
Write-Host "    .\.venv\Scripts\python.exe .\cinematic_beat_sync.py --help" -ForegroundColor White
Write-Host ""
Write-Host "  Fertige Videos landen in: .\done  (oder --out Pfad)" -ForegroundColor Yellow
Write-Host "  Versionsinkrement ist aktiv — kein Überschreiben!" -ForegroundColor Yellow
Write-Host ""
Write-Host "  GPU erkannt? h264_nvenc wird auto-gewählt." -ForegroundColor DarkGray
Write-Host "  4K-Clips? Proxy-Modus ist Standard (--no-proxy zum Deaktivieren)" -ForegroundColor DarkGray
Write-Host ""

Read-Host "Drücke ENTER zum Schließen"
