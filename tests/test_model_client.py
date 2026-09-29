import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from minimum_sw_agent.model_client import (
    ModelToolCall,
    OpenAIModelClient,
    create_model_client,
)
from minimum_sw_agent.run_config import ModelConfig


class ModelClientTests(unittest.TestCase):
    def test_missing_api_key_fails_before_creating_sdk_client(self) -> None:
        with patch("minimum_sw_agent.model_client.OpenAI") as sdk_class:
            with self.assertRaisesRegex(ValueError, "缺少 API Key.*MINIMUM_SW_AGENT_API_KEY"):
                create_model_client(ModelConfig("openai", "test-model"), environ={})
            sdk_class.assert_not_called()

    def test_factory_reads_custom_environment_variable_without_exposing_key(self) -> None:
        with patch("minimum_sw_agent.model_client.OpenAI") as sdk_class:
            client = create_model_client(
                ModelConfig("openai", "test-model", "TEST_MODEL_KEY"),
                environ={"TEST_MODEL_KEY": " secret-value "},
            )
        sdk_class.assert_called_once_with(api_key="secret-value", timeout=60.0, max_retries=0)
        self.assertIsInstance(client, OpenAIModelClient)
        self.assertNotIn("secret-value", repr(client))

    def test_plain_reply_and_structured_tool_calls(self) -> None:
        sdk = Mock()
        sdk.responses.create.side_effect = [
            SimpleNamespace(id="resp_1", output_text="完成", output=[]),
            SimpleNamespace(
                id="resp_2",
                output_text="",
                output=[
                    SimpleNamespace(type="reasoning"),
                    SimpleNamespace(type="function_call", call_id="call_1", name="read_file", arguments='{"path":"a.py"}'),
                    SimpleNamespace(type="function_call", call_id="call_2", name="run_command", arguments='{"command":"pwd"}'),
                ],
            ),
        ]
        client = OpenAIModelClient("test-model", sdk)

        plain = client.generate("回答问题")
        self.assertEqual(plain.text, "完成")
        self.assertEqual(plain.tool_calls, ())
        self.assertEqual(plain.response_id, "resp_1")
        sdk.responses.create.assert_any_call(model="test-model", input="回答问题")

        tool = {"type": "function", "name": "read_file", "parameters": {"type": "object"}}
        structured = client.generate("读取文件", tools=[tool])
        self.assertEqual(structured.text, "")
        self.assertEqual(structured.response_id, "resp_2")
        self.assertEqual(structured.tool_calls, (
            ModelToolCall("call_1", "read_file", '{"path":"a.py"}'),
            ModelToolCall("call_2", "run_command", '{"command":"pwd"}'),
        ))
        sdk.responses.create.assert_any_call(model="test-model", input="读取文件", tools=[tool])

    def test_unsupported_provider_and_empty_prompt(self) -> None:
        with self.assertRaisesRegex(ValueError, "暂不支持模型供应商"):
            create_model_client(ModelConfig("other", "test-model"), environ={})
        with self.assertRaisesRegex(ValueError, "模型输入必须是非空字符串"):
            OpenAIModelClient("test-model", Mock()).generate(" ")


if __name__ == "__main__":
    unittest.main()
