-- ====================================================================
-- IBVAP Initial Database Schema Migration
-- Target: Supabase PostgreSQL (PostgreSQL 15+)
-- Version: 20260828000000_initial_schema
-- ====================================================================

-- 1. Enable UUID Extension if not already available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Cameras Table (Registry & State)
CREATE TABLE IF NOT EXISTS public.cameras (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    stream_url TEXT NOT NULL,
    location TEXT,
    terrain_profile TEXT NOT NULL DEFAULT 'open_ground',
    fps_target INTEGER NOT NULL DEFAULT 10,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL DEFAULT 'offline',
    spatial_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_frame_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index on camera activity status
CREATE INDEX IF NOT EXISTS idx_cameras_is_active ON public.cameras(is_active);

-- 3. Spatial Zones Table
CREATE TABLE IF NOT EXISTS public.zones (
    id TEXT PRIMARY KEY,
    camera_id TEXT NOT NULL REFERENCES public.cameras(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    zone_type TEXT NOT NULL DEFAULT 'restricted',
    severity_weight REAL NOT NULL DEFAULT 1.0,
    polygon_coordinates JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zones_camera_id ON public.zones(camera_id);

-- 4. Virtual Fences Table
CREATE TABLE IF NOT EXISTS public.virtual_fences (
    id TEXT PRIMARY KEY,
    camera_id TEXT NOT NULL REFERENCES public.cameras(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_point JSONB NOT NULL,
    end_point JSONB NOT NULL,
    crossing_direction_angle REAL,
    severity_weight REAL NOT NULL DEFAULT 1.5,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fences_camera_id ON public.virtual_fences(camera_id);

-- 5. Security Events Table
CREATE TABLE IF NOT EXISTS public.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id TEXT NOT NULL REFERENCES public.cameras(id) ON DELETE CASCADE,
    timestamp_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'MEDIUM',
    risk_score REAL NOT NULL DEFAULT 0.0,
    target_class TEXT NOT NULL,
    track_id INTEGER NOT NULL,
    detection_confidence REAL NOT NULL,
    track_persistence_frames INTEGER NOT NULL DEFAULT 1,
    dwell_time_seconds REAL NOT NULL DEFAULT 0.0,
    zone_id TEXT,
    fence_id TEXT,
    environment_quality TEXT NOT NULL DEFAULT 'good',
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation_summary TEXT NOT NULL,
    uncertainty_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_snapshot_path TEXT,
    evidence_clip_path TEXT,
    is_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_camera_id ON public.events(camera_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON public.events(timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_events_priority ON public.events(priority);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON public.events(event_type);

-- 6. Model Versions & Traceability Table
CREATE TABLE IF NOT EXISTS public.model_versions (
    id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    task TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    runtime TEXT NOT NULL,
    checksum TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Audit Logs Table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action TEXT NOT NULL,
    performed_by TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON public.audit_logs(timestamp_utc DESC);

-- 8. Row Level Security (RLS) Enablement & Default Policies
ALTER TABLE public.cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.virtual_fences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Allow service_role full read/write access
CREATE POLICY "Service role full access on cameras" ON public.cameras FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access on zones" ON public.zones FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access on virtual_fences" ON public.virtual_fences FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access on events" ON public.events FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access on model_versions" ON public.model_versions FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access on audit_logs" ON public.audit_logs FOR ALL TO service_role USING (true);

-- Allow anon / authenticated read access
CREATE POLICY "Anon read cameras" ON public.cameras FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Anon read zones" ON public.zones FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Anon read fences" ON public.virtual_fences FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Anon read events" ON public.events FOR SELECT TO anon, authenticated USING (true);
