import { AVAILABLE_PRESETS } from '../types';

interface PresetSelectorProps {
  selectedPreset: string;
  onPresetChange: (preset: string) => void;
  disabled?: boolean;
  className?: string;
}

export function PresetSelector({
  selectedPreset,
  onPresetChange,
  disabled,
  className
}: PresetSelectorProps) {
  return (
    <div className={`space-y-2 ${className}`}>
      <label className="text-sm font-medium text-gray-700">
        Animation Preset
      </label>
      <select
        value={selectedPreset}
        onChange={(e) => onPresetChange(e.target.value)}
        disabled={disabled}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        style={{ minHeight: '40px' }}
      >
        <option value="" disabled>Select animation preset...</option>
        {AVAILABLE_PRESETS.map(preset => (
          <option key={preset.name} value={preset.name}>
            {preset.name.replace('-', ' ').toUpperCase()}
          </option>
        ))}
      </select>

      {/* Show description below the select */}
      {selectedPreset && (
        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-sm text-blue-800">
            <strong>{selectedPreset.replace('-', ' ').toUpperCase()}:</strong>{' '}
            {AVAILABLE_PRESETS.find(p => p.name === selectedPreset)?.description}
          </p>
        </div>
      )}
    </div>
  );
}
