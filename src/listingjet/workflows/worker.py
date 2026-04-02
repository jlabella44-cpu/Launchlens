import asyncio
import json
import logging
import signal
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from listingjet.activities.pipeline import ALL_ACTIVITIES
from listingjet.config import settings
from listingjet.telemetry import init_tracing
from listingjet.workflows.baseline_aggregation import BaselineAggregationWorkflow, run_baseline_aggregation
from listingjet.workflows.demo_cleanup import DemoCleanupWorkflow, run_demo_cleanup
from listingjet.workflows.listing_pipeline import ListingPipeline
from listingjet.workflows.video_postprocess import VideoPostProcessWorkflow
from listingjet.activities.video_postprocess import run_append_endcard

logger = logging.getLogger(__name__)

# Health state shared between health server and worker
_health_state = {"ready": False, "shutting_down": False}

HEALTH_PORT = 8081


# ---------------------------------------------------------------------------
# Health check HTTP server (raw asyncio, no dependencies)
# ---------------------------------------------------------------------------

async def _handle_health_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle a single HTTP request on the health port."""
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        # Consume remaining headers
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if line in (b"\r\n", b"\n", b""):
                break
    except (asyncio.TimeoutError, ConnectionResetError):
        writer.close()
        return

    path = request_line.decode().split(" ")[1] if len(request_line.decode().split(" ")) > 1 else "/"

    if path == "/health":
        if _health_state["shutting_down"]:
            status, body = 503, {"status": "shutting_down"}
        elif _health_state["ready"]:
            status, body = 200, {"status": "ok"}
        else:
            status, body = 503, {"status": "starting"}
    elif path == "/ready":
        if _health_state["ready"] and not _health_state["shutting_down"]:
            status, body = 200, {"status": "ready"}
        else:
            status, body = 503, {"status": "not_ready"}
    else:
        status, body = 404, {"error": "not found"}

    response_body = json.dumps(body).encode()
    status_text = {200: "OK", 404: "Not Found", 503: "Service Unavailable"}.get(status, "Unknown")
    response = (
        f"HTTP/1.1 {status} {status_text}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(response_body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode() + response_body

    writer.write(response)
    await writer.drain()
    writer.close()


async def _start_health_server() -> asyncio.AbstractServer:
    server = await asyncio.start_server(_handle_health_request, "0.0.0.0", HEALTH_PORT)
    logger.info("Health check server listening on port %d", HEALTH_PORT)
    return server


# ---------------------------------------------------------------------------
# Temporal interceptors
# ---------------------------------------------------------------------------

def _get_interceptors() -> list:
    """Return Temporal interceptors. Adds tracing if opentelemetry is available."""
    interceptors = []
    try:
        from temporalio.contrib.opentelemetry import TracingInterceptor

        interceptors.append(TracingInterceptor())
        logger.info("Temporal TracingInterceptor enabled")
    except ImportError:
        logger.debug("temporalio opentelemetry contrib not available — skipping tracing interceptor")
    return interceptors


# ---------------------------------------------------------------------------
# Worker creation
# ---------------------------------------------------------------------------

async def create_worker() -> Worker:
    init_tracing()
    interceptors = _get_interceptors()
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
        interceptors=interceptors,
    )
    return Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ListingPipeline, DemoCleanupWorkflow, BaselineAggregationWorkflow, VideoPostProcessWorkflow],
        activities=[*ALL_ACTIVITIES, run_demo_cleanup, run_baseline_aggregation, run_append_endcard],
        interceptors=interceptors,
    )


# ---------------------------------------------------------------------------
# Cron schedule creation
# ---------------------------------------------------------------------------

async def _ensure_schedules(client: Client) -> None:
    """Create cron schedules if they don't already exist."""
    from temporalio.client import Schedule, ScheduleActionStartWorkflow, ScheduleIntervalSpec, ScheduleSpec

    schedules = [
        (
            "demo-cleanup-hourly",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    DemoCleanupWorkflow.run,
                    id="demo-cleanup",
                    task_queue=settings.temporal_task_queue,
                ),
                spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(hours=1))]),
            ),
        ),
        (
            "baseline-aggregation-weekly",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    BaselineAggregationWorkflow.run,
                    id="baseline-aggregation",
                    task_queue=settings.temporal_task_queue,
                ),
                spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(days=7))]),
            ),
        ),
    ]

    for schedule_id, schedule in schedules:
        try:
            await client.create_schedule(schedule_id, schedule)
            logger.info("Created schedule: %s", schedule_id)
        except Exception as exc:
            if "already exists" in str(exc).lower():
                logger.debug("Schedule %s already exists", schedule_id)
            else:
                logger.warning("Failed to create schedule %s: %s", schedule_id, exc)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

async def main():
    shutdown_event = asyncio.Event()
    shutdown_timeout = 30  # seconds

    # Start health check server
    health_server = await _start_health_server()

    # Create Temporal worker
    worker = await create_worker()

    # Mark as ready
    _health_state["ready"] = True
    logger.info("Worker ready — connected to Temporal at %s", settings.temporal_host)

    # Ensure cron schedules exist
    await _ensure_schedules(worker.client)

    # Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def _signal_handler(sig):
        logger.info("Received signal %s — initiating graceful shutdown", sig.name)
        _health_state["shutting_down"] = True
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler, sig)

    print(f"Worker started on queue: {settings.temporal_task_queue}")

    # Run worker until shutdown signal
    worker_task = asyncio.create_task(worker.run())
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    done, _ = await asyncio.wait(
        [worker_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if shutdown_event.is_set():
        logger.info("Graceful shutdown: stopping worker (timeout=%ds)...", shutdown_timeout)
        try:
            await asyncio.wait_for(worker.shutdown(), timeout=shutdown_timeout)
            logger.info("Worker stopped gracefully")
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout reached — forcing exit")
        except Exception as exc:
            logger.error("Error during shutdown: %s", exc)

    # Cleanup
    health_server.close()
    await health_server.wait_closed()
    _health_state["ready"] = False
    logger.info("Health server closed. Worker exit complete.")


if __name__ == "__main__":
    asyncio.run(main())
