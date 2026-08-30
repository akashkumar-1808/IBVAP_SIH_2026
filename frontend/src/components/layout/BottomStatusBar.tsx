import React from 'react';
import { Database, HardDrive, Bell, Shield } from 'lucide-react';

export const BottomStatusBar: React.FC = () => {
  return (
    <footer className="bottom-bar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Shield size={12} color="var(--accent-cyan)" />
          <span>IBVAP v1.0.0</span>
        </span>

        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Database size={12} />
          <span>DATA RETENTION: <strong>30 Days</strong></span>
        </span>

        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <HardDrive size={12} />
          <span>STORAGE: <strong>1.2 TB / 5.0 TB</strong></span>
        </span>

        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Bell size={12} />
          <span>ALERT SETTINGS: <strong style={{ color: '#ef4444' }}>HIGH</strong> & <strong style={{ color: '#f59e0b' }}>MEDIUM</strong></span>
        </span>
      </div>

      <div>
        <span>© 2026 IBVAP. Real-Time Border Video Analytics Platform.</span>
      </div>
    </footer>
  );
};
