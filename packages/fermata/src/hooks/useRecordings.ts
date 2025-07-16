import { useState, useCallback, useEffect } from 'react';
import { Recording, RecordingListState } from '../types';

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
      // TODO: Replace with actual Tauri invoke call
      // const recordings = await invoke('get_recordings');
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setState({
        recordings: mockRecordings,
        loading: false,
        error: null
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }));
    }
  }, []);

  // Load recordings on mount
  useEffect(() => {
    refreshRecordings();
  }, [refreshRecordings]);

  return {
    ...state,
    refreshRecordings
  };
}

export function useRecordingOperations() {
  const [operationState, setOperationState] = useState({
    running: false,
    output: '',
    error: null as string | null
  });

  const runNextStep = useCallback(async (recordingName: string) => {
    setOperationState({ running: true, output: '', error: null });
    
    try {
      // TODO: Replace with actual Tauri invoke call
      // const result = await invoke('run_next_step', { recordingName });
      
      // Simulate operation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setOperationState({
        running: false,
        output: `Successfully started next step for ${recordingName}`,
        error: null
      });
    } catch (error) {
      setOperationState({
        running: false,
        output: '',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }, []);

  const runSpecificStep = useCallback(async (recordingName: string, step: string) => {
    setOperationState({ running: true, output: '', error: null });
    
    try {
      // TODO: Replace with actual Tauri invoke call
      // const result = await invoke('run_specific_step', { recordingName, step });
      
      // Simulate operation
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setOperationState({
        running: false,
        output: `Successfully started ${step} for ${recordingName}`,
        error: null
      });
    } catch (error) {
      setOperationState({
        running: false,
        output: '',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }, []);

  return {
    ...operationState,
    runNextStep,
    runSpecificStep
  };
} 