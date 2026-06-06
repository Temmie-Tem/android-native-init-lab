#!/usr/bin/env python3
"""v264 QRTR/QMI userspace nameservice model.

This tool is host-only. It consumes prior no-scan/no-send evidence and produces
a decision artifact for the next QRTR/QMI step. It must not contact the device,
open QRTR sockets, start CNSS, run qmicli, or transmit QMI/QRTR packets.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v264-qrtr-qmi-nameservice-model")
DEFAULT_V262_MANIFEST = Path("tmp/wifi/v262-qrtr-qmi-no-scan-probe/manifest.json")
DEFAULT_V263_WARNING_MANIFEST = Path("tmp/wifi/v263-cnss-live-retry-20260519-091608/warning-disposition/manifest.json")

REFERENCE_URLS = {
    "linux_qrtr_kconfig": "https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html",
    "libqmi": "https://github.com/linux-mobile-broadband/libqmi",
    "qmicli_manpage": "https://manpages.ubuntu.com/manpages/questing/man1/qmicli.1.html",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object manifest: {path}")
    return payload


def optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        return None
    return load_json(path)


def bool_value(value: Any) -> bool:
    return bool(value)


def build_model(v262: dict[str, Any], v263: dict[str, Any] | None) -> dict[str, Any]:
    inventory = v262.get("inventory", {})
    probe_keys = v262.get("probe_keys", {})
    qipcrtr_present = bool_value(inventory.get("qipcrtr_protocol_present"))
    socket_open = str(probe_keys.get("socket.rc", inventory.get("qrtr_helper_socket_rc", ""))) == "0"
    send_attempted = str(probe_keys.get("send_attempted", inventory.get("qrtr_helper_send_attempted", "")))
    connect_attempted = str(probe_keys.get("connect_attempted", inventory.get("qrtr_helper_connect_attempted", "")))
    no_wlan_link = not bool_value(inventory.get("wlan_in_proc_net_dev")) and not bool_value(inventory.get("wlan_in_sys_class_net"))
    process_summary = inventory.get("process_summary") if isinstance(inventory.get("process_summary"), dict) else {}
    warning_disposition = {
        "provided": v263 is not None,
        "pass": bool(v263.get("pass")) if v263 else None,
        "decision": v263.get("decision") if v263 else None,
    }
    return {
        "kernel": {
            "qipcrtr_protocol_present": qipcrtr_present,
            "af_qipcrtr_socket_bind_ready": socket_open,
            "proc_net_qrtr_present": bool_value(inventory.get("proc_net_qrtr_present")),
        },
        "runtime_surface": {
            "dev_qrtr_present": bool_value(inventory.get("dev_qrtr_present")),
            "dev_diag_present": bool_value(inventory.get("dev_diag_present")),
            "dev_ipa_present": bool_value(inventory.get("dev_ipa_present")),
            "dev_wlan_present": bool_value(inventory.get("dev_wlan_present")),
            "dev_inventory_matches": inventory.get("dev_inventory_matches"),
            "sys_inventory_matches": inventory.get("sys_inventory_matches"),
            "wlan_link_surface_present": not no_wlan_link,
        },
        "prior_probe": {
            "v262_pass": bool(v262.get("pass")),
            "v262_decision": v262.get("decision"),
            "qrtr_helper_status": probe_keys.get("status", inventory.get("qrtr_helper_status")),
            "send_attempted": send_attempted,
            "connect_attempted": connect_attempted,
        },
        "process_state": {
            "cnss_process_clean": bool(process_summary.get("clean")),
            "target_process_count": process_summary.get("target_process_count"),
            "target_zombie_count": process_summary.get("target_zombie_count"),
        },
        "warning_disposition": warning_disposition,
        "missing_before_transmit": [
            "explicit QRTR nameservice transmit approval",
            "bounded helper that can prove exactly which QRTR packet type is sent",
            "postflight process and wlan-link audit gate",
            "decision on perfd/property/kmsg private shim for broader Wi-Fi",
            "no-scan QMI service query contract before any Wi-Fi scan/connect/link-up",
        ],
        "approval_gates": [
            "QRTR nameservice packet transmission",
            "QMI service request through qmicli/libqmi/custom helper",
            "cnss-daemon live run beyond bounded start-only",
            "cnss_diag execution",
            "rfkill unblock or wlan link-up",
            "Wi-Fi scan/connect/credentials/DHCP/routing",
        ],
    }


def build_checks(v262: dict[str, Any], v263: dict[str, Any] | None, model: dict[str, Any]) -> list[dict[str, Any]]:
    prior_probe = model["prior_probe"]
    kernel = model["kernel"]
    runtime_surface = model["runtime_surface"]
    process_state = model["process_state"]
    warning = model["warning_disposition"]
    checks = [
        {
            "name": "v262-manifest-pass",
            "pass": bool(v262.get("pass")) and v262.get("decision") == "qrtr-qmi-no-scan-ready",
            "severity": "critical",
            "detail": f"decision={v262.get('decision')} pass={v262.get('pass')}",
        },
        {
            "name": "qipcrtr-kernel-ready",
            "pass": bool(kernel["qipcrtr_protocol_present"]) and bool(kernel["af_qipcrtr_socket_bind_ready"]),
            "severity": "critical",
            "detail": json.dumps(kernel, sort_keys=True),
        },
        {
            "name": "no-prior-qrtr-transmit",
            "pass": prior_probe["send_attempted"] == "0" and prior_probe["connect_attempted"] == "0",
            "severity": "critical",
            "detail": json.dumps({
                "send_attempted": prior_probe["send_attempted"],
                "connect_attempted": prior_probe["connect_attempted"],
            }, sort_keys=True),
        },
        {
            "name": "cnss-process-clean",
            "pass": bool(process_state["cnss_process_clean"]),
            "severity": "critical",
            "detail": json.dumps(process_state, sort_keys=True),
        },
        {
            "name": "no-wlan-link-surface",
            "pass": not bool(runtime_surface["wlan_link_surface_present"]),
            "severity": "critical",
            "detail": json.dumps({"wlan_link_surface_present": runtime_surface["wlan_link_surface_present"]}, sort_keys=True),
        },
        {
            "name": "warning-disposition-ready",
            "pass": (not warning["provided"]) or (warning["pass"] is True and warning["decision"] == "cnss-warning-disposition-ready"),
            "severity": "warning",
            "detail": json.dumps(warning, sort_keys=True),
        },
        {
            "name": "transmit-still-approval-gated",
            "pass": True,
            "severity": "critical",
            "detail": "nameservice/QMI packet transmission is not authorized by this model",
        },
    ]
    return checks


def classify(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    critical_failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if critical_failed:
        return False, "qrtr-qmi-userspace-model-blocked", "critical model prerequisite failed: " + ", ".join(critical_failed)
    warning_failed = [item["name"] for item in checks if item["severity"] == "warning" and not item["pass"]]
    if warning_failed:
        return False, "qrtr-qmi-userspace-model-incomplete", "warning disposition missing or incomplete: " + ", ".join(warning_failed)
    return True, "qrtr-qmi-userspace-model-ready", "QRTR/QMI userspace boundary is modeled without packet transmission"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[item["name"], "PASS" if item["pass"] else "FAIL", item["severity"], item["detail"]] for item in manifest["checks"]]
    model_rows: list[list[str]] = []
    for section, values in manifest["model"].items():
        if isinstance(values, dict):
            for key, value in values.items():
                model_rows.append([section, key, json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)])
        elif isinstance(values, list):
            model_rows.append([section, "-", json.dumps(values, ensure_ascii=False)])
        else:
            model_rows.append([section, "-", str(values)])
    refs = [[key, value] for key, value in manifest["references"].items()]
    return "".join([
        "# v264 QRTR/QMI Userspace Nameservice Model\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- v262_manifest: `{manifest['inputs']['v262_manifest']}`\n",
        f"- v263_warning_manifest: `{manifest['inputs']['v263_warning_manifest']}`\n",
        "- daemon start: `not executed`\n",
        "- QRTR/QMI packet transmission: `not executed`\n",
        "- Wi-Fi scan/connect/link-up: `not executed`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "severity", "detail"], checks),
        "\n\n## Model\n\n",
        markdown_table(["section", "key", "value"], model_rows),
        "\n\n## Interpretation\n\n",
        "- Kernel QRTR socket readiness is necessary but not sufficient for Wi-Fi bring-up.\n",
        "- The next transmit-capable step must be a separately approved QRTR nameservice or QMI no-scan probe.\n",
        "- v264 does not authorize `cnss_diag`, Wi-Fi scan/connect/link-up, credentials, DHCP, or routing.\n",
        "- Perfd/property/kmsg runtime service gaps remain separate opt-in shim candidates before broader Wi-Fi.\n\n",
        "## References\n\n",
        markdown_table(["reference", "url"], refs),
        "\n\n## Guardrails\n\n",
        "- No bridge command is executed by this tool.\n",
        "- No QRTR socket is opened by this tool.\n",
        "- No QMI request is issued by this tool.\n",
        "- No device, kernel, Android runtime, Wi-Fi, or filesystem state is mutated by this tool.\n",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v262-manifest", type=Path, default=DEFAULT_V262_MANIFEST)
    parser.add_argument("--v263-warning-manifest", type=Path, default=DEFAULT_V263_WARNING_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    v262_path = repo_path(args.v262_manifest)
    v263_path = repo_path(args.v263_warning_manifest) if args.v263_warning_manifest else None
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v262 = load_json(v262_path)
    v263 = optional_json(v263_path)
    model = build_model(v262, v263)
    checks = build_checks(v262, v263, model)
    pass_ok, decision, reason = classify(checks)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-qmi-userspace-nameservice-model",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {
            "v262_manifest": str(v262_path),
            "v263_warning_manifest": str(v263_path) if v263_path and v263_path.exists() else None,
        },
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "model": model,
        "checks": checks,
        "guardrails": [
            "host-only model; no bridge command",
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no QRTR send/connect/nameservice packet",
            "no QMI request command",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition write, or reboot",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"out_dir: {out_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
