import React, { useState } from 'react';

interface SearchBarProps {
    onSearch: (query: string) => void;
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch }) => {
    const [value, setValue] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSearch(value);
    };

    return (
        <form onSubmit={handleSubmit}>
            <div style={{ position: 'relative' }}>
                <input
                    type="text"
                    placeholder="Search by episode ID..."
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    style={{
                        width: '100%',
                        padding: '10px 36px 10px 12px',
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                        fontSize: 13,
                        color: '#fff',
                        outline: 'none',
                        transition: 'all 0.2s'
                    }}
                    onFocus={(e) => {
                        e.currentTarget.style.borderColor = '#007AFF';
                        e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                    }}
                    onBlur={(e) => {
                        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                        e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                    }}
                />
                <button
                    type="submit"
                    style={{
                        position: 'absolute',
                        right: 8,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        color: '#666',
                        cursor: 'pointer',
                        fontSize: 14
                    }}
                >
                    🔍
                </button>
            </div>
        </form>
    );
};

export default SearchBar;