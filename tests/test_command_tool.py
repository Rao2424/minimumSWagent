import tempfile
import unittest
from pathlib import Path

from minimum_sw_agent.command_tool import run_command
from minimum_sw_agent.tool_result import DEFAULT_OUTPUT_LIMIT_CHARS


class CommandToolTests(unittest.TestCase):
    def test_success_uses_workdir_and_captures_output(self) -> None:
        """验证命令在指定目录运行并记录标准输出和退出码。"""
        with tempfile.TemporaryDirectory() as directory:
            result = run_command(directory, "(Get-Location).Path", 10)
            self.assertTrue(result.success, result.stderr)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(Path(result.stdout.strip()).resolve(), Path(directory).resolve())
            self.assertEqual(result.stderr, "")
            self.assertGreaterEqual(result.elapsed_seconds, 0)

    def test_failure_captures_exit_code_and_stderr(self) -> None:
        """验证失败命令的退出码和标准错误会被记录。"""
        result = run_command(Path.cwd(), "Write-Error '失败'; exit 7", 10)
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 7)
        self.assertIn("失败", result.stderr)

    def test_timeout_returns_structured_failure(self) -> None:
        """验证超时会停止命令并返回中文错误。"""
        result = run_command(Path.cwd(), "Start-Sleep -Seconds 3", 0.5)
        self.assertFalse(result.success)
        self.assertIsNone(result.exit_code)
        self.assertIn("命令执行超时", result.stderr)

    def test_output_is_limited(self) -> None:
        """验证过长的命令输出会被截断。"""
        result = run_command(Path.cwd(), "'甲' * 11000", 10)
        self.assertTrue(result.success, result.stderr)
        self.assertTrue(result.stdout_truncated)
        self.assertLessEqual(len(result.stdout), DEFAULT_OUTPUT_LIMIT_CHARS)

    def test_invalid_inputs_return_failure(self) -> None:
        """验证无效命令、工作目录和超时返回失败结果。"""
        with tempfile.TemporaryDirectory() as directory:
            self.assertIn("命令必须是非空字符串", run_command(directory, " ", 5).stderr)
            self.assertIn("命令超时必须", run_command(directory, "Get-Date", 0).stderr)
            self.assertIn("工作目录不存在", run_command(Path(directory) / "missing", "Get-Date", 5).stderr)


if __name__ == "__main__":
    unittest.main()
