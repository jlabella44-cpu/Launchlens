"""
Convenience entrypoint — delegates to the canonical worker in workflows/worker.py.

Usage: python -m launchlens.worker
"""
import asyncio

from launchlens.workflows.worker import main

if __name__ == "__main__":
    asyncio.run(main())
