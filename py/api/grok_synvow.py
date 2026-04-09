import json, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from . import synvow_auth
from .video_common import DIRECT_API_BASE, tensor_to_jpeg_bytes, download_video, upload_images

GROK_MODEL = "Grok"


def _submit_task(api_key, prompt, ratio, resolution, duration, image_urls=None):
    headers = synvow_auth.make_api_headers(api_key)
    payload = {"model": GROK_MODEL, "prompt": prompt}
    if ratio: payload["ratio"] = ratio
    if resolution: payload["resolution"] = resolution
    if duration: payload["duration"] = int(duration)
    if image_urls: payload["images"] = image_urls
    res = requests.post(f"{DIRECT_API_BASE}/api/models/video/generate",
                        headers=headers, json=payload, verify=False, timeout=120)
    if res.status_code != 200:
        raise Exception(f"submit failed ({res.status_code}): {res.text[:200]}")
    data = res.json()
    task_id = (data.get("task_id") or (data.get("data") or {}).get("task_id")
               or data.get("id") or (data.get("data") or {}).get("id"))
    if not task_id:
        raise Exception(f"no task_id: {data}")
    consumption_id = data.get("consumption_id") or ""
    return task_id, consumption_id


def _poll_grok(api_key, task_id, timeout=600, interval=5, consumption_id=""):
    url = f"{DIRECT_API_BASE}/api/models/tasks"
    headers = synvow_auth.make_api_headers(api_key)
    start = time.time()
    count = 0
    while True:
        count += 1
        if time.time() - start > timeout:
            raise Exception(f"Grok timeout ({timeout}s)")
        try:
            res = requests.post(url, headers=headers,
                                json={k: v for k, v in {
                                    "model": GROK_MODEL,
                                    "task_id": task_id,
                                    "consumption_id": consumption_id or None,
                                }.items() if v is not None},
                                verify=False, timeout=30)
            if res.status_code in (429, 500, 503):
                time.sleep(10)
                continue
            data = res.json() if res.status_code == 200 else {}
            inner = data if isinstance(data, dict) else {}
            raw = inner.get("status") or inner.get("task_status") or inner.get("state") or ""
            status = str(raw).upper()
            data_inner = inner.get("data") or {}
            video_url = (data_inner.get("output") or inner.get("output")
                         or inner.get("video_url") or inner.get("url") or "")
            print(f"[Grok] poll {count}: status={raw!r}")
            if status in ("SUCCESS", "SUCCEED", "COMPLETED", "DONE", "FINISH", "FINISHED"):
                return inner
            if video_url and status not in ("FAILURE", "FAILED", "ERROR", "NOT_START",
                                            "PENDING", "PROCESSING", "RUNNING", "QUEUED", ""):
                return inner
            if status in ("FAILURE", "FAILED", "ERROR"):
                raise Exception(f"task failed: {inner.get('fail_reason') or 'Unknown'}")
        except Exception as e:
            if "task failed" in str(e) or "timeout" in str(e):
                raise
            print(f"[Grok] poll error: {e}")
        time.sleep(interval)


def _poll_grok_only(api_key, task_id, save_path, filename="", stagger_delay=0):
    if stagger_delay > 0:
        time.sleep(stagger_delay)
    result = _poll_grok(api_key, task_id)
    video_url = ((result.get("data") or {}).get("output")
                 or result.get("output") or result.get("video_url") or "")
    if not video_url:
        raise Exception(f"no video URL: {result}")
    path = download_video(video_url, task_id, save_path, prefix="grok", filename=filename) or ""
    return {"success": True, "video_path": path, "video_url": video_url, "task_id": task_id}


def _grok_batch_filenames(base, count):
    if not base or not base.strip():
        return [""] * count
    base = base.strip()
    if base.lower().endswith(".mp4"):
        base = base[:-4]
    return [base] + [f"{base}({i})" for i in range(1, count)]


class SynVowGrokVideo:
    FUNCTION = "generate_video"
    CATEGORY = "\U0001f4abSynVow_api"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "a beautiful landscape"}),
                "ratio": (["2:3", "3:2", "1:1", "9:16", "16:9"], {"default": "3:2"}),
                "resolution": (["720P", "1080P"], {"default": "720P"}),
                "duration": (["6", "10"], {"default": "6"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def generate_video(self, prompt, ratio, resolution, duration, seed,
                       image_1=None, image_2=None, image_3=None, image_4=None,
                       image_5=None, image_6=None, image_7=None,
                       filename="", save_path=""):
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        try:
            tensors = [t for t in [image_1, image_2, image_3, image_4,
                                   image_5, image_6, image_7] if t is not None]
            img_bytes = [tensor_to_jpeg_bytes(t) for t in tensors]
            image_urls = upload_images(api_key, img_bytes) if img_bytes else None
            task_id, consumption_id = _submit_task(api_key, prompt, ratio, resolution, duration, image_urls)
            result = _poll_grok(api_key, task_id, consumption_id=consumption_id)
            video_url = ((result.get("data") or {}).get("output")
                         or result.get("output") or result.get("video_url") or "")
            if not video_url:
                raise Exception(f"no video URL: {result}")
            path = download_video(video_url, task_id, save_path, prefix="grok", filename=filename) or ""
            info = json.dumps({"status": "SUCCESS", "task_id": task_id,
                               "video_url": video_url, "video_path": path}, ensure_ascii=False)
            import os, shutil, folder_paths as _fp
            gifs = []
            if path and os.path.isfile(path):
                out_dir = _fp.get_output_directory()
                fname = os.path.basename(path)
                preview_path = os.path.join(out_dir, fname)
                if os.path.normpath(path) != os.path.normpath(preview_path):
                    shutil.copy2(path, preview_path)
                gifs.append({"filename": fname, "subfolder": "", "type": "output", "format": "video/mp4"})
            return {"ui": {"gifs": gifs}, "result": (path, video_url, info)}
        except Exception as e:
            print(f"[Grok] Error: {e}")
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


class SynVowGrokVideoBatch:
    FUNCTION = "process_batch"
    CATEGORY = "\U0001f4abSynVow_api"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "ratio": (["2:3", "3:2", "1:1", "9:16", "16:9"], {"default": "3:2"}),
                "resolution": (["720P", "1080P"], {"default": "720P"}),
                "duration": (["6", "10"], {"default": "6"}),
                "批次数量": ("INT", {"default": 3, "min": 1, "max": 10}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_paths", "video_urls", "batch_info")
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, True, False)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def process_batch(self, prompts_list, ratio, resolution, duration, 批次数量,
                      image_1=None, image_2=None, image_3=None, image_4=None,
                      image_5=None, image_6=None, image_7=None,
                      filename=None, save_path=None):
        _u = lambda v, d=None: v[0] if isinstance(v, list) and v else (v if v is not None else d)
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ([""], [""], json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        ratio = _u(ratio, "3:2")
        resolution = _u(resolution, "720P")
        duration = _u(duration, "5")
        max_concurrent = _u(批次数量, 3)
        filename = _u(filename, "")
        save_path = _u(save_path, "")

        # 收集图片并上传（所有批次共用同一组图片）
        image_urls = None
        tensors = [_u(t) for t in [image_1, image_2, image_3, image_4,
                                    image_5, image_6, image_7] if _u(t) is not None]
        if tensors:
            img_bytes = [tensor_to_jpeg_bytes(t) for t in tensors]
            image_urls = upload_images(api_key, img_bytes)

        raw = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        prompts = []
        for item in raw:
            if isinstance(item, list):
                prompts.extend([p for p in item if p and str(p).strip()])
            elif item and str(item).strip():
                prompts.append(str(item).strip())
        if not prompts:
            prompts = [""]
        filenames = _grok_batch_filenames(filename, len(prompts))
        results = [None] * len(prompts)
        task_ids = []
        for i, prompt in enumerate(prompts):
            try:
                task_id, _ = _submit_task(api_key, prompt, ratio, resolution, duration, image_urls)
                task_ids.append((i, task_id, filenames[i]))
                if i < len(prompts) - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"[Grok Batch] task{i} submit failed: {e}")
                results[i] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}
        with ThreadPoolExecutor(max_workers=min(max_concurrent, max(len(task_ids), 1))) as pool:
            futures = {}
            for seq, (i, task_id, fname) in enumerate(task_ids):
                futures[pool.submit(_poll_grok_only, api_key, task_id, save_path, fname, seq * 10)] = i
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    results[idx] = f.result()
                except Exception as e:
                    print(f"[Grok Batch] task{idx} failed: {e}")
                    results[idx] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}
        paths, urls, ok = [], [], 0
        for r in results:
            r = r or {"video_path": "", "video_url": "", "success": False}
            paths.append(r["video_path"])
            urls.append(r["video_url"])
            if r.get("success"): ok += 1
        info = json.dumps({"total": len(prompts), "successful": ok, "failed": len(prompts) - ok}, ensure_ascii=False)
        import os, shutil, folder_paths as _fp
        gifs = []
        out_dir = _fp.get_output_directory()
        for p in paths:
            if p and os.path.isfile(p):
                fname = os.path.basename(p)
                preview_path = os.path.join(out_dir, fname)
                if os.path.normpath(p) != os.path.normpath(preview_path):
                    shutil.copy2(p, preview_path)
                gifs.append({"filename": fname, "subfolder": "", "type": "output", "format": "video/mp4"})
        return {"ui": {"gifs": gifs}, "result": (paths, urls, info)}


NODE_CLASS_MAPPINGS = {
    "SynVowGrokVideo": SynVowGrokVideo,
    "SynVowGrokVideoBatch": SynVowGrokVideoBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGrokVideo": "SynVow Grok 视频生成",
    "SynVowGrokVideoBatch": "SynVow Grok 批量视频生成",
}
