"""FastAPI application entry point."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable
from typing import TypeVar

from fastapi import FastAPI, HTTPException

from app.config import MODEL_NAME
from app.llm import (
    BailianCatalogMatchClient,
    BailianReviewClient,
    LLMServiceError,
    LLMTimeoutError,
)
from app.models import (
    CatalogMatchRequest,
    CatalogMatchResponse,
    ClaimReviewRequest,
    ClaimReviewResponse,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
ResultT = TypeVar("ResultT")

app = FastAPI(
    title="医疗清单智能审核 API",
    version="0.2.0",
    description=(
        "提供医疗清单智能审核，以及医疗费用明细的批量名称清洗和标准名称归一接口。"
        "两个接口均通过百炼 qwen3.8-flash 一次生成结构化结果。"
    ),
)
review_client = BailianReviewClient()
catalog_match_client = BailianCatalogMatchClient()


async def _call_llm(
    operation: str,
    request_id: str,
    awaitable: Awaitable[ResultT],
) -> ResultT:
    try:
        return await awaitable
    except LLMTimeoutError as exc:
        logger.warning("%s timeout request_id=%s", operation, request_id)
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except LLMServiceError as exc:
        logger.exception("%s failed request_id=%s", operation, request_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}


@app.post(
    "/api/v1/claim-reviews",
    response_model=ClaimReviewResponse,
    tags=["claim-review"],
    summary="审核医疗清单",
)
async def create_claim_review(payload: ClaimReviewRequest) -> ClaimReviewResponse:
    request_id = uuid.uuid4().hex
    logger.info(
        "claim review started request_id=%s items=%s raw_text=%s",
        request_id,
        len(payload.medical_items),
        bool(payload.raw_bill_text),
    )

    result = await _call_llm(
        "claim review",
        request_id,
        review_client.review(payload),
    )

    logger.info("claim review completed request_id=%s", request_id)
    return ClaimReviewResponse(
        request_id=request_id,
        **result.model_dump(),
    )


@app.post(
    "/api/v1/catalog-matches",
    response_model=CatalogMatchResponse,
    tags=["name-normalization"],
    summary="标准化医疗项目名称",
)
async def create_catalog_match(payload: CatalogMatchRequest) -> CatalogMatchResponse:
    request_id = uuid.uuid4().hex
    logger.info(
        "name normalization started request_id=%s items=%s raw_text=%s",
        request_id,
        len(payload.items),
        bool(payload.raw_bill_text),
    )

    result = await _call_llm(
        "name normalization",
        request_id,
        catalog_match_client.match(payload),
    )

    logger.info("name normalization completed request_id=%s", request_id)
    return CatalogMatchResponse(
        request_id=request_id,
        **result.model_dump(),
    )

