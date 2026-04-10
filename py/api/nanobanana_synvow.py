"""
NanoBanana SynVow API nodes - 图像生成 / 批量生成
传图走图生图，不传图走文生图，模型固定 nano-banana-2
"""

import io
import time
import uuid
import asyncio

import numpy as np
import requests
import aiohttp
import torch
import urllib3
from PIL import Image, ImageOps
from concurrent.futures import ThreadPoolExecutor, as_completed
import server
from aiohttp import web

from . import synvow_auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pending_batch_sessions = {}
DIRECT_API_BASE = "https://service.synvow.com/api/v1"

# 模式 → 实际模型名（文生图 / 图生图）
MODE_OPTIONS = ["默认", "优质"]
MODE_T2I_MAP = {"默认": "nano-banana-2-文生图", "优质": "nano-banana-2-文生图-优质"}
MODE_I2I_MAP = {"默认": "nano-banana-2-默认", "优质": "nano-banana-2-优质"}


def create_session(unique_id, source):
    session_id = str(uuid.uuid4())
    pending_batch_sessions[session_id] = {"cancelled": False, "node_id": unique_id, "source": source}
    return session_id


def send_polling_status(unique_id, session_id, status, total=None):
    payload = {"node_id": unique_id, "session_id": session_id, "status": status}
    if total is not None:
        payload["total"] = total
    server.PromptServer.instance.send_sync("batch_polling_status", payload)


def cleanup_session(session_id):
    if session_id in pending_batch_sessions:
        del pending_batch_sessions[session_id]


def tensor_to_pil_image(image_tensor):
    if len(image_tensor.shape) > 3:
        image_tensor = image_tensor[0]
    i = 255. * image_tensor.cpu().numpy()
    return Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))


# 全部比例（Nano2 使用）
ASPECT_RATIOS = {
    "1:1": (1, 1), "2:3": (2, 3), "3:2": (3, 2), "3:4": (3, 4), "4:3": (4, 3),
    "4:5": (4, 5), "5:4": (5, 4), "9:16": (9, 16), "16:9": (16, 9), "21:9": (21, 9),
    "1:4": (1, 4), "4:1": (4, 1), "1:8": (1, 8), "8:1": (8, 1),
}

# NanoBanana Pro 支持的比例（不含 1:4/4:1/1:8/8:1）
PRO_ASPECT_RATIOS = {k: v for k, v in ASPECT_RATIOS.items()
                     if k not in ("1:4", "4:1", "1:8", "8:1")}


def calc_size_from_ratio(aspect_ratio, image_size):
    base_sizes = {"1K": 1024, "2K": 2048, "4K": 4096}
    base = base_sizes.get(image_size, 2048)
    if aspect_ratio not in ASPECT_RATIOS:
        return None, None
    w_ratio, h_ratio = ASPECT_RATIOS[aspect_ratio]
    if w_ratio >= h_ratio:
        w = base
        h = int(base * h_ratio / w_ratio)
    else:
        h = base
        w = int(base * w_ratio / h_ratio)
    return w, h


def find_closest_aspect_ratio(width, height):
    input_ratio = width / height
    best_match = "1:1"
    min_diff = float('inf')
    for name, (w, h) in ASPECT_RATIOS.items():
        diff = abs(input_ratio - w / h)
        if diff < min_diff:
            min_diff = diff
            best_match = name
    return best_match


def _check_auth_error(resp):
    if resp.status_code == 401:
        raise RuntimeError("Auth expired, please login again")


def _extract_task_id(response_json):
    if not isinstance(response_json, dict):
        return None
    task_data = response_json.get("data", {})
    return (
        response_json.get("task_id")
        or (task_data.get("task_id") if isinstance(task_data, dict) else None)
        or ((task_data.get("data") or {}).get("task_id") if isinstance(task_data, dict) else None)
        or ((task_data.get("sourceData") or {}).get("task_id") if isinstance(task_data, dict) else None)
    )


def submit_image_task(api_key, model, prompt, images=None, aspect_ratio=None, image_size=None, seed=0):
    url = f"{DIRECT_API_BASE}/api/models/image/edit"
    params = {"async": "true"}
    headers = synvow_auth.make_api_headers(api_key)

    data = {"model": model, "prompt": prompt, "response_format": "url", "async": "true"}
    if aspect_ratio:
        data["aspect_ratio"] = aspect_ratio
    if image_size:
        data["image_size"] = image_size
    if seed > 0:
        data["seed"] = seed

    tag = "I2I" if images else "T2I"

    if images:
        import base64
        data_uris = []
        for img in images:
            pil = img if hasattr(img, "save") else Image.fromarray(
                (np.array(img) * 255).clip(0, 255).astype(np.uint8)
            )
            rgb = pil.convert("RGB") if pil.mode != "RGB" else pil
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            data_uris.append(f"data:image/jpeg;base64,{b64}")
        data["image"] = data_uris[0]
        if len(data_uris) > 1:
            data["images"] = data_uris[1:]

    for attempt in range(3):
        res = requests.post(url, headers=headers, params=params, json=data, timeout=300, verify=False)
        if res.status_code in (502, 503, 504):
            print(f"[Warn] {tag} 服务器暂时不可用 ({res.status_code})，第{attempt+1}次重试...", flush=True)
            time.sleep(3 * (attempt + 1))
            continue
        break

    _check_auth_error(res)
    if not res.text.strip():
        raise Exception(f"Empty response from server (status {res.status_code})")
    try:
        response_json = res.json()
    except Exception:
        raise Exception(f"服务器返回非JSON (status {res.status_code}): {res.text[:200]}")

    resp_code = response_json.get("code", res.status_code) if isinstance(response_json, dict) else res.status_code
    if res.status_code != 200 or (isinstance(resp_code, int) and resp_code >= 400):
        msg = response_json.get("message", str(response_json)) if isinstance(response_json, dict) else str(response_json)
        raise Exception(f"Request failed ({resp_code}): {msg[:200]}")

    task_id = _extract_task_id(response_json)
    consumption_id = response_json.get("consumption_id") or "" if isinstance(response_json, dict) else ""
    if task_id:
        return {"type": "async", "task_id": task_id, "consumption_id": consumption_id}
    else:
        return {"type": "sync", "data": response_json}


def poll_task_result(api_key, task_id, session_id=None, model=None, consumption_id=""):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _async_poll_task(api_key, task_id, session_id, model, consumption_id)).result()
    else:
        return asyncio.run(_async_poll_task(api_key, task_id, session_id, model, consumption_id))


async def _async_poll_task(api_key, task_id, session_id=None, model=None, consumption_id=""):
    timeout = 180
    interval = 2
    poll_url = f"{DIRECT_API_BASE}/api/models/tasks"
    headers = synvow_auth.make_api_headers(api_key)
    poll_body = {"task_id": task_id}
    if model:
        poll_body["model"] = model
    if consumption_id:
        poll_body["consumption_id"] = consumption_id

    poll_count = 0
    start_time = time.time()
    short_id = task_id[:8]

    async with aiohttp.ClientSession() as session:
        while True:
            if session_id and session_id in pending_batch_sessions:
                if pending_batch_sessions[session_id].get("cancelled", False):
                    print(f"[{short_id}] Cancelled", flush=True)
                    return None
            poll_count += 1
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"[{short_id}] Timeout ({timeout}s)", flush=True)
                return None

            response_json = None
            for attempt in range(3):
                try:
                    async with session.post(poll_url, headers=headers, json=poll_body,
                                            ssl=False, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 401:
                            raise RuntimeError("Auth expired, please login again")
                        response_json = await resp.json()
                        break
                except RuntimeError:
                    raise
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(1)

            if response_json is None:
                await asyncio.sleep(interval)
                continue

            data = response_json.get("data", response_json)
            status = data.get("status", "")

            if status == "SUCCESS":
                print(f"✅ [{short_id}] {poll_count}次 {elapsed:.1f}s SUCCESS", flush=True)
                return data
            elif status == "FAILURE":
                reason = data.get("fail_reason", "Unknown")
                print(f"❌ [{short_id}] {poll_count}次 {elapsed:.1f}s FAILURE ({reason})", flush=True)
                return None
            else:
                print(f"⏳ [{short_id}] {poll_count}次 {elapsed:.1f}s {status}", flush=True)

            await asyncio.sleep(interval)


def _download_single_image(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            res = requests.get(url, timeout=120, verify=False)
            if res.status_code == 200:
                return Image.open(io.BytesIO(res.content)).convert("RGB")
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
    return None


def download_image_from_result(result_data, target_w=None, target_h=None):
    inner_data = result_data.get("data", {})
    if isinstance(inner_data, dict):
        source_data = inner_data.get("sourceData", {})
        if isinstance(source_data, dict) and "data" in source_data:
            image_list = source_data.get("data", [])
        else:
            image_list = inner_data.get("data", [])
    else:
        image_list = []
    if not isinstance(image_list, list):
        image_list = []
    urls = [item.get("url", "") for item in image_list if isinstance(item, dict) and item.get("url")]
    if not urls:
        raise Exception("No image URLs in result")

    image_objects = []
    with ThreadPoolExecutor(max_workers=max(len(urls), 1)) as executor:
        futures = [executor.submit(_download_single_image, url) for url in urls]
        for f in futures:
            r = f.result()
            if r:
                image_objects.append(r)
    if not image_objects:
        raise Exception("No images downloaded")

    final_tensors = []
    base_w, base_h = target_w, target_h
    for i, img in enumerate(image_objects):
        if i == 0 and not (target_w and target_h):
            base_w, base_h = img.size
        elif base_w and base_h:
            img = img.resize((base_w, base_h), Image.LANCZOS)
        final_tensors.append(torch.from_numpy(np.array(img).astype(np.float32) / 255.0))
    return torch.stack(final_tensors)


def _create_error_result(error_message, original_image=None):
    print(f"Node error: {error_message}")
    image_out = original_image if original_image is not None else torch.zeros((1, 1, 1, 3), dtype=torch.float32)
    return {"ui": {"string": [error_message]}, "result": (image_out, f"Failed: {error_message}")}


def _resolve_model(mode, has_images=False):
    if has_images:
        return MODE_I2I_MAP.get(mode, MODE_I2I_MAP["默认"])
    return MODE_T2I_MAP.get(mode, MODE_T2I_MAP["默认"])


def _run_generate(api_key, model, prompt, images=None, aspect_ratio="1:1", image_size="2K", seed=0, session_id=None):
    submit_result = submit_image_task(api_key, model, prompt, images=images,
                                      aspect_ratio=aspect_ratio, image_size=image_size, seed=seed)
    w, h = calc_size_from_ratio(aspect_ratio, image_size)
    if submit_result["type"] == "async":
        result_data = poll_task_result(api_key, submit_result["task_id"],
                                       session_id=session_id, model=model)
        if result_data is None:
            raise Exception("Task polling failed or timed out")
        return download_image_from_result(result_data, target_w=w, target_h=h)
    else:
        return download_image_from_result(submit_result["data"], target_w=w, target_h=h)


# ---------------------------------------------------------------------------
# NanoBanana Pro 节点
# ---------------------------------------------------------------------------

class SynVowNanoBanana:
    """统一图像生成节点：传图=图生图，不传图=文生图，支持多张并发出图"""
    FUNCTION = "execute"
    CATEGORY = "\U0001f4abSynVow_api"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模式": (MODE_OPTIONS, {"default": "默认"}),
                "prompt": ("STRING", {"multiline": True, "default": "a cute cat napping in sunlight"}),
                "aspect_ratio": (["auto"] + list(PRO_ASPECT_RATIOS.keys()), {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
                "batch_count": ("INT", {"default": 1, "min": 1, "max": 99}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
                "image_10": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "status")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def execute(self, prompt, aspect_ratio="1:1", image_size="2K", batch_count=1, seed=0, **kwargs):
        mode = kwargs.get("模式", "默认")
        images_in = []
        first_image_tensor = None
        for i in range(1, 11):
            img = kwargs.get(f"image_{i}")
            if img is not None:
                if first_image_tensor is None:
                    first_image_tensor = img
                images_in.append(tensor_to_pil_image(img))

        model = _resolve_model(mode, has_images=bool(images_in))
        tag = "I2I" if images_in else "T2I"
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return _create_error_result(str(e), original_image=first_image_tensor)

        if images_in and aspect_ratio == "auto":
            aspect_ratio = find_closest_aspect_ratio(images_in[0].width, images_in[0].height)
        elif aspect_ratio == "auto":
            aspect_ratio = "1:1"

        if batch_count == 1:
            try:
                image_out = _run_generate(api_key, model, prompt,
                                          images=images_in if images_in else None,
                                          aspect_ratio=aspect_ratio, image_size=image_size, seed=seed)
                status = f"SynVow {tag} | {model} | success"
                return {"ui": {"string": [status]}, "result": (image_out, status)}
            except RuntimeError as e:
                return _create_error_result(str(e), original_image=first_image_tensor)
            except Exception as e:
                return _create_error_result(f"{tag} failed: {e}", original_image=first_image_tensor)

        def _run_single(idx):
            s = seed + idx if seed > 0 else 0
            try:
                tensor = _run_generate(api_key, model, prompt,
                                       images=images_in if images_in else None,
                                       aspect_ratio=aspect_ratio, image_size=image_size, seed=s)
                return idx, tensor, None
            except RuntimeError:
                raise
            except Exception as e:
                return idx, None, f"Task {idx+1}: {e}"

        results = [None] * batch_count
        errors = []
        try:
            with ThreadPoolExecutor(max_workers=batch_count) as pool:
                futures = {pool.submit(_run_single, i): i for i in range(batch_count)}
                for f in as_completed(futures):
                    try:
                        idx, tensor, err = f.result()
                        if err:
                            errors.append(err)
                        else:
                            results[idx] = tensor
                    except RuntimeError:
                        raise
                    except Exception as e:
                        errors.append(str(e))
        except RuntimeError as e:
            return _create_error_result(str(e), original_image=first_image_tensor)

        all_tensors = [t for t in results if t is not None]
        if not all_tensors:
            return _create_error_result(f"All failed: {'; '.join(errors)}", original_image=first_image_tensor)
        image_out = torch.cat(all_tensors, dim=0)
        status = f"SynVow {tag} | {len(all_tensors)}/{batch_count}"
        if errors:
            status += f" | errors: {'; '.join(errors)}"
        return {"ui": {"string": [status]}, "result": (image_out, status)}


# ---------------------------------------------------------------------------
# Nano2 节点
# ---------------------------------------------------------------------------

NANO2_T2I_MAP = {"默认": "Nano2-默认-文生图", "优质": "Nano2-优质-文生图"}
NANO2_I2I_MAP = {"默认": "Nano2-默认", "优质": "Nano2-优质"}


def _resolve_nano2_model(mode, has_images=False):
    if has_images:
        return NANO2_I2I_MAP.get(mode, NANO2_I2I_MAP["默认"])
    return NANO2_T2I_MAP.get(mode, NANO2_T2I_MAP["默认"])


class SynVowNano2:
    """Nano2 图像生成节点：传图=图生图，不传图=文生图，支持多张并发出图"""
    FUNCTION = "execute"
    CATEGORY = "\U0001f4abSynVow_api"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模式": (MODE_OPTIONS, {"default": "默认"}),
                "prompt": ("STRING", {"multiline": True, "default": "a cute cat napping in sunlight"}),
                "aspect_ratio": (["auto"] + list(ASPECT_RATIOS.keys()), {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
                "batch_count": ("INT", {"default": 1, "min": 1, "max": 99}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
                "image_10": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "status")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def execute(self, prompt, aspect_ratio="1:1", image_size="2K", batch_count=1, seed=0, **kwargs):
        mode = kwargs.get("模式", "默认")
        images_in = []
        first_image_tensor = None
        for i in range(1, 11):
            img = kwargs.get(f"image_{i}")
            if img is not None:
                if first_image_tensor is None:
                    first_image_tensor = img
                images_in.append(tensor_to_pil_image(img))

        model = _resolve_nano2_model(mode, has_images=bool(images_in))
        tag = "I2I" if images_in else "T2I"
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return _create_error_result(str(e), original_image=first_image_tensor)

        if images_in and aspect_ratio == "auto":
            aspect_ratio = find_closest_aspect_ratio(images_in[0].width, images_in[0].height)
        elif aspect_ratio == "auto":
            aspect_ratio = "1:1"

        if batch_count == 1:
            try:
                image_out = _run_generate(api_key, model, prompt,
                                          images=images_in if images_in else None,
                                          aspect_ratio=aspect_ratio, image_size=image_size, seed=seed)
                status = f"SynVow Nano2 {tag} | {model} | success"
                return {"ui": {"string": [status]}, "result": (image_out, status)}
            except RuntimeError as e:
                return _create_error_result(str(e), original_image=first_image_tensor)
            except Exception as e:
                return _create_error_result(f"Nano2 {tag} failed: {e}", original_image=first_image_tensor)

        def _run_single(idx):
            s = seed + idx if seed > 0 else 0
            try:
                tensor = _run_generate(api_key, model, prompt,
                                       images=images_in if images_in else None,
                                       aspect_ratio=aspect_ratio, image_size=image_size, seed=s)
                return idx, tensor, None
            except RuntimeError:
                raise
            except Exception as e:
                return idx, None, f"Task {idx+1}: {e}"

        results = [None] * batch_count
        errors = []
        try:
            with ThreadPoolExecutor(max_workers=batch_count) as pool:
                futures = {pool.submit(_run_single, i): i for i in range(batch_count)}
                for f in as_completed(futures):
                    try:
                        idx, tensor, err = f.result()
                        if err:
                            errors.append(err)
                        else:
                            results[idx] = tensor
                    except RuntimeError:
                        raise
                    except Exception as e:
                        errors.append(str(e))
        except RuntimeError as e:
            return _create_error_result(str(e), original_image=first_image_tensor)

        all_tensors = [t for t in results if t is not None]
        if not all_tensors:
            return _create_error_result(f"All failed: {'; '.join(errors)}", original_image=first_image_tensor)
        image_out = torch.cat(all_tensors, dim=0)
        status = f"SynVow Nano2 {tag} | {len(all_tensors)}/{batch_count}"
        if errors:
            status += f" | errors: {'; '.join(errors)}"
        return {"ui": {"string": [status]}, "result": (image_out, status)}


# ---------------------------------------------------------------------------
# NanoBanana Pro TI批量节点
# ---------------------------------------------------------------------------

class SynVowNanaBanana_TIBatch:
    pass
SynVowNanaBanana_TIBatch = None

class SynVowNanoBanana_TIBatch:
    """NanoBanana Pro 图生图批量节点：多组图像+多条提示词并发处理"""
    FUNCTION = "process_batch"
    CATEGORY = "\U0001f4abSynVow_api"
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "模式": (MODE_OPTIONS, {"default": "默认"}),
                "aspect_ratio": (["auto"] + list(PRO_ASPECT_RATIOS.keys()), {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
                "prompt_order": (["sequential", "reverse", "random"], {"default": "sequential"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "images_list2": ("IMAGE",), "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",), "images_list5": ("IMAGE",),
                "images_list6": ("IMAGE",), "images_list7": ("IMAGE",),
                "images_list8": ("IMAGE",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("batch_images", "batch_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def _process_single(self, pil_images, prompt, api_key, model, aspect_ratio, image_size, seed, session_id=None):
        import json as _json
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = submit_image_task(api_key, model, prompt, images=pil_images,
                                           aspect_ratio=aspect_ratio, image_size=image_size, seed=seed)
                w, h = calc_size_from_ratio(aspect_ratio, image_size)
                if result["type"] == "async":
                    result_data = poll_task_result(api_key, result["task_id"], session_id=session_id, model=model, consumption_id=result.get("consumption_id", ""))
                    if result_data is None:
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return {"success": False, "error": "polling timeout"}
                    return {"success": True, "images": download_image_from_result(result_data, w, h)}
                else:
                    return {"success": True, "images": download_image_from_result(result["data"], w, h)}
            except RuntimeError:
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"success": False, "error": str(e)}

    def process_batch(self, prompts_list, images_list1, 模式, aspect_ratio, image_size,
                      prompt_order, seed, images_list2=None, images_list3=None,
                      images_list4=None, images_list5=None, images_list6=None,
                      images_list7=None, images_list8=None, unique_id=None):
        import json, random as _random
        # 解包 INPUT_IS_LIST 标量
        mode = 模式[0] if isinstance(模式, list) else 模式
        aspect_ratio = aspect_ratio[0] if isinstance(aspect_ratio, list) else aspect_ratio
        image_size = image_size[0] if isinstance(image_size, list) else image_size
        prompt_order = prompt_order[0] if isinstance(prompt_order, list) else prompt_order
        seed = seed[0] if isinstance(seed, list) else seed
        if isinstance(unique_id, list):
            unique_id = unique_id[0] if unique_id else None

        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            w, h = calc_size_from_ratio(aspect_ratio, image_size)
            black = _create_black_image_tensor(w, h)
            return (black, json.dumps({"error": str(e)}, ensure_ascii=False))

        model = _resolve_model(mode, has_images=True)
        session_id = create_session(unique_id, "Pro_TIBatch")
        if prompts_list is None:
            prompts_list = [""]
        prompts = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        prompts_count = len(prompts)

        all_lists = [images_list1] + [lst or [] for lst in [images_list2, images_list3, images_list4,
                                                              images_list5, images_list6, images_list7, images_list8]]
        images_max_len = max((len(lst) for lst in all_lists), default=0)
        batch_size = max(images_max_len, prompts_count)

        if prompt_order == "reverse":
            prompts = prompts[::-1]
        assigned_prompts = [
            _random.choice(prompts) if prompt_order == "random" else prompts[i % prompts_count]
            for i in range(batch_size)
        ]

        # 处理 auto aspect_ratio
        if aspect_ratio == "auto":
            first_imgs = [lst for lst in all_lists if len(lst) > 0]
            if first_imgs:
                pil0 = tensor_to_pil_image(first_imgs[0][0])
                aspect_ratio = find_closest_aspect_ratio(pil0.width, pil0.height)
            else:
                aspect_ratio = "1:1"

        send_polling_status(unique_id, session_id, "polling", batch_size)

        w, h = calc_size_from_ratio(aspect_ratio, image_size)
        shared_pil_cache = {li: tensor_to_pil_image(lst[0]) for li, lst in enumerate(all_lists) if len(lst) == 1}
        results = [None] * batch_size

        try:
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = {}
                for i in range(batch_size):
                    combined = []
                    for li, lst in enumerate(all_lists):
                        if not lst:
                            continue
                        if li in shared_pil_cache:
                            combined.append(shared_pil_cache[li])
                        elif i < len(lst):
                            pil = tensor_to_pil_image(lst[i])
                            if pil:
                                combined.append(pil)
                    futures[executor.submit(self._process_single, combined, assigned_prompts[i],
                                            api_key, model, aspect_ratio, image_size, seed, session_id)] = i
                for f in as_completed(futures):
                    idx = futures[f]
                    try:
                        results[idx] = f.result()
                    except RuntimeError:
                        raise
                    except Exception as e:
                        results[idx] = {"success": False, "error": str(e)}
        except RuntimeError as e:
            send_polling_status(unique_id, session_id, "idle")
            cleanup_session(session_id)
            black = _create_black_image_tensor(w, h)
            return (black, json.dumps({"error": str(e)}, ensure_ascii=False))
        finally:
            send_polling_status(unique_id, session_id, "idle")
            cleanup_session(session_id)

        all_images, ok = [], 0
        for r in results:
            if r and r["success"]:
                all_images.append(r["images"])
                ok += 1
            else:
                all_images.append(_create_black_image_tensor(w, h))

        batch_info = json.dumps({"total": batch_size, "successful": ok, "failed": batch_size - ok}, ensure_ascii=False)
        return (torch.cat(all_images, dim=0), batch_info)


# ---------------------------------------------------------------------------
# Nano2 TI批量节点
# ---------------------------------------------------------------------------

class SynVowNano2_TIBatch:
    """Nano2 图生图批量节点：多组图像+多条提示词并发处理"""
    FUNCTION = "process_batch"
    CATEGORY = "\U0001f4abSynVow_api"
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "模式": (MODE_OPTIONS, {"default": "默认"}),
                "aspect_ratio": (["auto"] + list(ASPECT_RATIOS.keys()), {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
                "prompt_order": (["sequential", "reverse", "random"], {"default": "sequential"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "images_list2": ("IMAGE",), "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",), "images_list5": ("IMAGE",),
                "images_list6": ("IMAGE",), "images_list7": ("IMAGE",),
                "images_list8": ("IMAGE",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("batch_images", "batch_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def _process_single(self, pil_images, prompt, api_key, model, aspect_ratio, image_size, seed, session_id=None):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = submit_image_task(api_key, model, prompt, images=pil_images,
                                           aspect_ratio=aspect_ratio, image_size=image_size, seed=seed)
                w, h = calc_size_from_ratio(aspect_ratio, image_size)
                if result["type"] == "async":
                    result_data = poll_task_result(api_key, result["task_id"], session_id=session_id, model=model, consumption_id=result.get("consumption_id", ""))
                    if result_data is None:
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return {"success": False, "error": "polling timeout"}
                    return {"success": True, "images": download_image_from_result(result_data, w, h)}
                else:
                    return {"success": True, "images": download_image_from_result(result["data"], w, h)}
            except RuntimeError:
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"success": False, "error": str(e)}

    def process_batch(self, prompts_list, images_list1, 模式, aspect_ratio, image_size,
                      prompt_order, seed, images_list2=None, images_list3=None,
                      images_list4=None, images_list5=None, images_list6=None,
                      images_list7=None, images_list8=None, unique_id=None):
        import json, random as _random
        mode = 模式[0] if isinstance(模式, list) else 模式
        aspect_ratio = aspect_ratio[0] if isinstance(aspect_ratio, list) else aspect_ratio
        image_size = image_size[0] if isinstance(image_size, list) else image_size
        prompt_order = prompt_order[0] if isinstance(prompt_order, list) else prompt_order
        seed = seed[0] if isinstance(seed, list) else seed
        if isinstance(unique_id, list):
            unique_id = unique_id[0] if unique_id else None

        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            w, h = calc_size_from_ratio(aspect_ratio, image_size)
            black = _create_black_image_tensor(w, h)
            return (black, json.dumps({"error": str(e)}, ensure_ascii=False))

        model = _resolve_nano2_model(mode, has_images=True)
        session_id = create_session(unique_id, "Nano2_TIBatch")
        prompts = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        prompts_count = len(prompts)

        all_lists = [images_list1] + [lst or [] for lst in [images_list2, images_list3, images_list4,
                                                              images_list5, images_list6, images_list7, images_list8]]
        images_max_len = max((len(lst) for lst in all_lists), default=0)
        batch_size = max(images_max_len, prompts_count)

        if prompt_order == "reverse":
            prompts = prompts[::-1]
        assigned_prompts = [
            _random.choice(prompts) if prompt_order == "random" else prompts[i % prompts_count]
            for i in range(batch_size)
        ]

        if aspect_ratio == "auto":
            first_imgs = [lst for lst in all_lists if len(lst) > 0]
            if first_imgs:
                pil0 = tensor_to_pil_image(first_imgs[0][0])
                aspect_ratio = find_closest_aspect_ratio(pil0.width, pil0.height)
            else:
                aspect_ratio = "1:1"

        send_polling_status(unique_id, session_id, "polling", batch_size)

        w, h = calc_size_from_ratio(aspect_ratio, image_size)
        shared_pil_cache = {li: tensor_to_pil_image(lst[0]) for li, lst in enumerate(all_lists) if len(lst) == 1}
        results = [None] * batch_size

        try:
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = {}
                for i in range(batch_size):
                    combined = []
                    for li, lst in enumerate(all_lists):
                        if not lst:
                            continue
                        if li in shared_pil_cache:
                            combined.append(shared_pil_cache[li])
                        elif i < len(lst):
                            pil = tensor_to_pil_image(lst[i])
                            if pil:
                                combined.append(pil)
                    futures[executor.submit(self._process_single, combined, assigned_prompts[i],
                                            api_key, model, aspect_ratio, image_size, seed, session_id)] = i
                for f in as_completed(futures):
                    idx = futures[f]
                    try:
                        results[idx] = f.result()
                    except RuntimeError:
                        raise
                    except Exception as e:
                        results[idx] = {"success": False, "error": str(e)}
        except RuntimeError as e:
            send_polling_status(unique_id, session_id, "idle")
            cleanup_session(session_id)
            black = _create_black_image_tensor(w, h)
            return (black, json.dumps({"error": str(e)}, ensure_ascii=False))
        finally:
            send_polling_status(unique_id, session_id, "idle")
            cleanup_session(session_id)

        all_images, ok = [], 0
        for r in results:
            if r and r["success"]:
                all_images.append(r["images"])
                ok += 1
            else:
                all_images.append(_create_black_image_tensor(w, h))

        batch_info = json.dumps({"total": batch_size, "successful": ok, "failed": batch_size - ok}, ensure_ascii=False)
        return (torch.cat(all_images, dim=0), batch_info)


# ---------------------------------------------------------------------------
# 黑图辅助（批量节点用）
# ---------------------------------------------------------------------------

def _create_black_image_tensor(w, h):
    arr = np.zeros((1, h, w, 3), dtype=np.float32)
    return torch.from_numpy(arr)


NODE_CLASS_MAPPINGS = {
    "SynVowNanoBanana": SynVowNanoBanana,
    "SynVowNanoBanana_TIBatch": SynVowNanoBanana_TIBatch,
    "SynVowNano2": SynVowNano2,
    "SynVowNano2_TIBatch": SynVowNano2_TIBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowNanoBanana": "SynVow NanoBanana Pro图像生成",
    "SynVowNanoBanana_TIBatch": "SynVow NanoBanana Pro 批量出图",
    "SynVowNano2": "SynVow Nano2 图像生成",
    "SynVowNano2_TIBatch": "SynVow Nano2 批量出图",
}
