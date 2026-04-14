import React from 'react';

interface ExportButtonProps {
    onExport: () => void;
}

const ExportButton: React.FC<ExportButtonProps> = ({ onExport }) => {
    return (
        <button
            onClick={onExport}
            style={{
                background: 'rgba(0, 122, 255, 0.15)',
                border: '1px solid rgba(0, 122, 255, 0.3)',
                color: '#007AFF',
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: 6
            }}
            onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(0, 122, 255, 0.25)';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(0, 122, 255, 0.15)';
            }}
        >
            📸 Export PNG
        </button>
    );
};

export default ExportButton;