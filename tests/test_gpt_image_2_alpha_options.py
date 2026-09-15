import unittest
from unittest import mock

import torch

from py.api import gpt_image_2_alpha_synvow as alpha


class GptImage2AlphaBackgroundOptionTests(unittest.TestCase):
    def test_transparent_input_defaults_to_enabled(self):
        transparent_input = alpha.SynVowGptImage2Alpha_TBatch.INPUT_TYPES()["required"]["transparent"]
        self.assertEqual(transparent_input, ("BOOLEAN", {"default": True}))

    def test_background_payload_supports_transparent_and_opaque(self):
        transparent_payload = {}
        opaque_payload = {}

        alpha._apply_background_mode(transparent_payload, "gpt-image-2.5-sunburst-gf", True)
        alpha._apply_background_mode(opaque_payload, "gpt-image-2.5-sunburst-gf", False)

        self.assertEqual(transparent_payload["background"], "transparent")
        self.assertTrue(transparent_payload["transparentBackground"])
        self.assertEqual(opaque_payload["background"], "opaque")
        self.assertFalse(opaque_payload["transparentBackground"])
        self.assertEqual(transparent_payload["output_format"], "png")
        self.assertEqual(opaque_payload["output_format"], "png")

    @mock.patch.object(alpha.synvow_auth, "refresh_balance")
    @mock.patch.object(alpha.synvow_auth, "make_api_headers", return_value={"X-API-Key": "test"})
    @mock.patch.object(alpha.synvow_auth, "read_api_key", return_value="test-key")
    @mock.patch.object(alpha, "_run_tasks_with_background", return_value=["https://test/image.png"])
    def test_opaque_selection_reaches_runner(
        self,
        run_tasks,
        _read_api_key,
        _make_headers,
        _refresh_balance,
    ):
        _, status = alpha.SynVowGptImage2Alpha_TBatch().process_batch(
            model_type="PT2.5-官方",
            gpt_style="sunburst",
            quality="high",
            resolution="1K",
            aspect_ratio="1:1",
            transparent=False,
            seed=1,
            prompts_list=["test"],
        )

        self.assertFalse(run_tasks.call_args.kwargs["transparent"])
        self.assertIn("background=opaque", status)

    @mock.patch.object(alpha.synvow_auth, "refresh_balance")
    @mock.patch.object(alpha.synvow_auth, "make_api_headers", return_value={"X-API-Key": "test"})
    @mock.patch.object(alpha.synvow_auth, "read_api_key", return_value="test-key")
    @mock.patch.object(alpha, "_run_tasks_with_background", return_value=["https://test/image.png"])
    def test_auto_aspect_follows_first_reference_image(
        self,
        run_tasks,
        _read_api_key,
        _make_headers,
        _refresh_balance,
    ):
        alpha.SynVowGptImage2Alpha_TBatch().process_batch(
            model_type="PT2.5-官方",
            gpt_style="sunburst",
            quality="high",
            resolution="1K",
            aspect_ratio="auto",
            transparent=True,
            seed=1,
            prompts_list=["test"],
            image1=torch.zeros((1, 907, 482, 3)),
        )
        self.assertEqual(run_tasks.call_args.args[2], "9:16")

    @mock.patch.object(alpha.synvow_auth, "refresh_balance")
    @mock.patch.object(alpha.synvow_auth, "make_api_headers", return_value={"X-API-Key": "test"})
    @mock.patch.object(alpha.synvow_auth, "read_api_key", return_value="test-key")
    @mock.patch.object(alpha, "_run_tasks_with_background", return_value=["https://test/image.png"])
    def test_image25_auto_aspect_uses_reference_matched_custom_size(
        self,
        run_tasks,
        _read_api_key,
        _make_headers,
        _refresh_balance,
    ):
        alpha.SynVowGptImage2Alpha_TBatch().process_batch(
            model_type="PT2.5-2609",
            gpt_style="sunburst",
            quality="high",
            resolution="1K",
            aspect_ratio="auto",
            transparent=True,
            seed=1,
            prompts_list=["test"],
            image1=torch.zeros((1, 907, 482, 3)),
        )
        self.assertEqual(run_tasks.call_args.args[2], "816x1536")

    @mock.patch.object(alpha.synvow_auth, "refresh_balance")
    @mock.patch.object(alpha.synvow_auth, "make_api_headers", return_value={"X-API-Key": "test"})
    @mock.patch.object(alpha.synvow_auth, "read_api_key", return_value="test-key")
    @mock.patch.object(alpha, "_run_tasks_with_background", return_value=["https://test/bg.png", "https://test/fg.png"])
    def test_split_background_is_opaque_while_foreground_stays_transparent(
        self,
        run_tasks,
        _read_api_key,
        _make_headers,
        _refresh_balance,
    ):
        background_prompt = "Edit the input image. Return only the complete background: living room."
        foreground_prompt = "Reference image layer split request: subject.\nLayer name: 主体层"
        _, status = alpha.SynVowGptImage2Alpha_TBatch().process_batch(
            model_type="PT2.5-2609",
            gpt_style="sunburst",
            quality="high",
            resolution="1K",
            aspect_ratio="auto",
            transparent=True,
            seed=1,
            prompts_list=[background_prompt, foreground_prompt],
            image1=torch.zeros((1, 907, 482, 3)),
        )
        tasks = run_tasks.call_args.args[0]
        self.assertFalse(tasks[0][2])
        self.assertTrue(tasks[1][2])
        self.assertIn("分层背景自动不透明=1", status)

    @mock.patch.object(alpha.synvow_auth, "refresh_balance")
    @mock.patch.object(alpha.synvow_auth, "make_api_headers", return_value={"X-API-Key": "test"})
    @mock.patch.object(alpha.synvow_auth, "read_api_key", return_value="test-key")
    @mock.patch.object(alpha, "_run_tasks_with_background", return_value=[None, None, None, None])
    def test_all_failed_tasks_return_four_black_placeholder_slots(
        self,
        _run_tasks,
        _read_api_key,
        _make_headers,
        _refresh_balance,
    ):
        output, status = alpha.SynVowGptImage2Alpha_TBatch().process_batch(
            model_type="PT2.5-2609",
            gpt_style="sunburst",
            quality="high",
            resolution="1K",
            aspect_ratio="1:1",
            transparent=True,
            seed=1,
            prompts_list=["one", "two", "three", "four"],
        )
        self.assertEqual(output.splitlines(), [
            f"{alpha.BLACK_PLACEHOLDER_TOKEN}:1",
            f"{alpha.BLACK_PLACEHOLDER_TOKEN}:2",
            f"{alpha.BLACK_PLACEHOLDER_TOKEN}:3",
            f"{alpha.BLACK_PLACEHOLDER_TOKEN}:4",
        ])
        self.assertIn("失败黑图占位=4/4", status)

    @mock.patch.object(alpha.synvow_auth, "refresh_balance")
    @mock.patch.object(alpha.synvow_auth, "make_api_headers", return_value={"X-API-Key": "test"})
    @mock.patch.object(alpha.synvow_auth, "read_api_key", return_value="test-key")
    @mock.patch.object(
        alpha,
        "_run_tasks_with_background",
        return_value=["https://test/one.png", None, "https://test/three.png"],
    )
    def test_partial_failure_preserves_url_and_placeholder_order(
        self,
        _run_tasks,
        _read_api_key,
        _make_headers,
        _refresh_balance,
    ):
        output, status = alpha.SynVowGptImage2Alpha_TBatch().process_batch(
            model_type="PT2.5-2609",
            gpt_style="sunburst",
            quality="high",
            resolution="1K",
            aspect_ratio="1:1",
            transparent=True,
            seed=1,
            prompts_list=["one", "two", "three"],
        )
        self.assertEqual(output.splitlines(), [
            "https://test/one.png",
            f"{alpha.BLACK_PLACEHOLDER_TOKEN}:2",
            "https://test/three.png",
        ])
        self.assertIn("失败黑图占位=1/3", status)

    @mock.patch.object(alpha.synvow_auth, "refresh_balance")
    @mock.patch.object(alpha.synvow_auth, "make_api_headers", return_value={"X-API-Key": "test"})
    @mock.patch.object(alpha.synvow_auth, "read_api_key", return_value="test-key")
    @mock.patch.object(
        alpha,
        "_run_tasks_with_background",
        return_value=["https://test/bg.png", "https://test/subject.png", "https://test/text.png", "https://test/decor.png"],
    )
    def test_quality_split_routing_assigns_verified_models_per_slot(
        self,
        run_tasks,
        _read_api_key,
        _make_headers,
        _refresh_balance,
    ):
        prompts = [
            "[Layer: background] Edit in place.",
            "[Layer: subject_product] Edit in place.",
            "[Layer: text_logo] Edit in place.",
            "[Layer: decorations] Edit in place.",
        ]
        _, status = alpha.SynVowGptImage2Alpha_TBatch().process_batch(
            model_type="PT2.5-2609",
            gpt_style="sunburst",
            quality="medium",
            resolution="1K",
            aspect_ratio="auto",
            transparent=True,
            seed=1,
            prompts_list=prompts,
            split_routing="质量优先自动路由",
            image1=torch.zeros((1, 907, 482, 3)),
        )
        tasks = run_tasks.call_args.args[0]
        self.assertEqual(tasks[0][3]["model"], "gpt-image-2.5-sunburst-2609")
        self.assertEqual(tasks[1][3]["model"], "gpt-image-2.5-sunburst-2609")
        self.assertEqual(tasks[2][3]["model"], "gpt-image-2.5-sunburst-gf")
        self.assertEqual(tasks[2][3]["quality"], "high")
        self.assertEqual(tasks[3][3]["model"], "gpt-image-2.5-flare-2609")
        self.assertIn("质量优先分槽路由=4/4", status)

    @mock.patch.object(alpha, "_raise_if_alpha_cancelled")
    @mock.patch.object(alpha, "_sleep_interruptible")
    @mock.patch.object(alpha.comfy.utils, "ProgressBar")
    @mock.patch.object(alpha, "_build_payload", return_value={})
    @mock.patch.object(alpha, "_submit_alpha_task_with_retry", side_effect=RuntimeError("submit failed"))
    def test_submit_exceptions_become_failed_slots(
        self,
        _submit,
        _build_payload,
        _progress_bar,
        _sleep,
        _cancel_check,
    ):
        result = alpha._run_tasks_with_background(
            [("one", [], True), ("two", [], True)],
            "gpt-image-2.5-sunburst-2609",
            "1:1",
            "high",
            "1K",
            False,
            "test-key",
            {"X-API-Key": "test"},
        )
        self.assertEqual(result, [None, None])

    @mock.patch.object(alpha, "_raise_if_alpha_cancelled")
    @mock.patch.object(alpha, "_sleep_interruptible")
    @mock.patch.object(alpha.comfy.utils, "ProgressBar")
    @mock.patch.object(alpha, "_build_payload", return_value={})
    @mock.patch.object(alpha, "_submit_alpha_task_with_retry", return_value=("task-12345678", None))
    @mock.patch.object(alpha, "_poll_alpha_task", side_effect=RuntimeError("poll failed"))
    def test_poll_exceptions_become_failed_slots(
        self,
        _poll,
        _submit,
        _build_payload,
        _progress_bar,
        _sleep,
        _cancel_check,
    ):
        result = alpha._run_tasks_with_background(
            [("one", [], True)],
            "gpt-image-2.5-sunburst-2609",
            "1:1",
            "high",
            "1K",
            False,
            "test-key",
            {"X-API-Key": "test"},
        )
        self.assertEqual(result, [None])


if __name__ == "__main__":
    unittest.main()
