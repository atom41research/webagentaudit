"""Script analysis checker for LLM-related patterns in JavaScript."""

from __future__ import annotations

import logging
import re

from ...core.enums import DetectionMethod
from ...core.models import ConfidenceScore
from ..consts import SIGNAL_WEIGHT_SCRIPT_ANALYSIS
from ..models import DetectionSignal, PageData
from .base import BaseSignalChecker

logger = logging.getLogger(__name__)

# Regex patterns that suggest LLM SDK usage or LLM-related JavaScript code.
SCRIPT_LLM_PATTERNS: list[re.Pattern[str]] = [
    # OpenAI / Anthropic / other LLM SDK references
    re.compile(r"openai", re.IGNORECASE),
    re.compile(r"anthropic", re.IGNORECASE),
    re.compile(r"@google/generative-ai", re.IGNORECASE),
    re.compile(r"cohere-ai", re.IGNORECASE),
    re.compile(r"langchain", re.IGNORECASE),
    re.compile(r"llamaindex", re.IGNORECASE),
    # WebSocket connections with chat/llm keywords
    re.compile(r"new\s+WebSocket\s*\([^)]*(?:chat|llm|ai|gpt|assistant)", re.IGNORECASE),
    re.compile(r"wss?://[^\s\"']*(?:chat|llm|ai-api|gpt|assistant)", re.IGNORECASE),
    # Streaming response handling (SSE, ReadableStream, EventSource)
    re.compile(r"new\s+EventSource\s*\(", re.IGNORECASE),
    re.compile(r"ReadableStream", re.IGNORECASE),
    re.compile(r"getReader\s*\(\s*\)", re.IGNORECASE),
    re.compile(r"text/event-stream", re.IGNORECASE),
    re.compile(r"data:\s*\[DONE\]", re.IGNORECASE),
    # Chat/completion API calls
    re.compile(r"fetch\s*\([^)]*(?:/chat/completions|/v\d+/messages|/v\d+/chat)", re.IGNORECASE),
    re.compile(r"(?:axios|fetch|XMLHttpRequest)[^;]*(?:chat/completions|/v\d+/messages)", re.IGNORECASE),
    re.compile(r"/api/v\d+/chat", re.IGNORECASE),
    re.compile(r"/api/chat/completions", re.IGNORECASE),
    re.compile(r"\.createChatCompletion", re.IGNORECASE),
    re.compile(r"\.chat\.completions\.create", re.IGNORECASE),
    re.compile(r"\.messages\.create", re.IGNORECASE),
    # Variable / identifier names suggesting LLM usage
    re.compile(r"\bchatbot\b", re.IGNORECASE),
    re.compile(r"\baiAssistant\b"),
    re.compile(r"\bllmClient\b"),
    re.compile(r"\bai_assistant\b", re.IGNORECASE),
    re.compile(r"\bllm_client\b", re.IGNORECASE),
    re.compile(r"\bchatCompletion\b"),
    re.compile(r"\bgptResponse\b"),
    re.compile(r"\bai_chat\b", re.IGNORECASE),
]


class ScriptAnalysisChecker(BaseSignalChecker):
    """Analyze inline and external script references for LLM-related patterns."""

    @property
    def name(self) -> str:
        return "script_analysis"

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        signals: list[DetectionSignal] = []

        # Collect script content from all available sources
        script_contents: list[str] = []

        # 1. Script src URLs
        for src in page_data.scripts:
            if src:
                script_contents.append(src)

        # 2. Inline scripts provided via page_data
        for code in page_data.inline_scripts:
            if code:
                script_contents.append(code)

        # 3. Extract inline scripts from HTML via BeautifulSoup
        if page_data.html:
            try:
                soup = page_data.get_soup()
                for tag in soup.find_all("script"):
                    content = tag.string
                    if content and content.strip():
                        script_contents.append(content)
            except Exception:
                logger.debug("Failed to parse HTML for script analysis")

        if not script_contents:
            return signals

        # Track already-seen (pattern_text, snippet) pairs to avoid duplicate signals
        seen: set[tuple[str, str]] = set()

        for content in script_contents:
            for pattern in SCRIPT_LLM_PATTERNS:
                try:
                    match = pattern.search(content)
                except Exception:
                    continue
                if not match:
                    continue

                # Build a context snippet around the match (up to 200 chars)
                start = max(0, match.start() - 60)
                end = min(len(content), match.end() + 60)
                snippet = content[start:end].strip()[:200]

                key = (pattern.pattern, snippet)
                if key in seen:
                    continue
                seen.add(key)

                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="llm_script_pattern",
                        description=f"Found LLM-related script pattern: {pattern.pattern}",
                        confidence=ConfidenceScore(value=SIGNAL_WEIGHT_SCRIPT_ANALYSIS),
                        evidence=snippet,
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={
                            "matched_pattern": pattern.pattern,
                        },
                    )
                )

        return signals
