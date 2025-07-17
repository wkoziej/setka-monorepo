import { useState } from 'react';
import { RecordingList } from './components/RecordingList';
import { RecordingDetails } from './components/RecordingDetails';

function App() {
  const [selectedRecording, setSelectedRecording] = useState<string | null>(null);

  if (selectedRecording) {
    return (
      <div style={{ height: '100vh', overflow: 'auto' }}>
        <RecordingDetails 
          recordingName={selectedRecording} 
          onBack={() => setSelectedRecording(null)} 
        />
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', overflow: 'auto' }}>
      <RecordingList onSelectRecording={setSelectedRecording} />
    </div>
  );
}

export default App 