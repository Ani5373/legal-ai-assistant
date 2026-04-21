"""
测试所有 Agent 和工具的导入是否正常。
"""

def test_imports():
    """测试所有模块导入。"""
    print("测试导入...")
    
    # 测试 schemas
    try:
        from agent.schemas.contracts import (
            AnalysisRequest,
            CaseAnalysisResponse,
            ChargePrediction,
            GraphNode,
            GraphEdge,
            ExecutionStep,
            FactExtractionResult,
            ChargePredictionResult,
            LawRetrievalResult,
            ReportGenerationResult,
        )
        print("✓ schemas.contracts 导入成功")
    except Exception as e:
        print(f"✗ schemas.contracts 导入失败: {e}")
        return False
    
    # 测试 Ollama 工具
    try:
        from agent.tools.ollama.client import OllamaClient
        print("✓ tools.ollama.client 导入成功")
    except Exception as e:
        print(f"✗ tools.ollama.client 导入失败: {e}")
        return False
    
    # 测试 FactExtractorAgent
    try:
        from agent.agents.fact_extractor.agent import FactExtractorAgent
        print("✓ agents.fact_extractor.agent 导入成功")
    except Exception as e:
        print(f"✗ agents.fact_extractor.agent 导入失败: {e}")
        return False
    
    # 测试 ReportGeneratorAgent
    try:
        from agent.agents.report_generator.agent import ReportGeneratorAgent
        print("✓ agents.report_generator.agent 导入成功")
    except Exception as e:
        print(f"✗ agents.report_generator.agent 导入失败: {e}")
        return False
    
    # 测试 ChargePredictorAgent
    try:
        from agent.agents.charge_predictor.agent import ChargePredictorAgent
        print("✓ agents.charge_predictor.agent 导入成功")
    except Exception as e:
        print(f"✗ agents.charge_predictor.agent 导入失败: {e}")
        return False
    
    # 测试 LawRetrieverAgent
    try:
        from agent.agents.law_retriever.agent import LawRetrieverAgent
        print("✓ agents.law_retriever.agent 导入成功")
    except Exception as e:
        print(f"✗ agents.law_retriever.agent 导入失败: {e}")
        return False
    
    # 测试 Coordinator
    try:
        from agent.coordinator.engine import CaseAnalysisCoordinator
        print("✓ coordinator.engine 导入成功")
    except Exception as e:
        print(f"✗ coordinator.engine 导入失败: {e}")
        return False
    
    # 测试 BERT 工具
    try:
        from agent.tools.bert_predictor.tool import BertChargePredictorTool
        print("✓ tools.bert_predictor.tool 导入成功")
    except Exception as e:
        print(f"✗ tools.bert_predictor.tool 导入失败: {e}")
        return False
    
    # 测试法条检索工具
    try:
        from agent.tools.law_lookup.tool import LawKnowledgeBaseTool
        print("✓ tools.law_lookup.tool 导入成功")
    except Exception as e:
        print(f"✗ tools.law_lookup.tool 导入失败: {e}")
        return False
    
    print("\n所有模块导入测试通过！✓")
    return True


if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)
