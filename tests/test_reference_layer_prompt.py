import json
import copy
import unittest
import tempfile
from pathlib import Path
from unittest import mock

import torch
from PIL import Image, ImageDraw

from py.api import reference_layer_prompt as dedicated
from py.api import transparent_asset_generator as planner
from py.image import transparent_png_save_preview as saver
from py.image import psd_layer_composer as psd
from py.api import gpt_image_2_alpha_synvow as alpha


def adaptive_plan(count=2):
    elements = [{"id": "bg", "label": "蓝色墙面", "role": "background", "visible_area_ratio": .4,
                 "bbox_normalized": [0, 0, 1, 1]},
                {"id": "person", "label": "人物及佩戴的耳塞", "role": "foreground", "visible_area_ratio": .3,
                 "bbox_normalized": [.1, .1, .9, .8]}]
    layers = [{"name": "蓝色墙面", "kind": "background", "members": ["bg"],
               "target": "原有蓝色墙面", "occlusion": ""}]
    for i in range(1, count):
        elements.append({"id": f"case{i}", "label": f"下方第{i}个耳机盒",
                         "role": "foreground", "visible_area_ratio": .03,
                         "bbox_normalized": [.6, .7, .95, .98]})
        members = ["person", f"case{i}"] if i == 1 else [f"case{i}"]
        target = f"人物、佩戴的耳塞及下方第{i}个耳机盒" if i == 1 else f"下方第{i}个耳机盒"
        layers.append({"name": f"耳机盒{i}", "kind": "subject_product", "members": members,
                       "target": target, "occlusion": "保持原有前后遮挡"})
    return {"source_image_description": "人物和前景耳机盒", "elements": elements, "layers": layers}


class ReferenceLayerPromptTests(unittest.TestCase):
    @mock.patch.object(dedicated.llm_client, "fetch_models", return_value=["mock-model"])
    def test_inputs_and_existing_node_preserved(self, _models):
        inputs = dedicated.SynVowReferenceLayerPromptGenerator.INPUT_TYPES()["required"]
        self.assertEqual(set(inputs), {
            "reference_image", "layer_count", "custom_prompt", "llm_model", "seed",
        })
        original = planner.SynVowTransparentAssetPromptGenerator.INPUT_TYPES()
        self.assertIn(planner.LAYOUT_SPLIT_SCENE, original["required"]["scene_preset"][0])
        self.assertIn("asset_count", original["required"])

    @mock.patch.object(dedicated.llm_client, "image_to_data_urls", return_value=["data:image/png;base64,test"])
    @mock.patch.object(dedicated.llm_client, "chat_completion")
    def test_legacy_mode_cannot_select_old_templates(self, chat, _images):
        image = torch.zeros((1, 32, 24, 3))
        self.assertFalse(issubclass(dedicated.SynVowReferenceLayerPromptGenerator,
                                   planner.SynVowTransparentAssetPromptGenerator))
        with mock.patch.object(planner.SynVowTransparentAssetPromptGenerator, "generate",
                               side_effect=AssertionError("legacy node must not be called")):
            for count in range(2, 7):
                chat.return_value = json.dumps(adaptive_plan(count))
                actual = dedicated.SynVowReferenceLayerPromptGenerator().generate(
                    reference_image=[image], layer_count=str(count), custom_prompt="",
                    llm_model="mock-model", seed=42, planner_mode="规则预设(不调用LLM)")
                self.assertEqual(len(actual[0]), count)
                self.assertEqual(json.loads(actual[1])["planner_type"], "llm_only")
        self.assertEqual(chat.call_count, 5)

    @mock.patch.object(dedicated.llm_client, "image_to_data_urls", return_value=["data:image/png;base64,test"])
    @mock.patch.object(dedicated.llm_client, "chat_completion")
    def test_llm_receives_reference_and_returns_same_output_contract(self, chat, images):
        chat.return_value = json.dumps(adaptive_plan())
        image = torch.zeros((1, 32, 24, 3))
        result = dedicated.SynVowReferenceLayerPromptGenerator().generate(
            [image], ["2"], ["keep bottle"], ["mock-model"], [42],
        )
        images.assert_called_once_with(image)
        payload = json.loads(chat.call_args.args[2])
        self.assertEqual(payload["user_direction"], "keep bottle")
        self.assertNotIn("asset_count", payload)
        self.assertEqual(json.loads(result[1])["plan_source"], "llm:mock-model")
        self.assertEqual(json.loads(result[1])["generation_prompt_config_path"], str(dedicated.GENERATION_PROMPT_PATH))
        self.assertNotIn("planner_mode", json.loads(result[1]))
        self.assertEqual(len(result), 4)
        self.assertEqual(len(result[0]), 2)
        self.assertNotIn("slots", payload)
        self.assertEqual(payload["foreground_layer_count"], 1)
        self.assertEqual(payload["background_layer_count"], 1)
        self.assertIn("not_bbox", payload["allocation_order"])
        self.assertGreater(chat.call_args.kwargs["max_tokens"], 2000)
        chat.assert_called_once()
        self.assertIn("下方第1个耳机盒", result[0][0])
        self.assertIn("人物、佩戴的耳塞", result[0][1])
        self.assertIn("完整提取本层全部目标及同组实例", result[0][1])

    def test_dynamic_groups_and_existing_consumers(self):
        for count in range(2, 7):
            items, elements = dedicated._normalize_plan(adaptive_plan(count), count)
            self.assertEqual(len(items), count)
            self.assertEqual(len(elements), count + 1)
            self.assertEqual([item["slot_id"] for item in items[1:]], ["subject_product"] * (count - 1))
            plan = json.dumps({"items": items, "layer_order_bottom_to_top": [i["key"] for i in items]})
            self.assertEqual([r["source_index"] for r in psd._parse_plan(plan, count)], list(range(count)))
            names = saver._layer_names_from_plan(plan, count)
            self.assertEqual(saver._background_layer_index(names), 0)
            for item in items:
                prompt = dedicated._compile_prompt(item, items, {"width": 500, "height": 1000, "aspect_ratio": "1:2"})
                self.assertGreaterEqual(len(prompt), 200)
                self.assertLessEqual(len(prompt), 500)
                self.assertTrue(prompt.startswith(f"[Layer: {item['slot_id']}]"))
                self.assertEqual(alpha._is_background_layer_prompt(prompt), item["slot_id"] == "background")
                self.assertIn("不裁边、不居中、不放大", prompt)
                self.assertNotIn("...", prompt)

    def test_text_below_subject_keeps_order_instead_of_fixed_slots(self):
        data = adaptive_plan(3)
        data["layers"][1].update(kind="text_logo", name="后方文字", target="位于人物后面的文字")
        items, _ = dedicated._normalize_plan(data, 3)
        records = psd._parse_plan(json.dumps({"items": items, "layer_order_bottom_to_top": [i["key"] for i in items]}), 3)
        self.assertEqual(records[1]["name"], "后方文字")
        self.assertEqual(records[2]["name"], "耳机盒2")
        prompt = dedicated._compile_prompt(items[2], items, {"width": 500, "height": 1000, "aspect_ratio": "1:2"})
        self.assertIn("明确排除其他层：后方文字", prompt)

    def test_pattern_group_union_does_not_use_bbox_as_visible_area(self):
        data = adaptive_plan(3)
        data["layers"][1].update(members=["case1", "case2"], target="两个重复图案，保持各自位置")
        data["layers"][2].update(members=["person"], target="人物及佩戴的耳塞", occlusion="")
        data["elements"][2]["bbox_normalized"] = [0, 0, .2, .4]
        data["elements"][3]["bbox_normalized"] = [.8, .6, 1, 1]
        items, _ = dedicated._normalize_plan(data, 3)
        self.assertEqual(items[1]["geometry"]["layer_bbox_normalized"], [0, 0, 1, 1])
        self.assertEqual(len(items[1]["geometry"]["regions"]), 2)
        self.assertEqual(items[1]["area_priority"], 2)
        self.assertEqual(items[2]["area_priority"], 1)
        self.assertAlmostEqual(items[1]["visible_area_ratio_estimate"], .06)
        self.assertEqual([item["key"] for item in items], ["layer_01", "layer_02", "layer_03"])
        prompt = dedicated._compile_prompt(items[1], items, {"width": 500, "height": 1000, "aspect_ratio": "1:2"})
        self.assertIn("(10,20),(90,80)", prompt)
        self.assertIn("保留间隔透明空隙", prompt)
        self.assertIn("目标遮住其他元素的可见部分也必须保留", prompt)
        self.assertIn("只不补目标被遮住或画外的部分", prompt)

    def test_prompt_budget_with_long_layer_names_and_complete_targets(self):
        data = adaptive_plan(6)
        for index, layer in enumerate(data["layers"]):
            layer["name"] = str(index) + "层" * 19
            layer["target"] = str(index) + "物" * 47
        items, _ = dedicated._normalize_plan(data, 6)
        for item in items:
            prompt = dedicated._compile_prompt(item, items, {"width": 1000, "height": 1999, "aspect_ratio": "1000:1999"})
            self.assertLessEqual(len(prompt), 500)
            self.assertIn(item["visible_content"], prompt)

    def test_budget_never_truncates_invariants_or_remove_targets(self):
        data = adaptive_plan(6)
        for i, layer in enumerate(data["layers"]):
            layer["target"] = str(i) + "中" * 47
            layer["occlusion"] = "遮" * 48
        items, _ = dedicated._normalize_plan(data, 6)
        canvas = {"width": 1000, "height": 1999, "aspect_ratio": "1000:1999"}
        for item in items:
            prompt = dedicated._compile_prompt(item, items, canvas)
            self.assertLessEqual(len(prompt), 500)
            self.assertIn("不重新排字", prompt)
            if item["slot_id"] == "background":
                for overlay in items[1:]:
                    self.assertIn(overlay["visible_content"], prompt)
                self.assertTrue(prompt.endswith("不新增场景或改黑底。"))
                self.assertIn("本层只保留：", prompt)
                self.assertNotIn("保留原文字笔画", prompt)
                self.assertIn("背景净版提取", prompt)
                self.assertIn("删除区域只能延续邻近背景", prompt)
                self.assertIn("禁止保留、重画或缩小后藏回待删除元素的任何局部及轮廓", prompt)
            else:
                self.assertTrue(prompt.endswith("只输出本层，不拼图、不画棋盘格。"))

    def test_background_template_edits_do_not_change_foreground_prompts(self):
        items, _ = dedicated._normalize_plan(adaptive_plan(4), 4)
        rules = json.loads(dedicated.GENERATION_PROMPT_PATH.read_text(encoding="utf-8"))
        altered = copy.deepcopy(rules)
        altered["background"]["finish"] = "背景测试替换指令。"
        canvas = {"width": 500, "height": 1000, "aspect_ratio": "1:2"}
        self.assertNotEqual(dedicated._compile_prompt(items[0], items, canvas, rules),
                            dedicated._compile_prompt(items[0], items, canvas, altered))
        for item in items[1:]:
            self.assertEqual(dedicated._compile_prompt(item, items, canvas, rules),
                             dedicated._compile_prompt(item, items, canvas, altered))

    def test_invalid_ownership_geometry_and_count(self):
        mutations = [
            lambda d: d["layers"][1]["members"].append("person"),
            lambda d: d["layers"][1]["members"].append("missing"),
            lambda d: d["elements"][1].update(bbox_normalized=[0, 0, float("nan"), 1]),
            lambda d: d["elements"][1].update(bbox_normalized=[1, 0, 0, 1]),
            lambda d: d["layers"][1].update(kind="background"),
            lambda d: d["layers"].pop(),
            lambda d: d["elements"][1].update(visible_area_ratio=float("nan")),
            lambda d: d["elements"][1].update(visible_area_ratio=-.01),
            lambda d: d["elements"][1].update(visible_area_ratio=1.01),
            lambda d: d["elements"][1].update(role="unknown"),
        ]
        for mutate in mutations:
            data = copy.deepcopy(adaptive_plan())
            mutate(data)
            with self.assertRaises(ValueError):
                dedicated._normalize_plan(data, 2)

    @mock.patch.object(dedicated.llm_client, "image_to_data_urls", return_value=["data:image/png;base64,test"])
    @mock.patch.object(dedicated.llm_client, "chat_completion", return_value='{"layers":[')
    def test_invalid_llm_reply_falls_back_without_another_llm_call(self, chat, _images):
        with mock.patch.object(dedicated, "_save_failed_plan", return_value="diagnostic.json"):
            result = dedicated.SynVowReferenceLayerPromptGenerator().generate(
                torch.zeros((1, 32, 24, 3)), 4, "", "mock", 0)
        plan = json.loads(result[1])
        self.assertEqual(plan["status"], "ready_fallback")
        self.assertEqual(plan["plan_source"], "legacy_fixed_fallback")
        self.assertTrue(plan["generation_allowed"])
        self.assertEqual(len(result[0]), 4)
        self.assertEqual([i["slot_id"] for i in plan["items"]],
                         ["background", "subject_product", "text_logo", "decorations"])
        self.assertIn("已回退旧固定分类", result[3])
        self.assertEqual(plan["diagnostic_path"], "diagnostic.json")
        chat.assert_called_once()
        self.assertEqual(chat.call_args.kwargs["max_attempts"], 1)

    @mock.patch.object(dedicated.llm_client, "image_to_data_urls", return_value=["data:image/png;base64,test"])
    @mock.patch.object(dedicated.llm_client, "chat_completion", side_effect=TimeoutError("timeout"))
    def test_api_failure_returns_requested_layers_and_explicit_fallback(self, chat, _images):
        result = dedicated.SynVowReferenceLayerPromptGenerator().generate(
            torch.zeros((1, 32, 24, 3)), 2, "", "mock", 0)
        self.assertEqual(len(result[0]), 2)
        self.assertEqual(json.loads(result[1])["plan_source"], "legacy_fixed_fallback")
        self.assertIn("timeout", result[3])
        chat.assert_called_once()

    def test_system_prompt_and_cache_are_independent(self):
        system = dedicated.SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        self.assertIn("Do NOT use fixed", system)
        self.assertIn("Every element belongs to exactly one layer", system)
        self.assertNotEqual(dedicated.SynVowReferenceLayerPromptGenerator.IS_CHANGED(seed=0),
                            planner.SynVowTransparentAssetPromptGenerator.IS_CHANGED(seed=0))

    def test_background_cannot_absorb_foreground_to_save_slots(self):
        data = adaptive_plan()
        data["layers"][0]["members"].append("person")
        data["layers"][1]["members"].remove("person")
        with self.assertRaisesRegex(ValueError, "背景必须独立"):
            dedicated._normalize_plan(data, 2)

    @mock.patch.object(dedicated.llm_client, "image_to_data_urls", return_value=["data:image/png;base64,test"])
    @mock.patch.object(dedicated.llm_client, "chat_completion")
    def test_area_estimate_mismatch_does_not_discard_new_plan(self, chat, _images):
        data = adaptive_plan()
        data["elements"][1]["visible_area_ratio"] = .7  # Its estimated box covers .56.
        chat.return_value = json.dumps(data)
        with mock.patch.object(planner.SynVowTransparentAssetPromptGenerator, "generate",
                               side_effect=AssertionError("must not call the old generator")):
            result = dedicated.SynVowReferenceLayerPromptGenerator().generate(
                torch.zeros((1, 32, 24, 3)), 2, "", "mock", 0)
        plan = json.loads(result[1])
        self.assertEqual(plan["plan_source"], "llm:mock")
        self.assertEqual(plan["elements"][1]["visible_area_ratio"], .7)
        self.assertEqual(plan["items"][1]["geometry"]["layer_bbox_normalized"], [])
        self.assertEqual(len(plan["planning_warnings"]), 1)
        self.assertIn("0.7000", plan["planning_warnings"][0])
        self.assertIn("0.5600", plan["planning_warnings"][0])
        self.assertIn("未回退旧模板", result[3])
        self.assertIn("原有可见像素", result[0][1])
        chat.assert_called_once()

    def test_zero_rounded_area_keeps_small_element(self):
        data = adaptive_plan()
        data["elements"][2]["visible_area_ratio"] = 0
        items, elements = dedicated._normalize_plan(data, 2)
        self.assertIn("case1", items[1]["members"])
        self.assertIn("面积估计为0", elements[2]["area_estimate_warning"])

    def test_no_empty_foreground_padding(self):
        data = adaptive_plan(3)
        data["layers"][1]["members"].extend(data["layers"][2]["members"])
        data["layers"][2].update(members=[], target="")
        with self.assertRaisesRegex(ValueError, "前景层不能为空"):
            dedicated._normalize_plan(data, 3)

    @mock.patch.object(dedicated.llm_client, "image_to_data_urls", return_value=["data:image/png;base64,test"])
    @mock.patch.object(dedicated.llm_client, "chat_completion")
    def test_area_priority_and_psd_order_are_independent(self, chat, _images):
        data = adaptive_plan(3)
        data["layers"][1], data["layers"][2] = data["layers"][2], data["layers"][1]
        chat.return_value = json.dumps(data)
        result = dedicated.SynVowReferenceLayerPromptGenerator().generate(
            torch.zeros((1, 32, 24, 3)), 3, "", "mock", 0)
        plan = json.loads(result[1])
        self.assertEqual(plan["planning_priority_large_to_small"], ["layer_03", "layer_02"])
        self.assertEqual(plan["element_priority_large_to_small"][0], "person")
        self.assertEqual(plan["layer_order_bottom_to_top"], ["layer_01", "layer_02", "layer_03"])
        self.assertEqual([r["name"] for r in psd._parse_plan(result[1], 3)],
                         [i["name"] for i in plan["items"]])

    def test_complete_inventory_across_layer_counts(self):
        elements = [
            {"id": "bg", "label": "底色", "role": "background", "visible_area_ratio": .06, "bbox_normalized": [0, 0, 1, 1]},
            {"id": "text", "label": "大标题", "role": "foreground", "visible_area_ratio": .3, "bbox_normalized": [.1, .1, .9, .5]},
            {"id": "main", "label": "主体", "role": "foreground", "visible_area_ratio": .2, "bbox_normalized": [.1, .5, .9, .9]},
            {"id": "red", "label": "全部红色饰物", "role": "foreground", "visible_area_ratio": .1, "bbox_normalized": [0, 0, 1, 1]},
            {"id": "pale", "label": "全部浅色饰物", "role": "foreground", "visible_area_ratio": .08, "bbox_normalized": [0, 0, 1, 1]},
            {"id": "stars", "label": "四角小星星", "role": "foreground", "visible_area_ratio": .005, "bbox_normalized": [0, 0, 1, 1]},
        ]
        foreground = [e["id"] for e in elements[1:]]
        for count in range(2, 7):
            # Large groups get their own slot; every remaining small element stays in the final group.
            groups = [[key] for key in foreground[:count - 2]] + [foreground[count - 2:]]
            layers = [{"name": "底色", "kind": "background", "members": ["bg"], "target": "底色"}]
            for index, members in enumerate(groups):
                layers.append({"name": f"元素组{index}", "kind": "other_reusable", "members": members,
                               "target": "、".join(e["label"] for e in elements if e["id"] in members)})
            items, inventory = dedicated._normalize_plan({"elements": elements, "layers": layers}, count)
            self.assertEqual(len(items), count)
            assigned = [key for item in items for key in item["members"]]
            self.assertCountEqual(assigned, [e["id"] for e in inventory])
            self.assertEqual(assigned.count("stars"), 1)
            self.assertTrue(all(not item["empty"] for item in items[1:]))
            if count == 3:
                self.assertEqual(items[1]["members"], ["text"])
            for item in items:
                prompt = dedicated._compile_prompt(item, items, {"width": 500, "height": 1000, "aspect_ratio": "1:2"})
                self.assertLessEqual(len(prompt), 500)

    def test_export_keeps_reference_box_but_disables_foreground_refit(self):
        items, _ = dedicated._normalize_plan(adaptive_plan(), 2)
        original_box = list(items[1]["geometry"]["layer_bbox_normalized"])
        exported = [dedicated._export_full_canvas_item(i) for i in items]
        self.assertEqual(items[1]["geometry"]["layer_bbox_normalized"], original_box)
        self.assertEqual(exported[1]["geometry"]["reference_layer_bbox_normalized"], original_box)
        self.assertIsNone(saver._planned_layer_bbox(exported[1]))
        self.assertEqual(saver._planned_layer_bbox(exported[0]), (0, 0, 1, 1))
        self.assertEqual(dedicated._export_full_canvas_item(exported[1]), exported[1])
        canvas = {"width": 64, "height": 128, "aspect_ratio": "1:2"}
        self.assertEqual(dedicated._compile_prompt(items[1], items, canvas),
                         dedicated._compile_prompt(exported[1], exported, canvas))

    def test_full_canvas_overlay_pixels_survive_existing_saver_unchanged(self):
        items, _ = dedicated._normalize_plan(adaptive_plan(), 2)
        records = [dedicated._export_full_canvas_item(i) for i in items]
        base = Image.new("RGBA", (64, 128), (20, 40, 60, 255))
        overlay = Image.new("RGBA", (64, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle((2, 3, 14, 20), fill=(200, 10, 30, 128))
        draw.rectangle((43, 90, 58, 119), fill=(10, 200, 30, 255))
        normalized, size, adjusted = saver._normalize_split_rgba_layers([base, overlay], records, 0, (64, 128))
        self.assertEqual(size, (64, 128))
        self.assertEqual(adjusted, 1)  # Only the background's existing normalization.
        self.assertEqual(normalized[1].tobytes(), overlay.tobytes())
        for image in normalized + [base, overlay]:
            image.close()

    def test_saver_recognizes_dedicated_node_without_scene_widget(self):
        prompt = {"1": {"class_type": "SynVowReferenceLayerPromptGenerator",
                        "inputs": {"layer_count": "3"}}}
        self.assertEqual(saver._infer_split_layer_names_from_prompt(prompt, 3),
                         ["背景层", "主体/人物/产品层", "文字/Logo层"])

    @mock.patch.object(dedicated.llm_client, "chat_completion")
    def test_missing_reference_does_not_raise_inside_node(self, chat):
        result = dedicated.SynVowReferenceLayerPromptGenerator().generate(None, "2", "", "mock-model", 0)
        self.assertEqual(len(result[0]), 2)
        self.assertIn("请连接参考图", result[3])
        chat.assert_not_called()

    def test_single_owner_schema_derives_all_members_without_repair(self):
        data = adaptive_plan(4)
        by_id = {e["id"]: e for e in data["elements"]}
        for index, layer in enumerate(data["layers"], 1):
            for key in layer.pop("members"):
                by_id[key]["layer_index"] = index
        snapshot = copy.deepcopy(data)
        items, elements = dedicated._normalize_plan(data, 4)
        self.assertEqual(data, snapshot)
        self.assertCountEqual([key for item in items for key in item["members"]], list(by_id))
        self.assertFalse(any(e.get("membership_repair") for e in elements))

    def test_missing_background_member_is_repaired_in_place(self):
        data = adaptive_plan(3)
        data["layers"][0]["members"] = []
        items, elements = dedicated._normalize_plan(data, 3)
        self.assertEqual(items[0]["members"], ["bg"])
        self.assertEqual(items[1]["members"], ["person", "case1"])
        self.assertEqual(elements[0]["membership_repair"]["layer_index"], 1)
        self.assertEqual(len(items), 3)

    def test_missing_foreground_member_uses_explicit_owner_and_updates_prompt(self):
        data = adaptive_plan(3)
        data["layers"][1]["members"].remove("person")
        data["layers"][1]["target"] = "下方第1个耳机盒"
        data["elements"][1]["layer_index"] = 2
        items, elements = dedicated._normalize_plan(data, 3)
        self.assertIn("person", items[1]["members"])
        self.assertIn("人物及佩戴的耳塞", items[1]["visible_content"])
        self.assertEqual(elements[1]["membership_repair"]["layer_index"], 2)
        prompt = dedicated._compile_prompt(items[1], items, {"width": 500, "height": 1000, "aspect_ratio": "1:2"})
        self.assertIn("人物及佩戴的耳塞", prompt)

    @mock.patch.object(dedicated.llm_client, "image_to_data_urls", return_value=["data:image/png;base64,test"])
    @mock.patch.object(dedicated.llm_client, "chat_completion")
    def test_ambiguous_missing_member_falls_back_with_element_name(self, chat, _images):
        data = adaptive_plan(3)
        data["layers"][1]["members"].remove("person")
        chat.return_value = json.dumps(data)
        with mock.patch.object(dedicated, "_save_failed_plan", return_value="diagnostic.json") as diagnostic:
            result = dedicated.SynVowReferenceLayerPromptGenerator().generate(
                torch.zeros((1, 32, 24, 3)), 3, "", "mock", 0)
        self.assertEqual(len(result[0]), 3)
        self.assertEqual(json.loads(result[1])["plan_source"], "legacy_fixed_fallback")
        self.assertIn("person（人物及佩戴的耳塞）", result[3])
        self.assertEqual(diagnostic.call_args.args[0], chat.return_value)
        chat.assert_called_once()

    def test_conflicting_owner_is_not_silently_reassigned(self):
        data = adaptive_plan(3)
        data["elements"][1]["layer_index"] = 3
        with self.assertRaisesRegex(ValueError, "归属冲突"):
            dedicated._normalize_plan(data, 3)

    def test_emergency_still_returns_nonempty_prompts_if_legacy_renderer_fails(self):
        with mock.patch.object(planner.SynVowTransparentAssetPromptGenerator, "generate", side_effect=RuntimeError("bad preset")):
            for count in range(2, 7):
                result = dedicated._force_continue_result(torch.zeros((1, 32, 24, 3)), count, "", "mock", "bad JSON")
                self.assertEqual(len(result[0]), count)
                self.assertTrue(all(isinstance(p, str) and 0 < len(p) <= 500 for p in result[0]))
                self.assertEqual(json.loads(result[1])["plan_source"], "forced_continue")

    def test_diagnostic_preserves_raw_response_without_request_credentials(self):
        import folder_paths
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(folder_paths, "get_output_directory", return_value=folder):
            filename = dedicated._save_failed_plan('{"elements":[]}', "mock", 4, {"width": 500}, ValueError("missing e7"))
            record = json.loads(Path(filename).read_text(encoding="utf-8"))
            self.assertEqual(record["llm_raw_response"], '{"elements":[]}')
            self.assertEqual(record["error"], "missing e7")
            self.assertNotIn("api_key", record)
