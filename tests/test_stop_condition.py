import unittest

from minimum_sw_agent.stop_condition import StopReason, evaluate_stop
from minimum_sw_agent.task import Task, TaskStatus


class StopConditionTests(unittest.TestCase):
    def setUp(self) -> None:
        """准备一项尚未开始的测试任务。"""
        self.pending = Task("创建文件", "文件存在")

    def evaluate(self, **overrides: object) -> StopReason | None:
        """用默认进度和指定覆盖项检查结束原因。"""
        values = {
            "tasks": [self.pending],
            "rounds_completed": 0,
            "max_rounds": 5,
            "consecutive_failures": 0,
        }
        values.update(overrides)
        return evaluate_stop(**values)

    def test_each_end_condition(self) -> None:
        """验证五种结束条件分别返回对应原因。"""
        done = self.pending.transition_to(TaskStatus.IN_PROGRESS).transition_to(TaskStatus.DONE)
        self.assertEqual(self.evaluate(final_answer="已完成"), StopReason.FINAL_ANSWER)
        self.assertEqual(self.evaluate(tasks=[done]), StopReason.ALL_TASKS_DONE)
        self.assertEqual(self.evaluate(rounds_completed=5), StopReason.MAX_ROUNDS)
        self.assertEqual(self.evaluate(consecutive_failures=3), StopReason.CONSECUTIVE_FAILURES)
        self.assertEqual(self.evaluate(user_aborted=True), StopReason.USER_ABORTED)

    def test_unfinished_run_continues(self) -> None:
        """验证任务未完成且尚未达到限制时继续运行。"""
        self.assertIsNone(self.evaluate())
        self.assertIsNone(self.evaluate(tasks=[]))
        self.assertIsNone(self.evaluate(final_answer="   "))
        self.assertIsNone(self.evaluate(rounds_completed=4, consecutive_failures=2))

    def test_stop_reason_priority(self) -> None:
        """验证多个条件同时满足时按约定优先级选取原因。"""
        done = self.pending.transition_to(TaskStatus.IN_PROGRESS).transition_to(TaskStatus.DONE)
        self.assertEqual(
            self.evaluate(tasks=[done], rounds_completed=5, final_answer="完成", user_aborted=True),
            StopReason.USER_ABORTED,
        )
        self.assertEqual(
            self.evaluate(tasks=[done], rounds_completed=5, final_answer="完成"),
            StopReason.FINAL_ANSWER,
        )

    def test_invalid_progress_is_rejected(self) -> None:
        """验证无效计数和任务列表会被拒绝。"""
        with self.assertRaisesRegex(ValueError, "已完成轮数必须是非负整数"):
            self.evaluate(rounds_completed=-1)
        with self.assertRaisesRegex(ValueError, "连续失败次数上限必须是正整数"):
            self.evaluate(max_consecutive_failures=0)
        with self.assertRaisesRegex(ValueError, "任务列表必须由 Task 对象组成"):
            self.evaluate(tasks=["不是任务"])


if __name__ == "__main__":
    unittest.main()
