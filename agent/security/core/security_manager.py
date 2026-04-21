"""
三阶段安全检查系统 Security Manager

阶段 1: 规则快速过滤 - 基于规则的快速检查
阶段 2: 风险分级判断 - 使用本地模型评估风险等级
阶段 3: 高风险操作模拟审查 - 对高风险操作进行详细审查

特性：
- 多层防护：三阶段递进式检查
- 审计日志：所有操作记录到日志
- 灵活配置：可自定义规则和阈值
- 本地模型：使用 Ollama 进行风险评估
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class RiskLevel(str, Enum):
    """风险等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CheckResult(BaseModel):
    """安全检查结果"""

    passed: bool
    risk_level: RiskLevel
    stage: str
    reason: str = ""
    suggestions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditLogEntry(BaseModel):
    """审计日志条目"""

    timestamp: str
    case_id: str
    operation: str
    risk_level: RiskLevel
    passed: bool
    stage: str
    reason: str = ""
    text_preview: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SecurityManager:
    """三阶段安全检查管理器"""

    def __init__(
        self,
        base_path: str = "agent/security",
        enable_stage2: bool = True,
        enable_stage3: bool = True,
        enable_audit_log: bool = True,
        ollama_client=None,
    ):
        self.base_path = Path(base_path)
        if not self.base_path.is_absolute():
            self.base_path = PROJECT_ROOT / self.base_path
        self.policies_path = self.base_path / "policies"
        self.review_path = self.base_path / "review"
        self.logs_path = PROJECT_ROOT / "agent" / "logs"

        # 确保目录存在
        self.policies_path.mkdir(parents=True, exist_ok=True)
        self.review_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # 配置
        self.enable_stage2 = enable_stage2
        self.enable_stage3 = enable_stage3
        self.enable_audit_log = enable_audit_log
        self.ollama_client = ollama_client

        # 加载规则
        self._load_rules()

        # 审计日志文件
        self.audit_log_file = self.logs_path / "audit_log.jsonl"

    def _load_rules(self) -> None:
        """加载安全规则"""
        rules_file = self.policies_path / "security_rules.json"

        if rules_file.exists():
            with open(rules_file, encoding="utf-8") as f:
                self.rules = json.load(f)
        else:
            # 默认规则
            self.rules = {
                "blocked_keywords": [
                    "测试",
                    "demo",
                    "example",
                    "假设",
                    "虚构",
                ],
                "sensitive_keywords": [
                    "死亡",
                    "杀人",
                    "爆炸",
                    "恐怖",
                    "绑架",
                    "强奸",
                    "贩毒",
                ],
                "min_text_length": 10,
                "max_text_length": 10000,
                "blocked_patterns": [
                    r"^\s*$",  # 空白文本
                    r"^test\s+case",  # 测试用例
                ],
            }
            # 保存默认规则
            with open(rules_file, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _utc_now_iso() -> str:
        """获取当前UTC时间ISO格式"""
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def check(self, case_id: str, text: str, operation: str = "analyze") -> CheckResult:
        """
        执行三阶段安全检查

        Args:
            case_id: 案件ID
            text: 案情文本
            operation: 操作类型

        Returns:
            CheckResult: 检查结果
        """
        # 阶段 1: 规则快速过滤
        stage1_result = self._stage1_rule_filter(text)
        if not stage1_result.passed:
            self._log_audit(case_id, text, operation, stage1_result)
            return stage1_result

        # 默认风险等级
        final_risk_level = RiskLevel.LOW
        stage2_result = None

        # 阶段 2: 风险分级判断
        if self.enable_stage2:
            stage2_result = self._stage2_risk_assessment(text)
            final_risk_level = stage2_result.risk_level
            
            if not stage2_result.passed:
                self._log_audit(case_id, text, operation, stage2_result)
                return stage2_result

            # 高风险需要进入阶段3
            if stage2_result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                if self.enable_stage3:
                    stage3_result = self._stage3_high_risk_review(text, stage2_result)
                    self._log_audit(case_id, text, operation, stage3_result)
                    return stage3_result
                else:
                    # 阶段3被禁用，但仍然返回stage2的结果
                    self._log_audit(case_id, text, operation, stage2_result)
                    return stage2_result

        # 通过所有检查
        final_result = CheckResult(
            passed=True,
            risk_level=final_risk_level,
            stage="completed",
            reason="通过所有安全检查",
            metadata=stage2_result.metadata if stage2_result else {},
        )
        self._log_audit(case_id, text, operation, final_result)
        return final_result

    def _stage1_rule_filter(self, text: str) -> CheckResult:
        """
        阶段 1: 规则快速过滤

        检查项：
        - 文本长度
        - 阻止关键词
        - 阻止模式
        """
        # 检查文本长度
        if len(text) < self.rules["min_text_length"]:
            return CheckResult(
                passed=False,
                risk_level=RiskLevel.LOW,
                stage="stage1_rule_filter",
                reason=f"文本过短（{len(text)}字符），最少需要{self.rules['min_text_length']}字符",
                suggestions=["请提供更详细的案情描述"],
            )

        if len(text) > self.rules["max_text_length"]:
            return CheckResult(
                passed=False,
                risk_level=RiskLevel.LOW,
                stage="stage1_rule_filter",
                reason=f"文本过长（{len(text)}字符），最多允许{self.rules['max_text_length']}字符",
                suggestions=["请精简案情描述"],
            )

        # 检查阻止关键词
        for keyword in self.rules["blocked_keywords"]:
            if keyword in text.lower():
                return CheckResult(
                    passed=False,
                    risk_level=RiskLevel.MEDIUM,
                    stage="stage1_rule_filter",
                    reason=f"包含阻止关键词：{keyword}",
                    suggestions=["请提供真实案情，避免使用测试或虚构内容"],
                )

        # 检查阻止模式
        for pattern in self.rules["blocked_patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return CheckResult(
                    passed=False,
                    risk_level=RiskLevel.MEDIUM,
                    stage="stage1_rule_filter",
                    reason=f"匹配阻止模式：{pattern}",
                    suggestions=["请提供有效的案情描述"],
                )

        # 通过阶段1
        return CheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            stage="stage1_rule_filter",
            reason="通过规则快速过滤",
        )

    def _stage2_risk_assessment(self, text: str) -> CheckResult:
        """
        阶段 2: 风险分级判断

        使用启发式规则和可选的本地模型评估风险等级
        """
        risk_score = 0.0
        risk_factors = []

        # 检查敏感关键词
        sensitive_count = 0
        for keyword in self.rules["sensitive_keywords"]:
            if keyword in text:
                sensitive_count += 1
                risk_factors.append(f"包含敏感词：{keyword}")

        # 计算风险分数（提高敏感词权重）
        if sensitive_count > 0:
            # 每个敏感词增加0.35分，多个敏感词累加
            risk_score += min(sensitive_count * 0.35, 0.9)

        # 检查文本复杂度
        if len(text) > 2000:
            risk_score += 0.1
            risk_factors.append("案情描述较长")

        # 使用 Ollama 进行风险评估（如果可用）
        if self.ollama_client:
            try:
                model_risk = self._assess_risk_with_model(text)
                risk_score = (risk_score + model_risk) / 2
                risk_factors.append(f"模型评估风险：{model_risk:.2f}")
            except Exception:
                # 模型评估失败，使用启发式结果
                pass

        # 确定风险等级
        if risk_score < 0.3:
            risk_level = RiskLevel.LOW
        elif risk_score < 0.6:
            risk_level = RiskLevel.MEDIUM
        elif risk_score < 0.8:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL

        # 高风险和严重风险需要进一步审查
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return CheckResult(
                passed=True,  # 不阻止，但需要进入阶段3
                risk_level=risk_level,
                stage="stage2_risk_assessment",
                reason=f"风险等级：{risk_level.value}（分数：{risk_score:.2f}）",
                suggestions=["需要进行高风险操作审查"],
                metadata={"risk_score": risk_score, "risk_factors": risk_factors},
            )

        # 低风险和中风险直接通过
        return CheckResult(
            passed=True,
            risk_level=risk_level,
            stage="stage2_risk_assessment",
            reason=f"风险等级：{risk_level.value}（分数：{risk_score:.2f}）",
            metadata={"risk_score": risk_score, "risk_factors": risk_factors},
        )

    def _assess_risk_with_model(self, text: str) -> float:
        """
        使用本地模型评估风险

        Args:
            text: 案情文本

        Returns:
            风险分数 (0-1)
        """
        if not self.ollama_client:
            return 0.0

        prompt = f"""请评估以下法律案情的风险等级。

案情描述：
{text[:500]}

请从以下维度评估风险：
1. 案情严重程度（0-1）
2. 社会影响程度（0-1）
3. 处理复杂度（0-1）

返回JSON格式：
{{
  "severity": 0.0-1.0,
  "social_impact": 0.0-1.0,
  "complexity": 0.0-1.0,
  "overall_risk": 0.0-1.0
}}"""

        try:
            response = self.ollama_client.generate_json(
                prompt=prompt,
                model="qwen2.5:latest",
                temperature=0.3,
            )

            if response and "overall_risk" in response:
                return float(response["overall_risk"])
        except Exception:
            pass

        return 0.0

    def _stage3_high_risk_review(
        self, text: str, stage2_result: CheckResult
    ) -> CheckResult:
        """
        阶段 3: 高风险操作模拟审查

        对高风险案件进行详细审查
        """
        review_items = []
        warnings = []

        # 提取风险因素
        risk_factors = stage2_result.metadata.get("risk_factors", [])

        # 检查是否有足够的证据支持
        if "证据" not in text and "证明" not in text:
            warnings.append("案情描述中缺少证据相关信息")

        # 检查是否有时间地点等关键要素
        if not any(keyword in text for keyword in ["时间", "地点", "日期", "年", "月"]):
            warnings.append("案情描述中缺少时间要素")

        if not any(keyword in text for keyword in ["地点", "位置", "场所", "地方"]):
            warnings.append("案情描述中缺少地点要素")

        # 使用模型进行详细审查（如果可用）
        if self.ollama_client:
            try:
                model_review = self._detailed_review_with_model(text, risk_factors)
                review_items.extend(model_review)
            except Exception:
                pass

        # 决定是否通过
        critical_warnings = [w for w in warnings if "缺少" in w]

        if len(critical_warnings) >= 2:
            return CheckResult(
                passed=False,
                risk_level=stage2_result.risk_level,
                stage="stage3_high_risk_review",
                reason="高风险案件缺少关键要素",
                suggestions=warnings + ["请补充完整的案情信息"],
                metadata={
                    "risk_factors": risk_factors,
                    "review_items": review_items,
                    "warnings": warnings,
                },
            )

        # 通过但保留警告
        return CheckResult(
            passed=True,
            risk_level=stage2_result.risk_level,
            stage="stage3_high_risk_review",
            reason="通过高风险审查",
            suggestions=warnings,
            metadata={
                "risk_factors": risk_factors,
                "review_items": review_items,
                "warnings": warnings,
            },
        )

    def _detailed_review_with_model(
        self, text: str, risk_factors: List[str]
    ) -> List[str]:
        """
        使用模型进行详细审查

        Args:
            text: 案情文本
            risk_factors: 风险因素列表

        Returns:
            审查项列表
        """
        if not self.ollama_client:
            return []

        prompt = f"""请对以下高风险法律案情进行详细审查。

案情描述：
{text[:800]}

已识别的风险因素：
{chr(10).join(f"- {factor}" for factor in risk_factors)}

请从以下角度审查：
1. 案情描述的完整性
2. 关键证据的充分性
3. 法律适用的复杂性
4. 潜在的争议点

返回JSON格式的审查意见列表：
{{
  "review_items": ["审查意见1", "审查意见2", ...]
}}"""

        try:
            response = self.ollama_client.generate_json(
                prompt=prompt,
                model="qwen2.5:latest",
                temperature=0.3,
            )

            if response and "review_items" in response:
                return response["review_items"]
        except Exception:
            pass

        return []

    def _log_audit(
        self, case_id: str, text: str, operation: str, result: CheckResult
    ) -> None:
        """
        记录审计日志

        Args:
            case_id: 案件ID
            text: 案情文本
            operation: 操作类型
            result: 检查结果
        """
        if not self.enable_audit_log:
            return

        entry = AuditLogEntry(
            timestamp=self._utc_now_iso(),
            case_id=case_id,
            operation=operation,
            risk_level=result.risk_level,
            passed=result.passed,
            stage=result.stage,
            reason=result.reason,
            text_preview=text[:100] + "..." if len(text) > 100 else text,
            metadata={
                "suggestions": result.suggestions,
                "result_metadata": result.metadata,
            },
        )

        # 追加到日志文件
        with open(self.audit_log_file, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def get_audit_logs(
        self,
        limit: int = 100,
        risk_level: Optional[RiskLevel] = None,
        passed: Optional[bool] = None,
    ) -> List[AuditLogEntry]:
        """
        获取审计日志

        Args:
            limit: 返回数量限制
            risk_level: 过滤风险等级
            passed: 过滤通过状态

        Returns:
            审计日志列表
        """
        if not self.audit_log_file.exists():
            return []

        logs = []
        with open(self.audit_log_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = AuditLogEntry.model_validate_json(line)

                        # 应用过滤
                        if risk_level and entry.risk_level != risk_level:
                            continue
                        if passed is not None and entry.passed != passed:
                            continue

                        logs.append(entry)
                    except Exception:
                        continue

        # 返回最新的记录
        return logs[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取安全检查统计信息"""
        if not self.audit_log_file.exists():
            return {
                "total_checks": 0,
                "passed": 0,
                "blocked": 0,
                "by_risk_level": {},
                "by_stage": {},
            }

        total = 0
        passed = 0
        blocked = 0
        by_risk_level = {level.value: 0 for level in RiskLevel}
        by_stage = {}

        with open(self.audit_log_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = AuditLogEntry.model_validate_json(line)
                        total += 1

                        if entry.passed:
                            passed += 1
                        else:
                            blocked += 1

                        by_risk_level[entry.risk_level] += 1

                        if entry.stage not in by_stage:
                            by_stage[entry.stage] = 0
                        by_stage[entry.stage] += 1
                    except Exception:
                        continue

        return {
            "total_checks": total,
            "passed": passed,
            "blocked": blocked,
            "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
            "by_risk_level": by_risk_level,
            "by_stage": by_stage,
        }
