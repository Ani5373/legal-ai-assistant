"""
ChargePredictorAgent 主干版。
"""

from __future__ import annotations

from agent.schemas.contracts import ChargePredictionResult
from agent.tools.bert_predictor.tool import BertChargePredictorTool


class ChargePredictorAgent:
    """将本地 BERT Tool 接入 Coordinator。"""

    name = "ChargePredictorAgent"

    def __init__(self, bert_tool: BertChargePredictorTool) -> None:
        self.bert_tool = bert_tool

    def run(self, text: str) -> ChargePredictionResult:
        predictions = self.bert_tool.predict(text)
        if predictions:
            top_label = predictions[0].label
            summary = f"已完成罪名预测，当前最高候选为 {top_label}。"
        else:
            summary = "当前未得到有效罪名预测结果。"
        return ChargePredictionResult(
            predictions=predictions,
            summary=summary,
            threshold=self.bert_tool.threshold,
        )
