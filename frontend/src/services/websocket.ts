/**
 * Reconnecting WebSocket Telemetry Client for IBVAP.
 * 
 * Supports remote AWS EC2 deployment via centralized getWsUrl(), automatic
 * exponential reconnection backoff, and prototype query-token authentication.
 */

import { TelemetryPacket } from '../types';
import { getWsUrl, API_KEY } from '../config';

export class TelemetryWebSocket {
  private ws: WebSocket | null = null;
  private path: string;
  private onPacketCallback: (packet: TelemetryPacket) => void;
  private onStatusCallback: (status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING') => void;
  private isManualClose = false;
  private reconnectTimeout: number | null = null;
  private reconnectAttempts = 0;
  private readonly maxBackoffMs = 10000;
  private readonly baseBackoffMs = 2000;

  constructor(
    path: string,
    onPacket: (packet: TelemetryPacket) => void,
    onStatus: (status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING') => void
  ) {
    this.path = path;
    this.onPacketCallback = onPacket;
    this.onStatusCallback = onStatus;
  }

  public connect(): void {
    this.isManualClose = false;
    this.onStatusCallback('RECONNECTING');

    // Resolve URL through centralized remote backend configuration
    let wsUrl = this.path.startsWith('ws://') || this.path.startsWith('wss://')
      ? this.path
      : getWsUrl(this.path);

    // Attach prototype API key if configured
    if (API_KEY && !wsUrl.includes('api_key=')) {
      const sep = wsUrl.includes('?') ? '&' : '?';
      wsUrl = `${wsUrl}${sep}api_key=${encodeURIComponent(API_KEY)}`;
    }

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.onStatusCallback('CONNECTED');
      };

      this.ws.onmessage = (event) => {
        try {
          const packet: TelemetryPacket = JSON.parse(event.data);
          this.onPacketCallback(packet);
        } catch (e) {
          console.warn('[TelemetryWS] Failed to parse packet:', e);
        }
      };

      this.ws.onclose = () => {
        this.onStatusCallback('DISCONNECTED');
        if (!this.isManualClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch (e) {
      this.onStatusCallback('DISCONNECTED');
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.reconnectAttempts++;
    // Exponential backoff with jitter: 2s -> 4s -> 8s -> 10s max
    const delay = Math.min(this.baseBackoffMs * Math.pow(1.5, this.reconnectAttempts - 1), this.maxBackoffMs);
    this.reconnectTimeout = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  public disconnect(): void {
    this.isManualClose = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.onStatusCallback('DISCONNECTED');
  }
}
