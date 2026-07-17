"""Custom exception hierarchy for webagentaudit."""


class WebLlmError(Exception):
    """Base exception for all webagentaudit errors."""


class DetectionError(WebLlmError):
    """Error during LLM detection phase."""


class AssessmentError(WebLlmError):
    """Error during LLM assessment phase."""


class ChannelError(WebLlmError):
    """Error in LLM channel communication."""


class ChannelSubmissionError(ChannelError):
    """Error while typing or submitting a prompt."""


class ChannelResponseError(ChannelError):
    """Error while waiting for or reading a response."""

    def __init__(self, message: str, *, metadata: dict[str, str] | None = None):
        super().__init__(message)
        self.metadata = metadata or {}


class ChannelTimeoutError(ChannelResponseError):
    """Timeout waiting for LLM response."""


class ChannelNotReadyError(ChannelError):
    """Channel not initialized or LLM input not found."""
