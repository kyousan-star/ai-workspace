"""主流程编排 - 亚马逊 ABA 爆品关键词监测系统（通用版）

命令：
  python main.py init            # 类目初始化（交互式）
  python main.py init-confirm    # 确认 agent 生成的词典
  python main.py step1           # 抓取 + 本地匹配
  python main.py step2           # 合并 + Tier 分层 + Sorftime 查询
  python main.py step3           # 生成最终 HTML 报告
"""
import os
import sys
import json
import logging
import warnings
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

import config
from scraper import scrape_all_combos, entries_to_dicts
from classifier import CategoryClassifier
from analyzer import analyze_keywords_basic, apply_sorftime_results
from sorftime_client import query_sorftime_batch
from reporter import generate_report
from db import init_db, save_results

os.makedirs(config.REPORT_DIR, exist_ok=True)
os.makedirs(config.EXCHANGE_DIR, exist_ok=True)

_log_file = os.path.join(config.REPORT_DIR, f"run_{datetime.now():%Y-%m-%d-%H-%M}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

SCRAPED_PATH = os.path.join(config.EXCHANGE_DIR, "scraped.json")
LOCAL_MATCH_PATH = os.path.join(config.EXCHANGE_DIR, "local_match.json")
TIERED_PATH = os.path.join(config.EXCHANGE_DIR, "tiered.json")


def step1_scrape_and_local_match():
    logger.info("=" * 60)
    logger.info("🧬 第 1 步: 抓取 + 本地词典匹配")
    logger.info("=" * 60)

    has_sorftime = config.check_sorftime_ready()
    if not has_sorftime:
        logger.warning("Sorftime 未配置，将跳过深度数据查询")
    
    if not config.check_category_ready():
        return False

    category_name = config.get_category_name()
    logger.info(f"当前监测类目：{category_name}")

    init_db()

    logger.info("📡 抓取 AMZ123 ABA 热搜词...")
    entries = scrape_all_combos()
    entry_dicts = entries_to_dicts(entries)
    total_scraped = len(entry_dicts)
    logger.info(f"抓取完成: {total_scraped} 个去重关键词")
    if not entry_dicts:
        logger.error("未抓取到任何数据，退出")
        return False

    with open(SCRAPED_PATH, "w", encoding="utf-8") as f:
        json.dump(entry_dicts, f, ensure_ascii=False, indent=2)

    logger.info("🔬 本地词典匹配...")
    classifier = CategoryClassifier()
    all_keywords = [e["keyword"] for e in entry_dicts]
    local_results, llm_candidates = classifier.classify_all(all_keywords)

    with open(LOCAL_MATCH_PATH, "w", encoding="utf-8") as f:
        json.dump({"local_results": local_results, "total_scraped": total_scraped},
                  f, ensure_ascii=False, indent=2)

    if llm_candidates:
        classifier.request_llm_classification(llm_candidates)
        logger.info(f"✅ 第 1 步完成。{len(llm_candidates)} 个关键词待 agent 分类+翻译")
        logger.info(f'   返回格式: {{"keyword": {{"label": "ingredient", "zh": "中文翻译"}}}}')
    else:
        with open(os.path.join(config.EXCHANGE_DIR, "llm_output.json"), "w", encoding="utf-8") as f:
            json.dump({}, f)
        logger.info("✅ 第 1 步完成。所有关键词已由本地词典匹配")
    return True


def step2_analyze():
    logger.info("=" * 60)
    logger.info("📊 第 2 步: 分类合并 + 分层 + Sorftime 查询")
    logger.info("=" * 60)

    category_name = config.get_category_name()

    with open(SCRAPED_PATH, "r", encoding="utf-8") as f:
        entry_dicts = json.load(f)
    with open(LOCAL_MATCH_PATH, "r", encoding="utf-8") as f:
        local_data = json.load(f)

    classifier = CategoryClassifier()
    llm_classifications, llm_translations = classifier.read_llm_results()
    classifications = classifier.merge_llm_results(local_data["local_results"], llm_classifications)
    classifications, excluded_keywords = classifier.apply_exclusion_rules(classifications)
    total_cat = len(classifications)
    logger.info(f"过滤完成: {total_cat}/{local_data['total_scraped']} 个{category_name}相关词"
                f" (排除 {len(excluded_keywords)} 个)")

    results = analyze_keywords_basic(entry_dicts, classifications, llm_translations)

    tier1_kws = [r.keyword for r in results if r.tier == 1]
    tier2_kws = [r.keyword for r in results if r.tier == 2]
    sorftime_stats = {"total_calls": 0, "enriched": 0}
    if config.SORFTIME_API_KEY and (tier1_kws or tier2_kws):
        sorftime_data, sorftime_stats = query_sorftime_batch(tier1_kws, tier2_kws)
        results = apply_sorftime_results(results, sorftime_data)

    logger.info("💾 存储到 SQLite...")
    save_results(results)

    from dataclasses import asdict
    with open(TIERED_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "results": [asdict(r) for r in results],
            "total_scraped": local_data["total_scraped"],
            "total_category": total_cat,
            "new_words": classifier.new_words,
            "excluded_keywords": excluded_keywords,
            "sorftime_stats": sorftime_stats,
        }, f, ensure_ascii=False, indent=2)

    # 输出 analysis_input.json
    analysis_input = os.path.join(config.EXCHANGE_DIR, "analysis_input.json")
    analysis_output = os.path.join(config.EXCHANGE_DIR, "analysis_output.json")
    if os.path.exists(analysis_output):
        os.remove(analysis_output)

    tier1_data = [asdict(r) for r in results if r.tier == 1]

    with open(analysis_input, "w", encoding="utf-8") as f:
        json.dump({
            "task": "write_analysis",
            "category": category_name,
            "prompt": (
                f"为以下每个 Tier 1 关键词写一段中文分析摘要（2-3句话），包含：\n"
                f"1. 搜索量/排名变化趋势解读\n"
                f"2. CPC和竞争度判断\n"
                f"3. 机会/风险评估\n\n"
                f"当前监测类目：{category_name}\n\n"
                f"同时，将所有 Tier 1 关键词按赛道/主题聚类，\n"
                f"每个赛道写一个标题和简短描述。\n\n"
                f"返回 JSON 格式：\n"
                '{\n'
                '  "keyword_analysis": {"keyword": "分析摘要文字", ...},\n'
                '  "tracks": [{"name": "赛道名", "icon": "emoji", "keywords": ["kw1","kw2"], "summary": "描述"}, ...],\n'
                '  "core_findings": ["发现1", "发现2", ...]\n'
                '}'
            ),
            "tier1_keywords": tier1_data,
        }, f, ensure_ascii=False, indent=2)

    t1, t2, t3 = len(tier1_kws), len(tier2_kws), sum(1 for r in results if r.tier == 3)
    logger.info(f"✅ 第 2 步完成。Tier1={t1} | Tier2={t2} | Tier3={t3}")
    logger.info(f"   请 agent 读取 reports/.exchange/analysis_input.json 写分析摘要")
    logger.info(f"   写入 reports/.exchange/analysis_output.json 后运行 step3")
    return True


def step3_render_report():
    logger.info("=" * 60)
    logger.info("📝 第 3 步: 生成最终报告")
    logger.info("=" * 60)

    with open(TIERED_PATH, "r", encoding="utf-8") as f:
        tiered_data = json.load(f)

    analysis_path = os.path.join(config.EXCHANGE_DIR, "analysis_output.json")
    analysis = {}
    if os.path.exists(analysis_path):
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)
        logger.info("已读取分析摘要")

    from analyzer import TrendData
    results = [TrendData(**r) for r in tiered_data["results"]]

    report_path = generate_report(
        results=results,
        total_scraped=tiered_data["total_scraped"],
        total_supplement=tiered_data.get("total_category", tiered_data.get("total_supplement", 0)),
        new_dict_words=tiered_data["new_words"],
        analysis=analysis,
        excluded_keywords=tiered_data.get("excluded_keywords", {}),
        sorftime_stats=tiered_data.get("sorftime_stats", {}),
    )

    logger.info("=" * 60)
    logger.info(f"✅ 完成! 报告: {report_path}")
    t1 = sum(1 for r in results if r.tier == 1)
    t2 = sum(1 for r in results if r.tier == 2)
    t3 = sum(1 for r in results if r.tier == 3)
    logger.info(f"   Tier1={t1} | Tier2={t2} | Tier3={t3}")
    logger.info("=" * 60)
    return report_path


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "help"
    if step == "init":
        from category_init import run_init
        run_init()
    elif step == "init-confirm":
        from category_init import run_init_confirm
        run_init_confirm()
    elif step == "step1":
        step1_scrape_and_local_match()
    elif step == "step2":
        step2_analyze()
    elif step == "step3":
        step3_render_report()
    else:
        print("亚马逊 ABA 爆品关键词监测系统（通用版）")
        print()
        print("用法:")
        print("  python main.py init            # 首次运行：类目初始化")
        print("  python main.py init-confirm    # 确认 AI 生成的词典")
        print("  python main.py step1           # 抓取 + 本地匹配")
        print("  python main.py step2           # 分层 + Sorftime 查询")
        print("  python main.py step3           # 生成 HTML 报告")
        sys.exit(1)
