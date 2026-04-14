/**
 * Interactive map component using Deck.gl
 * Displays podcast episodes as scatter points with topic-based colors
 */

import React, { useState, useCallback, useRef } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { TOPIC_COLORS } from '../../utils/colors';

interface PodcastMapProps {
    points: any[];
    onViewportChange: (bounds: any) => void;
    onZoomEnd?: (bounds: any, zoom: number) => void;
}

const PodcastMap: React.FC<PodcastMapProps> = ({
                                                   points,
                                                   onViewportChange,
                                                   onZoomEnd
                                               }) => {
    const [viewState, setViewState] = useState({
        longitude: 0,
        latitude: 0,
        zoom: 3.5,
        pitch: 0,
        bearing: 0
    });

    const zoomTimeoutRef = useRef(null);
    const lastZoomRef = useRef(viewState.zoom);

    const handleViewStateChange = ({ viewState: newViewState }: any) => {
        setViewState(newViewState);

        // Вычисляем границы
        const { width, height, longitude, latitude, zoom } = newViewState;
        const lonPerPixel = 360 / (256 * Math.pow(2, zoom));
        const latPerPixel = 180 / (256 * Math.pow(2, zoom));

        const x1 = longitude - (width / 2) * lonPerPixel;
        const x2 = longitude + (width / 2) * lonPerPixel;
        const y1 = latitude - (height / 2) * latPerPixel;
        const y2 = latitude + (height / 2) * latPerPixel;

        // Отправляем границы при движении
        onViewportChange({ x1, y1, x2, y2, zoom });

        // Обработка окончания зума
        if (zoomTimeoutRef.current) clearTimeout(zoomTimeoutRef.current);

        if (Math.abs(zoom - lastZoomRef.current) > 0.01) {
            zoomTimeoutRef.current = setTimeout(() => {
                if (onZoomEnd) {
                    onZoomEnd({ x1, y1, x2, y2 }, zoom);
                }
                lastZoomRef.current = zoom;
            }, 300);
        }
    };

    const getPointColor = (point: any) => {
        const color = TOPIC_COLORS[point.dominant_topic];
        if (!color) return [128, 128, 128, 150];
        const hex = color.replace('#', '');
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        return [r, g, b, 180];
    };

    const layers = new ScatterplotLayer({
        id: 'podcast-points',
        data: points,
        pickable: true,
        getPosition: (d: any) => [d.x || 0, d.y || 0],
        getRadius: 6,
        getFillColor: (d: any) => getPointColor(d),
        getLineColor: [255, 255, 255, 80],
        getLineWidth: 1,
        stroked: true,
        radiusMinPixels: 3,
        radiusMaxPixels: 15,
        opacity: 0.9,
        blendMode: 'screen',
        transitions: {
            getRadius: { duration: 200 },
            getFillColor: { duration: 200 }
        }
    });

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%', background: '#0a0a0f' }}>
            <DeckGL
                viewState={viewState}
                onViewStateChange={handleViewStateChange}
                controller={{
                    dragRotate: false,
                    touchRotate: true,
                    inertia: 150,
                    scrollZoom: { speed: 0.008, smooth: true }
                }}
                layers={[layers]}
            />
        </div>
    );
};

export default PodcastMap;