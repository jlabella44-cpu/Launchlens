"""
Temporal cron workflow for global baseline weight aggregation.

Schedule: runs weekly via Temporal cron.
Aggregates LearningWeight across all tenants per room_label and updates
GlobalBaselineWeight. This ensures that industry-wide trends (e.g., drone
shots becoming more popular) are reflected in the default scoring for
new tenants.
"""
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@activity.defn
async def run_baseline_aggregation() -> dict:
    from sqlalchemy import func, select

    from launchlens.database import AsyncSessionLocal
    from launchlens.models.global_baseline_weight import GlobalBaselineWeight
    from launchlens.models.learning_weight import LearningWeight

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Average weight per room_label across all tenants
            result = await session.execute(
                select(
                    LearningWeight.room_label,
                    func.avg(LearningWeight.weight).label("avg_weight"),
                    func.count(LearningWeight.id).label("tenant_count"),
                )
                .group_by(LearningWeight.room_label)
                .having(func.count(LearningWeight.id) >= 3)  # Minimum 3 tenants for signal
            )
            rows = result.all()

            updated = 0
            for room_label, avg_weight, tenant_count in rows:
                existing = (await session.execute(
                    select(GlobalBaselineWeight).where(
                        GlobalBaselineWeight.room_label == room_label
                    )
                )).scalar_one_or_none()

                if existing:
                    existing.weight = round(float(avg_weight), 4)
                    existing.updated_at = func.now()
                else:
                    session.add(GlobalBaselineWeight(
                        room_label=room_label,
                        weight=round(float(avg_weight), 4),
                    ))
                updated += 1

    return {"updated": updated, "room_labels": len(rows)}


@workflow.defn
class BaselineAggregationWorkflow:
    """Cron workflow — Temporal schedules this weekly."""

    @workflow.run
    async def run(self) -> dict:
        return await workflow.execute_activity(
            run_baseline_aggregation,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
