#!/usr/bin/env python3
"""V2148 bounded wlan0 link-up plus one nl80211 scan on the V2137/V2146 route."""

from __future__ import annotations

import base64
import gzip
import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as base
import native_wifi_qcacld_fwclass_global_mac_assign_handoff_v2146 as macbase


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V2148"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2148-wlan0-linkup-scan-handoff"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2148_WLAN0_LINKUP_SCAN_HANDOFF_2026-06-05.md"
)
HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_nl80211_scan_once.c"
HELPER_BUILD_DIR = OUT_DIR / "host-build"
HELPER_LOCAL = HELPER_BUILD_DIR / "a90_nl80211_scan_once_v2148"
HELPER_REMOTE = "/cache/bin/a90_nl80211_scan_once_v2148"
HELPER_REMOTE_B64 = "/cache/a90-nl80211-scan-v2148.gz.b64"
HELPER_REMOTE_GZ = "/cache/a90-nl80211-scan-v2148.gz"
SCAN_SCRIPT = "/cache/a90-v2148-linkup-scan.sh"
SCAN_RESULT = "/cache/a90-v2148-linkup-scan.result"
CHUNK_SIZE = 512


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def protocol_payload(text: str) -> str:
    return macbase.protocol_payload(text)


def parse_result_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in protocol_payload(text).splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def build_helper(store: base.EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    HELPER_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        "aarch64-linux-gnu-gcc",
        "-static",
        "-Os",
        "-s",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-o",
        str(HELPER_LOCAL),
        str(HELPER_SOURCE),
    ]
    result = base.run_command(command, timeout=120)
    base.write_step(store, steps, "host-build-nl80211-scan-helper", result)
    if not result["ok"]:
        return {"ok": False, "sha256": "", "gzip_len": 0, "chunks": 0}
    helper_sha = base.sha256(HELPER_LOCAL)
    gzip_bytes = gzip.compress(HELPER_LOCAL.read_bytes(), compresslevel=9)
    (HELPER_BUILD_DIR / "a90_nl80211_scan_once_v2148.gz").write_bytes(gzip_bytes)
    return {
        "ok": True,
        "sha256": helper_sha,
        "gzip_len": len(gzip_bytes),
        "chunks": (len(base64.b64encode(gzip_bytes)) + CHUNK_SIZE - 1) // CHUNK_SIZE,
    }


def compact_step(store: base.EvidenceStore,
                 steps: list[dict[str, Any]],
                 name: str,
                 *,
                 command: list[str],
                 ok: bool,
                 rc: int,
                 stdout: str,
                 stderr: str = "") -> None:
    result = {
        "command": command,
        "started": base.now_iso(),
        "ended": base.now_iso(),
        "timeout": False,
        "rc": rc,
        "ok": ok,
        "stdout": stdout,
        "stderr": stderr,
    }
    base.write_step(store, steps, name, result)


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


def stage_helper_binary(store: base.EvidenceStore,
                        steps: list[dict[str, Any]],
                        helper_build: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {
        "helper_stage.begin": "1",
        "helper_stage.remote": HELPER_REMOTE,
        "helper_stage.local_sha256": str(helper_build.get("sha256") or ""),
        "helper_stage.gzip_len": str(helper_build.get("gzip_len") or "0"),
    }
    if not helper_build.get("ok"):
        fields["helper_stage.ok"] = "0"
        fields["helper_stage.reason"] = "host-build-failed"
        return fields

    run_step(
        store,
        steps,
        "scan-helper-stage-clean",
        ["run", "/cache/bin/busybox", "rm", "-f", HELPER_REMOTE, HELPER_REMOTE_B64, HELPER_REMOTE_GZ],
    )
    run_step(
        store,
        steps,
        "scan-helper-stage-touch",
        ["run", "/cache/bin/busybox", "touch", HELPER_REMOTE_B64],
    )
    gzip_bytes = gzip.compress(HELPER_LOCAL.read_bytes(), compresslevel=9)
    encoded = base64.b64encode(gzip_bytes).decode("ascii")
    chunks = [encoded[index:index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
    chunk_log: list[str] = []
    all_ok = True
    for index, chunk in enumerate(chunks):
        shell = f"printf '%s' {shlex.quote(chunk)} >> {HELPER_REMOTE_B64}"
        result = base.run_command(
            base.a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", shell], timeout=45),
            timeout=60,
        )
        ok = bool(result.get("ok"))
        all_ok = all_ok and ok
        chunk_log.append(f"chunk={index} rc={result.get('rc')} ok={ok} timeout={result.get('timeout')}")
        if not ok:
            break
    compact_step(
        store,
        steps,
        "scan-helper-stage-b64-chunks",
        command=["stage-base64-gzip", HELPER_REMOTE_B64, f"chunks={len(chunks)}"],
        ok=all_ok,
        rc=0 if all_ok else 1,
        stdout="\n".join(chunk_log) + "\n",
    )
    fields["helper_stage.chunks"] = str(len(chunks))
    fields["helper_stage.chunks_ok"] = "1" if all_ok else "0"
    if not all_ok:
        fields["helper_stage.ok"] = "0"
        fields["helper_stage.reason"] = "chunk-stage-failed"
        return fields

    decode_script = (
        f"set -e; "
        f"/cache/bin/busybox base64 -d {HELPER_REMOTE_B64} > {HELPER_REMOTE_GZ}; "
        f"/cache/bin/busybox zcat {HELPER_REMOTE_GZ} > {HELPER_REMOTE}; "
        f"/cache/bin/busybox chmod 700 {HELPER_REMOTE}; "
        f"printf 'helper_stage.remote_sha256='; /cache/bin/busybox sha256sum {HELPER_REMOTE} | /cache/bin/busybox awk '{{print $1}}'; "
        f"/cache/bin/busybox rm -f {HELPER_REMOTE_B64} {HELPER_REMOTE_GZ}; "
        f"echo helper_stage.decode_ok=1"
    )
    decode = run_step(
        store,
        steps,
        "scan-helper-stage-decode",
        ["run", "/cache/bin/busybox", "sh", "-c", decode_script],
        timeout=120,
        bridge_timeout=90,
    )
    fields.update(base.parse_key_values(str(decode.get("stdout") or "")))
    fields["helper_stage.ok"] = "1" if decode.get("ok") and fields.get("helper_stage.remote_sha256") == fields["helper_stage.local_sha256"] else "0"
    fields["helper_stage.reason"] = "ok" if fields["helper_stage.ok"] == "1" else "decode-or-sha-mismatch"
    return fields


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
    }
    run_step(store, steps, "scan-script-clean", ["run", "/cache/bin/busybox", "rm", "-f", SCAN_SCRIPT, SCAN_RESULT])
    run_step(store, steps, "scan-script-touch", ["run", "/cache/bin/busybox", "touch", SCAN_SCRIPT])
    script_lines = [
        "#!/cache/bin/busybox sh",
        f"out={SCAN_RESULT}",
        f"helper={HELPER_REMOTE}",
        "echo v2148.begin=1 > \"$out\"",
        "echo v2148.credentials=0 >> \"$out\"",
        "echo v2148.connect=0 >> \"$out\"",
        "echo v2148.dhcp_routing=0 >> \"$out\"",
        "echo v2148.external_ping=0 >> \"$out\"",
        "loop=0",
        "while [ \"$loop\" -lt 1200 ]; do",
        "if [ -e /sys/class/net/wlan0 ]; then echo v2148.wlan0_seen=1 >> \"$out\"; break; fi",
        "loop=$((loop+1))",
        "sleep 0.2",
        "done",
        "if [ ! -e /sys/class/net/wlan0 ]; then echo v2148.wlan0_seen=0 >> \"$out\"; echo v2148.result=wlan0-missing >> \"$out\"; echo v2148.end=1 >> \"$out\"; exit 20; fi",
        "printf 'v2148.pre_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2148.pre_carrier=' >> \"$out\"; cat /sys/class/net/wlan0/carrier >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2148.pre_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "/cache/bin/busybox ip link set wlan0 up >> \"$out\" 2>&1",
        "echo v2148.link_up_rc=$? >> \"$out\"",
        "sleep 1",
        "printf 'v2148.post_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2148.post_carrier=' >> \"$out\"; cat /sys/class/net/wlan0/carrier >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2148.post_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "echo v2148.scan_invoked=1 >> \"$out\"",
        "\"$helper\" wlan0 6000 >> \"$out\" 2>&1",
        "echo v2148.scan_helper_rc=$? >> \"$out\"",
        "echo v2148.end=1 >> \"$out\"",
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


def verify_staged_helper(store: base.EvidenceStore,
                         steps: list[dict[str, Any]],
                         helper_build: dict[str, Any]) -> dict[str, str]:
    expected_sha = str(helper_build.get("sha256") or "")
    fields: dict[str, str] = {
        "helper_verify.begin": "1",
        "helper_verify.remote": HELPER_REMOTE,
        "helper_verify.expected_sha256": expected_sha,
    }
    script = (
        f"test -x {HELPER_REMOTE}; "
        "echo helper_verify.executable_rc=$?; "
        f"printf 'helper_verify.remote_sha256='; "
        f"/cache/bin/busybox sha256sum {HELPER_REMOTE} 2>/dev/null | /cache/bin/busybox awk '{{print $1}}'"
    )
    result = run_step(
        store,
        steps,
        "scan-helper-verify-prestaged",
        ["run", "/cache/bin/busybox", "sh", "-c", script],
        timeout=60,
        bridge_timeout=45,
    )
    fields.update(base.parse_key_values(str(result.get("stdout") or "")))
    fields["helper_verify.ok"] = (
        "1"
        if result.get("ok")
        and fields.get("helper_verify.executable_rc") == "0"
        and fields.get("helper_verify.remote_sha256") == expected_sha
        else "0"
    )
    return fields


def post_flash_linkup_scan(store: base.EvidenceStore,
                           steps: list[dict[str, Any]],
                           helper_build: dict[str, Any],
                           prestage_fields: dict[str, str]) -> dict[str, Any]:
    mac_hook = macbase.post_flash_mac_assign(store, steps)
    helper_fields = verify_staged_helper(store, steps, helper_build)
    scan_fields = stage_scan_script(store, steps)
    ok = (
        prestage_fields.get("helper_stage.ok") == "1"
        and helper_fields.get("helper_verify.ok") == "1"
        and scan_fields.get("scan_script.ok") == "1"
    )
    return {
        "ok": ok,
        "mac_hook": mac_hook,
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
    wlan0_present = bool(clean.get("wlan0_present")) or scan_fields.get("v2148.wlan0_seen") == "1"
    link_up_rc = base.intish(scan_fields.get("v2148.link_up_rc"))
    link_up_ok = link_up_rc == 0
    scan_invoked = scan_fields.get("v2148.scan_invoked") == "1"
    trigger_attempted = scan_fields.get("nl80211_scan_once.trigger_attempted") == "1"
    trigger_ok = scan_fields.get("nl80211_scan_once.trigger_rc") == "0"
    scan_result_name = scan_fields.get("nl80211_scan_once.result", "")
    scan_count = base.intish(scan_fields.get("nl80211_scan_once.scan_result_count"))
    helper_rc = base.intish(scan_fields.get("v2148.scan_helper_rc"))
    no_credentials = (
        scan_fields.get("v2148.credentials") == "0"
        and scan_fields.get("v2148.connect") == "0"
        and scan_fields.get("v2148.dhcp_routing") == "0"
        and scan_fields.get("v2148.external_ping") == "0"
        and scan_fields.get("nl80211_scan_once.credentials") == "0"
        and scan_fields.get("nl80211_scan_once.connect") == "0"
        and scan_fields.get("nl80211_scan_once.dhcp_routing") == "0"
        and scan_fields.get("nl80211_scan_once.external_ping") == "0"
    )
    cfg80211_seen = "cfg80211" in combined_dmesg.lower()
    regulatory_seen = "regulatory" in combined_dmesg.lower()
    platform_mac = "using MAC address from platform driver" in combined_dmesg
    default_mac = "using default MAC address" in combined_dmesg

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
    elif not no_credentials:
        label = "wlan0-linkup-scan-safety-violation"
        passed = False
        reason = "scan gate output did not preserve the no-credentials/no-connect contract"
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
        "decision": f"v2148-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "wlan0_present": wlan0_present,
        "pre_operstate": scan_fields.get("v2148.pre_operstate", ""),
        "pre_carrier": scan_fields.get("v2148.pre_carrier", ""),
        "pre_flags": scan_fields.get("v2148.pre_flags", ""),
        "post_operstate": scan_fields.get("v2148.post_operstate", ""),
        "post_carrier": scan_fields.get("v2148.post_carrier", ""),
        "post_flags": scan_fields.get("v2148.post_flags", ""),
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
        "cfg80211_seen": cfg80211_seen,
        "regulatory_seen": regulatory_seen,
        "platform_mac": platform_mac,
        "default_mac": default_mac,
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
        "# Native Init V2148 wlan0 Link-Up Scan Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2148`",
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
        f"- `no_credentials`: `{gate['no_credentials']}`",
        f"- `helper_stage_ok`: `{gate['helper_stage_ok']}` verify `{gate['helper_verify_ok']}` reason `{gate['helper_stage_reason']}`",
        "",
        "## Driver Context",
        "",
        f"- `icnss_state_line`: `{gate['icnss_state_line']}`",
        f"- `cfg80211_seen`: `{gate['cfg80211_seen']}` regulatory_seen `{gate['regulatory_seen']}`",
        f"- `platform_mac`: `{gate['platform_mac']}` default_mac `{gate['default_mac']}`",
        f"- `helper_sha256`: `{helper.get('sha256', '')}` gzip_len `{helper.get('gzip_len', 0)}` chunks `{helper.get('chunks', 0)}`",
        "",
        "## Reframe",
        "",
        "- This gate accepts the current V2137/V2146 native path where `wlan0` exists and tests the next functional boundary only.",
        "- The only interface mutation is bounded `ip link set wlan0 up`; the only Wi-Fi operation is one nl80211 scan trigger plus redacted BSS count dump.",
        "- `set_features() failed (-11)` and secondary `swlan0` symptoms are not chased here unless the primary `wlan0` scan fails.",
        "- Credentials, association/connect, DHCP/routes, and external ping remain blocked until this scan-only gate passes.",
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
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- EFS was mounted read-only only for pre-HDD MAC assignment; no EFS, persist, firmware, boot, or partition file was written.",
        "",
    ])


def check_forbidden_output(summary: str) -> list[str]:
    patterns = [
        r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
    ]
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, summary):
            hits.append(pattern)
    return hits


def main() -> int:
    store = base.EvidenceStore(OUT_DIR)
    bootstrap_steps: list[dict[str, Any]] = []
    helper_build = build_helper(store, bootstrap_steps)
    prestage_fields = stage_helper_binary(store, bootstrap_steps, helper_build)

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
    }
    summary = render_report(manifest)
    forbidden_hits = check_forbidden_output(summary)
    manifest["forbidden_output_hits"] = forbidden_hits
    if forbidden_hits:
        manifest["decision"] = "v2148-forbidden-output-hit"
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
