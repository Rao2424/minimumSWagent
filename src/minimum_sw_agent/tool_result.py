"""定义各类工具共用的执行结果。"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


DEFAULT_OUTPUT_LIMIT_CHARS = 10_000
_TRUNCATION_MARKER = "…（输出已截断）"


def _limit_output(value: str, limit: int) -> tuple[str, bool]:
    """把单个输出字段限制在指定字符数内，并标记是否截断。"""
    if len(value) <= limit:
        return value, False
    if limit <= len(_TRUNCATION_MARKER):
        return _TRUNCATION_MARKER[:limit], True
    return value[: limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER, True


@dataclass(frozen=True)
class ToolResult:
    """记录工具执行结果；标准输出和标准错误分别受长度限制。"""

    tool_name: str
    success: bool
    stdout: str
    stderr: str
    elapsed_seconds: float
    exit_code: int | None = None
    http_status_code: int | None = None
    max_output_chars: int = field(default=DEFAULT_OUTPUT_LIMIT_CHARS, repr=False, compare=False)
    stdout_truncated: bool = field(init=False)
    stderr_truncated: bool = field(init=False)

    def __post_init__(self) -> None:
        """校验结果字段，并截断超出长度上限的输出。"""
        if not isinstance(self.tool_name, str) or not self.tool_name.strip():
            raise ValueError("工具名必须是非空字符串")
        object.__setattr__(self, "tool_name", self.tool_name.strip())

        if type(self.success) is not bool:
            raise ValueError("是否成功必须是布尔值")
        if not isinstance(self.stdout, str) or not isinstance(self.stderr, str):
            raise ValueError("标准输出和标准错误必须是字符串")

        if isinstance(self.elapsed_seconds, bool) or not isinstance(self.elapsed_seconds, (int, float)):
            raise ValueError("耗时必须是非负的有限数值（秒）")
        try:
            elapsed = float(self.elapsed_seconds)
        except OverflowError as exc:
            raise ValueError("耗时必须是非负的有限数值（秒）") from exc
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("耗时必须是非负的有限数值（秒）")
        object.__setattr__(self, "elapsed_seconds", elapsed)

        if self.exit_code is not None and type(self.exit_code) is not int:
            raise ValueError("退出码必须是整数")
        if self.http_status_code is not None:
            if type(self.http_status_code) is not int or not 100 <= self.http_status_code <= 599:
                raise ValueError("HTTP 状态码必须是 100 到 599 之间的整数")
        if self.exit_code is not None and self.http_status_code is not None:
            raise ValueError("退出码和 HTTP 状态码不能同时设置")

        if type(self.max_output_chars) is not int or self.max_output_chars <= 0:
            raise ValueError("输出长度上限必须是正整数")
        stdout, stdout_truncated = _limit_output(self.stdout, self.max_output_chars)
        stderr, stderr_truncated = _limit_output(self.stderr, self.max_output_chars)
        object.__setattr__(self, "stdout", stdout)
        object.__setattr__(self, "stderr", stderr)
        object.__setattr__(self, "stdout_truncated", stdout_truncated)
        object.__setattr__(self, "stderr_truncated", stderr_truncated)
