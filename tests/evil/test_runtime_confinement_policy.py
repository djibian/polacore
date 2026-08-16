#!/usr/bin/env python3
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "security" / "runtime-confinement-profile-v0.json"


def load_profile():
    return json.loads(PROFILE_PATH.read_text())


def validate_profile(profile):
    errors = []
    rootfs = profile.get("rootfs", {})
    oci = profile.get("oci", {})
    post_ready = profile.get("post_ready", {})

    if rootfs.get("readonly") is not True:
        errors.append("rootfs must be read-only")
    if rootfs.get("durable_writable_paths") != []:
        errors.append("durable writable paths are forbidden")
    if rootfs.get("worker_owned_persistent_paths") != []:
        errors.append("worker credentials must own no persistent path")
    if rootfs.get("worker_owned_persistent_objects") is not False:
        errors.append("worker credentials must own no persistent object")
    prefixes = rootfs.get("forbidden_shadow_prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        errors.append("shadow-protected native/runtime prefixes must be explicit")

    if oci.get("allowed_mounts") != []:
        errors.append("Standard v0 permits no runtime-added mounts")
    if oci.get("hooks_allowed") is not False:
        errors.append("OCI hooks are forbidden in Standard v0")
    if oci.get("rootfs_propagation") != "private":
        errors.append("rootfs propagation must be private")
    if oci.get("no_new_privileges") is not True:
        errors.append("no_new_privileges must be required")

    if post_ready.get("path_opens") is not False:
        errors.append("path-based authority must stay closed after READY")
    if post_ready.get("file_creation") is not False:
        errors.append("file creation must stay closed after READY")
    return errors


def path_is_shadowed(destination, prefixes):
    destination = "/" + destination.lstrip("/")
    for prefix in prefixes:
        prefix = prefix.rstrip("/") or "/"
        if destination == prefix or destination.startswith(prefix + "/"):
            return True
    return False


def validate_oci_config(profile, config):
    errors = []
    root = config.get("root") or {}
    process = config.get("process") or {}
    linux = config.get("linux") or {}
    mounts = config.get("mounts") or []
    hooks = config.get("hooks")

    if root.get("readonly") is not True:
        errors.append("effective OCI rootfs is not read-only")
    if process.get("noNewPrivileges") is not True:
        errors.append("effective OCI process lacks noNewPrivileges")
    if linux.get("rootfsPropagation") != profile["oci"]["rootfs_propagation"]:
        errors.append("effective OCI rootfsPropagation differs from profile")

    if hooks:
        nonempty_hooks = any(bool(entries) for entries in hooks.values())
        if nonempty_hooks:
            errors.append("OCI lifecycle hooks are forbidden")

    allowed_mounts = profile["oci"]["allowed_mounts"]
    prefixes = profile["rootfs"]["forbidden_shadow_prefixes"]
    if allowed_mounts == [] and mounts:
        errors.append("runtime-added mounts are forbidden")
    for mount in mounts:
        destination = mount.get("destination", "")
        options = set(mount.get("options") or [])
        if path_is_shadowed(destination, prefixes):
            errors.append(f"mount shadows protected path: {destination}")
        if "rw" in options or ("ro" not in options and ("bind" in options or "rbind" in options)):
            errors.append(f"mount is not explicitly read-only: {destination}")
    return errors


def baseline_oci_config():
    return {
        "ociVersion": "1.2.0",
        "root": {"path": "rootfs", "readonly": True},
        "process": {"cwd": "/", "noNewPrivileges": True},
        "mounts": [],
        "linux": {"rootfsPropagation": "private"},
    }


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


def main():
    profile = load_profile()
    errors = validate_profile(profile)
    if errors:
        raise AssertionError("baseline profile invalid: " + "; ".join(errors))
    errors = validate_oci_config(profile, baseline_oci_config())
    if errors:
        raise AssertionError("baseline OCI config invalid: " + "; ".join(errors))
    print("PASS baseline RuntimeConfinementProfile v0 + OCI config")

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
    assert_config_rejected("shared propagation", lambda c: c["linux"].__setitem__("rootfsPropagation", "shared"))
    assert_config_rejected("createRuntime hook", lambda c: c.__setitem__("hooks", {"createRuntime": [{"path": "/evil-hook"}]}))
    assert_config_rejected("writable bind /cache", lambda c: c["mounts"].append({"destination": "/cache", "type": "bind", "source": "/host/cache", "options": ["bind", "rw"]}))
    assert_config_rejected("read-only bind shadows /app/lib", lambda c: c["mounts"].append({"destination": "/app/lib", "type": "bind", "source": "/host/lib", "options": ["bind", "ro"]}))
    assert_config_rejected("bind shadows /usr/lib", lambda c: c["mounts"].append({"destination": "/usr/lib", "type": "bind", "source": "/host/usr-lib", "options": ["bind", "ro"]}))

    print("PASS all RuntimeConfinementProfile and OCI runtime mutations rejected")


if __name__ == "__main__":
    main()
