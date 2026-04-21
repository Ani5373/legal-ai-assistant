"""
FastAPI 后端推理服务

启动示例（项目根目录下执行）：
  cd 服务端
  uvicorn app:app --reload --port 8111

接口：
  POST /api/predict
  请求体：{"text": "这是一段案情描述..."}
  返回 Top-3 罪名及对应概率
"""

from __future__ import annotations

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import BertTokenizer

SERVICE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVICE_DIR.parent
TRAINING_CODE_DIR = PROJECT_ROOT / "模型训练" / "BERT罪名训练" / "scripts"
AGENT_RESOURCE_DIR = PROJECT_ROOT / "agent" / "资源"
# 保险起见：即使 uvicorn 的工作目录变化，也能稳定导入 train.py
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TRAINING_CODE_DIR))

from agent.agents.charge_predictor.agent import ChargePredictorAgent  # noqa: E402
from agent.agents.fact_extractor.agent import FactExtractorAgent  # noqa: E402
from agent.agents.law_retriever.agent import LawRetrieverAgent  # noqa: E402
from agent.agents.report_generator.agent import ReportGeneratorAgent  # noqa: E402
from agent.coordinator.engine import CaseAnalysisCoordinator  # noqa: E402
from agent.schemas.contracts import AnalysisRequest, CaseAnalysisResponse  # noqa: E402
from agent.tools.bert_predictor.tool import BertChargePredictorTool  # noqa: E402
from agent.tools.law_lookup.tool import LocalLawLookupTool  # noqa: E402
from train import HierarchicalRoBERTa  # noqa: E402


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="案情描述文本")


class PredictionItem(BaseModel):
    label: str
    probability: float


class PredictResponse(BaseModel):
    predictions: List[PredictionItem]


DEFAULT_WEIGHTS_PATH = PROJECT_ROOT / "模型训练" / "训练输出" / "best_model.pt"
DEFAULT_LABEL_MAPPING_PATH = PROJECT_ROOT / "模型训练" / "处理后数据" / "label_mapping.json"
DEFAULT_TOKENIZER_MODEL_PATH = PROJECT_ROOT / "模型训练" / "预训练模型" / "chinese-roberta-wwm-ext"

DEFAULT_LAW_KNOWLEDGE_BASE_PATH = AGENT_RESOURCE_DIR / "law_knowledge_base.json"


def _load_label_mapping(label_mapping_path: Path) -> Tuple[List[str], int]:
    if not label_mapping_path.exists():
        raise FileNotFoundError(f"未找到标签映射文件：{label_mapping_path}")

    with open(label_mapping_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "id2label" in data:
        id2label_obj = data["id2label"]
        num_classes = int(data.get("num_classes", len(id2label_obj)))
        id2label = [id2label_obj[str(i)] for i in range(num_classes)]
        return id2label, num_classes

    if "label2id" in data:
        label2id = data["label2id"]
        num_classes = int(data.get("num_classes", len(label2id)))
        id2label = [""] * num_classes
        for label, idx in label2id.items():
            id2label[int(idx)] = label
        return id2label, num_classes

    raise ValueError(f"标签映射文件缺少 id2label/label2id 字段：{label_mapping_path}")


def _resolve_runtime_path(path_value: str | Path, fallback: Path) -> Path:
    """
    兼容目录重组前写进 checkpoint 配置里的旧相对路径。
    """
    candidate = Path(path_value)
    if candidate.exists():
        return candidate

    normalized = str(candidate).replace("\\", "/").lstrip("./")
    legacy_map = {
        "models/chinese-roberta-wwm-ext": DEFAULT_TOKENIZER_MODEL_PATH,
        "saved_models/best_model.pt": DEFAULT_WEIGHTS_PATH,
        "data/processed/label_mapping.json": DEFAULT_LABEL_MAPPING_PATH,
    }
    if normalized in legacy_map:
        return legacy_map[normalized]

    if not candidate.is_absolute():
        project_candidate = PROJECT_ROOT / normalized
        if project_candidate.exists():
            return project_candidate

    return fallback


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    weights_path = Path(os.getenv("MODEL_WEIGHTS_PATH", str(DEFAULT_WEIGHTS_PATH)))
    label2id_path = Path(
        os.getenv(
            "LABEL2ID_PATH",
            str(PROJECT_ROOT / "模型训练" / "处理后数据" / "label2id.json"),
        )
    )
    label_mapping_path = Path(os.getenv("LABEL_MAPPING_PATH", str(DEFAULT_LABEL_MAPPING_PATH)))

    resolved_label_path = label2id_path if label2id_path.exists() else label_mapping_path

    if not weights_path.exists():
        raise RuntimeError(
            f"未找到权重文件：{weights_path}\n"
            "请确保训练脚本已生成 best_model.pt，且路径与 app.py 默认值一致。"
        )

    id2label, num_classes_from_labels = _load_label_mapping(resolved_label_path)

    # PyTorch 2.6+ 默认 weights_only=True 可能导致旧 checkpoint 反序列化失败；
    # 你的权重文件是本地可信来源，因此显式关闭。
    checkpoint = torch.load(weights_path, map_location="cpu", weights_only=False)
    config: Dict[str, Any] = checkpoint.get("config", {}) or {}

    model_path = str(_resolve_runtime_path(config.get("model_path", str(DEFAULT_TOKENIZER_MODEL_PATH)), DEFAULT_TOKENIZER_MODEL_PATH))
    max_chunk_length = int(config.get("max_chunk_length", 510))
    max_chunks = int(config.get("max_chunks", 3))
    dropout = float(config.get("dropout", 0.1))

    num_classes = int(config.get("num_classes", num_classes_from_labels))
    if num_classes != num_classes_from_labels:
        num_classes = num_classes_from_labels

    tokenizer = BertTokenizer.from_pretrained(model_path)

    model = HierarchicalRoBERTa(
        model_path=model_path,
        num_classes=num_classes,
        dropout=dropout,
    )
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(device)
    model.eval()

    app.state.device = device
    app.state.model = model
    app.state.tokenizer = tokenizer
    app.state.max_chunk_length = max_chunk_length
    app.state.max_chunks = max_chunks
    app.state.id2label = id2label
    app.state.bert_tool = BertChargePredictorTool(
        model=model,
        tokenizer=tokenizer,
        device=device,
        max_chunk_length=max_chunk_length,
        max_chunks=max_chunks,
        id2label=id2label,
    )
    app.state.law_lookup_tool = LocalLawLookupTool(DEFAULT_LAW_KNOWLEDGE_BASE_PATH)
    app.state.coordinator = CaseAnalysisCoordinator(
        fact_extractor=FactExtractorAgent(),
        charge_predictor=ChargePredictorAgent(app.state.bert_tool),
        law_retriever=LawRetrieverAgent(app.state.law_lookup_tool),
        report_generator=ReportGeneratorAgent(),
        enable_security_check=False,  # 禁用安全检查
    )

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/predict", response_model=PredictResponse)
async def predict(req: PredictRequest) -> Dict[str, Any]:
    if not getattr(app.state, "bert_tool", None):
        raise HTTPException(status_code=503, detail="模型未加载完成，请稍后重试。")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空。")

    predictions = [
        {"label": item.label, "probability": item.probability}
        for item in app.state.bert_tool.predict(text)
    ]
    return {"predictions": predictions}


@app.post("/api/analyze", response_model=CaseAnalysisResponse)
async def analyze(req: AnalysisRequest) -> CaseAnalysisResponse:
    if not getattr(app.state, "coordinator", None):
        raise HTTPException(status_code=503, detail="Coordinator 未初始化完成，请稍后重试。")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空。")

    return app.state.coordinator.analyze(text=text, case_id=req.case_id)


@app.post("/api/analyze/stream")
async def analyze_stream(req: AnalysisRequest):
    """流式分析接口，分阶段返回结果"""
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    if not getattr(app.state, "coordinator", None):
        raise HTTPException(status_code=503, detail="Coordinator 未初始化完成，请稍后重试。")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空。")

    async def generate():
        coordinator = app.state.coordinator
        case_id = req.case_id
        
        try:
            # 流式调用协调器
            async for chunk in coordinator.analyze_stream(text=text, case_id=case_id):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)  # 让出控制权
        except Exception as e:
            error_chunk = {
                "type": "error",
                "message": f"分析失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


class SimilarCaseRequest(BaseModel):
    charges: List[str] = Field(..., description="罪名列表")
    limit: int = Field(default=3, ge=1, le=10, description="返回数量")


class SimilarCaseItem(BaseModel):
    case_id: str
    text: str
    charges: List[str]
    similarity_score: float


class SimilarCaseResponse(BaseModel):
    similar_cases: List[SimilarCaseItem]


@app.post("/api/similar-cases", response_model=SimilarCaseResponse)
async def get_similar_cases(req: SimilarCaseRequest) -> Dict[str, Any]:
    """根据罪名推荐类案"""
    from agent.memory.core.memory_manager import MemoryManager
    
    memory_manager = MemoryManager()
    recent_cases = memory_manager.list_recent(limit=50)
    
    similar_cases = []
    for entry in recent_cases:
        # 加载案件详情
        topic_memory = memory_manager.retrieve(entry.case_id)
        if not topic_memory:
            continue
        
        # 提取案件的罪名
        case_charges = [pred.label for pred in topic_memory.predictions[:3]]
        
        # 计算相似度（基于罪名交集）
        if not case_charges:
            continue
        
        common_charges = set(req.charges) & set(case_charges)
        similarity = len(common_charges) / max(len(req.charges), len(case_charges))
        
        if similarity > 0:
            similar_cases.append({
                "case_id": topic_memory.case_id,
                "text": topic_memory.text[:200] + ("..." if len(topic_memory.text) > 200 else ""),
                "charges": case_charges,
                "similarity_score": round(similarity, 3)
            })
    
    # 按相似度排序并返回前N个
    similar_cases.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return {"similar_cases": similar_cases[:req.limit]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8111, reload=True)
