#!/usr/bin/env python3
"""V1976 native lower-publication context handoff.

Runs the proven V1937 rollbackable native handoff into a fresh evidence
directory, then classifies the lower publication context already emitted by the
V1936 helper: service74/180, pd-mapper text, wlan_pd/domain text, QMI server
text, and the libqmi DMS/WLFW lookup/wait state.
"""

from __future__ import annotations

import datetime as dt
import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import native_wifi_icnss_ipc_service69_integration_v1937 as v1937
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1976"
OUT_DIR = repo_path("tmp/wifi/v1976-lower-publication-context-handoff")
HANDOFF_DIR = OUT_DIR / "v1936-handoff"
HANDOFF_REPORT = OUT_DIR / "v1936-handoff-report.md"
REPORT_PATH = repo_path(
    "docs/reports/NATIVE_INIT_V1976_LOWER_PUBLICATION_CONTEXT_HANDOFF_2026-06-04.md"
)

KLOG_PHASES = (
    "after_holder_start",
    "after_early_listener",
    "after_post_listener_window",
)
KLOG_KEYS = (
    "count_sysmon_qmi",
    "count_180",
    "count_74",
    "raw_count_pd_mapper_text",
    "raw_count_service_locator_text",
    "raw_count_servloc_domain_text",
    "raw_count_wlan_fw_text",
    "raw_count_wlan_pd_domain_text",
    "raw_count_qmi_server_connected_text",
    "raw_count_wlan_pd_text",
    "raw_count_qmi_text",
    "raw_count_wlfw_text",
    "last_180",
    "last_74",
    "last_pd_mapper",
    "last_service_locator",
    "last_servloc_domain",
    "last_wlan_fw",
    "last_wlan_pd_domain",
    "last_qmi_server_connected",
    "last_wlan_pd",
    "last_qmi",
    "last_wlfw",
    "no_esoc0_open",
    "no_fake_online",
    "no_pmic_gpio_gdsc_write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "ok"}


def field_prefix(phase: str) -> str:
    return f"wlan_pd_post_pm_lower_handoff_klog.{phase}."


def collect_klog(fields: dict[str, str]) -> dict[str, Any]:
    samples: list[dict[str, str]] = []
    for phase in KLOG_PHASES:
        prefix = field_prefix(phase)
        sample = {"phase": phase}
        sample.update({key: fields.get(prefix + key, "") for key in KLOG_KEYS})
        samples.append(sample)

    def series(key: str) -> list[int]:
        return [intish(sample.get(key)) for sample in samples if sample.get(key) != ""]

    def any_positive(key: str) -> bool:
        return any(value > 0 for value in series(key))

    return {
        "samples": samples,
        "contract_ok": len(samples) == len(KLOG_PHASES)
        and all(sample.get("no_esoc0_open") == "1" for sample in samples),
        "safety_ok": all(
            sample.get("no_esoc0_open") == "1"
            and sample.get("no_fake_online") == "1"
            and sample.get("no_pmic_gpio_gdsc_write") == "1"
            for sample in samples
        ),
        "sysmon_qmi_counts": series("count_sysmon_qmi"),
        "service180_counts": series("count_180"),
        "service74_counts": series("count_74"),
        "pd_mapper_counts": series("raw_count_pd_mapper_text"),
        "service_locator_counts": series("raw_count_service_locator_text"),
        "servloc_domain_counts": series("raw_count_servloc_domain_text"),
        "wlan_fw_counts": series("raw_count_wlan_fw_text"),
        "wlan_pd_domain_counts": series("raw_count_wlan_pd_domain_text"),
        "qmi_server_connected_counts": series("raw_count_qmi_server_connected_text"),
        "wlan_pd_counts": series("raw_count_wlan_pd_text"),
        "qmi_text_counts": series("raw_count_qmi_text"),
        "wlfw_text_counts": series("raw_count_wlfw_text"),
        "sysmon_qmi_positive": any_positive("count_sysmon_qmi"),
        "service180_positive": any_positive("count_180"),
        "service74_positive": any_positive("count_74"),
        "pd_mapper_positive": any_positive("raw_count_pd_mapper_text"),
        "service_locator_positive": any_positive("raw_count_service_locator_text"),
        "servloc_domain_positive": any_positive("raw_count_servloc_domain_text"),
        "wlan_fw_positive": any_positive("raw_count_wlan_fw_text"),
        "wlan_pd_domain_positive": any_positive("raw_count_wlan_pd_domain_text"),
        "qmi_server_connected_positive": any_positive("raw_count_qmi_server_connected_text"),
        "wlan_pd_positive": any_positive("raw_count_wlan_pd_text"),
        "qmi_text_positive": any_positive("raw_count_qmi_text"),
        "wlfw_text_positive": any_positive("raw_count_wlfw_text"),
    }


def parse_helper_fields() -> dict[str, str]:
    return v1937.parent.base.v1847.runner().fwbase.parse_helper_fields(HANDOFF_DIR)


def configure_v1937() -> None:
    v1937.CYCLE = CYCLE
    v1937.OUT_DIR = OUT_DIR
    v1937.HANDOFF_DIR = HANDOFF_DIR
    v1937.HANDOFF_REPORT = HANDOFF_REPORT
    v1937.REPORT_PATH = REPORT_PATH


def classify(v1937_manifest: dict[str, Any], klog: dict[str, Any]) -> dict[str, Any]:
    details = v1937_manifest.get("details") if isinstance(v1937_manifest.get("details"), dict) else {}
    rollback = boolish(v1937_manifest.get("pass"))
    combined = (
        rollback
        and boolish(details.get("service74"))
        and boolish(details.get("service180"))
        and boolish(details.get("pm_open_subsys_modem"))
        and boolish(details.get("holder_opened"))
        and boolish(details.get("libqmi_lookup_service69_seen"))
        and boolish(details.get("libqmi_wlfw_wait_outstanding"))
        and "0x2" in set(details.get("libqmi_lookup_service_ids") or [])
    )
    no_publication = (
        not boolish(details.get("wlfw69"))
        and not boolish(details.get("wlan_pd"))
        and not boolish(details.get("wlanmdsp"))
        and not boolish(details.get("wlan0"))
    )
    missing_lower_domain = (
        klog.get("service180_positive")
        and klog.get("service74_positive")
        and not klog.get("pd_mapper_positive")
        and not klog.get("servloc_domain_positive")
        and not klog.get("wlan_fw_positive")
        and not klog.get("wlan_pd_domain_positive")
        and not klog.get("qmi_server_connected_positive")
        and not klog.get("wlan_pd_positive")
    )
    if not rollback:
        label = "v1937-inner-handoff-failed"
        passed = False
        reason = "inner rollbackable V1937 handoff did not pass"
    elif not klog.get("contract_ok") or not klog.get("safety_ok"):
        label = "lower-publication-klog-contract-or-safety-regression"
        passed = False
        reason = "lower-publication klog fields were missing or safety flags regressed"
    elif combined and no_publication and missing_lower_domain:
        label = "native-service74-dms-wlfw-no-pdmapper-domain-wlanpd-publication"
        passed = True
        reason = (
            "native rerun reproduced service74/180, PM open, DMS/WLFW lookup, and WLFW wait, "
            "but lower klog has no pd-mapper/domain/wlan_pd/QMI-server publication text and no WLFW69/wlanmdsp/wlan0"
        )
    elif combined and no_publication:
        label = "native-dms-wlfw-publication-context-inconclusive"
        passed = False
        reason = "native combined DMS/WLFW wait reproduced, but lower klog context no longer matches the missing-domain signature"
    elif combined:
        label = "native-lower-publication-progress-stop"
        passed = True
        reason = "native lower WLAN-PD/WLFW publication progressed; stop before Wi-Fi HAL/scan/connect"
    else:
        label = "native-combined-prereq-regression"
        passed = False
        reason = "native rerun did not reproduce service74/PM-open/DMS/WLFW wait prerequisites"
    return {
        "label": label,
        "decision": f"v1976-{label}-{'rollback-pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "combined": combined,
        "no_publication": no_publication,
        "missing_lower_domain": missing_lower_domain,
    }


def count_text(values: list[int]) -> str:
    return ",".join(str(value) for value in values)


def render_klog_rows(klog: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for sample in klog["samples"]:
        rows.append(
            [
                sample["phase"],
                f"180={sample.get('count_180')} 74={sample.get('count_74')} qmi={sample.get('count_sysmon_qmi')}",
                f"pd_mapper={sample.get('raw_count_pd_mapper_text')} domain={sample.get('raw_count_wlan_pd_domain_text')} qmi_server={sample.get('raw_count_qmi_server_connected_text')} wlan_pd={sample.get('raw_count_wlan_pd_text')}",
                str(sample.get("last_pd_mapper") or sample.get("last_wlan_pd") or "missing"),
            ]
        )
    return rows


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["v1937_details"]
    klog = manifest["lower_klog"]
    classification = manifest["classification"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        [
            "combined",
            classification["combined"],
            f"service74={details.get('service74')} service180={details.get('service180')} pm_open={details.get('pm_open_subsys_modem')} lookup_ids={details.get('libqmi_lookup_service_ids')}",
        ],
        [
            "publication",
            not classification["no_publication"],
            f"wlfw69={details.get('wlfw69')} wlan_pd={details.get('wlan_pd')} wlanmdsp={details.get('wlanmdsp')} wlan0={details.get('wlan0')}",
        ],
        [
            "lower-domain",
            not classification["missing_lower_domain"],
            f"pd_mapper={count_text(klog['pd_mapper_counts'])} domain={count_text(klog['wlan_pd_domain_counts'])} qmi_server={count_text(klog['qmi_server_connected_counts'])}",
        ],
        [
            "safety",
            klog["safety_ok"],
            "no_esoc0_open/no_fake_online/no_pmic_gpio_gdsc_write stayed asserted",
        ],
    ]
    return "\n".join(
        [
            "# Native Init V1976 Lower Publication Context Handoff",
            "",
            "## Summary",
            "",
            f"- Cycle: `{manifest['cycle']}`",
            f"- Decision: `{classification['decision']}`",
            f"- Label: `{classification['label']}`",
            f"- Pass: `{classification['pass']}`",
            f"- Reason: {classification['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            f"- V1937 manifest: `{manifest['v1937_manifest']}`",
            f"- Inner handoff: `{manifest['inner_handoff_manifest']}`",
            "",
            "## Gate",
            "",
            "V1975 showed native is not missing DMS/WLFW libqmi service discovery. V1976 reruns the same internal-modem native combo and classifies whether the lower publication context advances into pd-mapper/domain/wlan_pd/QMI-server text before WLFW69 remains absent.",
            "",
            "## Matrix",
            "",
            markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
            "",
            "## Lower Klog Samples",
            "",
            markdown_table(["phase", "service text", "publication text", "first missing-focus line"], render_klog_rows(klog)),
            "",
            "## Key Edges",
            "",
            f"- First DMS lookup: `{manifest['first_dms_lookup']}`",
            f"- First WLFW lookup: `{manifest['first_wlfw_lookup']}`",
            f"- First WLFW return: `{manifest['first_wlfw_return']}`",
            f"- First non-WLFW new-server: `{manifest['first_new_server']}`",
            "",
            "## Decision",
            "",
            "- Native rerun again reaches the internal-modem combo: service74/180, `/dev/subsys_modem` PM open, DMS lookup, and WLFW service69 wait.",
            "- The missing edge is below that: no pd-mapper/domain/wlan_pd/QMI-server publication text appears, and WLFW69/wlanmdsp/wlan0 remain absent.",
            "- Next live unit should pre-arm a safe native wrapper/strace around `pd-mapper` and `tftp_server` in this same combo to observe whether the modem ROOT-PD asks AP pd-mapper for wlan_pd and whether any `wlanmdsp.mbn` request is attempted. Do not revisit RIL, pm-service retries, eSoC/PCIe/MHI/GDSC, or Wi-Fi HAL/scan/connect before WLFW69 and `wlan0` exist.",
            "",
            "## Safety",
            "",
            "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
            "- No `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
            "- Mutation scope: `/cache` one-shot clean-DSP flag, V1936 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
            "",
        ]
    )


def first_line(details: dict[str, Any], event: str, needle: str = "") -> str:
    data = ((details.get("libqmi_events") or {}).get(event) or {})
    lines = [str(data.get("first_hit_line") or "")]
    lines.extend(str(data.get(f"sample_line_{index}") or "") for index in range(4))
    for line in lines:
        if line and line != "none" and (not needle or needle in line):
            return line
    return ""


def write_v1976_manifest(v1937_manifest: dict[str, Any]) -> dict[str, Any]:
    fields = parse_helper_fields()
    klog = collect_klog(fields)
    details = v1937_manifest.get("details") if isinstance(v1937_manifest.get("details"), dict) else {}
    classification = classify(v1937_manifest, klog)
    manifest = {
        "created": now_iso(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "v1937_manifest": rel(OUT_DIR / "manifest-v1937.json"),
        "inner_handoff_manifest": rel(HANDOFF_DIR / "manifest.json"),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "classification": classification,
        "lower_klog": klog,
        "v1937_details": details,
        "first_dms_lookup": first_line(details, "libqmi_get_service_list_lookup_call", "svc_id=0x2"),
        "first_wlfw_lookup": first_line(details, "libqmi_get_service_list_lookup_call", "svc_id=0x45"),
        "first_wlfw_return": first_line(details, "libqmi_get_service_list_lookup_ret", "cnss-daemon"),
        "first_new_server": first_line(details, "libqmi_xport_new_server_service"),
        "host_metadata": collect_host_metadata(),
    }
    store = EvidenceStore(OUT_DIR)
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary-v1976.md", report)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--classify-only",
        action="store_true",
        help="reuse an existing V1937 manifest in the V1976 evidence directory",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_v1937()
    rc = 0 if args.classify_only else v1937.main([])
    manifest_path = OUT_DIR / "manifest.json"
    if not manifest_path.exists():
        return rc or 1
    preserved_path = OUT_DIR / "manifest-v1937.json"
    if not preserved_path.exists() or not args.classify_only:
        shutil.copy2(manifest_path, preserved_path)
    v1937_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = write_v1976_manifest(v1937_manifest)
    print(json.dumps({"decision": manifest["decision"], "label": manifest["label"], "pass": manifest["pass"]}, sort_keys=True))
    return rc or (0 if manifest["pass"] else 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
