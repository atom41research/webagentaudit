"""Load probe definitions from YAML files."""

import logging
from pathlib import Path

import yaml

from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication

from .base import BaseProbe
from .conversation import Conversation, ConversationTurn
from .yaml_schema import YamlProbeSchema

logger = logging.getLogger(__name__)


class YamlProbeLoadError(Exception):
    """Raised when a YAML probe file cannot be loaded or validated."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load probe from {path}: {reason}")


class YamlProbe(BaseProbe):
    """A probe loaded from a YAML definition file.

    Wraps a validated ``YamlProbeSchema`` and exposes it through the
    ``BaseProbe`` interface so it is transparent to the harness, detector,
    and assessor.
    """

    def __init__(
        self, schema: YamlProbeSchema, source_path: Path | None = None
    ) -> None:
        self._schema = schema
        self._source_path = source_path

    @property
    def name(self) -> str:
        return self._schema.name

    @property
    def category(self) -> ProbeCategory:
        return self._schema.category

    @property
    def severity(self) -> Severity:
        return self._schema.severity

    @property
    def description(self) -> str:
        return self._schema.description

    @property
    def sophistication(self) -> Sophistication:
        return self._schema.sophistication

    @property
    def source_path(self) -> Path | None:
        """The YAML file this probe was loaded from."""
        return self._source_path

    def get_prompts(self) -> list[str]:
        return list(self._schema.prompts)

    def get_conversations(self) -> list[Conversation]:
        convs: list[Conversation] = []
        # Single-turn prompts
        for prompt in self._schema.prompts:
            convs.append(Conversation(turns=[ConversationTurn(prompt=prompt)]))
        # Multi-turn conversations
        for conv_schema in self._schema.conversations:
            turns = [
                ConversationTurn(
                    prompt=turn.prompt,
                    detect_after=turn.detect_after,
                )
                for turn in conv_schema.turns
            ]
            convs.append(
                Conversation(turns=turns, description=conv_schema.description)
            )
        return convs

    def get_detector_patterns(self) -> list[str]:
        return list(self._schema.detector_patterns)


def load_yaml_probe(path: Path) -> YamlProbe:
    """Load and validate a single YAML probe file.

    Args:
        path: Path to a ``.yaml`` or ``.yml`` file.

    Returns:
        A ``YamlProbe`` ready for registration.

    Raises:
        YamlProbeLoadError: If the file cannot be read, parsed, or validated.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise YamlProbeLoadError(path, f"YAML parse error: {exc}") from exc
    except OSError as exc:
        raise YamlProbeLoadError(path, f"Cannot read file: {exc}") from exc

    if not isinstance(raw, dict):
        raise YamlProbeLoadError(path, "File must contain a YAML mapping")

    try:
        schema = YamlProbeSchema(**raw)
    except Exception as exc:
        raise YamlProbeLoadError(path, str(exc)) from exc

    return YamlProbe(schema=schema, source_path=path)


def load_yaml_probes(
    directory: Path,
    *,
    recursive: bool = True,
) -> list[YamlProbe]:
    """Load all YAML probes from a directory.

    Invalid files are logged as warnings and skipped.

    Args:
        directory: Root directory to scan.
        recursive: If True, scan subdirectories too.

    Returns:
        List of successfully loaded ``YamlProbe`` instances.

    Raises:
        FileNotFoundError: If *directory* does not exist.
    """
    if not directory.is_dir():
        raise FileNotFoundError(f"Probe directory not found: {directory}")

    glob_pattern = "**/*" if recursive else "*"
    yaml_files = sorted(
        f
        for f in directory.glob(glob_pattern)
        if f.is_file() and f.suffix in (".yaml", ".yml")
    )

    probes: list[YamlProbe] = []
    for path in yaml_files:
        try:
            probe = load_yaml_probe(path)
            probes.append(probe)
            logger.debug("Loaded YAML probe '%s' from %s", probe.name, path)
        except YamlProbeLoadError as exc:
            logger.warning("Skipping invalid probe file: %s", exc)

    logger.info(
        "Loaded %d YAML probe(s) from %s (%d files scanned)",
        len(probes),
        directory,
        len(yaml_files),
    )
    return probes
