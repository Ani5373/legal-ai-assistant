"""
统一案件分析接口
"""

from fastapi import APIRouter, HTTPException, Request

from agent.schemas.contracts import CaseAnalysisResponse
from 服务端.schemas.requests import AnalysisRequest

router = APIRouter()


@router.post("/analyze", response_model=CaseAnalysisResponse)
async def analyze(req: AnalysisRequest, request: Request) -> CaseAnalysisResponse:
    """
    统一案件分析接口

    Args:
        req: 分析请求
        request: FastAPI 请求对象

    Returns:
        案件分析响应
    """
    analysis_service = getattr(request.app.state, "analysis_service", None)
    if not analysis_service:
        raise HTTPException(status_code=503, detail="分析服务未初始化，请稍后重试。")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空。")

    return analysis_service.analyze(text=text, case_id=req.case_id)
