#!/usr/bin/env python3
"""
Przykładowy skrypt do bezpośredniego importu sesji OBS Canvas do Blender VSE.

INSTRUKCJA UŻYCIA:
1. Otwórz Blender
2. Przejdź do workspace "Scripting"
3. Utwórz nowy text file (New)
4. Wklej ten kod
5. Zmień SESSION_PATH na ścieżkę do swojej sesji
6. Uruchom skrypt (Alt+P lub przycisk "Run Script")

PRZYKŁAD SESJI: /home/wojtas/Wideo/obs/2025-07-08 19-38-18
"""

from pathlib import Path

import bpy

# ==========================================
# KONFIGURACJA SESJI - ZMIEŃ TUTAJ ŚCIEŻKĘ
# ==========================================
SESSION_PATH = Path("/home/wojtas/Wideo/obs/2025-07-08 19-38-18")

# Automatyczne ścieżki na podstawie sesji
EXTRACTED_DIR = SESSION_PATH / "extracted"
BLENDER_DIR = SESSION_PATH / "blender"

# Pliki wideo (w kolejności alfabetycznej)
video_files = [
    EXTRACTED_DIR / "RPI_FRONT.mp4",
    EXTRACTED_DIR / "RPI_RIGHT.mp4",
    EXTRACTED_DIR / "Urządzenie przechwytujące obraz (V4L2) 2.mp4",
    EXTRACTED_DIR / "Urządzenie przechwytujące obraz (V4L2) 3.mp4",
    EXTRACTED_DIR / "Urządzenie przechwytujące obraz (V4L2).mp4",
]

# Główny plik audio
main_audio = EXTRACTED_DIR / "Przechwytywanie wejścia dźwięku (PulseAudio).m4a"

# Pliki wyjściowe
output_blend = BLENDER_DIR / "projekt.blend"
render_output = BLENDER_DIR / "render" / "projekt.mp4"

# Ustawienia projektu
RESOLUTION_X = 1280
RESOLUTION_Y = 720
FPS = 30


def setup_vse():
    """Konfiguruje projekt Blender VSE dla sesji OBS Canvas."""

    print("=== Import sesji OBS Canvas do Blender VSE ===")
    print(f"Sesja: {SESSION_PATH}")
    print()

    # Sprawdź czy sesja istnieje
    if not SESSION_PATH.exists():
        print(f"❌ Błąd: Sesja nie istnieje: {SESSION_PATH}")
        return False

    if not EXTRACTED_DIR.exists():
        print(f"❌ Błąd: Katalog extracted nie istnieje: {EXTRACTED_DIR}")
        return False

    # 1. Wyczyść domyślną scenę
    bpy.ops.wm.read_factory_settings(use_empty=True)
    print("✓ Wyczyszczono domyślną scenę")

    # 2. Utwórz sequence editor
    if not bpy.context.scene.sequence_editor:
        bpy.context.scene.sequence_editor_create()
    print("✓ Utworzono sequence editor")

    # 3. Ustawienia sceny
    scene = bpy.context.scene
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.fps = FPS
    scene.frame_start = 1
    print(f"✓ Ustawiono parametry sceny ({RESOLUTION_X}x{RESOLUTION_Y}, {FPS}fps)")

    sequencer = scene.sequence_editor

    # 4. Dodaj główny plik audio (kanał 1)
    if main_audio.exists():
        try:
            sequencer.sequences.new_sound(
                name="Main_Audio", filepath=str(main_audio), channel=1, frame_start=1
            )
            print(f"✓ Dodano audio: {main_audio.name} (kanał 1)")
        except Exception as e:
            print(f"❌ Błąd dodawania audio: {e}")
    else:
        print(f"⚠️  Plik audio nie istnieje: {main_audio}")

    # 5. Dodaj pliki wideo (kanały 2-6)
    added_videos = 0
    for i, video_file in enumerate(video_files):
        if video_file.exists():
            try:
                sequencer.sequences.new_movie(
                    name=f"Video_{i + 1}",
                    filepath=str(video_file),
                    channel=i + 2,  # Kanały 2-6
                    frame_start=1,
                )
                print(f"✓ Dodano wideo {i + 1}: {video_file.name} (kanał {i + 2})")
                added_videos += 1
            except Exception as e:
                print(f"❌ Błąd dodawania wideo {video_file}: {e}")
        else:
            print(f"⚠️  Plik wideo nie istnieje: {video_file}")

    if added_videos == 0:
        print("❌ Błąd: Nie dodano żadnych plików wideo")
        return False

    # 6. Ustawienia renderowania
    render = scene.render
    render.image_settings.file_format = "FFMPEG"
    render.ffmpeg.format = "MPEG4"
    render.ffmpeg.codec = "H264"
    render.ffmpeg.constant_rate_factor = "HIGH"
    render.filepath = str(render_output)
    print("✓ Skonfigurowano ustawienia renderowania (MP4, H.264)")

    # 7. Ustaw długość timeline
    if sequencer.sequences:
        max_frame_end = max(seq.frame_final_end for seq in sequencer.sequences)
        scene.frame_end = max_frame_end
        print(f"✓ Ustawiono timeline: {max_frame_end} klatek")

    # 8. Zapisz projekt
    try:
        BLENDER_DIR.mkdir(parents=True, exist_ok=True)
        (BLENDER_DIR / "render").mkdir(exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
        print(f"✓ Zapisano projekt: {output_blend}")
    except Exception as e:
        print(f"❌ Błąd zapisywania projektu: {e}")
        return False

    print()
    print("=== Import zakończony sukcesem! ===")
    print(f"📁 Projekt: {output_blend}")
    print(f"🎬 Renderowanie: {render_output}")
    print("🎵 Audio: kanał 1")
    print(f"🎥 Wideo: kanały 2-{added_videos + 1}")
    print()
    print("💡 Wskazówki:")
    print("- Przejdź do workspace 'Video Editing' aby edytować")
    print("- Użyj Space aby odtworzyć timeline")
    print("- Ctrl+F12 aby rozpocząć renderowanie")

    return True


def list_session_files():
    """Wyświetla listę plików w sesji."""
    print("=== Pliki w sesji ===")

    if not EXTRACTED_DIR.exists():
        print(f"❌ Katalog extracted nie istnieje: {EXTRACTED_DIR}")
        return

    print(f"📁 Katalog: {EXTRACTED_DIR}")
    print()

    # Lista plików audio
    audio_files = list(EXTRACTED_DIR.glob("*.m4a"))
    if audio_files:
        print("🎵 Pliki audio:")
        for audio in sorted(audio_files):
            marker = "✓" if audio == main_audio else " "
            print(f"  {marker} {audio.name}")
        print()

    # Lista plików wideo
    video_extensions = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"]
    all_videos = []
    for ext in video_extensions:
        all_videos.extend(EXTRACTED_DIR.glob(f"*{ext}"))

    if all_videos:
        print("🎥 Pliki wideo:")
        for video in sorted(all_videos):
            marker = "✓" if video in video_files else " "
            print(f"  {marker} {video.name}")
        print()


# ==========================================
# URUCHOMIENIE SKRYPTU
# ==========================================

if __name__ == "__main__":
    # Pokaż pliki w sesji
    list_session_files()

    # Uruchom import
    success = setup_vse()

    if success:
        print("✅ Sesja zaimportowana pomyślnie!")
    else:
        print("❌ Błąd podczas importu sesji")
