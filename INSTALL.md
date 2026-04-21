# 安装指南

## 📋 前置要求

- Python 3.8 或更高版本
- Node.js 16 或更高版本
- Git
- Ollama（用于本地大语言模型）

## 🔽 第一步：克隆项目

```bash
git clone [你的 GitHub 仓库地址]
cd [项目目录名]
```

## 📦 第二步：下载模型文件（重要！）

### 必需下载

从网盘下载训练好的模型文件：

- **文件名**：`best_model.pt`
- **大小**：1.16 GB
- **网盘链接**：https://pan.quark.cn/s/581c6d434bcb?pwd=gw2G
- **提取码**：`gw2G`

下载后，将文件放置到：
```
模型训练/训练输出/best_model.pt
```

### 可选下载（仅重新训练时需要）

如果需要重新训练模型，请参考 `模型训练/README.md` 下载预训练模型。

## 🐍 第三步：安装 Python 依赖

```bash
# 进入 agent 目录
cd agent

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 📦 第四步：安装前端依赖

```bash
# 进入前端目录
cd 网页/legal-ai-web

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

## 🦙 第五步：安装和配置 Ollama

### 安装 Ollama

访问 https://ollama.ai 下载并安装 Ollama。

### 下载所需模型

```bash
# 下载 Qwen 模型（推荐）
ollama pull qwen2.5:7b

# 或其他中文模型
ollama pull qwen:7b
```

### 启动 Ollama 服务

```bash
ollama serve
```

## ⚙️ 第六步：配置环境变量

```bash
# 复制环境变量模板
cd 服务端
copy .env.example .env

# 编辑 .env 文件，根据需要修改配置
```

## ✅ 第七步：验证安装

### 检查模型文件

确认以下文件存在：
```
模型训练/训练输出/best_model.pt
```

### 测试 Python 环境

```bash
cd agent
python -c "import torch; print('PyTorch:', torch.__version__)"
python tests/test_imports.py
```

### 测试前端环境

```bash
cd 网页/legal-ai-web
npm run build
```

## 🚀 第八步：启动项目

### 方式一：使用启动脚本（Windows）

```bash
启动项目.bat
```

### 方式二：手动启动

**启动后端服务：**
```bash
cd 服务端
python app.py
```

**启动前端服务（新终端）：**
```bash
cd 网页/legal-ai-web
npm run dev
```

**启动 Agent 服务（如果独立运行）：**
```bash
cd agent
python -m coordinator.engine
```

## 🌐 访问系统

打开浏览器访问：
- 前端界面：http://localhost:3000
- 后端 API：http://localhost:5000

## 🔧 常见问题

### 1. 模型文件未找到

**错误**：`FileNotFoundError: best_model.pt not found`

**解决**：确保已从网盘下载模型文件并放置到正确位置。

### 2. Ollama 连接失败

**错误**：`Connection refused to Ollama`

**解决**：
- 确保 Ollama 服务已启动：`ollama serve`
- 检查端口是否被占用（默认 11434）

### 3. Python 依赖安装失败

**解决**：
- 升级 pip：`pip install --upgrade pip`
- 使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 4. Node.js 依赖安装失败

**解决**：
- 清除缓存：`npm cache clean --force`
- 使用国内镜像：`npm install --registry=https://registry.npmmirror.com`

### 5. 端口被占用

**解决**：
- 修改配置文件中的端口号
- 或关闭占用端口的程序

## 📚 下一步

安装完成后，请阅读：
- `README.md` - 项目概述和使用说明
- `模型训练/README.md` - 模型相关说明
- `agent/资源/README.md` - 资源文件说明

## 💡 提示

- 首次启动可能需要较长时间加载模型
- 建议使用 GPU 以获得更好的性能
- 定期更新依赖以获取最新功能和安全修复

## 🆘 获取帮助

如遇到问题：
1. 查看项目 Issues
2. 提交新的 Issue 并附上错误信息
3. 联系项目维护者

---

祝使用愉快！🎉
