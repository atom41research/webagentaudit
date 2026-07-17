"""Abstract base class for assessment probes."""

from abc import ABC, abstractmethod

from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication

from .conversation import Conversation, ConversationTurn


class BaseProbe(ABC):
    """Base class for all LLM security probes.

    A probe defines attack conversations (single or multi-turn) and the
    regex patterns that indicate a vulnerability was exploited in the response.
    Assessment assumes a good probe: its positive signal is absent from every
    detection-active prompt, absent from the rendered page before submission,
    and specific enough not to occur independently. Output-directed probes
    should use transformed random canaries.

    Single-turn probes implement ``get_prompts()`` -- each prompt becomes
    its own conversation automatically via the default ``get_conversations()``.

    Multi-turn probes override ``get_conversations()`` directly and can
    implement ``get_prompts()`` returning ``[]``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifying this probe."""

    @property
    @abstractmethod
    def category(self) -> ProbeCategory:
        """The attack category this probe belongs to."""

    @property
    @abstractmethod
    def severity(self) -> Severity:
        """Default severity if this probe detects a vulnerability."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this probe tests."""

    @property
    @abstractmethod
    def sophistication(self) -> Sophistication:
        """How sophisticated/complex this attack technique is."""

    @abstractmethod
    def get_prompts(self) -> list[str]:
        """Return the list of attack prompts to send to the LLM.

        Each prompt is sent as a single-turn conversation. For multi-turn
        probes, override ``get_conversations()`` instead and return ``[]`` here.
        """

    def get_conversations(self) -> list[Conversation]:
        """Return conversation flows to execute.

        Each conversation gets a fresh channel. The default wraps
        each prompt from ``get_prompts()`` as a single-turn conversation.

        Override this for multi-turn probes where multiple messages must
        share the same session.
        """
        return [
            Conversation(turns=[ConversationTurn(prompt=p)])
            for p in self.get_prompts()
        ]

    @abstractmethod
    def get_detector_patterns(self) -> list[str]:
        """Return regex patterns that indicate a vulnerability in the response.

        Patterns are matched case-insensitively against the LLM's response text.
        Design patterns to be **unambiguous**: the expected matching output must
        not occur in a detection-active prompt or pre-submit page, and should
        only be produced by a successful attack (transformed random canaries or
        structured leaked content, never common words or refusal keywords).
        """

    def get_refusal_patterns(self) -> list[str]:
        """Optional probe-specific refusal patterns.

        If non-empty, responses matching any of these are filtered out.
        Prefer designing unambiguous detector patterns instead.
        """
        return []
