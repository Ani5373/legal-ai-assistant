"""
预测服务
"""

from typing import List

from agent.tools.bert_predictor.tool import BertChargePredictorTool
from 服务端.schemas.responses import PredictionItem


class PredictionService:
    """BERT 罪名预测服务"""

    def __init__(self, bert_tool: BertChargePredictorTool):
        self.bert_tool = bert_tool

    def predict(self, text: str) -> List[PredictionItem]:
        """
        预测罪名

        Args:
            text: 案情描述文本

        Returns:
            预测结果列表
        """
        predictions = self.bert_tool.predict(text)
        return [
            PredictionItem(label=item.label, probability=item.probability)
            for item in predictions
        ]
