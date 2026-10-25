"""Optional local Gemma wording for PitchIQ's verified deterministic insights.

The deterministic summary remains the source of truth. Model output is stored
separately, is kept short, and is rejected when it introduces new numeric claims.
"""

from __future__ import annotations

import asyncio
import os
import re
from functools import lru_cache

MODEL_NAME = os.getenv("PITCHIQ_OLLAMA_MODEL", "gemma4:e2b-it-q4_K_M")


def _enabled() -> bool:
    value = os.getenv("PITCHIQ_USE_LOCAL_AI", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


async def _ask_gemma(prompt: str) -> str:
    # Lazy imports keep ordinary deterministic tests independent of Ollama.
    from agent_framework import Agent
    from agent_framework.ollama import OllamaChatClient

    host = os.getenv("OLLAMA_HOST", "").strip()
    client_options = {"model": MODEL_NAME}
    if host:
        client_options["host"] = host

    agent = Agent(
        client=OllamaChatClient(**client_options),
        name="PitchIQLocalStoryteller",
        instructions=(
            "Rewrite only the supplied verified football summary. Do not add "
            "facts, events, names, statistics, tactical explanations, motives, "
            "causal claims, or conclusions. Preserve uncertainty. Return only "
            "one concise paraphrase, with no heading or preamble."
        ),
    )
    result = await asyncio.wait_for(agent.run(prompt), timeout=60)
    text = getattr(result, "text", "")
    return text.strip() if isinstance(text, str) else ""


@lru_cache(maxsize=96)
def _generate_cached(prompt: str) -> str:
    # Streamlit calls the orchestrator synchronously; Ollama's client is async.
    return asyncio.run(_ask_gemma(prompt))


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))


def _clean_and_validate(candidate: str, source_summary: str) -> str:
    candidate = " ".join(candidate.strip().strip('"').split())
    if not candidate or len(candidate) > 400 or len(candidate.split()) > 55:
        return ""
    # Reject a paraphrase if it introduces any new numeric value.
    if not _numbers(candidate).issubset(_numbers(source_summary)):
        return ""
    return candidate


def add_local_ai_commentary(match: dict, insights: list[dict], audience: str) -> list[dict]:
    """Attach optional paraphrases without modifying verified narrative fields."""
    if not _enabled():
        for insight in insights:
            insight["ai_commentary"] = ""
            insight["ai_commentary_status"] = "disabled"
        return insights

    for insight in insights:
        source_summary = insight.get("summary", "")
        prompt = (
            f"Audience: {audience}.\n"
            "Task: paraphrase the verified summary in one concise sentence. "
            "Do not add any information. If you cannot preserve the meaning, "
            "repeat the source summary verbatim.\n"
            f"Verified summary (authoritative): {source_summary}\n"
            "Return only the paraphrase."
        )
        try:
            raw = _generate_cached(prompt)
            commentary = _clean_and_validate(raw, source_summary)
        except Exception:
            commentary = ""

        insight["ai_commentary"] = commentary
        insight["ai_commentary_status"] = "generated" if commentary else "fallback"

    return insights
