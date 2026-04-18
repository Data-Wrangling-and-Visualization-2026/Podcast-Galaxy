/**
 * API client for backend communication
 * Handles fetching points, statistics, and episode details
 */

import { ViewportPoint, EpisodeDetails, YearStat, YearTopicStat } from '../types';

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
    async getPointsInViewport(bounds: { x1: number; y1: number; x2: number; y2: number }, limit: number = 5000): Promise<ViewportPoint[]> {
        try {
            const response = await fetch(`${BACKEND_URL}/episode/viewport`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    x1: bounds.x1,
                    y1: bounds.y1,
                    x2: bounds.x2,
                    y2: bounds.y2,
                    limit: limit
                })
            });

            if (!response.ok) return [];
            const data = await response.json();
            return Array.isArray(data) ? data : [];
        } catch (error) {
            console.error('Error fetching points:', error);
            return [];
        }
    },

    async getPointsByYear(year: number, bounds?: { x1: number; y1: number; x2: number; y2: number }): Promise<ViewportPoint[]> {
        try {
            const requestBody = {
                x1: bounds?.x1 || -100,
                y1: bounds?.y1 || -100,
                x2: bounds?.x2 || 100,
                y2: bounds?.y2 || 100
            };

            console.log(`Fetching points for year ${year}...`);

            const response = await fetch(`${BACKEND_URL}/episode/viewport/years`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    x1: requestBody.x1,
                    y1: requestBody.y1,
                    x2: requestBody.x2,
                    y2: requestBody.y2,
                    year: year
                })
            });

            if (!response.ok) return [];
            const data = await response.json();
            console.log(`Response for year ${year}:`, data);

            if (Array.isArray(data)) {
                const yearData = data.find(item => item.year === year);
                if (yearData && yearData.episodes) {
                    return yearData.episodes.map((ep: any) => ({
                        ...ep,
                        year: year
                    }));
                }
            }
            return [];
        } catch (error) {
            console.error(`Error fetching points for year ${year}:`, error);
            return [];
        }
    },

    async getYearTopicStats(): Promise<YearTopicStat[]> {
        try {
            const response = await fetch(`${BACKEND_URL}/episode/stats/year-topics`);
            if (!response.ok) return [];
            const data = await response.json();

            if (Array.isArray(data)) {
                return data.map(item => ({
                    year: item.year,
                    topics: item.topics.reduce((acc: Record<string, number>, t: any) => {
                        acc[t.topic] = t.count;
                        return acc;
                    }, {})
                }));
            }
            return [];
        } catch (error) {
            console.error('Error fetching year-topic stats:', error);
            return [];
        }
    },

    async getYearStats(): Promise<YearStat[]> {
        try {
            const yearTopicStats = await this.getYearTopicStats();
            return yearTopicStats.map(yt => ({
                year: yt.year,
                count: Object.values(yt.topics).reduce((sum, count) => sum + count, 0)
            })).sort((a, b) => a.year - b.year);
        } catch (error) {
            console.error('Error fetching year stats:', error);
            return [];
        }
    },

    async getEpisodeHover(episodeId: string): Promise<EpisodeDetails> {
        try {
            const response = await fetch(`${BACKEND_URL}/episode/${episodeId}/hover`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching episode details:', error);
            throw error;
        }
    }
};