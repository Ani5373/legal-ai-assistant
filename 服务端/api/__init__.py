"""
API 路由模块
"""

from fastapi import APIRouter

from 服务端.api.analyze import router as analyze_router
from 服务端.api.predict import router as predict_router

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(predict_router, tags=["预测"])
api_router.include_router(analyze_router, tags=["分析"])

__all__ = ["api_router"]
