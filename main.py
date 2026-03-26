from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 保证从 IdeaHunter 目录运行时能解析顶层包
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import get_settings
from core.logging_config import setup_logging
from core.orchestrator import SCORE_APPROVE_MIN, run_pipeline


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="IdeaHunter 商业雷达 CLI")
    parser.add_argument("--target", default="v2ex", help="数据源插件名，默认 v2ex")
    parser.add_argument(
        "--mode",
        default="daily_report",
        help="运行模式，默认 daily_report",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="最多抓取/分析的帖子数量上限",
    )
    parser.add_argument(
        "--keywords",
        nargs="*",
        default=None,
        help="可选：标题或正文需包含任一关键词",
    )
    args = parser.parse_args()

    get_settings()
    stats = run_pipeline(
        source=args.target,
        mode=args.mode,
        max_items=args.max_items,
        keywords=args.keywords,
        on_progress=lambda m: print(m, flush=True),
    )

    print("\n======== IdeaHunter 日报摘要 ========", flush=True)
    print(f"抓取: {stats.fetched}", flush=True)
    print(f"跳过(已处理): {stats.skipped_duplicate}", flush=True)
    print(f"跳过(关键词): {stats.skipped_keywords}", flush=True)
    print(f"跳过(过短): {stats.skipped_short}", flush=True)
    print(f"丢弃(无痛点): {stats.dropped}", flush=True)
    print(f"未过审(<{SCORE_APPROVE_MIN}): {stats.rejected}", flush=True)
    print(f"立项通过: {stats.approved}", flush=True)
    print(f"错误: {stats.errors}", flush=True)
    if stats.ideas:
        print("\n--- 本轮立项 ---", flush=True)
        for it in stats.ideas:
            print(f"  [{it['score']}] {it['title']}  -> {it['path']}", flush=True)
    print("====================================\n", flush=True)


if __name__ == "__main__":
    main()
