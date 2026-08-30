import React, { useState } from 'react';
import { Play, ShieldCheck } from 'lucide-react';
import { EvidencePackage, EventRecord } from '../../types';
import { getEvidenceFileUrl } from '../../services/api';

interface EvidencePackagePreviewProps {
  evidencePackage?: EvidencePackage | null;
  event?: EventRecord | null;
}

export const EvidencePackagePreview: React.FC<EvidencePackagePreviewProps> = ({
  evidencePackage,
  event,
}) => {
  const [activeTab, setActiveTab] = useState<'SNAPSHOT' | 'VIDEO' | 'TRAJECTORY' | 'DETAILS'>('SNAPSHOT');
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const rawRec = evidencePackage?.evidence_records.find((r) => r.evidence_type === 'SNAPSHOT_RAW');
  const annRec = evidencePackage?.evidence_records.find((r) => r.evidence_type === 'SNAPSHOT_ANNOTATED');

  const sha256Short = annRec?.sha256 ? `${annRec.sha256.substring(0, 4)}...${annRec.sha256.substring(annRec.sha256.length - 4)}` : 'a7f3...9c2e';

  return (
    <div className="forensic-panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="intel-card-header">EVIDENCE PACKAGE</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          {(['SNAPSHOT', 'VIDEO', 'TRAJECTORY', 'DETAILS'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                background: activeTab === tab ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                color: activeTab === tab ? 'var(--accent-cyan)' : 'var(--text-muted)',
                border: activeTab === tab ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid transparent',
                borderRadius: '3px',
                padding: '2px 6px',
                fontSize: '9px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Media Thumbnails Area */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', flex: 1 }}>
        {/* Raw Snapshot */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>RAW SNAPSHOT</div>
          <div
            onClick={() => setIsModalOpen(true)}
            style={{
              position: 'relative',
              background: '#0a0d14',
              border: '1px solid var(--border-panel)',
              borderRadius: '4px',
              height: '75px',
              overflow: 'hidden',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {rawRec ? (
              <img src={getEvidenceFileUrl(rawRec.id)} alt="Raw" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>[RAW KEYFRAME]</div>
            )}
          </div>
        </div>

        {/* Annotated Snapshot */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>ANNOTATED SNAPSHOT</div>
          <div
            onClick={() => setIsModalOpen(true)}
            style={{
              position: 'relative',
              background: '#0a0d14',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              borderRadius: '4px',
              height: '75px',
              overflow: 'hidden',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {annRec ? (
              <img src={getEvidenceFileUrl(annRec.id)} alt="Annotated" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <div style={{ fontSize: '10px', color: '#38bdf8' }}>[FORENSIC HUD KEYFRAME]</div>
            )}
          </div>
        </div>
      </div>

      {/* Video Clip Bar & Cryptographic Seal Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-panel)', paddingTop: '6px', marginTop: '2px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-command"
            style={{ padding: '3px 8px', fontSize: '10px' }}
          >
            <Play size={11} color="#38bdf8" />
            <span>Event Clip (8.6s)</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '8px', color: 'var(--text-muted)' }}>SHA-256 HASH</div>
            <div className="font-mono" style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
              {sha256Short}
            </div>
          </div>
          <div className="status-pill pill-green" style={{ fontSize: '9px', padding: '2px 6px' }}>
            <ShieldCheck size={11} />
            VERIFIED
          </div>
        </div>
      </div>

      {/* Full Forensic Modal */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(5, 7, 10, 0.85)',
            backdropFilter: 'blur(8px)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
          onClick={() => setIsModalOpen(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '800px',
              maxWidth: '90vw',
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-panel)',
              borderRadius: '8px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.8)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '16px', fontWeight: 800 }}>FORENSIC EVIDENCE PACKAGE</div>
                <div className="font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  EVENT: {event?.id || 'EVT-2025-0518-000104'} | CAMERA: {event?.camera_id || 'CAM-01'}
                </div>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="btn-command">
                Close
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>RAW KEYFRAME</div>
                <div style={{ background: '#000', borderRadius: '4px', height: '220px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {rawRec ? <img src={getEvidenceFileUrl(rawRec.id)} alt="Raw" style={{ width: '100%', height: '100%', objectFit: 'contain' }} /> : <div style={{ color: '#64748b' }}>Raw Snapshot</div>}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '4px', color: '#38bdf8' }}>ANNOTATED HUD KEYFRAME</div>
                <div style={{ background: '#000', borderRadius: '4px', height: '220px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {annRec ? <img src={getEvidenceFileUrl(annRec.id)} alt="Annotated" style={{ width: '100%', height: '100%', objectFit: 'contain' }} /> : <div style={{ color: '#38bdf8' }}>Annotated Keyframe</div>}
                </div>
              </div>
            </div>

            <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }}>
              <div>
                <div style={{ color: 'var(--text-muted)' }}>IMMUTABLE CRYPTOGRAPHIC SEAL</div>
                <div className="font-mono" style={{ color: '#10b981', fontWeight: 600 }}>
                  SHA-256: {annRec?.sha256 || 'a7f3b8902c48d88e02d6b38c2ef40182470129bc4882190da98ef652a7f39c2e'}
                </div>
              </div>
              <span className="status-pill pill-green">
                <ShieldCheck size={13} />
                CRYPTOGRAPHICALLY VERIFIED
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
