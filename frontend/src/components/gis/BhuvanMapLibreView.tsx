import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

type MapLibreMap = maplibregl.Map;

import {
  BHUVAN_SERVICES,
  SatelliteSourceType,
  INDIA_BOUNDARY_GEOJSON,
  FRONTIER_BORDERS_GEOJSON,
  PROTOTYPE_SECTOR_GEOJSON,
  CONTEXTUAL_SECTORS_GEOJSON,
  buildCameraGeoJson,
  buildTracksGeoJson,
  buildEventsGeoJson,
} from './bhuvanGisConfig';
import { CameraInfo, TrackState, EventRecord, StreamHealthContract, EnvironmentState } from '../../types';
import {
  Compass,
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Shield,
  Radio,
  AlertTriangle,
  Crosshair,
} from 'lucide-react';

export interface BhuvanLayerVisibility {
  satellite: boolean;
  nationalBoundary: boolean;
  borderContext: boolean;
  prototypeSector: boolean;
  cameraSensor: boolean;
  activeTracks: boolean;
  securityEvents: boolean;
  environment: boolean;
}

interface BhuvanMapLibreViewProps {
  camera: CameraInfo | null;
  activeEvents: EventRecord[];
  activeTracks: TrackState[];
  streamHealth?: StreamHealthContract;
  environment?: EnvironmentState;
  isBackendOnline: boolean;
  selectedSectorId?: string;
  onSelectSector?: (sectorId: string) => void;
  height?: string | number;
}

export const BhuvanMapLibreView: React.FC<BhuvanMapLibreViewProps> = ({
  camera,
  activeEvents,
  activeTracks,
  streamHealth,
  environment,
  isBackendOnline,
  selectedSectorId,
  onSelectSector,
  height = '100%',
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<MapLibreMap | null>(null);

  // Satellite Source State: Bhuvan WMS (remote) vs Local Offline Satellite vs Dark Tactical
  const [satelliteSource, setSatelliteSource] = useState<SatelliteSourceType>('BHUVAN_WMS');
  const [isWmsOnline, setIsWmsOnline] = useState<boolean>(true);
  const [cursorCoords, setCursorCoords] = useState<{ lng: number; lat: number }>({ lng: 77.2, lat: 28.6 });
  const [zoomLevel, setZoomLevel] = useState<number>(4.2);

  // Independent Layer Toggles
  const [layers, setLayers] = useState<BhuvanLayerVisibility>({
    satellite: true,
    nationalBoundary: true,
    borderContext: true,
    prototypeSector: true,
    cameraSensor: true,
    activeTracks: true,
    securityEvents: true,
    environment: true,
  });

  const toggleLayer = (key: keyof BhuvanLayerVisibility) => {
    setLayers((prev) => {
      const updated = { ...prev, [key]: !prev[key] };
      applyLayerVisibility(key, updated[key]);
      return updated;
    });
  };

  // Synchronize MapLibre layer visibility
  const applyLayerVisibility = (key: keyof BhuvanLayerVisibility, visible: boolean) => {
    const map = mapInstanceRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const visibilityStr = visible ? 'visible' : 'none';

    switch (key) {
      case 'satellite':
        if (map.getLayer('bhuvan-satellite-layer')) {
          map.setLayoutProperty('bhuvan-satellite-layer', 'visibility', visibilityStr);
        }
        break;
      case 'nationalBoundary':
        if (map.getLayer('india-boundary-line')) {
          map.setLayoutProperty('india-boundary-line', 'visibility', visibilityStr);
          map.setLayoutProperty('india-boundary-fill', 'visibility', visibilityStr);
        }
        break;
      case 'borderContext':
        if (map.getLayer('frontier-borders-line')) {
          map.setLayoutProperty('frontier-borders-line', 'visibility', visibilityStr);
        }
        break;
      case 'prototypeSector':
        if (map.getLayer('prototype-sector-fill')) {
          map.setLayoutProperty('prototype-sector-fill', 'visibility', visibilityStr);
          map.setLayoutProperty('prototype-sector-line', 'visibility', visibilityStr);
        }
        break;
      case 'cameraSensor':
        if (map.getLayer('camera-sensor-circle')) {
          map.setLayoutProperty('camera-sensor-circle', 'visibility', visibilityStr);
        }
        break;
      case 'activeTracks':
        if (map.getLayer('active-tracks-points')) {
          map.setLayoutProperty('active-tracks-points', 'visibility', visibilityStr);
          if (map.getLayer('active-tracks-lines')) {
            map.setLayoutProperty('active-tracks-lines', 'visibility', visibilityStr);
          }
        }
        break;
      case 'securityEvents':
        if (map.getLayer('security-events-points')) {
          map.setLayoutProperty('security-events-points', 'visibility', visibilityStr);
        }
        break;
      default:
        break;
    }
  };

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Tactical dark baseline style
    const initialStyle: maplibregl.StyleSpecification = {
      version: 8,
      sources: {
        'bhuvan-satellite-source': {
          type: 'raster',
          tiles: [BHUVAN_SERVICES.SATELLITE_HIGH_RES.tileUrlTemplate],
          tileSize: 256,
          attribution: '© NRSC / ISRO Bhuvan Satellite Portal',
        },
        'india-boundary-source': {
          type: 'geojson',
          data: INDIA_BOUNDARY_GEOJSON,
        },
        'frontier-borders-source': {
          type: 'geojson',
          data: FRONTIER_BORDERS_GEOJSON,
        },
        'prototype-sector-source': {
          type: 'geojson',
          data: PROTOTYPE_SECTOR_GEOJSON,
        },
        'contextual-sectors-source': {
          type: 'geojson',
          data: CONTEXTUAL_SECTORS_GEOJSON,
        },
        'camera-sensor-source': {
          type: 'geojson',
          data: buildCameraGeoJson(camera),
        },
        'active-tracks-source': {
          type: 'geojson',
          data: buildTracksGeoJson(activeTracks),
        },
        'security-events-source': {
          type: 'geojson',
          data: buildEventsGeoJson(activeEvents),
        },
      },
      layers: [
        // 1. Background Base
        {
          id: 'dark-background',
          type: 'background',
          paint: {
            'background-color': '#06090e',
          },
        },
        // 2. Bhuvan Satellite Raster Layer
        {
          id: 'bhuvan-satellite-layer',
          type: 'raster',
          source: 'bhuvan-satellite-source',
          paint: {
            'raster-opacity': 0.75,
            'raster-contrast': 0.1,
          },
        },
        // 3. National Boundary Fill & Line
        {
          id: 'india-boundary-fill',
          type: 'fill',
          source: 'india-boundary-source',
          paint: {
            'fill-color': '#0e1726',
            'fill-opacity': 0.35,
          },
        },
        {
          id: 'india-boundary-line',
          type: 'line',
          source: 'india-boundary-source',
          paint: {
            'line-color': '#60A5FA',
            'line-width': 1.5,
            'line-opacity': 0.8,
          },
        },
        // 4. Frontier Borders (LOC, International Borders)
        {
          id: 'frontier-borders-line',
          type: 'line',
          source: 'frontier-borders-source',
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 2.5,
            'line-dasharray': [3, 2],
          },
        },
        // 5. Prototype Sector (Sector B-07)
        {
          id: 'prototype-sector-fill',
          type: 'fill',
          source: 'prototype-sector-source',
          paint: {
            'fill-color': '#06B6D4',
            'fill-opacity': 0.15,
          },
        },
        {
          id: 'prototype-sector-line',
          type: 'line',
          source: 'prototype-sector-source',
          paint: {
            'line-color': '#10B981',
            'line-width': 2,
          },
        },
        // 6. Contextual Sector Markers
        {
          id: 'contextual-sectors-points',
          type: 'circle',
          source: 'contextual-sectors-source',
          paint: {
            'circle-radius': 4,
            'circle-color': '#6B7280',
            'circle-stroke-width': 1,
            'circle-stroke-color': '#9CA3AF',
          },
        },
        // 7. Active Camera Sensor
        {
          id: 'camera-sensor-circle',
          type: 'circle',
          source: 'camera-sensor-source',
          paint: {
            'circle-radius': 7,
            'circle-color': '#10B981',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#FFFFFF',
          },
        },
        // 8. Active Tracks
        {
          id: 'active-tracks-lines',
          type: 'line',
          source: 'active-tracks-source',
          filter: ['==', '$type', 'LineString'],
          paint: {
            'line-color': '#38BDF8',
            'line-width': 2,
            'line-dasharray': [2, 1],
          },
        },
        {
          id: 'active-tracks-points',
          type: 'circle',
          source: 'active-tracks-source',
          filter: ['==', '$type', 'Point'],
          paint: {
            'circle-radius': 5,
            'circle-color': '#38BDF8',
            'circle-stroke-width': 1,
            'circle-stroke-color': '#FFFFFF',
          },
        },
        // 9. Security Events
        {
          id: 'security-events-points',
          type: 'circle',
          source: 'security-events-source',
          paint: {
            'circle-radius': 9,
            'circle-color': '#EF4444',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#FBBF24',
          },
        },
      ],
    };

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: initialStyle,
      center: [78.96, 23.59], // Geographical center of India
      zoom: 4.2,
      minZoom: 3.5,
      maxZoom: 16,
      attributionControl: false,
    });

    map.on('mousemove', (e: any) => {
      setCursorCoords({
        lng: Math.round(e.lngLat.lng * 1000) / 1000,
        lat: Math.round(e.lngLat.lat * 1000) / 1000,
      });
    });

    map.on('zoom', () => {
      setZoomLevel(Math.round(map.getZoom() * 10) / 10);
    });

    // Interactive cursor and click handling
    map.on('click', 'prototype-sector-fill', () => {
      if (onSelectSector) onSelectSector('SECTOR-B07');
    });
    map.on('click', 'contextual-sectors-points', (e: any) => {
      if (e.features && e.features[0]) {
        const id = e.features[0].properties?.id;
        if (id && onSelectSector) onSelectSector(id);
      }
    });

    const pointerLayers = ['contextual-sectors-points', 'prototype-sector-fill', 'camera-sensor-circle', 'security-events-points'];
    pointerLayers.forEach((layerId) => {
      map.on('mouseenter', layerId, () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', layerId, () => {
        map.getCanvas().style.cursor = '';
      });
    });

    // Handle tile load errors on remote Bhuvan WMS
    map.on('error', (e: any) => {
      if (e.error && (e.error as any).status >= 400) {
        setIsWmsOnline(false);
      }
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update dynamic GeoJSON data when props change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // Update camera source
    const camSrc = map.getSource('camera-sensor-source') as maplibregl.GeoJSONSource;
    if (camSrc) camSrc.setData(buildCameraGeoJson(camera));

    // Update tracks source
    const trackSrc = map.getSource('active-tracks-source') as maplibregl.GeoJSONSource;
    if (trackSrc) trackSrc.setData(buildTracksGeoJson(activeTracks));

    // Update events source
    const evSrc = map.getSource('security-events-source') as maplibregl.GeoJSONSource;
    if (evSrc) evSrc.setData(buildEventsGeoJson(activeEvents));
  }, [camera, activeTracks, activeEvents]);

  // Handle satellite source switching (Bhuvan WMS vs Local Offline Satellite)
  const handleChangeSatelliteSource = (sourceType: SatelliteSourceType) => {
    setSatelliteSource(sourceType);
    const map = mapInstanceRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (sourceType === 'BHUVAN_WMS') {
      if (map.getLayer('bhuvan-satellite-layer')) {
        map.setLayoutProperty('bhuvan-satellite-layer', 'visibility', 'visible');
        map.setPaintProperty('bhuvan-satellite-layer', 'raster-opacity', 0.75);
      }
    } else if (sourceType === 'LOCAL_OFFLINE_SATELLITE') {
      if (map.getLayer('bhuvan-satellite-layer')) {
        // High-contrast offline tactical satellite backdrop
        map.setLayoutProperty('bhuvan-satellite-layer', 'visibility', 'none');
      }
      map.setPaintProperty('dark-background', 'background-color', '#09131e');
      if (map.getLayer('india-boundary-fill')) {
        map.setPaintProperty('india-boundary-fill', 'fill-opacity', 0.55);
        map.setPaintProperty('india-boundary-fill', 'fill-color', '#122336');
      }
    } else {
      if (map.getLayer('bhuvan-satellite-layer')) {
        map.setLayoutProperty('bhuvan-satellite-layer', 'visibility', 'none');
      }
      map.setPaintProperty('dark-background', 'background-color', '#05080c');
      if (map.getLayer('india-boundary-fill')) {
        map.setPaintProperty('india-boundary-fill', 'fill-opacity', 0.25);
        map.setPaintProperty('india-boundary-fill', 'fill-color', '#0e1726');
      }
    }
  };

  // Jump camera viewport to Sector B-07
  const handleFocusPrototypeSector = () => {
    const map = mapInstanceRef.current;
    if (!map) return;
    map.flyTo({
      center: [74.82, 34.25],
      zoom: 12,
      pitch: 35,
      bearing: 15,
      essential: true,
    });
    if (onSelectSector) onSelectSector('SECTOR-B07');
  };

  // Reset to national view
  const handleResetNationalView = () => {
    const map = mapInstanceRef.current;
    if (!map) return;
    map.flyTo({
      center: [78.96, 23.59],
      zoom: 4.2,
      pitch: 0,
      bearing: 0,
      essential: true,
    });
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: height,
        minHeight: '620px',
        backgroundColor: '#05080d',
        borderRadius: '6px',
        border: '1px solid var(--color-border)',
        overflow: 'hidden',
      }}
    >
      {/* 1. Top Ribbon: Bhuvan Service & Scope Indicator */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          left: 14,
          zIndex: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          pointerEvents: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              padding: '2px 8px',
              borderRadius: '3px',
              backgroundColor: 'rgba(59, 130, 246, 0.18)',
              border: '1px solid rgba(59, 130, 246, 0.45)',
              color: '#60A5FA',
              fontSize: '9.5px',
              fontWeight: 800,
              letterSpacing: '0.08em',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <Radio size={12} color="#60A5FA" />
            BHUVAN / NRSC GEOSPATIAL GIS (OGC WMS)
          </span>

          <span
            style={{
              padding: '2px 8px',
              borderRadius: '3px',
              backgroundColor: isBackendOnline ? 'rgba(16, 185, 129, 0.16)' : 'rgba(239, 68, 68, 0.16)',
              border: `1px solid ${isBackendOnline ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
              color: isBackendOnline ? '#34D399' : '#F87171',
              fontSize: '9.5px',
              fontWeight: 800,
              letterSpacing: '0.08em',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: isBackendOnline ? '#10B981' : '#EF4444',
              }}
            />
            {isBackendOnline ? 'ACTIVE PROTOTYPE SECTOR ONLINE' : 'BACKEND OFFLINE'}
          </span>
        </div>

        <div style={{ fontSize: '9.5px', color: 'var(--color-text-muted)', letterSpacing: '0.04em' }}>
          NATIONAL BORDER CONTEXT (STATIC GIS) · ACTIVE SECTOR B-07 (LIVE AI TELEMETRY)
        </div>
      </div>

      {/* 2. Top-Right Source Switcher & Quick Navigation */}
      <div
        style={{
          position: 'absolute',
          top: 48,
          right: 14,
          zIndex: 25,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        {/* Focus Sector B-07 Button */}
        <button
          onClick={handleFocusPrototypeSector}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '5px 10px',
            backgroundColor: 'rgba(16, 185, 129, 0.2)',
            border: '1px solid rgba(16, 185, 129, 0.45)',
            borderRadius: '4px',
            color: '#34D399',
            fontSize: '9.5px',
            fontWeight: 800,
            cursor: 'pointer',
            backdropFilter: 'blur(8px)',
          }}
        >
          <Crosshair size={12} /> Focus Sector B-07
        </button>

        {/* Satellite Basemap Switcher */}
        <div
          style={{
            display: 'flex',
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid var(--color-border)',
            borderRadius: '4px',
            padding: '2px',
            backdropFilter: 'blur(8px)',
          }}
        >
          <button
            onClick={() => handleChangeSatelliteSource('BHUVAN_WMS')}
            title="Live Bhuvan/NRSC WMS Satellite"
            style={{
              padding: '4px 8px',
              background: satelliteSource === 'BHUVAN_WMS' ? '#2563EB' : 'transparent',
              color: satelliteSource === 'BHUVAN_WMS' ? '#fff' : 'var(--color-text-secondary)',
              border: 'none',
              borderRadius: '3px',
              fontSize: '9.5px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Radio size={10} /> Bhuvan WMS
          </button>

          <button
            onClick={() => handleChangeSatelliteSource('LOCAL_OFFLINE_SATELLITE')}
            title="Local Offline Satellite Raster Fallback"
            style={{
              padding: '4px 8px',
              background: satelliteSource === 'LOCAL_OFFLINE_SATELLITE' ? '#2563EB' : 'transparent',
              color: satelliteSource === 'LOCAL_OFFLINE_SATELLITE' ? '#fff' : 'var(--color-text-secondary)',
              border: 'none',
              borderRadius: '3px',
              fontSize: '9.5px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Shield size={10} /> Local Satellite
          </button>
        </div>

        {/* Zoom Controls */}
        <div
          style={{
            display: 'flex',
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid var(--color-border)',
            borderRadius: '4px',
            backdropFilter: 'blur(8px)',
          }}
        >
          <button
            onClick={() => mapInstanceRef.current?.zoomIn()}
            title="Zoom In"
            style={{
              padding: '6px 8px',
              background: 'none',
              border: 'none',
              color: 'var(--color-text-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <ZoomIn size={14} />
          </button>
          <div style={{ width: 1, backgroundColor: 'var(--color-border-subtle)' }} />
          <button
            onClick={() => mapInstanceRef.current?.zoomOut()}
            title="Zoom Out"
            style={{
              padding: '6px 8px',
              background: 'none',
              border: 'none',
              color: 'var(--color-text-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <ZoomOut size={14} />
          </button>
          <div style={{ width: 1, backgroundColor: 'var(--color-border-subtle)' }} />
          <button
            onClick={handleResetNationalView}
            title="National Overview"
            style={{
              padding: '6px 8px',
              background: 'none',
              border: 'none',
              color: 'var(--color-text-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* 3. Main MapLibre GL Canvas Container */}
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* 4. Bottom HUD: Real-time Coordinates, Scale, Zoom, Compass */}
      <div
        style={{
          position: 'absolute',
          bottom: 12,
          left: 14,
          zIndex: 20,
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid var(--color-border)',
          borderRadius: '4px',
          padding: '5px 10px',
          backdropFilter: 'blur(8px)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
            CURSOR COORDINATES
          </span>
          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#38BDF8' }}>
            {cursorCoords.lat}° N, {cursorCoords.lng}° E
          </span>
        </div>

        <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
            ZOOM LEVEL
          </span>
          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#E2E8F0' }}>
            {zoomLevel}x
          </span>
        </div>

        <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Compass size={14} color="#38BDF8" />
          <span style={{ fontSize: '9px', fontWeight: 800, color: '#E2E8F0' }}>NORTH</span>
        </div>

        {selectedSectorId && (
          <>
            <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
                SECTOR INSPECTION
              </span>
              <span style={{ fontSize: '10px', fontWeight: 800, color: selectedSectorId === 'SECTOR-B07' ? '#10B981' : '#CBD5E1' }}>
                {selectedSectorId}
              </span>
            </div>
          </>
        )}

        {environment && (
          <>
            <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
                ATMOSPHERE
              </span>
              <span style={{ fontSize: '10px', fontWeight: 700, color: '#38BDF8' }}>
                {environment.visibility} ({environment.lighting})
              </span>
            </div>
          </>
        )}

        {streamHealth && (
          <>
            <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
                SENSOR INGEST
              </span>
              <span style={{ fontSize: '10px', fontWeight: 700, color: streamHealth.state === 'HEALTHY' ? '#10B981' : '#F59E0B' }}>
                {streamHealth.processing_fps?.toFixed(1) || '0.0'} FPS ({streamHealth.state})
              </span>
            </div>
          </>
        )}

        {!isWmsOnline && satelliteSource === 'BHUVAN_WMS' && (
          <>
            <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#F59E0B', fontSize: '9px', fontWeight: 700 }}>
              <AlertTriangle size={13} />
              <span>Remote WMS Unreachable (CORS/Network). Switch to Local Satellite.</span>
            </div>
          </>
        )}
      </div>

      {/* 5. Bottom-Right Layer Visibility Toggles */}
      <div
        style={{
          position: 'absolute',
          bottom: 12,
          right: 14,
          zIndex: 20,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid var(--color-border)',
          borderRadius: '4px',
          padding: '4px 10px',
          backdropFilter: 'blur(8px)',
          fontSize: '9.5px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-text-muted)' }}>
          <Layers size={13} color="#38BDF8" />
          <span style={{ fontWeight: 700 }}>LAYERS:</span>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.satellite ? '#E2E8F0' : '#6B7280' }}>
          <input
            type="checkbox"
            checked={layers.satellite}
            onChange={() => toggleLayer('satellite')}
            style={{ accentColor: '#2563EB', cursor: 'pointer' }}
          />
          Satellite
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.nationalBoundary ? '#E2E8F0' : '#6B7280' }}>
          <input
            type="checkbox"
            checked={layers.nationalBoundary}
            onChange={() => toggleLayer('nationalBoundary')}
            style={{ accentColor: '#60A5FA', cursor: 'pointer' }}
          />
          Boundary
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.borderContext ? '#E2E8F0' : '#6B7280' }}>
          <input
            type="checkbox"
            checked={layers.borderContext}
            onChange={() => toggleLayer('borderContext')}
            style={{ accentColor: '#EF4444', cursor: 'pointer' }}
          />
          Frontiers
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.prototypeSector ? '#10B981' : '#6B7280' }}>
          <input
            type="checkbox"
            checked={layers.prototypeSector}
            onChange={() => toggleLayer('prototypeSector')}
            style={{ accentColor: '#10B981', cursor: 'pointer' }}
          />
          Sector B-07
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.activeTracks ? '#38BDF8' : '#6B7280' }}>
          <input
            type="checkbox"
            checked={layers.activeTracks}
            onChange={() => toggleLayer('activeTracks')}
            style={{ accentColor: '#38BDF8', cursor: 'pointer' }}
          />
          Tracks
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.securityEvents ? '#EF4444' : '#6B7280' }}>
          <input
            type="checkbox"
            checked={layers.securityEvents}
            onChange={() => toggleLayer('securityEvents')}
            style={{ accentColor: '#EF4444', cursor: 'pointer' }}
          />
          Events
        </label>
      </div>
    </div>
  );
};
