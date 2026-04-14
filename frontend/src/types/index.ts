/**
 * Central types and interfaces for the Podcast Galaxy application
 * Defines data structures: map points, episodes, year and topic statistics
 */

export const TOPICS = [
    'politics',
    'science',
    'tech',
    'entertainment',
    'art',
    'education',
    'tourism',
    'economics',
    'law',
    'ecology',
    'style',
    'BBC',
    'sports',
    'psychology',
    'religion',
    'architecture',
    'medicine',
    'business',
    'food',
    'history',
    'relationship',
    'family'
] as const;

export type Topic = typeof TOPICS[number];

export interface ViewportPoint {
    episode_id: string;
    x: number;
    y: number;
    dominant_topic: Topic;
    year?: number;
}

export interface EpisodeDetails {
    episode_id: string;
    title: string;
    description: string;
    podcast_title: string;
    dominant_topic: Topic;
    top_3_topics: Array<{ topic: Topic; weight: number }>;
}

export interface YearStat {
    year: number;
    count: number;
}

export interface YearTopicStat {
    year: number;
    topics: Record<string, number>;
}

export interface YearEpisodesResponse {
    year: number;
    episodes: ViewportPoint[];
}

