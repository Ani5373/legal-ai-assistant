"""
模型加载服务
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from transformers import BertTokenizer

from agent.tools.bert_predictor.tool import BertChargePredictorTool
from agent.tools.law_lookup.tool import LocalLawLookupTool


def load_label_mapping(label_mapping_path: Path) -> Tuple[List[str], int]:
    """
    加载标签映射

    Args:
        label_mapping_path: 标签映射文件路径

    Returns:
        (id2label列表, 类别数量)
    """
    if not label_mapping_path.exists():
        raise FileNotFoundError(f"未找到标签映射文件：{label_mapping_path}")

    with open(label_mapping_path, encoding="utf-8") as f:
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


def resolve_runtime_path(
    path_value: str | Path, fallback: Path, legacy_map: Dict[str, Path]
) -> Path:
    """
    解析运行时路径，兼容旧的相对路径

    Args:
        path_value: 路径值
        fallback: 回退路径
        legacy_map: 旧路径映射

    Returns:
        解析后的路径
    """
    candidate = Path(path_value)
    if candidate.exists():
        return candidate

    normalized = str(candidate).replace("\\", "/").lstrip("./")
    if normalized in legacy_map:
        return legacy_map[normalized]

    if not candidate.is_absolute():
        # 尝试从项目根目录解析
        from 服务端.core.config import get_settings

        settings = get_settings()
        project_candidate = settings.PROJECT_ROOT / normalized
        if project_candidate.exists():
            return project_candidate

    return fallback


def load_bert_model(
    weights_path: Path,
    label_mapping_path: Path,
    device: torch.device,
    project_root: Path,
) -> Tuple[Any, BertTokenizer, BertChargePredictorTool, List[str]]:
    """
    加载 BERT 模型

    Args:
        weights_path: 权重文件路径
        label_mapping_path: 标签映射文件路径
        device: 设备
        project_root: 项目根目录

    Returns:
        (模型, tokenizer, BERT工具, id2label)
    """
    # 动态导入以避免循环依赖
    import sys

    training_code_dir = project_root / "模型训练" / "BERT罪名训练" / "scripts"
    sys.path.insert(0, str(training_code_dir))

    from train import HierarchicalRoBERTa

    if not weights_path.exists():
        raise RuntimeError(
            f"未找到权重文件：{weights_path}\n"
            "请确保训练脚本已生成 best_model.pt，且路径与配置一致。"
        )

    id2label, num_classes_from_labels = load_label_mapping(label_mapping_path)

    # 加载 checkpoint
    checkpoint = torch.load(weights_path, map_location="cpu", weights_only=False)
    config: Dict[str, Any] = checkpoint.get("config", {}) or {}

    # 解析配置
    default_tokenizer_path = project_root / "模型训练" / "预训练模型" / "chinese-roberta-wwm-ext"
    default_weights_path = project_root / "模型训练" / "训练输出" / "best_model.pt"
    default_label_mapping_path = (
        project_root / "模型训练" / "处理后数据" / "label_mapping.json"
    )

    legacy_map = {
        "models/chinese-roberta-wwm-ext": default_tokenizer_path,
        "saved_models/best_model.pt": default_weights_path,
        "data/processed/label_mapping.json": default_label_mapping_path,
    }

    model_path = str(
        resolve_runtime_path(
            config.get("model_path", str(default_tokenizer_path)),
            default_tokenizer_path,
            legacy_map,
        )
    )
    max_chunk_length = int(config.get("max_chunk_length", 510))
    max_chunks = int(config.get("max_chunks", 3))
    dropout = float(config.get("dropout", 0.1))

    num_classes = int(config.get("num_classes", num_classes_from_labels))
    if num_classes != num_classes_from_labels:
        num_classes = num_classes_from_labels

    # 加载 tokenizer
    tokenizer = BertTokenizer.from_pretrained(model_path)

    # 创建模型
    model = HierarchicalRoBERTa(
        model_path=model_path,
        num_classes=num_classes,
        dropout=dropout,
    )
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(device)
    model.eval()

    # 创建 BERT 工具
    bert_tool = BertChargePredictorTool(
        model=model,
        tokenizer=tokenizer,
        device=device,
        max_chunk_length=max_chunk_length,
        max_chunks=max_chunks,
        id2label=id2label,
    )

    return model, tokenizer, bert_tool, id2label


def load_law_lookup_tool(law_knowledge_base_path: Path) -> LocalLawLookupTool:
    """
    加载法条检索工具

    Args:
        law_knowledge_base_path: 法条知识库路径

    Returns:
        法条检索工具
    """
    return LocalLawLookupTool(law_knowledge_base_path)
