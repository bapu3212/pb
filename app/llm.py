"""Async client for the Alibaba Cloud Bailian OpenAI-compatible API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.catalog_prompts import (
    CATALOG_MATCH_SYSTEM_PROMPT,
    build_catalog_match_user_prompt,
)
from app.config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    LLM_TIMEOUT_SECONDS,
    MODEL_NAME,
)
from app.models import (
    CatalogMatchRequest,
    ClaimReviewRequest,
    LLMCatalogMatchPayload,
    LLMReviewPayload,
)
from app.prompts import SYSTEM_PROMPT, build_user_prompt


logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMServiceError(RuntimeError):
    """Raised when the upstream model fails or returns invalid data."""


class LLMTimeoutError(LLMServiceError):
    """Raised when the upstream model times out."""


def _extract_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise LLMServiceError("模型未返回 JSON 对象") from None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMServiceError(f"模型返回的 JSON 无法解析：{exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMServiceError("模型返回结果不是 JSON 对象")
    return parsed


async def _request_json_object(
    system_prompt: str,
    user_prompt: str,
    *,
    enable_search: bool = False,
) -> dict[str, Any]:
    if not DASHSCOPE_API_KEY:
        raise LLMServiceError(
            "未配置百炼 API Key，请设置 DASHSCOPE_API_KEY 或创建 app/local_config.py"
        )

    request_body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "top_p": 0.8,
        "max_tokens": 4096,
        "stream": False,
        "response_format": {"type": "json_object"},
        "enable_thinking": False,
    }
    if enable_search:
        request_body["enable_search"] = True

    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    endpoint = f"{DASHSCOPE_BASE_URL.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                endpoint,
                headers=headers,
                json=request_body,
            )
    except httpx.TimeoutException as exc:
        raise LLMTimeoutError("百炼接口调用超时") from exc
    except httpx.HTTPError as exc:
        raise LLMServiceError(f"百炼接口连接失败：{exc}") from exc

    if response.status_code >= 400:
        if enable_search and response.status_code in (400, 422):
            logger.warning(
                "Bailian rejected enable_search with HTTP %s; retrying without search",
                response.status_code,
            )
            return await _request_json_object(
                system_prompt,
                user_prompt,
                enable_search=False,
            )
        detail = response.text[:1000]
        raise LLMServiceError(
            f"百炼接口返回 HTTP {response.status_code}：{detail}"
        )

    try:
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMServiceError("百炼接口响应结构不符合预期") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMServiceError("百炼接口返回了空内容")

    return _extract_json_object(content)


async def _request_validated_model(
    system_prompt: str,
    user_prompt: str,
    schema: type[ModelT],
    *,
    validation_label: str,
    enable_search: bool = False,
) -> ModelT:
    raw_payload = await _request_json_object(
        system_prompt,
        user_prompt,
        enable_search=enable_search,
    )
    try:
        return schema.model_validate(raw_payload)
    except ValidationError as exc:
        raise LLMServiceError(f"{validation_label} JSON 字段校验失败：{exc}") from exc


class BailianReviewClient:
    async def review(self, payload: ClaimReviewRequest) -> LLMReviewPayload:
        return await _request_validated_model(
            SYSTEM_PROMPT,
            build_user_prompt(payload),
            LLMReviewPayload,
            validation_label="模型",
        )


class BailianCatalogMatchClient:
    async def match(self, payload: CatalogMatchRequest) -> LLMCatalogMatchPayload:
        return await _request_validated_model(
            CATALOG_MATCH_SYSTEM_PROMPT,
            build_catalog_match_user_prompt(payload),
            LLMCatalogMatchPayload,
            validation_label="名称归一",
            enable_search=True,
        )

