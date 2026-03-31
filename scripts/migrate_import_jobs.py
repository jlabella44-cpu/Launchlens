import asyncio
import os

import asyncpg


async def run():
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    c = await asyncpg.connect(url)
    await c.execute("""
        CREATE TABLE IF NOT EXISTS import_jobs (
            id UUID PRIMARY KEY,
            listing_id UUID NOT NULL,
            tenant_id UUID NOT NULL,
            url TEXT NOT NULL,
            platform VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            total_files INTEGER NOT NULL DEFAULT 0,
            completed_files INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    await c.execute("CREATE INDEX IF NOT EXISTS ix_import_jobs_listing_id ON import_jobs(listing_id)")
    await c.execute("CREATE INDEX IF NOT EXISTS ix_import_jobs_tenant_id ON import_jobs(tenant_id)")
    print("import_jobs table created")
    await c.close()

asyncio.run(run())
