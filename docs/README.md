<!-- ABOUTME: Indeks taksonomii katalogu docs/ — rola każdego podkatalogu i powiązanie ze skillami ce:*. -->
<!-- ABOUTME: Mapa nawigacyjna dla ludzi i agentów: co gdzie żyje i wg jakiej konwencji nazewnictwa. -->

# Mapa dokumentacji `docs/`

Ten katalog gromadzi dokumentację procesu (nie kod). Każdy podkatalog ma jedną rolę i
(zwykle) jeden skill `ce:*`, który go produkuje lub konsumuje. Fakty operacyjne dla agentów
żyją w `../AGENTS.md` (nie tutaj).

## Taksonomia katalogów

| Katalog | Cel | Konwencja nazewnictwa | Skill `ce:*` |
|---|---|---|---|
| [`brainstorms/`](brainstorms/) | Dokumenty wymagań — **co** budujemy i **dlaczego** | `YYYY-MM-DD-<temat>-requirements.md` | produkuje `ce:brainstorm` |
| [`plans/`](plans/) | Plany implementacji — **jak** budujemy | `YYYY-MM-DD-NNN-<type>-<nazwa>-plan.md` (`type` ∈ feat/fix/refactor) | produkuje `ce:plan`, wykonuje `ce:work` |
| [`solutions/`](solutions/) | Wiedza instytucjonalna — rozwiązane problemy i wnioski | `YYYY-MM-DD-<slug>.md` | konsumuje `learnings-researcher` |
| [`handoffs/`](handoffs/) | Briefingi przekazania kontekstu między sesjami/osobami | `YYYY-MM-DD-<temat>-briefing.md` | — |
| `ideation/` | Wczesne, surowe szkice przed brainstormem (jeśli istnieją) | luźna | — |
| [`archive/`](archive/) | Martwe/historyczne artefakty zachowane dla proweniencji | jak oryginał + nota w `archive/README.md` | — |

## Konwencje

- **Datowanie:** prefiks `YYYY-MM-DD` na wszystkim. Plany dodają sekwencję `NNN`
  (zerowana per dzień, od `001`).
- **Kolejność sekwencyjna planów:** kolejny plan tego samego dnia → kolejny `NNN`.
- **Kiedy archiwizować:** dokument jest „martwy", gdy opisuje zakończoną/porzuconą pracę,
  której nikt już nie reużywa. Przenoś do `archive/` przez `git mv` (zachowanie historii),
  nigdy nie kasuj. Dokument z nieaktualnym fragmentem, ale wciąż reużywany przez aktywny
  plan, NIE jest martwy — zostaw w miejscu z banerem „stale".

## Dokumenty top-level (poza katalogami)

- `DATA_FLOW_SPECIFICATION.md` — **dokument do aktualizacji w miejscu, NIE archiwum.**
  Ma nieaktualny fragment schematu JSON, ale aktywny plan `plans/2026-05-30-001-feat-gn-audio-visualizer-plan.md`
  reużywa z niego konwencji `blender/render/` i ma otwarty TODO jego aktualizacji.
- `duplication-inventory.md` — efemeryczny artefakt pomiaru (plan `2026-06-06-001`); kandydat
  do `archive/` po zamknięciu tematu reorganizacji.

## Schema dla agentów

Wytyczne dla agentów AI (Claude Code, Codex, Cursor) żyją w `../AGENTS.md` (kanon) oraz
`../packages/<pkg>/AGENTS.md` (per-pakiet). `CLAUDE.md` to tylko stub importujący `AGENTS.md`.
