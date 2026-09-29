import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from minimum_sw_agent.approval import ApprovalRequest
from minimum_sw_agent.file_tools import list_files, read_file, write_file
from minimum_sw_agent.tool_result import DEFAULT_OUTPUT_LIMIT_CHARS


def _approve_for_test(_request: ApprovalRequest) -> bool:
    """在测试中模拟用户批准。"""
    return True


class FileToolTests(unittest.TestCase):
    def test_write_read_and_list_nested_file(self) -> None:
        """验证写入会创建父目录，随后可读取并列出文件。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            written = write_file(root, "notes/todo.txt", "待办事项", approval=_approve_for_test)
            self.assertTrue(written.success)
            self.assertEqual((root / "notes" / "todo.txt").read_text(encoding="utf-8"), "待办事项")

            read = read_file(root, "notes/todo.txt")
            listed = list_files(root, "notes")
            self.assertTrue(read.success)
            self.assertEqual(read.stdout, "待办事项")
            self.assertTrue(listed.success)
            self.assertEqual(listed.stdout, "notes/todo.txt")
            self.assertEqual(list_files(root).stdout, "notes/")

    def test_outside_and_absolute_paths_are_rejected(self) -> None:
        """验证路径穿越及绝对路径不会被读写或列出。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "work"
            root.mkdir()
            outside = Path(directory) / "outside.txt"
            outside.write_text("保留", encoding="utf-8")

            for result in (
                read_file(root, "../outside.txt"),
                write_file(root, "../outside.txt", "覆盖"),
                list_files(root, ".."),
                read_file(root, str(outside)),
            ):
                self.assertFalse(result.success)
            self.assertEqual(outside.read_text(encoding="utf-8"), "保留")

    def test_symlink_outside_workdir_is_rejected(self) -> None:
        """验证指向工作目录外部的符号链接不能用于文件操作。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "work"
            root.mkdir()
            outside = Path(directory) / "outside.txt"
            outside.write_text("保留", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("当前环境无法创建符号链接")

            self.assertFalse(read_file(root, "link.txt").success)
            self.assertFalse(write_file(root, "link.txt", "覆盖").success)
            self.assertEqual(outside.read_text(encoding="utf-8"), "保留")

    def test_read_output_is_limited(self) -> None:
        """验证读取大文件时返回内容受统一输出上限约束。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large.txt").write_text("字" * (DEFAULT_OUTPUT_LIMIT_CHARS + 100), encoding="utf-8")
            result = read_file(root, "large.txt")
            self.assertTrue(result.success)
            self.assertTrue(result.stdout_truncated)
            self.assertLessEqual(len(result.stdout), DEFAULT_OUTPUT_LIMIT_CHARS)

    def test_missing_paths_return_structured_errors(self) -> None:
        """验证不存在的路径返回失败结果和中文错误。"""
        with tempfile.TemporaryDirectory() as directory:
            read = read_file(directory, "missing.txt")
            listed = list_files(directory, "missing")
            self.assertFalse(read.success)
            self.assertIn("目标文件不存在", read.stderr)
            self.assertFalse(listed.success)
            self.assertIn("目标目录不存在", listed.stderr)

    def test_write_requires_explicit_approval(self) -> None:
        """验证未经批准时不会创建目录或写入文件。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = write_file(root, "new/file.txt", "内容")
            rejected = write_file(root, "new/file.txt", "内容", approval=lambda _: False)
            self.assertFalse(missing.success)
            self.assertIn("需要用户确认", missing.stderr)
            self.assertFalse(rejected.success)
            self.assertIn("用户未批准", rejected.stderr)
            self.assertFalse((root / "new").exists())

    def test_approval_request_includes_write_details(self) -> None:
        """验证确认回调能看到规范化路径和待写入内容。"""
        with tempfile.TemporaryDirectory() as directory:
            requests: list[ApprovalRequest] = []

            def approve(request: ApprovalRequest) -> bool:
                """保存确认请求并模拟批准。"""
                requests.append(request)
                return True

            result = write_file(directory, "sub/../file.txt", "内容", approval=approve)
            self.assertTrue(result.success)
            self.assertEqual(requests[0].tool_name, "write_file")
            self.assertEqual(requests[0].relative_path, "file.txt")
            self.assertEqual(requests[0].content, "内容")

    def test_write_permission_error_is_structured(self) -> None:
        """验证写入权限错误会成为统一失败结果。"""
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(Path, "write_text", side_effect=PermissionError):
                result = write_file(directory, "file.txt", "内容", approval=_approve_for_test)
            self.assertFalse(result.success)
            self.assertIn("没有写入文件的权限", result.stderr)


if __name__ == "__main__":
    unittest.main()
