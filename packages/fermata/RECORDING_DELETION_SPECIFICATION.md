# Specyfikacja: Usuwanie Nagrań w Fermata

## Wprowadzenie

Dokument opisuje implementację funkcjonalności usuwania nagrań w aplikacji Fermata. Funkcja pozwala użytkownikowi na bezpieczne usunięcie nagrania wraz z wszystkimi powiązanymi plikami, z odpowiednimi zabezpieczeniami i walidacją.

## Wymagania Funkcjonalne

### F1. Przycisk Usuń

**F1.1 Lokalizacja i Wygląd**
- Przycisk "Usuń" umieszczony w wierszu nagrania, obok istniejących przycisków (następny krok, podgląd)
- Ikona: 🗑️ lub symbol kosza
- Kolor: czerwony (#dc2626) dla wyraźnego oznaczenia destrukcyjnej akcji
- Tekst: "Usuń" lub "Delete"
- Styl: outline button z czerwoną ramką i czerwonym tekstem

**F1.2 Stanowiska Przycisku**
- **Dostępny**: gdy nagranie nie ma aktywnych operacji
- **Niedostępny**: gdy na nagraniu trwa jakakolwiek operacja (extract, analyze, render, upload)
- **Hover state**: zmiana koloru na ciemniejszy czerwony
- **Disabled state**: szary kolor, brak interakcji, cursor: not-allowed

### F2. Walidacja Dostępności

**F2.1 Sprawdzanie Stanu Operacji**
```typescript
interface OperationState {
  recordingName: string;
  isRunning: boolean;
  currentOperation?: 'extract' | 'analyze' | 'setup_render' | 'render' | 'upload';
  startTime?: number;
}
```

**F2.2 Logika Dostępności**
- Przycisk niedostępny gdy `isRunning === true` dla danego nagrania
- Sprawdzanie stanu przed każdą próbą usunięcia
- Auto-refresh stanu co 2 sekundy podczas trwających operacji

### F3. Dialog Potwierdzenia

**F3.1 Wygląd Dialogu**
- Modal dialog wyśrodkowany na ekranie
- Tło z półprzezroczystą nakładką (backdrop)
- Wymiary: 400px szerokość, automatyczna wysokość
- Padding: 24px, border-radius: 12px

**F3.2 Zawartość Dialogu**
```
┌─────────────────────────────────────────┐
│  🗑️  Usuń nagranie                      │
│                                         │
│  Czy na pewno chcesz usunąć nagranie:   │
│  "stream_20240115_120000"?              │
│                                         │
│  ⚠️  Ta akcja jest nieodwracalna!       │
│                                         │
│     [Anuluj]    [Usuń nagranie] 🗑️      │
└─────────────────────────────────────────┘
```

**F3.3 Elementy Dialogu**
- **Tytuł**: Ikona kosza + "Usuń nagranie"
- **Nazwa nagrania**: Pogrubiona nazwa w cudzysłowie
- **Ostrzeżenie**: Ikona ⚠️ + tekst o nieodwracalności
- **Przyciski**:
  - "Anuluj" - szary, po lewej
  - "Usuń nagranie" - czerwony, po prawej, z ikoną kosza

### F4. Proces Usuwania

**F4.1 Sekwencja Usuwania**
1. **Sprawdź operacje**: Upewnij się że żadna operacja nie jest w toku
2. **Usuń folder nagrania**: Usunięcie całego folderu nagrania
3. **Aktualizuj UI**: Usunięcie z listy nagrań i odświeżenie

### F5. Feedback dla Użytkownika

**F5.1 Komunikaty Sukcesu**
- Toast notification: "✅ Nagranie zostało usunięte"
- Automatyczne odświeżenie listy nagrań
- Animacja zanikania wiersza z listy

**F5.2 Komunikaty Błędów**
- **Brak uprawnień**: "❌ Brak uprawnień do usunięcia plików"
- **Operacja w toku**: "⚠️ Nie można usunąć - trwa operacja na nagraniu"
- **Błąd usuwania**: "❌ Nie udało się usunąć nagrania"

## Wymagania Techniczne

### T1. Rozszerzenie Typów

**T1.1 Nowe Typy TypeScript**
```typescript
// Dodanie do types/index.ts
export interface DeletionConfirmationState {
  isOpen: boolean;
  recording?: Recording;
  isDeleting: boolean;
}
```

### T2. Rust Backend Commands

**T2.1 Nowe Tauri Commands**
```rust
// src-tauri/src/commands/recordings.rs

#[tauri::command]
pub async fn delete_recording(
    recording_name: String
) -> Result<(), String> {
    // Usunięcie całego folderu nagrania
}
```

### T3. Frontend Components

**T3.1 DeleteButton Component**
```typescript
interface DeleteButtonProps {
  recording: Recording;
  isOperationRunning: boolean;
  onDelete: (recordingName: string) => void;
}

export function DeleteButton({ recording, isOperationRunning, onDelete }: DeleteButtonProps) {
  // Implementacja przycisku usuń
}
```

**T3.2 DeletionConfirmDialog Component**
```typescript
interface DeletionConfirmDialogProps {
  isOpen: boolean;
  recording?: Recording;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}

export function DeletionConfirmDialog(props: DeletionConfirmDialogProps) {
  // Implementacja dialogu potwierdzenia
}
```

### T4. State Management

**T4.1 Rozszerzenie useRecordings Hook**
```typescript
export function useRecordings() {
  // ... istniejący kod ...
  
  const [deletionState, setDeletionState] = useState<DeletionConfirmationState>({
    isOpen: false,
    recording: undefined,
    isDeleting: false
  });
  
  const deleteRecording = useCallback(async (recordingName: string) => {
    setDeletionState(prev => ({ ...prev, isDeleting: true }));
    try {
      await invoke('delete_recording', { recordingName });
      setDeletionState({ isOpen: false, recording: undefined, isDeleting: false });
      refreshRecordings(); // Odśwież listę
    } catch (error) {
      setDeletionState(prev => ({ ...prev, isDeleting: false }));
      // Pokaż error toast
    }
  }, []);
  
  return {
    // ... istniejące wartości ...
    deletionState,
    deleteRecording,
    showDeletionDialog: (recording: Recording) => {
      setDeletionState({ isOpen: true, recording, isDeleting: false });
    },
    hideDeletionDialog: () => {
      setDeletionState({ isOpen: false, recording: undefined, isDeleting: false });
    }
  };
}
```

## Przypadki Użycia

### UC1. Podstawowe Usunięcie
1. Użytkownik klika przycisk "Usuń" przy nagraniu
2. Wyświetla się dialog potwierdzenia z nazwą nagrania
3. Użytkownik klika "Usuń nagranie"
4. System usuwa folder nagrania i odświeża listę

### UC2. Blokada Podczas Operacji
1. Na nagraniu trwa operacja (np. renderowanie)
2. Przycisk "Usuń" jest nieaktywny (szary)
3. Po zakończeniu operacji przycisk staje się aktywny

### UC3. Błąd Podczas Usuwania
1. Użytkownik potwierdza usunięcie
2. System nie może usunąć folderu
3. Wyświetla toast z błędem

### UC4. Anulowanie Usunięcia
1. Użytkownik klika "Usuń"
2. W dialogu klika "Anuluj"
3. Dialog zamyka się bez zmian

## Konfiguracja i Zabezpieczenia

### S1. Ograniczenia Bezpieczeństwa
- Brak możliwości usunięcia podczas operacji
- Wymagane potwierdzenie przed usunięciem
- Timeout 30s dla operacji usuwania

## Wdrożenie

### Faza 1: Backend
1. Implementacja `delete_recording` command w Rust
2. Usuwanie całego folderu nagrania

### Faza 2: Frontend
1. Dodanie przycisku "Usuń" w RecordingList
2. Dialog potwierdzenia 
3. Integracja z hook'iem

### Faza 3: Finalizacja
1. Toast notifications
2. Error handling
3. Testy podstawowe

**Uwaga**: Implementacja oparta na prostym usuwaniu folderu - bez skomplikowanych walidacji czy logowania. 