"""Standalone learning workflow — runs LearningAgent for a listing after delivery."""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from listingjet.activities.pipeline import run_learning
    from listingjet.agents.base import AgentContext


_DEFAULT_RETRY = RetryPolicy(maximum_attempts=2)


@workflow.defn
class LearningWorkflow:
    """Run LearningAgent for a listing in isolation.

    Decoupled from ListingPipeline so learning failures never block delivery,
    and so learning can be triggered externally (batch jobs, replays).
    """

    @workflow.run
    async def run(self, ctx: AgentContext) -> dict:
        return await workflow.execute_activity(
            run_learning, ctx,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=_DEFAULT_RETRY,
        )
