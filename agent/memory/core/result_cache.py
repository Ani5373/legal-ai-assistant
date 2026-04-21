"""
中间结果缓存系统

用于缓存事实抽取和报告生成的中间结果，避免重复计算
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from agent.schemas.contracts import GraphEdge, GraphNode

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class FactExtractionCache(BaseModel):
    """事实抽取缓存条目"""
    
    text_hash: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    summary: str
    mode: str
    cached_at: float
    hit_count: int = 0


class ReportGenerationCache(BaseModel):
    """报告生成缓存条目"""
    
    input_hash: str
    report: str
    summary: str
    cached_at: float
    hit_count: int = 0


class ResultCache:
    """中间结果缓存管理器"""
    
    def __init__(
        self,
        base_path: str = "agent/memory/cache",
        max_age_seconds: int = 3600,  # 1小时过期
        max_entries: int = 100,
    ):
        self.base_path = Path(base_path)
        if not self.base_path.is_absolute():
            self.base_path = PROJECT_ROOT / self.base_path
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.max_age_seconds = max_age_seconds
        self.max_entries = max_entries
        
        # 缓存文件路径
        self.fact_cache_file = self.base_path / "fact_extraction_cache.json"
        self.report_cache_file = self.base_path / "report_generation_cache.json"
        
        # 加载缓存
        self._load_caches()
    
    def _load_caches(self) -> None:
        """加载缓存文件"""
        # 加载事实抽取缓存
        if self.fact_cache_file.exists():
            with open(self.fact_cache_file, encoding="utf-8") as f:
                data = json.load(f)
                self.fact_cache = {
                    k: FactExtractionCache(**v) for k, v in data.items()
                }
        else:
            self.fact_cache: Dict[str, FactExtractionCache] = {}
        
        # 加载报告生成缓存
        if self.report_cache_file.exists():
            with open(self.report_cache_file, encoding="utf-8") as f:
                data = json.load(f)
                self.report_cache = {
                    k: ReportGenerationCache(**v) for k, v in data.items()
                }
        else:
            self.report_cache: Dict[str, ReportGenerationCache] = {}
    
    def _save_fact_cache(self) -> None:
        """保存事实抽取缓存"""
        data = {k: v.model_dump() for k, v in self.fact_cache.items()}
        with open(self.fact_cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_report_cache(self) -> None:
        """保存报告生成缓存"""
        data = {k: v.model_dump() for k, v in self.report_cache.items()}
        with open(self.report_cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _compute_hash(text: str) -> str:
        """计算文本哈希"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    
    def _cleanup_expired(self, cache: Dict[str, Any]) -> None:
        """清理过期缓存"""
        now = time.time()
        expired_keys = [
            k for k, v in cache.items()
            if now - v.cached_at > self.max_age_seconds
        ]
        for key in expired_keys:
            del cache[key]
    
    def _limit_size(self, cache: Dict[str, Any]) -> None:
        """限制缓存大小"""
        if len(cache) > self.max_entries:
            # 删除最少使用的条目
            sorted_items = sorted(
                cache.items(),
                key=lambda x: (x[1].hit_count, x[1].cached_at)
            )
            to_delete = len(cache) - self.max_entries
            for key, _ in sorted_items[:to_delete]:
                del cache[key]
    
    def get_fact_extraction(
        self,
        text: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取事实抽取缓存
        
        Args:
            text: 案情文本
            
        Returns:
            缓存的结果或 None
        """
        text_hash = self._compute_hash(text)
        
        if text_hash not in self.fact_cache:
            return None
        
        entry = self.fact_cache[text_hash]
        
        # 检查是否过期
        if time.time() - entry.cached_at > self.max_age_seconds:
            del self.fact_cache[text_hash]
            self._save_fact_cache()
            return None
        
        # 更新命中计数
        entry.hit_count += 1
        self._save_fact_cache()
        
        return {
            "nodes": entry.nodes,
            "edges": entry.edges,
            "summary": entry.summary,
            "mode": entry.mode,
        }
    
    def set_fact_extraction(
        self,
        text: str,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        summary: str,
        mode: str,
    ) -> None:
        """
        设置事实抽取缓存
        
        Args:
            text: 案情文本
            nodes: 图谱节点
            edges: 图谱边
            summary: 摘要
            mode: 模式
        """
        text_hash = self._compute_hash(text)
        
        self.fact_cache[text_hash] = FactExtractionCache(
            text_hash=text_hash,
            nodes=nodes,
            edges=edges,
            summary=summary,
            mode=mode,
            cached_at=time.time(),
            hit_count=0,
        )
        
        # 清理和限制
        self._cleanup_expired(self.fact_cache)
        self._limit_size(self.fact_cache)
        
        self._save_fact_cache()
    
    def get_report_generation(
        self,
        text: str,
        predictions: List[Any],
        nodes: List[GraphNode],
    ) -> Optional[Dict[str, str]]:
        """
        获取报告生成缓存
        
        Args:
            text: 案情文本
            predictions: 罪名预测
            nodes: 图谱节点
            
        Returns:
            缓存的报告或 None
        """
        # 构建输入哈希（基于关键输入）
        input_str = f"{text}|{len(predictions)}|{len(nodes)}"
        if predictions:
            input_str += f"|{predictions[0].label}"
        input_hash = self._compute_hash(input_str)
        
        if input_hash not in self.report_cache:
            return None
        
        entry = self.report_cache[input_hash]
        
        # 检查是否过期
        if time.time() - entry.cached_at > self.max_age_seconds:
            del self.report_cache[input_hash]
            self._save_report_cache()
            return None
        
        # 更新命中计数
        entry.hit_count += 1
        self._save_report_cache()
        
        return {
            "report": entry.report,
            "summary": entry.summary,
        }
    
    def set_report_generation(
        self,
        text: str,
        predictions: List[Any],
        nodes: List[GraphNode],
        report: str,
        summary: str,
    ) -> None:
        """
        设置报告生成缓存
        
        Args:
            text: 案情文本
            predictions: 罪名预测
            nodes: 图谱节点
            report: 报告内容
            summary: 摘要
        """
        # 构建输入哈希
        input_str = f"{text}|{len(predictions)}|{len(nodes)}"
        if predictions:
            input_str += f"|{predictions[0].label}"
        input_hash = self._compute_hash(input_str)
        
        self.report_cache[input_hash] = ReportGenerationCache(
            input_hash=input_hash,
            report=report,
            summary=summary,
            cached_at=time.time(),
            hit_count=0,
        )
        
        # 清理和限制
        self._cleanup_expired(self.report_cache)
        self._limit_size(self.report_cache)
        
        self._save_report_cache()
    
    def clear_all(self) -> None:
        """清空所有缓存"""
        self.fact_cache.clear()
        self.report_cache.clear()
        self._save_fact_cache()
        self._save_report_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        fact_hits = sum(e.hit_count for e in self.fact_cache.values())
        report_hits = sum(e.hit_count for e in self.report_cache.values())
        
        return {
            "fact_cache_size": len(self.fact_cache),
            "fact_cache_hits": fact_hits,
            "report_cache_size": len(self.report_cache),
            "report_cache_hits": report_hits,
            "total_hits": fact_hits + report_hits,
        }
