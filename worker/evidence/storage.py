"""
Local and Cloud Evidence Storage Management for IBVAP.

Manages structured local filesystem directory hierarchies and optional
asynchronous uploading to Supabase Storage.

Architecture Decision: DEC-0008
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from .schemas import EvidenceManifest, EvidencePackage
from .exceptions import StorageError
from backend.app.db.storage import evidence_storage

logger = logging.getLogger(__name__)


class EvidenceStorageManager:
    """Manages writing and retrieving packaged evidence on disk and Supabase Storage."""

    def __init__(self, root_dir: str = "storage/evidence"):
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    def get_package_dir(self, camera_id: str, event_id: str) -> str:
        """Returns the structured directory path for an evidence package."""
        pkg_dir = os.path.join(self.root_dir, camera_id, event_id)
        os.makedirs(pkg_dir, exist_ok=True)
        return pkg_dir

    def save_manifest(self, manifest: EvidenceManifest, package_dir: str) -> str:
        """Saves an EvidenceManifest to disk as manifest.json."""
        os.makedirs(package_dir, exist_ok=True)
        manifest_path = os.path.join(package_dir, "manifest.json")
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(manifest.model_dump_json(indent=2))
            return manifest_path
        except Exception as exc:
            raise StorageError(f"Failed to write manifest.json to '{manifest_path}': {exc}")

    def load_manifest(self, manifest_path: str) -> EvidenceManifest:
        """Loads and parses an EvidenceManifest from disk."""
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest not found at '{manifest_path}'")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EvidenceManifest.model_validate(data)
        except Exception as exc:
            raise StorageError(f"Failed to parse manifest at '{manifest_path}': {exc}")

    def upload_package_to_supabase(self, package: EvidencePackage) -> bool:
        """
        Uploads all artifacts in an EvidencePackage to the Supabase 'evidence' storage bucket.
        Non-blocking / resilient: returns False if Supabase is offline without crashing the worker.
        """
        if not evidence_storage.is_available():
            logger.debug("Supabase Storage client is offline. Skipping cloud upload.")
            return False

        try:
            # Ensure bucket exists
            evidence_storage.ensure_bucket_exists(is_public=False)

            manifest = package.manifest
            if not manifest:
                return False

            prefix = f"{package.camera_id}/{package.event_id}"

            for art in manifest.artifacts:
                art_path = os.path.join(package.package_dir, art.file_name)
                if os.path.exists(art_path):
                    with open(art_path, "rb") as f:
                        file_bytes = f.read()
                    dest_path = f"{prefix}/{art.file_name}"
                    evidence_storage.upload_file(
                        destination_path=dest_path,
                        file_bytes=file_bytes,
                        content_type=art.file_type,
                    )

            logger.info(f"Successfully uploaded EvidencePackage '{package.id}' to Supabase Storage at '{prefix}/'")
            return True
        except Exception as exc:
            logger.warning(f"Error uploading package '{package.id}' to Supabase Storage: {exc}")
            return False
