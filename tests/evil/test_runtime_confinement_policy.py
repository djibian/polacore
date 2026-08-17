#!/usr/bin/env python3
import copy
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY = ROOT / "security"
sys.path.insert(0, str(SECURITY))
from lint_runtime_config import load_json, validate_profile, validate_oci_config

PROFILE_PATH = SECURITY / "runtime-confinement-profile-v0.json"
BASELINE_CONFIG_PATH = ROOT / "tests" / "fixtures" / "oci" / "config-standard-v0.json"


def load_profile():
    return load_json(PROFILE_PATH)


def baseline_oci_config():
    return load_json(BASELINE_CONFIG_PATH)


def assert_profile_rejected(name, mutate):
    profile = load_profile()
    mutate(profile)
    errors = validate_profile(profile)
    if not errors:
        raise AssertionError(f"profile mutation unexpectedly accepted: {name}")
    print(f"PASS reject profile {name}: {', '.join(errors)}")


def assert_config_rejected(name, mutate):
    profile = load_profile()
    config = baseline_oci_config()
    mutate(config)
    errors = validate_oci_config(profile, config)
    if not errors:
        raise AssertionError(f"OCI mutation unexpectedly accepted: {name}")
    print(f"PASS reject OCI {name}: {', '.join(errors)}")


def add_mount(config, destination, options=None):
    config.setdefault("mounts", []).append({
        "destination": destination,
        "type": "bind",
        "source": "/host/evil",
        "options": options or ["bind", "ro"],
    })


def main():
    profile = load_profile()
    config = baseline_oci_config()
    errors = validate_profile(profile) + validate_oci_config(profile, config)
    if errors:
        raise AssertionError("baseline invalid: " + "; ".join(errors))
    print("PASS canonical RuntimeConfinementProfile v0 + deployment fixture")

    assert_profile_rejected("writable rootfs", lambda p: p["rootfs"].__setitem__("readonly", False))
    assert_profile_rejected("durable /tmp", lambda p: p["rootfs"].__setitem__("durable_writable_paths", ["/tmp"]))
    assert_profile_rejected("worker-owned cache", lambda p: p["rootfs"].__setitem__("worker_owned_persistent_paths", ["/cache/component-42"]))
    assert_profile_rejected("helper-owned materialization", lambda p: p["rootfs"].__setitem__("worker_owned_persistent_objects", True))
    assert_profile_rejected("post-READY opens", lambda p: p["post_ready"].__setitem__("path_opens", True))
    assert_profile_rejected("post-READY file creation", lambda p: p["post_ready"].__setitem__("file_creation", True))
    assert_profile_rejected("shared root propagation", lambda p: p["oci"].__setitem__("rootfs_propagation", "shared"))
    assert_profile_rejected("hooks enabled", lambda p: p["oci"].__setitem__("hooks_allowed", True))

    assert_config_rejected("effective writable rootfs", lambda c: c["root"].__setitem__("readonly", False))
    assert_config_rejected("missing noNewPrivileges", lambda c: c["process"].__setitem__("noNewPrivileges", False))
    for propagation in ("shared", "slave", "unbindable"):
        assert_config_rejected(f"{propagation} propagation", lambda c, p=propagation: c["linux"].__setitem__("rootfsPropagation", p))
    assert_config_rejected("createRuntime hook", lambda c: c.__setitem__("hooks", {"createRuntime": [{"path": "/evil-hook"}]}))
    assert_config_rejected("writable bind /cache", lambda c: add_mount(c, "/cache", ["bind", "rw"]))
    assert_config_rejected("read-only bind shadows /app/lib", lambda c: add_mount(c, "/app/lib"))
    assert_config_rejected("bind shadows /usr/lib", lambda c: add_mount(c, "/usr/lib"))
    assert_config_rejected("relative mount destination", lambda c: add_mount(c, "app/lib"))
    assert_config_rejected("dotdot mount destination", lambda c: add_mount(c, "/cache/../app/lib"))
    assert_config_rejected("double-slash mount destination", lambda c: add_mount(c, "/app//lib"))
    assert_config_rejected("trailing-slash mount destination", lambda c: add_mount(c, "/cache/"))

    print("PASS all mutations rejected by canonical linter implementation")


if __name__ == "__main__":
    main()
