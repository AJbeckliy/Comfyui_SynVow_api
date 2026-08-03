"""
SynVow Nodes V2 — ComfyUI Custom Nodes
"""
from aiohttp import web
import aiohttp
import server
import json
import os
from datetime import datetime, timezone
import folder_paths

WEB_DIRECTORY = "./web"
API_BASE = "https://service.synvow.com/api/v1"

# ---------------------------------------------------------------------------
#  通用代理
# ---------------------------------------------------------------------------

async def _proxy(method, endpoint, request, *, with_body=False, auth="jwt"):
    """统一 API 代理。auth='jwt' 用 Bearer token，auth='apikey' 用 X-API-Key"""
    try:
        if auth == "apikey":
            headers = {"X-API-Key": request.headers.get("X-API-Key", ""),
                       "Content-Type": "application/json"}
        else:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        data = await request.json() if with_body else None
        qs = request.rel_url.query_string
        url = f"{API_BASE}{endpoint}" + (f"?{qs}" if qs else "")
        if data and isinstance(data, dict) and "user_id" in data:
            data["user_id"] = int(data["user_id"])



        timeout = aiohttp.ClientTimeout(total=15) if auth == "jwt" else None
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.request(method, url, json=data, headers=headers) as resp:
                text = await resp.text()
                try:
                    return web.json_response(json.loads(text))
                except json.JSONDecodeError:
                    return web.json_response({"code": resp.status, "message": f"非JSON: {text[:200]}"})
    except Exception as e:
        print(f"[SV] ERR {endpoint}: {e}")
        return web.json_response({"code": 500, "message": str(e)})


# ---------------------------------------------------------------------------
#  批量路由注册（简单代理，无特殊逻辑）
# ---------------------------------------------------------------------------

_JWT_ROUTES = [
    # (method, local_path, remote_endpoint, with_body)
    ("POST", "/sv_api/auth/login",                  "/auth/login",                  True),
    ("POST", "/sv_api/auth/register",               "/auth/register",               True),
    ("POST", "/sv_api/auth/send-code",              "/auth/send-code",              True),
    ("POST", "/sv_api/auth/send-email-code",        "/auth/send-email-code",        True),
    ("POST", "/sv_api/auth/reset-password",         "/auth/reset-password",         True),
    ("POST", "/sv_api/auth/change-password",        "/auth/change-password",        True),
    ("POST", "/sv_api/auth/wechat/login-url",       "/auth/wechat/login-url",       True),
    ("POST", "/sv_api/auth/wechat/login",           "/auth/wechat/login",           True),
    ("POST", "/sv_api/auth/qrcode/token",           "/auth/qrcode/token",           True),
    ("POST", "/sv_api/auth/wechat/create-session",  "/auth/wechat/create-session",  True),
    ("POST", "/sv_api/auth/wechat/bind/url",        "/auth/wechat/bind/url",        True),
    ("POST", "/sv_api/auth/wechat/bind/verify",     "/auth/wechat/bind/verify",     True),
    ("POST", "/sv_api/auth/wechat/bind/status",     "/auth/wechat/bind/status",     True),
    ("POST", "/sv_api/account/recharge",            "/account/recharge",            True),
    ("POST", "/sv_api/user/bind-phone",             "/user/bind-phone",             True),
    ("POST", "/sv_api/api-key",                     "/api-key",                     True),
    ("PUT",  "/sv_api/user/info",                   "/user/info",                   True),
    ("GET",  "/sv_api/account/balance",             "/account/balance",             False),
    ("GET",  "/sv_api/account/info",                "/account/info",                False),
    ("GET",  "/sv_api/account/summary",             "/account/summary",             False),
    ("GET",  "/sv_api/user/info",                   "/user/info",                   False),
    ("GET",  "/sv_api/user/with-account",           "/user/with-account",           False),
    ("GET",  "/sv_api/api-key",                     "/api-key",                     False),
    ("GET",  "/sv_api/models",                      "/models",                      False),
    ("GET",  "/sv_api/models/public-list",          "/models/public-list",          False),
]

_APIKEY_ROUTES = [
    ("GET",  "/sv_api/api/models",                      "/api/models",                      False),
    ("POST", "/sv_api/api/models/chat/completions",     "/api/models/chat/completions",     True),
    ("POST", "/sv_api/api/models/completions",          "/api/models/completions",          True),
    ("POST", "/sv_api/api/models/image/edit",           "/api/models/image/edit",           True),
]

def _register_routes():
    router = server.PromptServer.instance.routes

    for method, path, endpoint, body in _JWT_ROUTES:
        ep = endpoint  # 闭包捕获
        bd = body
        if method == "GET":
            @router.get(path)
            async def _h(req, _ep=ep):
                return await _proxy("GET", _ep, req)
        elif method == "PUT":
            @router.put(path)
            async def _h(req, _ep=ep):
                return await _proxy("PUT", _ep, req, with_body=True)
        else:
            @router.post(path)
            async def _h(req, _ep=ep, _bd=bd):
                return await _proxy("POST", _ep, req, with_body=_bd)

    for method, path, endpoint, body in _APIKEY_ROUTES:
        ep = endpoint
        bd = body
        if method == "GET":
            @router.get(path)
            async def _h(req, _ep=ep):
                return await _proxy("GET", _ep, req, auth="apikey")
        else:
            @router.post(path)
            async def _h(req, _ep=ep, _bd=bd):
                return await _proxy("POST", _ep, req, with_body=_bd, auth="apikey")

_register_routes()


# ---------------------------------------------------------------------------
#  特殊路由（有自定义逻辑，不能用通用代理）
# ---------------------------------------------------------------------------

@server.PromptServer.instance.routes.get("/sv_api/auth/wechat/check-session")
async def _sv_wechat_check_session(request):
    """GET 带 query 参数的代理"""
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        session_id = request.query.get("session_id", "")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"{API_BASE}/auth/wechat/check-session?session_id={session_id}"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, headers=headers) as resp:
                text = await resp.text()
                try:
                    return web.json_response(json.loads(text))
                except json.JSONDecodeError:
                    return web.json_response({"code": resp.status, "message": text[:200]})
    except Exception as e:
        return web.json_response({"code": 500, "message": str(e)})


@server.PromptServer.instance.routes.get("/sv_api/account/recharge-records")
async def _sv_recharge_records(request):
    """GET 带分页 query 参数"""
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        page = request.query.get("page", "1")
        per_page = request.query.get("per_page", "10")
        url = f"{API_BASE}/account/recharge-records?page={page}&per_page={per_page}"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, headers={"Authorization": f"Bearer {token}"}) as resp:
                return web.json_response(await resp.json())
    except Exception as e:
        return web.json_response({"code": 500, "message": str(e)})


@server.PromptServer.instance.routes.get("/sv_api/account/consumption-records")
async def _sv_consumption_records(request):
    """GET 带分页 query 参数"""
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        page = request.query.get("page", "1")
        page_size = request.query.get("page_size", "20")
        url = f"{API_BASE}/account/consumption-records?page={page}&page_size={page_size}"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, headers={"Authorization": f"Bearer {token}"}) as resp:
                return web.json_response(await resp.json())
    except Exception as e:
        return web.json_response({"code": 500, "message": str(e)})


def _get_auth_file_path():
    return os.path.join(folder_paths.get_user_directory(), "synvow_auth.json")


def _clear_auth_file():
    path = _get_auth_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "token": "",
            "refresh_token": "",
            "api_key": "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": 0
        }, f, ensure_ascii=False, indent=2)


@server.PromptServer.instance.routes.post("/sv_api/auth/refresh")
async def _sv_refresh_token(request):
    """刷新 token 并更新本地文件"""
    try:
        body = await request.json()
        token = body.get("token", "")
        refresh_token = body.get("refresh_token", "")
        if not token and not refresh_token:
            _clear_auth_file()
            return web.json_response({"code": 400, "message": "token or refresh_token is required"})

        auth_token = refresh_token or token
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"{API_BASE}/auth/refresh", headers=headers) as resp:
                text = await resp.text()
                try:
                    result = json.loads(text)
                except json.JSONDecodeError:
                    _clear_auth_file()
                    return web.json_response({"code": resp.status, "message": text[:200]})

                if result.get("code") == 200 and result.get("data"):
                    new_access = result["data"].get("access_token", "")
                    if new_access:
                        path = _get_auth_file_path()
                        auth_data = {}
                        if os.path.exists(path):
                            with open(path, "r", encoding="utf-8") as f:
                                auth_data = json.load(f)
                        auth_data["token"] = new_access
                        new_refresh = result["data"].get("refresh_token")
                        if new_refresh:
                            auth_data["refresh_token"] = new_refresh
                        auth_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(auth_data, f, ensure_ascii=False, indent=2)
                        print("[SV] Token refreshed & saved")
                else:
                    _clear_auth_file()

                return web.json_response(result)
    except Exception as e:
        print(f"[SV] refresh ERR: {e}")
        _clear_auth_file()
        return web.json_response({"code": 500, "message": str(e)})


@server.PromptServer.instance.routes.post("/sv_api/auth/save-token")
async def _sv_save_token(request):
    """接收 JWT，自动生成/复用 API Key，写入本地文件"""
    try:
        body = await request.json()
        token = body.get("token", "")
        if not token:
            _clear_auth_file()
            return web.json_response({"code": 400, "message": "token is required"})

        auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        api_key = None

        async with aiohttp.ClientSession() as sess:
            # 查找已有的 comfyui_auto key
            async with sess.get(f"{API_BASE}/api-key", headers=auth_headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    raw = result.get("data", result) if isinstance(result, dict) else result
                    if isinstance(raw, dict):
                        keys = raw.get("list", raw.get("data", []))
                    else:
                        keys = raw
                    if isinstance(keys, list):
                        api_key = next((k.get("api_key") or k.get("key")
                                        for k in keys if isinstance(k, dict) and k.get("is_active")), None)

            # 没有则创建
            if not api_key:
                async with sess.post(f"{API_BASE}/api-key", json={"description": "comfyui_auto"}, headers=auth_headers) as resp:
                    if resp.status in (200, 201):
                        result = await resp.json()
                        data = result.get("data", result) if isinstance(result, dict) else result
                        api_key = data.get("api_key") or data.get("key") if isinstance(data, dict) else data
                    else:
                        _clear_auth_file()
                        return web.json_response({"code": 500, "message": "生成 API Key 失败"})

        if not api_key:
            _clear_auth_file()
            return web.json_response({"code": 500, "message": "未能获取到有效的 API Key"})

        path = _get_auth_file_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import time as _time
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "token": token,
                "refresh_token": body.get("refresh_token", ""),
                "api_key": api_key,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": _time.time() + 7 * 24 * 3600
            }, f, ensure_ascii=False, indent=2)

        return web.json_response({"code": 200, "message": "ok"})
    except Exception as e:
        print(f"[SV] save-token ERR: {e}")
        _clear_auth_file()
        return web.json_response({"code": 500, "message": str(e)})


@server.PromptServer.instance.routes.post("/sv_api/auth/clear-token")
async def _sv_clear_token(request):
    """清空本地认证文件"""
    try:
        _clear_auth_file()
        return web.json_response({"code": 200, "message": "ok"})
    except Exception as e:
        return web.json_response({"code": 500, "message": str(e)})


# ---------------------------------------------------------------------------
#  动态加载节点
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

import glob
import importlib

_py_dir = os.path.join(os.path.dirname(__file__), "py")
_py_files = glob.glob(os.path.join(_py_dir, "**", "*.py"), recursive=True)

for _f in _py_files:
    _relative_path = os.path.relpath(_f, _py_dir)
    _module_name = os.path.splitext(_relative_path)[0].replace(os.sep, ".")
    if _module_name == "__init__" or _module_name.endswith(".__init__"):
        continue
    try:
        _mod = importlib.import_module(f".py.{_module_name}", package=__package__)
        if hasattr(_mod, "NODE_CLASS_MAPPINGS"):
            NODE_CLASS_MAPPINGS.update(_mod.NODE_CLASS_MAPPINGS)
        if hasattr(_mod, "NODE_DISPLAY_NAME_MAPPINGS"):
            NODE_DISPLAY_NAME_MAPPINGS.update(_mod.NODE_DISPLAY_NAME_MAPPINGS)
    except Exception as e:
        print(f"[SV] Failed to import {_module_name}: {e}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
