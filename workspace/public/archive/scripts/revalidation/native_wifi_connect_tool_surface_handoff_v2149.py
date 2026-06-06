#!/usr/bin/env python3
"""V2149 connect-tool surface in the native wlan0 link-up/scan window."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as base
import native_wifi_qcacld_fwclass_global_mac_assign_handoff_v2146 as macbase
import native_wifi_wlan0_linkup_scan_handoff_v2148 as scanbase


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V2149"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2149-connect-tool-surface-handoff"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2149_CONNECT_TOOL_SURFACE_HANDOFF_2026-06-05.md"
)
SURFACE_SCRIPT = "/cache/a90-v2149-connect-surface.sh"
SURFACE_RESULT = "/cache/a90-v2149-connect-surface.result"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def protocol_payload(text: str) -> str:
    return macbase.protocol_payload(text)


def parse_fields(text: str) -> dict[str, str]:
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


def stage_surface_script(store: base.EvidenceStore,
                         steps: list[dict[str, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {
        "surface_script.begin": "1",
        "surface_script.path": SURFACE_SCRIPT,
        "surface_script.result_path": SURFACE_RESULT,
        "surface_script.credentials": "0",
        "surface_script.connect": "0",
        "surface_script.dhcp_routing": "0",
        "surface_script.external_ping": "0",
    }
    run_step(
        store,
        steps,
        "surface-script-clean",
        [
            "run",
            "/cache/bin/busybox",
            "rm",
            "-f",
            SURFACE_SCRIPT,
            SURFACE_RESULT,
        ],
    )
    run_step(store, steps, "surface-script-touch", ["run", "/cache/bin/busybox", "touch", SURFACE_SCRIPT])
    helper_command = " ".join(shlex.quote(part) for part in [
        "/cache/bin/a90_android_execns_probe",
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-connect-tool-surface",
        "--target-profile",
        "system-toybox",
        "--timeout-sec",
        "5",
    ])
    script_lines = [
        "#!/cache/bin/busybox sh",
        f"out={SURFACE_RESULT}",
        f"scan_helper={scanbase.HELPER_REMOTE}",
        "echo v2149.begin=1 > \"$out\"",
        "echo v2149.credentials=0 >> \"$out\"",
        "echo v2149.connect=0 >> \"$out\"",
        "echo v2149.dhcp_routing=0 >> \"$out\"",
        "echo v2149.external_ping=0 >> \"$out\"",
        "loop=0",
        "while [ \"$loop\" -lt 1200 ]; do",
        "if [ -e /sys/class/net/wlan0 ]; then echo v2149.wlan0_seen=1 >> \"$out\"; break; fi",
        "loop=$((loop+1))",
        "sleep 0.2",
        "done",
        "if [ ! -e /sys/class/net/wlan0 ]; then echo v2149.wlan0_seen=0 >> \"$out\"; echo v2149.result=wlan0-missing >> \"$out\"; echo v2149.end=1 >> \"$out\"; exit 20; fi",
        "printf 'v2149.pre_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2149.pre_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "/cache/bin/busybox ip link set wlan0 up >> \"$out\" 2>&1",
        "echo v2149.link_up_rc=$? >> \"$out\"",
        "sleep 1",
        "printf 'v2149.post_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2149.post_carrier=' >> \"$out\"; cat /sys/class/net/wlan0/carrier >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2149.post_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "echo v2149.scan_invoked=1 >> \"$out\"",
        "\"$scan_helper\" wlan0 6000 >> \"$out\" 2>&1",
        "echo v2149.scan_helper_rc=$? >> \"$out\"",
        "echo v2149.connect_tool_surface_invoked=1 >> \"$out\"",
        f"{helper_command} >> \"$out\" 2>&1",
        "echo v2149.connect_tool_surface_rc=$? >> \"$out\"",
        "echo v2149.end=1 >> \"$out\"",
    ]
    line_ok = True
    for index, line in enumerate(script_lines):
        result = run_step(
            store,
            steps,
            f"surface-script-line-{index:02d}",
            ["run", "/cache/bin/busybox", "sh", "-c", f"printf '%s\\n' {shlex.quote(line)} >> {SURFACE_SCRIPT}"],
        )
        line_ok = line_ok and bool(result.get("ok"))
    chmod = run_step(store, steps, "surface-script-chmod", ["run", "/cache/bin/busybox", "chmod", "700", SURFACE_SCRIPT])
    start = run_step(
        store,
        steps,
        "surface-script-start",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"/cache/bin/busybox setsid {SURFACE_SCRIPT} >/dev/null 2>&1 & echo surface_script.started=1",
        ],
    )
    fields.update(base.parse_key_values(str(start.get("stdout") or "")))
    fields["surface_script.lines_ok"] = "1" if line_ok else "0"
    fields["surface_script.ok"] = (
        "1"
        if line_ok and chmod.get("ok") and fields.get("surface_script.started") == "1"
        else "0"
    )
    return fields


def post_flash_surface(store: base.EvidenceStore,
                       steps: list[dict[str, Any]],
                       helper_build: dict[str, Any],
                       prestage_fields: dict[str, str]) -> dict[str, Any]:
    mac_hook = macbase.post_flash_mac_assign(store, steps)
    helper_fields = scanbase.verify_staged_helper(store, steps, helper_build)
    surface_fields = stage_surface_script(store, steps)
    ok = (
        prestage_fields.get("helper_stage.ok") == "1"
        and helper_fields.get("helper_verify.ok") == "1"
        and surface_fields.get("surface_script.ok") == "1"
    )
    return {
        "ok": ok,
        "mac_hook": mac_hook,
        "fields": {**prestage_fields, **helper_fields, **surface_fields},
    }


def collect_post_rollback_surface(store: base.EvidenceStore,
                                  steps: list[dict[str, Any]]) -> dict[str, Any]:
    result = base.a90ctl_step(
        store,
        steps,
        "post-rollback-connect-surface-result",
        ["cat", SURFACE_RESULT],
        timeout=90,
        bridge_timeout=60,
    )
    fields = parse_fields(str(result.get("stdout") or ""))
    cleanup = base.a90ctl_step(
        store,
        steps,
        "post-rollback-connect-surface-cleanup",
        [
            "run",
            "/cache/bin/busybox",
            "rm",
            "-f",
            SURFACE_SCRIPT,
            SURFACE_RESULT,
            scanbase.HELPER_REMOTE,
            scanbase.HELPER_REMOTE_B64,
            scanbase.HELPER_REMOTE_GZ,
        ],
        timeout=90,
        bridge_timeout=60,
    )
    return {
        "ok": bool(result.get("ok")),
        "fields": fields,
        "cleanup_ok": bool(cleanup.get("ok")),
    }


def collect_gate(manifest: dict[str, Any], surface_result: dict[str, Any]) -> dict[str, Any]:
    hook = manifest.get("post_flash_hook") if isinstance(manifest.get("post_flash_hook"), dict) else {}
    hook_fields = hook.get("fields") if isinstance(hook.get("fields"), dict) else {}
    fields = surface_result.get("fields") if isinstance(surface_result.get("fields"), dict) else {}
    rollback_ok = bool((manifest.get("rollback") or {}).get("ok"))
    wlan0_seen = fields.get("v2149.wlan0_seen") == "1"
    link_up_ok = base.intish(fields.get("v2149.link_up_rc")) == 0
    scan_result = fields.get("nl80211_scan_once.result", "")
    scan_count = base.intish(fields.get("nl80211_scan_once.scan_result_count"))
    scan_ok = scan_result == "pass" and scan_count > 0 and base.intish(fields.get("v2149.scan_helper_rc")) == 0
    surface_invoked = fields.get("v2149.connect_tool_surface_invoked") == "1"
    surface_rc = base.intish(fields.get("v2149.connect_tool_surface_rc"))
    surface_result_name = fields.get("wifi_connect_tool_surface.result", "")
    supplicant_ready = fields.get("wifi_connect_tool_surface.supplicant_ready") == "1"
    dhcp_ready = fields.get("wifi_connect_tool_surface.dhcp_ready") == "1"
    ping_ready = fields.get("wifi_connect_tool_surface.ping_ready") == "1"
    no_credentials = (
        fields.get("v2149.credentials") == "0"
        and fields.get("v2149.connect") == "0"
        and fields.get("v2149.dhcp_routing") == "0"
        and fields.get("v2149.external_ping") == "0"
        and fields.get("wifi_connect_tool_surface.credentials_read") == "0"
        and fields.get("wifi_connect_tool_surface.scan_connect_executed") == "0"
        and fields.get("wifi_connect_tool_surface.external_ping_executed") == "0"
    )

    if not manifest.get("test_flash_ok") or not rollback_ok:
        label = "connect-tool-surface-handoff-incomplete"
        passed = False
        reason = "test boot or rollback did not complete"
    elif hook_fields.get("helper_stage.ok") != "1" or hook_fields.get("helper_verify.ok") != "1":
        label = "connect-tool-surface-scan-helper-stage-failed"
        passed = False
        reason = "scan helper was not staged and verified"
    elif not no_credentials:
        label = "connect-tool-surface-safety-violation"
        passed = False
        reason = "surface output did not preserve no-credentials/no-connect contract"
    elif not wlan0_seen or not link_up_ok or not scan_ok:
        label = "connect-tool-surface-prereq-wlan0-scan-failed"
        passed = False
        reason = f"wlan0_seen={wlan0_seen} link_up={link_up_ok} scan={scan_result} count={scan_count}"
    elif not surface_invoked:
        label = "connect-tool-surface-not-invoked"
        passed = False
        reason = "connect-tool-surface helper was not invoked"
    elif surface_rc == 0 and surface_result_name == "connect-tools-ready" and supplicant_ready and dhcp_ready and ping_ready:
        label = "connect-tool-surface-ready-after-wlan0-scan"
        passed = True
        reason = "supplicant, DHCP, and ping tools are ready in the native wlan0 window"
    else:
        label = "connect-tool-surface-missing-after-wlan0-scan"
        passed = False
        reason = (
            f"surface_rc={surface_rc} result={surface_result_name or 'missing'} "
            f"supplicant={supplicant_ready} dhcp={dhcp_ready} ping={ping_ready}"
        )

    return {
        "label": label,
        "decision": f"v2149-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "wlan0_seen": wlan0_seen,
        "pre_operstate": fields.get("v2149.pre_operstate", ""),
        "pre_flags": fields.get("v2149.pre_flags", ""),
        "post_operstate": fields.get("v2149.post_operstate", ""),
        "post_carrier": fields.get("v2149.post_carrier", ""),
        "post_flags": fields.get("v2149.post_flags", ""),
        "link_up_ok": link_up_ok,
        "scan_result": scan_result,
        "scan_count": scan_count,
        "surface_invoked": surface_invoked,
        "surface_rc": surface_rc,
        "surface_result": surface_result_name,
        "supplicant_ready": supplicant_ready,
        "dhcp_ready": dhcp_ready,
        "ping_ready": ping_ready,
        "no_credentials": no_credentials,
        "helper_stage_ok": hook_fields.get("helper_stage.ok") == "1",
        "helper_verify_ok": hook_fields.get("helper_verify.ok") == "1",
        "cleanup_ok": bool(surface_result.get("cleanup_ok")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    gate = manifest["connect_surface_gate"]
    helper = manifest.get("helper_build") or {}
    steps = manifest["steps"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['stdout_file']}`"
        for step in steps
    ]
    return "\n".join([
        "# Native Init V2149 Connect Tool Surface Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2149`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Gate Results",
        "",
        f"- `wlan0_seen`: `{gate['wlan0_seen']}` link_up_ok `{gate['link_up_ok']}`",
        f"- `pre_operstate`: `{gate['pre_operstate']}` flags `{gate['pre_flags']}`",
        f"- `post_operstate`: `{gate['post_operstate']}` carrier `{gate['post_carrier']}` flags `{gate['post_flags']}`",
        f"- `scan_result`: `{gate['scan_result']}` scan_count `{gate['scan_count']}`",
        f"- `surface_invoked`: `{gate['surface_invoked']}` rc `{gate['surface_rc']}` result `{gate['surface_result']}`",
        f"- `supplicant_ready`: `{gate['supplicant_ready']}` dhcp_ready `{gate['dhcp_ready']}` ping_ready `{gate['ping_ready']}`",
        f"- `no_credentials`: `{gate['no_credentials']}`",
        f"- `helper_stage_ok`: `{gate['helper_stage_ok']}` verify `{gate['helper_verify_ok']}`",
        f"- `helper_sha256`: `{helper.get('sha256', '')}`",
        "",
        "## Reframe",
        "",
        "- V2148 proved primary `wlan0` accepts link-up and returns redacted BSS entries through nl80211.",
        "- V2149 keeps the same native window and only asks whether the real connect tools are available; it still does not read SSID/PSK or connect.",
        "- If this passes, the next bounded unit can write a private `/cache/a90-wifi` config, start supplicant, run DHCP, and ping with redacted outputs.",
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
        "- EFS was mounted read-only only for pre-HDD MAC assignment; no EFS, persist, firmware, boot, or partition file was written.",
        "",
    ])


def check_forbidden_output(summary: str) -> list[str]:
    hits: list[str] = []
    if re.search(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", summary):
        hits.append("mac")
    return hits


def main() -> int:
    store = base.EvidenceStore(OUT_DIR)
    bootstrap_steps: list[dict[str, Any]] = []
    helper_build = scanbase.build_helper(store, bootstrap_steps)
    prestage_fields = scanbase.stage_helper_binary(store, bootstrap_steps, helper_build)

    def hook(hook_store: base.EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
        steps.extend(bootstrap_steps)
        return post_flash_surface(hook_store, steps, helper_build, prestage_fields)

    manifest = base.run_handoff(
        cycle=CYCLE,
        out_dir=OUT_DIR,
        report_path=REPORT_PATH,
        post_flash_hook=hook,
    )
    store = base.EvidenceStore(OUT_DIR)
    steps = manifest["steps"]
    surface_result = collect_post_rollback_surface(store, steps)
    gate = collect_gate(manifest, surface_result)
    manifest = {
        **manifest,
        "decision": gate["decision"],
        "label": gate["label"],
        "pass": gate["pass"],
        "reason": gate["reason"],
        "helper_build": helper_build,
        "post_rollback_surface_result": surface_result,
        "connect_surface_gate": gate,
        "steps": steps,
        "credentials_read": False,
        "connect_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
    }
    summary = render_report(manifest)
    forbidden_hits = check_forbidden_output(summary)
    manifest["forbidden_output_hits"] = forbidden_hits
    if forbidden_hits:
        manifest["decision"] = "v2149-forbidden-output-hit"
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
        "connect_surface_gate": gate,
        "forbidden_output_hits": forbidden_hits,
    }, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
