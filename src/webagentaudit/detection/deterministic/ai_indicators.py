"""AI indicator checker — data-driven detection of AI/LLM UI elements.

Patterns derived from analyzing 16+ real web pages with known LLM boxes.
See kb/domain/llm_interface_analysis.md for the corpus analysis.

Detects: sparkle SVG icons, AI button text/aria-labels, AI CSS classes,
assistant panel CSS variables, AI placeholder text, AI disclaimer text,
and chat widget container patterns.
"""

from __future__ import annotations

import logging
import re

from ...core.enums import DetectionMethod
from ...core.models import ConfidenceScore
from ..models import DetectionSignal, PageData
from .base import BaseSignalChecker

logger = logging.getLogger(__name__)

# --- Patterns derived from real-page corpus analysis ---

# Icon library CSS classes that indicate AI sparkle icons
SPARKLE_ICON_CLASSES = [
    "lucide-sparkles",
    "lucide-sparkle",
    "lucide-wand-sparkles",
    "heroicon-sparkles",
    "heroicon-o-sparkles",
    "heroicon-s-sparkles",
    "bi-stars",
    "bi-magic",
    "fa-wand-magic-sparkles",
    "fa-wand-sparkles",
    "tabler-sparkles",
    "tabler-wand",
    "phosphor-sparkle",
    "phosphor-magic-wand",
]

# Material Icons ligature text that indicates AI
MATERIAL_AI_LIGATURES = ["auto_awesome", "auto_fix_high", "smart_toy"]

# Button/link text patterns indicating AI features (case-insensitive)
AI_BUTTON_TEXT_PATTERNS = [
    re.compile(r"\bAsk\s+AI\b", re.IGNORECASE),
    re.compile(r"\bAI\s+Chat\b", re.IGNORECASE),
    re.compile(r"\bAI\s+Assistant\b", re.IGNORECASE),
    re.compile(r"\bAsk\s+.*\s+AI\b", re.IGNORECASE),  # "Ask Supabase AI"
    re.compile(r"\bChat\s+with\s+AI\b", re.IGNORECASE),
    re.compile(r"\bGenerate\s+with\s+AI\b", re.IGNORECASE),
    re.compile(r"\bWrite\s+with\s+AI\b", re.IGNORECASE),
    re.compile(r"\bAI\s+Copilot\b", re.IGNORECASE),
    re.compile(r"\bToggle\s+assistant\b", re.IGNORECASE),
]

# aria-label patterns (case-insensitive substring)
AI_ARIA_LABEL_PATTERNS = [
    re.compile(r"Ask\s+AI", re.IGNORECASE),
    re.compile(r"AI\s+(?:assistant|chat|copilot)", re.IGNORECASE),
    re.compile(r"Toggle\s+assistant", re.IGNORECASE),
    re.compile(r"Open\s+(?:AI|assistant)", re.IGNORECASE),
    re.compile(r"Send\s+message", re.IGNORECASE),
]

# CSS class substrings that indicate AI chat features
AI_CLASS_PATTERNS = [
    "chat-assistant",
    "ai-chat",
    "ai-assistant",
    "StripeAssistant",
    "copilot-",
    "phind-ai",
    "ai-agent",
]

# CSS variable names indicating hidden AI panels (checked in style attributes + inline styles)
AI_CSS_VARIABLE_PATTERNS = [
    re.compile(r"--assistant[_-](?:width|sheet|panel)", re.IGNORECASE),
    re.compile(r"--ai[_-](?:width|panel|sidebar)", re.IGNORECASE),
]

# Textarea/input placeholder patterns observed in real AI chat boxes
AI_PLACEHOLDER_PATTERNS = [
    re.compile(r"^Ask\b", re.IGNORECASE),  # "Ask me anything", "Ask a question..."
    re.compile(r"\bask\s+(?:me\s+)?anything\b", re.IGNORECASE),
    re.compile(r"\bask\s+a\s+question\b", re.IGNORECASE),
]

# Disclaimer text patterns that indicate AI-powered responses.
# These must be specific to avoid matching article text ABOUT AI.
AI_DISCLAIMER_PATTERNS = [
    # "Responses are generated using AI" — very specific, real Mintlify pattern
    re.compile(r"responses?\s+(?:are|may\s+be)\s+(?:generated|powered)\s+(?:using|by|with)\s+AI", re.IGNORECASE),
    # "may contain mistakes/inaccuracies" near "AI" — but require both
    re.compile(r"AI\b.{0,30}\bmay\s+(?:contain|have|produce)\s+(?:mistakes|errors|inaccuracies)", re.IGNORECASE),
]

# Chat widget container selectors (vendor-agnostic structural patterns)
CHAT_CONTAINER_SELECTORS = [
    # Fixed-position floating widgets
    'div[style*="position: fixed"][style*="z-index: 99999"]',
    'div[style*="position:fixed"][style*="z-index:99999"]',
    # Iframes with chat-related titles
    'iframe[title*="chat" i]',
    'iframe[title*="widget" i]',
    'iframe[title*="messenger" i]',
    # Known container IDs (from real pages)
    "#tidio-chat",
    "#intercom-container",
    "#drift-widget",
    "#hubspot-messages-iframe-container",
    "#fc_frame",
    "#crisp-chatbox",
    ".crisp-client",
]

# data-testid patterns indicating AI features
AI_DATA_TESTID_PATTERNS = [
    re.compile(r"ai-chat", re.IGNORECASE),
    re.compile(r"chat-(?:input|send|submit)", re.IGNORECASE),
    re.compile(r"prompt-textarea", re.IGNORECASE),
    re.compile(r"send-button", re.IGNORECASE),
]

# Confidence weights
WEIGHT_SPARKLE_ICON = 0.55
WEIGHT_AI_BUTTON = 0.70
WEIGHT_AI_ARIA_LABEL = 0.65
WEIGHT_AI_CLASS = 0.50
WEIGHT_AI_CSS_VAR = 0.45
WEIGHT_AI_PLACEHOLDER = 0.55
WEIGHT_AI_DISCLAIMER = 0.50
WEIGHT_CHAT_CONTAINER = 0.60
WEIGHT_AI_DATA_TESTID = 0.60


class AiIndicatorChecker(BaseSignalChecker):
    """Data-driven checker for AI/LLM UI indicators on web pages.

    Scans for sparkle icons, AI buttons, assistant panels, chat containers,
    and other patterns observed across 16+ real LLM-enabled pages.
    """

    @property
    def name(self) -> str:
        return "ai_indicators"

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        signals: list[DetectionSignal] = []

        if not page_data.html:
            return signals

        try:
            soup = page_data.get_soup()
        except Exception:
            logger.debug("Failed to parse HTML for AI indicator checking")
            return signals

        self._check_sparkle_icons(soup, signals)
        self._check_ai_buttons(soup, signals)
        self._check_ai_aria_labels(soup, signals)
        self._check_ai_classes(soup, signals)
        self._check_ai_css_variables(page_data.html, signals)
        self._check_ai_placeholders(soup, signals)
        self._check_ai_disclaimers(soup, signals)
        self._check_chat_containers(soup, signals)
        self._check_ai_data_testids(soup, signals)
        self._check_material_icon_ligatures(soup, signals)

        return signals

    def _check_sparkle_icons(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for AI sparkle/star SVG icons from known icon libraries."""
        for svg in soup.find_all("svg"):
            classes = svg.get("class", [])
            if isinstance(classes, str):
                classes = classes.split()
            for cls in classes:
                if any(sparkle in cls for sparkle in SPARKLE_ICON_CLASSES):
                    # Find context — what's the parent element?
                    parent = svg.parent
                    parent_text = parent.get_text(strip=True)[:60] if parent else ""
                    signals.append(
                        DetectionSignal(
                            checker_name=self.name,
                            signal_type="ai_sparkle_icon",
                            description=f"AI sparkle icon (class '{cls}') near '{parent_text}'",
                            confidence=ConfidenceScore(value=WEIGHT_SPARKLE_ICON),
                            evidence=f"SVG class='{cls}' in <{parent.name if parent else '?'}>",
                            method=DetectionMethod.DETERMINISTIC,
                            metadata={"icon_class": cls, "parent_text": parent_text},
                        )
                    )
                    return  # One sparkle is enough

        # Also check for polygon-based sparkle icons (8-point stars like Mintlify)
        for svg in soup.find_all("svg"):
            polygons = svg.find_all("polygon")
            for poly in polygons:
                points = poly.get("points", "")
                # 8-point polygon with symmetric star pattern
                point_count = len(points.split()) if points else 0
                if point_count >= 8:
                    parent = svg.parent
                    parent_tag = parent.name if parent else "?"
                    # Only signal if parent is interactive (button, a, etc.)
                    if parent_tag in ("button", "a", "label", "span", "div"):
                        parent_text = parent.get_text(strip=True)[:60] if parent else ""
                        parent_aria = parent.get("aria-label", "") if parent else ""
                        signals.append(
                            DetectionSignal(
                                checker_name=self.name,
                                signal_type="ai_sparkle_icon",
                                description=f"Sparkle polygon SVG in <{parent_tag}> '{parent_text or parent_aria}'",
                                confidence=ConfidenceScore(value=WEIGHT_SPARKLE_ICON),
                                evidence=f"polygon points count={point_count}",
                                method=DetectionMethod.DETERMINISTIC,
                                metadata={
                                    "parent_tag": parent_tag,
                                    "parent_text": parent_text,
                                    "parent_aria": parent_aria,
                                },
                            )
                        )
                        return

    def _check_ai_buttons(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for buttons/links with AI-related text."""
        for el in soup.find_all(["button", "a"]):
            text = el.get_text(strip=True)
            if len(text) > 100:
                continue  # Skip elements with too much text (likely containers)
            for pattern in AI_BUTTON_TEXT_PATTERNS:
                if pattern.search(text):
                    signals.append(
                        DetectionSignal(
                            checker_name=self.name,
                            signal_type="ai_button",
                            description=f"AI button/link: '{text[:60]}'",
                            confidence=ConfidenceScore(value=WEIGHT_AI_BUTTON),
                            evidence=f"<{el.name}> text='{text[:80]}'",
                            method=DetectionMethod.DETERMINISTIC,
                            metadata={"element_tag": el.name, "text": text[:100]},
                        )
                    )
                    return  # One AI button is enough

    def _check_ai_aria_labels(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for elements with AI-related aria-labels."""
        for el in soup.find_all(attrs={"aria-label": True}):
            aria = el.get("aria-label", "")
            for pattern in AI_ARIA_LABEL_PATTERNS:
                if pattern.search(aria):
                    signals.append(
                        DetectionSignal(
                            checker_name=self.name,
                            signal_type="ai_aria_label",
                            description=f"AI aria-label: '{aria}'",
                            confidence=ConfidenceScore(value=WEIGHT_AI_ARIA_LABEL),
                            evidence=f"<{el.name}> aria-label='{aria}'",
                            method=DetectionMethod.DETERMINISTIC,
                            metadata={"element_tag": el.name, "aria_label": aria},
                        )
                    )
                    return

    def _check_ai_classes(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for elements with AI-related CSS class names."""
        for pattern in AI_CLASS_PATTERNS:
            elements = soup.find_all(
                class_=lambda c: c and any(pattern in cls for cls in (c if isinstance(c, list) else c.split()))
            )
            if elements:
                el = elements[0]
                classes = " ".join(el.get("class", []))[:80]
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="ai_class",
                        description=f"AI CSS class pattern '{pattern}' found",
                        confidence=ConfidenceScore(value=WEIGHT_AI_CLASS),
                        evidence=f"<{el.name}> class='{classes}'",
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={"pattern": pattern, "element_tag": el.name},
                    )
                )
                return

    def _check_ai_css_variables(self, html: str, signals: list[DetectionSignal]) -> None:
        """Check for CSS custom properties indicating hidden AI panels."""
        for pattern in AI_CSS_VARIABLE_PATTERNS:
            match = pattern.search(html)
            if match:
                # Extract surrounding context
                start = max(0, match.start() - 30)
                end = min(len(html), match.end() + 30)
                context = html[start:end]
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="ai_css_variable",
                        description=f"AI panel CSS variable found: '{match.group()}'",
                        confidence=ConfidenceScore(value=WEIGHT_AI_CSS_VAR),
                        evidence=context,
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={"variable": match.group()},
                    )
                )
                return

    def _check_ai_placeholders(self, soup, signals: list[DetectionSignal]) -> None:
        """Check textarea/input placeholders with AI-related text."""
        for el in soup.find_all(["textarea", "input"]):
            placeholder = el.get("placeholder", "")
            if not placeholder:
                continue
            input_type = el.get("type", "")
            # Skip search inputs (not AI-specific)
            if input_type == "search":
                continue
            for pattern in AI_PLACEHOLDER_PATTERNS:
                if pattern.search(placeholder):
                    signals.append(
                        DetectionSignal(
                            checker_name=self.name,
                            signal_type="ai_placeholder",
                            description=f"AI input placeholder: '{placeholder}'",
                            confidence=ConfidenceScore(value=WEIGHT_AI_PLACEHOLDER),
                            evidence=f"<{el.name}> placeholder='{placeholder}'",
                            method=DetectionMethod.DETERMINISTIC,
                            metadata={
                                "element_tag": el.name,
                                "placeholder": placeholder,
                            },
                        )
                    )
                    return

        # Also check contenteditable elements with AI-related placeholder attr
        for el in soup.find_all(attrs={"contenteditable": "true"}):
            placeholder = el.get("placeholder", "")
            if placeholder:
                for pattern in AI_PLACEHOLDER_PATTERNS:
                    if pattern.search(placeholder):
                        signals.append(
                            DetectionSignal(
                                checker_name=self.name,
                                signal_type="ai_placeholder",
                                description=f"AI contenteditable placeholder: '{placeholder}'",
                                confidence=ConfidenceScore(value=WEIGHT_AI_PLACEHOLDER),
                                evidence=f"<{el.name} contenteditable> placeholder='{placeholder}'",
                                method=DetectionMethod.DETERMINISTIC,
                                metadata={
                                    "element_tag": el.name,
                                    "placeholder": placeholder,
                                    "contenteditable": True,
                                },
                            )
                        )
                        return

    def _check_ai_disclaimers(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for AI disclaimer text (e.g., 'generated using AI')."""
        page_text = soup.get_text()
        for pattern in AI_DISCLAIMER_PATTERNS:
            match = pattern.search(page_text)
            if match:
                start = max(0, match.start() - 20)
                end = min(len(page_text), match.end() + 20)
                context = page_text[start:end].strip()
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="ai_disclaimer",
                        description=f"AI disclaimer text found",
                        confidence=ConfidenceScore(value=WEIGHT_AI_DISCLAIMER),
                        evidence=context[:120],
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={"matched_pattern": pattern.pattern},
                    )
                )
                return

    def _check_chat_containers(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for chat widget container elements."""
        for selector in CHAT_CONTAINER_SELECTORS:
            try:
                elements = soup.select(selector)
            except Exception:
                continue
            if elements:
                el = elements[0]
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="chat_container",
                        description=f"Chat widget container: '{selector}'",
                        confidence=ConfidenceScore(value=WEIGHT_CHAT_CONTAINER),
                        evidence=f"<{el.name}> matched '{selector}'",
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={"selector": selector, "element_tag": el.name},
                    )
                )
                return

    def _check_ai_data_testids(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for data-testid attributes with AI patterns."""
        for el in soup.find_all(attrs={"data-testid": True}):
            testid = el.get("data-testid", "")
            for pattern in AI_DATA_TESTID_PATTERNS:
                if pattern.search(testid):
                    signals.append(
                        DetectionSignal(
                            checker_name=self.name,
                            signal_type="ai_data_testid",
                            description=f"AI data-testid: '{testid}'",
                            confidence=ConfidenceScore(value=WEIGHT_AI_DATA_TESTID),
                            evidence=f"<{el.name}> data-testid='{testid}'",
                            method=DetectionMethod.DETERMINISTIC,
                            metadata={"data_testid": testid, "element_tag": el.name},
                        )
                    )
                    return

    def _check_material_icon_ligatures(self, soup, signals: list[DetectionSignal]) -> None:
        """Check for Material Icons AI ligatures (auto_awesome, smart_toy)."""
        for el in soup.find_all(
            class_=lambda c: c and any("material" in cls for cls in (c if isinstance(c, list) else c.split()))
        ):
            text = el.get_text(strip=True)
            if text in MATERIAL_AI_LIGATURES:
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="ai_material_icon",
                        description=f"Material Icons AI ligature: '{text}'",
                        confidence=ConfidenceScore(value=WEIGHT_SPARKLE_ICON),
                        evidence=f"<{el.name}> class='material-*' text='{text}'",
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={"ligature": text},
                    )
                )
                return
