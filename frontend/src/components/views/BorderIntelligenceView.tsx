import React, { useState } from 'react';
import {
  Eye,
  Sliders,
  Globe,
  Map as MapIcon,
} from 'lucide-react';
import { IndiaGisMap, BasemapMode, GisLayerVisibility } from '../gis/IndiaGisMap';
import { BhuvanMapLibreView } from '../gis/BhuvanMapLibreView';
import { NATIONAL_SECTOR_REGISTRY, SectorMarker } from '../gis/indiaBorderData';
import { CameraInfo, EventRecord, TrackState, StreamHealthContract, EnvironmentState } from '../../types';
import { NavTab } from '../layout/SidebarNav';

type GisEngineMode = 'BHUVAN_MAPLIBRE' | 'TACTICAL_SVG';

interface BorderIntelligenceViewProps {
  camera: CameraInfo | null;
  activeEvents: EventRecord[];
  activeTracks: TrackState[];
  streamHealth?: StreamHealthContract;
  environment?: EnvironmentState;
  isBackendOnline: boolean;
  onNavigate: (tab: NavTab) => void;
}

export const BorderIntelligenceView: React.FC<BorderIntelligenceViewProps> = ({
  camera,
  activeEvents,
  activeTracks,
  streamHealth,
  environment,
  isBackendOnline,
  onNavigate,
}) => {
  const [selectedSector, setSelectedSector] = useState<SectorMarker>(
    NATIONAL_SECTOR_REGISTRY.find((s) => s.id === 'SECTOR-B07') || NATIONAL_SECTOR_REGISTRY[0]
  );

  const [gisEngine, setGisEngine] = useState<GisEngineMode>('BHUVAN_MAPLIBRE');

  const [basemap, setBasemap] = useState<BasemapMode>('DARK_GIS');
  const [layers, setLayers] = useState<GisLayerVisibility>({
    nationalBoundary: true,
    borderLines: true,
    prototypeSector: true,
    surveillanceContext: true,
    activeEvents: true,
    activeTracks: true,
    environment: true,
    streamHealth: true,
  });

  const toggleLayer = (key: keyof GisLayerVisibility) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isPrototypeSelected = selectedSector.isActivePrototype;

  return (
    <div
      className="border-intelligence-workspace"
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 340px',
        gap: '12px',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* 1. Main Interactive Full-Screen GIS Canvas */}
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '640px' }}>
        {/* Top Floating Engine Switcher Tab */}
        <div
          style={{
            position: 'absolute',
            top: 12,
            right: 14,
            zIndex: 30,
            display: 'flex',
            alignItems: 'center',
            backgroundColor: 'rgba(15, 23, 42, 0.92)',
            border: '1px solid var(--color-border)',
            borderRadius: '4px',
            padding: '2px',
            backdropFilter: 'blur(8px)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
        >
          <button
            onClick={() => setGisEngine('BHUVAN_MAPLIBRE')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              fontSize: '10px',
              fontWeight: 800,
              letterSpacing: '0.04em',
              borderRadius: '3px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: gisEngine === 'BHUVAN_MAPLIBRE' ? '#2563EB' : 'transparent',
              color: gisEngine === 'BHUVAN_MAPLIBRE' ? '#FFFFFF' : '#94A3B8',
              transition: 'all 0.15s ease',
            }}
          >
            <Globe size={12} />
            BHUVAN / NRSC MAPLIBRE
          </button>
          <button
            onClick={() => setGisEngine('TACTICAL_SVG')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              fontSize: '10px',
              fontWeight: 800,
              letterSpacing: '0.04em',
              borderRadius: '3px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: gisEngine === 'TACTICAL_SVG' ? '#2563EB' : 'transparent',
              color: gisEngine === 'TACTICAL_SVG' ? '#FFFFFF' : '#94A3B8',
              transition: 'all 0.15s ease',
            }}
          >
            <MapIcon size={12} />
            SCHEMATIC VECTOR
          </button>
        </div>

        {gisEngine === 'BHUVAN_MAPLIBRE' ? (
          <BhuvanMapLibreView
            camera={camera}
            activeEvents={activeEvents}
            activeTracks={activeTracks}
            streamHealth={streamHealth}
            environment={environment}
            isBackendOnline={isBackendOnline}
            selectedSectorId={selectedSector.id}
            onSelectSector={(sectorId) => {
              const found = NATIONAL_SECTOR_REGISTRY.find((s) => s.id === sectorId);
              if (found) setSelectedSector(found);
            }}
            height="100%"
          />
        ) : (
          <IndiaGisMap
            mode="tactical"
            selectedSectorId={selectedSector.id}
            onSelectSector={setSelectedSector}
            activeEvents={activeEvents}
            activeTracks={activeTracks}
            streamHealth={streamHealth}
            isBackendOnline={isBackendOnline}
            layers={layers}
            onToggleLayer={toggleLayer}
            basemap={basemap}
            onChangeBasemap={setBasemap}
            height="100%"
          />
        )}
      </div>

      {/* 2. Tactical Drawer: Layer Controls, Sector Inspector, and Geographic Legend */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          height: '100%',
          overflowY: 'auto',
          paddingRight: '2px',
        }}
      >
        {/* Layer Controls Box */}
        <div
          style={{
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '6px', marginBottom: '8px' }}>
            <Sliders size={14} color="#38BDF8" />
            <span style={{ fontSize: '11px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
              TACTICAL GIS LAYERS
            </span>
          </div>

          {/* Basemap Selection */}
          <div style={{ marginBottom: '10px' }}>
            <span style={{ fontSize: '8.5px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
              BASEMAP VECTOR STYLE
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '4px', marginTop: '4px' }}>
              {(['DARK_GIS', 'SATELLITE', 'TERRAIN'] as BasemapMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setBasemap(mode)}
                  style={{
                    padding: '4px 6px',
                    borderRadius: '3px',
                    fontSize: '9px',
                    fontWeight: 700,
                    border: basemap === mode ? '1px solid #38BDF8' : '1px solid var(--color-border-subtle)',
                    backgroundColor: basemap === mode ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0,0,0,0.3)',
                    color: basemap === mode ? '#38BDF8' : 'var(--color-text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  {mode.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Layer Toggles */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '8.5px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
              INTELLIGENCE OVERLAYS
            </span>

            {[
              { key: 'nationalBoundary', label: 'National Boundary' },
              { key: 'borderLines', label: 'Restricted Frontiers & Borders' },
              { key: 'prototypeSector', label: 'Prototype Sector (B-07)' },
              { key: 'surveillanceContext', label: 'Contextual Sector Markers' },
              { key: 'activeEvents', label: 'Active Security Threat Markers' },
              { key: 'activeTracks', label: 'Active Target Tracks' },
              { key: 'environment', label: 'Atmospheric State' },
              { key: 'streamHealth', label: 'Stream Health Beacon' },
            ].map(({ key, label }) => (
              <label
                key={key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '10px',
                  color: layers[key as keyof GisLayerVisibility] ? '#E2E8F0' : 'var(--color-text-muted)',
                  cursor: 'pointer',
                }}
              >
                <span>{label}</span>
                <input
                  type="checkbox"
                  checked={layers[key as keyof GisLayerVisibility]}
                  onChange={() => toggleLayer(key as keyof GisLayerVisibility)}
                  style={{ accentColor: '#2563EB', cursor: 'pointer' }}
                />
              </label>
            ))}
          </div>
        </div>

        {/* Selected Sector Inspector Box */}
        <div
          style={{
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            border: `1px solid ${isPrototypeSelected ? 'rgba(16, 185, 129, 0.4)' : 'var(--color-border)'}`,
            borderRadius: '6px',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '6px' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, color: isPrototypeSelected ? '#10B981' : '#F1F5F9' }}>
              {selectedSector.name}
            </span>
            <span
              style={{
                fontSize: '8px',
                fontWeight: 800,
                padding: '1px 6px',
                borderRadius: '2px',
                backgroundColor: isPrototypeSelected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(107, 114, 128, 0.2)',
                color: isPrototypeSelected ? '#34D399' : '#9CA3AF',
              }}
            >
              {selectedSector.status.replace(/_/g, ' ')}
            </span>
          </div>

          <div style={{ fontSize: '9.5px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
            {selectedSector.description}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', backgroundColor: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '4px' }}>
            <div>
              <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>COORDINATES</span>
              <div style={{ fontSize: '9.5px', fontFamily: 'var(--font-mono)', color: '#38BDF8' }}>
                {selectedSector.lat}° N, {selectedSector.lng}° E
              </div>
            </div>

            <div>
              <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>ACTIVE SENSORS</span>
              <div style={{ fontSize: '9.5px', fontWeight: 800, color: isPrototypeSelected ? '#10B981' : 'var(--color-text-muted)' }}>
                {isPrototypeSelected ? '1 CAMERA CONNECTED' : 'NO SENSORS'}
              </div>
            </div>
          </div>

          {isPrototypeSelected ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '4px' }}>
              <div style={{ fontSize: '8.5px', fontWeight: 800, color: '#38BDF8', letterSpacing: '0.06em' }}>
                PROTOTYPE GEOFENCE CALIBRATION
              </div>
              <div style={{ fontSize: '8.5px', color: 'var(--color-text-secondary)', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <div>• Sensor: <strong style={{ color: '#E2E8F0' }}>{camera?.camera_id || 'DEMO-CAM-01'} ({environment?.visibility || 'GOOD'})</strong></div>
                <div>• Section: <strong style={{ color: '#E2E8F0' }}>SEC-ALPHA</strong> (Virtual Zero Line)</div>
                <div>• Restricted Depth: <strong style={{ color: '#EF4444' }}>0m – 30m (Full Ingress Zone)</strong></div>
                <div>• Warning Buffer: <strong style={{ color: '#F59E0B' }}>15m Spatial Buffer</strong></div>
                <div>• Monitored Ingress: <strong style={{ color: '#34D399' }}>Standard Surveillance Zone</strong></div>
              </div>

              <button
                onClick={() => onNavigate('LIVE_SURVEILLANCE')}
                style={{
                  marginTop: '6px',
                  padding: '6px 10px',
                  backgroundColor: '#2563EB',
                  border: 'none',
                  borderRadius: '3px',
                  color: '#FFFFFF',
                  fontSize: '9.5px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '4px',
                }}
              >
                <Eye size={12} /> Switch to Live Surveillance
              </button>
            </div>
          ) : (
            <div
              style={{
                padding: '8px',
                borderRadius: '3px',
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                color: '#F59E0B',
                fontSize: '8.5px',
                lineHeight: 1.35,
              }}
            >
              ⚠ <strong>DATA HONESTY COMPLIANCE:</strong> This sector is displayed purely as static geographic context. Live inference and hardware sensors are active only in Sector B-07.
            </div>
          )}
        </div>

        {/* Tactical Legend Box */}
        <div
          style={{
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            padding: '12px',
          }}
        >
          <span style={{ fontSize: '10px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
            TACTICAL GIS LEGEND
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '9px', color: 'var(--color-text-secondary)' }}>
              <span style={{ width: 12, height: 3, backgroundColor: '#EF4444', borderRadius: 1 }} />
              <span>Restricted Line of Control / Frontier</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '9px', color: 'var(--color-text-secondary)' }}>
              <span style={{ width: 12, height: 3, backgroundColor: '#F59E0B', borderRadius: 1 }} />
              <span>Western International Frontier</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '9px', color: 'var(--color-text-secondary)' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#10B981' }} />
              <span>Active Prototype Operational Sector</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '9px', color: 'var(--color-text-secondary)' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#6B7280' }} />
              <span>Contextual Boundary Reference</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
