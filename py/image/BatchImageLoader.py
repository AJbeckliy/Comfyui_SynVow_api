import os
import torch
import numpy as np
from PIL import Image
import folder_paths

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
        if not folder_path or not os.path.exists(folder_path):
            raise ValueError(f"文件夹路径不存在: {folder_path}")

        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tiff'}
        image_files = []
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file_name)
                if ext.lower() in image_extensions:
                    image_files.append(file_path)

        if not image_files:
            raise ValueError(f"文件夹中没有找到图像文件: {folder_path}")

        image_files = self._sort_files(image_files, sort_by)
        start_idx = index * batch_size
        end_idx = start_idx + batch_size
        batch_files = image_files[start_idx:end_idx]

        if not batch_files:
            raise ValueError(f"索引 {index} 超出范围,文件夹共有 {len(image_files)} 张图像,最多支持 {len(image_files) // batch_size} 个批次")

        images = []
        for img_path in batch_files:
            img = Image.open(img_path)
            img = img.convert('RGB')
            img_array = np.array(img).astype(np.float32) / 255.0
            images.append(img_array)

        images_tensor = torch.from_numpy(np.stack(images))
        batch_count = len(batch_files)
        filenames = [os.path.splitext(os.path.basename(f))[0] for f in batch_files]
        filenames_str = "\n".join(filenames)

        return (images_tensor, batch_count, filenames_str)

    def _sort_files(self, files, sort_by):
        if sort_by == "none":
            return files
        elif sort_by == "name_natural":
            return sorted(files, key=self._natural_sort_key)
        elif sort_by == "name_natural_desc":
            return sorted(files, key=self._natural_sort_key, reverse=True)
        elif sort_by == "time_asc":
            return sorted(files, key=lambda x: os.path.getmtime(x))
        elif sort_by == "time_desc":
            return sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
        return files

    def _natural_sort_key(self, path):
        import re
        filename = os.path.basename(path)
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', filename)]


NODE_CLASS_MAPPINGS = {
    "SynVowBatchImageLoader": SynVowBatchImageLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowBatchImageLoader": "批次图像加载器",
}
