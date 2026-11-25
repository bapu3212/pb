# 医疗清单智能审核与名称归一 API

基于 FastAPI、Pydantic v2 和百炼 `qwen3.8-flash` 的医疗账单处理服务。每个接口只调用一次模型，并严格校验模型返回的 JSON 结构。

## 接口总览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/v1/claim-reviews` | 医疗清单智能审核 |
| `POST` | `/api/v1/catalog-matches` | 医疗项目名称批量归一 |

接口文档：<http://127.0.0.1:8000/docs>

## 运行

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

运行测试：

```powershell
python -m unittest discover -v
```

## 医疗清单审核

`POST /api/v1/claim-reviews`

输入字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `medical_items` | `array` | 否 | 结构化医疗清单，与 `raw_bill_text` 至少提供一项 |
| `raw_bill_text` | `string` | 否 | 原始账单文本，与 `medical_items` 至少提供一项 |
| `accident_type` | `string` | 是 | `疾病` 或 `意外` |
| `disease_names` | `string[]` | 是 | 可多个，可为空；为空时由用药和项目推断 |
| `gender` | `string` | 是 | `男`、`女` 或 `未知` |
| `age` | `integer` | 是 | 周岁，范围 `0-150` |
| `additional_context` | `string` | 否 | 事故经过、症状、既往史等补充信息 |

`medical_items` 每项字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | `string` | 是 | 药品或项目原始名称 |
| `item_type` | `string` | 否 | 药品、诊疗项目、检查检验、医用材料等，默认 `其他` |
| `code` | `string` | 否 | 院内或医保编码 |
| `unit_content` | `string` | 否 | 每个计价单位包含的规格，如 `10g/瓶`、`30mg/片` |
| `quantity` | `number` | 否 | 数量 |
| `unit_price` | `number` | 否 | 计价单位价格 |
| `amount` | `number` | 否 | 金额 |
| `notes` | `string` | 否 | 医嘱、诊断或其他说明 |

请求示例：

```json
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
      "notes": "右小腿开放性外伤清创术后预防感染"
    },
    {
      "name": "破伤风人免疫球蛋白",
      "item_type": "药品",
      "code": "DRUG-TIG-001",
      "unit_content": "250IU/支",
      "quantity": 1,
      "unit_price": 168.0,
      "amount": 168.0,
      "notes": "外伤后预防破伤风"
    },
    {
      "name": "硝苯地平控释片",
      "item_type": "药品",
      "code": "DRUG-NIFEDIPINE-001",
      "unit_content": "30mg/片",
      "quantity": 7,
      "unit_price": 2.8,
      "amount": 19.6,
      "notes": "患者既往高血压，本次因交通事故入院，无血压控制不佳记录"
    },
    {
      "name": "美容缝合",
      "item_type": "诊疗项目",
      "code": "TREATMENT-COSMETIC-SUTURE",
      "quantity": 1,
      "unit_price": 680.0,
      "amount": 680.0,
      "notes": "使用美容缝合材料处理面部裂伤"
    },
    {
      "name": "健康体检套餐",
      "item_type": "检查检验",
      "code": "EXAM-HEALTH-CHECK",
      "quantity": 1,
      "unit_price": 360.0,
      "amount": 360.0,
      "notes": "入院体检项目，与本次外伤诊疗无直接针对性"
    },
    {
      "name": "红外线治疗",
      "item_type": "诊疗项目",
      "code": "TREATMENT-INFRARED",
      "quantity": 5,
      "unit_price": 26.0,
      "amount": 130.0,
      "notes": "右小腿伤口局部理疗"
    }
  ],
  "raw_bill_text": "头孢呋辛 1.5g 静滴 q8h 5天；破伤风人免疫球蛋白 250IU 肌注；硝苯地平控释片 30mg qd 7天；美容缝合 1次；健康体检套餐 1次；红外线治疗 5次。",
  "accident_type": "意外",
  "disease_names": ["右小腿开放性外伤", "面部裂伤", "高血压"],
  "gender": "男",
  "age": 46,
  "additional_context": "患者骑电动车摔倒后入院，右小腿及面部受伤。既往有高血压病史，本次未诉血压异常。"
}
```

也可以只传 `raw_bill_text`：

```json
{
  "raw_bill_text": "阿莫西林胶囊 0.5g 口服 每日2次 5天；胸部CT平扫 1次",
  "accident_type": "疾病",
  "disease_names": [],
  "gender": "女",
  "age": 35
}
```

返回字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次请求标识 |
| `primary_disease` | 最主要疾病或损伤、置信度和判断依据 |
| `icd10_code` | ICD-10 编码，无法可靠编码时为空字符串 |
| `icd10_name` | ICD-10 标准名称，无法可靠编码时为空字符串 |
| `unreasonable_items` | 不合理用药或项目 |
| `exempt_items` | 免责用药或项目及固定免责类别 |

返回示例：

```json
{
  "request_id": "7f7f0c8927f1488d9a5f8e5f0f2d7d7e",
  "primary_disease": {
    "name": "右小腿开放性外伤",
    "confidence": 0.96,
    "basis": "病历明确为骑电动车摔倒后的右小腿开放性损伤，清创及抗感染治疗均围绕该损伤"
  },
  "icd10_code": "S81.8",
  "icd10_name": "小腿开放性伤口，其他特指部位",
  "unreasonable_items": [
    {
      "item_name": "硝苯地平控释片",
      "item_type": "药品",
      "reason": "本次为意外外伤，账单和补充信息未提示高血压急性发作或需要调整降压治疗，该药与外伤诊疗无直接关系",
      "related_disease": "高血压",
      "exemption_category": null,
      "confidence": 0.88
    }
  ],
  "exempt_items": [
    {
      "item_name": "美容缝合",
      "item_type": "诊疗项目",
      "reason": "使用美容缝合材料以改善面部瘢痕外观，项目包含美容属性",
      "related_disease": "面部裂伤",
      "exemption_category": "美容",
      "confidence": 0.91
    },
    {
      "item_name": "健康体检套餐",
      "item_type": "检查检验",
      "reason": "属于入院健康检查项目，并非针对右小腿或面部外伤的必要诊断检查",
      "related_disease": null,
      "exemption_category": "健康检查",
      "confidence": 0.95
    },
    {
      "item_name": "红外线治疗",
      "item_type": "诊疗项目",
      "reason": "属于物理治疗项目，按给定免责范围列入物理治疗",
      "related_disease": "右小腿开放性外伤",
      "exemption_category": "物理治疗",
      "confidence": 0.9
    }
  ]
}
```

## 医疗项目名称归一

`POST /api/v1/catalog-matches`

将票据、HIS 或收费清单中的商品名、简称、错别字、规格和收费名称清洗为标准药品通用名、医疗服务项目名称或医用耗材名称，并按适用地区医保目录输出报销等级和报销比例。医保三目录固定指：医保药品目录 + 医疗服务项目目录 + 医用耗材目录。

地区目录优先级：提供 `city` 时优先按城市医保目录；未提供 `city` 时按 `province` 省级医保目录。

输入字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `items` | `array` | 否 | 待归一项目，与 `raw_bill_text` 至少提供一项 |
| `raw_bill_text` | `string` | 否 | 原始票据文本，与 `items` 至少提供一项 |
| `province` | `string` | 条件必填 | 医保目录所在省份，与 `city` 至少提供一个 |
| `city` | `string` | 条件必填 | 医保目录所在城市，提供时优先按城市目录，否则按省份目录 |
| `additional_context` | `string` | 否 | 采集来源、常见缩写、地区约定等 |

`items` 每项字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `raw_name` | `string` | 是 | 原始药品、诊疗项目或耗材名称 |
| `item_type` | `string` | 否 | 药品、诊疗项目、检查检验、医用耗材等 |
| `raw_code` | `string` | 否 | 原始院内、收费或医保编码 |
| `notes` | `string` | 否 | 规格、厂家、包装、医嘱等辅助信息 |

请求示例：

```json
{
  "items": [
    {
      "raw_name": "西力欣 0.75g 针",
      "item_type": "药品",
      "raw_code": "HIS-DRUG-001",
      "notes": "商品名西力欣，注射用头孢呋辛钠"
    },
    {
      "raw_name": "拜新同 控释片 30mg",
      "item_type": "药品",
      "notes": "硝苯地平控释片商品名"
    },
    {
      "raw_name": "红外线治疗",
      "item_type": "诊疗项目"
    },
    {
      "raw_name": "一次性无菌注射器 5ml",
      "item_type": "医用耗材"
    }
  ],
  "raw_bill_text": "西力欣 0.75g 针；拜新同控释片 30mg；红外线治疗 5次；一次性无菌注射器 5ml。",
  "province": "广东省",
  "city": "深圳市",
  "additional_context": "名称来自收费系统和纸质票据，存在商品名、缩写和错别字。"
}
```

如果 `items` 和 `raw_bill_text` 同时提供，模型必须为 `items` 中每项返回且只返回一条结果，`raw_bill_text` 只作为补充上下文。

返回字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 本次请求标识 |
| `matches` | 逐条名称归一结果 |
| `matches[].raw_name` | 原样返回的原始名称 |
| `matches[].standard_name` | 标准通用名或项目名称，无法确认时为空字符串 |
| `matches[].confidence` | 匹配可信度，范围 `0-1` |
| `matches[].reimbursement_level` | 报销等级：`甲`、`乙`、`丙` |
| `matches[].reimbursement_ratio` | 报销比例，范围 `0-1` |
| `matches[].basis` | 清洗、归一、适用地区医保目录和报销判断依据 |
| `matches[].alternatives` | 最多 3 个候选名称及依据 |

返回示例：

```json
{
  "request_id": "2a830f8d8b8e442e8a6a3d87f9b90d54",
  "matches": [
    {
      "raw_name": "西力欣 0.75g 针",
      "standard_name": "注射用头孢呋辛钠",
      "confidence": 0.96,
      "reimbursement_level": "乙",
      "reimbursement_ratio": 0.9,
      "basis": "西力欣为头孢呋辛钠商品名，已去除规格和剂型描述；按深圳市医保目录归为乙类",
      "alternatives": []
    },
    {
      "raw_name": "红外线治疗",
      "standard_name": "红外线治疗",
      "confidence": 0.93,
      "reimbursement_level": "丙",
      "reimbursement_ratio": 0.0,
      "basis": "原始名称与标准诊疗项目名称一致；按深圳市医疗服务项目目录归为丙类",
      "alternatives": []
    }
  ]
}
```

接口会先尝试百炼的联网检索参数 `enable_search`。若当前模型或接口不支持，会去掉该参数自动重试，不影响名称归一请求。

## 配置

配置集中在 `app/config.py`：

| 配置 | 默认值 | 是否可用环境变量覆盖 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | 从本机 `app/local_config.py` 或环境变量读取 | 是 |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 是 |
| `MODEL_NAME` | `qwen3.8-flash` | 是，变量名 `DASHSCOPE_MODEL` |
| `LLM_TIMEOUT_SECONDS` | `90` | 是 |

`app/local_config.py` 已加入 `.gitignore`，不会提交到仓库。首次部署时复制示例文件并填写密钥：

```powershell
Copy-Item app\local_config.example.py app\local_config.py
```

也可以通过环境变量提供：

```powershell
$env:DASHSCOPE_API_KEY = "your-api-key"
$env:DASHSCOPE_MODEL = "qwen3.8-flash"
$env:LLM_TIMEOUT_SECONDS = "90"
python -m uvicorn app.main:app --reload
```

## 项目结构

```text
app/
  main.py                 FastAPI 路由和异常转换
  llm.py                  百炼调用、JSON 提取和响应校验
  prompts.py              清单审核提示词
  catalog_prompts.py      名称归一提示词
  config.py               应用配置
  models/
    common.py             公共枚举和文本清洗
    review.py             清单审核模型
    name_normalization.py 名称归一模型
tests/
  test_api.py             离线接口测试
```
