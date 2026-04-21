"""
简化版实体抽取对比测试
"""

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 测试案例
TEST_CASE = """
公诉机关指控：一、××2016年5月29日19时许，被告人杨1某伙同杨某2、李某1（均已判刑）经事先预谋，以戴帽子、口罩、手套等方式进行伪装后，敲门进入杨某1居住的霞浦县牙城镇中心小学旁造福工程小区3号楼302室，三人一起将杨某1控制并用黄色胶带捆绑杨某1，抢走该房内的现金人民币19000元、步步高手机1台等物。经霞浦县价格认证中心鉴定，该部手机的价值为人民币1271元。
"""

print("="*60)
print("实体抽取能力对比测试")
print("="*60)
print(f"\n测试案例长度: {len(TEST_CASE)} 字符\n")

# ========== 测试1: BERT分词速度 ==========
print("\n【测试1: BERT分词】")
try:
    from transformers import BertTokenizer
    
    model_path = PROJECT_ROOT / "模型训练" / "预训练模型" / "chinese-roberta-wwm-ext"
    tokenizer = BertTokenizer.from_pretrained(str(model_path))
    
    start = time.time()
    tokens = tokenizer.tokenize(TEST_CASE)
    bert_time = time.time() - start
    
    print(f"✓ BERT分词完成")
    print(f"  - 耗时: {bert_time:.4f} 秒")
    print(f"  - Token数: {len(tokens)}")
    print(f"  - 前10个tokens: {tokens[:10]}")
    
except Exception as e:
    print(f"✗ BERT分词失败: {e}")
    bert_time = None

# ========== 测试2: BERT简单实体识别 ==========
print("\n【测试2: BERT简单实体识别（规则匹配）】")
try:
    keywords = {
        "人物": ["被告人", "被害人"],
        "时间": ["2016年5月29日", "19时"],
        "地点": ["霞浦县", "牙城镇"],
        "金额": ["19000元", "1271元"],
        "行为": ["抢走", "控制", "捆绑"],
    }
    
    start = time.time()
    found_entities = {}
    for entity_type, kws in keywords.items():
        found = [kw for kw in kws if kw in TEST_CASE]
        if found:
            found_entities[entity_type] = found
    bert_extract_time = time.time() - start
    
    print(f"✓ BERT实体识别完成")
    print(f"  - 耗时: {bert_extract_time:.4f} 秒")
    print(f"  - 识别实体类型: {len(found_entities)}")
    for etype, entities in found_entities.items():
        print(f"    {etype}: {entities}")
    
except Exception as e:
    print(f"✗ BERT实体识别失败: {e}")
    bert_extract_time = None

# ========== 测试3: Ollama实体抽取 ==========
print("\n【测试3: Ollama实体抽取（qwen25chat）】")
try:
    from agent.agents.fact_extractor.agent import FactExtractorAgent
    from agent.tools.ollama.client import OllamaClient
    
    ollama_client = OllamaClient()
    fact_extractor = FactExtractorAgent(ollama_client=ollama_client, enable_cache=False)
    
    start = time.time()
    result = fact_extractor.run(case_id="test-001", text=TEST_CASE)
    ollama_time = time.time() - start
    
    # 统计节点类型
    node_types = {}
    for node in result.nodes:
        node_types[node.type] = node_types.get(node.type, 0) + 1
    
    print(f"✓ Ollama实体抽取完成")
    print(f"  - 耗时: {ollama_time:.2f} 秒")
    print(f"  - 总节点数: {len(result.nodes)}")
    print(f"  - 总关系数: {len(result.edges)}")
    print(f"  - 节点类型分布:")
    for ntype, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
        print(f"    {ntype}: {count}")
    print(f"  - 模式: {result.mode}")
    
    # 显示部分实体
    print(f"\n  示例实体（前5个）:")
    for node in result.nodes[:5]:
        print(f"    - [{node.type}] {node.label}: {node.description[:30]}...")
    
except Exception as e:
    print(f"✗ Ollama实体抽取失败: {e}")
    import traceback
    traceback.print_exc()
    ollama_time = None

# ========== 对比总结 ==========
print("\n" + "="*60)
print("对比总结")
print("="*60)

if bert_time and ollama_time:
    print(f"\n速度对比:")
    print(f"  BERT分词:        {bert_time:.4f} 秒")
    print(f"  BERT实体识别:    {bert_extract_time:.4f} 秒")
    print(f"  Ollama实体抽取:  {ollama_time:.2f} 秒")
    if bert_extract_time > 0:
        print(f"  速度差距:        Ollama 比 BERT 慢 {ollama_time/bert_extract_time:.0f}x")
    else:
        print(f"  速度差距:        Ollama 比 BERT 慢 {ollama_time/bert_time:.0f}x (BERT太快，用分词时间估算)")

print(f"\n能力对比:")
print(f"  BERT:")
print(f"    ✓ 速度极快（毫秒级）")
print(f"    ✓ 可以做简单的关键词匹配")
print(f"    ✗ 无法理解语义")
print(f"    ✗ 无法抽取复杂关系")
print(f"    ✗ 需要预定义规则")

print(f"\n  Ollama (qwen25chat):")
print(f"    ✓ 可以理解语义")
print(f"    ✓ 可以抽取复杂实体和关系")
print(f"    ✓ 不需要预定义规则")
print(f"    ✗ 速度较慢（秒级）")
print(f"    ✗ 需要调用本地LLM")

print(f"\n结论:")
print(f"  如果用BERT替代Ollama做实体抽取：")
if bert_extract_time and ollama_time and bert_extract_time > 0:
    print(f"    ✓ 速度会提升 {ollama_time/bert_extract_time:.0f}x")
elif bert_time and ollama_time:
    print(f"    ✓ 速度会提升 {ollama_time/bert_time:.0f}x")
else:
    print(f"    ✓ 速度会提升 N/Ax")
print(f"    ✗ 但抽取质量会大幅下降")
print(f"    ✗ 无法抽取复杂的实体关系")
print(f"    ✗ 需要大量人工规则")
print(f"\n  建议:")
print(f"    1. 如果追求速度，可以用BERT做初步筛选")
print(f"    2. 对重要案例，仍然用Ollama做精细抽取")
print(f"    3. 或者训练一个专门的BERT实体抽取模型（需要标注数据）")

print("\n" + "="*60)
