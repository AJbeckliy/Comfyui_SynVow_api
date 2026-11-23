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
_MAX_IN_WINDOW = 5
_WINDOW_SEC = 2
_PLACEHOLDER = "请输入视频链接(支持DY、SPH电脑/手机端、BZ、KS、XHS、PPX、某梦APP、某宝APP、WB、PDD、JRTT、HS、XG、WS、QS、MP等30+平台)"


def _collect_urls(text):
    return [re.sub(r"[)\]}>，。、]+$", "", u) for u in re.findall(r"https?://\S+", text or "", re.I)]


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
        json={"model": _MODEL, "url": url},
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


def _filename(start, index):
    return f"jiexi30_{start + index + 1:05d}.mp4"


def _source_urls(url_text):
    parts = url_text if isinstance(url_text, list) else [url_text]
    urls = []
    for part in parts:
        urls.extend(_collect_urls("" if part is None else str(part)))
    return urls


def _first(value, default=""):
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


class SynVowVideoParse30:
    FUNCTION = "parse"
    CATEGORY = "💫SynVow_api/api/解析"
    DESCRIPTION = "[荐]视频解析30+"
    INPUT_IS_LIST = True

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
    OUTPUT_IS_LIST = (True, True, False)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def parse(self, url_text, save_path=""):
        urls = _source_urls(url_text)
        save_path = str(_first(save_path, "") or "")
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
        start = len(glob.glob(os.path.join(out_dir, "jiexi30_*.mp4"))) if out_dir else 0

        def one(index, url):
            gate.wait()
            remote = _submit(api_key, url)
            path = download_video(
                remote, f"jiexi30_{index}", save_path, prefix="jiexi30",
                filename=_filename(start, index),
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
            return (
                [item[0] for item in results],
                [item[1] for item in results],
                f"已完成 {_MODEL} x{len(urls)}",
            )
        finally:
            synvow_auth.refresh_balance()


class SynVowDyHome:
    FUNCTION = "parse"
    CATEGORY = "💫SynVow_api/api/解析"
    DESCRIPTION = "主页解析"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("works", "status")
    OUTPUT_IS_LIST = (True, False)
    IS_CHANGED = staticmethod(is_changed_by_inputs)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "请输入个人主页链接(只支持dy)",
                }),
                "page": ("INT", {"default": 1, "min": 1, "max": 20}),
            }
        }

    def parse(self, url_text, page=1):
        urls = _collect_urls(url_text)
        if not urls:
            raise ValueError("需要填写主页链接")
        api_key = synvow_auth.read_api_key()
        try:
            page = max(1, min(20, int(page)))
        except (TypeError, ValueError):
            page = 1
        res = requests.post(
            _SUBMIT_URL,
            headers=synvow_auth.make_api_headers(api_key),
            json={"model": "dyshow", "url": urls[0], "page": page},
            timeout=120,
            verify=False,
        )
        try:
            data = res.json()
        except Exception:
            data = {}
        if res.status_code != 200 or (data.get("code") not in (None, 200)):
            msg = data.get("message") or data.get("msg") or res.text[:200]
            raise Exception(f"dyshow: {msg}")
        payload = data.get("data") if isinstance(data.get("data"), dict) else {}
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        links = []
        for item in items:
            if not isinstance(item, dict):
                continue
            link = str(item.get("share_url") or "").strip()
            if link:
                links.append(link)
        synvow_auth.refresh_balance()
        return (links, f"已完成 dyshow 第{page}页 x{len(links)}")


NODE_CLASS_MAPPINGS = {
    "SynVowVideoParse30": SynVowVideoParse30,
    "SynVowDyHome": SynVowDyHome,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowVideoParse30": "[荐]视频解析30+",
    "SynVowDyHome": "主页解析",
}
