---
title: IBVAP Operator Console
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# IBVAP — Intelligent Border Video Analytics Platform

Production prototype for AI-assisted real-time border video surveillance, threat detection, and forensic evidence packaging.

## Architecture

The system executes a real 9-stage intelligence chain:
1. **Video Ingestion Layer**: Live RTSP stream ingestion or uploaded MP4 file playback with automatic reconnection.
2. **Environment Perception**: Real-time lighting, visibility, blur, and weather quality assessment.
3. **Deep Object Detection**: Pretrained YOLOv8n model on CPU/CUDA detecting Persons, Vehicles, and Animals.
4. **False Positive Filter**: Aspect-ratio sanity, camera motion stabilization, and boundary filtering.
5. **Multi-Target Tracking**: ByteTrack persistent kinematic tracker with velocity and footprint estimation.
6. **Spatial Border Reasoning**: Calibrated planar homography projecting real-world border fences, warning buffers, and restricted zones.
7. **Behavior Engine**: Temporal behavior recognition detecting loitering, fast approach, border breaches, and crawling.
8. **Multi-Modal Fusion**: Autonomous risk engine computing confidence, priority, and human-readable explanation factors.
9. **Evidence Packaging**: Cryptographic SHA-256 sealed evidence packages containing raw snapshots, annotated forensic frames, pre/post event MP4 clips, and Supabase cloud persistence.

## Hugging Face Spaces Setup

This Space is configured using the `docker` SDK running on port `7860`.

### Optional Secrets / Configuration
To connect this Space to your Supabase project for persistent cloud evidence and event history, configure these secrets in **Space Settings > Variables and secrets**:

* `SUPABASE_URL`: Your Supabase project URL
* `SUPABASE_ANON_KEY`: Supabase anon key
* `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key

*If Supabase secrets are omitted, IBVAP operates seamlessly in local-first mode.*
