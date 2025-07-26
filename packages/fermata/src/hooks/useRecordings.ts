import { useState, useCallback, useEffect } from 'react';
import { Recording, RecordingListState, DeletionConfirmationState, RenameConfirmationState, RenderOptions } from '../types';
import { invoke } from '@tauri-apps/api/core';

// Tauri API wrapper with fallback for development
const invokeCommand = async (command: string, args?: any): Promise<any> => {
  try {
    // Use modern Tauri 2.0 API
    console.log(`Invoking Tauri command: ${command}`, args);
    const result = await invoke(command, args);
    console.log(`Tauri command ${command} result:`, result);
    return result;
  } catch (error) {
    console.error(`Tauri command ${command} failed:`, error);
    console.warn('Falling back to mock data');
    throw new Error(`Tauri command failed: ${error}`);
  }
};

// Mock data for initial development
const mockRecordings: Recording[] = [
  {
    name: 'stream_20240115_120000',
    path: '/path/to/stream_20240115_120000',
    status: 'Rendered',
    last_updated: Date.now() - 7200000, // 2 hours ago
    file_sizes: {
      'recording.mkv': 2400000000, // 2.4GB
      'extracted': 1800000000,    // 1.8GB
      'analysis': 50000,          // 50KB
      'render': 1200000000        // 1.2GB
    }
  },
  {
    name: 'stream_20240115_140000',
    path: '/path/to/stream_20240115_140000',
    status: 'Analyzed',
    last_updated: Date.now() - 1800000, // 30 min ago
    file_sizes: {
      'recording.mkv': 1900000000,
      'extracted': 1400000000,
      'analysis': 48000
    }
  },
  {
    name: 'stream_20240115_160000',
    path: '/path/to/stream_20240115_160000',
    status: { Failed: 'Audio analysis failed: No audio tracks found' },
    last_updated: Date.now() - 3600000, // 1 hour ago
    file_sizes: {
      'recording.mkv': 2100000000,
      'extracted': 1600000000
    }
  },
  {
    name: 'stream_20240115_180000',
    path: '/path/to/stream_20240115_180000',
    status: 'Extracted',
    last_updated: Date.now() - 600000, // 10 min ago
    file_sizes: {
      'recording.mkv': 2200000000,
      'extracted': 1650000000
    }
  }
];

export function useRecordings() {
  const [state, setState] = useState<RecordingListState>({
    recordings: [],
    loading: true,
    error: null
  });

  const refreshRecordings = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const recordings = await invokeCommand('get_recordings') as Recording[];

      setState({
        recordings,
        loading: false,
        error: null
      });
    } catch (error) {
      // Fallback to mock data if Tauri is not available (dev mode)
      console.warn('Tauri not available, using mock data:', error);
      setState({
        recordings: mockRecordings,
        loading: false,
        error: null
      });
    }
  }, []);

  // Load recordings on mount
  useEffect(() => {
    refreshRecordings();
  }, [refreshRecordings]);

  const [deletionState, setDeletionState] = useState<DeletionConfirmationState>({
    isOpen: false,
    recording: undefined,
    isDeleting: false
  });

  const deleteRecording = useCallback(async (recordingName: string) => {
    setDeletionState(prev => ({ ...prev, isDeleting: true }));
    try {
      await invoke('delete_recording', { recordingName });
      setDeletionState({ isOpen: false, recording: undefined, isDeleting: false });
      refreshRecordings(); // Odśwież listę
    } catch (error) {
      setDeletionState(prev => ({ ...prev, isDeleting: false }));
      // TODO: Pokaż error toast
      console.error('Delete failed:', error);
    }
  }, []);

  return {
    ...state,
    refreshRecordings,
    deletionState,
    deleteRecording,
    showDeletionDialog: (recording: Recording) => {
      setDeletionState({ isOpen: true, recording, isDeleting: false });
    },
    hideDeletionDialog: () => {
      setDeletionState({ isOpen: false, recording: undefined, isDeleting: false });
    }
  };
}

export function useRecordingOperations() {
  const [operationState, setOperationState] = useState({
    running: {} as Record<string, boolean>,
    output: '',
    error: null as string | null
  });

  const runNextStep = useCallback(async (recordingName: string) => {
    console.log(`🚀 Starting runNextStep for: ${recordingName}`);
    setOperationState(prev => ({
      ...prev,
      running: { ...prev.running, [recordingName]: true },
      output: '',
      error: null
    }));

    try {
      // Always try to use Tauri command first
      console.log(`📞 Invoking run_next_step for: ${recordingName}`);
      const result = await invokeCommand('run_next_step', { recordingName });
      console.log(`✅ runNextStep result:`, result);

      setOperationState(prev => ({
        ...prev,
        running: { ...prev.running, [recordingName]: false },
        output: result as string,
        error: null
      }));
    } catch (error) {
      console.error(`❌ runNextStep failed:`, error);
      setOperationState(prev => ({
        ...prev,
        running: { ...prev.running, [recordingName]: false },
        output: '',
        error: error instanceof Error ? error.message : 'Unknown error'
      }));
    }
  }, []);

  const runSpecificStep = useCallback(async (recordingName: string, step: string) => {
    console.log(`🚀 Starting runSpecificStep for: ${recordingName}, step: ${step}`);
    setOperationState(prev => ({
      ...prev,
      running: { ...prev.running, [recordingName]: true },
      output: '',
      error: null
    }));

    try {
      // Always try to use Tauri command first
      console.log(`📞 Invoking run_specific_step for: ${recordingName}, step: ${step}`);
      const result = await invokeCommand('run_specific_step', { recordingName, step });
      console.log(`✅ runSpecificStep result:`, result);

      setOperationState(prev => ({
        ...prev,
        running: { ...prev.running, [recordingName]: false },
        output: result as string,
        error: null
      }));
    } catch (error) {
      console.error(`❌ runSpecificStep failed:`, error);
      setOperationState(prev => ({
        ...prev,
        running: { ...prev.running, [recordingName]: false },
        output: '',
        error: error instanceof Error ? error.message : 'Unknown error'
      }));
    }
  }, []);

  const runSetupRenderWithPreset = useCallback(async (recordingName: string, preset: string, mainAudio?: string) => {
    console.log(`🚀 Starting runSetupRenderWithPreset for: ${recordingName}, preset: ${preset}, mainAudio: ${mainAudio}`);
    setOperationState(prev => ({
      ...prev,
      running: { ...prev.running, [recordingName]: true },
      output: '',
      error: null
    }));

    try {
      const options: RenderOptions = { preset, main_audio: mainAudio };
      const result = await invokeCommand('run_specific_step_with_options', {
        recordingName,
        step: 'setuprender',
        options
      });

      setOperationState(prev => ({
        ...prev,
        running: { ...prev.running, [recordingName]: false },
        output: result as string,
        error: null
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setOperationState(prev => ({
        ...prev,
        running: { ...prev.running, [recordingName]: false },
        output: `Error: ${errorMessage}`,
        error: errorMessage
      }));
    }
  }, []);

  return {
    ...operationState,
    runNextStep,
    runSpecificStep,
    runSetupRenderWithPreset,
  };
}

// Hook for rename recording functionality
export function useRenameRecording() {
  const [renameState, setRenameState] = useState<RenameConfirmationState>({
    isOpen: false,
    recording: undefined,
    isRenaming: false,
  });

  const showRenameDialog = useCallback((recording: Recording) => {
    setRenameState({
      isOpen: true,
      recording,
      isRenaming: false,
    });
  }, []);

  const hideRenameDialog = useCallback(() => {
    setRenameState({
      isOpen: false,
      recording: undefined,
      isRenaming: false,
    });
  }, []);

  const renameRecording = useCallback(async (newName: string) => {
    const { recording } = renameState;
    if (!recording) return;

    console.log(`🔄 Starting rename operation: '${recording.name}' -> '${newName}'`);
    setRenameState(prev => ({ ...prev, isRenaming: true }));

    try {
      await invokeCommand('rename_recording', {
        oldName: recording.name,
        newName: newName
      });

      console.log(`✅ Successfully renamed recording to '${newName}'`);

      // Close dialog
      hideRenameDialog();

      // Note: Caller should refresh recordings list
      return true;
    } catch (error) {
      console.error(`❌ Failed to rename recording:`, error);
      setRenameState(prev => ({ ...prev, isRenaming: false }));

      // Re-throw error so caller can handle it
      throw error;
    }
  }, [renameState, hideRenameDialog]);

  return {
    renameState,
    showRenameDialog,
    hideRenameDialog,
    renameRecording,
  };
}
