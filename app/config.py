"""Application configuration."""

import os


try:
    from app.local_config import DASHSCOPE_API_KEY
except ImportError:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
MODEL_NAME = os.getenv("DASHSCOPE_MODEL", "qwen3.8-flash")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))

