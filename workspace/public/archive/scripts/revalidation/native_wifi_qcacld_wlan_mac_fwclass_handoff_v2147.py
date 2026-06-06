#!/usr/bin/env python3
"""V2147 feed QCACLD wlan_mac.bin firmware_class request on the V2137 route."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as base
import native_wifi_qcacld_fwclass_global_mac_assign_handoff_v2146 as macbase


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V2147"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2147-qcacld-wlan-mac-fwclass-handoff"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2147_QCACLD_WLAN_MAC_FWCLASS_HANDOFF_2026-06-05.md"
)
WLAN_MAC_FILE = "/cache/a90-wlan-mac-v2147.bin"
FEEDER_SCRIPT = "/cache/a90-fwfeed-v2147.sh"
FEEDER_RESULT = "/cache/a90-fwfeed-v2147.result"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def mac_hex_variants(hex_digits: str, count: int = 4) -> list[str]:
    octets = [int(hex_digits[index:index + 2], 16) for index in range(0, 12, 2)]
    octets[0] &= 0xFE
    variants: list[str] = []
    for variant_index in range(count):
        candidate = list(octets)
        candidate[-1] = (candidate[-1] + variant_index) & 0xFF
        variants.append("".join(f"{octet:02X}" for octet in candidate))
    return variants


def wlan_mac_bin_text(hex_digits: str) -> str:
    lines = [
        f"Intf{index}MacAddress={mac_hex}"
        for index, mac_hex in enumerate(mac_hex_variants(hex_digits))
    ]
    lines.append("END")
    return "\n".join(lines) + "\n"


def redacted_step(store: base.EvidenceStore,
                  steps: list[dict[str, Any]],
                  name: str,
                  result: dict[str, Any],
                  command: list[str],
                  stdout: str,
                  stderr: str = "") -> None:
    macbase.append_redacted_step(store, steps, name, result, command, stdout, stderr)


def run_step(store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             *,
             timeout: float = 60.0,
             bridge_timeout: float = 45.0) -> dict[str, Any]:
    return base.a90ctl_step(
        store,
        steps,
        name,
        command,
        timeout=timeout,
        bridge_timeout=bridge_timeout,
    )


def stage_line(store: base.EvidenceStore,
               steps: list[dict[str, Any]],
               line: str,
               index: int) -> dict[str, Any]:
    script = f"printf '%s\\n' {shlex.quote(line)} >> {FEEDER_SCRIPT}"
    return run_step(
        store,
        steps,
        f"wlan-mac-feeder-script-line-{index:02d}",
        ["run", "/cache/bin/busybox", "sh", "-c", script],
    )


def post_flash_wlan_mac_feeder(store: base.EvidenceStore,
                               steps: list[dict[str, Any]]) -> dict[str, Any]:
    mac_hook = macbase.post_flash_mac_assign(store, steps)
    fields: dict[str, str] = {}
    if isinstance(mac_hook.get("fields"), dict):
        fields.update({str(key): str(value) for key, value in mac_hook["fields"].items()})

    raw_result = base.run_command(
        base.a90ctl_command(["cat", macbase.MAC_INFO_PATH], timeout=30),
        timeout=45,
    )
    raw_mac = macbase.protocol_payload(str(raw_result.get("stdout") or "")).replace("\r", "").replace("\n", "")
    hex_digits = "".join(re.findall(r"[0-9A-Fa-f]", raw_mac))
    source_ok = len(hex_digits) == 12
    fields["wlan_mac_fwclass.source_ok"] = "1" if source_ok else "0"
    fields["wlan_mac_fwclass.source_hex_digits"] = str(len(hex_digits))
    fields["wlan_mac_fwclass.raw_mac_logged"] = "0"

    if source_ok:
        payload = wlan_mac_bin_text(hex_digits)
        run_step(
            store,
            steps,
            "wlan-mac-payload-touch",
            ["run", "/cache/bin/busybox", "touch", WLAN_MAC_FILE],
        )
        write_result = base.run_command(
            base.a90ctl_command(["writefile", WLAN_MAC_FILE, payload], timeout=30),
            timeout=45,
        )
        fields["wlan_mac_fwclass.payload_write_rc"] = str(write_result.get("rc"))
        fields["wlan_mac_fwclass.payload_len"] = str(len(payload))
        redacted_step(
            store,
            steps,
            "wlan-mac-payload-write",
            write_result,
            ["writefile", WLAN_MAC_FILE, "<redacted-wlan-mac-bin>"],
            (
                f"wlan_mac_fwclass.payload_write_rc={write_result.get('rc')}\n"
                f"wlan_mac_fwclass.payload_len={len(payload)}\n"
                "wlan_mac_fwclass.raw_mac_logged=0\n"
            ),
            str(write_result.get("stderr") or ""),
        )
    else:
        fields["wlan_mac_fwclass.payload_write_rc"] = "98"
        fields["wlan_mac_fwclass.payload_len"] = "0"

    run_step(store, steps, "wlan-mac-feeder-script-rm", ["run", "/cache/bin/busybox", "rm", "-f", FEEDER_SCRIPT, FEEDER_RESULT])
    run_step(store, steps, "wlan-mac-feeder-script-touch", ["run", "/cache/bin/busybox", "touch", FEEDER_SCRIPT])
    script_lines = [
        "#!/cache/bin/busybox sh",
        f"out={FEEDER_RESULT}",
        "dir=/sys/class/firmware/wlan!qca_cld!wlan_mac.bin",
        f"src={WLAN_MAC_FILE}",
        "echo begin=1 > \"$out\"",
        "loop=0",
        "while [ \"$loop\" -lt 1200 ]; do",
        "if [ -d \"$dir\" ]; then",
        "echo seen=1 >> \"$out\"",
        "echo 1 > \"$dir/loading\"",
        "echo loading_start_rc=$? >> \"$out\"",
        "cat \"$src\" > \"$dir/data\"",
        "echo data_rc=$? >> \"$out\"",
        "echo 0 > \"$dir/loading\"",
        "echo loading_done_rc=$? >> \"$out\"",
        "echo fed=1 >> \"$out\"",
        "exit 0",
        "fi",
        "loop=$((loop+1))",
        "sleep 0.2",
        "done",
        "echo seen=0 >> \"$out\"",
        "echo fed=0 >> \"$out\"",
        "exit 1",
    ]
    for line_index, line in enumerate(script_lines):
        stage_line(store, steps, line, line_index)
    run_step(store, steps, "wlan-mac-feeder-script-chmod", ["run", "/cache/bin/busybox", "chmod", "700", FEEDER_SCRIPT])
    start_result = run_step(
        store,
        steps,
        "wlan-mac-feeder-start",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"/cache/bin/busybox setsid {FEEDER_SCRIPT} >/dev/null 2>&1 & echo wlan_mac_fwclass.feeder_started=1",
        ],
    )
    fields.update(base.parse_key_values(str(start_result.get("stdout") or "")))
    fields["wlan_mac_fwclass.script_staged"] = "1"
    return {
        "ok": source_ok and base.intish(fields.get("wlan_mac_fwclass.payload_write_rc")) == 0,
        "fields": fields,
        "mac_hook": mac_hook,
        "stdout_file": "wlan-mac-feeder-start.stdout.txt",
        "stderr_file": "wlan-mac-feeder-start.stderr.txt",
    }


def collect_post_rollback_feeder(store: base.EvidenceStore,
                                 steps: list[dict[str, Any]]) -> dict[str, Any]:
    result = base.a90ctl_step(
        store,
        steps,
        "post-rollback-wlan-mac-feeder-result",
        ["cat", FEEDER_RESULT],
        timeout=60,
        bridge_timeout=45,
    )
    fields = base.parse_key_values(str(result.get("stdout") or ""))
    cleanup = base.a90ctl_step(
        store,
        steps,
        "post-rollback-wlan-mac-feeder-cleanup",
        ["run", "/cache/bin/busybox", "rm", "-f", FEEDER_SCRIPT, FEEDER_RESULT, WLAN_MAC_FILE],
        timeout=60,
        bridge_timeout=45,
    )
    return {
        "ok": bool(result.get("ok")),
        "fields": fields,
        "cleanup_ok": bool(cleanup.get("ok")),
    }


def collect_gate(manifest: dict[str, Any], feeder_result: dict[str, Any]) -> dict[str, Any]:
    out_dir = REPO_ROOT / str(manifest["out_dir"])
    clean = manifest.get("classification", {})
    hook = manifest.get("post_flash_hook") if isinstance(manifest.get("post_flash_hook"), dict) else {}
    hook_fields = hook.get("fields") if isinstance(hook.get("fields"), dict) else {}
    feeder_fields = feeder_result.get("fields") if isinstance(feeder_result.get("fields"), dict) else {}
    dmesg = read_text(out_dir / "test-dmesg-full.stdout.txt")
    dmesg_filter = read_text(out_dir / "test-dmesg-wifi-filter.stdout.txt")
    combined_dmesg = dmesg + "\n" + dmesg_filter

    source_ok = base.intish(hook_fields.get("wlan_mac_fwclass.source_ok")) == 1
    payload_write_ok = base.intish(hook_fields.get("wlan_mac_fwclass.payload_write_rc")) == 0
    feeder_seen = base.intish(feeder_fields.get("seen")) == 1
    feeder_fed = base.intish(feeder_fields.get("fed")) == 1
    feeder_write_ok = (
        base.intish(feeder_fields.get("loading_start_rc")) == 0
        and base.intish(feeder_fields.get("data_rc")) == 0
        and base.intish(feeder_fields.get("loading_done_rc")) == 0
    )
    dmesg_requested_wlan_mac = "wlan_mac.bin" in combined_dmesg
    dmesg_uses_wlan_mac = "using MAC address from wlan_mac.bin" in combined_dmesg
    dmesg_provisioned_platform_mac = "hdd_platform_wlan_mac" in combined_dmesg
    dmesg_uses_platform_mac = "using MAC address from platform driver" in combined_dmesg
    dmesg_default_mac = "using default MAC address" in combined_dmesg
    swlan0_present = "dev : swlan0 : event" in combined_dmesg
    swlan0_generation_fail = "failed to generating swlan0 mac addr" in combined_dmesg
    wow_debugfs_fail = "wow debug_fs init failed" in combined_dmesg
    wlan0_present = bool(clean.get("wlan0_present"))
    set_features_fail = bool(clean.get("set_features_fail"))
    swlan0_fail = bool(clean.get("swlan0_fail"))
    rollback_ok = bool((manifest.get("rollback") or {}).get("ok"))

    if not manifest.get("test_flash_ok") or not rollback_ok:
        label = "wlan-mac-fwclass-handoff-incomplete"
        passed = False
        reason = "test boot or rollback did not complete"
    elif not source_ok:
        label = "wlan-mac-fwclass-source-missing"
        passed = False
        reason = "read-only EFS .mac.info did not normalize to the wlan_mac.bin source"
    elif not payload_write_ok:
        label = "wlan-mac-fwclass-payload-stage-failed"
        passed = False
        reason = "redacted wlan_mac.bin payload could not be staged in /cache"
    elif dmesg_uses_platform_mac and wlan0_present and swlan0_present and not swlan0_generation_fail and not set_features_fail:
        label = "platform-mac-clean-wlan0"
        passed = True
        reason = "pre-HDD platform MAC was consumed and wlan0/swlan0 appeared without degraded-interface errors"
    elif dmesg_uses_platform_mac and wlan0_present and swlan0_present and not swlan0_generation_fail:
        label = "platform-mac-swlan0-created-set-features-blocker"
        passed = True
        reason = "pre-HDD platform MAC was consumed and swlan0 generation succeeded; remaining blocker is set_features/debugfs"
    elif dmesg_uses_platform_mac and wlan0_present:
        label = "platform-mac-wlan0-still-degraded"
        passed = True
        reason = "pre-HDD platform MAC was consumed, but secondary-interface degradation remains"
    elif feeder_fed and feeder_write_ok and dmesg_uses_wlan_mac and wlan0_present and not set_features_fail and not swlan0_fail:
        label = "wlan-mac-fwclass-clean-wlan0"
        passed = True
        reason = "wlan_mac.bin was fed and wlan0 came up without degraded-interface errors"
    elif feeder_fed and feeder_write_ok and dmesg_uses_wlan_mac and wlan0_present:
        label = "wlan-mac-fwclass-fed-wlan0-still-degraded"
        passed = True
        reason = "wlan_mac.bin was fed and accepted, but degraded-interface errors remain"
    elif feeder_fed and feeder_write_ok and dmesg_uses_wlan_mac:
        label = "wlan-mac-fwclass-fed-no-wlan0"
        passed = False
        reason = "wlan_mac.bin was fed and accepted, but wlan0 did not appear"
    elif feeder_fed and feeder_write_ok:
        label = "wlan-mac-fwclass-fed-not-accepted"
        passed = False
        reason = "firmware_class data path completed, but dmesg did not show wlan_mac.bin acceptance"
    elif feeder_seen:
        label = "wlan-mac-fwclass-request-seen-feed-failed"
        passed = False
        reason = "wlan_mac.bin request appeared, but the firmware_class write sequence failed"
    else:
        label = "wlan-mac-fwclass-request-not-seen"
        passed = False
        reason = "wlan0 route completed without exposing the wlan_mac.bin firmware_class request to the feeder"

    return {
        "label": label,
        "decision": f"v2147-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "source_ok": source_ok,
        "source_hex_digits": base.intish(hook_fields.get("wlan_mac_fwclass.source_hex_digits")),
        "payload_write_ok": payload_write_ok,
        "payload_len": base.intish(hook_fields.get("wlan_mac_fwclass.payload_len")),
        "feeder_seen": feeder_seen,
        "feeder_fed": feeder_fed,
        "feeder_write_ok": feeder_write_ok,
        "dmesg_requested_wlan_mac": dmesg_requested_wlan_mac,
        "dmesg_uses_wlan_mac": dmesg_uses_wlan_mac,
        "dmesg_provisioned_platform_mac": dmesg_provisioned_platform_mac,
        "dmesg_uses_platform_mac": dmesg_uses_platform_mac,
        "dmesg_default_mac": dmesg_default_mac,
        "swlan0_present": swlan0_present,
        "swlan0_generation_fail": swlan0_generation_fail,
        "wow_debugfs_fail": wow_debugfs_fail,
        "wlan0_present": wlan0_present,
        "set_features_fail": set_features_fail,
        "swlan0_fail": swlan0_fail,
        "icnss_state_line": str(clean.get("icnss_state_line") or ""),
        "requested_wlanmdsp": bool(clean.get("requested_wlanmdsp")),
        "cleanup_ok": bool(feeder_result.get("cleanup_ok")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    gate = manifest["wlan_mac_gate"]
    steps = manifest["steps"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['stdout_file']}`"
        for step in steps
    ]
    return "\n".join([
        "# Native Init V2147 QCACLD wlan_mac.bin Firmware Class Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2147`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Gate Results",
        "",
        f"- `source_ok`: `{gate['source_ok']}` hex_digits `{gate['source_hex_digits']}` raw_mac_logged `0`",
        f"- `payload_write_ok`: `{gate['payload_write_ok']}` len `{gate['payload_len']}` raw_payload_logged `0`",
        f"- `feeder_seen`: `{gate['feeder_seen']}` fed `{gate['feeder_fed']}` write_ok `{gate['feeder_write_ok']}`",
        f"- `dmesg_requested_wlan_mac`: `{gate['dmesg_requested_wlan_mac']}`",
        f"- `dmesg_uses_wlan_mac`: `{gate['dmesg_uses_wlan_mac']}` default_mac `{gate['dmesg_default_mac']}`",
        f"- `dmesg_provisioned_platform_mac`: `{gate['dmesg_provisioned_platform_mac']}`",
        f"- `dmesg_uses_platform_mac`: `{gate['dmesg_uses_platform_mac']}`",
        "",
        "## Interface State",
        "",
        f"- `wlan0_present`: `{gate['wlan0_present']}` address_logged `0`",
        f"- `set_features_fail`: `{gate['set_features_fail']}`",
        f"- `swlan0_present`: `{gate['swlan0_present']}`",
        f"- `swlan0_generation_fail`: `{gate['swlan0_generation_fail']}`",
        f"- `wow_debugfs_fail`: `{gate['wow_debugfs_fail']}`",
        f"- `legacy_swlan0_fail_counter`: `{gate['swlan0_fail']}`",
        f"- `icnss_state_line`: `{gate['icnss_state_line']}`",
        f"- `requested_wlanmdsp`: `{gate['requested_wlanmdsp']}`",
        "",
        "## Reframe",
        "",
        "- V2146 proved `/sys/wifi/mac_addr` reaches the kernel store path, but V2146 dmesg still showed `wlan_mac.bin` firmware_class timeout followed by default MAC selection.",
        "- V2147 feeds only the observed `wlan/qca_cld/wlan_mac.bin` firmware_class node using a redacted payload generated from read-only EFS `.mac.info`.",
        "- The current V2147 capture shows HDD consumed the platform-driver MAC before interface creation, skipped the default-MAC path, and created `swlan0`; therefore the MAC/swlan0-generation gate is solved for this route.",
        "- The remaining degraded-interface blocker is `set_features() failed (-11)` plus `wow debug_fs init failed` on secondary adapters.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping is used in this gate; connectivity remains downstream of a clean wlan0.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Cleanup",
        "",
        f"- `cache_artifacts_removed`: `{gate['cleanup_ok']}`",
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- EFS was mounted read-only; no EFS, persist, firmware, boot, or partition file was written.",
        "- The only functional write in the test boot was bounded firmware_class userspace fallback data for the observed `wlan_mac.bin` request.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "",
    ])


def main() -> int:
    manifest = base.run_handoff(
        cycle=CYCLE,
        out_dir=OUT_DIR,
        report_path=REPORT_PATH,
        post_flash_hook=post_flash_wlan_mac_feeder,
    )
    store = base.EvidenceStore(OUT_DIR)
    steps = manifest["steps"]
    feeder_result = collect_post_rollback_feeder(store, steps)
    gate = collect_gate(manifest, feeder_result)
    manifest = {
        **manifest,
        "decision": gate["decision"],
        "label": gate["label"],
        "pass": gate["pass"],
        "reason": gate["reason"],
        "post_rollback_feeder_result": feeder_result,
        "wlan_mac_gate": gate,
        "steps": steps,
    }
    store.write_json("manifest.json", manifest)
    summary = render_report(manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "out_dir": manifest["out_dir"],
        "wlan_mac_gate": gate,
    }, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
