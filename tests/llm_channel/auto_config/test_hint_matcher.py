"""Tests for hint parsing and fuzzy matching."""

import pytest

from webagentaudit.llm_channel.auto_config._hint_matcher import (
    compute_hint_match,
    parse_hint,
)
from webagentaudit.llm_channel.auto_config.models import ElementCandidate, ElementHint

pytestmark = pytest.mark.unit


class TestParseHint:
    """Tests for HTML snippet → ElementHint parsing."""

    def test_simple_textarea(self):
        hint = parse_hint('<textarea class="chat-input" placeholder="Ask...">')
        assert hint.tag_name == "textarea"
        assert hint.classes == ["chat-input"]
        assert hint.attributes["placeholder"] == "Ask..."
        assert hint.has_svg_child is False

    def test_button_with_svg(self):
        hint = parse_hint('<button title="Send"><svg></svg></button>')
        assert hint.tag_name == "button"
        assert hint.attributes["title"] == "Send"
        assert hint.has_svg_child is True

    def test_multiple_classes(self):
        hint = parse_hint('<textarea class="flex-1 border-0 rounded-md resize-none">')
        assert hint.tag_name == "textarea"
        assert hint.classes == ["flex-1", "border-0", "rounded-md", "resize-none"]

    def test_dir_attribute(self):
        hint = parse_hint('<textarea class="chat-input" dir="rtl">')
        assert hint.attributes["dir"] == "rtl"

    def test_button_with_type(self):
        hint = parse_hint('<button type="button" title="שלח">')
        assert hint.tag_name == "button"
        assert hint.attributes["type"] == "button"
        assert hint.attributes["title"] == "שלח"

    def test_contenteditable_div(self):
        hint = parse_hint('<div contenteditable="true" role="textbox">')
        assert hint.tag_name == "div"
        assert hint.attributes["contenteditable"] == "true"
        assert hint.attributes["role"] == "textbox"

    def test_preserves_raw_html(self):
        raw = '<textarea class="x">'
        hint = parse_hint(raw)
        assert hint.raw_html == raw

    def test_empty_string(self):
        hint = parse_hint("")
        assert hint.tag_name == ""
        assert hint.classes == []

    def test_svg_nested_in_button(self):
        hint = parse_hint(
            '<button class="send-btn"><svg xmlns="http://www.w3.org/2000/svg" '
            'width="18" height="18"><path d="m5 12 7-7 7 7"></path></svg></button>'
        )
        assert hint.tag_name == "button"
        assert hint.classes == ["send-btn"]
        assert hint.has_svg_child is True


class TestComputeHintMatch:
    """Tests for fuzzy matching between candidates and hints."""

    def _make_candidate(self, **kwargs) -> ElementCandidate:
        defaults = {
            "tag_name": "textarea",
            "selector": "textarea",
            "classes": [],
            "title": "",
        }
        defaults.update(kwargs)
        return ElementCandidate(**defaults)

    def test_exact_match_high_score(self):
        """A candidate matching all hint attributes should score high."""
        hint = ElementHint(
            tag_name="textarea",
            classes=["chat-input", "rounded-md"],
        )
        candidate = self._make_candidate(
            classes=["chat-input", "rounded-md"],
        )
        score = compute_hint_match(candidate, hint)
        assert score > 0.8

    def test_no_match_low_score(self):
        """A candidate with nothing in common should score near zero."""
        hint = ElementHint(
            tag_name="button",
            classes=["send-btn"],
        )
        candidate = self._make_candidate(
            tag_name="textarea",
            classes=["search-box"],
        )
        score = compute_hint_match(candidate, hint)
        assert score < 0.15

    def test_partial_class_overlap(self):
        """Partial class overlap gives proportional score."""
        hint = ElementHint(
            tag_name="textarea",
            classes=["flex-1", "border-0", "rounded-md", "resize-none"],
        )
        candidate = self._make_candidate(
            classes=["flex-1", "rounded-md", "extra-class"],
        )
        score = compute_hint_match(candidate, hint)
        # Should be > 0 (partial match) but < perfect
        assert 0.3 < score < 0.9

    def test_title_match_boosts_score(self):
        """Button with matching title should score well."""
        hint = ElementHint(
            tag_name="button",
            attributes={"title": "שלח"},
            has_svg_child=True,
        )
        candidate = self._make_candidate(
            tag_name="button",
            title="שלח",
            has_svg_child=True,
        )
        score = compute_hint_match(candidate, hint)
        assert score > 0.8

    def test_svg_mismatch_reduces_score(self):
        """If hint expects SVG but candidate has none, score drops."""
        hint = ElementHint(
            tag_name="button",
            has_svg_child=True,
        )
        with_svg = self._make_candidate(tag_name="button", has_svg_child=True)
        without_svg = self._make_candidate(tag_name="button", has_svg_child=False)

        score_with = compute_hint_match(with_svg, hint)
        score_without = compute_hint_match(without_svg, hint)
        assert score_with > score_without

    def test_empty_hint_returns_zero(self):
        """An empty hint should return 0.0."""
        hint = ElementHint()
        candidate = self._make_candidate()
        score = compute_hint_match(candidate, hint)
        assert score == 0.0

    def test_calcalist_input_hint(self):
        """Real-world: Calcalist's chat textarea vs the hint provided."""
        hint = parse_hint(
            '<textarea class="flex-1 border-0 outline-none rounded-md py-2 '
            'text-base bg-transparent w-full font-normal resize-none '
            'overflow-y-auto placeholder-gray-500" dir="rtl">'
        )

        # The correct textarea (many overlapping classes)
        correct = self._make_candidate(
            classes=[
                "flex-1", "border-0", "outline-none", "rounded-md",
                "py-2", "text-base", "bg-transparent", "w-full",
                "font-normal", "resize-none", "overflow-y-auto",
                "placeholder-gray-500", "focus:outline-none",
                "focus:ring-0", "focus:border-transparent", "text-gray-900",
            ],
        )

        # A random unrelated textarea
        wrong = self._make_candidate(
            classes=["some-other-textarea"],
        )

        score_correct = compute_hint_match(correct, hint)
        score_wrong = compute_hint_match(wrong, hint)

        assert score_correct > score_wrong
        assert score_correct > 0.5

    def test_calcalist_submit_hint(self):
        """Real-world: Calcalist's send button vs the hint provided."""
        hint = parse_hint(
            '<button class="flex items-center gap-1 p-3 rounded-full" '
            'title="שלח" type="button"><svg></svg></button>'
        )

        # The correct send button
        correct = self._make_candidate(
            tag_name="button",
            classes=["flex", "items-center", "gap-1", "p-3", "rounded-full",
                     "font-medium", "justify-center"],
            title="שלח",
            has_svg_child=True,
            element_type="button",
        )

        # The accessibility widget button (wrong one)
        wrong = self._make_candidate(
            tag_name="button",
            classes=["equally-ai-button"],
            title="",
            has_svg_child=False,
        )

        score_correct = compute_hint_match(correct, hint)
        score_wrong = compute_hint_match(wrong, hint)

        assert score_correct > score_wrong
        assert score_correct > 0.5
        assert score_wrong < 0.3
