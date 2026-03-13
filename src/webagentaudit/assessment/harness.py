"""Assessment harness for running probes against a target."""

from .assessor import LlmAssessor
from .models import AssessmentResult


class AssessmentHarness:
    """High-level harness that wraps LlmAssessor with convenience methods."""

    def __init__(self, assessor: LlmAssessor) -> None:
        self._assessor = assessor

    async def run(self, url: str) -> AssessmentResult:
        return await self._assessor.assess(url)
