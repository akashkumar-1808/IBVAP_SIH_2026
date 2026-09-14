import React from 'react';
import {
  ShieldAlert,
  Radio,
  Eye,
  Activity,
  ArrowRight,
  Sun,
  Moon,
} from 'lucide-react';
import { IndiaGisMap } from '../gis/IndiaGisMap';
import { SectorMarker } from '../gis/indiaBorderData';
import {
  CameraInfo,
  EventRecord,
  EvidencePackage,
  TelemetryPacket,
} from '../../types';
import { NavTab } from '../layout/SidebarNav';

interface OverviewViewProps {
  telemetry: TelemetryPacket;
  events: EventRecord[];
  evidencePackage: EvidencePackage | null;
  camera: CameraInfo | null;
  isBackendOnline: boolean;
  onNavigate: (tab: NavTab) => void;
  onSelectEvent: (ev: EventRecord) => void;
  onInspectEvidence: (ev?: EventRecord | null) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  telemetry,
  events,
  evidencePackage,
  camera,
  isBackendOnline,
  onNavigate,
  onSelectEvent,
  onInspectEvidence,
}) => {
  const activeEvents = telemetry.active_events || [];
  const activeTracks = telemetry.tracks || [];
  const streamHealth = telemetry.stream_health;
  const env = telemetry.environment;

  // Real metric computations
  const criticalCount = events.filter((e) => e.priority === 'CRITICAL').length;
  const highCount = events.filter((e) => e.priority === 'HIGH').length;
  const highestEvent = activeEvents[0] || events.find((e) => e.priority === 'CRITICAL' || e.priority === 'HIGH') || events[0] || null;

  const isDay = env?.lighting ? env.lighting.toString().toUpperCase().includes('DAY') : true;

  // Funnel observations from real session telemetry
  const tracksCount = activeTracks.length;
  const behaviorsCount = telemetry.behavior_primitives ? telemetry.behavior_primitives.length : 0;
  const activeEventsCount = activeEvents.length;
  const totalEvidenceCount = evidencePackage ? 1 : (events.length > 0 ? events.length : 0);

  return (
    <div className="overview-view-container" style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%', height: '100%', overflowY: 'auto', paddingRight: '4px' }}>
      {/* 1. Header Mission & Status Ribbon */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid var(--color-border)',
          borderRadius: '6px',
          padding: '10px 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(56, 189, 248, 0.12)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
            }}
          >
            <Radio size={20} color="#38BDF8" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '14px', fontWeight: 800, letterSpacing: '0.06em', color: '#F1F5F9', margin: 0 }}>
                NATIONAL BORDER INTELLIGENCE OVERVIEW
              </h2>
              <span
                style={{
                  fontSize: '8.5px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '3px',
                  backgroundColor: 'rgba(59, 130, 246, 0.15)',
                  color: '#60A5FA',
                  border: '1px solid rgba(59, 130, 246, 0.35)',
                }}
              >
                PROTOTYPE OPERATIONS
              </span>
            </div>
            <p style={{ fontSize: '10.5px', color: 'var(--color-text-secondary)', margin: '2px 0 0 0' }}>
              Subcontinental GIS Context · Active Automated Surveillance in Northern Frontier (Sector B-07)
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => onNavigate('LIVE_SURVEILLANCE')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#2563EB',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              padding: '7px 14px',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <Eye size={14} /> Open Live Feed <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* 2. Main Centerpiece: Full-India GIS Map + Right Intelligence Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.45fr 1fr', gap: '14px', minHeight: '520px' }}>
        {/* Left: Tactical Full-India GIS Map */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: '520px' }}>
          <IndiaGisMap
            mode="overview"
            selectedSectorId="SECTOR-B07"
            onSelectSector={(sec: SectorMarker) => {
              if (sec.isActivePrototype) {
                onNavigate('LIVE_SURVEILLANCE');
              }
            }}
            activeEvents={activeEvents}
            activeTracks={activeTracks}
            streamHealth={streamHealth}
            isBackendOnline={isBackendOnline}
            height="100%"
          />
        </div>

        {/* Right: Active Prototype Sector Intelligence Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Active Sector Summary Box */}
          <div
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Radio size={14} color="#10B981" />
                <span style={{ fontSize: '11px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
                  ACTIVE PROTOTYPE SECTOR: SECTOR B-07
                </span>
              </div>
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '3px',
                  backgroundColor: isBackendOnline ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: isBackendOnline ? '#34D399' : '#F87171',
                  border: `1px solid ${isBackendOnline ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
                }}
              >
                {isBackendOnline ? 'LIVE INFERENCE ACTIVE' : 'BACKEND UNAVAILABLE'}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
              <div style={{ backgroundColor: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '4px' }}>
                <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>CAMERA SENSOR</span>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
                  {camera?.camera_id || 'DEMO-CAM-01'}
                </div>
                <span style={{ fontSize: '8px', color: 'var(--color-text-secondary)' }}>
                  {camera?.resolution || '1280x720'}
                </span>
              </div>

              <div style={{ backgroundColor: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '4px' }}>
                <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>PROC FPS</span>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#10B981', marginTop: '2px' }}>
                  {streamHealth?.processing_fps ? streamHealth.processing_fps.toFixed(1) : (telemetry.fps > 0 ? telemetry.fps.toFixed(1) : '0.0')} FPS
                </div>
                <span style={{ fontSize: '8px', color: 'var(--color-text-secondary)' }}>
                  LATENCY: {streamHealth?.latency_ms ? Math.round(streamHealth.latency_ms) : '--'}ms
                </span>
              </div>

              <div style={{ backgroundColor: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '4px' }}>
                <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>AI PIPELINE</span>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#F59E0B', marginTop: '2px' }}>
                  YOLO + BYTETRACK
                </div>
                <span style={{ fontSize: '8px', color: 'var(--color-text-secondary)' }}>
                  FUSION ENGINE
                </span>
              </div>
            </div>

            <div style={{ fontSize: '9px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
              Sector B-07 is the authorized active prototype evaluation sector. Calibrated virtual geofence (Restricted Zone, 15m Warning Buffer, Monitored Zone) is active on this feed.
            </div>
          </div>

          {/* Active Security Threat Summary */}
          <div
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.85)',
              border: `1px solid ${highestEvent && (highestEvent.priority === 'CRITICAL' || highestEvent.priority === 'HIGH') ? 'rgba(239, 68, 68, 0.5)' : 'var(--color-border)'}`,
              borderRadius: '6px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldAlert size={14} color={criticalCount > 0 ? '#EF4444' : '#38BDF8'} />
                <span style={{ fontSize: '11px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
                  ACTIVE THREAT STATUS
                </span>
              </div>
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '3px',
                  backgroundColor: criticalCount > 0 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                  color: criticalCount > 0 ? '#F87171' : '#34D399',
                }}
              >
                {criticalCount > 0 ? `${criticalCount} CRITICAL ALERT` : (highCount > 0 ? `${highCount} HIGH THREAT` : 'NORMAL MONITORING')}
              </span>
            </div>

            {highestEvent ? (
              <div
                style={{
                  backgroundColor: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: '4px',
                  padding: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '11px', fontWeight: 800, color: '#EF4444' }}>
                    {highestEvent.event_type.replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: '9px', fontFamily: 'var(--font-mono)', color: '#38BDF8' }}>
                    RISK SCORE: {highestEvent.risk_score?.toFixed(1) || '--'}/100
                  </span>
                </div>
                <div style={{ fontSize: '9.5px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                  {highestEvent.explanation_summary || 'Autonomous risk escalation raised based on persistent track spatial breach.'}
                </div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                  <button
                    onClick={() => {
                      onSelectEvent(highestEvent);
                      onNavigate('INCIDENTS');
                    }}
                    style={{
                      padding: '4px 8px',
                      backgroundColor: 'rgba(59, 130, 246, 0.2)',
                      border: '1px solid rgba(59, 130, 246, 0.4)',
                      borderRadius: '3px',
                      color: '#60A5FA',
                      fontSize: '9px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    View Forensic Event →
                  </button>
                  <button
                    onClick={() => onInspectEvidence(highestEvent)}
                    style={{
                      padding: '4px 8px',
                      backgroundColor: 'rgba(16, 185, 129, 0.2)',
                      border: '1px solid rgba(16, 185, 129, 0.4)',
                      borderRadius: '3px',
                      color: '#34D399',
                      fontSize: '9px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    Inspect Sealed Evidence →
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '10.5px' }}>
                No active security threats in Sector B-07. System standing by for real-time target ingress.
              </div>
            )}
          </div>

          {/* Operational Environment & Stream Quick Metrics */}
          <div
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              padding: '12px 14px',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {isDay ? <Sun size={18} color="#F59E0B" /> : <Moon size={18} color="#38BDF8" />}
              <div>
                <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>ENVIRONMENT</span>
                <div style={{ fontSize: '10px', fontWeight: 800, color: '#F1F5F9' }}>
                  {env?.lighting ? env.lighting.toString().toUpperCase() : 'MONITORING'}
                </div>
                <span style={{ fontSize: '8px', color: 'var(--color-text-secondary)' }}>
                  VISIBILITY: {env?.visibility || 'GOOD'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} color="#10B981" />
              <div>
                <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>STREAM TRUST</span>
                <div style={{ fontSize: '10px', fontWeight: 800, color: '#10B981' }}>
                  {streamHealth ? `${Math.round(streamHealth.trust_score * 100)}% TRUST` : '100% NOMINAL'}
                </div>
                <span style={{ fontSize: '8px', color: 'var(--color-text-secondary)' }}>
                  {streamHealth?.state || 'HEALTHY'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Core Architecture Principle: Intelligence Funnel ("Detection != Threat") */}
      <div
        style={{
          backgroundColor: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid var(--color-border)',
          borderRadius: '6px',
          padding: '14px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '11px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
              INTELLIGENCE FUNNEL · MULTI-STAGE FILTERING PIPELINE
            </span>
            <p style={{ fontSize: '9px', color: 'var(--color-text-secondary)', margin: '2px 0 0 0' }}>
              Core Principle: <strong style={{ color: '#38BDF8' }}>"DETECTION DOES NOT EQUAL THREAT."</strong> Raw video observations are rigorously filtered through kinematics, spatial zones, and behavior before escalation.
            </p>
          </div>

          <button
            onClick={() => onNavigate('AI_ANALYTICS')}
            style={{
              background: 'none',
              border: 'none',
              color: '#38BDF8',
              fontSize: '10px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            Deep Analytics →
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '10px' }}>
          <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>1. OBSERVATIONS</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#9CA3AF', marginTop: '2px' }}>
              {telemetry.fps > 0 ? `${Math.round(telemetry.fps * 60)}/m` : '0/m'}
            </div>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)' }}>Raw Video Frames</span>
          </div>

          <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>2. DETECTIONS</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
              {telemetry.detections ? telemetry.detections.length : tracksCount}
            </div>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)' }}>YOLO Bounding Boxes</span>
          </div>

          <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>3. TRACKS</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#34D399', marginTop: '2px' }}>
              {tracksCount}
            </div>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)' }}>ByteTrack Association</span>
          </div>

          <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>4. BEHAVIORS</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#F59E0B', marginTop: '2px' }}>
              {behaviorsCount}
            </div>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)' }}>Spatial / Kinematic</span>
          </div>

          <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>5. SECURITY EVENTS</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: activeEventsCount > 0 ? '#EF4444' : '#9CA3AF', marginTop: '2px' }}>
              {events.length}
            </div>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)' }}>FusionEngine Raisings</span>
          </div>

          <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '4px', padding: '8px', textAlign: 'center' }}>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)', fontWeight: 700 }}>6. EVIDENCE PACKAGES</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#10B981', marginTop: '2px' }}>
              {totalEvidenceCount}
            </div>
            <span style={{ fontSize: '7.5px', color: 'var(--color-text-muted)' }}>SHA-256 Sealed</span>
          </div>
        </div>
      </div>
    </div>
  );
};
