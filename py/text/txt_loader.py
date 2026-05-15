import os
from typing import List, Dict, Any, Tuple

class SynVowTxtLoader:
    @classmethod
    def INPUT_TYPES(s) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "file_paths": ("STRING", {"multiline": True}),
                "file_index": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "process_texts"
    CATEGORY = "💫SynVow_api/Text"
    DESCRIPTION = "按路径读取多个TXT文本"

    def validate_file_paths(self, file_paths: str) -> List[str]:
        if not file_paths.strip():
            raise ValueError("Input file paths cannot be empty")
        paths = [path.strip() for path in file_paths.split("\n") if path.strip()]
        if not paths:
            raise ValueError("No valid file paths found in input")
        valid_paths = []
        for path in paths:
            if not os.path.exists(path):
                raise ValueError(f"File not found: {path}")
            if not path.lower().endswith('.txt'):
                raise ValueError(f"Not a text file: {path}")
            valid_paths.append(path)
        return valid_paths

    def read_text_file(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content.strip():
                raise ValueError(f"Empty file: {file_path}")
            return content
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {str(e)}")

    def process_texts(self, file_paths: str, file_index: int) -> Tuple[str]:
        try:
            valid_paths = self.validate_file_paths(file_paths)
            target_paths = valid_paths
            if file_index >= 0:
                if file_index >= len(valid_paths):
                    raise ValueError(f"File index {file_index} out of range (0-{len(valid_paths)-1})")
                target_paths = [valid_paths[file_index]]
            all_results = []
            for path in target_paths:
                content = self.read_text_file(path)
                all_results.append(content)
            if not all_results:
                return ("",)
            elif len(all_results) == 1:
                return (all_results[0],)
            else:
                return ("\n".join(all_results),)
        except Exception as e:
            raise ValueError(str(e))


NODE_CLASS_MAPPINGS = {
    "SynVowTxtLoader": SynVowTxtLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowTxtLoader": "TXT文件加载器",
}
