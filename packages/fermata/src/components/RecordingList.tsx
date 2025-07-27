import { Recording, RecordingStatus } from '../types';
import { useRecordings, useRecordingOperations } from '../hooks/useRecordings';
import { useSortingAndFiltering } from '../hooks/useSortingAndFiltering';
import { DeletionConfirmDialog } from './DeletionConfirmDialog';
import { VideoPlayer } from './VideoPlayer';
import { ControlsBar } from './ControlsBar';
import { ResultsCounter } from './ResultsCounter';
import { invoke } from '@tauri-apps/api/core';
import { useState } from 'react';

function formatFileSize(bytes: number): string {
  const sizes = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 B';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

function formatLastUpdated(timestamp: number): string {
  const now = Date.now();
  // Convert timestamp from seconds to milliseconds if it looks like Unix seconds
  const timestampMs = timestamp < 10000000000 ? timestamp * 1000 : timestamp;
  const diff = now - timestampMs;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (minutes > 0) return `${minutes} min ago`;
  return 'Just now';
}

function getStatusDisplay(status: RecordingStatus): { text: string; emoji: string; className: string } {
  if (typeof status === 'object' && 'Failed' in status) {
    return { text: 'Failed', emoji: '❌', className: 'failed' };
  }

  switch (status) {
    case 'Recorded':
      return { text: 'Recorded', emoji: '📹', className: 'recorded' };
    case 'Extracted':
      return { text: 'Extracted', emoji: '📁', className: 'extracted' };
    case 'Analyzed':
      return { text: 'Analyzed', emoji: '📊', className: 'analyzed' };
    case 'SetupRendered':
      return { text: 'Setup', emoji: '🎬', className: 'setup' };
    case 'Rendered':
      return { text: 'Rendered', emoji: '✅', className: 'rendered' };
    case 'Uploaded':
      return { text: 'Uploaded', emoji: '🚀', className: 'uploaded' };
    default:
      return { text: 'Unknown', emoji: '❓', className: 'failed' };
  }
}

function getNextAction(status: RecordingStatus): string | null {
  if (typeof status === 'object' && 'Failed' in status) {
    return 'Retry';
  }

  switch (status) {
    case 'Recorded':
      return 'Extract';
    case 'Extracted':
      return 'Analyze';
    case 'Analyzed':
      return 'Setup';
    case 'SetupRendered':
      return 'Render';
    case 'Rendered':
      return 'Upload';
    case 'Uploaded':
      return null;
    default:
      return null;
  }
}

function RecordingCard({ recording, onAction, isOperationRunning }: {
  recording: Recording;
  onAction: (name: string, action: string) => void;
  isOperationRunning: boolean;
}) {
  const statusDisplay = getStatusDisplay(recording.status);
  const nextAction = getNextAction(recording.status);
  const totalSize = Object.values(recording.file_sizes).reduce((sum, size) => sum + size, 0);

  return (
    <div className="recording-card">
      <div className="recording-card-header">
        <div>
          <h3 className="recording-title">{recording.name}</h3>
          <div className="recording-meta">
            <span>📁 {formatFileSize(totalSize)}</span>
            <span>🕒 {formatLastUpdated(recording.last_updated)}</span>
          </div>
        </div>
        <div className={`recording-status ${statusDisplay.className}`}>
          <span>{statusDisplay.emoji}</span>
          <span>{statusDisplay.text}</span>
        </div>
      </div>

      {typeof recording.status === 'object' && 'Failed' in recording.status && (
        <div style={{
          background: '#fee2e2',
          color: '#dc2626',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '0.875rem',
          marginBottom: '16px'
        }}>
          <strong>Error:</strong> {recording.status.Failed}
        </div>
      )}

      <div className="recording-actions">
        <button
          className="btn btn-secondary"
          onClick={() => onAction(recording.name, 'View')}
        >
          👁️ View
        </button>

        <button
          className="btn btn-primary"
          onClick={() => onAction(recording.name, 'Play Video')}
          disabled={isOperationRunning}
        >
          🎬 Play Video
        </button>

        <button
          className="btn btn-danger"
          onClick={() => onAction(recording.name, 'Delete')}
          disabled={isOperationRunning}
        >
          🗑️ Delete
        </button>

        {nextAction && (
          <button
            className="btn btn-primary"
            onClick={() => onAction(recording.name, nextAction)}
            disabled={isOperationRunning}
          >
            {nextAction}
          </button>
        )}
      </div>
    </div>
  );
}

interface RecordingListProps {
  onSelectRecording?: (recordingName: string) => void;
}

export function RecordingList({ onSelectRecording }: RecordingListProps) {
  const { recordings, loading, error, refreshRecordings, showDeletionDialog, deletionState, deleteRecording, hideDeletionDialog } = useRecordings();
  const { runNextStep, runSpecificStep, running, output } = useRecordingOperations();
  const {
    processedRecordings,
    filterConfig,
    hasActiveFilters,
    updateFilter,
    clearFilters
  } = useSortingAndFiltering(recordings);

  const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [videoPath, setVideoPath] = useState<string | null>(null);
  const [currentRecordingName, setCurrentRecordingName] = useState<string | null>(null);

  const handleAction = async (recordingName: string, action: string) => {
    if (action === 'View') {
      if (onSelectRecording) {
        onSelectRecording(recordingName);
      }
      return;
    }

    if (action === 'Play Video') {
      try {
        const path = await invoke('get_playable_video_path', { recordingName }) as string;
        console.log('🎬 Video path from backend:', path);
        setVideoPath(path);
        setCurrentRecordingName(recordingName);
        setShowVideoPlayer(true);
      } catch (error) {
        console.error('🚨 Video error:', error);
        alert(error instanceof Error ? error.message : 'Failed to find video file');
      }
      return;
    }

    if (action === 'Delete') {
      const recording = recordings.find(r => r.name === recordingName);
      if (recording) {
        showDeletionDialog(recording);
      }
      return;
    }

    if (action === 'Retry') {
      await runNextStep(recordingName);
    } else {
      // Map frontend action names to backend step names
      const stepMap: Record<string, string> = {
        'Extract': 'extract',
        'Analyze': 'analyze',
        'Setup': 'setup_render',
        'Render': 'render',
        'Upload': 'upload'
      };

      const step = stepMap[action] || action.toLowerCase();
      await runSpecificStep(recordingName, step);
    }

    // Refresh recordings after operation
    setTimeout(() => {
      refreshRecordings();
    }, 2000);
  };

  const handleDeleteConfirm = () => {
    if (deletionState.recording) {
      deleteRecording(deletionState.recording.name);
    }
  };

  return (
    <div>
      <header className="app-header">
        <h1 className="app-title">
          <span className="fermata-before">𝄐</span>
          fermata
          <span className="fermata-after">𝄑</span>
        </h1>
        <div className="header-actions">
          <button
            className="btn btn-secondary"
            onClick={refreshRecordings}
          >
            🔄 Refresh
          </button>
          <button
            className="btn btn-secondary"
          >
            ⚙️ Settings
          </button>
        </div>
      </header>

      <div className="content">
        {/* NEW: Controls Bar */}
        <ControlsBar
          filterConfig={filterConfig}
          onUpdateFilter={updateFilter}
          onClearFilters={clearFilters}
          hasActiveFilters={hasActiveFilters}
        />

        {/* NEW: Results Counter */}
        <ResultsCounter
          filteredCount={processedRecordings.length}
          totalCount={recordings.length}
          hasActiveFilters={hasActiveFilters}
        />

        {Object.values(running).some(Boolean) && (
          <div className="operation-status">
            <div className="title">Operation in progress...</div>
            {output && <div className="output">{output}</div>}
          </div>
        )}

        {loading && (
          <div className="loading-state">
            <div>Loading recordings...</div>
          </div>
        )}

        {error && (
          <div className="error-state">
            <div><strong>Error:</strong> {error}</div>
            <button
              className="btn btn-primary"
              onClick={refreshRecordings}
              style={{ marginTop: '10px' }}
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            {processedRecordings.length === 0 ? (
              <div className="empty-state">
                {hasActiveFilters ?
                  'No recordings match your filters. Try adjusting your search or filters.' :
                  'No recordings found. Check your recordings directory configuration.'
                }
              </div>
            ) : (
              <div>
                {processedRecordings.map((recording) => (
                  <RecordingCard
                    key={recording.name}
                    recording={recording}
                    onAction={handleAction}
                    isOperationRunning={!!running[recording.name]}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <DeletionConfirmDialog
        isOpen={deletionState.isOpen}
        recording={deletionState.recording}
        onConfirm={handleDeleteConfirm}
        onCancel={hideDeletionDialog}
        isDeleting={deletionState.isDeleting}
      />

      {/* Video Player Modal */}
      {showVideoPlayer && videoPath && currentRecordingName && (
        <VideoPlayer
          videoPath={videoPath}
          recordingName={currentRecordingName}
          onClose={() => {
            setShowVideoPlayer(false);
            setVideoPath(null);
            setCurrentRecordingName(null);
          }}
        />
      )}
    </div>
  );
}
