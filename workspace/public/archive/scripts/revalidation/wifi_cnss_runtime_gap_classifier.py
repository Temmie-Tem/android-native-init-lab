#!/usr/bin/env python3
"""v249 no-start CNSS runtime gap classifier.

This collector refines v248's runtime gap matrix without starting cnss-daemon,
cnss_diag, Wi-Fi scan/connect/link-up, property service, or Android services.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore
from wifi_cnss_start_only_runner import DEFAULT_HELPER_SHA256, parse_cnss_start_keys

DEFAULT_OUT_DIR = Path("tmp/wifi/v249-cnss-runtime-gap-classifier")
DEFAULT_V248_MANIFEST = Path("tmp/wifi/v248-cnss-runtime-primitives-preflight/manifest.json")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"

REFERENCE_URLS = {
    "android_property_service": "https://android.googlesource.com/platform/system/core/+/refs/heads/android11-release/init/property_service.cpp",
    "bionic_system_properties": "https://android.googlesource.com/platform/bionic/+/cc9b100/libc/system_properties/system_properties.cpp",
    "linux_qrtr_kconfig": "https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/refs/heads/master/net/qrtr/Kconfig",
}

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b/vendor/bin/cnss-daemon\b.*\b(?:-n|-l)\b", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b.*\b(?:-q|-f|-t)\b", re.IGNORECASE),
    re.compile(r"--allow-cnss-start-only", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bctl\.start\b|\bclass_start\b", re.IGNORECASE),
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("version", ["version"], 10.0, True),
    ("status", ["status"], 10.0, True),
    ("bootstatus", ["bootstatus"], 10.0, False),
    ("selftest-verbose", ["selftest", "verbose"], 20.0, False),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0, True),
    ("pidof-cnss-daemon", ["run", "/cache/bin/toybox", "pidof", "cnss-daemon"], 10.0, False),
    ("cat-proc-net-protocols", ["cat", "/proc/net/protocols"], 10.0, True),
    ("cat-proc-net-unix", ["cat", "/proc/net/unix"], 10.0, False),
    ("cat-proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0, False),
    ("cat-proc-modules", ["cat", "/proc/modules"], 10.0, False),
    ("cat-proc-mounts", ["cat", "/proc/mounts"], 10.0, False),
    ("stat-dev-socket", ["stat", "/dev/socket"], 10.0, False),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0, False),
    ("stat-properties-area", ["stat", "/dev/__properties__"], 10.0, False),
    ("stat-selinux-null", ["stat", "/sys/fs/selinux/null"], 10.0, False),
    ("stat-dev-diag", ["stat", "/dev/diag"], 10.0, False),
    ("stat-dev-qrtr", ["stat", "/dev/qrtr"], 10.0, False),
    ("find-dev-qmi-qrtr-cnss", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "4", "-name", "*qmi*", "-o", "-name", "*qrtr*", "-o", "-name", "*cnss*", "-o", "-name", "*diag*"], 20.0, False),
    ("find-sys-qmi-qrtr-cnss", ["run", "/cache/bin/toybox", "find", "/sys", "-maxdepth", "7", "-name", "*qmi*", "-o", "-name", "*qrtr*", "-o", "-name", "*cnss*", "-o", "-name", "*wlan*"], 30.0, False),
    ("find-property-files", ["run", "/cache/bin/toybox", "find", "/mnt/system", "-maxdepth", "8", "-name", "*property*", "-o", "-name", "build.prop"], 30.0, False),
    ("grep-property-contexts", ["run", "/cache/bin/toybox", "grep", "-R", "-n", "-i", "-m", "120", "-E", "cnss|wlan|wifi|qcom|qca|persist\\.vendor|vendor\\.", "/mnt/system/system/etc/selinux", "/mnt/system/vendor/etc/selinux", "/mnt/system/odm/etc/selinux", "/mnt/system/product/etc/selinux"], 30.0, False),
    ("grep-init-rc-hints", ["run", "/cache/bin/toybox", "grep", "-R", "-n", "-i", "-m", "160", "-E", "cnss|wlan|wifi|qcom|qca|diag|qrtr", "/mnt/system/system/etc/init", "/mnt/system/vendor/etc/init", "/mnt/system/odm/etc/init", "/mnt/system/product/etc/init"], 30.0, False),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"missing": True, "path": str(full), "decision": "missing", "pass": False}
    data = json.loads(full.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full)
    return data


def validate_no_denied_commands(commands: tuple[tuple[str, list[str], float, bool], ...]) -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _, _ in commands)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def helper_selinux_null_noallow_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "cnss-start-only",
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-current",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--timeout-sec",
        str(args.helper_timeout_sec),
    ]


def validate_helper_command(args: argparse.Namespace) -> None:
    text = " ".join(helper_selinux_null_noallow_command(args))
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied helper pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in LIVE_COMMANDS:
        capture = run_capture(args, name, command, timeout=timeout)
        store.write_text(f"captures/{safe_name(name)}.txt", capture.text if capture.text else capture.error + "\n")
        item = capture_to_manifest(capture)
        item["required"] = required
        captures.append(item)

    helper_capture = run_capture(
        args,
        "helper-selinux-null-noallow",
        helper_selinux_null_noallow_command(args),
        timeout=args.timeout + args.helper_timeout_sec + 10.0,
    )
    store.write_text(
        "helper-selinux-null-noallow.txt",
        helper_capture.text if helper_capture.text else helper_capture.error + "\n",
    )
    helper_item = capture_to_manifest(helper_capture)
    helper_item["required"] = True
    helper_item["cnss_start"] = parse_cnss_start_keys(helper_capture.text)
    captures.append(helper_item)
    return captures


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_rc(captures: dict[str, dict[str, Any]], name: str) -> int | None:
    value = captures.get(name, {}).get("rc")
    return value if isinstance(value, int) else None


def capture_text(captures: dict[str, dict[str, Any]], name: str) -> str:
    item = captures.get(name, {})
    return strip_cmdv1_text(str(item.get("text", ""))) if item.get("text") else ""


def build_prereq_checks(v248: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "v248-prerequisite",
            "pass": bool(v248.get("pass")) and v248.get("decision") == "cnss-runtime-primitives-ready-for-live-approval",
            "expected": "cnss-runtime-primitives-ready-for-live-approval",
            "actual": v248.get("decision", "missing"),
            "path": v248.get("_manifest_path", v248.get("path", "")),
        }
    ]


def build_runtime_checks(args: argparse.Namespace, captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    helper = captures.get("helper-selinux-null-noallow", {})
    helper_text = str(helper.get("text", ""))
    helper_keys = helper.get("cnss_start", {})
    protocols = capture_text(captures, "cat-proc-net-protocols")
    checks = [
        {
            "name": "required-control-captures",
            "pass": all(capture_ok(captures, name) for name, _, _, required in LIVE_COMMANDS if required),
            "detail": "all required cmdv1 captures returned rc=0/status=ok",
        },
        {
            "name": "cnss-daemon-absent",
            "pass": capture_rc(captures, "pidof-cnss-daemon") == 1,
            "detail": "pidof cnss-daemon returns rc=1",
        },
        {
            "name": "qrtr-kernel-family",
            "pass": bool(re.search(r"^QIPCRTR\s", protocols, re.MULTILINE)),
            "detail": "QIPCRTR present in /proc/net/protocols",
        },
        {
            "name": "helper-selinux-null-noallow-namespace",
            "pass": "helper_status=namespace-ready" in helper_text,
            "detail": "helper private namespace reaches namespace-ready",
        },
        {
            "name": "helper-selinux-null-noallow-guard",
            "pass": helper_keys.get("result") == "start-only-blocked" and helper_keys.get("exec_attempted") == "0",
            "detail": json.dumps(helper_keys, sort_keys=True),
        },
        {
            "name": "helper-selinux-null-materialized",
            "pass": "context.selinux_null.exists=1" in helper_text and "context.selinux_null.type=char" in helper_text,
            "detail": "private /sys/fs/selinux/null char device is materialized by helper mode",
        },
        {
            "name": "helper-sha-recorded",
            "pass": args.helper_sha256 == DEFAULT_HELPER_SHA256,
            "detail": args.helper_sha256,
        },
    ]
    return checks


def build_gap_classification(captures: dict[str, dict[str, Any]], runtime_checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    check_pass = {item["name"]: bool(item["pass"]) for item in runtime_checks}
    prop_socket = capture_ok(captures, "stat-property-socket")
    prop_area = capture_ok(captures, "stat-properties-area")
    dev_diag = capture_ok(captures, "stat-dev-diag")
    dev_qrtr = capture_ok(captures, "stat-dev-qrtr")
    property_hints = capture_text(captures, "grep-property-contexts")
    init_hints = capture_text(captures, "grep-init-rc-hints")
    return [
        {
            "name": "property-service",
            "state": "present" if prop_socket else "missing",
            "classification": "android-init-owned-runtime-gap" if not prop_socket else "unexpected-present-review",
            "evidence": "property context hints present" if property_hints.strip() else "no property context matches captured",
            "next": "do not fake property service before a dedicated read-only property shim plan",
        },
        {
            "name": "property-area",
            "state": "present" if prop_area else "missing",
            "classification": "android-init-owned-runtime-gap" if not prop_area else "unexpected-present-review",
            "evidence": "bionic expects /dev/__properties__/property_info for serialized contexts",
            "next": "collect exact cnss property reads only if live start logs prove property failure",
        },
        {
            "name": "selinux-null",
            "state": "private-materialization-pass" if check_pass.get("helper-selinux-null-materialized") else "global-missing",
            "classification": "private-helper-compatible-no-policy-domain" if check_pass.get("helper-selinux-null-materialized") else "manual-review",
            "evidence": "helper dev-null-selinux no-allow variant reached guarded block",
            "next": "live start-only can consider dev-null-selinux mode, but SELinux domain transition is still not reproduced",
        },
        {
            "name": "qrtr",
            "state": "kernel-family-present" if check_pass.get("qrtr-kernel-family") else "kernel-family-missing",
            "classification": "userspace-nameservice-or-endpoint-gap" if check_pass.get("qrtr-kernel-family") else "live-start-blocker",
            "evidence": "/dev/qrtr present" if dev_qrtr else "/dev/qrtr absent but QIPCRTR protocol checked separately",
            "next": "before scan/connect, add no-start AF_QIPCRTR socket/nameservice probe if needed",
        },
        {
            "name": "diag",
            "state": "present" if dev_diag else "missing",
            "classification": "cnss_diag-phase2-blocker" if not dev_diag else "available-review",
            "evidence": "/dev/diag stat result",
            "next": "keep cnss_diag blocked until diag device ownership and logging policy are understood",
        },
        {
            "name": "init-rc-hints",
            "state": "present" if init_hints.strip() else "not-captured",
            "classification": "android-service-model-reference-only",
            "evidence": "init rc grep captured CNSS/Wi-Fi hints" if init_hints.strip() else "no rc hints captured from mounted paths",
            "next": "do not replay Android service manager semantics in PID1 yet",
        },
    ]


def classify(prereq_checks: list[dict[str, Any]], runtime_checks: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> tuple[bool, str, str]:
    if not all(item["pass"] for item in prereq_checks):
        return False, "cnss-runtime-gaps-blocked", "v248 prerequisite is missing or stale"
    hard_names = {
        "required-control-captures",
        "cnss-daemon-absent",
        "qrtr-kernel-family",
        "helper-selinux-null-noallow-namespace",
        "helper-selinux-null-noallow-guard",
    }
    failed_hard = [item for item in runtime_checks if item["name"] in hard_names and not item["pass"]]
    if failed_hard:
        return False, "cnss-runtime-gaps-blocked", "hard no-start runtime check failed: " + ", ".join(item["name"] for item in failed_hard)
    unexpected = [item for item in gaps if item["classification"].startswith("unexpected")]
    if unexpected:
        return False, "cnss-runtime-gaps-manual-review", "unexpected runtime primitive became present: " + ", ".join(item["name"] for item in unexpected)
    optional_failed = [item for item in runtime_checks if not item["pass"] and item["name"] not in hard_names]
    if optional_failed:
        return True, "cnss-runtime-gaps-classified", "gaps classified with optional warnings: " + ", ".join(item["name"] for item in optional_failed)
    return True, "cnss-runtime-gaps-classified", "property/SELinux/QRTR/diag gaps classified without daemon execution"


def render_summary(manifest: dict[str, Any]) -> str:
    prereq_rows = [[i["name"], "PASS" if i["pass"] else "FAIL", i["expected"], i["actual"]] for i in manifest["prerequisite_checks"]]
    runtime_rows = [[i["name"], "PASS" if i["pass"] else "FAIL", i["detail"]] for i in manifest["runtime_checks"]]
    gap_rows = [[i["name"], i["state"], i["classification"], i["next"]] for i in manifest["gap_classification"]]
    reference_rows = [[key, url] for key, url in manifest["references"].items()]
    return "".join(
        [
            "# v249 CNSS Runtime Gap Classifier\n\n",
            f"- generated: `{manifest['created']}`\n",
            f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
            f"- decision: `{manifest['decision']}`\n",
            f"- reason: `{manifest['reason']}`\n",
            "- daemon start: `not executed`\n",
            f"- output: `{manifest['out_dir']}`\n\n",
            "## Prerequisites\n\n",
            markdown_table(["check", "result", "expected", "actual"], prereq_rows),
            "\n\n## Runtime Checks\n\n",
            markdown_table(["check", "result", "detail"], runtime_rows),
            "\n\n## Gap Classification\n\n",
            markdown_table(["gap", "state", "classification", "next"], gap_rows),
            "\n\n## References\n\n",
            markdown_table(["reference", "url"], reference_rows),
            "\n\n## Guardrails\n\n",
            "- No `--allow-cnss-start-only` was passed.\n",
            "- No `cnss-daemon` or `cnss_diag` process was started.\n",
            "- No property service, Wi-Fi scan/connect/link-up/credential/DHCP/routing action was attempted.\n",
            "- Next step remains explicit operator approval or further no-start probing.\n",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v248-manifest", type=Path, default=DEFAULT_V248_MANIFEST)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-timeout-sec", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_no_denied_commands(LIVE_COMMANDS)
    validate_helper_command(args)
    store = EvidenceStore(repo_path(args.out_dir))
    v248 = load_manifest(args.v248_manifest)
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    prereq_checks = build_prereq_checks(v248)
    runtime_checks = build_runtime_checks(args, captures)
    gap_classification = build_gap_classification(captures, runtime_checks)
    pass_ok, decision, reason = classify(prereq_checks, runtime_checks, gap_classification)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "daemon_start_executed": False,
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "prerequisite_checks": prereq_checks,
        "runtime_checks": runtime_checks,
        "gap_classification": gap_classification,
        "captures": captures_list,
        "guardrails": [
            "no --allow-cnss-start-only",
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no property service emulation",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write, ICNSS bind/unbind, firmware mutation, or Android partition write",
        ],
    }
    store.write_json("live-captures.json", {"captures": captures_list})
    store.write_json("runtime-gap-classification.json", {"runtime_checks": runtime_checks, "gap_classification": gap_classification})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
