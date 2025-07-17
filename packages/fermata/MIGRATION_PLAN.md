# Plan Migracji Fermata: Tauri → FastAPI + React

## 1. Przegląd Migracji

### Obecna Architektura
- **Frontend**: React + TypeScript + Vite
- **Backend**: Rust (Tauri) z IPC commands
- **Komunikacja**: `@tauri-apps/api` invoke()
- **Deployment**: Single binary desktop app

### Docelowa Architektura
- **Frontend**: React + TypeScript + Vite (bez zmian)
- **Backend**: Python FastAPI
- **Komunikacja**: HTTP REST API
- **Deployment**: Oddzielne procesy (web app)

## 2. Analiza Obecnej Funkcjonalności

### Komendy Rust do Przeportowania

| Komenda Rust | Endpoint FastAPI | Opis |
|--------------|------------------|------|
| `get_recordings` | `GET /recordings` | Lista wszystkich nagrań |
| `get_recording_details` | `GET /recordings/{name}` | Szczegóły nagrania |
| `get_recordings_by_status` | `GET /recordings?status={status}` | Filtrowanie po statusie |
| `get_recordings_needing_attention` | `GET /recordings/attention` | Nagrania wymagające uwagi |
| `update_recordings_path` | `PUT /config/recordings-path` | Aktualizacja ścieżki |
| `get_app_config` | `GET /config` | Konfiguracja aplikacji |

### Modele Danych do Przeportowania

```rust
// Rust (obecne)
pub struct AppConfig {
    pub recordings_path: PathBuf,
    pub cli_paths: CliPaths,
}

pub enum RecordingStatus {
    Recorded,
    Extracted, 
    Analyzed,
    Rendered,
    Uploaded,
    Failed(String),
}
```

## 3. Nowa Struktura Katalogów

```
packages/fermata/
├── frontend/                  # React app (przeprowadzka z src/)
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── backend/                   # Nowy Python FastAPI
│   ├── src/
│   │   ├── fermata_api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py        # FastAPI app
│   │   │   ├── models/        # Pydantic models
│   │   │   ├── services/      # Business logic
│   │   │   ├── routers/       # API routes
│   │   │   └── config.py      # App configuration
│   │   └── fermata_api.egg-info/
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
├── shared/                    # Wspólne typy TypeScript/Python
│   ├── types.py
│   └── types.ts
├── docker-compose.yml         # Development setup
├── MIGRATION_PLAN.md
└── README.md
```

## 4. Wykorzystanie Istniejących Pakietów

### setka-common Integration

```python
# backend/src/fermata_api/services/file_service.py
from setka_common.file_structure.specialized.recording import RecordingStructure
from setka_common.utils.files import ensure_directory

class RecordingService:
    def __init__(self, recordings_path: str):
        self.recordings_path = Path(recordings_path)
        
    def scan_recordings(self) -> List[Recording]:
        """Wykorzystuje setka-common do skanowania struktury plików"""
        recordings = []
        for recording_dir in self.recordings_path.iterdir():
            if recording_dir.is_dir():
                recording = RecordingStructure(recording_dir)
                recordings.append(self._convert_to_api_model(recording))
        return recordings
```

### Współdzielenie z innymi pakietami

- **beatrix**: Analiza audio przez API calls
- **obsession**: Metadata extraction z nagrań
- **medusa**: Upload workflow integration

## 5. Plan Implementacji

### Faza 1: Backend Foundation (2-3 dni)

#### 5.1 Podstawowa struktura FastAPI
```python
# backend/src/fermata_api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import recordings, config
from .config import settings

app = FastAPI(title="Fermata API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
app.include_router(config.router, prefix="/config", tags=["config"])
```

#### 5.2 Modele Pydantic
```python
# backend/src/fermata_api/models/recording.py
from pydantic import BaseModel
from enum import Enum
from typing import Dict, Union
from datetime import datetime

class RecordingStatus(str, Enum):
    RECORDED = "Recorded"
    EXTRACTED = "Extracted" 
    ANALYZED = "Analyzed"
    RENDERED = "Rendered"
    UPLOADED = "Uploaded"

class FailedStatus(BaseModel):
    Failed: str

class Recording(BaseModel):
    name: str
    path: str
    status: Union[RecordingStatus, FailedStatus]
    last_updated: int  # Unix timestamp
    file_sizes: Dict[str, int]
    
    class Config:
        use_enum_values = True
```

#### 5.3 Services z setka-common
```python
# backend/src/fermata_api/services/recording_service.py
from setka_common.file_structure.specialized.recording import RecordingStructure
from ..models.recording import Recording, RecordingStatus, FailedStatus
from pathlib import Path
from typing import List

class RecordingService:
    def __init__(self, recordings_path: str):
        self.recordings_path = Path(recordings_path)
    
    def get_all_recordings(self) -> List[Recording]:
        # Logika przeportowana z Rust FileScanner
        
    def get_recording_by_name(self, name: str) -> Recording:
        # Logika przeportowana z Rust get_recording_details
        
    def get_recordings_by_status(self, status: str) -> List[Recording]:
        # Filtrowanie implementowane w Python
```

### Faza 2: API Endpoints (1-2 dni)

#### 5.4 Routery FastAPI
```python
# backend/src/fermata_api/routers/recordings.py
from fastapi import APIRouter, HTTPException, Depends
from ..services.recording_service import RecordingService
from ..models.recording import Recording
from typing import List

router = APIRouter()

@router.get("/", response_model=List[Recording])
async def get_recordings(service: RecordingService = Depends()):
    return service.get_all_recordings()

@router.get("/{name}", response_model=Recording)
async def get_recording_details(name: str, service: RecordingService = Depends()):
    recording = service.get_recording_by_name(name)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording
```

### Faza 3: Frontend Migration (1 dzień)

#### 5.5 API Client
```typescript
// frontend/src/services/api.ts
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async getRecordings(): Promise<Recording[]> {
    return this.request<Recording[]>('/recordings');
  }
  
  async getRecordingDetails(name: string): Promise<Recording> {
    return this.request<Recording>(`/recordings/${name}`);
  }
}

export const apiClient = new ApiClient();
```

#### 5.6 Updated Hooks
```typescript
// frontend/src/hooks/useRecordings.ts - UPDATED
import { apiClient } from '../services/api';

export function useRecordings() {
  const refreshRecordings = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const recordings = await apiClient.getRecordings();
      setState({ recordings, loading: false, error: null });
    } catch (error) {
      setState({
        recordings: [],
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }, []);
  
  // Reszta logiki bez zmian
}
```

### Faza 4: Testing (2 dni)

#### 5.7 Backend Tests
```python
# backend/tests/test_recording_service.py
import pytest
from fermata_api.services.recording_service import RecordingService
from pathlib import Path
import tempfile

@pytest.fixture
def temp_recordings_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Tworzenie testowych struktur nagrań
        yield Path(tmpdir)

def test_scan_recordings(temp_recordings_dir):
    service = RecordingService(str(temp_recordings_dir))
    recordings = service.get_all_recordings()
    assert len(recordings) == 2
    assert recordings[0].name == "test_recording_001"

# backend/tests/test_api.py
from fastapi.testclient import TestClient
from fermata_api.main import app

client = TestClient(app)

def test_get_recordings():
    response = client.get("/recordings")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

#### 5.8 Frontend Tests
```typescript
// frontend/src/hooks/useRecordings.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useRecordings } from './useRecordings';
import { apiClient } from '../services/api';

// Mock API client
jest.mock('../services/api');
const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('useRecordings', () => {
  it('should load recordings on mount', async () => {
    const mockRecordings = [
      { name: 'test1', status: 'Recorded', /* ... */ }
    ];
    mockApiClient.getRecordings.mockResolvedValue(mockRecordings);
    
    const { result } = renderHook(() => useRecordings());
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.recordings).toEqual(mockRecordings);
    });
  });
});
```

### Faza 5: Integration & Deployment (1 dzień)

#### 5.9 Docker Development Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ${FERMATA_RECORDINGS_PATH}:/recordings
    environment:
      - RECORDINGS_PATH=/recordings
      - CORS_ORIGINS=http://localhost:5173
    command: uvicorn fermata_api.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
    environment:
      - VITE_API_URL=http://localhost:8000
    command: npm run dev
```

#### 5.10 Configuration Management
```python
# backend/src/fermata_api/config.py
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    recordings_path: str = "/tmp/recordings"
    allowed_origins: List[str] = ["http://localhost:5173"]
    cors_origins: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## 6. Checklist Migracji

### Backend ✅
- [ ] Podstawowa struktura FastAPI
- [ ] Modele Pydantic (Recording, Config, Status)
- [ ] Service layer z setka-common integration
- [ ] API routers (recordings, config)
- [ ] Error handling i logging
- [ ] Environment configuration
- [ ] Unit tests (services)
- [ ] Integration tests (API)

### Frontend ✅
- [ ] API client class
- [ ] Updated useRecordings hook
- [ ] Error boundary components
- [ ] Environment variables setup
- [ ] TypeScript types synchronization
- [ ] Unit tests (hooks, components)
- [ ] E2E tests (critical paths)

### Infrastructure ✅
- [ ] Docker setup
- [ ] Development docker-compose
- [ ] CORS configuration
- [ ] Logging setup
- [ ] Health checks
- [ ] Documentation update

### Integration ✅
- [ ] setka-common package wykorzystanie
- [ ] Shared types między frontend/backend
- [ ] Error handling spójność
- [ ] Performance testing
- [ ] Security review (CORS, validation)

## 7. Risk Analysis & Mitigation

### Wysokie Ryzyko
1. **Funkcjonalność CLI operations** - Rust wywołuje CLI przez proces, FastAPI musi to replikować
   - *Mitigacja*: Async subprocess calls, proper error handling
   
2. **File watching/monitoring** - Tauri ma native file watchers
   - *Mitigacja*: Python watchdog library, WebSocket notifications

3. **Performance** - Rust może być szybszy przy file scanning
   - *Mitigacja*: Profilowanie, optymalizacja, caching

### Średnie Ryzyko
1. **CORS issues** - Development może mieć problemy z cross-origin
   - *Mitigacja*: Proper CORS setup, reverse proxy option

2. **TypeScript types sync** - Ręczna synchronizacja typów
   - *Mitigacja*: Code generation lub shared schema

## 8. Post-Migration Tasks

- [ ] Performance monitoring setup
- [ ] Production deployment strategy
- [ ] Backup migration path (powrót do Tauri jeśli needed)
- [ ] Documentation update
- [ ] Team training na nowej architekturze

## 9. Timeline

**Łącznie: 7-9 dni**

- Faza 1: Backend Foundation (2-3 dni)
- Faza 2: API Endpoints (1-2 dni) 
- Faza 3: Frontend Migration (1 dzień)
- Faza 4: Testing (2 dni)
- Faza 5: Integration & Deployment (1 dzień)

## 10. Success Criteria

✅ **Functional Parity**
- Wszystkie obecne funkcje działają identycznie
- Performance nie gorsza niż o 20%
- UI/UX bez zmian dla end-usera

✅ **Technical Improvements**  
- Łatwiejsza integracja z innymi pakietami
- Lepsze testing capabilities
- Cleaner separation of concerns

✅ **Development Experience**
- Faster development iteration
- Better debugging capabilities  
- Improved error handling 