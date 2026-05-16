"""类目初始化模块 - 交互式流程

流程：
1. 检查 Sorftime MCP 配置
2. 用户输入目标类目
3. 输出 exchange/dict_draft.json 让 agent 用 LLM 生成初始词典
4. Agent 写入后，Python 读取并展示给用户确认
5. 用户确认后保存到 data/{category}/
"""
import json
import os
import re
import logging

import config

logger = logging.getLogger(__name__)


def slugify(name):
    """中文类目名转英文 slug，用于目录名"""
    # 常见类目映射
    mapping = {
        "保健品": "supplements", "宠物用品": "pet-supplies",
        "美妆护肤": "beauty", "户外运动": "outdoor-sports",
        "家居用品": "home-garden", "母婴用品": "baby",
        "电子产品": "electronics", "厨房用品": "kitchen",
        "办公用品": "office", "汽车用品": "automotive",
        "服装鞋帽": "clothing", "玩具游戏": "toys-games",
        "食品饮料": "grocery", "工具五金": "tools-hardware",
        "运动健身": "sports-fitness", "图书": "books",
        "珠宝首饰": "jewelry", "箱包": "luggage",
        "乐器": "musical-instruments", "园艺": "garden",
    }
    if name in mapping:
        return mapping[name]
    # fallback: 用拼音或直接用英文
    clean = re.sub(r'[^\w\s-]', '', name.lower())
    return re.sub(r'[\s]+', '-', clean).strip('-') or "custom-category"


def run_init():
    """交互式类目初始化"""
    print()
    print("=" * 60)
    print("🚀 亚马逊 ABA 爆品关键词监测系统 - 类目初始化")
    print("=" * 60)
    print()

    # Step 1: 检查 Sorftime（可选）
    has_sorftime = config.check_sorftime_ready()
    if has_sorftime:
        print("✅ Sorftime MCP 已配置")
    else:
        print("⚠️  Sorftime MCP 未配置（部分功能受限）")
    print()

    # Step 2: 检查是否已有配置
    existing = config.load_category_config()
    if existing.get("category_name"):
        print(f"⚠️  当前已配置类目：{existing['category_name']}")
        print(f"   数据目录：data/{existing['category_name_en']}/")
        print()
        confirm = input("是否重新初始化？(y/N): ").strip().lower()
        if confirm != 'y':
            print("已取消。")
            return False
        print()

    # Step 3: 用户输入类目
    print("📋 请输入你要监测的亚马逊类目（中文）")
    print("   示例：保健品、宠物用品、美妆护肤、户外运动、厨房用品")
    print()
    category_name = input("目标类目: ").strip()
    if not category_name:
        print("❌ 类目名不能为空")
        return False

    category_en = slugify(category_name)
    print(f"\n   类目名：{category_name}")
    print(f"   英文标识：{category_en}")
    print(f"   数据目录：data/{category_en}/")

    # 让用户确认或自定义英文标识
    custom_en = input(f"\n英文标识确认（回车使用 '{category_en}'，或输入自定义）: ").strip()
    if custom_en:
        category_en = re.sub(r'[^\w-]', '-', custom_en.lower()).strip('-')

    # Step 4: 生成 dict_draft.json 让 agent 用 LLM 填充
    os.makedirs(config.EXCHANGE_DIR, exist_ok=True)
    draft_path = os.path.join(config.EXCHANGE_DIR, "dict_draft.json")
    draft_output = os.path.join(config.EXCHANGE_DIR, "dict_draft_output.json")

    if os.path.exists(draft_output):
        os.remove(draft_output)

    draft = {
        "task": "generate_category_dict",
        "category_name": category_name,
        "category_name_en": category_en,
        "prompt": (
            f"请为亚马逊【{category_name}】类目生成关键词词典和排除规则。\n\n"
            f"需要生成两个 JSON：\n\n"
            f"1. category_dict.json - 关键词词典，包含以下分类：\n"
            f"   - ingredients: 该类目的核心产品词/成分词（50-100个常见词）\n"
            f"   - benefits: 功效/用途/场景词（30-50个）\n"
            f"   - brands: 该类目知名品牌（20-30个）\n"
            f"   - health_markers: 通用标记词，用于识别可能相关但不确定的词（如剂型、规格、材质等，20-30个）\n\n"
            f"2. exclusion_rules.json - 排除规则：\n"
            f"   - exclude_patterns: 正则表达式列表，排除明显不相关的词（如其他类目的产品）\n"
            f"   - exclude_keywords: 精确排除的关键词列表\n\n"
            f"3. classification_labels: 分类标签描述，用于 LLM 分类 prompt\n"
            f"   - description: 一句话描述各标签含义（适配该类目）\n\n"
            f"请将结果写入 reports/.exchange/dict_draft_output.json，格式：\n"
            f'{{\n'
            f'  "category_dict": {{"ingredients": [...], "benefits": [...], "brands": [...], "health_markers": [...]}},\n'
            f'  "exclusion_rules": {{"exclude_patterns": [...], "exclude_keywords": [...]}},\n'
            f'  "classification_labels": {{"description": "..."}}\n'
            f'}}'
        ),
    }

    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"📝 已生成词典草稿请求：reports/.exchange/dict_draft.json")
    print()
    print("请让 AI Agent 读取该文件，生成初始词典和排除规则，")
    print(f"写入 reports/.exchange/dict_draft_output.json 后，")
    print(f"再次运行: python {os.path.basename(config.SKILL_DIR)}/main.py init-confirm")
    print("=" * 60)

    # 保存临时配置（类目名，等 confirm 时完成）
    config.save_category_config({
        "category_name": category_name,
        "category_name_en": category_en,
        "status": "pending_dict",
    })

    return True


def run_init_confirm():
    """确认 agent 生成的词典，保存到 data 目录"""
    cfg = config.load_category_config()
    if not cfg.get("category_name"):
        print("❌ 请先运行 init 初始化类目")
        return False

    category_name = cfg["category_name"]
    category_en = cfg["category_name_en"]

    draft_output = os.path.join(config.EXCHANGE_DIR, "dict_draft_output.json")
    if not os.path.exists(draft_output):
        print(f"❌ 未找到 {draft_output}")
        print("   请先让 AI Agent 生成词典后再运行此命令")
        return False

    with open(draft_output, "r", encoding="utf-8") as f:
        data = json.load(f)

    cat_dict = data.get("category_dict", {})
    exclusion = data.get("exclusion_rules", {})
    labels = data.get("classification_labels", {})

    # 展示摘要
    print()
    print("=" * 60)
    print(f"📋 【{category_name}】类目词典预览")
    print("=" * 60)
    for key, words in cat_dict.items():
        print(f"\n  {key}: {len(words)} 个词")
        preview = words[:8]
        print(f"    前几个: {', '.join(str(w) for w in preview)}...")

    print(f"\n  排除正则: {len(exclusion.get('exclude_patterns', []))} 条")
    print(f"  精确排除: {len(exclusion.get('exclude_keywords', []))} 个词")
    if labels.get("description"):
        print(f"\n  分类标签: {labels['description']}")

    print()
    print("你可以：")
    print("  1. 确认使用（回车）")
    print("  2. 输入 'edit' 手动编辑后再确认")
    print("  3. 输入 'cancel' 取消")
    choice = input("\n选择: ").strip().lower()

    if choice == 'cancel':
        print("已取消。")
        return False

    if choice == 'edit':
        data_dir = config.get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        dict_path = os.path.join(data_dir, "category_dict.json")
        excl_path = os.path.join(data_dir, "exclusion_rules.json")
        with open(dict_path, "w", encoding="utf-8") as f:
            json.dump(cat_dict, f, ensure_ascii=False, indent=2)
        with open(excl_path, "w", encoding="utf-8") as f:
            json.dump(exclusion, f, ensure_ascii=False, indent=2)
        print(f"\n📂 词典已保存到：")
        print(f"   {dict_path}")
        print(f"   {excl_path}")
        print(f"\n请手动编辑后，再次运行 init-confirm 确认。")
        return False

    # 确认保存
    data_dir = config.get_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    dict_path = os.path.join(data_dir, "category_dict.json")
    excl_path = os.path.join(data_dir, "exclusion_rules.json")

    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(cat_dict, f, ensure_ascii=False, indent=2)
    with open(excl_path, "w", encoding="utf-8") as f:
        json.dump(exclusion, f, ensure_ascii=False, indent=2)

    # 更新配置为就绪状态
    config.save_category_config({
        "category_name": category_name,
        "category_name_en": category_en,
        "classification_labels": labels,
        "status": "ready",
    })

    print()
    print("=" * 60)
    print(f"✅ 【{category_name}】类目初始化完成！")
    print(f"   词典: {dict_path}")
    print(f"   排除规则: {excl_path}")
    print()
    print("现在可以运行监测：")
    print(f"   python {os.path.basename(config.SKILL_DIR)}/main.py step1")
    print("=" * 60)
    return True
