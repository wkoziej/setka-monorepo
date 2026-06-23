---
title: "fix: Setka monorepo audit remediation (P0 + security + cleanup, cinemon retired)"
type: fix
status: active
date: 2026-06-22
revised: 2026-06-23
origin: scratchpad/setka-audit-2026-06-22.md  # session audit artifact (7-agent whole-repo audit)
deepened: 2026-06-23  # strengthened via 6-persona document-review + 3 user decisions
---

# fix: Setka monorepo audit remediation

## Overview

Whole-repo audit (7 parallel agents) plus a 6-persona document-review of this plan surfaced execution-breaking bugs in 4 of 7 packages, security gaps in `medusa` and `fermata`, severe documentation drift, and a strategically dead package. This plan remediates all findings, delivered as **dependency-ordered branches/PRs (one per package + retirement + repo-wide docs/CI)**.

Three decisions shape this revision:
- **cinemon is retired.** It is ~10 months stale, non-executable on the installed Blender, its docs describe an architecture that does not exist, and `cymatic` (🟢, actively developed) covers the Blender-visual role. Rather than a full VSE migration, cinemon is **deleted** and all references purged. The pipeline becomes `obsession → beatrix → cymatic → medusa`.
- **Target the latest stable Blender (5.1.2, installed at `/Applications/Blender.app`).** Only `cymatic` (Geometry Nodes, not VSE) consumes Blender now, so the `sequences→strips` / deprecated `frame_*` VSE migration is moot — it died with cinemon.
- **Enforce honest 80% per-package coverage.** Today the workspace has no coverage gate at all and per-package gates already fail (obsession 60.39%); cinemon (15.67%) leaves with the package. Gates run per-package from the package directory and must reach 80%, budgeting the test-writing effort.

## Problem Frame

Setka is a `uv` workspace forming a media pipeline with fermata as Tauri GUI orchestrator. Post-retirement, six packages remain. Audit verdicts (cinemon struck):

| Package | Verdict | Headline |
|---|---|---|
| cymatic | 🟢 | Best. Sync harness exemplary; minor edge gaps. Now the sole Blender consumer. |
| setka-common | 🟡 | Shadowed builtin, two sources of truth for dir names, dead `ConfigValidator` |
| obsession | 🟡 | Audio-per-source bug, no ffmpeg timeout, stale docs |
| beatrix | 🟡 | **P0** div-by-zero on short audio; **P0** unversioned JSON contract |
| medusa | 🟡 | **P0** CLI upload broken (`PlatformConfig` split); **🔒P1** Facebook token in URL |
| fermata | 🔴 | **P0** build does not compile → `tauri build` fails; path traversal; no CI; calls retired cinemon |
| ~~cinemon~~ | ⚰️ | **Retired** — deleted; references purged |

Recurring cross-package patterns drive the work: implicit/unversioned contracts, an absent coverage gate, subprocess calls without timeouts, frontend-only input validation, dead code, and documentation describing nonexistent systems.

## Requirements Trace

- **R1 — Execution restored**: fermata builds + compiles; medusa CLI upload works; beatrix survives short/silent audio.
- **R2 — Security closed**: medusa credentials never travel in URLs, logs, `repr`, or `to_dict()`; credentials file is `0600`; OAuth scope minimized. fermata IPC validates paths server-side (no traversal), recordings root canonicalized at startup, CSP set.
- **R3 — Reliability hardened**: subprocess calls in obsession + fermata have timeouts; cymatic render edge cases closed.
- **R4 — Contract explicit & versioned**: `analysis.json` emits `schema_version` + correct `hop_length`(512)/`n_fft`(2048); cymatic validates it (missing version ⇒ assume 1.0); non-finite sanitized at producer; field name consistent across producer/consumer/spec.
- **R5 — Docs match code**: cinemon removed from all docs; CLAUDE.md/per-package CLAUDE.md fiction removed; `DATA_FLOW_SPECIFICATION.md` rewritten to match emitted keys + new pipeline + Blender 5.1.2.
- **R6 — Dead code & dev-cruft removed**: cinemon package retired; unused deps/classes, foreign paths, `snap run blender` (leaves with cinemon).
- **R7 — Test integrity + coverage**: honest per-package coverage measured from the package dir, gated at 80%; mock-theatre replaced; fermata CI runs `cargo test` + `vitest`; crash-path edge tests added.
- **R8 — cinemon retired cleanly**: `packages/cinemon` deleted; all references purged (workspace members, fermata process_runner, CLAUDE.md, data-flow spec); no broken imports anywhere.

## Scope Boundaries

- No new product features. Remediation + one strategic retirement.
- Not redesigning the surviving pipeline; the audit found the layering reasonable.
- cymatic targets the installed Blender 5.1.2; no dual-version support.

### Deferred to Separate Tasks

- (resolved — see Resolved section) fermata "Render" rewired to `cymatic-render`; obsession audio extracted per-source via `-map`.
- medusa `MedusaCore` orchestrator (upload→publish chain): not implemented here; the dead `PublishRequest` is removed.
- medusa persistent `TaskStore` (idempotency): documented as a limitation; durable backend is a follow-up.
- fermata persistent settings store + Settings-button wiring + typed TS↔Rust codegen (ts-rs/specta): all are new behavior — deferred, not in this remediation.

## Context & Research

### Relevant Code and Patterns

- **Contract spec is partly fiction**: `docs/DATA_FLOW_SPECIFICATION.md` declares `analysis.json version:"1.0"` but its body (beat_times, onset_times, frequency_bands-as-list) does NOT match actual beatrix output (`animation_events.{beats,energy_peaks,sections,onsets}`, `frequency_bands.{times,bass_energy,mid_energy,high_energy}`). Both consumers read the CODE shape. **Code is the truth for structure; only the version field is borrowed from the spec.** Unit 8.1 rewrites the spec section, not appends.
- **Good subprocess pattern to copy**: cymatic's ffmpeg invocation (`packages/cymatic/src/cymatic/runner.py`) uses argv lists + `shutil.which` + `timeout` + readable errors. obsession + fermata mirror it. `packages/obsession/.../advanced_scene_switcher_extractor.py` already has `timeout=1800`.
- **Canonical sanitize**: `packages/common/src/setka_common/utils/files.py` `sanitize_filename`. obsession's copy (`core/extractor.py`) is materially stronger (replaces `/\`, collapses `_`, non-empty fallback). The canonical version must become a **superset** of obsession's rules, with a regression test asserting byte-stable output on existing source names — otherwise unifying renames already-extracted files.
- **Dir-name constants**: `RecordingStructureManager.EXTRACTED_DIRNAME` / `ANALYSIS_DIRNAME` are the single source of truth; `MediaDiscovery` (in `setka_common.utils.files`, NOT `cinemon/config/media_discovery.py` as some docs claim) hardcodes the strings.
- **Coverage reality** (verified): workspace `pyproject.toml` defines no coverage gate; each package's `pyproject.toml` sets `--cov-fail-under=80` but only fires when invoked from the package dir (`cd packages/X`). Run correctly, obsession = 60.39% (fails); cinemon = 15.67% (leaves with retirement).

### Institutional Learnings

- `docs/solutions/` is empty. After this work, capture the contract-versioning approach and the cinemon-retirement rationale via `ce:compound`.

### External References

- Blender 5.1 API (bundled MCP docs): cymatic's Geometry-Nodes usage stays; no VSE concern after cinemon removal.

## Key Technical Decisions

- **Retire cinemon over migrating it.** Deleting ~21k LOC removes the single largest source of P0s, dead code, doc fiction, and the coverage drag — and the surviving cymatic already fills the Blender-visual role.
- **Code is the truth for the analysis.json contract structure.** Only the version field aligns to the spec; Unit 8.1 rewrites the spec body to match emitted keys.
- **One authoritative version field name: `schema_version`.** beatrix emits it, cymatic validates it, the spec is updated to use it (replacing `version`).
- **Sanitize unification = superset.** The canonical `sanitize_filename` adopts obsession's stronger rules so no existing extracted filename changes; guarded by a byte-stability regression test.
- **Honest coverage at 80%**, measured per-package from the package directory; CI enforces it.
- **Validation belongs in Rust for fermata IPC**; the frontend checks are bypassable via direct `invoke`.

## Open Questions

### Resolved During Planning / Review

- Scope: everything + cleanup; cinemon = **retire**; Blender = latest stable (5.1.2); coverage = **80%** (user decisions).
- Blender VSE migration: **moot** — cinemon (only VSE consumer) is retired.
- analysis.json: code is truth; field name `schema_version`; missing version ⇒ assume 1.0.
- Phase dependencies (verified): `audio_analyzer.py` imports nothing from setka-common (beatrix Units 2.1/2.2 do not depend on P1); medusa + fermata have no setka-common dependency (independent of P1); only obsession + cymatic + audio_validator genuinely need P1.

### Resolved (user, 2026-06-23)

- **fermata render path**: rewire the "Render" step to **`cymatic-render`** (the surviving 3D GN visualizer). The old VSE-composite output is gone with cinemon; fermata's render now drives cymatic. (Unit 7.4.)
- **obsession audio**: extract **per-source via `-map`** — each `has_audio` source gets its own correctly-mapped audio track (no more N identical copies). (Unit 5.1.)

## Phased Delivery

Phases map 1:1 to PRs. Dependency-verified ordering:

```
P1 common ─┬─► P3 cymatic        P2 beatrix (audio_analyzer: no P1 dep; only Unit 2.3 validator needs P1)
           ├─► P5 obsession           │
           └─► (P2 Unit 2.3 only)     └─► P3 cymatic (contract consumption)

P4 retire cinemon ──► P7 fermata (must drop cinemon calls)
P6 medusa  (independent — no setka-common dep)
P0' CI scaffolding (lands early, before P8)
P8 repo docs/CI  ◄── after P1–P7
```

- **beatrix P0/contract (Units 2.1, 2.2) can land in parallel with P1** — `audio_analyzer.py` imports nothing from common. Only Unit 2.3 (validator) waits for P1.
- **medusa (P6) and fermata (P7) do not depend on P1** (no setka-common dependency). obsession (P5) and cymatic (P3) do (sanitize + contract).
- **P7 fermata depends on P4** (cinemon retirement) so it can drop the cinemon invocation paths.
- **CI scaffolding** (the workflow files + per-package gate config) lands early so rot protection exists during the work; only the doc-truth half of P8 needs everything merged.

## Implementation Units

### Phase 1 — `fix/common-foundation` (R5, R6, R7)

- [ ] **Unit 1.1: API hygiene & dead-code removal**

**Goal:** Remove footguns and dead abstractions in the foundation.
**Requirements:** R6.
**Files:** Modify `packages/common/src/setka_common/exceptions.py` (remove/rename builtin-shadowing `FileNotFoundError`; base `ConfigValidationError` on `SetkaCommonError`); `packages/common/src/setka_common/config/yaml_config.py` (drop double path resolution in `load_config`; remove dead dict-`resolution` branches; remove unused `_validate_for_blender_execution`); Delete `packages/common/src/setka_common/config/validation.py` (`ConfigValidator` — zero call sites) + its `__init__.py` export; Modify `packages/common/src/setka_common/file_structure/specialized/recording.py` (remove redundant `is_valid` override); `packages/common/pyproject.toml` (drop unused `pathlib-extensions`).
**Approach:** `ConfigValidator` is a public export documented in `packages/common/CLAUDE.md` — the grep-before-delete must include the `blender_addon` symlinked copy and non-package scripts (`obs_script`), and Unit 8.1 must drop it from that CLAUDE.md. Keep `is_valid`/`exists` consistent with `find_recording_structure` (which requires `metadata.json`).
**Test scenarios:**
- Edge case: `RecordingStructure.exists()` returns False when `extracted_dir` missing but other files present.
- Error path: `except SetkaCommonError` now catches `ConfigValidationError`.
- Happy path: `load_config` with relative paths + `base_directory` resolves once, idempotent for absolutes.
**Verification:** `cd packages/common && uv run --package setka-common pytest` green at 80%; repo-wide grep (incl. blender_addon symlink, obs_script) shows no references to deleted symbols.

- [ ] **Unit 1.2: Single source of truth — sanitize (superset) + dir-name constants**

**Goal:** One `sanitize_filename` and one set of dir-name constants; no filename churn.
**Requirements:** R6.
**Dependencies:** Unit 1.1.
**Files:** Modify `packages/common/src/setka_common/utils/files.py` (`MediaDiscovery` uses `EXTRACTED_DIRNAME`/`ANALYSIS_DIRNAME`; make `sanitize_filename` a superset of obsession's rules — replace `/\`, collapse repeated `_`, non-empty fallback; export from `__init__.py`).
**Approach:** Diff the two implementations on real OBS source names first. obsession adopts the canonical version in Phase 5.
**Test scenarios:**
- Regression: canonical `sanitize_filename` produces byte-identical output to obsession's current impl on real source names (no rename of existing files).
- Edge case: `detect_main_audio` when `main_audio.m4a` coexists with other audio files.
- Happy path: renaming a dir-name constant updates `MediaDiscovery` (single source).
**Verification:** `cd packages/common && uv run --package setka-common pytest`; workspace-wide tests still green.

- [ ] **Unit 1.3: setka-common test gaps** *(renamed from "Foundation test gaps")*

**Goal:** Cover the setka-common base layer (scoped to the common package only).
**Requirements:** R7.
**Dependencies:** Unit 1.1.
**Files:** Modify/Create tests under `packages/common/tests/`.
**Approach:** The `VALID_*` vs `AnimationSpec.Literal` drift-guard moves OUT of here (AnimationSpec lived in cinemon, now retired) — drop it.
**Test scenarios:**
- Happy path: base `StructureManager.create_structure`/`get_structure`/`ensure_directory` (currently zero coverage).
**Verification:** `cd packages/common && uv run --package setka-common pytest --cov` ≥80%.

### Phase 2 — `fix/beatrix-contract` (R1, R4, R7) — *can land parallel with P1*

- [ ] **Unit 2.1: Crash hardening on short AND silent audio**

**Goal:** Stop `_find_bass_peaks` crashing on degenerate input — two distinct failure modes.
**Requirements:** R1.
**Dependencies:** None (audio_analyzer.py imports nothing from common).
**Files:** Modify `packages/beatrix/src/beatrix/core/audio_analyzer.py`; tests.
**Approach:** (a) **Short/empty**: guard `if len(times) < 2 or times[-1] <= 0: return []`; `distance = max(1, int(...))`. (b) **Silent-but-long** (distinct — `times[-1]≈duration` so the first guard never fires, but `np.percentile(zeros,75)==0` makes `find_peaks(height=0)` flag every sample): detect near-zero band energy (`max(band) < eps`) and return `[]` before `find_peaks`. Add `if len(y) == 0` guard after `librosa.load(..., mono=True)`.
**Execution note:** Failing tests first, one per mode.
**Test scenarios:**
- Error path: ≤10 ms / 1-sample audio → no ZeroDivisionError/IndexError, empty peaks.
- Edge case: 1 s of silence → `energy_peaks == []` and `beat_count == 0` with explicit no-rhythm signal (assert empty peaks, not merely "no crash").
**Verification:** `cd packages/beatrix && uv run --package beatrix pytest`; manual run on a <0.5 s clip and a 10 s silence file.

- [ ] **Unit 2.2: Version & complete the JSON contract**

**Goal:** Make the producer contract explicit and correct.
**Requirements:** R4.
**Dependencies:** None.
**Files:** Modify `packages/beatrix/src/beatrix/core/audio_analyzer.py`; tests.
**Approach:**
- Emit `schema_version: "1.0"` (authoritative name; spec updated to match in Unit 8.1).
- Emit `hop_length: 512` (governs `dt`) AND `n_fft: 2048` (the real `librosa.stft` default — NOT 512).
- Coerce `beat_events` (built via `range(0, len(beats), beat_division)` slicing → `np.float64`) to native `float`; drop the redundant range guard. (`beat_times` and band arrays already use `.tolist()` — leave them.)
- Sanitize non-finite (NaN/inf) in onsets/bass-peaks/band-energy before serialization.
- Guarantee `len(frequency_bands.times) >= 2` or raise explicitly.
**Test scenarios:**
- Happy path: output JSON has `schema_version`, `hop_length:512`, `n_fft:2048`; `beat_events` are `float`.
- Edge case: silence/short input never yields NaN/inf in any numeric array.
- Integration: a fixture run validates output against a JSON Schema mirroring the EMITTED keys (not the old spec body).
**Verification:** `cd packages/beatrix && uv run --package beatrix pytest`; inspect emitted JSON.

- [ ] **Unit 2.3: AudioValidator placement**

**Goal:** Resolve the dead-in-beatrix validator with fail-fast wiring.
**Requirements:** R6.
**Dependencies:** Phase 1 (imports `find_files_by_type` from common).
**Files:** Modify `packages/beatrix/src/beatrix/core/audio_validator.py`.
**Approach:** Wire fail-fast validation (`librosa.get_duration` decode probe) into the beatrix flow; unify PL/EN messages. (Decision made: wire in, don't leave it as a cymatic-only util.)
**Test scenarios:**
- Error path: a corrupt file passing extension/existence checks is rejected by the decode probe.
**Verification:** `cd packages/beatrix && uv run --package beatrix pytest`.

### Phase 3 — `fix/cymatic-edges` (R1, R3, R4)

- [ ] **Unit 3.1: Render-pipeline edge correctness**

**Goal:** Close frame-padding, output-existence, frame-count gaps.
**Requirements:** R1, R3.
**Files:** Modify `packages/cymatic/src/cymatic/runner.py`, `packages/cymatic/blender_script/build_scene.py`, `packages/cymatic/blender_script/hybrid_v1.py`; tests.
**Approach:** Derive the ffmpeg input pattern from the first frame's stem (not hardcoded `frame_%04d.png`); raise if output file absent after `_mux_frames`; unify `_expected_frame_count` on `max(1, ...)` and pass the already-loaded `AnalysisData` (no re-parse); pass `frame_start` into `build_preset_scene`.
**Test scenarios:**
- Edge case: ≥100000 frames → ffmpeg pattern still matches generated files.
- Error path: ffmpeg "succeeds" but writes no file → `render()` raises, CLI non-zero.
- Happy path: short clip uses `max(1, ...)`, no analysis re-parse.
**Verification:** `cd packages/cymatic && uv run --package cymatic pytest`; E2E `cymatic-render` on real analysis + long synthetic input → mp4 exists.

- [ ] **Unit 3.2: Contract consumption & quiet-failure removal**

**Goal:** Validate the producer contract; stop silent silent-renders. cymatic is now the SOLE analysis.json consumer.
**Requirements:** R4, R3.
**Dependencies:** Unit 2.2.
**Files:** Modify `packages/cymatic/src/cymatic/analysis_loader.py`, `packages/cymatic/src/cymatic/cli.py`, `packages/cymatic/src/cymatic/normalization.py`, `packages/cymatic/blender_script/build_scene.py`.
**Approach:** Validate `schema_version` major; **missing field ⇒ assume "1.0"** (backward compat for pre-existing on-disk analysis files) but mismatched major ⇒ hard error. Read emitted `hop_length` instead of hardcoding 512. Explicit missing `--audio-file` → WARNING; `--analysis-file` without audio → INFO "rendering silent". Vectorize `precompute_envelope`. Wrap `from_json`/`load_analysis` in `build_scene.main()` with readable error + `return 1`.
**Test scenarios:**
- Error path: incompatible major `schema_version` → clear error.
- Edge case: analysis file with NO version field → treated as 1.0, loads.
- Happy path: emitted `hop_length` drives `dt` sanity-check.
**Verification:** `cd packages/cymatic && uv run --package cymatic pytest`.

### Phase 4 — `chore/retire-cinemon` (R6, R8) — *unblocks P7*

- [ ] **Unit 4.1: Delete the cinemon package**

**Goal:** Remove `packages/cinemon` entirely.
**Requirements:** R6, R8.
**Files:** Delete `packages/cinemon/`; Modify workspace `pyproject.toml` (remove cinemon from workspace members + any `[tool.uv.sources]` / dependency entries); `uv.lock` (regenerate via `uv sync`).
**Approach:** This single deletion removes ~21k LOC, the largest P0 cluster (dead VSE API, magic-`all`, animation correctness), the doc fiction, the dev-cruft (foreign `/home/wojtas` + `/home/wokoziej/Wideo` paths, `snap run blender`), and the 15.67% coverage drag.
**Test scenarios:** Test expectation: none — deletion. Verified by the workspace resolving and building without cinemon.
**Verification:** `uv sync` succeeds; `uv run pytest` collects no cinemon tests; repo-wide grep for `cinemon` shows only intentional doc mentions (handled in 4.2 + Unit 8.1).

- [ ] **Unit 4.2: Purge cinemon references (non-fermata)**

**Goal:** No dangling references outside fermata (fermata handled in P7).
**Requirements:** R8, R5.
**Dependencies:** Unit 4.1.
**Files:** Grep-driven: Modify any `setka-common`/`beatrix`/`cymatic`/`obsession` code or tests importing cinemon (audit expects none); remove cinemon CLI entry points from packaging; flag CLAUDE.md / DATA_FLOW_SPECIFICATION edits for Unit 8.1.
**Approach:** Repo-wide `grep -ri cinemon` enumerates every reference; classify each as code (remove), docs (defer to 8.1), or fermata (defer to P7).
**Test scenarios:** Test expectation: none — reference purge. Verified by grep + green workspace.
**Verification:** No import errors anywhere; `grep -ril 'import.*cinemon\|cinemon-blend\|cinemon-generate'` returns only fermata (P7) and docs (8.1).

### Phase 5 — `fix/obsession-extract` (R3, R4, R5, R7) — *needs P1*

- [ ] **Unit 5.1: Audio extraction correctness + ffmpeg timeout**

**Goal:** Fix duplicate per-source audio and unbounded ffmpeg.
**Requirements:** R3, R4.
**Dependencies:** Unit 1.2 (canonical sanitize).
**Files:** Modify `packages/obsession/src/obsession/core/extractor.py`; tests.
**Approach:** **Per-source audio via `-map`** (user decision): for each source with `has_audio=True`, build the ffmpeg command with the correct `-map` for that source's audio stream so each `<source>.m4a` carries its own track — eliminating the current bug where all sources get an identical full-canvas copy. Verify the source→stream mapping against a real recording's `metadata.json` during implementation. Plus (decision-independent): `timeout=` + `TimeoutExpired` folded into `ExtractionResult` (mirror cymatic / `advanced_scene_switcher_extractor.py:161`); adopt canonical `sanitize_filename`; keep the `main_audio.m4a` convention for the main source.
**Execution note:** Failing test asserting expected audio outputs before changing extraction.
**Test scenarios:**
- Error path: hung/failed ffmpeg → `TimeoutExpired` surfaces as failed `ExtractionResult`.
- Happy path: multi-audio-source recording yields expected audio file(s), not N identical copies.
- Edge case: source partially outside canvas → crop clamps (negative `canvas_x`).
**Verification:** `cd packages/obsession && uv run --package obsession pytest`; extract a real recording, confirm audio names/content.

- [ ] **Unit 5.2: Metadata robustness + cleanup**

**Goal:** Defensive metadata handling; remove dead branch.
**Requirements:** R3.
**Files:** Modify `packages/obsession/src/obsession/core/extractor.py` (`position.get("x", 0)` — KeyError fires when `position:{}`; remove dead `except ValueError`), `.../core/metadata.py` (`validate_metadata` checks positions/`bounds`/`dimensions`), `.../obs_integration/obs_script.py` (validate `base_width/height > 0`), `.../cli/cameras.py` (validate `obs_host` as IP / heredoc).
**Test scenarios:**
- Error path: `position: {}` → handled, no uncaught `KeyError`.
- Edge case: zero/negative canvas in metadata → rejected by `validate_metadata`.
**Verification:** `cd packages/obsession && uv run --package obsession pytest`.

- [ ] **Unit 5.3: Test fixtures, stale setup, coverage to 80%**

**Goal:** Fix fixtures that mask regressions; reach the gate.
**Requirements:** R5, R7.
**Files:** Modify `packages/obsession/tests/conftest.py` and test modules.
**Approach:** Fixtures use `canvas_size` as a **list** and `sources` as a **dict** (real `obs_script` shape per `DATA_FLOW_SPECIFICATION.md`). Remove empty `setup_method(){pass}` (resolved importlib.reload). Raise coverage from 60.39% → 80% (cli/extract 38%, cameras 0% are the targets).
**Test scenarios:**
- Integration: a fixture-shaped `metadata.json` round-trips through `validate_metadata` and `extract_sources`.
**Verification:** `cd packages/obsession && uv run --package obsession pytest --cov` ≥80%.

### Phase 6 — `fix/medusa-security-cli` (R1, R2, R7) — *independent of P1*

- [ ] **Unit 6.1: Unify `PlatformConfig` (fix broken CLI upload)**

**Goal:** One config model; CLI upload works.
**Requirements:** R1.
**Files:** Modify `packages/medusa/src/medusa/utils/config.py`, `packages/medusa/src/medusa/models.py`, `packages/medusa/src/medusa/cli/commands.py`.
**Approach:** Collapse to the `models.py` `PlatformConfig` (used by uploaders); `ConfigLoader.load()` produces it (map flat fields → `credentials={...}`), killing the always-False `hasattr` path.
**Execution note:** Failing test through `ConfigLoader.load() → YouTubeUploader.authenticate()` first.
**Test scenarios:**
- Happy path: CLI upload authenticates without `ConfigError`.
- Integration: the config seam (loader → uploader) end-to-end.
- Error path: missing `client_secrets_file` → clear `ConfigError`, not silent `{}`.
**Verification:** `cd packages/medusa && uv run --package medusa pytest`; `python -m medusa.cli upload <file>` with test config reaches auth.

- [ ] **Unit 6.2: Credential leakage — URL, logs, repr, to_dict, perms, scope** 🔒

**Goal:** Credentials never travel in URLs or logs; minimal scope.
**Requirements:** R2.
**Files:** Modify `packages/medusa/src/medusa/publishers/facebook_auth.py`, `packages/medusa/src/medusa/uploaders/youtube.py`, `packages/medusa/src/medusa/exceptions.py`, `packages/medusa/src/medusa/models.py`, `packages/medusa/src/medusa/uploaders/youtube_auth.py`.
**Approach:**
- Facebook token/`app_secret`/`client_secret`: move out of URL query to `Authorization: Bearer` header / POST body — **endpoint-aware** (Meta requires the token differently per endpoint; `_build_api_url` appends it for ALL methods today, including POST `/feed` and the token-exchange call).
- Log only `status` + short message — covers BOTH `_handle_http_error` AND the retryable-error branch at `youtube.py:683` (which currently writes raw `e.content`).
- Mask URLs/token fields in `MedusaError.get_error_details` (`exceptions.py:52-59` serializes full traceback incl. `HttpError` content).
- `PlatformConfig.credentials`: `field(repr=False)` AND mask in `to_dict()` (`models.py:370` serializes raw credentials — repr=False alone misses this).
- `save_credentials` (`youtube_auth.py:286`): write with mode `0600` (today `open(path,'w')` uses umask → 0644).
- Reduce YouTube OAuth scope from full `youtube` to `youtube.upload` where upload-only.
**Test scenarios:**
- Security: retryable YouTube error → logs contain status, not raw `e.content`.
- Security: neither `repr(PlatformConfig)` nor `to_dict()` contains token values.
- Security: saved credentials file mode is `0600`.
- Integration: Facebook request carries the token in header/body per endpoint, not the URL.
**Verification:** `cd packages/medusa && uv run --package medusa pytest`; grep test logs for token/secret strings (none).

- [ ] **Unit 6.3: Upload reliability**

**Goal:** Bounded memory, rate-limit-aware retries, safe config access.
**Requirements:** R3.
**Dependencies:** Unit 6.1.
**Files:** Modify `packages/medusa/src/medusa/uploaders/youtube.py`, `packages/medusa/src/medusa/publishers/facebook.py`.
**Approach:** Finite `chunksize` (5–50 MB) not `-1` (OOM / fake resumable). Honor `Retry-After` on 429. `.get("page_id")` + validation, not bare `KeyError`.
**Test scenarios:**
- Error path: 429 with `Retry-After` → retry waits the advertised interval.
- Error path: missing `page_id` → `ConfigError`/`ValidationError`.
**Verification:** `cd packages/medusa && uv run --package medusa pytest`.

- [ ] **Unit 6.4: Remove dead orchestration + test integrity**

**Goal:** Remove confirmed dead code; fix dead tests; reach coverage.
**Requirements:** R6, R7.
**Dependencies:** Unit 6.1.
**Files:** Modify `packages/medusa/src/medusa/models.py` (remove unused `PublishRequest`), `packages/medusa/src/medusa/__init__.py` (drop the `MedusaCore` TODO — it never existed), `packages/medusa/tests/integration/test_youtube_real_api.py`.
**Approach:** Verified: `registry.py` IS used (by `tests/test_registry.py`) — KEEP it. `MedusaCore` never existed (only a TODO comment). `PublishRequest` is defined but never imported — REMOVE. Replace `skipif(True)` dead auth test with a real mocked OAuth test or remove. Document `TaskStore` in-memory limitation.
**Test scenarios:**
- Regression: raw API error content does not reach logs (cross-check 6.2).
**Verification:** `cd packages/medusa && uv run --package medusa pytest --cov` ≥80%.

### Phase 7 — `fix/fermata-build-ipc` (R1, R2, R3, R7, R8) — *needs P4*

- [ ] **Unit 7.1: Unblock the build (restores ~40 dead tests)**

**Goal:** Make `tsc`, `cargo test`, `tauri build` compile.
**Requirements:** R1.
**Files:** Modify `packages/fermata/src/hooks/useRecordings.ts`, `packages/fermata/src/types/index.ts`, `packages/fermata/src-tauri/src/services/process_runner.rs`, `packages/fermata/src-tauri/src/services/status_detector.rs`.
**Approach:** Fix imports: `DeletionConfirmationState`→`DeletionState`, `RenameConfirmationState`→`RenameState`; add/define `RenderOptions` (or remove if unused). Fix `run_cinemon_render` test arity — note this call site is removed in 7.2 anyway (cinemon retired), so the cleaner fix is deletion. Fix `status_detector` expected key to the real relative path.
**Test scenarios:**
- Happy path: `npm run build` (tsc) + `cargo test` compile; existing tests run.
**Verification:** `cd packages/fermata && npm run build && cargo test` succeed.

- [ ] **Unit 7.2: Drop cinemon orchestration + path-traversal hardening** 🔒

**Goal:** Remove retired-cinemon calls; secure IPC.
**Requirements:** R8, R2.
**Dependencies:** Unit 7.1, Phase 4.
**Files:** Modify `packages/fermata/src-tauri/src/services/process_runner.rs` (remove `run_cinemon_render` / `run_cinemon_render_with_audio` and the `cinemon-blend-setup`/`cinemon-generate-config` invocations), `packages/fermata/src-tauri/src/commands/operations.rs`, `.../commands/recordings.rs`, `.../commands/rename.rs`, `.../commands/video.rs`.
**Approach:**
- **cinemon retirement:** delete the cinemon render path. The "Render" step is rewired or removed per the Open Question (Unit 7.4 records the decision).
- **Path traversal:** change the IPC contract so file-touching commands take a `recording_name` + relative path resolved server-side; reject `..`/separators/absolute components; canonicalize and assert `starts_with(recordings_path)`. Covers delete, rename, `open_video_external`, AND `get_recording_details`.
**Execution note:** Failing traversal tests first (none exist today).
**Test scenarios:**
- Security: `name="../../etc/passwd"` and absolute paths → rejected before any `fs`/`open` op.
- Security: `open_video_external` / `get_recording_details` cannot escape `recordings_path`.
- Happy path: a legitimate recording name resolves.
**Verification:** `cargo test` with traversal tests; manual `tauri dev` rename with `../` refused.

- [ ] **Unit 7.3: Subprocess timeouts + CSP + root canonicalization**

**Goal:** No hangs; restrict web context; secure the root.
**Requirements:** R2, R3.
**Dependencies:** Unit 7.1.
**Files:** Modify `packages/fermata/src-tauri/src/commands/operations.rs`, `.../services/process_runner.rs`, `packages/fermata/src-tauri/tauri.conf.json`, the startup/config init.
**Approach:** Wrap surviving subprocess calls (`beatrix`, `cymatic`, `medusa`) in `tokio::time::timeout`. Replace `"csp": null` with a concrete restrictive policy (e.g. `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' asset: data:`). Canonicalize `FERMATA_RECORDINGS_PATH` at startup (else the traversal guard is defeated by an attacker-controlled root).
**Test scenarios:**
- Error path: subprocess exceeding the timeout returns a timeout error, not a hang.
**Verification:** `cargo test`; app loads with CSP set.

- [ ] **Unit 7.4: Cleanup, dead code, UX correctness (P2) — no new features**

**Goal:** Remove dead code; fix misleading UI; keep scope to remediation.
**Requirements:** R6, R7.
**Dependencies:** Unit 7.1.
**Files:** Modify `packages/fermata/src-tauri/src/services/process_runner.rs` (remove dead `get_directory_size`; wire `validate_cli_tools` into `setup()`), `packages/fermata/src-tauri/src/commands/recordings.rs` (lazy/cached sizes), `packages/fermata/src/components/RecordingDetails.tsx` (derive stage from backend, not `path.includes`), `.../operations.rs` (the "Render" step decision — see below).
**Approach:**
- **Excluded (new features → Deferred):** persistent config store, wiring the Settings button, ts-rs/specta codegen. Sync TS↔Rust types **manually** for now.
- **fermata render path (resolved):** rewire the "Render" step in `process_runner.rs` to invoke **`cymatic-render`** (via `uv run --package cymatic ...`) instead of the deleted cinemon CLIs. The NextStep "Render" handler in `operations.rs` calls cymatic with the recording's analysis. Keep the invocation minimal (argv + timeout from Unit 7.3); UI label updates to reflect the GN visualizer output.
- Manually align `NextStep`/`AppConfig` TS types with Rust (no codegen).
**Test scenarios:**
- Happy path: `validate_cli_tools` at startup fails fast when `uv`/packages missing.
- Edge case: `get_recordings` does not block on recursive size walk.
**Verification:** `cargo test` + `vitest`; manual `tauri dev` shows correct stage; no cinemon calls remain.

### Phase 0' / Phase 8 — `chore/repo-docs-ci` (R4, R5, R7) — *CI early, docs last*

- [ ] **Unit 8.0: CI scaffolding (lands EARLY)**

**Goal:** Rot protection exists during the rest of the work.
**Requirements:** R7.
**Dependencies:** None.
**Files:** Create `.github/workflows/` (per-package `cd packages/X && uv run --package X pytest --cov` with 80% gate; `cargo test` + `vitest` for fermata).
**Approach:** Per-package invocation from the package dir (the workspace-root run has no gate). Land this before P5/P6/P7 so regressions are caught immediately. Gates start at each package's current level if 80% isn't yet reached, ratcheting up as phases land — but the **target and end-state is 80%** per user decision.
**Test scenarios:** Test expectation: none — CI config. Validate by a fresh-checkout CI run.
**Verification:** CI green on a clean clone; per-package gates enforced.

- [ ] **Unit 8.1: Documentation truth (lands LAST)**

**Goal:** All docs match the post-retirement code.
**Requirements:** R5, R4, R8.
**Dependencies:** Phases 1–7.
**Files:** Modify `CLAUDE.md`, `packages/common/CLAUDE.md`, `packages/obsession/CLAUDE.md` (audit), `docs/DATA_FLOW_SPECIFICATION.md`; Delete `packages/cinemon/CLAUDE.md` (with the package).
**Approach:**
- **Remove cinemon entirely** from root `CLAUDE.md`: package list, pipeline diagram (`obsession → beatrix → cymatic → medusa`), dependency graph, CLI entry points (`cinemon-blend-setup`, `cinemon-generate-config`), all "Critical Architecture Patterns (cinemon)" sections.
- **Fix surviving fiction**: `MediaDiscovery` location (`setka_common.utils.files`, not `cinemon/config/media_discovery.py`); remove the resolved importlib.reload "Test Isolation Issues" note; `MedusaCore` "in progress" (removed); `packages/common/CLAUDE.md` Key Exports (drop `ConfigValidator`).
- **Rewrite (not append)** the `analysis.json` and `metadata.json` sections of `DATA_FLOW_SPECIFICATION.md` to match EMITTED keys; rename `version` → `schema_version`; add `hop_length`/`n_fft`; update Blender 4.3.0 → 5.1.2; update the pipeline to drop cinemon.
**Test scenarios:** Test expectation: none — docs. Verify each documented command/flag/symbol exists in code (manual checklist).
**Verification:** Every command/flag/symbol in every CLAUDE.md resolves to real code; `grep -ri cinemon docs/ CLAUDE.md` returns nothing.

## System-Wide Impact

- **Interaction graph:** `analysis.json` (Unit 2.2) now has a SINGLE consumer — cymatic (Unit 3.2). cinemon's old consumption is deleted. `setka-common` (Phase 1) ripples to obsession + cymatic + beatrix-validator.
- **cinemon retirement blast radius:** workspace `pyproject.toml`/`uv.lock`, fermata `process_runner` (cinemon CLI calls), root + cinemon CLAUDE.md, data-flow spec pipeline. Enumerated by repo-wide grep (Unit 4.2).
- **Error propagation:** beatrix sanitizes non-finite at source; cymatic's `_finite_times` becomes a backstop. medusa errors sanitized before logging.
- **State lifecycle risks:** medusa `TaskStore` in-memory (duplicate-upload) — documented, not fixed. cymatic temp-frame cleanup already correct.
- **API surface parity:** sanitize unification keeps output byte-stable for existing recordings (superset + regression test).
- **Integration coverage:** medusa config seam (6.1) and cymatic render E2E (3.1) are the unit-test-insufficient spots.
- **Unchanged invariants:** surviving pipeline stages and `RecordingStructureManager` layout unchanged; only the dir-name-constants source-of-truth changes (no on-disk layout change).

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| cinemon deletion breaks an unnoticed consumer | Repo-wide grep (Unit 4.2) before/after; `uv sync` + full test run gate the deletion |
| fermata render path left broken after cinemon removal | Unit 7.4 records the explicit rewire-to-cymatic vs remove decision; no speculative integration |
| `sanitize_filename` unification renames existing files | Canonical = superset of obsession's rules + byte-stability regression test on real source names |
| 80% coverage gate blocks P0 fixes | CI gates start at current level and ratchet to 80% target; cinemon's 15.67% leaves with retirement, easing the aggregate |
| Contract change landed before consumer validates | beatrix Unit 2.2 → cymatic Unit 3.2 ordering; missing version ⇒ assume 1.0 (no break for old files) |
| obsession audio semantics misjudged | Blocked pending user decision + real recording; decision-independent parts shippable alone |
| medusa security fix changes request shape | Integration test asserts requests still authenticate against mocked APIs |

## Documentation / Operational Notes

- After landing, run `ce:compound` to capture the cinemon-retirement rationale and the contract-versioning approach into `docs/solutions/` (currently empty).
- CI (Unit 8.0) lands early as the durable fix for the "dead tests rotted unnoticed" root cause.

## Sources & References

- **Origin (session audit artifact):** `scratchpad/setka-audit-2026-06-22.md`
- **Review:** 6-persona document-review (coherence, feasibility, security, scope, product, adversarial) + 2 code-verification agents, 2026-06-23
- Contract spec: `docs/DATA_FLOW_SPECIFICATION.md`
- Prior plan (cymatic): `docs/plans/2026-05-30-001-feat-gn-audio-visualizer-plan.md`
- Environment: Blender 5.1.2 at `/Applications/Blender.app`
