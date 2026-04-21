"""
测试三层智能内存系统
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.memory.core import MemoryManager
from agent.schemas.contracts import (
    CaseAnalysisResponse,
    ChargePrediction,
    GraphEdge,
    GraphNode,
)


def test_memory_basic_operations():
    """测试基本的存储和检索操作"""
    print("\n=== 测试 1: 基本存储和检索 ===")

    # 创建测试用的内存管理器
    memory = MemoryManager(base_path="agent/memory")

    # 创建测试案件
    test_response = CaseAnalysisResponse(
        case_id="test-case-001",
        text="张三于2023年1月在某商场盗窃手机一部，价值5000元。",
        predictions=[
            ChargePrediction(label="盗窃罪", probability=0.95, source="bert_tool", rank=1)
        ],
        nodes=[
            GraphNode(
                id="person-001",
                type="人物",
                label="张三",
                description="犯罪嫌疑人",
                source="fact_extractor",
            ),
            GraphNode(
                id="action-001",
                type="行为",
                label="盗窃",
                description="盗窃手机",
                source="fact_extractor",
            ),
        ],
        edges=[
            GraphEdge(
                id="edge-001",
                source="person-001",
                target="action-001",
                relation="实施",
                evidence="张三盗窃手机",
            )
        ],
        report="经分析，张三涉嫌盗窃罪，建议量刑6个月至1年。",
        metadata={"test": True},
    )

    # 存储案件
    print("存储案件...")
    memory.store(test_response)
    print(f"✓ 案件 {test_response.case_id} 已存储")

    # 检索案件
    print("\n通过 case_id 检索...")
    retrieved = memory.retrieve("test-case-001")
    if retrieved:
        print(f"✓ 检索成功: {retrieved.case_id}")
        print(f"  - 预测数量: {len(retrieved.predictions)}")
        print(f"  - 节点数量: {len(retrieved.nodes)}")
        print(f"  - 边数量: {len(retrieved.edges)}")
    else:
        print("✗ 检索失败")
        return False

    # 通过文本检索
    print("\n通过文本哈希检索...")
    retrieved_by_text = memory.search_by_text(test_response.text)
    if retrieved_by_text:
        print(f"✓ 文本检索成功: {retrieved_by_text.case_id}")
    else:
        print("✗ 文本检索失败")
        return False

    return True


def test_memory_signal_score():
    """测试信号强度评分"""
    print("\n=== 测试 2: 信号强度评分 ===")

    memory = MemoryManager(base_path="agent/memory")

    # 高质量案件
    high_quality = CaseAnalysisResponse(
        case_id="test-high-quality",
        text="这是一个高质量案件，包含详细的事实和分析。" * 50,
        predictions=[
            ChargePrediction(label="盗窃罪", probability=0.95, rank=1),
            ChargePrediction(label="抢劫罪", probability=0.85, rank=2),
        ],
        nodes=[GraphNode(id=f"node-{i}", type="测试", label=f"节点{i}") for i in range(15)],
        edges=[
            GraphEdge(id=f"edge-{i}", source=f"node-{i}", target=f"node-{i+1}", relation="测试")
            for i in range(20)
        ],
        report="这是一份详细的分析报告。" * 100,
    )

    # 低质量案件
    low_quality = CaseAnalysisResponse(
        case_id="test-low-quality",
        text="简单案件",
        predictions=[ChargePrediction(label="盗窃罪", probability=0.55, rank=1)],
        nodes=[],
        edges=[],
        report="简单报告",
        warnings=["警告1", "警告2"],
    )

    memory.store(high_quality)
    memory.store(low_quality)

    high_entry = memory.index["test-high-quality"]
    low_entry = memory.index["test-low-quality"]

    print(f"高质量案件信号分数: {high_entry.signal_score:.3f}")
    print(f"低质量案件信号分数: {low_entry.signal_score:.3f}")

    if high_entry.signal_score > low_entry.signal_score:
        print("✓ 信号评分正常工作")
        return True
    else:
        print("✗ 信号评分异常")
        return False


def test_memory_stats():
    """测试统计信息"""
    print("\n=== 测试 3: 统计信息 ===")

    memory = MemoryManager(base_path="agent/memory")
    stats = memory.get_stats()

    print(f"总案件数: {stats['total_cases']}")
    print(f"平均信号分数: {stats['avg_signal_score']}")
    print(f"总访问次数: {stats['total_accesses']}")
    print(f"存储大小: {stats['storage_size_mb']} MB")

    print("✓ 统计信息获取成功")
    return True


def test_memory_heal():
    """测试自愈功能"""
    print("\n=== 测试 4: 自愈功能 ===")

    memory = MemoryManager(base_path="agent/memory")
    heal_stats = memory.heal()

    print(f"检查案件数: {heal_stats['checked']}")
    print(f"缺失 topic 文件: {heal_stats['missing_topic']}")
    print(f"缺失 raw 文件: {heal_stats['missing_raw']}")
    print(f"孤立 topic 文件: {heal_stats['orphaned_topic']}")
    print(f"孤立 raw 文件: {heal_stats['orphaned_raw']}")
    print(f"修复数量: {heal_stats['repaired']}")

    print("✓ 自愈检查完成")
    return True


def test_memory_compression():
    """测试压缩功能"""
    print("\n=== 测试 5: 压缩功能（模拟运行）===")

    memory = MemoryManager(
        base_path="agent/memory",
        max_age_days=90,
        min_signal_score=0.3,
        compression_threshold=1000,
    )

    # 模拟运行压缩
    compress_stats = memory.compress(dry_run=True)

    print(f"压缩前总数: {compress_stats['total_before']}")
    print(f"删除过期案件: {compress_stats['deleted_old']}")
    print(f"删除低访问案件: {compress_stats['deleted_low_access']}")
    print(f"删除低信号案件: {compress_stats['deleted_low_signal']}")
    print(f"压缩后总数: {compress_stats['total_after']}")

    print("✓ 压缩模拟运行完成")
    return True


def test_memory_list_recent():
    """测试最近案件列表"""
    print("\n=== 测试 6: 最近案件列表 ===")

    memory = MemoryManager(base_path="agent/memory")
    recent = memory.list_recent(limit=5)

    print(f"最近 {len(recent)} 个案件:")
    for i, entry in enumerate(recent, 1):
        print(f"  {i}. {entry.case_id}")
        print(f"     访问次数: {entry.access_count}")
        print(f"     信号分数: {entry.signal_score:.3f}")
        print(f"     最后访问: {entry.last_accessed}")

    print("✓ 最近案件列表获取成功")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("三层智能内存系统测试")
    print("=" * 60)

    tests = [
        ("基本操作", test_memory_basic_operations),
        ("信号评分", test_memory_signal_score),
        ("统计信息", test_memory_stats),
        ("自愈功能", test_memory_heal),
        ("压缩功能", test_memory_compression),
        ("最近列表", test_memory_list_recent),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 出错: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
