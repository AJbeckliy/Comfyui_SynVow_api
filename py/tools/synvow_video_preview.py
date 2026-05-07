import os
import shutil


class SynVowVideoPreview:
    FUNCTION = "preview"
    CATEGORY = "\U0001f4abSynVow_api/tools"
    OUTPUT_NODE = True
    RETURN_TYPES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {"forceInput": True}),
            }
        }

    def preview(self, video_path=None):
        import folder_paths
        gifs = []
        if not video_path:
            return {"ui": {"gifs": []}}
        paths = [video_path] if isinstance(video_path, str) else list(video_path)
        out_dir = folder_paths.get_output_directory()
        for p in paths:
            if p and os.path.isfile(p):
                fname = os.path.basename(p)
                preview_path = os.path.join(out_dir, fname)
                if os.path.normpath(p) != os.path.normpath(preview_path):
                    shutil.copy2(p, preview_path)
                gifs.append({"filename": fname, "subfolder": "", "type": "output", "format": "video/mp4"})
        return {"ui": {"gifs": gifs}}


NODE_CLASS_MAPPINGS = {
    "SynVowApiVideoPreview": SynVowVideoPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiVideoPreview": "SynVow 视频预览",
}
