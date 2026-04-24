"""
端到端集成测试 — 使用真实 LLM API（SiliconFlow Qwen2.5-7B）。

运行前确保 .env 已配置 LLM_API_KEY。
默认跳过（CI 环境无真实 KEY），使用以下命令运行：
    pytest tests/test_e2e_integration.py -v -s

或设置环境变量：
    RUN_E2E=1 pytest tests/test_e2e_integration.py -v -s
"""
from __future__ import annotations

import os
import pytest

# 没有 RUN_E2E 标记或 LLM_API_KEY 时跳过
_SKIP = not (os.getenv("RUN_E2E") or os.getenv("LLM_API_KEY", "").startswith("sk-"))

@pytest.mark.skipif(_SKIP, reason="需要 RUN_E2E=1 且配置真实 LLM_API_KEY")
class TestE2EIngestPipeline:
    """端到端：webhook 注入 → Agent 链路 → SQLite 持久化"""

    def test_ingest_with_real_llm_pain_point(self, tmp_path):
        """注入一条明确的痛点内容，验证 extractor 能正确识别 has_pain_point=True。"""
        from config.settings import Settings, get_settings
        get_settings.cache_clear()
        real_settings = get_settings()  # 从 .env 加载真实 Key

        from core.agents.extractor_agent import run_extractor
        from plugins.base_scraper import RawItem

        item = RawItem(
            id="e2e_test_1",
            url="https://example.com",
            title="每天手动整理Excel发工资条太痛苦了",
            body=(
                "我们公司每个月发工资条，财务MM都要手动复制粘贴，"
                "每次要花2-3小时。有没有什么软件可以自动发到每个员工微信？"
                "现在用的方法：Excel导出 -> 手动复制 -> 逐一粘贴到微信 -> 发送。"
                "真的很浪费时间，而且容易出错。"
            ),
            source="v2ex",
        )
        result = run_extractor(real_settings, item)
        print(f"\n[E2E Extractor] has_pain_point={result.has_pain_point}, summary={result.summary[:60]}")
        assert result.has_pain_point is True, f"应识别为有痛点，实际: {result}"

    def test_ingest_with_real_llm_no_pain_point(self, tmp_path):
        """注入一条无意义内容，验证 extractor 正确返回 has_pain_point=False。"""
        from config.settings import get_settings
        get_settings.cache_clear()
        real_settings = get_settings()

        from core.agents.extractor_agent import run_extractor
        from plugins.base_scraper import RawItem

        item = RawItem(
            id="e2e_test_2",
            url="https://example.com",
            title="今天天气真好",
            body="阳光明媚，心情不错，出去溜达了一圈。",
            source="v2ex",
        )
        result = run_extractor(real_settings, item)
        print(f"\n[E2E Extractor] has_pain_point={result.has_pain_point}")
        assert result.has_pain_point is False, f"不应识别为痛点，实际: {result}"

    def test_full_pipeline_via_ingest(self, tmp_path):
        """全链路：run_ingested_contents 驱动完整 Agent 流水线（不 mock）。"""
        from config.settings import get_settings
        get_settings.cache_clear()
        real_settings = get_settings()
        real_settings = real_settings.model_copy(update={
            "ideahunter_sqlite_path": str(tmp_path / "e2e.db"),
            "output_dir": str(tmp_path / "output"),
        })

        from core.memory.sqlite_manager import SqliteManager
        from core.orchestrator import run_ingested_contents

        db = SqliteManager(real_settings.ideahunter_sqlite_path)
        content = (
            "我是电商卖家，每天需要从淘宝、京东、拼多多三个平台下载订单，"
            "然后手动合并到Excel里统计，再导入ERP。这个过程每天至少要1小时，"
            "非常枯燥。如果有个工具能自动同步三平台订单就好了！"
        )
        stats = run_ingested_contents(
            source_name="e2e_test",
            content_list=[content],
            settings=real_settings,
            db=db,
            output_dir=real_settings.output_dir,
            on_progress=lambda m: print(f"[进度] {m}"),
        )
        print(f"\n[E2E Pipeline] fetched={stats.fetched} approved={stats.approved} "
              f"rejected={stats.rejected} dropped={stats.dropped} errors={stats.errors}")
        if stats.errors:
            pytest.fail(f"Pipeline 有 {stats.errors} 个错误")
        assert stats.fetched == 1
        # 痛点明确，应通过 extractor，但 critic 可能评分不足 80
        assert stats.dropped == 0, "不应被 extractor 丢弃"
        print(f"最终结果：approved={stats.approved}, rejected={stats.rejected}")
        if stats.approved:
            idea = stats.ideas[0]
            print(f"🎉 立项通过: [{idea['score']}分] {idea['title']}")
