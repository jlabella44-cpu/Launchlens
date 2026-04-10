"""Smoke-test the DollhouseRenderAgent's real OpenAI gpt-image-1.5 call.

Usage:
    OPENAI_API_KEY=sk-... python scripts/smoke_dollhouse_render.py \\
        FLOORPLAN.jpg ROOM1.jpg ROOM2.jpg [... up to 4 room photos]

Output: writes smoke_dollhouse.png next to the repo root.

Cost: ~$0.05 per run at medium quality, 1536x1024.
"""
import asyncio
import mimetypes
import sys
from pathlib import Path

from listingjet.providers.openai_dollhouse import (
    DOLLHOUSE_PROMPT,
    OpenAIDollhouseProvider,
)


def _load(path_str: str) -> tuple[str, bytes, str]:
    path = Path(path_str)
    if not path.exists():
        raise SystemExit(f"missing file: {path}")
    content_type = (
        mimetypes.guess_type(str(path))[0] or "image/png"
    )
    return path.name, path.read_bytes(), content_type


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    image_paths = sys.argv[1:]
    images = [_load(p) for p in image_paths[:5]]
    print(f"loaded {len(images)} images:")
    for name, data, ctype in images:
        print(f"  {name} — {len(data):,} bytes, {ctype}")

    provider = OpenAIDollhouseProvider()
    print(f"calling {provider._model} (size={provider._size}, quality={provider._quality})...")
    print(f"prompt:\n{DOLLHOUSE_PROMPT}\n")

    png = await provider.generate_from_bytes(images=images)

    out = Path("smoke_dollhouse.png")
    out.write_bytes(png)
    print(f"wrote {len(png):,} bytes to {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
