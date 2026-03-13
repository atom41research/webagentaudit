"""Logger for assessment conversations."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class LogEntry:
    timestamp: datetime
    probe_name: str
    turn_index: int
    prompt: str
    response: str
    matched_patterns: list[str] = field(default_factory=list)


class ConversationLogger:
    """Records conversation interactions during assessment."""

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []

    def log(
        self,
        probe_name: str,
        turn_index: int,
        prompt: str,
        response: str,
        matched_patterns: list[str] | None = None,
    ) -> None:
        self._entries.append(
            LogEntry(
                timestamp=datetime.now(UTC),
                probe_name=probe_name,
                turn_index=turn_index,
                prompt=prompt,
                response=response,
                matched_patterns=matched_patterns or [],
            )
        )

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def get_for_probe(self, probe_name: str) -> list[LogEntry]:
        return [e for e in self._entries if e.probe_name == probe_name]
