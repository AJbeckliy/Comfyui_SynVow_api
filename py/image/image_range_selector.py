class ImageRangeSelector:
    """从图像列表或批次中根据起始和结束索引选择范围内的图像"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"forceInput": True}),
                "start_index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "end_index": ("INT", {"default": 10, "min": 1, "max": 999999}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "select_range"
    CATEGORY = "💫SynVow_api/Image"
    DESCRIPTION = "从图像列表或批次中根据起始和结束索引选择范围内的图像输出"

    def select_range(self, images, start_index, end_index):
        start = start_index[0] if isinstance(start_index, list) else start_index
        end = end_index[0] if isinstance(end_index, list) else end_index

        image_list = []
        for img in images:
            if img.shape[0] > 1:
                for i in range(img.shape[0]):
                    image_list.append(img[i:i+1])
            else:
                image_list.append(img)

        total_items = len(image_list)

        if start > end:
            raise Exception(f"Error: start_index ({start}) cannot be greater than end_index ({end})")

        if start >= total_items:
            raise Exception(f"Error: start_index ({start}) out of range (total items: {total_items})")

        if end >= total_items:
            end = total_items - 1

        selected = image_list[start:end + 1]

        return (selected,)


NODE_CLASS_MAPPINGS = {
    "SynVowImageRangeSelector": ImageRangeSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowImageRangeSelector": "图像范围选择器",
}
