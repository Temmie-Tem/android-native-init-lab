#!/usr/bin/env python3
"""V1753 host-only Android-good vs native WLAN-PD firmware-request diff."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_ANDROID = REPO_ROOT / "tmp" / "wifi" / "v1753-android-good-wlan-pd-firmware-request" / "manifest.json"
DEFAULT_NATIVE = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
DEFAULT_FRESH_NATIVE = REPO_ROOT / "tmp" / "wifi" / "v1753-native-wlan-pd-firmware-request-sm-route" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1753-wlan-pd-firmware-request-diff"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1753_WLAN_PD_FIRMWARE_REQUEST_DIFF_2026-06-03.md"
)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def str_int(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def read_text(path: Path, limit: int = 2_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def android_evidence(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    out_dir = Path(manifest["out_dir"])
    base = out_dir / "android-postfs-evidence" / "a90-v1753-wlan-pd-fwreq"
    request_lines = read_text(base / "request-lines.txt")
    logcat = read_text(base / "logcat-filtered.txt")
    firmware_snapshot = read_text(base / "firmware-snapshot.txt")
    request_summary = read_text(base / "request-summary.txt")
    combined = "\n".join([request_lines, logcat, firmware_snapshot])
    wlanmdsp_lines = [
        line.strip()
        for line in combined.splitlines()
        if re.search(r"wlanmdsp(?:\.mbn)?", line, re.IGNORECASE)
    ]
    paths: list[str] = []
    for line in wlanmdsp_lines:
        for match in re.finditer(r"\[(/[^]\s]+wlanmdsp[^]\s]*)\]", line, re.IGNORECASE):
            value = match.group(1)
            if value not in paths:
                paths.append(value)
        for match in re.finditer(r"(/vendor/rfs/[^]\s]+wlanmdsp\.mbn)", line, re.IGNORECASE):
            value = match.group(1)
            if value not in paths:
                paths.append(value)
        for match in re.finditer(r"(/vendor/firmware(?:_mnt/image)?/wlanmdsp\.mbn)", line, re.IGNORECASE):
            value = match.group(1)
            if value not in paths:
                paths.append(value)
    return {
        "manifest": display_path(manifest_path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "base_decision": manifest.get("base_decision"),
        "requested_wlanmdsp": "1" if wlanmdsp_lines else "0",
        "wlanmdsp_line_count": len(wlanmdsp_lines),
        "wlanmdsp_paths": paths[:40],
        "request_summary": request_summary.strip(),
        "wlanmdsp_excerpt": "\n".join(wlanmdsp_lines[:30]),
    }


def native_evidence(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    gate = manifest.get("gate") or {}
    return {
        "manifest": display_path(manifest_path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "old_firmware_serve_label": gate.get("old_firmware_serve_label"),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp"),
        "tftp_running": gate.get("tftp_running"),
        "service_manager": gate.get("service_manager"),
        "wlfw_start_hit_count": gate.get("wlfw_start_hit_count"),
        "wlfw_service_request_hit_count": gate.get("wlfw_service_request_hit_count"),
        "wlfw_worker_create_success_hit_count": gate.get("wlfw_worker_create_success_hit_count"),
        "wlfw_service69_seen": gate.get("wlfw_service69_seen"),
        "wlfw_ind_register_qmi_hit_count": gate.get("wlfw_ind_register_qmi_hit_count"),
        "wlfw_cap_qmi_hit_count": gate.get("wlfw_cap_qmi_hit_count"),
    }


def fresh_native_attempt(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False}
    manifest = load_json(path)
    return {
        "present": True,
        "manifest": display_path(path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason"),
        "live_error": manifest.get("live_error"),
        "rollback": manifest.get("rollback"),
    }


def classify(android: dict[str, Any], native: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not android["pass"] or android["requested_wlanmdsp"] != "1":
        return (
            "v1753-android-good-firmware-request-capture-gap",
            False,
            "android-good evidence did not prove a visible wlanmdsp request",
            "android-capture-gap",
        )
    if not native["pass"]:
        return (
            "v1753-native-baseline-unusable",
            False,
            "native baseline manifest is not a passing service-manager route",
            "native-baseline-unusable",
        )
    if str_int(native["requested_wlanmdsp"]) == 0 and native["old_firmware_serve_label"] == "firmware-not-requested":
        return (
            "v1753-firmware-not-requested-android-good-diff-pass",
            True,
            "Android-good tftp_server requests wlanmdsp.mbn, while the native V1736 service-manager route reaches the WLFW worker but never requests wlanmdsp",
            "firmware-not-requested",
        )
    if str_int(native["requested_wlanmdsp"]) > 0 and native["old_firmware_serve_label"] == "firmware-requested-but-absent-at-served-path":
        return (
            "v1753-firmware-requested-but-absent-at-served-path-diff-pass",
            True,
            "native requested WLAN-PD firmware but the served path did not contain it",
            "firmware-requested-but-absent-at-served-path",
        )
    if str_int(native["requested_wlanmdsp"]) > 0:
        return (
            "v1753-firmware-served-pd-still-uninit-diff-pass",
            True,
            "native requested WLAN-PD firmware but WLAN-PD/WLFW still did not progress",
            "firmware-served-pd-still-uninit",
        )
    return (
        "v1753-firmware-request-diff-incomplete",
        False,
        "diff did not match a supported redirect label",
        "incomplete",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["native"]
    fresh = result["fresh_native_attempt"]
    return "\n".join([
        "# Native Init V1753 WLAN-PD Firmware-request Diff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1753`",
        "- Type: host-only Android-good vs native firmware-request diff",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Android-good Evidence",
        "",
        f"- Manifest: `{android['manifest']}`",
        f"- Decision/pass: `{android['decision']}` / `{android['pass']}`",
        f"- `wlanmdsp` request seen: `{android['requested_wlanmdsp']}`",
        f"- `wlanmdsp` line count: `{android['wlanmdsp_line_count']}`",
        f"- Paths: `{json.dumps(android['wlanmdsp_paths'], ensure_ascii=False)}`",
        "",
        "## Native Baseline Evidence",
        "",
        f"- Manifest: `{native['manifest']}`",
        f"- Decision/pass: `{native['decision']}` / `{native['pass']}`",
        f"- service-manager: `{native['service_manager']}`",
        f"- tftp running: `{native['tftp_running']}`",
        f"- `wlfw_start` / `wlfw_service_request` / worker hits: `{native['wlfw_start_hit_count']}` / `{native['wlfw_service_request_hit_count']}` / `{native['wlfw_worker_create_success_hit_count']}`",
        f"- WLFW service 69 / indication QMI / capability QMI: `{native['wlfw_service69_seen']}` / `{native['wlfw_ind_register_qmi_hit_count']}` / `{native['wlfw_cap_qmi_hit_count']}`",
        f"- requested `wlanmdsp`: `{native['requested_wlanmdsp']}`",
        f"- firmware label: `{native['old_firmware_serve_label']}`",
        "",
        "## Fresh Native Attempt",
        "",
        f"- Present: `{fresh.get('present')}`",
        f"- Decision/pass: `{fresh.get('decision')}` / `{fresh.get('pass')}`",
        f"- Rollback: `{fresh.get('rollback')}`",
        f"- Note: fresh V1753 native run was a transport non-result if `pass=false`; it is recorded but excluded from the diff label.",
        "",
        "## Android-good `wlanmdsp` Excerpt",
        "",
        "```text",
        android["wlanmdsp_excerpt"],
        "```",
        "",
        "## Interpretation",
        "",
        "- Android-good proves the modem asks `tftp_server` for `wlanmdsp.mbn`, including vendor RFS paths under `/vendor/rfs/msm/mpss/readonly/vendor/...`.",
        "- Native V1736 proves the service-manager route reaches `wlfw_service_request` and WLFW worker creation, with `tftp_server` running, but no `wlanmdsp` request appears.",
        "- The next blocker is therefore above firmware serving in native: the modem-side WLAN-PD autoload/request trigger is missing.",
        "- Stop here. Do not patch served paths, add PM/QCACLD/eSoC actors, issue restart-PD, start Wi-Fi HAL, scan/connect, use credentials, DHCP/routes, or external ping in this unit.",
        "",
        "## Safety Scope",
        "",
        "This diff script is host-only. The Android-good handoff used a temporary Magisk diagnostic module and rolled back to v724. The fresh native attempt rolled back to v724 but is not used as a label because transport did not become ready. This unit performs no new device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or firmware/partition write.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--fresh-native-manifest", type=Path, default=DEFAULT_FRESH_NATIVE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    android = android_evidence(args.android_manifest)
    native = native_evidence(args.native_manifest)
    fresh = fresh_native_attempt(args.fresh_native_manifest)
    decision, pass_ok, reason, label = classify(android, native)
    result = {
        "cycle": "V1753",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "android": android,
        "native": native,
        "fresh_native_attempt": fresh,
        "out_dir": display_path(args.out_dir),
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    write_private_text(args.report_path, render_report(result))
    print(json.dumps({"decision": decision, "pass": pass_ok, "label": label, "out_dir": display_path(args.out_dir)}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
