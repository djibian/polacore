#!/usr/bin/env python3
"""Build and unwrap a schema-constrained Albert Reviewer chat request.

This module is transport-only. It does not score, repair, normalize, or reinterpret
Reviewer decisions. The returned model content is preserved byte-for-byte inside
one synthetic OpenCode-style text event so the existing deterministic Reviewer
validator remains the sole decision-contract validator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ENDPOINT = "https://albert.api.etalab.gouv.fr/v1/chat/completions"
MODEL = "mistral-small-3-2-24b-instruct-2506"
DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["READY_FOR_HUMAN", "CHANGES_REQUIRED", "BLOCKED"],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale": {"type": "string", "minLength": 20, "maxLength": 800},
    },
    "required": ["verdict", "confidence", "rationale"],
    "additionalProperties": False,
}


def agent_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("Reviewer agent frontmatter is missing")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("Reviewer agent frontmatter is unterminated")
    body = text[end + 5 :]
    if not body.strip():
        raise ValueError("Reviewer agent body is empty")
    return body


def build_request(bundle: str, system_prompt: str) -> dict:
    if not bundle:
        raise ValueError("bounded Reviewer bundle is empty")
    if not system_prompt:
        raise ValueError("Reviewer system prompt is empty")
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": bundle},
        ],
        "temperature": 0.0,
        "max_completion_tokens": 1200,
        "tool_choice": "none",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "polacore_reviewer_decision",
                "strict": True,
                "schema": DECISION_SCHEMA,
            },
        },
    }


def extract_content(response: object) -> str:
    if not isinstance(response, dict):
        raise ValueError("provider response must be a JSON object")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("provider response must contain exactly one choice")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError("provider choice must be a JSON object")
    if choice.get("finish_reason") != "stop":
        raise ValueError("provider choice must finish with stop")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("provider response is missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise ValueError("provider response message content must be a nonempty string")
    return content


def write_text_event(content: str, out: Path) -> None:
    event = {"type": "text", "part": {"text": content}}
    out.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-request")
    build.add_argument("--bundle", required=True, type=Path)
    build.add_argument("--agent", required=True, type=Path)
    build.add_argument("--out", required=True, type=Path)

    extract = sub.add_parser("extract-response")
    extract.add_argument("--response", required=True, type=Path)
    extract.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "build-request":
        request = build_request(
            args.bundle.read_text(encoding="utf-8"),
            agent_body(args.agent),
        )
        args.out.write_text(
            json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    else:
        response = json.loads(args.response.read_text(encoding="utf-8"))
        write_text_event(extract_content(response), args.out)


if __name__ == "__main__":
    main()
