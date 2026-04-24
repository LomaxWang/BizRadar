"""Tests for core.agents.pm_agent."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from config.settings import Settings


@pytest.fixture()
def settings() -> Settings:
    return Settings(llm_api_key="fake-key", llm_model="gpt-4o-mini")


class TestPMAgent:
    def test_run_pm_returns_pm_result(self, settings: Settings) -> None:
        """run_pm 应调用 LLM 并返回 PMResult 对象。"""
        from core.agents.pm_agent import PMResult, run_pm

        mock_result = PMResult(
            user_story="作为房产中介，我希望一键排版朋友圈文案，以便不被折叠",
            persona="每天需发多条朋友圈的房产中介和微商从业者",
        )

        with patch("core.agents.pm_agent.completion_structured", return_value=mock_result):
            result = run_pm(
                settings,
                title="朋友圈发帖总被折叠，有没有工具？",
                url="https://v2ex.com/t/12345",
                extracted_complaint="发朋友圈经常被折叠，每天要浪费大量时间重新排版",
                summary="用户希望朋友圈文案不被折叠",
            )

        assert isinstance(result, PMResult)
        assert "房产中介" in result.user_story
        assert result.persona != ""

    def test_pm_result_defaults(self) -> None:
        """PMResult 默认值应全为空字符串。"""
        from core.agents.pm_agent import PMResult

        r = PMResult()
        assert r.user_story == ""
        assert r.persona == ""

    def test_run_pm_passes_all_fields(self, settings: Settings) -> None:
        """run_pm 应将所有参数正确传入 completion_structured。"""
        from core.agents.pm_agent import PMResult, run_pm

        mock_result = PMResult(user_story="some story", persona="some persona")
        captured: dict = {}

        def fake_completion(settings, *, system, user, response_model, temperature):
            captured["user"] = user
            return mock_result

        with patch("core.agents.pm_agent.completion_structured", side_effect=fake_completion):
            run_pm(
                settings,
                title="测试标题",
                url="https://example.com",
                extracted_complaint="核心抱怨内容",
                summary="摘要内容",
            )

        assert "测试标题" in captured["user"]
        assert "核心抱怨内容" in captured["user"]
        assert "摘要内容" in captured["user"]
