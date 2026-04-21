"""
ReportGeneratorAgent - 基于本地 Ollama qwen25chat:latest 的报告生成与自审版本。

使用本地大模型进行专业报告生成、润色和自我审查。
直接使用 Ollama，不再提供降级机制。
"""

from __future__ import annotations

import logging
from typing import List, Optional

from agent.schemas.contracts import ChargePrediction, GraphNode, ReportGenerationResult
from agent.tools.ollama.client import OllamaClient
from agent.memory.core.result_cache import ResultCache

logger = logging.getLogger(__name__)


class ReportGeneratorAgent:
    """
    基于本地 Ollama qwen25chat:latest 的报告生成 Agent。

    使用本地大模型进行专业报告生成和自审。
    """

    name = "ReportGeneratorAgent"

    def __init__(self, ollama_client: Optional[OllamaClient] = None, enable_cache: bool = True) -> None:
        """
        初始化 ReportGeneratorAgent。

        Args:
            ollama_client: Ollama 客户端实例（可选，默认创建新实例）
            enable_cache: 是否启用缓存
        """
        self.ollama_client = ollama_client or OllamaClient()
        self.enable_cache = enable_cache
        self.cache = ResultCache() if enable_cache else None

    def run(
        self,
        text: str,
        predictions: List[ChargePrediction],
        nodes: List[GraphNode],
    ) -> ReportGenerationResult:
        """
        执行报告生成（带缓存）。

        使用 Ollama 进行专业报告生成和按需自审。

        Args:
            text: 原始案情文本
            predictions: 罪名预测结果
            nodes: 图谱节点列表

        Returns:
            报告生成结果
        """
        # 尝试从缓存获取
        if self.enable_cache and self.cache:
            cached = self.cache.get_report_generation(text, predictions, nodes)
            if cached:
                return ReportGenerationResult(
                    report=cached["report"],
                    summary=cached["summary"] + "（来自缓存）",
                )
        
        # 生成新报告
        result = self._generate_with_ollama(text, predictions, nodes)
        
        # 存入缓存
        if self.enable_cache and self.cache:
            self.cache.set_report_generation(
                text=text,
                predictions=predictions,
                nodes=nodes,
                report=result.report,
                summary=result.summary,
            )
        
        return result

    def _generate_with_ollama(
        self,
        text: str,
        predictions: List[ChargePrediction],
        nodes: List[GraphNode],
    ) -> ReportGenerationResult:
        """使用 Ollama 生成专业报告，按需进行二次自审。"""
        # 第一步：生成报告
        draft_report = self._generate_draft_report(text, predictions, nodes)

        # 第二步：检查是否需要二次自审
        needs_review = self._check_if_needs_review(draft_report, predictions)
        
        if needs_review:
            # 触发二次自审
            final_report = self._review_and_polish(draft_report, text, predictions)
            summary = "使用 Ollama 生成专业分析报告并完成自审（触发二次审查）。"
        else:
            # 直接使用初稿
            final_report = draft_report
            summary = "使用 Ollama 生成专业分析报告。"

        return ReportGenerationResult(
            report=final_report,
            summary=summary,
        )

    def _check_if_needs_review(
        self,
        report: str,
        predictions: List[ChargePrediction],
    ) -> bool:
        """
        检查报告是否需要二次自审
        
        触发条件：
        1. 报告为空或过短
        2. 缺少核心章节
        3. 没有引用候选罪名
        4. 结构严重异常
        
        Returns:
            True 表示需要二次自审
        """
        # 检查1：报告为空或过短（少于200字）
        if not report or len(report.strip()) < 200:
            return True
        
        # 检查2：缺少核心章节关键词
        required_sections = ["案情", "事实", "罪名", "法律"]
        missing_sections = sum(1 for section in required_sections if section not in report)
        if missing_sections >= 2:  # 缺少2个或以上核心章节
            return True
        
        # 检查3：没有引用任何候选罪名
        if predictions:
            top_charges = [p.label for p in predictions[:3]]
            has_charge_reference = any(charge in report for charge in top_charges)
            if not has_charge_reference:
                return True
        
        # 检查4：结构异常（没有任何标点符号或换行）
        if "。" not in report and "，" not in report and "\n" not in report:
            return True
        
        # 检查5：报告过长但没有分段（可能是格式问题）
        if len(report) > 1000 and report.count("\n") < 3:
            return True
        
        # 通过所有检查，不需要二次自审
        return False

    def _generate_draft_report(
        self,
        text: str,
        predictions: List[ChargePrediction],
        nodes: List[GraphNode],
    ) -> str:
        """生成初步报告（使用压缩的输入）。"""
        # 压缩输入：提取关键信息摘要
        report_input = self._build_compressed_input(text, predictions, nodes)
        
        # 构建系统提示词
        system_prompt = """你是一位专业的法律分析专家，擅长撰写案件分析报告。
你的报告应当：
1. 结构清晰，逻辑严密
2. 语言专业，表述准确
3. 基于事实，客观中立
4. 包含案情摘要、事实认定、罪名分析、法律依据、量刑建议等部分
5. 使用规范的法律术语"""

        # 构建用户提示词
        user_prompt = f"""请根据以下信息生成一份专业的案件分析报告：

{report_input}

请生成一份结构完整、专业规范的案件分析报告。"""

        draft = self.ollama_client.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.5,
            max_tokens=1536,  # 从2048降到1536，减少生成时间
        )
        return draft

    def _build_compressed_input(
        self,
        text: str,
        predictions: List[ChargePrediction],
        nodes: List[GraphNode],
    ) -> str:
        """
        构建压缩的报告输入摘要
        
        只保留关键信息，不传全量大 JSON
        """
        lines = []
        
        # 1. 原始案情（限制长度）
        lines.append("原始案情：")
        lines.append(text[:500] + ('...' if len(text) > 500 else ''))
        lines.append("")
        
        # 2. 罪名预测结果
        if predictions:
            lines.append("罪名预测结果：")
            for pred in predictions[:3]:  # 只取Top3
                lines.append(f"- {pred.label}（概率{pred.probability * 100:.1f}%）")
            lines.append("")
        
        # 3. 关键实体摘要（按类型分组）
        key_entity_types = ["人物", "受害人", "行为", "时间", "地点", "金额", "伤情", "证据"]
        entity_summary = {}
        
        for node in nodes:
            if node.type in key_entity_types:
                if node.type not in entity_summary:
                    entity_summary[node.type] = []
                entity_summary[node.type].append(node.label)
        
        if entity_summary:
            lines.append("抽取的关键要素：")
            for entity_type in key_entity_types:
                if entity_type in entity_summary:
                    labels = entity_summary[entity_type][:5]  # 每类最多5个
                    lines.append(f"- {entity_type}：{' '.join(labels)}")
            lines.append("")
        
        # 4. 法条和量刑摘要
        law_nodes = [n for n in nodes if n.type in ["法条", "量刑规则"]]
        if law_nodes:
            lines.append("法律依据：")
            for node in law_nodes[:5]:  # 最多5条
                lines.append(f"- {node.label}")
            lines.append("")
        
        return "\n".join(lines)

    def _review_and_polish(
        self,
        draft_report: str,
        text: str,
        predictions: List[ChargePrediction],
    ) -> str:
        """对报告进行自审和润色。"""
        system_prompt = """你是一位资深的法律审查专家，负责审查和完善案件分析报告。
你需要检查：
1. 事实表述是否准确，有无与原文矛盾
2. 法律术语使用是否规范
3. 逻辑推理是否严密
4. 结论是否客观中立
5. 格式是否规范

请对报告进行必要的修改和完善，确保其专业性和准确性。"""

        user_prompt = f"""请审查以下案件分析报告，并进行必要的修改和完善：

原始案情（用于核对事实）：
{text[:300]}{'...' if len(text) > 300 else ''}

待审查的报告：
{draft_report}

请输出修改后的最终报告。如果原报告已经很好，可以保持不变或仅做微调。"""

        final = self.ollama_client.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=2048,
        )
        return final

    def _generate_with_template(
        self,
        text: str,
        predictions: List[ChargePrediction],
        nodes: List[GraphNode],
    ) -> ReportGenerationResult:
        """模板化报告生成（备用方案，已不再使用）。"""
        people = self._collect_labels(nodes, "人物")
        victims = self._collect_labels(nodes, "受害人")
        actions = self._collect_labels(nodes, "行为")
        places = self._collect_labels(nodes, "地点")
        times = self._collect_labels(nodes, "时间")
        articles = self._collect_labels(nodes, "法条")
        sentencing = self._collect_labels(nodes, "量刑规则")

        top_predictions = "、".join(
            f"{item.label}({item.probability * 100:.1f}%)"
            for item in predictions[:3]
        ) or "暂无明确候选罪名"

        report_lines = [
            "本次案件分析由 Coordinator 主干版串行调用事实抽取、罪名预测、法条检索与报告生成模块完成。",
            f"案情摘要：输入文本长度约 {len(text)} 字，已抽取的人物要素包括 {people or '未识别'}；"
            f"受害对象包括 {victims or '未识别'}；关键行为包括 {actions or '未识别'}。",
            f"时空线索：时间要素为 {times or '未识别'}，地点要素为 {places or '未识别'}。",
            f"候选罪名判断：当前 BERT 输出的主要候选罪名为 {top_predictions}。",
            f"法条与量刑参考：已补充法条节点 {articles or '暂无'}；量刑参考为 {sentencing or '暂无'}。",
            "说明：当前报告为 Coordinator 主干版输出，事实抽取与报告生成仍采用骨架实现，"
            "后续会继续接入本地 Ollama 完成更高质量的实体关系抽取、专业报告润色与自审。",
        ]
        report = "\n".join(report_lines)
        return ReportGenerationResult(
            report=report,
            summary="已生成主干版分析报告。",
        )

    @staticmethod
    def _collect_labels(nodes: List[GraphNode], node_type: str, limit: int = 5) -> str:
        labels = [node.label for node in nodes if node.type == node_type]
        unique_labels: List[str] = []
        for label in labels:
            if label not in unique_labels:
                unique_labels.append(label)
        return "、".join(unique_labels[:limit])
