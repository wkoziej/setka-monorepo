import { Recording, RecordingStatus } from '../types';
import { useRecordings, useRecordingOperations } from '../hooks/useRecordings';

function formatFileSize(bytes: number): string {
  const sizes = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 B';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

function formatLastUpdated(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (minutes > 0) return `${minutes} min ago`;
  return 'Just now';
}

function getStatusDisplay(status: RecordingStatus): { text: string; emoji: string; color: string } {
  if (typeof status === 'object' && 'Failed' in status) {
    return { text: 'Failed', emoji: '❌', color: '#dc2626' };
  }
  
  switch (status) {
    case 'Recorded':
      return { text: 'Recorded', emoji: '📹', color: '#7c3aed' };
    case 'Extracted':
      return { text: 'Extracted', emoji: '📁', color: '#2563eb' };
    case 'Analyzed':
      return { text: 'Analyzed', emoji: '📊', color: '#059669' };
    case 'Rendered':
      return { text: 'Rendered', emoji: '✅', color: '#16a34a' };
    case 'Uploaded':
      return { text: 'Uploaded', emoji: '🚀', color: '#0891b2' };
    default:
      return { text: 'Unknown', emoji: '❓', color: '#6b7280' };
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
      return 'Render';
    case 'Rendered':
      return 'Upload';
    case 'Uploaded':
      return null;
    default:
      return null;
  }
}

function RecordingRow({ recording, onAction }: { 
  recording: Recording; 
  onAction: (name: string, action: string) => void;
}) {
  const statusDisplay = getStatusDisplay(recording.status);
  const nextAction = getNextAction(recording.status);
  const totalSize = Object.values(recording.file_sizes).reduce((sum, size) => sum + size, 0);

  return (
    <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
      <td style={{ padding: '12px 8px' }}>
        <div style={{ fontWeight: '500' }}>{recording.name}</div>
        <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
          {formatFileSize(totalSize)}
        </div>
      </td>
      <td style={{ padding: '12px 8px' }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px',
          color: statusDisplay.color 
        }}>
          <span>{statusDisplay.emoji}</span>
          <span>{statusDisplay.text}</span>
        </div>
        {typeof recording.status === 'object' && 'Failed' in recording.status && (
          <div style={{ fontSize: '0.75rem', color: '#dc2626', marginTop: '4px' }}>
            {recording.status.Failed}
          </div>
        )}
      </td>
      <td style={{ padding: '12px 8px', color: '#6b7280' }}>
        {formatLastUpdated(recording.last_updated)}
      </td>
      <td style={{ padding: '12px 8px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {nextAction && (
            <button
              onClick={() => onAction(recording.name, nextAction)}
              style={{
                padding: '6px 12px',
                fontSize: '0.875rem',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              {nextAction}
            </button>
          )}
          <button
            onClick={() => onAction(recording.name, 'View')}
            style={{
              padding: '6px 12px',
              fontSize: '0.875rem',
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            View
          </button>
        </div>
      </td>
    </tr>
  );
}

export function RecordingList() {
  const { recordings, loading, error, refreshRecordings } = useRecordings();
  const { runNextStep, runSpecificStep, running, output } = useRecordingOperations();

  const handleAction = async (recordingName: string, action: string) => {
    if (action === 'View') {
      // TODO: Implement recording details view
      console.log('View recording:', recordingName);
      return;
    }

    if (action === 'Retry') {
      await runNextStep(recordingName);
    } else {
      await runSpecificStep(recordingName, action.toLowerCase());
    }
    
    // Refresh recordings after operation
    setTimeout(() => {
      refreshRecordings();
    }, 2000);
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <div>Loading recordings...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: '#dc2626' }}>
        <div>Error: {error}</div>
        <button 
          onClick={refreshRecordings}
          style={{ marginTop: '10px' }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '20px' 
      }}>
        <h1>fermata - Recording Manager</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={refreshRecordings}
            style={{ padding: '8px 16px' }}
          >
            Refresh
          </button>
          <button 
            style={{ 
              padding: '8px 16px',
              backgroundColor: '#f3f4f6',
              color: '#374151'
            }}
          >
            Settings
          </button>
        </div>
      </div>

      {running && (
        <div style={{ 
          marginBottom: '20px', 
          padding: '12px', 
          backgroundColor: '#fef3c7', 
          border: '1px solid #f59e0b',
          borderRadius: '6px' 
        }}>
          <div style={{ fontWeight: '500' }}>Operation in progress...</div>
          {output && <div style={{ marginTop: '8px', fontFamily: 'monospace' }}>{output}</div>}
        </div>
      )}

      <div style={{ 
        border: '1px solid #e5e7eb', 
        borderRadius: '8px', 
        overflow: 'hidden' 
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ backgroundColor: '#f9fafb' }}>
            <tr>
              <th style={{ 
                padding: '12px 8px', 
                textAlign: 'left', 
                fontWeight: '600',
                borderBottom: '1px solid #e5e7eb'
              }}>
                Recording Name
              </th>
              <th style={{ 
                padding: '12px 8px', 
                textAlign: 'left', 
                fontWeight: '600',
                borderBottom: '1px solid #e5e7eb'
              }}>
                Status
              </th>
              <th style={{ 
                padding: '12px 8px', 
                textAlign: 'left', 
                fontWeight: '600',
                borderBottom: '1px solid #e5e7eb'
              }}>
                Last Updated
              </th>
              <th style={{ 
                padding: '12px 8px', 
                textAlign: 'left', 
                fontWeight: '600',
                borderBottom: '1px solid #e5e7eb'
              }}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {recordings.map((recording) => (
              <RecordingRow
                key={recording.name}
                recording={recording}
                onAction={handleAction}
              />
            ))}
          </tbody>
        </table>
      </div>

      {recordings.length === 0 && (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px', 
          color: '#6b7280' 
        }}>
          No recordings found. Check your recordings directory configuration.
        </div>
      )}
    </div>
  );
} 