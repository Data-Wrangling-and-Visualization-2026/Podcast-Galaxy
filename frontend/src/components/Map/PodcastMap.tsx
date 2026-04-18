/**
 * Interactive map component using Deck.gl
 * Displays podcast episodes as scatter points with topic-based colors
 */

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { ViewportPoint, Topic, EpisodeDetails } from '../../types';
import { TOPIC_COLORS } from '../../utils/colors';
import './PodcastMap.css';

interface PodcastMapProps {
    points: ViewportPoint[];
    hoveredTopic: Topic | null;
    onPointClick: (episodeId: string) => void;
    onPointHover: (topic: Topic | null) => void;
    onViewportChange?: (bounds: { x1: number; y1: number; x2: number; y2: number }) => void;
    onEpisodeDetails?: (episode: EpisodeDetails | null) => void;
    onZoomEnd?: (bounds: { x1: number; y1: number; x2: number; y2: number }) => void;
}

const DescriptionWithSeeMore: React.FC<{ description: string }> = ({ description }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const truncateLength = 200;

    if (!description) return null;

    const shouldTruncate = description.length > truncateLength && !isExpanded;
    const displayText = shouldTruncate
        ? description.slice(0, truncateLength) + '...'
        : description;

    return (
        <div className="description-inline">
            <span className="description-label">Description</span>
            <span className="tooltip-description">{displayText}</span>
            {description.length > truncateLength && (
                <button
                    className="see-more-btn-inline"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    {isExpanded ? 'Show less' : 'See more'}
                </button>
            )}
        </div>
    );
};

const PodcastMap: React.FC<PodcastMapProps> = ({
                                                   points,
                                                   hoveredTopic,
                                                   onPointClick,
                                                   onPointHover,
                                                   onViewportChange,
                                                   onEpisodeDetails,
                                                   onZoomEnd
                                               }) => {
    const [viewState, setViewState] = useState({
        longitude: 0,
        latitude: 0,
        zoom: 3.5,
        pitch: 0,
        bearing: 0
    });

    const [selectedPoint, setSelectedPoint] = useState<ViewportPoint | null>(null);
    const [hoveredPoint, setHoveredPoint] = useState<ViewportPoint | null>(null);
    const [episodeDetails, setEpisodeDetails] = useState<EpisodeDetails | null>(null);
    const [isLoadingDetails, setIsLoadingDetails] = useState(false);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
    const [glowPointId, setGlowPointId] = useState<string | null>(null);

    const hoverTimeoutRef = useRef<NodeJS.Timeout>();
    const clickTimeoutRef = useRef<NodeJS.Timeout>();
    const glowTimeoutRef = useRef<NodeJS.Timeout>();
    const zoomTimeoutRef = useRef<NodeJS.Timeout>();
    const lastZoomRef = useRef(viewState.zoom);

    const loadEpisodeDetails = useCallback(async (episodeId: string) => {
        console.log('Loading details for episode:', episodeId);
        setIsLoadingDetails(true);
        try {
            const { api } = await import('../../services/api');
            const details = await api.getEpisodeHover(episodeId);
            console.log('Details loaded:', details);
            setEpisodeDetails(details);
            if (onEpisodeDetails) onEpisodeDetails(details);
        } catch (error) {
            console.error('Error loading episode details:', error);
        } finally {
            setIsLoadingDetails(false);
        }
    }, [onEpisodeDetails]);

    const createParticles = useCallback((x: number, y: number, topicColor: string) => {
        const container = document.querySelector('.podcast-map-container');
        if (!container) return;

        const colors = [topicColor, '#ffffff', '#007AFF'];

        for (let i = 0; i < 16; i++) {
            const particle = document.createElement('div');
            particle.className = 'click-particle';

            const angle = (Math.PI * 2 * i) / 16 + Math.random() * 0.5;
            const distance = 40 + Math.random() * 30;
            const tx = Math.cos(angle) * distance;
            const ty = Math.sin(angle) * distance;

            particle.style.left = `${x + tx}px`;
            particle.style.top = `${y + ty}px`;
            particle.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            particle.style.width = `${3 + Math.random() * 4}px`;
            particle.style.height = `${3 + Math.random() * 4}px`;

            container.appendChild(particle);

            setTimeout(() => particle.remove(), 600);
        }
    }, []);

    const createRipple = useCallback((x: number, y: number) => {
        const container = document.querySelector('.podcast-map-container');
        if (!container) return;

        const ripple = document.createElement('div');
        ripple.className = 'click-ripple';
        ripple.style.left = `${x - 20}px`;
        ripple.style.top = `${y - 20}px`;
        ripple.style.width = '40px';
        ripple.style.height = '40px';
        container.appendChild(ripple);

        setTimeout(() => ripple.remove(), 500);
    }, []);

    const triggerGlowEffect = useCallback((episodeId: string) => {
        setGlowPointId(episodeId);

        if (glowTimeoutRef.current) clearTimeout(glowTimeoutRef.current);
        glowTimeoutRef.current = setTimeout(() => {
            setGlowPointId(null);
        }, 500);
    }, []);

    const handleViewStateChange = ({ viewState: newViewState }: any) => {
        setViewState(newViewState);

        if (onViewportChange) {
            const { width, height } = newViewState;
            const { longitude, latitude, zoom } = newViewState;
            const lonPerPixel = 360 / (256 * Math.pow(2, zoom));
            const latPerPixel = 180 / (256 * Math.pow(2, zoom));

            const x1 = longitude - (width / 2) * lonPerPixel;
            const x2 = longitude + (width / 2) * lonPerPixel;
            const y1 = latitude - (height / 2) * latPerPixel;
            const y2 = latitude + (height / 2) * latPerPixel;

            onViewportChange({ x1, y1, x2, y2 });
        }

        if (onZoomEnd) {
            if (zoomTimeoutRef.current) clearTimeout(zoomTimeoutRef.current);

            if (Math.abs(newViewState.zoom - lastZoomRef.current) > 0.01) {
                zoomTimeoutRef.current = setTimeout(() => {
                    const { width, height, longitude, latitude, zoom } = newViewState;
                    const lonPerPixel = 360 / (256 * Math.pow(2, zoom));
                    const latPerPixel = 180 / (256 * Math.pow(2, zoom));
                    const x1 = longitude - (width / 2) * lonPerPixel;
                    const x2 = longitude + (width / 2) * lonPerPixel;
                    const y1 = latitude - (height / 2) * latPerPixel;
                    const y2 = latitude + (height / 2) * latPerPixel;
                    onZoomEnd({ x1, y1, x2, y2 });
                    lastZoomRef.current = zoom;
                }, 300);
            }
        }
    };

    const getPointColor = useCallback((point: ViewportPoint) => {
        if (!point || !point.dominant_topic) return [128, 128, 128, 150];

        const color = TOPIC_COLORS[point.dominant_topic];
        if (!color) return [128, 128, 128, 150];

        const hex = color.replace('#', '');
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);

        const isSelected = selectedPoint?.episode_id === point.episode_id;
        const isGlowing = glowPointId === point.episode_id;
        const isTopicHighlight = hoveredTopic === point.dominant_topic;

        if (isSelected || isGlowing) {
            return [r, g, b, 255];
        }
        if (isTopicHighlight) {
            return [r, g, b, 230];
        }
        return [r, g, b, 160];
    }, [selectedPoint, hoveredTopic, glowPointId]);

    const getPointRadius = useCallback((point: ViewportPoint) => {
        const isSelected = selectedPoint?.episode_id === point.episode_id;
        const isGlowing = glowPointId === point.episode_id;
        const isTopicHighlight = hoveredTopic === point.dominant_topic;
        const isHovered = hoveredPoint?.episode_id === point.episode_id;

        if (isSelected || isGlowing) return 16;
        if (isTopicHighlight) return 11;
        if (isHovered) return 10;
        return 6;
    }, [selectedPoint, hoveredTopic, hoveredPoint, glowPointId]);

    const layers = useMemo(() => new ScatterplotLayer({
        id: 'podcast-points',
        data: points,
        pickable: true,
        getPosition: (d: ViewportPoint) => [d.x || 0, d.y || 0],
        getRadius: (d: ViewportPoint) => getPointRadius(d),
        getFillColor: (d: ViewportPoint) => getPointColor(d),
        getLineColor: [255, 255, 255, 120],
        getLineWidth: 1.5,
        stroked: true,
        radiusMinPixels: 4,
        radiusMaxPixels: 25,
        opacity: 0.95,
        blendMode: 'screen',
        transitions: {
            getRadius: { duration: 350, easing: (t: number) => 1 - Math.pow(1 - t, 3) },
            getFillColor: { duration: 300, easing: (t: number) => 1 - Math.pow(1 - t, 2) }
        }
    }), [points, getPointRadius, getPointColor]);

    const handleClick = useCallback((info: any) => {
        console.log('Click detected', info);

        if (clickTimeoutRef.current) clearTimeout(clickTimeoutRef.current);

        if (info.object && info.object.episode_id) {
            const topicColor = TOPIC_COLORS[info.object.dominant_topic] || '#007AFF';

            createRipple(info.x, info.y);
            createParticles(info.x, info.y, topicColor);
            triggerGlowEffect(info.object.episode_id);

            setSelectedPoint(info.object);
            loadEpisodeDetails(info.object.episode_id);

            if (onPointClick) {
                console.log('Calling onPointClick with:', info.object.episode_id);
                onPointClick(info.object.episode_id);
            }
        } else {
            setSelectedPoint(null);
            setEpisodeDetails(null);
            if (onEpisodeDetails) onEpisodeDetails(null);
        }
    }, [createRipple, createParticles, triggerGlowEffect, loadEpisodeDetails, onPointClick, onEpisodeDetails]);

    const handleHover = useCallback((info: any) => {
        if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);

        hoverTimeoutRef.current = setTimeout(() => {
            if (info.object && info.object.dominant_topic) {
                setHoveredPoint(info.object);
                onPointHover(info.object.dominant_topic);
                setTooltipPosition({ x: info.x, y: info.y });
            } else {
                setHoveredPoint(null);
                onPointHover(null);
            }
        }, 30);
    }, [onPointHover]);

    useEffect(() => {
        return () => {
            if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
            if (clickTimeoutRef.current) clearTimeout(clickTimeoutRef.current);
            if (glowTimeoutRef.current) clearTimeout(glowTimeoutRef.current);
            if (zoomTimeoutRef.current) clearTimeout(zoomTimeoutRef.current);
        };
    }, []);

    return (
        <div className="podcast-map-container">
            <DeckGL
                viewState={viewState}
                onViewStateChange={handleViewStateChange}
                controller={{
                    dragRotate: false,
                    touchRotate: true,
                    inertia: 120,
                    scrollZoom: { speed: 0.008, smooth: true }
                }}
                layers={[layers]}
                onClick={handleClick}
                onHover={handleHover}
            />

            {hoveredPoint && !selectedPoint && (
                <div
                    className="map-hover-tooltip"
                    style={{ left: tooltipPosition.x + 15, top: tooltipPosition.y - 15 }}
                >
                    <div
                        className="hover-tooltip-topic"
                        style={{ borderLeftColor: TOPIC_COLORS[hoveredPoint.dominant_topic] }}
                    >
                        {hoveredPoint.dominant_topic?.replace(/_/g, ' ')}
                    </div>
                </div>
            )}

            {selectedPoint && episodeDetails && (
                <div
                    className={`episode-tooltip ${isLoadingDetails ? 'loading' : ''}`}
                    style={{
                        left: '50%',
                        top: '50%',
                        transform: 'translate(-50%, -50%)'
                    }}
                >
                    <button
                        className="tooltip-close"
                        onClick={() => {
                            setSelectedPoint(null);
                            setEpisodeDetails(null);
                            if (onEpisodeDetails) onEpisodeDetails(null);
                        }}
                    >
                        ×
                    </button>

                    {isLoadingDetails ? (
                        <div className="tooltip-loading">
                            <div className="loading-spinner-small" />
                            <span>Loading episode details...</span>
                        </div>
                    ) : (
                        <>
                            <div
                                className="tooltip-topic-badge"
                                style={{ backgroundColor: `${TOPIC_COLORS[episodeDetails.dominant_topic]}20`, borderLeftColor: TOPIC_COLORS[episodeDetails.dominant_topic] }}
                            >
                                {episodeDetails.dominant_topic?.replace(/_/g, ' ')}
                            </div>

                            <h3 className="tooltip-title">{episodeDetails.title}</h3>

                            <div className="tooltip-podcast">
                                <span className="podcast-label">Podcast name</span>
                                <span className="podcast-name">{episodeDetails.podcast_title}</span>
                            </div>

                            <DescriptionWithSeeMore description={episodeDetails.description} />

                            {episodeDetails.top_3_topics && episodeDetails.top_3_topics.length > 0 && (
                                <div className="tooltip-topics">
                                    <div className="tooltip-topics-title">Top Topics</div>
                                    {episodeDetails.top_3_topics.map((item, idx) => {
                                        const topic = typeof item === 'string' ? item : item.topic;
                                        let weight = typeof item === 'string' ? 1 : item.weight;
                                        const normalizedWeight = weight > 1 ? weight / 100 : weight;
                                        const percent = Math.min(100, Math.max(0, Math.round(normalizedWeight * 100)));
                                        const color = TOPIC_COLORS[topic as keyof typeof TOPIC_COLORS];
                                        return (
                                            <div key={idx} className="tooltip-topic-item">
                                                <div className="tooltip-topic-bar">
                                                    <div
                                                        className="tooltip-topic-fill"
                                                        style={{ width: `${percent}%`, backgroundColor: color }}
                                                    />
                                                </div>
                                                <div className="tooltip-topic-label">
                                                    <span>{topic.replace(/_/g, ' ')}</span>
                                                    <span>{percent}%</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default PodcastMap;