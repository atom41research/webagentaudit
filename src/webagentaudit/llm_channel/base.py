"""Abstract base class for LLM channel communication."""

from abc import ABC, abstractmethod

from .config import ChannelConfig
from .models import ChannelMessage, ChannelResponse


class BaseLlmChannel(ABC):
    """Base class for communicating with web-based LLMs.

    Subclasses implement the actual browser automation or API interaction.
    """

    def __init__(self, config: ChannelConfig) -> None:
        self._config = config

    @property
    def config(self) -> ChannelConfig:
        return self._config

    @abstractmethod
    async def connect(self, url: str) -> None:
        """Navigate to the target URL and prepare the channel."""

    @abstractmethod
    async def send(self, message: ChannelMessage) -> ChannelResponse:
        """Send a message and wait for a response."""

    @abstractmethod
    async def write(self, text: str) -> None:
        """Write text into the LLM input field."""

    @abstractmethod
    async def read(self, timeout_ms: int | None = None) -> ChannelResponse:
        """Read the LLM's response."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up resources."""

    @abstractmethod
    async def is_ready(self) -> bool:
        """Check if the channel is connected and ready to send messages."""
