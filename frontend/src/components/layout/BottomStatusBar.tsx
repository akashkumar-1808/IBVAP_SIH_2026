import React from 'react';

export const BottomStatusBar: React.FC = () => {
  return (
    <footer className="bottom-system-bar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <span style={{ fontWeight: 700, color: 'var(--color-text-secondary)' }}>IBVAP v1.0.0</span>
        <span style={{ color: 'var(--color-border)' }}>|</span>
        <span>DATA RETENTION: <strong>30 Days</strong></span>
        <span style={{ color: 'var(--color-border)' }}>|</span>
        <span>STORAGE: <strong>SECURE EVIDENCE POOL</strong></span>
        <span style={{ color: 'var(--color-border)' }}>|</span>
        <span>
          ALERT SETTINGS: <strong style={{ color: 'var(--color-red)' }}>HIGH</strong> & <strong style={{ color: 'var(--color-amber)' }}>MEDIUM</strong>
        </span>
      </div>

      <div>
        <span>© 2026 IBVAP. Real-Time Border Video Analytics Platform.</span>
      </div>
    </footer>
  );
};
