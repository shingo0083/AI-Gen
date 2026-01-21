# 🌸 AI‑Gen / WaifuGen

> 🎨 一个本地运行的 AI 艺术创作工具  
> FastAPI 后端 + 本地静态前端 UI，专注 Waifu / 二次元图像生成体验

<p align="center">
  <img width="220" src="https://raw.githubusercontent.com/shingo0083/AI-Gen/main/static/logo.png" alt="AI-Gen Logo">
</p>

<p align="center">
  <a href="https://github.com/shingo0083/AI-Gen/stargazers"><img src="https://img.shields.io/github/stars/shingo0083/AI-Gen.svg" /></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-success" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

---

## 🚀 项目简介

**AI‑Gen / WaifuGen** 是一个为 AI 艺术创作者与二次元爱好者打造的本地图像生成工具：

✨ 本地运行，无需云端服务  
✨ 数据驱动（可扩展 catalog / style）  
✨ 自动保存生成历史记录  
✨ 结构清晰，易于扩展与二次元风格定制

---

## 🧠 功能亮点

- 💻 本地启动：无需网络或外部 API Key  
- 🎨 自由 Prompt 输入：支持各种创作风格  
- 📜 生成历史记录：自动保存用户生成数据  
- 📂 可扩展的数据结构：可自定义 catalog / styles  
- 🔧 易于二次开发：前端静态文件 & Python 后端分离

---

## 📁 仓库结构

```text
AI-Gen/
├── server.py
├── static/
│   ├── index.html
│   ├── css/
│   ├── js/
│   ├── images/
│   └── history/
├── requirements.txt
├── run.bat
├── secrets.example.json
└── README.md
```

---

## 📦 快速开始

```bash
git clone https://github.com/shingo0083/AI-Gen.git
cd AI-Gen
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
run.bat
```

浏览器打开： http://127.0.0.1:8069/

---

## 📄 License

MIT License © 2026
