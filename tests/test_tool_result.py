import unittest

from minimum_sw_agent.tool_result import ToolResult


class ToolResultTests(unittest.TestCase):
    def test_command_result_records_exit_code_and_duration(self) -> None:
        """验证命令结果记录退出码、输出和耗时。"""
        result = ToolResult(" run_command ", True, "完成", "", 0.25, exit_code=0)
        self.assertEqual(result.tool_name, "run_command")
        self.assertEqual(result.stdout, "完成")
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.http_status_code)
        self.assertEqual(result.elapsed_seconds, 0.25)
        self.assertFalse(result.stdout_truncated)

    def test_http_and_file_results_have_optional_status_codes(self) -> None:
        """验证 HTTP 工具和文件工具可使用同一结果结构。"""
        http = ToolResult("http_request", False, "", "请求失败", 1.2, http_status_code=503)
        file = ToolResult("read_file", True, "内容", "", 0.01)
        self.assertEqual(http.http_status_code, 503)
        self.assertIsNone(http.exit_code)
        self.assertIsNone(file.exit_code)
        self.assertIsNone(file.http_status_code)

    def test_each_output_field_is_truncated_within_limit(self) -> None:
        """验证两种输出各自受长度限制并显示截断标记。"""
        result = ToolResult("run_command", False, "甲" * 40, "乙" * 40, 0.1, max_output_chars=20)
        self.assertEqual(len(result.stdout), 20)
        self.assertEqual(len(result.stderr), 20)
        self.assertTrue(result.stdout.endswith("…（输出已截断）"))
        self.assertTrue(result.stderr.endswith("…（输出已截断）"))
        self.assertTrue(result.stdout_truncated)
        self.assertTrue(result.stderr_truncated)

    def test_invalid_result_fields_are_rejected(self) -> None:
        """验证状态码、耗时和输出上限中的无效值会被拒绝。"""
        with self.assertRaisesRegex(ValueError, "工具名必须是非空字符串"):
            ToolResult(" ", True, "", "", 0)
        with self.assertRaisesRegex(ValueError, "耗时必须是非负"):
            ToolResult("run_command", True, "", "", -1)
        with self.assertRaisesRegex(ValueError, "不能同时设置"):
            ToolResult("run_command", True, "", "", 0, exit_code=0, http_status_code=200)
        with self.assertRaisesRegex(ValueError, "输出长度上限必须是正整数"):
            ToolResult("run_command", True, "", "", 0, max_output_chars=0)


if __name__ == "__main__":
    unittest.main()
