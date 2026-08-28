import logging
from typing import Optional, Dict, Any
from .client import get_supabase_client
from ..config import settings

logger = logging.getLogger(__name__)


class SupabaseEvidenceStorage:
    """
    Evidence storage abstraction interacting with Supabase Storage buckets.
    Ensures safe handling of security incident snapshots, video clips, and metadata.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.EVIDENCE_STORAGE_BUCKET

    def is_available(self) -> bool:
        """Checks if Supabase client is initialized and storage service is reachable."""
        return get_supabase_client() is not None

    def ensure_bucket_exists(self, is_public: bool = False) -> bool:
        """
        Ensures the evidence bucket exists in Supabase Storage.
        Creates it with proper access policies if absent.
        """
        client = get_supabase_client()
        if not client:
            logger.warning("Cannot ensure bucket: Supabase client unavailable.")
            return False

        try:
            buckets = client.storage.list_buckets()
            existing_names = [b.name for b in buckets] if hasattr(buckets[0], "name") else [b.get("name") for b in buckets] if buckets else []
            if self.bucket_name not in existing_names:
                client.storage.create_bucket(self.bucket_name, options={"public": is_public})
                logger.info(f"Created Supabase Storage bucket: {self.bucket_name} (public={is_public})")
            return True
        except Exception as exc:
            logger.error(f"Error checking/creating storage bucket '{self.bucket_name}': {exc}")
            return False

    def upload_file(self, destination_path: str, file_bytes: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
        """
        Uploads file bytes to the evidence storage bucket at destination_path.
        Returns the stored file path on success, or None on failure.
        """
        client = get_supabase_client()
        if not client:
            logger.warning("Cannot upload file: Supabase client unavailable.")
            return None

        try:
            response = client.storage.from_(self.bucket_name).upload(
                path=destination_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            logger.info(f"Uploaded evidence file to '{self.bucket_name}/{destination_path}'")
            return destination_path
        except Exception as exc:
            logger.error(f"Failed to upload evidence to '{destination_path}': {exc}")
            return None

    def get_signed_url(self, file_path: str, expires_in_seconds: int = 3600) -> Optional[str]:
        """
        Generates a secure temporary signed URL for an evidence snapshot or clip.
        """
        client = get_supabase_client()
        if not client:
            return None

        try:
            res = client.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in_seconds,
            )
            if isinstance(res, dict):
                return res.get("signedURL") or res.get("signed_url")
            elif hasattr(res, "signed_url"):
                return res.signed_url
            return None
        except Exception as exc:
            logger.error(f"Failed to generate signed URL for '{file_path}': {exc}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """Deletes an evidence file from the bucket."""
        client = get_supabase_client()
        if not client:
            return False

        try:
            client.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as exc:
            logger.error(f"Failed to delete evidence file '{file_path}': {exc}")
            return False


# Singleton storage instance
evidence_storage = SupabaseEvidenceStorage()
