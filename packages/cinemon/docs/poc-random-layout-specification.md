# PoC: RandomLayout i Kompozytowe Animacje - Specyfikacja

## Cel PoC

Dowód koncepcji dla nowej architektury kompozytowej w cinemon:
1. **RandomLayout** - losowe rozmieszczenie wideo na ekranie
2. **Animacje kompozytowe** - ScaleAnimation, ShakeAnimation, RotationWobbleAnimation
3. **Refaktoryzacja** - wydzielenie wspólnej logiki z VintageFilmEffects
4. **TDD** - implementacja zgodnie z Test-Driven Development

## Architektura PoC

### 1. RandomLayout

```python
# vse/layouts/random_layout.py
class RandomLayout(BaseLayout):
    """
    Losowe rozmieszczenie stripów na ekranie.
    
    Parametry:
    - overlap_allowed: czy stripy mogą się nakładać
    - margin: minimalna odległość od krawędzi ekranu (%)
    - min_scale: minimalna skala stripu
    - max_scale: maksymalna skala stripu
    - seed: seed dla generatora losowego (dla powtarzalności)
    """
    
    def __init__(self, 
                 overlap_allowed: bool = False,
                 margin: float = 0.05,
                 min_scale: float = 0.3,
                 max_scale: float = 0.8,
                 seed: int = None):
        self.overlap_allowed = overlap_allowed
        self.margin = margin
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.seed = seed
        if seed:
            random.seed(seed)
    
    def calculate_positions(self, strip_count: int, resolution: tuple) -> List[LayoutPosition]:
        """Oblicz losowe pozycje dla wszystkich stripów."""
        positions = []
        width, height = resolution
        half_width = width // 2
        half_height = height // 2
        
        # Margines w pikselach
        margin_x = int(half_width * self.margin)
        margin_y = int(half_height * self.margin)
        
        occupied_areas = []  # Lista zajętych obszarów (jeśli overlap_allowed=False)
        
        for i in range(strip_count):
            # Losowa skala
            scale = random.uniform(self.min_scale, self.max_scale)
            
            # Próbuj znaleźć wolne miejsce (max 100 prób)
            for attempt in range(100):
                # Losowa pozycja (z uwzględnieniem marginesów)
                x = random.randint(-half_width + margin_x, half_width - margin_x)
                y = random.randint(-half_height + margin_y, half_height - margin_y)
                
                # Sprawdź kolizje jeśli overlap_allowed=False
                if not self.overlap_allowed:
                    collision = self._check_collision(x, y, scale, occupied_areas, resolution)
                    if collision:
                        continue
                
                # Dodaj pozycję
                position = LayoutPosition(x=x, y=y, scale=scale)
                positions.append(position)
                
                if not self.overlap_allowed:
                    occupied_areas.append((x, y, scale))
                break
            else:
                # Nie udało się znaleźć wolnego miejsca - użyj ostatniej pozycji
                positions.append(LayoutPosition(x=x, y=y, scale=scale))
        
        return positions
```

### 2. Refaktoryzacja VintageFilmEffects

Wydzielenie bazowej klasy dla animacji efektów:

```python
# vse/animations/base_effect_animation.py
class BaseEffectAnimation:
    """Bazowa klasa dla animacji efektów."""
    
    def __init__(self, keyframe_helper: KeyframeHelper = None):
        self.keyframe_helper = keyframe_helper or KeyframeHelper()
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """Zastosuj animację do pojedynczego stripu."""
        raise NotImplementedError
    
    def get_required_properties(self) -> List[str]:
        """Zwróć listę wymaganych właściwości stripu."""
        raise NotImplementedError
```

### 3. Animacje do implementacji

#### ScaleAnimation

```python
# vse/animations/scale_animation.py
class ScaleAnimation(BaseEffectAnimation):
    """
    Animacja skalowania na podstawie eventów.
    
    Parametry:
    - trigger: typ eventu ("bass", "beat", "energy_peaks")
    - intensity: intensywność skalowania (0.1 = 10% większe)
    - duration_frames: czas trwania efektu w klatkach
    - easing: typ easingu ("linear", "ease_in", "ease_out", "bounce")
    """
    
    def __init__(self, 
                 trigger: str = "bass",
                 intensity: float = 0.3,
                 duration_frames: int = 2,
                 easing: str = "linear"):
        super().__init__()
        self.trigger = trigger
        self.intensity = intensity
        self.duration_frames = duration_frames
        self.easing = easing
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """Animuj skalę stripu na podstawie eventów."""
        if not hasattr(strip, 'transform'):
            return False
        
        # Początkowa skala
        base_scale_x = strip.transform.scale_x
        base_scale_y = strip.transform.scale_y
        self.keyframe_helper.insert_transform_scale_keyframes(
            strip.name, 1, base_scale_x, base_scale_y
        )
        
        for event_time in events:
            frame = int(event_time * fps)
            
            # Skaluj w górę
            scale_factor = 1.0 + self.intensity
            strip.transform.scale_x = base_scale_x * scale_factor
            strip.transform.scale_y = base_scale_y * scale_factor
            self.keyframe_helper.insert_transform_scale_keyframes(
                strip.name, frame, 
                base_scale_x * scale_factor,
                base_scale_y * scale_factor
            )
            
            # Powrót do normalnej skali
            return_frame = frame + self.duration_frames
            strip.transform.scale_x = base_scale_x
            strip.transform.scale_y = base_scale_y
            self.keyframe_helper.insert_transform_scale_keyframes(
                strip.name, return_frame, base_scale_x, base_scale_y
            )
        
        return True
    
    def get_required_properties(self) -> List[str]:
        return ['transform']
```

#### ShakeAnimation

```python
# vse/animations/shake_animation.py
class ShakeAnimation(BaseEffectAnimation):
    """
    Animacja drgań pozycji (refaktoryzacja z VintageFilmEffects.apply_camera_shake).
    
    Parametry:
    - trigger: typ eventu ("beat", "bass", "energy_peaks")
    - intensity: intensywność drgań w pikselach
    - return_frames: po ilu klatkach wrócić do pozycji wyjściowej
    - random_direction: czy kierunek drgań ma być losowy
    """
    
    def __init__(self,
                 trigger: str = "beat",
                 intensity: float = 10.0,
                 return_frames: int = 2,
                 random_direction: bool = True):
        super().__init__()
        self.trigger = trigger
        self.intensity = intensity
        self.return_frames = return_frames
        self.random_direction = random_direction
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """Animuj pozycję stripu z efektem drgań."""
        if not hasattr(strip, 'transform'):
            return False
        
        # Pobierz bazową pozycję
        base_x = strip.transform.offset_x
        base_y = strip.transform.offset_y
        
        # Ustaw początkowy keyframe
        self.keyframe_helper.insert_transform_position_keyframes(strip.name, 1)
        
        for event_time in events:
            frame = int(event_time * fps)
            
            # Oblicz przesunięcie
            if self.random_direction:
                shake_x = random.uniform(-self.intensity, self.intensity)
                shake_y = random.uniform(-self.intensity, self.intensity)
            else:
                # Deterministyczne drgania (np. tylko w poziomie)
                shake_x = self.intensity
                shake_y = 0
            
            # Zastosuj drganie
            strip.transform.offset_x = base_x + shake_x
            strip.transform.offset_y = base_y + shake_y
            self.keyframe_helper.insert_transform_position_keyframes(strip.name, frame)
            
            # Powrót do pozycji bazowej
            return_frame = frame + self.return_frames
            strip.transform.offset_x = base_x
            strip.transform.offset_y = base_y
            self.keyframe_helper.insert_transform_position_keyframes(
                strip.name, return_frame
            )
        
        return True
    
    def get_required_properties(self) -> List[str]:
        return ['transform']
```

#### RotationWobbleAnimation

```python
# vse/animations/rotation_wobble_animation.py
class RotationWobbleAnimation(BaseEffectAnimation):
    """
    Animacja kołysania rotacji (refaktoryzacja z VintageFilmEffects.apply_rotation_wobble).
    
    Parametry:
    - trigger: typ eventu ("beat", "bass", "energy_peaks")
    - wobble_degrees: maksymalne wychylenie w stopniach
    - return_frames: po ilu klatkach wrócić do rotacji wyjściowej
    - oscillate: czy kołysać się tam i z powrotem
    """
    
    def __init__(self,
                 trigger: str = "beat",
                 wobble_degrees: float = 1.0,
                 return_frames: int = 3,
                 oscillate: bool = True):
        super().__init__()
        self.trigger = trigger
        self.wobble_degrees = wobble_degrees
        self.return_frames = return_frames
        self.oscillate = oscillate
    
    def apply_to_strip(self, strip, events: List[float], fps: int, **kwargs) -> bool:
        """Animuj rotację stripu z efektem kołysania."""
        if not hasattr(strip, 'transform'):
            return False
        
        # Ustaw początkowy keyframe
        self.keyframe_helper.insert_transform_rotation_keyframe(strip.name, 1, 0.0)
        
        direction = 1  # Kierunek kołysania
        
        for i, event_time in enumerate(events):
            frame = int(event_time * fps)
            
            # Oblicz rotację
            if self.oscillate and i > 0:
                direction *= -1  # Zmień kierunek
            
            wobble_rotation = random.uniform(0, self.wobble_degrees) * direction
            wobble_radians = math.radians(wobble_rotation)
            
            # Zastosuj kołysanie
            strip.transform.rotation = wobble_radians
            self.keyframe_helper.insert_transform_rotation_keyframe(
                strip.name, frame, wobble_radians
            )
            
            # Powrót do normalnej rotacji
            return_frame = frame + self.return_frames
            strip.transform.rotation = 0.0
            self.keyframe_helper.insert_transform_rotation_keyframe(
                strip.name, return_frame, 0.0
            )
        
        return True
    
    def get_required_properties(self) -> List[str]:
        return ['transform']
```

### 4. AnimationCompositor

```python
# vse/animation_compositor.py
class AnimationCompositor:
    """
    Kompozytor układów i animacji.
    
    Przykład użycia:
        layout = RandomLayout(overlap_allowed=False, seed=42)
        animations = [
            ScaleAnimation(trigger="bass", intensity=0.3),
            ShakeAnimation(trigger="beat", intensity=5.0),
            RotationWobbleAnimation(trigger="beat", wobble_degrees=0.5)
        ]
        compositor = AnimationCompositor(layout, animations)
        compositor.apply(video_strips, audio_analysis, fps)
    """
    
    def __init__(self, layout: BaseLayout, animations: List[BaseEffectAnimation]):
        self.layout = layout
        self.animations = animations
    
    def apply(self, video_strips: List, audio_analysis: Dict, fps: int) -> bool:
        """
        Zastosuj układ i animacje do stripów.
        
        Args:
            video_strips: Lista stripów wideo
            audio_analysis: Dane analizy audio z beatrix
            fps: Klatki na sekundę
            
        Returns:
            bool: True jeśli sukces
        """
        try:
            # 1. Pobierz rozdzielczość sceny
            import bpy
            resolution = (
                bpy.context.scene.render.resolution_x,
                bpy.context.scene.render.resolution_y
            )
            
            # 2. Zastosuj układ
            positions = self.layout.calculate_positions(len(video_strips), resolution)
            self._apply_layout(video_strips, positions)
            
            # 3. Zastosuj animacje
            for animation in self.animations:
                events = self._extract_events(audio_analysis, animation.trigger)
                if events:
                    for strip in video_strips:
                        animation.apply_to_strip(strip, events, fps)
            
            return True
            
        except Exception as e:
            print(f"Error in AnimationCompositor: {e}")
            return False
    
    def _apply_layout(self, strips: List, positions: List[LayoutPosition]):
        """Zastosuj pozycje układu do stripów."""
        for strip, position in zip(strips, positions):
            if hasattr(strip, 'transform'):
                strip.transform.offset_x = position.x
                strip.transform.offset_y = position.y
                strip.transform.scale_x = position.scale
                strip.transform.scale_y = position.scale
    
    def _extract_events(self, audio_analysis: Dict, trigger: str) -> List[float]:
        """Wyciągnij eventy z analizy audio."""
        events = audio_analysis.get("animation_events", {})
        
        trigger_map = {
            "bass": "energy_peaks",
            "beat": "beats",
            "energy_peaks": "energy_peaks",
            "sections": "sections"
        }
        
        event_key = trigger_map.get(trigger, trigger)
        return events.get(event_key, [])
```

## Plan implementacji TDD

### Faza 1: Testy i implementacja RandomLayout

```python
# tests/test_random_layout.py
class TestRandomLayout:
    def test_random_layout_basic(self):
        """Test podstawowego losowego układu."""
        layout = RandomLayout(seed=42)
        positions = layout.calculate_positions(4, (1920, 1080))
        
        assert len(positions) == 4
        for pos in positions:
            assert -960 <= pos.x <= 960  # W granicach ekranu
            assert -540 <= pos.y <= 540
            assert 0.3 <= pos.scale <= 0.8  # W granicach skali
    
    def test_random_layout_no_overlap(self):
        """Test układu bez nakładania się."""
        layout = RandomLayout(overlap_allowed=False, seed=42)
        positions = layout.calculate_positions(3, (1920, 1080))
        
        # Sprawdź czy pozycje się nie nakładają
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i+1:], i+1):
                assert not self._check_overlap(pos1, pos2)
    
    def test_random_layout_with_margin(self):
        """Test układu z marginesem."""
        layout = RandomLayout(margin=0.1, seed=42)
        positions = layout.calculate_positions(2, (1920, 1080))
        
        margin_x = 96  # 10% z 960
        margin_y = 54  # 10% z 540
        
        for pos in positions:
            assert -960 + margin_x <= pos.x <= 960 - margin_x
            assert -540 + margin_y <= pos.y <= 540 - margin_y
```

### Faza 2: Testy i implementacja animacji

```python
# tests/test_scale_animation.py
class TestScaleAnimation:
    def test_scale_animation_basic(self, mock_strip):
        """Test podstawowej animacji skali."""
        animation = ScaleAnimation(trigger="bass", intensity=0.3)
        events = [1.0, 2.0, 3.0]  # Sekundy
        fps = 30
        
        success = animation.apply_to_strip(mock_strip, events, fps)
        
        assert success
        # Sprawdź czy keyframes zostały dodane
        assert mock_strip.transform.scale_x == 1.0  # Końcowa wartość
        
    def test_scale_animation_without_transform(self, mock_strip_no_transform):
        """Test animacji na stripie bez transform."""
        animation = ScaleAnimation()
        events = [1.0]
        
        success = animation.apply_to_strip(mock_strip_no_transform, events, 30)
        
        assert not success  # Powinno zwrócić False

# tests/test_shake_animation.py
class TestShakeAnimation:
    def test_shake_animation_random(self, mock_strip):
        """Test losowych drgań."""
        animation = ShakeAnimation(intensity=10.0, random_direction=True)
        events = [1.0, 2.0]
        
        success = animation.apply_to_strip(mock_strip, events, 30)
        
        assert success
        # Pozycja końcowa powinna wrócić do (0, 0)
        assert mock_strip.transform.offset_x == 0
        assert mock_strip.transform.offset_y == 0
```

### Faza 3: Testy i implementacja kompozytora

```python
# tests/test_animation_compositor.py
class TestAnimationCompositor:
    def test_compositor_full_pipeline(self, mock_video_strips, mock_audio_analysis):
        """Test pełnego pipeline: layout + animacje."""
        layout = RandomLayout(seed=42)
        animations = [
            ScaleAnimation(trigger="bass", intensity=0.2),
            ShakeAnimation(trigger="beat", intensity=5.0)
        ]
        
        compositor = AnimationCompositor(layout, animations)
        success = compositor.apply(mock_video_strips, mock_audio_analysis, 30)
        
        assert success
        # Sprawdź czy pozycje zostały ustawione
        for strip in mock_video_strips:
            assert hasattr(strip.transform, 'offset_x')
            assert hasattr(strip.transform, 'scale_x')
```

### Faza 4: Integracja z AnimationEngine

```python
# Nowy CompositionalAnimator do dodania do AnimationEngine
class CompositionalAnimator:
    def get_animation_mode(self) -> str:
        return "compositional"
    
    def can_handle(self, animation_mode: str) -> bool:
        return animation_mode == "compositional"
    
    def animate(self, video_strips: List, animation_data: Dict, fps: int) -> bool:
        # Odczytaj konfigurację z environment variables
        layout_config = self._parse_layout_config()
        animation_config = self._parse_animation_config()
        
        # Stwórz layout
        layout = self._create_layout(layout_config)
        
        # Stwórz animacje
        animations = self._create_animations(animation_config)
        
        # Zastosuj przez kompozytor
        compositor = AnimationCompositor(layout, animations)
        return compositor.apply(video_strips, animation_data, fps)
```

## Harmonogram implementacji

### Dzień 1: Struktura i RandomLayout
1. ✅ Utworzenie struktury katalogów dla nowych modułów
2. ✅ Implementacja BaseLayout i LayoutPosition
3. ✅ Testy dla RandomLayout (TDD)
4. ✅ Implementacja RandomLayout

### Dzień 2: Refaktoryzacja i animacje
1. ⏸️ Refaktoryzacja VintageFilmEffects (odłożona - animacje działają niezależnie)
2. ✅ Implementacja BaseEffectAnimation
3. ✅ Testy dla ScaleAnimation, ShakeAnimation, RotationWobbleAnimation
4. ✅ Implementacja animacji

### Dzień 3: Kompozytor i integracja
1. ✅ Testy dla AnimationCompositor
2. ✅ Implementacja AnimationCompositor
3. ✅ Testy integracyjne (41 testów przechodzi)
4. ✅ Dodanie CompositionalAnimator do AnimationEngine
5. ✅ Testy integracji z AnimationEngine (64 testy przechodzą!)

### Dzień 4: Dokumentacja i demo
1. ✅ Aktualizacja CLAUDE.md
2. ✅ Przykłady użycia (compositional-animation-examples.md)
3. ✅ Demo z rzeczywistymi plikami

## Konfiguracja przez zmienne środowiskowe

```bash
# RandomLayout z animacjami
export BLENDER_VSE_ANIMATION_MODE="compositional"
export BLENDER_VSE_LAYOUT_TYPE="random"
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,margin=0.05,min_scale=0.3,max_scale=0.7,seed=42"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.3:2,shake:beat:10.0:2,rotation:beat:1.0:3"

cinemon-blend-setup ./recording_dir
```

## Oczekiwane rezultaty

1. **Elastyczność**: Możliwość dowolnego łączenia układów i animacji
2. **Rozszerzalność**: Łatwe dodawanie nowych układów i animacji
3. **Testowalnośc**: Każdy komponent w pełni testowalny
4. **Czytelność**: Jasna separacja odpowiedzialności
5. **Wydajność**: Brak duplikacji kodu dzięki refaktoryzacji

## Potencjalne wyzwania

1. **Kolizje w RandomLayout**: Algorytm unikania kolizji może być kosztowny
2. **Kompozycja animacji**: Niektóre animacje mogą się konfliktować (np. dwa shake)
3. **Performance**: Wiele keyframes może spowolnić Blender
4. **Backwards compatibility**: Zachowanie zgodności z istniejącymi animatorami