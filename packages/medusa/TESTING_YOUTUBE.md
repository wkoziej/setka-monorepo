# 🎬 YouTube API Real Testing Guide

Ten przewodnik pokazuje jak przetestować rzeczywiste wgrywanie na YouTube z naszą implementacją Medusa.

## 📋 Przygotowanie

### 1. Uzyskanie YouTube API Credentials

1. **Idź do [Google Cloud Console](https://console.cloud.google.com/)**
2. **Utwórz nowy projekt** lub wybierz istniejący
3. **Włącz YouTube Data API v3:**
   - Idź do "APIs & Services" > "Library"
   - Szukaj "YouTube Data API v3"
   - Kliknij "Enable"

4. **Utwórz OAuth 2.0 Credentials:**
   - Idź do "APIs & Services" > "Credentials"
   - Kliknij "Create Credentials" > "OAuth 2.0 Client IDs"
   - Wybierz "Desktop Application"
   - Nazwij aplikację (np. "Medusa YouTube Test")
   - Pobierz plik JSON

5. **Zapisz credentials:**
   ```bash
   # Przenieś pobrany plik do projektu jako:
   cp ~/Downloads/client_secret_*.json ./client_secrets.json
   ```

### 2. Przygotowanie pliku testowego (opcjonalne)

Dla testów upload'u potrzebujesz małego pliku wideo:

```bash
# Przykład: utwórz krótki test video (wymaga ffmpeg)
ffmpeg -f lavfi -i testsrc=duration=10:size=320x240:rate=1 -pix_fmt yuv420p test_video.mp4

# Lub skopiuj dowolny mały plik MP4
cp /path/to/your/small_video.mp4 ./test_video.mp4
```

## 🧪 Opcje testowania

### Opcja 1: Prosty skrypt (Rekomendowane)

```bash
# Uruchom prosty test script
python test_youtube_simple.py
```

**Co testuje:**
- ✅ OAuth authentication flow
- ✅ Metadata validation
- ✅ Upload simulation
- ✅ Rzeczywisty upload (opcjonalnie)

### Opcja 2: Pytest Integration Tests

```bash
# Uruchom testy integracyjne
python -m pytest tests/integration/test_youtube_real_api.py -v

# Tylko testy bez rzeczywistego upload'u
python -m pytest tests/integration/test_youtube_real_api.py -v -k "not manual"

# Pełne testy manualne (z upload'em)
python -m pytest tests/integration/test_youtube_real_api.py -m manual -v
```

### Opcja 3: Testy jednostkowe (bez API)

```bash
# Uruchom wszystkie testy z mockami
python -m pytest tests/test_uploaders/test_youtube_uploader.py -v

# Szybkie testy (30s limit)
timeout 30s python -m pytest tests/test_uploaders/test_youtube_uploader.py --tb=no -q
```

## 📊 Co można przetestować

### 🔐 Authentication Flow
- OAuth 2.0 browser flow
- Token storage i refresh
- Credential validation

### 📝 Metadata Handling
- Title, description, tags validation
- Privacy settings (private/public/unlisted)
- Category mapping
- Language settings
- Scheduled publishing
- Thumbnail upload

### 📤 Upload Process
- File validation
- Progress reporting
- Resumable uploads
- Error handling
- Retry logic

### 🛡️ Error Scenarios
- Network errors
- Rate limiting
- Invalid credentials
- File format issues
- Quota exceeded

## 🔍 Przykładowe użycie

### Podstawowy test z kodem:

```python
import asyncio
from medusa.uploaders.youtube import YouTubeUploader
from medusa.models import MediaMetadata, PlatformConfig

async def quick_test():
    # Setup
    config = PlatformConfig(
        platform_name="youtube",
        credentials={"client_secrets_file": "client_secrets.json"}
    )
    uploader = YouTubeUploader(config=config)
    
    # Authentication
    await uploader.authenticate()
    
    # Test metadata
    metadata = MediaMetadata(
        title="Test Video",
        description="Test upload",
        privacy="private",
        tags=["test"]
    )
    
    # Upload (jeśli masz plik)
    if os.path.exists("test_video.mp4"):
        result = await uploader.upload_media("test_video.mp4", metadata)
        print(f"Upload ID: {result.upload_id}")
        print(f"URL: {result.media_url}")

# Uruchom
asyncio.run(quick_test())
```

## ⚠️ Ważne uwagi

### 🔒 Bezpieczeństwo
- **Zawsze używaj `privacy="private"`** dla testów
- **Nie commituj** `client_secrets.json` do git
- **Usuń test videos** z YouTube Studio po testach

### 📈 Limity API
- **Quota daily limit:** 10,000 units
- **Upload cost:** ~1,600 units per upload
- **Można uploadować ~6 videos dziennie** w testach

### 🎯 Best Practices
- Używaj małych plików (< 50MB) do testów
- Testuj authentication flow regularnie
- Sprawdzaj różne formaty metadanych
- Testuj error scenarios z mockami

## 🐛 Troubleshooting

### Problem: "Invalid credentials"
```bash
# Sprawdź format pliku
python -c "import json; print(json.load(open('client_secrets.json')))"

# Regeneruj credentials w Google Cloud Console
```

### Problem: "Quota exceeded"
```bash
# Sprawdź usage w Google Cloud Console
# Poczekaj do następnego dnia lub zwiększ quota
```

### Problem: "Upload fails"
```bash
# Sprawdź logi
python test_youtube_simple.py 2>&1 | tee debug.log

# Sprawdź network connectivity
ping youtube.googleapis.com
```

### Problem: "Browser nie otwiera się"
```bash
# Uruchom w środowisku z GUI lub skopiuj URL ręcznie
export DISPLAY=:0  # Linux
```

## 📁 Struktura plików po testach

```
medusa/
├── client_secrets.json          # OAuth credentials (nie commituj!)
├── credentials.json             # Wygenerowane po auth (nie commituj!)
├── test_video.mp4              # Test file (opcjonalny)
├── test_youtube_simple.py      # Prosty test script
├── upload_result.txt           # Wynik ostatniego upload'u
├── last_upload_result.json     # Szczegóły ostatniego upload'u
└── debug.log                   # Logi debug (jeśli potrzebne)
```

## 🎉 Sukces!

Po pomyślnym teście powinieneś zobaczyć:

```
✅ Authentication successful!
✅ Metadata validation passed!
✅ Upload successful!
📺 Video ID: dQw4w9WgXcQ
🔗 Video URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

**Następne kroki:**
1. Sprawdź video w YouTube Studio
2. Usuń test video
3. Przetestuj różne scenariusze
4. Zintegruj z właściwą aplikacją

---

**Potrzebujesz pomocy?** Sprawdź logi lub uruchom testy z debug mode! 