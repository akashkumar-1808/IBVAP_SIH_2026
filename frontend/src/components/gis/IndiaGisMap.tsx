import React, { useState, useRef, useMemo } from 'react';
import {
  Compass,
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react';
import {
  INDIA_OUTLINE_PATH,
  FRONTIER_BORDER_PATHS,
  NEIGHBOR_CONTEXT,
  NATIONAL_SECTOR_REGISTRY,
  SectorMarker,
  unprojectSvgToGeo,
} from './indiaBorderData';
import { EventRecord, TrackState, StreamHealthContract } from '../../types';

export type BasemapMode = 'DARK_GIS' | 'SATELLITE' | 'TERRAIN';

export interface GisLayerVisibility {
  nationalBoundary: boolean;
  borderLines: boolean;
  prototypeSector: boolean;
  surveillanceContext: boolean;
  activeEvents: boolean;
  activeTracks: boolean;
  environment: boolean;
  streamHealth: boolean;
}

interface IndiaGisMapProps {
  mode?: 'overview' | 'tactical';
  selectedSectorId?: string;
  onSelectSector?: (sector: SectorMarker) => void;
  activeEvents?: EventRecord[];
  activeTracks?: TrackState[];
  streamHealth?: StreamHealthContract;
  isBackendOnline?: boolean;
  height?: string | number;
  layers?: GisLayerVisibility;
  onToggleLayer?: (layerKey: keyof GisLayerVisibility) => void;
  basemap?: BasemapMode;
  onChangeBasemap?: (basemap: BasemapMode) => void;
}

export const IndiaGisMap: React.FC<IndiaGisMapProps> = ({
  mode = 'overview',
  selectedSectorId = 'SECTOR-B07',
  onSelectSector,
  activeEvents = [],
  activeTracks = [],
  streamHealth,
  isBackendOnline = true,
  height = '100%',
  layers: externalLayers,
  onToggleLayer: externalToggleLayer,
  basemap: externalBasemap,
  onChangeBasemap: externalChangeBasemap,
}) => {
  // Local state for zoom & pan in tactical/overview mode
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [cursorGeo, setCursorGeo] = useState<{ lat: number; lng: number }>({ lat: 28.61, lng: 77.20 });
  const [hoveredSector, setHoveredSector] = useState<SectorMarker | null>(null);

  // Internal basemap & layers if not controlled externally
  const [internalBasemap, setInternalBasemap] = useState<BasemapMode>('DARK_GIS');
  const [internalLayers, setInternalLayers] = useState<GisLayerVisibility>({
    nationalBoundary: true,
    borderLines: true,
    prototypeSector: true,
    surveillanceContext: true,
    activeEvents: true,
    activeTracks: true,
    environment: true,
    streamHealth: true,
  });

  const basemap = externalBasemap || internalBasemap;
  const setBasemap = externalChangeBasemap || setInternalBasemap;

  const layers = externalLayers || internalLayers;
  const toggleLayer = (key: keyof GisLayerVisibility) => {
    if (externalToggleLayer) {
      externalToggleLayer(key);
    } else {
      setInternalLayers((prev) => ({ ...prev, [key]: !prev[key] }));
    }
  };

  const svgRef = useRef<SVGSVGElement | null>(null);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.35, 3.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.35, 0.8));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }

    if (svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      // Convert to SVG 1000x1000 space
      const svgX = (clientX / rect.width) * 1000;
      const svgY = (clientY / rect.height) * 1000;
      const [lng, lat] = unprojectSvgToGeo(svgX, svgY, 1000, 1000);
      if (lat >= 6 && lat <= 38 && lng >= 66 && lng <= 99) {
        setCursorGeo({ lat, lng });
      }
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  // Derive highest priority active event for Sector B-07
  const highestEvent = useMemo(() => {
    if (!activeEvents || activeEvents.length === 0) return null;
    return (
      activeEvents.find((e) => e.priority === 'CRITICAL') ||
      activeEvents.find((e) => e.priority === 'HIGH') ||
      activeEvents.find((e) => e.priority === 'MEDIUM') ||
      activeEvents[0]
    );
  }, [activeEvents]);

  // Basemap background color and styling
  const basemapBg =
    basemap === 'SATELLITE'
      ? 'radial-gradient(ellipse at 50% 40%, #0d1a24 0%, #060b11 75%, #03060a 100%)'
      : basemap === 'TERRAIN'
      ? 'radial-gradient(ellipse at 50% 40%, #131a15 0%, #09100c 75%, #040806 100%)'
      : 'radial-gradient(ellipse at 50% 40%, #0a111a 0%, #06090f 75%, #030508 100%)';

  const landFill =
    basemap === 'SATELLITE'
      ? '#101c27'
      : basemap === 'TERRAIN'
      ? '#152119'
      : '#0e1622';

  const isTactical = mode === 'tactical';

  return (
    <div
      className={`gis-map-container ${isTactical ? 'tactical-mode' : 'overview-mode'}`}
      style={{
        position: 'relative',
        width: '100%',
        height: height,
        minHeight: isTactical ? '620px' : '420px',
        backgroundColor: '#05080d',
        backgroundImage: basemapBg,
        borderRadius: '6px',
        border: '1px solid var(--color-border)',
        overflow: 'hidden',
        userSelect: 'none',
      }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* 1. Header Banner with Classification & Scope */}
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
              backgroundColor: 'rgba(59, 130, 246, 0.16)',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              color: '#60A5FA',
              fontSize: '9.5px',
              fontWeight: 800,
              letterSpacing: '0.08em',
            }}
          >
            NATIONAL BORDER CONTEXT (STATIC GIS)
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

        <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', letterSpacing: '0.04em' }}>
          IBVAP TATVA TACTICAL GEOGRAPHIC INFORMATION SYSTEM · DATUM: WGS-84 (VECTOR PROJECTION)
        </div>
      </div>

      {/* 2. Tactical Controls (Zoom, Pan, Basemap) */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          right: 14,
          zIndex: 25,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        {isTactical && (
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
              onClick={() => setBasemap('DARK_GIS')}
              style={{
                padding: '4px 10px',
                background: basemap === 'DARK_GIS' ? '#2563EB' : 'transparent',
                color: basemap === 'DARK_GIS' ? '#fff' : 'var(--color-text-secondary)',
                border: 'none',
                borderRadius: '3px',
                fontSize: '10px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Dark GIS
            </button>
            <button
              onClick={() => setBasemap('SATELLITE')}
              style={{
                padding: '4px 10px',
                background: basemap === 'SATELLITE' ? '#2563EB' : 'transparent',
                color: basemap === 'SATELLITE' ? '#fff' : 'var(--color-text-secondary)',
                border: 'none',
                borderRadius: '3px',
                fontSize: '10px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Satellite
            </button>
            <button
              onClick={() => setBasemap('TERRAIN')}
              style={{
                padding: '4px 10px',
                background: basemap === 'TERRAIN' ? '#2563EB' : 'transparent',
                color: basemap === 'TERRAIN' ? '#fff' : 'var(--color-text-secondary)',
                border: 'none',
                borderRadius: '3px',
                fontSize: '10px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Terrain
            </button>
          </div>
        )}

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
            onClick={handleZoomIn}
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
            onClick={handleZoomOut}
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
            onClick={handleReset}
            title="Reset View"
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

      {/* 3. Main SVG Map Canvas */}
      <svg
        ref={svgRef}
        viewBox="0 0 1000 1000"
        style={{
          width: '100%',
          height: '100%',
          cursor: isDragging ? 'grabbing' : 'grab',
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: '50% 50%',
          transition: isDragging ? 'none' : 'transform 0.15s ease-out',
        }}
        onMouseDown={handleMouseDown}
      >
        <defs>
          {/* Tactical Grid Pattern */}
          <pattern id="gisGrid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="0.5" />
            <circle cx="50" cy="50" r="0.8" fill="rgba(255, 255, 255, 0.1)" />
          </pattern>

          {/* Graticule Pattern for Lat/Lng (100px = ~3.5 deg) */}
          <pattern id="graticuleGrid" width="100" height="100" patternUnits="userSpaceOnUse">
            <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(75, 85, 99, 0.18)" strokeDasharray="2,4" strokeWidth="0.5" />
          </pattern>

          {/* Terrain Contour Texture */}
          <pattern id="contourPattern" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 0 20 Q 20 0 40 20 T 80 20" fill="none" stroke="rgba(16, 185, 129, 0.04)" strokeWidth="0.75" />
          </pattern>

          {/* Glowing Radial Beacon for Active Prototype Sector */}
          <radialGradient id="beaconGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#10B981" stopOpacity="0.8" />
            <stop offset="40%" stopColor="#06B6D4" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#06B6D4" stopOpacity="0" />
          </radialGradient>

          {/* Subtle drop shadow for labels */}
          <filter id="textGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="1" stdDeviation="1" floodColor="#000" floodOpacity="0.9" />
          </filter>
        </defs>

        {/* Tactical Grid Background */}
        <rect width="1000" height="1000" fill="url(#gisGrid)" />
        <rect width="1000" height="1000" fill="url(#graticuleGrid)" />

        {/* Surrounding Maritime Water Body Labels */}
        {NEIGHBOR_CONTEXT.map((neighbor, idx) => (
          <text
            key={idx}
            x={neighbor.x}
            y={neighbor.y}
            fill="rgba(156, 163, 175, 0.28)"
            fontSize="11"
            fontWeight="700"
            letterSpacing="0.16em"
            textAnchor="middle"
            filter="url(#textGlow)"
          >
            {neighbor.name}
          </text>
        ))}

        {/* National Boundary Polygon (Mainland India) */}
        {layers.nationalBoundary && (
          <g>
            {/* Outer Subtle Halo */}
            <path
              d={INDIA_OUTLINE_PATH}
              fill={landFill}
              stroke="rgba(59, 130, 246, 0.25)"
              strokeWidth="5"
              strokeLinejoin="round"
            />
            {/* Main Crisp Land Border */}
            <path
              d={INDIA_OUTLINE_PATH}
              fill={landFill}
              stroke="rgba(96, 165, 250, 0.65)"
              strokeWidth="1.75"
              strokeLinejoin="round"
            />

            {/* If Terrain basemap selected, overlay subtle topographic contour paths */}
            {basemap === 'TERRAIN' && (
              <path d={INDIA_OUTLINE_PATH} fill="url(#contourPattern)" opacity="0.6" />
            )}
          </g>
        )}

        {/* Frontier Restricted Border Segments */}
        {layers.borderLines &&
          FRONTIER_BORDER_PATHS.map((frontier) => (
            <g key={frontier.id}>
              <path
                d={frontier.path}
                fill="none"
                stroke={frontier.color}
                strokeWidth="2.5"
                strokeDasharray="5,3"
                strokeLinecap="round"
              />
              <path
                d={frontier.path}
                fill="none"
                stroke={frontier.color}
                strokeWidth="7"
                strokeOpacity="0.15"
                strokeLinecap="round"
              />
            </g>
          ))}

        {/* National Context Sector Markers (Restrained / Non-Active) */}
        {layers.surveillanceContext &&
          NATIONAL_SECTOR_REGISTRY.filter((s) => !s.isActivePrototype).map((sec) => {
            const isSelected = sec.id === selectedSectorId;
            return (
              <g
                key={sec.id}
                onClick={() => onSelectSector && onSelectSector(sec)}
                onMouseEnter={() => setHoveredSector(sec)}
                onMouseLeave={() => setHoveredSector(null)}
                style={{ cursor: 'pointer' }}
              >
                <circle cx={sec.x} cy={sec.y} r={isSelected ? 5 : 3} fill={isSelected ? '#38BDF8' : '#6B7280'} opacity="0.85" />
                <circle cx={sec.x} cy={sec.y} r={isSelected ? 11 : 8} fill="none" stroke={isSelected ? '#38BDF8' : '#6B7280'} strokeWidth={isSelected ? 1.2 : 0.75} opacity={isSelected ? 0.8 : 0.4} />
                <text
                  x={sec.x + 10}
                  y={sec.y + 3}
                  fill={isSelected ? '#38BDF8' : '#9CA3AF'}
                  fontSize="8.5"
                  fontWeight="600"
                  filter="url(#textGlow)"
                >
                  {sec.id}
                </text>
              </g>
            );
          })}

        {/* ====================================================================
            ACTIVE PROTOTYPE SECTOR (SECTOR B-07 - Real AI Intelligence Anchor)
            ==================================================================== */}
        {layers.prototypeSector && (
          <g
            onClick={() => {
              const b07 = NATIONAL_SECTOR_REGISTRY.find((s) => s.id === 'SECTOR-B07');
              if (b07 && onSelectSector) onSelectSector(b07);
            }}
            onMouseEnter={() => {
              const b07 = NATIONAL_SECTOR_REGISTRY.find((s) => s.id === 'SECTOR-B07');
              if (b07) setHoveredSector(b07);
            }}
            onMouseLeave={() => setHoveredSector(null)}
            style={{ cursor: 'pointer' }}
          >
            {/* Sector Range Arc / Sensor FOV Indicator */}
            <path
              d="M 295 125 L 265 95 A 45 45 0 0 1 325 95 Z"
              fill="rgba(6, 182, 212, 0.12)"
              stroke="#06B6D4"
              strokeWidth="1"
              strokeDasharray="3,2"
            />

            {/* Pulsing Beacon Rings */}
            <circle cx="295" cy="125" r="28" fill="url(#beaconGlow)" opacity="0.45" />
            <circle cx="295" cy="125" r="16" fill="none" stroke="#10B981" strokeWidth="1.2" opacity="0.8">
              <animate attributeName="r" values="12;24;12" dur="3s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.8;0.1;0.8" dur="3s" repeatCount="indefinite" />
            </circle>

            {/* Center Core Anchor */}
            <circle cx="295" cy="125" r="5" fill="#10B981" />
            <circle cx="295" cy="125" r="7" fill="none" stroke="#FFFFFF" strokeWidth="1" />

            {/* Callout Flag */}
            <line x1="295" y1="125" x2="350" y2="105" stroke="#10B981" strokeWidth="1.2" />
            <rect
              x="350"
              y="90"
              width="165"
              height="30"
              fill="rgba(15, 23, 42, 0.92)"
              stroke="#10B981"
              strokeWidth="1"
              rx="3"
              filter="url(#textGlow)"
            />
            <text x="358" y="103" fill="#10B981" fontSize="8.5" fontWeight="800">
              ACTIVE PROTOTYPE SECTOR
            </text>
            <text x="358" y="115" fill="#E2E8F0" fontSize="7.5" fontWeight="600">
              SECTOR B-07 · 1 CAM · {streamHealth?.state || 'ONLINE'}
            </text>

            {/* Active Security Threat Tag on Prototype Sector if High/Critical event occurs */}
            {highestEvent && layers.activeEvents && (
              <g>
                <circle
                  cx="295"
                  cy="125"
                  r="34"
                  fill="none"
                  stroke={highestEvent.priority === 'CRITICAL' ? '#EF4444' : '#F59E0B'}
                  strokeWidth="2"
                  strokeDasharray="4,2"
                >
                  <animate attributeName="transform" type="rotate" from="0 295 125" to="360 295 125" dur="8s" repeatCount="indefinite" />
                </circle>
                <rect
                  x="220"
                  y="140"
                  width="150"
                  height="22"
                  fill="rgba(239, 68, 68, 0.9)"
                  rx="3"
                  filter="url(#textGlow)"
                />
                <text x="295" y="154" fill="#FFFFFF" fontSize="8" fontWeight="800" textAnchor="middle">
                  ⚠ {highestEvent.priority}: {highestEvent.event_type.replace(/_/g, ' ')}
                </text>
              </g>
            )}

            {/* Active Real Track Marker in Sector B-07 */}
            {activeTracks.length > 0 && layers.activeTracks && (
              <g>
                <circle cx="280" cy="115" r="3" fill="#38BDF8" />
                <circle cx="280" cy="115" r="6" fill="none" stroke="#38BDF8" strokeWidth="1" strokeDasharray="2,2" />
                <text x="275" y="108" fill="#38BDF8" fontSize="7.5" fontWeight="700">
                  TRACK #{activeTracks[0].track_id}
                </text>
              </g>
            )}
          </g>
        )}
      </svg>

      {/* 4. Tactical HUD Overlay (Coordinates, Scale Bar, North Indicator) */}
      <div
        style={{
          position: 'absolute',
          bottom: 12,
          left: 14,
          zIndex: 20,
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          backgroundColor: 'rgba(15, 23, 42, 0.88)',
          border: '1px solid var(--color-border)',
          borderRadius: '4px',
          padding: '5px 10px',
          backdropFilter: 'blur(8px)',
        }}
      >
        {/* Cursor Lat/Lng */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
            CURSOR COORDINATES
          </span>
          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#38BDF8' }}>
            {cursorGeo.lat.toFixed(2)}° N, {cursorGeo.lng.toFixed(2)}° E
          </span>
        </div>

        <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />

        {/* Map Scale */}
        <div style={{ display: 'flex', flexDirection: 'column', width: 90 }}>
          <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
            MAP SCALE (KM)
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
            <div
              style={{
                width: '100%',
                height: '3px',
                backgroundColor: 'rgba(255,255,255,0.2)',
                position: 'relative',
                borderRadius: '1px',
              }}
            >
              <div style={{ width: '50%', height: '100%', backgroundColor: '#38BDF8' }} />
            </div>
            <span style={{ fontSize: '8px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
              500km
            </span>
          </div>
        </div>

        <div style={{ width: 1, height: 20, backgroundColor: 'var(--color-border-subtle)' }} />

        {/* North Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Compass size={14} color="#38BDF8" />
          <span style={{ fontSize: '9px', fontWeight: 800, color: '#E2E8F0' }}>N</span>
        </div>
      </div>

      {/* 5. Hover / Selection Tooltip */}
      {hoveredSector && (
        <div
          style={{
            position: 'absolute',
            bottom: 50,
            left: 14,
            zIndex: 30,
            backgroundColor: 'rgba(11, 15, 23, 0.95)',
            border: `1px solid ${hoveredSector.isActivePrototype ? '#10B981' : 'var(--color-border)'}`,
            borderRadius: '4px',
            padding: '8px 12px',
            maxWidth: '300px',
            backdropFilter: 'blur(8px)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, color: hoveredSector.isActivePrototype ? '#10B981' : '#E2E8F0' }}>
              {hoveredSector.name}
            </span>
            <span
              style={{
                fontSize: '8px',
                fontWeight: 700,
                padding: '1px 5px',
                borderRadius: '2px',
                backgroundColor: hoveredSector.isActivePrototype ? 'rgba(16, 185, 129, 0.2)' : 'rgba(107, 114, 128, 0.2)',
                color: hoveredSector.isActivePrototype ? '#34D399' : '#9CA3AF',
              }}
            >
              {hoveredSector.status.replace(/_/g, ' ')}
            </span>
          </div>
          <p style={{ fontSize: '9.5px', color: 'var(--color-text-secondary)', margin: '4px 0 0 0', lineHeight: 1.4 }}>
            {hoveredSector.description}
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '8.5px', color: 'var(--color-text-muted)' }}>
            <span>GEO: {hoveredSector.lat}°N, {hoveredSector.lng}°E</span>
            <span>SENSORS: {hoveredSector.sensorsCount}</span>
          </div>
        </div>
      )}

      {/* 6. Tactical Layer Panel (Visible when in tactical mode) */}
      {isTactical && (
        <div
          style={{
            position: 'absolute',
            bottom: 12,
            right: 14,
            zIndex: 20,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'rgba(15, 23, 42, 0.88)',
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

          <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.nationalBoundary ? '#E2E8F0' : '#6B7280' }}>
            <input
              type="checkbox"
              checked={layers.nationalBoundary}
              onChange={() => toggleLayer('nationalBoundary')}
              style={{ accentColor: '#2563EB', cursor: 'pointer' }}
            />
            Boundary
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.borderLines ? '#E2E8F0' : '#6B7280' }}>
            <input
              type="checkbox"
              checked={layers.borderLines}
              onChange={() => toggleLayer('borderLines')}
              style={{ accentColor: '#EF4444', cursor: 'pointer' }}
            />
            Borders
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.prototypeSector ? '#10B981' : '#6B7280' }}>
            <input
              type="checkbox"
              checked={layers.prototypeSector}
              onChange={() => toggleLayer('prototypeSector')}
              style={{ accentColor: '#10B981', cursor: 'pointer' }}
            />
            Prototype Sector
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '3px', cursor: 'pointer', color: layers.activeEvents ? '#F59E0B' : '#6B7280' }}>
            <input
              type="checkbox"
              checked={layers.activeEvents}
              onChange={() => toggleLayer('activeEvents')}
              style={{ accentColor: '#F59E0B', cursor: 'pointer' }}
            />
            Events
          </label>
        </div>
      )}
    </div>
  );
};
