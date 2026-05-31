#!/usr/bin/env python3
"""V1339 bounded Android-order pre-CNSS provider observer live gate.

Starts the Android-observed pre-CNSS provider chain with helper v278 and keeps
the test observe-only: no manual /dev/subsys_esoc0 open, no Wi-Fi HAL, no scan
or connect, no DHCP/routes, and no external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import native_wifi_esoc_node_parity_preflight_v855 as v855
import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1339-android-pre-cnss-provider-observer-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1339-android-pre-cnss-provider-observer-live.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LOCAL_HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe_v278")
DEFAULT_HELPER_SHA256 = "dd4f9996f5798a09498d4f7ce2f4e0385c161cc793e0ce0c96db284863f9d1e7"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v278"
DEFAULT_TOYBOX_TIMEOUT_SEC = 44
DEFAULT_HELPER_TIMEOUT_SEC = 18
MODE = "wifi-companion-android-order-pre-cnss-provider-observe-only"
EXPECTED_ORDER = (
    "servicemanager,hwservicemanager,vndservicemanager,per_proxy_helper,"
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,per_mgr,per_proxy,"
    "mdm_helper,cnss_diag,cnss_daemon"
)
FORBIDDEN_TRUE_KEYS = (
    "wifi_companion_start.wifi_hal",
    "wifi_companion_start.wificond",
    "wifi_companion_start.qcwlanstate_write",
    "wifi_companion_start.scan_connect_linkup",
    "wifi_companion_start.external_ping",
    "wifi_companion_start.subsys_esoc0_manual_open_attempted",
)
FORBIDDEN_PRESENT_PATTERNS = ()
ACTOR_RE = re.compile(
    r"\b(pm_proxy_helper|pm-service|pm-proxy|mdm_helper|cnss_diag|cnss-daemon|"
    r"qrtr-ns|rmt_storage|tftp_server|pd-mapper|servicemanager|hwservicemanager|"
    r"vndservicemanager|wificond|supplicant|hostapd|android\.hardware\.wifi|"
    r"vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v857.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v857.DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=v857.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v857.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--helper-timeout-sec", type=int, default=DEFAULT_HELPER_TIMEOUT_SEC)
    parser.add_argument("--toybox-timeout-sec", type=int, default=DEFAULT_TOYBOX_TIMEOUT_SEC)
    parser.add_argument("--allow-mountsystem-ro", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-android-pre-cnss-provider-observe-only", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--no-hide-on-busy", dest="hide_on_busy", action="store_false")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def read_step_file(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = str(step.get("file") or "")
    path = store.run_dir / rel
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return str(step.get("payload") or "")


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {"path": str(path), "exists": path.exists(), "sha256": "", "marker": False, "mode": False}
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    strings = subprocess.run(
        ["strings", str(path)],
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
    ).stdout
    info["marker"] = args.helper_marker in strings
    info["mode"] = MODE in strings
    return info


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-mountsystem-ro", args.allow_mountsystem_ro),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        (
            "--allow-android-pre-cnss-provider-observe-only",
            args.allow_android_pre_cnss_provider_observe_only,
        ),
        ("--allow-cleanup-reboot", args.allow_cleanup_reboot),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def helper_command(args: argparse.Namespace) -> list[str]:
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
        MODE,
        "--allow-wifi-companion-start-only",
        "--allow-cnss-start-only",
        "--allow-service-manager-start-only",
        "--timeout-sec",
        str(min(max(args.helper_timeout_sec, 6), 30)),
        "--property-root",
        v857.PROPERTY_ROOT,
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        v857.REAL_LD_CONFIG,
        "--apex-libraries-source",
        v857.REAL_APEX_LIBRARIES,
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--android-selinux-context-mode",
        "service-defaults",
    ]


def remote_helper_state(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    sha = v857.run_device(args, store, steps, "remote-helper-sha", ["run", args.toybox, "sha256sum", args.helper], timeout=12.0)
    usage = v857.run_device(args, store, steps, "remote-helper-usage", ["run", args.helper], timeout=12.0)
    sha_payload = read_step_file(store, sha)
    usage_payload = read_step_file(store, usage)
    return {
        "sha_ok": args.helper_sha256 in sha_payload,
        "marker_ok": args.helper_marker in usage_payload,
        "mode_ok": MODE in usage_payload,
        "sha_file": sha.get("file"),
        "usage_file": usage.get("file"),
    }


def mount_selinuxfs(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    script = (
        "$BB mkdir -p /sys/fs/selinux; "
        "if ! $BB cat /proc/mounts 2>/dev/null | $BB grep -q ' /sys/fs/selinux '; then "
        "$BB mount -t selinuxfs selinuxfs /sys/fs/selinux 2>&1 || true; "
        "fi; "
        "$BB cat /proc/mounts 2>/dev/null | $BB grep -i selinux || true; "
        "$BB ls -l /sys/fs/selinux/status /sys/fs/selinux/enforce 2>&1 || true"
    ).replace("$BB", args.busybox)
    v857.run_device(args, store, steps, "selinuxfs-mount", v855.shell_cmd(args, script), timeout=20.0)


def post_surface(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    ps = v857.run_device(args, store, steps, f"{prefix}-ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=20.0)
    net = v857.run_device(args, store, steps, f"{prefix}-proc-net-dev", ["cat", "/proc/net/dev"], timeout=12.0)
    qrtr = v857.run_device(
        args,
        store,
        steps,
        f"{prefix}-proc-net-qrtr",
        v855.shell_cmd(args, "$BB cat /proc/net/qrtr 2>/dev/null || true".replace("$BB", args.busybox)),
        timeout=12.0,
    )
    dmesg = v857.run_device(
        args,
        store,
        steps,
        f"{prefix}-dmesg-wifi-esoc-tail",
        v855.shell_cmd(
            args,
            (
                "$BB dmesg 2>&1 | "
                "$BB grep -iE 'esoc|mdm|subsys|wlan|wlfw|qmi|qrtr|mhi|icnss|cnss|bdf|gpio|ap2mdm|mdm2ap|pm-service|pm-proxy|mdm_helper' | "
                "$BB tail -n 260 || true"
            ).replace("$BB", args.busybox),
        ),
        timeout=24.0,
    )
    ps_text = read_step_file(store, ps)
    net_text = read_step_file(store, net)
    qrtr_text = read_step_file(store, qrtr)
    dmesg_text = read_step_file(store, dmesg)
    return {
        "actor_hits": [line.strip() for line in ps_text.splitlines() if ACTOR_RE.search(line)][:40],
        "wifi_link_hits": [line.strip() for line in net_text.splitlines() if WIFI_RE.search(line)][:16],
        "qrtr_wlfw_hits": [line.strip() for line in qrtr_text.splitlines() if re.search(r"\b69\b|wlfw", line, re.IGNORECASE)][:16],
        "dmesg_focus_hits": [
            line.strip()
            for line in dmesg_text.splitlines()
            if re.search(r"wlfw|wlan0|bdf|fw ready|qmi|qrtr|mdm|esoc|subsys|mhi|gpio|ap2mdm|mdm2ap|pm-service|pm-proxy|mdm_helper", line, re.IGNORECASE)
        ][-80:],
    }


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    forbidden_true = {
        key: keys.get(key)
        for key in FORBIDDEN_TRUE_KEYS
        if keys.get(key) not in (None, "0")
    }
    forbidden_terms = [term for term in FORBIDDEN_PRESENT_PATTERNS if term in text]
    return {
        "keys": keys,
        "contract": {
            "begin": keys.get("wifi_companion_start.begin", ""),
            "allowed": keys.get("wifi_companion_start.allowed", ""),
            "order": keys.get("wifi_companion_start.order", ""),
            "child_started": keys.get("wifi_companion_start.child_started", ""),
            "result": keys.get("wifi_companion_start.result", ""),
            "reason": keys.get("wifi_companion_start.reason", ""),
            "timed_out": keys.get("wifi_companion_start.timed_out", ""),
            "all_observable": keys.get("wifi_companion_start.all_observable", ""),
            "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", ""),
            "android_pre_cnss_provider_observe_only": keys.get("wifi_companion_start.android_pre_cnss_provider_observe_only", ""),
            "manual_subsys_esoc0_open": keys.get("wifi_companion_start.subsys_esoc0_manual_open_attempted", ""),
            "wifi_hal": keys.get("wifi_companion_start.wifi_hal", ""),
            "wificond": keys.get("wifi_companion_start.wificond", ""),
            "scan_connect_linkup": keys.get("wifi_companion_start.scan_connect_linkup", ""),
            "external_ping": keys.get("wifi_companion_start.external_ping", ""),
            "per_mgr_subsys_esoc0_window": keys.get("mdm_helper_queue_timing.android_pre_cnss_provider_window.per_mgr_subsys_esoc0_count", ""),
            "mdm_helper_subsys_esoc0_window": keys.get("mdm_helper_queue_timing.android_pre_cnss_provider_window.mdm_helper_subsys_esoc0_count", ""),
            "mdm_helper_esoc0_window": keys.get("mdm_helper_queue_timing.android_pre_cnss_provider_window.mdm_helper_esoc0_count", ""),
            "ks_window": keys.get("mdm_helper_queue_timing.android_pre_cnss_provider_window.ks_count", ""),
            "mhi_cmdline_window": keys.get("mdm_helper_queue_timing.android_pre_cnss_provider_window.mhi_cmdline_count", ""),
        },
        "forbidden_true": forbidden_true,
        "forbidden_terms": forbidden_terms,
    }


def run_a90ctl_capture(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    result = subprocess.run(
        ["python3", "scripts/revalidation/a90ctl.py", *command],
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    output = v857.redact(result.stdout)
    rel = f"reboot_cleanup/{safe_name(name)}.txt"
    store.write_text(rel, output.rstrip() + "\n")
    return {"name": name, "rc": result.returncode, "ok": result.returncode == 0, "file": rel, "output": output[-4096:]}


def reboot_cleanup(args: argparse.Namespace, store: EvidenceStore, reason: str) -> dict[str, Any]:
    cleanup: dict[str, Any] = {
        "requested": True,
        "reason": reason,
        "reboot_command": None,
        "attempts": [],
        "bootstatus_ok": False,
        "selftest_fail0": False,
        "healthy": False,
    }
    try:
        cleanup["reboot_command"] = run_a90ctl_capture(store, "reboot-command", ["--timeout", "3", "--allow-error", "--retry-unsafe", "reboot"], timeout=6.0)
    except subprocess.TimeoutExpired as exc:
        rel = "reboot_cleanup/reboot-command-timeout.txt"
        store.write_text(rel, (exc.stdout or "") + "\n[TIMEOUT]\n")
        cleanup["reboot_command"] = {"name": "reboot-command", "rc": -1, "ok": False, "file": rel, "output": "timeout"}
    for attempt in range(1, 31):
        time.sleep(2.0)
        boot = run_a90ctl_capture(store, f"post-reboot-bootstatus-{attempt:02d}", ["--timeout", "7", "--json", "bootstatus"], timeout=10.0)
        selftest = run_a90ctl_capture(store, f"post-reboot-selftest-{attempt:02d}", ["--timeout", "7", "--json", "selftest"], timeout=10.0)
        boot_ok = boot["ok"] and ("BOOT OK" in boot["output"] or '"status": "ok"' in boot["output"])
        selftest_ok = selftest["ok"] and ("fail=0" in selftest["output"] or "fail=0" in selftest["output"].replace("\\n", "\n"))
        cleanup["attempts"].append({"attempt": attempt, "bootstatus": boot, "selftest": selftest, "boot_ok": boot_ok, "selftest_ok": selftest_ok})
        if boot_ok and selftest_ok:
            cleanup["bootstatus_ok"] = True
            cleanup["selftest_fail0"] = True
            cleanup["healthy"] = True
            break
    return cleanup


def execute(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    v857.run_device(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    if args.allow_mountsystem_ro:
        v857.run_device(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    if args.allow_selinuxfs_mount:
        mount_selinuxfs(args, store, steps)
    analysis["remote_helper"] = remote_helper_state(args, store, steps)
    analysis["pre_surface"] = post_surface(args, store, steps, "pre")
    helper_step = v857.run_device(args, store, steps, "android-pre-cnss-provider-observer", helper_command(args), timeout=args.toybox_timeout_sec + 25.0)
    helper_text = read_step_file(store, helper_step)
    analysis["helper"] = helper_surface(helper_text)
    analysis["post_surface"] = post_surface(args, store, steps, "post")
    v857.run_device(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    v857.run_device(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)

    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    post = analysis.get("post_surface") or {}
    cleanup_needed = (
        contract.get("all_postflight_safe") == "0"
        or bool([line for line in post.get("actor_hits", []) if "a90_android_execns_probe" in line])
    )
    analysis["cleanup_needed"] = cleanup_needed
    if cleanup_needed and args.allow_cleanup_reboot:
        analysis["reboot_cleanup"] = reboot_cleanup(args, store, "android-order pre-CNSS provider actor not proven stopped")
    elif cleanup_needed:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "cleanup needed but --allow-cleanup-reboot not set", "healthy": False}
    else:
        analysis["reboot_cleanup"] = {"requested": False, "reason": "not needed", "healthy": True}
    return steps, analysis


def step_failures(steps: list[dict[str, Any]], helper: dict[str, Any]) -> list[str]:
    contract = helper.get("contract") or {}
    helper_has_evidence = contract.get("begin") == "1"
    ignored = {"remote-helper-usage"}
    if helper_has_evidence:
        ignored.add("android-pre-cnss-provider-observer")
    return [step["name"] for step in steps if not step.get("ok") and step.get("name") not in ignored]


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1339-plan-helper-v278-missing", False, f"local={local}", "build and deploy helper v278 before V1339"
        return "v1339-android-pre-cnss-provider-observer-plan-ready", True, "plan-only; no device command executed", "run bounded V1339 live observer"
    missing = required_flags(args)
    if missing:
        return "v1339-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1339 flags"
    helper = analysis.get("helper") or {}
    failed_steps = step_failures(steps, helper)
    if failed_steps:
        return "v1339-step-failed", False, f"failed_steps={failed_steps}", "inspect V1339 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1339-helper-v278-remote-mismatch", False, f"remote={remote}", "redeploy helper v278 before V1339"
    if helper.get("forbidden_true"):
        return "v1339-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    if helper.get("forbidden_terms"):
        return "v1339-forbidden-term-detected", False, f"terms={helper.get('forbidden_terms')}", "stop and audit helper output before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1339-helper-mode-not-executed", False, f"contract={contract}", "fix V1339 helper command before retry"
    if contract.get("order") != EXPECTED_ORDER or contract.get("android_pre_cnss_provider_observe_only") != "1":
        return "v1339-helper-contract-gap", False, f"contract={contract}", "audit helper v278 V1337 mode wiring"
    if contract.get("manual_subsys_esoc0_open") != "0":
        return "v1339-manual-esoc-open-violation", False, f"contract={contract}", "stop and audit helper before retry"
    cleanup = analysis.get("reboot_cleanup") or {}
    if analysis.get("cleanup_needed") and not cleanup.get("healthy"):
        return "v1339-reboot-cleanup-review", False, f"cleanup={cleanup}", "verify native recovery before continuing"

    auto_open = contract.get("per_mgr_subsys_esoc0_window") not in ("", "-1", "0")
    ks_seen = contract.get("ks_window") not in ("", "-1", "0") or contract.get("mhi_cmdline_window") not in ("", "-1", "0")
    post = analysis.get("post_surface") or {}
    wlfw_seen = bool(post.get("qrtr_wlfw_hits")) or any(
        re.search(r"wlfw|bdf|wlan0|fw ready", line, re.IGNORECASE)
        for line in post.get("dmesg_focus_hits", [])
    )
    if wlfw_seen:
        return (
            "v1339-wlfw-surface-observed-without-manual-esoc-open",
            True,
            f"contract={contract}",
            "classify WLFW/BDF/wlan0 surface before any Wi-Fi HAL or scan work",
        )
    if auto_open or ks_seen:
        return (
            "v1339-provider-chain-advanced-to-esoc-or-ks-no-wlfw",
            True,
            f"auto_open={auto_open} ks_seen={ks_seen} contract={contract}",
            "classify why provider-triggered eSoC/ks path still did not publish WLFW",
        )
    return (
        "v1339-pre-cnss-provider-chain-no-wlfw",
        True,
        f"contract={contract}",
        "classify provider-chain child stderr and Android delta before broader runtime changes",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    steps = manifest.get("steps", [])
    step_rows = [[step["name"], step["status"], step["rc"], step["duration_sec"], step["file"]] for step in steps]
    helper = ((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {}
    analysis_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)[:2000]] for key, value in (manifest.get("analysis") or {}).items()]
    return "\n".join([
        "# V1339 Android-order Pre-CNSS Provider Observer Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- mode: `{MODE}`",
        f"- helper_result: `{helper.get('result', '')}`",
        f"- helper_order: `{helper.get('order', '')}`",
        f"- manual_esoc_open_executed: `{manifest['manual_esoc_open_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- cleanup_reboot_executed: `{manifest['cleanup_reboot_executed']}`",
        "",
        "## Analysis",
        "",
        markdown_table(["section", "value"], analysis_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "status", "rc", "duration_sec", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "- Starts only the bounded Android-order pre-CNSS provider/CNSS observer chain.",
        "- No manual `/dev/subsys_esoc0` open, eSoC ioctl/notify/BOOT_DONE, PMIC/GPIO write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not required_flags(args):
        steps, analysis = execute(args, store)
    decision, passed, reason, next_step = decide(args, local, steps, analysis)
    helper = (analysis.get("helper") or {}).get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    wifi_hal_started = str(helper.get("wifi_hal") or "0") != "0"
    scan_connect_started = str(helper.get("scan_connect_linkup") or "0") == "1"
    external_ping_started = str(helper.get("external_ping") or "0") == "1"
    return {
        "cycle": "v1339",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "local_helper": local,
        "steps": steps,
        "analysis": analysis,
        "device_commands_executed": args.command == "run" and not required_flags(args),
        "deploy_executed": False,
        "manual_esoc_open_executed": helper.get("manual_subsys_esoc0_open") == "1",
        "live_esoc_ioctl_executed": False,
        "pm_actor_executed": args.command == "run" and not required_flags(args),
        "cnss_daemon_start_executed": helper.get("child_started", "0") not in ("", "0"),
        "wifi_hal_start_executed": wifi_hal_started,
        "scan_connect_executed": scan_connect_started,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": external_ping_started,
        "wifi_bringup_executed": any(
            (
                wifi_hal_started,
                scan_connect_started,
                external_ping_started,
            )
        ),
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "flash_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"manual_esoc_open_executed: {manifest['manual_esoc_open_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"cleanup_reboot_executed: {manifest['cleanup_reboot_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
