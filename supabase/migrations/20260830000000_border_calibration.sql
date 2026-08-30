-- ====================================================================
-- IBVAP Border Calibration Schema Migration
-- Target: Supabase PostgreSQL (PostgreSQL 15+)
-- Version: 20260830000000_border_calibration
-- Architecture Decision: DEC-0006
-- ====================================================================

-- 1. Border Sections Table (World-Space Border Definition)
CREATE TABLE IF NOT EXISTS public.border_sections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    coordinate_reference TEXT NOT NULL DEFAULT 'local_cartesian',
    points JSONB NOT NULL,
    permitted_side_normal JSONB NOT NULL DEFAULT '[0, 1]'::jsonb,
    warning_buffer_distance REAL NOT NULL DEFAULT 5.0,
    terrain_mode TEXT NOT NULL DEFAULT 'planar_ground',
    version TEXT NOT NULL DEFAULT '1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Camera Registrations Table (Camera ↔ Border Section Mapping)
CREATE TABLE IF NOT EXISTS public.camera_registrations (
    camera_id TEXT PRIMARY KEY REFERENCES public.cameras(id) ON DELETE CASCADE,
    visible_border_sections JSONB NOT NULL DEFAULT '[]'::jsonb,
    calibration_profile_id TEXT,
    calibration_version TEXT,
    calibration_status TEXT NOT NULL DEFAULT 'uncalibrated',
    height_meters REAL,
    orientation_deg REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_camera_registrations_status
    ON public.camera_registrations(calibration_status);

-- 3. Camera Calibrations Table (World-to-Image Correspondences & Transform Metadata)
CREATE TABLE IF NOT EXISTS public.camera_calibrations (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    camera_id TEXT NOT NULL REFERENCES public.cameras(id) ON DELETE CASCADE,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    correspondences JSONB NOT NULL,
    calibration_model TEXT NOT NULL DEFAULT 'planar_homography',
    calibration_version TEXT NOT NULL DEFAULT '1.0',
    reprojection_error REAL,
    distortion_coefficients JSONB,
    status TEXT NOT NULL DEFAULT 'uncalibrated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_camera_calibrations_camera_id
    ON public.camera_calibrations(camera_id);
CREATE INDEX IF NOT EXISTS idx_camera_calibrations_status
    ON public.camera_calibrations(status);

-- 4. Row Level Security
ALTER TABLE public.border_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.camera_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.camera_calibrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on border_sections"
    ON public.border_sections FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access on camera_registrations"
    ON public.camera_registrations FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access on camera_calibrations"
    ON public.camera_calibrations FOR ALL TO service_role USING (true);

CREATE POLICY "Anon read border_sections"
    ON public.border_sections FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Anon read camera_registrations"
    ON public.camera_registrations FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Anon read camera_calibrations"
    ON public.camera_calibrations FOR SELECT TO anon, authenticated USING (true);
