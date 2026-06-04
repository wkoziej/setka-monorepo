# ABOUTME: Testy czystej logiki setka-tray (tabela menu → komendy) bez importu GTK.
# ABOUTME: Importuje moduł przez SourceFileLoader, by uniknąć rozszerzenia .py.

import importlib.util
import importlib.machinery
import pathlib
import pytest

# Ścieżka absolutna do skryptu setka-tray (bez rozszerzenia .py)
TRAY_SCRIPT = pathlib.Path(__file__).parent.parent / "bin" / "setka-tray"


def load_tray_module():
    """Ładuje moduł setka-tray bez importu GTK (import gi jest w main())."""
    loader = importlib.machinery.SourceFileLoader("setka_tray", str(TRAY_SCRIPT))
    spec = importlib.util.spec_from_loader("setka_tray", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tray():
    return load_tray_module()


class TestMenuStructure:
    """Testy czystej tabeli menu (bez GTK)."""

    def test_pokaz_okna_mapuje_na_setka_live_show(self, tray):
        """Pozycja 'Pokaż okna' musi mapować na ['setka-live', 'show']."""
        items = tray.build_menu_items()
        labels = {label: argv for label, argv in items if label is not None}
        assert "Pokaż okna" in labels, "Brak pozycji 'Pokaż okna' w menu"
        assert labels["Pokaż okna"] == ["setka-live", "show"]

    def test_usun_ostatnie_nagranie_mapuje_na_delete_last(self, tray):
        """Pozycja 'Usuń ostatnie nagranie' musi mapować na ['setka-live', 'delete-last']."""
        items = tray.build_menu_items()
        labels = {label: argv for label, argv in items if label is not None}
        assert "Usuń ostatnie nagranie" in labels, (
            "Brak pozycji 'Usuń ostatnie nagranie' w menu"
        )
        assert labels["Usuń ostatnie nagranie"] == ["setka-live", "delete-last"]

    def test_nowy_projekt_bitwig_mapuje_na_new_take(self, tray):
        """Pozycja 'Nowy projekt Bitwig' musi mapować na ['setka-live', 'new-take']."""
        items = tray.build_menu_items()
        labels = {label: argv for label, argv in items if label is not None}
        assert "Nowy projekt Bitwig" in labels, (
            "Brak pozycji 'Nowy projekt Bitwig' w menu"
        )
        assert labels["Nowy projekt Bitwig"] == ["setka-live", "new-take"]

    def test_zakoncz_mapuje_na_brak_komendy(self, tray):
        """Pozycja 'Zakończ' musi mieć argv=None (czyste wyjście, brak komendy zewnętrznej)."""
        items = tray.build_menu_items()
        labels = {label: argv for label, argv in items if label is not None}
        assert "Zakończ" in labels, "Brak pozycji 'Zakończ' w menu"
        assert labels["Zakończ"] is None, (
            "Zakończ powinno mieć argv=None, nie wywoływać komendy"
        )

    def test_menu_zawiera_separator(self, tray):
        """Menu powinno zawierać przynajmniej jeden separator (krotka z label=None)."""
        items = tray.build_menu_items()
        separators = [item for item in items if item[0] is None]
        assert len(separators) >= 1, "Brak separatora w menu"

    def test_menu_zwraca_liste_krotek(self, tray):
        """build_menu_items() zwraca listę krotek (label, argv)."""
        items = tray.build_menu_items()
        assert isinstance(items, list), "build_menu_items() musi zwracać listę"
        for item in items:
            assert isinstance(item, tuple) and len(item) == 2, (
                f"Każda pozycja musi być krotką (label, argv), got: {item!r}"
            )
