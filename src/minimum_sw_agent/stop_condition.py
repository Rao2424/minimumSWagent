"""根据运行进度判断 Agent 是否应结束。"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from minimum_sw_agent.task import Task, TaskStatus


DEFAULT_MAX_CONSECUTIVE_FAILURES = 3


class StopReason(str, Enum):
    """表示触发 Agent 结束的原因。"""

    FINAL_ANSWER = "final_answer"
    ALL_TASKS_DONE = "all_tasks_done"
    MAX_ROUNDS = "max_rounds"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    USER_ABORTED = "user_aborted"


def evaluate_stop(
    *,
    tasks: Sequence[Task],
    rounds_completed: int,
    max_rounds: int,
    consecutive_failures: int,
    final_answer: str | None = None,
    user_aborted: bool = False,
    max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
) -> StopReason | None:
    """返回命中的结束原因；未命中时返回 ``None``。

    多个条件同时满足时，优先级依次为：用户中止、最终答复、任务全部完成、
    达到轮数上限、连续失败。空任务列表不会触发“任务全部完成”。
    """
    if not isinstance(tasks, Sequence) or any(not isinstance(task, Task) for task in tasks):
        raise ValueError("任务列表必须由 Task 对象组成")
    if type(rounds_completed) is not int or rounds_completed < 0:
        raise ValueError("已完成轮数必须是非负整数")
    if type(max_rounds) is not int or max_rounds <= 0:
        raise ValueError("最大轮数必须是正整数")
    if type(consecutive_failures) is not int or consecutive_failures < 0:
        raise ValueError("连续失败次数必须是非负整数")
    if type(max_consecutive_failures) is not int or max_consecutive_failures <= 0:
        raise ValueError("连续失败次数上限必须是正整数")
    if final_answer is not None and not isinstance(final_answer, str):
        raise ValueError("最终答复必须是字符串或 None")
    if type(user_aborted) is not bool:
        raise ValueError("用户中止标记必须是布尔值")

    if user_aborted:
        return StopReason.USER_ABORTED
    if final_answer is not None and final_answer.strip():
        return StopReason.FINAL_ANSWER
    if tasks and all(task.status is TaskStatus.DONE for task in tasks):
        return StopReason.ALL_TASKS_DONE
    if rounds_completed >= max_rounds:
        return StopReason.MAX_ROUNDS
    if consecutive_failures >= max_consecutive_failures:
        return StopReason.CONSECUTIVE_FAILURES
    return None
