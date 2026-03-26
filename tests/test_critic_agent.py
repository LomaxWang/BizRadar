"""Tests for CriticResult._coerce_score and PlannerResult._coerce_tech_stack validators."""

from __future__ import annotations

import pytest

from core.agents.critic_agent import CriticResult
from core.agents.planner_agent import PlannerResult


# ---------- CriticResult._coerce_score ----------


class TestCoerceScore:
    def test_int_value(self):
        r = CriticResult(score=85)
        assert r.score == 85

    def test_zero(self):
        r = CriticResult(score=0)
        assert r.score == 0

    def test_hundred(self):
        r = CriticResult(score=100)
        assert r.score == 100

    def test_float_rounds(self):
        r = CriticResult(score=72.6)
        assert r.score == 73

    def test_float_rounds_down(self):
        r = CriticResult(score=72.4)
        assert r.score == 72

    def test_string_integer(self):
        r = CriticResult(score="85")
        assert r.score == 85

    def test_string_float(self):
        r = CriticResult(score="72.6")
        assert r.score == 73

    def test_string_with_whitespace(self):
        r = CriticResult(score="  90  ")
        assert r.score == 90

    def test_string_invalid_returns_zero(self):
        r = CriticResult(score="not_a_number")
        assert r.score == 0

    def test_bool_true_returns_zero(self):
        r = CriticResult(score=True)
        assert r.score == 0

    def test_bool_false_returns_zero(self):
        r = CriticResult(score=False)
        assert r.score == 0

    def test_negative_clamped_to_zero(self):
        r = CriticResult(score=-10)
        assert r.score == 0

    def test_over_100_clamped(self):
        r = CriticResult(score=150)
        assert r.score == 100

    def test_none_coerced_to_zero(self):
        r = CriticResult(score=None)
        assert r.score == 0


# ---------- PlannerResult._coerce_tech_stack ----------


class TestCoerceTechStack:
    def test_list_of_strings(self):
        r = PlannerResult(tech_stack=["Python", "FastAPI"])
        assert r.tech_stack == ["Python", "FastAPI"]

    def test_none_becomes_empty_list(self):
        r = PlannerResult(tech_stack=None)
        assert r.tech_stack == []

    def test_single_string_becomes_list(self):
        r = PlannerResult(tech_stack="React")
        assert r.tech_stack == ["React"]

    def test_empty_string_becomes_empty_list(self):
        r = PlannerResult(tech_stack="")
        assert r.tech_stack == []

    def test_whitespace_string_becomes_empty_list(self):
        r = PlannerResult(tech_stack="   ")
        assert r.tech_stack == []

    def test_list_of_mixed_types(self):
        r = PlannerResult(tech_stack=["Python", 42, True])
        assert r.tech_stack == ["Python", "42", "True"]

    def test_non_string_non_list_wrapped(self):
        r = PlannerResult(tech_stack=42)
        assert r.tech_stack == ["42"]
