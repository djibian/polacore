#!/usr/bin/env python3
"""Build and validate schema-constrained Albert challenge-synthesis requests.

Transport only: no scoring, repair metadata, GitHub mutation or challenge
execution. Extracted model content is parsed and revalidated by the trusted #90
historical challenge contract before it can leave the synthesis job.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import reviewer_executable_historical as historical
except ModuleNotFoundError:  # pragma: no cover
    from scripts import reviewer_executable_historical as historical


ENDPOINT = "https://albert.api.etalab.gouv.fr/v1/chat/completions"
MODEL = "qwen3-coder-30b-A3b-instruct"
CHALLENGE_SCHEMA = {
    "type": "object",
    "properties": {
        "schema": {"type": "string", "const": historical.base.SCHEMA},
        "name": {"type": "string", "pattern": "^challenge_[a-z0-9_]{3,80}$"},
        "rationale": {"type": "string", "minLength": 20, "maxLength": historical.base.MAX_RATIONALE},
        "code": {"type": "string", "minLength": 1, "maxLength": historical.base.MAX_CODE_BYTES},
    },
    "required": ["schema", "name", "rationale", "code"],
    "additionalProperties": False,
}


def agent_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("challenge agent frontmatter is missing")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("challenge agent frontmatter is unterminated")
    body = text[end + 5 :]
    if not body.strip():
        raise ValueError("challenge agent body is empty")
    return body


def build_request(bundle: str, system_prompt: str) -> dict:
    if not bundle or len(bundle.encode("utf-8")) > 300_000:
        raise ValueError("bounded challenge bundle is empty or too large")
    if not system_prompt:
        raise ValueError("challenge system prompt is empty")
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": bundle},
        ],
        "temperature": 0.0,
        "max_completion_tokens": 4000,
        "tool_choice": "none",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "polacore_executable_challenge",
                "strict": True,
                "schema": CHALLENGE_SCHEMA,
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
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise ValueError("provider choice must be one completed stop choice")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("provider response is missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise ValueError("provider response content must be a nonempty string")
    return content


def extract_challenge(response: object) -> dict[str, str]:
    content = extract_content(response)
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("provider content is not JSON") from exc
    return historical.validate_historical_challenge(value)


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
        request = build_request(args.bundle.read_text(encoding="utf-8"), agent_body(args.agent))
        args.out.write_text(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    else:
        response = json.loads(args.response.read_text(encoding="utf-8"))
        challenge = extract_challenge(response)
        args.out.write_text(json.dumps(challenge, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
