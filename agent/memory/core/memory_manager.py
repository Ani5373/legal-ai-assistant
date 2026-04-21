"""
三层智能内存系统 Memory Manager

Layer 1: 轻量索引 (index/) - 快速查找和元数据
Layer 2: Topic 详细 JSON (topics/) - 结构化案件数据
Layer 3: 原始案情缓存 (raw/) - 原始文本存储

特性：
- 自愈更新：自动修复和更新过期数据
- 压缩旧记忆：定期清理低价值数据
- 高信号保留：保留高价值案件数据
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agent.schemas.contracts import (
    CaseAnalysisResponse,
    ChargePrediction,
    GraphEdge,
    GraphNode,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class MemoryIndex(BaseModel):
    """Layer 1: 轻量索引条目"""

    case_id: str
    text_hash: str
    created_at: str
    last_accessed: str
    access_count: int = 0
    topic_file: str
    raw_file: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    signal_score: float = 0.0  # 信号强度评分，用于压缩决策


class TopicMemory(BaseModel):
    """Layer 2: Topic 详细数据"""

    case_id: str
    text: str
    predictions: List[ChargePrediction] = Field(default_factory=list)
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    report: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class MemoryManager:
    """三层智能内存管理器"""

    def __init__(
        self,
        base_path: str = "agent/memory",
        max_age_days: int = 90,
        min_signal_score: float = 0.3,
        compression_threshold: int = 1000,
    ):
        self.base_path = Path(base_path)
        if not self.base_path.is_absolute():
            self.base_path = PROJECT_ROOT / self.base_path
        self.index_path = self.base_path / "index"
        self.topics_path = self.base_path / "topics"
        self.raw_path = self.base_path / "raw"

        # 确保目录存在
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.topics_path.mkdir(parents=True, exist_ok=True)
        self.raw_path.mkdir(parents=True, exist_ok=True)

        # 配置参数
        self.max_age_days = max_age_days
        self.min_signal_score = min_signal_score
        self.compression_threshold = compression_threshold

        # 索引文件路径
        self.index_file = self.index_path / "memory_index.json"
        self._load_index()

    def _load_index(self) -> None:
        """加载索引文件"""
        if self.index_file.exists():
            with open(self.index_file, encoding="utf-8") as f:
                data = json.load(f)
                self.index = {k: MemoryIndex(**v) for k, v in data.items()}
        else:
            self.index: Dict[str, MemoryIndex] = {}

    def _save_index(self) -> None:
        """保存索引文件"""
        data = {k: v.model_dump() for k, v in self.index.items()}
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _compute_text_hash(text: str) -> str:
        """计算文本哈希"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _utc_now_iso() -> str:
        """获取当前UTC时间ISO格式"""
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _calculate_signal_score(self, response: CaseAnalysisResponse) -> float:
        """
        计算案件信号强度评分

        评分标准：
        - 预测数量和置信度
        - 图谱节点和边的数量
        - 报告长度
        - 是否有警告
        """
        score = 0.0

        # 预测质量 (0-0.3)
        if response.predictions:
            avg_prob = sum(p.probability for p in response.predictions) / len(
                response.predictions
            )
            score += avg_prob * 0.3

        # 图谱丰富度 (0-0.3)
        node_score = min(len(response.nodes) / 20.0, 1.0) * 0.15
        edge_score = min(len(response.edges) / 30.0, 1.0) * 0.15
        score += node_score + edge_score

        # 报告质量 (0-0.2)
        if response.report:
            report_score = min(len(response.report) / 2000.0, 1.0) * 0.2
            score += report_score

        # 无警告加分 (0-0.2)
        if not response.warnings:
            score += 0.2

        return min(score, 1.0)

    def store(self, response: CaseAnalysisResponse) -> None:
        """
        存储案件分析结果到三层内存

        Args:
            response: 案件分析响应
        """
        case_id = response.case_id
        text_hash = self._compute_text_hash(response.text)
        now = self._utc_now_iso()

        # Layer 3: 存储原始文本
        raw_file = f"{case_id}_{text_hash}.txt"
        raw_path = self.raw_path / raw_file
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        # Layer 2: 存储详细数据
        topic_file = f"{case_id}_{text_hash}.json"
        topic_path = self.topics_path / topic_file

        topic_memory = TopicMemory(
            case_id=case_id,
            text=response.text,
            predictions=response.predictions,
            nodes=response.nodes,
            edges=response.edges,
            report=response.report,
            metadata=response.metadata,
            created_at=now,
            updated_at=now,
        )

        with open(topic_path, "w", encoding="utf-8") as f:
            json.dump(topic_memory.model_dump(), f, ensure_ascii=False, indent=2)

        # Layer 1: 更新索引
        signal_score = self._calculate_signal_score(response)

        if case_id in self.index:
            # 更新现有索引
            entry = self.index[case_id]
            entry.last_accessed = now
            entry.access_count += 1
            entry.text_hash = text_hash
            entry.topic_file = topic_file
            entry.raw_file = raw_file
            entry.signal_score = signal_score
        else:
            # 创建新索引
            self.index[case_id] = MemoryIndex(
                case_id=case_id,
                text_hash=text_hash,
                created_at=now,
                last_accessed=now,
                access_count=1,
                topic_file=topic_file,
                raw_file=raw_file,
                metadata={
                    "node_count": len(response.nodes),
                    "edge_count": len(response.edges),
                    "prediction_count": len(response.predictions),
                },
                signal_score=signal_score,
            )

        self._save_index()

    def retrieve(self, case_id: str) -> Optional[TopicMemory]:
        """
        从内存中检索案件数据

        Args:
            case_id: 案件ID

        Returns:
            TopicMemory 或 None
        """
        if case_id not in self.index:
            return None

        entry = self.index[case_id]
        topic_path = self.topics_path / entry.topic_file

        if not topic_path.exists():
            # 自愈：索引存在但文件丢失
            del self.index[case_id]
            self._save_index()
            return None

        # 更新访问记录
        entry.last_accessed = self._utc_now_iso()
        entry.access_count += 1
        self._save_index()

        with open(topic_path, encoding="utf-8") as f:
            data = json.load(f)
            return TopicMemory(**data)

    def search_by_text(self, text: str) -> Optional[TopicMemory]:
        """
        通过文本哈希搜索案件

        Args:
            text: 案情文本

        Returns:
            TopicMemory 或 None
        """
        text_hash = self._compute_text_hash(text)

        for case_id, entry in self.index.items():
            if entry.text_hash == text_hash:
                return self.retrieve(case_id)

        return None

    def list_recent(self, limit: int = 10) -> List[MemoryIndex]:
        """
        列出最近访问的案件

        Args:
            limit: 返回数量限制

        Returns:
            MemoryIndex 列表
        """
        sorted_entries = sorted(
            self.index.values(),
            key=lambda x: x.last_accessed,
            reverse=True,
        )
        return sorted_entries[:limit]

    def compress(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        压缩旧记忆，清理低价值数据

        策略：
        1. 删除超过 max_age_days 且信号分数低于 min_signal_score 的案件
        2. 删除访问次数为 1 且超过 30 天的案件
        3. 当总案件数超过 compression_threshold 时，删除最低分数的 20%

        Args:
            dry_run: 是否仅模拟运行

        Returns:
            压缩统计信息
        """
        now = datetime.utcnow()
        to_delete = []
        stats = {
            "total_before": len(self.index),
            "deleted_old": 0,
            "deleted_low_access": 0,
            "deleted_low_signal": 0,
            "total_after": 0,
        }

        # 策略 1: 删除过期低信号案件
        for case_id, entry in self.index.items():
            created = datetime.fromisoformat(entry.created_at.replace("Z", ""))
            age_days = (now - created).days

            if age_days > self.max_age_days and entry.signal_score < self.min_signal_score:
                to_delete.append(case_id)
                stats["deleted_old"] += 1

        # 策略 2: 删除低访问案件
        for case_id, entry in self.index.items():
            if case_id in to_delete:
                continue
            created = datetime.fromisoformat(entry.created_at.replace("Z", ""))
            age_days = (now - created).days

            if entry.access_count == 1 and age_days > 30:
                to_delete.append(case_id)
                stats["deleted_low_access"] += 1

        # 策略 3: 总量控制
        if len(self.index) > self.compression_threshold:
            remaining = {k: v for k, v in self.index.items() if k not in to_delete}
            sorted_by_signal = sorted(
                remaining.items(),
                key=lambda x: x[1].signal_score,
            )
            delete_count = int(len(sorted_by_signal) * 0.2)
            for case_id, _ in sorted_by_signal[:delete_count]:
                to_delete.append(case_id)
                stats["deleted_low_signal"] += 1

        # 执行删除
        if not dry_run:
            for case_id in to_delete:
                self._delete_case(case_id)

        stats["total_after"] = len(self.index) - len(to_delete)
        stats["deleted_total"] = len(to_delete)

        return stats

    def _delete_case(self, case_id: str) -> None:
        """删除案件的所有数据"""
        if case_id not in self.index:
            return

        entry = self.index[case_id]

        # 删除 Layer 2 文件
        topic_path = self.topics_path / entry.topic_file
        if topic_path.exists():
            topic_path.unlink()

        # 删除 Layer 3 文件
        raw_path = self.raw_path / entry.raw_file
        if raw_path.exists():
            raw_path.unlink()

        # 删除索引
        del self.index[case_id]
        self._save_index()

    def heal(self) -> Dict[str, Any]:
        """
        自愈：修复索引与文件不一致的问题

        Returns:
            修复统计信息
        """
        stats = {
            "checked": len(self.index),
            "missing_topic": 0,
            "missing_raw": 0,
            "orphaned_topic": 0,
            "orphaned_raw": 0,
            "repaired": 0,
        }

        # 检查索引指向的文件是否存在
        to_delete = []
        for case_id, entry in self.index.items():
            topic_exists = (self.topics_path / entry.topic_file).exists()
            raw_exists = (self.raw_path / entry.raw_file).exists()

            if not topic_exists:
                stats["missing_topic"] += 1
                to_delete.append(case_id)
            elif not raw_exists:
                stats["missing_raw"] += 1
                # 原始文本丢失不影响使用，仅记录

        # 删除损坏的索引
        for case_id in to_delete:
            del self.index[case_id]
            stats["repaired"] += 1

        # 检查孤立文件
        indexed_topics = {entry.topic_file for entry in self.index.values()}
        indexed_raws = {entry.raw_file for entry in self.index.values()}

        for topic_file in self.topics_path.glob("*.json"):
            if topic_file.name not in indexed_topics:
                stats["orphaned_topic"] += 1
                topic_file.unlink()

        for raw_file in self.raw_path.glob("*.txt"):
            if raw_file.name not in indexed_raws:
                stats["orphaned_raw"] += 1
                raw_file.unlink()

        self._save_index()
        return stats

    def get_stats(self) -> Dict[str, Any]:
        """获取内存系统统计信息"""
        if not self.index:
            return {
                "total_cases": 0,
                "avg_signal_score": 0.0,
                "total_accesses": 0,
                "storage_size_mb": 0.0,
            }

        total_accesses = sum(entry.access_count for entry in self.index.values())
        avg_signal = sum(entry.signal_score for entry in self.index.values()) / len(
            self.index
        )

        # 计算存储大小
        storage_size = 0
        for path in [self.index_path, self.topics_path, self.raw_path]:
            for file in path.rglob("*"):
                if file.is_file():
                    storage_size += file.stat().st_size

        return {
            "total_cases": len(self.index),
            "avg_signal_score": round(avg_signal, 3),
            "total_accesses": total_accesses,
            "storage_size_mb": round(storage_size / (1024 * 1024), 2),
        }
