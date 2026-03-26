from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from config.settings import Settings
from core.llm import completion_structured

SYSTEM = """你是微型 SaaS 立项顾问。基于已通过评审的痛点，输出一份《微型产品立项书》正文（Markdown）。
输出合法 JSON：
- title: string，产品/机会标题，简短有冲击力
- markdown_prd: string，完整 Markdown 正文，建议包含二级标题：痛点溯源、目标用户与付费意愿、竞品与差异化、MVP 功能清单、推荐技术栈、冷启动获客建议
- tech_stack: string[]，推荐技术栈条目，3-6 个
- target_audience: string，目标用户一句话
不要输出 markdown 代码块包裹 JSON。"""


class PlannerResult(BaseModel):
    title: str = ""
    markdown_prd: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    target_audience: str = ""

    @field_validator("tech_stack", mode="before")
    @classmethod
    def _coerce_tech_stack(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]


def run_planner(
    settings: Settings,
    *,
    user_story: str,
    persona: str,
    critic_reasoning: str,
    competitors_note: str,
    score: int,
    title: str,
    url: str,
    source: str,
) -> PlannerResult:
    user = f"""来源：{source}
原帖标题：{title}
链接：{url}
评审得分：{score}
评审意见：{critic_reasoning}
竞品备注：{competitors_note}
用户故事：{user_story}
用户画像：{persona}

请在 markdown_prd 开头用一行二级标题包含 emoji 可选，并注明原始出处链接。
"""
    return completion_structured(
        settings,
        system=SYSTEM,
        user=user,
        response_model=PlannerResult,
        temperature=0.4,
    )
