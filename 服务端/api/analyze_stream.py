"""
流式案件分析接口
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from agent.schemas.contracts import CaseAnalysisResponse
from 服务端.schemas.requests import AnalysisRequest

router = APIRouter()


async def stream_analysis(
    text: str,
    case_id: str | None,
    coordinator
) -> AsyncGenerator[str, None]:
    """
    流式分析生成器
    
    Args:
        text: 案情文本
        case_id: 案件ID
        coordinator: 协调器实例
        
    Yields:
        SSE 格式的数据流
    """
    try:
        # 发送开始信号
        yield f"data: {json.dumps({'type': 'start', 'message': '开始分析案件'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)
        
        # 调用协调器进行流式分析
        async for chunk in coordinator.analyze_stream(text=text, case_id=case_id):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
            
    except Exception as e:
        error_data = {
            'type': 'error',
            'message': f'分析失败: {str(e)}'
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


@router.post("/analyze/stream")
async def analyze_stream(req: AnalysisRequest, request: Request):
    """
    流式案件分析接口
    
    Args:
        req: 分析请求
        request: FastAPI 请求对象
        
    Returns:
        SSE 流式响应
    """
    coordinator = getattr(request.app.state, "coordinator", None)
    if not coordinator:
        raise HTTPException(status_code=503, detail="Coordinator 未初始化完成，请稍后重试。")
    
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空。")
    
    return StreamingResponse(
        stream_analysis(text, req.case_id, coordinator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
