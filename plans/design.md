# 🏗️ IdeaHunter 核心架构设计文档 (Architecture Design)

## 一、 系统总览 (System Overview)

IdeaHunter 是一个基于大语言模型 (LLM) 和多智能体协同 (Multi-Agent) 的自动化商业情报挖掘系统。系统整体采用**“流水线 (Pipeline) + 状态机 (State Graph)”**的混合架构。

它将非结构化的互联网噪音，通过**采集、清洗、多角色辩论评估、报告生成**四个阶段，最终转化为高价值的结构化《微型产品立项书》。

---

## 二、 逻辑架构分层 (Logical Architecture)

整个系统由下至上分为四层，每一层都通过明确的接口 (Interface) 进行通信，确保模块解耦。

### 1. 数据采集层 (Sensor Layer / Plugins)
*   **职责：** 负责从不同平台抓取原始文本数据。
*   **设计模式：** 采用**插件化设计 (Plugin Architecture)**。提供一个基类 `BaseScraper`，开发者只需继承该基类并实现 `fetch_data()` 方法，即可快速接入新平台。
*   **组件：** `V2EX_Plugin`, `Reddit_Plugin`, `Xiaohongshu_Plugin` 等。
*   **输出：** 统一格式的 JSON 对象流（包含：来源、时间、原帖内容、高赞评论、URL）。

### 2. 状态与记忆层 (Memory & State Layer)
*   **职责：** 管理 Agent 运行时的上下文，并防止系统对同一个痛点进行重复分析。
*   **组件：**
    *   **短期记忆 (Short-term Memory)：** 存储单次跑批 (Run) 过程中的 Agent 辩论对话上下文。
    *   **去重数据库 (Deduplication DB)：** 轻量级本地 SQLite。记录已分析过的帖子 ID 或痛点 Hash 值。一旦抓取到新数据，先与 DB 对比，滤除已处理信息。

### 3. 多智能体调度层 (Brain / Agent Orchestration Layer)
*   **职责：** 系统的“大脑中枢”，控制数据在不同 Agent 之间的流转与状态流转。
*   **核心引擎：** 推荐使用基于图逻辑的轻量级状态机（如 `LangGraph` 或纯手写状态路由），将分析过程定义为一张有向无环图 (DAG)。
*   **智能体节点 (Agent Nodes)：**
    *   `Extractor_Agent`: 从长篇水文中精准提取“痛点/抱怨”。
    *   `PM_Agent`: 将痛点翻译为标准的用户故事 (User Story)。
    *   `Critic_Agent`: （核心把关人）执行商业漏斗评估，打分 (0-100)。
    *   `Planner_Agent`: 仅在 `Critic_Agent` 打分 > 80 时触发，生成最终 PRD。

### 4. 表现与动作层 (Action Layer)
*   **职责：** 将最终结果交付给用户。
*   **组件：**
    *   `Markdown_Renderer`: 将 JSON 组装成排版精美的 Markdown 文档。
    *   `Notifier`: （可插拔）将生成的文档推送到终端控制台、微信企业号、飞书 Webhook 或邮箱。

---

## 三、 核心工作流引擎 (Workflow Engine)

为了直观展示数据是如何在 Agent 之间传递的，我们定义了如下的**标准工作流图 (Workflow DAG)**：

1.  **[触发 Trigger]** -> 定时任务 (Cron) 唤醒系统。
2.  **[加载 Load]** -> `Plugin Manager` 批量运行所有启用的抓取插件，获取 `Raw Data List`。
3.  **[过滤 Filter]** -> 经过 SQLite 校验，丢弃已处理数据。
4.  **[分析循环 Analysis Loop]** (针对每一条新数据)：
    *   👉 **Step A (提取):** 交给 `Extractor Agent`。如果未发现有效痛点，状态标记为 `Dropped`，结束当前循环。
    *   👉 **Step B (翻译):** 交给 `PM Agent`，标准化痛点描述。
    *   👉 **Step C (评估):** 交给 `Critic Agent`。调用“黄金三定律” Prompt。
        *   *If Score < 80:* 状态标记为 `Rejected`，记录被拒原因，结束当前循环。
        *   *If Score >= 80:* 状态标记为 `Approved`，流转到下一步。
    *   👉 **Step D (规划):** 交给 `Planner Agent`，生成《立项书》。
5.  **[分发 Publish]** -> 调用 `Notifier` 发送通知。

---

## 四、 技术栈选型建议 (Tech Stack Selection)

针对开源和独立开发者的特点，技术栈必须**便宜、好装、易改**：

*   **核心语言：** Python 3.10+ (AI 生态最完善)。
*   **大模型接口层：** `LiteLLM` (极其推荐。它能将 OpenAI, DeepSeek, Kimi, Claude 等所有主流 API 统一封装成一个格式，用户在 `.env` 里配什么 Key 就用什么，做到模型解耦)。
*   **多智能体框架：**
    *   *方案 A（极客纯手写）：* 纯 Python 函数调用 + `Pydantic` 强制结构化输出。（最轻量，推荐初期使用）。
    *   *方案 B（借力框架）：* `LangGraph`。（支持复杂的状态回溯和人类确认节点，适合未来演进）。
*   **本地存储：** 本地文件系统 (存 Markdown) + SQLite (存运行日志和去重数据)。绝对不要引入 MySQL 或 Redis，徒增用户的部署成本。
*   **数据抓取：** `BeautifulSoup4` (基础网页) / `Playwright` (需要绕过简单反爬的动态网页)。

---

## 五、 代码目录结构骨架 (Directory Structure)

有了以上架构，我们在 GitHub 上的代码目录就可以清晰地规划出来了：

```text
IdeaHunter/
├── core/                   # 核心大脑层
│   ├── orchestrator.py     # 状态机与工作流调度引擎
│   ├── agents/             # 存放各个 Agent 的定义与系统 Prompt
│   │   ├── pm_agent.py
│   │   ├── critic_agent.py
│   │   └── planner_agent.py
│   └── memory/             # 去重与状态记录机制
│       └── sqlite_manager.py
├── plugins/                # 数据采集层（插件目录）
│   ├── base_scraper.py     # 抓取器基类（接口定义）
│   ├── v2ex_scraper.py     # V2EX 具体实现
│   └── xhs_scraper.py      # 小红书具体实现
├── output/                 # 生成的立项书存放目录
├── config/                 # 配置管理
│   └── settings.py         # 读取 .env 配置
├── main.py                 # 程序的唯一入口文件
├── requirements.txt        # 依赖包列表
├── .env.example            # 环境变量示例
└── README.md               # 项目门面说明文档
```

---