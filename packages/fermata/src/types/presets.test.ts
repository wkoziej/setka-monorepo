// ABOUTME: Guards the fermata preset list against drift from cinemon's actual presets.
// ABOUTME: cinemon-generate-config --list-presets is the source of truth (minimal, multi_pip).
import { describe, it, expect } from 'vitest';
import { AVAILABLE_PRESETS } from './index';

// Keep in sync with `cinemon-generate-config --list-presets`. fermata historically
// offered beat-switch/music-video/vintage, which cinemon no longer ships, so the
// render step failed with "Preset '<name>' not found".
const CINEMON_PRESETS = ['minimal', 'multi_pip'];

describe('AVAILABLE_PRESETS', () => {
  it('only offers presets that cinemon actually supports', () => {
    const names = AVAILABLE_PRESETS.map((p) => p.name);
    expect(names).toEqual(CINEMON_PRESETS);
  });

  it('gives every preset a non-empty description', () => {
    for (const preset of AVAILABLE_PRESETS) {
      expect(preset.description.trim().length).toBeGreaterThan(0);
    }
  });
});
