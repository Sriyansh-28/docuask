"""Optional LLM answer generation via any OpenAI-compatible free API.

When ``LLM_API_KEY`` is set, answers are synthesized from the retrieved passages
by whatever OpenAI-compatible endpoint you point at — Groq (default, free),
Google Gemini's OpenAI endpoint, OpenRouter, etc. Without a key (including in
CI), this module is inert and ``/ask`` falls back to the extractive answer, so
the app runs with no network access and no credentials.

Configure via env vars:
  LLM_API_KEY   – your free API key (required to enable generation)
  LLM_PROVIDER  – preset base URL + model: "groq" (default), "gemini",
                  or "openrouter". Sign-in for each is by email/Google, no
                  GitHub required.
  LLM_BASE_URL  – override the preset's OpenAI-compatible base URL
  LLM_MODEL     – override the preset's model id

The OpenAI SDK is imported lazily so the package is never a hard import-time
dependency of the API.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("docuask")

# Provider presets: (OpenAI-compatible base URL, default model). Pick one with
# LLM_PROVIDER; override the pieces individually with LLM_BASE_URL / LLM_MODEL.
_PRESETS = {
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.0-flash",
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
}

_provider = os.getenv("LLM_PROVIDER", "groq").lower()
_preset_base, _preset_model = _PRESETS.get(_provider, _PRESETS["groq"])
_BASE_URL = os.getenv("LLM_BASE_URL", _preset_base)
_MODEL = os.getenv("LLM_MODEL", _preset_model)

_SYSTEM = (
    "You are DocuAsk, a document question-answering assistant. Answer the "
    "user's question using ONLY the source passages provided from their "
    "document. If the passages do not contain the answer, say so plainly "
    "rather than guessing. Keep the answer concise — a few sentences at most. "
    "Do not invent facts."
)


def llm_available() -> bool:
    """True when an LLM API key is configured."""
    return bool(os.getenv("LLM_API_KEY"))


def generate_answer(question: str, passages: list[str]) -> str | None:
    """Return a grounded answer from the passages, or None to fall back.

    Never raises: a missing key, missing package, or any API error returns None
    so the caller can use the extractive answer.
    """
    if not llm_available():
        return None
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; using extractive answer")
        return None

    context = "\n\n".join(f"[Passage {i + 1}]\n{p}" for i, p in enumerate(passages))
    prompt = f"Source passages from the document:\n\n{context}\n\nQuestion: {question}"

    try:
        client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=_BASE_URL)
        response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=512,
            temperature=0.2,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:  # never let generation break /ask
        logger.warning("LLM generation failed, using extractive answer: %s", exc)
        return None

    text = (response.choices[0].message.content or "").strip()
    return text or None
