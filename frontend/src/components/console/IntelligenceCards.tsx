import React from 'react';
import { CloudMoon, Navigation, MapPin, Activity, Gauge } from 'lucide-react';
import { EnvironmentState, BorderTrack, SpatialState, BehaviorPrimitive, EventRecord } from '../../types';

interface IntelligenceCardsProps {
  environment?: EnvironmentState;
  borderTrack?: BorderTrack;
  spatialState?: SpatialState;
  behaviors: BehaviorPrimitive[];
  activeEvent?: EventRecord | null;
}

export const IntelligenceCards: React.FC<IntelligenceCardsProps> = ({
  environment,
  borderTrack,
  spatialState,
  behaviors,
  activeEvent,
}) => {
  const score = activeEvent ? activeEvent.risk_score : 87.6;
  const isHigh = score >= 75;
  const isMedium = score >= 50 && score < 75;
  const riskColor = isHigh ? '#ef4444' : isMedium ? '#f59e0b' : '#10b981';

  return (
    <div className="intelligence-row">
      {/* 1. Environment Pillar */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">ENVIRONMENT</span>
          <CloudMoon size={14} color="#38bdf8" />
        </div>
        <div style={{ fontSize: '13px', fontWeight: 800, color: '#f8fafc', marginTop: '2px' }}>
          {environment?.lighting || 'NIGHT'}
        </div>
        <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
          VISIBILITY: <strong style={{ color: '#f59e0b' }}>{environment?.visibility || 'DEGRADED'}</strong>
        </div>
        <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
          QUALITY SCORE: <strong style={{ color: '#10b981' }}>{environment?.quality_score !== undefined ? environment.quality_score.toFixed(2) : '0.61'}</strong>
        </div>
      </div>

      {/* 2. Border Track (Cross-Camera Continuity) Pillar */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">BORDER TRACK</span>
          <Navigation size={14} color="#10b981" />
        </div>
        <div style={{ fontSize: '13px', fontWeight: 800, color: '#10b981', fontFamily: 'var(--font-mono)' }}>
          {borderTrack?.border_track_id || 'BT-104'}
        </div>
        <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
          {borderTrack?.camera_sequence ? borderTrack.camera_sequence.join(' → ') : 'CAM-01 → CAM-02'}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '2px' }}>
          <span className="status-pill pill-green" style={{ fontSize: '9px', padding: '1px 5px' }}>
            {borderTrack?.association_state || 'CONFIRMED'}
          </span>
          <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            ({borderTrack?.duration_seconds ? borderTrack.duration_seconds.toFixed(1) : '19.2'}s)
          </span>
        </div>
      </div>

      {/* 3. Spatial Intelligence Pillar */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">SPATIAL STATUS</span>
          <MapPin size={14} color="#ef4444" />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
          <span style={{ color: 'var(--text-muted)' }}>ZONE</span>
          <strong style={{ color: spatialState?.border_side === 'RESTRICTED' ? '#ef4444' : '#f59e0b' }}>
            {spatialState?.border_side || 'RESTRICTED'}
          </strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
          <span style={{ color: 'var(--text-muted)' }}>DISTANCE</span>
          <strong className="font-mono">
            {spatialState?.distance_to_border_meters !== undefined ? `${spatialState.distance_to_border_meters.toFixed(1)} m` : '2.3 m'}
          </strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
          <span style={{ color: 'var(--text-muted)' }}>DIRECTION</span>
          <strong style={{ color: '#10b981' }}>
            {spatialState?.movement_direction || 'TOWARD ↑'}
          </strong>
        </div>
      </div>

      {/* 4. Temporal Behaviour Pillar */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">BEHAVIOUR</span>
          <Activity size={14} color="#f59e0b" />
        </div>
        <div style={{ fontSize: '11px', fontWeight: 700, color: '#f59e0b', marginTop: '2px', lineHeight: 1.2 }}>
          {behaviors.length > 0 ? behaviors[0].behavior_type : 'PERSISTENT APPROACH'}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginTop: 'auto' }}>
          <span style={{ color: 'var(--text-muted)' }}>DURATION</span>
          <strong className="font-mono">{behaviors.length > 0 ? `${behaviors[0].duration_seconds.toFixed(1)}s` : '19.2 sec'}</strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
          <span style={{ color: 'var(--text-muted)' }}>CONFIDENCE</span>
          <strong style={{ color: '#10b981' }}>{behaviors.length > 0 && behaviors[0].confidence ? behaviors[0].confidence.toFixed(2) : '0.89'}</strong>
        </div>
      </div>

      {/* 5. Multi-Modal Risk Assessment Pillar */}
      <div className="intel-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="intel-card-header">RISK ASSESSMENT</span>
          <Gauge size={14} color={riskColor} />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>PRIORITY</div>
            <span className={`status-pill ${isHigh ? 'pill-red' : isMedium ? 'pill-amber' : 'pill-green'}`} style={{ fontSize: '9px' }}>
              {activeEvent?.priority || 'HIGH'}
            </span>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>SCORE</div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: riskColor, fontFamily: 'var(--font-mono)' }}>
              {score.toFixed(1)} <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>/ 100</span>
            </div>
          </div>
        </div>
        {/* Visual Risk Gauge Meter */}
        <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden', marginTop: '4px' }}>
          <div style={{ width: `${Math.min(100, Math.max(5, score))}%`, height: '100%', background: riskColor, transition: 'width 0.3s ease' }} />
        </div>
      </div>
    </div>
  );
};
