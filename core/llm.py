from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import Settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

_CACHED_CLIENT: OpenAI | None = None
_CACHED_KEY: str | None = None


def _get_client(settings: Settings) -> OpenAI:
    """获取或复用 OpenAI 客户端实例。"""
    global _CACHED_CLIENT, _CACHED_KEY
    cache_key = f"{settings.llm_api_key}|{settings.llm_base_url}"
    if _CACHED_CLIENT is not None and _CACHED_KEY == cache_key:
        return _CACHED_CLIENT

    kw: dict[str, Any] = {"api_key": settings.llm_api_key or None}
    base = (settings.llm_base_url or "").strip()
    if base:
        kw["base_url"] = base
    _CACHED_CLIENT = OpenAI(**kw)
    _CACHED_KEY = cache_key
    return _CACHED_CLIENT


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object in model response")
    return json.loads(m.group())


_RETRYABLE = (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)


@retry(
    retry=retry_if_exception_type(_RETRYABLE),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
    before_sleep=lambda state: logger.warning(
        "LLM 调用失败 (%s), 第 %d 次重试...",
        state.outcome.exception() if state.outcome else "unknown",
        state.attempt_number,
    ),
    reraise=True,
)
def _create_completion(client: OpenAI, kwargs: dict[str, Any], model_name: str) -> Any:
    """带重试的 LLM 调用，仅重试可恢复的异常。"""
    try:
        return client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except BadRequestError:
        logger.warning("模型 %s 不支持 json_object 模式，回退普通请求", model_name)
        return client.chat.completions.create(**kwargs)


def completion_structured(
    settings: Settings,
    *,
    system: str,
    user: str,
    response_model: type[T],
    temperature: float = 0.2,
) -> T:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    client = _get_client(settings)
    kwargs: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
    }

    logger.debug("LLM 请求: model=%s, temperature=%.1f", settings.llm_model, temperature)
    completion = _create_completion(client, kwargs, settings.llm_model)

    content = completion.choices[0].message.content or ""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = _extract_json_object(content)
    return response_model.model_validate(data)
