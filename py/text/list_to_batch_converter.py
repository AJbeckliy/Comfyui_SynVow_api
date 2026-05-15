import json


class ListToBatchConverter:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompts_list": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "placeholder": "输入提示词列表，每行一条",
                }),
                "batch_size": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 20,
                    "forceInput": False,
                    "tooltip": "每批处理的数量",
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("batch_output",)
    OUTPUT_IS_LIST = (False,)

    FUNCTION = "convert_list_to_batches"
    CATEGORY = "💫SynVow_api/Text"

    def convert_list_to_batches(self, prompts_list, batch_size):
        if not prompts_list or not prompts_list.strip():
            return ("Error: No prompts list provided",)

        try:
            if prompts_list.strip().startswith('['):
                try:
                    prompts = json.loads(prompts_list)
                    if isinstance(prompts, list):
                        prompt_items = prompts
                    else:
                        prompt_items = [str(prompts)]
                except json.JSONDecodeError:
                    prompt_items = [line.strip() for line in prompts_list.split('\n') if line.strip()]
            else:
                prompt_items = [line.strip() for line in prompts_list.split('\n') if line.strip()]

            if not prompt_items:
                return ("Error: No valid prompts found",)

            batches = ['\n'.join(prompt_items[i:i+batch_size]) for i in range(0, len(prompt_items), batch_size)]
            return ('\n---\n'.join(batches),)

        except Exception as e:
            return (f"Error: {str(e)}",)


NODE_CLASS_MAPPINGS = {
    "ListToBatchConverter": ListToBatchConverter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ListToBatchConverter": "列表批次转换器",
}
