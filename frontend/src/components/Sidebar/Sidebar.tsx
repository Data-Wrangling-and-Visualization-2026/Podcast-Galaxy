/**
 * Left sidebar with topic filters
 * Clickable chips for toggling topic visibility on map
 */

import React from 'react';
import { Topic, TOPICS } from '../../types';
import { TOPIC_COLORS } from '../../utils/colors';
import './Sidebar.css';

interface SidebarProps {
    selectedTopics: Set<Topic>;
    onToggleTopic: (topic: Topic) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
                                             selectedTopics,
                                             onToggleTopic
                                         }) => {
    return (
        <div className="sidebar">
            <div className="sidebar-filters">
                <div className="filters-header">
                    <span className="filters-title">FILTERS</span>
                    <div className="filters-line" />
                </div>
                <div className="filters-grid">
                    {TOPICS.map(topic => {
                        const isSelected = selectedTopics.has(topic);
                        return (
                            <button
                                key={topic}
                                className={`filter-chip ${isSelected ? 'active' : ''}`}
                                onClick={() => onToggleTopic(topic)}
                            >
                <span
                    className="filter-dot"
                    style={{ backgroundColor: TOPIC_COLORS[topic] }}
                />
                                <span className="filter-name">{topic.replace(/_/g, ' ')}</span>
                                {isSelected && <span className="filter-check">✓</span>}
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default Sidebar;