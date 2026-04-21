"""
测试 Ollama 集成的 Agent 功能。

运行前请确保：
1. Ollama 服务已启动（ollama serve）
2. 已拉取模型（ollama pull qwen25chat:latest）
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.tools.ollama.client import OllamaClient
from agent.agents.fact_extractor.agent import FactExtractorAgent
from agent.agents.report_generator.agent import ReportGeneratorAgent
from agent.schemas.contracts import ChargePrediction


def print_separator(title: str = ""):
    """打印分隔线。"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'-'*60}\n")


def test_ollama_connection():
    """测试 Ollama 服务连接。"""
    print_separator("测试 1: Ollama 服务连接")
    
    try:
        client = OllamaClient()
        is_healthy = client.health_check()
        
        if is_healthy:
            print("✓ Ollama 服务连接成功")
            print(f"  服务地址: {client.base_url}")
            print(f"  默认模型: {client.model}")
            return True
        else:
            print("✗ Ollama 服务不可用")
            print("  请确保 Ollama 服务已启动：ollama serve")
            return False
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False


def test_ollama_generate():
    """测试 Ollama 文本生成。"""
    print_separator("测试 2: Ollama 文本生成")
    
    try:
        client = OllamaClient()
        
        print("发送测试提示词...")
        start_time = time.time()
        
        response = client.generate(
            prompt="请用一句话介绍你自己。",
            system="你是一个法律分析助手。",
            temperature=0.7,
        )
        
        elapsed = time.time() - start_time
        
        print(f"✓ 生成成功（耗时 {elapsed:.2f} 秒）")
        print(f"  响应: {response[:100]}...")
        return True
    except Exception as e:
        print(f"✗ 生成失败: {e}")
        return False


def test_ollama_json_generate():
    """测试 Ollama JSON 格式生成。"""
    print_separator("测试 3: Ollama JSON 格式生成")
    
    try:
        client = OllamaClient()
        
        print("发送 JSON 格式请求...")
        start_time = time.time()
        
        response = client.generate_json(
            prompt='请生成一个包含 name 和 age 字段的 JSON 对象，name 为"张三"，age 为 30。',
            temperature=0.3,
        )
        
        elapsed = time.time() - start_time
        
        print(f"✓ JSON 生成成功（耗时 {elapsed:.2f} 秒）")
        print(f"  响应: {response}")
        return True
    except Exception as e:
        print(f"✗ JSON 生成失败: {e}")
        return False


def test_fact_extractor():
    """测试 FactExtractorAgent。"""
    print_separator("测试 4: FactExtractorAgent 实体关系抽取")
    
    # 测试案例
    test_case = """被告人张某于2023年1月15日晚9时许，在某市某区某路口，
酒后驾驶机动车，被公安机关当场查获。经检测，其血液酒精含量为150mg/100ml，
属于醉酒驾驶。案发后，张某如实供述了自己的犯罪事实。"""
    
    try:
        print("案情文本:")
        print(f"  {test_case[:80]}...")
        print()
        
        agent = FactExtractorAgent()
        
        print("开始抽取实体和关系...")
        start_time = time.time()
        
        result = agent.run(case_id="test-001", text=test_case)
        
        elapsed = time.time() - start_time
        
        print(f"✓ 抽取成功（耗时 {elapsed:.2f} 秒）")
        print(f"  模式: {result.mode}")
        print(f"  摘要: {result.summary}")
        print(f"  节点数: {len(result.nodes)}")
        print(f"  关系数: {len(result.edges)}")
        
        # 显示部分节点
        if result.nodes:
            print("\n  抽取的节点示例:")
            for node in result.nodes[:5]:
                print(f"    - [{node.type}] {node.label}")
        
        # 显示部分关系
        if result.edges:
            print("\n  抽取的关系示例:")
            for edge in result.edges[:5]:
                print(f"    - {edge.relation}: {edge.source} -> {edge.target}")
        
        return True
    except Exception as e:
        print(f"✗ 抽取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_generator():
    """测试 ReportGeneratorAgent。"""
    print_separator("测试 5: ReportGeneratorAgent 报告生成与自审")
    
    # 测试案例
    test_case = """被告人李某于2023年3月10日下午，在某商场内盗窃手机一部，
价值人民币5000元。被害人王某发现后报警，李某被当场抓获。
经查，李某有盗窃前科，属于累犯。"""
    
    try:
        print("案情文本:")
        print(f"  {test_case[:80]}...")
        print()
        
        # 先进行事实抽取
        print("步骤 1: 事实抽取...")
        fact_agent = FactExtractorAgent()
        fact_result = fact_agent.run(case_id="test-002", text=test_case)
        print(f"  ✓ 抽取完成: {len(fact_result.nodes)} 个节点")
        
        # 模拟罪名预测结果
        predictions = [
            ChargePrediction(label="盗窃", probability=0.92, rank=1),
            ChargePrediction(label="抢劫", probability=0.05, rank=2),
        ]
        
        print("\n步骤 2: 生成报告...")
        report_agent = ReportGeneratorAgent()
        
        start_time = time.time()
        
        result = report_agent.run(
            text=test_case,
            predictions=predictions,
            nodes=fact_result.nodes,
        )
        
        elapsed = time.time() - start_time
        
        print(f"✓ 报告生成成功（耗时 {elapsed:.2f} 秒）")
        print(f"  摘要: {result.summary}")
        print("\n生成的报告:")
        print("-" * 60)
        print(result.report)
        print("-" * 60)
        
        return True
    except Exception as e:
        print(f"✗ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complete_workflow():
    """测试完整工作流。"""
    print_separator("测试 6: 完整工作流测试")
    
    # 复杂案例
    test_case = """被告人赵某因琐事与被害人孙某发生口角，后持石头击打孙某头部，
致孙某右额部粉碎性骨折，经鉴定为轻伤一级。案发时间为2023年5月20日晚8时许，
地点为某县某镇某村。案发后，赵某主动投案，如实供述了犯罪事实。
被害人孙某要求赔偿医疗费等损失共计人民币30000元。"""
    
    try:
        print("测试案例:")
        print(f"  {test_case}")
        print()
        
        total_start = time.time()
        
        # 1. 事实抽取
        print("步骤 1/2: 事实抽取...")
        fact_agent = FactExtractorAgent()
        fact_result = fact_agent.run(case_id="test-003", text=test_case)
        print(f"  ✓ 完成: {len(fact_result.nodes)} 节点, {len(fact_result.edges)} 关系")
        
        # 2. 报告生成
        print("\n步骤 2/2: 报告生成...")
        predictions = [
            ChargePrediction(label="故意伤害", probability=0.95, rank=1),
        ]
        
        report_agent = ReportGeneratorAgent()
        report_result = report_agent.run(
            text=test_case,
            predictions=predictions,
            nodes=fact_result.nodes,
        )
        
        total_elapsed = time.time() - total_start
        
        print(f"  ✓ 完成")
        print(f"\n✓ 完整流程测试成功（总耗时 {total_elapsed:.2f} 秒）")
        
        print("\n最终报告:")
        print("=" * 60)
        print(report_result.report)
        print("=" * 60)
        
        return True
    except Exception as e:
        print(f"✗ 完整流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试。"""
    print("\n" + "=" * 60)
    print("  Ollama Agent 功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试 1: 连接测试
    results.append(("Ollama 连接", test_ollama_connection()))
    
    if not results[0][1]:
        print("\n" + "=" * 60)
        print("  测试终止: Ollama 服务不可用")
        print("  请先启动 Ollama 服务: ollama serve")
        print("=" * 60)
        return
    
    # 测试 2: 文本生成
    results.append(("文本生成", test_ollama_generate()))
    
    # 测试 3: JSON 生成
    results.append(("JSON 生成", test_ollama_json_generate()))
    
    # 测试 4: 事实抽取
    results.append(("事实抽取", test_fact_extractor()))
    
    # 测试 5: 报告生成
    results.append(("报告生成", test_report_generator()))
    
    # 测试 6: 完整流程
    results.append(("完整流程", test_complete_workflow()))
    
    # 汇总结果
    print_separator("测试结果汇总")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}  {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
