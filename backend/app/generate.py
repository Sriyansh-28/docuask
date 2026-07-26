"""Optional LLM answer generation.

When ``ANTHROPIC_API_KEY`` is set, answers are synthesized by Claude from the
retrieved passages — a grounded summary, with the source passage still shown in
the UI. Without a key (including in CI), this module is inert and ``/ask`` falls
back to the extractive answer, so the app runs and the tests pass with no
network access and no credentials.

The Anthropic SDK is imported lazily inside the call so the package is never a
hard import-time dependency of the API.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("docuask")

# Default to the latest, most capable model. Override with ANTHROPIC_MODEL
# (e.g. claude-sonnet-5 or claude-haiku-4-5) to trade quality for cost.
_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

_SYSTEM = (
    "You are DocuAsk, a document question-answering assistant. Answer the "
    "user's question using ONLY the source passages provided from their "
    "document. If the passages do not contain the answer, say so plainly "
    "rather than guessing. Keep the answer concise — a few sentences at most. "
    "Do not invent facts, and do not include internal or system XML tags in "
    "your response."
)


def llm_available() -> bool:
    """True when an Anthropic API key is configured."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def generate_answer(question: str, passages: list[str]) -> str | None:
    """Return a grounded answer from the passages, or None to fall back.

    Never raises: a missing key, missing package, network error, or model
    refusal all return None so the caller can use the extractive answer.
    """
    if not llm_available():
        return None
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed; using extractive answer")
        return None

    context = "\n\n".join(f"[Passage {i + 1}]\n{p}" for i, p in enumerate(passages))
    prompt = f"Source passages from the document:\n\n{context}\n\nQuestion: {question}"

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            system=_SYSTEM,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # never let generation break /ask
        logger.warning("LLM generation failed, using extractive answer: %s", exc)
        return None

    if getattr(response, "stop_reason", None) == "refusal":
        logger.info("LLM declined to answer; using extractive answer")
        return None

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    return text or None
