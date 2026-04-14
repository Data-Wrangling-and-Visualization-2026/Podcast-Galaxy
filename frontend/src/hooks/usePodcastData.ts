import { useState, useCallback, useEffect } from 'react';
import { ViewportPoint, EpisodeDetails, YearStat, YearTopicStat, Topic } from '../types';
import { api } from '../services/api';

export const usePodcastData = () => {
    const [allPoints, setAllPoints] = useState<ViewportPoint[]>([]);
    const [filteredPoints, setFilteredPoints] = useState<ViewportPoint[]>([]);
    const [selectedEpisode, setSelectedEpisode] = useState<EpisodeDetails | null>(null);
    const [yearStats, setYearStats] = useState<YearStat[]>([]);
    const [topicStats, setTopicStats] = useState<YearTopicStat[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedYear, setSelectedYear] = useState<number | null>(null);
    const [selectedTopics, setSelectedTopics] = useState<Set<Topic>>(new Set());
    const [searchQuery, setSearchQuery] = useState('');
    const [hoveredTopic, setHoveredTopic] = useState<Topic | null>(null);

    useEffect(() => {
        loadStats();
    }, []);

    const loadStats = async () => {
        const topics = await api.getYearTopicStats();
        const years = await api.getYearStats();
        setTopicStats(topics);
        setYearStats(years);
    };

    const loadPointsByYear = useCallback(async (year: number) => {
        setLoading(true);
        try {
            const points = await api.getPointsByYear(year);
            console.log(`Loaded ${points.length} points for year ${year}`);
            setAllPoints(points);
            setSelectedYear(year);
        } catch (error) {
            console.error('Error loading points:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    const resetYearFilter = useCallback(() => {
        setAllPoints([]);
        setSelectedYear(null);
    }, []);

    const applyFilters = useCallback(() => {
        let filtered = [...allPoints];

        if (selectedTopics.size > 0) {
            filtered = filtered.filter(p => selectedTopics.has(p.dominant_topic));
        }

        if (searchQuery) {
            filtered = filtered.filter(p =>
                p.episode_id.toLowerCase().includes(searchQuery.toLowerCase())
            );
        }

        setFilteredPoints(filtered);
    }, [allPoints, selectedTopics, searchQuery]);

    useEffect(() => {
        applyFilters();
    }, [applyFilters]);

    const toggleTopic = useCallback((topic: Topic) => {
        setSelectedTopics(prev => {
            const newSet = new Set(prev);
            if (newSet.has(topic)) newSet.delete(topic);
            else newSet.add(topic);
            return newSet;
        });
    }, []);

    return {
        points: filteredPoints,
        allPoints,
        selectedEpisode,
        yearStats,
        topicStats,
        loading,
        selectedYear,
        hoveredTopic,
        loadPointsByYear,
        resetYearFilter,
        setSelectedEpisode,
        toggleTopic,
        selectedTopics,
        searchQuery,
        setSearchQuery,
        setHoveredTopic
    };
};