#!/usr/bin/env python3
"""V2151 minimal wlan0 link-up plus one nl80211 scan on the V2137 route."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as base
import native_wifi_wlan0_linkup_scan_handoff_v2148 as scanbase


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V2151"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2151-wlan0-linkup-scan-minimal-handoff"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2151_WLAN0_LINKUP_SCAN_MINIMAL_HANDOFF_2026-06-05.md"
)
HELPER_BUILD_DIR = OUT_DIR / "host-build"
HELPER_LOCAL = HELPER_BUILD_DIR / "a90_nl80211_scan_once_v2151"
HELPER_REMOTE = "/cache/bin/a90_nl80211_scan_once_v2151"
HELPER_REMOTE_B64 = "/cache/a90-nl80211-scan-v2151.gz.b64"
HELPER_REMOTE_GZ = "/cache/a90-nl80211-scan-v2151.gz"
SCAN_SCRIPT = "/cache/a90-v2151-linkup-scan-minimal.sh"
SCAN_RESULT = "/cache/a90-v2151-linkup-scan-minimal.result"


def configure_scanbase_paths() -> None:
    scanbase.CYCLE = CYCLE
    scanbase.OUT_DIR = OUT_DIR
    scanbase.REPORT_PATH = REPORT_PATH
    scanbase.HELPER_BUILD_DIR = HELPER_BUILD_DIR
    scanbase.HELPER_LOCAL = HELPER_LOCAL
    scanbase.HELPER_REMOTE = HELPER_REMOTE
    scanbase.HELPER_REMOTE_B64 = HELPER_REMOTE_B64
    scanbase.HELPER_REMOTE_GZ = HELPER_REMOTE_GZ


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


def parse_result_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in protocol_payload(text).splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


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


def stage_scan_script(store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {
        "scan_script.begin": "1",
        "scan_script.path": SCAN_SCRIPT,
        "scan_script.result_path": SCAN_RESULT,
        "scan_script.credentials": "0",
        "scan_script.connect": "0",
        "scan_script.dhcp_routing": "0",
        "scan_script.external_ping": "0",
        "scan_script.mac_efs": "0",
    }
    run_step(store, steps, "scan-script-clean", ["run", "/cache/bin/busybox", "rm", "-f", SCAN_SCRIPT, SCAN_RESULT])
    run_step(store, steps, "scan-script-touch", ["run", "/cache/bin/busybox", "touch", SCAN_SCRIPT])
    script_lines = [
        "#!/cache/bin/busybox sh",
        f"out={SCAN_RESULT}",
        f"helper={HELPER_REMOTE}",
        "echo v2151.begin=1 > \"$out\"",
        "echo v2151.credentials=0 >> \"$out\"",
        "echo v2151.connect=0 >> \"$out\"",
        "echo v2151.dhcp_routing=0 >> \"$out\"",
        "echo v2151.external_ping=0 >> \"$out\"",
        "echo v2151.mac_efs=0 >> \"$out\"",
        "loop=0",
        "while [ \"$loop\" -lt 1200 ]; do",
        "if [ -e /sys/class/net/wlan0 ]; then echo v2151.wlan0_seen=1 >> \"$out\"; break; fi",
        "loop=$((loop+1))",
        "sleep 0.2",
        "done",
        "if [ ! -e /sys/class/net/wlan0 ]; then echo v2151.wlan0_seen=0 >> \"$out\"; echo v2151.result=wlan0-missing >> \"$out\"; echo v2151.end=1 >> \"$out\"; exit 20; fi",
        "printf 'v2151.pre_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2151.pre_carrier=' >> \"$out\"; cat /sys/class/net/wlan0/carrier >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2151.pre_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "/cache/bin/busybox ip link set wlan0 up >> \"$out\" 2>&1",
        "echo v2151.link_up_rc=$? >> \"$out\"",
        "sleep 1",
        "printf 'v2151.post_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2151.post_carrier=' >> \"$out\"; cat /sys/class/net/wlan0/carrier >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2151.post_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "echo v2151.scan_invoked=1 >> \"$out\"",
        "\"$helper\" wlan0 6000 >> \"$out\" 2>&1",
        "echo v2151.scan_helper_rc=$? >> \"$out\"",
        "echo v2151.end=1 >> \"$out\"",
    ]
    for index, line in enumerate(script_lines):
        run_step(
            store,
            steps,
            f"scan-script-line-{index:02d}",
            ["run", "/cache/bin/busybox", "sh", "-c", f"printf '%s\\n' {shlex.quote(line)} >> {SCAN_SCRIPT}"],
        )
    chmod = run_step(store, steps, "scan-script-chmod", ["run", "/cache/bin/busybox", "chmod", "700", SCAN_SCRIPT])
    start = run_step(
        store,
        steps,
        "scan-script-start",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"/cache/bin/busybox setsid {SCAN_SCRIPT} >/dev/null 2>&1 & echo scan_script.started=1",
        ],
    )
    fields.update(base.parse_key_values(str(start.get("stdout") or "")))
    fields["scan_script.ok"] = "1" if chmod.get("ok") and fields.get("scan_script.started") == "1" else "0"
    return fields


def post_flash_linkup_scan(store: base.EvidenceStore,
                           steps: list[dict[str, Any]],
                           helper_build: dict[str, Any],
                           prestage_fields: dict[str, str]) -> dict[str, Any]:
    helper_fields = scanbase.verify_staged_helper(store, steps, helper_build)
    scan_fields = stage_scan_script(store, steps)
    ok = (
        prestage_fields.get("helper_stage.ok") == "1"
        and helper_fields.get("helper_verify.ok") == "1"
        and scan_fields.get("scan_script.ok") == "1"
    )
    return {
        "ok": ok,
        "fields": {**prestage_fields, **helper_fields, **scan_fields},
    }


def collect_post_rollback_scan(store: base.EvidenceStore,
                               steps: list[dict[str, Any]]) -> dict[str, Any]:
    result = base.a90ctl_step(
        store,
        steps,
        "post-rollback-linkup-scan-result",
        ["cat", SCAN_RESULT],
        timeout=90,
        bridge_timeout=60,
    )
    fields = parse_result_fields(str(result.get("stdout") or ""))
    cleanup = base.a90ctl_step(
        store,
        steps,
        "post-rollback-linkup-scan-cleanup",
        ["run", "/cache/bin/busybox", "rm", "-f", SCAN_SCRIPT, SCAN_RESULT, HELPER_REMOTE, HELPER_REMOTE_B64, HELPER_REMOTE_GZ],
        timeout=90,
        bridge_timeout=60,
    )
    return {
        "ok": bool(result.get("ok")),
        "fields": fields,
        "cleanup_ok": bool(cleanup.get("ok")),
    }


def collect_gate(manifest: dict[str, Any], scan_result: dict[str, Any]) -> dict[str, Any]:
    out_dir = REPO_ROOT / str(manifest["out_dir"])
    clean = manifest.get("classification", {})
    hook = manifest.get("post_flash_hook") if isinstance(manifest.get("post_flash_hook"), dict) else {}
    hook_fields = hook.get("fields") if isinstance(hook.get("fields"), dict) else {}
    scan_fields = scan_result.get("fields") if isinstance(scan_result.get("fields"), dict) else {}
    dmesg = read_text(out_dir / "test-dmesg-full.stdout.txt")
    dmesg_filter = read_text(out_dir / "test-dmesg-wifi-filter.stdout.txt")
    combined_dmesg = dmesg + "\n" + dmesg_filter

    rollback_ok = bool((manifest.get("rollback") or {}).get("ok"))
    wlan0_present = bool(clean.get("wlan0_present")) or scan_fields.get("v2151.wlan0_seen") == "1"
    link_up_rc = base.intish(scan_fields.get("v2151.link_up_rc"))
    link_up_ok = link_up_rc == 0
    scan_invoked = scan_fields.get("v2151.scan_invoked") == "1"
    trigger_attempted = scan_fields.get("nl80211_scan_once.trigger_attempted") == "1"
    trigger_ok = scan_fields.get("nl80211_scan_once.trigger_rc") == "0"
    scan_result_name = scan_fields.get("nl80211_scan_once.result", "")
    scan_count = base.intish(scan_fields.get("nl80211_scan_once.scan_result_count"))
    helper_rc = base.intish(scan_fields.get("v2151.scan_helper_rc"))
    no_credentials = (
        scan_fields.get("v2151.credentials") == "0"
        and scan_fields.get("v2151.connect") == "0"
        and scan_fields.get("v2151.dhcp_routing") == "0"
        and scan_fields.get("v2151.external_ping") == "0"
        and scan_fields.get("nl80211_scan_once.credentials") == "0"
        and scan_fields.get("nl80211_scan_once.connect") == "0"
        and scan_fields.get("nl80211_scan_once.dhcp_routing") == "0"
        and scan_fields.get("nl80211_scan_once.external_ping") == "0"
    )
    mac_efs_skipped = scan_fields.get("v2151.mac_efs") == "0" and hook_fields.get("scan_script.mac_efs") == "0"
    cfg80211_seen = "cfg80211" in combined_dmesg.lower()
    regulatory_seen = "regulatory" in combined_dmesg.lower()

    if not manifest.get("test_flash_ok") or not rollback_ok:
        label = "wlan0-linkup-scan-handoff-incomplete"
        passed = False
        reason = "test boot or rollback did not complete"
    elif hook_fields.get("helper_stage.ok") != "1" or hook_fields.get("helper_verify.ok") != "1":
        label = "wlan0-linkup-scan-helper-stage-failed"
        passed = False
        reason = (
            f"scan helper staging/verification failed: "
            f"stage={hook_fields.get('helper_stage.reason', 'unknown')} "
            f"verify={hook_fields.get('helper_verify.ok', '0')}"
        )
    elif not no_credentials or not mac_efs_skipped:
        label = "wlan0-linkup-scan-safety-violation"
        passed = False
        reason = "scan gate output did not preserve the no-credentials/no-connect/no-MAC-EFS contract"
    elif not wlan0_present:
        label = "wlan0-linkup-scan-no-wlan0"
        passed = False
        reason = "wlan0 was not present in the scan window"
    elif not link_up_ok:
        label = "wlan0-linkup-failed"
        passed = False
        reason = f"ip link set wlan0 up failed rc={link_up_rc}"
    elif not scan_invoked or not trigger_attempted:
        label = "wlan0-linkup-scan-not-invoked"
        passed = False
        reason = "link-up completed but nl80211 scan helper was not invoked"
    elif scan_result_name == "pass" and trigger_ok and scan_count > 0 and helper_rc == 0:
        label = "wlan0-linkup-scan-bss-pass"
        passed = True
        reason = "wlan0 accepted link-up and one nl80211 scan returned redacted BSS entries"
    elif scan_result_name == "zero-bss" and trigger_ok:
        label = "wlan0-linkup-scan-zero-bss"
        passed = False
        reason = "nl80211 scan completed but returned zero BSS entries"
    else:
        label = "wlan0-linkup-scan-failed"
        passed = False
        reason = f"scan_result={scan_result_name or 'missing'} helper_rc={helper_rc} trigger_ok={trigger_ok}"

    return {
        "label": label,
        "decision": f"v2151-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "wlan0_present": wlan0_present,
        "pre_operstate": scan_fields.get("v2151.pre_operstate", ""),
        "pre_carrier": scan_fields.get("v2151.pre_carrier", ""),
        "pre_flags": scan_fields.get("v2151.pre_flags", ""),
        "post_operstate": scan_fields.get("v2151.post_operstate", ""),
        "post_carrier": scan_fields.get("v2151.post_carrier", ""),
        "post_flags": scan_fields.get("v2151.post_flags", ""),
        "link_up_rc": link_up_rc,
        "link_up_ok": link_up_ok,
        "scan_invoked": scan_invoked,
        "trigger_attempted": trigger_attempted,
        "trigger_ok": trigger_ok,
        "trigger_errno": base.intish(scan_fields.get("nl80211_scan_once.trigger_errno")),
        "scan_result": scan_result_name,
        "scan_count": scan_count,
        "scan_helper_rc": helper_rc,
        "family_id": base.intish(scan_fields.get("nl80211_scan_once.family_id")),
        "ifindex": base.intish(scan_fields.get("nl80211_scan_once.ifindex")),
        "raw_results_redacted": scan_fields.get("nl80211_scan_once.raw_results_redacted") == "1",
        "no_credentials": no_credentials,
        "mac_efs_skipped": mac_efs_skipped,
        "cfg80211_seen": cfg80211_seen,
        "regulatory_seen": regulatory_seen,
        "icnss_state_line": str(clean.get("icnss_state_line") or ""),
        "cleanup_ok": bool(scan_result.get("cleanup_ok")),
        "helper_stage_ok": hook_fields.get("helper_stage.ok") == "1",
        "helper_stage_reason": hook_fields.get("helper_stage.reason", ""),
        "helper_verify_ok": hook_fields.get("helper_verify.ok") == "1",
    }


def render_report(manifest: dict[str, Any]) -> str:
    gate = manifest["linkup_scan_gate"]
    helper = manifest.get("helper_build") or {}
    steps = manifest["steps"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['stdout_file']}`"
        for step in steps
    ]
    return "\n".join([
        "# Native Init V2151 Minimal wlan0 Link-Up Scan Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2151`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Gate Results",
        "",
        f"- `wlan0_present`: `{gate['wlan0_present']}` address_logged `0`",
        f"- `link_up_rc`: `{gate['link_up_rc']}` link_up_ok `{gate['link_up_ok']}`",
        f"- `pre_operstate`: `{gate['pre_operstate']}` carrier `{gate['pre_carrier']}` flags `{gate['pre_flags']}`",
        f"- `post_operstate`: `{gate['post_operstate']}` carrier `{gate['post_carrier']}` flags `{gate['post_flags']}`",
        f"- `scan_invoked`: `{gate['scan_invoked']}` trigger_attempted `{gate['trigger_attempted']}` trigger_ok `{gate['trigger_ok']}` trigger_errno `{gate['trigger_errno']}`",
        f"- `scan_result`: `{gate['scan_result']}` scan_count `{gate['scan_count']}` helper_rc `{gate['scan_helper_rc']}`",
        f"- `family_id`: `{gate['family_id']}` ifindex `{gate['ifindex']}` raw_results_redacted `{gate['raw_results_redacted']}`",
        f"- `no_credentials`: `{gate['no_credentials']}` mac_efs_skipped `{gate['mac_efs_skipped']}`",
        f"- `helper_stage_ok`: `{gate['helper_stage_ok']}` verify `{gate['helper_verify_ok']}` reason `{gate['helper_stage_reason']}`",
        "",
        "## Driver Context",
        "",
        f"- `icnss_state_line`: `{gate['icnss_state_line']}`",
        f"- `cfg80211_seen`: `{gate['cfg80211_seen']}` regulatory_seen `{gate['regulatory_seen']}`",
        f"- `helper_sha256`: `{helper.get('sha256', '')}` gzip_len `{helper.get('gzip_len', 0)}` chunks `{helper.get('chunks', 0)}`",
        "",
        "## Scope",
        "",
        "- The only interface mutation is bounded `ip link set wlan0 up`.",
        "- The only Wi-Fi operation is one nl80211 scan trigger plus redacted BSS count dump.",
        "- No MAC/EFS hook is run in this minimal pass.",
        "- `set_features() failed (-11)` and secondary `swlan0` symptoms are not chased here because primary `wlan0` scan is the gate.",
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
        "- No SSID/PSK/credential file or environment value was read.",
        "- No association/connect, DHCP, route change, or external ping was attempted.",
        "- No Wi-Fi HAL/wificond/supplicant was started by this runner.",
        "- No MAC/EFS mount or MAC sysfs assignment hook was run by this runner.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "",
    ])


def check_forbidden_output(summary: str) -> list[str]:
    patterns = [
        r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
    ]
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, summary, re.IGNORECASE):
            hits.append(pattern)
    return hits


def main() -> int:
    configure_scanbase_paths()
    store = base.EvidenceStore(OUT_DIR)
    bootstrap_steps: list[dict[str, Any]] = []
    helper_build = scanbase.build_helper(store, bootstrap_steps)
    prestage_fields = scanbase.stage_helper_binary(store, bootstrap_steps, helper_build)

    def hook(hook_store: base.EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
        steps.extend(bootstrap_steps)
        return post_flash_linkup_scan(hook_store, steps, helper_build, prestage_fields)

    manifest = base.run_handoff(
        cycle=CYCLE,
        out_dir=OUT_DIR,
        report_path=REPORT_PATH,
        post_flash_hook=hook,
    )
    store = base.EvidenceStore(OUT_DIR)
    steps = manifest["steps"]
    scan_result = collect_post_rollback_scan(store, steps)
    gate = collect_gate(manifest, scan_result)
    manifest = {
        **manifest,
        "decision": gate["decision"],
        "label": gate["label"],
        "pass": gate["pass"],
        "reason": gate["reason"],
        "helper_build": helper_build,
        "post_rollback_scan_result": scan_result,
        "linkup_scan_gate": gate,
        "steps": steps,
        "credentials_read": False,
        "connect_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "mac_efs_hook_executed": False,
    }
    summary = render_report(manifest)
    forbidden_hits = check_forbidden_output(summary)
    manifest["forbidden_output_hits"] = forbidden_hits
    if forbidden_hits:
        manifest["decision"] = "v2151-forbidden-output-hit"
        manifest["label"] = "forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "report contained forbidden credential/MAC/BSS output"
        summary = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "out_dir": manifest["out_dir"],
        "linkup_scan_gate": gate,
        "forbidden_output_hits": forbidden_hits,
    }, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
