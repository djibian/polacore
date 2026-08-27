from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import reviewer_provider_structured_transport as transport


class ReviewerProviderStructuredTransportTest(unittest.TestCase):
    def test_request_uses_exact_schema_and_no_tools(self) -> None:
        request = transport.build_request("bounded evidence", "trusted Reviewer prompt")
        self.assertEqual(request["model"], transport.MODEL)
        self.assertEqual(request["tool_choice"], "none")
        self.assertNotIn("tools", request)
        self.assertEqual(request["temperature"], 0.0)
        response_format = request["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        envelope = response_format["json_schema"]
        self.assertTrue(envelope["strict"])
        self.assertEqual(envelope["schema"], transport.DECISION_SCHEMA)
        self.assertFalse(envelope["schema"]["additionalProperties"])
        self.assertEqual(
            envelope["schema"]["required"],
            ["verdict", "confidence", "rationale"],
        )
        self.assertEqual(envelope["schema"]["properties"]["rationale"]["minLength"], 20)
        self.assertEqual(envelope["schema"]["properties"]["rationale"]["maxLength"], 800)

    def test_agent_body_excludes_frontmatter_without_rewriting_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.md"
            body = "Exact trusted body.\nSecond line.\n"
            path.write_text("---\nmodel: example\n---\n" + body, encoding="utf-8")
            self.assertEqual(transport.agent_body(path), body)

    def test_extract_preserves_model_content_verbatim(self) -> None:
        content = '```json\n{"verdict":"BLOCKED"}\n```'
        response = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": content},
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "event.jsonl"
            transport.write_text_event(transport.extract_content(response), out)
            event = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(event, {"type": "text", "part": {"text": content}})

    def test_extract_rejects_multiple_choices(self) -> None:
        response = {
            "choices": [
                {"finish_reason": "stop", "message": {"content": "a"}},
                {"finish_reason": "stop", "message": {"content": "b"}},
            ]
        }
        with self.assertRaisesRegex(ValueError, "exactly one choice"):
            transport.extract_content(response)

    def test_extract_rejects_non_stop_completion(self) -> None:
        response = {
            "choices": [
                {"finish_reason": "length", "message": {"content": "partial"}}
            ]
        }
        with self.assertRaisesRegex(ValueError, "finish with stop"):
            transport.extract_content(response)

    def test_extract_rejects_non_string_content(self) -> None:
        response = {
            "choices": [
                {"finish_reason": "stop", "message": {"content": [{"type": "text"}]}}
            ]
        }
        with self.assertRaisesRegex(ValueError, "nonempty string"):
            transport.extract_content(response)


if __name__ == "__main__":
    unittest.main()
