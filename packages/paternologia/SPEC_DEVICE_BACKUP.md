# ABOUTME: Specyfikacja backupu i restore dla zestawu urządzeń MIDI
# ABOUTME: Obejmuje: Nektar Pacer, BOSS RC-600, Elektron Model:Samples, Arturia MicroFreak

# Specyfikacja: Backup i Restore urządzeń MIDI

## 1. Przegląd zestawu

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ZESTAW MIDI - PATERNOLOGIA                      │
├─────────────────┬───────────────┬─────────────────┬─────────────────────┤
│  Nektar Pacer   │  BOSS RC-600  │ Model:Samples   │  Arturia MicroFreak │
│  (kontroler)    │  (looper)     │ (groovebox)     │  (syntezator)       │
├─────────────────┼───────────────┼─────────────────┼─────────────────────┤
│  ✅ amidi SysEx │  ✅ USB Mass  │ ✅ Elektroid    │  ⚠️ Ograniczone     │
│                 │    Storage    │    CLI          │                     │
└─────────────────┴───────────────┴─────────────────┴─────────────────────┘
```

### Porty MIDI na systemie (przykład)

```bash
$ amidi -l
Dir Device    Name
IO  hw:7,0,0  RC-600 MIDI 1
IO  hw:8,0,0  PACER MIDI1
IO  hw:8,0,1  PACER MIDI2
```

**Uwaga**: Numery portów (`hw:X,Y,Z`) mogą się zmieniać przy każdym podłączeniu USB.

---

## 2. Nektar Pacer

### 2.1 Metoda: amidi + SysEx

Pacer obsługuje pełny protokół SysEx do backup/restore.

### 2.2 Backup

```bash
# Wykryj port Pacera
PACER_PORT=$(amidi -l | grep PACER | head -1 | awk '{print $2}')

# Full dump - wysyła request i odbiera odpowiedź
amidi -p $PACER_PORT -S "F0 00 01 77 7F 02 7F F7" \
      -r ~/backup/pacer_$(date +%Y%m%d_%H%M%S).syx -t 10
```

### 2.3 Restore

```bash
# Wyślij zapisany dump do Pacera (CRITICAL: --sysex-interval=20!)
amidi -p $PACER_PORT --sysex-interval=20 -s ~/backup/pacer_20241225_120000.syx
```

### 2.4 Co jest backupowane

| Element | Backup | Uwagi |
|---------|--------|-------|
| Presety (A1-D6) | ✅ | Wszystkie 24 presety |
| Nazwy presetów | ✅ | 7 znaków max |
| Konfiguracja przycisków | ✅ | SW1-SW6 + FS1-FS4 |
| Kroki akcji | ✅ | Do 6 kroków per kontroler |
| Kolory LED | ✅ | Aktywny/nieaktywny |
| Ustawienia globalne | ✅ | MIDI channel, itp. |

### 2.5 Źródła

- Szczegóły: `SPEC_PACER_BRIDGE.md`
- Parser SysEx: `workspace/pacer_programming/pacer-editor/src/pacer/sysex.js`

---

## 3. BOSS RC-600

### 3.1 Metoda: USB Mass Storage

RC-600 montuje się jako urządzenie pamięci masowej. **Brak publicznej dokumentacji SysEx**.

### 3.2 Przygotowanie

```bash
# RC-600 musi być w trybie STORAGE
# Menu: SYSTEM → USB → MODE → STORAGE

# Sprawdź czy zamontowane
lsblk | grep -i boss
# lub
ls /media/$USER/
```

### 3.3 Backup

```bash
# Znajdź punkt montowania
RC600_MOUNT=$(findmnt -rn -S LABEL=RC-600 -o TARGET 2>/dev/null || \
              ls -d /media/$USER/RC-600* 2>/dev/null | head -1)

if [ -z "$RC600_MOUNT" ]; then
    echo "RC-600 nie jest zamontowane!"
    exit 1
fi

# Backup całego folderu ROLAND
BACKUP_DIR=~/backup/rc600_$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
cp -r "$RC600_MOUNT/ROLAND" "$BACKUP_DIR/"

# Weryfikacja
du -sh "$BACKUP_DIR/ROLAND"
echo "Backup zapisany: $BACKUP_DIR"
```

### 3.4 Restore

```bash
# UWAGA: To nadpisuje WSZYSTKIE dane na RC-600!
BACKUP_DIR=~/backup/rc600_20241225_120000
RC600_MOUNT=/media/$USER/RC-600

# Opcja 1: Pełny restore
rm -rf "$RC600_MOUNT/ROLAND"
cp -r "$BACKUP_DIR/ROLAND" "$RC600_MOUNT/"
sync

# Opcja 2: Selektywny restore (tylko konkretny Memory)
# Struktura: ROLAND/DATA/MEMORY/MEM001/ ... MEM099/
cp -r "$BACKUP_DIR/ROLAND/DATA/MEMORY/MEM042" "$RC600_MOUNT/ROLAND/DATA/MEMORY/"
sync
```

### 3.5 Struktura folderu ROLAND

```
ROLAND/
├── DATA/
│   ├── MEMORY/
│   │   ├── MEM001/          # Memory 1
│   │   │   ├── TRACK1.WAV   # Loop Track 1
│   │   │   ├── TRACK2.WAV
│   │   │   └── ...
│   │   ├── MEM002/
│   │   └── ... (do MEM099)
│   ├── SYSTEM/              # Ustawienia systemowe
│   └── ASSIGN/              # Przypisania MIDI
└── WAVE/                    # Importowane sample (rhythm, one-shot)
```

### 3.6 Co jest backupowane

| Element | Backup | Uwagi |
|---------|--------|-------|
| Loop audio (WAV) | ✅ | Główna zawartość |
| Memory settings | ✅ | Tempo, efekty, przypisania |
| System settings | ✅ | Globalne ustawienia |
| MIDI Assign | ✅ | Mapowania CC/PC |
| Rhythm patterns | ✅ | Wbudowane + custom |

### 3.7 Alternatywa: RC-600 Editor (Windows/Mac)

Jeśli potrzebujesz edycji wizualnej, rozważ [RC-600 Editor](https://www.rc600editor.com/) przez Wine lub VM.

---

## 4. Elektron Model:Samples

### 4.1 Metoda: Elektroid CLI

[Elektroid](https://github.com/dagargo/elektroid) to open-source narzędzie z pełnym wsparciem dla Model:Samples.

### 4.2 Instalacja

```bash
# Opcja 1: Z pakietów (jeśli dostępne)
sudo apt install elektroid

# Opcja 2: Flatpak
flatpak install flathub io.github.dagargo.Elektroid

# Opcja 3: Kompilacja ze źródeł
sudo apt install automake libtool build-essential libasound2-dev \
    libgtk-3-dev libpulse-dev libsndfile1-dev libsamplerate0-dev \
    autopoint gettext zlib1g-dev libjson-glib-dev libzip-dev

git clone https://github.com/dagargo/elektroid ~/tools/elektroid
cd ~/tools/elektroid
autoreconf --install
./configure
make
sudo make install
```

### 4.3 Weryfikacja połączenia

```bash
# Lista urządzeń
elektroid-cli ld

# Powinno pokazać:
# 0: Elektron Model:Samples @ hw:X,0,0
```

### 4.4 Backup

```bash
# Utwórz katalog backup
BACKUP_DIR=~/backup/model_samples_$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"/{data,samples}

# Backup projektów/patternów (SysEx)
elektroid-cli elektron:data:rdl "$BACKUP_DIR/data/"

# Backup sampli (osobno!)
elektroid-cli elektron:sample:dl -r "$BACKUP_DIR/samples/" 0:/

echo "Backup zapisany: $BACKUP_DIR"
```

### 4.5 Restore

```bash
BACKUP_DIR=~/backup/model_samples_20241225_120000

# Restore projektów/patternów
elektroid-cli elektron:data:ul "$BACKUP_DIR/data/"

# Restore sampli
elektroid-cli elektron:sample:ul -r "$BACKUP_DIR/samples/" 0:/
```

### 4.6 Co jest backupowane

| Element | Backup | Metoda |
|---------|--------|--------|
| Projekty | ✅ | `elektron:data:rdl` |
| Patterny | ✅ | `elektron:data:rdl` |
| Sample Pool | ✅ | `elektron:sample:dl` |
| +Drive samples | ✅ | `elektron:sample:dl` |
| Ustawienia globalne | ⚠️ | Wymaga osobnego dumpa |

### 4.7 Alternatywna metoda: amidi + SysEx (zaawansowane)

```bash
# Model:Samples w trybie SysEx receive
# Menu: SETTINGS → SYSEX DUMP → SYSEX RECEIVE

# Odbierz dump
MS_PORT=$(amidi -l | grep "Model:Samples" | awk '{print $2}')
amidi -p $MS_PORT -r ~/backup/ms_sysex_$(date +%Y%m%d).syx -t 30

# UWAGA: To backup TYLKO projektów/patternów, BEZ sampli!
```

---

## 5. Arturia MicroFreak

### 5.1 Status: Ograniczone wsparcie Linux

Arturia nie udostępnia MIDI Control Center dla Linux ani publicznej dokumentacji SysEx.

### 5.2 Dostępne opcje

#### Opcja A: MicroFreak Reader (tylko odczyt)

Web-based tool do **podglądu** presetów (nie można wysyłać do urządzenia).

```bash
# Otwórz w przeglądarce
xdg-open https://studiocode.dev/doc/microfreak-reader/

# Podłącz MicroFreak przez USB
# Kliknij "Connect" w aplikacji webowej
# Możesz zobaczyć presety, ale NIE możesz ich edytować ani wysyłać
```

#### Opcja B: amidi (eksperymentalne)

```bash
# Znajdź port MicroFreak
MF_PORT=$(amidi -l | grep -i "microfreak\|arturia" | awk '{print $2}')

# Próba odbioru dumpa (nieudokumentowane!)
# MicroFreak może wymagać wysłania specyficznego SysEx request
amidi -p $MF_PORT -r ~/backup/microfreak_raw.syx -t 30

# W tym czasie na MicroFreak:
# Utility → MIDI → Preset → Send (jeśli dostępne)
```

**Uwaga**: Format pliku może nie być kompatybilny z MIDI Control Center.

#### Opcja C: Wine + MIDI Control Center

```bash
# Instalacja Wine
sudo apt install wine winetricks

# Pobierz MIDI Control Center z arturia.com
# Zainstaluj przez Wine
wine ~/Downloads/Arturia_Software_Center.exe

# Konfiguracja MIDI w Wine może wymagać wineasio lub podobnych
```

#### Opcja D: VM z Windows/Mac

Najbardziej niezawodna opcja dla pełnego backupu.

### 5.3 Co można backupować

| Element | Linux natywnie | Wine/VM |
|---------|----------------|---------|
| Presety (view) | ⚠️ MicroFreak Reader | ✅ |
| Presety (backup) | ❌ | ✅ |
| Presety (restore) | ❌ | ✅ |
| Sekwencje | ❌ | ✅ |
| Ustawienia globalne | ❌ | ✅ |

### 5.4 Przyszłość

Społeczność pracuje nad reverse-engineeringiem protokołu SysEx:
- [Forum Arturia - SysEx dump request](https://legacy-forum.arturia.com/index.php?topic=102038.0)
- [GitHub - microfreak-reader](https://github.com/francoisgeorgy/microfreak-reader)

---

## 6. Skrypt zbiorczy: backup_all.sh

```bash
#!/bin/bash
# ABOUTME: Skrypt do backupu wszystkich urządzeń MIDI
# ABOUTME: Użycie: ./backup_all.sh [--dry-run]

set -e

BACKUP_ROOT=~/backup/midi_$(date +%Y%m%d_%H%M%S)
DRY_RUN=${1:-""}

log() { echo "[$(date +%H:%M:%S)] $1"; }
run() {
    if [ "$DRY_RUN" = "--dry-run" ]; then
        echo "[DRY-RUN] $@"
    else
        "$@"
    fi
}

mkdir -p "$BACKUP_ROOT"
log "Backup directory: $BACKUP_ROOT"

# ═══════════════════════════════════════════════════════════════════════
# 1. NEKTAR PACER
# ═══════════════════════════════════════════════════════════════════════
log "=== Nektar Pacer ==="
PACER_PORT=$(amidi -l | grep -i pacer | head -1 | awk '{print $2}')

if [ -n "$PACER_PORT" ]; then
    log "Pacer found at $PACER_PORT"
    run amidi -p "$PACER_PORT" \
        -S "F0 00 01 77 7F 02 7F F7" \
        -r "$BACKUP_ROOT/pacer.syx" -t 10
    log "Pacer backup: OK"
else
    log "Pacer: NOT CONNECTED"
fi

# ═══════════════════════════════════════════════════════════════════════
# 2. BOSS RC-600
# ═══════════════════════════════════════════════════════════════════════
log "=== BOSS RC-600 ==="
RC600_MOUNT=$(ls -d /media/$USER/RC-600* 2>/dev/null | head -1 || true)

if [ -d "$RC600_MOUNT/ROLAND" ]; then
    log "RC-600 mounted at $RC600_MOUNT"
    run cp -r "$RC600_MOUNT/ROLAND" "$BACKUP_ROOT/rc600_ROLAND"
    log "RC-600 backup: OK ($(du -sh "$BACKUP_ROOT/rc600_ROLAND" 2>/dev/null | cut -f1))"
else
    log "RC-600: NOT MOUNTED (przełącz na tryb STORAGE)"
fi

# ═══════════════════════════════════════════════════════════════════════
# 3. ELEKTRON MODEL:SAMPLES
# ═══════════════════════════════════════════════════════════════════════
log "=== Elektron Model:Samples ==="

if command -v elektroid-cli &> /dev/null; then
    MS_DEVICE=$(elektroid-cli ld 2>/dev/null | grep -i "model" | head -1 || true)

    if [ -n "$MS_DEVICE" ]; then
        log "Model:Samples found: $MS_DEVICE"
        mkdir -p "$BACKUP_ROOT/model_samples"/{data,samples}

        run elektroid-cli elektron:data:rdl "$BACKUP_ROOT/model_samples/data/"
        log "Model:Samples data backup: OK"

        run elektroid-cli elektron:sample:dl -r "$BACKUP_ROOT/model_samples/samples/" 0:/
        log "Model:Samples samples backup: OK"
    else
        log "Model:Samples: NOT CONNECTED"
    fi
else
    log "Model:Samples: elektroid-cli NOT INSTALLED"
    log "  Install: flatpak install flathub io.github.dagargo.Elektroid"
fi

# ═══════════════════════════════════════════════════════════════════════
# 4. ARTURIA MICROFREAK
# ═══════════════════════════════════════════════════════════════════════
log "=== Arturia MicroFreak ==="
MF_PORT=$(amidi -l | grep -i "microfreak\|arturia" | head -1 | awk '{print $2}' || true)

if [ -n "$MF_PORT" ]; then
    log "MicroFreak found at $MF_PORT"
    log "⚠️  MicroFreak backup wymaga MIDI Control Center (Windows/Mac)"
    log "    Alternatywa: https://studiocode.dev/doc/microfreak-reader/ (tylko podgląd)"

    # Eksperymentalny dump (może nie działać poprawnie)
    # run amidi -p "$MF_PORT" -r "$BACKUP_ROOT/microfreak_raw.syx" -t 10
else
    log "MicroFreak: NOT CONNECTED"
fi

# ═══════════════════════════════════════════════════════════════════════
# PODSUMOWANIE
# ═══════════════════════════════════════════════════════════════════════
echo ""
log "═══════════════════════════════════════════"
log "BACKUP COMPLETE"
log "═══════════════════════════════════════════"
log "Location: $BACKUP_ROOT"
ls -la "$BACKUP_ROOT"
du -sh "$BACKUP_ROOT"
```

---

## 7. Skrypt restore: restore_device.sh

```bash
#!/bin/bash
# ABOUTME: Skrypt do przywracania backupu konkretnego urządzenia
# ABOUTME: Użycie: ./restore_device.sh <device> <backup_dir>

set -e

DEVICE=$1
BACKUP_DIR=$2

usage() {
    echo "Użycie: $0 <device> <backup_dir>"
    echo "  device: pacer | rc600 | model_samples"
    echo "  backup_dir: ścieżka do katalogu z backupem"
    echo ""
    echo "Przykład: $0 pacer ~/backup/midi_20241225_120000"
    exit 1
}

[ -z "$DEVICE" ] || [ -z "$BACKUP_DIR" ] && usage

log() { echo "[$(date +%H:%M:%S)] $1"; }

case $DEVICE in
    pacer)
        log "Restoring Pacer from $BACKUP_DIR/pacer.syx"
        PACER_PORT=$(amidi -l | grep -i pacer | head -1 | awk '{print $2}')
        [ -z "$PACER_PORT" ] && { log "ERROR: Pacer not connected"; exit 1; }
        # CRITICAL: --sysex-interval=20 is required for reliable transfer!
        amidi -p "$PACER_PORT" --sysex-interval=20 -s "$BACKUP_DIR/pacer.syx"
        log "Pacer restore: OK"
        ;;

    rc600)
        log "Restoring RC-600 from $BACKUP_DIR/rc600_ROLAND"
        RC600_MOUNT=$(ls -d /media/$USER/RC-600* 2>/dev/null | head -1)
        [ -z "$RC600_MOUNT" ] && { log "ERROR: RC-600 not mounted"; exit 1; }

        echo "⚠️  UWAGA: To NADPISZE wszystkie dane na RC-600!"
        read -p "Kontynuować? (yes/no): " confirm
        [ "$confirm" != "yes" ] && { log "Anulowano"; exit 0; }

        rm -rf "$RC600_MOUNT/ROLAND"
        cp -r "$BACKUP_DIR/rc600_ROLAND" "$RC600_MOUNT/ROLAND"
        sync
        log "RC-600 restore: OK"
        ;;

    model_samples)
        log "Restoring Model:Samples from $BACKUP_DIR/model_samples"

        echo "⚠️  UWAGA: To NADPISZE dane na Model:Samples!"
        read -p "Kontynuować? (yes/no): " confirm
        [ "$confirm" != "yes" ] && { log "Anulowano"; exit 0; }

        elektroid-cli elektron:data:ul "$BACKUP_DIR/model_samples/data/"
        log "Data restore: OK"

        elektroid-cli elektron:sample:ul -r "$BACKUP_DIR/model_samples/samples/" 0:/
        log "Samples restore: OK"
        ;;

    *)
        log "ERROR: Nieznane urządzenie: $DEVICE"
        usage
        ;;
esac
```

---

## 8. Struktura katalogów backup

```
~/backup/
├── midi_20241225_120000/           # Zbiorczy backup
│   ├── pacer.syx                   # Nektar Pacer (SysEx)
│   ├── rc600_ROLAND/               # BOSS RC-600 (folder)
│   │   └── ROLAND/
│   │       ├── DATA/
│   │       └── WAVE/
│   └── model_samples/              # Elektron Model:Samples
│       ├── data/                   # Projekty/patterny
│       └── samples/                # Audio samples
│
├── pacer_20241220_090000.syx       # Pojedynczy backup Pacer
├── rc600_20241218_150000/          # Pojedynczy backup RC-600
└── model_samples_20241215_180000/  # Pojedynczy backup M:S
```

---

## 9. Harmonogram backupów (cron)

```bash
# Edytuj crontab
crontab -e

# Cotygodniowy backup (niedziela 3:00, gdy urządzenia podłączone)
0 3 * * 0 /home/wojtas/scripts/backup_all.sh >> /home/wojtas/backup/backup.log 2>&1
```

---

## 10. Integracja z Paternologia (przyszłość)

### 10.1 API endpoint do backupu

```python
# src/paternologia/routers/backup.py

from fastapi import APIRouter
from fastapi.responses import FileResponse
import subprocess
from pathlib import Path

router = APIRouter(prefix="/backup", tags=["backup"])

@router.post("/pacer")
async def backup_pacer():
    """Wykonaj backup Pacera i zwróć plik .syx"""
    output_file = Path(f"/tmp/pacer_{datetime.now():%Y%m%d_%H%M%S}.syx")

    result = subprocess.run([
        "amidi", "-p", detect_pacer_port(),
        "-S", "F0 00 01 77 7F 02 7F F7",
        "-r", str(output_file), "-t", "10"
    ], capture_output=True)

    if result.returncode != 0:
        raise HTTPException(500, "Backup failed")

    return FileResponse(output_file, filename=output_file.name)

@router.get("/status")
async def backup_status():
    """Sprawdź dostępność urządzeń do backupu"""
    return {
        "pacer": detect_pacer_port() is not None,
        "rc600": Path("/media").glob("*/RC-600*") != [],
        "model_samples": check_elektroid_device(),
        "microfreak": detect_microfreak_port() is not None
    }
```

### 10.2 UI w Paternologii

```html
<!-- templates/backup.html -->
<div class="backup-panel">
    <h2>Device Backup</h2>

    <div class="device-status">
        <div hx-get="/backup/status" hx-trigger="load, every 5s">
            Loading device status...
        </div>
    </div>

    <div class="backup-actions">
        <button hx-post="/backup/pacer" hx-swap="none"
                hx-on::after-request="downloadFile(event)">
            Backup Pacer
        </button>
        <!-- ... inne urządzenia -->
    </div>
</div>
```

---

## 11. Troubleshooting

### Problem: amidi nie widzi urządzeń

```bash
# Sprawdź czy ALSA widzi urządzenia
aplay -l
arecord -l

# Sprawdź uprawnienia
ls -la /dev/snd/

# Dodaj użytkownika do grupy audio
sudo usermod -a -G audio $USER
# Wyloguj i zaloguj ponownie
```

### Problem: RC-600 nie montuje się

```bash
# Sprawdź dmesg
dmesg | tail -20

# RC-600 musi być w trybie STORAGE
# Na RC-600: SYSTEM → USB → MODE → STORAGE

# Ręczne montowanie
sudo mkdir -p /mnt/rc600
sudo mount /dev/sdX1 /mnt/rc600
```

### Problem: Elektroid nie widzi Model:Samples

```bash
# Sprawdź czy urządzenie jest w trybie USB
# Na M:S: SETTINGS → USB CONFIG → USB MIDI

# Sprawdź uprawnienia
ls -la /dev/snd/
sudo usermod -a -G audio $USER

# Debug
RUST_LOG=debug elektroid-cli ld
```

---

## 12. Źródła i dokumentacja

### Oficjalne

- [BOSS RC-600 Manual](https://www.boss.info/global/support/by_product/rc-600/owners_manuals/)
- [Elektron Model:Samples Manual](https://www.elektron.se/support-downloads/modelsamples)
- [Arturia MicroFreak Resources](https://www.arturia.com/products/hardware-synths/microfreak/resources)

### Narzędzia

- [Elektroid (GitHub)](https://github.com/dagargo/elektroid) - Linux transfer tool
- [RC-600 Editor](https://www.rc600editor.com/) - Nieoficjalny edytor (Win/Mac)
- [MicroFreak Reader](https://github.com/francoisgeorgy/microfreak-reader) - Web viewer
- [amidi man page](https://linux.die.net/man/1/amidi) - ALSA MIDI CLI

### Społeczność

- [Elektronauts - SysEx Backup](https://www.elektronauts.com/t/sysex-project-backup/143648)
- [Elektronauts - Elektroid](https://www.elektronauts.com/t/elektroid-a-gnu-linux-transfer-application-for-elektron-devices/108761)
