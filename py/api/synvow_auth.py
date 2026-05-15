"""
SynVow 统一认证工具模块

提供 Token 文件读取、API Key 获取、请求头构建等公共功能，
供所有节点文件（nanobanana、gemini 等）调用。
"""

import json
import os
import time
import threading

import folder_paths
import requests


DIRECT_API_BASE = "https://service.synvow.com/api/v1"

TOKEN_FILE = os.path.join(folder_paths.get_user_directory(), "synvow_auth.json")


def clear_auth_file():
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "token": "",
            "refresh_token": "",
            "api_key": "",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "expires_at": 0
        }, f, ensure_ascii=False, indent=2)


def read_api_key():
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("请先登录 SynVow")

    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise RuntimeError("认证文件读取失败，请重新登录 SynVow") from e

    api_key = data.get("api_key")
    if not api_key:
        raise RuntimeError("未找到有效的凭证，请重新登录 SynVow")

    expires_at = data.get("expires_at")
    if expires_at and time.time() > expires_at:
        clear_auth_file()
        raise RuntimeError("SynVow 登录已过期，请重新登录")

    return api_key


def make_api_headers(api_key):
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }


def parse_chat_response(data):
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    if "candidates" in data:
        candidates = data["candidates"]
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            texts = [p.get("text", "") for p in parts if "text" in p]
            return "".join(texts)

    if "choices" in data:
        source_choices = data.get("sourceData", {}).get("choices", [])
        if source_choices:
            return source_choices[0].get("message", {}).get("content", "")
        choices = data["choices"]
        if choices:
            return choices[0].get("message", {}).get("content", "")

    return ""


_model_cache = {
    "models": [],
    "fetched_at": 0,
    "ttl": 300,
}

_DEFAULT_MODELS = {
    "image": ["奶糯芭娜娜-2K", "奶糯芭娜娜-文生图-2K"],
    "video": [],
    "chat": ["gemini-3-flash-preview", "gemini-3-pro-preview"],
}


def fetch_model_list(api_key):
    now = time.time()
    if _model_cache["models"] and (now - _model_cache["fetched_at"]) < _model_cache["ttl"]:
        return _model_cache["models"]

    try:
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


_CATEGORY_TAG_MAP = {
    "image": ["图形生成"],
    "video": ["视频"],
    "chat": ["文本对话", "多模态"],
}


def _filter_models_by_category(models, category):
    target_tags = _CATEGORY_TAG_MAP.get(category, [])
    names = []
    for m in models:
        if isinstance(m, dict):
            model_name = m.get("name", m.get("id", ""))
            if not model_name:
                continue
            if target_tags:
                raw_tags = m.get("tags", [])
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
    try:
        api_key = read_api_key()
        fetch_model_list(api_key)
    except Exception:
        pass

_sync_prefetch_cache()


def get_model_list(category="image"):
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

    _async_refresh_cache()
    return defaults


def get_pool_categories():
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
    return [name for name, _ in get_pool_categories()]


def get_model_list_by_pool(pool_name, category="image"):
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
    fallback = default if default is not None else [f"{prefix}-default"]
    names = get_model_list(category)
    filtered = [n for n in names if n.lower().startswith(prefix.lower())]
    return filtered if filtered else fallback
