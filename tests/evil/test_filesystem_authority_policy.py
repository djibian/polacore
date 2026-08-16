#!/usr/bin/env python3
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "security" / "runtime-filesystem-profile-v0.json"


def load_profile():
    return json.loads(PROFILE_PATH.read_text())


def validate(profile):
    errors = []
    if profile.get("root_readonly") is not True:
        errors.append("rootfs must be read-only")
    if profile.get("durable_writable_paths") != []:
        errors.append("durable writable paths are forbidden")
    if profile.get("writable_mounts") != []:
        errors.append("writable mounts are forbidden in Standard v0")
    if profile.get("worker_owned_persistent_paths") != []:
        errors.append("worker UID/GID must own no persistent path")
    if profile.get("worker_owned_persistent_objects") is not False:
        errors.append("worker credentials must own no persistent object")
    if profile.get("post_ready_path_opens") is not False:
        errors.append("path-based authority must stay closed after READY")
    if profile.get("post_ready_file_creation") is not False:
        errors.append("file creation must stay closed after READY")
    prefixes = profile.get("forbidden_shadow_prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        errors.append("native/runtime shadow prefixes must be explicit")
    return errors


def assert_rejected(name, mutate):
    profile = load_profile()
    mutate(profile)
    errors = validate(profile)
    if not errors:
        raise AssertionError(f"mutation unexpectedly accepted: {name}")
    print(f"PASS reject {name}: {', '.join(errors)}")


def main():
    baseline = load_profile()
    errors = validate(baseline)
    if errors:
        raise AssertionError("baseline invalid: " + "; ".join(errors))
    print("PASS baseline filesystem authority profile")

    assert_rejected("writable rootfs", lambda p: p.__setitem__("root_readonly", False))
    assert_rejected("durable /tmp", lambda p: p.__setitem__("durable_writable_paths", ["/tmp"]))
    assert_rejected("persistent upload staging", lambda p: p.__setitem__("durable_writable_paths", ["/var/lib/polacore/uploads-stage"]))
    assert_rejected("writable bind mount", lambda p: p.__setitem__("writable_mounts", [{"source": "/host/cache", "destination": "/cache", "options": ["rw", "bind"]}]))
    assert_rejected("worker-owned cache", lambda p: p.__setitem__("worker_owned_persistent_paths", ["/cache/component-42"]))
    assert_rejected("helper materializes persistent ownership", lambda p: p.__setitem__("worker_owned_persistent_objects", True))
    assert_rejected("post-READY opens", lambda p: p.__setitem__("post_ready_path_opens", True))
    assert_rejected("post-READY file creation", lambda p: p.__setitem__("post_ready_file_creation", True))

    print("PASS all filesystem persistence mutations rejected")


if __name__ == "__main__":
    main()
