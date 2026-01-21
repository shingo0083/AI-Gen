import os
import json
import time
import base64
import logging
import io  # <--- 新增
from PIL import Image, PngImagePlugin
import requests
import uvicorn
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

HISTORY_LIMIT = 100
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

HISTORY_LIMIT = _env_int("WF_HISTORY_LIMIT", HISTORY_LIMIT)

# --- 路径自动获取 (适配 Windows/Mac) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "static", "history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "history.json")
SECRETS_FILE = os.path.join(BASE_DIR, "secrets.json")

# --- 日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    prompt: str
    style_tag: Optional[str] = "Default"
    aspect_ratio: str = "1:1"
    ref_image: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# --- 辅助函数 ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)

            # === 修复逻辑：自动清洗不存在的文件 ===
            valid_history = []
            dirty = False # 标记是否发现了脏数据

            for item in history:
                # 获取文件名，例如 "Anime_20260118.png"
                filename = item.get("filename")
                if not filename: continue

                # 拼凑出绝对路径进行检查
                file_path = os.path.join(HISTORY_DIR, filename)
                
                # 只有文件真正存在时，才保留这条记录
                if os.path.exists(file_path):
                    valid_history.append(item)
                else:
                    dirty = True # 发现有记录但没文件，标记需要更新

            # 如果发现了脏数据，不仅返回清洗后的列表，还要把清洗后的结果写回 json 文件
            # 这样下次读取就不用再检查一遍了，提升性能
            if dirty:
                logger.info(f"🧹 发现无效记录，正在自动清理...")
                valid_history = valid_history[:HISTORY_LIMIT]
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(valid_history, f, ensure_ascii=False, indent=2)
            
            return valid_history[:HISTORY_LIMIT]

        except Exception as e: 
            logger.error(f"读取历史记录出错: {e}")
            return []
    return []

def save_history_item(item):
    history = load_history()
    history.insert(0, item)
    history = history[:HISTORY_LIMIT]  # 统一上限
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_api_key():
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return (data.get("api_key") or data.get("OPENAI_API_KEY") or data.get("key") or "").strip()
        except: pass
    return ""

def save_api_key(key):
    try:
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": key}, f)
    except: pass

def extract_image_data(result):
    if 'candidates' in result:
        try:
            for part in result['candidates'][0]['content']['parts']:
                if 'inline_data' in part: return part['inline_data']['data']
                elif 'inlineData' in part: return part['inlineData']['data']
        except: pass
    if 'data' in result: return result['data']
    if 'image' in result: return result['image']
    if 'generatedImages' in result:
        try: return result['generatedImages'][0]['data']
        except: pass
    return None

# --- 路由 ---
@app.get("/")
def read_index():
    return FileResponse(os.path.join(BASE_DIR, 'index.html'))

@app.get("/api/init")
def init_data():
    return {"history": load_history(), "has_saved_key": bool(load_api_key())}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    # 1. Key 处理
    current_key = req.api_key or load_api_key()
    if not current_key:
        raise HTTPException(status_code=400, detail="请填写 API Key")
    if req.api_key and req.api_key not in ("true", "false"):
        if req.api_key != load_api_key():
            save_api_key(req.api_key)


    # 2. Prompt 处理
    # 重要：后端不再把 style_tag 拼进 prompt（避免与 core 的风格注入重复）
    prompt = req.prompt
    
    parts = [{"text": prompt}]

    if req.ref_image:
        # 允许两种输入：
        # 1) data URL: data:image/png;base64,xxxx
        # 2) 纯 base64: xxxx
        mime = "image/jpeg"
        raw = req.ref_image.strip()

        if raw.startswith("data:") and ";base64," in raw:
            # data:image/png;base64,....
            mime = raw.split(";", 1)[0][5:]  # 去掉 "data:"
            img = raw.split("base64,", 1)[1]
        else:
            # 兼容可能带 "base64," 的情况
            img = raw.split("base64,", 1)[1] if "base64," in raw else raw

            # 简单魔数嗅探（不解码，足够可靠）
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
            "temperature": 0.9, "topK": 40, "topP": 0.95, "maxOutputTokens": 8192
        }
    }
    
    base = DEFAULT_API_BASE_URL.rstrip("/")
    url = f"{base}/v1beta/models/{MODEL}:generateContent"

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {current_key}"}

    try:
        logger.info(f"正在生成... Prompt: {prompt[:20]}...")
        # 设置 300秒 超时，不用担心 Nginx 断连了
        response = requests.post(url, headers=headers, json=payload, timeout=300)
        if response.status_code != 200:
            body = response.text or ""
            logger.error(f"API Error: {body}")
            # 兼容降级：部分上游渠道对 imageConfig / 扩展字段不兼容，会在代理侧表现为 do_request_failed / 5xx
            if ("do_request_failed" in body) or (response.status_code in (500, 502, 503, 504)):
                logger.info("⚠️ 触发兼容降级：使用最简 generationConfig 重试一次...")
                fallback_payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {
                        "temperature": 0.9,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 8192
                    }
                }
                response2 = requests.post(url, headers=headers, json=fallback_payload, timeout=300)
                if response2.status_code != 200:
                    body2 = response2.text or ""
                    logger.error(f"API Error (fallback): {body2}")
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "status": response2.status_code,
                            "body": body2[:2000],
                            "fallback": True
                        },
                    )

                result = response2.json()
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "status": response.status_code,
                        "body": body[:2000]
                    },
                )

        else:
            result = response.json()

        b64 = extract_image_data(result)
        
        if not b64:
            logger.error(f"API Response: {str(result)[:200]}")
            raise HTTPException(status_code=500, detail="没有生成图片，可能是安全拦截。")

        if 'base64,' in b64: b64 = b64.split('base64,')[1]

        # 4. 保存 (核心升级：PNG 无损格式 + 元数据注入)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_style = re.sub(r'[^a-zA-Z0-9_]', '', req.style_tag).strip()[:20] or "Anime"
        
        # ⚠️ 改动1: 后缀名改为 .png (无损，适合二次元)
        filename = f"{safe_style}_{timestamp}.png"
        save_path = os.path.join(HISTORY_DIR, filename)

        # 解码图片数据
        img_bytes = base64.b64decode(b64)
        
        # ⚠️ 改动2: 使用 Pillow 加载图片
        image = Image.open(io.BytesIO(img_bytes))

        # ⚠️ 改动3: 注入元数据 (Metadata Injection)
        png_info = PngImagePlugin.PngInfo()
        # 写入核心咒语
        png_info.add_text("Prompt", req.prompt)
        png_info.add_text("NegativePrompt", "low quality, bad anatomy, worst quality, text, watermark") # 默认负面词
        # 写入参数
        png_info.add_text("Style", req.style_tag)
        png_info.add_text("AspectRatio", req.aspect_ratio)
        png_info.add_text("Model", MODEL)
        png_info.add_text("Software", "Project 2D-Genesis (WaifuGen Local)")
        png_info.add_text("CreationTime", time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 如果有参考图，也可以标记一下
        if req.ref_image:
            png_info.add_text("ReferenceImage", "Yes")

        # 保存图片，并附带 pnginfo
        image.save(save_path, "PNG", pnginfo=png_info)
            
        logger.info(f"✅ 图片已保存(含元数据): {save_path}")
        
        # 组装 metadata：优先使用前端传来的 req.metadata，同时补齐固定字段
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
            "metadata": meta
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
uvicorn.run("server:app", host=HOST, port=PORT, reload=True, log_config=None, access_log=False)
