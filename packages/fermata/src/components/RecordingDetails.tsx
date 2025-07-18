import { useState, useEffect } from 'react';
import { ArrowLeft, Play, RotateCcw, Eye, Edit } from 'lucide-react';
import { Recording, RecordingStatus } from '../types';
import { useRecordingOperations, useRenameRecording } from '../hooks/useRecordings';
import { invoke } from '@tauri-apps/api/core';
import { RenameRecordingDialog } from './RenameRecordingDialog';

interface RecordingDetailsProps {
  recordingName: string;
  onBack: () => void;
  onRecordingRenamed?: (oldName: string, newName: string) => void;
}

export function RecordingDetails({ recordingName, onBack, onRecordingRenamed }: RecordingDetailsProps) {
  const [recording, setRecording] = useState<Recording | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { runNextStep, runSpecificStep, running, output, error: operationError } = useRecordingOperations();
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
      <div style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
          <button 
            onClick={onBack}
            style={{ 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center',
              fontSize: '16px'
            }}
          >
            <ArrowLeft size={20} style={{ marginRight: '8px' }} />
            Back
          </button>
        </div>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          Loading recording details...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
          <button 
            onClick={onBack}
            style={{ 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center',
              fontSize: '16px'
            }}
          >
            <ArrowLeft size={20} style={{ marginRight: '8px' }} />
            Back
          </button>
        </div>
        <div style={{ color: '#dc2626', padding: '20px' }}>
          Error: {error}
          <button 
            onClick={loadRecordingDetails}
            style={{ marginLeft: '10px' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!recording) {
    return (
      <div style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
          <button 
            onClick={onBack}
            style={{ 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center',
              fontSize: '16px'
            }}
          >
            <ArrowLeft size={20} style={{ marginRight: '8px' }} />
            Back
          </button>
        </div>
        <div>Recording not found</div>
      </div>
    );
  }

  const pipelineSteps = getPipelineSteps();
  const availableActions = getAvailableActions();

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <button 
            onClick={onBack}
            style={{ 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center',
              fontSize: '16px',
              marginRight: '15px'
            }}
          >
            <ArrowLeft size={20} style={{ marginRight: '8px' }} />
            Back
          </button>
          <h1 style={{ margin: 0, fontSize: '24px' }}>{recording.name}</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {getStatusIcon(recording.status)}
          <span style={{ marginLeft: '8px', fontSize: '16px', fontWeight: 'bold' }}>
            {typeof recording.status === 'object' && 'Failed' in recording.status 
              ? `Failed: ${recording.status.Failed}`
              : recording.status
            }
          </span>
        </div>
      </div>

      {/* Actions */}
      <div style={{ 
        border: '1px solid #e5e7eb', 
        borderRadius: '8px', 
        padding: '20px', 
        marginBottom: '30px' 
      }}>
        <h2 style={{ margin: '0 0 15px 0', fontSize: '18px' }}>Actions</h2>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {/* Rename button - always available */}
          <button
            onClick={handleRenameClick}
            disabled={!!running[recording.name] || renameState.isRenaming}
            style={{
              padding: '10px 16px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: (running[recording.name] || renameState.isRenaming) ? 'not-allowed' : 'pointer',
              opacity: (running[recording.name] || renameState.isRenaming) ? 0.6 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <Edit size={16} />
            Rename
          </button>

          {availableActions.map((action) => (
            <button
              key={action}
              onClick={() => handleRunAction(action)}
              disabled={!!running[recording.name]}
              style={{
                padding: '10px 16px',
                backgroundColor: action === 'Next Step' ? '#3b82f6' : '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: running ? 'not-allowed' : 'pointer',
                opacity: running ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
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
      <div style={{ 
        border: '1px solid #e5e7eb', 
        borderRadius: '8px', 
        padding: '20px', 
        marginBottom: '30px',
        backgroundColor: '#f9fafb'
      }}>
        <h2 style={{ margin: '0 0 20px 0', fontSize: '18px' }}>Pipeline Status</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {pipelineSteps.map((step, index) => (
            <div key={step.name} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '8px 12px',
                borderRadius: '6px',
                backgroundColor: 
                  step.status === 'completed' ? '#10b981' :
                  step.status === 'current' ? '#f59e0b' :
                  step.status === 'failed' ? '#ef4444' : '#6b7280',
                color: 'white',
                fontSize: '14px',
                fontWeight: 'bold',
                minWidth: '80px',
                textAlign: 'center'
              }}>
                {step.status === 'completed' ? '✅' : 
                 step.status === 'current' ? '⏳' :
                 step.status === 'failed' ? '❌' : '⭕'} {step.name}
              </div>
              {index < pipelineSteps.length - 1 && (
                <div style={{ margin: '0 5px', color: '#6b7280' }}>→</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* File Information */}
      <div style={{ 
        border: '1px solid #e5e7eb', 
        borderRadius: '8px', 
        padding: '20px', 
        marginBottom: '30px' 
      }}>
        <h2 style={{ margin: '0 0 15px 0', fontSize: '18px' }}>Files</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
          {Object.entries(recording.file_sizes).map(([filename, size]) => (
            <div key={filename} style={{
              padding: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              backgroundColor: '#f9fafb'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                {filename.includes('.mkv') ? '📹' :
                 filename.includes('extracted') ? '📁' :
                 filename.includes('analysis') ? '📊' :
                 filename.includes('render') ? '🎬' : '📄'} {filename}
              </div>
              <div style={{ color: '#6b7280', fontSize: '14px' }}>
                {formatFileSize(size)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Operation Output */}
      {(Object.values(running).some(Boolean) || output || operationError) && (
        <div style={{ 
          border: '1px solid #e5e7eb', 
          borderRadius: '8px', 
          padding: '20px',
          backgroundColor: '#f9fafb'
        }}>
          <h2 style={{ margin: '0 0 15px 0', fontSize: '18px' }}>Operation Status</h2>
          
          {Object.values(running).some(Boolean) && (
            <div style={{ color: '#f59e0b', marginBottom: '10px' }}>
              🔄 Operation in progress...
            </div>
          )}
          
          {output && (
            <div style={{ 
              backgroundColor: '#10b981', 
              color: 'white', 
              padding: '10px', 
              borderRadius: '4px',
              marginBottom: '10px',
              fontFamily: 'monospace'
            }}>
              ✅ {output}
            </div>
          )}
          
          {operationError && (
            <div style={{ 
              backgroundColor: '#ef4444', 
              color: 'white', 
              padding: '10px', 
              borderRadius: '4px',
              fontFamily: 'monospace'
            }}>
              ❌ {operationError}
            </div>
          )}
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
    </div>
  );
} 