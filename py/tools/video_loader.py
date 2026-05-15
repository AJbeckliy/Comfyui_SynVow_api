import os
import folder_paths
from comfy_api.latest._input_impl.video_types import VideoFromFile


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
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING")
    RETURN_NAMES = ("video", "video_path")
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, video):
        video_path = folder_paths.get_annotated_filepath(video)
        if os.path.isfile(video_path):
            return str(os.path.getmtime(video_path))
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(cls, video):
        if not folder_paths.exists_annotated_filepath(video):
            return f"视频文件不存在: {video}"
        return True

    def load_video(self, video):
        video_path = folder_paths.get_annotated_filepath(video)

        if not os.path.isfile(video_path):
            return {"ui": {"gifs": []}, "result": (None, "")}

        gifs = [{
            "filename": video,
            "subfolder": "",
            "type": "input",
            "format": "video/mp4",
        }]

        return {"ui": {"gifs": gifs}, "result": (VideoFromFile(video_path), video_path)}


NODE_CLASS_MAPPINGS = {
    "SynVowApiVideoLoader": VideoLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiVideoLoader": "加载视频（输出路径）",
}
