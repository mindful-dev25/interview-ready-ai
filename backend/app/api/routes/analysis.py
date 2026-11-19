import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_analysis_pipeline, get_llm_client, get_session_store
from app.api.session_helpers import load_session_or_404
from app.core.llm import LLMClient, LLMConfigurationError
from app.schemas import AnalysisRequest, AnalysisResponse, SessionState
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.analysis_progress import AnalysisProgress
from app.storage.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


@router.post("/analysis", response_model=AnalysisResponse)
async def create_analysis(
    request: AnalysisRequest,
    pipeline: AnalysisPipeline = Depends(get_analysis_pipeline),
    store: SessionStore = Depends(get_session_store),
    llm: LLMClient = Depends(get_llm_client),
) -> AnalysisResponse:
    _require_configured_llm(llm)
    session_id = str(uuid4())
    try:
        state = await pipeline.run(session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    await store.save(session_id, state)
    return _analysis_response(session_id, state)


@router.post("/analysis/stream")
async def stream_analysis(
    request: AnalysisRequest,
    pipeline: AnalysisPipeline = Depends(get_analysis_pipeline),
    store: SessionStore = Depends(get_session_store),
    llm: LLMClient = Depends(get_llm_client),
) -> StreamingResponse:
    """Run an analysis while reporting progress.

    The body is newline-delimited JSON: any number of ``{"type": "progress", ...}``
    events, then exactly one ``{"type": "result", "data": ...}`` (the same payload
    as ``POST /analysis``) or ``{"type": "error", "detail": ...}``.
    """
    _require_configured_llm(llm)
    session_id = str(uuid4())

    async def events() -> AsyncIterator[str]:
        updates: asyncio.Queue[AnalysisProgress | None] = asyncio.Queue()
        task = asyncio.create_task(pipeline.run(session_id, request, on_progress=updates.put_nowait))
        # The None wakes the loop below once the run has ended, whether it succeeded or failed.
        task.add_done_callback(lambda _task: updates.put_nowait(None))
        try:
            while (update := await updates.get()) is not None:
                yield _event("progress", **update.model_dump())
            state = task.result()
            await store.save(session_id, state)
            yield _event("result", data=_analysis_response(session_id, state).model_dump(mode="json"))
        except ValueError as exc:
            yield _event("error", detail=str(exc))
        except Exception as exc:
            logger.exception("Analysis %s failed.", session_id)
            yield _event("error", detail=f"Analysis failed: {exc}")
        finally:
            # If the client went away mid-run, stop the pipeline so it makes no further LLM calls.
            task.cancel()

    # no-transform and X-Accel-Buffering stop proxies in front (Next.js, a load balancer) from
    # compressing or buffering the stream, which would hold back the progress events.
    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/analysis/{session_id}", response_model=SessionState)
async def get_analysis(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> SessionState:
    return await load_session_or_404(store, session_id)


def _require_configured_llm(llm: LLMClient) -> None:
    """Fail up front when the LLM cannot be called.

    Every pipeline step falls back to generic output when its LLM call fails, so
    without this check a missing API key would produce a full set of generic
    answers instead of an error.
    """
    try:
        llm.ensure_configured()
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM not configured: {exc} Restart the server after editing backend/.env.",
        ) from exc


def _analysis_response(session_id: str, state: SessionState) -> AnalysisResponse:
    return AnalysisResponse(
        session_id=session_id,
        status=state.status,
        message="Draft answers are ready for review.",
        questions=state.questions,
        answers=state.answers,
        next_action="review_answers",
        metadata=state.metadata,
    )


def _event(kind: str, **fields: Any) -> str:
    return json.dumps({"type": kind, **fields}) + "\n"
