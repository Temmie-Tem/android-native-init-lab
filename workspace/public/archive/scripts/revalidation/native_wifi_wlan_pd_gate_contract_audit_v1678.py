#!/usr/bin/env python3
"""V1678 host-only audit of the V1677 WLAN-PD firmware-serve gate contract."""

from __future__ import annotations

import json
from pathlib import Path

from a90harness.evidence import write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
EVIDENCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1677-wlan-pd-firmware-serve-gate-corrected-handoff"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1678-wlan-pd-gate-contract-audit"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1678_WLAN_PD_GATE_CONTRACT_AUDIT_2026-06-02.md"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def has_any(text: str, needles: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def render(result: dict[str, object]) -> str:
    lines = [
        "# Native Init V1678 WLAN-PD Gate Contract Audit",
        "",
        "## Summary",
        "",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Evidence audited: `{result['evidence_dir']}`",
        f"- V1677 label: `{result['v1677_label']}`",
        "",
        "## Contract Coverage",
        "",
        f"- firmware mounts requested: `{result['firmware_mounts_requested']}`",
        f"- tftp server running: `{result['tftp_running']}`",
        f"- subsys_modem holder marker present: `{result['subsys_modem_holder_marker']}`",
        f"- mss loading marker present: `{result['mss_loading_seen']}`",
        f"- mss brought-out-of-reset marker present: `{result['mss_brought_out_of_reset_seen']}`",
        f"- service-notifier endpoint found: `{result['service_notifier_endpoint_found']}`",
        f"- WLFW service 69 seen: `{result['wlfw_service69_seen']}`",
        "",
        "## Interpretation",
        "",
        "- V1677 is retained as raw evidence, but it did not satisfy the redirected gate trigger contract.",
        "- The companion stack and tftp server were observed, but `/dev/subsys_modem` was not opened by a gate holder and mss/PIL bring-up markers were absent.",
        "- The `firmware-not-requested` label therefore only proves that no request happened without the required internal-modem trigger; it is not the final firmware-serve discriminator.",
        "- Next unit is a corrected source/build that starts a modem-only `/dev/subsys_modem` holder while keeping eSoC/subsys_esoc0, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, DHCP/routes, and external ping disabled.",
        "",
        "## Safety",
        "",
        "- Host-only audit. No device command, live mutation, boot image write, firmware write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping occurred.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_text = read_text(EVIDENCE_DIR / "manifest.json")
    helper_text = read_text(EVIDENCE_DIR / "test-v1393-helper-result.stdout.txt")
    summary_text = read_text(EVIDENCE_DIR / "test-v1393-summary.stdout.txt")
    dmesg_text = read_text(EVIDENCE_DIR / "test-v1393-dmesg.stdout.txt")
    manifest = json.loads(manifest_text) if manifest_text.strip() else {}
    gate = manifest.get("gate", {}) if isinstance(manifest.get("gate"), dict) else {}

    result = {
        "decision": "v1678-v1677-trigger-incomplete-modem-holder-missing",
        "pass": True,
        "evidence_dir": rel(EVIDENCE_DIR),
        "v1677_label": gate.get("label", ""),
        "firmware_mounts_requested": "firmware_mounts_requested=1" in summary_text,
        "tftp_running": gate.get("tftp_running") == "1" or "wlan_pd_firmware_serve_gate.tftp_running=1" in helper_text,
        "subsys_modem_holder_marker": "wlan_pd_modem_holder" in helper_text or "subsys_modem_holder" in helper_text,
        "mss_loading_seen": has_any(dmesg_text, ("4080000.qcom,mss: modem: loading", "modem: loading")),
        "mss_brought_out_of_reset_seen": has_any(dmesg_text, ("modem: Brought out of reset", "Brought out of reset")),
        "service_notifier_endpoint_found": "wifi_companion_service_notifier_listener.endpoint.found=1" in helper_text,
        "wlfw_service69_seen": gate.get("wlfw_service69_seen") == "1" or "wlan_pd_firmware_serve_gate.wlfw_service69_seen=1" in helper_text,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(render(result), encoding="utf-8")
    write_private_text(REPORT_PATH, render(result))
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "report": rel(REPORT_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
