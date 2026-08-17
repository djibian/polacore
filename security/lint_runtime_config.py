#!/usr/bin/env python3
"""Fail-closed linter for PolaCore RuntimeConfinementProfile v0 + OCI deployment bundle."""
import argparse
import hashlib
import json
import os
import posixpath
import stat
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


def canonical_relative_path(value):
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise ValueError("path must be non-empty and relative")
    normalized = posixpath.normpath(value)
    if normalized in (".", "..") or normalized.startswith("../"):
        raise ValueError("path must stay below bundle")
    if normalized != value.rstrip("/"):
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


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_symlink_components(bundle, relative_path):
    errors = []
    current = bundle
    for part in Path(relative_path).parts:
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except OSError as exc:
            errors.append(f"rootfs component unavailable: {current}: {exc.strerror}")
            break
        if stat.S_ISLNK(mode):
            errors.append(f"rootfs component must not be a symlink: {current}")
            break
    return errors


def validate_bundle(profile, bundle_dir):
    """Validate config.json and bind it to an existing, non-symlink rootfs below bundle.

    This closes lexical/symlink escapes at validation time. It is intentionally not
    claimed to close validation->runtime TOCTOU; the launcher must later keep a
    stable handle/identity to the validated object through create/start.
    """
    errors = []
    evidence = {}
    bundle = Path(bundle_dir)
    try:
        bundle_lstat = os.lstat(bundle)
    except OSError as exc:
        return [f"bundle unavailable: {exc.strerror}"], evidence
    if stat.S_ISLNK(bundle_lstat.st_mode):
        return ["bundle path itself must not be a symlink"], evidence
    if not stat.S_ISDIR(bundle_lstat.st_mode):
        return ["bundle path must be a directory"], evidence

    config_path = bundle / "config.json"
    try:
        config_lstat = os.lstat(config_path)
    except OSError as exc:
        return [f"bundle config.json unavailable: {exc.strerror}"], evidence
    if stat.S_ISLNK(config_lstat.st_mode) or not stat.S_ISREG(config_lstat.st_mode):
        return ["bundle config.json must be a regular non-symlink file"], evidence

    try:
        config = load_json(config_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid bundle config.json: {exc}"], evidence
    errors.extend(validate_oci_config(profile, config))

    root_value = (config.get("root") or {}).get("path")
    try:
        root_rel = canonical_relative_path(root_value)
    except ValueError as exc:
        errors.append(f"OCI root.path invalid: {root_value!r}: {exc}")
        return errors, evidence

    errors.extend(_reject_symlink_components(bundle, root_rel))
    root_path = bundle / root_rel
    if errors:
        return errors, evidence
    try:
        root_lstat = os.lstat(root_path)
    except OSError as exc:
        errors.append(f"rootfs unavailable: {exc.strerror}")
        return errors, evidence
    if not stat.S_ISDIR(root_lstat.st_mode):
        errors.append("OCI root.path must identify a directory")
        return errors, evidence

    bundle_real = bundle.resolve(strict=True)
    root_real = root_path.resolve(strict=True)
    try:
        root_real.relative_to(bundle_real)
    except ValueError:
        errors.append("OCI root.path escapes bundle")
        return errors, evidence

    evidence = {
        "config_sha256": _sha256_file(config_path),
        "root_path": root_rel,
        "root_st_dev": root_lstat.st_dev,
        "root_st_ino": root_lstat.st_ino,
    }
    return errors, evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", help="OCI runtime config.json")
    parser.add_argument("--bundle", help="OCI bundle directory containing config.json and rootfs")
    parser.add_argument("--profile", default=str(Path(__file__).with_name("runtime-confinement-profile-v0.json")))
    args = parser.parse_args()
    if bool(args.config) == bool(args.bundle):
        parser.error("provide exactly one of CONFIG or --bundle BUNDLE")
    try:
        profile = load_json(args.profile)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr); return 2

    errors = validate_profile(profile)
    evidence = None
    if args.bundle:
        bundle_errors, evidence = validate_bundle(profile, args.bundle)
        errors += bundle_errors
    else:
        try:
            config = load_json(args.config)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr); return 2
        errors += validate_oci_config(profile, config)

    if errors:
        for error in errors: print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if evidence:
        print("PASS RuntimeConfinementProfile v0 + OCI bundle " + json.dumps(evidence, sort_keys=True))
    else:
        print("PASS RuntimeConfinementProfile v0 + OCI config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
