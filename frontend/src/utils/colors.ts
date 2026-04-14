import { Topic, TOPICS } from '../types';

export const TOPIC_COLORS: Record<Topic, string> = {
    // Красные оттенки
    politics: '#E74C3C',      // Насыщенный красный
    relationship: '#FF6B6B',  // Светло-красный

    // Оранжевые оттенки
    food: '#FF8C42',          // Оранжевый
    tourism: '#F39C12',       // Золотисто-оранжевый

    // Желтые оттенки
    style: '#F1C40F',         // Желтый
    business: '#FFD93D',      // Светло-желтый

    // Зеленые оттенки
    ecology: '#2ECC71',       // Изумрудный
    medicine: '#27AE60',      // Темно-зеленый
    economics: '#1ABC9C',     // Бирюзово-зеленый

    // Голубые/Синие оттенки
    science: '#3498DB',       // Голубой
    tech: '#2980B9',          // Синий
    law: '#5DADE2',           // Светло-синий
    history: '#2471A3',       // Темно-синий
    architecture: '#85C1E9',  // Очень светлый синий

    // Фиолетовые оттенки
    entertainment: '#9B59B6', // Фиолетовый
    art: '#8E44AD',           // Темно-фиолетовый
    BBC: '#BB8FCE',           // Светло-фиолетовый

    // Розовые оттенки
    sports: '#E84393',        // Розовый
    psychology: '#FD99B6',    // Светло-розовый

    // Коричневые/Нейтральные
    religion: '#A0522D',      // Коричневый
    family: '#D35400',        // Терракотовый
    education: '#16A085',     // Мятный

};

// Функция для получения цвета с прозрачностью
export const getColorWithAlpha = (color: string, alpha: number): string => {
    const hex = color.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

// Проверка уникальности цветов
const validateColors = () => {
    const colors = Object.values(TOPIC_COLORS);
    const uniqueColors = new Set(colors);

    if (colors.length !== uniqueColors.size) {
        const duplicates = colors.filter((color, index) => colors.indexOf(color) !== index);
        console.warn('⚠️ Duplicate colors found:', [...new Set(duplicates)]);
    } else {
        console.log('✅ All 22 topics have unique colors');
    }

    const missingColors = TOPICS.filter(topic => !TOPIC_COLORS[topic]);
    if (missingColors.length > 0) {
        console.warn('⚠️ Missing colors for topics:', missingColors);
    }
};

validateColors();