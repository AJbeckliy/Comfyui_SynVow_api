import hashlib
import os
import shutil
import subprocess

import folder_paths


def _find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise RuntimeError(
        "未找到 ffmpeg。请安装 ffmpeg 并加入系统 PATH，"
        "或执行 pip install imageio-ffmpeg 后重启 ComfyUI。"
    )


def maybe_crop_media(source_path, start_time, crop_duration):
    crop_duration = float(crop_duration or 0)
    if crop_duration <= 0:
        return source_path

    start_time = max(0.0, float(start_time or 0))
    ext = os.path.splitext(source_path)[1] or ".mp4"
    temp_dir = folder_paths.get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)

    mtime = os.path.getmtime(source_path)
    key_src = f"{source_path}|{start_time:.3f}|{crop_duration:.3f}|{mtime}"
    key = hashlib.sha256(key_src.encode()).hexdigest()[:16]
    out_path = os.path.join(temp_dir, f"synvow_crop_{key}{ext}")

    if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        return out_path

    cmd = [
        _find_ffmpeg(), "-y",
        "-ss", str(start_time),
        "-i", source_path,
        "-t", str(crop_duration),
        "-c", "copy",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"ffmpeg 裁剪失败: {err or proc.returncode}")

    return out_path
