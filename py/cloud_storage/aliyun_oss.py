# 阿里云OSS上传节点

import io

import numpy as np
import oss2
from PIL import Image


class SynVowAliyunBucket:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "bucket_name": ("STRING", {"default": "your-bucket-name"}),
                "access_key_id": ("STRING", {"default": ""}),
                "access_key_secret": ("STRING", {"default": ""}),
                "endpoint": ("STRING", {"default": "oss-cn-hangzhou.aliyuncs.com"}),
                "object_name": ("STRING", {"default": "output/image.png"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("oss_url",)
    FUNCTION = "upload_image"
    CATEGORY = "💫SynVow_api/OSS"

    def upload_image(self, image, bucket_name, access_key_id, access_key_secret, endpoint, object_name):
        try:
            if image.shape[0] > 1:
                return ("Error: Batch processing not supported. Please provide a single image.",)
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            img_array = (image[0].cpu().numpy() * 255).astype(np.uint8)
            pil_image = Image.fromarray(img_array)
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format="PNG")
            result = bucket.put_object(object_name, img_byte_arr.getvalue())
            if result.status == 200:
                return (f"https://{bucket_name}.{endpoint}/{object_name}",)
            else:
                return (f"Error: Failed to upload image to OSS. Status code: {result.status}",)
        except Exception as e:
            return (f"Error uploading file: {str(e)}",)


NODE_CLASS_MAPPINGS = {
    "SynVowAliyunBucket": SynVowAliyunBucket,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowAliyunBucket": "SynVow 阿里云OSS上传",
}
