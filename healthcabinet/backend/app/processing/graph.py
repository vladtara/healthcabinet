"""LangGraph-backed orchestration for document processing."""

import uuid
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncEngine

from app.processing.nodes import (
    extract_values,
    finalize_document,
    generate_interpretation,
    load_document,
    persist_values,
)
from app.processing.schemas import (
    ProcessingGraphFallbackState,
    ProcessingGraphRuntime,
    ProcessingGraphState,
)


class ProcessingGraphExecutionError(RuntimeError):
    """Raised when graph execution fails after populating fallback context."""

    def __init__(self, fallback_state: ProcessingGraphFallbackState) -> None:
        super().__init__("Processing graph execution failed")
        self.fallback_state = fallback_state


def _route_after_persist(
    state: ProcessingGraphState,
) -> Literal["generate_interpretation", "finalize_document"]:
    if state["normalized_values"]:
        return "generate_interpretation"
    return "finalize_document"


def _bind_node(
    node: Callable[..., Awaitable[dict[str, object]]],
    fallback_state: ProcessingGraphFallbackState,
) -> Callable[[ProcessingGraphState], Awaitable[dict[str, object]]]:
    @wraps(node)
    async def _bound_node(state: ProcessingGraphState) -> dict[str, object]:
        result = await node(state, fallback_state)
        # Clear error_stage/error_message only if they still reflect THIS node's
        # stamp-on-entry marker. If a node intentionally set them for downstream
        # consumption (e.g. soft-failure breadcrumbs), preserve the signal.
        # Exceptions in the wrapped node propagate without reaching this line,
        # keeping the failing stage's name intact for the worker's except branch.
        if fallback_state.error_stage == node.__name__:
            fallback_state.error_stage = None
            fallback_state.error_message = None
        return result

    return _bound_node


def _build_processing_graph(fallback_state: ProcessingGraphFallbackState) -> Any:
    workflow = StateGraph(ProcessingGraphState)
    workflow.add_node("load_document", cast(Any, _bind_node(load_document, fallback_state)))
    workflow.add_node("extract_values", cast(Any, _bind_node(extract_values, fallback_state)))
    workflow.add_node("persist_values", cast(Any, _bind_node(persist_values, fallback_state)))
    workflow.add_node(
        "generate_interpretation",
        cast(Any, _bind_node(generate_interpretation, fallback_state)),
    )
    workflow.add_node(
        "finalize_document",
        cast(Any, _bind_node(finalize_document, fallback_state)),
    )

    workflow.add_edge(START, "load_document")
    workflow.add_edge("load_document", "extract_values")
    workflow.add_edge("extract_values", "persist_values")
    workflow.add_conditional_edges(
        "persist_values",
        _route_after_persist,
        {
            "generate_interpretation": "generate_interpretation",
            "finalize_document": "finalize_document",
        },
    )
    workflow.add_edge("generate_interpretation", "finalize_document")
    workflow.add_edge("finalize_document", END)

    return workflow.compile()


def _build_initial_state(
    ctx: dict[str, object],
    document_id: str,
    fallback_state: ProcessingGraphFallbackState,
) -> ProcessingGraphState:
    return {
        "runtime": ProcessingGraphRuntime(
            db_engine=cast(AsyncEngine, ctx["db_engine"]),
            redis=ctx["redis"],
        ),
        "fallback": fallback_state,
        "document_id": uuid.UUID(document_id),
        "document_id_str": document_id,
        "user_id": None,
        "document_mime_type": None,
        "s3_key": None,
        "document_bytes": None,
        "extraction_result": None,
        "normalized_values": [],
        "measured_at": None,
        "partial_measured_at_text": None,
        "source_language": None,
        "raw_lab_name": None,
        "terminal_status": None,
        "terminal_event": None,
    }


async def run_processing_graph(ctx: dict[str, object], document_id: str) -> ProcessingGraphState:
    """Run the compiled LangGraph workflow for a document-processing job."""
    fallback_state = ProcessingGraphFallbackState()

    try:
        initial_state = _build_initial_state(ctx, document_id, fallback_state)
        processing_graph = _build_processing_graph(fallback_state)
        final_state = await processing_graph.ainvoke(initial_state)
    except Exception as exc:
        if fallback_state.error_stage is None:
            fallback_state.error_stage = "graph_initialization"
        fallback_state.error_message = str(exc)
        raise ProcessingGraphExecutionError(fallback_state) from exc

    return cast(ProcessingGraphState, final_state)
