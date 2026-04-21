"""
从 CAIL 原始数据构建多 Agent 版本所需的本地资源文件。

输出内容：
1. entity_types.json：FactExtractorAgent 使用的实体类型清单
2. relation_types.json：FactExtractorAgent 使用的关系类型清单
3. law_knowledge_base.json：由原始样本汇总出的罪名/法条/量刑索引
4. test_cases.json：覆盖当前 10 类 BERT 标签和若干复杂场景的测试样本

执行方式（项目根目录下）：
  python agent/脚本/build_agent_resources.py
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUTS = [
    PROJECT_ROOT / "模型训练" / "原始数据" / "final_all_data" / "exercise_contest" / "data_train.json",
    PROJECT_ROOT / "模型训练" / "原始数据" / "final_all_data" / "exercise_contest" / "data_valid.json",
]
DEFAULT_LABEL_MAPPING = PROJECT_ROOT / "模型训练" / "处理后数据" / "label_mapping.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "agent" / "资源"

MAX_EXAMPLES_PER_GROUP = 3
MAX_FACT_EXCERPT = 220

REPRESENTATIVE_KEYWORDS: Dict[str, List[str]] = {
    "盗窃": ["盗窃", "窃取", "秘密窃取", "盗走", "偷走"],
    "危险驾驶": ["醉酒", "酒后", "驾驶", "机动车", "乙醇", "血液中乙醇"],
    "故意伤害": ["故意伤害", "殴打", "打伤", "轻伤", "重伤", "骨折"],
    "交通肇事": ["交通肇事", "交通事故", "驾驶", "撞", "逃逸", "责任认定"],
    "走私、贩卖、运输、制造毒品": ["毒品", "甲基苯丙胺", "海洛因", "冰毒", "贩卖", "运输", "制造"],
    "容留他人吸毒": ["容留", "吸毒", "毒品", "尿检", "吸食"],
    "诈骗": ["诈骗", "骗取", "骗得", "虚构", "谎称"],
    "寻衅滋事": ["寻衅滋事", "随意殴打", "辱骂", "追逐", "拦截", "起哄闹事"],
    "抢劫": ["抢劫", "持刀", "暴力", "胁迫", "抢走", "劫取"],
    "信用卡诈骗": ["信用卡", "透支", "套现", "银行", "催收", "恶意透支"],
}


ENTITY_TYPES: List[Dict[str, Any]] = [
    {
        "type": "案件",
        "description": "当前待分析案件的根节点，用于挂接全局事实、预测和法条信息。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["description", "timestamp", "case_tags"],
        "examples": ["案件-2026-0001"],
    },
    {
        "type": "人物",
        "description": "案件中的嫌疑人、被告人、同案人员、证人等参与者。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["role", "aliases", "evidence_span"],
        "examples": ["被告人段某", "证人张某"],
    },
    {
        "type": "受害人",
        "description": "受到侵害、伤害、骗取财物或其他损失的一方。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["role", "injury_level", "loss_summary", "evidence_span"],
        "examples": ["被害人王某", "受害人华某某"],
    },
    {
        "type": "组织机构",
        "description": "案件中出现的公司、门店、单位、银行、公安机关等组织。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["organization_type", "evidence_span"],
        "examples": ["嘉兴市多凌金牛制衣有限公司", "某某银行"],
    },
    {
        "type": "行为",
        "description": "案件中的核心动作、违法行为、交易行为、驾驶行为或暴力行为。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["action_mode", "evidence_span", "normalized_action"],
        "examples": ["持刀抢劫", "醉酒驾驶", "骗取钱款"],
    },
    {
        "type": "情节",
        "description": "影响罪名判断或量刑轻重的情节，如自首、累犯、酒后、纠纷起因等。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["severity", "evidence_span"],
        "examples": ["酒后", "因琐事发生口角", "拒不赔偿"],
    },
    {
        "type": "物品",
        "description": "涉案工具、赃物、违禁品、车辆、银行卡等具体物品。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["category", "quantity", "evidence_span"],
        "examples": ["石头", "手机", "毒品", "信用卡"],
    },
    {
        "type": "金额",
        "description": "涉案金额、罚金、赔偿、损失金额等数值类信息。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["currency", "normalized_value", "evidence_span"],
        "examples": ["529.94元", "3000元"],
    },
    {
        "type": "时间",
        "description": "案发时间、抓获时间、饮酒后驾驶时间等时间节点。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["normalized_value", "evidence_span"],
        "examples": ["2015年11月10日晚9时许"],
    },
    {
        "type": "地点",
        "description": "案发地、交易地、查获地、工作单位、道路等空间位置。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["location_type", "evidence_span"],
        "examples": ["悦来镇石锅烤肉店", "某县莲新公路"],
    },
    {
        "type": "伤情",
        "description": "轻伤、重伤、骨折、中毒等受害结果或医学鉴定结果。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["severity", "evidence_span"],
        "examples": ["轻伤一级", "右额部粉碎性骨折"],
    },
    {
        "type": "证据",
        "description": "鉴定意见、证言、勘验笔录、书证等支持事实或罪名判断的证据。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["evidence_type", "evidence_span"],
        "examples": ["司法鉴定意见", "现场勘验笔录", "被告人供述"],
    },
    {
        "type": "罪名",
        "description": "BERT 预测或法条检索后得到的候选罪名节点。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["probability", "rank", "normalized_value"],
        "examples": ["盗窃", "故意伤害"],
    },
    {
        "type": "法条",
        "description": "与案件或罪名关联的刑法条款编号与后续补充的法条正文。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["article_number", "text", "source_dataset"],
        "examples": ["刑法第264条", "刑法第234条"],
    },
    {
        "type": "量刑规则",
        "description": "根据统计规则、本地规则库或后续人工补充形成的量刑建议节点。",
        "required_graph_fields": ["id", "type", "label", "source"],
        "optional_fields": ["penalty_range", "confidence_note", "source_dataset"],
        "examples": ["常见刑期区间 7-12 月", "罚金区间 1000-5000 元"],
    },
]


RELATION_TYPES: List[Dict[str, Any]] = [
    {
        "relation": "从属于案件",
        "description": "将人物、行为、证据、法条等节点绑定到案件根节点。",
        "source_types": ["人物", "受害人", "组织机构", "行为", "情节", "物品", "金额", "时间", "地点", "伤情", "证据", "罪名", "法条", "量刑规则"],
        "target_types": ["案件"],
        "examples": ["行为 -> 案件", "法条 -> 案件"],
    },
    {
        "relation": "参与",
        "description": "表示人物或组织与案件的直接参与关系。",
        "source_types": ["人物", "组织机构"],
        "target_types": ["案件"],
        "examples": ["被告人 -> 案件", "涉案公司 -> 案件"],
    },
    {
        "relation": "实施",
        "description": "表示人物实施了某项行为。",
        "source_types": ["人物"],
        "target_types": ["行为"],
        "examples": ["段某 -> 持石头击打"],
    },
    {
        "relation": "作用于",
        "description": "表示行为作用到受害人、物品或组织上。",
        "source_types": ["行为"],
        "target_types": ["受害人", "物品", "组织机构"],
        "examples": ["击打 -> 被害人王某", "骗取 -> 钱款"],
    },
    {
        "relation": "发生于",
        "description": "表示行为在某个时间或地点发生。",
        "source_types": ["行为"],
        "target_types": ["时间", "地点"],
        "examples": ["醉酒驾驶 -> 2015年6月23日", "抢劫 -> 某路口"],
    },
    {
        "relation": "使用工具",
        "description": "表示行为或人物使用了某件涉案物品。",
        "source_types": ["人物", "行为"],
        "target_types": ["物品"],
        "examples": ["段某 -> 石头", "抢劫行为 -> 刀具"],
    },
    {
        "relation": "涉及金额",
        "description": "表示行为、案件或量刑规则涉及具体金额。",
        "source_types": ["案件", "行为", "量刑规则"],
        "target_types": ["金额"],
        "examples": ["诈骗行为 -> 3000元", "罚金建议 -> 5000元"],
    },
    {
        "relation": "造成",
        "description": "表示行为导致伤情、损失或其他后果。",
        "source_types": ["行为"],
        "target_types": ["伤情", "情节", "金额"],
        "examples": ["殴打 -> 轻伤一级", "肇事 -> 财产损失"],
    },
    {
        "relation": "支持证据",
        "description": "表示某项证据支持某个行为、伤情、罪名或量刑判断。",
        "source_types": ["证据"],
        "target_types": ["行为", "伤情", "罪名", "量刑规则"],
        "examples": ["司法鉴定意见 -> 轻伤一级", "供述 -> 诈骗行为"],
    },
    {
        "relation": "指向罪名",
        "description": "表示事实、行为、情节或证据共同支持某个候选罪名。",
        "source_types": ["行为", "情节", "伤情", "证据", "案件"],
        "target_types": ["罪名"],
        "examples": ["醉酒驾驶 -> 危险驾驶", "骗取钱款 -> 诈骗"],
    },
    {
        "relation": "对应法条",
        "description": "表示罪名与法条节点之间的静态知识关系。",
        "source_types": ["罪名"],
        "target_types": ["法条"],
        "examples": ["盗窃 -> 刑法第264条"],
    },
    {
        "relation": "约束量刑",
        "description": "表示法条或量刑情节对量刑规则节点的约束关系。",
        "source_types": ["法条", "情节", "罪名"],
        "target_types": ["量刑规则"],
        "examples": ["刑法第234条 -> 常见刑期区间", "酒后 -> 从重提示"],
    },
]


def normalize_charge_name(name: str) -> str:
    return name.replace("[", "").replace("]", "").strip()


def unique_preserve_order(values: Iterable[Any]) -> List[Any]:
    seen = set()
    result: List[Any] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def truncate_text(text: str, limit: int = MAX_FACT_EXCERPT) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}..."


def imprisonment_bucket(term: Dict[str, Any]) -> str:
    if term.get("death_penalty"):
        return "death_penalty"
    if term.get("life_imprisonment"):
        return "life_imprisonment"

    months = int(term.get("imprisonment") or 0)
    if months <= 0:
        return "0_month"
    if months <= 6:
        return "1_6_months"
    if months <= 12:
        return "7_12_months"
    if months <= 24:
        return "13_24_months"
    if months <= 36:
        return "25_36_months"
    if months <= 60:
        return "37_60_months"
    if months <= 120:
        return "61_120_months"
    return "121_plus_months"


def fine_bucket(amount: float) -> str:
    if amount <= 0:
        return "0"
    if amount <= 1000:
        return "1_1000"
    if amount <= 5000:
        return "1001_5000"
    if amount <= 10000:
        return "5001_10000"
    if amount <= 50000:
        return "10001_50000"
    return "50001_plus"


def safe_average(total: float, count: int) -> float | None:
    if count <= 0:
        return None
    return round(total / count, 2)


def month_summary(month_count: int, month_total: float, month_min: int | None, month_max: int | None) -> Dict[str, Any]:
    return {
        "finite_term_count": month_count,
        "average_months": safe_average(month_total, month_count),
        "min_months": month_min,
        "max_months": month_max,
    }


def quantize_score(length: int, accusation_count: int, article_count: int, months: int | None, fine: float) -> float:
    length_score = 120 - abs(min(length, 600) - 180) * 0.35
    multi_bonus = 18 if accusation_count > 1 else 0
    article_bonus = 10 if article_count > 1 else 0
    term_bonus = min((months or 0) / 6, 20)
    fine_bonus = min(fine / 2000, 16)
    return round(length_score + multi_bonus + article_bonus + term_bonus + fine_bonus, 4)


def representative_match_score(fact: str, model_charges: List[str]) -> Dict[str, int]:
    matches: Dict[str, int] = {}
    for charge in model_charges:
        keywords = REPRESENTATIVE_KEYWORDS.get(charge, [])
        score = sum(1 for keyword in keywords if keyword in fact)
        matches[charge] = score
    return matches


def load_model_charges(label_mapping_path: Path) -> List[str]:
    with label_mapping_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "id2label" in data:
        id2label = data["id2label"]
        return [id2label[str(i)] for i in range(int(data.get("num_classes", len(id2label))))]

    if "label2id" in data:
        label2id = data["label2id"]
        return [label for label, _ in sorted(label2id.items(), key=lambda item: item[1])]

    raise ValueError(f"无法从标签映射中读取标签：{label_mapping_path}")


def iter_jsonl(paths: Iterable[Path]) -> Iterable[Dict[str, Any]]:
    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                item = json.loads(stripped)
                item["_source_file"] = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
                item["_line_number"] = line_no
                yield item


@dataclass
class GroupSummary:
    name: str
    normalized_name: str | None = None
    sample_count: int = 0
    current_model_supported: bool = False
    related_counter: Counter = field(default_factory=Counter)
    co_occurrence_counter: Counter = field(default_factory=Counter)
    imprisonment_histogram: Counter = field(default_factory=Counter)
    fine_histogram: Counter = field(default_factory=Counter)
    finite_term_count: int = 0
    finite_term_total: float = 0.0
    finite_term_min: int | None = None
    finite_term_max: int | None = None
    fine_count: int = 0
    fine_total: float = 0.0
    fine_min: float | None = None
    fine_max: float | None = None
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def add_term(self, term: Dict[str, Any]) -> None:
        self.imprisonment_histogram[imprisonment_bucket(term)] += 1
        if term.get("death_penalty") or term.get("life_imprisonment"):
            return

        months = int(term.get("imprisonment") or 0)
        self.finite_term_count += 1
        self.finite_term_total += months
        if self.finite_term_min is None or months < self.finite_term_min:
            self.finite_term_min = months
        if self.finite_term_max is None or months > self.finite_term_max:
            self.finite_term_max = months

    def add_fine(self, amount: float) -> None:
        self.fine_histogram[fine_bucket(amount)] += 1
        self.fine_count += 1
        self.fine_total += amount
        if self.fine_min is None or amount < self.fine_min:
            self.fine_min = amount
        if self.fine_max is None or amount > self.fine_max:
            self.fine_max = amount

    def maybe_add_example(self, example: Dict[str, Any]) -> None:
        current_score = example["selection_score"]
        if len(self.examples) < MAX_EXAMPLES_PER_GROUP:
            self.examples.append(example)
        else:
            lowest_index = min(range(len(self.examples)), key=lambda idx: self.examples[idx]["selection_score"])
            if current_score > self.examples[lowest_index]["selection_score"]:
                self.examples[lowest_index] = example

        self.examples.sort(key=lambda item: item["selection_score"], reverse=True)

    def to_dict(self, top_key: str, top_value_key: str, co_occurrence_key: str) -> Dict[str, Any]:
        payload = {
            "name": self.name,
            "normalized_name": self.normalized_name,
            "sample_count": self.sample_count,
            "current_model_supported": self.current_model_supported,
            top_key: [
                {top_value_key: key, "count": value}
                for key, value in self.related_counter.most_common(8)
            ],
            co_occurrence_key: [
                {"name": key, "count": value}
                for key, value in self.co_occurrence_counter.most_common(8)
            ],
            "imprisonment_histogram": dict(self.imprisonment_histogram),
            "fine_histogram": dict(self.fine_histogram),
            "imprisonment_summary": month_summary(
                self.finite_term_count,
                self.finite_term_total,
                self.finite_term_min,
                self.finite_term_max,
            ),
            "fine_summary": {
                "sample_count": self.fine_count,
                "average_amount": safe_average(self.fine_total, self.fine_count),
                "min_amount": None if self.fine_min is None else round(self.fine_min, 2),
                "max_amount": None if self.fine_max is None else round(self.fine_max, 2),
            },
            "example_cases": [
                {
                    "sample_id": example["sample_id"],
                    "source_file": example["source_file"],
                    "line_number": example["line_number"],
                    "fact_excerpt": example["fact_excerpt"],
                    "raw_accusations": example["raw_accusations"],
                    "normalized_accusations": example["normalized_accusations"],
                    "relevant_articles": example["relevant_articles"],
                    "term_of_imprisonment": example["term_of_imprisonment"],
                    "punish_of_money": example["punish_of_money"],
                }
                for example in self.examples
            ],
        }
        return payload


def build_example_record(item: Dict[str, Any], normalized_accusations: List[str], score: float) -> Dict[str, Any]:
    meta = item["meta"]
    raw_accusations = unique_preserve_order(meta.get("accusation", []))
    relevant_articles = unique_preserve_order(int(article) for article in meta.get("relevant_articles", []))
    return {
        "sample_id": f"{item['_source_file']}#{item['_line_number']}",
        "source_file": item["_source_file"],
        "line_number": item["_line_number"],
        "fact_excerpt": truncate_text(item["fact"]),
        "raw_accusations": raw_accusations,
        "normalized_accusations": normalized_accusations,
        "relevant_articles": relevant_articles,
        "term_of_imprisonment": meta.get("term_of_imprisonment", {}),
        "punish_of_money": meta.get("punish_of_money", 0),
        "selection_score": score,
    }


def sample_tags(normalized_accusations: List[str], meta: Dict[str, Any], fact: str) -> List[str]:
    tags: List[str] = []
    accusation_text = " ".join(normalized_accusations)
    if any(keyword in accusation_text for keyword in ["盗窃", "抢劫", "诈骗", "信用卡诈骗"]):
        tags.append("财产型")
    if any(keyword in accusation_text for keyword in ["故意伤害", "抢劫", "寻衅滋事"]):
        tags.append("暴力型")
    if any(keyword in accusation_text for keyword in ["危险驾驶", "交通肇事"]):
        tags.append("交通类")
    if "毒品" in accusation_text:
        tags.append("毒品类")
    if len(meta.get("accusation", [])) > 1:
        tags.append("多罪名")
    if "轻伤" in fact or "重伤" in fact:
        tags.append("含伤情")
    if meta.get("punish_of_money", 0) > 0:
        tags.append("含罚金")
    if len(fact) >= 280:
        tags.append("长文本")
    return tags


def scenario_entry(case: Dict[str, Any], reason: str) -> Dict[str, Any]:
    payload = {
        key: value
        for key, value in case.items()
        if key not in {"representative_match_score"}
    }
    payload["selection_reason"] = reason
    return payload


def build_test_cases(cases: List[Dict[str, Any]], model_charges: List[str]) -> Dict[str, Any]:
    used_ids: set[str] = set()
    selected: List[Dict[str, Any]] = []

    for charge in model_charges:
        keyword_filtered = [
            case for case in cases
            if charge in case["expected"]["normalized_accusations"]
            and len(case["expected"]["normalized_accusations"]) == 1
            and case["representative_match_score"].get(charge, 0) > 0
        ]
        candidates = [
            case for case in cases
            if charge in case["expected"]["normalized_accusations"]
            and len(case["expected"]["normalized_accusations"]) == 1
        ]
        if keyword_filtered:
            candidates = keyword_filtered
        if not candidates:
            keyword_filtered = [
                case for case in cases
                if charge in case["expected"]["normalized_accusations"]
                and case["representative_match_score"].get(charge, 0) > 0
            ]
            candidates = keyword_filtered or [
                case for case in cases if charge in case["expected"]["normalized_accusations"]
            ]
        if not candidates:
            continue

        best = max(
            candidates,
            key=lambda item: (
                item["representative_match_score"].get(charge, 0),
                item["selection_score"],
            ),
        )
        if best["case_id"] in used_ids:
            continue

        used_ids.add(best["case_id"])
        selected.append(scenario_entry(best, f"覆盖当前 BERT 标签：{charge}"))

    scenario_rules = [
        (
            "多罪名联动",
            lambda item: len(item["expected"]["normalized_accusations"]) > 1,
        ),
        (
            "长文本抽取压力测试",
            lambda item: len(item["fact"]) >= 320,
        ),
        (
            "高罚金样本",
            lambda item: item["expected"]["punish_of_money"] > 10000,
        ),
        (
            "高刑期样本",
            lambda item: (
                item["expected"]["term_of_imprisonment"].get("death_penalty")
                or item["expected"]["term_of_imprisonment"].get("life_imprisonment")
                or int(item["expected"]["term_of_imprisonment"].get("imprisonment") or 0) >= 60
            ),
        ),
        (
            "多法条关联样本",
            lambda item: len(item["expected"]["relevant_articles"]) > 1,
        ),
    ]

    for reason, rule in scenario_rules:
        candidates = [case for case in cases if rule(case) and case["case_id"] not in used_ids]
        if not candidates:
            continue
        best = max(candidates, key=lambda item: item["selection_score"])
        used_ids.add(best["case_id"])
        selected.append(scenario_entry(best, reason))

    selected.sort(key=lambda item: item["selection_reason"])

    return {
        "summary": {
            "case_count": len(selected),
            "covered_model_charges": [
                charge
                for charge in model_charges
                if any(charge in case["expected"]["normalized_accusations"] for case in selected)
            ],
            "scenario_labels": [case["selection_reason"] for case in selected],
        },
        "cases": selected,
    }


def build_resources(input_paths: List[Path], label_mapping_path: Path, output_dir: Path) -> None:
    model_charges = load_model_charges(label_mapping_path)

    accusation_groups: Dict[str, GroupSummary] = {}
    article_groups: Dict[int, GroupSummary] = {}
    cases_for_tests: List[Dict[str, Any]] = []
    source_counter: Counter = Counter()
    total_samples = 0
    multi_label_samples = 0

    for item in iter_jsonl(input_paths):
        fact = item.get("fact", "")
        meta = item.get("meta", {})
        raw_accusations = unique_preserve_order(meta.get("accusation", []) or [])
        normalized_accusations = [normalize_charge_name(name) for name in raw_accusations]
        relevant_articles = unique_preserve_order(int(article) for article in meta.get("relevant_articles", []) or [])
        term = meta.get("term_of_imprisonment", {}) or {}
        punish_of_money = float(meta.get("punish_of_money", 0) or 0)
        finite_months = None if term.get("death_penalty") or term.get("life_imprisonment") else int(term.get("imprisonment") or 0)
        sample_score = quantize_score(
            length=len(fact),
            accusation_count=len(raw_accusations),
            article_count=len(relevant_articles),
            months=finite_months,
            fine=punish_of_money,
        )
        example = build_example_record(item, normalized_accusations, sample_score)

        total_samples += 1
        source_counter[item["_source_file"]] += 1
        if len(raw_accusations) > 1:
            multi_label_samples += 1

        for raw_name, normalized_name in zip(raw_accusations, normalized_accusations):
            group = accusation_groups.setdefault(
                raw_name,
                GroupSummary(
                    name=raw_name,
                    normalized_name=normalized_name,
                    current_model_supported=normalized_name in model_charges,
                ),
            )
            group.sample_count += 1
            group.related_counter.update(relevant_articles)
            group.co_occurrence_counter.update(
                other for other in normalized_accusations if other != normalized_name
            )
            group.add_term(term)
            group.add_fine(punish_of_money)
            group.maybe_add_example(example)

        for article in relevant_articles:
            group = article_groups.setdefault(
                article,
                GroupSummary(name=f"刑法第{article}条"),
            )
            group.sample_count += 1
            group.related_counter.update(normalized_accusations)
            group.co_occurrence_counter.update(
                f"刑法第{other}条" for other in relevant_articles if other != article
            )
            group.add_term(term)
            group.add_fine(punish_of_money)
            group.maybe_add_example(example)

        case_id = f"case-{len(cases_for_tests) + 1:05d}"
        cases_for_tests.append(
            {
                "case_id": case_id,
                "selection_score": sample_score,
                "representative_match_score": representative_match_score(fact, model_charges),
                "fact": fact,
                "source": {
                    "file": item["_source_file"],
                    "line_number": item["_line_number"],
                    "sample_id": example["sample_id"],
                },
                "tags": sample_tags(normalized_accusations, meta, fact),
                "expected": {
                    "raw_accusations": raw_accusations,
                    "normalized_accusations": normalized_accusations,
                    "relevant_articles": sorted(relevant_articles),
                    "term_of_imprisonment": term,
                    "punish_of_money": punish_of_money,
                },
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_files": [str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in input_paths],
        "source_sample_counts": dict(source_counter),
        "total_samples": total_samples,
        "multi_label_samples": multi_label_samples,
        "current_model_charges": model_charges,
        "notes": [
            "法条知识库当前只包含法条编号与统计信息，尚未包含法条全文。",
            "实体类型与关系类型为面向 Agent 工作流设计的抽取 schema，不是数据集自带标注。",
            "测试样本优先覆盖当前 10 类 BERT 罪名，同时补充多罪名、长文本和量刑压力样本。",
        ],
    }

    law_knowledge_base = {
        "metadata": metadata,
        "accusation_catalog": [
            accusation_groups[key].to_dict(
                top_key="top_relevant_articles",
                top_value_key="article_number",
                co_occurrence_key="co_occurring_accusations",
            )
            for key in sorted(
                accusation_groups,
                key=lambda name: (
                    0 if accusation_groups[name].current_model_supported else 1,
                    -accusation_groups[name].sample_count,
                    accusation_groups[name].normalized_name or name,
                ),
            )
        ],
        "article_catalog": [
            {
                **article_groups[article].to_dict(
                    top_key="top_accusations",
                    top_value_key="accusation",
                    co_occurrence_key="co_occurring_articles",
                ),
                "article_number": article,
            }
            for article in sorted(article_groups)
        ],
    }

    test_cases = {
        "metadata": metadata,
        **build_test_cases(cases_for_tests, model_charges),
    }

    write_json(output_dir / "entity_types.json", {"metadata": metadata, "entity_types": ENTITY_TYPES})
    write_json(output_dir / "relation_types.json", {"metadata": metadata, "relation_types": RELATION_TYPES})
    write_json(output_dir / "law_knowledge_base.json", law_knowledge_base)
    write_json(output_dir / "test_cases.json", test_cases)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建多 Agent 本地资源文件。")
    parser.add_argument(
        "--input",
        dest="inputs",
        action="append",
        help="指定输入 jsonl 文件，可重复传入；默认使用 exercise_contest 训练集和验证集。",
    )
    parser.add_argument(
        "--label-mapping",
        default=str(DEFAULT_LABEL_MAPPING),
        help="当前 BERT 标签映射文件路径。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="资源输出目录。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = [Path(path) for path in args.inputs] if args.inputs else list(DEFAULT_INPUTS)
    label_mapping_path = Path(args.label_mapping)
    output_dir = Path(args.output_dir)

    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(f"未找到输入文件：{path}")
    if not label_mapping_path.exists():
        raise FileNotFoundError(f"未找到标签映射文件：{label_mapping_path}")

    build_resources(input_paths, label_mapping_path, output_dir)
    print(f"资源构建完成，输出目录：{output_dir}")


if __name__ == "__main__":
    main()
