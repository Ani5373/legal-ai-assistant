"""
BERT 罪名预测接口
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from 服务端.schemas.requests import PredictRequest
from 服务端.schemas.responses import PredictResponse

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request) -> Dict[str, Any]:
    """
    BERT 罪名预测接口

    Args:
        req: 预测请求
        request: FastAPI 请求对象

    Returns:
        预测响应
    """
    prediction_service = getattr(request.app.state, "prediction_service", None)
    if not prediction_service:
        raise HTTPException(status_code=503, detail="预测服务未初始化，请稍后重试。")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空。")

    predictions = prediction_service.predict(text)
    return {"predictions": predictions}
