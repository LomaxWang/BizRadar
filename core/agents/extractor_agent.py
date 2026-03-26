from __future__ import annotations

from pydantic import BaseModel, Field

from config.settings import Settings
from core.llm import completion_structured
from plugins.base_scraper import RawItem

SYSTEM = """你是 IdeaHunter 的「痛点提取」助手。只根据给定帖子判断是否存在可做成小工具/SaaS 的「抱怨、痛点、效率浪费」。
输出必须是合法 JSON 对象，字段：
- has_pain_point: boolean
- summary: string，一句话概括（无痛点可为空）
- extracted_complaint: string，提炼出的核心抱怨原文风格复述（无痛点可为空）
不要输出 markdown 代码块。"""


class ExtractorResult(BaseModel):
    has_pain_point: bool = Field(default=False)
    summary: str = ""
    extracted_complaint: str = ""


def run_extractor(settings: Settings, item: RawItem) -> ExtractorResult:
    user = f"""标题：{item.title}
链接：{item.url}
来源：{item.source}
正文：
{item.body}
"""
    return completion_structured(
        settings,
        system=SYSTEM,
        user=user,
        response_model=ExtractorResult,
        temperature=0.1,
    )
