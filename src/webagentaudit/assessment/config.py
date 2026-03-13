"""Assessment configuration."""

from dataclasses import dataclass

from .consts import DEFAULT_INTER_PROBE_DELAY_MS, DEFAULT_STOP_ON_FIRST, DEFAULT_WORKERS


@dataclass
class AssessmentConfig:
    """Configuration for the LLM assessment process."""

    workers: int = DEFAULT_WORKERS
    stop_on_first: bool = DEFAULT_STOP_ON_FIRST
    inter_probe_delay_ms: int = DEFAULT_INTER_PROBE_DELAY_MS
