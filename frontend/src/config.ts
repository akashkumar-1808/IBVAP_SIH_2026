/**
 * Centralized Environment Configuration for IBVAP Operator Console.
 * 
 * Supports both split-deployment (Render React Frontend -> AWS EC2 Backend)
 * and unified local development (Vite dev server / FastAPI static mount).
 */

function cleanUrl(url?: string): string {
  if (!url) return '';
  return url.trim().replace(/\/+$/, '');
}

// 1. Centralized API and WebSocket Base URLs from Vite Environment
export const API_BASE_URL = cleanUrl(import.meta.env.VITE_API_BASE_URL);
export const WS_BASE_URL = cleanUrl(import.meta.env.VITE_WS_BASE_URL);

/**
 * Prototype API Key for browser-to-backend access gating.
 * 
 * IMPORTANT SECURITY NOTE:
 * Any VITE_* variable compiled into client-side code is visible in the evaluator's browser.
 * This prototype key is used strictly as a lightweight access gate between the Render-hosted
 * frontend and AWS EC2 backend. It is never reused for Supabase or backend secrets.
 */
export const API_KEY = (import.meta.env.VITE_API_KEY || '').trim();

/**
 * Resolves an HTTP API path against the configured backend base URL.
 * Falls back to current window origin if VITE_API_BASE_URL is unconfigured.
 */
export function getApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (API_BASE_URL) {
    return `${API_BASE_URL}${normalizedPath}`;
  }
  return normalizedPath;
}

/**
 * Resolves a WebSocket path against the configured backend WebSocket URL.
 * Automatic fallback hierarchy:
 * 1. VITE_WS_BASE_URL (e.g., wss://api.ibvap.example.com)
 * 2. Protocol-converted VITE_API_BASE_URL (https:// -> wss://, http:// -> ws://)
 * 3. window.location (wss:// or ws:// on current host)
 */
export function getWsUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  
  // 1. Explicit WS Base URL configured
  if (WS_BASE_URL) {
    return `${WS_BASE_URL}${normalizedPath}`;
  }

  // 2. Derive from API Base URL if available
  if (API_BASE_URL) {
    const wsPrefix = API_BASE_URL.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://');
    return `${wsPrefix}${normalizedPath}`;
  }

  // 3. Fallback to current browser window location
  const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = typeof window !== 'undefined' && window.location.host ? window.location.host : '127.0.0.1:8000';
  return `${protocol}//${host}${normalizedPath}`;
}
