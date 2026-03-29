"""
Convenience entrypoint — delegates to the canonical worker in workflows/worker.py.

Usage: python -m listingjet.worker
"""
import asyncio

from listingjet.workflows.worker import main

if __name__ == "__main__":
    asyncio.run(main())
