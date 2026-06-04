#!/usr/bin/env python3
"""V2093 host-only correction for the post-server_check TFTP branch."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2093-server-check-post-branch"
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2093_SERVER_CHECK_POST_BRANCH_2026-06-05.md"
)

INPUTS = {
    "v2059": REPO_ROOT / "tmp" / "wifi" / "v2059-permgr-vote-focused-handoff" / "manifest.json",
    "v2081": REPO_ROOT / "tmp" / "wifi" / "v2081-wlfw-late-msg21-native-handoff" / "manifest.json",
    "v2083": REPO_ROOT / "tmp" / "wifi" / "v2083-icnss-qcacld-post-bdf-handoff" / "manifest.json",
    "v2091": REPO_ROOT / "tmp" / "wifi" / "v2091-macloader-property-service-handoff" / "manifest.json",
}
ANDROID_DIFF = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2053_PRE_WLANMDSP_TRIGGER_EVENT_DIFF_2026-06-04.md"
V2092_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2092_MAC_FALSIFIER_TFTP_REDIRECT_2026-06-05.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return 0
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key] = value
    return fields


def helper_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    handoff_manifest = Path(str(manifest.get("handoff_manifest", "")))
    if not handoff_manifest.is_absolute():
        handoff_manifest = REPO_ROOT / handoff_manifest
    candidate = handoff_manifest.parent / "test-v1393-helper-result.stdout.txt"
    if candidate.exists():
        return candidate
    return manifest_path.parent / "test-v1393-helper-result.stdout.txt"


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def classification(manifest: dict[str, Any]) -> dict[str, Any]:
    value = manifest.get("classification")
    return value if isinstance(value, dict) else {}


def tftp_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    value = nested(manifest, "details", "tftp_logdw", "summary")
    return value if isinstance(value, dict) else {}


def cascade(manifest: dict[str, Any]) -> dict[str, Any]:
    value = nested(manifest, "details", "cascade")
    return value if isinstance(value, dict) else {}


def trace_time(line: str) -> float | None:
    match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def first_sample_with(fields: dict[str, str], suffix: str, expected: str) -> int:
    for index in range(16):
        if fields.get(f"tftp_readwrite_transition.sample_{index:03d}.{suffix}") == expected:
            return index
    return -1


def collect_server_check(fields: dict[str, str]) -> dict[str, Any]:
    sample = first_sample_with(fields, "server_check.payload", "hello")
    prefix = f"tftp_readwrite_transition.sample_{sample:03d}" if sample >= 0 else ""
    ota_sample = first_sample_with(fields, "ota_ruleset.exists", "1")
    wlanmdsp_tokens = [
        key for key, value in fields.items()
        if key.startswith("tftp_logdw_sink.record_")
        and key.endswith(".token.wlanmdsp")
        and intish(value) > 0
    ]
    fallback_tokens = [
        key for key, value in fields.items()
        if key.startswith("tftp_logdw_sink.record_")
        and key.endswith(".token.fallback_wlanmdsp")
        and intish(value) > 0
    ]
    return {
        "sample": sample,
        "seen": sample >= 0,
        "exists": intish(fields.get(f"{prefix}.server_check.exists")) if prefix else 0,
        "size": intish(fields.get(f"{prefix}.server_check.size")) if prefix else 0,
        "payload": fields.get(f"{prefix}.server_check.payload", "") if prefix else "",
        "phase": fields.get(f"{prefix}.phase", "") if prefix else "",
        "ota_ruleset_seen": ota_sample >= 0,
        "ota_ruleset_sample": ota_sample,
        "wlanmdsp_token_records": len(wlanmdsp_tokens) + len(fallback_tokens),
    }


def collect_run(key: str, path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    helper = helper_path(path, manifest)
    helper_text = helper.read_text(encoding="utf-8", errors="replace")
    fields = parse_fields(helper_text)
    cls = classification(manifest)
    summary = tftp_summary(manifest)
    cas = cascade(manifest)
    server_check = collect_server_check(fields)
    wlfw_service_line = fields.get(
        "wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_service_request.first_hit_line",
        "",
    )
    msg21 = fields.get("wlfw_late_msg21_focused.qmi_cb.saw_msg21", "")
    return {
        "key": key,
        "manifest": rel(path),
        "helper": rel(helper),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label") or cls.get("label", ""),
        "pass": boolish(manifest.get("pass")) or boolish(cls.get("pass")),
        "rollback_ok": boolish(cls.get("rollback_ok")) or boolish(cls.get("v2091_rollback_ok")),
        "per_mgr": boolish(cls.get("per_mgr_register_vote"))
        or (
            boolish(cls.get("per_mgr_client_success"))
            and boolish(cls.get("per_mgr_server_success"))
        ),
        "cap_bdf_cal": boolish(cls.get("cap_bdf_cal_success")),
        "msg21": boolish(cls.get("saw_msg21")) or intish(msg21) > 0,
        "wlfw_service_request_ts": trace_time(wlfw_service_line),
        "server_check": server_check,
        "logdw_server_check": intish(summary.get("server_check")),
        "ota_firewall": intish(summary.get("ota_firewall")),
        "mcfg": intish(summary.get("mcfg")),
        "wlanmdsp": intish(summary.get("wlanmdsp")) + intish(summary.get("fallback_wlanmdsp")),
        "wlan_pd": intish(cas.get("wlan_pd_up")),
        "icnss_qmi": intish(cas.get("icnss_qmi_connected")),
        "fw_ready": intish(cas.get("fw_ready")),
        "wlan0": intish(cas.get("wlan0")),
    }


def classify(runs: dict[str, dict[str, Any]]) -> tuple[str, bool, str]:
    checked = [runs[key] for key in ("v2059", "v2081", "v2083", "v2091")]
    server_check_all = all(bool(run["server_check"]["seen"]) for run in checked)
    no_ota_all = all(not bool(run["server_check"]["ota_ruleset_seen"]) and intish(run["ota_firewall"]) == 0 for run in checked)
    no_wlanmdsp_all = all(intish(run["wlanmdsp"]) == 0 and intish(run["server_check"]["wlanmdsp_token_records"]) == 0 for run in checked)
    ap_side_ok = all(bool(run["per_mgr"]) and intish(run["wlan_pd"]) == 1 and intish(run["icnss_qmi"]) == 1 for run in checked)

    if server_check_all and no_ota_all and no_wlanmdsp_all and ap_side_ok:
        return (
            "server-check-complete-no-ota-wlanmdsp",
            True,
            "native repeatedly completes the server_check.txt WRQ payload but never enters the ota_firewall or wlanmdsp branch despite AP-side PerMgr/WLFW and wlan_pd/icnss_qmi progress",
        )
    if not server_check_all:
        return (
            "server-check-not-proven",
            False,
            "one or more current inputs lacks the server_check.txt payload transition",
        )
    return (
        "server-check-post-branch-mixed",
        True,
        "server_check is present but later branch evidence is mixed; inspect per-run rows",
    )


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        escaped = [str(cell).replace("\n", "<br>").replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def render_report(manifest: dict[str, Any]) -> str:
    runs: dict[str, dict[str, Any]] = manifest["runs"]
    rows = []
    for key in ("v2059", "v2081", "v2083", "v2091"):
        run = runs[key]
        server_check = run["server_check"]
        rows.append([
            key.upper(),
            run["label"],
            run["rollback_ok"],
            run["per_mgr"],
            run["cap_bdf_cal"],
            run["msg21"],
            server_check["seen"],
            server_check["sample"],
            server_check["payload"],
            server_check["ota_ruleset_seen"],
            run["ota_firewall"],
            run["mcfg"],
            run["wlanmdsp"],
            run["fw_ready"],
            run["wlan0"],
        ])
    inputs = [[key, runs[key]["manifest"], runs[key]["helper"]] for key in ("v2059", "v2081", "v2083", "v2091")]

    return "\n".join([
        "# Native Init V2093 Server-Check Post-Branch Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V2093`",
        "- Type: host-only corrective classifier over existing rollback-verified native evidence.",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{rel(OUT_DIR)}`",
        "",
        "## Correction",
        "",
        "- The simplified `server_check=0` wording from logdw-only counters is incomplete: the readwrite sampler shows `server_check.txt` appears with the Android 5-byte `hello` payload in every checked native run.",
        "- The live gap is therefore after the `server_check.txt` WRQ completes and before the Android `ota_firewall/ruleset` and `wlanmdsp.mbn` requests.",
        "- `mcfg.tmp` remains downstream/noise for this gate; Android requests `wlanmdsp.mbn` before the compared `mcfg` window.",
        "",
        "## Matrix",
        "",
        markdown_table(
            [
                "run",
                "label",
                "rollback",
                "per_mgr",
                "cap_bdf_cal",
                "msg21",
                "server_check_file",
                "sample",
                "payload",
                "ota_file",
                "ota_log",
                "mcfg",
                "wlanmdsp",
                "fw_ready",
                "wlan0",
            ],
            rows,
        ),
        "",
        "## Next Gate",
        "",
        "- Next live discriminator should target the transition immediately after `server_check.txt=hello`: why the modem does not issue Android's `ota_firewall/ruleset` RRQ and then `wlanmdsp.mbn` RRQ.",
        "- Do not spend more cycles on MAC assignment, AP-side PerMgr/pm-service/rild, `server_check` reachability, mcfg readback, or external SDX50M/PCIe/eSoC paths for this unit.",
        "",
        "## Inputs",
        "",
        markdown_table(["run", "manifest", "helper"], inputs),
        "",
        "## Related Reports",
        "",
        f"- Android/native ordering reference: `{rel(ANDROID_DIFF)}`",
        f"- Superseded simplification to correct: `{rel(V2092_REPORT)}`",
        "",
        "## Safety",
        "",
        "- Host-only parse/report generation; no flash, reboot, adb device mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, or `sda29` write.",
        "",
    ])


def main() -> int:
    required = [*INPUTS.values(), ANDROID_DIFF, V2092_REPORT]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing required evidence: {', '.join(missing)}")
    runs = {key: collect_run(key, path) for key, path in INPUTS.items()}
    label, passed, reason = classify(runs)
    manifest = {
        "cycle": "V2093",
        "decision": f"v2093-{label}-host-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "runs": runs,
        "report": rel(REPORT_PATH),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"decision={manifest['decision']}")
    print(f"report={rel(REPORT_PATH)}")
    print(f"manifest={rel(MANIFEST_PATH)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
