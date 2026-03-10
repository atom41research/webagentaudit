"""Detection module configuration."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DetectionConfig:
    """Configuration for LLM detection."""

    enable_dom_patterns: bool = True
    enable_selector_matching: bool = True
    enable_known_signatures: bool = True
    enable_script_analysis: bool = True
    enable_network_hints: bool = True
    enable_ai_assisted: bool = False
    confidence_threshold: float = 0.3
    ai_model: Optional[str] = None
