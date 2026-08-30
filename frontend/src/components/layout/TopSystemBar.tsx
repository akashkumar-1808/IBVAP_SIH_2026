import React, { useState, useEffect } from 'react';
import { Shield, Radio, Activity, Eye } from 'lucide-react';
import { CameraInfo, DemonstrationScenario } from '../../types';

interface TopSystemBarProps {
  currentSector: string;
  isLiveMode: boolean;
  cameras: CameraInfo[];
  fps: number;
  systemHealth: string;
  scenarios: DemonstrationScenario[];
  activeScenarioId?: string;
  onSelectScenario: (scenarioId: string) => void;
}

export const TopSystemBar: React.FC<TopSystemBarProps> = ({
  currentSector,
  isLiveMode,
  cameras,
  fps,
  systemHealth,
  scenarios,
  activeScenarioId,
  onSelectScenario,
}) => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString('en-GB', { hour12: false }) +
          ' ' +
          now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const onlineCameras = cameras.filter((c) => c.status === 'ONLINE').length;

  return (
    <header className="top-bar">
      {/* Brand & Sector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#06b6d4',
            }}
          >
            <Shield size={16} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '13px', letterSpacing: '0.05em' }}>IBVAP</div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)', lineHeight: 1 }}>COMMAND CONSOLE</div>
          </div>
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-panel)' }} />

        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>{currentSector}</div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Northern Border Sector</div>
        </div>

        <div className={`status-pill ${isLiveMode ? 'pill-green' : 'pill-amber'}`}>
          <Radio size={12} className={isLiveMode ? 'animate-pulse' : ''} />
          {isLiveMode ? 'LIVE' : 'REPLAY'}
        </div>
      </div>

      {/* Center Operational Metrics */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
            {String(onlineCameras).padStart(2, '0')} / {String(cameras.length).padStart(2, '0')}
          </div>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Cameras Online</div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
            {fps > 0 ? fps.toFixed(1) : '--'} FPS
          </div>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Pipeline Rate</div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div className="status-pill pill-green">
            <Activity size={10} />
            {systemHealth}
          </div>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '2px' }}>
            System Health
          </div>
        </div>

        {/* Jury Demo Scenario Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
          <select
            value={activeScenarioId || ''}
            onChange={(e) => onSelectScenario(e.target.value)}
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-panel)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="" disabled>Select Jury Demo Scenario...</option>
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                ▶ {sc.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Right Time & Operator Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{timeStr}</div>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>UTC SYNCHRONIZED</div>
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-panel)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-secondary)',
            }}
          >
            <Eye size={14} />
          </div>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600 }}>OPERATOR</div>
            <div style={{ fontSize: '9px', color: 'var(--accent-cyan)' }}>CONTROL ROOM</div>
          </div>
        </div>
      </div>
    </header>
  );
};
