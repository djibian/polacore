#!/usr/bin/env python3
"""Schema-constrained Qwen critic transport for PolaCore #65.

The critic proposes bounded falsification hypotheses only. Its output is inference,
never authority and never a merge decision. This module has no network capability;
the workflow owns the bounded Albert request.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import reviewer_provider_structured_transport as reviewer_transport

MODEL = "qwen3-coder-30b-A3b-instruct"
MAX_HYPOTHESES = 6
CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "hypotheses": {
            "type": "array",
            "maxItems": MAX_HYPOTHESES,
            "items": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["BLOCKING", "NON_BLOCKING"],
                    },
                    "location": {"type": "string", "minLength": 1, "maxLength": 160},
                    "claim": {"type": "string", "minLength": 20, "maxLength": 300},
                    "failure_mode": {
                        "type": "string",
                        "minLength": 20,
                        "maxLength": 400,
                    },
                },
                "required": ["severity", "location", "claim", "failure_mode"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["hypotheses"],
    "additionalProperties": False,
}


def build_request(bundle: str, system_prompt: str) -> dict[str, Any]:
    if not bundle:
        raise ValueError("bounded critic bundle is empty")
    if not system_prompt:
        raise ValueError("critic system prompt is empty")
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": bundle},
        ],
        "temperature": 0.0,
        "max_completion_tokens": 1800,
        "tool_choice": "none",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "polacore_reviewer_critic_hypotheses",
                "strict": True,
                "schema": CRITIC_SCHEMA,
            },
        },
    }


def _bounded_string(value: object, *, name: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if len(value) < minimum or len(value) > maximum:
        raise ValueError(f"{name} length is outside contract")
    return value


def validate_critic(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"hypotheses"}:
        raise ValueError("critic output must contain only hypotheses")
    hypotheses = value.get("hypotheses")
    if not isinstance(hypotheses, list) or len(hypotheses) > MAX_HYPOTHESES:
        raise ValueError("critic hypotheses must be a bounded array")
    normalized: list[dict[str, str]] = []
    required = {"severity", "location", "claim", "failure_mode"}
    for index, item in enumerate(hypotheses):
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError(f"hypothesis {index} has invalid keys")
        severity = item.get("severity")
        if severity not in {"BLOCKING", "NON_BLOCKING"}:
            raise ValueError(f"hypothesis {index} severity is invalid")
        normalized.append(
            {
                "severity": str(severity),
                "location": _bounded_string(
                    item.get("location"), name="location", minimum=1, maximum=160
                ),
                "claim": _bounded_string(
                    item.get("claim"), name="claim", minimum=20, maximum=300
                ),
                "failure_mode": _bounded_string(
                    item.get("failure_mode"),
                    name="failure_mode",
                    minimum=20,
                    maximum=400,
                ),
            }
        )
    return {"hypotheses": normalized}


def extract_critic(response: object) -> dict[str, Any]:
    content = reviewer_transport.extract_content(response)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("critic content is not JSON") from exc
    return validate_critic(parsed)


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
            reviewer_transport.agent_body(args.agent),
        )
        args.out.write_text(
            json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        return

    response = json.loads(args.response.read_text(encoding="utf-8"))
    critic = extract_critic(response)
    args.out.write_text(
        json.dumps(critic, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(critic, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
