# 🔌 IdeaHunter API 接口设计文档 (v1.0)

## 一、 接口协议与全局规范 (Global Specs)

*   **Base URL:** `http://localhost:8000/api/v1` (本地部署) 或 `[https://api.yourdomain.com/v1](https://api.yourdomain.com/v1)` (云端部署)
*   **通信协议:** HTTP/1.1 (推荐升级至 HTTP/2)
*   **数据格式:** `application/json`
*   **鉴权方式 (Auth):** Bearer Token。所有受保护的接口均需在 Header 中携带：
    `Authorization: Bearer <YOUR_API_KEY>`
*   **标准返回结构 (Standard Response):**
    ```json
    {
      "code": 200,             // 业务状态码 (200成功, 400参数错误, 500内部错误)
      "msg": "success",        // 状态描述
      "data": {}               // 实际负载数据 (对象或数组)
    }
    ```

---

## 二、 核心业务接口定义 (Endpoints)

### 1. 触发商业挖掘任务 (Trigger Mining Task)
*由于 Agent 抓取和辩论需要几分钟甚至更久，此接口采用异步设计，立即返回任务 ID。*

*   **请求路径:** `POST /tasks/scan`
*   **功能描述:** 手动触发一次针对特定平台或关键词的扫描与分析任务。
*   **请求参数 (Request Body):**
    ```json
    {
      "source": "v2ex",              // 必填项: 数据源插件名称 (v2ex, xhs, zhihu 等)
      "keywords": ["效率工具", "太难用"], // 可选项: 强制过滤的关键词
      "max_items": 50                // 可选项: 本次抓取分析的最大帖子数量
    }
    ```
*   **响应示例 (Response):**
    ```json
    {
      "code": 200,
      "msg": "Task created successfully",
      "data": {
        "task_id": "tsk_987654321",
        "status": "pending"
      }
    }
    ```

### 2. 查询任务状态 (Check Task Status)
*   **请求路径:** `GET /tasks/{task_id}`
*   **功能描述:** 轮询查询特定扫描任务的进度和状态。
*   **响应示例 (Response):**
    ```json
    {
      "code": 200,
      "data": {
        "task_id": "tsk_987654321",
        "status": "processing",      // 状态: pending, processing, completed, failed
        "progress": "Agent[Critic] is evaluating idea 3/10...", // 人类可读的进度提示
        "result_count": 2            // 目前已成功挖掘出的高价值点子数量
      }
    }
    ```

### 3. 获取已挖掘的商业点子列表 (List Ideas)
*   **请求路径:** `GET /ideas`
*   **功能描述:** 获取 Agent 历史挖掘并通过“评审委员会”打分的优质微型产品立项清单。
*   **Query 参数 (Query Parameters):**
    *   `min_score` (int): 最低评分过滤（例如：`80`）
    *   `source` (string): 按来源过滤（例如：`xhs`）
    *   `page` (int), `size` (int): 分页参数
*   **响应示例 (Response):**
    ```json
    {
      "code": 200,
      "data": {
        "total": 12,
        "items": [
          {
            "idea_id": "ida_112233",
            "title": "房产中介专属：防折叠朋友圈文案工具",
            "score": 92,
            "source": "xiaohongshu",
            "created_at": "2026-03-19T10:00:00Z"
          }
        ]
      }
    }
    ```

### 4. 获取《产品立项书》详情 (Get Idea Details)
*   **请求路径:** `GET /ideas/{idea_id}`
*   **功能描述:** 获取某个具体商业灵感的完整 PRD 内容（包含 Markdown 格式）。
*   **响应示例 (Response):**
    ```json
    {
      "code": 200,
      "data": {
        "idea_id": "ida_112233",
        "title": "房产中介专属：防折叠朋友圈文案工具",
        "score": 92,
        "raw_complaints_analyzed": 42,
        "markdown_prd": "# 💡 [SaaS灵感] 房产中介专属...\n\n### 📌 痛点溯源...",
        "tech_stack": ["Uni-app", "FastAPI", "Kimi API"],
        "target_audience": "房产中介/微商"
      }
    }
    ```

---

## 三、 高阶特性：外部数据注入 (Data Ingestion Webhook)

*这是一个极其强大的“杀手级”接口。它允许企业用户跳过内置爬虫，直接把他们私域的客户反馈（如客服聊天记录、App Store 差评）推给 Agent 进行商业诊断。*

*   **请求路径:** `POST /webhooks/ingest`
*   **功能描述:** 接收外部系统推送的非结构化抱怨数据，直接喂给 Agent 评审委员会。
*   **请求参数 (Request Body):**
    ```json
    {
      "source_name": "zendesk_tickets",
      "content_list": [
        "客户A：你们导出的Excel为什么总是乱码，我每天要花半小时重新排版！",
        "客户B：希望能加个一键把账单发到微信群的功能，现在截图太傻了。"
      ]
    }
    ```
*   **响应 (Response):** 立即返回 200 OK 和一个 `task_id`，Agent 在后台开始进行痛点翻译和商业评估。

---

## 四、 错误码对照表 (Error Codes)

| HTTP 状态码 | 业务 Code | 说明 | 解决方案 |
| :--- | :--- | :--- | :--- |
| 401 | 40101 | Unauthorized: API Key 缺失或无效 | 检查 Header 中的 Bearer Token |
| 400 | 40001 | Bad Request: 缺少必填参数 | 检查 Request Body 格式是否正确 |
| 404 | 40401 | Not Found: 任务或点子不存在 | 检查 `task_id` 或 `idea_id` 是否正确 |
| 429 | 42901 | Too Many Requests: 触发频率超限 | 降低抓取或调用的频率，或升级配额 |
| 500 | 50001 | LLM API Error: 底层大模型调用失败 | 检查配置的 DeepSeek/Kimi 余额或网络连接 |

---