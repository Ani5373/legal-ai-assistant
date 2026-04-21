"""
Coordinator 与前后端共享的统一 JSON 契约。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


CONTRACT_VERSION = "case-analysis/v1"


def utc_now_iso() -> str:
    """统一输出 ISO 时间字符串。"""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class AnalysisRequest(BaseModel):
    """统一案件分析请求。"""

    text: str = Field(..., min_length=1, description="案情描述文本")
    case_id: Optional[str] = Field(default=None, description="可选的外部案件 ID")


class ChargePrediction(BaseModel):
    """BERT 罪名预测结果。"""

    label: str
    probability: float
    source: str = Field(default="bert_tool")
    rank: Optional[int] = None


class GraphNode(BaseModel):
    """统一图谱节点。"""

    id: str
    type: str
    label: str
    description: str = ""
    source: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """统一图谱关系边。"""

    id: str
    source: str
    target: str
    relation: str
    evidence: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionStep(BaseModel):
    """Coordinator 分步执行轨迹。"""

    id: str
    name: str
    agent: str
    status: Literal["completed", "failed", "skipped"] = "completed"
    started_at: str
    ended_at: str
    summary: str = ""
    output_keys: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class FactExtractionResult(BaseModel):
    """FactExtractorAgent 输出。"""

    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    summary: str = ""
    mode: str = Field(default="heuristic_fallback")


class ChargePredictionResult(BaseModel):
    """ChargePredictorAgent 输出。"""

    predictions: List[ChargePrediction] = Field(default_factory=list)
    summary: str = ""
    threshold: float = 0.5


class LawRetrievalResult(BaseModel):
    """LawRetrieverAgent 输出。"""

    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    matched_articles: List[int] = Field(default_factory=list)
    summary: str = ""


class ReportGenerationResult(BaseModel):
    """ReportGeneratorAgent 输出。"""

    report: str
    summary: str = ""


class CaseAnalysisResponse(BaseModel):
    """统一案件分析响应。"""

    contract_version: str = Field(default=CONTRACT_VERSION)
    case_id: str
    text: str
    predictions: List[ChargePrediction] = Field(default_factory=list)
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    steps: List[ExecutionStep] = Field(default_factory=list)
    report: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
