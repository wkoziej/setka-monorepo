import { useState, useCallback, useEffect } from 'react';
import { Recording, RecordingListState } from '../types';
import { invoke } from '@tauri-apps/api/core';

export function useRecordings() {
  const [state, setState] = useState<RecordingListState>({
    recordings: [],
    loading: true,
    error: null
  });

  const refreshRecordings = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const recordings = await invoke('get_recordings') as Recording[];
      setState({
        recordings,
        loading: false,
        error: null
      });
    } catch (error) {
      setState({
        recordings: [],
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load recordings'
      });
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
      const result = await invoke('run_next_step', { recordingName });
      setOperationState({
        running: false,
        output: result as string,
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
      const result = await invoke('run_specific_step', { recordingName, step });
      setOperationState({
        running: false,
        output: result as string,
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