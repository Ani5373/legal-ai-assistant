"""
请求模型定义
"""

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """BERT 罪名预测请求"""

    text: str = Field(..., min_length=1, description="案情描述文本")


class AnalysisRequest(BaseModel):
    """统一案件分析请求"""

    text: str = Field(..., min_length=1, description="案情描述文本")
    case_id: str | None = Field(default=None, description="可选的外部案件 ID")
