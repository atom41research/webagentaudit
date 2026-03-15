"""Tests for canary token generation — anti-echo properties."""

import re

from webagentaudit.assessment.probes.canary import (
    CanaryToken,
    generate_concat_canary,
    generate_separator_canary,
)


class TestConcatCanary:
    """Concatenation canary: prompt has two parts, detector looks for joined."""

    def test_expected_output_not_in_prompt(self):
        c = generate_concat_canary()
        assert c.expected_output not in c.prompt_fragment

    def test_expected_output_is_parts_joined(self):
        c = generate_concat_canary(part_length=6)
        # The output should be exactly 12 hex chars (two 6-char parts)
        assert len(c.expected_output) == 12
        assert all(ch in "0123456789abcdef" for ch in c.expected_output)

    def test_both_parts_in_prompt(self):
        c = generate_concat_canary(part_length=6)
        part_a = c.expected_output[:6]
        part_b = c.expected_output[6:]
        assert part_a in c.prompt_fragment
        assert part_b in c.prompt_fragment

    def test_detector_pattern_matches_expected(self):
        c = generate_concat_canary()
        assert re.search(c.detector_pattern, c.expected_output)

    def test_detector_pattern_does_not_match_prompt(self):
        c = generate_concat_canary()
        assert not re.search(c.detector_pattern, c.prompt_fragment)

    def test_each_call_unique(self):
        tokens = [generate_concat_canary() for _ in range(10)]
        outputs = {t.expected_output for t in tokens}
        assert len(outputs) == 10

    def test_custom_part_length(self):
        c = generate_concat_canary(part_length=8)
        assert len(c.expected_output) == 16


class TestSeparatorCanary:
    """Separator canary: prompt has 'abc-def', detector looks for 'abcdef'."""

    def test_expected_output_not_in_prompt(self):
        c = generate_separator_canary()
        assert c.expected_output not in c.prompt_fragment

    def test_separator_in_prompt_not_in_output(self):
        c = generate_separator_canary(separator="-")
        assert "-" in c.prompt_fragment
        assert "-" not in c.expected_output

    def test_detector_pattern_matches_expected(self):
        c = generate_separator_canary()
        assert re.search(c.detector_pattern, c.expected_output)

    def test_detector_pattern_does_not_match_prompt(self):
        c = generate_separator_canary()
        assert not re.search(c.detector_pattern, c.prompt_fragment)

    def test_each_call_unique(self):
        tokens = [generate_separator_canary() for _ in range(10)]
        outputs = {t.expected_output for t in tokens}
        assert len(outputs) == 10

    def test_custom_separator(self):
        c = generate_separator_canary(separator=".")
        assert "." in c.prompt_fragment
        assert "." not in c.expected_output

    def test_custom_segment_length(self):
        c = generate_separator_canary(segment_length=8)
        assert len(c.expected_output) == 16


class TestCanaryTokenDataclass:
    """CanaryToken is immutable and well-formed."""

    def test_frozen(self):
        c = generate_concat_canary()
        try:
            c.expected_output = "tampered"
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_detector_pattern_is_valid_regex(self):
        for gen in [generate_concat_canary, generate_separator_canary]:
            c = gen()
            re.compile(c.detector_pattern)  # should not raise
