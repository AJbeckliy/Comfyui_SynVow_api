import json
import base64
import io
import os
import numpy as np
import requests
from PIL import Image

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_CURRENT_DIR, "..", "prompts")

_DIRECT_API_BASE = "https://service.synvow.com/api/v1"
_MODEL_OPTIONS = ["gemini-3.1-flash", "gemini-3.1-pro"]
_MODE_OPTIONS = ["默认", "优质"]
_MODEL_MAP = {
    ("gemini-3.1-flash", "默认"): "gemini-3.1-flash-默认",
    ("gemini-3.1-flash", "优质"): "gemini-3.1-flash-优质",
    ("gemini-3.1-pro",   "默认"): "gemini-3.1-pro-默认",
    ("gemini-3.1-pro",   "优质"): "gemini-3.1-pro-优质",
}


def _load_prompt(filename):
    prompt_file = os.path.join(_PROMPTS_DIR, filename)
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"⚠️ Prompt file not found: {prompt_file}")
        return None
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
    def __init__(self):
        pass

    def split_response_to_screens(self, text, prompt_count):
        if text is None:
            return []

        s = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
        if not s:
            return []

        if prompt_count is None or int(prompt_count) <= 1:
            return [s]

        import re

        json_obj_pattern = r'\{\s*"prompt"\s*:\s*"'
        matches = list(re.finditer(json_obj_pattern, s))
        if len(matches) >= 2:
            parsed_objects = []
            idxs = [m.start() for m in matches]
            for i, start_idx in enumerate(idxs):
                end_idx = idxs[i + 1] if i + 1 < len(idxs) else len(s)
                chunk = s[start_idx:end_idx].strip().rstrip(',')
                try:
                    obj = json.loads(chunk)
                    if isinstance(obj, dict) and "prompt" in obj:
                        parsed_objects.append(obj["prompt"])
                    else:
                        parsed_objects.append(chunk)
                except json.JSONDecodeError:
                    clean = re.sub(r'^\s*\{\s*"prompt"\s*:\s*"', '', chunk)
                    clean = re.sub(r'"\s*\}\s*$', '', clean)
                    parsed_objects.append(clean)
            if parsed_objects:
                return parsed_objects

        start_markers = [
            r"(?m)^\s*屏幕定位\s*：",
            r"(?m)^\s*Screen Role\s*:",
            r"(?m)^\s*Main Title\s*:",
            r"(?m)^\s*主标题\s*：",
        ]
        for pat in start_markers:
            matches = list(re.finditer(pat, s))
            if len(matches) >= 2:
                idxs = [m.start() for m in matches] + [len(s)]
                parts = [s[idxs[i]:idxs[i + 1]].strip() for i in range(len(idxs) - 1)]
                parts = [p for p in parts if p]
                if parts:
                    return parts

        if "\n---\n" in s:
            parts = [p.strip() for p in s.split("\n---\n")]
            parts = [p for p in parts if p]
            if parts:
                return parts

        parts = [p.strip() for p in re.split(r"\n\s*\n\s*\n+", s)]
        parts = [p for p in parts if p]
        if len(parts) >= 2:
            return parts

        return [s]

    def _clean_code_fences(self, response_text):
        cleaned = (response_text or "").strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _parse_response_to_prompts_list(self, response_text, expected_count):
        method = "json"
        prompts_list = []
        try:
            cleaned = self._clean_code_fences(response_text)
            prompts_list = json.loads(cleaned)
            if not isinstance(prompts_list, list):
                method = "split:not_list"
                prompts_list = self.split_response_to_screens(response_text, expected_count)
        except json.JSONDecodeError:
            method = "split:json_decode_error"
            prompts_list = self.split_response_to_screens(response_text, expected_count)
        except Exception:
            method = "split:exception"
            prompts_list = self.split_response_to_screens(response_text, expected_count)

        normalized = []
        for item in prompts_list if isinstance(prompts_list, list) else [prompts_list]:
            text = self.extract_prompt_text(item)
            if text is None:
                continue
            normalized.append(self._strip_screen_role_header(text))

        if normalized:
            prompts_list = normalized
        else:
            prompts_list = []

        prompts_list = self.enforce_prompt_count(prompts_list, expected_count, response_text)
        if len(prompts_list) > expected_count:
            prompts_list = prompts_list[:expected_count]

        return prompts_list, method

    def _strip_screen_role_header(self, prompt_text):
        if not isinstance(prompt_text, str):
            return prompt_text

        s = prompt_text.replace("\r\n", "\n").replace("\r", "\n")
        import re

        m0 = re.search(r"(?m)^\s*(Main Copy\s*:|主文案\s*：|主文案\s*:)", s)
        if m0:
            return s[m0.start():].lstrip()

        m = re.search(r"(?m)^\s*(Main Title\s*:|主标题\s*：)", s)
        if m:
            return s[m.start():].lstrip()

        m2 = re.search(r"(?m)^\s*(Screen Role\s*:|屏幕定位\s*：)", s)
        if m2:
            after = s[m2.end():]
            after = re.sub(r"^\s*\n", "", after)
            return after.lstrip()

        return s.strip()

    def _is_prompt_structurally_complete(self, prompt_text):
        if not isinstance(prompt_text, str):
            return False
        s = prompt_text.strip()
        if not s:
            return False

        has_main = ("主文案" in s) or ("Main Copy" in s) or ("Main Title" in s) or ("主标题" in s)
        has_sub = ("副文案" in s) or ("SubTitle" in s) or ("Subtitle" in s) or ("副标题" in s)

        return has_main and has_sub

    def enforce_prompt_count(self, prompts_list, prompt_count, raw_response):
        try:
            pc = int(prompt_count)
        except Exception:
            pc = None

        if not pc or pc <= 0:
            return prompts_list

        if not prompts_list:
            return [str(raw_response)]

        if len(prompts_list) == pc:
            return prompts_list

        if len(prompts_list) > pc:
            head = prompts_list[:pc - 1]
            tail = prompts_list[pc - 1:]
            merged_tail = "\n\n".join([t for t in tail if isinstance(t, str) and t.strip()] or [str(t) for t in tail])
            head.append(merged_tail)
            return head

        if len(prompts_list) == 1 and isinstance(prompts_list[0], str):
            parts = self.split_response_to_screens(prompts_list[0], pc)
            if parts and len(parts) >= pc:
                head = parts[:pc - 1]
                tail = parts[pc - 1:]
                head.append("\n\n".join(tail).strip())
                return head

        parts = self.split_response_to_screens(raw_response, pc)
        if parts and len(parts) >= pc:
            head = parts[:pc - 1]
            tail = parts[pc - 1:]
            head.append("\n\n".join(tail).strip())
            return head

        return prompts_list

    def extract_prompt_text(self, item):
        if item is None:
            return None

        if isinstance(item, dict):
            prompt = item.get("prompt")
            if isinstance(prompt, str):
                return prompt
            return json.dumps(item, ensure_ascii=False)

        if isinstance(item, str):
            s = item.strip()
            if (s.startswith("{") and s.endswith("}")) or (s.startswith("[{") and s.endswith("}]")):
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict) and isinstance(obj.get("prompt"), str):
                        return obj["prompt"]
                except Exception:
                    pass

            return s.replace("\\n", "\n")

        return str(item)

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "模型": (_MODEL_OPTIONS, {"default": "gemini-3.1-flash"}),
                "模式": (_MODE_OPTIONS, {"default": "默认"}),
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
                "seed": ("INT", {"default": 0, "min": 0, "max": 99999}),
                "prompt_count": ("INT", {"default": 10, "min": 1, "max": 20, "forceInput": False})
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

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompts_list", "debug_info")
    OUTPUT_IS_LIST = (True, False)

    FUNCTION = "generate_prompts_with_vision"
    CATEGORY = "💫SynVow_api/tools"

    def tensor_to_base64(self, image, index=0):
        if image is None:
            return None

        img_tensor = image
        try:
            if hasattr(image, "shape") and len(image.shape) == 4:
                img_tensor = image[index]
        except Exception:
            img_tensor = image

        i = 255. * img_tensor.cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"

    def collect_base64_images(self, images, max_images=6):
        base64_images = []

        if images is None:
            return base64_images

        for img in images:
            if img is None:
                continue

            try:
                if hasattr(img, "shape") and len(img.shape) == 4:
                    batch = int(img.shape[0])
                    for bi in range(batch):
                        if len(base64_images) >= max_images:
                            return base64_images
                        base64_images.append(self.tensor_to_base64(img, bi))
                else:
                    if len(base64_images) >= max_images:
                        return base64_images
                    base64_images.append(self.tensor_to_base64(img, 0))
            except Exception:
                if len(base64_images) >= max_images:
                    return base64_images
                base64_images.append(self.tensor_to_base64(img, 0))

        return [b for b in base64_images if b]

    def call_llm_vision(self, model, system_prompt, user_prompt, base64_images=None, seed=None):
        from ..api import synvow_auth
        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)
        url = f"{_DIRECT_API_BASE}/api/models/chat/completions"

        content_list = [{"type": "text", "text": user_prompt}]
        if base64_images:
            if isinstance(base64_images, str):
                base64_images = [base64_images]
            for base64_image in base64_images:
                if not base64_image:
                    continue
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": base64_image}
                })

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_list},
            ],
            "max_tokens": 4096,
            "temperature": 0.7,
            "stream": False,
        }
        if seed is not None:
            payload["seed"] = seed % 2147483647

        try:
            print(f"🔗 Calling API: {url}")
            print(f"🔑 Using model: {model}")
            res = requests.post(url, headers=headers, json=payload, timeout=(30, 600), verify=False)
            if res.status_code != 200:
                error_msg = f"HTTP {res.status_code}: {res.text[:200]}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            content = synvow_auth.parse_chat_response(res.json())
            return {"success": True, "content": content}
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def generate_prompts_with_vision(self, 模型, 模式, product_type, selling_points, design_style, scene_preference, output_language, seed, prompt_count, product_image_1=None, product_image_2=None, product_image_3=None, product_image_4=None, product_image_5=None, product_image_6=None, product_image_7=None, product_image_8=None, ref_image_1=None, ref_image_2=None, ref_image_3=None, ref_image_4=None):
        model_name = _MODEL_MAP.get((模型, 模式), f"{模型}-{模式}")

        product_b64 = self.collect_base64_images(
            [product_image_1, product_image_2, product_image_3, product_image_4,
             product_image_5, product_image_6, product_image_7, product_image_8],
            max_images=8
        )
        ref_b64 = self.collect_base64_images(
            [ref_image_1, ref_image_2, ref_image_3, ref_image_4],
            max_images=4
        )
        base64_images = product_b64 + ref_b64

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

        try:
            target_count = int(prompt_count)
        except Exception:
            target_count = 10
        target_count = max(1, min(20, target_count))

        base_user_req = f"""
请为以下产品设计 {{COUNT}} 屏详情页提示词：
1. 产品类型: {product_type}
2. 核心卖点: {selling_points}
3. 设计风格: {design_style}
4. 场景偏好: {scene_preference}（必须遵守：{scene_instruction}）
5. 输出语言要求: {lang_instruction}

[图片分组说明 - 严格区分，禁止混用]

【产品参考图】共 {len(product_b64)} 张，编号：图片1 ~ 图片{len(product_b64) if product_b64 else 0}
  - 仅用于：锁定产品的形状、轮廓、颜色、材质、logo、细节纹理，所有屏必须保持产品外观完全一致。
  - 必须做到：抠出产品主体，丢弃原图背景，为每屏重建全新场景与镜头。
  - 严格禁止：从产品参考图中提取任何背景色调、氛围、排版或光影风格。

【风格参考图】共 {len(ref_b64)} 张，编号：图片{len(product_b64)+1} ~ 图片{len(product_b64)+len(ref_b64) if ref_b64 else len(product_b64)}
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
  - 严格禁止：把风格参考图的产品/人物当作本次产品的参考外观。

重要：每屏输出只包含提示词正文，不要出现字段名（例如 prompt、consistency_id），不要输出任何解释文字。

请严格输出 JSON 字符串列表 (List[str])，列表长度必须严格等于 {{COUNT}}。
每个元素对应一屏（一个字符串=一屏完整提示词正文），字符串内部允许换行。
每个元素的正文必须直接从"主文案：/Main Copy:"开始（或从"主标题：/Main Title:"开始），不要在开头输出任何"屏幕定位/Screen Role"或"首屏/次屏/卖点总览/核心机理"等屏幕标题行。
不要输出 Markdown、不要代码块、不要输出任何额外解释。
"""

        collected = []
        raw_responses = []
        attempts = []
        max_per_call = 6
        max_calls = 30
        call_idx = 0
        last_error = None

        while len(collected) < target_count and call_idx < max_calls:
            remaining = target_count - len(collected)
            request_n = remaining if remaining <= max_per_call else max_per_call

            user_req = base_user_req.replace("{COUNT}", str(request_n))
            if len(collected) > 0:
                user_req += f"\n\n补充要求：这是续写生成。请生成新的 {request_n} 屏，不要重复之前的内容与角度。"

            print(f"🎨 Generating {request_n} screen prompts... ({len(collected)}/{target_count})")

            current_seed = seed + call_idx if seed is not None else None

            result = self.call_llm_vision(model_name, system_instruction, user_req, base64_images if base64_images else None, current_seed)
            call_idx += 1

            if not result["success"]:
                last_error = result.get("error")
                attempts.append({
                    "call": call_idx,
                    "requested": request_n,
                    "parsed": 0,
                    "accepted": 0,
                    "method": "api_error",
                    "error": last_error,
                })
                continue

            response = result.get("content", "")
            raw_responses.append(response)

            batch_prompts, method = self._parse_response_to_prompts_list(response, request_n)

            accepted = []
            rejected = 0
            for p in batch_prompts:
                if self._is_prompt_structurally_complete(p):
                    accepted.append(p)
                else:
                    rejected += 1

            if not accepted and batch_prompts:
                accepted = batch_prompts

            if len(accepted) > request_n:
                accepted = accepted[:request_n]

            collected.extend(accepted)

            attempts.append({
                "call": call_idx,
                "requested": request_n,
                "parsed": len(batch_prompts),
                "accepted": len(accepted),
                "rejected": rejected,
                "method": method,
                "response_chars": len(response) if isinstance(response, str) else None,
            })

        if len(collected) > target_count:
            collected = collected[:target_count]

        if len(collected) < target_count:
            missing = target_count - len(collected)
            msg = "[GENERATION_FAILED] Unable to generate enough prompts."
            if last_error:
                msg = f"[GENERATION_FAILED] {last_error}"
            collected.extend([msg] * missing)

        debug_payload = {
            "input_summary": base_user_req.replace("{COUNT}", str(target_count)),
            "reference_image_count": len(base64_images),
            "attempts": attempts,
        }
        if raw_responses:
            debug_payload["raw_response"] = raw_responses[-1]
        if last_error:
            debug_payload["error"] = last_error

        return (collected, json.dumps(debug_payload, ensure_ascii=False))


class ListToBatchConverter:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompts_list": ("STRING", {
                    "forceInput": True,
                    "multiline": True,
                    "placeholder": "输入提示词列表，每行一个"
                }),
                "batch_size": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 20,
                    "forceInput": False,
                    "tooltip": "每批处理的数量"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("batch_output",)
    OUTPUT_IS_LIST = (False,)

    FUNCTION = "convert_list_to_batches"
    CATEGORY = "💫SynVow_api/tools"

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

            batches = []
            for i in range(0, len(prompt_items), batch_size):
                batch = prompt_items[i:i + batch_size]
                batches.append('\n'.join(batch))

            result = ""
            for i, batch in enumerate(batches):
                if i > 0:
                    result += "\n---\n"
                result += batch

            return (result,)

        except Exception as e:
            return (f"Error: {str(e)}",)


NODE_CLASS_MAPPINGS = {
    "EcommercePromptGenerator": EcommercePromptGenerator,
    "ListToBatchConverter": ListToBatchConverter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EcommercePromptGenerator": "🛒 电商详情页提示词生成器",
    "ListToBatchConverter": "🔄 List to Batch Converter",
}
