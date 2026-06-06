#!/usr/bin/env python3
"""V909 source/build verifier for mdm_helper /dev/esoc-0 stall capture support."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v909-mdm-helper-esoc-fd-stall-support")
LATEST_POINTER = Path("tmp/wifi/latest-v909-mdm-helper-esoc-fd-stall-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v909-execns-helper-v149-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v909-execns-helper-v149-build/build.log")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--build-artifact", type=Path, default=DEFAULT_BUILD_ARTIFACT)
    parser.add_argument("--build-log", type=Path, default=DEFAULT_BUILD_LOG)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.MULTILINE | re.DOTALL) is not None


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    return result.returncode, result.stdout


def classify(source: str, build_log: str, artifact: Path) -> dict[str, Any]:
    checks = {
        "execns_version_v149": 'EXECNS_VERSION "a90_android_execns_probe v149"' in source,
        "fd_match_fdinfo": has(
            source,
            r"append_proc_fd_target_match_scan.*?fdinfo_label.*?append_proc_fdinfo_compact",
        ),
        "window_stall_snapshot": "append_generic_stall_snapshot_capture(stdout_buf,\n                                                      mdm_helper->pid,\n                                                      \"mdm_helper_runtime_window\")" in source,
        "final_stall_snapshot": "append_generic_stall_snapshot_capture(stdout_buf,\n                                                  mdm_helper->pid,\n                                                  \"mdm_helper_runtime_final\")" in source,
        "runtime_mode_preserved": "wifi-companion-mdm-helper-runtime-contract-capture" in source,
        "artifact_exists": repo_path(artifact).exists(),
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
    }
    passed = all(checks.values())
    return {
        "decision": "v909-mdm-helper-esoc-fd-stall-support-pass" if passed else "v909-mdm-helper-esoc-fd-stall-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v149 adds fdinfo plus wchan/syscall/stack/status/sched stall snapshots around the mdm_helper /dev/esoc-0 boundary"
            if passed else
            "missing source/build checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v149, then rerun bounded runtime-contract capture"
            if passed else
            "repair helper v149 stall support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V909 mdm_helper eSoC FD Stall Support",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[k, v] for k, v in manifest["classification"]["checks"].items()]),
        "",
        "## Artifact",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["path", manifest["artifact"]["path"]],
                ["sha256", manifest["artifact"]["sha256"]],
                ["file", manifest["artifact"]["file_output"].strip()],
            ],
        ),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    source = read_text(args.helper_source)
    build_log = read_text(args.build_log)
    file_rc, file_output = run_host(["file", str(args.build_artifact)])
    classification = classify(source, build_log, args.build_artifact)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "helper_source": str(args.helper_source),
        "build_log": str(args.build_log),
        "classification": classification,
        "artifact": {
            "path": str(args.build_artifact),
            "exists": repo_path(args.build_artifact).exists(),
            "sha256": sha256(args.build_artifact),
            "file_rc": file_rc,
            "file_output": file_output,
        },
        "device_contact": False,
        "helper_deployment": False,
        "actor_start_executed": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
