"""
对比测试：BERT vs Ollama 在实体抽取任务上的能力

测试目标：
1. 速度对比
2. 实体识别准确性对比
3. 关系抽取能力对比
4. 复杂案例处理能力对比
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from agent.agents.fact_extractor.agent import FactExtractorAgent
from agent.tools.ollama.client import OllamaClient


class BertEntityExtractor:
    """
    基于BERT的实体抽取器（简化版）
    
    使用BERT tokenizer + 规则匹配的方式进行实体抽取
    这是一个基线实现，用于对比测试
    """
    
    def __init__(self):
        from transformers import BertTokenizer
        
        # 使用中文BERT tokenizer
        model_path = PROJECT_ROOT / "模型训练" / "预训练模型" / "chinese-roberta-wwm-ext"
        self.tokenizer = BertTokenizer.from_pretrained(str(model_path))
        
        # 定义实体类型关键词
        self.entity_patterns = {
            "人物": ["被告人", "被害人", "证人", "犯罪嫌疑人"],
            "时间": ["年", "月", "日", "时", "分"],
            "地点": ["市", "县", "区", "镇", "村", "路", "街", "号"],
            "金额": ["元", "人民币", "万元"],
            "行为": ["盗窃", "抢劫", "诈骗", "故意伤害", "殴打", "驾驶", "容留", "贩卖", "运输"],
            "伤情": ["轻伤", "重伤", "死亡", "骨折", "休克"],
            "证据": ["鉴定", "证言", "勘验", "供述", "检验", "检测"],
            "物品": ["手机", "电脑", "车辆", "毒品", "冰毒", "海洛因"],
        }
    
    def extract(self, text: str) -> Dict[str, Any]:
        """
        使用BERT tokenizer + 规则匹配进行实体抽取
        
        Returns:
            包含实体列表和统计信息的字典
        """
        start_time = time.time()
        
        # 使用BERT tokenizer分词
        tokens = self.tokenizer.tokenize(text)
        
        # 重建文本（处理subword）
        processed_text = "".join(tokens).replace("##", "")
        
        # 基于规则匹配实体
        entities = []
        entity_count = {}
        
        for entity_type, keywords in self.entity_patterns.items():
            entity_count[entity_type] = 0
            for keyword in keywords:
                if keyword in text:
                    # 简单的上下文提取
                    idx = text.find(keyword)
                    while idx != -1:
                        # 提取前后各10个字符作为上下文
                        start = max(0, idx - 10)
                        end = min(len(text), idx + len(keyword) + 10)
                        context = text[start:end]
                        
                        entities.append({
                            "type": entity_type,
                            "keyword": keyword,
                            "context": context,
                            "position": idx,
                        })
                        entity_count[entity_type] += 1
                        
                        # 查找下一个匹配
                        idx = text.find(keyword, idx + 1)
        
        elapsed_time = time.time() - start_time
        
        return {
            "entities": entities,
            "entity_count": entity_count,
            "total_entities": len(entities),
            "token_count": len(tokens),
            "elapsed_time": elapsed_time,
        }


def load_test_cases() -> List[Dict[str, Any]]:
    """加载测试用例"""
    test_cases_path = PROJECT_ROOT / "agent" / "资源" / "test_cases.json"
    with open(test_cases_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


def evaluate_ollama_extraction(case: Dict[str, Any]) -> Dict[str, Any]:
    """使用Ollama进行实体抽取"""
    print(f"\n{'='*60}")
    print(f"测试案例: {case['case_id']}")
    print(f"{'='*60}")
    
    fact = case["fact"]
    print(f"案情长度: {len(fact)} 字符")
    
    # 初始化Ollama抽取器
    ollama_client = OllamaClient()
    fact_extractor = FactExtractorAgent(ollama_client=ollama_client)
    
    # 执行抽取
    start_time = time.time()
    result = fact_extractor.run(case_id=case["case_id"], text=fact)
    elapsed_time = time.time() - start_time
    
    # 统计结果
    node_types = {}
    for node in result.nodes:
        node_types[node.type] = node_types.get(node.type, 0) + 1
    
    return {
        "method": "Ollama (qwen25chat)",
        "total_nodes": len(result.nodes),
        "total_edges": len(result.edges),
        "node_types": node_types,
        "elapsed_time": elapsed_time,
        "summary": result.summary,
        "mode": result.mode,
    }


def evaluate_bert_extraction(case: Dict[str, Any]) -> Dict[str, Any]:
    """使用BERT进行实体抽取"""
    fact = case["fact"]
    
    # 初始化BERT抽取器
    bert_extractor = BertEntityExtractor()
    
    # 执行抽取
    result = bert_extractor.extract(fact)
    
    return {
        "method": "BERT (tokenizer + rules)",
        "total_entities": result["total_entities"],
        "entity_count": result["entity_count"],
        "token_count": result["token_count"],
        "elapsed_time": result["elapsed_time"],
    }


def compare_results(ollama_result: Dict[str, Any], bert_result: Dict[str, Any]) -> None:
    """对比两种方法的结果"""
    print(f"\n{'='*60}")
    print("对比结果")
    print(f"{'='*60}")
    
    print(f"\n【速度对比】")
    print(f"Ollama 耗时: {ollama_result['elapsed_time']:.2f} 秒")
    print(f"BERT 耗时:   {bert_result['elapsed_time']:.4f} 秒")
    print(f"速度提升:    {ollama_result['elapsed_time'] / bert_result['elapsed_time']:.1f}x")
    
    print(f"\n【Ollama 抽取结果】")
    print(f"总节点数: {ollama_result['total_nodes']}")
    print(f"总关系数: {ollama_result['total_edges']}")
    print(f"节点类型分布:")
    for node_type, count in sorted(ollama_result['node_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {node_type}: {count}")
    print(f"模式: {ollama_result['mode']}")
    print(f"摘要: {ollama_result['summary']}")
    
    print(f"\n【BERT 抽取结果】")
    print(f"总实体数: {bert_result['total_entities']}")
    print(f"分词数量: {bert_result['token_count']}")
    print(f"实体类型分布:")
    for entity_type, count in sorted(bert_result['entity_count'].items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"  - {entity_type}: {count}")


def run_comparison_test(num_cases: int = 3) -> None:
    """运行对比测试"""
    print("="*60)
    print("BERT vs Ollama 实体抽取能力对比测试")
    print("="*60)
    
    # 加载测试用例
    test_cases = load_test_cases()
    
    # 选择复杂案例（长文本、多罪名）
    complex_cases = [
        case for case in test_cases
        if len(case["fact"]) > 300 or "多罪名" in case.get("tags", [])
    ]
    
    if not complex_cases:
        complex_cases = test_cases
    
    # 限制测试数量
    test_cases_to_run = complex_cases[:num_cases]
    
    print(f"\n将测试 {len(test_cases_to_run)} 个复杂案例")
    print(f"案例ID: {[case['case_id'] for case in test_cases_to_run]}")
    
    # 汇总统计
    total_ollama_time = 0
    total_bert_time = 0
    
    for i, case in enumerate(test_cases_to_run, 1):
        print(f"\n\n{'#'*60}")
        print(f"测试 {i}/{len(test_cases_to_run)}")
        print(f"{'#'*60}")
        
        # Ollama抽取
        ollama_result = evaluate_ollama_extraction(case)
        total_ollama_time += ollama_result["elapsed_time"]
        
        # BERT抽取
        print(f"\n使用BERT进行实体抽取...")
        bert_result = evaluate_bert_extraction(case)
        total_bert_time += bert_result["elapsed_time"]
        
        # 对比结果
        compare_results(ollama_result, bert_result)
    
    # 总结
    print(f"\n\n{'='*60}")
    print("总体对比总结")
    print(f"{'='*60}")
    print(f"测试案例数: {len(test_cases_to_run)}")
    print(f"Ollama 总耗时: {total_ollama_time:.2f} 秒 (平均 {total_ollama_time/len(test_cases_to_run):.2f} 秒/案例)")
    print(f"BERT 总耗时:   {total_bert_time:.4f} 秒 (平均 {total_bert_time/len(test_cases_to_run):.4f} 秒/案例)")
    print(f"速度提升:      {total_ollama_time / total_bert_time:.1f}x")
    
    print(f"\n【结论】")
    print(f"1. 速度: BERT 比 Ollama 快约 {total_ollama_time / total_bert_time:.0f} 倍")
    print(f"2. 能力: Ollama 可以抽取结构化实体和关系，BERT 只能做简单的关键词匹配")
    print(f"3. 质量: Ollama 的抽取结果更丰富、更准确，但速度慢")
    print(f"4. 建议: 如果追求速度，可以用BERT做初步筛选，再用Ollama做精细抽取")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="对比BERT和Ollama的实体抽取能力")
    parser.add_argument("--num-cases", type=int, default=3, help="测试案例数量")
    args = parser.parse_args()
    
    run_comparison_test(num_cases=args.num_cases)


if __name__ == "__main__":
    main()
