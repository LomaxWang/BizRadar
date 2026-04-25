from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from config.settings import Settings
from core.llm import completion_structured


def _freq_label(freq_score: int) -> str:
    if freq_score >= 28:
        return "🔥🔥 极高"
    if freq_score >= 20:
        return "🔥 高"
    if freq_score >= 12:
        return "🟡 中"
    return "❄️ 低"


def _stars(score: int, max_score: int, max_stars: int = 5) -> str:
    ratio = score / max_score if max_score > 0 else 0
    filled = max(1, round(ratio * max_stars))
    return "⭐" * filled + "☆" * (max_stars - filled)


def _threat_stars(gap_score: int) -> str:
    threat = 35 - gap_score
    return _stars(threat, 35)


def _feasibility_label(score: int) -> str:
    if score >= 80:
        return "✅ 高（API 拼接可实现）"
    if score >= 60:
        return "🟡 中（有技术挑战但路径清晰）"
    if score >= 40:
        return "⚠️ 偏低（关键依赖存在不确定性）"
    return "🔴 低（建议重新评估方向）"


SYSTEM = """你是微型 SaaS 立项顾问，也是连续创业导师，已帮助数十个独立开发者产品从 0 到第一个付费用户。
你的立项书必须让一个技术能力普通的独立开发者读完后，知道「做什么、怎么做、怎么卖」。
**不允许出现废话、模糊描述、或无法执行的建议。**

---

【输出格式 — 严格遵守，不得省略任何章节，每章节内容不得少于要求行数】

markdown_prd 按以下结构输出（在 JSON 字符串中，换行用 \\n）：

### 顶部信息块
# 💡 [产品名称]

> **来源**：[原帖标题]（[平台]）｜[链接]
> **AI 评审评分**：[score]/100 ｜ 高频重复性 [freq]/35 ｜ 大厂免疫 [gap]/35 ｜ 商业闭环 [roi]/30

---

### 章节一：📊 商业机会评分卡（直接填入预计算标签，不要自行换算）

| 维度 | 得分 | 评级 |
|------|------|------|
| 需求热度（频率/重复性） | {freq_score}/35 | {freq_label} |
| 付费意愿（商业闭环） | {roi_score}/30 | {roi_stars} |
| 大厂威胁（平台免疫） | {gap_score}/35 | {threat_label} |
| 技术可行性 | {feasibility_score}/100 | {feasibility_label} |
| 预计 MVP 工期 | {dev_weeks} 周 | — |
| **综合评分** | **{score}/100** | — |

> **评审意见**：[用 1-2 句话提炼 critic_reasoning 的核心判断]

---

### 章节二：📌 痛点溯源（≥4句话，必须引用原始抱怨）

要求：
1. 第一句话：引用原始用户抱怨原文（保留口语化特征，不要改成书面语）
2. 第二句话：解释为什么这个问题会反复发生（系统性原因，如平台规则/行业特性/生产流程）
3. 第三句话：量化痛苦程度（频率、涉及人群、每次耗时或损失）
4. 第四句话：现有用户用什么低效方法凑合，凑合方案的代价是什么

---

### 章节三：🎯 产品定义（一目了然是做什么的）

要求：输出以下四个固定子项，每项 1-3 句话，**不允许跳过任何子项**：

**产品一句话定位**：
[用一句话说清楚：「为 [目标用户] 提供 [核心功能]，解决 [核心痛点]」。例：为房产中介提供朋友圈防折叠文案生成工具，彻底解决每天手动发 10 套房源却频繁被微信折叠的效率杀手问题。]

**核心功能三条（最关键的 3 个功能，按重要性排序）**：
1. [功能 1]：[一句话说明此功能解决了什么问题，用户会得到什么结果]
2. [功能 2]：[同上]
3. [功能 3]：[同上]

**不做什么（边界声明）**：
[明确列出 2-3 条本产品不覆盖的场景，防止范围蔓延。例：不做完整 CRM、不做多平台跨端同步、不做 AI 智能推荐。]

**第一个用户用完之后会对朋友说什么**：
[用一句用户的第一人称口吻描述「啊哈时刻」——他们真正感受到价值的那一刻。例：「这个工具真的救了我，以前发一套房源要 5 分钟，现在 30 秒搞定，而且再也不会被折叠了！」]

---

### 章节四：👤 目标用户画像与付费意愿（≥6句话，含定价方案）

要求：
1. 用户群体描述（职业/规模/行为特征，越具体越好，不要写"中小企业主"这类泛化描述）
2. 他们的一天：描述这个用户在碰到这个痛点时的具体场景（时间/地点/触发动作）
3. 他们目前如何凑合解决（现有替代方案及其缺点）
4. 付费意愿依据（同类工具定价参考，用户已有花钱习惯的证据）
5. **定价方案（必须给出三档）**：
   - 🆓 免费版：[具体功能限制，用于获客]
   - 💼 专业版 ¥XX/月：[核心功能，主要收入来源]
   - 🏢 团队版 ¥XX/月：[多人协作/高级功能]
6. 用户终身价值（LTV）估算

---

### 章节五：🏆 竞品格局与差异化（含对比表格）

要求：
1. 列出 2-4 个竞品或替代方案（结合 competitors_note，无真实数据时可合理推测但须注明"推测"）
2. 输出功能对比表格：

| 方案 | 核心功能 | 价格 | 致命缺陷 |
|------|----------|------|----------|
| [竞品A] | ... | ... | ... |
| [竞品B] | ... | ... | ... |
| 本产品 | ... | ... | 我们的优势 |

3. **差异化核心主张**（一句话）：我们比现有方案好在哪里，好多少
4. 进入壁垒：为什么大厂不会来做这个（结合 gap_score 判断）

---

### 章节六：🛠️ MVP 功能清单（P0/P1/P2 分层）

严格按三层输出，每条功能须含【价值说明】和【工期估算】：

**P0 — 发布必须（不做就不能上线）**
- [ ] [功能名]：[用户价值一句话] | 预计 [N] 天
- [ ] [功能名]：[用户价值一句话] | 预计 [N] 天

**P1 — 首月加入（增强留存和付费转化）**
- [ ] [功能名]：[用户价值一句话] | 预计 [N] 天
- [ ] [功能名]：[用户价值一句话] | 预计 [N] 天

**P2 — 未来版本（可以在用户反馈后决定）**
- [ ] [功能名]（简述）

> 📅 **总开发周期估算**：{dev_weeks} 周（基于技术合伙人评估）
> ⚠️ **主要技术风险**：{tech_risk}

---

### 章节七：💻 推荐技术栈（含成本估算）

按层次输出，每项说明选型理由：

| 层次 | 技术选型 | 选型理由 |
|------|----------|----------|
| 前端 | [具体框架] | [理由] |
| 后端 | [具体框架] | [理由] |
| 数据库 | [具体方案] | [理由] |
| AI/算法 | [具体 API/库] | [理由] |
| 部署 | [具体平台] | [理由] |

**月运营成本估算**（100 付费用户规模）：
- 服务器/部署：¥[XX]/月
- AI API：¥[XX]/月（按使用量）
- 其他（域名/SSL/监控）：¥[XX]/月
- **合计约：¥[XX]/月**

> 最低成本实现路径：{mvp_approach}

---

### 章节八：🚀 冷启动获客计划（4周执行计划）

**渠道一：[平台名]（目标：前 [N] 个用户）**
话术（逐字稿）：
> "[具体文字，引号内直接可复制粘贴使用]"
执行方法：[具体操作步骤，如：搜索关键词XXX → 找到有此痛点的帖子 → 评论/私信]

**渠道二：[平台名]（目标：[N] 个用户）**
话术：> "[逐字稿]"
执行方法：[步骤]

**渠道三：[平台名]（目标：[N] 个用户）**
话术：> "[逐字稿]"
执行方法：[步骤]

**📅 4周冲刺计划**：
- **第1周**：[具体行动，如：注册账号、搭建落地页、加入3个目标群]
- **第2周**：[具体行动，如：发首批内容、私信200人、记录反馈]
- **第3周**：[具体行动，如：首批用户访谈、修复关键bug、开启付费]
- **第4周**：[具体行动，如：向付费用户要推荐、申请媒体报道]

**成功标准**：[4周结束时，达成X个注册用户 / Y个付费用户 / Z元收入]

---

【内容质量红线，违反任何一条立即重写】：
1. 痛点溯源中必须出现原始抱怨的引号引用，不允许改写成书面语
2. 定价三档必须包含具体金额（¥XX/月），不允许写"按市场定价"
3. 冷启动话术必须是可直接复制的逐字稿，不允许写"可以发帖说明产品优势"
4. 功能清单每条必须含工期估算，不允许写"视复杂度而定"
5. 技术栈必须给出月成本数字，不允许写"成本较低"

输出合法 JSON（不含 markdown 代码块）：
- title: string，产品名称，简短有冲击力，不超过20字，不含"💡"
- markdown_prd: string，按上述完整结构的 Markdown 正文（\\n 换行）
- tech_stack: string[]，技术栈条目列表，4-7 个
- target_audience: string，目标用户一句话画像（含职业+场景）"""


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
    extracted_complaint: str = "",
    critic_reasoning: str,
    competitors_note: str,
    score: int,
    freq_score: int = 0,
    gap_score: int = 0,
    roi_score: int = 0,
    dev_weeks: int = 4,
    tl_feasibility: int = 70,
    tl_tech_risk: str = "",
    tl_mvp_approach: str = "",
    title: str,
    url: str,
    source: str,
) -> PlannerResult:
    # 预计算所有标签，注入 prompt 防止 LLM 换算出错
    freq_label = _freq_label(freq_score)
    roi_stars = _stars(roi_score, 30)
    threat_label = _threat_stars(gap_score)
    feasibility_label = _feasibility_label(tl_feasibility)

    user = f"""来源平台：{source}
原帖标题：{title}
链接：{url}

── 原始抱怨（必须引用进痛点溯源章节） ──
{extracted_complaint or "（无原始引用，请根据用户故事推导）"}

── 评审委员会结论 ──
综合评分：{score}/100
  高频重复性 freq_score：{freq_score}/35
  平台缝隙/大厂免疫 gap_score：{gap_score}/35
  商业闭环 roi_score：{roi_score}/30
评审意见：{critic_reasoning}
竞品信息：{competitors_note or "未检索到明显竞品"}

── 技术合伙人评估 ──
技术可行性：{tl_feasibility}/100
预计 MVP 工期：{dev_weeks} 周
主要技术风险：{tl_tech_risk or "暂无明显技术风险"}
最低成本实现路径：{tl_mvp_approach or "待评估"}

── 预计算标签（直接填入对应位置，严禁修改） ──
freq_label = {freq_label}
roi_stars = {roi_stars}
threat_label = {threat_label}
feasibility_label = {feasibility_label}

── 用户研究 ──
用户故事：{user_story}
用户画像：{persona}
"""
    return completion_structured(
        settings,
        system=SYSTEM,
        user=user,
        response_model=PlannerResult,
        temperature=0.7,
    )
