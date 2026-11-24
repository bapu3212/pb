"""Shared enums and text helpers for request and response models."""

from __future__ import annotations

from enum import Enum


class AccidentType(str, Enum):
    DISEASE = "疾病"
    ACCIDENT = "意外"


class Gender(str, Enum):
    MALE = "男"
    FEMALE = "女"
    UNKNOWN = "未知"


class ExemptionCategory(str, Enum):
    MENTAL_BEHAVIORAL = "精神和行为障碍"
    CONGENITAL_CHROMOSOMAL = "先天性畸形、变形和染色体异常"
    REPRODUCTIVE = "生育相关"
    SEXUALLY_TRANSMITTED = "性病"
    NON_THERAPEUTIC_DENTAL = "非治疗性牙科"
    CLASS_A_B_INFECTIOUS = "甲乙类传染病"
    GENETIC = "遗传性疾病"
    REFRACTIVE_ERROR = "屈光不正"
    NON_DISEASE_TREATMENT = "非疾病治疗"
    HEALTH_CHECK = "健康检查"
    OCCUPATIONAL = "职业病"
    ORTHOPEDIC_CORRECTION = "矫形／矫正"
    COSMETIC = "美容"
    MEDICAL_CONSULTATION = "医疗咨询"
    PREVENTIVE_CARE = "预防性保健"
    ALOPECIA_AREATA = "斑秃"
    HAIR_LOSS = "脱发"
    TCM_PHYSIOTHERAPY = "中医理疗"
    PHYSICAL_THERAPY = "物理治疗"
    OTHER_REHABILITATION = "其他康复治疗"
    REFRACTIVE_EXAM = "屈光不正检查"
    SPECIAL_SERVICE = "特需"
    OTHER_NON_MEDICAL = "其他非医疗费用"
    DECOCTION = "煎药"
    PHYSICAL_EXAM = "体检"
    PHARMACY_COMMON_EXEMPTION = "药房常见免责"


def normalize_required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("字段不能为空")
    return value


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def deduplicate_non_empty(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        name = value.strip()
        if name and name not in seen:
            normalized.append(name)
            seen.add(name)
    return normalized
