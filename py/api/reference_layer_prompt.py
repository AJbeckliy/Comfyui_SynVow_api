"""Adaptive planning isolated from the integrated asset generator."""

import json
import math
import hashlib
import re
import logging
import tempfile
from pathlib import Path

from . import ymai_llm as llm_client


SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "reference_layer_adaptive_system.txt"
GENERATION_PROMPT_PATH = SYSTEM_PROMPT_PATH.with_name("reference_layer_generation.json")
NODE_VERSION = "independent-layers-v3.5-explicit-fallback"
KINDS = {"background", "subject_product", "text_logo", "decorations",
         "lighting_atmosphere", "other_reusable"}


def _unpack(value):
    return (value[0] if value else None) if isinstance(value, (list, tuple)) else value


def _default_model(models):
    return "GM3.6-flash-稳定" if "GM3.6-flash-稳定" in models else models[0]


def _source_canvas(image):
    shape = getattr(image, "shape", None)
    if shape is None or len(shape) < 3:
        raise ValueError("参考图没有有效的画布尺寸")
    height, width = int(shape[-3]), int(shape[-2])
    if min(height, width) <= 0:
        raise ValueError("参考图画布尺寸无效")
    divisor = math.gcd(width, height)
    return {"width": width, "height": height, "aspect_ratio": f"{width // divisor}:{height // divisor}",
            "coordinate_system": "normalized_top_left_origin"}


def _extract_plan(raw):
    text = str(raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    if start < 0:
        raise ValueError("LLM未返回规划JSON对象")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM规划JSON不完整或格式错误：{exc.msg}，位置{exc.pos}") from exc
    return value


def _plain_prompts(items, prompts):
    return "\n\n---\n\n".join(
        f"{index:02d}. {item['name']}\n{item['description']}\n{prompt}"
        for index, (item, prompt) in enumerate(zip(items, prompts), 1)
    )


def _text(value, limit, field, required=False):
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是字符串")
    value = " ".join(value.split())
    if len(value) > limit or (required and not value):
        raise ValueError(f"{field} 需为完整短句，最多 {limit} 字")
    return value


def _box(value):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("元素坐标必须是完整的四项原画布坐标")
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in value):
        raise ValueError("元素坐标必须在 0 至 1 之间")
    if value[0] >= value[2] or value[1] >= value[3]:
        raise ValueError("元素坐标范围无效")
    return list(value)


def _resolve_membership(elements, raw_layers):
    layers = []
    assigned = {}
    for index, raw in enumerate(raw_layers, 1):
        if not isinstance(raw, dict) or raw.get("kind") not in KINDS:
            raise ValueError("图层类型无效")
        if (index == 1) != (raw["kind"] == "background"):
            raise ValueError("仅最底层应为保留底图")
        members = raw.get("members", [])
        if not isinstance(members, list) or any(not isinstance(key, str) for key in members):
            raise ValueError("图层缺少有效元素归属")
        members = [key.strip() for key in members]
        for key in members:
            if key not in elements or key in assigned:
                raise ValueError(f"元素归属重复或引用了不存在的元素：{key}")
            assigned[key] = index
        layers.append({**raw, "members": members})

    unresolved = []
    for key, element in elements.items():
        owner = element.get("layer_index")
        if owner is not None and (type(owner) is not int or not 1 <= owner <= len(layers)):
            raise ValueError(f"{key}（{element['label']}）的layer_index必须在1至{len(layers)}之间")
        if key in assigned:
            if owner is not None and owner != assigned[key]:
                raise ValueError(f"{key}（{element['label']}）的layer_index与members归属冲突")
            owner = assigned[key]
        else:
            reason = ""
            if owner is not None:
                if "members" in raw_layers[owner - 1]:
                    reason = "按元素明确标注的layer_index补全成员名单"
            elif element["role"] == "background":
                owner, reason = 1, "按背景身份补入唯一背景层"
            elif len(layers) == 2:
                owner, reason = 2, "按前景身份补入唯一前景层"
            else:
                label = element["label"].casefold()
                matches = [index for index, layer in enumerate(layers, 1) if index > 1 and any(
                    isinstance(layer.get(field), str) and layer[field].strip().casefold() == label
                    for field in ("name", "target"))]
                if len(matches) == 1:
                    owner, reason = matches[0], "按与元素名称完全一致的唯一图层补全"
            if owner is None:
                unresolved.append(f"{key}（{element['label']}）")
                continue
            layers[owner - 1]["members"].append(key)
            if reason:
                element["membership_repair"] = {
                    "element_id": key, "label": element["label"], "layer_index": owner, "reason": reason,
                }
        expected_role = "background" if owner == 1 else "foreground"
        if element["role"] != expected_role:
            raise ValueError(f"背景必须独立：{key}（{element['label']}）的身份与第{owner}层冲突")
        element["layer_index"] = owner
    if unresolved:
        raise ValueError("未分配且无法确定归属：" + "、".join(unresolved))
    return layers


def _force_continue_result(image, layer_count, direction, model, reason, data=None, raw="", diagnostic=None):
    try:
        count = max(2, min(6, int(_unpack(layer_count))))
    except (ValueError, TypeError, OverflowError):
        count = 4
    try:
        # Only the user-authorized failure path uses the legacy preset renderer.
        # The normal node remains independent and always performs the new LLM planning.
        from .transparent_asset_generator import SynVowTransparentAssetPromptGenerator
        prompts, serialized, text, _ = SynVowTransparentAssetPromptGenerator().generate(
            scene_preset="参考图分层拆图", planner_mode="规则预设(不调用LLM)", asset_count=count,
            layer_count=count, custom_prompt=direction, llm_model=model, seed=0,
            product_or_reference_image=image,
        )
        plan = json.loads(serialized)
        plan.update(ok=True, status="ready_fallback", generation_allowed=True, degraded=True,
                    plan_source="legacy_fixed_fallback", primary_planning_strategy=NODE_VERSION,
                    planner_type="automatic_with_fallback",
                    fallback_reason=str(reason), diagnostic_path=diagnostic, llm_raw_response=raw,
                    inventory_membership_complete=False)
        status = f"新LLM规划未完成，已回退旧固定分类继续输出{count}层。原因：{reason}"
        if diagnostic:
            status += f" 原始规划：{diagnostic}"
        return prompts, json.dumps(plan, ensure_ascii=False, indent=2), text, status
    except Exception as fallback_error:
        return _emergency_continue_result(image, count, direction, model,
            f"{reason}；固定分类回退也失败：{fallback_error}", data, raw, diagnostic)


def _emergency_continue_result(image, layer_count, direction, model, reason, data=None, raw="", diagnostic=None):
    try:
        count = max(2, min(6, int(_unpack(layer_count))))
    except (ValueError, TypeError, OverflowError):
        count = 4
    try:
        canvas = _source_canvas(image)
        frame = f"原图整幅画布{canvas['width']}×{canvas['height']}，宽高比{canvas['aspect_ratio']}。"
    except Exception:
        canvas, frame = {}, "保持输入参考图的完整原画布及宽高比。"
    source_layers = data.get("layers", []) if isinstance(data, dict) else []
    if not isinstance(source_layers, list):
        source_layers = []
    items, prompts = [], []
    for index in range(count):
        candidate = source_layers[index] if index < len(source_layers) and isinstance(source_layers[index], dict) else {}
        raw_name = candidate.get("name")
        name = raw_name.strip() if isinstance(raw_name, str) and 0 < len(raw_name.strip()) <= 20 else f"前景组{index}"
        if index == 0:
            name = "背景/保留底图"
        else:
            name = name.replace("背景", "底景")
        hint = candidate.get("target", "")
        hint = " ".join(hint.split()) if isinstance(hint, str) else ""
        items.append({"index": index + 1, "key": f"layer_{index + 1:02d}",
                      "slot_id": "background" if index == 0 else "other_reusable", "name": name,
                      "description": hint if len(hint) <= 80 else name,
                      "visible_content": hint if len(hint) <= 80 else name,
                      "geometry": {"layer_bbox_normalized": [0, 0, 1, 1] if index == 0 else [],
                                   "placement_mode": "preserve_full_canvas"}})
    group_names = "、".join(item["name"] for item in items[1:])
    for index, item in enumerate(items):
        if index == 0:
            prompt = (
                "[Layer: background]" + frame +
                "从参考图提取完整背景净版，只保留原有背景底色、纹理及环境。移除全部前景，不保留主体、文字或装饰残片。"
                "移除区域只延续邻近背景，不重画被删除对象，不把对象缩小后藏回背景。"
                "保持背景原有视角、透视、颜色、光影和清晰度，不移动、不放大、不裁切画布。"
                "输出铺满原画布的不透明PNG，无透明洞、残影、羽化边、棋盘格或新增场景。只输出背景这一层。"
            )
        else:
            prompt = (
                f"[Layer: other_reusable]{frame}参考图前景统一划分为{count - 1}个互不重复的组，背景单独成层。"
                "先按完整元素的可见面积由大到小分组，不够则按颜色、内部组成和位置细分；多余小元素合并进末组，不遗漏可见内容。"
                f"各组参考名称依次为：{group_names}。本次只提取第{index}组：{item['name']}。"
                "其他组和背景全部透明。保留目标原有位置、比例、形状、颜色和细节，不居中、不放大、不重排、不补遮挡或画外部分。"
                "目标遮挡其他元素的可见部分仍须保留。输出完整原画布的真alpha PNG，不拼图、不画棋盘格。"
            )
        optional = []
        if item["visible_content"]:
            optional.append("本层内容参考：" + item["visible_content"] + "。")
        if isinstance(direction, str) and direction.strip():
            optional.append("用户分组要求：" + direction.strip() + "。")
        for hint in optional:
            if len(prompt) + len(hint) <= 500:
                prompt += hint
        prompts.append(prompt)
        item["generation_prompt"] = prompt
    status = f"已强制输出{count}层提示词并继续出图；规划有缺漏，分组未完整验证。原因：{reason}"
    plan = {
        "ok": True, "status": "ready_degraded", "generation_allowed": True, "degraded": True,
        "planner_type": "emergency_rule_continue", "plan_source": "forced_continue", "planning_strategy": NODE_VERSION,
        "scene_preset": "参考图分层拆图", "layer_count": count, "source_canvas": canvas,
        "user_direction": direction, "llm_model": str(model or ""), "items": items,
        "layer_order_bottom_to_top": [item["key"] for item in items],
        "planning_warnings": [str(reason)], "inventory_membership_complete": False,
        "diagnostic_path": diagnostic, "llm_raw_response": raw,
        "prompt_config_path": str(SYSTEM_PROMPT_PATH), "generation_prompt_config_path": str(GENERATION_PROMPT_PATH),
    }
    return prompts, json.dumps(plan, ensure_ascii=False, indent=2), _plain_prompts(items, prompts), status


def _save_failed_plan(raw, model, count, canvas, error):
    try:
        import folder_paths
        directory = Path(folder_paths.get_output_directory()) / "SynVowLayerPlanningDiagnostics"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", prefix="failed_plan_",
                                         dir=directory, delete=False) as file:
            json.dump({"version": NODE_VERSION, "model": model, "layer_count": count,
                       "source_canvas": canvas, "error": str(error), "llm_raw_response": raw},
                      file, ensure_ascii=False, indent=2)
            return file.name
    except Exception:
        logging.getLogger(__name__).warning("Unable to save layer-planning diagnostic", exc_info=True)
        return None


def _normalize_plan(data, count):
    if not isinstance(data, dict):
        raise ValueError("规划必须是 JSON 对象")
    raw_elements, raw_layers = data.get("elements"), data.get("layers")
    if not isinstance(raw_elements, list) or len(raw_elements) > 32:
        raise ValueError("规划缺少元素清单，或超过 32 组")
    if not isinstance(raw_layers, list) or len(raw_layers) != count:
        raise ValueError(f"规划必须返回 {count} 个图层")
    elements = {}
    for raw in raw_elements:
        if not isinstance(raw, dict):
            raise ValueError("元素记录无效")
        key = _text(raw.get("id"), 24, "element.id", True)
        if key in elements:
            raise ValueError("元素编号重复")
        bbox = _box(raw.get("bbox_normalized"))
        role = raw.get("role")
        if role not in ("background", "foreground"):
            raise ValueError("元素必须标明背景或前景归属")
        area = raw.get("visible_area_ratio")
        if type(area) not in (int, float) or not math.isfinite(area) or not 0 <= area <= 1:
            raise ValueError("元素必须给出有效的可见面积估计，不能用外框面积代替")
        elements[key] = {"id": key, "label": _text(raw.get("label"), 32, "element.label", True),
                         "role": role, "visible_area_ratio": area, "bbox_normalized": bbox}
        if "layer_index" in raw:
            elements[key]["layer_index"] = raw["layer_index"]
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        # Both values are vision estimates, not measured geometry. A mismatch
        # must not discard an otherwise usable plan or replace it with a preset.
        if area > bbox_area + 0.001:
            elements[key]["area_estimate_warning"] = (
                f"{key}（{elements[key]['label']}）：可见面积估计{area:.4f}高于外框面积{bbox_area:.4f}；"
                "保留原估计供排序参考，不作为裁切或缩放依据。"
            )
        elif area == 0:
            elements[key]["area_estimate_warning"] = (
                f"{key}（{elements[key]['label']}）：面积估计为0，仍保留该可见元素及其图层归属。"
            )
    layers = _resolve_membership(elements, raw_layers)
    items, assigned = [], set()
    for index, raw in enumerate(layers):
        if not isinstance(raw, dict) or raw.get("kind") not in KINDS:
            raise ValueError("图层类型无效")
        kind = raw["kind"]
        if (index == 0) != (kind == "background"):
            raise ValueError("仅最底层应为保留底图")
        members = raw.get("members")
        if not isinstance(members, list) or any(not isinstance(key, str) for key in members):
            raise ValueError("图层缺少有效元素归属")
        if len(set(members)) != len(members) or any(key not in elements or key in assigned for key in members):
            raise ValueError("元素归属重复或引用了不存在的元素")
        expected_role = "background" if index == 0 else "foreground"
        if any(elements[key]["role"] != expected_role for key in members):
            raise ValueError("背景必须独立，不能把前景元素藏进背景层或把背景放进前景层")
        if index and not members:
            raise ValueError("前景层不能为空：需按元素、颜色或位置继续细分，不能用空层凑数")
        assigned.update(members)
        regions = [elements[key] for key in members]
        target = _text(raw.get("target"), 48, "layer.target", bool(members))
        restored = [elements[key]["label"] for key in members if elements[key].get("membership_repair")]
        for label in restored:
            if label not in target:
                target = f"{target}；{label}" if target else label
        if index and not members and target:
            raise ValueError("空图层不能描述不存在的元素")
        occlusion = _text(raw.get("occlusion", ""), 48, "layer.occlusion")
        name = _text(raw.get("name"), 20, "layer.name", True)
        # The existing saver identifies the base by its Chinese name, not its kind.
        name = "背景/保留底图：" + name if index == 0 else name.replace("背景", "底景")
        bbox = [0, 0, 1, 1] if index == 0 else (
            [min(r["bbox_normalized"][0] for r in regions), min(r["bbox_normalized"][1] for r in regions),
             max(r["bbox_normalized"][2] for r in regions), max(r["bbox_normalized"][3] for r in regions)]
            if regions else []
        )
        geometry = {"layer_bbox_normalized": bbox, "regions": regions,
                    "occlusion_relationships": occlusion}
        items.append({"index": index + 1, "key": f"layer_{index + 1:02d}", "slot_id": kind,
                      "name": name, "members": members, "description": target, "visible_content": target,
                      "visible_area_ratio_estimate": sum(elements[key]["visible_area_ratio"] for key in members),
                      "empty": index > 0 and not members, "geometry": geometry})
    if assigned != set(elements):
        raise ValueError("内部归属校验失败，缺少：" + "、".join(sorted(set(elements) - assigned)))
    # Priority is diagnostic metadata, never a replacement for bottom-to-top order.
    for priority, item in enumerate(sorted(items[1:], key=lambda item: -item["visible_area_ratio_estimate"]), 1):
        item["area_priority"] = priority
    return items, list(elements.values())


def _compile_prompt(item, items, canvas, rules=None):
    if rules is None:
        rules = json.loads(GENERATION_PROMPT_PATH.read_text(encoding="utf-8"))
    kind = item["slot_id"]
    target = item["visible_content"]
    geometry = item["geometry"]
    canvas_text = f"原图整幅画布{canvas['width']}×{canvas['height']}，宽高比{canvas['aspect_ratio']}。"
    if kind == "background":
        removed = "；".join(layer["visible_content"] for layer in items[1:] if not layer["empty"])
        rule = rules["background"]
        action = rule["action"].format(target=target or "原有底色和纹理", removed=removed or "无")
    else:
        excluded = "、".join(layer["name"] for layer in items[1:]
                            if layer["key"] != item["key"] and not layer["empty"])
        rule = rules["foreground"]
        action = rule["action"].format(target=target)
        if excluded:
            action += rule["exclude"].format(excluded=excluded)
    lock, finish = rule["lock"], rule["finish"]
    parts = [f"[Layer: {kind}]", canvas_text, action, lock, finish]
    # Reserve whole invariants first. Optional geometry is added atomically, never tail-cut.
    extras = []
    if kind != "background" and not item["empty"]:
        regions = geometry.get("regions", [])
        if len(regions) > 1:
            centers = []
            for region in regions:
                x1, y1, x2, y2 = region["bbox_normalized"]
                centers.append(f"({round((x1 + x2) * 50)},{round((y1 + y2) * 50)})")
            extras.append(f"{len(regions)}个可见区域原位中心参考(全图百分比)：" + ",".join(centers) + "。")
        if geometry.get("occlusion_relationships"):
            extras.append("遮挡关系：" + geometry["occlusion_relationships"] + "。")
        extras.append("位置框(原画布左上为0，右下为1，非裁切范围)：" +
                      json.dumps(geometry.get("reference_layer_bbox_normalized") or
                                 geometry["layer_bbox_normalized"], separators=(",", ":")) + "。")
        for region in geometry.get("regions", []):
            extras.append(region["label"] + "=" + json.dumps(region["bbox_normalized"], separators=(",", ":")) + "。")
    for extra in extras:
        if len("".join(parts)) + len(extra) <= 500:
            parts.insert(-1, extra)
    prompt = "".join(parts)
    if len(prompt) > 500:
        raise ValueError("规划描述过长，无法在500字内保留完整约束")
    return prompt


def _export_full_canvas_item(item):
    result = dict(item)
    geometry = dict(item["geometry"])
    geometry["reference_layer_bbox_normalized"] = (
        geometry.get("reference_layer_bbox_normalized") or geometry.get("layer_bbox_normalized", [])
    )
    # Generated overlays already occupy the source canvas. A vision estimate is
    # a prompt hint, not authority to crop and stretch their nontransparent pixels.
    geometry["layer_bbox_normalized"] = [0, 0, 1, 1] if item["slot_id"] == "background" else []
    geometry.pop("bbox_normalized", None)
    geometry["placement_mode"] = "preserve_full_canvas"
    result["geometry"] = geometry
    return result


class SynVowReferenceLayerPromptGenerator:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/文本"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False, False, False)
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompts_list", "asset_plan_json", "prompts_text", "status")
    DESCRIPTION = "优先独立LLM规划，缺漏自动补全；仍失败则按指定层数回退旧固定分类继续出图，状态明确标注回退原因。"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        payload = {key: str(value) for key, value in kwargs.items() if key != "planner_mode"}
        payload.update(version=NODE_VERSION, system_prompt=SYSTEM_PROMPT_PATH.read_text(encoding="utf-8"),
                       generation_rules=GENERATION_PROMPT_PATH.read_text(encoding="utf-8"))
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    @classmethod
    def INPUT_TYPES(cls):
        models = llm_client.fetch_models()
        return {"required": {
            "reference_image": ("IMAGE",),
            "layer_count": (["2", "3", "4", "5", "6"], {"default": "4"}),
            "custom_prompt": ("STRING", {"multiline": True, "default": ""}),
            "llm_model": (models, {"default": _default_model(models)}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
        }}

    def generate(self, reference_image, layer_count, custom_prompt, llm_model, seed, **legacy_inputs):
        image = _unpack(reference_image)
        # Accept a stale API workflow field without allowing it to select old presets.
        try:
            if image is None:
                raise ValueError("请连接参考图 reference_image。")
            return self._adaptive_generate(image, layer_count, custom_prompt, llm_model)
        except Exception as exc:
            return _force_continue_result(image, layer_count, str(_unpack(custom_prompt) or ""),
                                          _unpack(llm_model), str(exc))

    def _adaptive_generate(self, image, layer_count, custom_prompt, llm_model):
        count = int(_unpack(layer_count))
        if count not in range(2, 7):
            raise ValueError("layer_count必须在2至6之间；旧工作流请刷新页面后重新导入")
        direction = str(_unpack(custom_prompt) or "").strip()
        model = _unpack(llm_model) or _default_model(llm_client.fetch_models())
        canvas = _source_canvas(image)
        system = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        rules = json.loads(GENERATION_PROMPT_PATH.read_text(encoding="utf-8"))
        raw = llm_client.chat_completion(
            model, system,
            json.dumps({"user_direction": direction, "layer_count": count, "background_layer_count": 1,
                        "foreground_layer_count": count - 1, "source_canvas": canvas,
                        "allocation_order": "visible_area_descending_not_bbox_area",
                        "stacking_order": "source_occlusion_bottom_to_top",
                        "coverage": "all_visible_content_exactly_once_no_empty_foreground"}, ensure_ascii=False),
            image_urls=llm_client.image_to_data_urls(image), temperature=0.2,
            max_tokens=6400, timeout=240, max_attempts=1,
        )
        data = None
        try:
            data = _extract_plan(raw)
            items, elements = _normalize_plan(data, count)
            prompts = [_compile_prompt(item, items, canvas, rules) for item in items]
            description = _text(data.get("source_image_description", ""), 160, "source description")
        except Exception as exc:
            diagnostic = _save_failed_plan(raw, model, count, canvas, exc)
            return _force_continue_result(image, count, direction, model, str(exc), data, raw, diagnostic)
        for item, prompt in zip(items, prompts):
            item["generation_prompt"] = prompt
        items = [_export_full_canvas_item(item) for item in items]
        warnings = [element["area_estimate_warning"] for element in elements if element.get("area_estimate_warning")]
        repairs = [element["membership_repair"] for element in elements if element.get("membership_repair")]
        plan = {
            "ok": True, "status": "ready_with_repairs" if repairs else "ready", "generation_allowed": True,
            "degraded": bool(repairs), "inventory_membership_complete": True,
            "scene_preset": "参考图分层拆图", "planner_type": "llm_only",
            "plan_source": f"llm:{model}", "planning_strategy": NODE_VERSION,
            "prompt_config_path": str(SYSTEM_PROMPT_PATH), "layer_count": count, "asset_count": None,
            "generation_prompt_config_path": str(GENERATION_PROMPT_PATH),
            "user_direction": direction, "source_canvas": canvas,
            "source_image_description": description,
            "elements": elements, "items": items,
            "planning_warnings": warnings,
            "membership_repairs": repairs,
            "background_layer_count": 1, "foreground_layer_count": count - 1,
            "area_measurement": "llm_estimate_of_visible_pixels_not_bbox_area",
            "placement_policy": "full_canvas_no_foreground_bbox_refit",
            "element_priority_large_to_small": [element["id"] for element in sorted(
                (element for element in elements if element["role"] == "foreground"),
                key=lambda element: -element["visible_area_ratio"])],
            "planning_priority_large_to_small": [item["key"] for item in sorted(
                items[1:], key=lambda item: item["area_priority"])],
            "layer_order_bottom_to_top": [item["key"] for item in items],
            "llm_raw_response": raw,
        }
        warning_status = f" 面积估计提醒{len(warnings)}项，未回退旧模板，详见asset_plan_json。" if warnings else ""
        if repairs:
            warning_status += f" 已补全{len(repairs)}项明确归属，未增减图层，详见membership_repairs。"
        return (prompts, json.dumps(plan, ensure_ascii=False, indent=2), _plain_prompts(items, prompts),
                f"独立参考图自适应规划完成：1层背景＋{count - 1}层前景，按可见面积分配、按遮挡叠放，模型={model}。"
                "坐标仅供提示参考，前景不按估计外框二次拉伸。清单内元素已完整归属；不代表视觉提取已验证。"
                "asset_plan_json继续连接PNG保存与PSD节点。" + warning_status)


NODE_CLASS_MAPPINGS = {
    "SynVowReferenceLayerPromptGenerator": SynVowReferenceLayerPromptGenerator,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowReferenceLayerPromptGenerator": "SynVow 参考图分层提示词生成器",
}
