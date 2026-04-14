/**
 * Main application component
 * Orchestrates map, timeline, chart, and sidebar
 */

import React, { useCallback, useEffect, useState, useRef } from 'react';
import PodcastMap from './components/Map/PodcastMap';
import TopicLineChart from './components/TopicLineChart/TopicLineChart';
import YearSlider from './components/YearSlider/YearSlider';
import Sidebar from './components/Sidebar/Sidebar';
import { api } from './services/api';
import { EpisodeDetails } from './types';
import './App.css';

const App: React.FC = () => {
    const [points, setPoints] = useState<any[]>([]);
    const [selectedEpisode, setSelectedEpisode] = useState<EpisodeDetails | null>(null);
    const [yearStats, setYearStats] = useState<any[]>([]);
    const [topicStats, setTopicStats] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedYear, setSelectedYear] = useState<number | null>(null);
    const [hoveredTopic, setHoveredTopic] = useState<string | null>(null);
    const [selectedTopics, setSelectedTopics] = useState<Set<string>>(new Set());

    const currentBoundsRef = useRef({ x1: -10, y1: -10, x2: 10, y2: 10 });
    const loadTimeoutRef = useRef<NodeJS.Timeout>();
    const tileCache = useRef<Map<string, any[]>>(new Map());

    useEffect(() => {
        loadStats();
        loadAllPoints();
    }, []);

    const loadStats = async () => {
        try {
            const years = await api.getYearStats();
            const topics = await api.getYearTopicStats();
            setYearStats(years || []);
            setTopicStats(topics || []);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    };

    const getExtendedBounds = useCallback((bounds: { x1: number; y1: number; x2: number; y2: number }, padding = 0.3) => {
        const width = bounds.x2 - bounds.x1;
        const height = bounds.y2 - bounds.y1;

        return {
            x1: bounds.x1 - width * padding,
            y1: bounds.y1 - height * padding,
            x2: bounds.x2 + width * padding,
            y2: bounds.y2 + height * padding,
        };
    }, []);

    const loadAllPoints = useCallback(async (bounds?: { x1: number; y1: number; x2: number; y2: number }) => {
        if (loading) return;

        setLoading(true);
        try {
            const viewportBounds = bounds || currentBoundsRef.current;
            const newPoints = await api.getPointsInViewport(viewportBounds, 5000);
            setPoints(newPoints);
            setSelectedYear(null);

            const extendedBounds = getExtendedBounds(viewportBounds);
            const extendedPoints = await api.getPointsInViewport(extendedBounds, 10000);

            const cacheKey = `${extendedBounds.x1}_${extendedBounds.y1}_${extendedBounds.x2}_${extendedBounds.y2}`;
            tileCache.current.set(cacheKey, extendedPoints);

            setTimeout(() => {
                tileCache.current.delete(cacheKey);
            }, 300000);

        } catch (error) {
            console.error('Error loading all points:', error);
            setPoints([]);
        } finally {
            setTimeout(() => setLoading(false), 300);
        }
    }, [loading, getExtendedBounds]);

    const loadPointsByYear = useCallback(async (year: number) => {
        if (selectedYear === year) return;

        setLoading(true);
        // ВАЖНО: очищаем точки перед загрузкой нового года
        setPoints([]);  // ← ДОБАВИТЬ ЭТУ СТРОКУ
        setSelectedYear(null);  // ← Временно сбрасываем, чтобы не было смешения

        try {
            const bounds = currentBoundsRef.current;
            const newPoints = await api.getPointsByYear(year, bounds);

            // Проверяем, что все точки имеют правильный год
            const correctYearPoints = newPoints.filter(p => p.year === year);
            console.log(`Loaded ${correctYearPoints.length} points for year ${year}`);

            // Устанавливаем только точки выбранного года
            setPoints(correctYearPoints);
            setSelectedYear(year);

            // Кэширование...
            const extendedBounds = getExtendedBounds(bounds);
            const extendedPoints = await api.getPointsByYear(year, extendedBounds);
            const extendedCorrectPoints = extendedPoints.filter(p => p.year === year);

            const cacheKey = `${year}_${extendedBounds.x1}_${extendedBounds.y1}_${extendedBounds.x2}_${extendedBounds.y2}`;
            tileCache.current.set(cacheKey, extendedCorrectPoints);

        } catch (error) {
            console.error('Error loading points:', error);
            setPoints([]);
            setSelectedYear(null);
        } finally {
            setLoading(false);
        }
    }, [selectedYear, getExtendedBounds]);

    const resetYearFilter = useCallback(() => {
        if (selectedYear === null) return;
        loadAllPoints();
    }, [selectedYear, loadAllPoints]);

    const handleViewportChange = useCallback((bounds: { x1: number; y1: number; x2: number; y2: number }) => {
        currentBoundsRef.current = bounds;

        if (loadTimeoutRef.current) clearTimeout(loadTimeoutRef.current);

        loadTimeoutRef.current = setTimeout(async () => {
            if (selectedYear !== null) {
                const cacheKey = `${selectedYear}_${bounds.x1}_${bounds.y1}_${bounds.x2}_${bounds.y2}`;
                const cached = tileCache.current.get(cacheKey);

                if (cached) {
                    setPoints(cached);
                } else {
                    const newPoints = await api.getPointsByYear(selectedYear, bounds);
                    const pointsWithYear = newPoints.map(p => ({ ...p, year: selectedYear }));
                    setPoints(pointsWithYear);
                    tileCache.current.set(cacheKey, pointsWithYear);
                }
            } else {
                const cacheKey = `${bounds.x1}_${bounds.y1}_${bounds.x2}_${bounds.y2}`;
                const cached = tileCache.current.get(cacheKey);

                if (cached) {
                    console.log('Using cached points');
                    setPoints(cached);
                } else {
                    const newPoints = await api.getPointsInViewport(bounds, 5000);
                    setPoints(newPoints);
                    tileCache.current.set(cacheKey, newPoints);
                    setTimeout(() => tileCache.current.delete(cacheKey), 300000);

                    const extendedBounds = getExtendedBounds(bounds);
                    const extendedKey = `${extendedBounds.x1}_${extendedBounds.y1}_${extendedBounds.x2}_${extendedBounds.y2}`;

                    if (!tileCache.current.has(extendedKey)) {
                        setTimeout(async () => {
                            const extendedPoints = selectedYear
                                ? await api.getPointsByYear(selectedYear, extendedBounds)
                                : await api.getPointsInViewport(extendedBounds, 10000);

                            if (selectedYear) {
                                const correctExtended = extendedPoints.filter(p => p.year === selectedYear);
                                tileCache.current.set(extendedKey, correctExtended);
                            } else {
                                tileCache.current.set(extendedKey, extendedPoints);
                            }
                        }, 500);
                    }
                }
            }
        }, 150);
    }, [selectedYear, getExtendedBounds]);

    const handleZoomEnd = useCallback((bounds: { x1: number; y1: number; x2: number; y2: number }) => {
        console.log('Zoom ended, loading precise points...');
        currentBoundsRef.current = bounds;

        if (selectedYear !== null) {
            loadPointsByYear(selectedYear);
        } else {
            loadAllPoints(bounds);
        }
    }, [selectedYear, loadPointsByYear, loadAllPoints]);

    const getFilteredPoints = useCallback(() => {
        // В начале getFilteredPoints добавьте:
        console.log('Filtering points:', {
            totalPoints: points.length,
            selectedYear,
            pointsWithYear: points.filter(p => p.year === selectedYear).length
        });
        if (selectedYear !== null) {
            const yearPoints = points.filter(p => p.year === selectedYear);
            // Дополнительная фильтрация по темам
            if (selectedTopics.size > 0) {
                return yearPoints.filter(p => selectedTopics.has(p.dominant_topic));
            }
            return yearPoints;
        }

        // Если год не выбран - фильтруем только по темам
        if (selectedTopics.size > 0) {
            return points.filter(p => selectedTopics.has(p.dominant_topic));
        }

        return points;
    }, [points, selectedTopics, selectedYear]);

    const filteredPoints = getFilteredPoints();

    const handleYearChange = useCallback((year: number | null) => {
        if (year === null) {
            resetYearFilter();
        } else {
            loadPointsByYear(year);
        }
    }, [loadPointsByYear, resetYearFilter]);

    const handleAllYears = useCallback(() => {
        resetYearFilter();
    }, [resetYearFilter]);

    const handlePointClick = useCallback(async (episodeId: string) => {
        try {
            const details = await api.getEpisodeHover(episodeId);
            setSelectedEpisode(details);
        } catch (error) {
            console.error('Error loading episode details:', error);
        }
    }, []);

    const toggleTopic = useCallback((topic: string) => {
        setSelectedTopics(prev => {
            const newSet = new Set(prev);
            if (newSet.has(topic)) {
                newSet.delete(topic);
            } else {
                newSet.add(topic);
            }
            return newSet;
        });
    }, []);

    const years = yearStats.map(s => s.year).sort((a, b) => a - b);

    return (
        <div className="app">
            <header className="app-header">
                <div className="header-logo">
                    <div className="logo-icon">
                        <svg width="36" height="36" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="16" cy="16" r="14" stroke="url(#grad)" strokeWidth="1.5" />
                            <circle cx="16" cy="16" r="8" stroke="url(#grad)" strokeWidth="1" />
                            <circle cx="16" cy="16" r="3" fill="#007AFF" />
                            <defs>
                                <linearGradient id="grad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#007AFF" />
                                    <stop offset="1" stopColor="#00C7BE" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <div className="header-title">
                        <h1>PODCAST GALAXY</h1>
                        <span>explore the universe of ideas</span>
                    </div>
                </div>

                {selectedYear && (
                    <div className="header-badge">
                        <span className="badge-label">viewing</span>
                        <span className="badge-value">{selectedYear}</span>
                    </div>
                )}
            </header>

            <div className="app-main">
                <div style={{ width: 160, flexShrink: 0, overflow: 'visible', borderRight: '1px solid rgba(255,255,255,0.05)' }}>
                    <Sidebar
                        selectedTopics={selectedTopics}
                        onToggleTopic={toggleTopic}
                    />
                </div>

                <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
                    <PodcastMap
                        points={filteredPoints}
                        hoveredTopic={hoveredTopic}
                        onPointClick={handlePointClick}
                        onPointHover={setHoveredTopic}
                        onViewportChange={handleViewportChange}
                        onZoomEnd={handleZoomEnd}
                    />

                    {years.length > 0 && (
                        <YearSlider
                            years={years}
                            selectedYear={selectedYear}
                            onYearChange={handleYearChange}
                            onAllYears={handleAllYears}
                            isLoading={loading}
                        />
                    )}

                    {loading && (
                        <div className="loading-overlay">
                            <div className="loading-spinner" />
                        </div>
                    )}

                    {selectedYear && (
                        <div className="year-badge">
                            Showing year: {selectedYear}
                        </div>
                    )}
                </div>

                <div style={{
                    width: 540,
                    flexShrink: 0,
                    padding: '12px 16px',
                    background: 'linear-gradient(180deg, rgba(15, 15, 25, 0.95) 0%, rgba(10, 10, 20, 0.98) 100%)',
                    borderLeft: '1px solid rgba(255,255,255,0.05)',
                    display: 'flex',
                    flexDirection: 'column',
                    height: '100%',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        background: 'rgba(20, 20, 30, 0.4)',
                        borderRadius: 12,
                        padding: '12px 14px',
                        backdropFilter: 'blur(10px)',
                        display: 'flex',
                        flexDirection: 'column',
                        height: '100%',
                        overflow: 'hidden'
                    }}>
                        <h3 style={{
                            color: '#fff',
                            fontSize: 12,
                            fontWeight: 600,
                            marginBottom: 12,
                            letterSpacing: '0.5px',
                            flexShrink: 0
                        }}>
                            TOPIC EVOLUTION ({topicStats.length} years)
                        </h3>
                        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
                            {topicStats.length > 0 ? (
                                <TopicLineChart data={topicStats} />
                            ) : (
                                <div style={{ color: '#666', textAlign: 'center', padding: 40 }}>Loading chart data...</div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default App;