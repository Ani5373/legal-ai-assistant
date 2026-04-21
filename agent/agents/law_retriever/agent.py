"""
LawRetrieverAgent 主干版。
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Set

from agent.schemas.contracts import ChargePrediction, GraphEdge, GraphNode, LawRetrievalResult
from agent.tools.law_lookup.tool import LocalLawLookupTool


def stable_id(kind: str, label: str) -> str:
    digest = hashlib.md5(f"{kind}:{label}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}-{digest}"


def edge_id(source_id: str, relation: str, target_id: str) -> str:
    digest = hashlib.md5(f"{source_id}:{relation}:{target_id}".encode("utf-8")).hexdigest()[:12]
    return f"edge-{digest}"


class LawRetrieverAgent:
    """从本地 law knowledge base 补充法条与量刑参考节点。"""

    name = "LawRetrieverAgent"

    def __init__(self, law_lookup_tool: LocalLawLookupTool) -> None:
        self.law_lookup_tool = law_lookup_tool

    def run(self, case_id: str, predictions: List[ChargePrediction]) -> LawRetrievalResult:
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        matched_articles: Set[int] = set()
        case_node_id = case_id if case_id.startswith("case-") else f"case-{case_id}"

        for prediction in predictions:
            charge_node = GraphNode(
                id=stable_id("罪名", prediction.label),
                type="罪名",
                label=prediction.label,
                description=f"BERT 候选罪名，概率 {(prediction.probability * 100):.1f}%",
                source="charge_predictor",
                metadata={
                    "probability": prediction.probability,
                    "rank": prediction.rank,
                },
            )
            nodes[charge_node.id] = charge_node
            edges[edge_id(case_node_id, "指向罪名", charge_node.id)] = GraphEdge(
                id=edge_id(case_node_id, "指向罪名", charge_node.id),
                source=case_node_id,
                target=charge_node.id,
                relation="指向罪名",
                evidence="由 BERT 候选罪名与 Coordinator 编排结果生成",
            )

            article_entries = self.law_lookup_tool.top_articles_for_charge(prediction.label, limit=3)
            for item in article_entries:
                article_number = int(item["article_number"])
                matched_articles.add(article_number)
                article_node = GraphNode(
                    id=stable_id("法条", f"刑法第{article_number}条"),
                    type="法条",
                    label=f"刑法第{article_number}条",
                    description=f"本地知识库统计命中的常见法条编号（样本数 {item['count']}）",
                    source="law_knowledge_base",
                    metadata={
                        "article_number": article_number,
                        "sample_count": item["count"],
                    },
                )
                nodes[article_node.id] = article_node
                edges[edge_id(charge_node.id, "对应法条", article_node.id)] = GraphEdge(
                    id=edge_id(charge_node.id, "对应法条", article_node.id),
                    source=charge_node.id,
                    target=article_node.id,
                    relation="对应法条",
                    evidence="由本地法条知识库匹配候选罪名得到",
                )

            sentencing_summary = self.law_lookup_tool.sentencing_summary_for_charge(prediction.label)
            if sentencing_summary:
                rule_node = GraphNode(
                    id=stable_id("量刑规则", f"{prediction.label}-量刑参考"),
                    type="量刑规则",
                    label=f"{prediction.label}量刑参考",
                    description=sentencing_summary["label"],
                    source="law_knowledge_base",
                    metadata=sentencing_summary["details"],
                )
                nodes[rule_node.id] = rule_node
                edges[edge_id(charge_node.id, "约束量刑", rule_node.id)] = GraphEdge(
                    id=edge_id(charge_node.id, "约束量刑", rule_node.id),
                    source=charge_node.id,
                    target=rule_node.id,
                    relation="约束量刑",
                    evidence="由本地知识库的统计型量刑摘要生成",
                )

        summary = (
            f"已为 {len(predictions)} 个候选罪名补充 {len(matched_articles)} 个法条编号"
            f" 和 {len([node for node in nodes.values() if node.type == '量刑规则'])} 个量刑参考节点。"
        )
        return LawRetrievalResult(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            matched_articles=sorted(matched_articles),
            summary=summary,
        )
