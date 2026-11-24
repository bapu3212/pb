"""Request and response models for medical claim review."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.common import (
    AccidentType,
    ExemptionCategory,
    Gender,
    deduplicate_non_empty,
    normalize_optional_text,
    normalize_required_text,
)


class MedicalItem(BaseModel):
    """One normalized line in a medical bill."""

    name: str = Field(..., min_length=1, max_length=200, description="药品或项目名称")
    item_type: str = Field(
        default="其他",
        max_length=50,
        description="药品、诊疗项目、检查检验、医用材料、其他等",
    )
    code: str | None = Field(default=None, max_length=100, description="院内或医保编码")
    unit_content: str | None = Field(
        default=None,
        max_length=100,
        description="每个计价单位包含的药品量或规格，例如 10g/瓶、250IU/支、30mg/片",
    )
    quantity: float | None = Field(default=None, ge=0, description="数量")
    unit_price: float | None = Field(default=None, ge=0, description="单价")
    amount: float | None = Field(default=None, ge=0, description="金额")
    notes: str | None = Field(default=None, max_length=1000, description="医嘱、诊断或其他说明")

    @field_validator("name", "item_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("code", "unit_content", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)


class ClaimReviewRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "medical_items": [
                        {
                            "name": "注射用头孢呋辛钠",
                            "item_type": "药品",
                            "code": "DRUG-CEFUROXIME-001",
                            "unit_content": "0.75g/瓶",
                            "quantity": 10,
                            "unit_price": 28.5,
                            "amount": 285.0,
                            "notes": "右小腿开放性外伤清创术后预防感染",
                        },
                        {
                            "name": "破伤风人免疫球蛋白",
                            "item_type": "药品",
                            "code": "DRUG-TIG-001",
                            "unit_content": "250IU/支",
                            "quantity": 1,
                            "unit_price": 168.0,
                            "amount": 168.0,
                            "notes": "外伤后预防破伤风",
                        },
                        {
                            "name": "硝苯地平控释片",
                            "item_type": "药品",
                            "code": "DRUG-NIFEDIPINE-001",
                            "unit_content": "30mg/片",
                            "quantity": 7,
                            "unit_price": 2.8,
                            "amount": 19.6,
                            "notes": "患者既往高血压，本次因交通事故入院，无血压控制不佳记录",
                        },
                        {
                            "name": "美容缝合",
                            "item_type": "诊疗项目",
                            "code": "TREATMENT-COSMETIC-SUTURE",
                            "quantity": 1,
                            "unit_price": 680.0,
                            "amount": 680.0,
                            "notes": "使用美容缝合材料处理面部裂伤",
                        },
                        {
                            "name": "健康体检套餐",
                            "item_type": "检查检验",
                            "code": "EXAM-HEALTH-CHECK",
                            "quantity": 1,
                            "unit_price": 360.0,
                            "amount": 360.0,
                            "notes": "入院体检项目，与本次外伤诊疗无直接针对性",
                        },
                        {
                            "name": "红外线治疗",
                            "item_type": "诊疗项目",
                            "code": "TREATMENT-INFRARED",
                            "quantity": 5,
                            "unit_price": 26.0,
                            "amount": 130.0,
                            "notes": "右小腿伤口局部理疗",
                        },
                    ],
                    "raw_bill_text": (
                        "头孢呋辛 1.5g 静滴 q8h 5天；破伤风人免疫球蛋白 250IU "
                        "肌注；硝苯地平控释片 30mg qd 7天；美容缝合 1次；"
                        "健康体检套餐 1次；红外线治疗 5次。"
                    ),
                    "accident_type": "意外",
                    "disease_names": ["右小腿开放性外伤", "面部裂伤", "高血压"],
                    "gender": "男",
                    "age": 46,
                    "additional_context": (
                        "患者骑电动车摔倒后入院，右小腿及面部受伤。"
                        "既往有高血压病史，本次未诉血压异常。"
                    ),
                }
            ]
        }
    )

    medical_items: list[MedicalItem] = Field(
        default_factory=list,
        max_length=200,
        description="结构化医疗清单；与 raw_bill_text 至少提供一项",
    )
    raw_bill_text: str | None = Field(
        default=None,
        max_length=50_000,
        description="原始账单文本；与 medical_items 至少提供一项",
    )
    accident_type: AccidentType = Field(..., description="疾病或意外")
    disease_names: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="可为一个或多个；为空时根据用药和项目推断",
    )
    gender: Gender = Field(..., description="男、女或未知")
    age: int = Field(..., ge=0, le=150, description="年龄，单位为周岁")
    additional_context: str | None = Field(
        default=None,
        max_length=5_000,
        description="可选补充信息，如事故经过、主要症状、既往史",
    )

    @field_validator("disease_names")
    @classmethod
    def normalize_disease_names(cls, values: list[str]) -> list[str]:
        return deduplicate_non_empty(values)

    @field_validator("raw_bill_text", "additional_context")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def require_bill_content(self) -> ClaimReviewRequest:
        if not self.medical_items and not self.raw_bill_text:
            raise ValueError("medical_items 和 raw_bill_text 不能同时为空")
        return self


class PrimaryDisease(BaseModel):
    name: str = Field(..., min_length=1, description="最主要疾病或损伤")
    confidence: float = Field(..., ge=0, le=1, description="主疾病判断置信度")
    basis: str = Field(..., min_length=1, description="简要判断依据，不包含内部思维过程")

    @field_validator("name", "basis")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return normalize_required_text(value)


class ItemReview(BaseModel):
    item_name: str = Field(..., min_length=1, description="对应账单中的药品或项目名称")
    item_type: str = Field(default="其他", description="药品、诊疗项目、检查检验等")
    reason: str = Field(..., min_length=1, description="不合理或免责的具体原因")
    related_disease: str | None = Field(default=None, description="相关疾病")
    exemption_category: ExemptionCategory | None = Field(
        default=None,
        description="免责项目对应的免责类别；不合理项目留空",
    )
    confidence: float = Field(..., ge=0, le=1, description="该项目判断置信度")

    @field_validator("item_name", "item_type", "reason")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("related_disease")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)


class LLMReviewPayload(BaseModel):
    """The exact JSON shape requested from the review model."""

    primary_disease: PrimaryDisease
    icd10_code: str = Field(..., description="ICD-10 编码；无法可靠编码时返回空字符串")
    icd10_name: str = Field(
        default="",
        description="ICD-10 标准名称；无法可靠编码时返回空字符串",
    )
    unreasonable_items: list[ItemReview] = Field(default_factory=list)
    exempt_items: list[ItemReview] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_exemption_categories(self) -> LLMReviewPayload:
        for item in self.exempt_items:
            if item.exemption_category is None:
                raise ValueError(f"免责项目 {item.item_name} 缺少 exemption_category")
        for item in self.unreasonable_items:
            if item.exemption_category is not None:
                raise ValueError(
                    f"不合理项目 {item.item_name} 不应填写 exemption_category"
                )
        return self


class ClaimReviewResponse(LLMReviewPayload):
    request_id: str
