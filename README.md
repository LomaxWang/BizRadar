<div align="center">
  <h1>🎯 BizRadar</h1>
  <p><strong>你的 24 小时 AI 商业探测雷达：从海量互联网吐槽中，挖掘下一个高价值 Micro-SaaS 点子</strong></p>

  <p>
    <a href="https://img.shields.io/badge/python-3.10%2B-blue"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
    <a href="https://img.shields.io/badge/license-MIT-green"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
    <a href="https://img.shields.io/badge/PRs-welcome-brightgreen.svg"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
  </p>
</div>

---

> 还在苦恼做不出有真实需求的产品？还在盲目跟随伪需求？
> **BizRadar (前身 IdeaHunter)** 是一个基于多智能体（Multi-Agent）架构的开源社交媒体痛点挖掘与商业机会评估系统。它能自动监控全网社区，把网友的“无能狂怒”和“心酸吐槽”转化为具有极高商业价值的产品立项书（PRD）！

## ✨ 核心亮点

*   🚀 **全自动商机挖掘**：自动巡检 V2EX、HackerNews、Reddit、微博、Twitter 以及 AppStore 的海量帖子与评论。
*   🤖 **四大 Agent 协作评审**：
    *   **提取员 (Extractor)**：大海捞针，精准识别真正的“用户痛点”。
    *   **产品经理 (PM)**：梳理需求，构建用户画像与使用场景。
    *   **商业评审 (Critic)**：残酷打分，从高频度、大厂免疫力、商业闭环三大维度砍掉“伪需求”。
    *   **技术合伙人 (TechLead)**：评估技术可行性、把控核心技术风险、估算 MVP 工期。
*   📊 **语义级跨源痛点聚合**：不同社区关于“客服效率低”的吐槽？聚合器会自动在语义层面进行 Jaccard 相似度匹配，将跨平台同类痛点合并，显著放大强需求信号！
*   📄 **开箱即用的专业立项书 (PRD)**：一键输出完整的 Markdown 格式商业计划，包含：**产品一句话定义**、**痛点溯源（保留原话）**、**竞品优劣势对比**、**三档定价方案**、**MVP 开发功能表** 以及 **4周冷启动获客计划（含话术）**。
*   🖥️ **可视化雷达大盘**：自带现代化且美观的 Web UI，进度状态、历史点子、立项书详情尽在掌握。

## ⚙️ 工作原理

```mermaid
graph LR
    subgraph 来源与监听
        V[V2EX / HN / Reddit等]
        W[Webhook 注入]
    end

    subgraph 核心编排 (Orchestrator)
        O[多源聚合 & 调度]
    end

    subgraph 智能体评审流 (Agents)
        E[痛点提取 Agent]
        PM[产品设计 Agent]
        C[商业评估 Agent]
        TL[技术评估 Agent]
        P[立项撰写 Agent]
    end

    subgraph 输出
        DB[(SQLite)]
        MD[商业立项书 PRD]
        UI[Web 可视化大盘]
    end

    V --> O
    W --> O
    O --> E --> PM --> C --> TL --> P
    P --> DB
    P --> MD
    DB --> UI
```

## 🚀 快速开始

### 1. 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/LomaxWang/ideahunter.git
cd ideahunter

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境 (填写你的大模型 API 密钥，默认支持所有兼容 OpenAI 接口的模型)
cp .env.example .env
# 编辑 .env：设置 LLM_API_KEY, LLM_BASE_URL (如 https://yunwu.ai/v1), LLM_MODEL

# 4. 启动可视化服务端
uvicorn api.server:app --host 0.0.0.0 --port 8000
```
启动后，打开浏览器访问 **`http://localhost:8000`** 即可进入大盘，点击**“触发扫描”** -> **“全源扫描”** 即可开始挖掘。

### 2. Docker 部署 (推荐)

如果你想把雷达挂在云服务器上 24 小时自动运行：

```bash
docker compose up -d
```
> 数据会自动挂载到 `./data`，生成的 PRD 文件会自动挂载到 `./output` 目录下。

## 🔌 高级玩法：API & Webhook

BizRadar 提供了一套完整的 REST API，你可以轻松将它接入现有的工作流。

```bash
# 通过 Webhook 注入你公司客服收到的吐槽，直接分析是否有做新产品的潜力：
curl -X POST http://localhost:8000/api/v1/webhooks/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_name": "custom_feedback", "content_list": ["你们导出的Excel总是乱码，每天浪费半小时整理！"]}'
```

详见 [API 文档](plans/api.md) 与 [架构设计说明](plans/design.md)。

## 📝 配置参数说明

在 `.env` 文件中，你可以深度定制你的雷达策略：

| 变量 | 默认值 | 作用 |
|---|---|---|
| `LLM_API_KEY` | - | (必填) 大语言模型 API Key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | `gpt-4o-mini` | 所选模型，建议使用推理能力较强的模型 |
| `SCORE_APPROVE_MIN` | `65` | 立项通过的分数线（最高100分）。如果想看更多点子，可以调低。 |
| `KEYWORD_POOL` | `["效率工具","求推荐软件"...]` | 驱动插件搜索的关键词池，每次扫描随机抽取，保证每日结果都不一样！ |
| `SCHEDULE_ENABLED` | `false` | 是否开启定时自动扫描 |
| `SCHEDULE_CRON` | `0 9 * * *` | 每天定时启动雷达的 Cron 表达式 |

## 💡 为什么做这个项目？

“做没用的东西”是独立开发者和创业团队最常见的死法。我们在开发中发现，与其在办公室拍脑袋想痛点，不如直接去互联网的汪洋大海中找**正在花时间抱怨的人**。

**BizRadar 不仅仅是一个爬虫，它是你的云端创业合伙人团队**。它无情地刷掉伪需求，把真实世界中那些**高频、大厂懒得做、技术上又完全可以实现**的痛点端到你面前，并附带了怎么收费、怎么获客的执行方案。

你唯一要做的，就是挑一个让你心动的 PRD，打开 IDE 开始写代码！

## 🤝 贡献与交流

发现了一个更好的痛点源？想优化 Agent 提示词？非常欢迎提交 Pull Request！
详细开发指南请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 协议

本项目基于 [MIT License](LICENSE) 开源。
