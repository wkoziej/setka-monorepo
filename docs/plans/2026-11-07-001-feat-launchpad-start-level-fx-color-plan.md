---
title: "feat: Lower Launchpad start level by one step and change FX-off LED color to dim amber"
type: feat
status: completed
date: 2026-11-07
origin: docs/brainstorms/2026-11-01-launchpad-rc600-requirements.md  # exists on branch feat/launchpad-rc600
---

# feat: Lower Launchpad start level by one step and change FX-off LED color to dim amber

## Overview

Two small changes in the `launchpad-rc600` translator (`lp-rc600`):

1. The start level of the RC-600 loop tracks (TRK1–6 LEVEL) goes down by one Launchpad row: from 71 to 57.
2. The 4 FX pads (T FX A–D) in the "off" state show dim amber instead of dim green.

## Problem Frame

- After a live test, the default loop volume is too loud. The user wants one row less on the Launchpad.
- The FX pads in the "off" state are dim green. The fader bars are also green, so the FX pads do not stand out. The user asked for blue. The Launchpad Mini (1st gen) has only red and green LEDs (velocity = `16 × green + red + 12`, each 0–3), so blue is not possible. The user chose **dim amber `color(1, 1)`** (decision in this planning session).

## Requirements Trace

- R1. At startup, the translator sends level 57 (CC 73) to TRK1–6 LEVEL and shows LED bars from row index 3 down (5 lit pads per column). Changes origin R4 (was 71).
- R2. An FX pad in the "off" state shows dim amber (`color(1, 1)` = velocity 29 / 0x1D). The "on" state stays full red. The fader bars stay full green.
- R3. README and origin R4 describe the new start level and the new FX-off color.

## Scope Boundaries

- No change to the level table (`LEVELS`, `_LEVEL_CC`), the ASSIGN config, the simulator, or the FX "on" color.
- No support for other Launchpad models (RGB). Not requested.
- No new config option for the start level. A constant change is enough (KISS).

## Context & Research

### Branch prerequisite

The `launchpad-rc600` package is **not on `master`**. It exists only on branch `feat/launchpad-rc600` (commit `89c6da0`, one commit ahead of `master`). The work must start from that branch (or after it merges). This worktree (`emdash/perky-peas-worry-zcp4e`) is on `master` and has no such package.

### Relevant Code and Patterns

- `packages/launchpad-rc600/src/launchpad_rc600/translator.py` — `START_LEVEL = 71` (with the comment "about 70%…"); `LEVELS = (0, 14, 29, 43, 57, 71, 86, 100)`. One step down from 71 = 57 → CC 73 (`_LEVEL_CC`). CC 73 → 57 is verified on the real RC-600 (README, 2026-11-01).
- `packages/launchpad-rc600/src/launchpad_rc600/launchpad.py` — `FX_OFF = color(0, 1)  # dim green`. `FX_ON = color(3, 0)`, `FADER_ON = color(0, 3)`.
- `packages/launchpad-rc600/README.md` — layout section ("Red = on, dim green = off"), start state ("all levels 71 (about 70%…)"), manual check steps 1 and 3 ("green bars from row 3 down", "dim green FX pads", "off (dim green)").
- `docs/brainstorms/2026-11-01-launchpad-rc600-requirements.md` R4 — "wszystkie poziomy 71".

### Tests that hard-code the current values

- `tests/unit/test_launchpad.py` — `FX_OFF == color(0, 1)  # dim green`.
- `tests/unit/test_translator.py` — `levels == [71] * 6` (several tests), startup CC value 90, startup LED column `[OFF] * 2 + [FADER_ON] * 6` with comment "start level 71 = row 2".
- `tests/integration/test_translator_app.py` — startup CC `cc_for_level(71)`.
- `tests/e2e/test_chain.py` — simulator log lines `"{target} ? → 71"`, `"TRK1 LEVEL 71 → 0"`, `"TRK3 LEVEL 71 → 43"`, `"TRK6 LEVEL 71 → 100"`.

### Institutional Learnings

- Origin plan and handoff: LED color = `16 × green + red + 12`; the FX colors were the user's decision (red = on, dim green = off). This plan replaces only the "off" color.

## Key Technical Decisions

- **Start level 57 (row index 3)**: "one step on the Launchpad" = one row in `LEVELS`. 57 is the next lower value after 71 and its CC (73) is verified on the device.
- **Dim amber `color(1, 1)`**: blue is not possible on this hardware. Dim amber differs from the green fader bars and from the red "on" state. User choice.
- **Tests reference the constant where possible**: in unit/integration tests, use `START_LEVEL` / `cc_for_level(START_LEVEL)` instead of the literal 71/57 where the test checks "start state", so a later change touches one place. Keep literal values in tests that check the exact numbers (e.g. the LED column for the start row, the `FX_OFF == color(1, 1)` check), because they document the expected hardware result. The e2e test matches simulator log text, so it keeps literals (57).

## Open Questions

### Resolved During Planning

- Which LED color replaces green, if blue is not possible? → Dim amber `color(1, 1)` (user answer).
- How big is "one step"? → One Launchpad row: 71 → 57.

### Deferred to Implementation

- Visual check on the physical Launchpad: is dim amber `(1, 1)` clearly visible and distinct on stage? If it is too weak, the user may pick `(2, 2)`. Only the constant changes.

## Implementation Units

- [x] **Unit 1: Start level 57**

**Goal:** The translator starts with TRK1–6 LEVEL = 57.

**Requirements:** R1

**Dependencies:** Branch `feat/launchpad-rc600` checked out.

**Files:**
- Modify: `packages/launchpad-rc600/src/launchpad_rc600/translator.py`
- Test: `packages/launchpad-rc600/tests/unit/test_translator.py`
- Test: `packages/launchpad-rc600/tests/integration/test_translator_app.py`
- Test: `packages/launchpad-rc600/tests/e2e/test_chain.py`

**Approach:**
- Change `START_LEVEL` to 57. Update its comment to an evergreen description (e.g. "about 57%, leaves room to raise to unity (100)").

**Execution note:** Test-first: change the test expectations to 57 first, see them fail, then change the constant.

**Patterns to follow:** existing startup tests in `test_translator.py`.

**Test scenarios:**
- Happy path: new translator → `levels == [57] * 6`.
- Happy path: `startup()` → 6 CC on channel 13, CC 64–69, value 73; then 4 FX CC with value 0.
- Happy path: `startup()` LED frame → each fader column is `[OFF] * 3 + [FADER_ON] * 5` (start level 57 = row 3).
- Edge case: ignored/invalid messages leave `levels == [57] * 6` (the tests that now check `[71] * 6`).
- Integration: `test_translator_app` startup messages equal `cc_for_level(57)` for CC 64–69.
- Integration (e2e): simulator logs `"{target} ? → 57"` at start; fader presses log `"TRK1 LEVEL 57 → 0"`, `"TRK3 LEVEL 57 → 43"`, `"TRK6 LEVEL 57 → 100"`; the unused-pad marker check expects `"TRK1 LEVEL 57 → 0"`.

**Verification:**
- All `launchpad-rc600` tests (unit, integration, e2e) pass with clean output.
- Running `rc600-sim` + `lp-rc600 --out "RC-600 SIM"` shows level 57 on all 6 tracks.

- [x] **Unit 2: FX-off color dim amber**

**Goal:** FX pads in the "off" state show dim amber.

**Requirements:** R2

**Dependencies:** None (independent of Unit 1).

**Files:**
- Modify: `packages/launchpad-rc600/src/launchpad_rc600/launchpad.py`
- Test: `packages/launchpad-rc600/tests/unit/test_launchpad.py`

**Approach:**
- Change `FX_OFF` to `color(1, 1)` and the comment to `# dim amber`. `translator.py` uses the constant, so no other code changes.

**Execution note:** Test-first.

**Test scenarios:**
- Happy path: `FX_OFF == color(1, 1)`, and `color(1, 1) == 29` (0x1D).
- Edge case: `FX_OFF` differs from `FADER_ON` and from `FX_ON` (guards the reason for the change: FX-off must not look like a fader bar).
- Integration: the existing translator tests (startup frame FX pads, FX toggle off → `FX_OFF`) pass without change, because they reference the constant.

**Verification:**
- Unit tests pass. On the physical Launchpad, FX pads at start are dim amber; press → red; press again → dim amber.

- [x] **Unit 3: Docs**

**Goal:** Docs describe the new start level and color.

**Requirements:** R3

**Dependencies:** Units 1 and 2.

**Files:**
- Modify: `packages/launchpad-rc600/README.md`
- Modify: `docs/brainstorms/2026-11-01-launchpad-rc600-requirements.md` (R4)

**Approach:**
- README: "Red = on, dim amber = off"; start state "all levels 57 (…room to raise them to unity 100)"; manual check step 1 → "levels 57", "green bars from row 4 down" (README counts rows from 1; 57 = row index 3) and "dim amber FX pads"; step 3 → "off (dim amber)".
- Origin R4: level 57; add a short note that it was lowered from 71 after a live test.

**Test scenarios:** Test expectation: none — documentation only.

**Verification:**
- `grep` for "dim green" and "levels 71" in the package README returns no results.

## Risks & Dependencies

- **Sound change on the real RC-600:** at startup the translator now sets all tracks to 57 (quieter than before). This is the goal, but the user must expect it at the first run.
- **Branch dependency:** the work fails if done on `master` (package missing). Start from `feat/launchpad-rc600`.
- **Dim amber visibility:** low brightness `(1, 1)` may be weak in light. Mitigation: deferred visual check; change one constant if needed.

## Sources & References

- Origin document: `docs/brainstorms/2026-11-01-launchpad-rc600-requirements.md` (branch `feat/launchpad-rc600`)
- Origin plan: `docs/plans/2026-11-01-001-feat-launchpad-rc600-translator-and-simulator-plan.md` (branch `feat/launchpad-rc600`)
- Code: `packages/launchpad-rc600/src/launchpad_rc600/translator.py` (`START_LEVEL`), `packages/launchpad-rc600/src/launchpad_rc600/launchpad.py` (`FX_OFF`)
