import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TopSystemBar } from './components/layout/TopSystemBar';
import { SidebarNav, NavTab } from './components/layout/SidebarNav';
import { BottomStatusBar } from './components/layout/BottomStatusBar';
import { AddCameraModal } from './components/console/AddCameraModal';
import { ForensicEvidenceModal } from './components/console/ForensicEvidenceModal';

import { OverviewView } from './components/views/OverviewView';
import { LiveSurveillanceView } from './components/views/LiveSurveillanceView';
import { BorderIntelligenceView } from './components/views/BorderIntelligenceView';
import { IncidentsView } from './components/views/IncidentsView';
import { TargetTrackingView } from './components/views/TargetTrackingView';
import { EvidenceAuditView } from './components/views/EvidenceAuditView';
import { AiAnalyticsView } from './components/views/AiAnalyticsView';
import { ReportsView } from './components/views/ReportsView';

import {
  CameraInfo,
  CameraCalibration,
  EventRecord,
  EvidencePackage,
  TelemetryPacket,
} from './types';

import {
  fetchCameras,
  fetchCameraCalibration,
  fetchEvents,
  fetchEventEvidence,
  acknowledgeEvent,
  disconnectCamera,
  checkBackendHealth,
} from './services/api';

import { TelemetryWebSocket } from './services/websocket';

export const App: React.FC = () => {
  // 1. Operational Views Navigation State (Default to Overview - Section 5)
  const [activeNav, setActiveNav] = useState<NavTab>('OVERVIEW');

  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('DEMO-CAM-01');
  const [, setCalibration] = useState<CameraCalibration | null>(null);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<EventRecord | null>(null);
  const [evidencePackage, setEvidencePackage] = useState<EvidencePackage | null>(null);
  const [isAddCameraModalOpen, setIsAddCameraModalOpen] = useState<boolean>(false);
  const [inspectedEvent, setInspectedEvent] = useState<EventRecord | null>(null);
  const [isEvidenceModalOpen, setIsEvidenceModalOpen] = useState<boolean>(false);

  // Deduplication ref for active event selection
  const lastAlertedEventIdRef = useRef<string | null>(null);

  // Real-time live telemetry state from WebSocket
  const [telemetry, setTelemetry] = useState<TelemetryPacket>({
    camera_id: '',
    timestamp_utc: new Date().toISOString(),
    fps: 0.0,
    is_calibrated: true,
    tracks: [],
    spatial_states: [],
    behavior_primitives: [],
    active_events: [],
  });

  const [wsStatus, setWsStatus] = useState<'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING'>('RECONNECTING');
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);

  // Periodic Backend Health Probe
  useEffect(() => {
    let isMounted = true;
    const probe = async () => {
      const res = await checkBackendHealth();
      if (isMounted) {
        setIsBackendOnline(res.ok);
      }
    };
    probe();
    const timer = setInterval(probe, 5000);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, []);

  // Initial Load: Cameras & Events
  useEffect(() => {
    fetchCameras()
      .then((cams) => {
        setCameras(cams);
        if (cams.length > 0) setSelectedCameraId(cams[0].camera_id);
      })
      .catch((err) => console.warn('Failed to load cameras:', err));

    fetchEvents()
      .then((evList) => {
        setEvents(evList);
        if (evList.length > 0) {
          setSelectedEvent(evList[0]);
          fetchEventEvidence(evList[0].id)
            .then(setEvidencePackage)
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

  // Load Calibration for selected camera
  useEffect(() => {
    if (!selectedCameraId) {
      setCalibration(null);
      return;
    }
    fetchCameraCalibration(selectedCameraId)
      .then(setCalibration)
      .catch(() => setCalibration(null));
  }, [selectedCameraId]);

  // Track session ID to reset when a new analysis starts
  const currentSessionIdRef = useRef<string | null>(null);

  // Connect to Real-Time Telemetry WebSocket
  const handleTelemetryPacket = useCallback((packet: TelemetryPacket) => {
    // Check if new analysis session began
    if (packet.session_id && currentSessionIdRef.current && packet.session_id !== currentSessionIdRef.current) {
      currentSessionIdRef.current = packet.session_id;
      lastAlertedEventIdRef.current = null;
    } else if (packet.session_id && !currentSessionIdRef.current) {
      currentSessionIdRef.current = packet.session_id;
    }

    setTelemetry((prev) => {
      // When analysis finishes, keep all previous tracks/spatial/behavior/events preserved
      if (packet.analysis_status === 'COMPLETED') {
        return {
          ...prev,
          ...packet,
          tracks: packet.tracks && packet.tracks.length > 0 ? packet.tracks : prev.tracks,
          spatial_states: packet.spatial_states && packet.spatial_states.length > 0 ? packet.spatial_states : prev.spatial_states,
          behavior_primitives: packet.behavior_primitives && packet.behavior_primitives.length > 0 ? packet.behavior_primitives : prev.behavior_primitives,
          active_events: packet.active_events && packet.active_events.length > 0 ? packet.active_events : prev.active_events,
          environment: packet.environment || prev.environment,
          camera: packet.camera || prev.camera,
        };
      }
      return packet;
    });

    if (packet.active_events && packet.active_events.length > 0) {
      setEvents((prev) => {
        const updated = [...prev];
        packet.active_events.forEach((newEv) => {
          const idx = updated.findIndex((e) => e.id === newEv.id);
          if (idx >= 0) updated[idx] = newEv;
          else updated.unshift(newEv);
        });
        return updated;
      });

      // Deduplicated selection for new high/critical event
      const highEv = packet.active_events.find(
        (e) => e.priority === 'CRITICAL' || e.priority === 'HIGH'
      );
      if (highEv && highEv.id !== lastAlertedEventIdRef.current) {
        lastAlertedEventIdRef.current = highEv.id;
        setSelectedEvent(highEv);
      }
    }
  }, []);

  useEffect(() => {
    const ws = new TelemetryWebSocket(
      '/api/v1/ws/telemetry',
      handleTelemetryPacket,
      setWsStatus
    );
    ws.connect();
    return () => ws.disconnect();
  }, [handleTelemetryPacket]);

  // Automatically fetch evidence package whenever selectedEvent changes
  useEffect(() => {
    if (selectedEvent?.id) {
      fetchEventEvidence(selectedEvent.id)
        .then(setEvidencePackage)
        .catch(() => setEvidencePackage(null));
    } else {
      setEvidencePackage(null);
    }
  }, [selectedEvent?.id]);

  const handleSelectEvent = (ev: EventRecord) => {
    setSelectedEvent(ev);
  };

  const handleInspectEvidence = (ev?: EventRecord | null) => {
    const target = ev || selectedEvent || activeAlertEvent;
    if (target) {
      setInspectedEvent(target);
      setSelectedEvent(target);
      setIsEvidenceModalOpen(true);
    }
  };

  // Handle Camera Connection Callback
  const handleCameraConnected = (newCamera: CameraInfo) => {
    setCameras((prev) => {
      const idx = prev.findIndex((c) => c.camera_id === newCamera.camera_id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = newCamera;
        return updated;
      }
      return [...prev, newCamera];
    });
    setSelectedCameraId(newCamera.camera_id);
  };

  // Handle Camera Disconnect
  const handleDisconnectCamera = async (camId: string) => {
    try {
      await disconnectCamera(camId);
      setCameras((prev) => prev.filter((c) => c.camera_id !== camId));
      if (selectedCameraId === camId) {
        const remaining = cameras.filter((c) => c.camera_id !== camId);
        setSelectedCameraId(remaining.length > 0 ? remaining[0].camera_id : '');
      }
    } catch (err) {
      console.warn('Failed to disconnect camera:', err);
    }
  };

  // Handle Event Acknowledge
  const handleAcknowledge = async (eventId: string) => {
    try {
      await acknowledgeEvent(eventId, 'Operator');
      setEvents((prev) =>
        prev.map((e) => (e.id === eventId ? { ...e, status: 'RESOLVED' as const } : e))
      );
    } catch (err) {
      console.warn('Failed to acknowledge event:', err);
    }
  };

  const selectedCam = cameras.find((c) => c.camera_id === selectedCameraId);
  const activeAlertEvent = telemetry.active_events.find(
    (e) => e.priority === 'CRITICAL' || e.priority === 'HIGH'
  ) || (selectedEvent && (selectedEvent.priority === 'CRITICAL' || selectedEvent.priority === 'HIGH') ? selectedEvent : null);

  return (
    <div className="app-container">
      {/* 1. Top Continuous Command System Bar (Persistent Status Strip) */}
      <TopSystemBar
        isLiveMode={wsStatus === 'CONNECTED'}
        analysisStatus={telemetry.analysis_status}
        camera={selectedCam}
        cameraTelemetry={telemetry.camera}
        streamHealth={telemetry.stream_health}
        environment={telemetry.environment}
        fps={telemetry.fps}
        systemHealth={wsStatus === 'CONNECTED' ? 'HEALTHY' : 'RECONNECTING'}
        isBackendOnline={isBackendOnline}
        wsStatus={wsStatus}
        hasActiveSecurityEvent={Boolean(activeAlertEvent)}
        activeEvidenceCount={evidencePackage ? 1 : events.length}
      />

      {/* 2. Main Dashboard Layout (Left Nav + Dynamic Central View Deck) */}
      <main className="dashboard-layout">
        {/* Left Sidebar Navigation with 8 Primary Operational Views */}
        <SidebarNav
          activeNav={activeNav}
          onSelectNav={setActiveNav}
          cameras={cameras}
          selectedCameraId={selectedCameraId}
          onSelectCamera={setSelectedCameraId}
          onOpenAddCamera={() => setIsAddCameraModalOpen(true)}
          onDisconnectCamera={handleDisconnectCamera}
          events={events}
          activeTracksCount={telemetry.tracks.length}
          evidenceCount={evidencePackage ? 1 : events.length}
          isBackendOnline={isBackendOnline}
        />

        {/* Central Operations Deck Swapped by activeNav */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {activeNav === 'OVERVIEW' && (
            <OverviewView
              telemetry={telemetry}
              events={events}
              evidencePackage={evidencePackage}
              camera={selectedCam || null}
              isBackendOnline={isBackendOnline}
              onNavigate={setActiveNav}
              onSelectEvent={handleSelectEvent}
              onInspectEvidence={handleInspectEvidence}
            />
          )}

          {activeNav === 'LIVE_SURVEILLANCE' && (
            <LiveSurveillanceView
              telemetry={telemetry}
              selectedCameraId={selectedCameraId}
              selectedCam={selectedCam}
              activeAlertEvent={activeAlertEvent}
              selectedEvent={selectedEvent}
              events={events}
              evidencePackage={evidencePackage}
              onSelectEvent={handleSelectEvent}
              onAcknowledge={handleAcknowledge}
              onInspectEvidence={handleInspectEvidence}
              onOpenAddCamera={() => setIsAddCameraModalOpen(true)}
            />
          )}

          {activeNav === 'BORDER_INTELLIGENCE' && (
            <BorderIntelligenceView
              camera={selectedCam || null}
              activeEvents={events}
              activeTracks={telemetry.tracks}
              streamHealth={telemetry.stream_health}
              environment={telemetry.environment}
              isBackendOnline={isBackendOnline}
              onNavigate={setActiveNav}
            />
          )}

          {activeNav === 'INCIDENTS' && (
            <IncidentsView
              events={events}
              selectedEvent={selectedEvent}
              evidencePackage={evidencePackage}
              environment={telemetry.environment}
              streamHealth={telemetry.stream_health}
              onSelectEvent={handleSelectEvent}
              onAcknowledge={handleAcknowledge}
              onInspectEvidence={handleInspectEvidence}
            />
          )}

          {activeNav === 'TARGET_TRACKING' && (
            <TargetTrackingView
              tracks={telemetry.tracks}
              spatialStates={telemetry.spatial_states}
              behaviors={telemetry.behavior_primitives}
              camera={selectedCam || null}
              fps={telemetry.fps}
            />
          )}

          {activeNav === 'EVIDENCE_AUDIT' && (
            <EvidenceAuditView
              events={events}
              selectedEvent={selectedEvent}
              evidencePackage={evidencePackage}
              onSelectEvent={handleSelectEvent}
              onInspectFullModal={handleInspectEvidence}
            />
          )}

          {activeNav === 'AI_ANALYTICS' && (
            <AiAnalyticsView
              telemetry={telemetry}
              events={events}
              streamHealth={telemetry.stream_health}
              environment={telemetry.environment}
            />
          )}

          {activeNav === 'REPORTS' && (
            <ReportsView
              events={events}
              camera={selectedCam || null}
              streamHealth={telemetry.stream_health}
              environment={telemetry.environment}
              evidencePackage={evidencePackage}
            />
          )}
        </div>
      </main>

      {/* 3. Bottom Operational Status Bar */}
      <BottomStatusBar />

      {/* Connect Camera Modal */}
      <AddCameraModal
        isOpen={isAddCameraModalOpen}
        onClose={() => setIsAddCameraModalOpen(false)}
        onCameraConnected={handleCameraConnected}
      />

      {/* Full Forensic Evidence Dossier & Footages Modal */}
      <ForensicEvidenceModal
        isOpen={isEvidenceModalOpen}
        onClose={() => setIsEvidenceModalOpen(false)}
        event={inspectedEvent}
        evidencePackage={inspectedEvent?.id === evidencePackage?.event_id ? evidencePackage : null}
        onAcknowledge={handleAcknowledge}
      />
    </div>
  );
};

export default App;
