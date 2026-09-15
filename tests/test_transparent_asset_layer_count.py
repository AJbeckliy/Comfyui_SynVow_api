import json
import unittest
from unittest import mock

import torch

from py.api import transparent_asset_generator as generator


class TransparentAssetLayerCountTests(unittest.TestCase):
    @mock.patch.object(generator, "fetch_models", return_value=["mock-model"])
    def test_layer_count_input_defaults_to_four(self, _fetch_models):
        layer_input = generator.SynVowTransparentAssetPromptGenerator.INPUT_TYPES()["required"]["layer_count"]
        self.assertEqual(layer_input[0], ["2", "3", "4", "5", "6"])
        self.assertEqual(layer_input[1]["default"], "4")

    def test_geometry_planner_prefers_flash_model(self):
        models = ["GM3.1-pro-2606", "GM3.5-flash-2606"]
        self.assertEqual(generator._default_planner_model(models), "GM3.5-flash-2606")

    @mock.patch.object(generator, "image_to_data_urls", return_value=["https://example.test/source.png"])
    @mock.patch.object(generator, "chat_completion")
    def test_split_auto_mode_sends_structured_geometry_to_llm(self, chat_completion, _image_to_data_urls):
        chat_completion.return_value = json.dumps({
            "source_image_description": "visible source",
            "source_canvas": {
                "width": 482,
                "height": 907,
                "aspect_ratio": "482:907",
                "coordinate_system": "normalized_top_left_origin",
            },
            "style_prompt": "",
            "slots": [
                {
                    "slot_id": "background",
                    "name": "背景层",
                    "description": "背景",
                    "prompt": "background only",
                    "geometry": {
                        "layer_bbox_normalized": [0, 0, 1, 1],
                        "center_normalized": [0.5, 0.5],
                        "size_normalized": [1, 1],
                        "touches_edges": ["left", "right", "top", "bottom"],
                        "regions": [],
                    },
                },
                {
                    "slot_id": "subject_product",
                    "name": "主体/人物/产品层",
                    "description": "主体产品",
                    "visible_content": "robot vacuum",
                    "edit_instruction": "Extract only the robot vacuum.",
                    "geometry": {
                        "layer_bbox_normalized": [0.1, 0.3, 0.9, 0.95],
                        "regions": [
                            {"label": "product", "bbox_normalized": [0.2, 0.4, 0.8, 0.8]},
                            {"label": "hand", "bbox_normalized": [0.1, 0.1, 0.7, 0.5]},
                            {"label": "person", "bbox_normalized": [0.5, 0.2, 0.8, 0.7]},
                        ],
                    },
                },
                {
                    "slot_id": "text_logo",
                    "name": "文字/Logo层",
                    "description": "文字",
                    "prompt": "text and logo only",
                    "geometry": {
                        "layer_bbox_normalized": [0.2, 0.04, 0.8, 0.24],
                        "regions": [{"label": "headline", "bbox_normalized": [0.2, 0.04, 0.8, 0.14]}],
                    },
                },
            ],
        }, ensure_ascii=False)
        reference = torch.zeros((1, 907, 482, 3), dtype=torch.float32)
        result = generator.SynVowTransparentAssetPromptGenerator().generate(
            scene_preset="参考图分层拆图",
            planner_mode="自动规划(LLM)",
            asset_count="12",
            layer_count="3",
            custom_prompt="只拆图中真实存在的内容",
            llm_model="mock-model",
            seed=1,
            product_or_reference_image=reference,
        )

        plan = json.loads(result[1])
        llm_payload = json.loads(chat_completion.call_args.args[2])
        self.assertEqual(len(result[0]), 3)
        self.assertEqual(plan["plan_source"], "llm:mock-model")
        self.assertEqual(plan["layer_count"], 3)
        self.assertIsNone(plan["asset_count"])
        self.assertEqual(llm_payload["layer_count"], 3)
        self.assertEqual(llm_payload["source_canvas"]["width"], 482)
        self.assertEqual(llm_payload["source_canvas"]["height"], 907)
        self.assertEqual(
            [slot["slot_id"] for slot in llm_payload["slots"]],
            ["background", "subject_product", "text_logo"],
        )
        self.assertNotIn("asset_count", llm_payload)
        self.assertEqual(plan["source_canvas"]["aspect_ratio"], "482:907")
        self.assertEqual(plan["items"][1]["geometry"]["regions"][0]["label"], "product")
        self.assertIn("bbox=[0.1,0.3,0.9,0.95]", result[0][1])
        self.assertIn("hand[0.1,0.1,0.7,0.5]", result[0][1])
        self.assertIn("person[0.5,0.2,0.8,0.7]", result[0][1])
        self.assertIn("Edit the input image in place.", result[0][1])
        self.assertNotIn("Reference layer split mode.", result[0][1])
        self.assertTrue(all(200 <= len(prompt) <= 500 for prompt in result[0]))
        chat_completion.assert_called_once()

    @mock.patch.object(generator, "chat_completion")
    def test_split_rule_mode_uses_layer_count_without_llm(self, chat_completion):
        result = generator.SynVowTransparentAssetPromptGenerator().generate(
            scene_preset="参考图分层拆图",
            planner_mode="规则预设(不调用LLM)",
            asset_count="12",
            layer_count="3",
            custom_prompt="",
            llm_model="mock-model",
            seed=1,
        )
        plan = json.loads(result[1])
        self.assertEqual(plan["plan_source"], "layer_preset")
        self.assertEqual([item["name"] for item in plan["items"]], ["背景层", "主体/人物/产品层", "文字/Logo层"])
        chat_completion.assert_not_called()

    def test_layer_counts_use_prefix_of_fixed_six_slots(self):
        full_names = [slot["name"] for slot in generator.LAYOUT_SPLIT_SLOTS]
        self.assertEqual(full_names, [
            "背景层",
            "主体/人物/产品层",
            "文字/Logo层",
            "装饰元素层",
            "光影氛围层",
            "其他可复用元素层",
        ])
        for count in range(2, 7):
            items = generator._layout_split_fallback_items(count)
            self.assertEqual([item["name"] for item in items], full_names[:count])

    def test_duplicate_llm_slots_cannot_duplicate_final_layers(self):
        repeated = {
            "slots": [
                {"slot_id": "text_logo", "name": "文字/Logo层", "visible_content": "headline"},
                {"slot_id": "text_logo", "name": "文字/Logo层", "visible_content": "headline"},
                {"slot_id": "text_logo", "name": "文字/Logo层", "visible_content": "headline"},
                {"slot_id": "text_logo", "name": "文字/Logo层", "visible_content": "headline"},
            ]
        }
        items = generator._normalize_layout_split_slots(repeated, 4)
        self.assertEqual(
            [item["slot_id"] for item in items],
            ["background", "subject_product", "text_logo", "decorations"],
        )
        self.assertEqual([item["name"] for item in items].count("文字/Logo层"), 1)

    def test_five_layers_separate_decoration_and_light_effects(self):
        items = generator._layout_split_fallback_items(5)
        prompts = {item["name"]: item["prompt"] for item in items}
        self.assertIn("separately requested light/atmosphere layer", prompts["装饰元素层"])
        self.assertIn("atmospheric overlay effects", prompts["光影氛围层"])


if __name__ == "__main__":
    unittest.main()
