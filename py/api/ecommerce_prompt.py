"""
SynVow 电商提示词生成节点
"""
import json
import os
import requests

from .media_common import upload_image as _upload_image, DIRECT_API_BASE as _DIRECT_API_BASE

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_CURRENT_DIR, "..", "prompts")

_MODEL_OPTIONS = ["gemini-3.1-flash-2606", "gemini-3.5-flash-2606", "gemini-3.1-pro-2606", "gemini-3-pro-2606", "gemini-3.1-pro-2605", "gemini-3.1-flash-2605", "gemini-3.5-flash-2605", "gemini-3-pro-2605"]


def _load_prompt(filename):
    prompt_file = os.path.join(_PROMPTS_DIR, filename)
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"⚠️ Error loading prompt file {filename}: {e}")
        return None


def _load_system_prompt():
    prompt = _load_prompt("ecommerce_system_prompt.txt")
    if prompt is None:
        print("⚠️ Falling back to ecommerce_default_prompt.txt")
        prompt = _load_prompt("ecommerce_default_prompt.txt")
    if prompt is None:
        raise FileNotFoundError("No prompt files found. Please ensure ecommerce_system_prompt.txt or ecommerce_default_prompt.txt exists in py/prompts/.")
    return prompt


class EcommercePromptGenerator:
    def _parse_response_to_prompts_list(self, response_text):
        import re
        cleaned = (response_text or "").strip()
        for prefix in ("```json", "```"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            result = json.loads(cleaned)
            if isinstance(result, list):
                return [str(item) for item in result]
        except Exception:
            pass
        parts = [p.strip() for p in re.split(r"\n\s*\n\s*\n+", response_text) if p.strip()]
        if len(parts) > 1:
            return parts
        return [response_text]

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "模型": (_MODEL_OPTIONS, {"default": "gemini-3.1-flash-2606"}),
                "product_type": ("STRING", {
                    "multiline": False,
                    "default": "美妆粉底液",
                }),
                "selling_points": ("STRING", {
                    "multiline": True,
                    "default": "持久显色、自动避障",
                }),
                "design_style": (
                    [
                        "简约 Ins 风",
                        "高级奢华",
                        "科技感",
                        "清新自然",
                        "国潮风",
                        "活泼撞色",
                        "极简工业风",
                        "梦幻唯美",
                        "亚马逊风格",
                    ],
                    {"default": "简约 Ins 风"}
                ),
                "scene_preference": (
                    [
                        "混合（以使用场景为主）",
                        "生活方式使用场景（人物/手部交互）",
                        "棚拍干净背景（不复刻参考图背景）",
                    ],
                    {"default": "混合（以使用场景为主）"}
                ),
                "output_language": (
                    [
                        "中文 (Chinese)",
                        "English",
                        "自动检测 (Auto)",
                    ],
                    {"default": "自动检测 (Auto)"}
                ),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "prompt_count": ("INT", {"default": 5, "min": 1, "max": 20, "forceInput": False})
            },
            "optional": {
                "product_image_1": ("IMAGE",),
                "product_image_2": ("IMAGE",),
                "product_image_3": ("IMAGE",),
                "product_image_4": ("IMAGE",),
                "product_image_5": ("IMAGE",),
                "product_image_6": ("IMAGE",),
                "product_image_7": ("IMAGE",),
                "product_image_8": ("IMAGE",),
                "ref_image_1": ("IMAGE",),
                "ref_image_2": ("IMAGE",),
                "ref_image_3": ("IMAGE",),
                "ref_image_4": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("prompts_list", "prompts_count", "debug_info")
    OUTPUT_IS_LIST = (True, False, False)

    FUNCTION = "generate_prompts_with_vision"
    CATEGORY = "💫SynVow_api/api/文本"

    def _collect_image_urls(self, images, api_key, max_images=8):
        urls = []
        for img in images:
            if img is None or len(urls) >= max_images:
                continue
            try:
                if hasattr(img, "shape") and len(img.shape) == 4:
                    for bi in range(int(img.shape[0])):
                        if len(urls) >= max_images:
                            break
                        urls.append(_upload_image(api_key, img[bi:bi+1]))
                else:
                    urls.append(_upload_image(api_key, img))
            except Exception as e:
                print(f"[EcommercePrompt] image upload error: {e}")
        return urls

    def call_llm_vision(self, api_key, model, system_prompt, user_prompt, image_urls=None, seed=None):
        from . import synvow_auth
        headers = synvow_auth.make_api_headers(api_key)
        url = f"{_DIRECT_API_BASE}/api/models/completions"

        if image_urls:
            user_content = [{"type": "text", "text": user_prompt}]
            for img_url in image_urls:
                user_content.append({"type": "image_url", "image_url": {"url": img_url}})
        else:
            user_content = user_prompt

        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        if seed is not None:
            payload["seed"] = seed % 2147483647
        print(f"[EcommercePrompt] {model} 模型正在生成...")
        res = requests.post(url, headers=headers, json=payload, timeout=600, verify=False)
        if res.status_code != 200:
            raise RuntimeError(f"HTTP {res.status_code}: {res.text}")
        result = synvow_auth.parse_chat_response(res.json()) or ""
        print(f"[EcommercePrompt] {model} 模型生成完毕。")
        return result

    def generate_prompts_with_vision(self, 模型, product_type, selling_points, design_style, scene_preference, output_language, seed, prompt_count, product_image_1=None, product_image_2=None, product_image_3=None, product_image_4=None, product_image_5=None, product_image_6=None, product_image_7=None, product_image_8=None, ref_image_1=None, ref_image_2=None, ref_image_3=None, ref_image_4=None):
        from . import synvow_auth
        api_key = synvow_auth.read_api_key()
        model_name = 模型 or "gemini-3.1-flash-2606"

        product_urls = self._collect_image_urls(
            [product_image_1, product_image_2, product_image_3, product_image_4,
             product_image_5, product_image_6, product_image_7, product_image_8],
            api_key, max_images=8
        )
        ref_urls = self._collect_image_urls(
            [ref_image_1, ref_image_2, ref_image_3, ref_image_4],
            api_key, max_images=4
        )
        image_urls = product_urls + ref_urls

        system_instruction = _load_system_prompt()

        if output_language == "中文 (Chinese)":
            lang_instruction = "请使用中文生成所有提示词内容（包括主文案、副文案、画面描述等）。"
        elif output_language == "English":
            lang_instruction = "Please generate all prompt content in English (including main copy, sub-copy, scene descriptions, etc.)."
        else:
            lang_instruction = "请根据用户输入的语言自动选择输出语言（中文输入→中文输出，英文输入→英文输出）。"

        if scene_preference == "生活方式使用场景（人物/手部交互）":
            scene_instruction = "每一屏都必须是全新设计的生活方式/使用场景画面，画面中必须有人物或手部与产品交互（手持/使用/穿着/涂抹/喷洒/操作），并且必须有真实场景背景（浴室/梳妆台/卧室/街拍/家居等）。硬性禁止：白底棚拍、白底平铺、俯拍平铺、证件照式正面商品图。"
        elif scene_preference == "棚拍干净背景（不复刻参考图背景）":
            scene_instruction = "每一屏都必须是全新设计的棚拍画面（干净背景/渐变/纯色/摄影棚布光），禁止复刻参考图的原背景与道具；允许少量手部交互特写来表现使用。硬性禁止：白底平铺、俯拍平铺、证件照式正面商品图。"
        else:
            scene_instruction = "以全新设计的使用场景为主（优先有人物/手部交互 + 真实环境背景），少量屏幕可用干净棚拍用于参数/结构说明；禁止把参考图背景当作必须复刻的场景。硬性禁止：白底棚拍、白底平铺、俯拍平铺、证件照式正面商品图。"

        target_count = max(1, min(20, int(prompt_count)))

        image_section = ""
        if product_urls or ref_urls:
            product_end = len(product_urls) if product_urls else 0
            ref_start = product_end + 1
            ref_end = product_end + len(ref_urls) if ref_urls else product_end
            product_block = f"""
【产品参考图】共 {len(product_urls)} 张，编号：图片1 ~ 图片{product_end}
  - 仅用于：锁定产品的形状、轮廓、颜色、材质、logo、细节纹理，所有屏必须保持产品外观完全一致。
  - 必须做到：抠出产品主体，丢弃原图背景，为每屏重建全新场景与镜头。
  - 严格禁止：从产品参考图中提取任何背景色调、氛围、排版或光影风格。""" if product_urls else ""
            ref_block = f"""
【风格参考图】共 {len(ref_urls)} 张，编号：图片{ref_start} ~ 图片{ref_end}
  - 仅用于：提取视觉风格——色调配色、背景氛围、光影风格、排版结构、构图节奏。
  - 必须做到（两步强制执行）：
    第一步 分析：仔细观察风格参考图，提取以下具体描述（不能泛泛而谈）：
      · 色调/配色：例如"深红+黑色高对比"、"米白+金色暖调"
      · 背景氛围：例如"暗调戏剧感纯色红背景"、"极简米白渐变棚拍"
      · 光影风格：例如"强侧光硬阴影"、"柔和漫射光"、"电影感逆光"
      · 排版风格：例如"左对齐大字重+细衬线副标题"、"居中极简风"
      · 构图节奏：例如"主体占画面75%留右侧文字区"、"上下分割图文各半"
    第二步 写入：把第一步提取的具体描述逐字写入每一屏提示词的"设计与排版"和"画质与细节"字段，禁止写"参考风格图"等模糊表达。
  - 严格禁止：从风格参考图中提取或描述任何产品形状、产品细节、人物身份或品牌信息。
  - 严格禁止：把风格参考图的产品/人物当作本次产品的参考外观。""" if ref_urls else ""
            image_section = f"\n[图片分组说明 - 严格区分，禁止混用]{product_block}{ref_block}\n"

        base_user_req = f"""
请为以下产品设计 {{COUNT}} 屏详情页提示词：
1. 产品类型: {product_type}
2. 核心卖点: {selling_points}
3. 设计风格: {design_style}
4. 场景偏好: {scene_preference}（必须遵守：{scene_instruction}）
5. 输出语言要求: {lang_instruction}
{image_section}
重要：每个元素是纯字符串，不要包装成 JSON 对象，不要出现 prompt、consistency_id 等字段名，不要输出任何解释文字。

请严格输出 JSON 字符串列表 (List[str])，列表长度必须严格等于 {{COUNT}}。
每个元素对应一屏，字符串内部允许换行。不要输出 Markdown、不要代码块、不要额外解释。
"""

        max_per_call = 6
        collected = []
        call_idx = 0
        last_error = None
        while len(collected) < target_count and call_idx < 30:
            remaining = target_count - len(collected)
            request_n = min(remaining, max_per_call)
            user_req = base_user_req.replace("{COUNT}", str(request_n))
            if collected:
                user_req += f"\n\n补充要求：这是续写生成。请生成新的 {request_n} 屏，不要重复之前的内容与角度。"
            print(f"[EcommercePrompt] 生成第 {len(collected)+1}~{len(collected)+request_n} 屏 ({len(collected)}/{target_count})")
            try:
                result = self.call_llm_vision(api_key, model_name, system_instruction, user_req, image_urls or None, seed + call_idx)
            except Exception as e:
                last_error = str(e)
                break
            batch = self._parse_response_to_prompts_list(result)
            collected.extend(batch)
            call_idx += 1
        if not collected:
            err = last_error or "未知错误"
            try:
                import server
                server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
            except Exception:
                pass
            return ([f"[GENERATION_FAILED] {err}"], 0, err)

        collected = collected[:target_count]
        debug_payload = {
            "model": model_name,
            "image_count": len(image_urls),
            "collected_count": len(collected),
        }
        try:
            import server
            server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
        except Exception:
            pass
        return (collected, len(collected), json.dumps(debug_payload, ensure_ascii=False))



NODE_CLASS_MAPPINGS = {
    "EcommercePromptGenerator": EcommercePromptGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EcommercePromptGenerator": "🛒 电商详情页提示词生成器",
}
