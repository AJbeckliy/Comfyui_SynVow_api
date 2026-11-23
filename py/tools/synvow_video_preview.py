import os
import shutil
import folder_paths


def _paths(video_path):
    raw = video_path if isinstance(video_path, list) else [video_path]
    return [str(item).strip() for item in raw if str(item or "").strip()]


class SynVowVideoPreview:
    FUNCTION = "preview"
    CATEGORY = "💫SynVow_api/Utils"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    RETURN_TYPES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {"forceInput": True}),
            }
        }

    def preview(self, video_path=None):
        paths = _paths(video_path)
        if not paths:
            print("[VideoPreview] video_path 为空")
            return {"ui": {"gifs": []}}
        gifs = []
        out_dir = folder_paths.get_output_directory()
        for p in paths:
            if not os.path.isfile(p):
                print(f"[VideoPreview] 文件不存在: {p!r}")
                continue
            fname = os.path.basename(p)
            preview_path = os.path.join(out_dir, fname)
            if os.path.normpath(p) != os.path.normpath(preview_path):
                shutil.copy2(p, preview_path)
            gifs.append({"filename": fname, "subfolder": "", "type": "output", "format": "video/mp4"})
        print(f"[VideoPreview] gifs={gifs}")
        return {"ui": {"gifs": gifs}}


NODE_CLASS_MAPPINGS = {
    "SynVowApiVideoPreview": SynVowVideoPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiVideoPreview": "SynVow 视频预览",
}
