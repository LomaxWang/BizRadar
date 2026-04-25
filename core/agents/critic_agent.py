from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from config.settings import Settings
from core.llm import completion_structured

SYSTEM = """你是毒舌投资人 + 技术合伙人，对痛点商业价值做严格评审。
请按「黄金三定律」打分，**三项子分之和 = score 总分**：

1. 高频重复性 freq_score（0-35分）：日常是否反复发生？大量手工/重复劳动？
   - 35分：每天发生，无法忍受 | 10分：偶发性，可以接受
2. 平台缝隙/大厂免疫 gap_score（0-35分）：大厂是否不便做/不会做？
   - 35分：因平台割裂/规模限制，大厂天然不做 | 10分：大厂随时可抄
3. 商业闭环 roi_score（0-30分）：用户愿意付费吗？成本回收路径清晰吗？
   - 30分：用户明确愿意付钱，竞品稀少 | 5分：免费替代品已存在

【竞品参考】：
- 若用户信息中提供了真实竞品搜索结果，**优先据此判断竞品成熟度**，并直接影响 roi_score
- 若竞品成熟度高（Notion/Trello/Jira 级别），roi_score 强制 ≤10，score 压至 40 以下
- 若搜索结果显示竞品稀少或均为弱竞品，可适当拉高 roi_score

【技术可行性参考】：
- 若用户信息中提供了「技术评估」，参考其中的 feasibility_score 与 dev_weeks
- feasibility_score < 50：说明该方案技术壁垒极高或存在平台违规风险，freq_score 强制扣减 10 分
- dev_weeks > 12：说明独立开发者难以快速验证，gap_score 酌情扣减 5 分
- 这些惩罚项已体现在你的子分中，无需额外说明

【评分校准锚点】：
- 90+：需求爆炸、大厂空白、用户极度痛苦、付费意愿强
- 75-89：痛点明确，市场有空间，但有竞品或频率稍低
- 55-74：痛点真实但规模有限，或竞争已较激烈
- 35-54：用户抱怨但多有免费替代，商业闭环模糊
- 0-34：无商业价值，或已有成熟解决方案

【严格要求】：
- freq_score + gap_score + roi_score 必须严格等于 score
- 不得将大多数项目打在 70-80 区间，超过 85 分须在 reasoning 中说明具体优势
- 不要为了"中庸"而打 72/78 这种"安全分"；逼迫自己做出判断

输出合法 JSON（不含 markdown 代码块），字段：
- score: number，0-100 整数（= freq_score + gap_score + roi_score）
- freq_score: number，0-35 整数
- gap_score: number，0-35 整数
- roi_score: number，0-30 整数
- reasoning: string，中文理由，须说明三项各得多少分及原因
- competitors_note: string，基于搜索结果的竞品判断，无真实搜索则写推测"""


class CriticResult(BaseModel):
    score: int = Field(default=0, ge=0, le=100)
    freq_score: int = Field(default=0, ge=0, le=35)   # 高频重复性
    gap_score: int = Field(default=0, ge=0, le=35)    # 平台缝隙/大厂免疫
    roi_score: int = Field(default=0, ge=0, le=30)    # 商业闭环
    reasoning: str = ""
    competitors_note: str = ""

    @field_validator("score", "freq_score", "gap_score", "roi_score", mode="before")
    @classmethod
    def _coerce_int(cls, v: object) -> int:
        if isinstance(v, bool):
            return 0
        if isinstance(v, float):
            return int(round(v))
        if isinstance(v, str):
            try:
                return int(round(float(v.strip())))
            except ValueError:
                return 0
        try:
            return int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0

    def model_post_init(self, __context: object) -> None:
        """若 LLM 子分之和与 score 出入过大，以子分之和为准修正 score。"""
        sub_sum = self.freq_score + self.gap_score + self.roi_score
        if sub_sum > 0 and abs(sub_sum - self.score) > 3:
            object.__setattr__(self, "score", max(0, min(100, sub_sum)))


def run_critic(
    settings: Settings,
    *,
    user_story: str,
    persona: str,
    title: str,
    url: str,
    summary: str = "",
    competitor_context: str = "",   # 真实竞品搜索结果（可选）
    tech_context: str = "",         # Tech Lead 技术评估（可选）
) -> CriticResult:
    comp_section = (
        f"\n\n{competitor_context}"
        if competitor_context
        else "\n\n【竞品搜索】：未执行（SERPER_API_KEY 未配置），请凭已有知识推测。"
    )
    tech_section = (
        f"\n\n{tech_context}"
        if tech_context
        else ""
    )
    user = f"""原帖标题：{title}
链接：{url}
痛点摘要（一句话核心）：{summary}
用户故事：{user_story}
用户画像：{persona}{comp_section}{tech_section}
"""
    return completion_structured(
        settings,
        system=SYSTEM,
        user=user,
        response_model=CriticResult,
        temperature=0.5,
    )
