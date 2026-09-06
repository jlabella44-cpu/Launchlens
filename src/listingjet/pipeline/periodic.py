"""Periodic maintenance tasks run in-process by `pipeline.runner.periodic_loop`.

These were previously Temporal cron workflows/activities; Task 9 removes
Temporal, so they run as plain coroutines on the pipeline worker's own
schedule instead. Both open an `admin_session()` (not `AsyncSessionLocal`)
because they are system actors that read/write across tenants.
"""


async def run_demo_cleanup() -> dict:
    from listingjet.database import admin_session
    from listingjet.services.demo_cleanup import cleanup_expired_demos
    from listingjet.services.storage import get_storage

    async with admin_session() as session:
        return await cleanup_expired_demos(session, storage=get_storage())


async def run_baseline_aggregation() -> dict:
    """Average LearningWeight across tenants per room_label into GlobalBaselineWeight.

    Ported from `workflows/baseline_aggregation.py`'s Temporal activity body.
    """
    from sqlalchemy import func, select

    from listingjet.database import admin_session
    from listingjet.models.global_baseline_weight import GlobalBaselineWeight
    from listingjet.models.learning_weight import LearningWeight

    async with admin_session() as session:
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
