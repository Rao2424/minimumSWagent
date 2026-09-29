"""使用 Windows PowerShell 执行本地命令。"""

from __future__ import annotations

import base64
import math
import os
import subprocess
import time
from pathlib import Path

from minimum_sw_agent.tool_result import ToolResult


def _validate_workdir(workdir: str | os.PathLike[str]) -> Path:
    """确认工作目录存在，并返回规范化后的绝对路径。"""
    try:
        root = Path(workdir).resolve(strict=True)
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("工作目录不存在或无法访问") from exc
    if not root.is_dir():
        raise ValueError("工作目录路径不是目录")
    return root


def _decode_output(output: str | bytes | None) -> str:
    """把超时异常中可能出现的字节输出转换为文本。"""
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def run_command(
    workdir: str | os.PathLike[str],
    command: str,
    timeout_seconds: float,
) -> ToolResult:
    """在指定目录执行 PowerShell 命令，并返回受长度限制的结果。"""
    started = time.perf_counter()

    def result(success: bool, *, stdout: str = "", stderr: str = "", exit_code: int | None = None) -> ToolResult:
        """把命令执行情况转换为统一工具结果。"""
        return ToolResult(
            tool_name="run_command",
            success=success,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            elapsed_seconds=time.perf_counter() - started,
        )

    try:
        if os.name != "nt":
            raise ValueError("当前仅支持 Windows PowerShell")
        root = _validate_workdir(workdir)
        if not isinstance(command, str) or not command.strip():
            raise ValueError("命令必须是非空字符串")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("命令超时必须是大于 0 的有限数值（秒）")
        try:
            timeout = float(timeout_seconds)
        except OverflowError as exc:
            raise ValueError("命令超时必须是大于 0 的有限数值（秒）") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("命令超时必须是大于 0 的有限数值（秒）")

        script = (
            "$ProgressPreference = 'SilentlyContinue'; "
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
            + command
        )
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        completed = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
            cwd=root,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result(
            completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
        )
    except ValueError as exc:
        return result(False, stderr=str(exc))
    except subprocess.TimeoutExpired as exc:
        stderr = _decode_output(exc.stderr)
        if stderr and not stderr.endswith("\n"):
            stderr += "\n"
        stderr += f"命令执行超时（上限 {timeout_seconds} 秒）"
        return result(False, stdout=_decode_output(exc.stdout), stderr=stderr)
    except FileNotFoundError:
        return result(False, stderr="未找到 PowerShell 可执行程序")
    except PermissionError:
        return result(False, stderr="没有执行 PowerShell 的权限")
    except OSError:
        return result(False, stderr="命令启动失败")
