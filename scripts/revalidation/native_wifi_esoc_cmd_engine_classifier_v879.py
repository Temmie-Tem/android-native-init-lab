#!/usr/bin/env python3
"""V879 host-only eSoC CMD engine ownership classifier.

This folds V878's `REG_CMD_ENG` EBUSY / `REG_REQ_ENG` rc0 result into local
Samsung OSRC sources and public msm eSoC references. It does not contact the
device, deploy helpers, execute eSoC ioctls, start actors, bring up Wi-Fi, or
use credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v879-cmd-engine-ownership-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v879-cmd-engine-ownership-classifier.txt")
KERNEL_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")
ESOC_CTRL = KERNEL_ROOT / "include/uapi/linux/esoc_ctrl.h"
ESOC_CLIENT = KERNEL_ROOT / "include/linux/esoc_client.h"
SSR_C = KERNEL_ROOT / "drivers/soc/qcom/subsystem_restart.c"
MHI_ARCH = KERNEL_ROOT / "drivers/bus/mhi/controllers/mhi_arch_qcom.c"
ICNSS_C = KERNEL_ROOT / "drivers/soc/qcom/icnss.c"
CNSS2_MAIN = KERNEL_ROOT / "drivers/net/wireless/cnss2/main.c"
HELPER_C = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
V878_MANIFEST = Path("tmp/wifi/v878-esoc-engine-register-preflight-live/manifest.json")
V878_DMESG = Path("tmp/wifi/v878-esoc-engine-register-preflight-live/host/post-dmesg-esoc.txt")
PUBLIC_ESOC_DEV = "https://android.googlesource.com/kernel/msm/+/d210dd22d8bfbd55a320f57eaac861137dd3eca0%5E2..d210dd22d8bfbd55a320f57eaac861137dd3eca0/"
PUBLIC_ESOC_CTRL = "https://android.googlesource.com/platform/hardware/qcom/msm8994/+/f480e4a/kernel-headers/linux/esoc_ctrl.h"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(payload, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    payload.setdefault("exists", True)
    payload.setdefault("path", str(resolved))
    return payload


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return line_number
    return None


def bool_from(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def nested(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def ioctl_result(manifest: dict[str, Any], name: str) -> dict[str, str]:
    result = nested(manifest, "analysis", "helper", "ioctls", name)
    if not isinstance(result, dict):
        return {"request": "", "rc": "", "errno": ""}
    return {
        "request": str(result.get("request", "")),
        "rc": str(result.get("rc", "")),
        "errno": str(result.get("errno", "")),
    }


def v878_summary() -> dict[str, Any]:
    manifest = load_json(V878_MANIFEST)
    dmesg = read_text(V878_DMESG)
    helper = nested(manifest, "analysis", "helper")
    keys = helper.get("keys", {}) if isinstance(helper, dict) else {}
    forbidden = helper.get("forbidden_true", {}) if isinstance(helper, dict) else {}
    post = nested(manifest, "analysis", "post_surface") or {}
    node = nested(manifest, "analysis", "node") or {}
    cmd = ioctl_result(manifest, "REG_CMD_ENG")
    req = ioctl_result(manifest, "REG_REQ_ENG")
    return {
        "manifest_path": str(repo_path(V878_MANIFEST)),
        "dmesg_path": str(repo_path(V878_DMESG)),
        "manifest_exists": bool_from(manifest.get("exists")),
        "decision": manifest.get("decision"),
        "pass": bool_from(manifest.get("pass")),
        "helper_result": keys.get("result", ""),
        "cmd": cmd,
        "req": req,
        "cmd_ebusy": cmd["rc"] == "-1" and cmd["errno"] == "16",
        "req_ok": req["rc"] == "0" and req["errno"] == "0",
        "forbidden_empty": not bool(forbidden),
        "cleanup_ok": bool_from(nested(node, "cleanup", "removed_all_created")),
        "selftest_fail0": bool_from(nested(node, "postflight", "selftest_fail0")),
        "actor_hits": post.get("actor_hits", []),
        "wifi_link_hits": post.get("wifi_link_hits", []),
        "client_hooks_dmesg": "Client hooks not registered for the device" in dmesg,
        "dmesg_excerpt": [line.strip() for line in dmesg.splitlines() if "Client hooks" in line][:4],
    }


def source_summary() -> dict[str, Any]:
    esoc_ctrl = read_text(ESOC_CTRL)
    esoc_client = read_text(ESOC_CLIENT)
    ssr = read_text(SSR_C)
    mhi = read_text(MHI_ARCH)
    icnss = read_text(ICNSS_C)
    cnss2 = read_text(CNSS2_MAIN)
    helper = read_text(HELPER_C)
    research = read_text(ESOC_RESEARCH)
    return {
        "paths": {
            "esoc_ctrl": {"path": str(repo_path(ESOC_CTRL)), "exists": bool(esoc_ctrl)},
            "esoc_client": {"path": str(repo_path(ESOC_CLIENT)), "exists": bool(esoc_client)},
            "subsystem_restart": {"path": str(repo_path(SSR_C)), "exists": bool(ssr)},
            "mhi_arch": {"path": str(repo_path(MHI_ARCH)), "exists": bool(mhi)},
            "icnss": {"path": str(repo_path(ICNSS_C)), "exists": bool(icnss)},
            "cnss2": {"path": str(repo_path(CNSS2_MAIN)), "exists": bool(cnss2)},
            "helper": {"path": str(repo_path(HELPER_C)), "exists": bool(helper)},
            "research": {"path": str(repo_path(ESOC_RESEARCH)), "exists": bool(research)},
        },
        "uapi": {
            "reg_req_nr7": "ESOC_REG_REQ_ENG" in esoc_ctrl and "_IO(ESOC_CODE, 7)" in esoc_ctrl,
            "reg_cmd_nr8": "ESOC_REG_CMD_ENG" in esoc_ctrl and "_IO(ESOC_CODE, 8)" in esoc_ctrl,
            "cmd_exe_nr1": "ESOC_CMD_EXE" in esoc_ctrl and "_IOW(ESOC_CODE, 1" in esoc_ctrl,
            "pwr_on_value1": "ESOC_PWR_ON = 1" in esoc_ctrl,
            "req_eng_on_enum": "ESOC_REQ_ENG_ON" in esoc_ctrl,
        },
        "local_esoc_clients": {
            "hook_prios_present": "ESOC_MHI_HOOK" in esoc_client and "ESOC_CNSS_HOOK" in esoc_client,
            "mhi_registers_mdm_client": "devm_register_esoc_client" in mhi and '"mdm"' in mhi,
            "mhi_power_on_hook": "mhi_arch_esoc_ops_power_on" in mhi and "esoc_link_power_on" in mhi,
            "icnss_registers_mdm_client": "icnss_register_esoc_client" in icnss and '"mdm"' in icnss,
            "icnss_power_off_hook_only": "icnss_esoc_ops_power_off" in icnss and "esoc_link_power_off" in icnss,
            "cnss2_registers_esoc_or_notifier": "cnss_register_esoc" in cnss2 and "devm_register_esoc_client" in cnss2,
        },
        "subsystem_path": {
            "state_read_only": "DEVICE_ATTR_RO(state)" in ssr,
            "open_calls_subsystem_get": "subsystem_get_with_fwname" in ssr,
            "release_calls_subsystem_put": "subsystem_put(subsys_dev);" in ssr,
            "start_calls_powerup": "subsys->desc->powerup" in ssr,
        },
        "research_contract": {
            "req_eng_wait_recorded": "req_eng_wait" in research and "REQ_ENG 등록" in research,
            "subsys_dstate_recorded": "mdm_subsys_powerup" in research and "D-state" in research,
            "complete_android_chain_recorded": "완전한 Android mdm3 bring-up 체인" in research,
        },
        "helper_gaps": {
            "stale_open_errno_likely": "saved_errno = errno;" in helper and "cmd_fd = open" in helper,
            "current_mode_closes_req_fd": "close(req_fd);" in helper and "engine-register-preflight-complete" in helper,
            "no_req_registered_subsys_mode": "req-registered-subsys" not in helper,
        },
        "line_anchors": {
            "esoc_client_hook_prio": line_of(esoc_client, r"enum esoc_client_hook_prio"),
            "mhi_devm_register_esoc_client": line_of(mhi, r"devm_register_esoc_client"),
            "mhi_power_on_hook": line_of(mhi, r"mhi_arch_esoc_ops_power_on"),
            "icnss_register_esoc_client": line_of(icnss, r"icnss_register_esoc_client"),
            "subsystem_get_with_fwname": line_of(ssr, r"subsystem_get_with_fwname"),
            "device_attr_ro_state": line_of(ssr, r"DEVICE_ATTR_RO\\(state\\)"),
            "helper_engine_register": line_of(helper, r"run_wifi_companion_esoc_engine_register_preflight_guarded"),
        },
    }


def classify(v878: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    source_ready = all(section.get("exists") for section in source["paths"].values())
    uapi_ready = all(source["uapi"].values())
    req_registered_subsys_candidate = (
        v878["req_ok"]
        and source["subsystem_path"]["open_calls_subsystem_get"]
        and source["subsystem_path"]["start_calls_powerup"]
        and source["research_contract"]["req_eng_wait_recorded"]
    )
    direct_cmd_exe_blocked = v878["cmd_ebusy"]
    client_hook_gap = v878["client_hooks_dmesg"]
    return {
        "source_ready": source_ready,
        "uapi_ready": uapi_ready,
        "direct_userspace_cmd_exe_blocked": direct_cmd_exe_blocked,
        "direct_userspace_cmd_exe_reason": "REG_CMD_ENG returned EBUSY, and public esoc_dev gates ESOC_CMD_EXE on command-engine ownership",
        "req_registered_subsys_candidate": req_registered_subsys_candidate,
        "req_registered_subsys_reason": "REG_REQ_ENG returned rc0 and the documented V849 blocker was req_eng_wait before subsystem powerup",
        "client_hook_gap": client_hook_gap,
        "client_hook_reason": "V878 dmesg reports missing eSoC client hooks; local OSRC has MHI/CNSS hook registration paths, so next proof must capture hook state around any subsystem powerup",
        "helper_repair_needed": source["helper_gaps"]["stale_open_errno_likely"] and source["helper_gaps"]["no_req_registered_subsys_mode"],
        "selected_next": "V880 helper v138 source/build-only stale-open-errno repair plus REQ-registered subsys-hold preflight support",
        "live_allowed_next": False,
        "future_live_gate": "REQ fd held while bounded /dev/subsys_esoc0 open is attempted with dmesg/wchan capture and cleanup/reboot plan",
        "blocked_operations": [
            "direct userspace ESOC_CMD_EXE",
            "explicit userspace ESOC_PWR_ON",
            "ESOC_WAIT_FOR_REQ",
            "ESOC_NOTIFY",
            "mdm_helper/ks/pm_proxy_helper actor start",
            "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
        ],
    }


def decide(v878: dict[str, Any], source: dict[str, Any], classification: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not v878["manifest_exists"]:
        return "v879-v878-evidence-missing", False, "V878 manifest is missing", "rerun V878 or restore evidence"
    if not classification["source_ready"] or not classification["uapi_ready"]:
        return "v879-source-incomplete", False, "local OSRC source inputs are incomplete", "restore source inputs before next helper work"
    if not (v878["req_ok"] and v878["cmd_ebusy"] and v878["forbidden_empty"] and v878["cleanup_ok"] and v878["selftest_fail0"]):
        return "v879-v878-result-not-classifiable", False, f"v878={v878}", "inspect V878 before selecting next gate"
    if classification["req_registered_subsys_candidate"] and classification["direct_userspace_cmd_exe_blocked"]:
        return (
            "v879-cmd-engine-ebusy-classified",
            True,
            "direct userspace CMD_EXE remains blocked; REQ-registered subsystem powerup path is the next source/build-only candidate",
            classification["selected_next"],
        )
    return "v879-review", False, f"classification={classification}", "review eSoC state machine before live work"


def render_summary(manifest: dict[str, Any]) -> str:
    source = manifest["analysis"]["source"]
    v878 = manifest["analysis"]["v878"]
    classification = manifest["analysis"]["classification"]
    source_rows = []
    for section, values in source.items():
        if isinstance(values, dict) and section not in {"paths", "line_anchors"}:
            for key, value in values.items():
                source_rows.append([section, key, value])
    path_rows = [[name, item["exists"], item["path"]] for name, item in source["paths"].items()]
    class_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in classification.items()]
    v878_rows = [
        ["decision", v878["decision"]],
        ["REG_CMD_ENG", json.dumps(v878["cmd"], sort_keys=True)],
        ["REG_REQ_ENG", json.dumps(v878["req"], sort_keys=True)],
        ["client_hooks_dmesg", v878["client_hooks_dmesg"]],
        ["cleanup_ok", v878["cleanup_ok"]],
        ["selftest_fail0", v878["selftest_fail0"]],
        ["actor_hits", len(v878["actor_hits"])],
        ["wifi_link_hits", len(v878["wifi_link_hits"])],
    ]
    return "\n".join([
        "# V879 CMD Engine Ownership Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_device_contact: `{manifest['live_device_contact']}`",
        f"- mutating_esoc_ioctl_executed: `{manifest['mutating_esoc_ioctl_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## V878 Inputs",
        "",
        markdown_table(["item", "value"], v878_rows),
        "",
        "## Source Inputs",
        "",
        markdown_table(["name", "exists", "path"], path_rows),
        "",
        "## Source Classification",
        "",
        markdown_table(["section", "key", "value"], source_rows),
        "",
        "## Decision Classification",
        "",
        markdown_table(["key", "value"], class_rows),
        "",
        "## Public References",
        "",
        f"- eSoC device ioctl path: {PUBLIC_ESOC_DEV}",
        f"- eSoC UAPI header: {PUBLIC_ESOC_CTRL}",
        "",
        "## Guardrails",
        "",
        "- Host-only: no bridge/device command executed.",
        "- No helper deploy, eSoC ioctl, subsystem open, actor start, or Wi-Fi bring-up.",
        "- No scan/connect, credentials, DHCP/routes, or external ping.",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v878 = v878_summary()
    source = source_summary()
    classification = classify(v878, source)
    decision, pass_ok, reason, next_step = decide(v878, source, classification)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "analysis": {
            "v878": v878,
            "source": source,
            "classification": classification,
            "public_references": {
                "esoc_dev": PUBLIC_ESOC_DEV,
                "esoc_ctrl": PUBLIC_ESOC_CTRL,
            },
        },
        "live_device_contact": False,
        "mutating_esoc_ioctl_executed": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"live_device_contact: {manifest['live_device_contact']}")
    print(f"mutating_esoc_ioctl_executed: {manifest['mutating_esoc_ioctl_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
