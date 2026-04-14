// src/components/Timeline/Timeline.tsx
import React, { useState, useRef } from 'react';
import { YearStat } from '../../types';

interface TimelineProps {
    data: YearStat[];
    selectedYear: number | null;
    onYearClick: (year: number) => void;
    onReset: () => void;
    pointsCount?: number;
}

const Timeline: React.FC<TimelineProps> = ({
                                               data = [],
                                               selectedYear,
                                               onYearClick,
                                               onReset,
                                               pointsCount = 0
                                           }) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const playIntervalRef = useRef<NodeJS.Timeout>();
    const currentIndexRef = useRef(0);

    console.log('Timeline received data:', data);

    if (!data || !Array.isArray(data) || data.length === 0) {
        return (
            <div style={{ padding: 20, textAlign: 'center', color: '#666' }}>
                <div>No year data available</div>
                <button
                    onClick={() => window.location.reload()}
                    style={{
                        marginTop: 12,
                        background: 'rgba(0, 122, 255, 0.2)',
                        border: '1px solid rgba(0, 122, 255, 0.3)',
                        color: '#007AFF',
                        padding: '6px 12px',
                        borderRadius: 6,
                        fontSize: 11,
                        cursor: 'pointer'
                    }}
                >
                    Reload Data
                </button>
            </div>
        );
    }

    const maxCount = Math.max(...data.map(d => d.count), 1);
    const sortedData = [...data].sort((a, b) => a.year - b.year);

    const stopPlayback = () => {
        setIsPlaying(false);
        if (playIntervalRef.current) {
            clearInterval(playIntervalRef.current);
            playIntervalRef.current = undefined;
        }
    };

    const startPlayback = () => {
        if (isPlaying) {
            stopPlayback();
            return;
        }

        setIsPlaying(true);
        let currentIndex = selectedYear
            ? sortedData.findIndex(d => d.year === selectedYear)
            : 0;

        if (currentIndex === -1) currentIndex = 0;
        currentIndexRef.current = currentIndex;

        playIntervalRef.current = setInterval(() => {
            if (currentIndexRef.current < sortedData.length) {
                const year = sortedData[currentIndexRef.current].year;
                onYearClick(year);
                currentIndexRef.current++;
            } else {
                stopPlayback();
            }
        }, 800);
    };

    const handleReset = () => {
        stopPlayback();
        onReset();
    };

    const handleYearClickLocal = (year: number) => {
        if (!isPlaying) {
            onYearClick(year);
        }
    };

    return (
        <div style={{ padding: '20px', background: 'rgba(20, 20, 30, 0.6)', borderRadius: 12, backdropFilter: 'blur(10px)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ color: '#fff', fontSize: 14, fontWeight: 600, letterSpacing: '0.5px', margin: 0 }}>
                    EPISODES BY YEAR ({sortedData.length} years)
                </h3>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button
                        onClick={startPlayback}
                        style={{
                            background: isPlaying ? 'rgba(255, 59, 48, 0.2)' : 'rgba(0, 122, 255, 0.2)',
                            border: `1px solid ${isPlaying ? '#FF3B30' : '#007AFF'}`,
                            color: isPlaying ? '#FF3B30' : '#007AFF',
                            padding: '4px 12px',
                            borderRadius: 6,
                            fontSize: 11,
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        {isPlaying ? '⏸ PAUSE' : '▶ PLAY'}
                    </button>
                    <button
                        onClick={handleReset}
                        style={{
                            background: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: '#aaa',
                            padding: '4px 12px',
                            borderRadius: 6,
                            fontSize: 11,
                            fontWeight: 600,
                            cursor: 'pointer'
                        }}
                    >
                        RESET
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 140 }}>
                {sortedData.map(stat => {
                    const height = (stat.count / maxCount) * 110;
                    const isSelected = selectedYear === stat.year;

                    return (
                        <div
                            key={stat.year}
                            onClick={() => handleYearClickLocal(stat.year)}
                            style={{
                                flex: 1,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                cursor: isPlaying ? 'default' : 'pointer',
                                transition: 'transform 0.2s'
                            }}
                            onMouseEnter={(e) => {
                                if (!isPlaying) e.currentTarget.style.transform = 'translateY(-4px)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.transform = 'translateY(0)';
                            }}
                        >
                            <div
                                style={{
                                    width: '100%',
                                    height: Math.max(height, 4),
                                    background: isSelected
                                        ? 'linear-gradient(180deg, #007AFF, #00C7BE)'
                                        : 'linear-gradient(180deg, #3a3a4a, #2a2a3a)',
                                    borderRadius: '4px 4px 0 0',
                                    transition: 'all 0.2s',
                                    position: 'relative',
                                    overflow: 'hidden'
                                }}
                            >
                                <div style={{
                                    position: 'absolute',
                                    bottom: 4,
                                    left: 0,
                                    right: 0,
                                    textAlign: 'center',
                                    fontSize: 10,
                                    color: isSelected ? '#fff' : '#888',
                                    fontWeight: isSelected ? 600 : 400
                                }}>
                                    {stat.count}
                                </div>
                            </div>
                            <div style={{
                                fontSize: 10,
                                color: isSelected ? '#007AFF' : '#666',
                                marginTop: 8,
                                fontWeight: isSelected ? 600 : 400
                            }}>
                                {stat.year}
                            </div>
                        </div>
                    );
                })}
            </div>

            {selectedYear && (
                <div style={{
                    marginTop: 12,
                    padding: '8px',
                    background: 'rgba(0, 122, 255, 0.1)',
                    borderRadius: 6,
                    fontSize: 11,
                    color: '#007AFF',
                    textAlign: 'center'
                }}>
                    📍 Showing {pointsCount} episodes from {selectedYear}
                    <button
                        onClick={handleReset}
                        style={{
                            marginLeft: 8,
                            background: 'none',
                            border: 'none',
                            color: '#007AFF',
                            cursor: 'pointer',
                            fontSize: 11,
                            textDecoration: 'underline'
                        }}
                    >
                        Clear
                    </button>
                </div>
            )}
        </div>
    );
};

export default Timeline;