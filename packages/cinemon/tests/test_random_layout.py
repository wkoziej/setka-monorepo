"""Tests for RandomLayout implementation."""

from vse.layouts import LayoutPosition, RandomLayout


class TestRandomLayout:
    """Test suite for RandomLayout."""

    def test_random_layout_basic(self):
        """Test podstawowego losowego układu."""
        layout = RandomLayout(seed=42)
        positions = layout.calculate_positions(4, (1920, 1080))

        assert len(positions) == 4
        for pos in positions:
            assert isinstance(pos, LayoutPosition)
            assert -960 <= pos.x <= 960  # W granicach ekranu
            assert -540 <= pos.y <= 540
            assert 0.3 <= pos.scale <= 0.8  # W granicach skali

    def test_random_layout_deterministic_with_seed(self):
        """Test że seed daje powtarzalne rezultaty."""
        layout1 = RandomLayout(seed=42)
        layout2 = RandomLayout(seed=42)

        positions1 = layout1.calculate_positions(3, (1920, 1080))
        positions2 = layout2.calculate_positions(3, (1920, 1080))

        for pos1, pos2 in zip(positions1, positions2):
            assert pos1.x == pos2.x
            assert pos1.y == pos2.y
            assert pos1.scale == pos2.scale

    def test_random_layout_no_overlap(self):
        """Test układu bez nakładania się."""
        layout = RandomLayout(overlap_allowed=False, seed=42, min_scale=0.3, max_scale=0.4)
        positions = layout.calculate_positions(3, (1920, 1080))

        # Sprawdź czy pozycje się nie nakładają
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i+1:], i+1):
                assert not self._check_overlap(pos1, pos2, (1920, 1080))

    def test_random_layout_with_margin(self):
        """Test układu z marginesem."""
        layout = RandomLayout(margin=0.1, seed=42)
        positions = layout.calculate_positions(2, (1920, 1080))

        half_width = 960
        half_height = 540
        margin_x = int(half_width * 0.1)  # 10% margin
        margin_y = int(half_height * 0.1)

        for pos in positions:
            assert -half_width + margin_x <= pos.x <= half_width - margin_x
            assert -half_height + margin_y <= pos.y <= half_height - margin_y

    def test_random_layout_scale_range(self):
        """Test że skala jest w zadanym zakresie."""
        layout = RandomLayout(min_scale=0.5, max_scale=0.7, seed=42)
        positions = layout.calculate_positions(5, (1920, 1080))

        for pos in positions:
            assert 0.5 <= pos.scale <= 0.7

    def test_random_layout_single_strip(self):
        """Test dla pojedynczego stripu."""
        layout = RandomLayout(seed=42)
        positions = layout.calculate_positions(1, (1920, 1080))

        assert len(positions) == 1
        assert isinstance(positions[0], LayoutPosition)

    def test_random_layout_zero_strips(self):
        """Test dla zero stripów."""
        layout = RandomLayout()
        positions = layout.calculate_positions(0, (1920, 1080))

        assert len(positions) == 0

    def test_random_layout_supports_any_strip_count(self):
        """Test że RandomLayout obsługuje dowolną liczbę stripów."""
        layout = RandomLayout()

        assert layout.supports_strip_count(1)
        assert layout.supports_strip_count(10)
        assert layout.supports_strip_count(100)
        assert not layout.supports_strip_count(0)  # Zero nie jest obsługiwane

    def _check_overlap(self, pos1: LayoutPosition, pos2: LayoutPosition, resolution: tuple) -> bool:
        """
        Helper do sprawdzania czy dwie pozycje się nakładają.
        
        Zakłada że stripy są kwadratowe i używa przybliżonej kalkulacji.
        """
        width, height = resolution

        # Przybliżona szerokość/wysokość stripu na podstawie skali
        strip1_half_width = int(width * pos1.scale * 0.5)
        strip1_half_height = int(height * pos1.scale * 0.5)
        strip2_half_width = int(width * pos2.scale * 0.5)
        strip2_half_height = int(height * pos2.scale * 0.5)

        # Sprawdź czy prostokąty się nakładają
        x_overlap = abs(pos1.x - pos2.x) < (strip1_half_width + strip2_half_width)
        y_overlap = abs(pos1.y - pos2.y) < (strip1_half_height + strip2_half_height)

        return x_overlap and y_overlap
