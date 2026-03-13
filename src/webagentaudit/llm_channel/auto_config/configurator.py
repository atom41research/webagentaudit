"""Algorithmic auto-configurator orchestrating input/submit/response discovery."""

from __future__ import annotations

import logging

from playwright.async_api import Frame, Page

from webagentaudit.core.models import ConfidenceScore

from ._frame_finder import FrameFinder
from ._input_finder import InputFinder
from ._response_finder import ResponseFinder
from ._selector_builder import SelectorBuilder
from ._submit_finder import SubmitFinder
from ._trigger_finder import TriggerFinder
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint, FrameCandidate, ScoredElement
from . import consts

logger = logging.getLogger(__name__)


class AlgorithmicAutoConfigurator(BaseAutoConfigurator):
    """Discovers chat element selectors using DOM analysis and interaction probing.

    Uses:
    - TriggerFinder: detect and click hidden panel buttons
    - FrameFinder: discover iframes containing chat widgets
    - InputFinder: heuristic scoring of candidate input elements
    - SubmitFinder: spatial proximity + label scoring of buttons
    - ResponseFinder: interactive DOM diffing after sending a probe
    - SelectorBuilder: constructs reusable CSS selectors
    """

    def __init__(self) -> None:
        self._selector_builder = SelectorBuilder()
        self._trigger_finder = TriggerFinder(self._selector_builder)
        self._frame_finder = FrameFinder()
        self._input_finder = InputFinder(self._selector_builder)
        self._submit_finder = SubmitFinder(self._selector_builder)
        self._response_finder = ResponseFinder(self._selector_builder)

    async def configure(
        self,
        page: Page | Frame,
        *,
        skip_response: bool = False,
        input_hint: ElementHint | None = None,
        submit_hint: ElementHint | None = None,
        response_hint: ElementHint | None = None,
    ) -> AutoConfigResult:
        """Run the full discovery pipeline.

        Pipeline: trigger -> frame discovery -> input -> submit -> response.
        Input is searched across the main page AND any discovered chat iframes.
        """
        result = AutoConfigResult()

        # Phase 0: Try to activate hidden panels (main page only)
        if isinstance(page, Page):
            trigger_result = await self._trigger_finder.find_and_activate(page)
            if trigger_result:
                result.trigger_used = trigger_result
                logger.info(
                    "Trigger activated: %s (mechanism=%s)",
                    trigger_result.trigger_selector,
                    trigger_result.mechanism.value,
                )

        # Phase 0.5: Discover chat iframes (main page only)
        contexts: list[tuple[Page | Frame, FrameCandidate | None]] = [(page, None)]
        if isinstance(page, Page):
            frame_candidates = await self._frame_finder.find_chat_frames(page)
            for fc in frame_candidates:
                contexts.append((fc.frame, fc))

        # Phase 1: Find input across all contexts (main page + iframes)
        best_input: ScoredElement | None = None
        best_context: Page | Frame = page
        best_frame_candidate: FrameCandidate | None = None

        for ctx, fc in contexts:
            ctx_label = "main page" if fc is None else f"iframe({fc.iframe_selector})"
            input_scored = await self._input_finder.find(ctx, hint=input_hint)
            if input_scored is not None:
                logger.debug(
                    "Input candidate in %s: %s (score=%.3f)",
                    ctx_label,
                    input_scored.candidate.selector,
                    input_scored.score,
                )
                if best_input is None or input_scored.score > best_input.score:
                    best_input = input_scored
                    best_context = ctx
                    best_frame_candidate = fc

        if best_input is None:
            logger.warning("Could not find any input element on the page or its iframes")
            return result

        # Store frame info if input was found in an iframe
        if best_frame_candidate is not None:
            result.discovery_frame = best_frame_candidate.frame
            result.iframe_selector = best_frame_candidate.iframe_selector
            logger.info(
                "Input found in iframe: %s", best_frame_candidate.iframe_selector
            )

        result.input_selector = best_input.candidate.selector
        result.input_confidence = ConfidenceScore(
            value=min(best_input.score / 0.8, 1.0)
        )
        logger.info(
            "Input found: %s (confidence=%.2f)",
            result.input_selector,
            result.input_confidence.value,
        )

        # Phase 2: Find submit button (in same context as input)
        submit_scored = await self._submit_finder.find(
            best_context, best_input.candidate, hint=submit_hint
        )
        if submit_scored is not None:
            result.submit_selector = submit_scored.candidate.selector
            result.submit_confidence = ConfidenceScore(
                value=min(submit_scored.score / 0.7, 1.0)
            )
            result.use_enter_to_submit = False
            logger.info(
                "Submit found: %s (confidence=%.2f)",
                result.submit_selector,
                result.submit_confidence.value,
            )
        else:
            result.use_enter_to_submit = True
            result.submit_confidence = ConfidenceScore(value=0.5)
            logger.info("No submit button found; will use Enter key")

        # Phase 3: Find response element (in same context as input)
        if skip_response:
            logger.info("Skipping response discovery (skip_response=True)")
        else:
            response_scored, response_text = await self._response_finder.find(
                best_context,
                input_selector=result.input_selector,
                submit_selector=result.submit_selector,
            )
            if response_scored is not None:
                result.response_selector = response_scored.candidate.selector
                result.response_confidence = ConfidenceScore(
                    value=min(response_scored.score / 0.7, 1.0),
                )
                result.test_message_used = consts.RESPONSE_PROBE_MESSAGE
                result.test_response_received = response_text
                logger.info(
                    "Response found: %s (confidence=%.2f)",
                    result.response_selector,
                    result.response_confidence.value,
                )
            else:
                logger.warning("Could not discover response element")

        return result
