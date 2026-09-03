import React from 'react';
import { CloudMoon, Crosshair, Navigation, MapPin, Activity, AlertOctagon } from 'lucide-react';
import { EnvironmentState, TrackState, SpatialState, BehaviorPrimitive, EventRecord } from '../../types';

interface IntelligenceCardsProps {
  environment?: EnvironmentState;
  tracks?: TrackState[];
  selectedTrack?: TrackState | null;
  spatialStates?: SpatialState[];
  behaviors: BehaviorPrimitive[];
  activeEvent?: EventRecord | null;
}

export const IntelligenceCards: React.FC<IntelligenceCardsProps> = ({
  environment,
  tracks = [],
  selectedTrack,
  spatialStates = [],
  behaviors = [],
  activeEvent,
}) => {
  // Primary active track
  const activeTrk = selectedTrack || (tracks.length > 0 ? tracks[0] : null);
  const activeSpatial = spatialStates.find((s) => s.track_id === activeTrk?.track_id) || spatialStates[0];
  const activeBeh = behaviors.find((b) => b.track_id === activeTrk?.track_id) || (behaviors.length > 0 ? behaviors[0] : null);

  const hasEvent = Boolean(activeEvent);
  const score = activeEvent ? activeEvent.risk_score : 0.0;
  const isCritical = activeEvent?.priority === 'CRITICAL';
  const isHigh = activeEvent?.priority === 'HIGH' || score >= 75;
  const isMedium = activeEvent?.priority === 'MEDIUM' || (score >= 50 && score < 75);
  const riskColor = hasEvent ? (isCritical || isHigh ? '#ef4444' : isMedium ? '#f59e0b' : '#10b981') : '#64748b';

  const detectionConfidence = activeTrk?.confidence ? (activeTrk.confidence * 100).toFixed(0) + '%' : '--';
  const eventConfidence = activeEvent?.confidence !== undefined ? (activeEvent.confidence * 100).toFixed(0) + '%' : '--';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto' }}>
      {/* 6. RISK / THREAT ASSESSMENT (Prominently Placed at Top) */}
      <div
        className="intel-card"
        style={{
          background: hasEvent ? 'rgba(239, 68, 68, 0.08)' : 'var(--bg-panel)',
          border: `1px solid ${hasEvent ? (isHigh ? 'rgba(239, 68, 68, 0.5)' : 'rgba(245, 158, 11, 0.5)') : 'var(--border-panel)'}`,
          padding: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span className="intel-card-header" style={{ color: riskColor, letterSpacing: '0.08em' }}>
            THREAT & RISK ASSESSMENT
          </span>
          <AlertOctagon size={16} color={riskColor} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
          <div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>DETECTION CONFIDENCE</div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
              {detectionConfidence}
            </div>
            <div style={{ fontSize: '8px', color: 'var(--text-muted)' }}>Raw Sensor Signal</div>
          </div>

          <div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>EVENT CONFIDENCE</div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: '#10b981', fontFamily: 'var(--font-mono)' }}>
              {eventConfidence}
            </div>
            <div style={{ fontSize: '8px', color: 'var(--text-muted)' }}>Behavioral Intent</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', borderTop: '1px solid var(--border-panel)', paddingTop: '6px' }}>
          <div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>ALERT PRIORITY</div>
            <span
              className={`status-pill ${hasEvent ? (isHigh ? 'pill-red' : isMedium ? 'pill-amber' : 'pill-green') : 'pill-gray'}`}
              style={{ fontSize: '10px', fontWeight: 700, padding: '2px 8px' }}
            >
              {activeEvent?.priority || 'NORMAL'}
            </span>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>RISK SCORE</div>
            <div style={{ fontSize: '18px', fontWeight: 900, color: riskColor, fontFamily: 'var(--font-mono)' }}>
              {hasEvent ? score.toFixed(1) : '0.0'} <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 400 }}>/ 100</span>
            </div>
          </div>
        </div>

        {/* Dynamic Risk Gauge */}
        <div style={{ width: '100%', height: '5px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden', marginTop: '6px' }}>
          <div style={{ width: `${Math.min(100, Math.max(0, score))}%`, height: '100%', background: riskColor, transition: 'width 0.3s ease' }} />
        </div>
      </div>

      {/* 1. ENVIRONMENT CARD */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">1. ENVIRONMENT</span>
          <CloudMoon size={14} color="#38bdf8" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '10px', marginTop: '2px' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>LIGHTING: </span>
            <strong>{environment?.lighting || 'DAYLIGHT'}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>VISIBILITY: </span>
            <strong style={{ color: environment?.visibility === 'DEGRADED' ? '#f59e0b' : '#10b981' }}>
              {environment?.visibility || 'HIGH'}
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>QUALITY: </span>
            <strong className="font-mono">{environment?.quality_score !== undefined ? environment.quality_score.toFixed(2) : '0.80'}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>WEATHER: </span>
            <span>{environment?.weather_hint || 'CLEAR'}</span>
          </div>
        </div>
      </div>

      {/* 2. DETECTION CARD */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">2. ACTIVE TARGETS</span>
          <Crosshair size={14} color="#10b981" />
        </div>
        {tracks.length === 0 ? (
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', padding: '4px 0' }}>NO TARGETS IN SCENE</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '2px' }}>
            {tracks.map((t) => (
              <div
                key={t.track_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: 'rgba(255,255,255,0.03)',
                  padding: '3px 6px',
                  borderRadius: '3px',
                  fontSize: '10px',
                  border: t.track_id === activeTrk?.track_id ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid transparent',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontWeight: 700, color: '#f8fafc' }}>{t.class_id || 'PERSON'}</span>
                  <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>ID #{t.track_id}</span>
                </div>
                <div className="font-mono" style={{ color: '#10b981', fontWeight: 600 }}>
                  {t.confidence !== undefined ? `${(t.confidence * 100).toFixed(0)}%` : '--'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3. TRACKING CARD */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">3. TRACK KINEMATICS</span>
          <Navigation size={14} color="#a78bfa" />
        </div>
        {activeTrk ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '10px', marginTop: '2px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>TRACK ID: </span>
              <strong className="font-mono" style={{ color: 'var(--accent-cyan)' }}>#{activeTrk.track_id}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>PERSISTENCE: </span>
              <strong className="font-mono">{activeTrk.persistence || activeTrk.age_frames || 1} f</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>SPEED: </span>
              <strong className="font-mono">
                {activeTrk.speed_pixels_per_sec !== undefined ? `${activeTrk.speed_pixels_per_sec.toFixed(0)} px/s` : '--'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>FOOT XY: </span>
              <strong className="font-mono">
                {activeTrk.ground_point ? `${activeTrk.ground_point.x.toFixed(0)}, ${activeTrk.ground_point.y.toFixed(0)}` : '--'}
              </strong>
            </div>
          </div>
        ) : (
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', padding: '4px 0' }}>Awaiting track confirmation</div>
        )}
      </div>

      {/* 4. SPATIAL CARD */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">4. SPATIAL GEOMETRY</span>
          <MapPin size={14} color="#ef4444" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '10px', marginTop: '2px' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>BORDER ID: </span>
            <strong className="font-mono">{activeSpatial?.border_id || 'SEC-ALPHA'}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>ZONE: </span>
            <strong
              style={{
                color: activeSpatial?.border_side === 'RESTRICTED' ? '#ef4444' : activeSpatial?.border_side === 'WARNING_BUFFER' ? '#f59e0b' : '#10b981',
              }}
            >
              {activeSpatial?.border_side || 'PERMITTED'}
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>DISTANCE: </span>
            <strong className="font-mono">
              {activeSpatial?.distance_to_border_meters !== undefined ? `${activeSpatial.distance_to_border_meters.toFixed(1)} m` : '--'}
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>CROSSING: </span>
            <strong style={{ color: activeSpatial?.crossing_status?.includes('CROSSING') ? '#ef4444' : '#10b981' }}>
              {activeSpatial?.crossing_status || 'NONE'}
            </strong>
          </div>
        </div>
      </div>

      {/* 5. BEHAVIOR CARD */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">5. BEHAVIOR PATTERNS</span>
          <Activity size={14} color="#f59e0b" />
        </div>
        {activeBeh ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '10px', marginTop: '2px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>PRIMITIVE:</span>
              <strong style={{ color: '#f59e0b' }}>{activeBeh.behavior_type}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>CONFIDENCE:</span>
              <strong className="font-mono" style={{ color: '#10b981' }}>
                {activeBeh.confidence !== undefined ? `${(activeBeh.confidence * 100).toFixed(0)}%` : '--'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>DURATION:</span>
              <strong className="font-mono">{activeBeh.duration_seconds.toFixed(1)}s</strong>
            </div>
          </div>
        ) : (
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', padding: '4px 0' }}>NORMAL TRANSIT / LOITERING NONE</div>
        )}
      </div>
    </div>
  );
};
