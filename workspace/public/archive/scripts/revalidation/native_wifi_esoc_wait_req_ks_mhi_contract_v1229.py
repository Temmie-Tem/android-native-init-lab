#!/usr/bin/env python3
"""V1229 host-only ESOC WAIT_FOR_REQ / ks-MHI contract classifier.

V1228 proved the non-ptrace native PM/CNSS path reaches ``mdm_helper`` blocked
inside ``ESOC_WAIT_FOR_REQ`` while ``pm-service`` attempts ``/dev/subsys_esoc0``.
This classifier joins that evidence with older native negative controls and the
Android positive contract to choose the next minimal gate toward native Wi-Fi.

It is host-only: no device command, actor start, eSoC ioctl, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, flash, or partition
write is executed.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1229-esoc-wait-req-ks-mhi-contract")
LATEST_POINTER = Path("tmp/wifi/latest-v1229-esoc-wait-req-ks-mhi-contract.txt")
DEFAULT_V1228_MANIFEST = Path("tmp/wifi/v1228-mdm-helper-early-compact-trace-live/manifest.json")
DEFAULT_V891_MANIFEST = Path("tmp/wifi/v891-esoc-conditional-response-live-v142/manifest.json")
DEFAULT_V1199_MANIFEST = Path("tmp/wifi/v1199-esoc-img-xfer-mhi-observe/manifest.json")
DEFAULT_V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")

REFERENCE_REPORTS = {
    "v891": Path("docs/reports/NATIVE_INIT_V891_ESOC_CONDITIONAL_RESPONSE_PROOF_2026-05-26.md"),
    "v896": Path("docs/reports/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_2026-05-26.md"),
    "v1145": Path("docs/reports/NATIVE_INIT_V1145_POST_PM_IMAGE_LINK_CONTRACT_2026-05-27.md"),
    "v1199": Path("tmp/wifi/v1199-esoc-img-xfer-mhi-observe/summary.md"),
    "v1228": Path("docs/reports/NATIVE_INIT_V1228_MDM_HELPER_EARLY_COMPACT_TRACE_LIVE_2026-05-31.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1228-manifest", type=Path, default=DEFAULT_V1228_MANIFEST)
    parser.add_argument("--v891-manifest", type=Path, default=DEFAULT_V891_MANIFEST)
    parser.add_argument("--v1199-manifest", type=Path, default=DEFAULT_V1199_MANIFEST)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896_MANIFEST)
    return parser.parse_args()


def read_text(path: Path, limit: int = 4_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def intish(value: Any, fallback: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return fallback


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = data
    for item in path:
        if not isinstance(current, dict):
            return default
        current = current.get(item)
    return default if current is None else current


def summarize_v1228(manifest: dict[str, Any]) -> dict[str, Any]:
    early = manifest.get("mdm_helper_early_compact_trace") or {}
    parity = manifest.get("mdm_helper_ks_mhi_parity") or {}
    boundary = manifest.get("post_esoc_boundary") or {}
    wait_threads = early.get("wait_for_req_threads") or []
    if not isinstance(wait_threads, list):
        wait_threads = []
    safety_keys = [
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    ]
    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "early_emitted": boolish(early.get("emitted")),
        "sample_count": intish(early.get("sample_count"), -1),
        "max_fd_esoc0_count": intish(early.get("max_fd_esoc0_count"), -1),
        "max_fd_mhi_pipe_count": intish(early.get("max_fd_mhi_pipe_count"), -1),
        "wait_for_req_thread_count": intish(early.get("wait_for_req_thread_count"), 0),
        "wait_thread_names": sorted({str(item.get("ioctl_name", "")) for item in wait_threads if isinstance(item, dict)}),
        "wait_wchans": sorted({str(item.get("wchan", "")) for item in wait_threads if isinstance(item, dict)}),
        "wait_arg1_values": sorted({str(item.get("arg1", "")) for item in wait_threads if isinstance(item, dict)}),
        "pm_service_subsys_esoc0_attempt": boolish(parity.get("pm_service_subsys_esoc0_attempt")),
        "mdm_helper_esoc_present": boolish(parity.get("mdm_helper_esoc_present")),
        "ks_or_mhi_present": boolish(parity.get("ks_or_mhi_present")),
        "ks_count_window": intish(parity.get("ks_count_window"), -1),
        "mhi_pipe_count_window": intish(parity.get("mdm_helper_mhi_pipe_count_window"), -1),
        "mhi_cmdline_count_window": intish(parity.get("mhi_cmdline_count_window"), -1),
        "max_dmesg_modem_down_count": intish(boundary.get("max_dmesg_modem_down_count"), 0),
        "max_dmesg_wlfw_count": intish(boundary.get("max_dmesg_wlfw_count"), 0),
        "wlan0_seen": boolish(boundary.get("wlan0_seen")),
        "mdm3_state_transitions": boundary.get("mdm3_state_transitions") if isinstance(boundary.get("mdm3_state_transitions"), list) else [],
        "safety": {key: boolish(manifest.get(key)) for key in safety_keys},
    }


def summarize_v891(manifest: dict[str, Any]) -> dict[str, Any]:
    conditional = nested_get(manifest, ("analysis", "conditional"), {})
    if not isinstance(conditional, dict):
        conditional = {}
    if not conditional:
        reason = str(manifest.get("reason", ""))
        marker = "conditional="
        if marker in reason:
            try:
                parsed = ast.literal_eval(reason.split(marker, 1)[1])
                if isinstance(parsed, dict):
                    conditional = parsed
            except (SyntaxError, ValueError):
                conditional = {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "wait_rc": intish(conditional.get("wait_rc"), -1),
        "wait_errno": intish(conditional.get("wait_errno"), -1),
        "wait_value": intish(conditional.get("wait_value"), -1),
        "wait_request_name": conditional.get("wait_request_name", ""),
        "request_observed": boolish(conditional.get("request_observed")),
        "img_xfer_attempted": boolish(conditional.get("img_xfer_attempted")),
        "img_xfer_sent": boolish(conditional.get("img_xfer_sent")),
        "status_poll_count": intish(conditional.get("status_poll_count"), 0),
        "status_ready": boolish(conditional.get("status_ready")),
        "status_last_value": intish(conditional.get("status_last_value"), -1),
        "boot_done_attempted": boolish(conditional.get("boot_done_attempted")),
        "result": conditional.get("result", ""),
    }


def summarize_v1199(manifest: dict[str, Any]) -> dict[str, Any]:
    helper = nested_get(manifest, ("analysis", "helper"), {})
    if not isinstance(helper, dict):
        helper = {}
    mhi = helper.get("mhi_obs") or helper.get("mhi_observe") or helper.get("mhi") or {}
    if not isinstance(mhi, dict):
        mhi = {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "img_xfer_sent": (
            "IMG_XFER_DONE sent" in str(manifest.get("reason", ""))
            or boolish(nested_get(helper, ("notify", "ESOC_IMG_XFER_DONE", "sent"), False))
            or boolish(mhi.get("img_xfer_sent"))
        ),
        "mhi_not_appeared": (
            "MHI did not appear" in str(manifest.get("reason", ""))
            or "mhi-not-appeared" in str(manifest.get("decision", ""))
            or boolish(mhi.get("mhi_not_appeared"))
        ),
        "max_gpio142_zero": "max_gpio142=0" in str(manifest.get("reason", "")),
    }


def summarize_v896(manifest: dict[str, Any]) -> dict[str, Any]:
    summary_text = read_text(REFERENCE_REPORTS["v896"])
    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "android_mdm3_online": "mdm3=ONLINE" in summary_text,
        "android_ks_mhi_contract": all(
            needle in summary_text
            for needle in (
                "`mdm_helper` holds `/dev/esoc-0`",
                "`ks` uses `/dev/mhi_0305_01.01.00_pipe_10`",
                "`pm-service` holds `/dev/subsys_esoc0`",
            )
        ),
        "android_wlan0_positive": all(
            needle in summary_text
            for needle in ("WLFW", "BDF", "`wlan0`")
        ),
    }


def summarize_references() -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for name, path in REFERENCE_REPORTS.items():
        text = read_text(path)
        checks: dict[str, bool]
        if name == "v891":
            checks = {
                "wait_req_img": "ESOC_WAIT_FOR_REQ` | rc `4`, errno `0`, value `1`" in text,
                "img_xfer_not_status": "not sufficient to make `ESOC_GET_STATUS` become ready" in text,
            }
        elif name == "v896":
            checks = {
                "android_ks_mhi": "`ks` uses `/dev/mhi_0305_01.01.00_pipe_10`" in text,
                "android_irq": "GPIO 142 `mdm status` IRQ count `1`" in text,
            }
        elif name == "v1145":
            checks = {
                "selected_post_pm_verifier": "post-PM eSoC request verifier" in text,
                "ks_mhi_positive_reference": "ks              -> /dev/mhi_0305_01.01.00_pipe_10" in text,
            }
        elif name == "v1199":
            checks = {
                "mhi_not_appeared": "MHI did not appear" in text or "mhi-not-appeared" in text,
                "img_xfer_done_sent": "IMG_XFER_DONE sent" in text or "img_xfer_sent | 1" in text,
            }
        else:
            checks = {
                "v1228_wait": "ESOC_WAIT_FOR_REQ" in text and "No `ks`" in text,
            }
        refs[name] = {
            "path": str(path),
            "present": bool(text),
            "checks": checks,
            "all_checks": all(checks.values()) if checks else bool(text),
        }
    return refs


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    v1228 = analysis["v1228"]
    v891 = analysis["v891"]
    v1199 = analysis["v1199"]
    v896 = analysis["v896"]
    refs = analysis["references"]
    flags = {
        "v1228_natural_wait_req_seen": (
            v1228["pass"]
            and v1228["early_emitted"]
            and v1228["wait_for_req_thread_count"] > 0
            and "ESOC_WAIT_FOR_REQ" in v1228["wait_thread_names"]
            and "esoc_dev_ioctl" in v1228["wait_wchans"]
        ),
        "v1228_pm_service_subsys_trigger_seen": v1228["pm_service_subsys_esoc0_attempt"],
        "v1228_no_ks_mhi_wlfw_wlan0": (
            not v1228["ks_or_mhi_present"]
            and v1228["ks_count_window"] == 0
            and v1228["mhi_pipe_count_window"] == 0
            and v1228["mhi_cmdline_count_window"] <= 0
            and v1228["max_dmesg_wlfw_count"] == 0
            and not v1228["wlan0_seen"]
        ),
        "v891_req_img_and_img_xfer_response_known": (
            v891["pass"]
            and v891["request_observed"]
            and v891["wait_rc"] == 4
            and v891["wait_value"] == 1
            and v891["wait_request_name"] == "ESOC_REQ_IMG"
            and v891["img_xfer_sent"]
        ),
        "v891_status_not_ready_no_boot_done": (
            v891["pass"]
            and not v891["status_ready"]
            and v891["status_last_value"] == 0
            and not v891["boot_done_attempted"]
        ),
        "v1199_img_xfer_alone_no_mhi": (
            v1199["pass"]
            and v1199["img_xfer_sent"]
            and v1199["mhi_not_appeared"]
        ),
        "v896_android_positive_requires_ks_mhi": (
            v896["pass"]
            and v896["android_mdm3_online"]
            and v896["android_ks_mhi_contract"]
            and v896["android_wlan0_positive"]
        ),
        "reference_reports_consistent": all(ref["present"] and ref["all_checks"] for ref in refs.values()),
        "safety_clean": not any(v1228["safety"].values()),
    }
    required = [
        "v1228_natural_wait_req_seen",
        "v1228_pm_service_subsys_trigger_seen",
        "v1228_no_ks_mhi_wlfw_wlan0",
        "v891_req_img_and_img_xfer_response_known",
        "v891_status_not_ready_no_boot_done",
        "v1199_img_xfer_alone_no_mhi",
        "v896_android_positive_requires_ks_mhi",
        "reference_reports_consistent",
        "safety_clean",
    ]
    missing = [name for name in required if not flags.get(name)]
    if not missing:
        return {
            "decision": "v1229-esoc-wait-req-ks-mhi-contract-classified",
            "pass": True,
            "reason": (
                "V1228 proves the natural native path reaches mdm_helper in ESOC_WAIT_FOR_REQ, "
                "while V891/V1199 prove bare ESOC_REQ_IMG plus IMG_XFER_DONE does not create "
                "MHI readiness; Android positive evidence still requires the ks/MHI image-link contract."
            ),
            "next_step": (
                "V1230 should add source/build-only support for a bounded mdm_helper request-return/ks "
                "observer: preserve the V1228 non-ptrace path, capture the ESOC_WAIT_FOR_REQ return or "
                "immediate post-return branch, and sample /vendor/bin/ks plus "
                "/dev/mhi_0305_01.01.00_pipe_10 before considering any ESOC_NOTIFY/BOOT_DONE or Wi-Fi HAL."
            ),
            "missing": [],
            "flags": flags,
        }
    return {
        "decision": "v1229-esoc-wait-req-ks-mhi-contract-input-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh V1228/V891/V1199/V896 evidence before another live or source/build gate",
        "missing": missing,
        "flags": flags,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    classification = analysis["classification"]
    v1228 = analysis["v1228"]
    v891 = analysis["v891"]
    v1199 = analysis["v1199"]
    v896 = analysis["v896"]
    rows = [
        ["V1228 natural WAIT_FOR_REQ", str(classification["flags"]["v1228_natural_wait_req_seen"]), f"threads={v1228['wait_for_req_thread_count']} wchan={v1228['wait_wchans']}"],
        ["V1228 PM subsys trigger", str(classification["flags"]["v1228_pm_service_subsys_trigger_seen"]), str(v1228["pm_service_subsys_esoc0_attempt"])],
        ["V1228 no ks/MHI/WLFW", str(classification["flags"]["v1228_no_ks_mhi_wlfw_wlan0"]), f"ks={v1228['ks_count_window']} mhi={v1228['mhi_pipe_count_window']} wlfw={v1228['max_dmesg_wlfw_count']}"],
        ["V891 ESOC_REQ_IMG", str(classification["flags"]["v891_req_img_and_img_xfer_response_known"]), f"rc={v891['wait_rc']} value={v891['wait_value']} img_xfer={v891['img_xfer_sent']}"],
        ["V891 status not ready", str(classification["flags"]["v891_status_not_ready_no_boot_done"]), f"polls={v891['status_poll_count']} value={v891['status_last_value']}"],
        ["V1199 IMG_XFER no MHI", str(classification["flags"]["v1199_img_xfer_alone_no_mhi"]), v1199["decision"]],
        ["V896 Android ks/MHI", str(classification["flags"]["v896_android_positive_requires_ks_mhi"]), v896["decision"]],
        ["safety clean", str(classification["flags"]["safety_clean"]), "no HAL/scan/credential/DHCP/ping/flash"],
    ]
    reference_rows = [
        [name, str(ref["present"]), str(ref["all_checks"]), json.dumps(ref["checks"], sort_keys=True)]
        for name, ref in analysis["references"].items()
    ]
    return "\n".join([
        "# V1229 ESOC WAIT_FOR_REQ / ks-MHI Contract Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Classification",
        "",
        markdown_table(["evidence", "ok", "detail"], rows),
        "",
        "## Reference Checks",
        "",
        markdown_table(["ref", "present", "all checks", "checks"], reference_rows),
        "",
        "## Safety",
        "",
        "- device commands executed: `false`",
        "- live eSoC ioctl or notify executed: `false`",
        "- PM/CNSS actor or Wi-Fi HAL start executed: `false`",
        "- scan/connect, credentials, DHCP/routes, external ping: `false`",
        "- flash, partition writes, and boot image writes: `false`",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "v1228": summarize_v1228(load_json(args.v1228_manifest)),
        "v891": summarize_v891(load_json(args.v891_manifest)),
        "v1199": summarize_v1199(load_json(args.v1199_manifest)),
        "v896": summarize_v896(load_json(args.v896_manifest)),
        "references": summarize_references(),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1229",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1228_manifest": str(repo_path(args.v1228_manifest)),
            "v891_manifest": str(repo_path(args.v891_manifest)),
            "v1199_manifest": str(repo_path(args.v1199_manifest)),
            "v896_manifest": str(repo_path(args.v896_manifest)),
            "reference_reports": {key: str(repo_path(path)) for key, path in REFERENCE_REPORTS.items()},
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
