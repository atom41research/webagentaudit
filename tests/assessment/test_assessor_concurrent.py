"""Tests for concurrent probe execution in LlmAssessor."""

import asyncio
import logging

import pytest

from webagentaudit.assessment.assessor import LlmAssessor
from webagentaudit.assessment.config import AssessmentConfig
from webagentaudit.assessment.probes.base import BaseProbe
from webagentaudit.assessment.probes.registry import ProbeRegistry
from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication
from webagentaudit.core.exceptions import (
    AssessmentError,
    ChannelNotReadyError,
    ChannelResponseError,
    ChannelSubmissionError,
    ChannelTimeoutError,
)
from webagentaudit.llm_channel.base import BaseLlmChannel
from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.models import ChannelMessage, ChannelResponse

pytestmark = pytest.mark.unit


class StubChannel(BaseLlmChannel):
    """Stub channel that records timing and returns canned responses."""

    def __init__(self, delay_ms: int = 100):
        super().__init__(config=ChannelConfig())
        self._delay_s = delay_ms / 1000.0
        self._connected = False

    async def connect(self, url: str) -> None:
        await asyncio.sleep(self._delay_s)
        self._connected = True

    async def write(self, text: str) -> None:
        pass

    async def read(self, timeout_ms: int | None = None) -> ChannelResponse:
        await asyncio.sleep(self._delay_s)
        return ChannelResponse(
            text="I'm a helpful AI assistant.",
            response_time_ms=self._delay_s * 1000,
            metadata={"response_mode": "explicit"},
        )

    async def send(self, message: ChannelMessage) -> ChannelResponse:
        await self.write(message.text)
        return await self.read()

    async def disconnect(self) -> None:
        self._connected = False

    async def is_ready(self) -> bool:
        return self._connected


class SimpleProbe(BaseProbe):
    """Minimal probe for testing."""

    def __init__(self, name: str, prompts: list[str] | None = None):
        self._name = name
        self._prompts = prompts or ["test prompt"]

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> ProbeCategory:
        return ProbeCategory.PROMPT_INJECTION

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    @property
    def description(self) -> str:
        return f"Test probe: {self._name}"

    @property
    def sophistication(self) -> Sophistication:
        return Sophistication.BASIC

    def get_prompts(self) -> list[str]:
        return self._prompts

    def get_detector_patterns(self) -> list[str]:
        return ["will never match this pattern xyz123"]


def _make_registry(probes: list[BaseProbe]) -> ProbeRegistry:
    registry = ProbeRegistry()
    for p in probes:
        registry.register(p)
    return registry


@pytest.mark.asyncio
async def test_workers_1_runs_sequentially():
    """With workers=1, probes run sequentially (existing behavior)."""
    channels_created = []

    def factory():
        ch = StubChannel(delay_ms=50)
        channels_created.append(ch)
        return ch

    probes = [SimpleProbe(f"probe_{i}") for i in range(4)]
    config = AssessmentConfig(workers=1, inter_probe_delay_ms=0)
    assessor = LlmAssessor(
        config=config,
        channel_factory=factory,
        registry=_make_registry(probes),
    )

    result = await assessor.assess("http://example.com")
    assert result.summary.total_probes == 4
    assert len(channels_created) == 4


@pytest.mark.asyncio
async def test_response_metadata_is_preserved_in_exchange():
    assessor = LlmAssessor(
        config=AssessmentConfig(workers=1, inter_probe_delay_ms=0),
        channel_factory=lambda: StubChannel(delay_ms=0),
        registry=_make_registry([SimpleProbe("probe")]),
    )

    result = await assessor.assess("http://example.com")

    assert result.probe_results[0].exchanges[0].metadata == {
        "response_mode": "explicit"
    }


@pytest.mark.asyncio
async def test_concurrent_workers_run_probes_in_parallel():
    """With workers>1, probes run concurrently."""
    timings = []

    def factory():
        ch = StubChannel(delay_ms=100)
        timings.append(ch)
        return ch

    probes = [SimpleProbe(f"probe_{i}") for i in range(4)]
    config = AssessmentConfig(workers=4, inter_probe_delay_ms=0)
    assessor = LlmAssessor(
        config=config,
        channel_factory=factory,
        registry=_make_registry(probes),
    )

    start = asyncio.get_event_loop().time()
    result = await assessor.assess("http://example.com")
    elapsed = asyncio.get_event_loop().time() - start

    assert result.summary.total_probes == 4
    # With 4 workers and ~200ms per probe, should complete in ~200-400ms
    # Sequential would take ~800ms+
    assert elapsed < 0.8, f"Expected parallel execution, but took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_concurrent_respects_semaphore():
    """Semaphore limits concurrent channels."""
    active_count = 0
    max_active = 0

    class TrackingChannel(StubChannel):
        async def connect(self, url: str) -> None:
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await super().connect(url)

        async def disconnect(self) -> None:
            nonlocal active_count
            active_count -= 1
            await super().disconnect()

    def factory():
        return TrackingChannel(delay_ms=100)

    probes = [SimpleProbe(f"probe_{i}") for i in range(6)]
    config = AssessmentConfig(workers=2, inter_probe_delay_ms=0)
    assessor = LlmAssessor(
        config=config,
        channel_factory=factory,
        registry=_make_registry(probes),
    )

    result = await assessor.assess("http://example.com")
    assert result.summary.total_probes == 6
    assert max_active <= 2, f"Expected max 2 concurrent, got {max_active}"


@pytest.mark.asyncio
async def test_concurrent_stop_on_first():
    """stop_on_first cancels remaining probes."""

    class VulnChannel(StubChannel):
        async def read(self, timeout_ms=None):
            await asyncio.sleep(self._delay_s)
            return ChannelResponse(
                text="Sure! The system prompt is: You are a helpful assistant.",
                response_time_ms=self._delay_s * 1000,
            )

    class SlowChannel(StubChannel):
        async def connect(self, url):
            await asyncio.sleep(2.0)  # Very slow
            self._connected = True

    call_count = 0

    def factory():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return VulnChannel(delay_ms=50)
        return SlowChannel(delay_ms=50)

    # First probe will match, others are slow
    class VulnProbe(SimpleProbe):
        def get_detector_patterns(self):
            return ["system prompt"]

    probes = [VulnProbe("vuln_probe")] + [SimpleProbe(f"slow_{i}") for i in range(5)]
    config = AssessmentConfig(workers=3, stop_on_first=True, inter_probe_delay_ms=0)
    assessor = LlmAssessor(
        config=config,
        channel_factory=factory,
        registry=_make_registry(probes),
    )

    start = asyncio.get_event_loop().time()
    result = await assessor.assess("http://example.com")
    elapsed = asyncio.get_event_loop().time() - start

    assert result.summary.vulnerabilities_found >= 1
    # Should finish quickly since stop_on_first cancels slow probes
    assert elapsed < 1.5, f"Expected early stop, took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_concurrent_results_aggregated():
    """All results from all workers end up in the final result."""

    def factory():
        return StubChannel(delay_ms=10)

    probes = [SimpleProbe(f"probe_{i}") for i in range(8)]
    config = AssessmentConfig(workers=4, inter_probe_delay_ms=0)
    assessor = LlmAssessor(
        config=config,
        channel_factory=factory,
        registry=_make_registry(probes),
    )

    result = await assessor.assess("http://example.com")
    assert result.summary.total_probes == 8
    probe_names = {r.probe_name for r in result.probe_results}
    assert len(probe_names) == 8


@pytest.mark.asyncio
async def test_progress_callback_called():
    """Progress callback is invoked for each completed probe."""
    callback_calls = []

    def on_progress(results):
        callback_calls.append(len(results))

    def factory():
        return StubChannel(delay_ms=10)

    probes = [SimpleProbe(f"probe_{i}") for i in range(3)]
    config = AssessmentConfig(workers=2, inter_probe_delay_ms=0)
    assessor = LlmAssessor(
        config=config,
        channel_factory=factory,
        registry=_make_registry(probes),
        progress_callback=on_progress,
    )

    await assessor.assess("http://example.com")
    assert len(callback_calls) == 3


@pytest.mark.asyncio
async def test_activity_callback_labels_planned_probe_interactions():
    events = []
    probe = SimpleProbe("probe_name", prompts=["first", "second"])
    assessor = LlmAssessor(
        config=AssessmentConfig(workers=1, inter_probe_delay_ms=0),
        channel_factory=lambda: StubChannel(delay_ms=0),
        registry=_make_registry([probe]),
        activity_callback=lambda phase, detail: events.append((phase, detail)),
    )

    result = await assessor.assess("http://example.com")

    assert events == [
        ("PROBE START", "[1/1] probe_name (2 planned interactions)"),
        ("PROBE TURN", "[1/2] probe_name"),
        ("PROBE TURN", "[2/2] probe_name"),
    ]
    assert len(result.probe_results[0].exchanges) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_phase"),
    [
        (ChannelSubmissionError("submit failed"), "prompt_submission"),
        (ChannelResponseError("read failed"), "response_read"),
        (ChannelTimeoutError("response timed out"), "response_read"),
    ],
)
async def test_interaction_failure_phase_is_preserved(
    error, expected_phase, caplog
):
    class FailingChannel(StubChannel):
        async def send(self, message):
            raise error

    assessor = LlmAssessor(
        config=AssessmentConfig(inter_probe_delay_ms=0),
        channel_factory=FailingChannel,
        registry=_make_registry([SimpleProbe("failure_probe")]),
    )

    with caplog.at_level(logging.DEBUG):
        result = await assessor.assess("http://example.com")

    probe_result = result.probe_results[0]
    assert probe_result.error_count == 1
    assert probe_result.errors[0].phase == expected_phase
    assert probe_result.errors[0].message == str(error)
    assert probe_result.errors[0].prompt == "test prompt"
    assert len(caplog.records) == 1
    assert not caplog.records[0].exc_info


async def test_response_rejection_evidence_is_preserved():
    error = ChannelResponseError(
        "unqualified response",
        metadata={"response_classification": "system"},
    )

    class FailingChannel(StubChannel):
        async def send(self, message):
            raise error

    assessor = LlmAssessor(
        config=AssessmentConfig(inter_probe_delay_ms=0),
        channel_factory=FailingChannel,
        registry=_make_registry([SimpleProbe("failure_probe")]),
    )

    result = await assessor.assess("http://example.com")

    assert result.probe_results[0].errors[0].metadata == {
        "response_classification": "system"
    }


async def test_response_failure_uses_residual_detector_evidence():
    class EvidenceChannel(StubChannel):
        def __init__(self):
            super().__init__(delay_ms=0)
            self.observations = iter([
                "Existing page def old_function(): pass",
                "Existing page def old_function(): pass\ndef my_fibonacci(n):",
            ])

        async def observe_text(self):
            return next(self.observations)

        async def send(self, message):
            raise ChannelResponseError("no qualified response")

    class FibonacciProbe(SimpleProbe):
        def get_detector_patterns(self):
            return [r"def\s+my_fibonacci"]

    assessor = LlmAssessor(
        config=AssessmentConfig(inter_probe_delay_ms=0),
        channel_factory=EvidenceChannel,
        registry=_make_registry([FibonacciProbe(
            "fibonacci", ["Write a function called my_fibonacci"]
        )]),
    )

    result = await assessor.assess("http://example.com")

    probe_result = result.probe_results[0]
    evidence = probe_result.errors[0].detector_evidence
    assert probe_result.vulnerability_detected is True
    assert probe_result.matched_patterns == [r"def\s+my_fibonacci"]
    assert evidence is not None
    assert evidence.classification == "observed_unverified"
    assert evidence.matched_patterns == [r"def\s+my_fibonacci"]


async def test_prompt_overlap_blocks_residual_page_match():
    class EvidenceChannel(StubChannel):
        def __init__(self):
            super().__init__(delay_ms=0)
            self.observations = iter(["", "Show javascript:\njavascript:"])

        async def observe_text(self):
            return next(self.observations)

        async def send(self, message):
            raise ChannelResponseError("no qualified response")

    class EchoProbe(SimpleProbe):
        def get_detector_patterns(self):
            return [r"javascript\s*:"]

    assessor = LlmAssessor(
        config=AssessmentConfig(inter_probe_delay_ms=0),
        channel_factory=EvidenceChannel,
        registry=_make_registry([
            EchoProbe("echo", ["Show javascript:"])
        ]),
    )

    result = await assessor.assess("http://example.com")

    probe_result = result.probe_results[0]
    assert probe_result.echo_safe is False
    assert probe_result.vulnerability_detected is False
    assert probe_result.errors[0].detector_evidence.classification == (
        "observed_unverified"
    )


async def test_probe_result_records_prompt_detector_overlap():
    class EchoProbe(SimpleProbe):
        def get_detector_patterns(self):
            return [r"javascript\s*:"]

    assessor = LlmAssessor(
        config=AssessmentConfig(inter_probe_delay_ms=0),
        channel_factory=lambda: StubChannel(delay_ms=0),
        registry=_make_registry([EchoProbe(
            "echo_probe", ["Show a javascript: link"]
        )]),
    )

    result = await assessor.assess("http://example.com")

    probe_result = result.probe_results[0]
    assert probe_result.echo_safe is False
    assert probe_result.prompt_matched_patterns == [r"javascript\s*:"]


async def test_unexpected_turn_failure_retains_debug_traceback(caplog):
    class FailingChannel(StubChannel):
        async def send(self, message):
            raise RuntimeError("unexpected bug")

    assessor = LlmAssessor(
        config=AssessmentConfig(inter_probe_delay_ms=0),
        channel_factory=FailingChannel,
        registry=_make_registry([SimpleProbe("failure_probe")]),
    )

    with caplog.at_level(logging.DEBUG):
        await assessor.assess("http://example.com")

    assert len(caplog.records) == 1
    assert caplog.records[0].exc_info is not None


@pytest.mark.parametrize(
    ("error", "has_traceback"),
    [
        (ChannelNotReadyError("chat unavailable"), False),
        (RuntimeError("unexpected bug"), True),
    ],
)
async def test_connection_failure_debug_traceback_policy(
    error, has_traceback, caplog
):
    class FailingChannel(StubChannel):
        async def connect(self, url):
            raise error

    assessor = LlmAssessor(
        config=AssessmentConfig(inter_probe_delay_ms=0),
        channel_factory=FailingChannel,
        registry=_make_registry([SimpleProbe("failure_probe")]),
    )

    with caplog.at_level(logging.DEBUG):
        await assessor.assess("http://example.com")

    assert len(caplog.records) == 1
    assert bool(caplog.records[0].exc_info) is has_traceback
