"""Progress reporting for a running analysis."""

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

AnalysisPhase = Literal["resume", "job", "research", "draft"]
Stage = Literal["resume", "job", "research", "questions"]

# Rough share of the total time each stage takes; drafting gets the rest.
_STAGE_WEIGHTS: dict[Stage, int] = {"resume": 10, "job": 15, "research": 10, "questions": 20}
_DRAFTS_WEIGHT = 100 - sum(_STAGE_WEIGHTS.values())
# 100% is only reached when the result itself arrives.
_MAX_PERCENT_WHILE_RUNNING = 99


class AnalysisProgress(BaseModel):
    """One progress update sent to the client while an analysis runs."""

    phase: AnalysisPhase
    percent: int
    message: str


ProgressCallback = Callable[[AnalysisProgress], None]


class ProgressReporter:
    """Turns "this stage finished" calls from the pipeline into percent-and-message updates."""

    def __init__(self, on_progress: ProgressCallback | None = None) -> None:
        self._on_progress = on_progress
        self._finished: set[Stage] = set()
        self._drafts_total = 0
        self._drafts_done = 0

    def start(self) -> None:
        self._report()

    def finish(self, stage: Stage) -> None:
        self._finished.add(stage)
        self._report()

    def expect_drafts(self, total: int) -> None:
        self._drafts_total = total
        self._report()

    def draft_finished(self) -> None:
        self._drafts_done += 1
        self._report()

    def _report(self) -> None:
        if self._on_progress is None:
            return
        phase, message = self._current_activity()
        self._on_progress(AnalysisProgress(phase=phase, percent=self._percent(), message=message))

    def _percent(self) -> int:
        done = sum(_STAGE_WEIGHTS[stage] for stage in self._finished)
        if self._drafts_total:
            done += _DRAFTS_WEIGHT * self._drafts_done / self._drafts_total
        return min(_MAX_PERCENT_WHILE_RUNNING, round(done))

    def _current_activity(self) -> tuple[AnalysisPhase, str]:
        """The earliest step that has not finished yet (the resume and the job are read at the same time)."""
        finished = self._finished
        if "resume" not in finished and "job" not in finished:
            return "resume", "Reading the resume and the job posting"
        if "resume" not in finished:
            return "resume", "Reading the resume"
        if "job" not in finished:
            return "job", "Reading the job posting"
        if "research" not in finished:
            return "research", "Researching the company"
        if "questions" not in finished:
            return "draft", "Writing interview questions"
        if not self._drafts_total:
            return "draft", "Drafting answers"
        return "draft", f"Drafting answers ({self._drafts_done} of {self._drafts_total} done)"
