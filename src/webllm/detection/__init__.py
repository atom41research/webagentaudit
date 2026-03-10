"""Detection module - detect interactive LLMs on webpages."""

from .config import DetectionConfig
from .detector import LlmDetector
from .models import DetectionResult, DetectionSignal, PageData

__all__ = [
    "DetectionConfig",
    "DetectionResult",
    "DetectionSignal",
    "LlmDetector",
    "PageData",
]
