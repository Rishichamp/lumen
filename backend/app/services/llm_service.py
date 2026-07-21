"""
LLM abstraction.

The rest of the app calls `LLMClient.generate(...)` and never imports an
SDK directly. This buys two things:
  1. Provider swap (OpenAI <-> Gemini <-> Kimi <-> a local vLLM server)
     is a one-file change, since all of them expose OpenAI-compatible
     chat-completions endpoints or a thin adapter can be added here.
  2. A safe extractive fallback when no API key is configured, so the
     app is still demoable/testable without paid credentials — it
     returns the most relevant retrieved passages verbatim instead of a
     generated answer, clearly labeled as such, rather than crashing or
     hallucinating without a model.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from openai import OpenAI

from app.core.config import get_settings

settings = get_settings()


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class OpenAICompatibleClient(LLMClient):
    """Works with OpenAI directly, or any OpenAI-compatible endpoint
    (Gemini/Kimi via compatibility shims, or a self-hosted vLLM server)
    by overriding `base_url`."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.client is None:
            raise RuntimeError("No API key configured for LLM client")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return response.choices[0].message.content or ""


class ExtractiveFallbackClient(LLMClient):
    """No-API-key mode: returns a clearly-labeled extractive answer built
    directly from the prompt's retrieved context, instead of failing the
    request. Used automatically when OPENAI_API_KEY is empty."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return (
            "⚠️ No LLM API key configured — showing the most relevant excerpt(s) "
            "retrieved from your library instead of a generated answer:\n\n"
            f"{user_prompt.split('CONTEXT:')[-1][:800].strip()}"
        )


def get_llm_client() -> LLMClient:
    if settings.OPENAI_API_KEY:
        return OpenAICompatibleClient(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_CHAT_MODEL)
    return ExtractiveFallbackClient()
