# src/listingjet/providers/shadow.py
"""
Shadow-mode LLM provider.

Runs the *primary* (cheap/new) provider to serve the response, but also
fires the *truth* provider (typically Claude) in the background and logs
any divergence between the two outputs. Use this to validate that a new
provider (Qwen/Gemma) produces acceptable quality before cutting over
fully.

The background call's latency never affects the user request. Failures
in the truth call are swallowed and logged — shadow mode must never
degrade production.
"""
import asyncio
import logging

from .base import LLMProvider

logger = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> float:
    """Crude token-overlap similarity in [0, 1]. 1.0 == identical token sets."""
    ta, tb = set(a.lower().split()), set(b.lower().split())
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


class ShadowLLMProvider(LLMProvider):
    """Returns *primary*'s output, logs divergence from *truth*."""

    def __init__(
        self,
        primary: LLMProvider,
        truth: LLMProvider,
        *,
        similarity_threshold: float = 0.5,
        label: str = "shadow",
    ):
        self.primary = primary
        self.truth = truth
        self._threshold = similarity_threshold
        self._label = label

    async def complete(
        self,
        prompt: str,
        context: dict,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        primary_task = asyncio.create_task(
            self.primary.complete(prompt, context, temperature=temperature, system_prompt=system_prompt)
        )
        truth_task = asyncio.create_task(
            self._run_truth(prompt, context, temperature, system_prompt)
        )

        primary_result = await primary_task
        # Compare once truth completes, but don't block the caller.
        asyncio.create_task(self._compare(primary_result, truth_task, prompt))
        return primary_result

    async def _run_truth(self, prompt, context, temperature, system_prompt) -> str | None:
        try:
            return await self.truth.complete(
                prompt, context, temperature=temperature, system_prompt=system_prompt,
            )
        except Exception as exc:  # noqa: BLE001 - shadow must never raise
            logger.warning("shadow[%s] truth provider failed: %s", self._label, exc)
            return None

    async def _compare(self, primary_result: str, truth_task: asyncio.Task, prompt: str) -> None:
        try:
            truth_result = await truth_task
        except Exception as exc:  # noqa: BLE001
            logger.warning("shadow[%s] truth await failed: %s", self._label, exc)
            return
        if truth_result is None:
            return
        score = _similarity(primary_result, truth_result)
        if score < self._threshold:
            logger.info(
                "shadow[%s] divergence score=%.2f prompt_chars=%d primary_chars=%d truth_chars=%d",
                self._label, score, len(prompt), len(primary_result), len(truth_result),
            )
        from listingjet.monitoring.metrics import emit_metric
        emit_metric(
            "ShadowSimilarity",
            score,
            unit="None",
            dimensions={"label": self._label},
        )
