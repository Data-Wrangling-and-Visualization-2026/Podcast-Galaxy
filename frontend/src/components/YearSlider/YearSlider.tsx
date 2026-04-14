import React, { useState, useEffect, useCallback, useRef } from 'react';
import './YearSlider.css';

interface YearSliderProps {
    years: number[];
    selectedYear: number | null;
    onYearChange: (year: number | null) => void;
    onAllYears: () => void;
    isLoading?: boolean;
}

const YearSlider: React.FC<YearSliderProps> = ({
                                                   years,
                                                   selectedYear,
                                                   onYearChange,
                                                   onAllYears,
                                                   isLoading = false
                                               }) => {
    const [mode, setMode] = useState<'all' | 'single'>('all');
    const [singleYear, setSingleYear] = useState<number>(0);

    const singleTimeoutRef = useRef<NodeJS.Timeout>();

    const sortedYears = React.useMemo(() => [...years].sort((a, b) => a - b), [years]);
    const minYear = sortedYears[0];

    useEffect(() => {
        if (sortedYears.length > 0) {
            setSingleYear(selectedYear !== null ? selectedYear : minYear);
        }
    }, [sortedYears, minYear, selectedYear]);

    const getPercent = useCallback((year: number) => {
        const index = sortedYears.indexOf(year);
        if (index === -1) return 0;
        return (index / (sortedYears.length - 1)) * 100;
    }, [sortedYears]);

    const getYearFromPercent = useCallback((percent: number) => {
        const index = Math.round((percent / 100) * (sortedYears.length - 1));
        return sortedYears[Math.max(0, Math.min(sortedYears.length - 1, index))];
    }, [sortedYears]);

    const handleSingleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (isLoading) return;
        const percent = parseFloat(e.target.value);
        const year = getYearFromPercent(percent);
        setSingleYear(year);

        if (singleTimeoutRef.current) clearTimeout(singleTimeoutRef.current);
        singleTimeoutRef.current = setTimeout(() => {
            onYearChange(year);
        }, 300);
    }, [getYearFromPercent, onYearChange, isLoading]);

    const enableAllMode = useCallback(() => {
        if (isLoading) return;
        setMode('all');
        onAllYears();
    }, [onAllYears, isLoading]);

    const enableSingleMode = useCallback(() => {
        if (isLoading) return;
        setMode('single');
        const currentYear = selectedYear !== null ? selectedYear : singleYear;
        onYearChange(currentYear);
    }, [selectedYear, singleYear, onYearChange, isLoading]);

    const handleYearClick = useCallback((year: number) => {
        if (isLoading) return;
        if (mode === 'single') {
            setSingleYear(year);
            onYearChange(year);
        }
    }, [mode, onYearChange, isLoading]);

    useEffect(() => {
        return () => {
            if (singleTimeoutRef.current) clearTimeout(singleTimeoutRef.current);
        };
    }, []);

    const singlePercent = getPercent(singleYear);

    return (
        <div className={`timeline-container ${isLoading ? 'loading' : ''}`}>
            <div className="timeline-header">
                <div className="timeline-title">TEMPORAL NAVIGATOR</div>
                <div className="timeline-controls">
                    <button
                        className={`timeline-mode-btn ${mode === 'all' ? 'active' : ''}`}
                        onClick={enableAllMode}
                        disabled={isLoading}
                    >
                        All Years
                    </button>
                    <button
                        className={`timeline-mode-btn ${mode === 'single' ? 'active' : ''}`}
                        onClick={enableSingleMode}
                        disabled={isLoading}
                    >
                        Single Year
                    </button>
                </div>
            </div>

            <div className="timeline-slider-container">
                <div className="timeline-track">
                    <div className="timeline-line" />

                    {mode === 'all' && (
                        <div className="timeline-range all-range" style={{ left: 0, width: '100%' }} />
                    )}

                    {mode === 'single' && (
                        <>
                            <div
                                className="timeline-range single-range"
                                style={{ left: 0, width: `${singlePercent}%` }}
                            />
                            <div
                                className="timeline-handle"
                                style={{ left: `${singlePercent}%` }}
                            >
                                <div className="star-handle">
                                    <div className="star-core" />
                                    <div className="star-rays">
                                        <span></span><span></span><span></span><span></span>
                                    </div>
                                </div>
                                <div className="handle-tooltip">{singleYear}</div>
                            </div>
                            <input
                                type="range"
                                min={0}
                                max={100}
                                step={100 / (sortedYears.length - 1)}
                                value={singlePercent}
                                onChange={handleSingleChange}
                                className="timeline-input"
                                disabled={isLoading}
                            />
                        </>
                    )}
                </div>

                <div className="timeline-labels">
                    {sortedYears.map((year, idx) => {
                        const percent = (idx / (sortedYears.length - 1)) * 100;
                        let isActive = false;
                        if (mode === 'single') {
                            isActive = year === singleYear;
                        }
                        return (
                            <div
                                key={year}
                                className={`timeline-label ${isActive ? 'active' : ''}`}
                                onClick={() => handleYearClick(year)}
                                style={{ left: `${percent}%` }}
                            >
                                <div className="label-marker" />
                                <span className="label-year">{year}</span>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="timeline-footer">
                <div className="timeline-info">
                    {mode === 'all' && <span className="all-label">ALL YEARS</span>}
                    {mode === 'single' && (
                        <>
                            <span className="single-label">SELECTED YEAR</span>
                            <span className="single-value">{singleYear}</span>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default YearSlider;