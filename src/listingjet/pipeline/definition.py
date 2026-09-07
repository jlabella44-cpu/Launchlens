"""Declarative listing pipeline. Replaces workflows/listing_pipeline.py.

Each Step becomes one pipeline_jobs row when a listing is enqueued. A row is
runnable when every `requires` row is satisfied: done, skipped, or (failed and
that step is optional). The runner never inserts rows mid-flight.
"""
from dataclasses import dataclass

_MIN = 60


@dataclass(frozen=True)
class Step:
    name: str
    requires: tuple[str, ...] = ()
    timeout_s: int = 10 * _MIN
    max_attempts: int = 3
    optional: bool = False
    gate: str | None = None


PIPELINE: list[Step] = [
    # Phase 1: analysis
    Step("ingestion"),
    Step("photo_analysis", requires=("ingestion",), timeout_s=20 * _MIN),
    Step("property_verification", requires=("ingestion",), timeout_s=2 * _MIN, optional=True),
    Step("coverage", requires=("photo_analysis",)),
    Step("virtual_staging", requires=("coverage",), timeout_s=15 * _MIN, optional=True, gate="addon:virtual_staging"),
    Step("floorplan", requires=("coverage", "virtual_staging"), timeout_s=20 * _MIN),
    Step("dollhouse_render", requires=("floorplan",), optional=True),
    Step("packaging", requires=("floorplan", "dollhouse_render", "property_verification")),
    Step("video", requires=("packaging",), timeout_s=30 * _MIN, optional=True, gate="video"),
    # Human gate
    Step("await_review", requires=("packaging",), gate="review"),
    # Phase 2: post-approval
    Step("content_social", requires=("await_review",)),
    Step("brand", requires=("content_social",), optional=True),
    Step("social_cuts", requires=("video", "await_review"), optional=True),
    Step("mls_export", requires=("content_social", "brand"), timeout_s=15 * _MIN),
    Step("distribution", requires=("mls_export", "social_cuts")),
    # Phase 3: after delivery, all best-effort
    Step("microsite", requires=("distribution",), timeout_s=5 * _MIN, optional=True, gate="feature:microsite"),
    Step("learning", requires=("distribution",), optional=True, gate="feature:learning"),
    Step("social_event", requires=("distribution",), timeout_s=2 * _MIN, optional=True),
    Step("health_score", requires=("distribution",), timeout_s=2 * _MIN, optional=True, gate="feature:health_score"),
    Step("performance_intelligence", requires=("distribution",), timeout_s=2 * _MIN, optional=True,
         gate="feature:performance_intelligence"),
]


def validate_pipeline(steps: list[Step]) -> None:
    names = [s.name for s in steps]
    if len(names) != len(set(names)):
        raise ValueError("duplicate step names")
    known = set(names)
    for s in steps:
        for dep in s.requires:
            if dep not in known:
                raise ValueError(f"step {s.name!r} requires unknown step {dep!r}")
    topological_order(steps)  # raises on cycle


def topological_order(steps: list[Step]) -> list[str]:
    deps = {s.name: set(s.requires) for s in steps}
    order: list[str] = []
    while deps:
        ready = sorted(n for n, d in deps.items() if not d)
        if not ready:
            raise ValueError(f"cycle among steps: {sorted(deps)}")
        for n in ready:
            order.append(n)
            deps.pop(n)
        for d in deps.values():
            d.difference_update(ready)
    return order


def transitive_requires(name: str, steps: list[Step] = PIPELINE) -> set[str]:
    """Every step name reachable from `name` by following `requires` edges."""
    index = {s.name: s for s in steps}
    seen: set[str] = set()
    stack = list(index[name].requires)
    while stack:
        dep = stack.pop()
        if dep in seen:
            continue
        seen.add(dep)
        stack.extend(index[dep].requires)
    return seen


def post_review_steps(steps: list[Step] = PIPELINE) -> frozenset[str]:
    """Names whose transitive requires include the `await_review` gate."""
    return frozenset(s.name for s in steps if "await_review" in transitive_requires(s.name, steps))


validate_pipeline(PIPELINE)
STEP_INDEX: dict[str, Step] = {s.name: s for s in PIPELINE}
