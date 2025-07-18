# Specyfikacja: Odtwarzanie Wideo w fermata

## Cel

Umożliwienie użytkownikowi odtwarzania plików wideo z poziomu aplikacji fermata, z opcjami odtwarzania w zewnętrznym odtwarzaczu oraz wbudowanym web playerze.

## Analiza Obecnej Architektury

### Struktura Plików Wideo
Każde nagranie zawiera pliki wideo w standardowej strukturze:
```
recording_name/
├── recording_name.mkv       # Główne nagranie OBS
├── metadata.json           # Metadane sceny
├── extracted/              # Wyekstraktowane źródła
│   ├── source1.mp4         # Poszczególne źródła wideo
│   └── source2.m4v         # Inne formaty wideo
├── blender/               
│   └── render/             # Wyrenderowane pliki
│       └── final.mp4       # Ostateczne wideo
└── analysis/
```

### Formaty Wideo w Ecosystemie
- **OBS Recording**: `.mkv` (główne nagranie)
- **Extracted Sources**: `.mp4`, `.m4v`, `.avi`
- **Blender Render**: `.mp4`, `.mov`
- **Compatibility**: Różne formaty wymagają różnego podejścia

## Wymagania Funkcjonalne

### F1. External Video Player

**F1.1 Przycisk "Open Video"**
- Dodanie przycisku "🎬 Open Video" w sekcji Actions
- Dostępny dla wszystkich nagrań zawierających pliki wideo
- Otwiera główny plik wideo w systemowym odtwarzaczu

**F1.2 Obsługa Wielu Plików**
- Lista wszystkich plików wideo w nagraniu
- Możliwość wyboru konkretnego pliku do odtworzenia
- Oddzielne przyciski dla każdego pliku wideo

### F2. Web-based Video Player

**F2.1 Wbudowany Odtwarzacz**
- HTML5 video element z podstawowymi kontrolkami
- Modal overlay na pełny ekran
- Wsparcie dla format web-compatible

**F2.2 Streaming dla Dużych Plików**
- HTTP server w Tauri dla plików > 500MB
- Chunked transfer encoding
- Seek support w timeline

### F3. Video Preview & Thumbnails

**F3.1 Thumbnail Generation**
- Generowanie miniaturek z FFmpeg
- Cache thumbnails lokalnie
- Podgląd w sekcji Files

**F3.2 Video Information**
- Rozdzielczość, codec, bitrate
- Długość wideo
- Rozmiar pliku

## Wymagania Techniczne

### Frontend (React/TypeScript)

**Nowe Komponenty:**
```typescript
// src/components/VideoPlayer.tsx
interface VideoPlayerProps {
  videoPath: string;
  onClose: () => void;
  isExternal?: boolean;
}

// src/components/VideoFilesList.tsx
interface VideoFilesListProps {
  videoFiles: VideoFile[];
  onPlayVideo: (path: string, external?: boolean) => void;
}

// src/types/index.ts
interface VideoFile {
  name: string;
  path: string;
  size: number;
  format: string;
  duration?: number;
  thumbnail?: string;
}
```

**Rozszerzenie Istniejących Komponentów:**
- `RecordingDetails.tsx`: dodanie sekcji Video Files
- `useRecordings.ts`: hook dla video operations
- `types/index.ts`: nowe typy VideoFile

### Backend (Rust)

**Nowe Komendy Tauri:**
```rust
// src-tauri/src/commands/video.rs
#[tauri::command]
pub fn open_video_external(file_path: String) -> Result<(), String>

#[tauri::command] 
pub fn get_video_files(recording_path: String) -> Result<Vec<VideoFile>, String>

#[tauri::command]
pub fn get_video_info(file_path: String) -> Result<VideoInfo, String>

#[tauri::command]
pub fn generate_thumbnail(file_path: String, output_path: String) -> Result<String, String>
```

**HTTP Server dla Streamingu:**
```rust
// src-tauri/src/services/video_server.rs
pub struct VideoServer {
    port: u16,
    server_handle: Option<JoinHandle<()>>,
}

impl VideoServer {
    pub fn start(&mut self) -> Result<u16, String>
    pub fn stop(&mut self) -> Result<(), String>
    pub fn serve_video(&self, file_path: &str) -> Result<String, String>
}
```

### File Detection & Analysis

**Video File Scanner:**
```rust
// src-tauri/src/services/video_scanner.rs
impl VideoScanner {
    pub fn scan_video_files(recording_dir: &Path) -> Vec<VideoFile>
    pub fn get_video_metadata(file_path: &Path) -> Result<VideoMetadata, String>
    pub fn is_web_compatible(file_path: &Path) -> bool
}

// Supported formats detection
const VIDEO_EXTENSIONS: &[&str] = &[".mkv", ".mp4", ".avi", ".mov", ".m4v", ".webm"];
const WEB_COMPATIBLE: &[&str] = &[".mp4", ".webm"];
```

## Implementacja UI

### Rozszerzenie RecordingDetails

**Sekcja Video Files (nowa, po Actions):**
```typescript
{/* Video Files */}
<div style={{ 
  border: '1px solid #e5e7eb', 
  borderRadius: '8px', 
  padding: '20px', 
  marginBottom: '30px' 
}}>
  <h2 style={{ margin: '0 0 15px 0', fontSize: '18px' }}>Video Files</h2>
  <div style={{ display: 'grid', gap: '15px' }}>
    {videoFiles.map((video) => (
      <div key={video.path} style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px',
        border: '1px solid #d1d5db',
        borderRadius: '6px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {video.thumbnail && (
            <img src={video.thumbnail} style={{ width: '60px', height: '40px' }} />
          )}
          <div>
            <div style={{ fontWeight: 'bold' }}>🎬 {video.name}</div>
            <div style={{ fontSize: '12px', color: '#6b7280' }}>
              {video.format} • {formatFileSize(video.size)} 
              {video.duration && ` • ${formatDuration(video.duration)}`}
            </div>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => handlePlayVideo(video.path, false)}>
            ▶️ Play
          </button>
          <button onClick={() => handlePlayVideo(video.path, true)}>
            🔗 External
          </button>
        </div>
      </div>
    ))}
  </div>
</div>
```

**Dodanie do Actions:**
```typescript
// Quick action dla głównego pliku wideo
<button onClick={() => handlePlayMainVideo()}>
  <Play size={16} />
  Play Video
</button>
```

### Modal Video Player

```typescript
// src/components/VideoPlayer.tsx
export function VideoPlayer({ videoPath, onClose }: VideoPlayerProps) {
  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.9)',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        padding: '20px',
        color: 'white'
      }}>
        <h2>{path.basename(videoPath)}</h2>
        <button onClick={onClose} style={{ color: 'white', fontSize: '24px' }}>×</button>
      </div>
      
      <video 
        controls 
        autoPlay
        style={{ flex: 1, width: '100%' }}
        src={getVideoUrl(videoPath)}
        onError={(e) => console.error('Video playback error:', e)}
      />
    </div>
  );
}
```

## Konfiguracja Tauri

### allowlist Configuration
```json
// tauri.conf.json
{
  "allowlist": {
    "protocol": {
      "asset": true,
      "assetScope": ["$VIDEO", "$DOCUMENTS/**"]
    },
    "shell": {
      "open": true,
      "scope": [
        {
          "name": "open-video",
          "cmd": "xdg-open",
          "args": true
        }
      ]
    },
    "http": {
      "all": true,
      "request": true
    }
  }
}
```

### Custom Protocol Registration
```rust
// src-tauri/src/main.rs
fn main() {
    tauri::Builder::default()
        .register_uri_scheme_protocol("video", |app, request| {
            // Handle video streaming requests
            handle_video_request(app, request)
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Etapy Implementacji

### Phase 1: External Player (MVP)
**Priorytet: Wysoki | Czas: 2-3h**

1. Komenda `open_video_external` w Rust
2. Przycisk "Open Video" w Actions
3. Auto-detection głównego pliku .mkv
4. Basic error handling

**Deliverables:**
- Jeden przycisk w Actions
- Otwieranie systemowego playera
- Works on Linux/Windows/macOS

### Phase 2: Video Files List
**Priorytet: Średni | Czas: 4-5h**

1. `VideoScanner` w Rust - wykrywanie wszystkich plików wideo
2. Nowa sekcja "Video Files" w UI
3. Lista wszystkich plików z przyciskami Play/External
4. Basic file info (size, format)

**Deliverables:**
- Sekcja Video Files w RecordingDetails
- Przyciski dla każdego pliku wideo
- File format detection

### Phase 3: Web Player Integration
**Priorytet: Średni | Czas: 6-8h**

1. HTTP server w Tauri dla serwowania plików
2. Modal VideoPlayer component
3. Format compatibility checking
4. Streaming support dla dużych plików

**Deliverables:**
- Wbudowany web player
- Modal overlay
- Streaming capability

### Phase 4: Advanced Features
**Priorytet: Niski | Czas: 8-10h**

1. Thumbnail generation z FFmpeg
2. Video metadata extraction
3. Format conversion pipeline
4. Quality selection, seek optimization

**Deliverables:**
- Thumbnails w UI
- Rich video metadata
- Advanced player controls

## Przypadki Brzegowe

### Błędy do Obsłużenia
1. **Brak systemowego playera** → fallback na web player
2. **Nieobsługiwany format** → komunikat o potrzebie konwersji
3. **Brak uprawnień** → clear error message
4. **Uszkodzony plik wideo** → graceful error handling
5. **Bardzo duże pliki** → streaming lub external player only

### Ograniczenia
- Formaty `.mkv` mogą nie działać w web playerze
- Duże pliki (>2GB) wymagają streamingu
- Cross-platform differences w external players
- CORS issues z local file serving

## Kompatybilność

### Formaty Wideo
- **Web Compatible**: `.mp4` (H.264), `.webm`
- **External Only**: `.mkv`, `.avi`, `.mov`
- **Conversion Needed**: Legacy formaty

### Systemy Operacyjne
- **Linux**: `xdg-open`
- **Windows**: `start`
- **macOS**: `open`

### Integracja z Istniejącymi Pakietami
- **obsession**: Główne pliki .mkv
- **cinemon**: Wyrenderowane .mp4 z Blender
- **setka-common**: File structure compatibility

## Success Criteria

1. **Functionality**: Użytkownik może odtwarzać wszystkie pliki wideo w nagraniu
2. **Performance**: Smooth playback dla plików do 2GB
3. **UX**: Intuicyjny interface z clear visual feedback
4. **Reliability**: Graceful error handling i fallbacks
5. **Cross-platform**: Działa na Linux/Windows/macOS

## Pytania do Rozstrzygnięcia

1. **Format Conversion**: Czy implementować auto-conversion do web formats?
2. **Thumbnail Storage**: Lokalne cache czy generate on-demand?
3. **Player Selection**: Default web player czy external player?
4. **File Size Limits**: Jaki limit dla web player vs external?
5. **Quality Options**: Czy obsługiwać multiple quality streams?

## Zależności

### Nowe Dependencje Rust
```toml
# Cargo.toml
[dependencies]
tokio = { version = "1.0", features = ["full"] }
tiny_http = "0.12"
ffmpeg-next = "0.13"  # Dla thumbnails i metadata
mime_guess = "2.0"
```

### Frontend Dependencies
```json
// package.json - już dostępne w Tauri
// Nie potrzeba dodatkowych dependencies
``` 