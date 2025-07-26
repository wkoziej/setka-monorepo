# Cinemon Architecture Expansion Plan

## Cel rozszerzeń

Celem jest rozszerzenie architektury cinemon o:

1. **Różne układy wideo** (PiP, wszystkie w centrum, układane by wypełniały obraz, grid layouts)
2. **Niezależne animacje wideo** uwzględniające różne informacje z analizy audio (skala/bass, drgania/beat, rozmycie/głośność)

## Analiza obecnej architektury

### ✅ Co już działa:
- **Delegation pattern** w `AnimationEngine` - łatwe dodawanie nowych animatorów
- **LayoutManager** - centralizuje logikę układów (ale tylko 2x2 grid)
- **Separacja układu i animacji** - layout w `_setup_layout()`, animacje w `_animate_*()`
- **Modularne komponenty** - `KeyframeHelper`, `VintageFilmEffects`

### ❌ Obecne ograniczenia:

1. **Układy wideo**: Tylko hardcoded 2x2 grid w `MultiPipAnimator`
2. **Sprzężone animacje**: Każdy animator ma własną logikę, bez możliwości kombinowania
3. **Ograniczone właściwości**: Tylko `blend_alpha`, `scale_x/y`, `offset_x/y`
4. **Monolityczne tryby**: `beat-switch`, `energy-pulse`, `multi-pip` są niepodzielne

## Propozycja rozwiązania: Compositional Pattern

### Architektura docelowa

Zamiast monolitycznych animatorów, **composition-based approach**:

```python
# Nowy workflow:
layout = GridLayout(rows=2, cols=2)  # lub CenterLayout(), FillLayout()
animations = [
    ScaleAnimation(trigger="bass", intensity=0.3),
    BlurAnimation(trigger="volume", range=(0, 5)),
    ShakeAnimation(trigger="beat", intensity=2.0)
]

compositor = AnimationCompositor(layout, animations)
compositor.apply(video_strips, audio_analysis, fps)
```

### 1. Rozwiązanie dla układów wideo

```python
# vse/layouts/base.py
class BaseLayout:
    def calculate_positions(self, strip_count: int, resolution: tuple) -> List[LayoutPosition]:
        """Oblicz pozycje dla wszystkich stripów w układzie."""
        raise NotImplementedError

    def supports_strip_count(self, count: int) -> bool:
        """Sprawdź czy układ obsługuje daną liczbę stripów."""
        raise NotImplementedError

# vse/layouts/grid_layout.py
class GridLayout(BaseLayout):
    def __init__(self, rows: int, cols: int, spacing: float = 0.1):
        self.rows = rows
        self.cols = cols
        self.spacing = spacing

    def calculate_positions(self, strip_count: int, resolution: tuple) -> List[LayoutPosition]:
        """Oblicz pozycje dla siatki NxM."""
        # Implementacja kalkulacji pozycji w siatce
        pass

# vse/layouts/center_layout.py
class CenterLayout(BaseLayout):
    def __init__(self, scale: float = 1.0):
        self.scale = scale

    def calculate_positions(self, strip_count: int, resolution: tuple) -> List[LayoutPosition]:
        """Wszystkie stripy w centrum, jeden na drugim."""
        # Implementacja centrowania wszystkich stripów
        pass

# vse/layouts/fill_layout.py
class FillLayout(BaseLayout):
    def __init__(self, arrangement: str = "auto"):  # auto, horizontal, vertical
        self.arrangement = arrangement

    def calculate_positions(self, strip_count: int, resolution: tuple) -> List[LayoutPosition]:
        """Stripy wypełniają obraz bez nakładania."""
        # Implementacja automatycznego rozmieszczania
        pass
```

### 2. Rozwiązanie dla niezależnych animacji

```python
# vse/animations/base.py
class BaseAnimation:
    def __init__(self, trigger: str, property: str, **config):
        self.trigger = trigger  # "bass", "beat", "volume", "energy_peaks"
        self.property = property  # "scale", "blur", "shake", "alpha"
        self.config = config

    def apply(self, strips: List, events: List, fps: int):
        """Zastosuj animację do stripów na podstawie eventów."""
        raise NotImplementedError

    def can_apply_to_property(self, property: str) -> bool:
        """Sprawdź czy animacja może być zastosowana do danej właściwości."""
        raise NotImplementedError

# vse/animations/scale_animation.py
class ScaleAnimation(BaseAnimation):
    def __init__(self, trigger="bass", intensity=0.3, duration_frames=2):
        super().__init__(trigger, "scale", intensity=intensity, duration_frames=duration_frames)

    def apply(self, strips: List, events: List, fps: int):
        """Animuj skalę stripów na podstawie eventów."""
        for event_time in events:
            frame = int(event_time * fps)
            for strip in strips:
                # Zwiększ skalę na event
                new_scale = 1.0 + self.config['intensity']
                strip.transform.scale_x = new_scale
                strip.transform.scale_y = new_scale
                # Dodaj keyframe
                # Wróć do normalnej skali po duration_frames

# vse/animations/blur_animation.py
class BlurAnimation(BaseAnimation):
    def __init__(self, trigger="volume", range=(0, 5), smoothing=0.1):
        super().__init__(trigger, "blur", range=range, smoothing=smoothing)

    def apply(self, strips: List, events: List, fps: int):
        """Animuj rozmycie na podstawie poziomu głośności."""
        # Implementacja rozmycia przez efekty Blender
        pass

# vse/animations/shake_animation.py
class ShakeAnimation(BaseAnimation):
    def __init__(self, trigger="beat", intensity=2.0, decay=0.8):
        super().__init__(trigger, "shake", intensity=intensity, decay=decay)

    def apply(self, strips: List, events: List, fps: int):
        """Animuj drgania pozycji na podstawie beatów."""
        # Implementacja losowych przesunięć pozycji
        pass
```

### 3. Compositor - główny orchestrator

```python
# vse/compositor.py
class AnimationCompositor:
    def __init__(self, layout: BaseLayout, animations: List[BaseAnimation]):
        self.layout = layout
        self.animations = animations

    def apply(self, video_strips: List, audio_analysis: Dict, fps: int) -> bool:
        """Zastosuj layout i animacje do stripów."""
        try:
            # 1. Apply layout
            resolution = self._get_scene_resolution()
            positions = self.layout.calculate_positions(len(video_strips), resolution)
            self._apply_layout(video_strips, positions)

            # 2. Apply animations independently
            for animation in self.animations:
                events = self._extract_events(audio_analysis, animation.trigger)
                animation.apply(video_strips, events, fps)

            return True
        except Exception as e:
            print(f"Error applying compositor: {e}")
            return False

    def _apply_layout(self, strips: List, positions: List[LayoutPosition]):
        """Zastosuj pozycje układu do stripów."""
        for strip, position in zip(strips, positions):
            strip.transform.offset_x = position.x
            strip.transform.offset_y = position.y
            strip.transform.scale_x = position.scale
            strip.transform.scale_y = position.scale

    def _extract_events(self, audio_analysis: Dict, trigger: str) -> List[float]:
        """Wyciągnij eventy z analizy audio na podstawie triggera."""
        events = audio_analysis.get("animation_events", {})

        if trigger == "bass":
            return events.get("energy_peaks", [])
        elif trigger == "beat":
            return events.get("beats", [])
        elif trigger == "volume":
            # Tutaj trzeba by było rozszerzyć beatrix o analizę głośności
            return events.get("volume_changes", [])
        else:
            return []
```

## Plan implementacji stopniowej

### Faza 1: Rozszerzenie LayoutManager (backward compatible)

```python
# Dodaj nowe metody do istniejącego LayoutManager
class BlenderLayoutManager:
    def calculate_center_layout(self, strip_count: int) -> List[Tuple[int, int, float]]:
        """Wszystkie stripy w centrum, jeden na drugim."""
        return [(0, 0, 1.0)] * strip_count

    def calculate_fill_layout(self, strip_count: int, arrangement: str = "auto") -> List[Tuple[int, int, float]]:
        """Stripy wypełniają obraz bez nakładania."""
        if arrangement == "horizontal":
            return self._calculate_horizontal_fill(strip_count)
        elif arrangement == "vertical":
            return self._calculate_vertical_fill(strip_count)
        else:
            return self._calculate_auto_fill(strip_count)

    def calculate_grid_layout(self, rows: int, cols: int, strip_count: int) -> List[Tuple[int, int, float]]:
        """Siatka NxM, bardziej elastyczna niż obecna multi-pip."""
        # Implementacja elastycznej siatki
        pass
```

### Faza 2: Separacja animacji od animatorów

```python
# Wyciągnij logikę animacji z MultiPipAnimator do niezależnych klas
class ScaleOnBassAnimation:
    def apply_to_strips(self, strips, bass_events, fps):
        """Logika skalowania na bass, wyciągnięta z energy-pulse."""
        pass

class VisibilityOnSectionAnimation:
    def apply_to_strips(self, strips, section_events, fps):
        """Logika przełączania widoczności, wyciągnięta z multi-pip."""
        pass

class PositionShakeAnimation:
    def apply_to_strips(self, strips, beat_events, fps):
        """Nowa animacja - drgania pozycji."""
        pass
```

### Faza 3: Nowy compositor API

```python
# Dodaj nowy compositor jako alternatywę dla istniejących animatorów
class CompositionalAnimator:
    """Nowy animator używający pattern compositional."""

    def __init__(self):
        self.compositor = None

    def get_animation_mode(self) -> str:
        return "compositional"

    def can_handle(self, animation_mode: str) -> bool:
        return animation_mode == "compositional"

    def animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool:
        # Konfiguracja z parametrów środowiskowych
        layout_type = os.getenv("BLENDER_VSE_LAYOUT_TYPE", "grid")
        animation_config = os.getenv("BLENDER_VSE_ANIMATION_CONFIG", "")

        # Tworzenie layoutu
        if layout_type == "center":
            layout = CenterLayout()
        elif layout_type == "fill":
            layout = FillLayout()
        else:
            layout = GridLayout(2, 2)  # domyślnie

        # Parsowanie animacji z config
        animations = self._parse_animation_config(animation_config)

        # Aplikacja
        compositor = AnimationCompositor(layout, animations)
        return compositor.apply(video_strips, animation_data, fps)
```

## Zalety tego podejścia

1. **Kompozycyjność**: Dowolne kombinacje układów i animacji
2. **Rozszerzalność**: Łatwe dodawanie nowych układów/animacji bez modyfikacji istniejącego kodu
3. **Testowalnośc**: Każdy komponent testowalny osobno
4. **Backward compatibility**: Stare animatory nadal działają
5. **Granularność**: Animacje niezależne od siebie
6. **Konfigurowalność**: Parametry przez zmienne środowiskowe

## Rozszerzenia beatrix

Dla pełnej funkcjonalności, beatrix powinien zostać rozszerzony o:

```python
# W beatrix - dodatkowe analizy audio
class AudioAnalyzer:
    def analyze_volume_changes(self, audio_file: Path) -> List[float]:
        """Analiza zmian głośności dla blur/fade effects."""
        pass

    def analyze_frequency_bands(self, audio_file: Path) -> Dict[str, List[float]]:
        """Analiza pasm częstotliwości (bass, mid, treble)."""
        pass

    def analyze_spectral_features(self, audio_file: Path) -> Dict[str, List[float]]:
        """Analiza cech spektralnych (brightness, roughness, etc.)."""
        pass
```

## Przykłady użycia

### Przykład 1: Kompleksowy układ z wieloma animacjami

```bash
# Zmienne środowiskowe
export BLENDER_VSE_LAYOUT_TYPE="grid"
export BLENDER_VSE_LAYOUT_CONFIG="rows=2,cols=2,spacing=0.1"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.3,shake:beat:2.0,blur:volume:0-5"

cinemon-blend-setup ./recording --animation-mode compositional
```

### Przykład 2: Wszystkie wideo w centrum z efektami

```bash
export BLENDER_VSE_LAYOUT_TYPE="center"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.5,alpha:beat:0.8-1.0"

cinemon-blend-setup ./recording --animation-mode compositional
```

### Przykład 3: Wypełnianie ekranu automatyczne

```bash
export BLENDER_VSE_LAYOUT_TYPE="fill"
export BLENDER_VSE_LAYOUT_CONFIG="arrangement=auto"
export BLENDER_VSE_ANIMATION_CONFIG="shake:beat:1.0,blur:volume:0-3"

cinemon-blend-setup ./recording --animation-mode compositional
```

## Następne kroki

1. **Proof of concept**: Implementacja podstawowego layoutu i jednej animacji
2. **Rozszerzenie testów**: Testy dla nowych komponentów
3. **Dokumentacja**: Aktualizacja CLAUDE.md z nowymi wzorcami
4. **Integracja**: Dodanie do AnimationEngine jako nowy animator
5. **Rozszerzenie beatrix**: Dodanie nowych typów analizy audio
