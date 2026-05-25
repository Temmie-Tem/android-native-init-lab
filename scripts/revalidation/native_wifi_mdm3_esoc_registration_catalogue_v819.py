#!/usr/bin/env python3
"""V819 bounded live mdm3/esoc0 registration catalogue.

V818 selected a read-only registration catalogue as the next safe live gate.
This runner reuses the V817 lower-window harness and injects extra read-only
catalogue snapshots at the existing before-holder, after-holder, and
after-companion checkpoints.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_in_window_sysmon_sampler_v817 as v817
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v819-mdm3-esoc-registration-catalogue")
LATEST_POINTER = Path("tmp/wifi/latest-v819-mdm3-esoc-registration-catalogue.txt")
DEFAULT_V818_MANIFEST = Path("tmp/wifi/v818-mdm3-esoc-registration-classifier/manifest.json")
PROOF_PREFIX = "/tmp/a90-v819-"

FORBIDDEN_ACTIONS = (
    "custom kernel flash, boot image write, or partition write",
    "bootloader handoff",
    "esoc0 open, qcwlanstate on/off, bind/unbind, driver override, or module load/unload",
    "service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v817.base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v817.base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v817.base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=v817.base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=v817.base.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=v817.base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v817.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v817.DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=v817.base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=v817.base.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=v817.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=v817.base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=v817.base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=v817.base.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v817.base.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=v817.v735.DEFAULT_V734_MANIFEST)
    parser.add_argument("--v816-manifest", type=Path, default=v817.DEFAULT_V816_MANIFEST)
    parser.add_argument("--v818-manifest", type=Path, default=DEFAULT_V818_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
    if not resolved.exists():
        return {"file": {"path": str(resolved), "exists": False}, "data": {}}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"file": {"path": str(resolved), "exists": True}, "data": {}, "error": str(exc)}
    return {
        "file": {"path": str(resolved), "exists": True, "size": resolved.stat().st_size},
        "data": data if isinstance(data, dict) else {},
    }


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def configure_base() -> None:
    v817.configure_base()
    v817.PROOF_PREFIX = PROOF_PREFIX


REGISTRATION_COMMANDS: tuple[tuple[str, str], ...] = (
    (
        "registration-subsys-state",
        "for p in /sys/bus/msm_subsys/devices/subsys0 /sys/bus/msm_subsys/devices/subsys9 /sys/class/subsys/subsys_modem /sys/class/subsys/subsys_esoc0; do printf '%s\\n' \"## $p\"; $T ls -la \"$p\" 2>&1 || true; for f in name state crash_count restart_level firmware_name uevent; do [ -e \"$p/$f\" ] && { printf '%s\\n' \"FILE $p/$f\"; $T cat \"$p/$f\" 2>&1; }; done; done",
    ),
    (
        "registration-esoc-surface",
        "for p in /sys/bus/esoc/devices /sys/bus/esoc/devices/esoc0 /sys/devices/platform/soc/soc:qcom,mdm3 /sys/devices/platform/soc/soc:qcom,mdm3/esoc0; do printf '%s\\n' \"## $p\"; $T ls -la \"$p\" 2>&1 || true; for f in uevent power/runtime_status power/control; do [ -e \"$p/$f\" ] && { printf '%s\\n' \"FILE $p/$f\"; $T cat \"$p/$f\" 2>&1; }; done; done",
    ),
    (
        "registration-debug-surfaces",
        "for p in /sys/kernel/debug/service_notifier /sys/kernel/debug/service_locator /sys/kernel/debug/servreg /sys/kernel/debug/msm_subsys /sys/kernel/debug/icnss /d/service_notifier /d/service_locator /d/servreg /d/msm_subsys /d/icnss; do printf '%s\\n' \"## $p\"; $T ls -la \"$p\" 2>&1 || true; done",
    ),
    (
        "registration-proc-net",
        "for f in /proc/net/qrtr /proc/net/netlink /proc/net/unix /proc/net/protocols; do printf '%s\\n' \"FILE $f\"; $T cat \"$f\" 2>&1 || true; done",
    ),
    (
        "registration-process-net",
        "for name in qrtr-ns pd-mapper rmt_storage tftp_server cnss_diag cnss-daemon mdm_helper; do for pid in $($T pidof \"$name\" 2>/dev/null); do printf '%s\\n' \"PROCESS $name pid=$pid\"; $T readlink \"/proc/$pid/ns/net\" 2>&1 || true; for f in qrtr netlink unix; do printf '%s\\n' \"FILE /proc/$pid/net/$f\"; $T cat \"/proc/$pid/net/$f\" 2>&1 || true; done; done; done",
    ),
    (
        "registration-dmesg-focus",
        "$T dmesg | $T grep -iE 'service.loc|service-locator|servreg|service-notifier|sysmon|ssctl|mdm3|esoc|wlan_pd|wlfw|icnss|qmi|qrtr' | $T tail -240 || true",
    ),
)


def collect_catalogue(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], phase: str) -> None:
    for name, script in REGISTRATION_COMMANDS:
        command = v817.shell_cmd(args, f"T={args.toybox}; {script}")
        item = v817.run_snapshot_step(args, store, steps, phase, name, command, 20.0)
        item["phase"] = f"{phase}-catalogue"


def install_snapshot_hook() -> Any:
    original = v817.collect_snapshot

    def wrapped(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], phase: str) -> None:
        original(args, store, steps, phase)
        collect_catalogue(args, store, steps, phase)

    v817.collect_snapshot = wrapped
    return original


def restore_snapshot_hook(original: Any) -> None:
    v817.collect_snapshot = original


def payload(steps: list[dict[str, Any]], name: str) -> str:
    return v817.base.step_payload(steps, name)


def count_catalogue(text: str) -> dict[str, int | bool]:
    lower = text.lower()
    return {
        "service_notifier_refs": lower.count("service_notifier") + lower.count("service-notifier"),
        "service_locator_refs": lower.count("service_locator") + lower.count("service-locator") + lower.count("service.loc"),
        "servreg_refs": lower.count("servreg"),
        "sysmon_refs": lower.count("sysmon"),
        "ssctl_refs": lower.count("ssctl"),
        "qrtr_refs": lower.count("qrtr"),
        "qmi_refs": lower.count("qmi"),
        "mdm3_refs": lower.count("mdm3"),
        "esoc_refs": lower.count("esoc"),
        "wlan_pd_refs": lower.count("wlan_pd"),
        "wlfw_refs": lower.count("wlfw"),
        "proc_net_qrtr_missing": "cat: /proc/net/qrtr: no such file or directory" in lower,
        "service_debug_missing": "/sys/kernel/debug/service_notifier" in text and "No such file or directory" in text,
        "process_net_sections": text.count("PROCESS "),
    }


def summarize_catalogues(steps: list[dict[str, Any]]) -> dict[str, Any]:
    phases = ("before-holder", "after-holder", "after-companion")
    summaries: dict[str, Any] = {}
    for phase in phases:
        phase_steps = [
            step for step in steps
            if step.get("phase") == f"{phase}-catalogue"
            and "-registration-" in str(step.get("name", ""))
        ]
        item_payload = "\n".join(str(step.get("payload") or "") for step in phase_steps)
        summaries[phase] = {
            "captured": bool(item_payload),
            "ok": bool(phase_steps) and all(bool(step.get("ok")) for step in phase_steps),
            "files": [step.get("file") for step in phase_steps],
            "counts": count_catalogue(item_payload),
        }
    return summaries


def load_v818(path: Path) -> dict[str, Any]:
    loaded = load_json(path)
    data = loaded["data"]
    return {
        "path": loaded["file"]["path"],
        "exists": loaded["file"]["exists"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
    }


def run_wrapped_v817(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    original = install_snapshot_hook()
    try:
        return v817.build_manifest(args, store)
    finally:
        restore_snapshot_hook(original)


def build_checks(args: argparse.Namespace,
                 v818_input: dict[str, Any],
                 wrapped: dict[str, Any] | None,
                 catalogue: dict[str, Any]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "plan-only; no device command executed",
            "next_step": "run V819 bounded live catalogue",
        }]
    live = as_dict((wrapped or {}).get("live"))
    after_companion = as_dict(catalogue.get("after-companion"))
    after_counts = as_dict(after_companion.get("counts"))
    all_catalogues = all(as_dict(catalogue.get(phase)).get("captured") for phase in ("before-holder", "after-holder", "after-companion"))
    below_hal = not any(bool((wrapped or {}).get(key)) for key in (
        "service_manager_start_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "external_ping_executed",
        "credential_use_executed",
        "custom_kernel_flash_executed",
        "boot_image_write_executed",
        "partition_write_executed",
        "esoc0_open_executed",
        "module_load_unload_executed",
    ))
    return [
        {
            "name": "v818-route-ready",
            "status": "pass" if v818_input["pass"] and v818_input["decision"] == "v818-mdm3-esoc-registration-gap-classified" else "blocked",
            "detail": v818_input,
            "next_step": "restore V818 classifier evidence before V819 live run",
        },
        {
            "name": "wrapped-v817-window",
            "status": "pass" if bool((wrapped or {}).get("pass")) else "blocked",
            "detail": {
                "decision": (wrapped or {}).get("decision"),
                "pass": (wrapped or {}).get("pass"),
                "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_companion")],
                "mdm3": [live.get("mdm3_before"), live.get("mdm3_after_holder"), live.get("mdm3_after_companion")],
            },
            "next_step": "debug V817 lower window if mss/sysmon baseline no longer reproduces",
        },
        {
            "name": "catalogue-completeness",
            "status": "pass" if all_catalogues else "blocked",
            "detail": catalogue,
            "next_step": "rerun V819 if any checkpoint catalogue is missing",
        },
        {
            "name": "below-hal-contract",
            "status": "pass" if below_hal else "blocked",
            "detail": {
                "service_manager": (wrapped or {}).get("service_manager_start_executed"),
                "wifi_hal": (wrapped or {}).get("wifi_hal_start_executed"),
                "scan_connect": (wrapped or {}).get("scan_connect_executed"),
                "external_ping": (wrapped or {}).get("external_ping_executed"),
                "esoc0_open": (wrapped or {}).get("esoc0_open_executed"),
                "module_load_unload": (wrapped or {}).get("module_load_unload_executed"),
            },
            "next_step": "discard run if forbidden action appears",
        },
        {
            "name": "after-companion-registration-signal",
            "status": "finding",
            "detail": after_counts,
            "next_step": "route V820 based on missing debugfs/proc QRTR versus present registration hints",
        },
        {
            "name": "postflight-cleanup",
            "status": "pass" if as_dict(live.get("reboot_cleanup")).get("status_healthy") else "blocked",
            "detail": live.get("reboot_cleanup"),
            "next_step": "restore v724 health before continuing if cleanup failed",
        },
    ]


def decide(args: argparse.Namespace,
           checks: list[dict[str, Any]],
           wrapped: dict[str, Any] | None,
           catalogue: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v819-mdm3-esoc-registration-catalogue-plan-ready",
            True,
            "plan-only; no device command executed",
            "run bounded live registration catalogue",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v819-mdm3-esoc-registration-catalogue-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore health or required evidence before next Wi-Fi gate",
        )
    after_counts = as_dict(as_dict(catalogue.get("after-companion")).get("counts"))
    if after_counts.get("proc_net_qrtr_missing"):
        next_step = "V820 should inspect helper/per-process QRTR namespace state and service-locator visibility without HAL/connect"
    else:
        next_step = "V820 should classify registration catalogue findings before any HAL/connect or credential gate"
    return (
        "v819-mdm3-esoc-registration-catalogue-captured",
        True,
        "bounded V817 lower window plus V819 read-only registration catalogues completed below HAL/connect",
        next_step,
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v818_input = load_v818(args.v818_manifest)
    wrapped: dict[str, Any] | None = None
    catalogue: dict[str, Any] = {}
    if args.command == "run":
        wrapped = run_wrapped_v817(args, store)
        catalogue = summarize_catalogues(wrapped.get("steps", []))
    checks = build_checks(args, v818_input, wrapped, catalogue)
    decision, pass_ok, reason, next_step = decide(args, checks, wrapped, catalogue)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v819",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v818": v818_input,
        "wrapped_v817": wrapped,
        "catalogue": catalogue,
        "checks": checks,
        "device_commands_executed": bool((wrapped or {}).get("device_commands_executed")),
        "device_mutations": bool((wrapped or {}).get("device_mutations")),
        "firmware_mounts_executed": bool((wrapped or {}).get("firmware_mounts_executed")),
        "subsys_modem_opened": bool((wrapped or {}).get("subsys_modem_opened")),
        "lower_companion_start_executed": bool((wrapped or {}).get("lower_companion_start_executed")),
        "cnss_diag_start_executed": bool((wrapped or {}).get("cnss_diag_start_executed")),
        "cnss_daemon_start_executed": bool((wrapped or {}).get("cnss_daemon_start_executed")),
        "reboot_cleanup_executed": bool((wrapped or {}).get("reboot_cleanup_executed")),
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "esoc0_open_executed": False,
        "module_load_unload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    catalogue_rows = [
        [phase, str(item.get("captured")), json.dumps(item.get("counts"), ensure_ascii=False, sort_keys=True)]
        for phase, item in manifest.get("catalogue", {}).items()
    ]
    return "\n".join([
        "# V819 mdm3/esoc0 Registration Catalogue",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Catalogue",
        "",
        markdown_table(["phase", "captured", "counts"], catalogue_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    configure_base()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"esoc0_open_executed: {manifest['esoc0_open_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
