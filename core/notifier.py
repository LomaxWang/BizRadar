"""IdeaHunter Notifier — 多渠道推送通知模块.

支持以下推送渠道（可同时启用多个）：
  - 控制台 (console) — 始终可用，打印到 stdout
  - 飞书 Webhook (feishu)  — 配置 NOTIFIER_FEISHU_WEBHOOK
  - 企业微信 Webhook (wecom) — 配置 NOTIFIER_WECOM_WEBHOOK
  - 自定义 HTTP Webhook    — 配置 NOTIFIER_CUSTOM_WEBHOOK

使用方式：
    from core.notifier import Notifier
    n = Notifier()
    n.send_daily_report(stats)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class IdeaSummary:
    idea_id: str
    title: str
    score: int
    source: str
    path: str = ""


@dataclass
class ReportStats:
    source: str
    fetched: int
    approved: int
    rejected: int
    errors: int
    ideas: list[IdeaSummary] = field(default_factory=list)


def _post(url: str, payload: dict[str, Any], label: str) -> None:
    """发送 HTTP POST，失败时只记录日志，不抛出异常。"""
    try:
        import httpx  # 延迟导入避免循环依赖
        resp = httpx.post(url, json=payload, timeout=10.0)
        if resp.status_code >= 400:
            logger.warning("Notifier[%s]: HTTP %s — %s", label, resp.status_code, resp.text[:200])
        else:
            logger.info("Notifier[%s]: 推送成功", label)
    except Exception as exc:
        logger.warning("Notifier[%s]: 推送失败 — %s", label, exc)


class ConsoleNotifier:
    """打印到 stdout，始终可用。"""

    def send(self, title: str, body: str) -> None:
        print(f"\n{'=' * 60}", flush=True)
        print(f"📢 {title}", flush=True)
        print(body, flush=True)
        print("=" * 60, flush=True)


class FeishuNotifier:
    """飞书群机器人 Webhook 推送（Markdown 卡片）。"""

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    def send(self, title: str, body: str) -> None:
        payload = {
            "msg_type": "interactive",
            "card": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"**{title}**\n\n{body}",
                    }
                ],
                "header": {
                    "title": {"content": "IdeaHunter 商业雷达", "tag": "plain_text"},
                    "template": "green",
                },
            },
        }
        _post(self._url, payload, "feishu")


class WeComNotifier:
    """企业微信群机器人 Webhook 推送（Markdown）。"""

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    def send(self, title: str, body: str) -> None:
        content = f"# {title}\n\n{body}"
        payload = {"msgtype": "markdown", "markdown": {"content": content}}
        _post(self._url, payload, "wecom")


class CustomWebhookNotifier:
    """自定义 HTTP Webhook，发送 JSON 载荷。"""

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    def send(self, title: str, body: str) -> None:
        payload = {"title": title, "body": body, "source": "ideahunter"}
        _post(self._url, payload, "custom_webhook")


def _build_report_text(stats: ReportStats) -> tuple[str, str]:
    """根据 ReportStats 构建（title, body）文本对。"""
    title = f"IdeaHunter 日报 · {stats.source} · 发现 {stats.approved} 个商业机会"
    lines = [
        f"> 来源：**{stats.source}**",
        f"> 抓取：{stats.fetched} 条  |  通过立项：**{stats.approved}** 个  |"
        f"  被拒：{stats.rejected}  |  错误：{stats.errors}",
        "",
    ]
    if stats.ideas:
        lines.append("### 📌 本轮立项清单")
        for idea in stats.ideas:
            lines.append(f"- **[{idea.score}分]** {idea.title}")
    else:
        lines.append("*本轮未发现高价值商业机会*")
    return title, "\n".join(lines)


class Notifier:
    """聚合通知器，从环境变量自动配置并分发通知。

    环境变量：
        NOTIFIER_FEISHU_WEBHOOK   — 飞书 Webhook URL
        NOTIFIER_WECOM_WEBHOOK    — 企业微信 Webhook URL
        NOTIFIER_CUSTOM_WEBHOOK   — 自定义 HTTP Webhook URL
        NOTIFIER_CONSOLE_ENABLED  — 是否启用控制台输出（默认 true）
    """

    def __init__(self) -> None:
        self._backends: list[Any] = []

        # 控制台（默认开启）
        console_enabled = os.getenv("NOTIFIER_CONSOLE_ENABLED", "true").lower() != "false"
        if console_enabled:
            self._backends.append(ConsoleNotifier())

        # 飞书
        feishu_url = os.getenv("NOTIFIER_FEISHU_WEBHOOK", "").strip()
        if feishu_url:
            self._backends.append(FeishuNotifier(feishu_url))
            logger.info("Notifier: 飞书推送已启用")

        # 企业微信
        wecom_url = os.getenv("NOTIFIER_WECOM_WEBHOOK", "").strip()
        if wecom_url:
            self._backends.append(WeComNotifier(wecom_url))
            logger.info("Notifier: 企业微信推送已启用")

        # 自定义 Webhook
        custom_url = os.getenv("NOTIFIER_CUSTOM_WEBHOOK", "").strip()
        if custom_url:
            self._backends.append(CustomWebhookNotifier(custom_url))
            logger.info("Notifier: 自定义 Webhook 推送已启用")

    def send_raw(self, title: str, body: str) -> None:
        """向所有配置好的渠道发送通知。"""
        for backend in self._backends:
            try:
                backend.send(title, body)
            except Exception as exc:
                logger.warning("Notifier: backend %s 推送失败: %s", type(backend).__name__, exc)

    def send_daily_report(self, stats: ReportStats) -> None:
        """发送每日商业情报日报。"""
        title, body = _build_report_text(stats)
        self.send_raw(title, body)
