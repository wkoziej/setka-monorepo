import { useState, useEffect } from 'react';
import { ArrowLeft, Play, RotateCcw, Eye, Edit, Film } from 'lucide-react';
import { Recording, RecordingStatus } from '../types';
import { useRecordingOperations, useRenameRecording } from '../hooks/useRecordings';
import { invoke } from '@tauri-apps/api/core';
import { RenameRecordingDialog } from './RenameRecordingDialog';
import { PresetSelector } from './PresetSelector';
import { VideoPlayer } from './VideoPlayer';

interface RecordingDetailsProps {
  recordingName: string;
  onBack: () => void;
  onRecordingRenamed?: (oldName: string, newName: string) => void;
}

export function RecordingDetails({ recordingName, onBack, onRecordingRenamed }: RecordingDetailsProps) {
  const [recording, setRecording] = useState<Recording | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState("beat-switch");
  const [showPresetConfig, setShowPresetConfig] = useState(false);
  const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [videoPath, setVideoPath] = useState<string | null>(null);
  const { runNextStep, runSpecificStep, runSetupRenderWithPreset, running, output, error: operationError } = useRecordingOperations();
  const { renameState, showRenameDialog, hideRenameDialog, renameRecording } = useRenameRecording();

  useEffect(() => {
    loadRecordingDetails();
  }, [recordingName]);

  const loadRecordingDetails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await invoke('get_recording_details', { name: recordingName });
      setRecording(result as Recording);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recording details');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAction = async (action: string) => {
    if (action === 'Next Step' && recording?.status === 'Analyzed') {
      // Pokaż konfigurację presetów przed wykonaniem
      setShowPresetConfig(true);
      return;
    }
    
    if (action === 'Setup') {
      // Pokaż konfigurację presetów dla manual setup
      setShowPresetConfig(true);
      return;
    }
    
    if (action === 'Setup Render') {
      // Execute setup render with selected preset
      try {
        await runSetupRenderWithPreset(recordingName, selectedPreset);
        
        // Refresh recording details
        setTimeout(() => {
          loadRecordingDetails();
          setShowPresetConfig(false);
        }, 2000);
      } catch (error) {
        console.error('Setup render failed:', error);
      }
      return;
    }
    
    // Existing logic for other actions
    if (action === 'Next Step') {
      await runNextStep(recordingName);
    } else {
      await runSpecificStep(recordingName, action.toLowerCase());
    }
    
    // Refresh recording details after operation
    setTimeout(() => {
      loadRecordingDetails();
    }, 2000);
  };

  const handleRename = async (newName: string) => {
    try {
      await renameRecording(newName);
      
      // Notify parent about rename
      if (onRecordingRenamed) {
        onRecordingRenamed(recordingName, newName);
      } else {
        // Fallback: go back to list if no callback provided
        onBack();
      }
    } catch (error) {
      console.error('Rename failed:', error);
      // Error is handled by the hook and dialog
    }
  };

  const handleRenameClick = () => {
    if (recording) {
      showRenameDialog(recording);
    }
  };

  const handlePlayVideo = async () => {
    try {
      const path = await invoke('get_playable_video_path', { recordingName }) as string;
      console.log('🎬 Video path from backend:', path);
      console.log('🎬 Setting videoPath to:', path);
      setVideoPath(path);
      console.log('🎬 Setting showVideoPlayer to true');
      setShowVideoPlayer(true);
      console.log('🎬 State after setting - showVideoPlayer should be true, videoPath should be:', path);
    } catch (error) {
      console.error('🚨 Video error:', error);
      alert(error instanceof Error ? error.message : 'Failed to find video file');
    }
  };

  const getStatusIcon = (status: RecordingStatus) => {
    if (typeof status === 'object' && 'Failed' in status) {
      return '❌';
    }
    
    switch (status) {
      case 'Recorded': return '📹';
      case 'Extracted': return '📁';
      case 'Analyzed': return '📊';
      case 'SetupRendered': return '🎬';
      case 'Rendered': return '🎥';
      case 'Uploaded': return '🚀';
      default: return '❓';
    }
  };

  const getStatusClassName = (status: RecordingStatus): string => {
    if (typeof status === 'object' && 'Failed' in status) {
      return 'failed';
    }
    
    switch (status) {
      case 'Recorded': return 'recorded';
      case 'Extracted': return 'extracted';
      case 'Analyzed': return 'analyzed';
      case 'SetupRendered': return 'setup';
      case 'Rendered': return 'rendered';
      case 'Uploaded': return 'uploaded';
      default: return 'failed';
    }
  };

  const getPipelineSteps = () => {
    const steps = [
      { name: 'Recorded', status: 'completed' },
      { name: 'Extracted', status: 'pending' },
      { name: 'Analyzed', status: 'pending' },
      { name: 'Setup', status: 'pending' },
      { name: 'Rendered', status: 'pending' },
      { name: 'Uploaded', status: 'pending' }
    ];

    if (!recording) return steps;

    const currentStatus = recording.status;
    let currentIndex = 0;

    if (typeof currentStatus === 'object' && 'Failed' in currentStatus) {
      // For failed status, mark appropriate steps as completed based on what exists
      const path = recording.path;
      if (path.includes('extracted')) currentIndex = 1;
      if (path.includes('analysis')) currentIndex = 2;
      if (path.includes('blender') && !path.includes('render')) currentIndex = 3;
      if (path.includes('render')) currentIndex = 4;
      if (path.includes('uploads')) currentIndex = 5;
      
      steps[currentIndex].status = 'failed';
    } else {
      switch (currentStatus) {
        case 'Recorded': currentIndex = 0; break;
        case 'Extracted': currentIndex = 1; break;
        case 'Analyzed': currentIndex = 2; break;
        case 'SetupRendered': currentIndex = 3; break;
        case 'Rendered': currentIndex = 4; break;
        case 'Uploaded': currentIndex = 5; break;
      }

      // Mark completed steps
      for (let i = 0; i <= currentIndex; i++) {
        steps[i].status = 'completed';
      }

      // Mark current step as current if not the last one
      if (currentIndex < steps.length - 1) {
        steps[currentIndex + 1].status = 'current';
      }
    }

    return steps;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getAvailableActions = () => {
    if (!recording) return [];
    
    const actions = [];
    
    // Add next step action
    if (typeof recording.status === 'string' && recording.status !== 'Uploaded') {
      actions.push('Next Step');
    }
    
    // Add specific step actions based on current status
    if (typeof recording.status === 'object' && 'Failed' in recording.status) {
      actions.push('Retry');
    }
    
    // Add manual step options
    switch (recording.status) {
      case 'Extracted':
        actions.push('Analyze');
        break;
      case 'Analyzed':
        actions.push('Analyze', 'Setup');
        break;
      case 'SetupRendered':
        actions.push('Analyze', 'Setup', 'Render');
        break;
      case 'Rendered':
        actions.push('Analyze', 'Setup', 'Render', 'Upload');
        break;
      case 'Uploaded':
        actions.push('Re-render', 'Re-upload');
        break;
    }
    
    return actions;
  };

  if (loading) {
    return (
      <div>
        <header className="app-header">
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button 
              className="btn btn-secondary"
              onClick={onBack}
              style={{ marginRight: '16px' }}
            >
              <ArrowLeft size={16} />
              Back
            </button>
            <h1 className="app-title" style={{ fontSize: '1.5rem' }}>Loading...</h1>
          </div>
        </header>
        <div className="content content-loading">
          <div className="loading-state">
            Loading recording details...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <header className="app-header">
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button 
              className="btn btn-secondary"
              onClick={onBack}
              style={{ marginRight: '16px' }}
            >
              <ArrowLeft size={16} />
              Back
            </button>
            <h1 className="app-title" style={{ fontSize: '1.5rem' }}>Error</h1>
          </div>
        </header>
        <div className="content content-error">
          <div className="error-state">
            <strong>Error:</strong> {error}
            <button 
              className="btn btn-primary"
              onClick={loadRecordingDetails}
              style={{ marginTop: '10px' }}
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!recording) {
    return (
      <div>
        <header className="app-header">
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button 
              className="btn btn-secondary"
              onClick={onBack}
              style={{ marginRight: '16px' }}
            >
              <ArrowLeft size={16} />
              Back
            </button>
            <h1 className="app-title" style={{ fontSize: '1.5rem' }}>Not Found</h1>
          </div>
        </header>
        <div className="content content-notfound">
          <div className="empty-state">
            Recording not found
          </div>
        </div>
      </div>
    );
  }

  const pipelineSteps = getPipelineSteps();
  const availableActions = getAvailableActions();

  return (
    <div>
      {/* Header */}
      <header className="app-header">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <button 
            className="btn btn-secondary"
            onClick={onBack}
            style={{ marginRight: '16px' }}
          >
            <ArrowLeft size={16} />
            Back
          </button>
          <h1 className="app-title" style={{ fontSize: '1.5rem' }}>{recording.name}</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.5rem' }}>{getStatusIcon(recording.status)}</span>
          <div className={`recording-status ${getStatusClassName(recording.status)}`}>
            {typeof recording.status === 'object' && 'Failed' in recording.status 
              ? `Failed: ${recording.status.Failed}`
              : recording.status
            }
          </div>
        </div>
      </header>

      <div className="content content-main">
        {/* Actions */}
        <div className="recording-card">
          <h2 style={{ margin: '0 0 16px 0', fontSize: '1.125rem', fontWeight: '600' }}>Actions</h2>
          <div className="recording-actions">
            {/* Rename button - always available */}
            <button
              className="btn btn-secondary"
              onClick={handleRenameClick}
              disabled={!!running[recording.name] || renameState.isRenaming}
            >
              <Edit size={16} />
              Rename
            </button>

            {/* Play Video button - always try to show */}
            <button
              className="btn btn-primary"
              onClick={handlePlayVideo}
              disabled={!!running[recording.name]}
            >
              <Film size={16} />
              Play Video
            </button>

            {availableActions.map((action) => (
              <button
                key={action}
                className={`btn ${action === 'Next Step' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => handleRunAction(action)}
                disabled={!!running[recording.name]}
              >
                {action === 'Next Step' && <Play size={16} />}
                {action === 'Retry' && <RotateCcw size={16} />}
                {action === 'View Logs' && <Eye size={16} />}
                {action}
              </button>
            ))}
          </div>
        </div>

        {/* Pipeline Status */}
        <div className="recording-card pipeline-status">
          <h2 style={{ margin: '0 0 20px 0', fontSize: '1.125rem', fontWeight: '600' }}>Pipeline Status</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {pipelineSteps.map((step, index) => (
              <div key={step.name} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--border-radius)',
                  backgroundColor: 
                    step.status === 'completed' ? 'var(--green-success)' :
                    step.status === 'current' ? 'var(--orange-warning)' :
                    step.status === 'failed' ? 'var(--red-danger)' : 'var(--gray-400)',
                  color: 'white',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  minWidth: '80px',
                  textAlign: 'center'
                }}>
                  {step.status === 'completed' ? '✅' : 
                   step.status === 'current' ? '⏳' :
                   step.status === 'failed' ? '❌' : '⭕'} {step.name}
                </div>
                {index < pipelineSteps.length - 1 && (
                  <div style={{ margin: '0 8px', color: 'var(--gray-400)' }}>→</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* File Information */}
        <div className="recording-card">
          <h2 style={{ margin: '0 0 16px 0', fontSize: '1.125rem', fontWeight: '600' }}>Files</h2>
          <div className="files-grid">
            {Object.entries(recording.file_sizes).map(([filename, size]) => (
              <div key={filename} className="file-item">
                <div className="file-item-name">
                  {filename.includes('.mkv') ? '📹' :
                   filename.includes('extracted') ? '📁' :
                   filename.includes('analysis') ? '📊' :
                   filename.includes('render') ? '🎬' : '📄'} {filename}
                </div>
                <div className="file-item-size">
                  {formatFileSize(size)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Operation Output */}
        {(Object.values(running).some(Boolean) || output || operationError) && (
          <div className="recording-card" style={{ backgroundColor: 'var(--gray-50)' }}>
            <h2 style={{ margin: '0 0 16px 0', fontSize: '1.125rem', fontWeight: '600' }}>Operation Status</h2>
            
            {Object.values(running).some(Boolean) && (
              <div style={{ color: 'var(--orange-warning)', marginBottom: '12px', fontWeight: '500' }}>
                🔄 Operation in progress...
              </div>
            )}
            
            {output && (
              <div style={{ 
                backgroundColor: 'var(--green-success)', 
                color: 'white', 
                padding: '12px', 
                borderRadius: 'var(--border-radius)',
                marginBottom: '12px',
                fontFamily: 'monospace',
                fontSize: '0.875rem'
              }}>
                ✅ {output}
              </div>
            )}
            
            {operationError && (
              <div style={{ 
                backgroundColor: 'var(--red-danger)', 
                color: 'white', 
                padding: '12px', 
                borderRadius: 'var(--border-radius)',
                fontFamily: 'monospace',
                fontSize: '0.875rem'
              }}>
                ❌ {operationError}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Preset Configuration Dialog */}
      {showPresetConfig && recording?.status === 'Analyzed' && (
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
          zIndex: 50
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: 'var(--border-radius-lg)',
            padding: '24px',
            maxWidth: '500px',
            width: '90%',
            margin: '16px',
            boxShadow: 'var(--shadow-lg)'
          }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
              Configure Animation
            </h3>
            
            <PresetSelector
              selectedPreset={selectedPreset}
              onPresetChange={setSelectedPreset}
              disabled={!!running[recordingName]}
              className="mb-6"
            />
            
            {/* Show main audio info if available */}
            <div style={{ marginBottom: '16px', padding: '12px', backgroundColor: 'var(--gray-100)', borderRadius: 'var(--border-radius)' }}>
              <p style={{ fontSize: '0.875rem', color: 'var(--gray-600)', margin: 0 }}>
                <strong>Path:</strong> {recording.path}
              </p>
            </div>
            
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowPresetConfig(false)}
                disabled={!!running[recordingName]}
                style={{ flex: 1 }}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={() => handleRunAction('Setup Render')}
                disabled={!!running[recordingName]}
                style={{ flex: 1 }}
              >
                {running[recordingName] ? 'Setting up...' : 'Setup Render'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rename Dialog */}
      <RenameRecordingDialog
        isOpen={renameState.isOpen}
        recording={renameState.recording}
        onRename={handleRename}
        onCancel={hideRenameDialog}
        isRenaming={renameState.isRenaming}
      />

      {/* Video Player Modal */}
      {(() => {
        console.log('🎬 VideoPlayer render check - showVideoPlayer:', showVideoPlayer, 'videoPath:', videoPath);
        return showVideoPlayer && videoPath && (
          <VideoPlayer
            videoPath={videoPath}
            recordingName={recording.name}
            onClose={() => {
              console.log('🎬 Closing VideoPlayer');
              setShowVideoPlayer(false);
              setVideoPath(null);
            }}
          />
        );
      })()}
    </div>
  );
} 