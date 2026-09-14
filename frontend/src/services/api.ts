/**
 * IBVAP Operator Console REST API Client
 * 
 * Supports centralized remote EC2 backend connectivity and local development fallback.
 */

import {
  CameraInfo,
  CameraCalibration,
  EventRecord,
  EvidencePackage,
  DemonstrationScenario,
} from '../types';
import { getApiUrl, API_KEY } from '../config';

const API_BASE = '/api/v1';

/**
 * Builds request headers with prototype API Key authentication if configured.
 */
function authHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extraHeaders };
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
    headers['Authorization'] = `Bearer ${API_KEY}`;
  }
  return headers;
}

/**
 * Appends prototype API key query param for media endpoints loaded by browser <img> / <video> tags.
 */
function withAuthQuery(url: string): string {
  if (!API_KEY) return url;
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}api_key=${encodeURIComponent(API_KEY)}`;
}

/**
 * Fast production probe checking if the AI backend is reachable.
 */
export async function checkBackendHealth(): Promise<{
  ok: boolean;
  status: string;
  database_status?: string;
  app_name?: string;
}> {
  try {
    const res = await fetch(getApiUrl('/health?check_db=false'), {
      headers: authHeaders(),
    });
    if (!res.ok) return { ok: false, status: `HTTP ${res.status}` };
    const data = await res.json();
    return {
      ok: data.status === 'ok',
      status: data.status,
      database_status: data.database_status,
      app_name: data.app_name,
    };
  } catch (err: any) {
    return { ok: false, status: err?.message || 'UNREACHABLE' };
  }
}

export async function fetchCameras(): Promise<CameraInfo[]> {
  const res = await fetch(getApiUrl(`${API_BASE}/cameras`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch cameras: ${res.statusText}`);
  return res.json();
}

export async function connectCamera(params: {
  camera_id: string;
  name: string;
  rtsp_url?: string;
  video_file_path?: string;
  sector_id?: string;
  sector_name?: string;
  device?: string;
}): Promise<{ status: string; message: string; camera: CameraInfo }> {
  const payload: any = { ...params };
  if (params.rtsp_url && !params.video_file_path && (params.rtsp_url.endsWith('.mp4') || !params.rtsp_url.startsWith('rtsp://'))) {
    payload.video_file_path = params.rtsp_url;
    delete payload.rtsp_url;
  }

  const res = await fetch(getApiUrl(`${API_BASE}/cameras/connect`), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to connect camera');
  }
  return res.json();
}

export async function disconnectCamera(cameraId: string): Promise<any> {
  const res = await fetch(getApiUrl(`${API_BASE}/cameras/${cameraId}/disconnect`), {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to disconnect camera ${cameraId}`);
  return res.json();
}

export async function deleteCamera(cameraId: string): Promise<any> {
  const res = await fetch(getApiUrl(`${API_BASE}/cameras/${cameraId}`), {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to remove camera ${cameraId}`);
  return res.json();
}

export async function fetchCameraCalibration(cameraId: string): Promise<CameraCalibration> {
  const res = await fetch(getApiUrl(`${API_BASE}/cameras/${cameraId}/calibration`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch calibration for ${cameraId}`);
  return res.json();
}

export async function fetchEvents(params?: {
  cameraId?: string;
  priority?: string;
  limit?: number;
}): Promise<EventRecord[]> {
  const query = new URLSearchParams();
  if (params?.cameraId) query.set('camera_id', params.cameraId);
  if (params?.priority) query.set('priority', params.priority);
  if (params?.limit) query.set('limit', String(params.limit));

  const res = await fetch(getApiUrl(`${API_BASE}/events?${query.toString()}`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch events: ${res.statusText}`);
  return res.json();
}

export async function fetchEvent(eventId: string): Promise<EventRecord> {
  const res = await fetch(getApiUrl(`${API_BASE}/events/${eventId}`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch event ${eventId}`);
  return res.json();
}

export async function fetchEventEvidence(eventId: string): Promise<EvidencePackage> {
  const res = await fetch(getApiUrl(`${API_BASE}/events/${eventId}/evidence`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch evidence for event ${eventId}`);
  return res.json();
}

export async function verifyEvidenceIntegrity(evidenceId: string): Promise<any> {
  const res = await fetch(getApiUrl(`${API_BASE}/evidence/${evidenceId}/verify`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to verify evidence ${evidenceId}`);
  return res.json();
}

export async function acknowledgeEvent(eventId: string, operatorName: string = 'Operator'): Promise<any> {
  const res = await fetch(getApiUrl(`${API_BASE}/events/${eventId}/acknowledge`), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ acknowledged_by: operatorName }),
  });
  if (!res.ok) throw new Error(`Failed to acknowledge event ${eventId}`);
  return res.json();
}

export async function fetchScenarios(): Promise<DemonstrationScenario[]> {
  const res = await fetch(getApiUrl(`${API_BASE}/scenarios`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch scenarios`);
  return res.json();
}

export async function runScenario(scenarioId: string, speedFactor: number = 1.0): Promise<any> {
  const res = await fetch(getApiUrl(`${API_BASE}/scenarios/${scenarioId}/run`), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ speed_factor: speedFactor }),
  });
  if (!res.ok) throw new Error(`Failed to run scenario ${scenarioId}`);
  return res.json();
}

export function getEvidenceFileUrl(evidenceId: string): string {
  return withAuthQuery(getApiUrl(`${API_BASE}/evidence/${evidenceId}/file`));
}

export function getStreamUrl(cameraId: string): string {
  return withAuthQuery(getApiUrl(`${API_BASE}/streams/${cameraId}/live`));
}

export async function uploadAnalysisVideo(
  file: File,
  cameraId: string = 'DEMO-CAM-01',
  onProgress?: (percent: number) => void
): Promise<{
  status: string;
  file_name: string;
  video_path: string;
  file_size_bytes: number;
  camera_id: string;
  message: string;
}> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('camera_id', cameraId);

    xhr.open('POST', getApiUrl(`${API_BASE}/cameras/upload`));
    if (API_KEY) {
      xhr.setRequestHeader('X-API-Key', API_KEY);
      xhr.setRequestHeader('Authorization', `Bearer ${API_KEY}`);
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100);
          onProgress(pct);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          resolve({
            status: 'READY TO ANALYZE',
            file_name: file.name,
            video_path: file.name,
            file_size_bytes: file.size,
            camera_id: cameraId,
            message: 'Uploaded',
          });
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || 'Upload failed'));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => reject(new Error('Network error during video upload'));
    xhr.send(formData);
  });
}

export async function runAnalysis(params: {
  camera_id: string;
  video_file_path: string;
  device?: string;
}): Promise<any> {
  const res = await fetch(getApiUrl(`${API_BASE}/cameras/run-analysis`), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to start analysis');
  }
  return res.json();
}

export async function stopAnalysis(cameraId: string): Promise<any> {
  const res = await fetch(getApiUrl(`${API_BASE}/cameras/stop-analysis`), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ camera_id: cameraId }),
  });
  if (!res.ok) throw new Error(`Failed to stop analysis for ${cameraId}`);
  return res.json();
}

export async function fetchAnalysisStatus(cameraId: string): Promise<{
  camera_id: string;
  status: 'IDLE' | 'READY' | 'UPLOADING' | 'READY TO ANALYZE' | 'STARTING' | 'ANALYZING' | 'EVENT_DETECTED' | 'COMPLETED' | 'ERROR';
  session_id?: string;
  file_name?: string;
  video_path?: string;
  is_running: boolean;
}> {
  const res = await fetch(getApiUrl(`${API_BASE}/cameras/${cameraId}/analysis-status`), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch analysis status`);
  return res.json();
}
