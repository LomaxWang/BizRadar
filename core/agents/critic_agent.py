from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from config.settings import Settings
from core.llm import completion_structured

SYSTEM = """你是毒舌投资人 + 技术合伙人，需同时评估商业与实现成本。
请严格按「黄金三定律」打分（每项 roughly 0-33，总分 0-100，可非整数但 JSON 里用整数）：
1) 高频重复：是否日常发生、是否大量手工/复制粘贴类劳动
2) 平台缝隙/大厂免疫：是否因平台割裂或大厂不便做而有机会
3) 商业闭环/ROI：用户是否愿意为省时间付费；是否容易找到竞品若已有成熟竞品则压低分

另请简要考虑技术可行性：若必须自训大模型或周期明显超过两个月，应在 reasoning 中说明并压低总分。

输出合法 JSON：
- score: number，0-100 的整数
- reasoning: string，简短中文理由
- competitors_note: string，已知或推测的竞品情况，没有则写「未发现明显成熟竞品」
不要输出 markdown 代码块。"""


class CriticResult(BaseModel):
    score: int = Field(default=0, ge=0, le=100)
    reasoning: str = ""
    competitors_note: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def _coerce_score(cls, v: object) -> int:
        if isinstance(v, bool):
            return 0
        if isinstance(v, float):
            x = int(round(v))
        elif isinstance(v, str):
            try:
                x = int(round(float(v.strip())))
            except ValueError:
                x = 0
        else:
            try:
                x = int(v)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                x = 0
        return max(0, min(100, x))


def run_critic(
    settings: Settings,
    *,
    user_story: str,
    persona: str,
    title: str,
    url: str,
) -> CriticResult:
    user = f"""原帖标题：{title}
链接：{url}
用户故事：{user_story}
用户画像：{persona}
"""
    return completion_structured(
        settings,
        system=SYSTEM,
        user=user,
        response_model=CriticResult,
        temperature=0.3,
    )
