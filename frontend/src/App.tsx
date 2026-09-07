import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TopSystemBar } from './components/layout/TopSystemBar';
import { SidebarNav } from './components/layout/SidebarNav';
import { BottomStatusBar } from './components/layout/BottomStatusBar';
import { PrimaryVideoPanel } from './components/console/PrimaryVideoPanel';
import { ActiveSecurityEventBanner } from './components/console/ActiveSecurityEventBanner';
import { IntelligenceCards } from './components/console/IntelligenceCards';
import { EventTimeline } from './components/console/EventTimeline';
import { WhyThisEvent } from './components/console/WhyThisEvent';
import { EvidencePackagePreview } from './components/console/EvidencePackagePreview';
import { AddCameraModal } from './components/console/AddCameraModal';
import { ForensicEvidenceModal } from './components/console/ForensicEvidenceModal';

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
} from './services/api';

import { TelemetryWebSocket } from './services/websocket';

export const App: React.FC = () => {
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

  // 1. Initial Load: Cameras & Events
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

  // 2. Load Calibration for selected camera
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

  // 3. Connect to Real-Time Telemetry WebSocket
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

  // 4. Automatically fetch evidence package whenever selectedEvent changes
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

  // 5. Handle Camera Connection Callback
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

  // 6. Handle Camera Disconnect
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

  // 7. Handle Event Acknowledge
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
      {/* 1. Top Continuous Command System Bar */}
      <TopSystemBar
        isLiveMode={wsStatus === 'CONNECTED'}
        analysisStatus={telemetry.analysis_status}
        camera={selectedCam}
        cameraTelemetry={telemetry.camera}
        streamHealth={telemetry.stream_health}
        environment={telemetry.environment}
        fps={telemetry.fps}
        systemHealth={wsStatus === 'CONNECTED' ? 'HEALTHY' : 'RECONNECTING'}
      />

      {/* 2. Main Dashboard Layout (Left Nav + Central Deck) */}
      <main className="dashboard-layout">
        {/* Left Sidebar Navigation & Context */}
        <SidebarNav
          cameras={cameras}
          selectedCameraId={selectedCameraId}
          onSelectCamera={setSelectedCameraId}
          onOpenAddCamera={() => setIsAddCameraModalOpen(true)}
          onDisconnectCamera={handleDisconnectCamera}
          events={events}
        />

        {/* Central Operations Area */}
        <section className="main-console-deck">
          {/* Upper Deck: Live Video Feed (Left) + Active Security Event & 6-Card Intelligence Grid (Right) */}
          <div className="upper-command-deck">
            {/* Live Video Panel */}
            <PrimaryVideoPanel
              cameraId={selectedCameraId}
              cameraName={selectedCam?.name || 'No Active Camera'}
              fps={telemetry.fps}
              environment={telemetry.environment}
              tracks={telemetry.tracks}
              spatialStates={telemetry.spatial_states}
              behaviors={telemetry.behavior_primitives}
              activeEvents={telemetry.active_events}
              cameraTelemetry={telemetry.camera}
              streamHealth={telemetry.stream_health}
              analysisStatus={telemetry.analysis_status}
              onOpenAddCamera={() => setIsAddCameraModalOpen(true)}
            />

            {/* Right Deck: Active Alert Banner + 6 Intelligence Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <ActiveSecurityEventBanner
                event={activeAlertEvent}
                onSelectEvent={handleSelectEvent}
                onAcknowledge={handleAcknowledge}
                onInspectEvidence={handleInspectEvidence}
              />

              <IntelligenceCards
                environment={telemetry.environment}
                tracks={telemetry.tracks}
                selectedTrack={telemetry.tracks.length > 0 ? telemetry.tracks[0] : null}
                spatialStates={telemetry.spatial_states}
                behaviors={telemetry.behavior_primitives}
                activeEvent={telemetry.active_events[0] || selectedEvent}
              />
            </div>
          </div>

          {/* Lower Operations Area: Event Timeline (Left) + Why This Event (Center) + Evidence Package (Right) */}
          <div className="lower-operations-deck">
            <EventTimeline
              events={events}
              selectedEvent={selectedEvent}
              onSelectEvent={handleSelectEvent}
              onInspectEvidence={handleInspectEvidence}
            />

            <WhyThisEvent
              event={selectedEvent}
              onAcknowledge={handleAcknowledge}
              onInspectEvidence={handleInspectEvidence}
            />

            <EvidencePackagePreview
              evidencePackage={evidencePackage}
              event={selectedEvent}
              onInspectEvidence={handleInspectEvidence}
            />
          </div>
        </section>
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
