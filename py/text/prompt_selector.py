class PromptSelector:
    """从prompts列表中根据索引选择单个文本"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_text",)
    INPUT_IS_LIST = True
    FUNCTION = "select_prompt"
    CATEGORY = "💫SynVow_api/Text"
    DESCRIPTION = "从文本列表中根据索引选择单个文本输出"

    def select_prompt(self, prompts_list, index):
        idx = index[0] if isinstance(index, list) else index

        if not isinstance(prompts_list, list):
            prompts_list = [prompts_list]

        if idx >= len(prompts_list):
            print(f"⚠️ 索引 {idx} 超出范围(共{len(prompts_list)}条),返回最后一条")
            idx = len(prompts_list) - 1

        selected = prompts_list[idx]

        return (selected,)


NODE_CLASS_MAPPINGS = {
    "SynVowPromptSelector": PromptSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowPromptSelector": "提示词选择器",
}
