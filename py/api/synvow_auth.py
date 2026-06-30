"""
SynVow 统一认证工具模块

提供 Token 文件读取、API Key 获取、请求头构建等公共功能，
供所有节点文件（nanobanana、gemini 等）调用。
"""

import json
import os
import time

import folder_paths


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


def refresh_balance():
    try:
        import server
        server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
    except Exception:
        pass


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
