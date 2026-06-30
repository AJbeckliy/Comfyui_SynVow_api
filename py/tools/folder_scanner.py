import os
import re
from pathlib import Path
from typing import List, Tuple, Set, Dict, Union

class SynVowFolderScanner:
    @classmethod
    def INPUT_TYPES(s) -> Dict[str, Dict[str, Union[str, bool, int, List[str]]]]:
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "recursive": ("BOOLEAN", {"default": True}),
                "output_mode": (["files", "folders"], {"default": "files"}),
                "file_type": (["all", "images", "txt", "video", "audio"], {"default": "all"}),
                "sort_by": (["none", "name_natural", "name_natural_desc", "time_asc", "time_desc"], {"default": "none"}),
                "max_depth": ("INT", {"default": -1, "min": -1, "max": 20, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("paths", "count")
    FUNCTION = "scan_folder"
    CATEGORY = "💫SynVow_api/Utils"
    DESCRIPTION = "扫描文件夹输出路径列表"

    def __init__(self) -> None:
        self._image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}
        self._txt_extensions = {'.txt'}
        self._video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        self._audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}

    @classmethod
    def IS_CHANGED(cls, folder_path: str, recursive: bool, output_mode: str,
                  file_type: str, sort_by: str, max_depth: int, seed: int) -> str:
        return f"{seed}"

    def _natural_sort_key(self, text: str) -> Tuple[int, List[Union[int, str]]]:
        def convert(part: str) -> Union[int, str]:
            return int(part) if part.isdigit() else part.lower()
        natural_key = [convert(c) for c in re.split(r'(\d+)', text)]
        first_char = text[0] if text else ''
        if first_char.isdigit():
            type_order = 0
        elif first_char.isascii() and first_char.isalpha():
            type_order = 1
        else:
            type_order = 2
        return (type_order, natural_key)

    def _get_file_mtime(self, file_path: str) -> float:
        try:
            return os.path.getmtime(file_path)
        except OSError:
            return 0.0

    def _sort_files(self, file_paths: List[str], sort_by: str) -> List[str]:
        if sort_by == "none":
            return file_paths
        try:
            if sort_by == "name_natural":
                return sorted(file_paths, key=lambda x: self._natural_sort_key(os.path.basename(x)))
            elif sort_by == "name_natural_desc":
                return sorted(file_paths, key=lambda x: self._natural_sort_key(os.path.basename(x)), reverse=True)
            file_infos = [(path, self._get_file_mtime(path)) for path in file_paths]
            if sort_by == "time_asc":
                file_infos.sort(key=lambda x: x[1])
            elif sort_by == "time_desc":
                file_infos.sort(key=lambda x: x[1], reverse=True)
            return [info[0] for info in file_infos]
        except Exception:
            return file_paths

    def _validate_path(self, path: str) -> str:
        if not path:
            raise ValueError("Folder path cannot be empty")
        abs_path = str(Path(path).resolve())
        if len(abs_path) > 260:
            raise ValueError(f"Path too long: {abs_path}")
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Path does not exist: {abs_path}")
        if not os.path.isdir(abs_path):
            raise NotADirectoryError(f"Path is not a directory: {abs_path}")
        if not os.access(abs_path, os.R_OK):
            raise PermissionError(f"No read permission: {abs_path}")
        return abs_path

    def _is_valid_file(self, file_path: str, file_type: str) -> bool:
        if file_type == "all":
            return True
        ext = os.path.splitext(file_path)[1].lower()
        if file_type == "images":
            return ext in self._image_extensions
        elif file_type == "txt":
            return ext in self._txt_extensions
        elif file_type == "video":
            return ext in self._video_extensions
        elif file_type == "audio":
            return ext in self._audio_extensions
        return False

    def scan_folder(self, folder_path: str, recursive: bool, output_mode: str,
                   file_type: str, sort_by: str, max_depth: int, seed: int) -> Tuple[str, int]:
        try:
            abs_path = self._validate_path(folder_path)
            if not recursive and output_mode == "folders":
                return (abs_path, 1)
            paths: List[str] = []
            folder_count = 0
            file_count = 0
            seen_folders: Set[str] = set()

            def scan_dir(path: str, depth: int) -> None:
                nonlocal folder_count, file_count
                if max_depth >= 0 and depth > max_depth:
                    return
                try:
                    for item in os.listdir(path):
                        full_path = os.path.join(path, item)
                        if os.path.isfile(full_path):
                            if output_mode == "files" and self._is_valid_file(full_path, file_type):
                                paths.append(full_path)
                                file_count += 1
                        elif os.path.isdir(full_path):
                            folder_count += 1
                            if output_mode == "folders" and full_path not in seen_folders:
                                paths.append(full_path)
                                seen_folders.add(full_path)
                            if recursive:
                                scan_dir(full_path, depth + 1)
                except (PermissionError, Exception):
                    pass

            scan_dir(abs_path, 0)
            if output_mode == "folders" and not paths:
                paths.append(abs_path)
                folder_count = 1
            if not paths:
                return ("", 0)
            paths = self._sort_files(paths, sort_by)
            count = file_count if output_mode == "files" else folder_count
            return ("\n".join(paths), count)
        except Exception as e:
            raise ValueError(str(e))


NODE_CLASS_MAPPINGS = {
    "SynVowFolderScanner": SynVowFolderScanner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowFolderScanner": "文件夹扫描器",
}
