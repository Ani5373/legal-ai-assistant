"""
案件分析服务
"""

from agent.coordinator.engine import CaseAnalysisCoordinator
from agent.schemas.contracts import CaseAnalysisResponse


class AnalysisService:
    """统一案件分析服务"""

    def __init__(self, coordinator: CaseAnalysisCoordinator):
        self.coordinator = coordinator

    def analyze(self, text: str, case_id: str | None = None) -> CaseAnalysisResponse:
        """
        分析案件

        Args:
            text: 案情描述文本
            case_id: 可选的案件ID

        Returns:
            案件分析响应
        """
        return self.coordinator.analyze(text=text, case_id=case_id)
