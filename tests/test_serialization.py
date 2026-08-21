"""针对各 provider 序列化构建器的单元测试。

会话层与具体 provider 无关；序列化逻辑位于 kova.serialization。
这些测试用于锁定各种线上传输格式（wire format），更关键的是锁定
Extended Thinking 的往返（round-trip）契约：带 tool-use 的这一轮必须把它
带签名的 thinking block 一并回传给 API（否则 Anthropic 会返回 400）。
"""

from __future__ import annotations

import pytest

from kova.conversation import (
    ConversationManager,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from kova.serialization import (
    build_anthropic_messages,
    build_chat_completion_messages,
    build_messages,
    build_openai_input,
)


def test_anthropic_preserves_signed_thinking_at_head():
    conv = ConversationManager()
    conv.add_assistant_message(
        "answer",
        tool_uses=[
            ToolUseBlock(
                tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
            )
        ],
        thinking_blocks=[ThinkingBlock(thinking="let me think", signature="sig-1")],
    )
    conv.add_tool_results_message(
        [ToolResultBlock(tool_use_id="tu-1", content="files", is_error=False)]
    )
    msgs = build_anthropic_messages(conv.get_messages())
    assert len(msgs) == 2
    content = msgs[0]["content"]
    assert content[0]["type"] == "thinking"
    assert content[0]["signature"] == "sig-1"
    assert content[-1]["type"] == "tool_use"


def test_anthropic_tool_results_become_user_blocks():
    conv = ConversationManager()
    # 需要先有 tool_use 消息
    conv.add_assistant_message(
        "I'll call the tool",
        tool_uses=[
            ToolUseBlock(
                tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
            )
        ],
    )
    conv.add_tool_results_message(
        [ToolResultBlock(tool_use_id="tu-1", content="out", is_error=False)]
    )
    msgs = build_anthropic_messages(conv.get_messages())
    assert msgs[0]["role"] == "assistant"
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"][0]["type"] == "tool_result"
    assert msgs[1]["content"][0]["tool_use_id"] == "tu-1"


def test_anthropic_merges_system_reminder_into_prev_user():
    conv = ConversationManager()
    conv.add_user_message("hello")
    conv.add_system_reminder("note")
    msgs = build_anthropic_messages(conv.get_messages())
    assert len(msgs) == 1
    assert "hello" in msgs[0]["content"]
    assert "system-reminder" in msgs[0]["content"]


def test_openai_input_tool_use_as_function_call():
    conv = ConversationManager()
    conv.add_assistant_message(
        "text",
        tool_uses=[
            ToolUseBlock(
                tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
            )
        ],
    )
    conv.add_tool_results_message(
        [ToolResultBlock(tool_use_id="tu-1", content="files")]
    )
    msgs = build_openai_input(conv.get_messages())
    # 找到 function_call 类型的消息
    func_calls = [m for m in msgs if m.get("type") == "function_call"]
    assert len(func_calls) == 1
    assert func_calls[0]["name"] == "Bash"


def test_openai_input_tool_results_as_function_call_output():
    conv = ConversationManager()
    # 需要先有 tool_use 消息
    conv.add_assistant_message(
        "Calling tool",
        tool_uses=[
            ToolUseBlock(
                tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
            )
        ],
    )
    conv.add_tool_results_message([ToolResultBlock(tool_use_id="tu-1", content="out")])
    msgs = build_openai_input(conv.get_messages())
    # 找到 function_call_output 类型的消息
    output_msgs = [m for m in msgs if m.get("type") == "function_call_output"]
    assert len(output_msgs) == 1
    assert output_msgs[0]["output"] == "out"


def test_chat_completion_uses_tool_calls_with_reasoning_content():
    conv = ConversationManager()
    conv.add_assistant_message(
        "text",
        tool_uses=[
            ToolUseBlock(
                tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
            )
        ],
        thinking_blocks=[ThinkingBlock(thinking="let me think", signature="sig")],
    )
    conv.add_tool_results_message(
        [ToolResultBlock(tool_use_id="tu-1", content="files")]
    )
    msgs = build_chat_completion_messages(conv.get_messages())
    # 找到 assistant 消息（包含 tool_calls）
    assistant_msgs = [m for m in msgs if m.get("role") == "assistant"]
    assert len(assistant_msgs) >= 1
    assert assistant_msgs[0]["tool_calls"][0]["function"]["name"] == "Bash"
    # thinking blocks 作为 reasoning_content 回传（DeepSeek/小米等 provider 要求）
    assert assistant_msgs[0]["reasoning_content"] == "let me think"


def test_chat_completion_no_reasoning_when_no_thinking():
    conv = ConversationManager()
    conv.add_assistant_message(
        "text",
        tool_uses=[
            ToolUseBlock(
                tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
            )
        ],
    )
    conv.add_tool_results_message(
        [ToolResultBlock(tool_use_id="tu-1", content="files")]
    )
    msgs = build_chat_completion_messages(conv.get_messages())
    assistant_msgs = [m for m in msgs if m.get("role") == "assistant"]
    assert "reasoning_content" not in assistant_msgs[0]


def test_openai_input_includes_reasoning_items():
    conv = ConversationManager()
    conv.add_assistant_message(
        "text",
        tool_uses=[
            ToolUseBlock(
                tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
            )
        ],
        thinking_blocks=[ThinkingBlock(thinking="reasoning here", signature="rs-001")],
    )
    conv.add_tool_results_message(
        [ToolResultBlock(tool_use_id="tu-1", content="files")]
    )
    msgs = build_openai_input(conv.get_messages())
    # 第一个 item 应该是 reasoning
    reasoning_items = [m for m in msgs if m.get("type") == "reasoning"]
    assert len(reasoning_items) >= 1
    assert reasoning_items[0]["id"] == "rs-001"
    assert reasoning_items[0]["summary"][0]["text"] == "reasoning here"


def test_build_messages_dispatch_by_protocol():
    conv = ConversationManager()
    conv.add_user_message("hi")
    msgs = conv.get_messages()
    assert build_messages(msgs, "anthropic") == build_anthropic_messages(msgs)
    assert build_messages(msgs, "openai") == build_openai_input(msgs)
    assert build_messages(msgs, "openai-compat") == build_chat_completion_messages(msgs)


class TestSerializationToolCallValidation:
    """测试序列化时的 tool_calls/tool_results 严格配对验证。"""

    def test_anthropic_rejects_missing_tool_result(self):
        """Anthropic 序列化：tool_call 后没有紧跟 tool_result 应报错。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "I'll call a tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        # 错误：添加一个普通 user 消息而不是 tool_result
        conv.add_user_message("some other message")

        with pytest.raises(ValueError, match="pending tool_result"):
            build_anthropic_messages(conv.get_messages())

    def test_anthropic_rejects_wrong_tool_result_id(self):
        """Anthropic 序列化：tool_result id 不匹配应报错。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "I'll call a tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        # 错误：tool_result 的 id 与 tool_use 不匹配
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-WRONG", content="wrong")]
        )

        with pytest.raises(ValueError, match="no matching pending tool_use"):
            build_anthropic_messages(conv.get_messages())

    def test_anthropic_accepts_valid_sequence(self):
        """Anthropic 序列化：正确的 tool_call/result 序列应通过。"""
        conv = ConversationManager()
        conv.add_user_message("Do something")
        conv.add_assistant_message(
            "Calling tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-1", content="result")]
        )

        # 不应该抛出异常
        msgs = build_anthropic_messages(conv.get_messages())
        assert len(msgs) == 3

    def test_anthropic_rejects_multiple_missing_results(self):
        """Anthropic 序列化：多个 tool_call 后紧跟另一个 tool_call 应报错。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "First call",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        # 错误：在提供 tu-1 的结果之前又调用了另一个工具
        conv.add_assistant_message(
            "Second call",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-2",
                    tool_name="ReadFile",
                    arguments={"path": "a.txt"},
                )
            ],
        )

        with pytest.raises(ValueError, match="pending tool_result"):
            build_anthropic_messages(conv.get_messages())

    def test_openai_rejects_missing_tool_result(self):
        """OpenAI 序列化：tool_call 后没有紧跟 tool_result 应报错。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "I'll call a tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_user_message("interrupting message")

        with pytest.raises(ValueError, match="pending tool_result"):
            build_openai_input(conv.get_messages())

    def test_openai_rejects_wrong_tool_result_id(self):
        """OpenAI 序列化：tool_result id 不匹配应报错。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "I'll call a tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-WRONG", content="wrong")]
        )

        with pytest.raises(ValueError, match="no matching pending tool_use"):
            build_openai_input(conv.get_messages())

    def test_openai_accepts_valid_sequence(self):
        """OpenAI 序列化：正确的 tool_call/result 序列应通过。"""
        conv = ConversationManager()
        conv.add_user_message("Do something")
        conv.add_assistant_message(
            "Calling tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-1", content="result")]
        )

        msgs = build_openai_input(conv.get_messages())
        assert len(msgs) >= 3

    def test_chat_completion_rejects_missing_tool_result(self):
        """Chat Completion 序列化：tool_call 后没有紧跟 tool_result 应报错。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "I'll call a tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_user_message("interrupting message")

        with pytest.raises(ValueError, match="pending tool_result"):
            build_chat_completion_messages(conv.get_messages())

    def test_chat_completion_rejects_wrong_tool_result_id(self):
        """Chat Completion 序列化：tool_result id 不匹配应报错。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "I'll call a tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-WRONG", content="wrong")]
        )

        with pytest.raises(ValueError, match="no matching pending tool_use"):
            build_chat_completion_messages(conv.get_messages())

    def test_chat_completion_accepts_valid_sequence(self):
        """Chat Completion 序列化：正确的 tool_call/result 序列应通过。"""
        conv = ConversationManager()
        conv.add_user_message("Do something")
        conv.add_assistant_message(
            "Calling tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-1", content="result")]
        )

        msgs = build_chat_completion_messages(conv.get_messages())
        assert len(msgs) == 3

    def test_multiple_tools_must_all_have_results(self):
        """多个 tool_call 必须都有对应的 tool_result。"""
        conv = ConversationManager()
        conv.add_assistant_message(
            "Calling multiple tools",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                ),
                ToolUseBlock(
                    tool_use_id="tu-2",
                    tool_name="ReadFile",
                    arguments={"path": "a.txt"},
                ),
            ],
        )
        # 只提供了 tu-1 的结果，tu-2 缺失
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-1", content="result1")]
        )
        # 添加一个新消息来触发验证（序列化时检查 pending_tool_ids）
        conv.add_user_message("interrupting")

        with pytest.raises(ValueError, match="pending tool_result"):
            build_anthropic_messages(conv.get_messages())
