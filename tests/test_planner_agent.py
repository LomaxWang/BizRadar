"""Tests for core.agents.planner_agent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings


@pytest.fixture()
def settings() -> Settings:
    return Settings(llm_api_key="fake-key", llm_model="gpt-4o-mini")


class TestPlannerAgent:
    def test_run_planner_returns_planner_result(self, settings: Settings) -> None:
        """run_planner 应调用 LLM 并返回 PlannerResult 对象。"""
        from core.agents.planner_agent import PlannerResult, run_planner

        mock_result = PlannerResult(
            title="朋友圈防折叠排版工具",
            markdown_prd="## 微型产品立项书\n\n痛点溯源：...",
            tech_stack=["FastAPI", "Vue3", "Kimi API"],
            target_audience="房产中介/微商从业者",
        )

        with patch("core.agents.planner_agent.completion_structured", return_value=mock_result):
            result = run_planner(
                settings,
                user_story="作为房产中介，我希望一键排版朋友圈文案，以便不被折叠",
                persona="房产中介，日均发3条朋友圈",
                critic_reasoning="高频、平台缝隙、用户愿意付费",
                competitors_note="未发现成熟竞品",
                score=88,
                title="朋友圈折叠问题",
                url="https://v2ex.com/t/12345",
                source="v2ex",
            )

        assert isinstance(result, PlannerResult)
        assert result.title == "朋友圈防折叠排版工具"
        assert len(result.tech_stack) == 3
        assert result.target_audience != ""

    def test_planner_result_defaults(self) -> None:
        """PlannerResult 默认值应全为空/空列表。"""
        from core.agents.planner_agent import PlannerResult

        r = PlannerResult()
        assert r.title == ""
        assert r.markdown_prd == ""
        assert r.tech_stack == []
        assert r.target_audience == ""

    def test_tech_stack_coercion_from_string(self) -> None:
        """当 tech_stack 是字符串时应被转为单元素列表。"""
        from core.agents.planner_agent import PlannerResult

        r = PlannerResult.model_validate(
            {"title": "t", "markdown_prd": "m", "tech_stack": "FastAPI", "target_audience": "a"}
        )
        assert r.tech_stack == ["FastAPI"]

    def test_tech_stack_coercion_from_none(self) -> None:
        """tech_stack 为 None 时应被转为空列表。"""
        from core.agents.planner_agent import PlannerResult

        r = PlannerResult.model_validate(
            {"title": "t", "markdown_prd": "m", "tech_stack": None, "target_audience": "a"}
        )
        assert r.tech_stack == []

    def test_tech_stack_coercion_from_list(self) -> None:
        """tech_stack 为混合类型列表时应强制转为字符串列表。"""
        from core.agents.planner_agent import PlannerResult

        r = PlannerResult.model_validate(
            {
                "title": "t",
                "markdown_prd": "m",
                "tech_stack": ["FastAPI", 42, None],
                "target_audience": "a",
            }
        )
        assert r.tech_stack == ["FastAPI", "42", "None"]
