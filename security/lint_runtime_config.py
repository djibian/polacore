#!/usr/bin/env python3
"""Fail-closed linter for PolaCore RuntimeConfinementProfile v0 + OCI config.json."""
import argparse
import json
import posixpath
import sys
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text())


def canonical_abs_path(value):
    if not isinstance(value, str) or not value.startswith("/"):
        raise ValueError("path must be absolute")
    normalized = posixpath.normpath(value)
    if normalized != value.rstrip("/") and not (value == "/" and normalized == "/"):
        raise ValueError("path must already be normalized")
    return normalized


def path_is_shadowed(destination, prefixes):
    try:
        destination = canonical_abs_path(destination)
    except ValueError:
        return True
    for raw_prefix in prefixes:
        try:
            prefix = canonical_abs_path(raw_prefix)
        except ValueError:
            return True
        if destination == prefix or destination.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def validate_profile(profile):
    errors = []
    rootfs = profile.get("rootfs", {})
    oci = profile.get("oci", {})
    post_ready = profile.get("post_ready", {})
    if rootfs.get("readonly") is not True: errors.append("rootfs must be read-only")
    if rootfs.get("durable_writable_paths") != []: errors.append("durable writable paths are forbidden")
    if rootfs.get("worker_owned_persistent_paths") != []: errors.append("worker credentials must own no persistent path")
    if rootfs.get("worker_owned_persistent_objects") is not False: errors.append("worker credentials must own no persistent object")
    prefixes = rootfs.get("forbidden_shadow_prefixes")
    if not isinstance(prefixes, list) or not prefixes: errors.append("shadow-protected prefixes must be explicit")
    else:
        for prefix in prefixes:
            try: canonical_abs_path(prefix)
            except ValueError: errors.append(f"invalid protected prefix: {prefix!r}")
    if oci.get("allowed_mounts") != []: errors.append("Standard v0 permits no runtime-added mounts")
    if oci.get("hooks_allowed") is not False: errors.append("OCI hooks are forbidden")
    if oci.get("rootfs_propagation") != "private": errors.append("rootfs propagation must be private")
    if oci.get("no_new_privileges") is not True: errors.append("no_new_privileges must be required")
    if post_ready.get("path_opens") is not False: errors.append("path authority must stay closed after READY")
    if post_ready.get("file_creation") is not False: errors.append("file creation must stay closed after READY")
    return errors


def validate_oci_config(profile, config):
    errors = []
    root = config.get("root") or {}
    process = config.get("process") or {}
    linux = config.get("linux") or {}
    mounts = config.get("mounts") or []
    hooks = config.get("hooks")
    if root.get("readonly") is not True: errors.append("effective OCI rootfs is not read-only")
    if process.get("noNewPrivileges") is not True: errors.append("effective OCI process lacks noNewPrivileges")
    if linux.get("rootfsPropagation") != profile["oci"]["rootfs_propagation"]: errors.append("effective OCI rootfsPropagation differs from profile")
    if hooks:
        errors.append("OCI hooks object must be absent or empty")
    if not isinstance(mounts, list):
        errors.append("OCI mounts must be an array")
        mounts = []
    if profile["oci"]["allowed_mounts"] == [] and mounts:
        errors.append("runtime-added mounts are forbidden")
    prefixes = profile["rootfs"]["forbidden_shadow_prefixes"]
    for mount in mounts:
        destination = mount.get("destination", "") if isinstance(mount, dict) else ""
        try: canonical_abs_path(destination)
        except ValueError: errors.append(f"mount destination is not canonical absolute path: {destination!r}")
        if path_is_shadowed(destination, prefixes): errors.append(f"mount shadows protected path: {destination}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="OCI runtime config.json")
    parser.add_argument("--profile", default=str(Path(__file__).with_name("runtime-confinement-profile-v0.json")))
    args = parser.parse_args()
    try:
        profile = load_json(args.profile)
        config = load_json(args.config)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr); return 2
    errors = validate_profile(profile) + validate_oci_config(profile, config)
    if errors:
        for error in errors: print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS RuntimeConfinementProfile v0 + OCI config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
