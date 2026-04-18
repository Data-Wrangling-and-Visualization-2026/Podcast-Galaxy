/**
 * Color scheme for 22 podcast categories
 * Unique colors for each topic, used on map and line chart
 */

import { Topic, TOPICS } from '../types';

export const TOPIC_COLORS: Record<Topic, string> = {
    politics: '#E74C3C',
    relationship: '#FF6B6B',

    food: '#FF8C42',
    tourism: '#F39C12',

    style: '#F1C40F',
    business: '#FFD93D',

    ecology: '#2ECC71',
    medicine: '#27AE60',
    economics: '#1ABC9C',

    science: '#3498DB',
    tech: '#2980B9',
    law: '#5DADE2',
    history: '#2471A3',
    architecture: '#85C1E9',

    entertainment: '#9B59B6',
    art: '#8E44AD',
    BBC: '#BB8FCE',

    sports: '#E84393',
    psychology: '#FD99B6',

    religion: '#A0522D',
    family: '#D35400',
    education: '#16A085',

};

export const getColorWithAlpha = (color: string, alpha: number): string => {
    const hex = color.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const validateColors = () => {
    const colors = Object.values(TOPIC_COLORS);
    const uniqueColors = new Set(colors);

    if (colors.length !== uniqueColors.size) {
        const duplicates = colors.filter((color, index) => colors.indexOf(color) !== index);
    } else {
        console.log('All 22 topics have unique colors');
    }

    const missingColors = TOPICS.filter(topic => !TOPIC_COLORS[topic]);
    if (missingColors.length > 0) {
        console.warn('⚠️ Missing colors for topics:', missingColors);
    }
};

validateColors();