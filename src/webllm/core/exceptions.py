"""Custom exception hierarchy for webllm."""


class WebLlmError(Exception):
    """Base exception for all webllm errors."""


class DetectionError(WebLlmError):
    """Error during LLM detection phase."""


class AssessmentError(WebLlmError):
    """Error during LLM assessment phase."""


class ChannelError(WebLlmError):
    """Error in LLM channel communication."""


class ChannelTimeoutError(ChannelError):
    """Timeout waiting for LLM response."""


class ChannelNotReadyError(ChannelError):
    """Channel not initialized or LLM input not found."""
