import { invoke } from '@tauri-apps/api/core';
import { useEffect } from 'react';

interface VideoPlayerProps {
  videoPath: string;
  recordingName: string;
  onClose: () => void;
}

export function VideoPlayer({ videoPath, recordingName, onClose }: VideoPlayerProps) {
  useEffect(() => {
    // Bezpośrednio otwórz w zewnętrznym odtwarzaczu
    const openVideo = async () => {
      try {
        console.log('🎬 Opening video in external player:', videoPath);
        await invoke('open_video_external', { filePath: videoPath });
        console.log('✅ Video opened successfully');
        // Zamknij modal od razu po otwarciu
        onClose();
      } catch (error) {
        console.error('❌ Failed to open video:', error);
        alert(`Failed to open video: ${error}`);
        onClose();
      }
    };

    openVideo();
  }, [videoPath, onClose]);

  // Prosty modal z informacją o ładowaniu
  return (
    <div
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        color: 'white',
        fontSize: '18px'
      }}
      onClick={onClose}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '48px', marginBottom: '20px' }}>🎬</div>
        <div>Opening video in external player...</div>
        <div style={{ fontSize: '14px', marginTop: '10px', opacity: 0.7 }}>
          {recordingName}
        </div>
        <button
          onClick={onClose}
          style={{
            marginTop: '30px',
            background: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            borderRadius: '6px',
            color: 'white',
            padding: '8px 16px',
            cursor: 'pointer'
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
