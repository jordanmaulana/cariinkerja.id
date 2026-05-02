from functools import cache
from typing import TypeVar

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PromptManager:
    def __init__(self, default_model: str | None = None):
        self._client: OpenAI | None = None
        self._default_model = default_model or settings.OPENAI_MODEL

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def parse(
        self,
        *,
        system: str,
        user: str,
        response_format: type[T],
        model: str | None = None,
    ) -> T:
        resp = self.client.chat.completions.parse(
            model=model or self._default_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=response_format,
        )
        return resp.choices[0].message.parsed


@cache
def get_prompt_manager() -> PromptManager:
    return PromptManager()
