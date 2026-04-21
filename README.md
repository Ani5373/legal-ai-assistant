# 法律 AI 智能分析系统

一个基于多智能体架构的法律案件分析系统，能够自动提取案件事实、检索相关法律条文、预测罪名并生成专业的法律分析报告。

## 📋 项目简介

本系统采用多智能体协作架构，包含以下核心功能：

- **事实提取智能体**：从案件描述中提取关键事实和实体
- **法律检索智能体**：检索相关法律条文和司法解释
- **罪名预测智能体**：基于 BERT 模型预测可能的罪名
- **报告生成智能体**：生成结构化的法律分析报告

## 🏗️ 项目结构

```
.
├── agent/                  # 智能体系统
│   ├── agents/            # 各个智能体实现
│   ├── coordinator/       # 协调引擎
│   ├── memory/           # 记忆系统
│   ├── security/         # 安全管理
│   ├── tools/            # 工具集
│   └── schemas/          # 数据契约
├── 服务端/                # 后端 API 服务
├── 网页/                  # 前端 Web 应用
├── 模型训练/              # 模型训练脚本和数据
└── 启动项目.bat          # 快速启动脚本
```

## 📦 模型文件下载

由于模型文件较大，无法直接上传到 GitHub，请从以下网盘下载：

### 必需的模型文件

**1. 训练好的罪名预测模型（必需）**
- 文件：`best_model.pt` (1.16 GB)
- 网盘链接：https://pan.quark.cn/s/581c6d434bcb?pwd=gw2G
- 提取码：`gw2G`
- 放置位置：`模型训练/训练输出/best_model.pt`

**2. 预训练模型（可选，如需重新训练）**

如果你需要重新训练模型，请下载以下预训练模型：

- **UIE-Base 模型**
  - 官方下载：https://paddlenlp.bj.bcebos.com/taskflow/information_extraction/uie_base_v1.0/model_state.pdparams
  - 放置位置：`模型训练/预训练模型/uie-base/`

- **Chinese-RoBERTa-WWM-Ext 模型**
  - 官方下载：https://huggingface.co/hfl/chinese-roberta-wwm-ext
  - 放置位置：`模型训练/预训练模型/chinese-roberta-wwm-ext/`

### 模型文件放置说明

下载后，请按照以下结构放置文件：

```
模型训练/
├── 训练输出/
│   └── best_model.pt          # 从网盘下载
└── 预训练模型/                 # 如需重新训练
    ├── uie-base/
    │   └── model_state.pdparams
    └── chinese-roberta-wwm-ext/
        └── pytorch_model.bin
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- Ollama（用于本地 LLM）

### 1. 下载模型文件

首先从上述网盘链接下载 `best_model.pt`，并放置到 `模型训练/训练输出/` 目录。

### 2. 安装 Python 依赖

```bash
cd agent
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd 网页/legal-ai-web
npm install
```

### 4. 配置环境变量

复制 `服务端/.env.example` 为 `服务端/.env`，并根据需要修改配置。

### 5. 启动 Ollama

确保 Ollama 服务已启动，并下载所需模型：

```bash
ollama pull qwen2.5:7b
```

### 6. 启动项目

使用快速启动脚本：

```bash
启动项目.bat
```

或手动启动各个服务：

```bash
# 启动后端服务
cd 服务端
python app.py

# 启动前端服务
cd 网页/legal-ai-web
npm run dev
```

### 7. 访问系统

打开浏览器访问：http://localhost:3000

## 🔧 配置说明

### Agent 配置

编辑 `agent/coordinator/engine.py` 中的配置项：

- Ollama 服务地址
- 模型选择
- 超时设置

### 安全策略

安全规则配置文件：`agent/security/policies/security_rules.json`

## 📚 使用说明

1. 在 Web 界面输入案件描述
2. 系统自动分析并提取关键信息
3. 检索相关法律条文
4. 预测可能的罪名
5. 生成完整的法律分析报告

## 🧪 测试

运行测试套件：

```bash
cd agent
pytest tests/
```

## 📝 开发说明

### 添加新的智能体

1. 在 `agent/agents/` 创建新的智能体目录
2. 实现 `agent.py` 并继承基础智能体类
3. 在协调引擎中注册新智能体

### 添加新的工具

1. 在 `agent/tools/` 创建工具目录
2. 实现 `tool.py` 并定义工具接口
3. 在智能体中引用新工具

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！


## ⚠️ 注意事项

- 本系统仅供学习和研究使用
- 生成的法律分析仅供参考，不构成正式法律意见
- 实际法律问题请咨询专业律师

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- Issue：[GitHub Issues]
- Email：[haoli4286@gmail.com]

---

**重要提醒**：首次使用前，请务必从网盘下载模型文件！
