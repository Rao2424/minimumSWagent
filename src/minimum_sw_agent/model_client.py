"""模型请求的统一入口及 OpenAI 官方 SDK 适配。"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI

from minimum_sw_agent.run_config import ModelConfig


@dataclass(frozen=True)
class ModelToolCall:
    """保留模型返回的原生工具调用参数，供后续分发层校验。"""

    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ModelResponse:
    """供应商无关的单轮模型结果。"""

    text: str
    tool_calls: tuple[ModelToolCall, ...]
    response_id: str


class ModelClient(Protocol):
    """Agent 循环依赖的模型调用接口。"""

    def generate(
        self,
        prompt: str,
        tools: Sequence[Mapping[str, Any]] = (),
    ) -> ModelResponse: ...


class OpenAIModelClient:
    """通过 OpenAI Responses API 完成一轮模型请求。"""

    def __init__(self, model: str, sdk_client: OpenAI) -> None:
        self._model = model
        self._sdk_client = sdk_client

    def generate(
        self,
        prompt: str,
        tools: Sequence[Mapping[str, Any]] = (),
    ) -> ModelResponse:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("模型输入必须是非空字符串")

        request: dict[str, Any] = {"model": self._model, "input": prompt}
        if tools:
            request["tools"] = list(tools)
        response = self._sdk_client.responses.create(**request)
        calls = tuple(
            ModelToolCall(item.call_id, item.name, item.arguments)
            for item in response.output
            if item.type == "function_call"
        )
        return ModelResponse(response.output_text, calls, response.id)


def create_model_client(
    config: ModelConfig,
    environ: Mapping[str, str] | None = None,
) -> ModelClient:
    """从环境变量读取密钥，创建已支持的供应商客户端。"""

    if not isinstance(config, ModelConfig):
        raise ValueError("模型配置必须是 ModelConfig 类型")
    if config.provider.lower() != "openai":
        raise ValueError(f"暂不支持模型供应商：{config.provider}")

    environment = os.environ if environ is None else environ
    api_key = environment.get(config.api_key_env, "").strip()
    if not api_key:
        raise ValueError(f"缺少 API Key，请设置环境变量 {config.api_key_env}")

    return OpenAIModelClient(
        config.model,
        OpenAI(api_key=api_key, timeout=60.0, max_retries=0),
    )
