# -*- coding: utf-8 -*-
"""SynVow 视频解析 30+：请求 jiexi30+，从 data.video_url 取视频。"""
import glob
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from . import synvow_auth
from .media_common import download_video, is_changed_by_inputs

_SUBMIT_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/video/generate"
_MODEL = "jiexi30+"
_APP_ID = "118314"
_MAX_IN_WINDOW = 5
_WINDOW_SEC = 2
_PLACEHOLDER = "请输入视频链接(支持DY、SPH电脑/手机端、BZ、KS、XHS、PPX、某梦APP、某宝APP、WB、PDD、JRTT、HS、XG、WS、QS、MP等30+平台)"


def _collect_urls(text):
    found = re.findall(r"https?://\S+", text or "", re.I)
    urls = [re.sub(r"[)\]}>，。、]+$", "", u) for u in found]
    if urls:
        return urls
    trimmed = (text or "").strip()
    return [trimmed] if re.match(r"^https?://", trimmed, re.I) else []


class _RateGate:
    def __init__(self):
        self._lock = threading.Lock()
        self._started = []

    def wait(self):
        while True:
            with self._lock:
                now = time.time()
                self._started = [t for t in self._started if now - t < _WINDOW_SEC]
                if len(self._started) < _MAX_IN_WINDOW:
                    self._started.append(now)
                    return
            time.sleep(0.05)


def _submit(api_key, url):
    res = requests.post(
        _SUBMIT_URL,
        headers=synvow_auth.make_api_headers(api_key),
        json={"model": _MODEL, "url": url, "appId": _APP_ID},
        timeout=120,
        verify=False,
    )
    try:
        data = res.json()
    except Exception:
        data = {}
    if res.status_code != 200:
        msg = data.get("message") or data.get("msg") or res.text[:200]
        raise Exception(f"HTTP {res.status_code}: {msg}")
    payload = data.get("data") if isinstance(data.get("data"), dict) else {}
    video_url = str(payload.get("video_url") or "").strip()
    if not video_url:
        raise Exception(f"响应中无视频 URL: {str(data)[:200]}")
    return video_url


def _next_filename(out_dir, index):
    existing = glob.glob(os.path.join(out_dir, "jiexi30_*.mp4")) if out_dir else []
    return f"jiexi30_{len(existing) + index + 1:05d}.mp4"


class SynVowVideoParse30:
    FUNCTION = "parse"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "[荐]视频解析30+"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url_text": ("STRING", {"multiline": True, "default": "", "placeholder": _PLACEHOLDER}),
                "save_path": ("STRING", {"multiline": False, "default": "", "placeholder": "留空则保存至 output 目录"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_url", "video_path", "status")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def parse(self, url_text, save_path=""):
        urls = _collect_urls(url_text)
        if not urls:
            raise ValueError("需要填写视频链接")
        api_key = synvow_auth.read_api_key()
        out_dir = save_path.strip() if save_path and save_path.strip() else ""
        if not out_dir:
            try:
                import folder_paths as _fp
                out_dir = _fp.get_output_directory()
            except Exception:
                out_dir = ""
        gate = _RateGate()
        results = [None] * len(urls)

        def one(index, url):
            gate.wait()
            remote = _submit(api_key, url)
            path = download_video(
                remote, f"jiexi30_{index}", save_path, prefix="jiexi30",
                filename=_next_filename(out_dir, index),
            ) or ""
            return remote, path

        try:
            workers = min(_MAX_IN_WINDOW, len(urls))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(one, i, url): i for i, url in enumerate(urls)}
                for future in as_completed(futures):
                    index = futures[future]
                    try:
                        results[index] = future.result()
                    except Exception as e:
                        raise Exception(f"第 {index + 1} 条失败: {e}") from e
            video_urls = "\n".join(item[0] for item in results)
            video_paths = "\n".join(item[1] for item in results)
            return (video_urls, video_paths, f"已完成 {_MODEL} x{len(urls)}")
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowVideoParse30": SynVowVideoParse30,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowVideoParse30": "[荐]视频解析30+",
}
