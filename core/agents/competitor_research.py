"""
competitor_research.py — 竞品真实调研模块

当 SERPER_API_KEY 已配置时，在 Critic 评分前先做真实竞品搜索，
避免 LLM 凭训练数据幻觉出"已知竞品"。未配置时返回空字符串，
Critic 降级为仅凭训练数据判断（保持向后兼容）。
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"
_TIMEOUT = 10.0
_MAX_PER_QUERY = 3   # 每个查询取前 N 条


def research_competitors(
    api_key: str,
    *,
    summary: str,
    max_results: int = 6,
) -> str:
    """用 Serper 搜索与 summary 相关的竞品，返回给 Critic 参考的文本块。

    Args:
        api_key: Serper API Key（空字符串时静默跳过）。
        summary: Extractor 产出的一句话痛点摘要，作为搜索基础。
        max_results: 最多返回几条竞品条目。

    Returns:
        格式化的竞品信息字符串，若无结果返回空字符串。
    """
    if not api_key or not api_key.strip():
        return ""

    # 分两个维度搜索：直接工具 + 替代方案
    queries = [
        f"{summary} tool OR app OR software",
        f"{summary} alternative site:producthunt.com OR site:alternativeto.net",
    ]

    snippets: list[str] = []
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            for q in queries:
                try:
                    resp = client.post(
                        SERPER_URL,
                        headers={
                            "X-API-KEY": api_key,
                            "Content-Type": "application/json",
                        },
                        json={"q": q, "num": _MAX_PER_QUERY},
                    )
                    resp.raise_for_status()
                    organic = resp.json().get("organic", [])
                    for item in organic[:_MAX_PER_QUERY]:
                        title = item.get("title", "").strip()
                        snippet = item.get("snippet", "").strip()
                        link = item.get("link", "")
                        if title:
                            snippets.append(f"• **{title}**：{snippet}  \n  链接：{link}")
                except Exception as exc:
                    logger.debug("竞品搜索查询失败 %r: %s", q, exc)
    except Exception as exc:
        logger.debug("竞品搜索网络失败: %s", exc)

    if not snippets:
        return ""

    lines = ["【真实竞品搜索结果（via Serper，供参考）】"] + snippets[:max_results]
    return "\n".join(lines)
