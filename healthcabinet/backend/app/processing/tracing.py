"""LangSmith tracing helpers for processing graph execution."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from langsmith import trace as langsmith_trace

from app.core.config import settings

logger = structlog.get_logger()


def is_tracing_enabled() -> bool:
    return settings.LANGSMITH_TRACING or os.getenv("LANGSMITH_TRACING", "").lower() == "true"


@asynccontextmanager
async def pipeline_trace(*, document_id: str, document_type: str) -> AsyncIterator[None]:
    """Wrap the extraction pipeline in a LangSmith trace when tracing is enabled."""
    if is_tracing_enabled():
        with langsmith_trace(
            name="document_extraction_pipeline",
            run_type="chain",
            project_name=settings.LANGSMITH_PROJECT,
            metadata={
                "document_id": document_id,
                "document_type": document_type,
            },
            tags=["extraction", document_type],
        ):
            logger.info(
                "processing.trace.start",
                document_id=document_id,
                document_type=document_type,
                project=settings.LANGSMITH_PROJECT,
            )
            yield
            logger.info(
                "processing.trace.end",
                document_id=document_id,
                document_type=document_type,
                project=settings.LANGSMITH_PROJECT,
            )
    else:
        yield
