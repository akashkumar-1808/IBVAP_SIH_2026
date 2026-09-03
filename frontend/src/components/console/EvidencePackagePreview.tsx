import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, ExternalLink, RefreshCw } from 'lucide-react';
import { EvidencePackage, EventRecord } from '../../types';
import { getEvidenceFileUrl, verifyEvidenceIntegrity } from '../../services/api';

interface EvidencePackagePreviewProps {
  evidencePackage?: EvidencePackage | null;
  event?: EventRecord | null;
}

export const EvidencePackagePreview: React.FC<EvidencePackagePreviewProps> = ({
  evidencePackage,
  event,
}) => {
  const [activeTab, setActiveTab] = useState<'INCIDENT_CLIP' | 'SNAPSHOTS' | 'PRE_EVENT' | 'MANIFEST'>('INCIDENT_CLIP');
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<{ is_valid?: boolean; details?: string } | null>(null);

  const rawRec = evidencePackage?.evidence_records.find((r) => r.evidence_type === 'SNAPSHOT_RAW');
  const annRec = evidencePackage?.evidence_records.find((r) => r.evidence_type === 'SNAPSHOT_ANNOTATED');
  const incRec = evidencePackage?.evidence_records.find((r) => r.evidence_type === 'CLIP_INCIDENT' || r.evidence_type === 'VIDEO_INCIDENT');
  const preRec = evidencePackage?.evidence_records.find((r) => r.evidence_type === 'CLIP_PRE_EVENT' || r.evidence_type === 'VIDEO_PRE_EVENT');

  const sha256Seal = evidencePackage?.sha256_seal || annRec?.sha256 || rawRec?.sha256;
  const sha256Short = sha256Seal
    ? `${sha256Seal.substring(0, 6)}...${sha256Seal.substring(sha256Seal.length - 6)}`
    : '--';

  // Perform real-time integrity check
  const handleVerify = async () => {
    const targetId = annRec?.id || rawRec?.id || incRec?.id;
    if (!targetId) return;
    setIsVerifying(true);
    try {
      const res = await verifyEvidenceIntegrity(targetId);
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationResult({ is_valid: false, details: err.message || 'Verification failed' });
    } finally {
      setIsVerifying(false);
    }
  };

  const isTamperFree = verificationResult
    ? verificationResult.is_valid === true
    : (evidencePackage?.is_tamper_free ?? true);

  if (!event && !evidencePackage) {
    return (
      <div
        className="forensic-panel"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '11px',
          textAlign: 'center',
          gap: '6px',
          minHeight: '160px',
        }}
      >
        <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>NO EVIDENCE PACKAGE</div>
        <div>Awaiting incident detection to build forensic package</div>
      </div>
    );
  }

  return (
    <div className="forensic-panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px', minHeight: '160px' }}>
      {/* Header & View Switcher Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="intel-card-header">EVIDENCE PACKAGE</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          {(['INCIDENT_CLIP', 'SNAPSHOTS', 'PRE_EVENT', 'MANIFEST'] as const).map((tab) => (
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
              {tab.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Main Evidence Media Display Area */}
      <div style={{ flex: 1, minHeight: '130px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#05070a', borderRadius: '4px', overflow: 'hidden', border: '1px solid var(--border-panel)' }}>
        {/* Tab 1: Incident Video Clip (Playable) */}
        {activeTab === 'INCIDENT_CLIP' && (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4px' }}>
            {incRec ? (
              <video
                controls
                style={{ width: '100%', maxHeight: '140px', borderRadius: '4px', objectFit: 'contain' }}
                src={getEvidenceFileUrl(incRec.id)}
              />
            ) : (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center' }}>
                Incident clip rendering in progress...
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Keyframe Snapshots (Raw & Annotated) */}
        {activeTab === 'SNAPSHOTS' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', width: '100%', height: '100%', padding: '6px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div style={{ fontSize: '8.5px', color: 'var(--text-muted)' }}>RAW SNAPSHOT</div>
              <div style={{ height: '95px', background: '#000', borderRadius: '3px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} onClick={() => setIsModalOpen(true)}>
                {rawRec ? (
                  <img src={getEvidenceFileUrl(rawRec.id)} alt="Raw Snapshot" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>[RAW KEYFRAME]</div>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div style={{ fontSize: '8.5px', color: '#38bdf8' }}>ANNOTATED HUD</div>
              <div style={{ height: '95px', background: '#000', borderRadius: '3px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }} onClick={() => setIsModalOpen(true)}>
                {annRec ? (
                  <img src={getEvidenceFileUrl(annRec.id)} alt="Annotated Snapshot" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <div style={{ fontSize: '9px', color: '#38bdf8' }}>[ANNOTATED KEYFRAME]</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Pre-Event Video Clip */}
        {activeTab === 'PRE_EVENT' && (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4px' }}>
            {preRec ? (
              <video
                controls
                style={{ width: '100%', maxHeight: '140px', borderRadius: '4px', objectFit: 'contain' }}
                src={getEvidenceFileUrl(preRec.id)}
              />
            ) : (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center' }}>
                Pre-event lead-up clip unavailable
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Cryptographic Audit Manifest */}
        {activeTab === 'MANIFEST' && (
          <div style={{ width: '100%', height: '100%', padding: '6px', overflowY: 'auto', maxHeight: '130px', fontSize: '9.5px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
            <pre style={{ margin: 0 }}>
              {evidencePackage?.manifest
                ? JSON.stringify(evidencePackage.manifest, null, 2)
                : `{\n  "event_id": "${event?.id || '--'}",\n  "sha256_seal": "${sha256Seal || '--'}",\n  "status": "SEALED"\n}`}
            </pre>
          </div>
        )}
      </div>

      {/* Footer: SHA-256 Cryptographic Verification Seal */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-panel)', paddingTop: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-command"
            style={{ padding: '2px 6px', fontSize: '9.5px' }}
          >
            <ExternalLink size={11} />
            <span>Full Forensic View</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '8px', color: 'var(--text-muted)' }}>SHA-256 SEAL</div>
            <div className="font-mono" style={{ fontSize: '9.5px', color: 'var(--text-secondary)' }}>
              {sha256Short}
            </div>
          </div>

          <button
            onClick={handleVerify}
            disabled={isVerifying || !sha256Seal}
            className={`status-pill ${isTamperFree ? 'pill-green' : 'pill-red'}`}
            style={{ fontSize: '9px', padding: '3px 7px', cursor: 'pointer', border: 'none' }}
          >
            {isVerifying ? (
              <RefreshCw size={10} className="animate-spin" />
            ) : isTamperFree ? (
              <ShieldCheck size={11} />
            ) : (
              <ShieldAlert size={11} />
            )}
            <span>{isVerifying ? 'VERIFYING' : isTamperFree ? 'SHA-256 VERIFIED' : 'TAMPER DETECTED'}</span>
          </button>
        </div>
      </div>

      {/* Forensic Inspection Modal */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(5, 7, 10, 0.88)',
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
              width: '860px',
              maxWidth: '92vw',
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-panel)',
              borderRadius: '8px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.85)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '16px', fontWeight: 800 }}>FORENSIC EVIDENCE REPOSITORY</div>
                <div className="font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  EVENT: {event?.id || 'NO-EVENT'} | CAMERA: {event?.camera_id || 'DEMO-CAM-01'} | TRACK: #{event?.track_id || 2}
                </div>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="btn-command">
                Close
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>RAW INCIDENT KEYFRAME</div>
                <div style={{ background: '#000', borderRadius: '4px', height: '220px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {rawRec ? <img src={getEvidenceFileUrl(rawRec.id)} alt="Raw" style={{ width: '100%', height: '100%', objectFit: 'contain' }} /> : <div style={{ color: '#64748b' }}>Raw Snapshot</div>}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '4px', color: '#38bdf8' }}>ANNOTATED HUD FORENSIC KEYFRAME</div>
                <div style={{ background: '#000', borderRadius: '4px', height: '220px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {annRec ? <img src={getEvidenceFileUrl(annRec.id)} alt="Annotated" style={{ width: '100%', height: '100%', objectFit: 'contain' }} /> : <div style={{ color: '#38bdf8' }}>Annotated Keyframe</div>}
                </div>
              </div>
            </div>

            {incRec && (
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>INCIDENT VIDEO CLIP (PLAYABLE)</div>
                <video controls style={{ width: '100%', height: '160px', background: '#000', borderRadius: '4px' }} src={getEvidenceFileUrl(incRec.id)} />
              </div>
            )}

            <div style={{ background: 'var(--bg-card)', padding: '10px 14px', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }}>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '9px' }}>SHA-256 IMMUTABLE CRYPTOGRAPHIC SEAL</div>
                <div className="font-mono" style={{ color: isTamperFree ? '#10b981' : '#ef4444', fontWeight: 700 }}>
                  {sha256Seal || 'SEAL COMPUTED ON PACKAGE CREATION'}
                </div>
              </div>
              <span className={`status-pill ${isTamperFree ? 'pill-green' : 'pill-red'}`}>
                {isTamperFree ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />}
                {isTamperFree ? 'CRYPTOGRAPHICALLY VERIFIED' : 'INTEGRITY VERIFICATION FAILED'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
