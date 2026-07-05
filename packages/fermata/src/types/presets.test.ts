// ABOUTME: Guards the fermata preset list (UI labels) against accidental drift.
// ABOUTME: cinemon is retired; cymatic (the GN visualizer) has no preset concept,
// ABOUTME: so these are informational UI options only — kept stable for the Setup UI.
import { describe, it, expect } from 'vitest';
import { AVAILABLE_PRESETS } from './index';

// The render step now drives cymatic-render, which ignores the preset entirely.
// These names are UI-only labels; keep the list stable so the PresetSelector and
// RenderOptions default stay in sync.
const EXPECTED_PRESETS = ['minimal', 'multi_pip'];

describe('AVAILABLE_PRESETS', () => {
  it('offers the expected stable UI preset list', () => {
    const names = AVAILABLE_PRESETS.map((p) => p.name);
    expect(names).toEqual(EXPECTED_PRESETS);
  });

  it('gives every preset a non-empty description', () => {
    for (const preset of AVAILABLE_PRESETS) {
      expect(preset.description.trim().length).toBeGreaterThan(0);
    }
  });
});
