class TextRepeat:
    FUNCTION = "repeat"
    CATEGORY = "💫SynVow_api/Text"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
                "数量": ("INT", {"default": 2, "min": 1}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("texts",)
    OUTPUT_IS_LIST = (True,)

    def repeat(self, text, 数量):
        return ([text] * 数量,)


NODE_CLASS_MAPPINGS = {
    "SynVowApiTextRepeat": TextRepeat,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiTextRepeat": "复制文本",
}
