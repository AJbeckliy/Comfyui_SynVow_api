import torch

from .FolderImageListLoader import (
    filename_stems,
    image_path_to_tensor,
    scan_image_files,
    sort_image_files,
)

class SynVowBatchImageLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": ""}),
                "batch_size": ("INT", {"default": 2, "min": 1, "max": 1000}),
                "sort_by": (["none", "name_natural", "name_natural_desc", "time_asc", "time_desc"], {"default": "none"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 99999}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING")
    RETURN_NAMES = ("images", "batch_count", "filenames")
    FUNCTION = "load_batch"
    CATEGORY = "💫SynVow_api/Image"
    DESCRIPTION = "按批次加载文件夹图像"

    def load_batch(self, folder_path, batch_size, sort_by, index):
        image_files = sort_image_files(scan_image_files(folder_path), sort_by)
        start_idx = index * batch_size
        end_idx = start_idx + batch_size
        batch_files = image_files[start_idx:end_idx]

        if not batch_files:
            raise ValueError(f"索引 {index} 超出范围,文件夹共有 {len(image_files)} 张图像,最多支持 {len(image_files) // batch_size} 个批次")

        images_tensor = torch.cat([image_path_to_tensor(img_path) for img_path in batch_files], dim=0)
        batch_count = len(batch_files)
        filenames_str = "\n".join(filename_stems(batch_files))

        return (images_tensor, batch_count, filenames_str)


NODE_CLASS_MAPPINGS = {
    "SynVowBatchImageLoader": SynVowBatchImageLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowBatchImageLoader": "批次图像加载器",
}
