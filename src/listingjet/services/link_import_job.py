"""Runs a link-import job: downloads photos from a third-party link and
creates Asset records.

A plain coroutine invoked from a fire-and-forget background task in
`api/listings_import.py`.
"""
from __future__ import annotations

import dataclasses
import logging

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class LinkImportParams:
    listing_id: str
    tenant_id: str
    url: str
    platform: str
    import_job_id: str


async def run_link_import(params: LinkImportParams) -> dict:
    """Download photos from a third-party link and create Asset records."""

    from listingjet.database import admin_session
    from listingjet.models.asset import Asset
    from listingjet.models.import_job import ImportJob
    from listingjet.services.events import emit_event
    from listingjet.services.link_import import import_from_link
    from listingjet.services.storage import StorageService

    storage = StorageService()

    async with admin_session() as db:
        # Mark job as running
        job = await db.get(ImportJob, params.import_job_id)
        if job:
            job.status = "running"
            await db.commit()

        try:
            # Track progress via closure
            def _on_progress(completed: int, total: int) -> None:
                # Note: sync callback — we update the DB in bulk after import
                pass

            imported = await import_from_link(
                url=params.url,
                platform=params.platform,
                listing_id=params.listing_id,
                storage=storage,
                on_progress=_on_progress,
            )

            # Create Asset records for each imported file
            for item in imported:
                asset = Asset(
                    tenant_id=params.tenant_id,
                    listing_id=params.listing_id,
                    file_path=item["file_path"],
                    file_hash=item["file_hash"],
                    state="uploaded",
                )
                db.add(asset)

            # Update job status
            if job:
                job.status = "completed"
                job.total_files = len(imported)
                job.completed_files = len(imported)

            await emit_event(
                session=db,
                event_type="import.completed",
                payload={
                    "import_job_id": params.import_job_id,
                    "platform": params.platform,
                    "files_imported": len(imported),
                },
                tenant_id=params.tenant_id,
                listing_id=params.listing_id,
            )
            await db.commit()

            return {
                "import_job_id": params.import_job_id,
                "files_imported": len(imported),
                "status": "completed",
            }

        except Exception as exc:
            logger.exception(
                "Link import failed for job %s", params.import_job_id,
            )
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                await db.commit()
            return {
                "import_job_id": params.import_job_id,
                "files_imported": 0,
                "status": "failed",
                "error": str(exc)[:500],
            }
