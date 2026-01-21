# 🌸 AI-Gen / WaifuGen

<p align="center">
  <img src="./assets/banner.png" alt="AI-Gen Banner" />
</p>

> 🎨 一个本地启动的 AI 艺术创作工具  
> FastAPI 后端 + 本地静态前端 UI，面向二次元图像生成/工作流整合

<p align="center">
  <a href="https://github.com/shingo0083/AI-Gen/stargazers"><img src="https://img.shields.io/github/stars/shingo0083/AI-Gen.svg" /></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-success" />
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey" />
</p>

---

## 🚀 项目简介

**AI-Gen / WaifuGen** 是一个 **本地启动** 的图像生成工具/前端壳，目标是把「提示词、参数、历史记录、调用生成服务」整合成一个更顺手的二次元创作体验。

- ✅ 本地启动（Windows 优先）
- ✅ 前后端分离：FastAPI + 静态前端
- ✅ 生成历史记录（本地保存）
- ✅ 结构清晰，便于二次开发与扩展

> 注意：**本项目是“本地启动”，不是“无需 API Key”。**  
> 如果你接入的是需要鉴权的生成服务（例如第三方推理服务或你自己的 API 网关），仍然需要配置对应的 **API Key / Base URL**。

---

## ✨ 功能亮点

- 🎨 Prompt 与参数输入
- 🧾 历史记录自动保存（本地）
- 🔌 可配置的 API 入口（Key / Base URL）
- 🧩 易扩展：可以继续接入不同模型、不同推理后端


## 🚀 快速开始（Windows）

### 1) 克隆项目
```powershell
git clone https://github.com/shingo0083/AI-Gen.git
cd AI-Gen
```

### 2) 安装依赖（建议虚拟环境）
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3) 配置（如果你需要调用带鉴权的生成服务）
复制示例配置：

```powershell
copy secrets.example.json secrets.json
```

按需填写（示例字段以你的文件为准）：
- `api_key`：你的服务 Key
- `api_base`：服务地址（例如你的推理服务地址）

> ⚠️ 不要把 `secrets.json` 提交到 GitHub（建议加入 .gitignore）。

### 4) 启动
推荐直接运行：

```powershell
run.bat
```

或手动启动（按你的项目实际命令调整）：
```powershell
python -m uvicorn server:app --reload --host 127.0.0.1 --port 8069
```

浏览器打开：
- `http://127.0.0.1:8069/`

---

## 🤝 贡献

欢迎 Issue / PR：
- 🐛 Bug 修复
- ✨ 新功能建议
- 📖 文档优化
- 🎨 UI 改进

---

## 📄 License
MIT
