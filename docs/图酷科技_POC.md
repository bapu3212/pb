# 医疗清单智能审核与名称归一系统 POC 接口文档

## 1. 项目概览

本 POC 由杭州图酷科技有限公司提供，面向医疗费用审核与数据标准化场景，提供两条核心 API：

- 医疗清单智能审核；
- 医疗项目名称批量归一。

医疗清单智能审核与名称归一系统通过标准化接口返回结构化 JSON，可对接业务系统、规则引擎和人工复核工作台。

| 项目 | 内容 |
| --- | --- |
| 产品提供方 | 杭州图酷科技有限公司 |
| 服务文档 | `/docs` |
| OpenAPI | `/openapi.json` |

## 2. 接口总览

| 方法 | 路径 | 接口名称 | 核心输出 |
| --- | --- | --- | --- |
| `GET` | `/health` | 健康检查 | 服务状态与模型名称 |
| `POST` | `/api/v1/claim-reviews` | 医疗清单智能审核 | 主要疾病、ICD-10、不合理项目、免责项目 |
| `POST` | `/api/v1/catalog-matches` | 医疗项目名称归一 | 标准名称、置信度、依据、候选结果 |

### 通用约定

| 项目 | 约定 |
| --- | --- |
| 请求格式 | `application/json`，UTF-8 |
| 返回格式 | 严格 JSON |
| 请求追踪 | 每个业务响应包含唯一 `request_id` |
| 业务处理 | 每次请求返回一份结构化业务结果 |
| 结构校验 | 校验字段、类型、枚举和数值范围 |

### HTTP 状态码

| 状态码 | 含义 | 场景 |
| --- | --- | --- |
| `200` | 成功 | 业务处理与结果校验通过 |
| `422` | 参数错误 | 字段缺失、枚举错误、类型错误、数值越界、输入为空 |
| `502` | 处理服务异常 | 业务处理失败、响应异常或 JSON 校验失败 |
| `504` | 处理超时 | 业务处理超过服务超时时间 |

## 3. 医疗清单智能审核接口

### 3.1 接口定义

```text
POST /api/v1/claim-reviews
```

根据医疗账单、事故类型、疾病名称、性别和年龄，一次生成：

- 最主要疾病或损伤；
- 对应 ICD-10 编码和名称；
- 不合理用药或项目；
- 免责用药或项目及免责类别；
- 每条结论的原因、相关疾病和置信度。

接口能力：

| 项目 | 说明 |
| --- | --- |
| 输入 | 结构化医疗清单或原始账单文本 |
| 输出 | 主要疾病、ICD-10 编码、不合理项目及免责项目 |
| 响应格式 | JSON 对象 |

### 3.2 请求字段

#### 顶层字段

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `medical_items` | `array` | 条件必填 | 最多 200 项 | 结构化医疗清单；与 `raw_bill_text` 至少提供一项 |
| `raw_bill_text` | `string` | 条件必填 | 最多 50,000 字符 | 原始账单文本；与 `medical_items` 至少提供一项 |
| `accident_type` | `string` | 是 | `疾病`、`意外` | 事故类型 |
| `disease_names` | `string[]` | 是 | 最多 20 项，可为空 | 疾病名称；为空时根据用药和项目推断 |
| `gender` | `string` | 是 | `男`、`女`、`未知` | 患者性别 |
| `age` | `integer` | 是 | `0-150` | 患者年龄，单位周岁 |
| `additional_context` | `string` | 否 | 最多 5,000 字符 | 事故经过、症状、既往史等补充信息 |

#### `medical_items` 字段

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | 1-200 字符 | 药品、诊疗项目、检查检验或医用材料名称 |
| `item_type` | `string` | 否 | 最多 50 字符，默认 `其他` | 药品、诊疗项目、检查检验、医用材料等 |
| `code` | `string` | 否 | 最多 100 字符 | 院内编码、收费编码或医保编码 |
| `unit_content` | `string` | 否 | 最多 100 字符 | 每个计价单位包含的规格，如 `10g/瓶`、`30mg/片` |
| `quantity` | `number` | 否 | `>= 0` | 数量 |
| `unit_price` | `number` | 否 | `>= 0` | 计价单位价格 |
| `amount` | `number` | 否 | `>= 0` | 金额 |
| `notes` | `string` | 否 | 最多 1,000 字符 | 医嘱、诊断、使用背景等补充说明 |

### 3.3 请求示例

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
      "amount": 285,
      "notes": "右小腿开放性外伤清创术后预防感染"
    },
    {
      "name": "破伤风人免疫球蛋白",
      "item_type": "药品",
      "code": "DRUG-TIG-001",
      "unit_content": "250IU/支",
      "quantity": 1,
      "unit_price": 168,
      "amount": 168,
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
      "unit_price": 680,
      "amount": 680,
      "notes": "使用美容缝合材料处理面部裂伤"
    },
    {
      "name": "健康体检套餐",
      "item_type": "检查检验",
      "code": "EXAM-HEALTH-CHECK",
      "quantity": 1,
      "unit_price": 360,
      "amount": 360,
      "notes": "入院体检项目，与本次外伤诊疗无直接针对性"
    }
  ],
  "raw_bill_text": "头孢呋辛 1.5g 静滴 q8h 5天；破伤风人免疫球蛋白 250IU 肌注；硝苯地平控释片 30mg qd 7天；美容缝合 1次；健康体检套餐 1次。",
  "accident_type": "意外",
  "disease_names": [
    "右小腿开放性外伤",
    "面部裂伤",
    "高血压"
  ],
  "gender": "男",
  "age": 46,
  "additional_context": "患者骑电动车摔倒后入院，右小腿及面部受伤。既往有高血压病史，本次未诉血压异常。"
}
```

仅提供原始文本：

```json
{
  "raw_bill_text": "阿莫西林胶囊 0.5g 口服 每日2次 5天；胸部CT平扫 1次。",
  "accident_type": "疾病",
  "disease_names": [],
  "gender": "女",
  "age": 35,
  "additional_context": "因发热、咳嗽入院。"
}
```

### 3.4 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `request_id` | `string` | 请求唯一标识 |
| `primary_disease` | `object` | 主要疾病或损伤 |
| `primary_disease.name` | `string` | 最主要疾病或损伤名称 |
| `primary_disease.confidence` | `number` | 判断置信度，范围 `0-1` |
| `primary_disease.basis` | `string` | 判断依据 |
| `icd10_code` | `string` | ICD-10 编码；无法可靠编码时为空字符串 |
| `icd10_name` | `string` | ICD-10 标准名称；无法可靠编码时为空字符串 |
| `unreasonable_items` | `array` | 不合理用药或项目 |
| `exempt_items` | `array` | 免责用药或项目 |

审核明细字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `item_name` | `string` | 对应账单中的药品或项目名称 |
| `item_type` | `string` | 药品、诊疗项目、检查检验、医用材料等 |
| `reason` | `string` | 不合理或免责的具体原因 |
| `related_disease` | `string/null` | 相关疾病或损伤 |
| `exemption_category` | `string/null` | 免责类别；不合理项目固定为 `null` |
| `confidence` | `number` | 项目判断置信度，范围 `0-1` |

### 3.5 响应示例

```json
{
  "request_id": "7f7f0c8927f1488d9a5f8e5f0f2d7d7e",
  "primary_disease": {
    "name": "右小腿开放性外伤",
    "confidence": 0.96,
    "basis": "患者因交通事故导致右小腿开放性损伤，清创、抗感染及破伤风预防治疗均围绕该损伤展开"
  },
  "icd10_code": "S81.8",
  "icd10_name": "小腿开放性伤口，其他特指部位",
  "unreasonable_items": [
    {
      "item_name": "硝苯地平控释片",
      "item_type": "药品",
      "reason": "本次为意外外伤，账单及补充信息未提示高血压急性发作或需要调整降压治疗，该药与本次外伤诊疗无直接关系",
      "related_disease": "高血压",
      "exemption_category": null,
      "confidence": 0.88
    }
  ],
  "exempt_items": [
    {
      "item_name": "美容缝合",
      "item_type": "诊疗项目",
      "reason": "使用美容缝合材料以改善面部瘢痕外观，项目具有明确美容属性",
      "related_disease": "面部裂伤",
      "exemption_category": "美容",
      "confidence": 0.91
    },
    {
      "item_name": "健康体检套餐",
      "item_type": "检查检验",
      "reason": "属于健康检查项目，并非针对本次右小腿或面部外伤的必要诊断检查",
      "related_disease": null,
      "exemption_category": "健康检查",
      "confidence": 0.95
    }
  ]
}
```

### 3.6 审核口径

- 疾病名称非空时，以疾病名称作为重要依据，同时结合账单、性别、年龄和事故类型；
- 疾病名称为空时，结合药品适应证、诊疗项目、检查信息和事故类型推断主要疾病；
- 不合理项目需与主要疾病及常见并发症无关，且对本次诊疗没有明确治疗、诊断、支持或预防作用；
- 事故类型为 `意外` 时，仅针对既往疾病且与本次意外损伤无关的用药或项目进入不合理项目；
- 免责项目必须归入以下类别之一。

```text
精神和行为障碍、先天性畸形、变形和染色体异常、生育相关、性病、
非治疗性牙科、甲乙类传染病、遗传性疾病、屈光不正、非疾病治疗、
健康检查、职业病、矫形／矫正、美容、医疗咨询、预防性保健、斑秃、
脱发、中医理疗、物理治疗、其他康复治疗、屈光不正检查、特需、
其他非医疗费用、煎药、体检、药房常见免责
```

## 4. 医疗项目名称归一接口

### 4.1 接口定义

```text
POST /api/v1/catalog-matches
```

用于将票据、HIS、收费清单和原始采集数据中的药品、诊疗项目、检查及医用耗材名称，清洗并归一为标准通用名称。

医保三目录固定口径：

```text
医保药品目录 + 医疗服务项目目录 + 医用耗材目录
```

接口能力：

| 项目 | 说明 |
| --- | --- |
| 输入 | 待归一项目或原始账单文本 |
| 输出 | 标准名称、置信度、依据及候选结果 |
| 响应格式 | JSON 对象 |

### 4.2 请求字段

#### 顶层字段

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `items` | `array` | 条件必填 | 最多 200 项 | 待归一项目；与 `raw_bill_text` 至少提供一项 |
| `raw_bill_text` | `string` | 条件必填 | 最多 50,000 字符 | 原始票据或账单文本；与 `items` 至少提供一项 |
| `additional_context` | `string` | 否 | 最多 5,000 字符 | 采集来源、地区约定、常见缩写等补充信息 |

#### `items` 字段

| 字段 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `raw_name` | `string` | 是 | 1-500 字符 | 票据、HIS 或收费系统中的原始名称 |
| `item_type` | `string` | 否 | 最多 50 字符，默认 `其他` | 药品、诊疗项目、检查检验、医用耗材等 |
| `raw_code` | `string` | 否 | 最多 100 字符 | 原始院内编码、收费编码或医保编码 |
| `notes` | `string` | 否 | 最多 1,000 字符 | 规格、厂家、包装、医嘱或其他匹配信息 |

### 4.3 请求示例

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
      "raw_name": "胸部 CT 平扫（64排）",
      "item_type": "检查检验",
      "notes": "胸部CT平扫"
    },
    {
      "raw_name": "一次性无菌注射器 5ml",
      "item_type": "医用耗材",
      "notes": "5ml 带针"
    }
  ],
  "raw_bill_text": "西力欣 0.75g 针；拜新同控释片 30mg；胸部CT平扫（64排）；一次性无菌注射器 5ml。",
  "additional_context": "名称来自收费系统和纸质票据，存在商品名、缩写、剂型和规格描述。"
}
```

仅提供原始文本：

```json
{
  "raw_bill_text": "西力欣 0.75g 针；拜新同控释片 30mg；一次性无菌注射器 5ml。",
  "additional_context": "名称来自纸质票据。"
}
```

### 4.4 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `request_id` | `string` | 请求唯一标识 |
| `matches` | `array` | 逐条名称归一结果 |
| `matches[].raw_name` | `string` | 原样返回的原始名称 |
| `matches[].standard_name` | `string` | 标准通用名或标准项目名称；无法确认时为空字符串 |
| `matches[].confidence` | `number` | 匹配置信度，范围 `0-1` |
| `matches[].basis` | `string` | 名称清洗和归一依据 |
| `matches[].alternatives` | `array` | 最多三个候选名称 |
| `alternatives[].standard_name` | `string` | 候选标准名称 |
| `alternatives[].reason` | `string` | 候选依据 |
| `alternatives[].confidence` | `number` | 候选可信度，范围 `0-1` |

### 4.5 响应示例

```json
{
  "request_id": "2a830f8d8b8e442e8a6a3d87f9b90d54",
  "matches": [
    {
      "raw_name": "西力欣 0.75g 针",
      "standard_name": "注射用头孢呋辛钠",
      "confidence": 0.98,
      "basis": "西力欣为头孢呋辛钠商品名，已去除规格、剂型和收费描述",
      "alternatives": []
    },
    {
      "raw_name": "拜新同 控释片 30mg",
      "standard_name": "硝苯地平控释片",
      "confidence": 0.98,
      "basis": "拜新同为硝苯地平控释片商品名，已去除规格描述",
      "alternatives": []
    },
    {
      "raw_name": "胸部 CT 平扫（64排）",
      "standard_name": "胸部CT平扫",
      "confidence": 0.97,
      "basis": "已清洗设备排数等非标准收费描述",
      "alternatives": []
    },
    {
      "raw_name": "一次性无菌注射器 5ml",
      "standard_name": "一次性使用无菌注射器",
      "confidence": 0.96,
      "basis": "已保留核心耗材名称，并按标准名称补充使用属性",
      "alternatives": [
        {
          "standard_name": "一次性使用无菌注射器带针",
          "reason": "与原始描述中的带针信息一致",
          "confidence": 0.91
        }
      ]
    }
  ]
}
```

### 4.6 归一契约

- `items` 存在时，每个 item 必须返回且只返回一条结果；
- `raw_name` 必须原样带回，不遗漏、不合并、不新增；
- `items` 与 `raw_bill_text` 同时存在时，以 `items` 为结果集合，文本用于补充上下文；
- 仅提供 `raw_bill_text` 时，自动识别每个独立收费项目并逐项输出；
- 自动清洗商品名、厂家名、包装描述、营销性词语、收费编码和非必要规格；
- 处理常见错别字、简称、英文缩写、商品名和不同写法；
- 候选结果最多三个，并按可信度排序。

## 5. 联调示例

### 医疗清单审核

```bash
curl -X POST "http://127.0.0.1:8001/api/v1/claim-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_bill_text": "阿莫西林胶囊 0.5g 口服 每日2次 5天；胸部CT平扫 1次。",
    "accident_type": "疾病",
    "disease_names": [],
    "gender": "女",
    "age": 35,
    "additional_context": "因发热、咳嗽入院。"
  }'
```

### 医疗项目名称归一

```bash
curl -X POST "http://127.0.0.1:8001/api/v1/catalog-matches" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "raw_name": "西力欣 0.75g 针",
        "item_type": "药品"
      },
      {
        "raw_name": "一次性无菌注射器 5ml",
        "item_type": "医用耗材"
      }
    ]
  }'
```

## 6. 配置与部署

| 项目 | 值 |
| --- | --- |
| 服务端口 | `8001` |
| 接口文档 | `/docs` |
| OpenAPI | `/openapi.json` |

健康检查：

```bash
curl http://127.0.0.1:8001/health
```

```json
{
  "status": "ok",
  "model": "<服务标识>"
}
```

其中，`model` 为字符串，上例以占位值展示响应结构。

## 7. 验收摘要

| 验收项 | 标准 |
| --- | --- |
| 服务启动 | `/health` 返回 `200` 和 `status=ok` |
| 接口文档 | `/docs` 正常展示全部接口 |
| 清单审核 | 返回主要疾病、ICD-10、不合理项目和免责项目 |
| 名称归一 | 返回标准名称、置信度、依据和候选结果 |
| 参数校验 | 非法请求返回 `422` |
| 服务异常 | 超时返回 `504`，处理或结果结构异常返回 `502` |
| 端口隔离 | 服务运行于 `8001` |

本 POC 提供上述两条业务 API，可按文档所列的请求字段、响应结构及样例开展联调验证。
