"""
idea_aggregator.py — 跨源痛点聚合模块

在一轮扫描结束后，对本轮新增的 ideas 进行字符 bigram Jaccard 相似度比较，
将描述同一痛点但来自不同数据源的条目合并：保留评分更高的那个，
并将被合并条目的 raw_complaints_analyzed 数量累加进来，
从而正确放大"多平台同时印证"的热度信号。

不依赖任何外部 embedding API 或机器学习库，完全基于内置 Python 实现。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────────────────────────────────
_NGRAM_SIZE = 2          # 字符 bigram（中文效果好）
_DEFAULT_THRESHOLD = 0.42  # Jaccard 相似度合并阈值；可通过参数覆盖


# ── 数据结构 ──────────────────────────────────────────────────────────────────
@dataclass
class _IdeaMeta:
    idea_id: str
    title: str
    score: int
    text: str = ""
    accumulated: int = field(default=1)   # 已聚合的 raw_complaints 数量


# ── 核心算法 ──────────────────────────────────────────────────────────────────
def _ngram_set(text: str, n: int = _NGRAM_SIZE) -> set[str]:
    """生成字符 n-gram 集合（中英混合友好）。"""
    text = text.strip()
    return {text[i : i + n] for i in range(max(0, len(text) - n + 1))}


def _jaccard(a: str, b: str) -> float:
    """计算两段文本的字符 bigram Jaccard 相似度。"""
    sa, sb = _ngram_set(a), _ngram_set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


# ── 公开接口 ──────────────────────────────────────────────────────────────────
def aggregate_ideas(
    db,
    ideas: list[dict],
    *,
    threshold: float = _DEFAULT_THRESHOLD,
) -> int:
    """对本轮新增 ideas 做相似度聚合，原地合并重复痛点。

    Args:
        db: SqliteManager 实例（需具备 bump_complaints / delete_idea 方法）。
        ideas: orchestrator RunStats.ideas 列表，每项至少含 idea_id / title / score。
        threshold: Jaccard 相似度合并阈值，超过则视为同一痛点。

    Returns:
        实际发生合并的次数。
    """
    if len(ideas) < 2:
        return 0

    metas = [
        _IdeaMeta(
            idea_id=i["idea_id"], 
            title=i["title"], 
            score=i["score"],
            text=(i.get("summary", "") + " " + i.get("user_story", "")).strip() or i["title"]
        )
        for i in ideas
    ]

    merged_count = 0
    to_drop: set[str] = set()

    for i in range(len(metas)):
        if metas[i].idea_id in to_drop:
            continue
        for j in range(i + 1, len(metas)):
            if metas[j].idea_id in to_drop:
                continue

            sim = _jaccard(metas[i].text, metas[j].text)
            if sim < threshold:
                continue

            # 保留分数更高的；相同时保留 i
            keep, drop = (
                (metas[i], metas[j])
                if metas[i].score >= metas[j].score
                else (metas[j], metas[i])
            )

            logger.info(
                "聚合痛点 | 保留 [%s] %.30s (score=%d) ← 合并 [%s] %.30s"
                " | jaccard=%.2f | 热度 +%d",
                keep.idea_id, keep.title, keep.score,
                drop.idea_id, drop.title,
                sim, drop.accumulated,
            )

            db.bump_complaints(keep.idea_id, delta=drop.accumulated)
            db.delete_idea(drop.idea_id)
            to_drop.add(drop.idea_id)
            keep.accumulated += drop.accumulated
            merged_count += 1

    if merged_count:
        logger.info("痛点聚合完成：共合并 %d 对重复条目", merged_count)

    return merged_count
