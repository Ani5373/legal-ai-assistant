"""
本地法条知识库检索 Tool。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def normalize_charge_name(name: str) -> str:
    return name.replace("[", "").replace("]", "").strip()


class LocalLawLookupTool:
    """
    读取 `agent/资源/law_knowledge_base.json`，
    为 LawRetrieverAgent 提供罪名与法条的本地索引能力。
    """

    def __init__(self, knowledge_base_path: Path) -> None:
        self.knowledge_base_path = knowledge_base_path
        with knowledge_base_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        self.metadata = payload.get("metadata", {})
        self.accusation_catalog = {
            normalize_charge_name(item.get("normalized_name") or item["name"]): item
            for item in payload.get("accusation_catalog", [])
        }
        self.article_catalog = {
            int(item["article_number"]): item
            for item in payload.get("article_catalog", [])
        }

    def lookup_charge(self, label: str) -> Optional[Dict[str, Any]]:
        return self.accusation_catalog.get(normalize_charge_name(label))

    def lookup_article(self, article_number: int) -> Optional[Dict[str, Any]]:
        return self.article_catalog.get(int(article_number))

    def top_articles_for_charge(self, label: str, limit: int = 3) -> List[Dict[str, Any]]:
        record = self.lookup_charge(label)
        if not record:
            return []

        articles: List[Dict[str, Any]] = []
        for item in record.get("top_relevant_articles", [])[:limit]:
            article_number = int(item["article_number"])
            articles.append(
                {
                    "article_number": article_number,
                    "count": int(item.get("count", 0)),
                    "article_record": self.lookup_article(article_number),
                }
            )
        return articles

    def sentencing_summary_for_charge(self, label: str) -> Optional[Dict[str, Any]]:
        record = self.lookup_charge(label)
        if not record:
            return None

        imprisonment = record.get("imprisonment_summary", {})
        fine = record.get("fine_summary", {})
        parts: List[str] = []

        average_months = imprisonment.get("average_months")
        if average_months is not None:
            min_months = imprisonment.get("min_months")
            max_months = imprisonment.get("max_months")
            parts.append(
                f"常见有限刑期均值约 {average_months} 月，区间 {min_months} - {max_months} 月"
            )

        average_amount = fine.get("average_amount")
        if average_amount is not None:
            min_amount = fine.get("min_amount")
            max_amount = fine.get("max_amount")
            parts.append(
                f"罚金均值约 {average_amount} 元，区间 {min_amount} - {max_amount} 元"
            )

        if not parts:
            return None

        return {
            "label": "；".join(parts),
            "details": {
                "imprisonment_summary": imprisonment,
                "fine_summary": fine,
            },
        }
