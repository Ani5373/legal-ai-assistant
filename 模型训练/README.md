# 模型训练说明

## 📦 模型文件下载

### 训练好的模型（必需）

**best_model.pt** - 罪名预测模型
- 大小：1.16 GB
- 网盘链接：https://pan.quark.cn/s/581c6d434bcb?pwd=gw2G
- 提取码：`gw2G`
- 放置位置：将下载的文件放到 `训练输出/best_model.pt`

### 预训练模型（可选）

如果需要重新训练模型，请下载以下预训练模型：

#### 1. UIE-Base 模型
- 用途：信息抽取
- 下载地址：https://paddlenlp.bj.bcebos.com/taskflow/information_extraction/uie_base_v1.0/model_state.pdparams
- 放置位置：`预训练模型/uie-base/model_state.pdparams`

#### 2. Chinese-RoBERTa-WWM-Ext 模型
- 用途：中文语义理解
- 下载地址：https://huggingface.co/hfl/chinese-roberta-wwm-ext
- 放置位置：`预训练模型/chinese-roberta-wwm-ext/pytorch_model.bin`

## 📁 目录结构

```
模型训练/
├── 训练输出/
│   └── best_model.pt          # 从网盘下载（必需）
├── 预训练模型/                 # 从官方下载（可选）
│   ├── uie-base/
│   │   ├── model_state.pdparams
│   │   └── ...
│   └── chinese-roberta-wwm-ext/
│       ├── pytorch_model.bin
│       ├── config.json
│       └── ...
├── 数据集/                     # 训练数据
└── 训练脚本/                   # 训练代码
```

## 🚀 使用说明

### 仅使用预测功能

如果只需要使用罪名预测功能，只需下载 `best_model.pt` 即可。

### 重新训练模型

如果需要重新训练或微调模型：

1. 下载所有预训练模型
2. 准备训练数据
3. 运行训练脚本
4. 新模型将保存到 `训练输出/` 目录

## ⚠️ 注意事项

- `best_model.pt` 是必需的，系统运行需要此文件
- 预训练模型仅在重新训练时需要
- 模型文件较大，请确保有足够的磁盘空间
- 建议使用 GPU 进行训练以提高速度

## 📝 模型信息

- 模型类型：BERT-based 分类模型
- 训练数据：法律案件数据集
- 输出：罪名预测及置信度
- 支持罪名：[根据实际情况填写]
