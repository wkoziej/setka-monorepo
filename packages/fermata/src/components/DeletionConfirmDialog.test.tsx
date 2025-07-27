import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DeletionConfirmDialog } from './DeletionConfirmDialog';
import { Recording, RecordingStatus } from '../types';

const mockRecording: Recording = {
  name: 'test_recording_123',
  path: '/path/to/test_recording_123',
  status: 'Recorded' as RecordingStatus,
  last_updated: Date.now(),
  file_sizes: { 'recording.mkv': 2400000000 } // 2.4GB
};

describe('DeletionConfirmDialog', () => {
  const mockOnConfirm = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when isOpen is false', () => {
    render(
      <DeletionConfirmDialog
        isOpen={false}
        recording={mockRecording}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isDeleting={false}
      />
    );

    expect(screen.queryByText(/usuń nagranie/i)).not.toBeInTheDocument();
  });

  it('should render dialog when isOpen is true', () => {
    render(
      <DeletionConfirmDialog
        isOpen={true}
        recording={mockRecording}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isDeleting={false}
      />
    );

    expect(screen.getByText(/usuń nagranie/i)).toBeInTheDocument();
    expect(screen.getByText(/test_recording_123/i)).toBeInTheDocument();
    expect(screen.getByText(/ta akcja jest nieodwracalna/i)).toBeInTheDocument();
  });

  it('should call onCancel when Anuluj button is clicked', () => {
    render(
      <DeletionConfirmDialog
        isOpen={true}
        recording={mockRecording}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isDeleting={false}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /anuluj/i });
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('should call onConfirm when Usuń nagranie button is clicked', () => {
    render(
      <DeletionConfirmDialog
        isOpen={true}
        recording={mockRecording}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isDeleting={false}
      />
    );

    const confirmButton = screen.getByRole('button', { name: /usuń nagranie/i });
    fireEvent.click(confirmButton);

    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('should disable buttons when isDeleting is true', () => {
    render(
      <DeletionConfirmDialog
        isOpen={true}
        recording={mockRecording}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isDeleting={true}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /anuluj/i });
    const confirmButton = screen.getByRole('button', { name: /usuń nagranie/i });

    expect(cancelButton).toBeDisabled();
    expect(confirmButton).toBeDisabled();
  });

  it('should not render when recording is undefined', () => {
    render(
      <DeletionConfirmDialog
        isOpen={true}
        recording={undefined}
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        isDeleting={false}
      />
    );

    expect(screen.queryByText(/usuń nagranie/i)).not.toBeInTheDocument();
  });
});
