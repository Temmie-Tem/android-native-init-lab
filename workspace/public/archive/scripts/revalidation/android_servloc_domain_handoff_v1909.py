#!/usr/bin/env python3
"""V1909 autonomous Android-good service-locator domain-list handoff.

Flash Android, install a temporary Magisk post-fs-data module that repeatedly
runs a standalone read-only AF_QIPCRTR service-locator `wlan/fw` domain-list
query, capture the normal internal-modem WLAN window, then remove the module and
roll back to native v724.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521
import android_wlan_pd_firmware_request_handoff_v1753 as v1753


CYCLE = "V1909"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1909-android-servloc-domain-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v725_fasttransport.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1909_ANDROID_SERVLOC_DOMAIN_HANDOFF_2026-06-03.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1909-android-servloc-domain-handoff.txt")
MODULE_NAME = "a90_v1909_servloc_domain"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1909-servloc-domain"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1909_servloc_domain"
SERVLOC_SOURCE = Path("stage3/linux_init/helpers/a90_servloc_query.c")
SERVLOC_BINARY_NAME = "a90_servloc_query"
DEFAULT_V1908_MANIFEST = Path("tmp/wifi/v1908-servloc-domain-list-live-handoff/manifest.json")
REDACT_CMD = "sed -E 's/t[e]mmie[[:alnum:]_@.-]*/[REDACTED]/g'"
ORIGINAL_BUILD_PLAN = v1521.build_plan

DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
WLAN0_RE = re.compile(r"\bdev : wlan0\b|\bicnss .*wlan0", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
WLFW_REQUEST_RE = re.compile(r"wlfw_service_request", re.IGNORECASE)
WLANMDSP_RE = re.compile(r"wlanmdsp\.mbn", re.IGNORECASE)
SERVICE74_RE = re.compile(r"service_notifier_new_server: .* 74 service", re.IGNORECASE)
SERVICE180_RE = re.compile(r"service_notifier_new_server: .* 180 service", re.IGNORECASE)
PCIE_MHI_RE = re.compile(r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable", re.IGNORECASE)
ESOC_BOOT_FAILED_RE = re.compile(r"esoc0.*boot.*fail|boot_failed", re.IGNORECASE)
FILTER_RE = re.compile(
    r"service-locator|servloc|domain|service-notifier|service_notifier|ssctl|SSCTL|"
    r"wlanmdsp|wlan[_/-]?pd|wlan/fw|wlfw_service_request|WLFW|wlfw|icnss|cnss|"
    r"tftp|wlan0|PCIe|pcie|MHI|mhi|pcie_initialized|mhi_enable|esoc0|boot_failed",
    re.IGNORECASE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def remote_quote(path: str) -> str:
    return v1753.remote_quote(path)


def read_file(path: Path, limit: int = 5_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--native-expect-version", default=DEFAULT_NATIVE_EXPECT_VERSION)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=v1521.DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=v1521.DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=v1521.DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=v1521.DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--recovery-timeout", type=int, default=240)
    parser.add_argument("--android-timeout", type=int, default=420)
    parser.add_argument("--sampler-samples", type=int, default=18)
    parser.add_argument("--sampler-delay-us", type=int, default=500000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=180)
    parser.add_argument("--servloc-source", type=Path, default=SERVLOC_SOURCE)
    parser.add_argument("--v1908-manifest", type=Path, default=DEFAULT_V1908_MANIFEST)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def module_prop() -> str:
    return "\n".join([
        f"id={MODULE_NAME}",
        "name=A90 V1909 Android servloc domain observer",
        "version=1",
        "versionCode=1",
        "author=A90 native-init project",
        "description=Temporary Android-good read-only service-locator wlan/fw domain-list observer. Remove after capture.",
        "",
    ])


def sepolicy_rule() -> str:
    return """# Temporary V1909 diagnostic policy for read-only AF_QIPCRTR observation.
allow magisk vendor_file dir { getattr open read search };
allow magisk vendor_file file { execute execute_no_trans getattr map open read };
allow magisk shell_data_file dir { add_name create getattr open read remove_name search write };
allow magisk shell_data_file file { append create getattr open read setattr unlink write };
allow magisk adb_data_file dir { add_name create getattr open read remove_name search write };
allow magisk adb_data_file file { append create getattr open read setattr unlink write };
"""


def post_fs_data_script(samples: int, delay_us: int) -> str:
    filter_expr = (
        "service-locator|servloc|domain|service-notifier|service_notifier|ssctl|SSCTL|"
        "wlanmdsp|wlan[_/-]?pd|wlan/fw|wlfw_service_request|WLFW|wlfw|icnss|cnss|"
        "tftp|wlan0|PCIe|pcie|MHI|mhi|pcie_initialized|mhi_enable|esoc0|boot_failed"
    )
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
MOD={REMOTE_MODULE_DIR}
BIN="$MOD/{SERVLOC_BINARY_NAME}"
SAMPLES={samples}
DELAY_US={delay_us}
FILTER='{filter_expr}'
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
LOG="$OUT/samples.log"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
PROPS="$OUT/props.txt"
SUMMARY="$OUT/query-summary.txt"

write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1909_STATUS $1 $now" > "$STATUS"
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
    printf 'wlan0_seen='
    cat "$DMESG" "$LOGCAT" 2>/dev/null | grep -Eiq '\bwlan0\b' && echo 1 || echo 0
    printf 'wlan_pd_seen='
    cat "$DMESG" 2>/dev/null | grep -Eiq 'service-notifier: .*msm/modem/wlan_pd' && echo 1 || echo 0
    printf 'service74_seen='
    cat "$DMESG" 2>/dev/null | grep -Eiq 'service_notifier_new_server: .* 74 service' && echo 1 || echo 0
    printf 'service180_seen='
    cat "$DMESG" 2>/dev/null | grep -Eiq 'service_notifier_new_server: .* 180 service' && echo 1 || echo 0
  }} > "$SUMMARY.tmp"
  mv "$SUMMARY.tmp" "$SUMMARY" 2>/dev/null || true
}}

(
  umask 022
  write_status start
  : > "$LOG"
  echo "A90_V1909_POSTFS_BEGIN" >> "$LOG"
  id >> "$LOG" 2>&1 || true
  cat /proc/self/attr/current >> "$LOG" 2>&1 || true
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1909_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    if [ -x "$BIN" ]; then
      "$BIN" > "$OUT/query-$i.txt" 2>&1
      rc=$?
    else
      echo "a90_servloc_query.result=missing-binary" > "$OUT/query-$i.txt"
      rc=127
    fi
    echo "a90_servloc_query.wrapper.index=$i" >> "$OUT/query-$i.txt"
    echo "a90_servloc_query.wrapper.rc=$rc" >> "$OUT/query-$i.txt"
    cat "$OUT/query-$i.txt" >> "$LOG" 2>/dev/null || true
    dump_filtered
    dump_props
    summarize_queries
    echo "SRC servloc_domain_observer" >> "$LOG"
    cat "$SUMMARY" >> "$LOG" 2>/dev/null || true
    echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    echo "A90_V1909_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    write_status "sample $i"
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  dump_filtered
  dump_props
  summarize_queries
  echo "A90_V1909_POSTFS_END" >> "$LOG"
  write_status done
  touch "$OUT/done"
  chmod 755 "$OUT" 2>/dev/null
  chmod 644 "$OUT"/* 2>/dev/null
) >/dev/null 2>&1 &
exit 0
"""


def module_stage_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "magisk-module"


def build_servloc_binary(source: Path, output: Path) -> tuple[str, str]:
    command = [
        "aarch64-linux-gnu-gcc",
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-o",
        str(output),
        str(repo_path(source)),
    ]
    result = subprocess.run(command, cwd=repo_path("."), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stdout)
    subprocess.run(["aarch64-linux-gnu-strip", str(output)], cwd=repo_path("."), check=True)
    sha = subprocess.run(["sha256sum", str(output)], cwd=repo_path("."), text=True, stdout=subprocess.PIPE, check=True).stdout.split()[0]
    info = subprocess.run(["file", str(output)], cwd=repo_path("."), text=True, stdout=subprocess.PIPE, check=True).stdout.strip()
    return sha, info


def prepare_module(store: EvidenceStore, args: argparse.Namespace, execute: bool) -> v1521.StepResult:
    started = time.monotonic()
    if not execute:
        return v1521.write_step(store, "prepare-v1909-magisk-module", "host:prepare temporary servloc Magisk module", "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    stage = module_stage_dir(store)
    ensure_private_dir(stage)
    binary = stage / SERVLOC_BINARY_NAME
    sha, info = build_servloc_binary(args.servloc_source, binary)
    write_private_text(stage / "module.prop", module_prop())
    write_private_text(stage / "post-fs-data.sh", post_fs_data_script(args.sampler_samples, args.sampler_delay_us))
    write_private_text(stage / "sepolicy.rule", sepolicy_rule())
    (stage / "post-fs-data.sh").chmod(0o700)
    binary.chmod(0o700)
    (stage / "sepolicy.rule").chmod(0o600)
    text = "\n".join([
        f"module_dir={rel(stage)}",
        f"servloc_source={rel(repo_path(args.servloc_source))}",
        f"servloc_binary={rel(binary)}",
        f"servloc_sha256={sha}",
        f"servloc_file={info}",
        f"samples={args.sampler_samples}",
        f"delay_us={args.sampler_delay_us}",
        "files=module.prop post-fs-data.sh sepolicy.rule a90_servloc_query",
        "",
    ])
    return v1521.write_step(store, "prepare-v1909-magisk-module", "host:prepare temporary servloc Magisk module", text, "", 0, time.monotonic() - started)


def install_module_android_steps(args: argparse.Namespace, store: EvidenceStore) -> list[tuple[str, list[str], int]]:
    stage = module_stage_dir(store)
    remote_prop = f"{REMOTE_STAGE_PREFIX}_module.prop"
    remote_postfs = f"{REMOTE_STAGE_PREFIX}_post-fs-data.sh"
    remote_policy = f"{REMOTE_STAGE_PREFIX}_sepolicy.rule"
    remote_binary = f"{REMOTE_STAGE_PREFIX}_{SERVLOC_BINARY_NAME}"
    install_shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)}; "
        f"mkdir -p {remote_quote(REMOTE_MODULE_DIR)}; "
        f"cp {remote_quote(remote_prop)} {remote_quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"cp {remote_quote(remote_postfs)} {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"cp {remote_quote(remote_policy)} {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"cp {remote_quote(remote_binary)} {remote_quote(REMOTE_MODULE_DIR)}/{SERVLOC_BINARY_NAME}; "
        f"chmod 600 {remote_quote(REMOTE_MODULE_DIR)}/module.prop {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"chmod 700 {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh {remote_quote(REMOTE_MODULE_DIR)}/{SERVLOC_BINARY_NAME}; "
        f"rm -f {remote_quote(remote_prop)} {remote_quote(remote_postfs)} {remote_quote(remote_policy)} {remote_quote(remote_binary)}; "
        "sync"
    )
    return [
        ("push-v1909-module-prop-android", [*v1521.adb_base(args), "push", str(stage / "module.prop"), remote_prop], args.timeout),
        ("push-v1909-post-fs-data-android", [*v1521.adb_base(args), "push", str(stage / "post-fs-data.sh"), remote_postfs], args.timeout),
        ("push-v1909-sepolicy-android", [*v1521.adb_base(args), "push", str(stage / "sepolicy.rule"), remote_policy], args.timeout),
        ("push-v1909-servloc-binary-android", [*v1521.adb_base(args), "push", str(stage / SERVLOC_BINARY_NAME), remote_binary], args.timeout * 2),
        ("install-v1909-module-android-su", [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(install_shell)], args.timeout),
    ]


def cleanup_module_android_command(args: argparse.Namespace) -> list[str]:
    shell = f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)} {remote_quote(REMOTE_STAGE_PREFIX)}_*; sync"
    return [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(shell)]


def cleanup_module_recovery_best_effort_command(args: argparse.Namespace) -> list[str]:
    return [*v1521.adb_base(args), "shell", f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)} {remote_quote(REMOTE_STAGE_PREFIX)}_* 2>/dev/null || true; sync"]


def redacted_a90ctl_command(kind: str) -> list[str]:
    if kind == "version":
        inner = f"python3 scripts/revalidation/a90ctl.py --json version | {REDACT_CMD}"
    elif kind == "status":
        inner = f"python3 scripts/revalidation/a90ctl.py status | {REDACT_CMD}"
    else:
        raise ValueError(kind)
    return ["bash", "-lc", inner]


def redacted_shell_pipeline(command: list[str]) -> list[str]:
    return ["bash", "-lc", f"set -o pipefail; {shlex.join(command)} | {REDACT_CMD}"]


def build_plan_v1909(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    plan = ORIGINAL_BUILD_PLAN(args, store, android_image, native_image)
    updated: list[tuple[str, list[str] | str, int]] = []
    for name, command, timeout in plan:
        if name == "native-version":
            updated.append(("native-version-redacted", redacted_a90ctl_command("version"), timeout))
        elif name == "native-status":
            updated.append(("native-status-redacted", redacted_a90ctl_command("status"), timeout))
        elif name == "restore-native" and isinstance(command, list):
            updated.append((name, redacted_shell_pipeline(command), timeout))
        else:
            updated.append((name, command, timeout))
    updated.append(("post-rollback-native-status-redacted", redacted_a90ctl_command("status"), args.timeout))
    return updated


def configure_v1521_engine() -> None:
    v1521.MODULE_NAME = MODULE_NAME
    v1521.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1521.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1521.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1521.DEFAULT_NATIVE_IMAGE = DEFAULT_NATIVE_IMAGE
    v1521.DEFAULT_NATIVE_EXPECT_VERSION = DEFAULT_NATIVE_EXPECT_VERSION
    v1521.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    v1521.LATEST_POINTER = LATEST_POINTER
    v1521.module_prop = module_prop
    v1521.post_fs_data_script = post_fs_data_script
    v1521.prepare_module = prepare_module
    v1521.install_module_android_steps = install_module_android_steps
    v1521.cleanup_module_android_command = cleanup_module_android_command
    v1521.cleanup_module_recovery_best_effort_command = cleanup_module_recovery_best_effort_command
    v1521.analyze_pulled_evidence = analyze_pulled_evidence
    v1521.build_plan = build_plan_v1909


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / Path(REMOTE_EVIDENCE_DIR).name
    return candidate if candidate.is_dir() else root


def parse_key_values(text: str, prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if prefix and key.startswith(prefix):
            key = key[len(prefix):]
        result[key] = value.strip()
    return result


def first_dmesg_time(lines: list[str], regex: re.Pattern[str]) -> float | None:
    for line in lines:
        if not regex.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_lines(lines: list[str] | str, regex: re.Pattern[str]) -> int:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    return sum(1 for line in iterable if regex.search(line))


def first_line(lines: list[str] | str, regex: re.Pattern[str]) -> str:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    for line in iterable:
        if regex.search(line):
            return line.strip()
    return ""


def count_dmesg_before(lines: list[str], regex: re.Pattern[str], before_time: float | None) -> int:
    count = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before_time is not None and float(match.group("time")) > before_time:
            continue
        if regex.search(line):
            count += 1
    return count


def query_summaries(base: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path in sorted(base.glob("query-*.txt"), key=lambda p: p.name):
        text = read_file(path)
        values = parse_key_values(text, "a90_servloc_query.")
        instances = sorted({intish(value) for key, value in values.items() if re.match(r"domain\.\d+\.instance_id", key)})
        names = [value for key, value in values.items() if re.match(r"domain\.\d+\.name$", key)]
        summaries.append({
            "file": rel(path),
            "name": path.name,
            "success": values.get("response_success") == "1",
            "result": values.get("result", ""),
            "domain_count": intish(values.get("domain_count")),
            "wlan_like_domains": intish(values.get("wlan_like_domains")),
            "instances": instances,
            "names": names,
            "wrapper_rc": intish(values.get("wrapper.rc")),
            "endpoint_found": values.get("endpoint.found", ""),
            "raw_excerpt": "\n".join(text.splitlines()[:80]),
        })
    return summaries


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = v1521.pulled_evidence_dir(store)
    base = evidence_base(store)
    samples = read_file(base / "samples.log")
    dmesg = read_file(base / "dmesg-filtered.txt") + "\n" + read_file(root / "host-dmesg-filtered.txt")
    logcat = read_file(base / "logcat-filtered.txt")
    props = read_file(base / "props.txt")
    status = read_file(base / "status.txt")
    summary_text = read_file(base / "query-summary.txt")
    queries = query_summaries(base)
    successful = [item for item in queries if item["success"]]
    instance_set = sorted({instance for item in successful for instance in item["instances"]})
    name_set = sorted({name for item in successful for name in item["names"]})
    dmesg_lines = dmesg.splitlines()
    logcat_lines = logcat.splitlines()
    all_lines = dmesg_lines + logcat_lines
    wlan0_time = first_dmesg_time(dmesg_lines, WLAN0_RE)
    pcie_mhi_before = count_dmesg_before(dmesg_lines, PCIE_MHI_RE, wlan0_time)
    esoc_failed_before = count_dmesg_before(dmesg_lines, ESOC_BOOT_FAILED_RE, wlan0_time)
    return {
        "base": rel(base),
        "android_dir": rel(base),
        "files_present": {
            "samples": bool(samples),
            "dmesg": bool(dmesg.strip()),
            "props": bool(props),
            "status": bool(status),
            "done": (base / "done").exists(),
            "query_summary": bool(summary_text.strip()),
            "query_files": bool(queries),
        },
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V1909_SAMPLE_BEGIN"),
        "sample_first_uptime": None,
        "sample_last_uptime": None,
        "query_summary": parse_key_values(summary_text),
        "query_count": len(queries),
        "query_success_count": len(successful),
        "query_instances": instance_set,
        "query_names": name_set,
        "query_domain74_seen": 74 in instance_set,
        "query_domain180_seen": 180 in instance_set,
        "query_success_examples": successful[:3],
        "query_last_success": successful[-1] if successful else {},
        "query_first_excerpt": queries[0]["raw_excerpt"] if queries else "",
        "dmesg": {
            "wlfw_lines": count_lines(all_lines, re.compile(r"\bwlfw\b|WLFW", re.IGNORECASE)),
            "bdf_lines": count_lines(all_lines, re.compile(r"BDF file|regdb\.bin|bdwlan\.bin", re.IGNORECASE)),
            "wlan0_lines": count_lines(all_lines, re.compile(r"\bwlan0\b", re.IGNORECASE)),
            "wlan0_time_s": wlan0_time,
            "pcie_mhi_before_wlan0": pcie_mhi_before,
            "esoc_boot_failed_before_wlan0": esoc_failed_before,
            "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        },
        "pm_vote_count": count_lines(logcat_lines, re.compile(r"cnss-daemon voting for modem", re.IGNORECASE)),
        "wlfw_service_request_count": count_lines(all_lines, WLFW_REQUEST_RE),
        "wlan_pd_indication_count": count_lines(dmesg_lines, WLAN_PD_RE),
        "wlanmdsp_count": count_lines(all_lines, WLANMDSP_RE),
        "service74_count": count_lines(dmesg_lines, SERVICE74_RE),
        "service180_count": count_lines(dmesg_lines, SERVICE180_RE),
        "first_service74_line": first_line(dmesg_lines, SERVICE74_RE),
        "first_service180_line": first_line(dmesg_lines, SERVICE180_RE),
        "first_wlan_pd_line": first_line(dmesg_lines, WLAN_PD_RE),
        "first_wlanmdsp_line": first_line(all_lines, WLANMDSP_RE),
        "props_text": props.strip(),
        "matched_window": {"first_lower_time": wlan0_time},
    }


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=repo_path("."), check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001
        return None, "", str(exc), time.monotonic() - started


def step_text(store: EvidenceStore, step: v1521.StepResult) -> str:
    return (store.run_dir / step.file).read_text(encoding="utf-8", errors="replace")


def rollback_selftest_ok(store: EvidenceStore, steps: list[v1521.StepResult]) -> bool:
    for step in reversed(steps):
        if step.name == "post-rollback-native-status-redacted":
            return bool(re.search(r"selftest:\s+pass=\d+\s+warn=\d+\s+fail=0\b", step_text(store, step)))
    return False


def native_v1908_summary(path: Path) -> dict[str, Any]:
    manifest = json.loads(repo_path(path).read_text(encoding="utf-8")) if repo_path(path).exists() else {}
    gate = manifest.get("gate") or {}
    return {
        "manifest": rel(repo_path(path)),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "label": gate.get("servloc_live_label", ""),
        "servloc_result": gate.get("servloc_domain_result", ""),
        "servloc_count": gate.get("servloc_domain_count", ""),
        "servloc_name": gate.get("servloc_domain0_name", ""),
        "servloc_instance": gate.get("servloc_domain0_instance_id", ""),
        "service74_counts": gate.get("raw_service74_text_counts", ""),
        "wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
    }


def classify_result(base_decision: str,
                    base_pass: bool,
                    context: dict[str, Any],
                    native: dict[str, Any],
                    selftest_ok: bool) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return ("v1909-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed")
    if not base_pass:
        return (f"v1909-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed")
    analysis = context.get("analysis") or {}
    files = analysis.get("files_present") or {}
    if not files.get("query_files"):
        return ("v1909-android-servloc-query-missing-rollback-pass", False, "Android capture completed but servloc query files were missing", "android-servloc-query-missing")
    dmesg = analysis.get("dmesg") or {}
    contaminated = bool(dmesg.get("degraded_257s_like")) or int(dmesg.get("pcie_mhi_before_wlan0") or 0) > 0 or int(dmesg.get("esoc_boot_failed_before_wlan0") or 0) > 0
    if contaminated:
        return ("v1909-android-capture-rejected-degraded-or-pcie-mhi", False, "Android capture was degraded or had pre-wlan0 PCIe/MHI/eSoC contamination", "android-capture-rejected-degraded-or-pcie-mhi")
    stateup = (
        int(analysis.get("service74_count") or 0) > 0
        and int(analysis.get("service180_count") or 0) > 0
        and int(analysis.get("wlan_pd_indication_count") or 0) > 0
        and int(analysis.get("wlanmdsp_count") or 0) > 0
        and dmesg.get("wlan0_time_s") is not None
    )
    if not stateup:
        return ("v1909-android-normal-stateup-incomplete-rollback-pass", False, "Android capture did not prove normal service74/180 -> wlan_pd -> wlan0 state-up", "android-normal-stateup-incomplete")
    if int(analysis.get("query_success_count") or 0) == 0:
        return ("v1909-android-servloc-query-no-success-rollback-pass", False, "Android service-locator query ran but no successful response was captured", "android-servloc-query-no-success")
    if not native.get("pass") or native.get("label") != "servloc-domain-list-180-only-service74-missing":
        return ("v1909-native-v1908-baseline-unusable", False, "native V1908 service-locator baseline is missing or not passing", "native-v1908-baseline-unusable")
    if bool(analysis.get("query_domain74_seen")):
        return (
            "v1909-android-servloc-domain74-native-180-only-diff-pass",
            True,
            "Android-good direct service-locator query sees instance 74 while native V1908 direct query returns only instance 180",
            "android-servloc-domain74-native-180-only",
        )
    if bool(analysis.get("query_domain180_seen")):
        return (
            "v1909-android-servloc-180-only-service74-published-elsewhere-pass",
            True,
            "Android-good direct service-locator query also sees only instance 180, yet service-notifier 74 publishes during normal state-up; source inference must move to the kernel/servreg publication path rather than locator response content",
            "android-servloc-180-only-service74-published-elsewhere",
        )
    return ("v1909-android-servloc-domain-result-incomplete", False, "Android servloc query succeeded but neither instance 74 nor 180 was parsed", "android-servloc-domain-result-incomplete")


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    native = manifest.get("native_v1908") or {}
    return "\n".join([
        "# V1909 Android Service-locator Domain-list Handoff",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- label: `{manifest['label']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- evidence: `{rel(Path(manifest['out_dir']))}`",
        "",
        "## Android Direct Query",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["android_dir", analysis.get("android_dir")],
                ["query success/count/instances/names", f"{analysis.get('query_success_count')}/{analysis.get('query_count')}/{json.dumps(analysis.get('query_instances'))}/{json.dumps(analysis.get('query_names'))}"],
                ["domain74/domain180", f"{analysis.get('query_domain74_seen')}/{analysis.get('query_domain180_seen')}"],
                ["service74/service180/wlan_pd/wlanmdsp/wlan0", f"{analysis.get('service74_count')}/{analysis.get('service180_count')}/{analysis.get('wlan_pd_indication_count')}/{analysis.get('wlanmdsp_count')}/{dmesg.get('wlan0_time_s')}"],
                ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
                ["first service74", analysis.get("first_service74_line", "")],
                ["first wlan_pd", analysis.get("first_wlan_pd_line", "")],
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
        (analysis.get("query_last_success") or {}).get("raw_excerpt", analysis.get("query_first_excerpt", "")),
        "```",
        "",
        "## Rollback Gate",
        "",
        f"- native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
        f"- base handoff decision/pass: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
        "",
        "## Safety",
        "",
        "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module runs only a read-only AF_QIPCRTR service-locator get-domain-list query for `wlan/fw` plus log capture. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, or partition write beyond the declared boot-image handoff/rollback.",
        "",
        "## Next",
        "",
        "- Use the selected label to choose the next native action; do not attempt Wi-Fi connect/ping until native init proves WLFW service69 and `wlan0`.",
        "",
    ])


def main() -> int:
    configure_v1521_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1521.execute_plan(args, store, execute=execute)
    native = native_v1908_summary(args.v1908_manifest)
    selftest_ok = rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, context, native, selftest_ok)
    else:
        decision = "v1909-android-servloc-domain-plan-ready" if args.command == "plan" else "v1909-android-servloc-domain-dryrun-ready"
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-servloc-domain-handoff-ready"
    manifest = {
        "cycle": CYCLE,
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "out_dir": rel(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "native_v1908": native,
        "rollback_selftest_fail0": selftest_ok,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "restart_pd_request_executed": False,
        "pmic_gpio_gdsc_regulator_write_executed": False,
        "forced_rc1_case_write_executed": False,
        "subsys_esoc0_open_executed": False,
        "fake_online_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"label:    {manifest['label']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
