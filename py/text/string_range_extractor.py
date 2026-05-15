import re
import json


class StringRangeExtractor:
    """根据范围模板从文本中提取匹配片段列表。
    支持两种模式：
    - 普通模式：pattern 包含 |，如 {|}，以左右两侧为开始/结束标记提取文本片段
    - JSON模式：pattern 格式为 {[字段名]}，从文本中解析 JSON 数组，提取每个对象的指定字段
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "pattern": ("STRING", {"multiline": False, "default": "{|}"}),
                "index": ("INT", {"default": -1, "min": -1, "max": 0xfffffffffffff, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("items",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "extract"
    CATEGORY = "💫SynVow_api/Text"
    DESCRIPTION = "根据范围模板提取内容：{|} 普通标记模式；{[字段名]} JSON数组字段提取模式"

    _JSON_PATTERN = re.compile(r"^\{\[(.+)\]\}$")

    def extract(self, text, pattern, index):
        text = text.strip()
        if not text:
            return ([],)

        json_match = self._JSON_PATTERN.match(pattern.strip())
        if json_match:
            matches = self._extract_json_field(text, json_match.group(1).strip())
        else:
            matches = self._extract_by_marks(text, pattern)

        if not matches:
            return ([text],)

        if index == -1:
            return (matches,)

        if index >= len(matches):
            raise IndexError(f"index ({index}) 超出范围，共匹配到 {len(matches)} 项（索引 0~{len(matches)-1}）")

        return ([matches[index]],)

    def _extract_json_field(self, text, field_name):
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = text.find(start_char)
            if start == -1:
                continue
            for end in range(len(text), start, -1):
                candidate = text[start:end]
                try:
                    parsed = json.loads(candidate)
                    break
                except json.JSONDecodeError:
                    continue
            else:
                continue

            if isinstance(parsed, list):
                array = parsed
            elif isinstance(parsed, dict):
                array = next((v for v in parsed.values() if isinstance(v, list)), None)
                if array is None:
                    raise ValueError(f"JSON 中未找到数组字段，无法提取 '{field_name}'")
            else:
                raise ValueError("JSON 根节点既不是数组也不是对象")

            results = []
            for i, item in enumerate(array):
                if not isinstance(item, dict):
                    continue
                if field_name not in item:
                    raise KeyError(f"第 {i} 个对象中不存在字段 '{field_name}'，可用字段：{list(item.keys())}")
                results.append(str(item[field_name]).strip())
            return results

        raise ValueError("文本中未找到有效的 JSON 内容")

    def _extract_by_marks(self, text, pattern):
        if "|" not in pattern:
            raise ValueError(f"pattern 格式错误：必须包含 '|' 或使用 {{[字段名]}} 格式，当前输入：{pattern!r}")

        sep = pattern.index("|")
        start_mark = pattern[:sep]
        end_mark = pattern[sep + 1:]

        if not start_mark and not end_mark:
            raise ValueError("pattern 的开始标记和结束标记不能同时为空")

        regex = re.escape(start_mark) + "(.*?)" + re.escape(end_mark)
        matches = re.findall(regex, text, re.DOTALL)
        return [m.strip() for m in matches]


NODE_CLASS_MAPPINGS = {
    "SynVowApiStringRangeExtractor": StringRangeExtractor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiStringRangeExtractor": "字符串范围提取器",
}
