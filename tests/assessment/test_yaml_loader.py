"""Tests for YAML probe loading, validation, and integration."""

from pathlib import Path

import pytest

from webagentaudit.assessment.probes.base import BaseProbe
from webagentaudit.assessment.probes.conversation import Conversation, ConversationTurn
from webagentaudit.assessment.probes.registry import ProbeRegistry
from webagentaudit.assessment.probes.yaml_loader import (
    YamlProbe,
    YamlProbeLoadError,
    load_yaml_probe,
    load_yaml_probes,
)
from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "yaml_probes"
INVALID_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "yaml_probes_invalid"


# ---------------------------------------------------------------------------
# Single-turn probes
# ---------------------------------------------------------------------------


class TestSingleTurnYamlProbe:
    def test_load_properties(self):
        probe = load_yaml_probe(FIXTURES / "single_turn.yaml")
        assert probe.name == "extraction.custom_direct_ask"
        assert probe.category == ProbeCategory.EXTRACTION
        assert probe.severity == Severity.CRITICAL
        assert probe.sophistication == Sophistication.BASIC
        assert "system prompt" in probe.description.lower()

    def test_get_prompts(self):
        probe = load_yaml_probe(FIXTURES / "single_turn.yaml")
        prompts = probe.get_prompts()
        assert len(prompts) == 3
        assert "system prompt" in prompts[0].lower()

    def test_get_conversations_wraps_prompts(self):
        probe = load_yaml_probe(FIXTURES / "single_turn.yaml")
        convs = probe.get_conversations()
        assert len(convs) == 3
        for conv in convs:
            assert len(conv.turns) == 1
            assert conv.turns[0].detect_after is True

    def test_get_detector_patterns(self):
        probe = load_yaml_probe(FIXTURES / "single_turn.yaml")
        patterns = probe.get_detector_patterns()
        assert len(patterns) == 4
        assert any("system" in p for p in patterns)


# ---------------------------------------------------------------------------
# Multi-turn probes
# ---------------------------------------------------------------------------


class TestMultiTurnYamlProbe:
    def test_load_properties(self):
        probe = load_yaml_probe(FIXTURES / "multi_turn.yaml")
        assert probe.name == "extraction.trust_building_custom"
        assert probe.category == ProbeCategory.EXTRACTION
        assert probe.severity == Severity.HIGH
        assert probe.sophistication == Sophistication.ADVANCED

    def test_get_prompts_returns_empty(self):
        probe = load_yaml_probe(FIXTURES / "multi_turn.yaml")
        assert probe.get_prompts() == []

    def test_get_conversations(self):
        probe = load_yaml_probe(FIXTURES / "multi_turn.yaml")
        convs = probe.get_conversations()
        assert len(convs) == 2

        # First conversation
        assert convs[0].description == "Compliment, then ask for instructions"
        assert len(convs[0].turns) == 2
        assert convs[0].turns[0].detect_after is False
        assert convs[0].turns[1].detect_after is True

        # Second conversation
        assert convs[1].description == "Establish expertise, then probe"
        assert len(convs[1].turns) == 2

    def test_detect_after_defaults_true(self):
        """Turns without explicit detect_after should default to True."""
        probe = load_yaml_probe(FIXTURES / "multi_turn.yaml")
        convs = probe.get_conversations()
        # Second turn in each conversation has detect_after=true (explicit)
        assert convs[0].turns[1].detect_after is True
        assert convs[1].turns[1].detect_after is True


# ---------------------------------------------------------------------------
# Mixed probes (both prompts and conversations)
# ---------------------------------------------------------------------------


class TestMixedYamlProbe:
    def test_get_prompts_returns_only_single_turn(self):
        probe = load_yaml_probe(FIXTURES / "mixed.yaml")
        prompts = probe.get_prompts()
        assert len(prompts) == 1
        assert "FreeBot" in prompts[0]

    def test_get_conversations_combines_both(self):
        probe = load_yaml_probe(FIXTURES / "mixed.yaml")
        convs = probe.get_conversations()
        # 1 from prompts + 1 from conversations = 2
        assert len(convs) == 2

        # First is the single-turn prompt wrapped
        assert len(convs[0].turns) == 1
        assert "FreeBot" in convs[0].turns[0].prompt

        # Second is the multi-turn conversation
        assert len(convs[1].turns) == 2
        assert convs[1].description == "Gradual persona shift"


# ---------------------------------------------------------------------------
# Type compatibility
# ---------------------------------------------------------------------------


class TestYamlProbeIsBaseProbe:
    def test_isinstance(self):
        probe = load_yaml_probe(FIXTURES / "single_turn.yaml")
        assert isinstance(probe, BaseProbe)

    def test_source_path(self):
        path = FIXTURES / "single_turn.yaml"
        probe = load_yaml_probe(path)
        assert probe.source_path == path


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    def test_register_yaml_probe(self):
        registry = ProbeRegistry()
        probe = load_yaml_probe(FIXTURES / "single_turn.yaml")
        registry.register(probe)

        found = registry.get_by_name("extraction.custom_direct_ask")
        assert found is probe

    def test_get_by_category(self):
        registry = ProbeRegistry()
        probe = load_yaml_probe(FIXTURES / "single_turn.yaml")
        registry.register(probe)

        by_cat = registry.get_by_category(ProbeCategory.EXTRACTION)
        assert probe in by_cat

    def test_load_yaml_dir(self):
        registry = ProbeRegistry()
        count = registry.load_yaml_dir(FIXTURES)
        # single_turn + multi_turn + mixed + nested/vendor_specific = 4
        assert count == 4
        assert len(registry.get_all()) == 4

    def test_load_yaml_file(self):
        registry = ProbeRegistry()
        registry.load_yaml_file(FIXTURES / "single_turn.yaml")
        assert registry.get_by_name("extraction.custom_direct_ask") is not None

    def test_yaml_probe_overwrites_existing(self):
        registry = ProbeRegistry()
        probe1 = load_yaml_probe(FIXTURES / "single_turn.yaml")
        registry.register(probe1)

        # Register another probe with the same name — should overwrite
        probe2 = load_yaml_probe(FIXTURES / "single_turn.yaml")
        registry.register(probe2)

        assert registry.get_by_name("extraction.custom_direct_ask") is probe2
        assert len(registry.get_all()) == 1

    def test_filter_works_with_yaml_probes(self):
        registry = ProbeRegistry()
        registry.load_yaml_dir(FIXTURES)

        # Filter by severity
        critical = registry.filter(severities=[Severity.CRITICAL])
        assert any(p.name == "extraction.custom_direct_ask" for p in critical)

        # Filter by sophistication
        advanced = registry.filter(sophistication_levels=[Sophistication.ADVANCED])
        assert any(p.name == "extraction.trust_building_custom" for p in advanced)


# ---------------------------------------------------------------------------
# Directory loading
# ---------------------------------------------------------------------------


class TestLoadYamlProbes:
    def test_loads_recursively(self):
        probes = load_yaml_probes(FIXTURES)
        names = {p.name for p in probes}
        # Should find nested/vendor_specific.yaml
        assert "prompt_injection.vendor_override" in names
        assert len(probes) == 4

    def test_loads_non_recursively(self):
        probes = load_yaml_probes(FIXTURES, recursive=False)
        names = {p.name for p in probes}
        # Should NOT find nested/vendor_specific.yaml
        assert "prompt_injection.vendor_override" not in names
        assert len(probes) == 3

    def test_nonexistent_directory_raises(self):
        with pytest.raises(FileNotFoundError):
            load_yaml_probes(Path("/nonexistent/probe/dir"))

    def test_skips_invalid_files(self):
        """Directory with all invalid files should return empty list."""
        probes = load_yaml_probes(INVALID_FIXTURES)
        # All files in INVALID_FIXTURES should fail validation
        assert len(probes) == 0


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_missing_name(self):
        with pytest.raises(YamlProbeLoadError):
            load_yaml_probe(INVALID_FIXTURES / "missing_name.yaml")

    def test_bad_category(self):
        with pytest.raises(YamlProbeLoadError):
            load_yaml_probe(INVALID_FIXTURES / "bad_category.yaml")

    def test_no_prompts_or_conversations(self):
        with pytest.raises(YamlProbeLoadError):
            load_yaml_probe(INVALID_FIXTURES / "no_prompts.yaml")

    def test_bad_regex(self):
        with pytest.raises(YamlProbeLoadError):
            load_yaml_probe(INVALID_FIXTURES / "bad_regex.yaml")

    def test_bad_yaml_syntax(self):
        with pytest.raises(YamlProbeLoadError):
            load_yaml_probe(INVALID_FIXTURES / "bad_syntax.yaml")

    def test_non_dict_yaml(self, tmp_path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        with pytest.raises(YamlProbeLoadError, match="YAML mapping"):
            load_yaml_probe(f)

    def test_nonexistent_file(self, tmp_path):
        with pytest.raises(YamlProbeLoadError, match="Cannot read file"):
            load_yaml_probe(tmp_path / "does_not_exist.yaml")

    def test_empty_detector_patterns(self, tmp_path):
        f = tmp_path / "empty_patterns.yaml"
        f.write_text(
            "name: test.empty\n"
            "category: extraction\n"
            "severity: high\n"
            "sophistication: basic\n"
            "description: Missing patterns.\n"
            "prompts:\n"
            "  - test\n"
            "detector_patterns: []\n"
        )
        with pytest.raises(YamlProbeLoadError):
            load_yaml_probe(f)


# ---------------------------------------------------------------------------
# ProbeRegistry loading and filtering (moved from e2e tests — no browser needed)
# ---------------------------------------------------------------------------


class TestProbeRegistry:
    """Test probe registry loading from YAML fixtures."""

    def test_load_yaml_dir(self):
        registry = ProbeRegistry()
        loaded = registry.load_yaml_dir(FIXTURES)
        assert loaded > 0
        all_probes = registry.get_all()
        assert len(all_probes) == loaded

    def test_load_single_file(self):
        registry = ProbeRegistry()
        registry.load_yaml_file(FIXTURES / "single_turn.yaml")
        all_probes = registry.get_all()
        assert len(all_probes) == 1
        assert all_probes[0].name == "extraction.custom_direct_ask"

    def test_filter_by_category(self):
        registry = ProbeRegistry()
        registry.load_yaml_dir(FIXTURES)
        filtered = registry.filter(categories=[ProbeCategory.EXTRACTION])
        assert len(filtered) > 0
        for probe in filtered:
            assert probe.category == ProbeCategory.EXTRACTION

    def test_filter_by_sophistication(self):
        registry = ProbeRegistry()
        registry.load_yaml_dir(FIXTURES)
        filtered = registry.filter(sophistication_levels=[Sophistication.BASIC])
        for probe in filtered:
            assert probe.sophistication == Sophistication.BASIC

    def test_probe_has_required_fields(self):
        registry = ProbeRegistry()
        registry.load_yaml_file(FIXTURES / "single_turn.yaml")
        probe = registry.get_all()[0]
        assert probe.name
        assert probe.category
        assert probe.severity
        assert probe.sophistication
        assert probe.description
        assert len(probe.get_detector_patterns()) > 0
