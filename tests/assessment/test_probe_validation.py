"""Probe-author anti-echo validation."""

import re

import pytest

from webagentaudit.assessment.probes.registry import ProbeRegistry
from webagentaudit.assessment.validation import find_prompt_pattern_overlaps

pytestmark = pytest.mark.unit


def test_every_builtin_detection_active_prompt_is_echo_safe():
    affected = {
        probe.name: find_prompt_pattern_overlaps(probe)
        for probe in ProbeRegistry.default().get_all()
        if find_prompt_pattern_overlaps(probe)
    }

    assert affected == {}


def test_image_capability_expected_positive_is_absent_from_prompt():
    probe = ProbeRegistry.default().get_by_name(
        "system_prompt_leak.image_generation_capability"
    )

    assert probe is not None
    assert not re.search(r"\byes\b", probe.get_prompts()[0], re.IGNORECASE)
