"""Conversation types for multi-turn probe interactions."""

from dataclasses import dataclass, field


@dataclass
class ConversationTurn:
    """A single turn in a multi-turn conversation.

    Attributes:
        prompt: The text to send to the LLM.
        detect_after: Whether to run pattern detection on this turn's response.
            Set to False for setup turns (e.g., establishing context).
    """

    prompt: str
    detect_after: bool = True


@dataclass
class Conversation:
    """A sequence of turns that must share the same browser session.

    Each conversation gets a fresh browser session to avoid contamination
    from other conversations or probes.
    """

    turns: list[ConversationTurn] = field(default_factory=list)
    description: str = ""
