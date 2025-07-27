import { useState, useEffect } from 'react';
import { Recording } from '../types';

interface RenameRecordingDialogProps {
  isOpen: boolean;
  recording?: Recording;
  onRename: (newName: string) => void;
  onCancel: () => void;
  isRenaming: boolean;
}

export function RenameRecordingDialog({
  isOpen,
  recording,
  onRename,
  onCancel,
  isRenaming
}: RenameRecordingDialogProps) {
  const [newName, setNewName] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && recording) {
      setNewName(recording.name);
      setValidationError(null);
    }
  }, [isOpen, recording]);

  const validateName = (name: string): string | null => {
    if (!name.trim()) {
      return 'Recording name cannot be empty';
    }

    if (name === recording?.name) {
      return 'New name must be different from current name';
    }

    // Basic filename validation - invalid characters
    const invalidChars = /[<>:"|?*]/;
    if (invalidChars.test(name)) {
      return 'Invalid characters in name (< > : " | ? *)';
    }

    // Check for leading/trailing spaces or dots
    if (name !== name.trim()) {
      return 'Name cannot start or end with spaces';
    }

    if (name.startsWith('.') || name.endsWith('.')) {
      return 'Name cannot start or end with dots';
    }

    // Length check
    if (name.length > 255) {
      return 'Name is too long (max 255 characters)';
    }

    return null;
  };

  const handleInputChange = (value: string) => {
    setNewName(value);
    setValidationError(validateName(value));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const error = validateName(newName);
    if (error) {
      setValidationError(error);
      return;
    }

    onRename(newName.trim());
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        minWidth: '400px',
        maxWidth: '500px',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{ margin: '0 0 16px 0', fontSize: '20px', fontWeight: '600' }}>
          Rename Recording
        </h2>

        <p style={{ margin: '0 0 20px 0', color: '#6b7280', fontSize: '14px' }}>
          Changing the name will rename the directory and main recording file.
          This will not affect any currently running operations.
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{
              display: 'block',
              marginBottom: '6px',
              fontWeight: '500',
              fontSize: '14px'
            }}>
              Current name: <span style={{ fontWeight: 'normal', color: '#6b7280' }}>{recording?.name}</span>
            </label>

            <label style={{
              display: 'block',
              marginBottom: '6px',
              fontWeight: '500',
              fontSize: '14px'
            }}>
              New name:
            </label>

            <input
              type="text"
              value={newName}
              onChange={(e) => handleInputChange(e.target.value)}
              placeholder={recording?.name || 'Enter new name'}
              disabled={isRenaming}
              autoFocus
              style={{
                width: '100%',
                padding: '8px 12px',
                border: `1px solid ${validationError ? '#ef4444' : '#d1d5db'}`,
                borderRadius: '6px',
                fontSize: '14px',
                backgroundColor: isRenaming ? '#f9fafb' : 'white'
              }}
            />

            {validationError && (
              <div style={{
                marginTop: '6px',
                color: '#ef4444',
                fontSize: '12px'
              }}>
                {validationError}
              </div>
            )}
          </div>

          <div style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'flex-end'
          }}>
            <button
              type="button"
              onClick={onCancel}
              disabled={isRenaming}
              style={{
                padding: '8px 16px',
                fontSize: '14px',
                backgroundColor: '#f3f4f6',
                color: '#374151',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                cursor: isRenaming ? 'not-allowed' : 'pointer',
                opacity: isRenaming ? 0.6 : 1
              }}
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isRenaming || !!validationError || newName.trim() === recording?.name}
              style={{
                padding: '8px 16px',
                fontSize: '14px',
                backgroundColor: (isRenaming || !!validationError || newName.trim() === recording?.name)
                  ? '#9ca3af' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: (isRenaming || !!validationError || newName.trim() === recording?.name)
                  ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {isRenaming && (
                <span>🔄</span>
              )}
              {isRenaming ? 'Renaming...' : 'Rename'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
