"""为有副作用的工具提供用户确认入口。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ApprovalRequest:
    """保存待确认的工具、工作目录以及写入内容或命令。"""

    tool_name: str
    workdir: Path
    relative_path: str | None = None
    content: str | None = None
    command: str | None = None


ApprovalCallback = Callable[[ApprovalRequest], bool]


def require_approval(approval: ApprovalCallback | None, request: ApprovalRequest) -> None:
    """要求确认回调明确批准；缺少回调或拒绝时禁止执行。"""
    action = "写入文件" if request.tool_name == "write_file" else "执行命令"
    if approval is None:
        raise ValueError(f"{action}需要用户确认")
    try:
        approved = approval(request)
    except Exception as exc:
        raise ValueError("用户确认过程失败") from exc
    if type(approved) is not bool:
        raise ValueError("用户确认结果必须是布尔值")
    if not approved:
        raise ValueError(f"用户未批准{action}")
