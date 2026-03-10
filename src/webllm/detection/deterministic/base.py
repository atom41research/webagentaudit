"""Base class for deterministic detection signal checkers."""

from abc import ABC, abstractmethod

from ..models import DetectionSignal, PageData


class BaseSignalChecker(ABC):
    """Abstract base for deterministic detection signal checkers.

    Each checker examines one aspect of the page (DOM, selectors, scripts, etc.)
    and produces zero or more DetectionSignal objects.
    """

    @abstractmethod
    def check(self, page_data: PageData) -> list[DetectionSignal]:
        """Run this checker against page data.

        Args:
            page_data: Parsed page data (DOM, HTML, scripts, etc.)

        Returns:
            List of detection signals found. Empty list if none.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this checker."""
