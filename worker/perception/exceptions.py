class PerceptionError(Exception):
    """Base exception for all perception and object detection errors."""
    pass


class ModelLoadError(PerceptionError):
    """Raised when loading or initializing the detection model fails."""
    pass


class ModelNotFoundError(ModelLoadError):
    """Raised when the specified model file or weights artifact cannot be found."""
    pass


class ModelInferenceError(PerceptionError):
    """Raised when executing model forward pass / inference fails."""
    pass


class InvalidInputError(PerceptionError):
    """Raised when incoming image or FramePacket is invalid, empty, or wrong shape."""
    pass


class UnsupportedDeviceError(PerceptionError):
    """Raised when requesting an unavailable compute device (e.g., CUDA on CPU-only host)."""
    pass


class ModelCompatibilityError(PerceptionError):
    """Raised when the installed model runtime or framework does not support the requested model family or weights architecture."""
    pass

