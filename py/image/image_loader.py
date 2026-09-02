import os

import numpy as np
import torch
from PIL import Image


class SynVowImageLoader:
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "paths": ("STRING", {"default": "", "multiline": True}),
                "index": ("INT", {"default": -1, "min": -1, "max": 1000000, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "filename", "filepath")
    OUTPUT_IS_LIST = (True, True, True, True)
    FUNCTION = "load_image"
    CATEGORY = "💫SynVow_api/Image"
    DESCRIPTION = "按索引加载图像，-1 表示加载全部路径列表"

    def _create_empty_image(self, width=512, height=512):
        img = torch.zeros((1, height, width, 3))
        mask = torch.ones((1, height, width))
        return img, mask

    def _load_one(self, path):
        image = Image.open(path)
        if image.mode == "RGBA":
            alpha = np.array(image.split()[3]).astype(np.float32) / 255.0
            mask = torch.from_numpy(alpha).unsqueeze(0)
            image = image.convert("RGB")
        else:
            if image.mode != "RGB":
                image = image.convert("RGB")
            mask = torch.ones((1, image.height, image.width))
        image_np = np.array(image).astype(np.float32) / 255.0
        tensor = torch.from_numpy(image_np).unsqueeze(0)
        filename = os.path.splitext(os.path.basename(path))[0]
        filepath = os.path.dirname(path)
        return tensor, mask, filename, filepath

    def load_image(self, paths, index):
        path_list = [p.strip() for p in paths.split("\n") if p.strip()]
        for path in path_list:
            if os.path.isdir(path):
                raise ValueError(f"Folder path not supported: {path}, please input file path")
        if not path_list:
            raise ValueError("No paths provided")
        image_files = []
        for path in path_list:
            if os.path.exists(path) and os.path.splitext(path.lower())[1] in self.IMAGE_EXTENSIONS:
                image_files.append(path)
        if not image_files:
            raise ValueError("No valid image files found")

        if index == -1:
            tensors, masks, filenames, filepaths = [], [], [], []
            for path in image_files:
                try:
                    tensor, mask, filename, filepath = self._load_one(path)
                    tensors.append(tensor)
                    masks.append(mask)
                    filenames.append(filename)
                    filepaths.append(filepath)
                except Exception:
                    continue
            if not tensors:
                img, mask = self._create_empty_image()
                return ([img], [mask], ["none"], [""])
            return (tensors, masks, filenames, filepaths)

        if index >= len(image_files):
            raise ValueError(f"Index {index} out of range [0, {len(image_files) - 1}]")
        selected_path = image_files[index]
        try:
            tensor, mask, filename, filepath = self._load_one(selected_path)
            return ([tensor], [mask], [filename], [filepath])
        except Exception:
            img, mask = self._create_empty_image()
            return ([img], [mask], [""], [""])


NODE_CLASS_MAPPINGS = {
    "SynVowImageLoader": SynVowImageLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowImageLoader": "图像列表加载器",
}
