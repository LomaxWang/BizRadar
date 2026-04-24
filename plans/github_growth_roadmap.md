# 🚀 IdeaHunter GitHub 高 Star 增长路线图

> 目标：打造 GitHub 高 Star 开源项目
> 参考标杆：AutoGPT / MetaGPT / Perplexica / OpenManus
> 最后更新：2026-04-12

---

## 一、当前核心差距诊断

### ❌ 没有「Wow 时刻」
高 Star 项目都有一个 **30 秒内震撼用户的 Demo**。当前问题：
- README 无动图 / 视频演示
- Web UI 输出的立项书视觉感不够震撼
- 用户看不到「从一条帖子 → 完整商业计划书」的魔法全流程

### ❌ 部署门槛过高
`.env` 配置 + API Key 申请 + 本地启动，每多一步流失一半用户。

```bash
# 高 Star 项目的标配（目标）
docker run -e LLM_API_KEY=xxx -p 8000:8000 ideahunter/ideahunter
```

### ❌ 数据源不够「性感」
当前 5 个数据源，缺少最具传播力的痛点宝库：

| 缺失数据源 | 为什么重要 |
|---|---|
| **ProductHunt** | 每天发布新产品，评论区全是「这做不到 XXX」的痛点 |
| **IndieHackers** | 独立开发者社区，最浓缩的创业痛点 |
| **Twitter/X `#buildinpublic`** | 创业者公开吐槽的一手痛点 |
| **少数派 / sspai** | 中文工具评测，差评 = 痛点宝库 |
| **App Store 低分评论** | 1 星评价是最纯粹的用户痛点 |

---

## 二、功能提升优先级

### 🔥 高优先级：直接带来 Star 的改动

#### 1. 实时流式输出（Streaming UI）
用户触发扫描后，实时展示 AI 分析过程：
```
正在采集数据... → 发现痛点：用户每天手动整理...
→ Critic 打分中：78分 ✅ → 正在生成立项书...
```
- 这是产出 **Demo GIF 的核心素材**，也是在 HN/Twitter 引爆分享的关键

#### 2. 立项书「分享卡片」生成
- 一键生成**可分享的商业机会图片卡片**（类似 Readwise Quote Card）
- 有人转发卡片 = 项目被动曝光，形成病毒传播

#### 3. One-click Deploy 按钮
在 README 最显眼位置放：
- [![Deploy on Railway](https://railway.app/button.svg)](...)
- [![Deploy on Zeabur](https://zeabur.com/button.svg)](...)
- 把部署时间从 30 分钟压缩到 3 分钟

#### 4. Telegram Bot 推送模式
```
每天早上 9 点自动推送：
🎯 今日发现 3 个商业机会
1. [78分] 上下文记忆助手...
点击查看完整立项书 →
```
- Telegram Bot 是高 Star AI 工具标配，极大提升日活粘性

---

### 💡 中优先级：提升「深度」的功能

#### 5. 痛点趋势追踪 Dashboard
- 追踪某个痛点词频的时间变化（7 天内从 5 次 → 50 次 = 风口信号）
- 类似 Google Trends，但专为创业痛点设计

#### 6. 行业垂直模式
```bash
# 用户可指定垂直行业，系统自动调整搜索词和评审维度
VERTICAL_FOCUS="跨境电商"
```

#### 7. 「机会图谱」可视化
- 把发现的痛点按行业 / 话题聚类，生成交互式关系图
- 这类可视化极易在 HN / Twitter 上引发传播

#### 8. 竞品自动调研
- Critic Agent 通过后，自动搜索「该赛道已有产品」
- 输出：「该赛道已有 AppFlowy / Notion，但均未解决 XXX」

---

### 📦 低优先级：生态完善

#### 9. 英文版完整支持
- README 中英双语（或国际化），打开 HN 等英文社区流量
- 默认关键词池提供英文版

#### 10. 手动注入 + 批量导入
- 支持用户粘贴任意文本 / 上传 CSV 直接进入分析流水线
- 方便企业用户批量处理内部调研数据

#### 11. 输出导出
- 导出为 Notion 页面 / PDF / Markdown 文件
- 便于用户在自己的工具链中继续使用

#### 12. 用户投票机制
- 在 Web UI 中对已发现的商业机会进行「有价值 / 无价值」评分
- 积累数据后可用于微调 Critic Agent 的评分标准

---

## 三、新数据源接入计划

| 数据源 | 接入难度 | 痛点密度 | 优先级 |
|---|---|---|---|
| **ProductHunt** | 中（有官方 API） | ⭐⭐⭐⭐⭐ | P0 |
| **IndieHackers** | 中（RSS + 爬虫） | ⭐⭐⭐⭐⭐ | P0 |
| **App Store 差评** | 中（iTunes RSS） | ⭐⭐⭐⭐ | P1 |
| **少数派 / sspai** | 低（公开 RSS） | ⭐⭐⭐⭐ | P1 |
| **Twitter/X** | 高（API 付费） | ⭐⭐⭐⭐⭐ | P2 |
| **36氪 / 虎嗅** | 低（RSS） | ⭐⭐⭐ | P2 |
| **Weibo 热搜** | 中 | ⭐⭐⭐ | P3 |

---

## 四、病毒传播路径

| 渠道 | 内容策略 | 预期效果 |
|---|---|---|
| **V2EX** | 发帖「用 AI 每天自动发现商业机会，已开源」+ Demo GIF | 国内开发者圈首发 |
| **少数派** | 工具评测长文 + 精美截图 | 中文用户深度种草 |
| **HN Show HN** | 英文 README + 公开 Demo 环境 | 国际开发者曝光 |
| **Twitter thread** | 「从一条抱怨帖到完整商业计划」全流程截图 | 转发裂变 |
| **GitHub Trending** | 集中 Star 冲榜（朋友帮忙 + 社区发帖同步） | 进榜后自然流量 |

---

## 五、执行时间线

### Week 1 — 打造 Wow 时刻
- [ ] 实现流式输出 UI（Server-Sent Events 或 WebSocket）
- [ ] 立项书视觉升级（更专业的排版，代码高亮，封面）
- [ ] 录制 Demo GIF（工具：Kap / LICEcap）

### Week 2 — 降低部署门槛
- [ ] Railway / Zeabur 一键部署配置
- [ ] 英文 README 重写（含架构图、截图）
- [ ] `.env.example` 精简到 3 个必填项

### Week 3 — 扩大数据源
- [ ] ProductHunt 插件（`plugins/producthunt_scraper.py`）
- [ ] App Store 差评插件（`plugins/appstore_scraper.py`）
- [ ] Telegram Bot 推送（`core/notifier.py` 扩展）

### Week 4 — 社区运营
- [ ] 发布 V2EX / 少数派 / HN Show HN
- [ ] 完善 `CONTRIBUTING.md`，欢迎 PR
- [ ] 建立 Discussions / Discord 社区

---

## 六、成功标准

| 阶段 | Star 目标 | 关键里程碑 |
|---|---|---|
| 发布后 1 周 | 500+ | 上 GitHub Trending Daily |
| 发布后 1 月 | 2k+ | 上 HN 首页 |
| 发布后 3 月 | 5k+ | 形成社区贡献 |
| 长期 | 10k+ | 成为该方向的标准工具 |

---

> 💡 **核心原则**：Pipeline 逻辑已扎实，现在最缺的是「展示层」和「传播层」——
> 让更多人在 10 秒内看懂它的价值，并且 3 分钟内能跑起来。
