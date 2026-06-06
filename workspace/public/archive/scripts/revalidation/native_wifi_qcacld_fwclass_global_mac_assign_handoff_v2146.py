#!/usr/bin/env python3
"""V2146 host-side pre-HDD MAC assignment on the known-good V2137 route."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V2146"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2146-qcacld-fwclass-global-mac-assign-handoff"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2146_QCACLD_FWCLASS_GLOBAL_MAC_ASSIGN_HANDOFF_2026-06-05.md"
)
EFS_MOUNT = "/cache/a90-mac-efs"
EFS_BLOCK = "/dev/block/a90-efs"
MAC_INFO_PATH = f"{EFS_MOUNT}/wifi/.mac.info"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def protocol_payload(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("A90P1 BEGIN ") or line.startswith("A90P1 END "):
            continue
        if line == "a90:/#" or line.startswith("a90:/#"):
            continue
        if line.startswith("run: ") or line.startswith("[exit ") or line.startswith("[done]") or line.startswith("[err]"):
            continue
        if line.startswith("linker: ") or line.startswith("WARNING: linker:"):
            continue
        lines.append(line)
    return "\n".join(lines)


def merge_step_fields(fields: dict[str, str], result: dict[str, Any]) -> None:
    fields.update(base.parse_key_values(str(result.get("stdout") or "")))


def append_redacted_step(store: base.EvidenceStore,
                         steps: list[dict[str, Any]],
                         name: str,
                         result: dict[str, Any],
                         command: list[str],
                         stdout: str,
                         stderr: str = "") -> None:
    stdout_file = f"{name}.stdout.txt"
    stderr_file = f"{name}.stderr.txt"
    store.write_text(stdout_file, stdout)
    store.write_text(stderr_file, stderr)
    steps.append({
        "name": name,
        "command": command,
        "started": result.get("started", base.now_iso()),
        "ended": result.get("ended", base.now_iso()),
        "timeout": result.get("timeout", False),
        "rc": result.get("rc"),
        "ok": result.get("ok"),
        "stdout_file": stdout_file,
        "stderr_file": stderr_file,
    })


def post_flash_mac_assign(store: base.EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, str] = {
        "mac_assign.begin": "1",
        "mac_assign.mode": "global-readonly-efs-to-real-icnss-sysfs-before-hdd",
        "mac_assign.no_efs_write": "1",
        "mac_assign.no_wifi_hal": "1",
        "mac_assign.scan_connect": "0",
        "mac_assign.credentials": "0",
        "mac_assign.dhcp_routing": "0",
        "mac_assign.external_ping": "0",
        "mac_assign.source.raw_mac_logged": "0",
        "mac_assign.write_format": "colon-hex",
    }

    def step(name: str,
             command: list[str],
             *,
             timeout: float = 60.0,
             bridge_timeout: float = 45.0) -> dict[str, Any]:
        result = base.a90ctl_step(
            store,
            steps,
            name,
            command,
            timeout=timeout,
            bridge_timeout=bridge_timeout,
        )
        merge_step_fields(fields, result)
        return result

    step("mac-assign-begin", ["run", "/cache/bin/busybox", "echo", "mac_assign.begin=1"])
    step("mac-assign-mkdir-dev-block", ["run", "/cache/bin/busybox", "mkdir", "-p", "/dev/block"])
    step("mac-assign-mkdir-efs", ["run", "/cache/bin/busybox", "mkdir", "-p", EFS_MOUNT])

    efs_uevent_script = "for f in /sys/class/block/*/uevent;do if grep -q '^PARTNAME=efs$' $f;then cat $f;exit 0;fi;done;exit 1"
    efs_uevent = step(
        "mac-assign-efs-uevent",
        ["run", "/cache/bin/busybox", "sh", "-c", efs_uevent_script],
    )
    efs_payload = protocol_payload(str(efs_uevent.get("stdout") or ""))
    major = re.search(r"(?m)^MAJOR=(\d+)$", efs_payload)
    minor = re.search(r"(?m)^MINOR=(\d+)$", efs_payload)
    devname = re.search(r"(?m)^DEVNAME=([A-Za-z0-9_.+-]+)$", efs_payload)
    fields["mac_assign.efs_partition.found"] = "1" if major and minor and devname else "0"
    fields["mac_assign.efs_partition.devname"] = devname.group(1) if devname else ""
    if major and minor:
        step("mac-assign-efs-block-rm", ["run", "/cache/bin/busybox", "rm", "-f", EFS_BLOCK])
        step(
            "mac-assign-efs-block-mknod",
            ["run", "/cache/bin/busybox", "mknod", EFS_BLOCK, "b", major.group(1), minor.group(1)],
        )

    mount_result = step(
        "mac-assign-efs-ro-mount",
        [
            "run",
            "/cache/bin/busybox",
            "mount",
            "-t",
            "ext4",
            "-o",
            "ro,noload,nosuid,nodev,noexec",
            EFS_BLOCK,
            EFS_MOUNT,
        ],
        timeout=90,
        bridge_timeout=60,
    )
    fields["mac_assign.efs_mount_rc"] = str(mount_result.get("rc"))
    mounted_result = step(
        "mac-assign-efs-mounted-check",
        ["run", "/cache/bin/busybox", "grep", EFS_MOUNT, "/proc/mounts"],
    )
    fields["mac_assign.efs_mounted"] = "1" if mounted_result.get("rc") == 0 else "0"

    source_test = step(
        "mac-assign-source-readable-test",
        ["run", "/cache/bin/busybox", "test", "-r", MAC_INFO_PATH],
    )
    fields["mac_assign.source.exists"] = "1" if source_test.get("rc") == 0 else "0"
    source_wc = step(
        "mac-assign-source-wc",
        ["run", "/cache/bin/busybox", "wc", "-c", MAC_INFO_PATH],
    )
    wc_match = re.search(r"(?m)^(\d+)\s+", protocol_payload(str(source_wc.get("stdout") or "")))
    fields["mac_assign.source.bytes"] = wc_match.group(1) if wc_match else "0"

    raw_result = base.run_command(
        base.a90ctl_command(
            ["cat", MAC_INFO_PATH],
            timeout=30,
        ),
        timeout=45,
    )
    raw_mac = protocol_payload(str(raw_result.get("stdout") or "")).replace("\r", "").replace("\n", "").strip()
    hex_digits = "".join(re.findall(r"[0-9A-Fa-f]", raw_mac))
    source_colon_hex = bool(re.fullmatch(r"[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}", raw_mac))
    source_ok = source_colon_hex or len(hex_digits) == 12
    fields["mac_assign.source.hex_digits"] = str(len(hex_digits))
    if source_colon_hex:
        fields["mac_assign.source.shape"] = "colon_hex"
    elif len(hex_digits) == 12:
        fields["mac_assign.source.shape"] = "twelve_hex_normalized"
    else:
        fields["mac_assign.source.shape"] = "missing" if not raw_mac else "invalid"
    normalized_mac = ":".join(hex_digits[index:index + 2] for index in range(0, 12, 2))

    target_exists = step(
        "mac-assign-target-exists-test",
        ["run", "/cache/bin/busybox", "test", "-e", "/sys/wifi/mac_addr"],
    )
    fields["mac_assign.target.exists"] = "1" if target_exists.get("rc") == 0 else "0"
    target_writable = step(
        "mac-assign-target-writable-test",
        ["run", "/cache/bin/busybox", "test", "-w", "/sys/wifi/mac_addr"],
    )
    fields["mac_assign.target.writable"] = "1" if target_writable.get("rc") == 0 else "0"
    step("mac-assign-target-stat", ["run", "/cache/bin/busybox", "stat", "/sys/wifi/mac_addr"])

    write_result: dict[str, Any]
    if source_ok and target_writable.get("rc") == 0:
        write_result = base.run_command(
            base.a90ctl_command(
                ["writefile", "/sys/wifi/mac_addr", normalized_mac],
                timeout=30,
            ),
            timeout=45,
        )
        fields["mac_assign.write_rc"] = str(write_result.get("rc"))
        fields["mac_assign.write_value_len"] = "17"
        append_redacted_step(
            store,
            steps,
            "mac-assign-write-sysfs",
            write_result,
            ["writefile", "/sys/wifi/mac_addr", "<redacted-colon-hex-mac>"],
            (
                f"mac_assign.write_rc={write_result.get('rc')}\n"
                "mac_assign.write_value_len=17\n"
                "mac_assign.write_raw_mac_logged=0\n"
            ),
            str(write_result.get("stderr") or ""),
        )
    else:
        fields["mac_assign.write_rc"] = "98" if not source_ok else "97"
        fields["mac_assign.write_value_len"] = "0"
        write_result = {
            "ok": False,
            "rc": base.intish(fields["mac_assign.write_rc"]),
            "stdout": "",
            "stderr": "",
        }

    proof_script = "dmesg|grep -i 'Assigning MAC from Macloader'|tail -5"
    proof_result = step(
        "mac-assign-dmesg-proof",
        ["run", "/cache/bin/busybox", "sh", "-c", proof_script],
        timeout=90,
        bridge_timeout=60,
    )
    fields["mac_assign.end"] = "1"
    fields["mac_assign.kernel_proof_seen"] = (
        "1" if "Assigning MAC from Macloader" in str(proof_result.get("stdout") or "") else "0"
    )

    return {
        "ok": bool(source_ok and target_writable.get("rc") == 0 and base.intish(fields.get("mac_assign.write_rc")) == 0),
        "rc": write_result.get("rc"),
        "fields": fields,
        "stdout_file": "mac-assign-write-sysfs.stdout.txt",
        "stderr_file": "mac-assign-write-sysfs.stderr.txt",
    }


def collect_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    out_dir = REPO_ROOT / str(manifest["out_dir"])
    hook = manifest.get("post_flash_hook") or {}
    fields = hook.get("fields") if isinstance(hook.get("fields"), dict) else {}
    clean = manifest.get("classification", {})
    dmesg = read_text(out_dir / "test-dmesg-full.stdout.txt")
    dmesg_filter = read_text(out_dir / "test-dmesg-wifi-filter.stdout.txt")
    hook_proof = read_text(out_dir / "mac-assign-dmesg-proof.stdout.txt")

    write_ok = base.intish(fields.get("mac_assign.write_rc")) == 0
    source_ok = fields.get("mac_assign.source.shape") in {"colon_hex", "twelve_hex_normalized"}
    target_writable = base.intish(fields.get("mac_assign.target.writable")) == 1
    assigning_mac = (
        "Assigning MAC from Macloader" in dmesg
        or "Assigning MAC from Macloader" in dmesg_filter
        or "Assigning MAC from Macloader" in hook_proof
        or base.intish(fields.get("mac_assign.kernel_proof_seen")) == 1
    )
    wlan0_present = bool(clean.get("wlan0_present"))
    set_features_fail = bool(clean.get("set_features_fail"))
    swlan0_fail = bool(clean.get("swlan0_fail"))
    rollback_ok = bool((manifest.get("rollback") or {}).get("ok"))

    if not manifest.get("test_flash_ok") or not rollback_ok:
        label = "global-mac-assign-handoff-incomplete"
        passed = False
        reason = "test boot or rollback did not complete"
    elif not source_ok:
        label = "global-mac-assign-source-unavailable"
        passed = False
        reason = "read-only EFS .mac.info was not available or did not normalize to 12 hex digits"
    elif not target_writable:
        label = "global-mac-assign-target-not-writable"
        passed = False
        reason = "/sys/wifi/mac_addr was not writable in the test boot global namespace"
    elif assigning_mac and wlan0_present and not set_features_fail and not swlan0_fail:
        label = "global-mac-assign-clean-wlan0"
        passed = True
        reason = "pre-HDD MAC assignment reached the kernel store path and wlan0 came up clean"
    elif assigning_mac and wlan0_present:
        label = "global-mac-assign-kernel-proof-wlan0-still-degraded"
        passed = True
        reason = "pre-HDD MAC assignment reached the kernel store path and wlan0, but degraded-interface errors remain"
    elif assigning_mac:
        label = "global-mac-assign-kernel-proof-no-wlan0"
        passed = False
        reason = "pre-HDD MAC assignment reached the kernel store path, but wlan0 did not appear"
    elif write_ok:
        label = "global-mac-assign-write-no-kernel-proof"
        passed = False
        reason = "MAC sysfs write returned success but the required kernel proof line was absent"
    elif wlan0_present:
        label = "global-mac-assign-write-failed-wlan0-present"
        passed = False
        reason = "wlan0 appeared but the pre-HDD MAC write did not succeed"
    else:
        label = "global-mac-assign-write-failed-no-wlan0"
        passed = False
        reason = "pre-HDD MAC write did not succeed and wlan0 did not appear"

    return {
        "label": label,
        "decision": f"v2146-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "source_ok": source_ok,
        "source_shape": fields.get("mac_assign.source.shape", ""),
        "source_exists": base.intish(fields.get("mac_assign.source.exists")),
        "source_bytes": base.intish(fields.get("mac_assign.source.bytes")),
        "target_writable": target_writable,
        "target_exists": base.intish(fields.get("mac_assign.target.exists")),
        "write_ok": write_ok,
        "write_rc": base.intish(fields.get("mac_assign.write_rc")),
        "write_value_len": base.intish(fields.get("mac_assign.write_value_len")),
        "assigning_mac": assigning_mac,
        "kernel_store_ok": assigning_mac,
        "wlan0_present": wlan0_present,
        "set_features_fail": set_features_fail,
        "swlan0_fail": swlan0_fail,
        "icnss_state_line": str(clean.get("icnss_state_line") or ""),
        "requested_wlanmdsp": bool(clean.get("requested_wlanmdsp")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    gate = manifest["mac_gate"]
    clean = manifest.get("classification", {})
    steps = manifest["steps"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['stdout_file']}`"
        for step in steps
    ]
    return "\n".join([
        "# Native Init V2146 QCACLD Firmware Class Global MAC Assign Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2146`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## MAC Gate",
        "",
        f"- `source_ok`: `{gate['source_ok']}` shape `{gate['source_shape']}` exists `{gate['source_exists']}` bytes `{gate['source_bytes']}` raw_logged `0`",
        f"- `target_exists`: `{gate['target_exists']}` writable `{gate['target_writable']}`",
        f"- `write_ok`: `{gate['write_ok']}` rc `{gate['write_rc']}` len `{gate['write_value_len']}`",
        f"- `assigning_mac`: `{gate['assigning_mac']}` kernel_store_ok `{gate['kernel_store_ok']}`",
        "",
        "## Interface State",
        "",
        f"- `wlan0_present`: `{gate['wlan0_present']}` address `{clean.get('wlan0_address')}`",
        f"- `set_features_fail`: `{gate['set_features_fail']}`",
        f"- `swlan0_fail`: `{gate['swlan0_fail']}`",
        f"- `icnss_state_line`: `{gate['icnss_state_line']}`",
        f"- `requested_wlanmdsp`: `{gate['requested_wlanmdsp']}`",
        "",
        "## Reframe",
        "",
        "- V2146 keeps the proven V2137 `boot_wlan + firmware_class` route and adds a host-side pre-HDD MAC write immediately after test-boot verification.",
        "- The EFS mount is read-only and only supplies `.mac.info`; the only write is the bounded ICNSS `/sys/wifi/mac_addr` sysfs assignment.",
        "- If FW_READY/wlan0 still occur with no live dmesg `wlanmdsp.mbn`, the modem tftp branch remains moot for this native path.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No EFS/persist/file/partition write was used; EFS was mounted read-only and `.mac.info` was read-only.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "",
    ])


def main() -> int:
    manifest = base.run_handoff(
        cycle=CYCLE,
        out_dir=OUT_DIR,
        report_path=REPORT_PATH,
        post_flash_hook=post_flash_mac_assign,
    )
    gate = collect_gate(manifest)
    manifest = {
        **manifest,
        "decision": gate["decision"],
        "label": gate["label"],
        "pass": gate["pass"],
        "reason": gate["reason"],
        "mac_gate": gate,
    }
    store = base.EvidenceStore(OUT_DIR)
    store.write_json("manifest.json", manifest)
    summary = render_report(manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "out_dir": manifest["out_dir"],
        "mac_gate": gate,
    }, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
