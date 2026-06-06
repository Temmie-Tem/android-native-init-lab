#!/usr/bin/env python3
"""Build and audit a90_android_execns_probe before any device deployment."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v325-execns-helper-deploy-preflight")
SOURCE_PATH = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_LOCAL_ARTIFACT = Path("stage3/linux_init/helpers/a90_android_execns_probe")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")
EXPECTED_MARKER = "a90_android_execns_probe v11"
REQUIRED_STRINGS = (
    EXPECTED_MARKER,
    "property-lookup",
    "system-getprop",
    "--property-root",
    "--property-key",
)
REMOTE_TARGET = "/cache/bin/a90_android_execns_probe"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    parser.add_argument("--local-artifact", type=Path, default=DEFAULT_LOCAL_ARTIFACT)
    parser.add_argument("--build-script", type=Path, default=BUILD_SCRIPT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strings_text(path: Path) -> str:
    result = subprocess.run(
        ["strings", str(path)],
        cwd=repo_path(Path(".")),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def marker_from_strings(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("a90_android_execns_probe v"):
            return line.strip()
    return "<missing>"


def file_info(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"path": str(resolved), "present": False}
    text = strings_text(resolved)
    return {
        "path": str(resolved),
        "present": True,
        "size": resolved.stat().st_size,
        "mode": oct(resolved.stat().st_mode & 0o777),
        "sha256": sha256_file(resolved),
        "marker": marker_from_strings(text),
        "required_strings_present": {item: item in text for item in REQUIRED_STRINGS},
    }


def build_helper(args: argparse.Namespace, out_path: Path) -> tuple[int, str]:
    try:
        info = out_path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink build output: {out_path}")
    result = subprocess.run(
        ["bash", str(repo_path(args.build_script)), str(out_path)],
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.returncode, result.stdout


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    artifact = store.path("a90_android_execns_probe")
    build_rc, build_log = build_helper(args, artifact)
    store.write_text("build.log", build_log)
    source_info = file_info(args.source)
    local_info = file_info(args.local_artifact)
    built_info = file_info(Path(os.path.relpath(artifact, repo_path(Path(".")))))
    built_strings = built_info.get("required_strings_present", {}) if built_info.get("present") else {}
    built_ok = (
        build_rc == 0 and
        built_info.get("marker") == EXPECTED_MARKER and
        all(bool(built_strings.get(item)) for item in REQUIRED_STRINGS)
    )
    local_marker = str(local_info.get("marker", "<missing>"))
    if not local_info.get("present"):
        local_default_status = "missing"
    elif local_marker == EXPECTED_MARKER:
        local_default_status = "current"
    else:
        local_default_status = "stale"
    decision = "execns-helper-deploy-preflight-ready" if built_ok else "execns-helper-deploy-preflight-blocked"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": built_ok,
        "reason": "fresh helper artifact built and verified" if built_ok else "fresh helper artifact failed verification",
        "next_step": "copy built artifact to device only under explicit deploy/mutation step" if built_ok else "fix helper build before deployment",
        "host": collect_host_metadata(),
        "expected_marker": EXPECTED_MARKER,
        "required_strings": list(REQUIRED_STRINGS),
        "build_rc": build_rc,
        "source": source_info,
        "built_artifact": built_info,
        "local_default_artifact": local_info,
        "local_default_status": local_default_status,
        "deploy_target": REMOTE_TARGET,
        "manifest_hint": {
            "name": "a90_android_execns_probe",
            "path": REMOTE_TARGET,
            "role": "android-exec-namespace-probe",
            "required": "no",
            "sha256": built_info.get("sha256"),
            "mode": "0755",
            "size": built_info.get("size"),
        },
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        ["source", manifest["source"].get("present"), manifest["source"].get("marker"), manifest["source"].get("sha256"), manifest["source"].get("path")],
        ["built", manifest["built_artifact"].get("present"), manifest["built_artifact"].get("marker"), manifest["built_artifact"].get("sha256"), manifest["built_artifact"].get("path")],
        ["local-default", manifest["local_default_artifact"].get("present"), manifest["local_default_artifact"].get("marker"), manifest["local_default_artifact"].get("sha256"), manifest["local_default_artifact"].get("path")],
    ]
    string_rows = [[key, str(value)] for key, value in sorted(manifest["built_artifact"].get("required_strings_present", {}).items())]
    hint = manifest["manifest_hint"]
    manifest_line = f"{hint['name']} {hint['path']} {hint['role']} {hint['required']} {hint['sha256']} {hint['mode']} {hint['size']}"
    return "\n".join([
        "# v325 Execns Helper Deploy Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- local_default_status: `{manifest['local_default_status']}`",
        f"- deploy_target: `{manifest['deploy_target']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Files",
        "",
        markdown_table(["name", "present", "marker", "sha256", "path"], rows),
        "",
        "## Built Artifact Required Strings",
        "",
        markdown_table(["string", "present"], string_rows),
        "",
        "## Future Manifest Hint",
        "",
        f"`{manifest_line}`",
        "",
        "## Future Deploy Boundary",
        "",
        "This preflight does not copy to the device. Deploying the helper to `/cache/bin` is a separate device-mutation step.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"built_marker: {manifest['built_artifact'].get('marker')}")
    print(f"local_default_status: {manifest['local_default_status']}")
    print(f"built_artifact: {manifest['built_artifact'].get('path')}")
    print(f"deploy_target: {manifest['deploy_target']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
