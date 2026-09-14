import React from 'react';
import { PrimaryVideoPanel } from '../console/PrimaryVideoPanel';
import { ActiveSecurityEventBanner } from '../console/ActiveSecurityEventBanner';
import { IntelligenceCards } from '../console/IntelligenceCards';
import { EventTimeline } from '../console/EventTimeline';
import { WhyThisEvent } from '../console/WhyThisEvent';
import { EvidencePackagePreview } from '../console/EvidencePackagePreview';
import { CameraInfo, EventRecord, EvidencePackage, TelemetryPacket } from '../../types';

interface LiveSurveillanceViewProps {
  telemetry: TelemetryPacket;
  selectedCameraId: string;
  selectedCam?: CameraInfo;
  activeAlertEvent: EventRecord | null;
  selectedEvent: EventRecord | null;
  events: EventRecord[];
  evidencePackage: EvidencePackage | null;
  onSelectEvent: (ev: EventRecord) => void;
  onAcknowledge: (eventId: string) => void;
  onInspectEvidence: (ev?: EventRecord | null) => void;
  onOpenAddCamera: () => void;
}

export const LiveSurveillanceView: React.FC<LiveSurveillanceViewProps> = ({
  telemetry,
  selectedCameraId,
  selectedCam,
  activeAlertEvent,
  selectedEvent,
  events,
  evidencePackage,
  onSelectEvent,
  onAcknowledge,
  onInspectEvidence,
  onOpenAddCamera,
}) => {
  return (
    <section className="main-console-deck" style={{ display: 'flex', flexDirection: 'column', gap: '10px', height: '100%', overflowY: 'auto' }}>
      {/* Upper Deck: Live Video Feed (Left) + Active Alert & 6-Card Intelligence Grid (Right) */}
      <div className="upper-command-deck">
        <PrimaryVideoPanel
          cameraId={selectedCameraId}
          cameraName={selectedCam?.name || 'Sector B-07 Border Camera'}
          fps={telemetry.fps}
          environment={telemetry.environment}
          tracks={telemetry.tracks}
          spatialStates={telemetry.spatial_states}
          behaviors={telemetry.behavior_primitives}
          activeEvents={telemetry.active_events}
          cameraTelemetry={telemetry.camera}
          streamHealth={telemetry.stream_health}
          analysisStatus={telemetry.analysis_status}
          onOpenAddCamera={onOpenAddCamera}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <ActiveSecurityEventBanner
            event={activeAlertEvent}
            onSelectEvent={onSelectEvent}
            onAcknowledge={onAcknowledge}
            onInspectEvidence={onInspectEvidence}
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
          onSelectEvent={onSelectEvent}
          onInspectEvidence={onInspectEvidence}
        />

        <WhyThisEvent
          event={selectedEvent}
          onAcknowledge={onAcknowledge}
          onInspectEvidence={onInspectEvidence}
        />

        <EvidencePackagePreview
          evidencePackage={evidencePackage}
          event={selectedEvent}
          onInspectEvidence={onInspectEvidence}
        />
      </div>
    </section>
  );
};
