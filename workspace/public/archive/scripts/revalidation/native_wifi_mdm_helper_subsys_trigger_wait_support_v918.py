#!/usr/bin/env python3
"""V918 source/build verifier for bounded wait mdm_helper /dev/subsys_esoc0 trigger support."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v918-mdm-helper-subsys-trigger-wait-support")
LATEST_POINTER = Path("tmp/wifi/latest-v918-mdm-helper-subsys-trigger-wait-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v918-execns-helper-v151-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v918-execns-helper-v151-build/build.log")


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


def extract_function(source: str, name: str) -> str:
    marker = f"static int {name}("
    start = source.find(marker)
    if start < 0:
        return ""
    next_marker = source.find("\nstatic ", start + len(marker))
    return source[start:] if next_marker < 0 else source[start:next_marker]


def classify(source: str, build_log: str, artifact: Path) -> dict[str, Any]:
    trigger_function = extract_function(
        source,
        "run_wifi_companion_mdm_helper_runtime_subsys_trigger_capture_guarded",
    )
    wifi_focus_function = extract_function(source, "append_wifi_cnss2_focus_capture")
    checks = {
        "execns_version_v151": 'EXECNS_VERSION "a90_android_execns_probe v151"' in source,
        "mode_string": "wifi-companion-mdm-helper-runtime-subsys-trigger-capture" in source,
        "allow_flag": "--allow-mdm-helper-subsys-trigger-capture" in source,
        "config_field": "allow_mdm_helper_subsys_trigger_capture" in source,
        "predicate": "is_wifi_companion_mdm_helper_subsys_trigger_capture_mode" in source,
        "dispatch": "run_wifi_companion_mdm_helper_runtime_subsys_trigger_capture_guarded" in source,
        "function_present": bool(trigger_function),
        "per_mgr_then_mdm_helper": "per_mgr_light" in trigger_function and "/vendor/bin/mdm_helper" in trigger_function,
        "subsys_child_open": 'open("/dev/subsys_esoc0", O_RDONLY | O_NONBLOCK | O_CLOEXEC)' in source,
        "child_chroot": "subsys_trigger.child_chroot=1" in source and "chroot(paths->root)" in source,
        "no_notify_ioctl": "A90_ESOC_NOTIFY" not in trigger_function and "ESOC_NOTIFY" not in trigger_function,
        "no_boot_done_ioctl": "A90_ESOC_BOOT_DONE" not in trigger_function and "ESOC_BOOT_DONE" not in trigger_function,
        "guardrail_outputs": all(
            token in trigger_function
            for token in (
                "notify_attempted=0",
                "boot_done_attempted=0",
                "wifi_hal_start_executed=0",
                "scan_connect_linkup=0",
                "credentials=0",
                "dhcp_routing=0",
                "external_ping=0",
            )
        ),
        "corrected_upper_surfaces": (
            "wlan0" in wifi_focus_function.lower()
            and "/proc/net/qrtr" in source
            and "service_notifier" in source
        ),
        "wifi_focus_captured": "append_wifi_cnss2_focus_capture" in trigger_function,
        "bounded_gate_poll": "gate_esoc0_poll_%02d" in trigger_function and "gate_poll_count" in trigger_function,
        "trigger_helper_extract": "start_mdm_helper_subsys_trigger_child" in source,
        "reboot_required_on_unclean_trigger": "result=reboot-required" in trigger_function,
        "artifact_exists": repo_path(artifact).exists(),
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
    }
    passed = all(checks.values())
    return {
        "decision": "v918-mdm-helper-subsys-trigger-wait-support-pass" if passed else "v918-mdm-helper-subsys-trigger-wait-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v151 adds bounded wait-until-/dev/esoc-0 mdm_helper runtime-subsys-trigger capture with no Notify/BOOT_DONE spoofing"
            if passed else
            "missing source/build checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v151, then run bounded V918 wait-gated native trigger gate"
            if passed else
            "repair helper v151 wait-gate support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V918 mdm_helper Subsys Trigger Wait Support",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[key, value] for key, value in manifest["classification"]["checks"].items()]),
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
        "boot_or_partition_write": False,
        "credentials_used": False,
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
