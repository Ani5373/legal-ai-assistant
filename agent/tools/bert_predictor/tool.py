"""
将现有 BERT 多标签罪名预测逻辑包装成可复用 Tool。
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import torch
from transformers import BertTokenizer

from agent.schemas.contracts import ChargePrediction


def build_hierarchical_inputs(
    text: str,
    tokenizer: BertTokenizer,
    max_chunk_length: int,
    max_chunks: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """将长文本切块后编码为层次化 BERT 输入。"""
    tokens = tokenizer.tokenize(text)

    chunked_tokens: List[List[str]] = []
    for index in range(0, len(tokens), max_chunk_length):
        chunked_tokens.append(tokens[index : index + max_chunk_length])
        if len(chunked_tokens) >= max_chunks:
            break

    max_len = max_chunk_length + 2
    chunk_input_ids: List[List[int]] = []
    chunk_attention_masks: List[List[int]] = []

    for chunk in chunked_tokens:
        chunk_with_special = ["[CLS]"] + chunk + ["[SEP]"]
        input_ids = tokenizer.convert_tokens_to_ids(chunk_with_special)
        attention_mask = [1] * len(input_ids)

        if len(input_ids) < max_len:
            pad_len = max_len - len(input_ids)
            input_ids += [0] * pad_len
            attention_mask += [0] * pad_len

        chunk_input_ids.append(input_ids[:max_len])
        chunk_attention_masks.append(attention_mask[:max_len])

    while len(chunk_input_ids) < max_chunks:
        chunk_input_ids.append([0] * max_len)
        chunk_attention_masks.append([0] * max_len)

    return (
        torch.tensor([chunk_input_ids], dtype=torch.long),
        torch.tensor([chunk_attention_masks], dtype=torch.long),
    )


class BertChargePredictorTool:
    """对当前本地加载的 HierarchicalRoBERTa 模型进行包装。"""

    def __init__(
        self,
        model: torch.nn.Module,
        tokenizer: BertTokenizer,
        device: torch.device,
        max_chunk_length: int,
        max_chunks: int,
        id2label: Sequence[str],
        threshold: float = 0.5,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.max_chunk_length = max_chunk_length
        self.max_chunks = max_chunks
        self.id2label = list(id2label)
        self.threshold = threshold

    def predict(self, text: str) -> List[ChargePrediction]:
        """执行多标签罪名预测。"""
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        input_ids, attention_mask = build_hierarchical_inputs(
            text=cleaned_text,
            tokenizer=self.tokenizer,
            max_chunk_length=self.max_chunk_length,
            max_chunks=self.max_chunks,
        )
        input_ids = input_ids.to(self.device)
        attention_mask = attention_mask.to(self.device)

        with torch.no_grad():
            logits, _ = self.model(input_ids, attention_mask)
            probs = torch.sigmoid(logits).squeeze(0)

        predictions: List[ChargePrediction] = []
        for idx, prob in enumerate(probs.tolist()):
            if prob >= self.threshold:
                predictions.append(
                    ChargePrediction(
                        label=self.id2label[idx],
                        probability=round(float(prob), 6),
                    )
                )

        if not predictions:
            top_probs, top_indices = torch.topk(
                probs,
                k=min(3, probs.size(0)),
                largest=True,
                sorted=True,
            )
            for prob, idx in zip(top_probs.tolist(), top_indices.tolist()):
                predictions.append(
                    ChargePrediction(
                        label=self.id2label[int(idx)],
                        probability=round(float(prob), 6),
                    )
                )

        predictions.sort(key=lambda item: item.probability, reverse=True)
        for rank, item in enumerate(predictions, start=1):
            item.rank = rank
        return predictions
