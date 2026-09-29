"""在指定工作目录内执行受控的本地文件操作。"""

from __future__ import annotations

import os
import time
from pathlib import Path

from minimum_sw_agent.approval import ApprovalCallback, ApprovalRequest, require_approval
from minimum_sw_agent.tool_result import DEFAULT_OUTPUT_LIMIT_CHARS, ToolResult


def _resolve_path(workdir: str | os.PathLike[str], relative_path: str) -> tuple[Path, Path]:
    """规范化路径，并确认目标没有离开工作目录。"""
    try:
        root = Path(workdir).resolve(strict=True)
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("工作目录不存在或无法访问") from exc
    if not root.is_dir():
        raise ValueError("工作目录路径不是目录")

    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("相对路径必须是非空字符串")
    relative = Path(relative_path)
    if relative.is_absolute() or relative.drive:
        raise ValueError("路径必须相对于工作目录")

    try:
        target = (root / relative).resolve(strict=False)
    except (OSError, ValueError) as exc:
        raise ValueError("无法解析目标路径") from exc
    if not target.is_relative_to(root):
        raise ValueError("路径超出工作目录")
    return root, target


def _result(tool_name: str, started: float, *, success: bool, stdout: str = "", stderr: str = "") -> ToolResult:
    """把文件工具的执行情况转换为统一结果。"""
    return ToolResult(
        tool_name=tool_name,
        success=success,
        stdout=stdout,
        stderr=stderr,
        elapsed_seconds=time.perf_counter() - started,
    )


def read_file(workdir: str | os.PathLike[str], relative_path: str) -> ToolResult:
    """读取工作目录内的 UTF-8 文件，并限制返回内容长度。"""
    started = time.perf_counter()
    try:
        _, target = _resolve_path(workdir, relative_path)
        if not target.is_file():
            raise ValueError("目标文件不存在或不是普通文件")
        with target.open("r", encoding="utf-8") as handle:
            content = handle.read(DEFAULT_OUTPUT_LIMIT_CHARS + 1)
        return _result("read_file", started, success=True, stdout=content)
    except ValueError as exc:
        return _result("read_file", started, success=False, stderr=str(exc))
    except UnicodeError:
        return _result("read_file", started, success=False, stderr="文件不是有效的 UTF-8 文本")
    except PermissionError:
        return _result("read_file", started, success=False, stderr="没有读取文件的权限")
    except OSError:
        return _result("read_file", started, success=False, stderr="读取文件失败")


def write_file(
    workdir: str | os.PathLike[str],
    relative_path: str,
    content: str,
    *,
    approval: ApprovalCallback | None = None,
) -> ToolResult:
    """经用户确认后写入 UTF-8 文件，必要时先创建父目录。"""
    started = time.perf_counter()
    try:
        root, target = _resolve_path(workdir, relative_path)
        if not isinstance(content, str):
            raise ValueError("写入内容必须是字符串")
        if target.is_dir():
            raise ValueError("目标路径是目录，不能写入文件")

        require_approval(
            approval,
            ApprovalRequest(
                tool_name="write_file",
                workdir=root,
                relative_path=target.relative_to(root).as_posix(),
                content=content,
            ),
        )

        target.parent.mkdir(parents=True, exist_ok=True)
        target = target.resolve(strict=False)
        if not target.is_relative_to(root):
            raise ValueError("路径超出工作目录")
        if target.is_dir():
            raise ValueError("目标路径是目录，不能写入文件")
        target.write_text(content, encoding="utf-8")
        return _result("write_file", started, success=True, stdout="文件写入成功")
    except ValueError as exc:
        return _result("write_file", started, success=False, stderr=str(exc))
    except PermissionError:
        return _result("write_file", started, success=False, stderr="没有写入文件的权限")
    except OSError:
        return _result("write_file", started, success=False, stderr="写入文件失败")


def list_files(workdir: str | os.PathLike[str], relative_path: str = ".") -> ToolResult:
    """列出工作目录内指定目录的直接子项。"""
    started = time.perf_counter()
    try:
        root, target = _resolve_path(workdir, relative_path)
        if not target.is_dir():
            raise ValueError("目标目录不存在或不是目录")
        entries = sorted(
            child.relative_to(root).as_posix() + ("/" if child.is_dir() else "")
            for child in target.iterdir()
        )
        return _result("list_files", started, success=True, stdout="\n".join(entries))
    except ValueError as exc:
        return _result("list_files", started, success=False, stderr=str(exc))
    except PermissionError:
        return _result("list_files", started, success=False, stderr="没有列出目录的权限")
    except OSError:
        return _result("list_files", started, success=False, stderr="列出目录失败")
