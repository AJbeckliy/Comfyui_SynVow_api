"""
SynVow GPT-Image-2 节点 — 通过 SynVow /api/models/image/edit 接口生成/编辑图片
"""

import base64 as _b64
import concurrent.futures
import io
import random
import time

import comfy.utils

import numpy as np
import requests
import torch
import urllib3
from PIL import Image

from . import synvow_auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


_RATIO_TO_SIZE_1K = {
    "auto":  "auto",
    "1:1":   "1024x1024",
    "16:9":  "1536x1024",
    "9:16":  "1024x1536",
    "4:3":   "1360x1024",
    "3:4":   "1024x1360",
    "5:4":   "1280x1024",
    "4:5":   "1024x1280",
    "3:2":   "1152x768",
    "2:3":   "768x1152",
    "3:1":   "1536x512",
    "1:3":   "512x1536",
    "2:1":   "1280x640",
    "1:2":   "640x1280",
    "21:9":  "1792x768",
    "9:21":  "768x1792",
}

_RATIO_TO_SIZE_2K = {
    "auto":  "auto",
    "1:1":   "2048x2048",
    "16:9":  "2048x1152",
    "9:16":  "1152x2048",
    "4:3":   "2048x1536",
    "3:4":   "1536x2048",
    "5:4":   "2048x1632",
    "4:5":   "1632x2048",
    "3:2":   "2048x1360",
    "2:3":   "1360x2048",
    "3:1":   "2048x688",
    "1:3":   "688x2048",
    "2:1":   "2048x1024",
    "1:2":   "1024x2048",
    "21:9":  "2560x1104",
    "9:21":  "1104x2560",
}

_RATIO_TO_SIZE_4K = {
    "auto":  "auto",
    "1:1":   "2880x2880",
    "16:9":  "3840x2160",
    "9:16":  "2160x3840",
    "4:3":   "3312x2480",
    "3:4":   "2480x3312",
    "5:4":   "3200x2560",
    "4:5":   "2560x3200",
    "3:2":   "3840x2352",
    "2:3":   "2352x3520",
    "3:1":   "3840x1280",
    "1:3":   "1280x3840",
    "2:1":   "3840x1920",
    "1:2":   "1920x3840",
    "21:9":  "3840x1648",
    "9:21":  "1648x3840",
}

_RATIO_MAPS = {"1K": _RATIO_TO_SIZE_1K, "2K": _RATIO_TO_SIZE_2K, "4K": _RATIO_TO_SIZE_4K}


class SynVowGptImage2:
    """通过 SynVow 代理调用 GPT-Image-2，支持文生图和图生图（最多 8 张输入图）"""

    _conversation_history = []
    _last_image_urls = ""

    FUNCTION = "generate"
    CATEGORY = "\U0001f4abSynVow_api"
    OUTPUT_NODE = False
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "direction": (["文生图", "图生图"], {"default": "文生图"}),
                "mode": (["默认", "优质"], {"default": "默认"}),
                "quality": (["auto", "low", "medium", "high"], {"default": "auto"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (list(_RATIO_TO_SIZE_1K.keys()), {"default": "1:1"}),
                "count": ("INT", {"default": 1, "min": 1, "max": 4}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "prompts_list": ("STRING", {"forceInput": True}),
                "images_list": ("IMAGE",),
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "image6": ("IMAGE",),
                "image7": ("IMAGE",),
                "image8": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("images", "response", "image_urls", "chats")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def _format_history(self):
        if not SynVowGptImage2._conversation_history:
            return ""
        out = ""
        for entry in SynVowGptImage2._conversation_history:
            out += f"**User**: {entry['user']}\n\n**AI**: {entry['ai']}\n\n---\n\n"
        return out.strip()

    def _blank_image(self):
        return torch.zeros((1, 1024, 1024, 3), dtype=torch.float32)

    def _submit(self, payload, headers, api_url):
        """提交任务，返回 (task_id, consumption_id)，失败抛异常"""
        def _trunc(v):
            if isinstance(v, str) and len(v) > 40:
                return v[:40] + "..."
            if isinstance(v, list):
                return [_trunc(i) for i in v]
            return v
        _log_payload = {k: _trunc(v) for k, v in payload.items()}
        print(f"[SynVow GPT-Image-2] 提交参数: {_log_payload}")
        res = requests.post(api_url, headers=headers, json=payload,
                            params={"async": "true"}, timeout=60, verify=False)
        res.raise_for_status()
        _d = res.json() if isinstance(res.json(), dict) else {}
        task_id = (
            _d.get("task_id")
            or (_d.get("data") or {}).get("task_id")
            or ((_d.get("data") or {}).get("sourceData") or {}).get("task_id")
        )
        consumption_id = (
            _d.get("consumption_id")
            or (_d.get("data") or {}).get("consumption_id")
            or None
        )
        if not task_id:
            raise RuntimeError(f"响应中无 task_id: {str(_d)[:200]}")
        print(f"[SynVow GPT-Image-2] 提交响应: task_id={task_id[:8]}... consumption_id={consumption_id}")
        return task_id, consumption_id

    def _poll(self, task_id, consumption_id, headers, poll_url, model):
        """轮询单个任务，返回 poll_json 或 None"""
        print(f"[SynVow GPT-Image-2] task_id={task_id[:8]}... 轮询中")
        poll_body = {"task_id": task_id, "model": model}
        if consumption_id is not None:
            poll_body["consumption_id"] = consumption_id

        timeout_total = 900
        interval = 5
        start_time = time.time()
        while True:
            time.sleep(interval)
            elapsed = int(time.time() - start_time)
            if elapsed >= timeout_total:
                print(f"[SynVow GPT-Image-2] ⏰ {task_id[:8]}... 超时 ({elapsed}s)")
                return None
            try:
                poll_res = requests.post(poll_url, headers=headers, json=poll_body, timeout=30, verify=False)
                poll_res.raise_for_status()
                poll_json = poll_res.json()
                data_field = poll_json.get("data", poll_json) if isinstance(poll_json, dict) else poll_json
                status = data_field.get("status", "") if isinstance(data_field, dict) else ""
                print(f"[SynVow GPT-Image-2] {task_id[:8]}... status={status} ({elapsed}s)")
                if status in ("SUCCESS", "success", "completed", "done", "finished"):
                    print(f"[SynVow GPT-Image-2] ✅ {task_id[:8]}... 完成 ({elapsed}s)")
                    return poll_json
                elif status in ("FAILURE", "failed", "error"):
                    msg = data_field.get("fail_reason", "任务失败")
                    print(f"[SynVow GPT-Image-2] ❌ {task_id[:8]}... {msg} ({elapsed}s)")
                    return None
            except Exception as e:
                print(f"[SynVow GPT-Image-2] ⚠️ {task_id[:8]}... 轮询异常 ({elapsed}s): {e}")
                raise Exception(f"轮询请求失败: {e}")

    def _tensor_to_b64(self, img_tensor):
        arr = (img_tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(arr).convert("RGB").save(buf, format="PNG")
        return "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()

    def _build_payload(self, model, prompt, size, quality, seed, is_img2img, img_tensors):
        payload = {"model": model, "prompt": prompt, "size": size}
        if quality and quality != "auto":
            payload["quality"] = quality
        if is_img2img and img_tensors:
            b64_list = [self._tensor_to_b64(t) for t in img_tensors]
            payload["image"] = b64_list[0]
            if len(b64_list) > 1:
                payload["images"] = b64_list[1:]
        return payload

    def generate(self, direction, mode, quality, resolution, aspect_ratio, count, seed,
                 prompt=None, prompts_list=None, images_list=None,
                 image1=None, image2=None, image3=None, image4=None,
                 image5=None, image6=None, image7=None, image8=None):
        # INPUT_IS_LIST=True: 所有参数均为列表，拆包标量参数
        direction = direction[0] if isinstance(direction, list) else direction
        mode = mode[0] if isinstance(mode, list) else mode
        quality = quality[0] if isinstance(quality, list) else quality
        resolution = resolution[0] if isinstance(resolution, list) else resolution
        aspect_ratio = aspect_ratio[0] if isinstance(aspect_ratio, list) else aspect_ratio
        count = count[0] if isinstance(count, list) else count
        seed = seed[0] if isinstance(seed, list) else seed
        image1 = image1[0] if isinstance(image1, list) else image1
        image2 = image2[0] if isinstance(image2, list) else image2
        image3 = image3[0] if isinstance(image3, list) else image3
        image4 = image4[0] if isinstance(image4, list) else image4
        image5 = image5[0] if isinstance(image5, list) else image5
        image6 = image6[0] if isinstance(image6, list) else image6
        image7 = image7[0] if isinstance(image7, list) else image7
        image8 = image8[0] if isinstance(image8, list) else image8
        prompt = prompt[0] if isinstance(prompt, list) else prompt
        # prompts_list/images_list 保持列表形式

        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            msg = str(e)
            print(f"[SynVow GPT-Image-2] {msg}")
            return (self._blank_image(), msg, "", self._format_history())

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        DIRECT_API_BASE = "https://service.synvow.com/api/v1"
        LOCAL_BASE = synvow_auth.get_proxy_base()
        headers = synvow_auth.make_api_headers(api_key)
        model = f"gpt-image-2-{direction}-{mode}"
        is_img2img = direction == "图生图"
        effective_resolution = resolution if mode != "默认" else "1K"
        ratio_map = _RATIO_MAPS.get(effective_resolution, _RATIO_TO_SIZE_1K)
        size = ratio_map.get(aspect_ratio, "auto")
        api_url = f"{LOCAL_BASE}/api/models/image/edit"
        poll_url = f"{DIRECT_API_BASE}/api/models/tasks"

        def _extract_urls(d):
            if isinstance(d, list):
                return [item["url"] for item in d if isinstance(item, dict) and item.get("url")]
            if isinstance(d, dict):
                if "url" in d and d["url"]:
                    return [d["url"]]
                for key in ("data", "sourceData", "images"):
                    if key in d:
                        result = _extract_urls(d[key])
                        if result:
                            return result
            return []

        # ── 准备提示词列表 ──
        # prompts_list 优先（多任务）；否则用 prompt 单条；都没有则空
        if prompts_list is not None:
            prompts = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        elif prompt is not None and str(prompt).strip():
            prompts = [str(prompt).strip()]
        else:
            prompts = [""]

        # ── 准备图片列表 ──
        if images_list is not None:
            if isinstance(images_list, (list, tuple)):
                img_batch = [[t] for t in images_list]
            else:
                img_batch = [[images_list[i:i+1]] for i in range(images_list.shape[0])]
        else:
            single_imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8] if t is not None]
            # single_imgs 是参考图列表，每个任务都用同一组参考图
            img_batch = [single_imgs] * max(len(prompts), 1) if single_imgs else []

        if is_img2img and not img_batch:
            return (self._blank_image(), "图生图模式需要至少一张输入图", "", self._format_history())

        # 每条提示词 × count 展开任务列表
        base_count = max(len(prompts), len(img_batch)) if img_batch else len(prompts)
        tasks = []
        for i in range(base_count):
            p = prompts[i % len(prompts)]
            imgs = img_batch[i % len(img_batch)] if img_batch else []
            for _ in range(count):
                tasks.append((p, imgs))

        total = len(tasks)
        print(f"[SynVow GPT-Image-2] {total} 个任务 (prompts={len(prompts)}, count={count}), model={model}")

        pbar = comfy.utils.ProgressBar(total)

        # 串行提交，每条间隔 1s
        submitted = []
        for i, (p, imgs) in enumerate(tasks):
            payload = self._build_payload(model, p, size, quality, seed, is_img2img, imgs)
            try:
                task_id, consumption_id = self._submit(payload, headers, api_url)
                submitted.append((task_id, consumption_id))
                print(f"[SynVow GPT-Image-2] [{i+1}/{total}] 提交成功 task_id={task_id[:8]}...")
            except Exception as e:
                print(f"[SynVow GPT-Image-2] [{i+1}/{total}] 提交失败: {e}")
                submitted.append(None)
            if i < total - 1:
                time.sleep(1)

        # 并发轮询
        def _poll_one(item):
            if item is None:
                pbar.update(1)
                return None
            task_id, consumption_id = item
            result = self._poll(task_id, consumption_id, headers, poll_url, model)
            pbar.update(1)
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=total) as executor:
            results = list(executor.map(_poll_one, submitted))

        image_urls = []
        for i, r in enumerate(results):
            if r is not None:
                # 对齐 TS 版：先剥 data.data，再回退到整体
                d = r.get("data", r) if isinstance(r, dict) else r
                inner = d.get("data", d) if isinstance(d, dict) else d
                urls = _extract_urls(inner) or _extract_urls(d) or _extract_urls(r)
                print(f"[SynVow GPT-Image-2] task[{i}] 提取到 {len(urls)} 个URL")
                if not urls:
                    print(f"[SynVow GPT-Image-2] task[{i}] 原始响应: {str(r)[:300]}")
                image_urls.extend(urls)
            else:
                print(f"[SynVow GPT-Image-2] task[{i}] 失败，黑图占位")
                image_urls.append(None)

        image_urls_str = "\n".join(u for u in image_urls if u)
        if image_urls_str:
            SynVowGptImage2._last_image_urls = image_urls_str

        technical_response = f"**Model**: {model}\n**Size**: {size}\n**Time**: {timestamp}"
        SynVowGptImage2._conversation_history.append({"user": prompts[0], "ai": technical_response})
        chat_history = self._format_history()

        if image_urls:
            tensors = []
            for img_url in image_urls:
                if img_url is None:
                    tensors.append(self._blank_image())
                    continue
                try:
                    r = requests.get(img_url, timeout=120, verify=False)
                    r.raise_for_status()
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    arr = np.array(img).astype(np.float32) / 255.0
                    tensors.append(torch.from_numpy(arr).unsqueeze(0))
                except Exception as e:
                    print(f"[SynVow GPT-Image-2] 下载图片失败 {img_url}: {e}")
                    tensors.append(self._blank_image())
            if tensors:
                # 统一 resize 到第一张图的尺寸再 cat
                h, w = tensors[0].shape[1], tensors[0].shape[2]
                resized = []
                for t in tensors:
                    if t.shape[1] != h or t.shape[2] != w:
                        pil = Image.fromarray((t[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8))
                        pil = pil.resize((w, h), Image.LANCZOS)
                        t = torch.from_numpy(np.array(pil).astype(np.float32) / 255.0).unsqueeze(0)
                    resized.append(t)
                return (torch.cat(resized, dim=0), technical_response, image_urls_str, chat_history)

        first_input = next((t for t in [image1, image2, image3, image4, image5, image6, image7, image8] if t is not None), None)
        if first_input is not None:
            return (first_input, technical_response, image_urls_str, chat_history)
        return (self._blank_image(), technical_response, image_urls_str, chat_history)


NODE_CLASS_MAPPINGS = {
    "SynVowGptImage2": SynVowGptImage2,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGptImage2": "SynVow GPT-Image-2",
}
