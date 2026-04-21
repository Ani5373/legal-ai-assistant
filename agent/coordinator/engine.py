"""
Coordinator 主干版实现。
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from agent.memory.core import MemoryManager
from agent.security.core import SecurityManager
from agent.schemas.contracts import (
    CaseAnalysisResponse,
    ChargePrediction,
    ExecutionStep,
    GraphEdge,
    GraphNode,
    utc_now_iso,
)


class CaseAnalysisCoordinator:
    """
    多 Agent 主干编排器。

    当前阶段职责：
    1. 串行调度 FactExtractor / ChargePredictor / LawRetriever / ReportGenerator
    2. 输出统一 JSON 契约
    3. 集成三层智能内存系统
    4. 集成三阶段安全检查系统
    """

    def __init__(
        self,
        fact_extractor,
        charge_predictor,
        law_retriever,
        report_generator,
        memory_manager: Optional[MemoryManager] = None,
        security_manager: Optional[SecurityManager] = None,
        enable_memory_cache: bool = True,
        enable_security_check: bool = True,
        version: str = "coordinator/v0.3",
    ) -> None:
        self.fact_extractor = fact_extractor
        self.charge_predictor = charge_predictor
        self.law_retriever = law_retriever
        self.report_generator = report_generator
        self.version = version
        self.enable_memory_cache = enable_memory_cache
        self.enable_security_check = enable_security_check
        self.memory = memory_manager or MemoryManager()
        self.security = security_manager or SecurityManager()

    async def analyze_stream(self, text: str, case_id: str | None = None):
        """流式分析，分阶段返回结果"""
        resolved_case_id = case_id or f"case-{uuid.uuid4().hex[:12]}"
        warnings: List[str] = []
        
        # 安全检查
        if self.enable_security_check:
            security_result = self.security.check(resolved_case_id, text, "analyze")
            if not security_result.passed:
                yield {
                    "type": "error",
                    "message": f"安全检查未通过：{security_result.reason}",
                    "risk_level": security_result.risk_level,
                }
                return
            
            if security_result.suggestions:
                warnings.extend(security_result.suggestions)
        
        # 尝试从内存中检索
        if self.enable_memory_cache:
            cached = self.memory.search_by_text(text)
            if cached:
                yield {
                    "type": "complete",
                    "data": {
                        "case_id": cached.case_id,
                        "text": cached.text,
                        "predictions": [p.model_dump() for p in cached.predictions],
                        "nodes": [n.model_dump() for n in cached.nodes],
                        "edges": [e.model_dump() for e in cached.edges],
                        "steps": [],
                        "report": cached.report,
                        "metadata": {**cached.metadata, "from_cache": True},
                        "warnings": ["结果来自内存缓存"] + warnings,
                    }
                }
                return
        
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        predictions: List[ChargePrediction] = []
        steps: List[ExecutionStep] = []
        
        # 阶段1：事实抽取
        yield {"type": "stage", "stage": "fact_extraction", "message": "正在抽取案件事实..."}
        
        fact_result = self._run_step(
            steps=steps,
            name="事实抽取",
            agent_name=self.fact_extractor.name,
            runner=lambda: self.fact_extractor.run(resolved_case_id, text),
            output_keys=["nodes", "edges", "summary", "mode"],
            warnings=warnings,
        )
        
        if fact_result:
            self._merge_nodes(nodes, fact_result.nodes)
            self._merge_edges(edges, fact_result.edges)
        else:
            self._ensure_case_node(nodes, resolved_case_id)
        
        # 发送事实抽取结果
        yield {
            "type": "fact_extraction_complete",
            "data": {
                "nodes": [n.model_dump() for n in nodes.values()],
                "edges": [e.model_dump() for e in edges.values()],
                "summary": fact_result.summary if fact_result else "事实抽取失败",
            }
        }
        
        # 阶段2：罪名预测
        yield {"type": "stage", "stage": "charge_prediction", "message": "正在预测罪名..."}
        
        prediction_result = self._run_step(
            steps=steps,
            name="罪名预测",
            agent_name=self.charge_predictor.name,
            runner=lambda: self.charge_predictor.run(text),
            output_keys=["predictions", "summary", "threshold"],
            warnings=warnings,
        )
        
        if prediction_result:
            predictions = prediction_result.predictions
        
        yield {
            "type": "charge_prediction_complete",
            "data": {
                "predictions": [p.model_dump() for p in predictions],
            }
        }
        
        # 阶段3：法条检索
        yield {"type": "stage", "stage": "law_retrieval", "message": "正在检索相关法条..."}
        
        law_result = self._run_step(
            steps=steps,
            name="法条检索",
            agent_name=self.law_retriever.name,
            runner=lambda: self.law_retriever.run(resolved_case_id, predictions),
            output_keys=["nodes", "edges", "matched_articles", "summary"],
            warnings=warnings,
        )
        
        if law_result:
            self._merge_nodes(nodes, law_result.nodes)
            self._merge_edges(edges, law_result.edges)
        
        yield {
            "type": "law_retrieval_complete",
            "data": {
                "nodes": [n.model_dump() for n in nodes.values()],
                "edges": [e.model_dump() for e in edges.values()],
            }
        }
        
        # 阶段4：报告生成（流式）
        yield {"type": "stage", "stage": "report_generation", "message": "正在生成分析报告..."}
        
        report_result = self._run_step(
            steps=steps,
            name="报告生成",
            agent_name=self.report_generator.name,
            runner=lambda: self.report_generator.run(
                text=text,
                predictions=predictions,
                nodes=list(nodes.values()),
            ),
            output_keys=["report", "summary"],
            warnings=warnings,
        )
        
        report = report_result.report if report_result else "当前未成功生成案件分析报告。"
        
        # 发送完整结果
        metadata = {
            "coordinator_version": self.version,
            "fact_extractor_mode": fact_result.mode if fact_result else "unknown",
            "graph_summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "prediction_count": len(predictions),
            },
        }
        
        if self.enable_security_check:
            metadata["security_check"] = {
                "passed": True,
                "risk_level": security_result.risk_level,
                "stage": security_result.stage,
            }
        
        response = CaseAnalysisResponse(
            case_id=resolved_case_id,
            text=text,
            predictions=predictions,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            steps=steps,
            report=report,
            metadata=metadata,
            warnings=warnings,
        )
        
        # 存储到内存
        if self.enable_memory_cache:
            try:
                self.memory.store(response)
            except Exception as exc:
                warnings.append(f"内存存储失败：{exc}")
        
        yield {
            "type": "complete",
            "data": response.model_dump(),
        }

    def analyze(self, text: str, case_id: str | None = None) -> CaseAnalysisResponse:
        resolved_case_id = case_id or f"case-{uuid.uuid4().hex[:12]}"
        warnings: List[str] = []
        
        # 安全检查
        if self.enable_security_check:
            security_result = self.security.check(resolved_case_id, text, "analyze")
            if not security_result.passed:
                # 安全检查未通过，返回错误响应
                return CaseAnalysisResponse(
                    case_id=resolved_case_id,
                    text=text,
                    predictions=[],
                    nodes=[],
                    edges=[],
                    steps=[],
                    report=f"安全检查未通过：{security_result.reason}",
                    metadata={
                        "coordinator_version": self.version,
                        "security_check": {
                            "passed": False,
                            "risk_level": security_result.risk_level,
                            "stage": security_result.stage,
                            "reason": security_result.reason,
                        },
                    },
                    warnings=[security_result.reason] + security_result.suggestions,
                )
            
            # 记录安全检查结果
            if security_result.suggestions:
                warnings.extend(security_result.suggestions)
        
        # 尝试从内存中检索
        if self.enable_memory_cache:
            cached = self.memory.search_by_text(text)
            if cached:
                # 从缓存重建响应
                response = CaseAnalysisResponse(
                    case_id=cached.case_id,
                    text=cached.text,
                    predictions=cached.predictions,
                    nodes=cached.nodes,
                    edges=cached.edges,
                    steps=[],
                    report=cached.report,
                    metadata={
                        **cached.metadata,
                        "from_cache": True,
                        "coordinator_version": self.version,
                    },
                    warnings=["结果来自内存缓存"] + warnings,
                )
                return response
        
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        predictions: List[ChargePrediction] = []
        steps: List[ExecutionStep] = []
        fact_mode = "unknown"

        fact_result = self._run_step(
            steps=steps,
            name="事实抽取",
            agent_name=self.fact_extractor.name,
            runner=lambda: self.fact_extractor.run(resolved_case_id, text),
            output_keys=["nodes", "edges", "summary", "mode"],
            warnings=warnings,
        )
        if fact_result:
            fact_mode = fact_result.mode
            self._merge_nodes(nodes, fact_result.nodes)
            self._merge_edges(edges, fact_result.edges)
        else:
            self._ensure_case_node(nodes, resolved_case_id)

        prediction_result = self._run_step(
            steps=steps,
            name="罪名预测",
            agent_name=self.charge_predictor.name,
            runner=lambda: self.charge_predictor.run(text),
            output_keys=["predictions", "summary", "threshold"],
            warnings=warnings,
        )
        if prediction_result:
            predictions = prediction_result.predictions

        law_result = self._run_step(
            steps=steps,
            name="法条检索",
            agent_name=self.law_retriever.name,
            runner=lambda: self.law_retriever.run(resolved_case_id, predictions),
            output_keys=["nodes", "edges", "matched_articles", "summary"],
            warnings=warnings,
        )
        if law_result:
            self._merge_nodes(nodes, law_result.nodes)
            self._merge_edges(edges, law_result.edges)

        report_result = self._run_step(
            steps=steps,
            name="报告生成",
            agent_name=self.report_generator.name,
            runner=lambda: self.report_generator.run(
                text=text,
                predictions=predictions,
                nodes=list(nodes.values()),
            ),
            output_keys=["report", "summary"],
            warnings=warnings,
        )
        report = report_result.report if report_result else "当前未成功生成案件分析报告。"

        node_list = list(nodes.values())
        edge_list = list(edges.values())

        metadata = {
            "coordinator_version": self.version,
            "fact_extractor_mode": fact_mode,
            "graph_summary": {
                "node_count": len(node_list),
                "edge_count": len(edge_list),
                "prediction_count": len(predictions),
            },
        }
        
        # 添加安全检查信息
        if self.enable_security_check:
            metadata["security_check"] = {
                "passed": True,
                "risk_level": security_result.risk_level,
                "stage": security_result.stage,
            }

        response = CaseAnalysisResponse(
            case_id=resolved_case_id,
            text=text,
            predictions=predictions,
            nodes=node_list,
            edges=edge_list,
            steps=steps,
            report=report,
            metadata=metadata,
            warnings=warnings,
        )
        
        # 存储到内存系统
        if self.enable_memory_cache:
            try:
                self.memory.store(response)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"内存存储失败：{exc}")
        
        return response

    async def analyze_stream(self, text: str, case_id: str | None = None):
        """
        流式分析，逐步返回中间结果
        
        Args:
            text: 案情文本
            case_id: 案件ID
            
        Yields:
            分析过程中的各个阶段数据
        """
        resolved_case_id = case_id or f"case-{uuid.uuid4().hex[:12]}"
        warnings: List[str] = []
        
        # 安全检查
        if self.enable_security_check:
            security_result = self.security.check(resolved_case_id, text, "analyze")
            if not security_result.passed:
                yield {
                    "type": "error",
                    "message": f"安全检查未通过：{security_result.reason}",
                    "case_id": resolved_case_id,
                    "risk_level": security_result.risk_level,
                }
                return
            
            if security_result.suggestions:
                warnings.extend(security_result.suggestions)
        
        # 尝试从内存中检索
        if self.enable_memory_cache:
            cached = self.memory.search_by_text(text)
            if cached:
                yield {
                    "type": "complete",
                    "data": {
                        "case_id": cached.case_id,
                        "text": cached.text,
                        "predictions": [p.model_dump() for p in cached.predictions],
                        "nodes": [n.model_dump() for n in cached.nodes],
                        "edges": [e.model_dump() for e in cached.edges],
                        "steps": [],
                        "report": cached.report,
                        "metadata": {
                            **cached.metadata,
                            "from_cache": True,
                            "coordinator_version": self.version,
                        },
                        "warnings": ["结果来自内存缓存"] + warnings,
                    }
                }
                return
        
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        predictions: List[ChargePrediction] = []
        steps: List[ExecutionStep] = []
        fact_mode = "unknown"

        # 阶段1：事实抽取
        yield {"type": "stage", "stage": "fact_extraction", "message": "正在抽取案件事实..."}
        
        fact_result = self._run_step(
            steps=steps,
            name="事实抽取",
            agent_name=self.fact_extractor.name,
            runner=lambda: self.fact_extractor.run(resolved_case_id, text),
            output_keys=["nodes", "edges", "summary", "mode"],
            warnings=warnings,
        )
        if fact_result:
            fact_mode = fact_result.mode
            self._merge_nodes(nodes, fact_result.nodes)
            self._merge_edges(edges, fact_result.edges)
        else:
            self._ensure_case_node(nodes, resolved_case_id)
        
        # 事实抽取完成，返回中间结果
        yield {
            "type": "fact_extraction_complete",
            "data": {
                "nodes": [n.model_dump() for n in nodes.values()],
                "edges": [e.model_dump() for e in edges.values()],
                "steps": [s.model_dump() for s in steps],
            }
        }

        # 阶段2：罪名预测
        yield {"type": "stage", "stage": "charge_prediction", "message": "正在预测罪名..."}
        
        prediction_result = self._run_step(
            steps=steps,
            name="罪名预测",
            agent_name=self.charge_predictor.name,
            runner=lambda: self.charge_predictor.run(text),
            output_keys=["predictions", "summary", "threshold"],
            warnings=warnings,
        )
        if prediction_result:
            predictions = prediction_result.predictions
        
        yield {
            "type": "charge_prediction_complete",
            "data": {
                "predictions": [p.model_dump() for p in predictions],
                "steps": [s.model_dump() for s in steps],
            }
        }

        # 阶段3：法条检索
        yield {"type": "stage", "stage": "law_retrieval", "message": "正在检索相关法条..."}
        
        law_result = self._run_step(
            steps=steps,
            name="法条检索",
            agent_name=self.law_retriever.name,
            runner=lambda: self.law_retriever.run(resolved_case_id, predictions),
            output_keys=["nodes", "edges", "matched_articles", "summary"],
            warnings=warnings,
        )
        if law_result:
            self._merge_nodes(nodes, law_result.nodes)
            self._merge_edges(edges, law_result.edges)
        
        yield {
            "type": "law_retrieval_complete",
            "data": {
                "nodes": [n.model_dump() for n in nodes.values()],
                "edges": [e.model_dump() for e in edges.values()],
                "steps": [s.model_dump() for s in steps],
            }
        }

        # 阶段4：报告生成
        yield {"type": "stage", "stage": "report_generation", "message": "正在生成分析报告..."}
        
        report_result = self._run_step(
            steps=steps,
            name="报告生成",
            agent_name=self.report_generator.name,
            runner=lambda: self.report_generator.run(
                text=text,
                predictions=predictions,
                nodes=list(nodes.values()),
            ),
            output_keys=["report", "summary"],
            warnings=warnings,
        )
        report = report_result.report if report_result else "当前未成功生成案件分析报告。"

        node_list = list(nodes.values())
        edge_list = list(edges.values())

        metadata = {
            "coordinator_version": self.version,
            "fact_extractor_mode": fact_mode,
            "graph_summary": {
                "node_count": len(node_list),
                "edge_count": len(edge_list),
                "prediction_count": len(predictions),
            },
        }
        
        if self.enable_security_check:
            metadata["security_check"] = {
                "passed": True,
                "risk_level": security_result.risk_level,
                "stage": security_result.stage,
            }

        response = CaseAnalysisResponse(
            case_id=resolved_case_id,
            text=text,
            predictions=predictions,
            nodes=node_list,
            edges=edge_list,
            steps=steps,
            report=report,
            metadata=metadata,
            warnings=warnings,
        )
        
        # 存储到内存系统
        if self.enable_memory_cache:
            try:
                self.memory.store(response)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"内存存储失败：{exc}")
        
        # 返回最终完整结果
        yield {
            "type": "complete",
            "data": response.model_dump()
        }

    @staticmethod
    def _merge_nodes(container: Dict[str, GraphNode], incoming: List[GraphNode]) -> None:
        for node in incoming:
            container[node.id] = node

    @staticmethod
    def _merge_edges(container: Dict[str, GraphEdge], incoming: List[GraphEdge]) -> None:
        for edge in incoming:
            container[edge.id] = edge

    @staticmethod
    def _ensure_case_node(container: Dict[str, GraphNode], case_id: str) -> None:
        node_id = case_id if case_id.startswith("case-") else f"case-{case_id}"
        if node_id not in container:
            container[node_id] = GraphNode(
                id=node_id,
                type="案件",
                label=f"案件 {case_id}",
                description="Coordinator 默认创建的案件根节点",
                source="coordinator",
            )

    @staticmethod
    def _run_step(steps, name, agent_name, runner, output_keys, warnings):
        started_at = utc_now_iso()
        try:
            result = runner()
            steps.append(
                ExecutionStep(
                    id=f"step-{len(steps) + 1}",
                    name=name,
                    agent=agent_name,
                    status="completed",
                    started_at=started_at,
                    ended_at=utc_now_iso(),
                    summary=getattr(result, "summary", ""),
                    output_keys=output_keys,
                    details={},
                )
            )
            return result
        except Exception as exc:  # noqa: BLE001 - 主干期需要把失败写入 steps 而不是直接中断
            warnings.append(f"{agent_name} 执行失败：{exc}")
            steps.append(
                ExecutionStep(
                    id=f"step-{len(steps) + 1}",
                    name=name,
                    agent=agent_name,
                    status="failed",
                    started_at=started_at,
                    ended_at=utc_now_iso(),
                    summary=f"{agent_name} 执行失败，已记录 warning。",
                    output_keys=[],
                    details={"error": str(exc)},
                )
            )
            return None
