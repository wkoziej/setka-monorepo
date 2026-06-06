---
date: 2026-06-06
topic: audio-structure-brief-for-cymatic
---

# Structure Brief audio dla autorowania klipu w cymatic

## Problem Frame

Bespoke looki w cymatic autoruje agent LLM na żywo przez Blender MCP, metodą prób —
bez mapy tego, co audio robi w czasie. Jedyny istniejący sygnał struktury,
`animation_events.sections` z beatrix (agglomerative clustering na chroma+MFCC+
spectral_contrast, sztywne `k=10`), jest słabym proxy: marnuje rozdzielczość na
ciszę/intro i scala muzyczny korpus w jeden blok (zweryfikowane na nagraniach
22-37-24 i 15-15-01 — patrz Key Decisions).

Tymczasem realna struktura aranżacji jest czytelna z **energii per stem**: kiedy
który instrument wchodzi i wychodzi. Brakuje warstwy, która zredukuje surową
analizę do zwięzłej, semantycznej formy, jaką agent-autor MCP może przeczytać raz
i od razu podjąć decyzje (który stem mapować, kiedy pojawić/zgasić element, gdzie
umieścić eskalację).

Odbiorcą priorytetowym jest **agent-autor (LLM przez MCP)**, nie tylko człowiek.
To determinuje format: zwięzłe *wnioski*, nie surowe tablice i nie sam obraz.

## Requirements

- R1. Narzędzie czyta `analysis/index.json` nagrania oraz wskazane przez manifest
  per-stem `*_analysis.json` (master + stemy). Bez stemów degraduje się do briefu
  opartego o sam master (degradacja, nie błąd).
- R2. **Per-stem activity** — dla każdego stemu wyznacza przedziały aktywności
  („kto gra kiedy") z wygładzonej, znormalizowanej obwiedni energii broadband;
  scala krótkie luki; oznacza stemy ≈ciche jako „pomiń mapowanie".
- R3. **Eventy ENTER/EXIT** — czasy wejść i wyjść poszczególnych stemów,
  wyprowadzone z R2.
- R4. **Energia mastera w czasie** zredukowana do poziomów (low/mid/high) plus
  wykrycie momentów dropu (skok energii po spadku/ciszy).
- R5. **Output 1 — structure brief**: zwięzły artefakt zaprojektowany pod
  konsumpcję przez agenta MCP — dokładne czasy (≈1 s), semantyka, mały rozmiar
  (rząd setek–niskich tysięcy tokenów). Kanoniczna forma maszynowa (JSON) +
  czytelny render (markdown/tekst) z R2–R4.
- R6. **Output 2 — PNG-podgląd**: arrangement heatmap (stem × czas × energia) +
  panel energii mastera. Gestalt dla ludzkiego oka i agenta multimodalnego.
- R7. Artefakty zapisywane w katalogu nagrania (np. `analysis/`), odkrywalne obok
  istniejących analiz.
- R8. Brief jawnie deklaruje, że podział jest oparty o aktywność/energię, a NIE o
  `beatrix.sections` (uczciwość źródła). `sections` mogą wystąpić najwyżej jako
  opcjonalne tło.

## Success Criteria

- Agent-autor potrafi **z samego briefu** (bez słuchania, bez surowych tablic)
  wskazać: które stemy mapować, kiedy się pojawiają/znikają, gdzie umieścić
  eskalację — z dokładnością ~1 s.
- Stemy ≈ciche (np. `track_3` w 15-15-01) są poprawnie oznaczone do pominięcia.
- Brief mieści się w budżecie rzędu setek–niskich tysięcy tokenów (nie dziesiątki
  tysięcy surowych próbek).
- PNG czytelny okiem — przejścia aranżacji widoczne bez dodatkowego opisu.

## Scope Boundaries

- **Bez** energy/novelty-based segmentacji na sekcje — naiwny podział okazał się
  scalać 106 s w jeden blok; porządna segmentacja to osobny, nietrywialny etap.
- **Bez** wpięcia kanałów `gate_<stem>` do `data_object` (sterowanie GN maszynowo)
  — odłożone jako trzecie ujście warstwy pochodnych.
- **Bez** naprawy `beatrix.sections`.
- **Bez** integracji z fermatą/GUI.
- **Bez** automatycznego sterowania sceną — brief tylko *informuje* agenta-autora,
  decyzje wizualne pozostają po stronie autorowania w MCP.

## Key Decisions

- Odbiorca priorytetowy = agent-autor MCP → format = zwięzły brief (wnioski), nie
  surowy JSON (token-bloat, LLM nie „liczy" z tablic) i nie sam PNG (estymacja
  okiem). PNG zostaje jako pomocniczy gestalt.
- `sections` (chroma+MFCC, `k=10`) odrzucone jako oś struktury — dowód ze spike'ów:
  granice tłoczą się w ciszy intro, korpus scalony; nie pokrywają się z wejściami
  stemów (~58 s, ~120 s w 15-15-01).
- Wartość siedzi w per-stem activity + energii; segmentacja sekcji odłożona, bo
  naiwny active-set scala sustain (gitara) i rozsypuje się na perkusji (m:s migocze
  jako uderzenia, nie sustain).
- Warstwa pochodnych sygnałów ma trzy ujścia (kanały `data_object`, PNG, brief);
  MVP realizuje dwa: brief + PNG.

## Dependencies / Assumptions

- Zakłada wcześniejsze `beatrix analyze-recording` (istnieją per-stem analizy +
  `index.json`).
- Działa najlepiej na nagraniach ze stemami (`mixed/stems/` lub `bitwig/samples/`).
- Host-side numpy (bez `bpy`, bez PyYAML) — zgodnie z podziałem cymatic host/in-Blender.

## Outstanding Questions

### Resolve Before Planning
- (brak — zakres MVP jest jednoznaczny)

### Deferred to Planning
- [Affects R1,R5][Technical] Gdzie umieścić narzędzie: host-side w cymatic
  (`cymatic/src/cymatic/`, naturalne — to dla cymatic, host-side ma numpy) vs nowy
  command w beatrix. Skłaniam się ku cymatic host-side.
- [Affects R5][Technical] Dokładny schemat JSON briefu (pola, nazwy, jednostki).
- [Affects R2,R4][Needs research] Parametry detekcji activity (próg, okno
  wygładzania, scalanie luk) i dropu — strojenie na kilku nagraniach. Perkusja
  (m:s) prawdopodobnie wymaga innego traktowania niż instrument sustain (np.
  „density" zamiast „gate").
- [Affects R6][Technical] Czy i jak dołączać `beatrix.sections` jako tło w PNG/briefie.

## Next Steps

→ `/ce:plan` for structured implementation planning
