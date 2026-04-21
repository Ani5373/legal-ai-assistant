"""
响应模型定义
"""

from typing import List

from pydantic import BaseModel


class PredictionItem(BaseModel):
    """单个罪名预测项"""

    label: str
    probability: float


class PredictResponse(BaseModel):
    """BERT 罪名预测响应"""

    predictions: List[PredictionItem]


# 统一案件分析响应使用 agent.schemas.contracts.CaseAnalysisResponse
