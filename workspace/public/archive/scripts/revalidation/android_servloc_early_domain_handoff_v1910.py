#!/usr/bin/env python3
"""V1910 autonomous Android-good early service-locator domain-list handoff."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path

import android_servloc_domain_handoff_v1909 as base


CYCLE = "V1910"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1910-android-early-servloc-domain-handoff")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1910_ANDROID_EARLY_SERVLOC_DOMAIN_HANDOFF_2026-06-03.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1910-android-early-servloc-domain-handoff.txt")
MODULE_NAME = "a90_v1910_early_servloc"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1910-early-servloc"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1910_early_servloc"
BASE_CLASSIFY_RESULT = base.classify_result


def module_prop() -> str:
    return "\n".join([
        f"id={MODULE_NAME}",
        "name=A90 V1910 Android early servloc observer",
        "version=1",
        "versionCode=1",
        "author=A90 native-init project",
        "description=Temporary Android-good early read-only service-locator wlan/fw observer. Remove after capture.",
        "",
    ])


def post_fs_data_script(samples: int, delay_us: int) -> str:
    del samples, delay_us
    filter_expr = (
        "service-locator|servloc|domain|service-notifier|service_notifier|ssctl|SSCTL|"
        "wlanmdsp|wlan[_/-]?pd|wlan/fw|wlfw_service_request|WLFW|wlfw|icnss|cnss|"
        "tftp|wlan0|PCIe|pcie|MHI|mhi|pcie_initialized|mhi_enable|esoc0|boot_failed"
    )
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
MOD={REMOTE_MODULE_DIR}
BIN="$MOD/{base.SERVLOC_BINARY_NAME}"
FILTER='{filter_expr}'
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
LOG="$OUT/samples.log"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
PROPS="$OUT/props.txt"
SUMMARY="$OUT/query-summary.txt"

uptime_now() {{
  cat /proc/uptime 2>/dev/null | awk '{{print $1}}'
}}

write_status() {{
  now="$(uptime_now)"
  echo "A90_V1910_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

dump_filtered() {{
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 2500 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -d 2>/dev/null | grep -Ei "$FILTER" | tail -n 3000 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.pm-service init.svc.vendor.rmt_storage init.svc.vendor.tftp_server init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.pm-service ro.boottime.vendor.tftp_server ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}

summarize_queries() {{
  {{
    printf 'success_count='
    grep -Rhs '^a90_servloc_query.response_success=1$' "$OUT"/query-*.txt 2>/dev/null | wc -l
    printf 'domain74_seen='
    grep -Rhs '^a90_servloc_query.domain[.][0-9][0-9]*[.]instance_id=74$' "$OUT"/query-*.txt 2>/dev/null | grep -q . && echo 1 || echo 0
    printf 'domain180_seen='
    grep -Rhs '^a90_servloc_query.domain[.][0-9][0-9]*[.]instance_id=180$' "$OUT"/query-*.txt 2>/dev/null | grep -q . && echo 1 || echo 0
    printf 'early_success='
    grep -q '^a90_servloc_query.response_success=1$' "$OUT"/query-early.txt 2>/dev/null && echo 1 || echo 0
    printf 'late_success='
    grep -q '^a90_servloc_query.response_success=1$' "$OUT"/query-late.txt 2>/dev/null && echo 1 || echo 0
  }} > "$SUMMARY.tmp"
  mv "$SUMMARY.tmp" "$SUMMARY" 2>/dev/null || true
}}

(
  umask 022
  write_status start
  : > "$LOG"
  echo "A90_V1910_POSTFS_BEGIN uptime=$(uptime_now)" >> "$LOG"
  echo "A90_V1910_SAMPLE_BEGIN index=early uptime=$(uptime_now)" >> "$LOG"
  echo "A90_V1521_SAMPLE_BEGIN index=early uptime=$(uptime_now)" >> "$LOG"
  early_begin="$(uptime_now)"
  if [ -x "$BIN" ]; then
    "$BIN" --lookup-wait-ms 12000 --lookup-poll-ms 1000 --lookup-retry-ms 50 --response-ms 2500 > "$OUT/query-early.txt" 2>&1
    rc=$?
  else
    echo "a90_servloc_query.result=missing-binary" > "$OUT/query-early.txt"
    rc=127
  fi
  early_end="$(uptime_now)"
  echo "a90_servloc_query.wrapper.label=early" >> "$OUT/query-early.txt"
  echo "a90_servloc_query.wrapper.uptime_begin=$early_begin" >> "$OUT/query-early.txt"
  echo "a90_servloc_query.wrapper.uptime_end=$early_end" >> "$OUT/query-early.txt"
  echo "a90_servloc_query.wrapper.rc=$rc" >> "$OUT/query-early.txt"
  cat "$OUT/query-early.txt" >> "$LOG" 2>/dev/null || true
  summarize_queries
  echo "A90_V1521_SAMPLE_END index=early uptime=$(uptime_now)" >> "$LOG"
  echo "A90_V1910_SAMPLE_END index=early uptime=$(uptime_now)" >> "$LOG"
  write_status early-query
  sleep 16
  dump_filtered
  dump_props
  echo "A90_V1910_SAMPLE_BEGIN index=late uptime=$(uptime_now)" >> "$LOG"
  if [ -x "$BIN" ]; then
    "$BIN" --lookup-wait-ms 1500 --lookup-poll-ms 1500 --response-ms 2500 > "$OUT/query-late.txt" 2>&1
    rc=$?
  else
    echo "a90_servloc_query.result=missing-binary" > "$OUT/query-late.txt"
    rc=127
  fi
  echo "a90_servloc_query.wrapper.label=late" >> "$OUT/query-late.txt"
  echo "a90_servloc_query.wrapper.rc=$rc" >> "$OUT/query-late.txt"
  cat "$OUT/query-late.txt" >> "$LOG" 2>/dev/null || true
  dump_filtered
  dump_props
  summarize_queries
  echo "SRC early_servloc_domain_observer" >> "$LOG"
  cat "$SUMMARY" >> "$LOG" 2>/dev/null || true
  echo "A90_V1910_POSTFS_END uptime=$(uptime_now)" >> "$LOG"
  write_status done
  touch "$OUT/done"
  chmod 755 "$OUT" 2>/dev/null
  chmod 644 "$OUT"/* 2>/dev/null
) >/dev/null 2>&1 &
exit 0
"""


def query_summaries(base_dir: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path in sorted(base_dir.glob("query-*.txt"), key=lambda item: item.name):
        if path.name == "query-summary.txt":
            continue
        text = base.read_file(path)
        values = base.parse_key_values(text, "a90_servloc_query.")
        instances = sorted({base.intish(value) for key, value in values.items() if re.match(r"domain[.]\d+[.]instance_id", key)})
        names = [value for key, value in values.items() if re.match(r"domain[.]\d+[.]name$", key)]
        summaries.append({
            "file": base.rel(path),
            "name": path.name,
            "success": values.get("response_success") == "1",
            "result": values.get("result", ""),
            "domain_count": base.intish(values.get("domain_count")),
            "wlan_like_domains": base.intish(values.get("wlan_like_domains")),
            "instances": instances,
            "names": names,
            "wrapper_label": values.get("wrapper.label", ""),
            "wrapper_uptime_begin": values.get("wrapper.uptime_begin", ""),
            "wrapper_uptime_end": values.get("wrapper.uptime_end", ""),
            "wrapper_rc": base.intish(values.get("wrapper.rc")),
            "endpoint_found": values.get("endpoint.found", ""),
            "endpoint_found_ms": base.intish(values.get("endpoint.found_ms")),
            "send_ms": base.intish(values.get("send.ms")),
            "response_ms": base.intish(values.get("response.ms")),
            "raw_excerpt": "\n".join(text.splitlines()[:100]),
        })
    return summaries


def dmesg_time(line: str) -> float | None:
    match = base.DMESG_TIME_RE.search(line or "")
    return float(match.group("time")) if match else None


def classify_result(base_decision: str,
                    base_pass: bool,
                    context: dict[str, Any],
                    native: dict[str, Any],
                    selftest_ok: bool) -> tuple[str, bool, str, str]:
    decision, pass_ok, reason, label = BASE_CLASSIFY_RESULT(base_decision, base_pass, context, native, selftest_ok)
    if not pass_ok:
        return (decision.replace("v1909", "v1910", 1), pass_ok, reason, label)
    analysis = context.get("analysis") or {}
    early = next((item for item in analysis.get("query_success_examples", []) if item.get("name") == "query-early.txt"), None)
    if not early:
        queries = analysis.get("query_success_examples", [])
        early = next((item for item in queries if item.get("wrapper_label") == "early"), None)
    first_service74_s = dmesg_time(analysis.get("first_service74_line", ""))
    first_wlan_pd_s = dmesg_time(analysis.get("first_wlan_pd_line", ""))
    if not early:
        return (
            "v1910-android-early-servloc-window-missed-rollback-pass",
            True,
            "normal Android state-up was captured, but the early service-locator query did not return before the window",
            "android-early-servloc-window-missed",
        )
    send_s = float(early.get("send_ms") or 0) / 1000.0
    response_s = float(early.get("response_ms") or 0) / 1000.0
    before_service74 = first_service74_s is not None and send_s > 0 and send_s < first_service74_s
    before_wlan_pd = first_wlan_pd_s is not None and response_s > 0 and response_s < first_wlan_pd_s
    if 74 in (early.get("instances") or []):
        return (
            "v1910-android-early-servloc-domain74-native-180-only-diff-pass",
            True,
            "early Android service-locator query sees instance 74 before the WLAN-PD state-up window while native V1908 returns only 180",
            "android-early-servloc-domain74-native-180-only",
        )
    if 180 in (early.get("instances") or []) and before_service74 and before_wlan_pd:
        return (
            "v1910-android-early-servloc-180-only-before-service74-pass",
            True,
            "early Android service-locator query still sees only instance 180 before service-notifier 74 and wlan_pd state-up",
            "android-early-servloc-180-only-before-service74",
        )
    if 180 in (early.get("instances") or []) and before_wlan_pd:
        return (
            "v1910-android-early-servloc-180-only-after-service74-before-wlanpd-pass",
            True,
            "early Android service-locator query sees only instance 180 after service74 publication but before wlan_pd state-up",
            "android-early-servloc-180-only-after-service74-before-wlanpd",
        )
    if 180 in (early.get("instances") or []):
        return (
            "v1910-android-servloc-180-only-timing-not-decisive-rollback-pass",
            True,
            "Android service-locator query sees only instance 180, but its timing is not early enough to decide whether instance 74 was ever in the locator response",
            "android-servloc-180-only-timing-not-decisive",
        )
    return (
        "v1910-android-early-servloc-domain-result-incomplete",
        False,
        "early Android service-locator query succeeded but parsed neither instance 74 nor 180",
        "android-early-servloc-domain-result-incomplete",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    native = manifest.get("native_v1908") or {}
    early = next((item for item in analysis.get("query_success_examples", []) if item.get("name") == "query-early.txt"), {})
    first_service74_s = dmesg_time(analysis.get("first_service74_line", ""))
    first_wlan_pd_s = dmesg_time(analysis.get("first_wlan_pd_line", ""))
    early_send_s = float(early.get("send_ms") or 0) / 1000.0 if early else 0.0
    early_response_s = float(early.get("response_ms") or 0) / 1000.0 if early else 0.0
    return "\n".join([
        "# V1910 Android Early Service-locator Domain-list Handoff",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- label: `{manifest['label']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- evidence: `{base.rel(Path(manifest['out_dir']))}`",
        "",
        "## Android Early Query",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["android_dir", analysis.get("android_dir")],
                ["query success/count/instances/names", f"{analysis.get('query_success_count')}/{analysis.get('query_count')}/{json.dumps(analysis.get('query_instances'))}/{json.dumps(analysis.get('query_names'))}"],
                ["early instances/names", f"{json.dumps(early.get('instances', []))}/{json.dumps(early.get('names', []))}"],
                ["early send/response vs service74/wlan_pd", f"{early_send_s}/{early_response_s}/{first_service74_s}/{first_wlan_pd_s}"],
                ["service74/service180/wlan_pd/wlanmdsp/wlan0", f"{analysis.get('service74_count')}/{analysis.get('service180_count')}/{analysis.get('wlan_pd_indication_count')}/{analysis.get('wlanmdsp_count')}/{dmesg.get('wlan0_time_s')}"],
                ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
            ],
        ),
        "",
        "## Native Baseline",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["manifest", native.get("manifest")],
                ["decision/pass/label", f"{native.get('decision')}/{native.get('pass')}/{native.get('label')}"],
                ["servloc result/count/name/instance", f"{native.get('servloc_result')}/{native.get('servloc_count')}/{native.get('servloc_name')}/{native.get('servloc_instance')}"],
                ["service74/wlan_pd counts", f"{native.get('service74_counts')}/{native.get('wlan_pd_counts')}"],
            ],
        ),
        "",
        "## Query Example",
        "",
        "```text",
        early.get("raw_excerpt", analysis.get("query_first_excerpt", "")),
        "```",
        "",
        "## Rollback Gate",
        "",
        f"- native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
        f"- base handoff decision/pass: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
        "",
        "## Safety",
        "",
        "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module runs only a read-only AF_QIPCRTR service-locator get-domain-list query for `wlan/fw` plus delayed log capture. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, or partition write beyond the declared boot-image handoff/rollback.",
        "",
        "## Next",
        "",
        "- If the label remains 180-only before service74, stop treating service-locator domain content as the source of service74 and instrument the SERVREG publisher/consumer edge.",
        "",
    ])


def configure() -> None:
    base.CYCLE = CYCLE
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.LATEST_POINTER = LATEST_POINTER
    base.MODULE_NAME = MODULE_NAME
    base.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    base.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    base.REMOTE_STAGE_PREFIX = REMOTE_STAGE_PREFIX
    base.module_prop = module_prop
    base.post_fs_data_script = post_fs_data_script
    base.query_summaries = query_summaries
    base.classify_result = classify_result
    base.render_summary = render_summary


def main() -> int:
    configure()
    return base.main()


if __name__ == "__main__":
    sys.exit(main())
