import os
import folder_paths
from comfy_api.latest._input_impl.video_types import VideoFromFile

from .media_crop import maybe_crop_media


class VideoLoader:
    FUNCTION = "load_video"
    CATEGORY = "💫SynVow_api/Utils"

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = sorted(folder_paths.filter_files_content_types(files, ["video"]))
        if not files:
            files = [""]
        return {
            "required": {
                "video": (files, {}),
                "起始秒": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1}),
                "裁剪秒数": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING")
    RETURN_NAMES = ("video", "video_path")
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, video, 起始秒, 裁剪秒数):
        video_path = folder_paths.get_annotated_filepath(video)
        if os.path.isfile(video_path):
            return f"{os.path.getmtime(video_path)}|{起始秒:.6f}|{裁剪秒数:.6f}"
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(cls, video):
        if not folder_paths.exists_annotated_filepath(video):
            return f"视频文件不存在: {video}"
        return True

    def load_video(self, video, 起始秒, 裁剪秒数):
        video_path = folder_paths.get_annotated_filepath(video)

        if not os.path.isfile(video_path):
            return {"ui": {"gifs": []}, "result": (None, "")}

        effective_path = maybe_crop_media(video_path, 起始秒, 裁剪秒数)

        gifs = [{
            "filename": video,
            "subfolder": "",
            "type": "input",
            "format": "video/mp4",
        }]

        return {"ui": {"gifs": gifs}, "result": (VideoFromFile(effective_path), effective_path)}


NODE_CLASS_MAPPINGS = {
    "SynVowApiVideoLoader": VideoLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiVideoLoader": "加载视频（输出路径）",
}
