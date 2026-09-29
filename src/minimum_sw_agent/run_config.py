"""定义并校验一次 Agent 运行所需的输入。

一轮指一次模型请求。后续 Agent 循环负责执行 ``max_rounds`` 限制，
每次工具调用分别执行 ``tool_timeout_seconds`` 限制。
"""

from __future__ import annotations

import argparse
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


_ENV_VAR_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True)
class ModelConfig:
    """记录模型标识和保存 API Key 的环境变量名。"""

    provider: str
    model: str
    api_key_env: str

    def __post_init__(self) -> None:
        """清理并校验模型配置字段。"""
        field_names = {
            "provider": "模型供应商",
            "model": "模型名称",
            "api_key_env": "API Key 环境变量名",
        }
        for field_name, display_name in field_names.items():
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{display_name}必须是非空字符串")
            object.__setattr__(self, field_name, value.strip())

        if not _ENV_VAR_NAME.fullmatch(self.api_key_env):
            raise ValueError("API Key 环境变量名格式无效")


@dataclass(frozen=True)
class RunConfig:
    """保存 Agent 启动前必须校验的运行输入。"""

    user_goal: str
    workdir: Path
    model: ModelConfig
    max_rounds: int
    tool_timeout_seconds: float

    def __post_init__(self) -> None:
        """校验运行参数，并将工作目录规范化为绝对路径。"""
        if not isinstance(self.user_goal, str) or not self.user_goal.strip():
            raise ValueError("用户目标必须是非空字符串")
        object.__setattr__(self, "user_goal", self.user_goal.strip())

        if not isinstance(self.model, ModelConfig):
            raise ValueError("模型配置必须是 ModelConfig 类型")

        if not isinstance(self.workdir, (str, os.PathLike)) or not os.fspath(self.workdir):
            raise ValueError("工作目录路径不能为空")
        if isinstance(self.workdir, str) and not self.workdir.strip():
            raise ValueError("工作目录路径不能为空")
        try:
            workdir = Path(self.workdir).resolve(strict=True)
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(f"无法解析工作目录：{self.workdir}") from exc
        if not workdir.is_dir():
            raise ValueError(f"工作目录路径不是目录：{workdir}")
        object.__setattr__(self, "workdir", workdir)

        if type(self.max_rounds) is not int or self.max_rounds <= 0:
            raise ValueError("最大轮数必须是正整数")

        timeout = self.tool_timeout_seconds
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("单次工具超时必须是大于 0 的有限数值（秒）")
        try:
            timeout = float(timeout)
        except OverflowError as exc:
            raise ValueError("单次工具超时必须是大于 0 的有限数值（秒）") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("单次工具超时必须是大于 0 的有限数值（秒）")
        object.__setattr__(self, "tool_timeout_seconds", timeout)


def parse_run_config(argv: Sequence[str] | None = None) -> RunConfig:
    """解析命令行参数并生成经过校验的运行配置。

    此处仅记录环境变量名；后续接入模型客户端时再读取 API Key 的值。
    """

    parser = argparse.ArgumentParser(description="校验一次 Agent 运行所需的输入")
    parser.add_argument("user_goal", help="希望 Agent 完成的任务")
    parser.add_argument("--workdir", type=Path, default=Path.cwd(), help="Agent 工作目录")
    parser.add_argument("--model-provider", required=True, help="模型供应商名称")
    parser.add_argument("--model", required=True, help="模型名称")
    parser.add_argument("--api-key-env", required=True, help="保存 API Key 的环境变量名")
    parser.add_argument("--max-rounds", type=int, default=20, help="最多调用模型的次数")
    parser.add_argument(
        "--tool-timeout-seconds", type=float, default=30.0,
        help="每次工具调用的超时时间，单位为秒",
    )
    args = parser.parse_args(argv)

    try:
        return RunConfig(
            user_goal=args.user_goal,
            workdir=args.workdir,
            model=ModelConfig(
                provider=args.model_provider,
                model=args.model,
                api_key_env=args.api_key_env,
            ),
            max_rounds=args.max_rounds,
            tool_timeout_seconds=args.tool_timeout_seconds,
        )
    except ValueError as exc:
        parser.error(str(exc))
