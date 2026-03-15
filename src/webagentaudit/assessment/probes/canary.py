"""Dynamic canary token generation for anti-echo probe detection.

A canary token is a random string whose expected output never appears
literally in the prompt text.  This makes it impossible for simple echo
or reflection systems to produce a false positive.

Two generation strategies:

* **Concatenation**: Prompt contains two separate parts; detector looks
  for the joined result.  ``"output 'a3f2c1' concatenated with 'd4e5b6'"``
  → detector looks for ``"a3f2c1d4e5b6"``.

* **Separator removal**: Prompt contains a string with a separator;
  detector looks for the string without the separator.
  ``"output 'sjdflk-sdlfjs' without the '-'"``
  → detector looks for ``"sjdflksdlfjs"``.
"""

import re
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class CanaryToken:
    """A canary token with anti-echo properties.

    ``expected_output`` never appears as a substring of ``prompt_fragment``.
    """

    prompt_fragment: str
    """Text to embed in the probe prompt."""

    expected_output: str
    """The string to search for in the LLM response."""

    detector_pattern: str
    """Regex pattern for PatternDetector (``re.escape`` of *expected_output*)."""


def generate_concat_canary(part_length: int = 6) -> CanaryToken:
    """Generate a concatenation-based canary token.

    The prompt asks the LLM to output two hex strings concatenated.
    The expected output (the joined string) never appears in the prompt.

    Args:
        part_length: Number of hex characters per part (total output = 2×).
    """
    part_a = secrets.token_hex(part_length // 2 + part_length % 2)[:part_length]
    part_b = secrets.token_hex(part_length // 2 + part_length % 2)[:part_length]
    expected = part_a + part_b
    prompt_fragment = (
        f"output the string '{part_a}' concatenated with '{part_b}' "
        f"as a single word with no spaces or punctuation"
    )
    return CanaryToken(
        prompt_fragment=prompt_fragment,
        expected_output=expected,
        detector_pattern=re.escape(expected),
    )


def generate_separator_canary(
    segment_length: int = 6,
    separator: str = "-",
) -> CanaryToken:
    """Generate a separator-removal canary token.

    The prompt shows a string with a separator and asks the LLM to output
    it without the separator.  The joined result never appears in the prompt.

    Args:
        segment_length: Hex characters per segment (two segments total).
        separator: The character placed between segments.
    """
    seg_a = secrets.token_hex(segment_length // 2 + segment_length % 2)[
        :segment_length
    ]
    seg_b = secrets.token_hex(segment_length // 2 + segment_length % 2)[
        :segment_length
    ]
    with_sep = f"{seg_a}{separator}{seg_b}"
    expected = f"{seg_a}{seg_b}"
    prompt_fragment = (
        f"output the string '{with_sep}' with the '{separator}' removed"
    )
    return CanaryToken(
        prompt_fragment=prompt_fragment,
        expected_output=expected,
        detector_pattern=re.escape(expected),
    )
