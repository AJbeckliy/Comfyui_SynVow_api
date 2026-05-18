class ImageListValidator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "images_list2": ("IMAGE",),
            },
            "optional": {
                "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",),
                "images_list5": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("images_list1", "images_list2", "images_list3", "images_list4", "images_list5")
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, True, True, True, True)
    FUNCTION = "validate"
    CATEGORY = "💫SynVow_api/Image"
    DESCRIPTION = "校验多组图像列表数量是否对等，不对等则报错"

    def get_image_count(self, img_list):
        if img_list is None:
            return 0
        if not isinstance(img_list, list):
            img_list = [img_list]
        total = 0
        for item in img_list:
            if len(item.shape) == 4:
                total += item.shape[0]
            else:
                total += 1
        return total

    def validate(self, images_list1, images_list2, images_list3=None, images_list4=None, images_list5=None):
        inputs = {
            "images_list1": images_list1,
            "images_list2": images_list2,
        }
        if images_list3 is not None:
            inputs["images_list3"] = images_list3
        if images_list4 is not None:
            inputs["images_list4"] = images_list4
        if images_list5 is not None:
            inputs["images_list5"] = images_list5

        counts = {name: self.get_image_count(img) for name, img in inputs.items()}
        unique_counts = set(counts.values())
        if len(unique_counts) > 1:
            detail = ", ".join([f"{name}={count}" for name, count in counts.items()])
            raise ValueError(f"图像数量不对等: {detail}")

        print(f"✅ [图像列表数量校验] 校验通过: {list(counts.values())[0]} 张/组")
        return (images_list1, images_list2, images_list3 or [], images_list4 or [], images_list5 or [])


NODE_CLASS_MAPPINGS = {
    "SynVowImageListValidator": ImageListValidator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowImageListValidator": "图像列表数量校验",
}
