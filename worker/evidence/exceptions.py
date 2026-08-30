"""
Domain exceptions for IBVAP Structured Evidence Storage & Packaging Subsystem.
"""

class EvidenceError(Exception):
    """Base exception for all evidence packaging and storage errors."""
    pass


class BufferUnderflowError(EvidenceError):
    """Raised when insufficient frames are available in the rolling buffer for the requested window."""
    pass


class EncodingError(EvidenceError):
    """Raised when snapshot or video clip encoding fails."""
    pass


class IntegrityVerificationError(EvidenceError):
    """Raised when an evidence package fails cryptographic SHA-256 tamper verification."""
    pass


class StorageError(EvidenceError):
    """Raised when saving or uploading evidence artifacts fails."""
    pass
