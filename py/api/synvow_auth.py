"""
SynVow 统一认证工具模块

提供 Token 文件读取、API Key 获取、请求头构建等公共功能，
供所有节点文件（nanobanana、sora2、gemini 等）调用。
"""

import json
import os
import sys
import time
import threading

import folder_paths

import base64
import io

import numpy as np
import torch
from PIL import Image
import requests


# Token 文件路径
TOKEN_FILE = os.path.join(folder_paths.get_user_directory(), "synvow_auth.json")


def read_api_key():
    """从 synvow_auth.json 读取 api_key。

    Returns:
        str: 有效的 API Key

    Raises:
        RuntimeError: 文件不存在或 api_key 为空时抛出
    """
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("请先 SynVow 登录，然后再登录")

    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise RuntimeError("请先 SynVow 登录，然后再登录") from e

    api_key = data.get("api_key")
    if not api_key:
        raise RuntimeError("请先 SynVow 登录，然后再登录")

    return api_key


def get_proxy_base():
    """返回 Login_Plugin 代理路由的基础 URL。

    端口检测优先级:
    1. server.PromptServer.instance.port (ComfyUI 运行时)
    2. sys.argv 中的 --port 参数
    3. 默认 8188

    Returns:
        str: 形如 "http://127.0.0.1:{port}/sv_api"
    """
    port = 8188  # ComfyUI 默认端口

    # 优先从 PromptServer 实例获取端口
    try:
        import server
        port = server.PromptServer.instance.port
        return f"http://127.0.0.1:{port}/sv_api"
    except Exception:
        pass

    # 备选: 从命令行参数中读取 --port
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == "--port" and i + 1 < len(argv):
            try:
                port = int(argv[i + 1])
            except ValueError:
                pass
            break

    return f"http://127.0.0.1:{port}/sv_api"


def make_api_headers(api_key):
    """构建包含 X-API-Key 的请求头字典。

    Args:
        api_key: API Key 字符串

    Returns:
        dict: 包含 X-API-Key 和 Content-Type 的请求头
    """
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# 图片工具函数
# ---------------------------------------------------------------------------


def tensor_to_data_uri(tensor, quality=85):
    """ComfyUI tensor [B,H,W,C] -> data URI string。

    Args:
        tensor: PyTorch tensor，shape [B, H, W, C]，float32 范围 [0, 1]
        quality: JPEG 压缩质量 (1-100)，默认 85

    Returns:
        str: data URI 格式字符串，如 "data:image/jpeg;base64,..."
    """
    img_np = (tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(img_np)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def data_uri_to_tensor(data_uri):
    """data URI -> ComfyUI tensor [1,H,W,C]。

    Args:
        data_uri: data URI 格式字符串

    Returns:
        torch.Tensor: shape [1, H, W, C]，float32 范围 [0, 1]
    """
    header, b64_data = data_uri.split(",", 1)
    img_bytes = base64.b64decode(b64_data)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_np = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)


def url_to_tensor(url):
    """图片 URL -> ComfyUI tensor [1,H,W,C]。

    Args:
        url: 图片的 HTTP(S) URL

    Returns:
        torch.Tensor: shape [1, H, W, C]，float32 范围 [0, 1]

    Raises:
        requests.HTTPError: 请求失败时抛出
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    img_np = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)


def compress_image(tensor, max_size=1024, quality=85):
    """缩图压缩，返回压缩后的 tensor。

    若图片长边超过 max_size，等比缩小到 max_size。

    Args:
        tensor: PyTorch tensor，shape [B, H, W, C]，float32 范围 [0, 1]
        max_size: 最长边的最大像素数，默认 1024
        quality: 未使用，保留参数（调用 tensor_to_data_uri 时再用）

    Returns:
        torch.Tensor: shape [1, H, W, C]，float32 范围 [0, 1]
    """
    img_np = (tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(img_np)
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    img_np = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)


# ---------------------------------------------------------------------------
# 响应解析和格式转换函数
# ---------------------------------------------------------------------------


def messages_to_contents(messages):
    """OpenAI messages -> Gemini contents 格式转换。

    Args:
        messages: OpenAI 格式消息列表，例如:
            [{"role": "user", "content": "Hello"},
             {"role": "assistant", "content": "Hi"}]
            content 也可以是多模态列表:
            [{"type": "text", "text": "describe"},
             {"type": "image_url", "image_url": {"url": "data:image/..."}}]

    Returns:
        list: Gemini contents 格式列表，例如:
            [{"role": "user", "parts": [{"text": "Hello"}]},
             {"role": "model", "parts": [{"text": "Hi"}]}]
    """
    contents = []
    for msg in messages:
        role = "model" if msg.get("role") == "assistant" else msg.get("role", "user")
        content = msg.get("content", "")
        parts = []
        if isinstance(content, str):
            parts.append({"text": content})
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    parts.append({"text": item.get("text", "")})
                elif item.get("type") == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        header, b64_data = url.split(",", 1)
                        mime_type = header.split(":")[1].split(";")[0]
                        parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})
                    else:
                        parts.append({"text": f"[Image: {url}]"})
        contents.append({"role": role, "parts": parts})
    return contents


def parse_chat_response(data):
    """解析 Gemini/OpenAI/SynVow 聊天响应格式，返回文本内容。

    支持的格式:
    1. Gemini: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
    2. OpenAI: {"choices": [{"message": {"content": "..."}}]}
    3. SynVow 包装: {"data": {"choices": [...]}} 或 {"data": {"candidates": [...]}}

    Args:
        data: 响应数据字典

    Returns:
        str: 解析出的文本内容
    """
    # Unwrap SynVow wrapper
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    # Gemini format
    if "candidates" in data:
        candidates = data["candidates"]
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            texts = [p.get("text", "") for p in parts if "text" in p]
            return "".join(texts)

    # OpenAI format
    if "choices" in data:
        choices = data["choices"]
        if choices:
            msg = choices[0].get("message", {})
            return msg.get("content", "")

    return ""


def parse_image_response(data):
    """图片响应解析，返回 {"type": ..., "value": ...} 字典。

    支持的格式:
    1. URL: {"data": [{"url": "https://..."}]} 或 {"url": "https://..."}
    2. Base64: {"data": [{"b64_json": "..."}]} 或 {"b64_json": "..."}
    3. SynVow 包装: {"data": {"data": [{"url": "..."}]}}

    Args:
        data: 响应数据字典

    Returns:
        dict: {"type": "url"/"b64_json", "value": "..."}

    Raises:
        ValueError: 无法解析图片响应时抛出
    """
    # Unwrap SynVow wrapper
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], (dict, list)):
        inner = data["data"]
        if isinstance(inner, dict) and "data" in inner:
            inner = inner["data"]
        if isinstance(inner, list) and inner:
            item = inner[0]
            if "url" in item:
                return {"type": "url", "value": item["url"]}
            if "b64_json" in item:
                return {"type": "b64_json", "value": item["b64_json"]}

    # Direct format
    if isinstance(data, dict):
        if "url" in data:
            return {"type": "url", "value": data["url"]}
        if "b64_json" in data:
            return {"type": "b64_json", "value": data["b64_json"]}
        if "data" in data and isinstance(data["data"], list) and data["data"]:
            item = data["data"][0]
            if "url" in item:
                return {"type": "url", "value": item["url"]}
            if "b64_json" in item:
                return {"type": "b64_json", "value": item["b64_json"]}

    raise ValueError(f"无法解析图片响应: {str(data)[:200]}")


# ---------------------------------------------------------------------------
# 模型列表动态获取
# ---------------------------------------------------------------------------

# 模块级缓存
_model_cache = {
    "models": [],
    "fetched_at": 0,
    "ttl": 300,  # 5 分钟
}

# 默认降级模型列表（与现有节点硬编码名称对应）
_DEFAULT_MODELS = {
    "image": ["奶糯芭娜娜-2K", "奶糯芭娜娜-文生图-2K"],
    "video": ["sora-2", "veo3.1"],
    "chat": ["gemini-3-flash-preview", "gemini-3-pro-preview"],
}


def fetch_model_list(api_key):
    """通过代理路由获取模型列表并缓存。

    优先返回缓存数据（TTL 300 秒内），过期后重新请求。
    请求失败时返回上次缓存的数据，若无缓存则返回空列表。

    Args:
        api_key: API Key 字符串

    Returns:
        list: 模型列表（每个元素为 dict 或 str）
    """
    now = time.time()
    if _model_cache["models"] and (now - _model_cache["fetched_at"]) < _model_cache["ttl"]:
        return _model_cache["models"]

    try:
        # 直接请求外部 API，避免 ComfyUI 事件循环死锁
        DIRECT_API_BASE = "https://service.synvow.com/api/v1"
        headers = make_api_headers(api_key)
        all_models = []
        page = 1
        while True:
            resp = requests.get(f"{DIRECT_API_BASE}/api/models?page={page}&per_page=50", headers=headers, timeout=10, verify=False)
            resp.raise_for_status()
            data = resp.json()
            inner = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(inner, dict):
                models = inner.get("list", inner.get("items", inner.get("data", [])))
                page_size = inner.get("page_size", 10)
                total = inner.get("total", len(models))
                total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
            elif isinstance(inner, list):
                models = inner
                total_pages = 1
            else:
                break
            if not models:
                break
            all_models.extend(models)
            if page >= total_pages:
                break
            page += 1
        models = all_models
        if isinstance(models, list) and len(models) > 0:
            _model_cache["models"] = models
            _model_cache["fetched_at"] = now
            return models
    except Exception as e:
        print(f"[SynVow] 获取模型列表失败: {e}")

    return _model_cache["models"] if _model_cache["models"] else []


# category → 后台 tag name 映射（支持多个标签，满足其一即匹配）
_CATEGORY_TAG_MAP = {
    "image": ["图形生成"],
    "video": ["视频"],
    "chat": ["文本对话", "多模态"],
}


def _filter_models_by_category(models, category):
    """按后台 tags 字段筛选模型，返回名称列表。
    tags 可能是字符串数组 ["语言", "多模态"] 或对象数组 [{"name": "语言"}]，两种都兼容。
    """
    target_tags = _CATEGORY_TAG_MAP.get(category, [])
    names = []
    for m in models:
        if isinstance(m, dict):
            model_name = m.get("name", m.get("id", ""))
            if not model_name:
                continue
            if target_tags:
                raw_tags = m.get("tags", [])
                # 兼容字符串数组和对象数组
                if raw_tags and isinstance(raw_tags[0], dict):
                    tag_names = [t.get("name", "") for t in raw_tags]
                else:
                    tag_names = [str(t) for t in raw_tags]
                if any(t in tag_names for t in target_tags):
                    names.append(model_name)
            else:
                names.append(model_name)
        elif isinstance(m, str):
            names.append(m)
    return names


_refresh_lock = threading.Lock()
_refresh_pending = False


def _async_refresh_cache():
    """后台线程异步刷新模型列表缓存，避免阻塞节点加载。"""
    global _refresh_pending
    with _refresh_lock:
        if _refresh_pending:
            return
        _refresh_pending = True

    def _do_refresh():
        global _refresh_pending
        try:
            api_key = read_api_key()
            fetch_model_list(api_key)
        except Exception as e:
            print(f"[SynVow] 后台刷新模型列表失败: {e}")
        finally:
            with _refresh_lock:
                _refresh_pending = False

    threading.Thread(target=_do_refresh, daemon=True).start()


def _sync_prefetch_cache():
    """插件加载时同步预拉取模型列表，直接请求外部 API 不会死锁。"""
    try:
        api_key = read_api_key()
        fetch_model_list(api_key)
    except Exception as e:
        print(f"[SynVow] 模型列表预加载失败（将使用默认列表）: {e}")

# 模块导入时同步预拉取一次
_sync_prefetch_cache()


def get_model_list(category="image"):
    """按类别返回模型名称列表，失败时降级为硬编码默认列表。

    节点加载阶段（INPUT_TYPES 调用）如果缓存为空，直接返回默认列表并触发后台异步刷新，
    避免在 ComfyUI 启动时同步请求自身代理路由导致死锁/超时。

    Args:
        category: 模型类别，可选 "image"、"video"、"chat"

    Returns:
        list[str]: 模型名称列表
    """
    defaults = _DEFAULT_MODELS.get(category, _DEFAULT_MODELS.get("image", []))

    if _model_cache["models"]:
        names = _filter_models_by_category(_model_cache["models"], category)
        if names:
            if (time.time() - _model_cache["fetched_at"]) >= _model_cache["ttl"]:
                _async_refresh_cache()
            for d in defaults:
                if d not in names:
                    names.append(d)
            return names

    # 缓存为空：返回默认列表，后台异步刷新
    _async_refresh_cache()
    return defaults


def get_pool_categories():
    """从缓存模型列表中提取所有 API 池分类，返回 [(display_name, code), ...] 列表。

    第一项固定为 ("全部", "all")，后续按 sort 字段排序。

    Returns:
        list[tuple]: [(display_name, code), ...]，例如 [("全部","all"),("默认","default"),("G官方","official")]
    """
    seen = {}
    for m in _model_cache.get("models", []):
        if not isinstance(m, dict):
            continue
        pool = m.get("api_pool_category")
        if isinstance(pool, dict):
            code = pool.get("code", "")
            name = pool.get("name", code)
            sort = pool.get("sort", 99)
            if code and code not in seen:
                seen[code] = (name, sort)
    sorted_pools = sorted(seen.items(), key=lambda x: x[1][1])
    result = [("全部", "all")] + [(v[0], k) for k, v in sorted_pools]
    return result


def get_pool_category_names():
    """返回 API 池分类的显示名称列表（用于节点下拉框）。"""
    return [name for name, _ in get_pool_categories()]


def get_model_list_by_pool(pool_name, category="image"):
    """按 API 池显示名称 + 类别筛选模型，返回名称列表。

    Args:
        pool_name: API 池显示名称，"全部" 表示不过滤池
        category: 模型类别，可选 "image"、"video"、"chat"

    Returns:
        list[str]: 模型名称列表
    """
    # 找到对应的 pool code
    pool_code = "all"
    for name, code in get_pool_categories():
        if name == pool_name:
            pool_code = code
            break

    models = _model_cache.get("models", [])
    if pool_code != "all":
        models = [m for m in models if isinstance(m, dict) and
                  isinstance(m.get("api_pool_category"), dict) and
                  m["api_pool_category"].get("code") == pool_code]

    if not models:
        return get_model_list(category)

    names = _filter_models_by_category(models, category)
    defaults = _DEFAULT_MODELS.get(category, [])
    if not names:
        return defaults
    return names


def get_model_list_by_prefix(prefix, category="video", default=None):
    """从视频（或指定类别）模型列表中，筛选名称以 prefix 开头的模型。

    Args:
        prefix: 名称前缀，如 "veo"、"sora"、"kling"
        category: 模型类别，默认 "video"
        default: 缓存为空时的降级列表，None 则用 [prefix + "-default"]

    Returns:
        list[str]: 匹配的模型名称列表
    """
    fallback = default if default is not None else [f"{prefix}-default"]
    names = get_model_list(category)
    filtered = [n for n in names if n.lower().startswith(prefix.lower())]
    return filtered if filtered else fallback
