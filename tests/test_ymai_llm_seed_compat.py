"""Regression test for prompt-node seed compatibility."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


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


if __name__ == "__main__":
    unittest.main()
