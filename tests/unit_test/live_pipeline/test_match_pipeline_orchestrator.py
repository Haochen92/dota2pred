"""Tests for MatchPipelineOrchestrator stage isolation."""

from unittest.mock import AsyncMock

import pytest

from live_orchestrator_app.app import MatchPipelineOrchestrator

pytestmark = pytest.mark.asyncio


def _build_orchestrator(odds_capture_enabled: bool = False) -> MatchPipelineOrchestrator:
    new_match = AsyncMock()
    new_match.run_new_match_cycle = AsyncMock(return_value=1)
    feature_engineering = AsyncMock()
    feature_engineering.run_feature_engineering_cycle = AsyncMock(return_value=1)
    prediction = AsyncMock()
    prediction.run_prediction_cycle = AsyncMock(return_value=1)
    completion = AsyncMock()
    completion.run_completion_cycle = AsyncMock(return_value=1)
    odds = AsyncMock()
    odds.run_odds_cycle = AsyncMock(return_value=1)
    notification = AsyncMock()
    notification.notify_state_change = AsyncMock()
    dlq = AsyncMock()
    dlq.run_retry_sweep = AsyncMock(return_value=None)

    return MatchPipelineOrchestrator(
        new_match_orchestrator=new_match,
        feature_engineering_orchestrator=feature_engineering,
        prediction_orchestrator=prediction,
        completion_orchestrator=completion,
        odds_orchestrator=odds,
        notification_service=notification,
        dlq_retry_service=dlq,
        odds_capture_enabled=odds_capture_enabled,
    )


async def test_all_stages_run_on_happy_path() -> None:
    app = _build_orchestrator()

    await app.run_cycle()

    app.new_match_orchestrator.run_new_match_cycle.assert_awaited_once()
    app.feature_engineering_orchestrator.run_feature_engineering_cycle.assert_awaited_once()
    app.prediction_orchestrator.run_prediction_cycle.assert_awaited_once()
    app.completion_orchestrator.run_completion_cycle.assert_awaited_once()
    app.notification_service.notify_state_change.assert_awaited_once()


async def test_failing_stage_does_not_skip_later_stages() -> None:
    app = _build_orchestrator()
    # Feature engineering blows up; prediction and completion must still run.
    app.feature_engineering_orchestrator.run_feature_engineering_cycle.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="feature_engineering"):
        await app.run_cycle()

    app.prediction_orchestrator.run_prediction_cycle.assert_awaited_once()
    app.completion_orchestrator.run_completion_cycle.assert_awaited_once()


async def test_notification_failure_does_not_propagate() -> None:
    app = _build_orchestrator()
    app.notification_service.notify_state_change.side_effect = RuntimeError("notify down")

    # A notification failure should not fail the cycle, and no stage failed.
    await app.run_cycle()

    app.completion_orchestrator.run_completion_cycle.assert_awaited_once()


async def test_odds_stage_skipped_when_disabled() -> None:
    app = _build_orchestrator(odds_capture_enabled=False)

    await app.run_cycle()

    # Default-off: the odds stage must never run, while the rest of the pipeline does.
    app.odds_orchestrator.run_odds_cycle.assert_not_awaited()
    app.completion_orchestrator.run_completion_cycle.assert_awaited_once()


async def test_odds_stage_runs_when_enabled() -> None:
    app = _build_orchestrator(odds_capture_enabled=True)

    await app.run_cycle()

    app.odds_orchestrator.run_odds_cycle.assert_awaited_once()


async def test_odds_stage_failure_does_not_break_pipeline() -> None:
    app = _build_orchestrator(odds_capture_enabled=True)
    app.odds_orchestrator.run_odds_cycle.side_effect = RuntimeError("odds boom")

    # The odds stage is terminal and isolated: its failure is surfaced (aggregated) but the
    # earlier stages still ran to completion.
    with pytest.raises(RuntimeError, match="odds"):
        await app.run_cycle()

    app.completion_orchestrator.run_completion_cycle.assert_awaited_once()
    app.prediction_orchestrator.run_prediction_cycle.assert_awaited_once()
