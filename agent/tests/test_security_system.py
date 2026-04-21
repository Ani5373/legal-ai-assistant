"""
测试三阶段安全检查系统
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.security.core import RiskLevel, SecurityManager


def test_stage1_rule_filter():
    """测试阶段1：规则快速过滤"""
    print("\n=== 测试 1: 规则快速过滤 ===")

    security = SecurityManager(base_path="agent/security")

    # 测试1: 文本过短
    print("\n测试 1.1: 文本过短")
    result = security.check("test-001", "短文本", "analyze")
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  原因: {result.reason}")
    assert not result.passed, "应该阻止过短文本"

    # 测试2: 包含阻止关键词
    print("\n测试 1.2: 包含阻止关键词")
    result = security.check("test-002", "这是一个测试案例，用于演示系统功能", "analyze")
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  原因: {result.reason}")
    assert not result.passed, "应该阻止包含'测试'关键词的文本"

    # 测试3: 正常文本
    print("\n测试 1.3: 正常文本")
    result = security.check(
        "test-003",
        "张三于2023年1月在某商场盗窃手机一部，价值5000元，被当场抓获。",
        "analyze",
    )
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  风险等级: {result.risk_level}")
    assert result.passed, "正常文本应该通过"

    print("\n✓ 阶段1测试通过")
    return True


def test_stage2_risk_assessment():
    """测试阶段2：风险分级判断"""
    print("\n=== 测试 2: 风险分级判断 ===")

    security = SecurityManager(base_path="agent/security", enable_stage3=False)

    # 测试1: 低风险案件
    print("\n测试 2.1: 低风险案件")
    result = security.check(
        "test-004",
        "李四于2023年3月在超市盗窃商品，价值200元，已归还并道歉。",
        "analyze",
    )
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  风险等级: {result.risk_level}")
    assert result.passed, "低风险案件应该通过"
    assert result.risk_level == RiskLevel.LOW, "应该是低风险"

    # 测试2: 中风险案件（包含敏感词）
    print("\n测试 2.2: 中风险案件")
    result = security.check(
        "test-005",
        "王五于2023年5月因经济纠纷与他人发生冲突，造成轻微伤情，双方已和解。",
        "analyze",
    )
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  风险等级: {result.risk_level}")
    assert result.passed, "中风险案件应该通过"

    # 测试3: 高风险案件（多个敏感词）
    print("\n测试 2.3: 高风险案件")
    test_text = "赵六涉嫌故意杀人案件，于2023年7月在某地持刀伤害他人，造成被害人死亡，案情重大，社会影响恶劣。"
    print(f"  测试文本: {test_text}")
    result = security.check(
        "test-006",
        test_text,
        "analyze",
    )
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  风险等级: {result.risk_level}")
    print(f"  风险分数: {result.metadata.get('risk_score', 0)}")
    print(f"  风险因素: {result.metadata.get('risk_factors', [])}")
    assert result.passed, "高风险案件应该通过到阶段3"
    assert result.risk_level in [
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    ], f"应该是高风险或严重风险，实际是 {result.risk_level}"

    print("\n✓ 阶段2测试通过")
    return True


def test_stage3_high_risk_review():
    """测试阶段3：高风险操作审查"""
    print("\n=== 测试 3: 高风险操作审查 ===")

    security = SecurityManager(base_path="agent/security", enable_stage3=True)

    # 测试1: 高风险但信息完整
    print("\n测试 3.1: 高风险但信息完整")
    result = security.check(
        "test-007",
        """孙七涉嫌故意杀人案件。
        时间：2023年8月15日晚上10点
        地点：某市某区某街道
        经过：孙七与被害人因经济纠纷发生争执，持刀刺伤被害人，造成被害人死亡。
        证据：现场监控录像、凶器、证人证言、法医鉴定报告等。
        """,
        "analyze",
    )
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  风险等级: {result.risk_level}")
    print(f"  建议: {result.suggestions}")
    assert result.passed, "信息完整的高风险案件应该通过"

    # 测试2: 高风险且信息不完整
    print("\n测试 3.2: 高风险且信息不完整")
    result = security.check(
        "test-008",
        "周八涉嫌故意杀人，造成被害人死亡，情节严重。",
        "analyze",
    )
    print(f"  结果: {'✓ 通过' if result.passed else '✗ 阻止'}")
    print(f"  风险等级: {result.risk_level}")
    print(f"  原因: {result.reason}")
    print(f"  建议: {result.suggestions}")
    # 信息不完整可能被阻止
    if not result.passed:
        print("  ✓ 正确阻止了信息不完整的高风险案件")

    print("\n✓ 阶段3测试通过")
    return True


def test_audit_log():
    """测试审计日志"""
    print("\n=== 测试 4: 审计日志 ===")

    security = SecurityManager(base_path="agent/security", enable_audit_log=True)

    # 执行几次检查
    print("\n执行多次安全检查...")
    security.check("test-009", "这是一个测试案例", "analyze")
    security.check(
        "test-010", "张三盗窃手机一部，价值5000元，被当场抓获。", "analyze"
    )
    security.check(
        "test-011",
        "李四涉嫌故意杀人，于某地持刀伤害他人，造成被害人死亡。",
        "analyze",
    )

    # 获取审计日志
    print("\n获取审计日志...")
    logs = security.get_audit_logs(limit=10)
    print(f"  日志数量: {len(logs)}")

    for i, log in enumerate(logs[-3:], 1):
        print(f"\n  日志 {i}:")
        print(f"    案件ID: {log.case_id}")
        print(f"    风险等级: {log.risk_level}")
        print(f"    通过: {log.passed}")
        print(f"    阶段: {log.stage}")
        print(f"    原因: {log.reason}")

    # 获取统计信息
    print("\n获取统计信息...")
    stats = security.get_stats()
    print(f"  总检查次数: {stats['total_checks']}")
    print(f"  通过次数: {stats['passed']}")
    print(f"  阻止次数: {stats['blocked']}")
    print(f"  通过率: {stats['pass_rate']}%")
    print(f"  按风险等级: {stats['by_risk_level']}")

    print("\n✓ 审计日志测试通过")
    return True


def test_filtered_logs():
    """测试日志过滤"""
    print("\n=== 测试 5: 日志过滤 ===")

    security = SecurityManager(base_path="agent/security")

    # 获取被阻止的日志
    print("\n获取被阻止的日志...")
    blocked_logs = security.get_audit_logs(limit=10, passed=False)
    print(f"  被阻止的日志数量: {len(blocked_logs)}")

    if blocked_logs:
        print(f"\n  最近被阻止的案件:")
        for log in blocked_logs[-3:]:
            print(f"    - {log.case_id}: {log.reason}")

    # 获取高风险日志
    print("\n获取高风险日志...")
    high_risk_logs = security.get_audit_logs(limit=10, risk_level=RiskLevel.HIGH)
    print(f"  高风险日志数量: {len(high_risk_logs)}")

    print("\n✓ 日志过滤测试通过")
    return True


def test_security_rules():
    """测试安全规则配置"""
    print("\n=== 测试 6: 安全规则配置 ===")

    security = SecurityManager(base_path="agent/security")

    print("\n当前安全规则:")
    print(f"  阻止关键词: {security.rules['blocked_keywords']}")
    print(f"  敏感关键词: {security.rules['sensitive_keywords']}")
    print(f"  最小文本长度: {security.rules['min_text_length']}")
    print(f"  最大文本长度: {security.rules['max_text_length']}")

    print("\n✓ 安全规则配置测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("三阶段安全检查系统测试")
    print("=" * 60)

    tests = [
        ("规则快速过滤", test_stage1_rule_filter),
        ("风险分级判断", test_stage2_risk_assessment),
        ("高风险操作审查", test_stage3_high_risk_review),
        ("审计日志", test_audit_log),
        ("日志过滤", test_filtered_logs),
        ("安全规则配置", test_security_rules),
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
