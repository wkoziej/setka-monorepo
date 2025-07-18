import { Recording } from '../types';

interface DeletionConfirmDialogProps {
  isOpen: boolean;
  recording?: Recording;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}

export function DeletionConfirmDialog({ 
  isOpen, 
  recording, 
  onConfirm, 
  onCancel, 
  isDeleting 
}: DeletionConfirmDialogProps) {
  if (!isOpen || !recording) {
    return null;
  }

  return (
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
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '24px',
        width: '400px',
        maxWidth: '90vw',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15)'
      }}>
        {/* Tytuł */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '20px',
          fontSize: '1.25rem',
          fontWeight: '600'
        }}>
          <span>🗑️</span>
          <span>Usuń nagranie</span>
        </div>

        {/* Pytanie z nazwą nagrania */}
        <div style={{ marginBottom: '16px', fontSize: '1rem' }}>
          Czy na pewno chcesz usunąć nagranie:
        </div>
        
        <div style={{
          marginBottom: '20px',
          fontSize: '1rem',
          fontWeight: '600',
          color: '#1f2937'
        }}>
          "{recording.name}"?
        </div>

        {/* Ostrzeżenie */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '24px',
          padding: '12px',
          backgroundColor: '#fef3c7',
          borderRadius: '8px',
          color: '#92400e'
        }}>
          <span>⚠️</span>
          <span>Ta akcja jest nieodwracalna!</span>
        </div>

        {/* Przyciski */}
        <div style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'flex-end'
        }}>
          <button
            onClick={onCancel}
            disabled={isDeleting}
            style={{
              padding: '10px 20px',
              fontSize: '0.875rem',
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              cursor: isDeleting ? 'not-allowed' : 'pointer',
              opacity: isDeleting ? 0.6 : 1
            }}
          >
            Anuluj
          </button>
          
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            style={{
              padding: '10px 20px',
              fontSize: '0.875rem',
              backgroundColor: isDeleting ? '#f3f4f6' : '#dc2626',
              color: isDeleting ? '#9ca3af' : 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: isDeleting ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              opacity: isDeleting ? 0.6 : 1
            }}
          >
            {isDeleting ? (
              <>
                <span>⏳</span>
                <span>Usuwanie...</span>
              </>
            ) : (
              <>
                <span>🗑️</span>
                <span>Usuń nagranie</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
} 