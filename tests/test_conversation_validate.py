"""针对 conversation.py 中消息顺序验证的单元测试。

验证 tool_calls 和 tool_results 必须严格配对的规则。
"""

from __future__ import annotations

import pytest

from kova.conversation import (
    ConversationManager,
    ToolResultBlock,
    ToolUseBlock,
)


class TestValidateMessageOrder:
    """测试 validate_message_order 方法的各种场景。"""

    def test_valid_simple_tool_call_and_result(self):
        """正常的 tool_call 后紧跟 tool_result，应该通过。"""
        conv = ConversationManager()
        conv.add_user_message("Do something")
        conv.add_assistant_message(
            "I'll call the tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-1", content="files", is_error=False)]
        )

        errors = conv.validate_message_order()
        assert errors == []

    def test_valid_multiple_tool_calls_and_results(self):
        """多个 tool_calls 后紧跟对应的 tool_results，应该通过。"""
        conv = ConversationManager()
        conv.add_user_message("Do two things")
        conv.add_assistant_message(
            "I'll call two tools",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                ),
                ToolUseBlock(
                    tool_use_id="tu-2",
                    tool_name="ReadFile",
                    arguments={"file_path": "/tmp/test.txt"},
                ),
            ],
        )
        conv.add_tool_results_message(
            [
                ToolResultBlock(tool_use_id="tu-1", content="output1", is_error=False),
                ToolResultBlock(tool_use_id="tu-2", content="content", is_error=False),
            ]
        )

        errors = conv.validate_message_order()
        assert errors == []

    def test_missing_tool_result(self):
        """有 tool_call 但没有对应的 tool_result，应该报错。"""
        conv = ConversationManager()
        conv.add_user_message("Do something")
        conv.add_assistant_message(
            "I'll call the tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        # 没有 add_tool_results_message，直接结束

        errors = conv.validate_message_order()
        assert len(errors) == 1
        assert "tu-1" in errors[0]
        assert "no corresponding tool_result" in errors[0]

    def test_extra_tool_result_without_tool_call(self):
        """有 tool_result 但没有对应的 tool_call，应该报错。"""
        conv = ConversationManager()
        conv.add_user_message("previous context")
        # 直接添加 tool_result 而没有先添加带 tool_use 的 assistant 消息
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-999", content="orphan result")]
        )

        errors = conv.validate_message_order()
        assert len(errors) == 1
        assert "tu-999" in errors[0]
        assert "no matching tool_use" in errors[0]

    def test_mismatched_tool_result_id(self):
        """tool_result 的 id 与 tool_call 不匹配，应该报错。"""
        conv = ConversationManager()
        conv.add_user_message("Do something")
        conv.add_assistant_message(
            "I'll call the tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        # 错误：应该是 tu-1 但写成了 tu-2
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-2", content="wrong id")]
        )

        errors = conv.validate_message_order()
        assert len(errors) == 2  # tu-1 缺失 + tu-2 找不到匹配
        error_ids = " ".join(errors)
        assert "tu-1" in error_ids
        assert "tu-2" in error_ids

    def test_user_text_between_tool_call_and_result(self):
        """在 tool_call 和 tool_result 之间插入纯文本 user 消息，应该报错。"""
        conv = ConversationManager()
        conv.add_user_message("Do something")
        conv.add_assistant_message(
            "I'll call the tool",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                )
            ],
        )
        # 错误：在 tool_result 之前插入了纯文本 user 消息
        conv.add_user_message("This is an intermediate user message")
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-1", content="result")]
        )

        errors = conv.validate_message_order()
        assert len(errors) >= 1
        assert any("pending" in e for e in errors)

    def test_multiple_pending_tool_results(self):
        """有多个待匹配的 tool_call，只匹配了部分，应该报错。"""
        conv = ConversationManager()
        conv.add_user_message("Do three things")
        conv.add_assistant_message(
            "I'll call three tools",
            tool_uses=[
                ToolUseBlock(
                    tool_use_id="tu-1", tool_name="Bash", arguments={"command": "ls"}
                ),
                ToolUseBlock(
                    tool_use_id="tu-2",
                    tool_name="ReadFile",
                    arguments={"path": "a.txt"},
                ),
                ToolUseBlock(
                    tool_use_id="tu-3", tool_name="Glob", arguments={"pattern": "*.py"}
                ),
            ],
        )
        # 只提供了 tu-1 的结果，tu-2 和 tu-3 缺失
        conv.add_tool_results_message(
            [ToolResultBlock(tool_use_id="tu-1", content="result1")]
        )

        errors = conv.validate_message_order()
        assert len(errors) == 1
        assert "tu-2" in errors[0] or "tu-3" in errors[0]
        assert "no corresponding tool_result" in errors[0]

    def test_empty_conversation(self):
        """空对话应该通过验证。"""
        conv = ConversationManager()
        errors = conv.validate_message_order()
        assert errors == []

    def test_conversation_without_tools(self):
        """没有工具调用的正常对话应该通过验证。"""
        conv = ConversationManager()
        conv.add_user_message("Hello")
        conv.add_assistant_message("Hi there!")
        conv.add_user_message("How are you?")
        conv.add_assistant_message("I'm fine, thanks!")

        errors = conv.validate_message_order()
        assert errors == []
