"""Request and response models for medical item name normalization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.common import (
    ReimbursementLevel,
    normalize_optional_text,
    normalize_required_text,
)


class CatalogRawItem(BaseModel):
    """One raw medical item name collected from a bill or HIS."""

    raw_name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="票据或原始采集数据中的药品、诊疗项目、耗材名称",
    )
    item_type: str = Field(
        default="其他",
        max_length=50,
        description="原始类型，如药品、诊疗项目、检查检验、医用耗材、其他",
    )
    raw_code: str | None = Field(
        default=None,
        max_length=100,
        description="原始院内编码、收费编码或医保编码",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="规格、厂家、包装、医嘱或其他可用于匹配的说明",
    )

    @field_validator("raw_name", "item_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("raw_code", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)


class CatalogMatchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "raw_name": "西力欣 0.75g 针",
                            "item_type": "药品",
                            "raw_code": "HIS-DRUG-001",
                            "notes": "商品名西力欣，注射用头孢呋辛钠",
                        },
                        {
                            "raw_name": "拜新同 控释片 30mg",
                            "item_type": "药品",
                            "notes": "硝苯地平控释片商品名",
                        },
                        {
                            "raw_name": "红外线治疗",
                            "item_type": "诊疗项目",
                        },
                        {
                            "raw_name": "一次性无菌注射器 5ml",
                            "item_type": "医用耗材",
                        },
                    ],
                    "raw_bill_text": (
                        "西力欣 0.75g 针；拜新同控释片 30mg；"
                        "红外线治疗 5次；一次性无菌注射器 5ml。"
                    ),
                    "province": "广东省",
                    "city": "深圳市",
                    "additional_context": "名称来自收费系统和纸质票据，存在商品名、缩写和错别字。",
                }
            ]
        }
    )

    items: list[CatalogRawItem] = Field(
        default_factory=list,
        max_length=200,
        description="待归一的原始药品、诊疗项目或耗材；与 raw_bill_text 至少提供一项",
    )
    raw_bill_text: str | None = Field(
        default=None,
        max_length=50_000,
        description="原始票据或账单文本；与 items 至少提供一项",
    )
    province: str | None = Field(
        default=None,
        max_length=50,
        description="医保目录所在省份；与 city 至少提供一项",
    )
    city: str | None = Field(
        default=None,
        max_length=50,
        description="医保目录所在城市；提供时优先按城市目录，否则按省份目录",
    )
    additional_context: str | None = Field(
        default=None,
        max_length=5_000,
        description="可选，采集来源、常见缩写、地区约定等补充信息",
    )

    @field_validator("raw_bill_text", "province", "city", "additional_context")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def require_match_content_and_region(self) -> CatalogMatchRequest:
        if not self.items and not self.raw_bill_text:
            raise ValueError("items 和 raw_bill_text 不能同时为空")
        if not self.province and not self.city:
            raise ValueError("province 和 city 至少提供一个")
        return self


class CatalogMatchCandidate(BaseModel):
    standard_name: str = Field(..., min_length=1, description="候选的标准目录名称")
    reason: str = Field(..., min_length=1, description="候选依据")
    confidence: float = Field(..., ge=0, le=1, description="候选可信度")

    @field_validator("standard_name", "reason")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return normalize_required_text(value)


class CatalogMatchItem(BaseModel):
    raw_name: str = Field(..., min_length=1, description="输入的原始名称")
    standard_name: str = Field(
        default="",
        description="标准化后的药品通用名或诊疗、耗材标准名称；无法确认时为空字符串",
    )
    confidence: float = Field(..., ge=0, le=1, description="匹配可信度")
    reimbursement_level: ReimbursementLevel = Field(
        ...,
        description="项目在适用医保目录中的报销等级：甲、乙或丙",
    )
    reimbursement_ratio: float = Field(
        ...,
        ge=0,
        le=1,
        description="按适用城市或省份医保目录得到的报销比例，例如 1.0、0.9、0.0",
    )
    basis: str = Field(
        ...,
        min_length=1,
        description="名称清洗、归一、适用地区医保目录和报销等级依据",
    )
    alternatives: list[CatalogMatchCandidate] = Field(
        default_factory=list,
        max_length=3,
        description="候选结果，按可信度排序",
    )

    @field_validator("raw_name", "basis")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("standard_name")
    @classmethod
    def strip_standard_name(cls, value: str) -> str:
        return value.strip()


class LLMCatalogMatchPayload(BaseModel):
    """The exact JSON shape requested from the name normalization model."""

    matches: list[CatalogMatchItem] = Field(
        ...,
        min_length=1,
        description="逐条名称清洗和标准名称归一结果",
    )


class CatalogMatchResponse(LLMCatalogMatchPayload):
    request_id: str
