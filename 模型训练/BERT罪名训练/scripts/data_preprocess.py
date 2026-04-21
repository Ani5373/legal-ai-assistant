"""
法律长文本罪名预测系统 - 数据预处理脚本（多标签版本）
功能：
1. 读取原始 CAIL 数据集
2. 提取案情文本和罪名标签（支持多标签）
3. 过滤出 Top 10 罪名类别
4. 构建 label2id 和 id2label 映射
5. 转换为 Multi-hot 编码
6. 划分训练集和验证集
"""

import json
import os
from collections import Counter
from pathlib import Path


def main():
    # 配置路径
    project_root = Path(__file__).resolve().parent.parent
    training_dir = project_root / "模型训练"
    data_dir = training_dir / "原始数据" / "final_all_data" / "first_stage"
    output_dir = training_dir / "处理后数据"
    output_dir.mkdir(parents=True, exist_ok=True)

    train_file = data_dir / "train.json"

    print("=" * 60)
    print("开始数据预处理（多标签版本）...")
    print("=" * 60)

    # 第一步：读取数据并统计罪名频率
    print("\n[1/6] 正在读取原始数据并统计罪名...")
    valid_data = []
    accusation_counter = Counter()

    with open(train_file, 'r', encoding='utf-8') as f:
        line_count = 0
        for line in f:
            line_count += 1
            if line_count % 100000 == 0:
                print(f"    已处理 {line_count} 行...")

            try:
                item = json.loads(line.strip())
                fact = item.get('fact', '')
                if not fact:
                    continue

                meta = item.get('meta', {})
                accusations = meta.get('accusation', [])
                if not accusations:
                    continue

                # 保留所有罪名
                valid_data.append({
                    'fact': fact,
                    'accusations': accusations
                })
                # 统计每个罪名出现次数
                for acc in accusations:
                    accusation_counter[acc] += 1

            except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                continue

    total_valid = len(valid_data)
    print(f"    ✓ 读取完成！共解析 {total_valid} 条有效数据")

    # 第二步：筛选 Top 10 罪名
    print("\n[2/6] 正在筛选 Top 10 罪名类别...")
    top_10_accusations = accusation_counter.most_common(10)

    print("\n    Top 10 罪名类别及其出现次数：")
    print("    " + "-" * 50)
    for i, (accusation, count) in enumerate(top_10_accusations, 1):
        print(f"    {i}. {accusation:15s} : {count:>8} 次")
    print("    " + "-" * 50)

    top_10_labels = [acc for acc, _ in top_10_accusations]

    # 第三步：构建 label2id 和 id2label
    print("\n[3/6] 正在构建标签映射...")
    label2id = {label: idx for idx, label in enumerate(top_10_labels)}
    id2label = {idx: label for label, idx in label2id.items()}

    mapping_file = output_dir / "label_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump({
            'label2id': label2id,
            'id2label': id2label,
            'num_classes': 10
        }, f, ensure_ascii=False, indent=2)
    print(f"    ✓ 标签映射已保存至: {mapping_file}")

    # 第四步：过滤数据并转换为 Multi-hot 编码
    print("\n[4/6] 正在过滤数据并转换为 Multi-hot 编码...")
    filtered_data = []
    multi_label_count = 0

    for item in valid_data:
        # 找出该样本在 Top 10 中的罪名
        valid_labels = [label2id[acc] for acc in item['accusations'] if acc in label2id]
        
        if valid_labels:
            # 创建 Multi-hot 向量
            multi_hot = [0] * 10
            for label_id in valid_labels:
                multi_hot[label_id] = 1
            
            filtered_data.append({
                'fact': item['fact'],
                'label': multi_hot
            })
            if len(valid_labels) > 1:
                multi_label_count += 1

    total_filtered = len(filtered_data)
    print(f"    ✓ 过滤完成！保留 {total_filtered} 条数据")
    print(f"    ✓ 其中多标签样本: {multi_label_count} 条 ({multi_label_count/total_filtered*100:.1f}%)")

    # 第五步：划分训练集和验证集（8:2）
    print("\n[5/6] 正在划分训练集和验证集（8:2）...")
    import random
    random.seed(42)
    random.shuffle(filtered_data)

    split_idx = int(len(filtered_data) * 0.8)
    train_data = filtered_data[:split_idx]
    val_data = filtered_data[split_idx:]

    # 保存训练集
    train_output = output_dir / "train_processed.json"
    with open(train_output, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    # 保存验证集
    val_output = output_dir / "val_processed.json"
    with open(val_output, 'w', encoding='utf-8') as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"    ✓ 训练集已保存: {train_output} ({len(train_data)} 条)")
    print(f"    ✓ 验证集已保存: {val_output} ({len(val_data)} 条)")

    # 第六步：统计结果
    print("\n[6/6] 统计结果...")
    print("\n" + "=" * 60)
    print("数据预处理完成！最终统计结果：")
    print("=" * 60)
    print(f"总数据量: {total_filtered} 条")
    print(f"训练集: {len(train_data)} 条")
    print(f"验证集: {len(val_data)} 条")
    print(f"多标签样本: {multi_label_count} 条 ({multi_label_count/total_filtered*100:.1f}%)")

    # 统计每个类别的样本数
    print("\n各类别样本统计：")
    print("-" * 60)
    train_label_counts = [0] * 10
    val_label_counts = [0] * 10
    
    for item in train_data:
        for i, v in enumerate(item['label']):
            if v == 1:
                train_label_counts[i] += 1
    
    for item in val_data:
        for i, v in enumerate(item['label']):
            if v == 1:
                val_label_counts[i] += 1

    for idx, (accusation, _) in enumerate(top_10_accusations):
        train_count = train_label_counts[idx]
        val_count = val_label_counts[idx]
        print(f"{idx}. {accusation:15s} | 训练: {train_count:>6} | 验证: {val_count:>6}")

    print("=" * 60)
    print("✓ 所有预处理任务完成！")


if __name__ == "__main__":
    main()
