#!/usr/bin/env python3
"""V1932 service-notifier/ICNSS source-chain gap classifier."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1932"
OUT_DIR = repo_path("tmp/wifi/v1932-servnotif-icnss-source-gap")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1932_SERVNOTIF_ICNSS_SOURCE_GAP_2026-06-04.md")

V1916_MANIFEST = repo_path("tmp/wifi/v1916-android-broad-kallsyms-tracefs-handoff/manifest.json")
V1923_MANIFEST = repo_path("tmp/wifi/v1923-post-wlfw-qmi-service-delta/manifest.json")
V1931_MANIFEST = repo_path("tmp/wifi/v1931-android-servnotif-native-libqmi69-diff/manifest.json")

SOURCE_ROOT = repo_path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")
ICNSS_SOURCE = SOURCE_ROOT / "drivers/soc/qcom/icnss.c"
SERVICE_NOTIFIER_SOURCE = SOURCE_ROOT / "drivers/soc/qcom/service-notifier.c"
SERVICE_NOTIFIER_PRIVATE = SOURCE_ROOT / "drivers/soc/qcom/service-notifier-private.h"
CNSS2_QMI_SOURCE = SOURCE_ROOT / "drivers/net/wireless/cnss2/qmi.c"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def rel(path: Path | str) -> str:
    value = Path(path)
    try:
        return str(value.relative_to(repo_path(".")))
    except ValueError:
        return str(value)


def first_match(path: Path, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern)
    if not path.exists():
        return {"path": rel(path), "line": None, "text": "", "present": False}
    for line_no, line in enumerate(read_lines(path), start=1):
        if regex.search(line):
            return {"path": rel(path), "line": line_no, "text": line.strip(), "present": True}
    return {"path": rel(path), "line": None, "text": "", "present": False}


def source_anchor(name: str, path: Path, pattern: str, meaning: str) -> dict[str, Any]:
    anchor = first_match(path, pattern)
    anchor["name"] = name
    anchor["meaning"] = meaning
    return anchor


def source_chain() -> dict[str, Any]:
    anchors = {
        "icnss_register_callback": source_anchor(
            "icnss_register_callback",
            ICNSS_SOURCE,
            r"priv->service_notifier_nb\.notifier_call = icnss_service_notifier_notify",
            "ICNSS installs the callback used for WLAN-PD service state notifications",
        ),
        "icnss_register_notifier": source_anchor(
            "icnss_register_notifier",
            ICNSS_SOURCE,
            r"service_notif_register_notifier\(pd->domain_list\[i\]\.name",
            "ICNSS registers each service-locator domain name/instance with service-notifier",
        ),
        "icnss_state_up_callback": source_anchor(
            "icnss_state_up_callback",
            ICNSS_SOURCE,
            r"notification == SERVREG_NOTIF_SERVICE_STATE_UP_V01",
            "ICNSS observes SERVREG UP by clearing FW_DOWN in the notifier callback",
        ),
        "servnotif_public_api": source_anchor(
            "servnotif_public_api",
            SERVICE_NOTIFIER_SOURCE,
            r"void \*service_notif_register_notifier\(const char \*service_path, int instance_id",
            "Kernel clients enter the service-notifier path through service_notif_register_notifier",
        ),
        "servnotif_new_server": source_anchor(
            "servnotif_new_server",
            SERVICE_NOTIFIER_SOURCE,
            r"static int service_notifier_new_server\(struct qmi_handle \*qmi,",
            "QMI name-service arrival for SERVREG notifier instance queues listener registration",
        ),
        "servnotif_new_server_print": source_anchor(
            "servnotif_new_server_print",
            SERVICE_NOTIFIER_SOURCE,
            r"Connection established between QMI handle and %d service",
            "The Android/native 180 and 74 dmesg lines print runtime instance_id here",
        ),
        "servnotif_root_indication": source_anchor(
            "servnotif_root_indication",
            SERVICE_NOTIFIER_SOURCE,
            r"static void root_service_service_ind_cb",
            "Remote SERVREG state-up indications enter HLOS through root_service_service_ind_cb",
        ),
        "servnotif_indication_print": source_anchor(
            "servnotif_indication_print",
            SERVICE_NOTIFIER_SOURCE,
            r"Indication received from %s, state: 0x%x, trans-id: %d",
            "The Android WLAN-PD state-up dmesg line is emitted here",
        ),
        "servnotif_servreg_lookup": source_anchor(
            "servnotif_servreg_lookup",
            SERVICE_NOTIFIER_SOURCE,
            r"qmi_add_lookup\(&qmi_data->clnt_handle,",
            "service-notifier asks QRTR for SERVREG notifier service 0x42 with runtime instance",
        ),
        "servreg_service_id": source_anchor(
            "servreg_service_id",
            SERVICE_NOTIFIER_PRIVATE,
            r"#define SERVREG_NOTIF_SERVICE_ID_V01 0x42",
            "The service-notifier lookup service id is fixed 0x42; 180/74 are runtime instances",
        ),
        "cnss_wlfw_new_server": source_anchor(
            "cnss_wlfw_new_server",
            CNSS2_QMI_SOURCE,
            r"static int wlfw_new_server\(struct qmi_handle \*qmi_wlfw,",
            "CNSS handles WLFW service 69 publication in wlfw_new_server",
        ),
        "cnss_wlfw_lookup": source_anchor(
            "cnss_wlfw_lookup",
            CNSS2_QMI_SOURCE,
            r"qmi_add_lookup\(&plat_priv->qmi_wlfw, WLFW_SERVICE_ID_V01",
            "CNSS waits for WLFW service 0x45/69 after the userspace worker starts",
        ),
    }
    return {
        "anchors": anchors,
        "all_required_present": all(anchor["present"] for anchor in anchors.values()),
    }


def prior_evidence() -> dict[str, Any]:
    v1916 = read_json(V1916_MANIFEST)
    v1923 = read_json(V1923_MANIFEST)
    v1931 = read_json(V1931_MANIFEST)
    android_trace = v1916.get("context", {}).get("analysis", {})
    native_v1923 = v1923.get("native", {})
    native_v1931 = v1931.get("native", {})
    return {
        "v1916": {
            "manifest": rel(V1916_MANIFEST),
            "pass": bool(v1916.get("pass")),
            "label": v1916.get("label", ""),
            "service180_count": android_trace.get("service180_count"),
            "service74_count": android_trace.get("service74_count"),
            "wlan_pd_indication_count": android_trace.get("wlan_pd_indication_count"),
            "wlanmdsp_count": android_trace.get("wlanmdsp_count"),
            "wlan0_time_s": android_trace.get("dmesg", {}).get("wlan0_time_s"),
            "pcie_mhi_before_wlan0": android_trace.get("dmesg", {}).get("pcie_mhi_before_wlan0"),
            "degraded_257s_like": android_trace.get("dmesg", {}).get("degraded_257s_like"),
            "tracefs_status": android_trace.get("tracefs_status", {}),
            "symbol_counts": android_trace.get("symbol_counts", {}),
        },
        "v1923": {
            "manifest": rel(V1923_MANIFEST),
            "pass": bool(v1923.get("pass")),
            "label": v1923.get("label", ""),
            "service74": native_v1923.get("service74"),
            "service180": native_v1923.get("service180"),
            "pm_open_subsys_modem": native_v1923.get("pm_open_subsys_modem"),
            "holder_opened": native_v1923.get("holder_opened"),
            "wlfw_service_request_hit": native_v1923.get("wlfw_service_request_hit"),
            "wlfw_worker_success_hit": native_v1923.get("wlfw_worker_success_hit"),
            "wlfw_ind_register_hit": native_v1923.get("wlfw_ind_register_hit"),
            "wlfw_cap_hit": native_v1923.get("wlfw_cap_hit"),
            "wlfw69": native_v1923.get("wlfw69"),
            "wlan_pd": native_v1923.get("wlan_pd"),
            "wlanmdsp": native_v1923.get("wlanmdsp"),
            "wlan0": native_v1923.get("wlan0"),
        },
        "v1931": {
            "manifest": rel(V1931_MANIFEST),
            "pass": bool(v1931.get("pass")),
            "label": v1931.get("classification", {}).get("label", v1931.get("label", "")),
            "service74": native_v1931.get("service74"),
            "service180": native_v1931.get("service180"),
            "servloc_result": native_v1931.get("servloc_result"),
            "servloc_domain": native_v1931.get("servloc_domain"),
            "servloc_instance": native_v1931.get("servloc_instance"),
            "libqmi_lookup_service69_seen": native_v1931.get("libqmi_lookup_service69_seen"),
            "libqmi_new_server_service69_seen": native_v1931.get("libqmi_new_server_service69_seen"),
            "libqmi_lookup_service_ids": native_v1931.get("libqmi_lookup_service_ids", []),
            "libqmi_new_server_service_ids": native_v1931.get("libqmi_new_server_service_ids", []),
            "servnotif_late_state": native_v1931.get("servnotif_late_state"),
            "servnotif_late_indication": native_v1931.get("servnotif_late_indication"),
            "wlfw_wait_outstanding": native_v1931.get("wlfw_wait_outstanding"),
        },
    }


def classify(chain: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    v1916 = evidence["v1916"]
    v1923 = evidence["v1923"]
    v1931 = evidence["v1931"]
    android_normal_trace_limited = (
        v1916["pass"]
        and int(v1916.get("service180_count") or 0) > 0
        and int(v1916.get("service74_count") or 0) > 0
        and int(v1916.get("wlan_pd_indication_count") or 0) > 0
        and int(v1916.get("wlanmdsp_count") or 0) > 0
        and int(v1916.get("pcie_mhi_before_wlan0") or 0) == 0
        and not bool(v1916.get("degraded_257s_like"))
        and v1916.get("tracefs_status", {}).get("kprobe_events_exists") == "0"
    )
    native_combined_wait = (
        v1923["pass"]
        and bool(v1923.get("service74"))
        and bool(v1923.get("service180"))
        and bool(v1923.get("pm_open_subsys_modem"))
        and bool(v1923.get("holder_opened"))
        and int(v1923.get("wlfw_service_request_hit") or 0) > 0
        and int(v1923.get("wlfw_worker_success_hit") or 0) > 0
        and int(v1923.get("wlfw_ind_register_hit") or 0) == 0
        and int(v1923.get("wlfw_cap_hit") or 0) == 0
        and not bool(v1923.get("wlfw69"))
        and not bool(v1923.get("wlan_pd"))
    )
    native_missing_publication = (
        v1931["pass"]
        and bool(v1931.get("service74"))
        and bool(v1931.get("service180"))
        and v1931.get("servloc_result") == "domain-list-response-success"
        and v1931.get("servloc_domain") == "msm/modem/wlan_pd"
        and str(v1931.get("servloc_instance")) == "180"
        and bool(v1931.get("libqmi_lookup_service69_seen"))
        and not bool(v1931.get("libqmi_new_server_service69_seen"))
        and v1931.get("servnotif_late_state") == "uninit"
        and bool(v1931.get("wlfw_wait_outstanding"))
    )
    source_ready = bool(chain["all_required_present"])
    if source_ready and android_normal_trace_limited and native_combined_wait and native_missing_publication:
        label = "servnotif-icnss-domainlist-to-wlfw69-publication-gap"
        reason = (
            "source maps the ICNSS service-locator -> service-notifier -> SERVREG state-up -> WLFW69 path; "
            "Android normal proves the edge, but Android kernel kprobes are unavailable and native reaches A1+WLFW lookup while service69/WLAN-PD publication stays absent"
        )
        passed = True
    elif not source_ready:
        label = "servnotif-source-chain-incomplete"
        reason = "required ICNSS/service-notifier/WLFW source anchors were not all found"
        passed = False
    elif not android_normal_trace_limited:
        label = "android-normal-trace-baseline-incomplete"
        reason = "retained Android normal trace or tracefs capability evidence is incomplete"
        passed = False
    elif not native_combined_wait:
        label = "native-a1-post-wlfw-evidence-regressed"
        reason = "native V1923 no longer proves A1 plus WLFW worker waiting before indication/capability QMI"
        passed = False
    elif not native_missing_publication:
        label = "native-publication-state-changed-review"
        reason = "native V1931 no longer proves service69 publication missing after lookup"
        passed = True
    else:
        label = "servnotif-gap-review"
        reason = "source and retained evidence need manual review"
        passed = False
    return {
        "label": label,
        "decision": f"v1932-{label}-host-{'pass' if passed else 'fail'}",
        "pass": passed,
        "reason": reason,
        "source_ready": source_ready,
        "android_normal_trace_limited": android_normal_trace_limited,
        "native_combined_wait": native_combined_wait,
        "native_missing_publication": native_missing_publication,
    }


def anchor_rows(chain: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, anchor in chain["anchors"].items():
        line_ref = f"{anchor['path']}:{anchor['line']}" if anchor["line"] else anchor["path"]
        rows.append([name, str(anchor["present"]), line_ref, anchor["meaning"]])
    return rows


def evidence_rows(evidence: dict[str, Any], classification: dict[str, Any]) -> list[list[str]]:
    v1916 = evidence["v1916"]
    v1923 = evidence["v1923"]
    v1931 = evidence["v1931"]
    return [
        [
            "Android trace",
            str(classification["android_normal_trace_limited"]),
            f"180={v1916['service180_count']} 74={v1916['service74_count']} wlan_pd={v1916['wlan_pd_indication_count']} wlanmdsp={v1916['wlanmdsp_count']} pcie_mhi_before_wlan0={v1916['pcie_mhi_before_wlan0']}",
        ],
        [
            "Android tracefs",
            str(v1916.get("tracefs_status", {}).get("kprobe_events_exists") == "0"),
            f"kprobe_events={v1916.get('tracefs_status', {}).get('kprobe_events_exists')} uprobe_events={v1916.get('tracefs_status', {}).get('uprobe_events_exists')} available_filter_functions={v1916.get('tracefs_status', {}).get('available_filter_functions_exists')}",
        ],
        [
            "Native A1 wait",
            str(classification["native_combined_wait"]),
            f"service74={v1923['service74']} pm_open={v1923['pm_open_subsys_modem']} holder={v1923['holder_opened']} worker={v1923['wlfw_worker_success_hit']} ind={v1923['wlfw_ind_register_hit']} cap={v1923['wlfw_cap_hit']}",
        ],
        [
            "Native publication",
            str(classification["native_missing_publication"]),
            f"lookup69={v1931['libqmi_lookup_service69_seen']} new69={v1931['libqmi_new_server_service69_seen']} servnotif={v1931['servnotif_late_state']}/{v1931['servnotif_late_indication']} servloc={v1931['servloc_domain']}:{v1931['servloc_instance']}",
        ],
    ]


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    chain = manifest["source_chain"]
    evidence = manifest["evidence"]
    lines = [
        "# Native Init V1932 Servnotif/ICNSS Source Gap\n\n",
        "## Summary\n\n",
        f"- Cycle: `{CYCLE}`\n",
        f"- Decision: `{classification['decision']}`\n",
        f"- Label: `{classification['label']}`\n",
        f"- Pass: `{manifest['pass']}`\n",
        f"- Reason: {classification['reason']}\n",
        f"- Evidence: `{manifest['out_dir']}`\n\n",
        "## Source Chain\n\n",
        markdown_table(["anchor", "present", "line", "meaning"], anchor_rows(chain)),
        "\n\n## Retained Evidence\n\n",
        markdown_table(["area", "pass", "detail"], evidence_rows(evidence, classification)),
        "\n\n## Decision\n\n",
        "- The Android state-up edge is not a pm-service/msg22/eSoC/PCIe/GDSC path. Source maps it to ICNSS registering the `msm/modem/wlan_pd` service-locator domain with service-notifier, then receiving a SERVREG state-up indication.\n",
        "- Native already reaches the A1 surface: clean-DSP/sibling-sysmon service74/service180, PM `/dev/subsys_modem` open, modem holder, DMS request, and CNSS WLFW worker/service69 lookup.\n",
        "- The missing transition is remote publication/state-up: no `root_service_service_ind_cb` WLAN-PD indication and no WLFW service69 `new_server` before the worker can send indication/capability QMI.\n",
        "- Android kernel kprobe observation is not available from retained tracefs (`kprobe_events=0`), so the next live unit should be native-side and source-aligned.\n\n",
        "## Next Read-Only Unit\n\n",
        "- Prefer native helper-mounted tracefs if available: observe `service_notif_register_notifier`, `service_notifier_new_server`, `root_service_service_ind_cb`, `qmi_add_lookup` for SERVREG 0x42/instance 180, and `wlfw_new_server`/WLFW 0x45.\n",
        "- If kernel kprobes are unavailable, fall back to native dmesg/QRTR/libqmi wait snapshots around the same A1 boot window.\n",
        "- Stop before Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until native exposes WLFW69/WLAN-PD and `wlan0`.\n\n",
        "## Safety Scope\n\n",
        "Host-only. This classifier reads retained manifests and local source text only. It does not issue live device commands, flash, reboot, stage properties, write firmware/partitions, remount-write, open `/dev/subsys_esoc0`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, external ping, force RC1/case, touch PMIC/GPIO/GDSC/regulators, rescan PCI, bind/unbind platforms, fake ONLINE, or send eSoC notify/BOOT_DONE.\n",
    ]
    return "".join(lines)


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    chain = source_chain()
    evidence = prior_evidence()
    classification = classify(chain, evidence)
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "pass": bool(classification["pass"]),
        "decision": classification["decision"],
        "label": classification["label"],
        "reason": classification["reason"],
        "classification": classification,
        "source_chain": chain,
        "evidence": evidence,
        "host_metadata": host_metadata,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"label={manifest['label']} "
        f"source_ready={classification['source_ready']} "
        f"native_missing_publication={classification['native_missing_publication']} "
        f"out_dir={manifest['out_dir']}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
