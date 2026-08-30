"""
Cryptographic Evidence Sealing and Tamper-Verification Engine.

Computes immutable SHA-256 checksums of raw snapshots, video clips, and audit manifests
to guarantee non-repudiation and forensic chain of custody.

Architecture Decision: DEC-0008
"""

import os
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple

from .schemas import ArtifactChecksum, EvidenceManifest
from .exceptions import IntegrityVerificationError


class EvidenceHasher:
    """Computes and verifies cryptographic SHA-256 hashes for evidence artifacts."""

    @staticmethod
    def hash_file(file_path: str) -> str:
        """Computes hex-encoded SHA-256 checksum of a file on disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot hash missing file: '{file_path}'")

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """Computes hex-encoded SHA-256 checksum of in-memory bytes."""
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def create_artifact_checksum(cls, file_path: str, file_type: str) -> ArtifactChecksum:
        """Creates an ArtifactChecksum record for a specific file."""
        sha256 = cls.hash_file(file_path)
        size = os.path.getsize(file_path)
        name = os.path.basename(file_path)
        return ArtifactChecksum(
            file_name=name,
            file_type=file_type,
            file_size_bytes=size,
            sha256_hash=sha256,
        )

    @classmethod
    def verify_package_integrity(cls, manifest_path: str) -> Tuple[bool, List[str]]:
        """
        Verifies that all artifacts in an evidence package match their sealed SHA-256 checksums.

        Returns:
            (is_valid, list_of_errors)
        """
        if not os.path.exists(manifest_path):
            return False, [f"Manifest file missing: '{manifest_path}'"]

        package_dir = os.path.dirname(manifest_path)

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            manifest = EvidenceManifest.model_validate(data)
        except Exception as exc:
            return False, [f"Failed to parse manifest JSON: {exc}"]

        errors = []
        for art in manifest.artifacts:
            art_path = os.path.join(package_dir, art.file_name)
            if not os.path.exists(art_path):
                errors.append(f"Missing artifact file: '{art.file_name}'")
                continue

            current_hash = cls.hash_file(art_path)
            if current_hash != art.sha256_hash:
                errors.append(
                    f"TAMPER DETECTED in '{art.file_name}': "
                    f"manifest={art.sha256_hash[:12]}... current={current_hash[:12]}..."
                )

        is_valid = len(errors) == 0
        return is_valid, errors
