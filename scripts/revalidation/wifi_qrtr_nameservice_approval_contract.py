#!/usr/bin/env python3
"""v265 QRTR nameservice transmit approval contract.

This is a host-only contract generator. It does not contact the device, open a
QRTR socket, send a nameservice packet, or issue a QMI request.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v265-qrtr-nameservice-approval-contract")
DEFAULT_V264_MANIFEST = Path("tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json")
DEFAULT_FUTURE_RUN_DIR = Path("tmp/wifi/v266-qrtr-nameservice-no-scan-run")
DEFAULT_FUTURE_RUNNER = Path("scripts/revalidation/wifi_qrtr_nameservice_runner.py")

QRTR_PORT_CTRL = 0xFFFFFFFE
QRTR_TYPE_NEW_LOOKUP = 10
QRTR_TYPE_DEL_LOOKUP = 11

REFERENCE_URLS = {
    "linux_qrtr_kconfig": "https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html",
    "linux_qrtr_uapi": "https://codebrowser.dev/linux/include/linux/qrtr.h.html",
    "linux_qrtr_ns": "https://codebrowser.dev/linux/linux/net/qrtr/ns.c.html",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object manifest: {path}")
    return payload


def shell_join(argv: list[str]) -> str:
    return " ".join(shlex.quote(item) for item in argv)


def future_command(args: argparse.Namespace) -> list[str]:
    return [
        "python3",
        str(args.future_runner),
        "--out-dir",
        str(args.future_run_dir),
        "--v264-manifest",
        str(args.v264_manifest),
        "--max-runtime-sec",
        str(args.max_runtime_sec),
        "run",
        "--service",
        args.service,
        "--instance",
        args.instance,
        "--allow-qrtr-ns-transmit",
        "--assume-yes",
        "--i-understand-qrtr-packet-transmission",
    ]


def render_rollback_checklist() -> str:
    return """# QRTR Nameservice Transmit Rollback Checklist

## Before Any Transmit-Capable Run

- Confirm bridge command path is responsive.
- Confirm `status` reports CNSS process clean.
- Confirm no `wlan*` interface is visible.
- Confirm `netservice` and `rshell` exposure state is expected.
- Confirm thermal/power state is acceptable.
- Keep reboot/recovery path available.

## During Run

- Send only the single approved QRTR nameservice lookup packet.
- Do not run `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP, or routing.
- Do not unblock rfkill or set a `wlan*` link up.
- Do not scan/connect or provide Wi-Fi credentials.

## Postflight

- Run CNSS process audit.
- Run `/proc/net/dev` and `/sys/class/net` audit for unexpected `wlan*`.
- Run `wifiinv full` and preserve evidence.
- If any CNSS process remains, stop and treat as cleanup blocker.
- If a `wlan*` interface appears unexpectedly, stop and require manual review.

## If Control Is Lost

- Stop automation.
- Do not improvise ICNSS bind/unbind or rfkill writes.
- Reboot/recovery is the accepted recovery primitive.
"""


def build_contract(args: argparse.Namespace, v264: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_scope": {
            "qrtr_port_ctrl": f"0x{QRTR_PORT_CTRL:08x}",
            "allowed_packet_type": "QRTR_TYPE_NEW_LOOKUP",
            "allowed_packet_type_value": QRTR_TYPE_NEW_LOOKUP,
            "cleanup_packet_type": "QRTR_TYPE_DEL_LOOKUP",
            "cleanup_packet_type_value": QRTR_TYPE_DEL_LOOKUP,
            "qmi_payload_allowed": False,
            "wifi_scan_connect_allowed": False,
        },
        "default_lookup": {
            "service": args.service,
            "instance": args.instance,
            "wildcard": args.service == "0" and args.instance == "0",
            "wildcard_allowed_by_default": False,
        },
        "required_future_flags": [
            "--allow-qrtr-ns-transmit",
            "--assume-yes",
            "--i-understand-qrtr-packet-transmission",
            "--service",
            "--instance",
            "--max-runtime-sec",
        ],
        "required_postflight": [
            "cnss process audit",
            "wlan link surface audit",
            "wifiinv full capture",
            "status capture",
            "evidence analyzer classification",
        ],
        "blocked_actions": [
            "cnss-daemon live run beyond nameservice-only",
            "cnss_diag execution",
            "QMI service request",
            "rfkill unblock",
            "wlan link-up",
            "Wi-Fi scan/connect/credential/DHCP/routing",
            "ICNSS bind/unbind",
            "firmware or Android partition mutation",
        ],
        "v264_decision": v264.get("decision"),
        "v264_pass": v264.get("pass"),
    }


def build_checks(v264: dict[str, Any], contract: dict[str, Any], command: list[str]) -> list[dict[str, Any]]:
    command_text = " ".join(command)
    required_flags = contract["required_future_flags"]
    wildcard = bool(contract["default_lookup"]["wildcard"])
    checks = [
        {
            "name": "v264-model-ready",
            "pass": bool(v264.get("pass")) and v264.get("decision") == "qrtr-qmi-userspace-model-ready",
            "severity": "critical",
            "detail": f"decision={v264.get('decision')} pass={v264.get('pass')}",
        },
        {
            "name": "approval-flags-present",
            "pass": all(flag in command_text for flag in required_flags),
            "severity": "critical",
            "detail": shell_join(command),
        },
        {
            "name": "wildcard-blocked-by-default",
            "pass": not wildcard,
            "severity": "critical",
            "detail": json.dumps(contract["default_lookup"], sort_keys=True),
        },
        {
            "name": "qmi-payload-blocked",
            "pass": contract["packet_scope"]["qmi_payload_allowed"] is False,
            "severity": "critical",
            "detail": "nameservice control packet only; no QMI payload",
        },
        {
            "name": "wifi-link-actions-blocked",
            "pass": contract["packet_scope"]["wifi_scan_connect_allowed"] is False,
            "severity": "critical",
            "detail": "scan/connect/link-up remain blocked",
        },
        {
            "name": "no-execution-in-v265",
            "pass": True,
            "severity": "critical",
            "detail": "contract generator is host-only and performs no bridge/device calls",
        },
    ]
    return checks


def classify(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-nameservice-approval-contract-blocked", "contract gate failed: " + ", ".join(failed)
    return True, "qrtr-nameservice-approval-contract-ready", "future QRTR nameservice transmission requires explicit approval and bounded postflight"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[item["name"], "PASS" if item["pass"] else "FAIL", item["severity"], item["detail"]] for item in manifest["checks"]]
    contract_rows: list[list[str]] = []
    for section, values in manifest["contract"].items():
        if isinstance(values, dict):
            for key, value in values.items():
                contract_rows.append([section, key, json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)])
        elif isinstance(values, list):
            contract_rows.append([section, "-", json.dumps(values, ensure_ascii=False)])
        else:
            contract_rows.append([section, "-", str(values)])
    refs = [[key, value] for key, value in manifest["references"].items()]
    return "".join([
        "# v265 QRTR Nameservice Approval Contract\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- v264_manifest: `{manifest['inputs']['v264_manifest']}`\n",
        "- daemon start: `not executed`\n",
        "- QRTR/QMI packet transmission: `not executed`\n",
        "- Wi-Fi scan/connect/link-up: `not executed`\n\n",
        "## Future Command Template\n\n",
        "```bash\n",
        manifest["future_command"],
        "\n```\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "severity", "detail"], checks),
        "\n\n## Contract\n\n",
        markdown_table(["section", "key", "value"], contract_rows),
        "\n\n## References\n\n",
        markdown_table(["reference", "url"], refs),
        "\n\n## Guardrails\n\n",
        "- v265 does not execute the future command.\n",
        "- v265 does not open QRTR sockets or send QRTR/QMI packets.\n",
        "- The future command remains invalid until the runner exists and the operator explicitly approves packet transmission.\n",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v264-manifest", type=Path, default=DEFAULT_V264_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--future-runner", type=Path, default=DEFAULT_FUTURE_RUNNER)
    parser.add_argument("--future-run-dir", type=Path, default=DEFAULT_FUTURE_RUN_DIR)
    parser.add_argument("--max-runtime-sec", default="5")
    parser.add_argument("--service", default="__SERVICE_ID__", help="non-wildcard placeholder service id for the future contract")
    parser.add_argument("--instance", default="__INSTANCE_ID__", help="non-wildcard placeholder instance id for the future contract")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    v264_path = repo_path(args.v264_manifest)
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v264 = load_json(v264_path)
    contract = build_contract(args, v264)
    command = future_command(args)
    checks = build_checks(v264, contract, command)
    pass_ok, decision, reason = classify(checks)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-nameservice-approval-contract",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {"v264_manifest": str(v264_path)},
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "future_command": shell_join(command),
        "contract": contract,
        "checks": checks,
        "guardrails": [
            "host-only contract; no bridge command",
            "no QRTR socket open",
            "no QRTR send/connect/nameservice packet",
            "no QMI request command",
            "no cnss-daemon or cnss_diag execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition write, or reboot",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    store.write_text("future-command.sh", "#!/usr/bin/env bash\nset -euo pipefail\n# Requires explicit user approval before execution.\n" + shell_join(command) + "\n")
    store.write_text("rollback-checklist.md", render_rollback_checklist())
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"out_dir: {out_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
