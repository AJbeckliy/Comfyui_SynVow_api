# 文本分割节点

from typing import List, Dict, Any, Tuple, Union

class SynVowApiTextSplitter:
    @classmethod
    def INPUT_TYPES(s) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "delimiter": ("STRING", {"default": "\\n"}),
                "index": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "list")
    OUTPUT_IS_LIST = (False, True)
    FUNCTION = "split_text"
    CATEGORY = "💫SynVow_api/tools"
    DESCRIPTION = "按分隔符切分文本"

    def validate_input(self, text: str, delimiter: str) -> None:
        if not text.strip():
            raise ValueError("Input text cannot be empty")
        if not delimiter:
            raise ValueError("Delimiter cannot be empty")
        delimiter = delimiter.replace('\\n', '\n')
        if not delimiter:
            raise ValueError("Invalid delimiter")
        return delimiter

    def split_text(self, text: str, delimiter: str, index: int) -> Tuple:
        try:
            delimiter = self.validate_input(text, delimiter)
            parts = [part.strip() for part in text.split(delimiter) if part.strip()]
            if not parts:
                raise ValueError("No valid text parts found after splitting")
            if index == -1:
                return ("\n".join(parts), parts)
            elif 0 <= index < len(parts):
                return (parts[index], parts)
            else:
                raise ValueError(f"Index {index} out of range (0-{len(parts)-1})")
        except Exception as e:
            raise ValueError(str(e))

NODE_CLASS_MAPPINGS = {
    "SynVowApiTextSplitter": SynVowApiTextSplitter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiTextSplitter": "SynVow 文本分割"
}
