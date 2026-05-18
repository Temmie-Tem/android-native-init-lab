#!/usr/bin/env python3
"""Collect CNSS runtime requirements before any native daemon start.

This collector is intentionally read-only with respect to Wi-Fi/CNSS runtime
state. It does not execute cnss-daemon, cnss_diag, rfkill, wpa_supplicant,
wificond, hostapd, or Android ctl.start/class_start commands.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v242-cnss-runtime-inventory")
DEFAULT_V216_MANIFEST = Path("tmp/wifi/v216-service-replay-model/manifest.json")
DEFAULT_V218_MANIFEST = Path("tmp/wifi/v218-cnss-daemon-dryrun/manifest.json")
DEFAULT_V241_MANIFEST = Path("tmp/wifi/v241-vndk-apex-alias-live-final/manifest.json")

REQUIRED_DECISIONS = {
    "v216": "replay-model-ready",
    "v241": "android-linker-vndk-apex-alias-cnss-list-pass",
}

TARGET_SERVICES = ("cnss-daemon", "cnss_diag")

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b(?:cnss-daemon|cnss_diag)\b.*\b(?:-n|-q)\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/|>\s*/proc/sys/|>\s*/config/", re.IGNORECASE),
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("version", ["version"], 10.0, True),
    ("status", ["status"], 10.0, True),
    ("bootstatus", ["bootstatus"], 10.0, False),
    ("selftest-verbose", ["selftest", "verbose"], 20.0, False),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0, True),
    ("mounts", ["mounts"], 10.0, False),
    ("logpath", ["logpath"], 10.0, False),
    ("netservice-status", ["netservice", "status"], 10.0, False),
    ("wifiinv-full", ["wifiinv", "full"], 20.0, False),
    ("wififeas-full", ["wififeas", "full"], 20.0, False),
    ("kernelinv-summary", ["kernelinv", "summary"], 20.0, False),
    ("cat-proc-mounts", ["cat", "/proc/mounts"], 10.0, False),
    ("cat-proc-net-dev", ["cat", "/proc/net/dev"], 10.0, False),
    ("cat-proc-net-wireless", ["cat", "/proc/net/wireless"], 10.0, False),
    ("cat-proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0, False),
    ("cat-firmware-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0, False),
    ("cat-icnss-uevent", ["cat", "/sys/devices/platform/soc/18800000.qcom,icnss/uevent"], 10.0, False),
    ("ls-sys-class-net", ["ls", "/sys/class/net"], 10.0, False),
    ("ls-sys-class-rfkill", ["ls", "/sys/class/rfkill"], 10.0, False),
    ("ls-sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 10.0, False),
    ("ls-icnss", ["ls", "/sys/devices/platform/soc/18800000.qcom,icnss"], 10.0, False),
    ("ls-dev", ["ls", "/dev"], 20.0, False),
    ("stat-helper", ["stat", "/cache/bin/a90_android_execns_probe"], 10.0, True),
    ("stat-real-ld-config", ["stat", "/cache/bin/a90_real_ld.config.txt"], 10.0, True),
    ("stat-real-apex-libraries", ["stat", "/cache/bin/a90_real_apex.libraries.config.txt"], 10.0, False),
    ("stat-mnt-cnss-daemon", ["stat", "/mnt/system/vendor/bin/cnss-daemon"], 10.0, False),
    ("stat-mnt-cnss-diag", ["stat", "/mnt/system/vendor/bin/cnss_diag"], 10.0, False),
    ("stat-system-cnss-daemon", ["stat", "/system/vendor/bin/cnss-daemon"], 10.0, False),
    ("stat-vendor-cnss-daemon", ["stat", "/vendor/bin/cnss-daemon"], 10.0, False),
    ("stat-system-linker64", ["stat", "/system/bin/linker64"], 10.0, False),
    ("stat-mnt-linker64", ["stat", "/mnt/system/system/bin/linker64"], 10.0, True),
    ("stat-dev-null", ["stat", "/dev/null"], 10.0, False),
    ("stat-dev-socket", ["stat", "/dev/socket"], 10.0, False),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0, False),
    ("stat-properties-area", ["stat", "/dev/__properties__"], 10.0, False),
    ("stat-dev-diag", ["stat", "/dev/diag"], 10.0, False),
    ("stat-dev-ipa", ["stat", "/dev/ipa"], 10.0, False),
    ("stat-dev-qrtr", ["stat", "/dev/qrtr"], 10.0, False),
    ("stat-dev-wlan", ["stat", "/dev/wlan"], 10.0, False),
    ("find-dev-diag", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*diag*"], 20.0, False),
    ("find-dev-qrtr", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*qrtr*"], 20.0, False),
    ("find-dev-ipa", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*ipa*"], 20.0, False),
    ("find-dev-wlan", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*wlan*"], 20.0, False),
    ("find-dev-cnss", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*cnss*"], 20.0, False),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("collect", "dry-run"), default="collect")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216_MANIFEST)
    parser.add_argument("--v218-manifest", type=Path, default=DEFAULT_V218_MANIFEST)
    parser.add_argument("--v241-manifest", type=Path, default=DEFAULT_V241_MANIFEST)
    return parser.parse_args()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def manifest_decision(manifest: dict[str, Any]) -> str:
    if manifest.get("missing"):
        return "missing"
    return str(manifest.get("decision", "unknown"))


def manifest_pass(manifest: dict[str, Any]) -> bool:
    return bool(manifest.get("pass")) and not manifest.get("missing")


def validate_no_denied_live_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _, _ in LIVE_COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"denied live command pattern present: {pattern.pattern}")


def service_from_v216(v216: dict[str, Any], name: str) -> dict[str, Any]:
    for service in v216.get("graph", {}).get("services", []):
        if isinstance(service, dict) and service.get("name") == name:
            return service
    return {"name": name, "missing": True}


def daemon_from_v218(v218: dict[str, Any], name: str) -> dict[str, Any]:
    for daemon in v218.get("daemons", []):
        if isinstance(daemon, dict) and daemon.get("name") == name:
            return daemon
    return {"name": name, "missing": True}


def build_service_requirements(v216: dict[str, Any], v218: dict[str, Any]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for name in TARGET_SERVICES:
        model = service_from_v216(v216, name)
        dryrun = daemon_from_v218(v218, name)
        requirements.append(
            {
                "name": name,
                "executable": dryrun.get("executable") or model.get("executable", ""),
                "vendor_relative_path": dryrun.get("vendor_relative_path", ""),
                "args": dryrun.get("args") or model.get("args", []),
                "user": dryrun.get("user") or model.get("user") or "system",
                "groups": dryrun.get("groups") or model.get("groups", []),
                "capabilities": dryrun.get("capabilities") or model.get("capabilities", []),
                "classes": dryrun.get("classes") or model.get("classes", []),
                "flags": dryrun.get("flags") or model.get("flags", []),
                "risk": dryrun.get("risk") or model.get("risk", ""),
                "android_state": model.get("android_state") or dryrun.get("android_state", ""),
                "android_pid": model.get("android_pid", ""),
                "android_boottime": model.get("android_boottime", ""),
                "source": model.get("source") or dryrun.get("init_source", ""),
                "evidence": model.get("evidence", []),
                "runtime_assumptions": dryrun.get("android_runtime_assumptions", []),
                "blockers": sorted(set(model.get("blockers", []) + dryrun.get("blockers", []))),
            }
        )
    return requirements


def capture_live(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    captures_dir = store.mkdir("captures")
    for name, command, timeout, required in LIVE_COMMANDS:
        capture = run_capture(args, name, command, timeout=timeout)
        text = capture.text if capture.text else capture.error + "\n"
        relative = f"captures/{safe_name(name)}.txt"
        store.write_text(relative, text)
        entry = capture_to_manifest(capture)
        entry["required"] = required
        entry["file"] = str(captures_dir / f"{safe_name(name)}.txt")
        captures.append(entry)
    return captures


def capture_by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def stripped_capture_text(captures: dict[str, dict[str, Any]], name: str) -> str:
    item = captures.get(name, {})
    return strip_cmdv1_text(str(item.get("text", ""))) if item.get("text") else ""


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def build_prerequisite_checks(manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for key, expected in REQUIRED_DECISIONS.items():
        manifest = manifests[key]
        actual = manifest_decision(manifest)
        ok = manifest_pass(manifest) and actual == expected
        checks.append(
            {
                "name": key,
                "expected_decision": expected,
                "actual_decision": actual,
                "pass": ok,
                "manifest": manifest.get("_manifest_path", manifest.get("path", "")),
                "reason": manifest.get("reason", ""),
            }
        )
    v218 = manifests["v218"]
    checks.append(
        {
            "name": "v218-service-dryrun-present",
            "expected_decision": "daemon-dryrun-partial",
            "actual_decision": manifest_decision(v218),
            "pass": not v218.get("missing") and bool(v218.get("daemons")),
            "manifest": v218.get("_manifest_path", v218.get("path", "")),
            "reason": v218.get("reason", ""),
        }
    )
    return checks


def build_runtime_checks(
    captures: dict[str, dict[str, Any]],
    service_requirements: list[dict[str, Any]],
    v241: dict[str, Any],
) -> list[dict[str, Any]]:
    required_names = [name for name, _, _, required in LIVE_COMMANDS if required]
    checks: list[dict[str, Any]] = []
    for name in required_names:
        checks.append({"name": f"live-{name}", "pass": capture_ok(captures, name), "detail": captures.get(name, {}).get("error", "")})

    version_text = stripped_capture_text(captures, "version")
    checks.append(
        {
            "name": "native-version-v159",
            "pass": "A90 Linux init 0.9.59 (v159)" in version_text,
            "detail": version_text.splitlines()[0] if version_text.splitlines() else "",
        }
    )

    daemon = next(item for item in service_requirements if item["name"] == "cnss-daemon")
    checks.append(
        {
            "name": "service-cnss-daemon-net-admin-contract",
            "pass": "NET_ADMIN" in daemon.get("capabilities", []),
            "detail": ",".join(daemon.get("capabilities", [])),
        }
    )
    checks.append(
        {
            "name": "service-cnss-daemon-group-contract",
            "pass": {"system", "inet", "net_admin", "wifi"}.issubset(set(daemon.get("groups", []))),
            "detail": ",".join(daemon.get("groups", [])),
        }
    )
    checks.append(
        {
            "name": "v241-private-vendor-cnss-linker-list",
            "pass": manifest_pass(v241) and manifest_decision(v241) == "android-linker-vndk-apex-alias-cnss-list-pass",
            "detail": manifest_decision(v241),
        }
    )
    return checks


def build_start_only_blockers(
    captures: dict[str, dict[str, Any]],
    service_requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    daemon = next(item for item in service_requirements if item["name"] == "cnss-daemon")
    diag = next(item for item in service_requirements if item["name"] == "cnss_diag")

    blockers.append(
        {
            "name": "launcher-identity-contract",
            "severity": "blocker-before-start",
            "detail": (
                f"{daemon['name']} expects user={daemon['user']} "
                f"groups={','.join(daemon.get('groups', []))} "
                f"capabilities={','.join(daemon.get('capabilities', []))}"
            ),
            "next": "implement or explicitly waive uid/gid/setgroups/capability handling in controlled native launcher",
        }
    )
    blockers.append(
        {
            "name": "selinux-service-context-not-recreated",
            "severity": "known-gap",
            "detail": "Android evidence shows vendor_wcnss_service context; native init does not reproduce Android SELinux domain transition",
            "next": "keep start-only bounded; record whether SELinux is disabled/permissive in native environment before daemon start",
        }
    )
    if not capture_ok(captures, "stat-property-socket") or not capture_ok(captures, "stat-properties-area"):
        blockers.append(
            {
                "name": "android-property-runtime-gap",
                "severity": "probable-runtime-gap",
                "detail": "/dev/socket/property_service or /dev/__properties__ is not visible in native runtime",
                "next": "treat libcutils/system-property use as a possible start-only failure mode",
            }
        )
    if not capture_ok(captures, "stat-dev-diag"):
        blockers.append(
            {
                "name": "diag-device-gap",
                "severity": "phase2-blocker",
                "detail": f"{diag['name']} expects diagnostic device/group availability; /dev/diag stat did not pass",
                "next": "do not run cnss_diag until diagnostic device availability is understood",
            }
        )
    if not capture_ok(captures, "stat-dev-qrtr"):
        blockers.append(
            {
                "name": "qrtr-device-gap",
                "severity": "runtime-risk",
                "detail": "/dev/qrtr stat did not pass; QMI/PDR style dependencies may fail if daemon expects QRTR",
                "next": "inspect cnss-daemon runtime logs only under bounded start-only runner",
            }
        )
    if not capture_ok(captures, "stat-system-cnss-daemon") or not capture_ok(captures, "stat-vendor-cnss-daemon"):
        blockers.append(
            {
                "name": "global-android-path-alias-gap",
                "severity": "expected-private-namespace-only",
                "detail": "global /system/vendor or /vendor path is not expected to be ready outside private helper namespace",
                "next": "start-only must use the private exec namespace helper, not global native root paths",
            }
        )
    return blockers


def classify(
    prerequisite_checks: list[dict[str, Any]],
    runtime_checks: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> tuple[bool, str, str]:
    if not all(item["pass"] for item in prerequisite_checks):
        return False, "cnss-runtime-inventory-prereq-gap", "required prior evidence is missing or not PASS"
    required_live = [item for item in runtime_checks if item["name"].startswith("live-")]
    if not all(item["pass"] for item in required_live):
        return False, "cnss-runtime-inventory-live-gap", "required live read-only inventory commands did not pass"
    if blockers:
        return True, "cnss-runtime-inventory-ready-for-launcher-contract-plan", "linker prerequisite is closed; remaining work is launcher/runtime contract planning"
    return True, "cnss-runtime-inventory-manual-review", "no blockers were generated, which is unexpected before a daemon start"


def write_summary(
    store: EvidenceStore,
    manifest: dict[str, Any],
    service_requirements: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> None:
    prereq_rows = [
        [item["name"], "PASS" if item["pass"] else "FAIL", item.get("actual_decision", ""), item.get("reason", "")]
        for item in manifest["prerequisite_checks"]
    ]
    runtime_rows = [
        [item["name"], "PASS" if item["pass"] else "FAIL", item.get("detail", "")]
        for item in manifest["runtime_checks"]
    ]
    service_rows = [
        [
            item["name"],
            item.get("executable", ""),
            " ".join(item.get("args", [])),
            item.get("user", ""),
            ",".join(item.get("groups", [])),
            ",".join(item.get("capabilities", [])),
        ]
        for item in service_requirements
    ]
    blocker_rows = [
        [item["name"], item["severity"], item["detail"], item["next"]]
        for item in blockers
    ]

    lines = [
        "# v242 CNSS Runtime Requirement Inventory\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- daemon start: `not executed`\n",
        f"- output: `{manifest['out_dir']}`\n\n",
        "## Prerequisites\n\n",
        markdown_table(["check", "result", "decision", "reason"], prereq_rows),
        "\n\n## Service Runtime Contract\n\n",
        markdown_table(["service", "executable", "args", "user", "groups", "capabilities"], service_rows),
        "\n\n## Live Runtime Checks\n\n",
        markdown_table(["check", "result", "detail"], runtime_rows),
        "\n\n## Start-Only Blockers\n\n",
        markdown_table(["name", "severity", "detail", "next"], blocker_rows),
        "\n\n## Interpretation\n\n",
        "- v241 closed the linker dependency blocker only inside the private helper namespace.\n",
        "- v242 keeps daemon start blocked until a launcher contract explicitly handles identity, groups, capabilities, path aliases, and expected Android runtime gaps.\n",
        "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.\n",
    ]
    store.write_text("summary.md", "".join(lines))


def run_collect(args: argparse.Namespace) -> int:
    validate_no_denied_live_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifests = {
        "v216": load_manifest(args.v216_manifest),
        "v218": load_manifest(args.v218_manifest),
        "v241": load_manifest(args.v241_manifest),
    }
    service_requirements = build_service_requirements(manifests["v216"], manifests["v218"])

    captures = [] if args.command == "dry-run" else capture_live(args, store)
    captures_by_name = capture_by_name(captures)
    prerequisite_checks = build_prerequisite_checks(manifests)
    runtime_checks = [] if args.command == "dry-run" else build_runtime_checks(captures_by_name, service_requirements, manifests["v241"])
    blockers = [] if args.command == "dry-run" else build_start_only_blockers(captures_by_name, service_requirements)
    result_pass, decision, reason = classify(
        prerequisite_checks,
        runtime_checks if runtime_checks else [{"name": "live-dry-run", "pass": True}],
        blockers if args.command != "dry-run" else [{"name": "dry-run-no-start", "severity": "not-run", "detail": "", "next": ""}],
    )

    runtime_requirements = {
        "services": service_requirements,
        "start_only_blockers": blockers,
        "guardrails": [
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill writes",
            "no ICNSS bind/unbind or sysfs writes",
            "no persistent Android partition writes",
            "private/no-follow host evidence output",
        ],
    }
    live_capture_manifest = {"captures": captures}
    manifest = {
        "created": now_iso(),
        "out_dir": str(out_dir),
        "pass": result_pass,
        "decision": decision,
        "reason": reason,
        "expect_version": args.expect_version,
        "host_metadata": collect_host_metadata(),
        "inputs": {
            key: value.get("_manifest_path", value.get("path", ""))
            for key, value in manifests.items()
        },
        "prerequisite_checks": prerequisite_checks,
        "runtime_checks": runtime_checks,
        "runtime_requirements": runtime_requirements,
        "captures": captures,
        "guardrails": runtime_requirements["guardrails"],
    }

    store.write_json("runtime-requirements.json", runtime_requirements)
    store.write_json("live-captures.json", live_capture_manifest)
    store.write_json("manifest.json", manifest)
    write_summary(store, manifest, service_requirements, blockers)

    print(f"decision: {decision}")
    print(f"pass: {result_pass}")
    print(f"out_dir: {out_dir}")
    print(f"blockers: {len(blockers)}")
    return 0 if result_pass else 1


def main() -> int:
    args = parse_args()
    return run_collect(args)


if __name__ == "__main__":
    raise SystemExit(main())
