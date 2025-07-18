import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RecordingList } from './RecordingList';
import { Recording, RecordingStatus } from '../types';

// Mock hook
const mockRecordings: Recording[] = [
  {
    name: 'test_recording_1',
    path: '/path/to/test_recording_1',
    status: 'Recorded' as RecordingStatus,
    last_updated: Date.now(),
    file_sizes: { 'recording.mkv': 1000000 }
  }
];

const mockUseRecordings = {
  recordings: mockRecordings,
  loading: false,
  error: null,
  refreshRecordings: vi.fn(),
  deletionState: {
    isOpen: false,
    recording: undefined,
    isDeleting: false
  },
  deleteRecording: vi.fn(),
  showDeletionDialog: vi.fn(),
  hideDeletionDialog: vi.fn()
};

const mockUseRecordingOperations = {
  runNextStep: vi.fn(),
  runSpecificStep: vi.fn(),
  running: {},
  output: ''
};

vi.mock('../hooks/useRecordings', () => ({
  useRecordings: () => mockUseRecordings,
  useRecordingOperations: () => mockUseRecordingOperations
}));

describe('RecordingList Delete Button', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render delete button for each recording', () => {
    render(<RecordingList />);
    
    const deleteButtons = screen.getAllByRole('button', { name: /usuń/i });
    expect(deleteButtons).toHaveLength(1);
  });

  it('should call showDeletionDialog when delete button is clicked', () => {
    render(<RecordingList />);
    
    const deleteButton = screen.getByRole('button', { name: /usuń/i });
    fireEvent.click(deleteButton);
    
    expect(mockUseRecordings.showDeletionDialog).toHaveBeenCalledWith(mockRecordings[0]);
  });

  it('should disable delete button when operation is running', () => {
    mockUseRecordingOperations.running = { 'test_recording_1': true };
    
    render(<RecordingList />);
    
    const deleteButton = screen.getByRole('button', { name: /usuń/i });
    expect(deleteButton).toBeDisabled();
  });

  it('should enable delete button when no operation is running', () => {
    mockUseRecordingOperations.running = {};
    
    render(<RecordingList />);
    
    const deleteButton = screen.getByRole('button', { name: /usuń/i });
    expect(deleteButton).not.toBeDisabled();
  });
}); 