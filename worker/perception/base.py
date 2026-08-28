from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from ..ingestion.frame import FramePacket
from .schemas import Detection


class DetectorInterface(ABC):
    """
    Abstract Base Class for all object detection backends in IBVAP.
    Enforces strict decoupling between detector model implementations (RF-DETR, YOLO, ONNX)
    and downstream multi-object tracking / event reasoning layers.
    """

    @abstractmethod
    def load(self, model_path: Optional[str] = None) -> bool:
        """
        Loads model weights into memory and initializes computation graph.
        Returns True if loaded successfully, False otherwise.
        """
        pass

    @abstractmethod
    def warmup(self, input_size: Tuple[int, int] = (640, 640)) -> bool:
        """
        Executes dummy forward passes to warm up computation engine / GPU kernels.
        Returns True if warmup completes without error.
        """
        pass

    @abstractmethod
    def infer(self, frame_packet: FramePacket) -> List[Detection]:
        """
        Performs object detection on the provided canonical FramePacket.
        Returns a list of structured Detection objects.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns model metadata (name, version, device, confidence threshold, runtime).
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Releases model weights and frees memory buffers cleanly.
        """
        pass
