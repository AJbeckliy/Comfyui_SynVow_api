class PromptRangeSelector:
    """从prompts列表中根据起始和结束索引选择范围内的文本"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "start_index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "end_index": ("INT", {"default": 10, "min": 0, "max": 999999}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_prompts",)
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "select_range"
    CATEGORY = "💫SynVow_api/Text"
    DESCRIPTION = "从文本列表中根据起始和结束索引选择范围内的文本输出"

    def select_range(self, prompts_list, start_index, end_index):
        start = start_index[0] if isinstance(start_index, list) else start_index
        end = end_index[0] if isinstance(end_index, list) else end_index

        if not isinstance(prompts_list, list):
            prompts_list = [prompts_list]

        total_items = len(prompts_list)

        if start > end:
            raise Exception(f"Error: start_index ({start}) cannot be greater than end_index ({end})")

        if start >= total_items:
            raise Exception(f"Error: start_index ({start}) out of range (total items: {total_items})")

        if end >= total_items:
            end = total_items - 1

        selected = prompts_list[start:end + 1]

        return (selected,)


NODE_CLASS_MAPPINGS = {
    "SynVowPromptRangeSelector": PromptRangeSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowPromptRangeSelector": "提示词范围选择器",
}
