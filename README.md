# AI-Gen - Local Prompt/Image Tool

一个本地运行的工具：前端静态页面 + FastAPI/Uvicorn 后端，支持生成、历史记录与数据驱动配置。

## Features
- 本地运行（无云依赖）
- 数据驱动（catalog / styles）
- 生成记录 history（本地保存）
- 可扩展的数据结构与 UI

---

## Requirements
- Windows / macOS / Linux
推荐：3.10
允许：3.10+
- 已安装依赖：FastAPI、Uvicorn（见 requirements.txt）

> Windows 用户如果系统里有多个 Python，推荐使用 `py` launcher 指定版本（例如 `py -3.10`）。

---

## Run (Windows, 推荐)
你可以直接使用项目内的启动脚本（如果已存在）：

```bat
run.bat
它会使用：
py -3.10 -m uvicorn server:app --host 127.0.0.1 --port 8069 --reload
启动后打开：
http://127.0.0.1:8069/


Run (Manual)
在项目根目录执行：
py -3.10 -m pip install -r requirements.txt
py -3.10 -m uvicorn server:app --host 127.0.0.1 --port 8069 --reload --no-use-colors


Project Structure (Simplified)

server.py：FastAPI app / API
static/：前端静态资源（HTML/CSS/JS）
static/js/app/：store/reducer/selectors（状态与分层）
static/js/domain/：领域逻辑（如 prompt 构建）
static/js/infra/：API / 存储等基础设施封装
static/history/：本地历史记录（建议不提交到 git）

Notes for Contributors

请不要提交 static/history/history.json（属于个人运行数据）
提交前建议跑一遍页面，确认无控制台报错
数据修改（catalog/styles）建议遵守既有结构


## Configuration (API Base URL & Key)
本项目不提供第三方 API Key 与 API 端点，请自行准备。

你可以创建 `secrets.json`（不要提交到 git）：

- 复制 `secrets.example.json` 为 `secrets.json`
- 填入你自己的 `api_key`
- 如需自定义 API 端点，请在 `secrets.json` 中填写或按 server.py 的说明修改/设置环境变量


> 注意：请勿将真实 key 提交到 GitHub。
