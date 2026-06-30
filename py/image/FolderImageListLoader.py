import os
import re
import math
import random
import torch
import numpy as np
from PIL import Image


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tiff'}


def natural_sort_key(path):
    filename = os.path.basename(path)
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', filename)]


def scan_image_files(folder_path):
    if not folder_path or not os.path.exists(folder_path):
        raise ValueError(f"文件夹路径不存在: {folder_path}")

    image_files = []
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(file_name)
            if ext.lower() in IMAGE_EXTENSIONS:
                image_files.append(file_path)

    if not image_files:
        raise ValueError(f"文件夹中没有找到图像文件: {folder_path}")
    return image_files


def sort_image_files(files, sort_by, seed=0):
    if sort_by == "none":
        return files
    if sort_by == "name_natural":
        return sorted(files, key=natural_sort_key)
    if sort_by == "name_natural_desc":
        return sorted(files, key=natural_sort_key, reverse=True)
    if sort_by == "time_asc":
        return sorted(files, key=lambda x: os.path.getmtime(x))
    if sort_by == "time_desc":
        return sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
    if sort_by == "random":
        shuffled = files.copy()
        random.seed(seed)
        random.shuffle(shuffled)
        return shuffled
    return files


def image_path_to_tensor(img_path):
    img = Image.open(img_path).convert('RGB')
    img_array = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(img_array).unsqueeze(0)


def filename_stems(files):
    return [os.path.splitext(os.path.basename(f))[0] for f in files]


class SynVowFolderImageListLoader:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": ""}),
                "group_size": ("INT", {"default": 81, "min": 1, "max": 9999, "step": 1}),
                "group_index": ("INT", {"default": 0, "min": 0, "max": 9999, "step": 1}),
                "sort_by": (["name_natural", "name_natural_desc", "time_asc", "time_desc", "random"], {"default": "name_natural"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT")
    RETURN_NAMES = ("images", "filenames", "total_groups", "current_group_frames")
    OUTPUT_IS_LIST = (True, True, False, False)
    FUNCTION = "load_list"
    CATEGORY = "💫SynVow_api/Image"
    DESCRIPTION = "从文件夹按组加载图像列表，输出图像列表和文件名列表"

    def load_list(self, folder_path, group_size, group_index, sort_by, seed):
        image_files = sort_image_files(scan_image_files(folder_path), sort_by, seed)

        total_images = len(image_files)
        total_groups = math.ceil(total_images / group_size)

        if group_index < 0:
            raise ValueError(f"Group index must be non-negative, got {group_index}")
        if group_index >= total_groups:
            raise ValueError(
                f"Group index {group_index} is out of range. "
                f"Total images: {total_images}, Group size: {group_size}, Total groups: {total_groups}"
            )

        start_idx = group_index * group_size
        end_idx = min(start_idx + group_size, total_images)
        group_files = image_files[start_idx:end_idx]
        current_group_frames = len(group_files)

        images_list = [image_path_to_tensor(img_path) for img_path in group_files]
        filenames = filename_stems(group_files)

        print(f"📂 [FolderImageListLoader] Loaded group {group_index + 1}/{total_groups}, "
              f"frames {start_idx}-{end_idx - 1} ({current_group_frames} images)")

        return (images_list, filenames, total_groups, current_group_frames)

NODE_CLASS_MAPPINGS = {
    "SynVowFolderImageListLoader": SynVowFolderImageListLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowFolderImageListLoader": "文件夹图像列表加载器",
}
