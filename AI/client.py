"""Клиент модели. Без скрытого состояния.

Главное отличие от прежней версии: `complete()` ничего не запоминает.
Что отдали — то и ушло в запрос. История принадлежит сцене, а не клиенту,
иначе системные промпты разных персонажей копятся в одном списке и
начинают течь друг в друга.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")


class LLM:
    def __init__(self, model: str | None = None, api_key: str | None = None,
                 base_url: str = "https://openrouter.ai/api/v1") -> None:
        self.model = model or DEFAULT_MODEL
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY не задан (см. AI/.env)")
        self.client = OpenAI(base_url=base_url, api_key=key)

    # ------------------------------------------------------------------
    def complete(self, system: list[str], messages: list[dict],
                 temperature: float = 0.9, max_tokens: int = 300) -> str:
        """Один изолированный вызов.

        system[0] — стабильный префикс (личность). Он не меняется между
        репликами, поэтому помечается под кеш. Остальные блоки летучие.
        """
        payload = [self._system_message(system)] + messages
        r = self.client.chat.completions.create(
            model=self.model,
            messages=payload,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (r.choices[0].message.content or "").strip()

    # ------------------------------------------------------------------
    def _system_message(self, blocks: list[str]) -> dict:
        blocks = [b for b in blocks if b]
        # Явный cache_control понимают модели Anthropic через OpenRouter.
        # Для остальных провайдеров работает автоматический префиксный кеш,
        # поэтому стабильный блок всё равно должен идти первым.
        if self.model.startswith("anthropic/") and len(blocks) > 1:
            parts = [{"type": "text", "text": blocks[0],
                      "cache_control": {"type": "ephemeral"}}]
            parts += [{"type": "text", "text": b} for b in blocks[1:]]
            return {"role": "system", "content": parts}
        return {"role": "system", "content": "\n\n".join(blocks)}


# Совместимость со старым именем.
AIRole = LLM
