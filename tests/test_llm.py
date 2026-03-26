"""Tests for core.llm — _extract_json_object and completion_structured."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from core.llm import _extract_json_object


# ---------- _extract_json_object ----------


class TestExtractJsonObject:
    def test_clean_json(self):
        raw = '{"score": 85, "reasoning": "good"}'
        result = _extract_json_object(raw)
        assert result == {"score": 85, "reasoning": "good"}

    def test_json_with_surrounding_text(self):
        raw = 'Here is my answer: {"score": 42, "note": "ok"} end'
        result = _extract_json_object(raw)
        assert result["score"] == 42

    def test_markdown_wrapped_json(self):
        raw = '```json\n{"score": 90, "reasoning": "great"}\n```'
        result = _extract_json_object(raw)
        assert result == {"score": 90, "reasoning": "great"}

    def test_markdown_wrapped_with_extra_whitespace(self):
        raw = '  ```json\n  {"key": "value"}  \n```  '
        result = _extract_json_object(raw)
        assert result == {"key": "value"}

    def test_no_json_raises_value_error(self):
        with pytest.raises(ValueError, match="No JSON object"):
            _extract_json_object("no json here at all")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="No JSON object"):
            _extract_json_object("")

    def test_nested_json(self):
        raw = '{"outer": {"inner": 1}, "list": [1,2]}'
        result = _extract_json_object(raw)
        assert result["outer"] == {"inner": 1}
        assert result["list"] == [1, 2]


# ---------- completion_structured (mocked) ----------


class _DummyModel(BaseModel):
    score: int = 0
    note: str = ""


class TestCompletionStructured:
    def test_happy_path(self):
        """Mock the OpenAI client to test completion_structured end-to-end."""
        response_data = {"score": 88, "note": "looks good"}

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(response_data)
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        mock_settings = MagicMock()
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "http://localhost:8000/v1"
        mock_settings.llm_model = "test-model"

        with patch("core.llm._get_client", return_value=mock_client):
            from core.llm import completion_structured

            result = completion_structured(
                mock_settings,
                system="You are a test.",
                user="Test input",
                response_model=_DummyModel,
            )

        assert isinstance(result, _DummyModel)
        assert result.score == 88
        assert result.note == "looks good"

    def test_fallback_to_extract_json(self):
        """When the model returns non-JSON content, _extract_json_object is used."""
        raw_text = 'Here is the result: {"score": 55, "note": "partial"}'

        mock_choice = MagicMock()
        mock_choice.message.content = raw_text
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        mock_settings = MagicMock()
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = ""
        mock_settings.llm_model = "test-model"

        with patch("core.llm._get_client", return_value=mock_client):
            from core.llm import completion_structured

            result = completion_structured(
                mock_settings,
                system="sys",
                user="usr",
                response_model=_DummyModel,
            )

        assert result.score == 55
        assert result.note == "partial"
