import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from minimum_sw_agent.run_config import ModelConfig, RunConfig, load_run_config


class RunConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        """准备各测试共用的模型配置。"""
        self.model = ModelConfig("example", "example-model")

    def make_config(self, workdir: Path, **overrides: object) -> RunConfig:
        """用默认参数及指定覆盖项创建运行配置。"""
        values = {
            "user_goal": " create a file ",
            "workdir": workdir,
            "model": self.model,
            "max_rounds": 20,
            "tool_timeout_seconds": 30,
        }
        values.update(overrides)
        return RunConfig(**values)

    def test_valid_inputs_are_normalized(self) -> None:
        """验证有效输入会被规范化。"""
        with tempfile.TemporaryDirectory() as directory:
            config = self.make_config(Path(directory))
            self.assertEqual(config.user_goal, "create a file")
            self.assertEqual(config.workdir, Path(directory).resolve())
            self.assertEqual(config.tool_timeout_seconds, 30.0)

    def test_goal_and_model_fields_must_be_nonempty(self) -> None:
        """验证目标和模型字段不能为空。"""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "用户目标必须是非空字符串"):
                self.make_config(Path(directory), user_goal="  ")
        with self.assertRaisesRegex(ValueError, "模型供应商必须是非空字符串"):
            ModelConfig(" ", "model", "KEY")
        with self.assertRaisesRegex(ValueError, "API Key 环境变量名格式无效"):
            ModelConfig("provider", "model", "invalid-key")

    def test_workdir_must_exist_and_be_a_directory(self) -> None:
        """验证工作目录必须存在且为目录。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "无法解析工作目录"):
                self.make_config(root / "missing")
            file_path = root / "file.txt"
            file_path.touch()
            with self.assertRaisesRegex(ValueError, "工作目录路径不是目录"):
                self.make_config(file_path)

    def test_limits_reject_invalid_values(self) -> None:
        """验证轮数和工具超时会拒绝无效值。"""
        with tempfile.TemporaryDirectory() as directory:
            for value in (0, -1, True, 1.5):
                with self.subTest(max_rounds=value), self.assertRaisesRegex(ValueError, "最大轮数必须是正整数"):
                    self.make_config(Path(directory), max_rounds=value)
            for value in (0, -1, True, float("nan"), float("inf"), 10**1000):
                with self.subTest(timeout=value), self.assertRaisesRegex(ValueError, "单次工具超时"):
                    self.make_config(Path(directory), tool_timeout_seconds=value)

    def test_environment_variables_supply_configuration(self) -> None:
        """验证运行配置来自环境变量，目标来自本次调用。"""
        with tempfile.TemporaryDirectory() as directory:
            config = load_run_config("创建文件", environ={
                "MINIMUM_SW_AGENT_WORKDIR": directory,
                "MINIMUM_SW_AGENT_MODEL_PROVIDER": "example",
                "MINIMUM_SW_AGENT_MODEL": "example-model",
                "MINIMUM_SW_AGENT_MAX_ROUNDS": "4",
                "MINIMUM_SW_AGENT_TOOL_TIMEOUT_SECONDS": "1.5",
            })
            self.assertEqual(config.user_goal, "创建文件")
            self.assertEqual(config.workdir, Path(directory).resolve())
            self.assertEqual(config.model.provider, "example")
            self.assertEqual(config.model.model, "example-model")
            self.assertEqual(config.model.api_key_env, "MINIMUM_SW_AGENT_API_KEY")
            self.assertEqual(config.max_rounds, 4)
            self.assertEqual(config.tool_timeout_seconds, 1.5)

    def test_process_environment_is_used_by_default(self) -> None:
        """验证未注入环境映射时会读取当前进程的环境变量。"""
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "MINIMUM_SW_AGENT_WORKDIR": directory,
                "MINIMUM_SW_AGENT_MODEL_PROVIDER": "example",
                "MINIMUM_SW_AGENT_MODEL": "example-model",
            }, clear=True):
                config = load_run_config("创建文件")
            self.assertEqual(config.user_goal, "创建文件")
            self.assertEqual(config.max_rounds, 20)
            self.assertEqual(config.tool_timeout_seconds, 30.0)

    def test_invalid_environment_limit_reports_chinese_error(self) -> None:
        """验证环境变量中的无效数值会给出中文提示。"""
        with self.assertRaisesRegex(ValueError, "最大轮数必须是正整数"):
            load_run_config("创建文件", environ={
                "MINIMUM_SW_AGENT_MODEL_PROVIDER": "example",
                "MINIMUM_SW_AGENT_MODEL": "example-model",
                "MINIMUM_SW_AGENT_MAX_ROUNDS": "错误值",
            })


if __name__ == "__main__":
    unittest.main()
