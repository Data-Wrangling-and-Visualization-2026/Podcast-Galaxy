/**
 * Custom hook for managing podcast data state
 * Handles points loading, filtering, and year selection
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { api } from '../services/api';

// Кэш для предзагруженных тайлов
const tileCache = new Map();

export const usePodcastData = () => {
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedYear, setSelectedYear] = useState(null);
    const currentBoundsRef = useRef(null);
    const zoomTimeoutRef = useRef(null);
    const preloadTimeoutRef = useRef(null);

    // Функция для расширения границ (предзагрузка соседних тайлов)
    const getExtendedBounds = useCallback((bounds, padding = 0.3) => {
        const width = bounds.x2 - bounds.x1;
        const height = bounds.y2 - bounds.y1;

        return {
            x1: bounds.x1 - width * padding,
            y1: bounds.y1 - height * padding,
            x2: bounds.x2 + width * padding,
            y2: bounds.y2 + height * padding,
        };
    }, []);

    // Функция для разбиения области на тайлы (для предзагрузки)
    const getTiles = useCallback((bounds, tileSize = 5) => {
        const tiles = [];
        const xSteps = Math.ceil((bounds.x2 - bounds.x1) / tileSize);
        const ySteps = Math.ceil((bounds.y2 - bounds.y1) / tileSize);

        for (let i = 0; i <= xSteps; i++) {
            for (let j = 0; j <= ySteps; j++) {
                tiles.push({
                    x1: bounds.x1 + i * tileSize,
                    x2: bounds.x1 + (i + 1) * tileSize,
                    y1: bounds.y1 + j * tileSize,
                    y2: bounds.y1 + (j + 1) * tileSize,
                });
            }
        }
        return tiles;
    }, []);

    // Загрузка точек с плавным переходом
    const loadPointsSmooth = useCallback(async (bounds, year = null) => {
        if (!bounds) return;

        setLoading(true);
        currentBoundsRef.current = bounds;

        try {
            // Сначала загружаем основные точки
            const mainPoints = year
                ? await api.getPointsByYear(year, bounds)
                : await api.getPointsInViewport(bounds);

            setPoints(mainPoints);

            // Предзагружаем соседние тайлы
            const extendedBounds = getExtendedBounds(bounds);
            const tiles = getTiles(extendedBounds);

            // Загружаем тайлы, которых нет в кэше
            for (const tile of tiles) {
                const tileKey = `${tile.x1}_${tile.y1}_${tile.x2}_${tile.y2}_${year || 'all'}`;

                if (!tileCache.has(tileKey)) {
                    tileCache.set(tileKey, true);

                    // Фоновая загрузка
                    setTimeout(async () => {
                        const preloadPoints = year
                            ? await api.getPointsByYear(year, tile)
                            : await api.getPointsInViewport(tile);

                        tileCache.set(tileKey, preloadPoints);
                    }, 100);
                }
            }
        } catch (error) {
            console.error('Error loading points:', error);
        } finally {
            setLoading(false);
        }
    }, [getExtendedBounds, getTiles]);

    // Обработчик изменения зума с плавностью
    const handleZoomChange = useCallback((newBounds, zoomLevel) => {
        // Очищаем предыдущий таймаут
        if (zoomTimeoutRef.current) clearTimeout(zoomTimeoutRef.current);

        // Показываем приблизительные точки (из кэша)
        if (tileCache.size > 0) {
            const cachedPoints = [];
            for (const [_, cachedData] of tileCache) {
                if (Array.isArray(cachedData)) {
                    cachedPoints.push(...cachedData);
                }
            }
            if (cachedPoints.length > 0) {
                setPoints(cachedPoints);
            }
        }

        // Загружаем точные точки после остановки зума
        zoomTimeoutRef.current = setTimeout(() => {
            loadPointsSmooth(newBounds, selectedYear);
        }, 200);
    }, [loadPointsSmooth, selectedYear]);

    return {
        points,
        loading,
        selectedYear,
        loadPointsSmooth,
        handleZoomChange,
        setSelectedYear,
    };
};