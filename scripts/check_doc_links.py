"""Check that every relative markdown link in the repo points at a real file.

Walks *.md (skipping vendored and tool directories), extracts markdown links,
ignores external schemes and pure anchors, and resolves the rest relative to
the file that contains them. Prints each miss and exits 1 if there are any.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"node_modules", ".venv", ".next", ".superpowers", ".git"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
CODE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "//")


def markdown_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.md"):
        if SKIP_DIRS.isdisjoint(p.name for p in path.relative_to(ROOT).parents):
            files.append(path)
    return sorted(files)


def misses(path: Path) -> list[str]:
    text = CODE_RE.sub("", path.read_text(encoding="utf-8", errors="replace"))
    out = []
    for target in LINK_RE.findall(text):
        if target.startswith(EXTERNAL) or target.startswith("<"):
            continue
        target = target.split("?", 1)[0]
        if not target:
            continue
        resolved = (ROOT / target.lstrip("/")) if target.startswith("/") else (path.parent / target)
        if not resolved.exists():
            out.append(target)
    return out


def main() -> int:
    broken = 0
    for path in markdown_files():
        for target in misses(path):
            print(f"{path.relative_to(ROOT).as_posix()}: broken link -> {target}")
            broken += 1
    if broken:
        print(f"\n{broken} broken link(s)")
        return 1
    print("all relative markdown links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
