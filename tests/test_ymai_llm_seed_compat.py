"""Regression test for prompt-node seed compatibility."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

folder_paths = types.ModuleType("folder_paths")
folder_paths.get_user_directory = lambda: "C:/temp"
sys.modules.setdefault("folder_paths", folder_paths)

server = types.ModuleType("server")
server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(send_sync=lambda *args, **kwargs: None))
sys.modules.setdefault("server", server)

comfy = types.ModuleType("comfy")
comfy_model_management = types.ModuleType("comfy.model_management")
comfy.model_management = comfy_model_management
sys.modules.setdefault("comfy", comfy)
sys.modules.setdefault("comfy.model_management", comfy_model_management)

from py.api import ymai_llm


class YmaiLlmSeedCompatibilityTests(unittest.TestCase):
    def test_chat_completion_accepts_seed_without_forwarding_it(self):
        response = {"choices": [{"message": {"content": "ok"}}]}
        with patch.object(ymai_llm, "post_chat_completion", return_value=response) as post:
            result = ymai_llm.chat_completion("model", "system", "user", seed=123)
        self.assertEqual(result, "ok")
        self.assertNotIn("seed", post.call_args.args[0])

    def test_request_limit_is_forwarded(self):
        response = {"choices": [{"message": {"content": "ok"}}]}
        with patch.object(ymai_llm, "post_chat_completion", return_value=response) as post:
            ymai_llm.chat_completion("model", "system", "user", max_attempts=1)
        self.assertEqual(post.call_args.kwargs["max_attempts"], 1)

    def test_one_attempt_does_not_repeat_transient_paid_request(self):
        response = Mock(status_code=503, text="temporary failure")
        response.json.return_value = {"message": "temporary failure"}
        with patch.object(ymai_llm.synvow_auth, "read_api_key", return_value="test-only"), patch.object(
            ymai_llm.requests, "post", return_value=response
        ) as post:
            with self.assertRaises(RuntimeError):
                ymai_llm.post_chat_completion({"model": "test"}, max_attempts=1)
        self.assertEqual(post.call_count, 1)

    def test_existing_default_retry_behavior_is_unchanged(self):
        response = Mock(status_code=503, text="temporary failure")
        response.json.return_value = {"message": "temporary failure"}
        with patch.object(ymai_llm.synvow_auth, "read_api_key", return_value="test-only"), patch.object(
            ymai_llm.requests, "post", return_value=response
        ) as post, patch.object(ymai_llm.time, "sleep"):
            with self.assertRaises(RuntimeError):
                ymai_llm.post_chat_completion({"model": "test"})
        self.assertEqual(post.call_count, ymai_llm.CHAT_MAX_RETRIES)


if __name__ == "__main__":
    unittest.main()
