class SynVowImageListCompose:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image1": ("IMAGE",),
            },
            "optional": {
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "image6": ("IMAGE",),
                "image7": ("IMAGE",),
                "image8": ("IMAGE",),
                "image9": ("IMAGE",),
                "image10": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image list",)
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "compose"
    CATEGORY = "💫SynVow_api/Image"
    DESCRIPTION = "将多个图像输入按顺序组合为图像列表，支持列表和batch输入，自动展开为单张"

    def compose(self, image1, image2=None, image3=None, image4=None, image5=None,
                image6=None, image7=None, image8=None, image9=None, image10=None):
        def _expand(val):
            if val is None:
                return []
            items = val if isinstance(val, list) else [val]
            result = []
            for t in items:
                if t is None:
                    continue
                if len(t.shape) == 4 and t.shape[0] > 1:
                    for i in range(t.shape[0]):
                        result.append(t[i:i+1])
                else:
                    result.append(t)
            return result

        images = []
        for slot in (image1, image2, image3, image4, image5, image6, image7, image8, image9, image10):
            images.extend(_expand(slot))
        return (images,)


NODE_CLASS_MAPPINGS = {
    "SynVowImageListCompose": SynVowImageListCompose,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowImageListCompose": "图像列表组合器",
}
