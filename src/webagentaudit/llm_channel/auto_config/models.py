"""Data models for auto-configuration results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from playwright.async_api import Frame

from webagentaudit.core.models import ConfidenceScore


class TriggerMechanism(Enum):
    """Type of UI interaction that reveals a hidden AI panel."""

    DIALOG = "dialog"
    SIDE_PANEL = "side_panel"
    COMMAND_MENU = "command_menu"


@dataclass
class TriggerResult:
    """Result of trigger detection: which element was clicked and how."""

    trigger_selector: str
    mechanism: TriggerMechanism
    confidence: float  # 0.0 - 1.0


@dataclass
class ElementCandidate:
    """Raw properties extracted from a DOM element for scoring."""

    tag_name: str
    selector: str
    placeholder: str = ""
    aria_label: str = ""
    role: str = ""
    classes: list[str] = field(default_factory=list)
    data_testid: str = ""
    element_type: str = ""
    is_contenteditable: bool = False
    text_content: str = ""
    bounding_box: dict | None = None
    parent_classes: list[str] = field(default_factory=list)
    is_visible: bool = True
    has_svg_child: bool = False
    title: str = ""


@dataclass
class ElementHint:
    """Parsed attributes from a user-provided HTML snippet.

    Used to fuzzy-match against live DOM elements during auto-discovery.
    """

    tag_name: str = ""
    classes: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    has_svg_child: bool = False
    raw_html: str = ""


@dataclass
class ScoredElement:
    """An element candidate with a computed score."""

    candidate: ElementCandidate
    score: float  # 0.0 - 1.0
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class FrameCandidate:
    """An iframe that may contain a chat widget."""

    frame: Frame = field(repr=False)
    score: float = 0.0
    iframe_selector: str = ""
    src: str = ""
    title: str = ""
    has_input: bool = False


@dataclass
class AutoConfigResult:
    """Result of auto-configuration: discovered selectors with confidence."""

    input_selector: str | None = None
    submit_selector: str | None = None
    response_selector: str | None = None
    input_confidence: ConfidenceScore = field(
        default_factory=lambda: ConfidenceScore(value=0.0)
    )
    submit_confidence: ConfidenceScore = field(
        default_factory=lambda: ConfidenceScore(value=0.0)
    )
    response_confidence: ConfidenceScore = field(
        default_factory=lambda: ConfidenceScore(value=0.0)
    )
    use_enter_to_submit: bool = False
    trigger_used: TriggerResult | None = None
    test_message_used: str | None = None
    test_response_received: str | None = None
    discovery_frame: Frame | None = field(default=None, repr=False)
    iframe_selector: str | None = None

    @property
    def is_usable(self) -> bool:
        """Whether we have minimum viable selectors (input + response)."""
        return self.input_selector is not None and self.response_selector is not None

    def to_channel_config_kwargs(self) -> dict:
        """Return kwargs suitable for PlaywrightChannelConfig construction."""
        return {
            "input_selector": self.input_selector,
            "submit_selector": self.submit_selector,
            "response_selector": self.response_selector,
            "iframe_selector": self.iframe_selector,
        }
