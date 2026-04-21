"""
FactExtractorAgent - 混合方案A：UIE实体抽取 + Qwen关系抽取

使用 UIE 进行快速实体抽取，使用 Qwen 进行关系抽取，兼顾速度和质量。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from agent.schemas.contracts import FactExtractionResult, GraphEdge, GraphNode
from agent.tools.ollama.client import OllamaClient
from agent.memory.core.result_cache import ResultCache

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESOURCE_DIR = PROJECT_ROOT / "agent" / "资源"

# 尝试导入 PaddleNLP
try:
    from paddlenlp import Taskflow
    PADDLENLP_AVAILABLE = True
except ImportError:
    PADDLENLP_AVAILABLE = False
    logger.warning("PaddleNLP 未安装，将使用 Ollama 进行实体抽取（较慢）")


TIME_PATTERN = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日(?:[上下中晚早]午)?(?:\d{1,2}时(?:许|左右)?|[上下中晚早]午)?")
AMOUNT_PATTERN = re.compile(r"(?:人民币)?\d+(?:\.\d+)?元")
INJURY_PATTERN = re.compile(r"(轻伤一级|轻伤二级|重伤一级|重伤二级|骨折|死亡|创伤性休克)")
EVIDENCE_PATTERN = re.compile(r"(经鉴定|司法鉴定|证人证言|现场勘验|被告人供述|检验报告|检测报告)")
ROLE_PATTERNS: List[Tuple[str, str, re.Pattern[str]]] = [
    ("人物", "被告人", re.compile(r"被告人([\u4e00-\u9fa5A-Za-z0-9某×]{1,12})")),
    ("受害人", "被害人", re.compile(r"被害人([\u4e00-\u9fa5A-Za-z0-9某×]{1,12})")),
    ("人物", "证人", re.compile(r"证人([\u4e00-\u9fa5A-Za-z0-9某×]{1,12})")),
]
PLACE_PATTERNS = [
    re.compile(r"在([^，。；]{2,30}(?:路|街|镇|村|店|公司|室|县|区|市|宾馆|房间|饭店|酒吧))"),
]
ACTION_KEYWORDS = [
    "盗窃",
    "抢劫",
    "诈骗",
    "故意伤害",
    "殴打",
    "打伤",
    "醉酒驾驶",
    "酒后驾驶",
    "交通肇事",
    "撞倒",
    "逃逸",
    "容留吸毒",
    "容留他人吸毒",
    "吸食毒品",
    "贩卖毒品",
    "运输毒品",
    "制造毒品",
    "寻衅滋事",
]


def stable_id(kind: str, label: str) -> str:
    digest = hashlib.md5(f"{kind}:{label}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}-{digest}"


def edge_id(source_id: str, relation: str, target_id: str) -> str:
    digest = hashlib.md5(f"{source_id}:{relation}:{target_id}".encode("utf-8")).hexdigest()[:12]
    return f"edge-{digest}"


def unique_preserve_order(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


class FactExtractorAgent:
    """
    混合方案A：UIE实体抽取 + Qwen关系抽取
    
    使用 UIE 进行快速实体抽取（~2.5秒），使用 Qwen 进行关系抽取（~3秒），
    总耗时约5.5秒，比纯 Qwen 方案快6倍。
    """

    name = "FactExtractorAgent"

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        entity_types_path: Optional[str] = None,
        relation_types_path: Optional[str] = None,
        enable_cache: bool = True,
        use_uie: bool = True,  # 新增：是否使用 UIE
    ) -> None:
        """
        初始化 FactExtractorAgent。

        Args:
            ollama_client: Ollama 客户端实例（可选，默认创建新实例）
            entity_types_path: 实体类型配置文件路径
            relation_types_path: 关系类型配置文件路径
            enable_cache: 是否启用缓存
            use_uie: 是否使用 UIE 进行实体抽取（默认True，更快）
        """
        self.ollama_client = ollama_client or OllamaClient()
        self.entity_types = self._load_entity_types(entity_types_path)
        self.relation_types = self._load_relation_types(relation_types_path)
        self.enable_cache = enable_cache
        self.cache = ResultCache() if enable_cache else None
        self.use_uie = use_uie and PADDLENLP_AVAILABLE
        
        # 初始化 UIE 模型（如果可用）
        self.uie_model = None
        if self.use_uie:
            try:
                logger.info("正在加载 UIE 模型...")
                self.uie_model = Taskflow(
                    task="information_extraction",
                    model="uie-base",
                    mode="dynamic",
                    schema=["人物", "受害人", "时间", "地点", "金额", "伤情", "证据", "行为", "物品", "组织机构", "罪名"]
                )
                logger.info("✓ UIE 模型加载完成")
            except Exception as e:
                logger.warning(f"UIE 模型加载失败: {e}，将使用 Ollama 进行实体抽取")
                self.use_uie = False
                self.uie_model = None

    def _load_entity_types(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """加载实体类型配置。"""
        resolved_path = Path(path) if path is not None else RESOURCE_DIR / "entity_types.json"
        if not resolved_path.is_absolute():
            resolved_path = PROJECT_ROOT / resolved_path
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("entity_types", [])
        except Exception as e:
            logger.warning(f"加载实体类型配置失败: {e}，使用默认配置")
            return []

    def _load_relation_types(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """加载关系类型配置。"""
        resolved_path = Path(path) if path is not None else RESOURCE_DIR / "relation_types.json"
        if not resolved_path.is_absolute():
            resolved_path = PROJECT_ROOT / resolved_path
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("relation_types", [])
        except Exception as e:
            logger.warning(f"加载关系类型配置失败: {e}，使用默认配置")
            return []

    def run(self, case_id: str, text: str) -> FactExtractionResult:
        """
        执行事实抽取。

        使用混合方案A：UIE实体抽取 + Qwen关系抽取

        Args:
            case_id: 案件ID
            text: 案情文本

        Returns:
            事实抽取结果
        """
        if self.use_uie and self.uie_model:
            return self._extract_hybrid_uie_qwen(case_id, text)
        else:
            return self._extract_with_ollama(case_id, text)

    def _extract_hybrid_uie_qwen(self, case_id: str, text: str) -> FactExtractionResult:
        """混合方案A：UIE实体抽取 + Qwen关系抽取（带缓存）"""
        # 尝试从缓存获取
        if self.enable_cache and self.cache:
            cached = self.cache.get_fact_extraction(text)
            if cached:
                return FactExtractionResult(
                    nodes=cached["nodes"],
                    edges=cached["edges"],
                    summary=cached["summary"] + "（来自缓存）",
                    mode=cached["mode"],
                )
        
        # 步骤1：使用 UIE 抽取实体
        uie_entities = self._extract_entities_with_uie(text)
        
        # 步骤2：使用 Qwen 抽取关系
        qwen_relations = self._extract_relations_with_qwen(text, uie_entities)
        
        # 步骤3：转换为图谱节点和边
        nodes, edges = self._build_graph_from_hybrid(case_id, uie_entities, qwen_relations)
        
        summary = (
            f"使用混合方案A抽取完成：UIE抽取 {len(uie_entities)} 个实体，"
            f"Qwen抽取 {len(qwen_relations)} 条关系，生成 {len(nodes)} 个节点、{len(edges)} 条边。"
        )
        
        # 存入缓存
        if self.enable_cache and self.cache:
            self.cache.set_fact_extraction(
                text=text,
                nodes=nodes,
                edges=edges,
                summary=summary,
                mode="hybrid_uie_qwen",
            )
        
        return FactExtractionResult(
            nodes=nodes,
            edges=edges,
            summary=summary,
            mode="hybrid_uie_qwen",
        )
    
    def _extract_entities_with_uie(self, text: str) -> List[Dict[str, str]]:
        """使用 UIE 抽取实体"""
        result = self.uie_model(text)
        entities = []
        
        if result and len(result) > 0:
            for entity_type, entity_list in result[0].items():
                for entity_info in entity_list:
                    entities.append({
                        "type": entity_type,
                        "label": entity_info["text"],
                    })
        
        return entities
    
    def _extract_relations_with_qwen(self, text: str, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """使用 Qwen 抽取关系"""
        if not entities:
            return []
        
        entity_list = "\n".join([f"- [{e['type']}] {e['label']}" for e in entities])
        
        system_prompt = """你是关系抽取专家。根据给定的实体列表和原文，抽取实体之间的关系。

输出JSON格式：
{
  "relations": [
    {"source": "实体1", "target": "实体2", "relation": "关系类型"}
  ]
}

常见关系类型：实施、作用于、发生于、涉及、造成、参与、位于、在时间、涉嫌、处理"""

        user_prompt = f"""原文：
{text}

已识别实体：
{entity_list}

请抽取实体之间的关系，只输出JSON："""

        result = self.ollama_client.generate_json(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=1024,
        )
        
        return result.get("relations", [])
    
    def _build_graph_from_hybrid(
        self, 
        case_id: str, 
        entities: List[Dict[str, str]], 
        relations: List[Dict[str, str]]
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """从混合抽取结果构建图谱"""
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        
        # 创建案件根节点
        case_node_id = case_id if case_id.startswith("case-") else f"case-{case_id}"
        case_node = GraphNode(
            id=case_node_id,
            type="案件",
            label=f"案件 {case_id}",
            description="当前输入案情的根节点",
            source="coordinator",
        )
        nodes[case_node.id] = case_node
        
        # 创建实体节点
        entity_label_to_id: Dict[str, str] = {}
        for entity in entities:
            entity_type = entity.get("type", "未知")
            label = entity.get("label", "")
            
            if not label:
                continue
            
            node = self._create_node(
                entity_type, label, f"UIE抽取的{entity_type}", "fact_extractor:uie"
            )
            nodes[node.id] = node
            entity_label_to_id[label] = node.id
            
            # 连接到案件节点
            self._connect_to_case(edges, node, case_node, "从属于案件")
        
        # 创建关系边
        for relation in relations:
            source_label = relation.get("source", "")
            target_label = relation.get("target", "")
            relation_type = relation.get("relation", "")
            
            source_id = entity_label_to_id.get(source_label)
            target_id = entity_label_to_id.get(target_label)
            
            if not source_id or not target_id or not relation_type:
                continue
            
            edge = GraphEdge(
                id=edge_id(source_id, relation_type, target_id),
                source=source_id,
                target=target_id,
                relation=relation_type,
                evidence="由 Qwen 抽取",
            )
            edges[edge.id] = edge
        
        return list(nodes.values()), list(edges.values())

    def _extract_with_ollama(self, case_id: str, text: str) -> FactExtractionResult:
        """使用 Ollama 进行结构化实体和关系抽取（带缓存）。"""
        # 尝试从缓存获取
        if self.enable_cache and self.cache:
            cached = self.cache.get_fact_extraction(text)
            if cached:
                return FactExtractionResult(
                    nodes=cached["nodes"],
                    edges=cached["edges"],
                    summary=cached["summary"] + "（来自缓存）",
                    mode=cached["mode"],
                )
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt()

        # 构建用户提示词
        user_prompt = self._build_user_prompt(text)

        # 调用 Ollama
        result = self.ollama_client.generate_json(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,  # 从0.3降到0.2，更确定性
            max_tokens=2048,  # 从4096降到2048，减少生成时间
        )

        # 解析结果
        nodes, edges = self._parse_ollama_result(case_id, result)

        summary = (
            f"使用 Ollama 抽取完成：{len(nodes)} 个节点、{len(edges)} 条关系。"
        )
        
        # 存入缓存
        if self.enable_cache and self.cache:
            self.cache.set_fact_extraction(
                text=text,
                nodes=nodes,
                edges=edges,
                summary=summary,
                mode="ollama_structured",
            )

        return FactExtractionResult(
            nodes=nodes,
            edges=edges,
            summary=summary,
            mode="ollama_structured",
        )

    def _build_system_prompt(self) -> str:
        """构建系统提示词（优化为严格结构化输出）。"""
        entity_types_desc = "\n".join(
            f"- {et['type']}: {et['description']}"
            for et in self.entity_types[:8]  # 限制为8个，减少提示词长度
        )

        relation_types_desc = "\n".join(
            f"- {rt['relation']}: {rt['description']}"
            for rt in self.relation_types[:8]  # 限制为8个
        )

        return f"""你是一个专业的法律案件事实抽取助手。你的任务是从案情描述中抽取结构化的实体和关系。

支持的实体类型：
{entity_types_desc}

支持的关系类型：
{relation_types_desc}

**严格要求**：
1. 只输出JSON格式，不要任何解释性文字
2. 实体数量控制在15个以内，只抽取核心要素
3. 关系数量控制在20个以内，只保留关键关系
4. 每个实体必须包含：type、label、description
5. 每个关系必须包含：source_label、target_label、relation、evidence
6. 优先抽取：人物、行为、时间、地点、金额、伤情
7. 禁止输出任何JSON之外的内容"""

    def _build_user_prompt(self, text: str) -> str:
        """构建用户提示词（简化版）。"""
        return f"""请从以下案情描述中抽取实体和关系：

案情描述：
{text}

请严格按照以下JSON格式输出，不要添加任何其他内容：
{{
  "entities": [
    {{"type": "实体类型", "label": "实体名称", "description": "简短描述"}}
  ],
  "relations": [
    {{"source_label": "源实体", "target_label": "目标实体", "relation": "关系类型", "evidence": "证据文本"}}
  ]
}}"""

    def _parse_ollama_result(
        self, case_id: str, result: Dict[str, Any]
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """解析 Ollama 返回的结果。"""
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}

        # 创建案件根节点
        case_node_id = case_id if case_id.startswith("case-") else f"case-{case_id}"
        case_node = GraphNode(
            id=case_node_id,
            type="案件",
            label=f"案件 {case_id}",
            description="当前输入案情的根节点",
            source="coordinator",
        )
        nodes[case_node.id] = case_node

        # 解析实体
        entities = result.get("entities", [])
        entity_label_to_id: Dict[str, str] = {}

        for entity in entities:
            entity_type = entity.get("type", "未知")
            label = entity.get("label", "")
            description = entity.get("description", "")

            if not label:
                continue

            node = self._create_node(
                entity_type, label, description, "fact_extractor:ollama"
            )
            nodes[node.id] = node
            entity_label_to_id[label] = node.id

            # 连接到案件节点
            self._connect_to_case(edges, node, case_node, "从属于案件")

        # 解析关系
        relations = result.get("relations", [])
        for relation in relations:
            source_label = relation.get("source_label", "")
            target_label = relation.get("target_label", "")
            relation_type = relation.get("relation", "")
            evidence = relation.get("evidence", "")

            source_id = entity_label_to_id.get(source_label)
            target_id = entity_label_to_id.get(target_label)

            if not source_id or not target_id or not relation_type:
                continue

            edge = GraphEdge(
                id=edge_id(source_id, relation_type, target_id),
                source=source_id,
                target=target_id,
                relation=relation_type,
                evidence=evidence or "由 Ollama 抽取",
            )
            edges[edge.id] = edge

        return list(nodes.values()), list(edges.values())

    def _extract_with_heuristic(self, case_id: str, text: str) -> FactExtractionResult:
        """启发式规则抽取（降级方案）。"""
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        case_node_id = case_id if case_id.startswith("case-") else f"case-{case_id}"

        case_node = GraphNode(
            id=case_node_id,
            type="案件",
            label=f"案件 {case_id}",
            description="当前输入案情的根节点",
            source="coordinator",
        )
        nodes[case_node.id] = case_node

        people_nodes: List[GraphNode] = []
        victim_nodes: List[GraphNode] = []
        action_nodes: List[GraphNode] = []

        for node_type, role_label, pattern in ROLE_PATTERNS:
            for match in pattern.findall(text):
                label = f"{role_label}{match}"
                node = self._create_node(node_type, label, f"从案情中识别出的{role_label}", "fact_extractor:heuristic")
                nodes[node.id] = node
                self._connect_to_case(edges, node, case_node, "参与" if node_type in {"人物", "受害人"} else "从属于案件")
                if node_type == "受害人":
                    victim_nodes.append(node)
                else:
                    people_nodes.append(node)

        times = unique_preserve_order(TIME_PATTERN.findall(text))[:3]
        for label in times:
            node = self._create_node("时间", label, "案情中的时间要素", "fact_extractor:heuristic")
            nodes[node.id] = node
            self._connect_to_case(edges, node, case_node, "从属于案件")

        amounts = unique_preserve_order(AMOUNT_PATTERN.findall(text))[:3]
        for label in amounts:
            node = self._create_node("金额", label, "案情中的金额要素", "fact_extractor:heuristic")
            nodes[node.id] = node
            self._connect_to_case(edges, node, case_node, "从属于案件")

        injuries = unique_preserve_order(match.group(1) for match in INJURY_PATTERN.finditer(text))[:3]
        for label in injuries:
            node = self._create_node("伤情", label, "案情中的伤情结果", "fact_extractor:heuristic")
            nodes[node.id] = node
            self._connect_to_case(edges, node, case_node, "从属于案件")

        evidences = unique_preserve_order(match.group(1) for match in EVIDENCE_PATTERN.finditer(text))[:3]
        for label in evidences:
            node = self._create_node("证据", label, "案情中出现的证据线索", "fact_extractor:heuristic")
            nodes[node.id] = node
            self._connect_to_case(edges, node, case_node, "从属于案件")

        places: List[str] = []
        for pattern in PLACE_PATTERNS:
            places.extend(match.group(1) for match in pattern.finditer(text))
        for label in unique_preserve_order(places)[:3]:
            node = self._create_node("地点", label, "案情中的地点要素", "fact_extractor:heuristic")
            nodes[node.id] = node
            self._connect_to_case(edges, node, case_node, "从属于案件")

        for keyword in ACTION_KEYWORDS:
            if keyword in text:
                node = self._create_node("行为", keyword, "从案情中命中的行为关键词", "fact_extractor:heuristic")
                nodes[node.id] = node
                action_nodes.append(node)
                self._connect_to_case(edges, node, case_node, "从属于案件")

        action_nodes = list({node.id: node for node in action_nodes}.values())[:4]

        primary_actor = people_nodes[0] if people_nodes else None
        primary_victim = victim_nodes[0] if victim_nodes else None
        time_nodes = [node for node in nodes.values() if node.type == "时间"]
        place_nodes = [node for node in nodes.values() if node.type == "地点"]
        amount_nodes = [node for node in nodes.values() if node.type == "金额"]
        injury_nodes = [node for node in nodes.values() if node.type == "伤情"]
        evidence_nodes = [node for node in nodes.values() if node.type == "证据"]

        for action in action_nodes:
            if primary_actor:
                self._connect(edges, primary_actor, action, "实施", "从案情角色关系推断主要实施者")
            if primary_victim:
                self._connect(edges, action, primary_victim, "作用于", "从案情角色关系推断主要受害对象")
            for node in time_nodes:
                self._connect(edges, action, node, "发生于", "从时间要素绑定到行为")
            for node in place_nodes:
                self._connect(edges, action, node, "发生于", "从地点要素绑定到行为")
            for node in amount_nodes:
                self._connect(edges, action, node, "涉及金额", "从金额要素绑定到行为")
            for node in injury_nodes:
                self._connect(edges, action, node, "造成", "从伤情要素绑定到行为")
            for node in evidence_nodes:
                self._connect(edges, node, action, "支持证据", "从证据要素绑定到行为")

        summary = (
            f"已抽取 {len(nodes)} 个节点、{len(edges)} 条关系；"
            f"其中人物/受害人 {len(people_nodes) + len(victim_nodes)} 个，行为 {len(action_nodes)} 个。"
        )
        return FactExtractionResult(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            summary=summary,
            mode="heuristic_fallback",
        )

    @staticmethod
    def _create_node(node_type: str, label: str, description: str, source: str) -> GraphNode:
        return GraphNode(
            id=stable_id(node_type, label),
            type=node_type,
            label=label,
            description=description,
            source=source,
        )

    @staticmethod
    def _connect_to_case(edges: Dict[str, GraphEdge], node: GraphNode, case_node: GraphNode, relation: str) -> None:
        edge = GraphEdge(
            id=edge_id(node.id, relation, case_node.id),
            source=node.id,
            target=case_node.id,
            relation=relation,
            evidence="由 FactExtractorAgent 主干版归并到案件上下文",
        )
        edges[edge.id] = edge

    @staticmethod
    def _connect(
        edges: Dict[str, GraphEdge],
        source_node: GraphNode,
        target_node: GraphNode,
        relation: str,
        evidence: str,
    ) -> None:
        edge = GraphEdge(
            id=edge_id(source_node.id, relation, target_node.id),
            source=source_node.id,
            target=target_node.id,
            relation=relation,
            evidence=evidence,
        )
        edges[edge.id] = edge
