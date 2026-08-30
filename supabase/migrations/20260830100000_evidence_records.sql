-- ====================================================================
-- IBVAP Phase 9 Migration: Structured Evidence Records & Provenance
-- ====================================================================

CREATE TABLE IF NOT EXISTS public.evidence_records (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    camera_id TEXT NOT NULL REFERENCES public.cameras(id) ON DELETE CASCADE,
    track_id INTEGER,
    evidence_type TEXT NOT NULL, -- 'snapshot_raw', 'snapshot_annotated', 'pre_event_clip', 'incident_clip', 'manifest'
    storage_reference TEXT NOT NULL,
    source_reference TEXT,
    start_time_utc TIMESTAMPTZ,
    end_time_utc TIMESTAMPTZ,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    mime_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sealed', -- 'sealed', 'partial', 'failed', 'tampered'
    model_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_event_id ON public.evidence_records(event_id);
CREATE INDEX IF NOT EXISTS idx_evidence_camera_id ON public.evidence_records(camera_id);
CREATE INDEX IF NOT EXISTS idx_evidence_sha256 ON public.evidence_records(sha256);
CREATE INDEX IF NOT EXISTS idx_evidence_created_at ON public.evidence_records(created_at DESC);

-- Enable RLS
ALTER TABLE public.evidence_records ENABLE ROW LEVEL SECURITY;

-- Read policy for authenticated users / service role
CREATE POLICY "Allow read access on evidence_records"
    ON public.evidence_records FOR SELECT
    USING (true);

-- Insert/update policy for service role / worker
CREATE POLICY "Allow insert/update on evidence_records"
    ON public.evidence_records FOR ALL
    USING (true)
    WITH CHECK (true);
