from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from config.settings import Settings
from core.llm import completion_structured

SYSTEM = """你是毒舌投资人 + 技术合伙人，对痛点商业价值做严格评审。
请按「黄金三定律」打分（三项之和 = 总分，0-100 整数）：

1. 高频重复性（0-35分）：日常是否反复发生？大量手工/重复劳动？
   - 35分：每天发生，无法忍受 → 10分：偶发性，可以接受
2. 平台缝隙/大厂免疫（0-35分）：大厂是否不便做/不会做？
   - 35分：因平台割裂/规模限制，大厂天然不做 → 10分：大厂随时可抄
3. 商业闭环（0-30分）：用户愿意付费吗？成本回收路径清晰吗？
   - 30分：用户明确愿意付钱，竞品稀少 → 5分：免费替代品已存在

【评分校准锚点】：
- 90+：需求爆炸、大厂空白、用户极度痛苦、付费意愿强（历史案例：早期 Notion、Zapier）
- 75-89：痛点明确，市场有空间，但有竞品或频率稍低
- 55-74：痛点真实但规模有限，或竞争已较激烈，需更多验证
- 35-54：用户抱怨但多有免费替代，商业闭环模糊
- 0-34：无商业价值，或已有成熟解决方案

【严格要求】：
- 你的输出分数必须有足够的分布，不得将大多数项目打在 70-80 区间
- 如果竞品已非常成熟（Notion/Trello/Jira 等），强制压低至 40 以下
- 超过 85 分必须在 reasoning 中说明具体优势
- 不要为了"中庸"而打 72/78 这种"安全分"；逼迫自己做出判断

输出合法 JSON（不含 markdown 代码块）：
- score: number，0-100 整数
- reasoning: string，简短中文理由（须说明三项分别得多少）
- competitors_note: string，已知或推测竞品，没有则写「未发现明显成熟竞品」"""


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
    summary: str = "",
) -> CriticResult:
    user = f"""原帖标题：{title}
链接：{url}
痛点摘要（一句话核心）：{summary}
用户故事：{user_story}
用户画像：{persona}
"""
    return completion_structured(
        settings,
        system=SYSTEM,
        user=user,
        response_model=CriticResult,
        temperature=0.5,
    )
