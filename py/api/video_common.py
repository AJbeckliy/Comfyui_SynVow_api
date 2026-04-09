"""
视频节点公共函数 — sora2 / veo3 共享
"""
import requests
import json
import time
import os
import io
import asyncio
import numpy as np
import aiohttp
from PIL import Image
import folder_paths
from . import synvow_auth

DIRECT_API_BASE = "https://service.synvow.com/api/v1"


def tensor_to_jpeg_bytes(image_tensor):
    """ComfyUI IMAGE tensor → JPEG bytes（不含 base64 编码）"""
    if image_tensor is None:
        return None
    if len(image_tensor.shape) > 3:
        image_tensor = image_tensor[0]
    arr = (255.0 * image_tensor.cpu().numpy()).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def parse_task_id(response_json):
    """从多种响应格式中提取 task_id"""
    outer = response_json if isinstance(response_json, dict) else {}
    task_id = (
        outer.get("task_id")
        or (outer.get("data") or {}).get("task_id")
        or ((outer.get("data") or {}).get("data") or {}).get("task_id")
    )
    if not task_id:
        raise Exception(f"响应中无 task_id: {response_json}")
    return task_id


def poll_video_result(api_key, model, task_id, timeout=300, interval=5, tag="Video"):
    """通用视频任务轮询（异步，不阻塞事件循环）"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 已在事件循环中（ComfyUI 主线程），用线程执行异步轮询
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _async_poll_video(api_key, model, task_id, timeout, interval, tag)).result()
    else:
        return asyncio.run(_async_poll_video(api_key, model, task_id, timeout, interval, tag))


async def _async_poll_video(api_key, model, task_id, timeout=300, interval=5, tag="Video"):
    """异步视频轮询实现"""
    url = f"{DIRECT_API_BASE}/api/models/tasks"
    headers = synvow_auth.make_api_headers(api_key)
    start = time.time()
    count = 0

    async with aiohttp.ClientSession() as session:
        while True:
            count += 1
            if time.time() - start > timeout:
                raise Exception(f"任务 {task_id} 超时 ({timeout}秒)")
            try:
                async with session.post(url, headers=headers,
                                        json={"model": model, "task_id": task_id},
                                        ssl=False, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    data = await resp.json()
                    inner = data if isinstance(data, dict) else {}
                    # 首次打印完整响应便于调试
                    raw = inner.get("status") or inner.get("task_status") or ""
                    status = raw.upper()
                    progress = inner.get("progress", "")

                    if status in ("SUCCESS", "SUCCEED", "COMPLETED", "DONE", "FINISH", "FINISHED"):
                        print(f"✅ [{tag}][{task_id[:8]}] 轮询 {count} 次: {raw}")
                        return inner
                    elif status in ("FAILURE", "FAILED", "ERROR"):
                        reason = inner.get("fail_reason") or inner.get("message") or "Unknown"
                        raise Exception(f"任务失败: {reason}")
                    else:
                        print(f"⏳ [{tag}][{task_id[:8]}] 轮询 {count}: {raw or '(无状态)'} {progress}")
            except Exception as e:
                if "任务失败" in str(e) or "超时" in str(e):
                    raise
                print(f"⚠️ [{tag}] 轮询异常: {e}")
            await asyncio.sleep(interval)


def extract_video_url(result_data):
    """从轮询结果中提取视频 URL"""
    if isinstance(result_data, dict):
        # 优先从 data.output 取（sora2 结构）
        nested = result_data.get("data")
        if isinstance(nested, dict) and nested.get("output"):
            return nested["output"]
        # 再从顶层取
        output = result_data.get("output")
        if output:
            return output
    raise Exception(f"响应中无视频 URL: {result_data}")


def download_video(video_url, task_id, save_path="", prefix="video", max_retries=3, filename=""):
    """下载视频到本地"""
    output_dir = save_path.strip() if save_path and save_path.strip() else ""
    if not output_dir:
        try:
            output_dir = folder_paths.get_output_directory()
        except Exception:
            output_dir = ""
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    if filename and filename.strip():
        fname = filename.strip()
        if not fname.lower().endswith(".mp4"):
            fname += ".mp4"
    else:
        fname = f"{prefix}_{task_id[:8].replace(':', '_')}.mp4"

    # 同名文件自动加 (1)(2)... 后缀，不覆盖
    base, ext = os.path.splitext(fname)
    candidate = fname
    counter = 1
    while os.path.exists(os.path.join(output_dir, candidate)):
        candidate = f"{base}({counter}){ext}"
        counter += 1
    fname = candidate
    video_path = os.path.join(output_dir, fname)
    for attempt in range(max_retries):
        try:
            res = requests.get(video_url, verify=False, timeout=120, stream=True)
            if res.status_code == 200:
                with open(video_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                size = os.path.getsize(video_path)
                return video_path
        except Exception as e:
            print(f"[{prefix}] 下载失败 ({attempt+1}/{max_retries}): {e}")
        if attempt < max_retries - 1:
            time.sleep(3)
    return None


def upload_images(api_key, image_bytes_list):
    """上传图片到 synvow，返回 URL 列表"""
    url = f"{DIRECT_API_BASE}/api/upload/images"
    headers = {"X-API-Key": api_key}
    files = [("files", (f"image_{i}.jpg", b, "image/jpeg")) for i, b in enumerate(image_bytes_list)]
    res = requests.post(url, headers=headers, files=files, verify=False, timeout=60)
    data = res.json()
    if res.status_code != 200 or data.get("code") != 200:
        raise Exception(f"图片上传失败: {data}")
    urls = data.get("data", {}).get("urls", [])
    if not urls:
        raise Exception(f"图片上传返回无 URL: {data}")
    return urls
