"""
测试混合方案A的 FactExtractorAgent
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from agent.agents.fact_extractor.agent import FactExtractorAgent


def test_hybrid_extraction():
    """测试混合方案A"""
    print("="*80)
    print("测试混合方案A：UIE实体 + Qwen关系")
    print("="*80)
    print()
    
    # 测试案例
    test_text = """
    2016年5月29日19时许，被告人杨某1伙同杨某2（另案处理）在霞浦县牙城镇中心小学旁造福工程小区3号楼302室内，
    盗窃被害人李某1的现金人民币19000元、步步高手机1台（经霞浦县价格认证中心鉴定，价值人民币1000元）。
    """
    
    # 初始化 Agent
    print("初始化 FactExtractorAgent（混合方案A）...")
    agent = FactExtractorAgent(use_uie=True, enable_cache=False)
    print()
    
    # 执行抽取
    print("执行事实抽取...")
    result = agent.run(case_id="test-001", text=test_text)
    print()
    
    # 显示结果
    print("="*80)
    print("抽取结果")
    print("="*80)
    print(f"\n{result.summary}\n")
    
    print(f"节点数: {len(result.nodes)}")
    print(f"边数: {len(result.edges)}")
    print(f"模式: {result.mode}")
    print()
    
    print("实体节点（前10个）:")
    for node in result.nodes[:10]:
        if node.type != "案件":
            print(f"  - [{node.type}] {node.label}")
    print()
    
    print("关系边（前10条）:")
    for edge in result.edges[:10]:
        source_node = next((n for n in result.nodes if n.id == edge.source), None)
        target_node = next((n for n in result.nodes if n.id == edge.target), None)
        if source_node and target_node:
            print(f"  - {source_node.label} --[{edge.relation}]--> {target_node.label}")
    print()
    
    print("="*80)
    print("✓ 测试完成")
    print("="*80)


if __name__ == "__main__":
    test_hybrid_extraction()
