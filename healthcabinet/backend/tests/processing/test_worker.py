"""Unit tests for the thin ARQ processing worker boundary."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.processing.graph import ProcessingGraphExecutionError
from app.processing.schemas import ProcessingGraphFallbackState
from app.processing.worker import (
    WorkerSettings,
    process_document,
    reconcile_deleted_user_storage,
    shutdown,
    startup,
)


def _make_ctx(db_engine=None, redis=None):
    if redis is None:
        redis = MagicMock()
        redis.set = AsyncMock()
        redis.publish = AsyncMock()
    if db_engine is None:
        db_engine = MagicMock()
    return {"db_engine": db_engine, "redis": redis}


def _make_session_mock() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def _published_events(redis: MagicMock) -> list[str]:
    return [json.loads(call.args[1])["event"] for call in redis.publish.call_args_list]


@pytest.mark.asyncio
async def test_process_document_delegates_to_graph_runner():
    ctx = _make_ctx()
    document_id = str(uuid.uuid4())

    with patch("app.processing.worker.run_processing_graph", new=AsyncMock()) as run_graph:
        await process_document(ctx, document_id)

    run_graph.assert_awaited_once_with(ctx, document_id)
    assert ctx["redis"].publish.call_count == 0


@pytest.mark.asyncio
async def test_process_document_graph_failure_with_prior_values_marks_partial():
    ctx = _make_ctx()
    document_id = str(uuid.uuid4())
    status_updates: list[str] = []

    async def _update_status(db, doc_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.worker.run_processing_graph",
            new=AsyncMock(
                side_effect=ProcessingGraphExecutionError(
                    ProcessingGraphFallbackState(prior_values_existed=True)
                )
            ),
        ),
        patch(
            "app.processing.worker.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch("app.processing.worker.AsyncSession", return_value=_make_session_mock()),
    ):
        await process_document(ctx, document_id)

    assert status_updates == ["partial"]
    assert _published_events(ctx["redis"])[-1] == "document.partial"


@pytest.mark.asyncio
async def test_process_document_graph_failure_after_values_committed_marks_partial():
    ctx = _make_ctx()
    document_id = str(uuid.uuid4())
    status_updates: list[str] = []

    async def _update_status(db, doc_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.worker.run_processing_graph",
            new=AsyncMock(
                side_effect=ProcessingGraphExecutionError(
                    ProcessingGraphFallbackState(values_committed=True)
                )
            ),
        ),
        patch(
            "app.processing.worker.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch("app.processing.worker.AsyncSession", return_value=_make_session_mock()),
    ):
        await process_document(ctx, document_id)

    assert status_updates == ["partial"]
    assert _published_events(ctx["redis"])[-1] == "document.partial"


@pytest.mark.asyncio
async def test_process_document_fresh_graph_failure_marks_failed():
    ctx = _make_ctx()
    document_id = str(uuid.uuid4())
    status_updates: list[str] = []

    async def _update_status(db, doc_id, status):
        status_updates.append(status)

    with (
        patch(
            "app.processing.worker.run_processing_graph",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch(
            "app.processing.worker.document_repository.update_document_status_internal",
            side_effect=_update_status,
        ),
        patch("app.processing.worker.AsyncSession", return_value=_make_session_mock()),
    ):
        await process_document(ctx, document_id)

    assert status_updates == ["failed"]
    assert _published_events(ctx["redis"])[-1] == "document.failed"


@pytest.mark.asyncio
async def test_process_document_invalid_uuid_is_handled_without_crashing():
    ctx = _make_ctx()

    with (
        patch("app.processing.worker.run_processing_graph", new=AsyncMock()) as run_graph,
        patch(
            "app.processing.worker.document_repository.update_document_status_internal",
            new=AsyncMock(),
        ) as update_status,
    ):
        await process_document(ctx, "not-a-uuid")

    run_graph.assert_not_awaited()
    update_status.assert_not_awaited()
    assert ctx["redis"].publish.call_count == 0


@pytest.mark.asyncio
async def test_worker_startup_populates_ctx():
    ctx = {}
    mock_engine = MagicMock()
    mock_redis = MagicMock()

    with (
        patch("app.processing.worker.import_orm_models") as mock_import_models,
        patch("app.processing.worker.create_async_engine", return_value=mock_engine),
        patch("app.processing.worker.aioredis.from_url", return_value=mock_redis),
    ):
        await startup(ctx)

    mock_import_models.assert_called_once_with()
    assert ctx == {"db_engine": mock_engine, "redis": mock_redis}


@pytest.mark.asyncio
async def test_worker_shutdown_disposes_resources():
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()

    await shutdown({"db_engine": mock_engine, "redis": mock_redis})

    mock_engine.dispose.assert_awaited_once()
    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconcile_deleted_user_storage_deletes_prefix():
    with patch("app.processing.worker.delete_user_storage_prefix", return_value=2) as delete_prefix:
        await reconcile_deleted_user_storage(_make_ctx(), "user-id", "user-id/")

    delete_prefix.assert_called_once_with("user-id/")


@pytest.mark.asyncio
async def test_reconcile_deleted_user_storage_swallows_cleanup_failure():
    with patch(
        "app.processing.worker.delete_user_storage_prefix",
        side_effect=RuntimeError("boom"),
    ):
        await reconcile_deleted_user_storage(_make_ctx(), "user-id", "user-id/")


def test_worker_settings_functions():
    assert WorkerSettings.functions == [process_document, reconcile_deleted_user_storage]


def test_worker_settings_queues():
    assert WorkerSettings.queues == ["default", "priority"]
