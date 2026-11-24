"""Offline API tests using a mocked model response."""

from unittest import TestCase
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import LLMCatalogMatchPayload, LLMReviewPayload


class ClaimReviewApiTests(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_medical_item_schema_uses_unit_content(self) -> None:
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        properties = response.json()["components"]["schemas"]["MedicalItem"]["properties"]
        self.assertIn("unit_content", properties)
        self.assertNotIn("unit", properties)

    def test_catalog_match_endpoint_is_exposed(self) -> None:
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/v1/catalog-matches", response.json()["paths"])

    def test_claim_review_with_mocked_model(self) -> None:
        model_result = LLMReviewPayload.model_validate(
            {
                "primary_disease": {
                    "name": "社区获得性肺炎",
                    "confidence": 0.93,
                    "basis": "抗菌治疗与胸部CT相符",
                },
                "icd10_code": "J18.9",
                "icd10_name": "肺炎，未特指",
                "unreasonable_items": [
                    {
                        "item_name": "维生素C片",
                        "item_type": "药品",
                        "reason": "无明确适应证",
                        "related_disease": None,
                        "exemption_category": None,
                        "confidence": 0.72,
                    }
                ],
                "exempt_items": [
                    {
                        "item_name": "健康体检套餐",
                        "item_type": "检查检验",
                        "reason": "属于健康检查免责范围",
                        "related_disease": None,
                        "exemption_category": "健康检查",
                        "confidence": 0.95,
                    }
                ],
            }
        )

        with patch(
            "app.main.review_client.review",
            new=AsyncMock(return_value=model_result),
        ):
            response = self.client.post(
                "/api/v1/claim-reviews",
                json={
                    "medical_items": [
                        {"name": "阿莫西林胶囊", "item_type": "药品"}
                    ],
                    "accident_type": "疾病",
                    "disease_names": ["社区获得性肺炎"],
                    "gender": "男",
                    "age": 42,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["icd10_code"], "J18.9")
        self.assertEqual(len(body["unreasonable_items"]), 1)
        self.assertEqual(body["exempt_items"][0]["exemption_category"], "健康检查")
        self.assertTrue(body["request_id"])
        for removed_field in (
            "inference_note",
            "warnings",
            "review_summary",
            "model",
            "disclaimer",
        ):
            self.assertNotIn(removed_field, body)

    def test_empty_bill_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/claim-reviews",
            json={
                "accident_type": "疾病",
                "disease_names": [],
                "gender": "未知",
                "age": 30,
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_catalog_match_with_mocked_model(self) -> None:
        model_result = LLMCatalogMatchPayload.model_validate(
            {
                "matches": [
                    {
                        "raw_name": "西力欣 0.75g 针",
                        "standard_name": "注射用头孢呋辛钠",
                        "confidence": 0.96,
                        "basis": "西力欣为头孢呋辛钠商品名，已去除规格和剂型描述",
                        "alternatives": [],
                    },
                    {
                        "raw_name": "红外线治疗",
                        "standard_name": "红外线治疗",
                        "confidence": 0.93,
                        "basis": "原始名称与标准诊疗项目名称一致",
                        "alternatives": [],
                    },
                ]
            }
        )

        with patch(
            "app.main.catalog_match_client.match",
            new=AsyncMock(return_value=model_result),
        ):
            response = self.client.post(
                "/api/v1/catalog-matches",
                json={
                    "items": [
                        {
                            "raw_name": "西力欣 0.75g 针",
                            "item_type": "药品",
                        },
                        {
                            "raw_name": "红外线治疗",
                            "item_type": "诊疗项目",
                        },
                    ],
                    "additional_context": "名称来自收费系统。",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["request_id"])
        self.assertEqual(len(body["matches"]), 2)
        self.assertEqual(body["matches"][0]["standard_name"], "注射用头孢呋辛钠")
        for removed_field in ("catalog_type", "catalog_code", "match_status"):
            self.assertNotIn(removed_field, body["matches"][0])

    def test_catalog_match_rejects_empty_input(self) -> None:
        response = self.client.post(
            "/api/v1/catalog-matches",
            json={
                "items": [],
            },
        )

        self.assertEqual(response.status_code, 422)
