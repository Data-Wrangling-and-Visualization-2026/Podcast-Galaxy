import React, { useMemo, useState, useCallback } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Brush
} from 'recharts';
import { YearTopicStat, Topic } from '../../types';
import { TOPIC_COLORS } from '../../utils/colors';
import './TopicLineChart.css';

interface TopicLineChartProps {
    data: YearTopicStat[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    const sortedData = [...payload].sort((a, b) => b.value - a.value);

    return (
        <div className="custom-tooltip">
            <div className="custom-tooltip-header">
                <span className="custom-tooltip-year">{label}</span>
                <span className="custom-tooltip-total">
          Total: {sortedData.reduce((sum, entry) => sum + entry.value, 0)}
        </span>
            </div>
            <div className="custom-tooltip-grid">
                {sortedData.map((entry, index) => (
                    <div key={index} className="custom-tooltip-item">
                        <div className="custom-tooltip-color" style={{ backgroundColor: entry.color }} />
                        <span className="custom-tooltip-name">{entry.name.replace(/_/g, ' ')}</span>
                        <span className="custom-tooltip-value">{entry.value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

const TopicLineChart: React.FC<TopicLineChartProps> = ({ data = [] }) => {
    const [hiddenTopics, setHiddenTopics] = useState<Set<string>>(new Set());
    const [selectedSingleTopic, setSelectedSingleTopic] = useState<string | null>(null);

    const allTopicsList = useMemo(() => {
        if (!data || data.length === 0) return [];
        const allTopics = new Set<string>();
        data.forEach(yearData => {
            if (yearData.topics && typeof yearData.topics === 'object') {
                Object.keys(yearData.topics).forEach(topic => allTopics.add(topic));
            }
        });
        return Array.from(allTopics).sort();
    }, [data]);

    const toggleTopic = useCallback((topic: string) => {
        setHiddenTopics(prev => {
            const newSet = new Set(prev);
            if (newSet.has(topic)) {
                newSet.delete(topic);
            } else {
                newSet.add(topic);
            }
            return newSet;
        });
        setSelectedSingleTopic(null);
    }, []);

    const showSingleTopic = useCallback((topic: string | null) => {
        if (topic === null || topic === 'all') {
            setHiddenTopics(new Set());
            setSelectedSingleTopic(null);
        } else {
            const allTopics = new Set(allTopicsList);
            allTopics.delete(topic);
            setHiddenTopics(allTopics);
            setSelectedSingleTopic(topic);
        }
    }, [allTopicsList]);

    const resetAllFilters = useCallback(() => {
        setHiddenTopics(new Set());
        setSelectedSingleTopic(null);
    }, []);

    const chartData = useMemo(() => {
        if (!data || !Array.isArray(data) || data.length === 0) return [];

        const allTopics = new Set<string>();
        data.forEach(yearData => {
            if (yearData.topics && typeof yearData.topics === 'object') {
                Object.keys(yearData.topics).forEach(topic => allTopics.add(topic));
            }
        });

        const topicsList = Array.from(allTopics);
        if (topicsList.length === 0) return [];

        return data.map(yearData => ({
            year: yearData.year,
            ...topicsList.reduce((acc, topic) => ({
                ...acc,
                [topic]: yearData.topics?.[topic] || 0
            }), {})
        })).sort((a, b) => a.year - b.year);
    }, [data]);

    const allLines = useMemo(() => {
        if (!chartData.length) return [];
        const firstItem = chartData[0];
        if (!firstItem) return [];
        return Object.keys(firstItem).filter(k => k !== 'year');
    }, [chartData]);

    const visibleLines = useMemo(() => {
        return allLines.filter(topic => !hiddenTopics.has(topic));
    }, [allLines, hiddenTopics]);

    if (!data || data.length === 0 || chartData.length === 0) {
        return (
            <div className="chart-loading-state">
                <div className="loading-spinner-chart" />
                <span>Loading topic data...</span>
            </div>
        );
    }

    const selectOptions = [
        { value: 'all', label: 'All Topics' },
        ...allTopicsList.map(topic => ({ value: topic, label: topic.replace(/_/g, ' ') }))
    ];

    return (
        <div className="topic-chart-container">
            <div className="chart-controls">
                <div className="chart-dropdown">
                    <select
                        className="topic-select"
                        value={selectedSingleTopic || 'all'}
                        onChange={(e) => showSingleTopic(e.target.value === 'all' ? null : e.target.value)}
                    >
                        {selectOptions.map(option => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>
                <button className="chart-reset-btn" onClick={resetAllFilters}>
                    Reset All
                </button>
            </div>

            <div className="chart-legend-wrapper">
                <div className="legend-title">TOPICS ({allLines.length})</div>
                <div className="legend-grid">
                    {allLines.map(topic => {
                        const color = TOPIC_COLORS[topic as Topic] || '#888';
                        const isHidden = hiddenTopics.has(topic);
                        return (
                            <div
                                key={topic}
                                className={`legend-item ${isHidden ? 'hidden' : ''}`}
                                onClick={() => toggleTopic(topic)}
                            >
                                <div className="legend-color" style={{ backgroundColor: isHidden ? '#444' : color }} />
                                <span className="legend-name">{topic.replace(/_/g, ' ')}</span>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="chart-main">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                        data={chartData}
                        margin={{ top: 20, right: 30, left: 10, bottom: 30 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                        <XAxis
                            dataKey="year"
                            stroke="#666"
                            tick={{ fill: '#888', fontSize: 12, fontWeight: 500 }}
                            tickLine={{ stroke: '#444' }}
                            axisLine={{ stroke: '#333' }}
                            dy={10}
                        />
                        <YAxis
                            stroke="#666"
                            tick={{ fill: '#888', fontSize: 11 }}
                            tickLine={{ stroke: '#444' }}
                            axisLine={{ stroke: '#333' }}
                            dx={-5}
                        />
                        <Tooltip
                            content={<CustomTooltip />}
                            cursor={{ stroke: '#007AFF', strokeWidth: 1, strokeDasharray: '4 4' }}
                        />
                        <Brush
                            dataKey="year"
                            height={40}
                            stroke="#007AFF"
                            fill="rgba(0, 122, 255, 0.08)"
                            travellerWidth={12}
                            className="chart-brush"
                        />
                        {visibleLines.map(topic => {
                            const color = TOPIC_COLORS[topic as Topic] || '#888';
                            return (
                                <Line
                                    key={topic}
                                    type="monotone"
                                    dataKey={topic}
                                    stroke={color}
                                    strokeWidth={2.5}
                                    dot={{ r: 3, strokeWidth: 1.5, stroke: color, fill: '#0a0a0f', fillOpacity: 0.8 }}
                                    activeDot={{ r: 6, strokeWidth: 2, stroke: color, fill: color, fillOpacity: 0.3 }}
                                    animationDuration={500}
                                    animationEasing="ease-out"
                                    connectNulls={true}
                                    isAnimationActive={true}
                                />
                            );
                        })}
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="chart-footer">
                <span className="footer-hint">Select topic from dropdown | Click on legend to hide/show</span>
                <span className="footer-stats">{visibleLines.length} of {allLines.length} topics visible</span>
            </div>
        </div>
    );
};

export default TopicLineChart;