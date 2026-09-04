import React from 'react';
import {
  ShieldAlert,
  CloudSun,
  Users,
  GitCommit,
  Compass,
  Activity,
} from 'lucide-react';
import {
  EnvironmentState,
  TrackState,
  SpatialState,
  BehaviorPrimitive,
  EventRecord,
} from '../../types';

interface IntelligenceCardsProps {
  environment?: EnvironmentState;
  tracks: TrackState[];
  selectedTrack?: TrackState | null;
  spatialStates: SpatialState[];
  behaviors: BehaviorPrimitive[];
  activeEvent?: EventRecord | null;
}

export const IntelligenceCards: React.FC<IntelligenceCardsProps> = ({
  environment,
  tracks,
  selectedTrack,
  spatialStates,
  behaviors,
  activeEvent,
}) => {
  // Focus on activeEvent track if available, else selectedTrack, else tracks[0]
  const primaryTrackId = activeEvent?.track_id || selectedTrack?.track_id || (tracks.length > 0 ? tracks[0].track_id : null);
  const primaryTrack = tracks.find((t) => t.track_id === primaryTrackId) || (tracks.length > 0 ? tracks[0] : null);
  const primarySpatial = spatialStates.find((s) => s.track_id === primaryTrack?.track_id) || (spatialStates.length > 0 ? spatialStates[0] : null);
  const primaryBehavior = behaviors.find((b) => b.track_id === primaryTrack?.track_id) || (behaviors.length > 0 ? behaviors[0] : null);

  // 1. Threat & Risk
  const detConf = primaryTrack && typeof primaryTrack.confidence === 'number'
    ? Math.round(primaryTrack.confidence * 100)
    : (activeEvent?.detection_confidence ? Math.round(activeEvent.detection_confidence * 100) : 0);

  const eventConf = activeEvent?.evidence_confidence
    ? Math.round(activeEvent.evidence_confidence * 100)
    : (activeEvent?.detection_confidence ? Math.round(activeEvent.detection_confidence * 100) : 0);

  const riskScore = activeEvent?.risk_score !== undefined
    ? activeEvent.risk_score.toFixed(1)
    : '0.0';

  const priorityStr = activeEvent?.priority || 'NORMAL';
  const isHighOrCritical = priorityStr === 'CRITICAL' || priorityStr === 'HIGH';

  // 2. Environment
  const lightingStr = environment?.lighting ? environment.lighting.toString().toUpperCase() : 'UNKNOWN';
  const visStr = environment?.visibility ? environment.visibility.toString().toUpperCase() : 'UNKNOWN';
  const qualScore = environment?.quality_score !== undefined ? environment.quality_score.toFixed(2) : '--';
  const weatherStr = environment?.weather_hint ? environment.weather_hint.toUpperCase() : 'MONITORING';

  // 3. Kinematics
  const trackIdVal = primaryTrack ? `#${primaryTrack.track_id}` : (activeEvent?.track_id ? `#${activeEvent.track_id}` : '--');
  const persistenceVal = primaryTrack ? `${primaryTrack.age_frames || 0} frames` : '--';
  const speedVal = primaryTrack?.speed_pixels_per_sec !== undefined
    ? `${(primaryTrack.speed_pixels_per_sec * 0.05).toFixed(1)} m/s`
    : '--';

  const footXy = primarySpatial?.ground_contact_point
    ? `${Math.round(primarySpatial.ground_contact_point.x)}, ${Math.round(primarySpatial.ground_contact_point.y)}`
    : (primaryTrack?.ground_point ? `${Math.round(primaryTrack.ground_point.x)}, ${Math.round(primaryTrack.ground_point.y)}` : '--');

  const dirStr = primarySpatial?.movement_direction ? `${primarySpatial.movement_direction} →` : (primaryTrack ? 'STABLE' : '--');

  // 4. Spatial Geometry
  const borderIdStr = primarySpatial?.border_id || (primaryTrack ? 'SEC-ALPHA' : '--');
  const zoneStr = primarySpatial?.border_side ? primarySpatial.border_side.replace(/_/g, ' ') : (primaryTrack ? 'MONITORED' : '--');
  const distStr = primarySpatial?.distance_to_border_meters !== undefined ? `${primarySpatial.distance_to_border_meters.toFixed(1)} m` : '--';
  const crossingStr = primarySpatial?.crossing_status ? primarySpatial.crossing_status.replace(/_/g, ' ') : (primaryTrack ? 'NONE' : '--');

  // 5. Behavior
  const behTypeStr = primaryBehavior?.behavior_type ? primaryBehavior.behavior_type.replace(/_/g, ' ') : (primaryTrack ? 'NORMAL_TRANSIT' : '--');
  const behConfStr = primaryBehavior?.confidence !== undefined ? `${Math.round(primaryBehavior.confidence * 100)}%` : '--';
  const behDurStr = primaryBehavior?.duration_seconds !== undefined ? `${primaryBehavior.duration_seconds.toFixed(1)} s` : '--';
  const intentStr = zoneStr.includes('RESTRICTED') ? 'RESTRICTED_OCCUPANCY' : (primaryTrack ? 'SURVEILLANCE' : '--');

  return (
    <div className="intelligence-grid-3x2">
      {/* 1. THREAT & RISK */}
      <div className="intel-box">
        <div className="intel-box-title">
          <span>THREAT & RISK</span>
          <ShieldAlert size={13} color={isHighOrCritical ? 'var(--color-red)' : 'var(--color-green)'} />
        </div>

        <div className="intel-data-table">
          <div>
            <div className="intel-data-row">
              <span className="intel-data-label">DETECTION CONFIDENCE</span>
              <span className="intel-data-val">{detConf}%</span>
            </div>
            <div style={{ width: '100%', height: '3px', backgroundColor: 'var(--color-surface-elevated)', borderRadius: '2px', overflow: 'hidden', marginTop: '2px' }}>
              <div style={{ width: `${detConf}%`, height: '100%', backgroundColor: '#38BDF8' }} />
            </div>
          </div>

          <div style={{ marginTop: '4px' }}>
            <div className="intel-data-row">
              <span className="intel-data-label">EVENT CONFIDENCE</span>
              <span className="intel-data-val">{eventConf}%</span>
            </div>
            <div style={{ width: '100%', height: '3px', backgroundColor: 'var(--color-surface-elevated)', borderRadius: '2px', overflow: 'hidden', marginTop: '2px' }}>
              <div style={{ width: `${eventConf}%`, height: '100%', backgroundColor: 'var(--color-green)' }} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px', paddingTop: '4px', borderTop: '1px solid var(--color-border-subtle)' }}>
            <div>
              <div className="intel-data-label">RISK SCORE</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: 800, color: isHighOrCritical ? 'var(--color-red)' : 'var(--color-green)' }}>
                {riskScore} <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>/ 100</span>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="intel-data-label">PRIORITY</div>
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 800,
                  color: isHighOrCritical ? 'var(--color-red)' : 'var(--color-green)',
                  backgroundColor: isHighOrCritical ? 'var(--color-red-bg)' : 'var(--color-green-bg)',
                  padding: '2px 6px',
                  borderRadius: '3px',
                }}
              >
                {priorityStr}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. ENVIRONMENT */}
      <div className="intel-box">
        <div className="intel-box-title">
          <span>ENVIRONMENT</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: environment ? 'var(--color-green)' : 'var(--color-border)' }} />
            <CloudSun size={13} color="var(--color-text-muted)" />
          </div>
        </div>

        <div className="intel-data-table" style={{ gap: '6px' }}>
          <div className="intel-data-row">
            <span className="intel-data-label">LIGHTING</span>
            <span className="intel-data-val">{lightingStr}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">VISIBILITY</span>
            <span className="intel-data-val" style={{ color: visStr.includes('GOOD') || visStr.includes('EXCELLENT') ? 'var(--color-green)' : 'var(--color-text-primary)' }}>
              {visStr}
            </span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">QUALITY SCORE</span>
            <span className="intel-data-val">{qualScore}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">WEATHER</span>
            <span className="intel-data-val">{weatherStr}</span>
          </div>
        </div>
      </div>

      {/* 3. ACTIVE TARGETS */}
      <div className="intel-box">
        <div className="intel-box-title">
          <span>ACTIVE TARGETS</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{tracks.length}</span>
            <Users size={13} color="var(--color-text-muted)" />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minHeight: '60px' }}>
          {tracks.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-muted)', fontSize: '10px', paddingTop: '15px' }}>
              No active targets in view
            </div>
          ) : (
            tracks.slice(0, 4).map((t) => {
              const isTargetActive = t.track_id === primaryTrackId;
              const targetConf = t.confidence !== undefined ? Math.round(t.confidence * 100) : '--';
              return (
                <div
                  key={t.track_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '2px 4px',
                    borderRadius: '2px',
                    fontSize: '10px',
                    backgroundColor: isTargetActive ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
                    color: isTargetActive ? 'var(--color-red)' : 'var(--color-text-secondary)',
                    fontWeight: isTargetActive ? 700 : 500,
                  }}
                >
                  <span className="font-mono">ID #{t.track_id}</span>
                  <span>{t.class_id || 'PERSON'}</span>
                  <span className="font-mono">{targetConf}%</span>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 4. TRACK KINEMATICS */}
      <div className="intel-box">
        <div className="intel-box-title">
          <span>TRACK KINEMATICS</span>
          <GitCommit size={13} color="var(--color-text-muted)" />
        </div>

        <div className="intel-data-table" style={{ gap: '5px' }}>
          <div className="intel-data-row">
            <span className="intel-data-label">TRACK ID</span>
            <span className="intel-data-val">{trackIdVal}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">PERSISTENCE</span>
            <span className="intel-data-val">{persistenceVal}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">SPEED</span>
            <span className="intel-data-val">{speedVal}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">FOOT XY</span>
            <span className="intel-data-val" style={{ color: footXy !== '--' ? 'var(--color-green)' : 'var(--color-text-muted)' }}>
              {footXy}
            </span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">DIRECTION</span>
            <span className="intel-data-val" style={{ color: dirStr !== '--' ? 'var(--color-green)' : 'var(--color-text-muted)' }}>
              {dirStr}
            </span>
          </div>
        </div>
      </div>

      {/* 5. SPATIAL GEOMETRY */}
      <div className="intel-box">
        <div className="intel-box-title">
          <span>SPATIAL GEOMETRY</span>
          <Compass size={13} color="var(--color-text-muted)" />
        </div>

        <div className="intel-data-table" style={{ gap: '5px' }}>
          <div className="intel-data-row">
            <span className="intel-data-label">BORDER ID</span>
            <span className="intel-data-val">{borderIdStr}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">ZONE</span>
            <span className="intel-data-val" style={{ color: zoneStr.includes('RESTRICTED') ? 'var(--color-red)' : 'var(--color-text-primary)' }}>
              {zoneStr}
            </span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">DISTANCE TO BORDER</span>
            <span className="intel-data-val">{distStr}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">MOVEMENT</span>
            <span className="intel-data-val">{dirStr.replace(' →', '')}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">CROSSING STATUS</span>
            <span className="intel-data-val" style={{ color: crossingStr.includes('CONFIRMED') ? 'var(--color-red)' : 'var(--color-text-primary)' }}>
              {crossingStr}
            </span>
          </div>
        </div>
      </div>

      {/* 6. BEHAVIOR PATTERN */}
      <div className="intel-box">
        <div className="intel-box-title">
          <span>BEHAVIOR PATTERN</span>
          <Activity size={13} color="var(--color-text-muted)" />
        </div>

        <div className="intel-data-table" style={{ gap: '5px' }}>
          <div className="intel-data-row">
            <span className="intel-data-label">ACTIVE BEHAVIOR</span>
            <span className="intel-data-val" style={{ color: behTypeStr.includes('APPROACH') ? 'var(--color-amber)' : 'var(--color-text-primary)' }}>
              {behTypeStr}
            </span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">CONFIDENCE</span>
            <span className="intel-data-val">{behConfStr}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">DURATION</span>
            <span className="intel-data-val">{behDurStr}</span>
          </div>
          <div className="intel-data-row">
            <span className="intel-data-label">INTENT</span>
            <span className="intel-data-val" style={{ color: intentStr.includes('RESTRICTED') ? 'var(--color-red)' : 'var(--color-text-primary)' }}>
              {intentStr}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
