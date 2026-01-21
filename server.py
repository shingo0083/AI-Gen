import os
import json
import time
import base64
import logging
import io
import tempfile
import requests
import uvicorn
import re

from PIL import Image, PngImagePlugin
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

DEFAULT_HISTORY_LIMIT = 100

# --- 配置（支持环境变量覆盖）---
def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return default if v is None or str(v).strip() == "" else str(v).strip()


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _env_csv(name: str, default_list):
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return list(default_list)
    return [s.strip() for s in str(v).split(",") if s.strip()]


PORT = _env_int("WF_PORT", 8069)
HOST = _env_str("WF_HOST", "127.0.0.1")

# 上游 API
DEFAULT_API_BASE_URL = _env_str("WF_API_BASE_URL", "http://156.238.229.55:3000")
MODEL = _env_str("WF_MODEL", "gemini-3-pro-image-preview")

HISTORY_LIMIT = _env_int("WF_HISTORY_LIMIT", DEFAULT_HISTORY_LIMIT)

# --- 路径自动获取 (适配 Windows/Mac) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "static", "history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "history.json")
SECRETS_FILE = os.path.join(BASE_DIR, "secrets.json")

# --- 日志 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("WaifuLocal")

app = FastAPI()

_default_origins = [
    f"http://localhost:{PORT}",
    f"http://127.0.0.1:{PORT}",
]
CORS_ORIGINS = _env_csv("WF_CORS_ORIGINS", _default_origins)

# --- 允许跨域 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
os.makedirs(HISTORY_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# --- 数据模型 ---
class GenerateRequest(BaseModel):
    api_key: Optional[str] = None
    # 兼容稳定版行为：不传该字段时，仍然会把用户输入的 api_key 写入 secrets.json
    # 如果你想“本次只用不保存”，前端可显式传 remember_key=false
    remember_key: bool = True

    prompt: str
    style_tag: Optional[str] = "Default"
    aspect_ratio: str = "1:1"
    ref_image: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# --- 辅助函数 ---
def atomic_write_json(path: str, data) -> None:
    """原子写 JSON：避免并发写/程序中断导致文件半截损坏。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dirpath = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f) or []
        if not isinstance(history, list):
            history = []

        # === 自动清洗不存在的文件 ===
        valid_history = []
        dirty = False

        for item in history:
            if not isinstance(item, dict):
                dirty = True
                continue

            filename = item.get("filename")
            if not filename:
                dirty = True
                continue

            file_path = os.path.join(HISTORY_DIR, filename)
            if os.path.exists(file_path):
                valid_history.append(item)
            else:
                dirty = True

        valid_history = valid_history[:HISTORY_LIMIT]

        if dirty:
            logger.info("🧹 发现无效记录，正在自动清理...")
            atomic_write_json(HISTORY_FILE, valid_history)

        return valid_history

    except Exception as e:
        logger.error(f"读取历史记录出错: {e}")
        return []


def save_history_item(item):
    history = load_history()
    history.insert(0, item)
    history = history[:HISTORY_LIMIT]
    atomic_write_json(HISTORY_FILE, history)


def load_api_key():
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return (data.get("api_key") or data.get("OPENAI_API_KEY") or data.get("key") or "").strip()
        except Exception:
            pass
    return ""


def save_api_key(key: str):
    try:
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": key}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def extract_image_data(result: dict):
    if "candidates" in result:
        try:
            for part in result["candidates"][0]["content"]["parts"]:
                if "inline_data" in part:
                    return part["inline_data"]["data"]
                if "inlineData" in part:
                    return part["inlineData"]["data"]
        except Exception:
            pass

    if "data" in result:
        return result["data"]
    if "image" in result:
        return result["image"]
    if "generatedImages" in result:
        try:
            return result["generatedImages"][0]["data"]
        except Exception:
            pass
    return None


# --- 路由 ---
@app.get("/")
def read_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/api/init")
def init_data():
    return {"history": load_history(), "has_saved_key": bool(load_api_key())}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    # 1. Key 处理
    current_key = (req.api_key or load_api_key() or "").strip()
    if not current_key:
        raise HTTPException(status_code=400, detail="请填写 API Key")

    # ✅ 兼容稳定版：用户传了 api_key 且允许记住时，就写入 secrets.json
    if req.remember_key and req.api_key and req.api_key not in ("true", "false"):
        if req.api_key.strip() != load_api_key():
            save_api_key(req.api_key.strip())

    # 2. Prompt 处理
    prompt = req.prompt
    parts = [{"text": prompt}]

    if req.ref_image:
        mime = "image/jpeg"
        raw = req.ref_image.strip()

        if raw.startswith("data:") and ";base64," in raw:
            mime = raw.split(";", 1)[0][5:]
            img = raw.split("base64,", 1)[1]
        else:
            img = raw.split("base64,", 1)[1] if "base64," in raw else raw
            head = img[:16]
            if head.startswith("iVBOR"):
                mime = "image/png"
            elif head.startswith("/9j/"):
                mime = "image/jpeg"
            elif head.startswith("R0lGOD"):
                mime = "image/gif"
            elif head.startswith("UklGR"):
                mime = "image/webp"

        parts.append({"inline_data": {"mime_type": mime, "data": img}})

    # 3. 请求 API
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "imageConfig": {"aspectRatio": req.aspect_ratio},
            "temperature": 0.9,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        },
    }

    base = DEFAULT_API_BASE_URL.rstrip("/")
    url = f"{base}/v1beta/models/{MODEL}:generateContent"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {current_key}"}

    try:
        logger.info(f"正在生成... Prompt: {prompt[:20]}...")
        TIMEOUT = (10, 300)
        response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)

        if response.status_code != 200:
            body = response.text or ""
            logger.error(f"API Error: {body}")

            if ("do_request_failed" in body) or (response.status_code in (500, 502, 503, 504)):
                logger.info("⚠️ 触发兼容降级：使用最简 generationConfig 重试一次...")
                fallback_payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {
                        "temperature": 0.9,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 8192,
                    },
                }
                response2 = requests.post(url, headers=headers, json=fallback_payload, timeout=TIMEOUT)
                if response2.status_code != 200:
                    body2 = response2.text or ""
                    logger.error(f"API Error (fallback): {body2}")
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "status": response2.status_code,
                            "body": body2[:2000],
                            "fallback": True,
                        },
                    )
                result = response2.json()
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "status": response.status_code,
                        "body": body[:2000],
                    },
                )
        else:
            result = response.json()

        b64 = extract_image_data(result)
        if not b64:
            logger.error(f"API Response: {str(result)[:200]}")
            raise HTTPException(status_code=500, detail="没有生成图片，可能是安全拦截。")

        if "base64," in b64:
            b64 = b64.split("base64,", 1)[1]

        # 4. 保存 (PNG 无损 + 元数据注入)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_style = re.sub(r"[^a-zA-Z0-9_]", "", (req.style_tag or "")).strip()[:20] or "Anime"
        filename = f"{safe_style}_{timestamp}.png"
        save_path = os.path.join(HISTORY_DIR, filename)

        img_bytes = base64.b64decode(b64)
        image = Image.open(io.BytesIO(img_bytes))

        png_info = PngImagePlugin.PngInfo()
        png_info.add_text("Prompt", req.prompt)
        png_info.add_text("NegativePrompt", "low quality, bad anatomy, worst quality, text, watermark")
        png_info.add_text("Style", req.style_tag or "Default")
        png_info.add_text("AspectRatio", req.aspect_ratio)
        png_info.add_text("Model", MODEL)
        png_info.add_text("Software", "Project 2D-Genesis (WaifuGen Local)")
        png_info.add_text("CreationTime", time.strftime("%Y-%m-%d %H:%M:%S"))
        if req.ref_image:
            png_info.add_text("ReferenceImage", "Yes")

        image.save(save_path, "PNG", pnginfo=png_info)
        logger.info(f"✅ 图片已保存(含元数据): {save_path}")

        meta = req.metadata or {}
        if not isinstance(meta, dict):
            meta = {}
        meta.setdefault("model", MODEL)
        meta.setdefault("software", "WaifuGen Local")

        record = {
            "filename": filename,
            "prompt": req.prompt,
            "style": req.style_tag,
            "url": f"/static/history/{filename}",
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "aspect_ratio": req.aspect_ratio,
            "metadata": meta,
        }
        save_history_item(record)
        return record

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print(f"🚀 启动成功！请在浏览器访问: http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, reload=False, log_config=None, access_log=False)
