"""Pydantic schema for YAML probe definitions."""

import re

from pydantic import BaseModel, Field, field_validator, model_validator

from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication


class YamlTurnSchema(BaseModel):
    """Schema for a single conversation turn."""

    prompt: str
    detect_after: bool = True


class YamlConversationSchema(BaseModel):
    """Schema for a multi-turn conversation."""

    turns: list[YamlTurnSchema] = Field(min_length=1)
    description: str = ""


class YamlProbeSchema(BaseModel):
    """Validated schema for a YAML probe definition.

    At least one of ``prompts`` or ``conversations`` must be present.
    All ``detector_patterns`` are validated as compilable regexes.
    """

    name: str = Field(min_length=1)
    category: ProbeCategory
    severity: Severity
    sophistication: Sophistication
    description: str = Field(min_length=1)
    prompts: list[str] = Field(default_factory=list)
    conversations: list[YamlConversationSchema] = Field(default_factory=list)
    detector_patterns: list[str] = Field(min_length=1)
    refusal_patterns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_has_prompts_or_conversations(self) -> "YamlProbeSchema":
        if not self.prompts and not self.conversations:
            raise ValueError(
                "Probe must define at least one of 'prompts' or 'conversations'"
            )
        return self

    @field_validator("detector_patterns", "refusal_patterns")
    @classmethod
    def _validate_regex_patterns(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"Invalid regex pattern '{pattern}': {exc}"
                ) from exc
        return patterns
