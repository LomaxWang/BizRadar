# 我开源了一个 AI 商业雷达，专门把网上的「吐槽」变成创业项目

---

> **适合发布的社区：** V2EX（程序员版 / 分享发现板）、即刻、掘金、少数派、Reddit (r/entrepreneur, r/SideProject, r/webdev)

---

## 🇨🇳 中文版（V2EX / 即刻 / 掘金 / 少数派）

---

**标题：** 我做了一个开源的 AI 商业雷达，专门把 V2EX/HN 上的「吐槽帖」榨干，变成可以直接开干的产品方案！

---

做独立开发最绝望的时刻是什么？
不是 Bug 解不出来，而是吭哧吭哧写了几个月代码，产品上线后，除了自己和亲友团，根本没人用。

我们总是容易“拍脑袋”想需求，却忽略了真实的需求往往藏在用户的**无能狂怒**和**心酸吐槽**里。

每天，V2EX、Hacker News、Reddit、甚至微博上，都有大量真实用户在抱怨：
“为什么没有一个工具能 xxx？”
“每次遇到这个问题我都想砸键盘！”
“这个软件用了 10 年了还是这么难用！”

这些抱怨，其实就是未被满足的**金矿**。绝大多数人刷帖子只是看个乐子，划过去就忘了。
为了不再盲目开发“伪需求”，我干脆写了一个工具，自动去挖掘这些金矿。

---

### 🛠️ 它是如何工作的？

**[BizRadar](https://github.com/LomaxWang/BizRadar)**，你可以把它理解为你个人的“赛博创业智囊团”。只要部署在本地或服务器上，它就会自动巡检各大社区的海量帖子与评论。

最核心的，是它内置了 **5 大 AI Agent 协作流水线**，帮你完成从“发现问题”到“产品立项”的全部工作：

1. 🕵️ **痛点提取 Agent**：在海量长文中“大海捞针”，剥离无效情绪，提取底层真实痛点。
2. 👨‍💼 **产品经理 Agent**：梳理用户画像，将抽象痛点转化为具象的产品形态和功能点。
3. 🧑‍⚖️ **商业评审 Agent**：最无情的一环。它会像严苛的投资人一样，从“高频度”、“大厂免疫力（防巨头碾压）”和“商业闭环变现”三大维度打分，低于分数线的点子直接淘汰！
4. 👨‍💻 **技术合伙人 Agent**：评估技术可行性，直接给你推荐最快落地的技术栈，并预估 MVP 开发周期。
5. 📝 **立项撰写 Agent**：整合前面所有信息，自动调用搜索引擎调研竞品，生成最终的商业立项书。

---

### 🎯 实际产出效果（有图有真相）

光说不练假把式。比如最近网上有一批帖子在骂「电商平台的 AI 客服纯属智障，根本不解决问题只会打太极」。

BizRadar 抓取到这些信号后，立刻嗅到了商机，打出了 **82/100** 的高分，并自动生成了这样的商业机会卡片：

![AI客服破壁人商机卡片](../assets/example_1.png)

除了这张可以直接分享的卡片，它还会为你生成一份**极其详尽的 Markdown 格式商业立项书（PRD）**。这份报告到底有多细？它包含了：

- **痛点溯源**（引用真实的抱怨帖子作为依据）
- **竞品格局与差异化分析**（比如黑猫投诉只能曝光，代投诉又太贵）
- **三档递进式定价策略**（免费引流/专业版19元/团队版59元，甚至估算了 LTV）
- **P0/P1/P2 MVP 功能清单**（精确到每个功能的开发天数）
- **4周冷启动获客计划**（连你去小红书发帖的“姐妹们！遇到质量问题找客服被AI气死怎么办”的种草话术都帮你写好了！）

有了这个，你就可以直接打开 IDE 开始写代码，而不用再怀疑自己做出来的东西有没有人要了。

---

### 🤝 为什么要开源？

我自己是独立开发者，这个工具帮我省下了极大的心智负担。

我觉得这类工具的本质是「提示词 + 爬虫 + 数据流水线」，与其藏着掖着，不如开源出来。社区的力量是强大的，大家可以一起改进 Agent 的 Prompt，接入更多的数据源（比如 YouTube 评论、知乎想法等），甚至优化打分逻辑。

只要懂点 Python，你完全可以基于它打造属于你的独家雷达。

---

### 🚀 怎么跑起来？

极致简单，Docker 一行命令：

```bash
docker compose up -d
```

然后打开 `http://localhost:8000`，填一下你的 LLM API Key（支持 DeepSeek / GPT / Claude 等任何兼容接口），点击「开始扫描」，让子弹飞一会。

---

**⭐ GitHub 传送门：** [https://github.com/LomaxWang/BizRadar](https://github.com/LomaxWang/BizRadar)

如果觉得这个点子有点意思，或者对你的独立开发之路有启发，**求一个 Star 支持一下！** 
也极其欢迎来提 Issue 聊聊你希望 BizRadar 还能监控什么平台！

---
---

## 🇺🇸 英文版（Reddit r/SideProject / r/entrepreneur / Hacker News）

---

**Title:** I built an open-source "Cyber Co-founder" that turns Reddit/HN complaints into fully fleshed-out startup ideas!

---

The hardest part of being an indie hacker isn't the coding — it's the crushing feeling of spending 3 months building a product that literally nobody wants.

We often rely on "shower thoughts" for ideas, completely ignoring the fact that real demand is hidden in **user frustration and complaints**. Every day, across Reddit, Hacker News, and Twitter, people are ranting:
*"Why doesn't a simple tool for X exist?"*
*"I want to throw my keyboard out the window every time I do Y!"*

Most people scroll past these rants. I decided to mine them.

---

### 🛠️ What is it?

Meet **[BizRadar](https://github.com/LomaxWang/BizRadar)**, a self-hosted, open-source tool powered by a Multi-Agent architecture. It's essentially an automated startup incubator sitting on your server.

It continuously crawls community platforms and runs the raw, emotional data through a pipeline of **5 specialized AI Agents**:

1. **The Extractor:** Filters out noise and pinpoints the actual underlying pain point.
2. **The PM:** Translates abstract pain into a concrete product concept and user persona.
3. **The Critic (The ruthless one):** Scores the idea based on *Frequency*, *Big-Tech Immunity* (can Apple/Google crush this in a day?), and *Monetization logic*. Ideas below a certain score are immediately trashed.
4. **The Tech Lead:** Recommends the optimal tech stack and estimates the MVP development timeline.
5. **The Planner:** Uses web-search to analyze competitors and outputs a comprehensive Product Requirement Document (PRD).

---

### 🎯 Real Output Example

Recently, it picked up a lot of chatter about how useless and frustrating AI Customer Service bots are on e-commerce platforms. BizRadar scored this opportunity an **82/100** and generated this shareable opportunity card:

![BizRadar Example](../assets/example_1.png)

*(Note: The card above was generated natively by BizRadar)*

But it doesn't stop at an image. It outputs a full Markdown PRD that includes:
- **Pain point origins** (quoting the actual Reddit/forum complaints)
- **Competitive analysis & differentiation**
- **Pricing strategy** (e.g., Free tier -> $5/mo -> $15/mo Team plan)
- **MVP feature list** with time estimates for P0/P1/P2 features
- **A 4-week cold-start acquisition plan** with exact marketing copy you can post on relevant subreddits.

It gives you the complete blueprint. All you have to do is open your IDE.

---

### 🤝 Why open source?

I'm an indie dev, and this tool saves me countless hours of validation anxiety. 

The core of this project is prompt engineering, crawling, and data pipelining. I believe open-sourcing it allows the community to build better prompts, add new data sources (imagine parsing YouTube comments or Discord chats!), and refine the scoring criteria together.

---

### 🚀 How to run it

It's dead simple. Just use Docker:

```bash
docker compose up -d
```

Open `http://localhost:8000`, paste in your LLM API Key (supports GPT/Claude/DeepSeek, etc.), hit "Scan", and let it cook.

---

**⭐ GitHub Link:** [https://github.com/LomaxWang/BizRadar](https://github.com/LomaxWang/BizRadar)

If you find this useful or even just structurally interesting, **I would immensely appreciate a Star!** 
Issues and PRs are incredibly welcome, especially if you want to integrate a new platform to scrape!

---
---

## 📱 极简版（即刻 / 微信朋友圈 / 推特，140字以内）

---

**中文（即刻/朋友圈）：**

> 独立开发还在拍脑袋想需求？
> 我开源了一个“赛博合伙人” BizRadar！它内置 5 大 AI Agent，自动去 V2EX/Reddit 挖用户的“吐槽帖”，无情打分淘汰伪需求，最后给你输出一份包含【竞品分析+MVP工期+定价策略+发帖获客话术】的完整立项书！
> 
> GitHub: https://github.com/LomaxWang/BizRadar （求个⭐）

---

**英文（Twitter/X）：**

> Stop building products nobody wants! 🛑
> I open-sourced BizRadar: a Multi-Agent system that scrapes Reddit/HN complaints and turns them into validated startup ideas. 
> It outputs a full brief: competitive analysis, pricing, MVP tech stack, and cold-start marketing copy!
> 
> Self-hosted via Docker.
> GitHub: https://github.com/LomaxWang/BizRadar (⭐ appreciated!)
