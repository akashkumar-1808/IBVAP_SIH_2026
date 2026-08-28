# Supabase PostgreSQL & Storage Setup Guide for IBVAP

This guide provides instructions for connecting and developing against the shared Supabase PostgreSQL and Storage backend for IBVAP.

---

## 1. Overview
The IBVAP backend architecture uses Supabase for:
1. **Persistent PostgreSQL Database:** Stores cameras, zones, virtual fences, events, model registry metadata, and audit logs.
2. **Supabase Storage (`evidence` bucket):** Stores security incident frame snapshots (`.jpg`) and short video clips (`.mp4`).

> **Architectural Boundary Rule:** The AI/video worker processes real-time video feeds and sends structured events/evidence to the FastAPI backend, which handles all database operations and storage interactions with Supabase. Continuous video streams and heavy ML inference do **not** run inside Supabase.

---

## 2. Environment Variables Configuration

Copy `backend/.env.example` to `backend/.env` (or `.env` in the project root):

```bash
cp backend/.env.example backend/.env
```

Set the project credentials provided by the team administrator:

```env
# Application Settings
ENVIRONMENT=development
APP_NAME=IBVAP-Backend
DEBUG=true
LOG_LEVEL=INFO
API_V1_STR=/api/v1
HOST=0.0.0.0
PORT=8000

# Supabase Credentials (Obtained from Supabase Project Dashboard -> Settings -> API)
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_ANON_KEY=<your-anon-public-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-secret-key>

# Supabase Storage Configuration
EVIDENCE_STORAGE_BUCKET=evidence
MAX_UPLOAD_SIZE_MB=50
```

> **SECURITY WARNING:**
> - Never commit `.env` files to git.
> - Never expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend or in logs.

---

## 3. Database Migration Execution

The initial schema script is located at:
`supabase/migrations/20260828000000_initial_schema.sql`

To apply the schema to your Supabase project:
1. Open the **SQL Editor** in your Supabase Dashboard.
2. Paste the contents of `supabase/migrations/20260828000000_initial_schema.sql`.
3. Click **Run**.

Tables created:
- `cameras`: Camera stream registry, location, terrain profile, and active status.
- `zones`: Spatial polygon definitions and severity weights.
- `virtual_fences`: Virtual tripwire coordinates and crossing direction angles.
- `events`: Security incidents with risk scores, reason codes, dwell times, and evidence pointers.
- `model_versions`: Traceability records for all AI detection/enhancement models.
- `audit_logs`: Operational activity logs.

---

## 4. Running the Backend & Verifying Connectivity

1. Start the FastAPI development server:
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Verify system and database health:
```bash
curl http://localhost:8000/health
```

Expected JSON response when Supabase is connected:
```json
{
  "status": "ok",
  "environment": "development",
  "app_name": "IBVAP-Backend",
  "database_status": "healthy",
  "database_message": null,
  "supabase_configured": true
}
```

If Supabase credentials are missing or the database is unreachable, the response will report `"database_status": "not_configured"` or `"unreachable"` without exposing secrets.
