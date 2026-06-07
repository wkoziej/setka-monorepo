<!-- ABOUTME: Pomiar literalnej (verbatim) duplikacji między root CLAUDE.md a per-package CLAUDE.md. -->
<!-- ABOUTME: Artefakt decyzyjny Unit 0 planu 2026-06-06-001 — podstawa wyboru split-vs-trim. -->

# Inwentaryzacja duplikacji CLAUDE.md (Unit 0)

Pomiar wykonany na wersji z `origin/master` (worktree), NIE na niezacommitowanej `M CLAUDE.md`.

## Rozmiary plików (linie)

| Plik | Linie |
|---|---|
| `CLAUDE.md` (root) | 370 |
| `packages/cinemon/CLAUDE.md` | 555 |
| `packages/obsession/CLAUDE.md` | 339 |
| `packages/beatrix/CLAUDE.md` | 184 |
| `packages/medusa/CLAUDE.md` | 145 |
| `packages/common/CLAUDE.md` | 88 |
| **Razem** | **1681** |

## Literalna (verbatim / near-verbatim) duplikacja root ↔ pakiet

Liczę TYLKO fakty powtórzone dosłownie lub prawie-dosłownie. Nakładanie tematyczne
(ten sam temat, inne słowa/ścieżki/perspektywa) NIE liczy się jako duplikat.

| # | Powtórzony fragment | Lokalizacje | Linie | Charakter |
|---|---|---|---|---|
| 1 | Boilerplate nagłówka: `# CLAUDE.md` + „This file provides guidance to Claude Code (claude.ai/code)…" | root:1-3 oraz wszystkie 5 pakietów:1-3 | ~2 treści × 5 = ~10 | czysty boilerplate, nie „fakt" |
| 2 | `uv sync` (instalacja workspace) | root:26, beatrix:14, obsession:38, medusa:36 | ~4 | generyczna komenda uv |
| 3 | `uv run --package <pkg> pytest` | root:53-57, beatrix:26, (warianty lokalne w pozostałych) | ~2 | częściowe; pakiety mają wersje lokalne |
| 4 | `uv run ruff check / ruff format` | root:42-44, cinemon:55-57 | ~3 | generyczna komenda uv |
| 5 | `uv sync --group dev` | beatrix:17, obsession:42 | ~2 | generyczna (między pakietami, nie z rootem) |

**Suma literalnych duplikatów faktów (bez boilerplate nagłówka): ≈ 9–11 linii**,
w całości generyczne komendy `uv` (i tak udokumentowane w `~/.claude/docs/using-uv.md`).

## Nakładanie TEMATYCZNE (NIE liczone jako literalny duplikat)

Te obszary opisują podobne tematy, ale każdym plikiem innymi słowami / z własnej perspektywy
i z innymi ścieżkami — to NIE jest literalna duplikacja:

- **Diagram `recording_name/`**: root:169-183 (kanon), obsession:179-193, cinemon:248-263,
  beatrix:113-117. Każdy wariant inny (cinemon dodaje `animation_config.yaml`, beatrix
  okrojony do extracted+analysis). Wspólny fakt strukturalny używany przez >1 pakiet → kandydat do roota.
- **„analysis JSON format / animation_events"**: obsession:309-338, cinemon:236-243 — różne
  poziomy szczegółu, oba pochodne od kontraktu beatrix.
- **Animation modes (beat-switch/energy-pulse/multi-pip)**: opisane w root, obsession, cinemon —
  za każdym razem inną narracją.

## Obserwacje poboczne (poza zakresem tego refactoru — do osobnych issue)

- `obsession/CLAUDE.md` zawiera dużą sekcję o Blender VSE / animacjach / „Phase 3A MVP"
  (linie 145-338), która tematycznie należy do cinemon i wygląda na przestarzałą kopię.
  NIE ruszam treści w tym refactorze (non-goal: przepisywanie treści).
- `medusa/CLAUDE.md` podaje „~65% complete" (linia 133) — stan-w-czasie, kandydat do odświeżenia.

## Rekomendacja (próg z planu)

Próg planu: „<~10 linii literalnych → trim w miejscu; dużo LUB waży cross-tool standard → split".

- **Z perspektywy DRY/duplikacji: trim wygrywa.** Literalnych duplikatów jest ~10 linii,
  w całości generycznych. Pełny split (12 plików: 6× AGENTS.md + 6× stub) nie jest uzasadniony
  samą redukcją duplikacji — wprowadziłby więcej plików niż usuwa duplikatów.
- **Z perspektywy STRATEGICZNEJ: decyzja należy do użytkownika.** Pierwotny cel
  (AGENTS.md jako cross-tool kanon czytany przez Codex/Cursor) jest NIEZALEŻNY od ilości
  duplikacji i pozostaje ważny. Split realizuje ten cel; trim go porzuca.

Wniosek: duplikacja NIE wymusza splitu. O splicie decyduje wyłącznie waga celu cross-tool —
to wybór użytkownika (patrz pytanie w sesji ce:work). Trzecia droga (split tylko w roocie +
trim w pakietach) minimalizuje churn, dając cross-tool widoczność tam, gdzie najważniejsza.
