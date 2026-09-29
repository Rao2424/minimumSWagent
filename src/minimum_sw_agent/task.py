"""定义任务内容和任务状态的流转规则。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class TaskStatus(str, Enum):
    """表示任务尚未开始、进行中、已完成或受阻。"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


_ALLOWED_TRANSITIONS = {
    TaskStatus.PENDING: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED}),
    TaskStatus.IN_PROGRESS: frozenset({TaskStatus.DONE, TaskStatus.BLOCKED}),
    TaskStatus.BLOCKED: frozenset({TaskStatus.IN_PROGRESS}),
    TaskStatus.DONE: frozenset(),
}


@dataclass(frozen=True)
class Task:
    """记录一项任务的目标、完成条件和当前状态。"""

    goal: str
    completion_condition: str
    status: TaskStatus = TaskStatus.PENDING

    def __post_init__(self) -> None:
        """检查目标、完成条件和状态，并清理文本两端的空白。"""
        for field_name, display_name in (
            ("goal", "任务目标"),
            ("completion_condition", "完成条件"),
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{display_name}必须是非空字符串")
            object.__setattr__(self, field_name, value.strip())

        if not isinstance(self.status, TaskStatus):
            raise ValueError("任务状态必须是 TaskStatus 枚举值")

    def transition_to(self, status: TaskStatus) -> Task:
        """按允许的流转规则返回状态已更新的新任务。"""
        if not isinstance(status, TaskStatus):
            raise ValueError("目标状态必须是 TaskStatus 枚举值")
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"任务状态不能从 {self.status.value} 变为 {status.value}")
        return replace(self, status=status)
