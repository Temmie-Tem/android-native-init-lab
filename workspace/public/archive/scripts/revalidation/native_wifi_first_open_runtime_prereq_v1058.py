#!/usr/bin/env python3
"""V1058 read-only first-open runtime prerequisite classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1058-first-open-runtime-prereq")
LATEST_POINTER = Path("tmp/wifi/latest-v1058-first-open-runtime-prereq.txt")
EXPECTED_FIRMWARE_CLASS_PATH = "/vendor/firmware_mnt/image"
TOYBOX = "/cache/bin/toybox"
BUSYBOX = "/cache/bin/busybox"

FIRMWARE_DIRS = (
    "/vendor",
    "/vendor/firmware_mnt",
    "/vendor/firmware_mnt/image",
    "/vendor/firmware-modem",
    "/vendor/firmware-modem/image",
    "/firmware",
    "/firmware/image",
)
MODEM_BLOBS = (
    "/vendor/firmware_mnt/image/modem.b00",
    "/vendor/firmware_mnt/image/modem.mdt",
    "/vendor/firmware-modem/image/modem.b00",
    "/vendor/firmware-modem/image/modem.mdt",
    "/firmware/image/modem.b00",
    "/firmware/image/modem.mdt",
)
DEVICE_NODES = (
    "/dev/subsys_modem",
    "/dev/subsys_esoc0",
    "/dev/esoc-0",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def sh(command: str) -> list[str]:
    return ["run", BUSYBOX, "sh", "-c", command]


def stat_script(paths: tuple[str, ...]) -> str:
    quoted = " ".join("'" + path.replace("'", "'\\''") + "'" for path in paths)
    return (
        f"for p in {quoted}; do "
        "if [ -e \"$p\" ]; then "
        f"{TOYBOX} ls -ld \"$p\"; "
        "else echo \"missing $p\"; "
        "fi; "
        "done"
    )


def command_specs() -> list[tuple[str, list[str], float]]:
    return [
        ("version", ["version"], 20.0),
        ("selftest", ["selftest"], 20.0),
        ("netservice-status", ["netservice", "status"], 20.0),
        (
            "firmware-class-path",
            ["run", TOYBOX, "cat", "/sys/module/firmware_class/parameters/path"],
            20.0,
        ),
        ("cmdline", ["run", TOYBOX, "cat", "/proc/cmdline"], 20.0),
        (
            "mounts-filter",
            sh("cat /proc/mounts | grep -Ei 'firmware|vendor|persist|dsp|modem|efs' || true"),
            20.0,
        ),
        ("firmware-dirs", sh(stat_script(FIRMWARE_DIRS)), 20.0),
        ("modem-blobs", sh(stat_script(MODEM_BLOBS)), 20.0),
        ("device-nodes", sh(stat_script(DEVICE_NODES)), 20.0),
        (
            "msm-subsys-states",
            sh(
                "for d in /sys/bus/msm_subsys/devices/*; do "
                "[ -d \"$d\" ] || continue; "
                "n=$(cat \"$d/name\" 2>/dev/null || echo -); "
                "s=$(cat \"$d/state\" 2>/dev/null || echo -); "
                "echo \"$(basename \"$d\") name=$n state=$s\"; "
                "done"
            ),
            20.0,
        ),
        (
            "dmesg-lower-filter",
            sh(
                "dmesg 2>/dev/null | "
                "grep -Ei 'firmware_class|pil|modem|subsys|mdm|esoc|wlfw|icnss|qmi|qrtr' | "
                "tail -n 160 || true"
            ),
            30.0,
        ),
    ]


def clean_text(captures: dict[str, Any], name: str) -> str:
    capture = captures.get(name) or {}
    return strip_cmdv1_text(str(capture.get("text") or ""))


def first_nonempty_line(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line:
            return line
    return ""


def path_present(text: str, path: str) -> bool:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("missing "):
            continue
        if re.search(r"(^|\s)" + re.escape(path) + r"$", line):
            return True
    return False


def mount_present(text: str, mountpoint: str) -> bool:
    for raw_line in text.splitlines():
        fields = raw_line.split()
        if len(fields) >= 2 and fields[1] == mountpoint:
            return True
    return False


def parse_subsys_states(text: str) -> dict[str, str]:
    states: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.search(r"name=(?P<name>\\S+)\\s+state=(?P<state>\\S+)", line)
        if match:
            states[match.group("name")] = match.group("state")
    return states


def lower_markers(text: str) -> dict[str, bool]:
    patterns = {
        "pil_boot": r"pil[_ -]?boot|pil_load|pil_load_segs",
        "subsystem_get_modem": r"__subsystem_get\\(\\): modem|subsys.*modem.*count",
        "sysmon_qmi": r"sysmon-qmi|sysmon.*connection",
        "wlfw": r"wlfw|WLFW",
        "icnss": r"icnss",
        "qrtr_qmi": r"qrtr|qmi",
        "esoc": r"esoc|mdm_helper",
    }
    return {key: bool(re.search(pattern, text, re.IGNORECASE)) for key, pattern in patterns.items()}


def decide(analysis: dict[str, Any], command_ok: bool) -> tuple[str, bool, str, str]:
    if not command_ok:
        return (
            "v1058-readonly-capture-incomplete",
            False,
            "one or more read-only captures failed",
            "repair bridge/device health before continuing",
        )
    if not analysis["native_health_ok"]:
        return (
            "v1058-native-health-blocked",
            True,
            "native version/selftest/netservice health did not pass",
            "repair native health before Wi-Fi lower work",
        )
    if analysis["firmware_class_path"] != EXPECTED_FIRMWARE_CLASS_PATH:
        return (
            "v1058-firmware-class-path-gap",
            True,
            f"firmware_class.path={analysis['firmware_class_path'] or '<empty>'}",
            "restore Android-equivalent firmware_class.path before PM first-open retry",
        )
    if not analysis["global_firmware_mounts"].get("/vendor/firmware_mnt", False):
        return (
            "v1058-global-firmware-mount-gap",
            True,
            "/vendor/firmware_mnt is not mounted in the current native global namespace",
            "run a bounded firmware-mount prerequisite refresh before any PM first-open live gate",
        )
    required_blobs = (
        "/vendor/firmware_mnt/image/modem.b00",
        "/vendor/firmware_mnt/image/modem.mdt",
    )
    missing_blobs = [path for path in required_blobs if not analysis["blob_presence"].get(path, False)]
    if missing_blobs:
        return (
            "v1058-pil-blob-visibility-gap",
            True,
            "missing PIL blobs at firmware_class.path: " + ", ".join(missing_blobs),
            "repair firmware mount/blob visibility before PM first-open retry",
        )
    if analysis["lower_state_dirty"]:
        return (
            "v1058-current-boot-lower-state-dirty",
            True,
            "current boot already contains lower modem/PIL/eSoC/WLFW markers",
            "reboot or run cleanup before a clean PM first-open live gate",
        )
    return (
        "v1058-first-open-runtime-prereq-ready",
        True,
        "firmware path, mounts, blobs, and device-node visibility are ready without lower perturbation markers",
        "run the smallest Android-faithful PM first-open live gate",
    )


def analyze(captures: dict[str, Any]) -> dict[str, Any]:
    firmware_path = first_nonempty_line(clean_text(captures, "firmware-class-path"))
    mounts = clean_text(captures, "mounts-filter")
    dirs = clean_text(captures, "firmware-dirs")
    blobs = clean_text(captures, "modem-blobs")
    nodes = clean_text(captures, "device-nodes")
    subsys = clean_text(captures, "msm-subsys-states")
    dmesg = clean_text(captures, "dmesg-lower-filter")
    markers = lower_markers(dmesg)
    version_ok = captures.get("version", {}).get("ok") is True
    selftest_text = clean_text(captures, "selftest")
    netservice_text = clean_text(captures, "netservice-status")
    selftest_ok = "fail=0" in selftest_text
    netservice_ok = "tcpctl=yes" in netservice_text
    mountpoints = {
        "/vendor/firmware_mnt": mount_present(mounts, "/vendor/firmware_mnt"),
        "/vendor/firmware-modem": mount_present(mounts, "/vendor/firmware-modem"),
        "/firmware": mount_present(mounts, "/firmware"),
    }
    directory_presence = {path: path_present(dirs, path) for path in FIRMWARE_DIRS}
    blob_presence = {path: path_present(blobs, path) for path in MODEM_BLOBS}
    device_presence = {path: path_present(nodes, path) for path in DEVICE_NODES}
    states = parse_subsys_states(subsys)
    lower_state_dirty = any(
        markers[key]
        for key in ("pil_boot", "subsystem_get_modem", "sysmon_qmi", "wlfw")
    )
    return {
        "native_health_ok": version_ok and selftest_ok and netservice_ok,
        "version_ok": version_ok,
        "selftest_fail_zero": selftest_ok,
        "netservice_tcpctl_helper_ok": netservice_ok,
        "firmware_class_path": firmware_path,
        "firmware_class_path_expected": EXPECTED_FIRMWARE_CLASS_PATH,
        "firmware_class_path_ok": firmware_path == EXPECTED_FIRMWARE_CLASS_PATH,
        "global_firmware_mounts": mountpoints,
        "directory_presence": directory_presence,
        "blob_presence": blob_presence,
        "device_node_presence": device_presence,
        "subsys_states": states,
        "lower_markers": markers,
        "lower_state_dirty": lower_state_dirty,
        "guardrails": {
            "opened_modem_or_esoc_nodes": False,
            "started_daemons_or_wifi_hal": False,
            "used_credentials": False,
            "network_scan_connect_or_external_ping": False,
            "wrote_device_state": False,
            "boot_or_partition_write": False,
        },
    }


def build_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"], manifest["reason"]],
        ["firmware_class.path", analysis["firmware_class_path"], f"ok={analysis['firmware_class_path_ok']}"],
        [
            "global mounts",
            json.dumps(analysis["global_firmware_mounts"], sort_keys=True),
            "read-only /proc/mounts",
        ],
        [
            "required blobs",
            json.dumps(
                {
                    "/vendor/firmware_mnt/image/modem.b00": analysis["blob_presence"].get(
                        "/vendor/firmware_mnt/image/modem.b00"
                    ),
                    "/vendor/firmware_mnt/image/modem.mdt": analysis["blob_presence"].get(
                        "/vendor/firmware_mnt/image/modem.mdt"
                    ),
                },
                sort_keys=True,
            ),
            "stat only",
        ],
        ["device nodes", json.dumps(analysis["device_node_presence"], sort_keys=True), "stat only; no open"],
        ["lower markers", json.dumps(analysis["lower_markers"], sort_keys=True), f"dirty={analysis['lower_state_dirty']}"],
        ["next", manifest["next_step"], ""],
    ]
    return "\n".join(
        [
            "# V1058 First-Open Runtime Prerequisite Summary",
            "",
            markdown_table(["item", "value", "note"], rows),
            "",
        ]
    )


def run(args: argparse.Namespace) -> int:
    if args.command == "plan":
        print(__doc__.strip())
        print(f"out_dir={args.out_dir}")
        return 0

    run_dir = repo_path(args.out_dir)
    store = EvidenceStore(run_dir)
    captures: dict[str, Any] = {}
    for name, command, timeout in command_specs():
        capture = run_capture(args, name, command, timeout)
        captures[name] = asdict(capture)
        store.write_text(f"native/{name}.txt", capture.text or capture.error)

    command_ok = all(bool(capture.get("ok")) for capture in captures.values())
    analysis = analyze(captures)
    decision, passed, reason, next_step = decide(analysis, command_ok)
    manifest = {
        "schema": "native-wifi-first-open-runtime-prereq-v1058",
        "created_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "captures": captures,
    }
    summary = build_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(run_dir) + "\n")
    print(summary, end="")
    print(f"manifest={run_dir / 'manifest.json'}")
    print(f"decision={decision}")
    print(f"pass={passed}")
    print(f"next_step={next_step}")
    return 0 if passed else 1


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
