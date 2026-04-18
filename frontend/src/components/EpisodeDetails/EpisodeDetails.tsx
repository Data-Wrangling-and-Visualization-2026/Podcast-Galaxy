/**
 * Episode details panel
 * Shows full episode information on point click
 */

import React from 'react';
import { EpisodeDetails as EpisodeDetailsType } from '../../types';
import { TOPIC_COLORS } from '../../utils/colors';

interface EpisodeDetailsProps {
    episode: EpisodeDetailsType | null;
}

const EpisodeDetails: React.FC<EpisodeDetailsProps> = ({ episode }) => {
    if (!episode) {
        return (
            <div style={{
                padding: 20,
                textAlign: 'center',
                color: '#555',
                fontSize: 13,
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 8,
                border: '1px dashed rgba(255,255,255,0.1)'
            }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}></div>
                Click on any point<br />to see episode details
            </div>
        );
    }

    return (
        <div style={{
            background: 'rgba(255,255,255,0.02)',
            borderRadius: 8,
            overflow: 'hidden'
        }}>
            <div style={{
                padding: 12,
                borderBottom: '1px solid rgba(255,255,255,0.05)'
            }}>
                <div style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    background: TOPIC_COLORS[episode.dominant_topic] + '20',
                    borderLeft: `3px solid ${TOPIC_COLORS[episode.dominant_topic]}`,
                    borderRadius: 4,
                    fontSize: 10,
                    fontWeight: 600,
                    color: TOPIC_COLORS[episode.dominant_topic],
                    marginBottom: 10,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                }}>
                    {episode.dominant_topic.replace(/_/g, ' ')}
                </div>

                <h4 style={{
                    color: '#fff',
                    fontSize: 14,
                    fontWeight: 600,
                    marginBottom: 6,
                    lineHeight: 1.3
                }}>
                    {episode.title.length > 60 ? episode.title.slice(0, 60) + '...' : episode.title}
                </h4>

                <p style={{
                    color: '#888',
                    fontSize: 11,
                    marginBottom: 10
                }}>
                    🎙️ {episode.podcast_title}
                </p>

                <p style={{
                    color: '#aaa',
                    fontSize: 11,
                    lineHeight: 1.4,
                    marginBottom: 12
                }}>
                    {episode.description.length > 120
                        ? episode.description.slice(0, 120) + '...'
                        : episode.description}
                </p>
            </div>

            {episode.top_3_topics && episode.top_3_topics.length > 0 && (
                <div style={{ padding: 12 }}>
                    <div style={{
                        fontSize: 10,
                        fontWeight: 600,
                        color: '#666',
                        marginBottom: 10,
                        letterSpacing: '0.5px'
                    }}>
                        TOP TOPICS
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {episode.top_3_topics.map((item, idx) => {
                            const topic = typeof item === 'string' ? item : item.topic;
                            const weight = typeof item === 'string' ? 1 : item.weight;
                            const color = TOPIC_COLORS[topic as keyof typeof TOPIC_COLORS] || '#888';

                            return (
                                <div key={idx}>
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        fontSize: 10,
                                        marginBottom: 3
                                    }}>
                                        <span style={{ color: '#ccc' }}>{topic.replace(/_/g, ' ')}</span>
                                        <span style={{ color: '#666' }}>{Math.round(weight * 100)}%</span>
                                    </div>
                                    <div style={{
                                        height: 2,
                                        background: 'rgba(255,255,255,0.1)',
                                        borderRadius: 1,
                                        overflow: 'hidden'
                                    }}>
                                        <div style={{
                                            width: `${weight * 100}%`,
                                            height: '100%',
                                            background: color,
                                            borderRadius: 1
                                        }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            <div style={{
                padding: 10,
                background: 'rgba(0,122,255,0.1)',
                fontSize: 10,
                color: '#007AFF',
                textAlign: 'center',
                borderTop: '1px solid rgba(0,122,255,0.2)'
            }}>
                ID: {episode.episode_id.slice(0, 16)}...
            </div>
        </div>
    );
};

export default EpisodeDetails;