"""通用关键词分类器 - 类目动态化

LLM 分类由 AI IDE agent 完成：
1. 将待分类关键词写入 exchange/llm_input.json
2. Agent 读取后分类+翻译，写入 exchange/llm_output.json
3. Python 读取结果继续流程

所有 prompt 中的类目名从 category_config.json 动态读取。
"""
import json
import logging
import os
import re
import time
from typing import Optional

import config

logger = logging.getLogger(__name__)


class CategoryClassifier:
    """通用类目关键词分类器"""

    CATEGORIES = {"ingredient", "benefit", "brand", "condition", "form", "unrelated"}

    def __init__(self):
        self.category_name = config.get_category_name()
        self.category_name_en = config.get_category_name_en()
        self.dict_path = config.get_dict_path()
        self.exclusion_path = config.get_exclusion_path()
        self.dict_data = self._load_dict()
        self._build_patterns()
        self.new_words = {
            "ingredients": [], "benefits": [], "brands": [], "health_markers": []
        }

    def _load_dict(self):
        if not os.path.exists(self.dict_path):
            return {"ingredients": [], "benefits": [], "brands": [], "health_markers": []}
        with open(self.dict_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_patterns(self):
        self.patterns = {}
        for category, words in self.dict_data.items():
            sorted_words = sorted(words, key=len, reverse=True)
            escaped = [re.escape(w) for w in sorted_words]
            if escaped:
                self.patterns[category] = re.compile(
                    r'\b(' + '|'.join(escaped) + r')\b', re.IGNORECASE
                )

    def match_local(self, keyword):
        kw = keyword.lower().strip()
        if self.patterns.get("ingredients") and self.patterns["ingredients"].search(kw):
            return "ingredient"
        if self.patterns.get("benefits") and self.patterns["benefits"].search(kw):
            return "benefit"
        if self.patterns.get("brands") and self.patterns["brands"].search(kw):
            return "brand"
        return None

    def has_health_marker(self, keyword):
        if self.patterns.get("health_markers"):
            return bool(self.patterns["health_markers"].search(keyword.lower()))
        return False

    def request_llm_classification(self, keywords):
        """将待分类关键词写入交换文件，prompt 动态注入类目名"""
        os.makedirs(config.EXCHANGE_DIR, exist_ok=True)
        input_path = os.path.join(config.EXCHANGE_DIR, "llm_input.json")
        output_path = os.path.join(config.EXCHANGE_DIR, "llm_output.json")
        if os.path.exists(output_path):
            os.remove(output_path)

        # 从配置读取自定义分类标签
        cat_cfg = config.load_category_config()
        labels = cat_cfg.get("classification_labels", {})
        label_desc = labels.get("description", (
            "ingredient(核心产品/成分), benefit(功效/用途), brand(品牌), "
            "condition(场景/症状), form(形态/规格), unrelated(无关)"
        ))

        prompt = (
            f"判断以下每个关键词是否与亚马逊【{self.category_name}】类目相关并分类，"
            f"同时提供中文语义翻译。\n"
            f"分类标签：{label_desc}\n"
            '返回 JSON: {"keyword": {"label": "ingredient", "zh": "中文翻译"}, ...}\n'
            "unrelated 的词也需要翻译。"
        )

        with open(input_path, "w", encoding="utf-8") as f:
            json.dump({
                "task": "category_classification",
                "category": self.category_name,
                "prompt": prompt,
                "keywords": keywords,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"已写入 {len(keywords)} 个待分类关键词到 {input_path}")
        return input_path

    def read_llm_results(self):
        output_path = os.path.join(config.EXCHANGE_DIR, "llm_output.json")
        if not os.path.exists(output_path):
            logger.warning(f"未找到分类结果文件: {output_path}")
            return {}, {}
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        classifications = {}
        translations = {}
        for kw, val in data.items():
            if isinstance(val, dict):
                classifications[kw] = val.get("label", "unrelated")
                translations[kw] = val.get("zh", "")
            elif isinstance(val, str):
                classifications[kw] = val
        return classifications, translations

    def writeback_new_words(self, classified):
        category_map = {
            "ingredient": "ingredients",
            "benefit": "benefits",
            "brand": "brands",
            "condition": "benefits",
            "form": "health_markers",
        }
        for keyword, label in classified.items():
            if label == "unrelated":
                continue
            dict_key = category_map.get(label)
            if dict_key and keyword.lower() not in [w.lower() for w in self.dict_data.get(dict_key, [])]:
                self.dict_data[dict_key].append(keyword.lower())
                self.new_words[dict_key].append(keyword.lower())
        with open(self.dict_path, "w", encoding="utf-8") as f:
            json.dump(self.dict_data, f, ensure_ascii=False, indent=2)
        total_new = sum(len(v) for v in self.new_words.values())
        if total_new:
            logger.info(f"回写 {total_new} 个新词到本地词典")

    def classify_all(self, keywords):
        results = {}
        llm_candidates = []
        for kw in keywords:
            label = self.match_local(kw)
            if label:
                results[kw] = label
            elif self.has_health_marker(kw):
                llm_candidates.append(kw)
        logger.info(f"本地词典命中 {len(results)} 个，可疑词 {len(llm_candidates)} 个待 LLM 分类")
        return results, llm_candidates

    def merge_llm_results(self, local_results, llm_classifications):
        merged = dict(local_results)
        for kw, label in llm_classifications.items():
            if label != "unrelated":
                merged[kw] = label
        self.writeback_new_words(llm_classifications)
        logger.info(f"最终识别 {len(merged)} 个{self.category_name}相关关键词")
        return merged

    def load_exclusion_rules(self):
        if not os.path.exists(self.exclusion_path):
            return {}
        try:
            with open(self.exclusion_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def apply_exclusion_rules(self, classifications):
        rules = self.load_exclusion_rules()
        if not rules:
            return classifications, {}
        excluded = {}
        kept = {}
        pat_list = [re.compile(p, re.IGNORECASE) for p in rules.get("exclude_patterns", [])]
        exact_excludes = set(kw.lower() for kw in rules.get("exclude_keywords", []))
        for kw, label in classifications.items():
            kw_lower = kw.lower()
            if kw_lower in exact_excludes:
                excluded[kw] = "精确排除"
                continue
            hit = False
            for pat in pat_list:
                if pat.search(kw_lower):
                    excluded[kw] = "正则排除"
                    hit = True
                    break
            if not hit:
                kept[kw] = label
        if excluded:
            logger.info(f"排除规则过滤: {len(excluded)} 个词被排除")
        return kept, excluded
