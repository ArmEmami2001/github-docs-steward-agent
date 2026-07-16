import json
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import agent


FACTS = {
    "repository": "owner/docs",
    "default_branch": "main",
    "primary_language": "TypeScript",
    "pushed_at": "2026-07-16T00:00:00Z",
    "description_state": "present",
    "topic_count": 4,
    "license_name": "MIT",
    "tree_files": 100,
    "documentation_files": 20,
    "markdown_files": 18,
    "other_documentation_files": 2,
    "guidance_files": 3,
    "docs_directory_files": 15,
    "open_issues": 7,
    "documentation_issues": 2,
    "release_count": 5,
    "latest_release": "v1.2.0",
    "readme_state": "present",
    "readme_size": 2048,
}


class StewardTests(unittest.TestCase):
    def test_prompt_basket_has_fifteen_unique_renderable_entries(self):
        prompts = json.loads((Path(__file__).parent / "prompts.json").read_text())
        self.assertEqual(len(prompts), 15)
        self.assertEqual(len(set(prompts)), 15)
        for prompt in prompts:
            self.assertTrue(prompt.format(**FACTS))

    @patch.dict(os.environ, {
        "TARGET_REPOSITORY": "owner/docs",
        "GITHUB_TOKEN": "github-token",
        "NOOSPHERE_CREDENTIAL": "nsc_test",
        "PROMPT_INDEX": "10",
    }, clear=True)
    @patch("agent.mcp_call")
    @patch("agent.collect_facts", return_value=FACTS)
    def test_main_connects_then_logs_one_truthful_event(self, _facts, call):
        self.assertEqual(agent.main(), 0)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(call.call_args_list[0].args[2], "connect")
        self.assertEqual(call.call_args_list[1].args[2], "log_event")
        self.assertIn("MIT", call.call_args_list[1].args[3]["description"])

    @patch("agent.time.sleep")
    @patch("agent.httpx.post")
    def test_mcp_call_retries_transient_classifier_response(self, post, _sleep):
        rejected = Mock()
        rejected.raise_for_status.return_value = None
        rejected.json.return_value = {
            "result": {"isError": True, "content": [{"text": "E_CLASSIFIER_RESPONSE"}]}
        }
        accepted = Mock()
        accepted.raise_for_status.return_value = None
        accepted.json.return_value = {"result": {"content": [{"text": "ok"}]}}
        post.side_effect = [rejected, accepted]

        result = agent.mcp_call("https://example.test/mcp/", "credential", "log_event", {"description": "work"})

        self.assertEqual(post.call_count, 2)
        self.assertFalse(result.get("isError", False))


if __name__ == "__main__":
    unittest.main()
