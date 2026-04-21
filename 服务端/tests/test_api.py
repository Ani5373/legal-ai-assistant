"""
API 接口测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_predict_api():
    """测试预测接口"""
    print("\n=== 测试 1: 预测接口 ===")

    import requests

    url = "http://127.0.0.1:8111/api/predict"
    data = {"text": "张三于2023年1月在某商场盗窃手机一部，价值5000元，被当场抓获。"}

    print(f"请求 URL: {url}")
    print(f"请求数据: {data}")

    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        print(f"\n响应状态: {response.status_code}")
        print(f"预测结果:")
        for i, pred in enumerate(result["predictions"], 1):
            print(f"  {i}. {pred['label']}: {pred['probability']:.4f}")

        print("\n✓ 预测接口测试通过")
        return True
    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到服务器，请确保服务已启动")
        print("  启动命令: python -m uvicorn 服务端.app:app --reload --port 8111")
        return False
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


def test_analyze_api():
    """测试分析接口"""
    print("\n=== 测试 2: 分析接口 ===")

    import requests

    url = "http://127.0.0.1:8111/api/analyze"
    data = {
        "text": "李四于2023年3月在某地持刀抢劫他人财物，价值3000元，造成被害人轻伤。",
        "case_id": "test-case-001",
    }

    print(f"请求 URL: {url}")
    print(f"请求数据: {data}")

    try:
        response = requests.post(url, json=data, timeout=120)
        response.raise_for_status()

        result = response.json()
        print(f"\n响应状态: {response.status_code}")
        print(f"案件ID: {result['case_id']}")
        print(f"预测数量: {len(result['predictions'])}")
        print(f"节点数量: {len(result['nodes'])}")
        print(f"边数量: {len(result['edges'])}")
        print(f"步骤数量: {len(result['steps'])}")
        print(f"报告长度: {len(result['report'])} 字符")

        if result["predictions"]:
            print(f"\n首要罪名:")
            pred = result["predictions"][0]
            print(f"  {pred['label']}: {pred['probability']:.4f}")

        if result["warnings"]:
            print(f"\n警告:")
            for warning in result["warnings"]:
                print(f"  - {warning}")

        print("\n✓ 分析接口测试通过")
        return True
    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到服务器，请确保服务已启动")
        print("  启动命令: python -m uvicorn 服务端.app:app --reload --port 8111")
        return False
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_health_api():
    """测试健康检查接口"""
    print("\n=== 测试 3: 健康检查接口 ===")

    import requests

    url = "http://127.0.0.1:8111/health"

    print(f"请求 URL: {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        result = response.json()
        print(f"\n响应状态: {response.status_code}")
        print(f"服务状态: {result['status']}")
        print(f"服务组件:")
        for service, status in result["services"].items():
            status_text = "✓ 正常" if status else "✗ 异常"
            print(f"  {service}: {status_text}")

        print("\n✓ 健康检查接口测试通过")
        return True
    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到服务器，请确保服务已启动")
        return False
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("API 接口测试")
    print("=" * 60)
    print("\n请确保服务已启动：python -m uvicorn 服务端.app:app --reload --port 8111")
    print("按 Enter 继续...")
    input()

    tests = [
        ("健康检查接口", test_health_api),
        ("预测接口", test_predict_api),
        ("分析接口", test_analyze_api),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 出错: {e}")
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
