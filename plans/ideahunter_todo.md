# ✅ IdeaHunter 待做工作清单

> 基于现有代码 (`api/`, `core/`, `plugins/`) 与设计文档 (`plans/api.md`, `plans/rfc.md`, `plans/design.md`) 的 Gap 分析，按优先级排列。

---

## 🔴 P0 — 核心功能缺口（当前代码与 api.md 文档的直接差距）

### API 层
- [ ] **`GET /ideas/{idea_id}` 响应缺少 `source` 字段**：api.md 示例中有 `"source": "xiaohongshu"`，但当前 `get_idea` 接口的响应体未返回该字段。
- [ ] **`POST /webhooks/ingest` 缺少 `keywords` 参数**：`POST /tasks/scan` 支持关键词过滤，但 webhook 注入路径 `run_ingested_contents` 不支持，功能不对称。
- [ ] **`429 Too Many Requests` 错误码未实现**：api.md §四 错误码表中有 `42901`，但代码中完全缺少速率限制 (rate limiting) 中间件（如 `slowapi`）。

### 数据源插件
- [ ] **`xhs_scraper.py`（小红书）未实现**：`design.md` §一 和 `rfc.md` §四 均将小红书列为核心数据源；`plugins/__init__.py` 中占位符存在，但无实际采集逻辑。
- [ ] **`zhihu_scraper.py`（知乎）未实现**：api.md 请求示例中出现 `"source": "zhihu"` 作为合法值，但插件不存在，调用时会返回 `40001 Bad Request`。

---

## 🟠 P1 — 重要功能完善（rfc.md Roadmap 明确规划的）

### 通知与分发（Notifier）
- [ ] **Notifier 模块完全缺失**：`design.md` §二 表现层描述了 `Notifier`（推送到控制台、企业微信、飞书 Webhook、邮箱），当前 `core/` 下无此模块，立项书只写入本地磁盘，无任何推送能力。
- [ ] **飞书 / 企业微信 Webhook 推送**：实现优先级最高的通知渠道，让用户每日自动接收挖掘报告。

### Web UI（v1.0 规划）
- [ ] **可视化大盘 Web UI**：rfc.md §五 v1.0 规划了"可视化大盘看板"，目前完全没有前端代码，用户只能通过 CLI 或原始 API 交互。需实现：
  - [ ] 点子列表页（带分数筛选、来源筛选、分页）
  - [ ] 立项书详情页（Markdown 渲染）
  - [ ] 任务状态实时查看页（轮询 `GET /tasks/{task_id}`）

### Scheduler 增强
- [ ] **调度任务缺少 Web API 管理接口**：当前 `scheduler.py` 在启动时静态配置，运行期间无法动态增减调度任务，应增加 `GET /scheduler/jobs` 接口。
- [ ] **`GET /ideas` 缺少行业 Tag 过滤参数**：rfc.md §五 规划了"用户输入行业关键词进行定向过滤"，目前 API 仅支持 `min_score` + `source`，无标签/行业维度。

---

## 🟡 P2 — 工程质量与稳定性

### 并发安全
- [ ] **`SqliteManager` 使用 `check_same_thread=False` 但无锁保护**：FastAPI `BackgroundTasks` 与请求线程可能并发写入 SQLite，存在数据竞争风险，需引入线程锁或改用 `aiosqlite`。
- [ ] **LLM 客户端全局单例线程不安全**：`core/llm.py` 中 `_CACHED_CLIENT` 是全局变量，多线程并发初始化时存在竞态，应加 `threading.Lock` 保护。

### 错误处理
- [ ] **后台任务 `except` 块中连接泄漏**：`server.py` L137 在异常处理中新建 `ldb = SqliteManager(...)` 但原 `ldb` 连接未显式关闭，存在连接泄漏，应在 `finally` 中统一关闭。
- [ ] **404 响应格式需对齐 api.md 错误码表**：`GET /ideas/{idea_id}` 与 `GET /tasks/{task_id}` 的错误响应，需确认 `detail` 中的 `code` 字段与 api.md §四 完全对应。

### 配置与部署
- [ ] **`Settings.get_settings()` 使用 `lru_cache`，进程内无法热重载**：修改 `.env` 后须重启，应在文档中说明此限制或提供 `reload_settings()` 工具函数。
- [ ] **`Dockerfile` 缺少 `HEALTHCHECK` 指令**：应利用已有的 `GET /health` 端点配置 `HEALTHCHECK CMD curl -f http://localhost:8000/health`。
- [ ] **`.env.example` 与 `settings.py` 字段对应不完整**：需检查 `schedule_cron`、`schedule_sources`、`output_dir` 等字段是否都有对应示例与注释说明。

---

## 🟢 P3 — 测试与文档

### 测试覆盖
- [ ] **缺少 `test_planner_agent.py`**：`planner_agent.py` 是输出质量关键路径，无任何单元测试。
- [ ] **缺少 `test_pm_agent.py`**：`pm_agent.py` 无对应测试。
- [ ] **`test_api.py` 缺少 Webhook 端点测试**：`POST /webhooks/ingest` 和 `GET /processed-items` 均无测试覆盖。
- [ ] **`test_orchestrator.py` 缺少 `run_ingested_contents` 分支测试**：仅覆盖 `run_pipeline`，webhook 注入流程无测试。
- [ ] **缺少端到端集成测试**：无 CLI → Scraper → Agent 链路 → SQLite 的全链路测试，只有孤立单元测试。

### 文档
- [ ] **`plans/api.md` 未记录 `GET /processed-items` 接口**：该接口已在 `server.py` L260-292 中实现，但 api.md 完全未提及，需补充文档。
- [ ] **`README.md` 缺少 API Server 启动方式**：目前只描述 CLI 用法，未说明 `uvicorn api.server:app --reload` 启动步骤。
- [ ] **`plans/api.md` HTTP/2 升级建议未落地**：api.md §一 提到"推荐升级至 HTTP/2"，但 `Dockerfile` 和部署文档未提供任何 HTTP/2 配置指引。

---

## 📌 工作汇总

| 优先级 | 数量 | 主要方向 |
|:---:|:---:|:---|
| 🔴 P0 | 5 项 | API 行为与文档对齐、核心插件缺失 |
| 🟠 P1 | 5 项 | Notifier 推送、Web UI、Scheduler 管理 API、Tag 过滤 |
| 🟡 P2 | 7 项 | 并发安全、错误处理、配置与部署 |
| 🟢 P3 | 8 项 | 测试覆盖、API 文档补全 |
| **合计** | **25 项** | |
