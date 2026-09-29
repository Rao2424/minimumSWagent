import unittest

from minimum_sw_agent.task import Task, TaskStatus


class TaskTests(unittest.TestCase):
    def test_task_records_goal_condition_and_default_status(self) -> None:
        """验证任务保存目标和完成条件，并默认处于待开始状态。"""
        task = Task(" 创建文件 ", " 文件存在 ")
        self.assertEqual(task.goal, "创建文件")
        self.assertEqual(task.completion_condition, "文件存在")
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_task_can_progress_block_resume_and_finish(self) -> None:
        """验证受阻后恢复并完成任务的状态流转。"""
        pending = Task("创建文件", "文件存在")
        in_progress = pending.transition_to(TaskStatus.IN_PROGRESS)
        blocked = in_progress.transition_to(TaskStatus.BLOCKED)
        resumed = blocked.transition_to(TaskStatus.IN_PROGRESS)
        done = resumed.transition_to(TaskStatus.DONE)

        self.assertEqual(pending.status, TaskStatus.PENDING)
        self.assertEqual(blocked.status, TaskStatus.BLOCKED)
        self.assertEqual(done.status, TaskStatus.DONE)
        self.assertEqual(done.completion_condition, "文件存在")

    def test_invalid_task_inputs_are_rejected(self) -> None:
        """验证目标、完成条件和状态的无效值会被拒绝。"""
        with self.assertRaisesRegex(ValueError, "任务目标必须是非空字符串"):
            Task(" ", "文件存在")
        with self.assertRaisesRegex(ValueError, "完成条件必须是非空字符串"):
            Task("创建文件", " ")
        with self.assertRaisesRegex(ValueError, "任务状态必须是 TaskStatus 枚举值"):
            Task("创建文件", "文件存在", "pending")

    def test_invalid_transitions_are_rejected(self) -> None:
        """验证跳过进行中状态及修改已完成任务会被拒绝。"""
        task = Task("创建文件", "文件存在")
        with self.assertRaisesRegex(ValueError, "任务状态不能从 pending 变为 done"):
            task.transition_to(TaskStatus.DONE)
        with self.assertRaisesRegex(ValueError, "目标状态必须是 TaskStatus 枚举值"):
            task.transition_to("done")

        done = task.transition_to(TaskStatus.IN_PROGRESS).transition_to(TaskStatus.DONE)
        with self.assertRaisesRegex(ValueError, "任务状态不能从 done 变为 in_progress"):
            done.transition_to(TaskStatus.IN_PROGRESS)


if __name__ == "__main__":
    unittest.main()
