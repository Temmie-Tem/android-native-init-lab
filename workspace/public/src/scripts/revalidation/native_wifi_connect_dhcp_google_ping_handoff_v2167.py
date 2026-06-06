#!/usr/bin/env python3
"""V2167 native wlan0 connect, DHCP, and google.com ping handoff."""

from __future__ import annotations

import base64
from contextlib import contextmanager
import datetime as dt
import gzip
import hashlib
import json
import lzma
import os
import re
import shlex
import shutil
import tarfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import a90_ncm_transport as ncm_transport
import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as base
import native_property_runtime_overlay_v471 as propbase
import native_property_runtime_overlay_v535 as prop535
from a90harness.evidence import safe_artifact_label, wifi_artifact_dir, workspace_private_input_path


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def load_local_env_file(path: Path) -> dict[str, Any]:
    allowed_keys = {
        "A90_WIFI_SSID",
        "A90_WIFI_PSK",
        "A90_WIFI_RUN_LABEL",
        "A90_WIFI_QA_HOLD_SEC",
        "A90_WIFI_QA_HOLD_INTERVAL_SEC",
        "A90_WIFI_QA_RECONNECT_ON_DROP",
        "A90_WIFI_FORCE_POWER_ON",
        "A90_WIFI_CONNECT_HOLD_SUBSYS_MODEM",
        "A90_FAST_TRANSFER",
        "A90_FAST_TRANSFER_NM_PROFILE",
        "A90_WIFI_TEST_BOOT_IMAGE",
        "A90_WIFI_TEST_EXPECT_VERSION",
        "A90_WIFI_ROLLBACK_IMAGE",
        "A90_WIFI_ROLLBACK_EXPECT_VERSION",
        "A90_WIFI_HELPER_WAIT_SEC",
        "A90_WIFI_BOOT_PROPERTY_REMOTE_BASE",
        "A90_WIFI_TEST_LOG_PATH",
        "A90_WIFI_TEST_SUMMARY_PATH",
        "A90_WIFI_TEST_HELPER_RESULT_PATH",
        "A90_STANDALONE_WPA",
        "A90_STANDALONE_WPA_SUITE",
        "A90_STANDALONE_WPA_BASE_URL",
    }
    loaded_keys: list[str] = []
    if not path.exists():
        return {"path": str(path), "present": False, "loaded_keys": loaded_keys}
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise ValueError(f"{path} must not be group/world readable; run: chmod 600 {path}")
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            parts = shlex.split(line, comments=True, posix=True)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: invalid env syntax") from exc
        if len(parts) == 2 and parts[0] == "export":
            assignment = parts[1]
        elif len(parts) == 1:
            assignment = parts[0]
        else:
            raise ValueError(f"{path}:{line_no}: expected KEY=value or export KEY=value")
        if "=" not in assignment:
            raise ValueError(f"{path}:{line_no}: missing '='")
        key, value = assignment.split("=", 1)
        if key not in allowed_keys:
            raise ValueError(f"{path}:{line_no}: unsupported key {key}")
        if key not in os.environ:
            os.environ[key] = value
            loaded_keys.append(key)
    return {"path": str(path), "present": True, "loaded_keys": loaded_keys}


WORKSPACE_ENV_FILE = REPO_ROOT / "workspace" / "private" / "secrets" / "a90-wifi-test.env"
LEGACY_LOCAL_ENV_FILE = REPO_ROOT / "tmp" / "wifi" / ".wifi-test.env"
ENV_FILE_OVERRIDE = os.environ.get("A90_WIFI_ENV_FILE", "").strip()
LOCAL_ENV_FILES = (
    [Path(ENV_FILE_OVERRIDE).expanduser()]
    if ENV_FILE_OVERRIDE
    else [WORKSPACE_ENV_FILE, LEGACY_LOCAL_ENV_FILE]
)
LOCAL_ENV_LOAD = [load_local_env_file(path) for path in LOCAL_ENV_FILES]
CYCLE = "V2167"
RAW_RUN_LABEL = os.environ.get("A90_WIFI_RUN_LABEL", "").strip().lower()
RUN_LABEL = safe_artifact_label(RAW_RUN_LABEL, max_len=48)
RUN_SUFFIX = "" if RUN_LABEL == "default" else f"-{RUN_LABEL}"
REPORT_SUFFIX = "" if RUN_LABEL == "default" else f"_{RUN_LABEL.upper().replace('-', '_').replace('.', '_')}"
OUT_DIR = wifi_artifact_dir("runs", f"v2167-connect-dhcp-google-ping-handoff{RUN_SUFFIX}")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / f"NATIVE_INIT_V2167_CONNECT_DHCP_GOOGLE_PING_HANDOFF{REPORT_SUFFIX}_2026-06-05.md"
)
HELPER_BUILD_DIR = OUT_DIR / "host-build"
HELPER_LOCAL = HELPER_BUILD_DIR / "a90_android_execns_probe_v2167"
HELPER_REMOTE = "/cache/bin/a90_android_execns_probe_v2167"
HELPER_REMOTE_B64 = "/cache/a90-execns-v2167.gz.b64"
HELPER_REMOTE_GZ = "/cache/a90-execns-v2167.gz"
STRACE_LOCAL = workspace_private_input_path("external_tools", "userland", "bin", "strace-aarch64-static")
STRACE_REMOTE = "/cache/a90-wifi/a90_strace_v2167"
CONNECT_DIR = "/cache/a90-wifi"
CONNECT_CONFIG = f"{CONNECT_DIR}/v2167.conf"
CONNECT_CONFIG_B64 = f"{CONNECT_CONFIG}.b64"
CONNECT_SCRIPT = "/cache/a90-v2167-connect-ping.sh"
CONNECT_RESULT = "/cache/a90-v2167-connect-ping.result"
STANDALONE_WPA_ENABLED = os.environ.get("A90_STANDALONE_WPA", "1").lower() not in {"0", "false", "no"}
STANDALONE_WPA_SUITE = os.environ.get("A90_STANDALONE_WPA_SUITE", "resolute")
STANDALONE_WPA_BASE_URL = os.environ.get("A90_STANDALONE_WPA_BASE_URL", "https://archive.ubuntu.com/ubuntu")
STANDALONE_WPA_CACHE_DIR = workspace_private_input_path(
    "external_tools", "userland", "downloads", "ubuntu-arm64-wpa", legacy_fallback=False
)
STANDALONE_WPA_BUILD_DIR = HELPER_BUILD_DIR / "wpa-standalone"
STANDALONE_WPA_ARCHIVE = HELPER_BUILD_DIR / "wpa-standalone-v2167.tgz"
STANDALONE_WPA_REMOTE_TGZ = f"{CONNECT_DIR}/wpa-standalone-v2167.tgz"
STANDALONE_WPA_REMOTE_DIR = f"{CONNECT_DIR}/wpa-standalone"
STANDALONE_WPA_REMOTE_WRAPPER = f"{STANDALONE_WPA_REMOTE_DIR}/wpa_supplicant-a90.sh"
PROPERTY_LAYOUT_DIR = OUT_DIR / "layout"
PROPERTY_ROOT = PROPERTY_LAYOUT_DIR / "dev" / "__properties__"
PROPERTY_REMOTE_BASE = "/cache/a90-wifi-property-v2167"
PROPERTY_REMOTE_ROOT = f"{PROPERTY_REMOTE_BASE}/dev/__properties__"
BOOT_PROPERTY_REMOTE_BASE = os.environ.get(
    "A90_WIFI_BOOT_PROPERTY_REMOTE_BASE",
    "/mnt/sdext/a90/private-property-v317/v726",
)
BOOT_PROPERTY_REMOTE_ROOT = f"{BOOT_PROPERTY_REMOTE_BASE}/dev/__properties__"
PROPERTY_REMOTE_TGZ = "/cache/a90-property-v2167.tgz"
PROPERTY_REMOTE_B64 = f"{PROPERTY_REMOTE_TGZ}.b64"
PING_TARGET = "google.com"
DEFAULT_BASELINE_BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v726_wifi_lifecycle.img"
)
DEFAULT_BASELINE_EXPECT_VERSION = "A90 Linux init 0.9.246 (v726-wifi-lifecycle)"
DEFAULT_TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v726.log"
DEFAULT_TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v726.summary"
DEFAULT_TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v726-helper.result"
TEST_BOOT_IMAGE = Path(os.environ.get("A90_WIFI_TEST_BOOT_IMAGE", str(DEFAULT_BASELINE_BOOT_IMAGE))).expanduser()
TEST_EXPECT_VERSION = os.environ.get("A90_WIFI_TEST_EXPECT_VERSION", DEFAULT_BASELINE_EXPECT_VERSION)
ROLLBACK_BOOT_IMAGE = Path(os.environ.get("A90_WIFI_ROLLBACK_IMAGE", str(DEFAULT_BASELINE_BOOT_IMAGE))).expanduser()
ROLLBACK_EXPECT_VERSION = os.environ.get("A90_WIFI_ROLLBACK_EXPECT_VERSION", DEFAULT_BASELINE_EXPECT_VERSION)
TEST_LOG_PATH = os.environ.get("A90_WIFI_TEST_LOG_PATH", DEFAULT_TEST_LOG_PATH)
TEST_SUMMARY_PATH = os.environ.get("A90_WIFI_TEST_SUMMARY_PATH", DEFAULT_TEST_SUMMARY_PATH)
TEST_HELPER_RESULT_PATH = os.environ.get("A90_WIFI_TEST_HELPER_RESULT_PATH", DEFAULT_TEST_HELPER_RESULT_PATH)
base.TEST_LOG_PATH = TEST_LOG_PATH
base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
base.TEST_EVIDENCE_LABEL = os.environ.get("A90_WIFI_TEST_EVIDENCE_LABEL", "v726")
QA_HOLD_SEC = env_int("A90_WIFI_QA_HOLD_SEC", 0, 0, 900)
QA_HOLD_INTERVAL_SEC = env_int("A90_WIFI_QA_HOLD_INTERVAL_SEC", 20, 1, 120)
QA_RECONNECT_ON_DROP = os.environ.get("A90_WIFI_QA_RECONNECT_ON_DROP", "1").lower() not in {"0", "false", "no"}
FORCE_POWER_ON = os.environ.get("A90_WIFI_FORCE_POWER_ON", "0").lower() not in {"0", "false", "no"}
CONNECT_HOLD_SUBSYS_MODEM = os.environ.get("A90_WIFI_CONNECT_HOLD_SUBSYS_MODEM", "1").lower() not in {"0", "false", "no"}
HELPER_WAIT_SEC = env_int("A90_WIFI_HELPER_WAIT_SEC", 280 + QA_HOLD_SEC, 0, 1200)
CHUNK_SIZE = 1536
FAST_TRANSFER_ENABLED = os.environ.get("A90_FAST_TRANSFER", "1").lower() not in {"0", "false", "no"}
FAST_TRANSFER_IFNAME = "ncm0"
FAST_TRANSFER_DEVICE_IP = "192.168.7.2"
FAST_TRANSFER_NETMASK = "255.255.255.0"
FAST_TRANSFER_NM_PROFILE = os.environ.get("A90_FAST_TRANSFER_NM_PROFILE", "a90-v725-ncm-bench")
A90_USB_VENDOR_ID = "04e8"
A90_USB_PRODUCT_ID = "6861"
A90_USB_NCM_DRIVER = "cdc_ncm"
RAW_SECRET_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")
SUPPLICANT_PROPERTY_KEYS = (
    "debug.ld.app.wpa_supplicant",
    "arm64.memtag.process.wpa_supplicant",
    "persist.log.tag.wpa_supplicant",
    "log.tag.wpa_supplicant",
)


class PhaseTimer:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    @contextmanager
    def phase(self, name: str):
        started_iso = base.now_iso()
        started = time.monotonic()
        detail = ""
        ok = False
        try:
            yield
            ok = True
        except Exception as exc:
            detail = type(exc).__name__
            raise
        finally:
            self.records.append({
                "name": name,
                "started": started_iso,
                "ended": base.now_iso(),
                "elapsed_sec": round(time.monotonic() - started, 3),
                "ok": ok,
                "detail": detail,
            })


def parse_iso(value: object) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def step_elapsed_sec(step: dict[str, Any]) -> float:
    started = parse_iso(step.get("started"))
    ended = parse_iso(step.get("ended"))
    if started is None or ended is None:
        return 0.0
    elapsed = (ended - started).total_seconds()
    return elapsed if elapsed > 0 else 0.0


def step_phase_name(step_name: str) -> str:
    if step_name == "test-flash-from-native":
        return "flash_total"
    if step_name in {"pre-status", "pre-selftest", "set-sibling-fwssctl-flag"}:
        return "preflight_device"
    if step_name.startswith("property-runtime") or step_name.startswith("execns-helper") or step_name == "host-build-execns-helper":
        return "helper_stage"
    if step_name.startswith("connect-config"):
        return "connect_config_stage"
    if step_name.startswith("connect-script") or step_name == "connect-result-wait-polls":
        return "connect_window"
    if step_name.startswith("test-fast-evidence") or step_name.startswith("fast-upload-v2167"):
        return "artifact_upload"
    if step_name.startswith("post-rollback-connect-ping-result"):
        return "artifact_upload"
    if step_name.startswith("test-dmesg") or step_name.startswith("test-v2137") or step_name.startswith("test-v2168") or step_name.startswith("test-icnss"):
        return "artifact_upload"
    if step_name.startswith("test-wlan0") or step_name.startswith("test-sys-wifi"):
        return "artifact_upload"
    if step_name.startswith("rollback-from"):
        return "rollback_flash_total"
    if step_name == "rollback-status":
        return "rollback_status"
    if step_name in {"rollback-selftest", "test-selftest"}:
        return "selftest"
    return "other"


def summarize_step_phases(steps: list[dict[str, Any]]) -> dict[str, Any]:
    phases: dict[str, dict[str, Any]] = {}
    for step in steps:
        elapsed = step_elapsed_sec(step)
        phase = step_phase_name(str(step.get("name") or ""))
        bucket = phases.setdefault(phase, {"elapsed_sec": 0.0, "step_count": 0, "slow_steps": []})
        bucket["elapsed_sec"] += elapsed
        bucket["step_count"] += 1
        if elapsed > 0:
            bucket["slow_steps"].append({
                "name": step.get("name", ""),
                "elapsed_sec": round(elapsed, 3),
                "ok": bool(step.get("ok")),
                "timeout": bool(step.get("timeout")),
            })
    for bucket in phases.values():
        bucket["elapsed_sec"] = round(float(bucket["elapsed_sec"]), 3)
        bucket["slow_steps"] = sorted(
            bucket["slow_steps"],
            key=lambda item: float(item.get("elapsed_sec") or 0.0),
            reverse=True,
        )[:8]
    return phases


NATIVE_FLASH_PHASE_RE = re.compile(
    r"phase\.native_init_flash\.([A-Za-z0-9_.-]+)\.elapsed_sec=([0-9.]+)\s+ok=([01])"
)


def extract_native_flash_phase_timers(store: base.EvidenceStore,
                                      steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for step in steps:
        step_name = str(step.get("name") or "")
        if not (step_name == "test-flash-from-native" or step_name.startswith("rollback-from")):
            continue
        stderr_file = step.get("stderr_file")
        if not stderr_file:
            continue
        text = read_text(store.run_dir / str(stderr_file))
        for match in NATIVE_FLASH_PHASE_RE.finditer(text):
            records.append({
                "step": step_name,
                "name": match.group(1),
                "elapsed_sec": float(match.group(2)),
                "ok": match.group(3) == "1",
            })
    return records


def slow_steps(steps: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    rows = [
        {
            "name": step.get("name", ""),
            "elapsed_sec": round(step_elapsed_sec(step), 3),
            "ok": bool(step.get("ok")),
            "timeout": bool(step.get("timeout")),
        }
        for step in steps
    ]
    return [
        row for row in sorted(rows, key=lambda item: float(item["elapsed_sec"]), reverse=True)
        if float(row["elapsed_sec"]) > 0
    ][:limit]


def render_slow_step_refs(rows: list[dict[str, Any]]) -> str:
    return ", ".join(
        f"{row.get('name')}:{row.get('elapsed_sec')}s"
        for row in rows[:3]
    )


def attach_timing_manifest(store: base.EvidenceStore,
                           manifest: dict[str, Any],
                           phase_timer: PhaseTimer | None) -> None:
    steps = manifest.get("steps") if isinstance(manifest.get("steps"), list) else []
    manifest["phase_timers"] = list(phase_timer.records) if phase_timer is not None else []
    manifest["step_phase_summary"] = summarize_step_phases(steps)
    manifest["native_init_flash_phase_timers"] = extract_native_flash_phase_timers(store, steps)
    manifest["slow_steps"] = slow_steps(steps)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def protocol_payload(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("A90P1 BEGIN ") or line.startswith("A90P1 END "):
            continue
        if line == "a90:/#" or line.startswith("a90:/#"):
            continue
        if line.startswith("run: ") or line.startswith("[exit ") or line.startswith("[done]") or line.startswith("[err]"):
            continue
        if line.startswith("linker: ") or line.startswith("WARNING: linker:"):
            continue
        lines.append(line)
    return "\n".join(lines)


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in protocol_payload(text).splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def has_v2167_result(text: str) -> bool:
    return parse_fields(text).get("v2167.begin") == "1"


def intish(value: object) -> int:
    return base.intish(value)


def field_or_embedded_sample(fields: dict[str, str], key: str, default: str = "") -> str:
    value = fields.get(key)
    if value is not None:
        return value
    prefixes = (
        "wifi_connect_ping.supplicant_stdio.sample_",
        "wifi_connect_ping.supplicant_stdio.tail_sample_",
        "wifi_connect_ping.supplicant_stdio.nonproperty_sample_",
    )
    marker = f"{key}="
    for sample_key, sample_value in fields.items():
        if not sample_key.startswith(prefixes):
            continue
        if sample_value.startswith(marker):
            return sample_value.split("=", 1)[1]
    return default


def collect_hold_sample_details(fields: dict[str, str]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for index in range(16):
        prefix = f"wifi_connect_ping.hold.sample_{index:02d}"
        if f"{prefix}.carrier" not in fields:
            continue
        details.append({
            "index": index,
            "elapsed_ms": intish(fields.get(f"{prefix}.elapsed_ms")),
            "carrier": fields.get(f"{prefix}.carrier") == "1",
            "route_default": fields.get(f"{prefix}.route_default_present") == "1",
            "route_gateway": fields.get(f"{prefix}.route_gateway_present") == "1",
            "route_flags_up": fields.get(f"{prefix}.route_flags_up") == "1",
            "route_flags_gateway": fields.get(f"{prefix}.route_flags_gateway") == "1",
            "route_errno": intish(fields.get(f"{prefix}.route_errno")),
            "arp_before_present": fields.get(f"{prefix}.arp_before_present") == "1",
            "arp_before_complete": fields.get(f"{prefix}.arp_before_complete") == "1",
            "arp_before_errno": intish(fields.get(f"{prefix}.arp_before_errno")),
            "arp_after_present": fields.get(f"{prefix}.arp_after_present") == "1",
            "arp_after_complete": fields.get(f"{prefix}.arp_after_complete") == "1",
            "arp_after_errno": intish(fields.get(f"{prefix}.arp_after_errno")),
            "stats_before_ok": fields.get(f"{prefix}.stats_before_ok") == "1",
            "stats_after_ok": fields.get(f"{prefix}.stats_after_ok") == "1",
            "rx_packets_delta": intish(fields.get(f"{prefix}.rx_packets_delta")),
            "tx_packets_delta": intish(fields.get(f"{prefix}.tx_packets_delta")),
            "rx_errors_delta": intish(fields.get(f"{prefix}.rx_errors_delta")),
            "tx_errors_delta": intish(fields.get(f"{prefix}.tx_errors_delta")),
            "rx_dropped_delta": intish(fields.get(f"{prefix}.rx_dropped_delta")),
            "tx_dropped_delta": intish(fields.get(f"{prefix}.tx_dropped_delta")),
            "gateway_ping_available": fields.get(f"{prefix}.gateway_ping_available") == "1",
            "gateway_ping_ok": fields.get(f"{prefix}.gateway_ping_ok") == "1",
            "gateway_ping_classifier": fields.get(f"{prefix}.gateway_ping_classifier", ""),
            "ip_ping_ok": fields.get(f"{prefix}.ip_ping_ok") == "1",
            "ip_ping_classifier": fields.get(f"{prefix}.ip_ping_classifier", ""),
            "host_ping_ok": fields.get(f"{prefix}.host_ping_ok") == "1",
            "host_ping_classifier": fields.get(f"{prefix}.host_ping_classifier", ""),
            "wpa_status_rc": intish(fields.get(f"{prefix}.wpa_status_rc")),
            "wpa_state": fields.get(f"{prefix}.wpa_state", ""),
            "wpa_freq_mhz": intish(fields.get(f"{prefix}.wpa_freq_mhz")),
            "wpa_ip_present": fields.get(f"{prefix}.wpa_ip_present") == "1",
            "wpa_bssid_present": fields.get(f"{prefix}.wpa_bssid_present") == "1",
            "signal_poll_rc": intish(fields.get(f"{prefix}.signal_poll_rc")),
            "signal_rssi_dbm": intish(fields.get(f"{prefix}.signal_rssi_dbm")),
            "signal_linkspeed_mbps": intish(fields.get(f"{prefix}.signal_linkspeed_mbps")),
            "signal_frequency_mhz": intish(fields.get(f"{prefix}.signal_frequency_mhz")),
            "power_class": fields.get(f"{prefix}.power_class", ""),
            "power_device": fields.get(f"{prefix}.power_device", ""),
            "driver_power_state": fields.get(f"{prefix}.driver_power_state", ""),
            "cnss_daemon_count": intish(fields.get(f"{prefix}.owner.cnss_daemon_count")),
            "pm_service_count": intish(fields.get(f"{prefix}.owner.pm_service_count")),
            "per_mgr_count": intish(fields.get(f"{prefix}.owner.per_mgr_count")),
            "wifi_hal_count": intish(fields.get(f"{prefix}.owner.wifi_hal_count")),
            "supplicant_count": intish(fields.get(f"{prefix}.owner.supplicant_count")),
            "ipacm_count": intish(fields.get(f"{prefix}.owner.ipacm_count")),
            "fd_dev_ipa_count": intish(fields.get(f"{prefix}.owner.fd_dev_ipa_count")),
            "fd_subsys_modem_count": intish(fields.get(f"{prefix}.owner.fd_subsys_modem_count")),
            "dev_ipa_exists": fields.get(f"{prefix}.owner.dev_ipa_exists") == "1",
            "icnss_runtime_status": fields.get(f"{prefix}.icnss.runtime_status", ""),
            "wlan0_device_runtime_status": fields.get(f"{prefix}.icnss.wlan0_device_runtime_status", ""),
            "wlan_pd_seen": fields.get(f"{prefix}.subsys.wlan_seen") == "1",
            "wlan_pd_name": fields.get(f"{prefix}.subsys.wlan_name", ""),
            "wlan_pd_state": fields.get(f"{prefix}.subsys.wlan_state", ""),
            "wlan_pd_crash_count": fields.get(f"{prefix}.subsys.wlan_crash_count", ""),
            "modem_seen": fields.get(f"{prefix}.subsys.modem_seen") == "1",
            "modem_state": fields.get(f"{prefix}.subsys.modem_state", ""),
        })
    return details


def run_step(store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             *,
             timeout: float = 60.0,
             bridge_timeout: float = 45.0) -> dict[str, Any]:
    return base.a90ctl_step(
        store,
        steps,
        name,
        command,
        timeout=timeout,
        bridge_timeout=bridge_timeout,
    )


def append_compact_step(store: base.EvidenceStore,
                        steps: list[dict[str, Any]],
                        name: str,
                        *,
                        command: list[str],
                        ok: bool,
                        rc: int,
                        stdout: str,
                        stderr: str = "") -> None:
    result = {
        "command": command,
        "started": base.now_iso(),
        "ended": base.now_iso(),
        "timeout": False,
        "rc": rc,
        "ok": ok,
        "stdout": stdout,
        "stderr": stderr,
    }
    base.write_step(store, steps, name, result)


class FastTransferSession(ncm_transport.FastTransferSession):
    def __init__(self, store: base.EvidenceStore, steps: list[dict[str, Any]]) -> None:
        super().__init__(
            store,
            steps,
            run_step=run_step,
            enabled=FAST_TRANSFER_ENABLED,
            device_ifname=FAST_TRANSFER_IFNAME,
            device_ip=FAST_TRANSFER_DEVICE_IP,
            device_netmask=FAST_TRANSFER_NETMASK,
            nm_profile=FAST_TRANSFER_NM_PROFILE,
        )


def secret_byte_patterns() -> dict[str, bytes]:
    patterns: dict[str, bytes] = {}
    for key, value in secret_values().items():
        if value:
            patterns[key] = value.encode("utf-8")
    return patterns


def validate_uploaded_archive(archive_path: Path) -> dict[str, Any]:
    return ncm_transport.validate_uploaded_archive(
        archive_path,
        secret_patterns=secret_byte_patterns(),
        forbidden_patterns=(
            "v2167.conf",
            "connect_config",
            "connect-config",
            "sockets",
            ".b64",
            "wpa_supplicant.conf",
            "env",
        ),
    )


TcpArchiveReceiver = ncm_transport.TcpArchiveReceiver


class FastUploadSession:
    def __init__(self, transfer: FastTransferSession) -> None:
        self.transfer = transfer

    def upload_v2167_logs(self) -> dict[str, Any]:
        started = time.monotonic()
        if not self.transfer.ensure_device_reachable():
            result = {
                "ok": False,
                "reason": self.transfer.reason,
                "method": "ncm-targzip-nc",
                "elapsed_sec": 0.0,
                "archive": {},
                "validation": {},
            }
            append_compact_step(
                self.transfer.store,
                self.transfer.steps,
                "fast-upload-v2167-skipped",
                command=["fast-upload", "v2167-logs"],
                ok=False,
                rc=1,
                stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
            )
            return result

        archive_path = OUT_DIR / f"fast-upload-v2167-{int(time.time())}.tgz"
        with TcpArchiveReceiver(archive_path, timeout=60.0) as receiver:
            remote_host = shlex.quote(self.transfer.host_link_local + "%" + FAST_TRANSFER_IFNAME)
            script = "\n".join([
                "bb=/cache/bin/busybox",
                "tmp=/cache/a90-fastupload-v2167-$$",
                "payload=$tmp/a90-v2167-evidence",
                "$bb rm -rf \"$tmp\"",
                "$bb mkdir -p \"$payload\"",
                "copy_if() { src=\"$1\"; dst=\"$2\"; [ -f \"$src\" ] && $bb cp \"$src\" \"$payload/$dst\"; }",
                f"copy_if {shlex.quote(CONNECT_RESULT)} connect-result.txt",
                "copy_if /cache/native-init.log native-init.log",
                "copy_if /cache/native-init-netservice.log native-init-netservice.log",
                "copy_if /cache/usbnet.log usbnet.log",
                "i=0; for src in /cache/a90-wifi/a90_supplicant_strace*; do [ -f \"$src\" ] || continue; $bb cp \"$src\" \"$payload/strace-$i.txt\"; i=$((i+1)); done",
                "if [ -x /cache/bin/a90_netservice ]; then /cache/bin/a90_netservice status > \"$payload/netservice-status.txt\" 2>&1; fi",
                "if [ -f /sys/kernel/debug/icnss/stats ]; then $bb cat /sys/kernel/debug/icnss/stats > \"$payload/icnss-stats.txt\" 2>&1; fi",
                "if [ -d /sys/class/net/wlan0 ]; then $bb cat /sys/class/net/wlan0/operstate > \"$payload/wlan0-operstate.txt\" 2>&1; fi",
                "(cd \"$tmp\" && $bb tar -cf - a90-v2167-evidence) | $bb gzip -c | $bb timeout 5 $bb nc -w 1 "
                f"{remote_host} {receiver.port}",
                "rc=$?",
                "$bb rm -rf \"$tmp\"",
                "echo fast_upload.nc_rc=$rc",
                "exit \"$rc\"",
            ])
            step = run_step(
                self.transfer.store,
                self.transfer.steps,
                "fast-upload-v2167-device-stream",
                ["run", "/cache/bin/busybox", "sh", "-c", script],
                timeout=90,
                bridge_timeout=65,
            )
        upload_output = "\n".join([str(step.get("stdout") or ""), str(step.get("stderr") or "")])
        fields = base.parse_key_values(upload_output)
        validation = validate_uploaded_archive(archive_path)
        device_nc_rc = fields.get("fast_upload.nc_rc", "")
        device_stream_ok = bool(step.get("ok")) and device_nc_rc in {"", "0"}
        ok = (
            device_stream_ok
            and bool(receiver.result.get("ok"))
            and bool(validation.get("ok"))
        )
        result = {
            "ok": ok,
            "reason": "ok" if ok else "upload-or-validation-failed",
            "method": "ncm-targzip-nc",
            "elapsed_sec": round(time.monotonic() - started, 3),
            "device_nc_rc": device_nc_rc,
            "archive_path": base.rel(archive_path) if archive_path.exists() else "",
            "receiver": receiver.result,
            "validation": {
                key: value
                for key, value in validation.items()
                if key != "connect_result_text"
            },
            "host_ifname": self.transfer.ifname,
            "host_link_local": self.transfer.host_link_local,
        }
        append_compact_step(
            self.transfer.store,
            self.transfer.steps,
            "fast-upload-v2167-result",
            command=["fast-upload-result", "v2167-logs"],
            ok=ok,
            rc=0 if ok else 1,
            stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
        )
        result["connect_result_text"] = str(validation.get("connect_result_text") or "")
        return result


def secret_values() -> dict[str, str]:
    return {key: os.environ.get(key, "") for key in RAW_SECRET_KEYS}


def build_wpa_config() -> tuple[bytes, dict[str, Any]]:
    values = secret_values()
    ssid = values["A90_WIFI_SSID"]
    psk = values["A90_WIFI_PSK"]
    if not ssid or not psk:
        raise ValueError("A90_WIFI_SSID and A90_WIFI_PSK are required")
    if len(ssid.encode("utf-8")) > 32:
        raise ValueError("SSID is longer than 32 bytes")
    if len(psk) < 8 or len(psk) > 63:
        raise ValueError("WPA PSK passphrase must be 8..63 characters")
    ssid_hex = ssid.encode("utf-8").hex()
    psk_hex = hashlib.pbkdf2_hmac(
        "sha1",
        psk.encode("utf-8"),
        ssid.encode("utf-8"),
        4096,
        32,
    ).hex()
    text = "\n".join([
        "ctrl_interface=DIR=/cache/a90-wifi/sockets",
        "update_config=0",
        "ap_scan=1",
        "network={",
        f"    ssid={ssid_hex}",
        "    disabled=0",
        "    scan_ssid=1",
        "    key_mgmt=WPA-PSK",
        f"    psk={psk_hex}",
        "}",
        "",
    ])
    return text.encode("ascii"), {
        "ssid_present": True,
        "psk_present": True,
        "ssid_len": len(ssid.encode("utf-8")),
        "config_len": len(text.encode("ascii")),
        "security_mode": "wpa-psk",
        "raw_values_logged": False,
        "network_initially_disabled": False,
    }


def build_helper(store: base.EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    HELPER_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        "workspace/public/archive/scripts/revalidation/build_android_execns_probe_helper.sh",
        str(HELPER_LOCAL),
    ]
    result = base.run_command(command, timeout=180)
    base.write_step(store, steps, "host-build-execns-helper", result)
    if not result["ok"]:
        return {"ok": False, "sha256": "", "gzip_len": 0, "chunks": 0}
    helper_sha = base.sha256(HELPER_LOCAL)
    gzip_bytes = gzip.compress(HELPER_LOCAL.read_bytes(), compresslevel=9)
    (HELPER_BUILD_DIR / "a90_android_execns_probe_v2167.gz").write_bytes(gzip_bytes)
    return {
        "ok": True,
        "sha256": helper_sha,
        "gzip_len": len(gzip_bytes),
        "gzip_sha256": hashlib.sha256(gzip_bytes).hexdigest(),
        "chunks": (len(base64.b64encode(gzip_bytes)) + CHUNK_SIZE - 1) // CHUNK_SIZE,
    }


def stage_helper_binary(store: base.EvidenceStore,
                        steps: list[dict[str, Any]],
                        helper_build: dict[str, Any],
                        fast_transfer: FastTransferSession | None = None) -> dict[str, str]:
    fields: dict[str, str] = {
        "helper_stage.begin": "1",
        "helper_stage.remote": HELPER_REMOTE,
        "helper_stage.local_sha256": str(helper_build.get("sha256") or ""),
        "helper_stage.gzip_len": str(helper_build.get("gzip_len") or "0"),
    }
    if not helper_build.get("ok"):
        fields["helper_stage.ok"] = "0"
        fields["helper_stage.reason"] = "host-build-failed"
        return fields
    verify = run_step(
        store,
        steps,
        "execns-helper-verify-existing",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"test -x {HELPER_REMOTE}; echo helper_existing.executable_rc=$?; "
            f"printf 'helper_existing.remote_sha256='; /cache/bin/busybox sha256sum {HELPER_REMOTE} 2>/dev/null | /cache/bin/busybox awk '{{print $1}}'",
        ],
        timeout=30,
        bridge_timeout=15,
    )
    existing = base.parse_key_values("\n".join([str(verify.get("stdout") or ""), str(verify.get("stderr") or "")]))
    if existing.get("helper_existing.executable_rc") == "0" and existing.get("helper_existing.remote_sha256") == fields["helper_stage.local_sha256"]:
        fields["helper_stage.ok"] = "1"
        fields["helper_stage.reason"] = "already-present"
        fields["helper_stage.remote_sha256"] = fields["helper_stage.local_sha256"]
        return fields
    run_step(
        store,
        steps,
        "execns-helper-stage-clean",
        ["run", "/cache/bin/busybox", "rm", "-f", HELPER_REMOTE, HELPER_REMOTE_B64, HELPER_REMOTE_GZ],
    )
    gzip_bytes = gzip.compress(HELPER_LOCAL.read_bytes(), compresslevel=9)
    gzip_path = HELPER_BUILD_DIR / "a90_android_execns_probe_v2167.gz"
    gzip_path.write_bytes(gzip_bytes)
    gzip_sha = hashlib.sha256(gzip_bytes).hexdigest()
    fields["helper_stage.transfer_method"] = "serial-base64"
    if fast_transfer is not None:
        transfer = fast_transfer.transfer_file(
            label="execns-helper",
            local_path=gzip_path,
            remote_path=HELPER_REMOTE_GZ,
            expected_sha256=gzip_sha,
            mode="600",
        )
        fields["helper_stage.fast_transfer_ok"] = "1" if transfer.get("ok") else "0"
        fields["helper_stage.fast_transfer_reason"] = str(transfer.get("reason") or "")
        fields["helper_stage.fast_transfer_elapsed_sec"] = str(transfer.get("elapsed_sec") or "")
        if transfer.get("ok"):
            fields["helper_stage.transfer_method"] = "ncm-wget"
            decode_script = (
                f"set -e; "
                f"/cache/bin/busybox zcat {HELPER_REMOTE_GZ} > {HELPER_REMOTE}; "
                f"/cache/bin/busybox chmod 700 {HELPER_REMOTE}; "
                f"printf 'helper_stage.remote_sha256='; /cache/bin/busybox sha256sum {HELPER_REMOTE} | /cache/bin/busybox awk '{{print $1}}'; "
                f"/cache/bin/busybox rm -f {HELPER_REMOTE_B64} {HELPER_REMOTE_GZ}; "
                f"echo helper_stage.decode_ok=1"
            )
            decode = run_step(
                store,
                steps,
                "execns-helper-stage-decode",
                ["run", "/cache/bin/busybox", "sh", "-c", decode_script],
                timeout=45,
                bridge_timeout=20,
            )
            decode_output = "\n".join([str(decode.get("stdout") or ""), str(decode.get("stderr") or "")])
            fields.update(base.parse_key_values(decode_output))
            if not fields.get("helper_stage.remote_sha256") and fields["helper_stage.local_sha256"] in decode_output:
                fields["helper_stage.remote_sha256"] = fields["helper_stage.local_sha256"]
            fields["helper_stage.ok"] = "1" if fields.get("helper_stage.remote_sha256") == fields["helper_stage.local_sha256"] else "0"
            fields["helper_stage.reason"] = "ok" if fields["helper_stage.ok"] == "1" else "decode-or-sha-mismatch"
            return fields
    run_step(
        store,
        steps,
        "execns-helper-stage-touch",
        ["run", "/cache/bin/busybox", "touch", HELPER_REMOTE_B64],
    )
    encoded = base64.b64encode(gzip_bytes).decode("ascii")
    chunks = [encoded[index:index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
    chunk_log: list[str] = []
    all_ok = True
    for index, chunk in enumerate(chunks):
        shell = f"printf '%s' {shlex.quote(chunk)} >> {HELPER_REMOTE_B64}"
        result = base.run_command(
            base.a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", shell], timeout=45),
            timeout=60,
        )
        ok = bool(result.get("ok"))
        all_ok = all_ok and ok
        chunk_log.append(f"chunk={index} rc={result.get('rc')} ok={ok} timeout={result.get('timeout')}")
        if not ok:
            break
    append_compact_step(
        store,
        steps,
        "execns-helper-stage-b64-chunks",
        command=["stage-base64-gzip", HELPER_REMOTE_B64, f"chunks={len(chunks)}"],
        ok=all_ok,
        rc=0 if all_ok else 1,
        stdout="\n".join(chunk_log) + "\n",
    )
    fields["helper_stage.chunks"] = str(len(chunks))
    fields["helper_stage.chunks_ok"] = "1" if all_ok else "0"
    if not all_ok:
        fields["helper_stage.ok"] = "0"
        fields["helper_stage.reason"] = "chunk-stage-failed"
        return fields
    decode_script = (
        f"set -e; "
        f"/cache/bin/busybox base64 -d {HELPER_REMOTE_B64} > {HELPER_REMOTE_GZ}; "
        f"/cache/bin/busybox zcat {HELPER_REMOTE_GZ} > {HELPER_REMOTE}; "
        f"/cache/bin/busybox chmod 700 {HELPER_REMOTE}; "
        f"printf 'helper_stage.remote_sha256='; /cache/bin/busybox sha256sum {HELPER_REMOTE} | /cache/bin/busybox awk '{{print $1}}'; "
        f"/cache/bin/busybox rm -f {HELPER_REMOTE_B64} {HELPER_REMOTE_GZ}; "
        f"echo helper_stage.decode_ok=1"
    )
    decode = run_step(
        store,
        steps,
        "execns-helper-stage-decode",
        ["run", "/cache/bin/busybox", "sh", "-c", decode_script],
        timeout=120,
        bridge_timeout=90,
    )
    fields.update(base.parse_key_values(str(decode.get("stdout") or "")))
    fields["helper_stage.ok"] = "1" if decode.get("ok") and fields.get("helper_stage.remote_sha256") == fields["helper_stage.local_sha256"] else "0"
    fields["helper_stage.reason"] = "ok" if fields["helper_stage.ok"] == "1" else "decode-or-sha-mismatch"
    return fields


def stage_strace_binary(store: base.EvidenceStore,
                        steps: list[dict[str, Any]],
                        fast_transfer: FastTransferSession | None = None) -> dict[str, str]:
    fields: dict[str, str] = {
        "strace_stage.begin": "1",
        "strace_stage.local": str(STRACE_LOCAL),
        "strace_stage.remote": STRACE_REMOTE,
    }
    if not STRACE_LOCAL.exists():
        fields["strace_stage.ok"] = "0"
        fields["strace_stage.reason"] = "local-strace-missing"
        return fields
    local_sha = base.sha256(STRACE_LOCAL)
    fields["strace_stage.local_sha256"] = local_sha
    prep = run_step(
        store,
        steps,
        "strace-helper-prepare-cache-dir",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            "/cache/bin/busybox mkdir -p /cache/a90-wifi && "
            "/cache/bin/busybox chmod 0770 /cache/a90-wifi && "
            "echo strace_stage.cache_dir_ready=1",
        ],
        timeout=30,
        bridge_timeout=15,
    )
    fields.update(base.parse_key_values(str(prep.get("stdout") or "")))
    if not prep.get("ok") or fields.get("strace_stage.cache_dir_ready") != "1":
        fields["strace_stage.ok"] = "0"
        fields["strace_stage.reason"] = "cache-dir-prepare-failed"
        return fields
    verify = run_step(
        store,
        steps,
        "strace-helper-verify-existing",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"test -x {STRACE_REMOTE}; echo strace_existing.executable_rc=$?; "
            f"printf 'strace_existing.remote_sha256='; /cache/bin/busybox sha256sum {STRACE_REMOTE} 2>/dev/null | /cache/bin/busybox awk '{{print $1}}'",
        ],
        timeout=30,
        bridge_timeout=15,
    )
    existing = base.parse_key_values("\n".join([str(verify.get("stdout") or ""), str(verify.get("stderr") or "")]))
    if existing.get("strace_existing.executable_rc") == "0" and existing.get("strace_existing.remote_sha256") == local_sha:
        fields["strace_stage.ok"] = "1"
        fields["strace_stage.reason"] = "already-present"
        fields["strace_stage.remote_sha256"] = local_sha
        return fields
    if fast_transfer is None:
        fields["strace_stage.ok"] = "0"
        fields["strace_stage.reason"] = "fast-transfer-required"
        return fields
    transfer = fast_transfer.transfer_file(
        label="strace-helper",
        local_path=STRACE_LOCAL,
        remote_path=STRACE_REMOTE,
        expected_sha256=local_sha,
        mode="700",
    )
    fields["strace_stage.fast_transfer_ok"] = "1" if transfer.get("ok") else "0"
    fields["strace_stage.fast_transfer_reason"] = str(transfer.get("reason") or "")
    fields["strace_stage.fast_transfer_elapsed_sec"] = str(transfer.get("elapsed_sec") or "")
    fields["strace_stage.remote_sha256"] = str(transfer.get("remote_sha256") or "")
    fields["strace_stage.ok"] = "1" if transfer.get("ok") else "0"
    fields["strace_stage.reason"] = "ok" if transfer.get("ok") else str(transfer.get("reason") or "transfer-failed")
    return fields


def parse_deb_dependencies(depends: str) -> list[str]:
    names: list[str] = []
    for item in depends.split(","):
        choice = item.split("|", 1)[0].strip()
        match = re.match(r"([A-Za-z0-9+.-]+)", choice)
        if match:
            names.append(match.group(1))
    return names


def parse_packages_index(text: str) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for paragraph in text.split("\n\n"):
        fields: dict[str, str] = {}
        key = ""
        for raw_line in paragraph.splitlines():
            if not raw_line:
                continue
            if raw_line[:1].isspace() and key:
                fields[key] = fields[key] + " " + raw_line.strip()
            elif ":" in raw_line:
                key, value = raw_line.split(":", 1)
                fields[key] = value.strip()
        package = fields.get("Package")
        if package:
            entries[package] = fields
    return entries


def fetch_url_bytes(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "A90-native-init-revalidation/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def load_ubuntu_arm64_package_index() -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    index_dir = STANDALONE_WPA_CACHE_DIR / "indexes" / STANDALONE_WPA_SUITE
    index_dir.mkdir(parents=True, exist_ok=True)
    for component in ("main", "universe"):
        cache_path = index_dir / f"{component}-binary-arm64-Packages.xz"
        if not cache_path.exists() or cache_path.stat().st_size == 0:
            url = f"{STANDALONE_WPA_BASE_URL}/dists/{STANDALONE_WPA_SUITE}/{component}/binary-arm64/Packages.xz"
            cache_path.write_bytes(fetch_url_bytes(url, 60))
        text = lzma.decompress(cache_path.read_bytes()).decode("utf-8", errors="replace")
        merged.update(parse_packages_index(text))
    return merged


def standalone_wpa_runtime_packages(index: dict[str, dict[str, str]]) -> list[str]:
    include_explicit = {"wpasupplicant", "zlib1g", "openssl-provider-legacy", "gcc-16-base", "readline-common"}
    skip = {"adduser", "debconf", "debconf-2.0", "libc-gconv-modules-extra"}
    seen: set[str] = set()
    queue = ["wpasupplicant"]
    while queue:
        package = queue.pop(0)
        if package in seen or package in skip:
            continue
        if package != "wpasupplicant" and not (package.startswith("lib") or package in include_explicit):
            continue
        entry = index.get(package)
        if not entry:
            continue
        seen.add(package)
        for dependency in parse_deb_dependencies(entry.get("Depends", "")):
            if dependency not in seen:
                queue.append(dependency)
    seen.update(package for package in include_explicit if package in index)
    return sorted(seen)


def download_standalone_wpa_debs(index: dict[str, dict[str, str]],
                                 packages: list[str]) -> list[Path]:
    STANDALONE_WPA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    debs: list[Path] = []
    for package in packages:
        entry = index.get(package)
        if not entry:
            raise RuntimeError(f"missing Ubuntu arm64 package index entry: {package}")
        filename = entry.get("Filename", "")
        sha256 = entry.get("SHA256", "")
        if not filename or not sha256:
            raise RuntimeError(f"missing Filename/SHA256 for {package}")
        deb_path = STANDALONE_WPA_CACHE_DIR / Path(filename).name
        if deb_path.exists() and hashlib.sha256(deb_path.read_bytes()).hexdigest() != sha256:
            deb_path.unlink()
        if not deb_path.exists():
            url = f"{STANDALONE_WPA_BASE_URL}/{filename}"
            deb_path.write_bytes(fetch_url_bytes(url, 90))
        actual = hashlib.sha256(deb_path.read_bytes()).hexdigest()
        if actual != sha256:
            raise RuntimeError(f"sha256 mismatch for {package}: {actual} != {sha256}")
        debs.append(deb_path)
    return debs


def prune_standalone_wpa_root(root: Path) -> None:
    for rel in (
        "usr/share/doc",
        "usr/share/man",
        "usr/share/lintian",
        "usr/share/bash-completion",
        "usr/share/dbus-1",
        "usr/share/systemd",
        "lib/systemd",
        "usr/lib/systemd",
        "etc/dbus-1",
        "etc/init.d",
    ):
        target = root / rel
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


def create_standalone_wpa_wrapper(root: Path) -> None:
    wrapper = root / "wpa_supplicant-a90.sh"
    wrapper.write_text(
        "\n".join([
            "#!/cache/bin/busybox sh",
            "root=/cache/a90-wifi/wpa-standalone",
            "loader=$root/lib/ld-linux-aarch64.so.1",
            "[ -x \"$loader\" ] || loader=$root/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1",
            "[ -x \"$loader\" ] || loader=$root/usr/lib/ld-linux-aarch64.so.1",
            "[ -x \"$loader\" ] || loader=$root/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1",
            "libpath=$root/usr/lib/aarch64-linux-gnu:$root/lib/aarch64-linux-gnu:$root/usr/lib:$root/lib",
            "export LD_LIBRARY_PATH=$libpath",
            "export OPENSSL_MODULES=$root/usr/lib/aarch64-linux-gnu/ossl-modules",
            "export PATH=/cache/bin:/system/bin:/vendor/bin",
            "exec \"$loader\" --library-path \"$libpath\" \"$root/usr/sbin/wpa_supplicant\" \"$@\"",
            "",
        ]),
        encoding="utf-8",
    )
    wrapper.chmod(0o700)


def build_standalone_wpa_archive(store: base.EvidenceStore,
                                 steps: list[dict[str, Any]]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "ok": False,
        "enabled": STANDALONE_WPA_ENABLED,
        "archive": base.rel(STANDALONE_WPA_ARCHIVE),
        "remote_wrapper": STANDALONE_WPA_REMOTE_WRAPPER,
        "suite": STANDALONE_WPA_SUITE,
        "base_url": STANDALONE_WPA_BASE_URL,
    }
    if not STANDALONE_WPA_ENABLED:
        fields["reason"] = "disabled"
        return fields
    try:
        index = load_ubuntu_arm64_package_index()
        packages = standalone_wpa_runtime_packages(index)
        debs = download_standalone_wpa_debs(index, packages)
        if STANDALONE_WPA_BUILD_DIR.exists():
            shutil.rmtree(STANDALONE_WPA_BUILD_DIR)
        root = STANDALONE_WPA_BUILD_DIR / "wpa-standalone"
        root.mkdir(parents=True, exist_ok=True)
        for deb in debs:
            result = base.run_command(["dpkg-deb", "-x", str(deb), str(root)], timeout=90)
            if not result.get("ok"):
                base.write_step(store, steps, f"standalone-wpa-extract-{deb.name}", result)
                raise RuntimeError(f"dpkg-deb extract failed: {deb.name}")
        prune_standalone_wpa_root(root)
        create_standalone_wpa_wrapper(root)
        binary = root / "usr" / "sbin" / "wpa_supplicant"
        loader_candidates = [
            root / "lib" / "ld-linux-aarch64.so.1",
            root / "lib" / "aarch64-linux-gnu" / "ld-linux-aarch64.so.1",
            root / "usr" / "lib" / "ld-linux-aarch64.so.1",
            root / "usr" / "lib" / "aarch64-linux-gnu" / "ld-linux-aarch64.so.1",
        ]
        if not binary.exists() or not any(path.exists() for path in loader_candidates):
            raise RuntimeError("standalone wpa_supplicant binary or loader missing after extraction")
        manifest = {
            "packages": packages,
            "package_count": len(packages),
            "suite": STANDALONE_WPA_SUITE,
            "base_url": STANDALONE_WPA_BASE_URL,
            "binary": "usr/sbin/wpa_supplicant",
            "wrapper": "wpa_supplicant-a90.sh",
        }
        (root / "a90-standalone-wpa-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        STANDALONE_WPA_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(STANDALONE_WPA_ARCHIVE, "w:gz") as tar:
            tar.add(root, arcname="wpa-standalone", recursive=True)
        archive_bytes = STANDALONE_WPA_ARCHIVE.read_bytes()
        fields.update({
            "ok": True,
            "reason": "ok",
            "packages": packages,
            "package_count": len(packages),
            "bytes": len(archive_bytes),
            "sha256": hashlib.sha256(archive_bytes).hexdigest(),
        })
    except Exception as exc:
        fields["reason"] = f"{type(exc).__name__}: {exc}"
    append_compact_step(
        store,
        steps,
        "standalone-wpa-host-bundle",
        command=["build-standalone-wpa-bundle"],
        ok=bool(fields.get("ok")),
        rc=0 if fields.get("ok") else 1,
        stdout=json.dumps({
            key: value
            for key, value in fields.items()
            if key not in {"base_url"}
        }, ensure_ascii=False, sort_keys=True) + "\n",
    )
    return fields


def stage_standalone_wpa_bundle(store: base.EvidenceStore,
                                steps: list[dict[str, Any]],
                                archive_info: dict[str, Any],
                                fast_transfer: FastTransferSession | None = None) -> dict[str, str]:
    fields: dict[str, str] = {
        "standalone_wpa_stage.begin": "1",
        "standalone_wpa_stage.enabled": "1" if STANDALONE_WPA_ENABLED else "0",
        "standalone_wpa_stage.remote_dir": STANDALONE_WPA_REMOTE_DIR,
        "standalone_wpa_stage.remote_wrapper": STANDALONE_WPA_REMOTE_WRAPPER,
        "standalone_wpa_stage.local_sha256": str(archive_info.get("sha256") or ""),
        "standalone_wpa_stage.package_count": str(archive_info.get("package_count") or "0"),
        "standalone_wpa_stage.archive_len": str(archive_info.get("bytes") or "0"),
    }
    if not STANDALONE_WPA_ENABLED:
        fields["standalone_wpa_stage.ok"] = "1"
        fields["standalone_wpa_stage.reason"] = "disabled"
        return fields
    if not archive_info.get("ok") or not STANDALONE_WPA_ARCHIVE.exists():
        fields["standalone_wpa_stage.ok"] = "0"
        fields["standalone_wpa_stage.reason"] = str(archive_info.get("reason") or "host-bundle-failed")
        return fields
    prep = run_step(
        store,
        steps,
        "standalone-wpa-prepare-cache-dir",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"/cache/bin/busybox mkdir -p {CONNECT_DIR}; /cache/bin/busybox chmod 0770 {CONNECT_DIR}; echo standalone_wpa_stage.cache_dir_ready=1",
        ],
        timeout=30,
        bridge_timeout=15,
    )
    fields.update(base.parse_key_values(str(prep.get("stdout") or "")))
    if not prep.get("ok"):
        fields["standalone_wpa_stage.ok"] = "0"
        fields["standalone_wpa_stage.reason"] = "cache-dir-prepare-failed"
        return fields
    verify = run_step(
        store,
        steps,
        "standalone-wpa-verify-existing",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"test -x {STANDALONE_WPA_REMOTE_WRAPPER}; echo standalone_wpa_existing.executable_rc=$?; "
            f"printf 'standalone_wpa_existing.bundle_sha256='; /cache/bin/busybox cat {STANDALONE_WPA_REMOTE_DIR}/.a90_bundle_sha256 2>/dev/null",
        ],
        timeout=30,
        bridge_timeout=15,
    )
    existing = base.parse_key_values("\n".join([str(verify.get("stdout") or ""), str(verify.get("stderr") or "")]))
    if (
        existing.get("standalone_wpa_existing.executable_rc") == "0"
        and existing.get("standalone_wpa_existing.bundle_sha256") == fields["standalone_wpa_stage.local_sha256"]
    ):
        fields["standalone_wpa_stage.ok"] = "1"
        fields["standalone_wpa_stage.reason"] = "already-present"
        fields["standalone_wpa_stage.remote_sha256"] = fields["standalone_wpa_stage.local_sha256"]
        return fields
    if fast_transfer is None:
        fields["standalone_wpa_stage.ok"] = "0"
        fields["standalone_wpa_stage.reason"] = "fast-transfer-required"
        return fields
    transfer = fast_transfer.transfer_file(
        label="standalone-wpa",
        local_path=STANDALONE_WPA_ARCHIVE,
        remote_path=STANDALONE_WPA_REMOTE_TGZ,
        expected_sha256=str(archive_info.get("sha256") or ""),
        mode="600",
    )
    fields["standalone_wpa_stage.fast_transfer_ok"] = "1" if transfer.get("ok") else "0"
    fields["standalone_wpa_stage.fast_transfer_reason"] = str(transfer.get("reason") or "")
    fields["standalone_wpa_stage.fast_transfer_elapsed_sec"] = str(transfer.get("elapsed_sec") or "")
    fields["standalone_wpa_stage.remote_sha256"] = str(transfer.get("remote_sha256") or "")
    if not transfer.get("ok"):
        fields["standalone_wpa_stage.ok"] = "0"
        fields["standalone_wpa_stage.reason"] = str(transfer.get("reason") or "transfer-failed")
        return fields
    extract_script = (
        f"set -e; "
        f"/cache/bin/busybox rm -rf {STANDALONE_WPA_REMOTE_DIR}; "
        f"/cache/bin/busybox tar -xzf {STANDALONE_WPA_REMOTE_TGZ} -C {CONNECT_DIR}; "
        f"/cache/bin/busybox chmod 700 {STANDALONE_WPA_REMOTE_WRAPPER}; "
        f"/cache/bin/busybox chmod 755 {STANDALONE_WPA_REMOTE_DIR}/usr/sbin/wpa_supplicant; "
        f"printf '%s' {shlex.quote(str(archive_info.get('sha256') or ''))} > {STANDALONE_WPA_REMOTE_DIR}/.a90_bundle_sha256; "
        f"test -x {STANDALONE_WPA_REMOTE_WRAPPER}; echo standalone_wpa_stage.wrapper_executable_rc=$?; "
        f"/cache/bin/busybox timeout 6 {STANDALONE_WPA_REMOTE_WRAPPER} -v >/cache/a90-wifi/standalone-wpa-version.txt 2>&1; "
        f"echo standalone_wpa_stage.version_rc=$?; "
        f"printf 'standalone_wpa_stage.version_sample='; /cache/bin/busybox head -n 1 /cache/a90-wifi/standalone-wpa-version.txt 2>/dev/null | /cache/bin/busybox tr ' ' '_'"
    )
    extract = run_step(
        store,
        steps,
        "standalone-wpa-stage-extract-verify",
        ["run", "/cache/bin/busybox", "sh", "-c", extract_script],
        timeout=90,
        bridge_timeout=60,
    )
    fields.update(base.parse_key_values("\n".join([str(extract.get("stdout") or ""), str(extract.get("stderr") or "")])))
    fields["standalone_wpa_stage.ok"] = (
        "1"
        if extract.get("ok")
        and fields.get("standalone_wpa_stage.wrapper_executable_rc") == "0"
        and fields.get("standalone_wpa_stage.version_rc") == "0"
        else "0"
    )
    fields["standalone_wpa_stage.reason"] = "ok" if fields["standalone_wpa_stage.ok"] == "1" else "extract-or-version-failed"
    return fields


def build_supplicant_property_runtime(store: base.EvidenceStore) -> dict[str, Any]:
    args = type("Args", (), {
        "out_dir": OUT_DIR,
        "v295_manifest": propbase.DEFAULT_V295,
        "v470_analysis": propbase.DEFAULT_V470,
        "android_getprop": propbase.DEFAULT_ANDROID_GETPROP,
    })()
    original_runtime_keys = propbase.RUNTIME_OBSERVED_KEYS
    original_fallback_values = dict(propbase.FALLBACK_VALUES)
    if PROPERTY_LAYOUT_DIR.exists():
        shutil.rmtree(PROPERTY_LAYOUT_DIR)
    try:
        propbase.RUNTIME_OBSERVED_KEYS = tuple(dict.fromkeys(
            original_runtime_keys +
            prop535.WIFI_COMPANION_OBSERVED_KEYS +
            SUPPLICANT_PROPERTY_KEYS
        ))
        propbase.FALLBACK_VALUES.update(prop535.RMT_STORAGE_FALLBACK_VALUES)
        propbase.FALLBACK_VALUES.update({key: "" for key in SUPPLICANT_PROPERTY_KEYS})
        manifest = propbase.build_manifest(args, store)
    finally:
        propbase.RUNTIME_OBSERVED_KEYS = original_runtime_keys
        propbase.FALLBACK_VALUES.clear()
        propbase.FALLBACK_VALUES.update(original_fallback_values)

    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v2167-wpa-supplicant-private-property-runtime-ready"
        if pass_ok
        else "v2167-wpa-supplicant-private-property-runtime-blocked"
    )
    manifest["reason"] = (
        "private property layout includes the wpa_supplicant loader/log lookup keys"
        if pass_ok
        else str(manifest.get("reason") or "property runtime generation blocked")
    )
    manifest["remote_property_root"] = PROPERTY_REMOTE_ROOT
    manifest["supplicant_property_keys"] = list(SUPPLICANT_PROPERTY_KEYS)
    store.write_json("property-runtime-manifest.json", manifest)
    return manifest


def build_property_archive(property_manifest: dict[str, Any]) -> dict[str, Any]:
    archive = OUT_DIR / "property-runtime-v2167.tgz"
    if not PROPERTY_ROOT.exists():
        return {"ok": False, "reason": "property-root-missing", "path": str(PROPERTY_ROOT)}
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(PROPERTY_ROOT.iterdir()):
            if path.is_file():
                tar.add(path, arcname=path.name, recursive=False)
    data = archive.read_bytes()
    return {
        "ok": True,
        "path": base.rel(archive),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "chunks": (len(base64.b64encode(data)) + CHUNK_SIZE - 1) // CHUNK_SIZE,
        "file_count": len([
            item for item in property_manifest.get("files", [])
            if str(item.get("relative_path") or "").startswith("layout/dev/__properties__/")
        ]),
    }


def stage_property_runtime(store: base.EvidenceStore,
                           steps: list[dict[str, Any]],
                           property_manifest: dict[str, Any],
                           archive_info: dict[str, Any],
                           fast_transfer: FastTransferSession | None = None) -> dict[str, str]:
    fields: dict[str, str] = {
        "property_stage.begin": "1",
        "property_stage.remote_root": PROPERTY_REMOTE_ROOT,
        "property_stage.boot_remote_root": BOOT_PROPERTY_REMOTE_ROOT,
        "property_stage.archive_sha256": str(archive_info.get("sha256") or ""),
        "property_stage.archive_len": str(archive_info.get("bytes") or "0"),
        "property_stage.file_count": str(archive_info.get("file_count") or "0"),
        "property_stage.runtime_decision": str(property_manifest.get("decision") or ""),
    }
    if not property_manifest.get("pass") or not archive_info.get("ok"):
        fields["property_stage.ok"] = "0"
        fields["property_stage.reason"] = "runtime-or-archive-build-failed"
        return fields

    archive_path = OUT_DIR / "property-runtime-v2167.tgz"
    clean_script = (
        f"/cache/bin/busybox rm -rf {PROPERTY_REMOTE_BASE} {BOOT_PROPERTY_REMOTE_BASE} {PROPERTY_REMOTE_TGZ} {PROPERTY_REMOTE_B64}; "
        f"/cache/bin/busybox mkdir -p {PROPERTY_REMOTE_ROOT} {BOOT_PROPERTY_REMOTE_ROOT}"
    )
    clean = run_step(
        store,
        steps,
        "property-runtime-stage-clean",
        ["run", "/cache/bin/busybox", "sh", "-c", clean_script],
        timeout=90,
        bridge_timeout=60,
    )
    if not clean.get("ok"):
        fields["property_stage.ok"] = "0"
        fields["property_stage.reason"] = "clean-or-mkdir-failed"
        return fields
    fields["property_stage.transfer_method"] = "serial-base64"
    if fast_transfer is not None:
        transfer = fast_transfer.transfer_file(
            label="property-runtime",
            local_path=archive_path,
            remote_path=PROPERTY_REMOTE_TGZ,
            expected_sha256=str(archive_info.get("sha256") or ""),
            mode="600",
        )
        fields["property_stage.fast_transfer_ok"] = "1" if transfer.get("ok") else "0"
        fields["property_stage.fast_transfer_reason"] = str(transfer.get("reason") or "")
        fields["property_stage.fast_transfer_elapsed_sec"] = str(transfer.get("elapsed_sec") or "")
        if transfer.get("ok"):
            fields["property_stage.transfer_method"] = "ncm-wget"
            extract_script = (
                f"set -e; "
                f"/cache/bin/busybox tar -xzf {PROPERTY_REMOTE_TGZ} -C {PROPERTY_REMOTE_ROOT}; "
                f"/cache/bin/busybox tar -xzf {PROPERTY_REMOTE_TGZ} -C {BOOT_PROPERTY_REMOTE_ROOT}; "
                f"/cache/bin/busybox chmod 755 {PROPERTY_REMOTE_BASE} {PROPERTY_REMOTE_BASE}/dev {PROPERTY_REMOTE_ROOT} "
                f"{BOOT_PROPERTY_REMOTE_BASE} {BOOT_PROPERTY_REMOTE_BASE}/dev {BOOT_PROPERTY_REMOTE_ROOT}; "
                f"/cache/bin/busybox chmod 644 {PROPERTY_REMOTE_ROOT}/* {BOOT_PROPERTY_REMOTE_ROOT}/*; "
                f"printf 'property_stage.remote_sha256='; /cache/bin/busybox sha256sum {PROPERTY_REMOTE_TGZ} | /cache/bin/busybox awk '{{print $1}}'; "
                f"printf 'property_stage.remote_file_count='; /cache/bin/busybox find {PROPERTY_REMOTE_ROOT} -type f | /cache/bin/busybox wc -l; "
                f"printf 'property_stage.property_info_size='; /cache/bin/busybox stat -c '%s' {PROPERTY_REMOTE_ROOT}/property_info 2>/dev/null; "
                f"printf 'property_stage.boot_remote_file_count='; /cache/bin/busybox find {BOOT_PROPERTY_REMOTE_ROOT} -type f | /cache/bin/busybox wc -l; "
                f"printf 'property_stage.boot_property_info_size='; /cache/bin/busybox stat -c '%s' {BOOT_PROPERTY_REMOTE_ROOT}/property_info 2>/dev/null"
            )
            extract = run_step(
                store,
                steps,
                "property-runtime-stage-extract",
                ["run", "/cache/bin/busybox", "sh", "-c", extract_script],
                timeout=45,
                bridge_timeout=20,
            )
            extract_output = "\n".join([str(extract.get("stdout") or ""), str(extract.get("stderr") or "")])
            fields.update(base.parse_key_values(extract_output))
            if not fields.get("property_stage.remote_sha256") and fields["property_stage.archive_sha256"] in extract_output:
                fields["property_stage.remote_sha256"] = fields["property_stage.archive_sha256"]
            fields["property_stage.ok"] = (
                "1"
                if fields.get("property_stage.remote_sha256") == fields["property_stage.archive_sha256"]
                else "0"
            )
            fields["property_stage.reason"] = "ok" if fields["property_stage.ok"] == "1" else "extract-or-sha-failed"
            return fields
    run_step(
        store,
        steps,
        "property-runtime-stage-touch-b64",
        ["run", "/cache/bin/busybox", "touch", PROPERTY_REMOTE_B64],
    )
    encoded = base64.b64encode(archive_path.read_bytes()).decode("ascii")
    chunks = [encoded[index:index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
    chunk_log: list[str] = []
    all_ok = True
    for index, chunk in enumerate(chunks):
        shell = f"printf '%s' {shlex.quote(chunk)} >> {PROPERTY_REMOTE_B64}"
        result = base.run_command(
            base.a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", shell], timeout=45),
            timeout=60,
        )
        ok = bool(result.get("ok"))
        all_ok = all_ok and ok
        chunk_log.append(f"chunk={index} rc={result.get('rc')} ok={ok} timeout={result.get('timeout')}")
        if not ok:
            break
    append_compact_step(
        store,
        steps,
        "property-runtime-stage-b64-chunks",
        command=["stage-base64-tgz", PROPERTY_REMOTE_B64, f"chunks={len(chunks)}"],
        ok=all_ok,
        rc=0 if all_ok else 1,
        stdout="\n".join(chunk_log) + "\n",
    )
    if not all_ok:
        fields["property_stage.ok"] = "0"
        fields["property_stage.reason"] = "chunk-write-failed"
        return fields

    extract_script = (
        f"set -e; "
        f"/cache/bin/busybox base64 -d {PROPERTY_REMOTE_B64} > {PROPERTY_REMOTE_TGZ}; "
        f"/cache/bin/busybox tar -xzf {PROPERTY_REMOTE_TGZ} -C {PROPERTY_REMOTE_ROOT}; "
        f"/cache/bin/busybox tar -xzf {PROPERTY_REMOTE_TGZ} -C {BOOT_PROPERTY_REMOTE_ROOT}; "
        f"/cache/bin/busybox chmod 755 {PROPERTY_REMOTE_BASE} {PROPERTY_REMOTE_BASE}/dev {PROPERTY_REMOTE_ROOT} "
        f"{BOOT_PROPERTY_REMOTE_BASE} {BOOT_PROPERTY_REMOTE_BASE}/dev {BOOT_PROPERTY_REMOTE_ROOT}; "
        f"/cache/bin/busybox chmod 644 {PROPERTY_REMOTE_ROOT}/* {BOOT_PROPERTY_REMOTE_ROOT}/*; "
        f"/cache/bin/busybox rm -f {PROPERTY_REMOTE_B64}; "
        f"printf 'property_stage.remote_sha256='; /cache/bin/busybox sha256sum {PROPERTY_REMOTE_TGZ} | /cache/bin/busybox awk '{{print $1}}'; "
        f"printf 'property_stage.remote_file_count='; /cache/bin/busybox find {PROPERTY_REMOTE_ROOT} -type f | /cache/bin/busybox wc -l; "
        f"printf 'property_stage.property_info_size='; /cache/bin/busybox stat -c '%s' {PROPERTY_REMOTE_ROOT}/property_info 2>/dev/null; "
        f"printf 'property_stage.boot_remote_file_count='; /cache/bin/busybox find {BOOT_PROPERTY_REMOTE_ROOT} -type f | /cache/bin/busybox wc -l; "
        f"printf 'property_stage.boot_property_info_size='; /cache/bin/busybox stat -c '%s' {BOOT_PROPERTY_REMOTE_ROOT}/property_info 2>/dev/null"
    )
    extract = run_step(
        store,
        steps,
        "property-runtime-stage-extract",
        ["run", "/cache/bin/busybox", "sh", "-c", extract_script],
        timeout=120,
        bridge_timeout=90,
    )
    fields.update(base.parse_key_values(str(extract.get("stdout") or "")))
    fields["property_stage.ok"] = (
        "1"
        if extract.get("ok") and fields.get("property_stage.remote_sha256") == fields["property_stage.archive_sha256"]
        else "0"
    )
    fields["property_stage.reason"] = "ok" if fields["property_stage.ok"] == "1" else "extract-or-sha-failed"
    return fields


def stage_connect_config(store: base.EvidenceStore,
                         steps: list[dict[str, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {
        "connect_config.begin": "1",
        "connect_config.path": CONNECT_CONFIG,
        "connect_config.raw_values_logged": "0",
    }
    try:
        config_bytes, meta = build_wpa_config()
    except ValueError as exc:
        fields["connect_config.ok"] = "0"
        fields["connect_config.reason"] = str(exc)
        return fields
    fields["connect_config.ssid_present"] = "1" if meta["ssid_present"] else "0"
    fields["connect_config.psk_present"] = "1" if meta["psk_present"] else "0"
    fields["connect_config.ssid_len"] = str(meta["ssid_len"])
    fields["connect_config.size"] = str(len(config_bytes))
    fields["connect_config.security_mode"] = str(meta["security_mode"])
    fields["connect_config.network_initially_disabled"] = "1" if meta["network_initially_disabled"] else "0"
    mkdir = run_step(
        store,
        steps,
        "connect-config-mkdir",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                f"umask 077; "
                f"/cache/bin/busybox mkdir -p {CONNECT_DIR}/sockets; "
                f"/cache/bin/busybox chown 1010:1010 {CONNECT_DIR} {CONNECT_DIR}/sockets; "
                f"/cache/bin/busybox chmod 770 {CONNECT_DIR} {CONNECT_DIR}/sockets; "
                f"/cache/bin/busybox rm -f {CONNECT_DIR}/sockets/wpa_global {CONNECT_DIR}/sockets/wlan0 "
                f"{CONNECT_DIR}/a90_supplicant_strace*"
            ),
        ],
    )
    if not mkdir.get("ok"):
        fields["connect_config.ok"] = "0"
        fields["connect_config.reason"] = "mkdir-failed"
        return fields
    run_step(
        store,
        steps,
        "connect-config-clean",
        ["run", "/cache/bin/busybox", "rm", "-f", CONNECT_CONFIG, CONNECT_CONFIG_B64],
    )
    run_step(
        store,
        steps,
        "connect-config-touch-b64",
        ["run", "/cache/bin/busybox", "touch", CONNECT_CONFIG_B64],
    )
    encoded = base64.b64encode(config_bytes).decode("ascii")
    chunks = [encoded[index:index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]
    chunk_log: list[str] = []
    all_ok = True
    for index, chunk in enumerate(chunks):
        shell = f"printf '%s' {shlex.quote(chunk)} >> {CONNECT_CONFIG_B64}"
        result = base.run_command(
            base.a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", shell], timeout=45),
            timeout=60,
        )
        ok = bool(result.get("ok"))
        all_ok = all_ok and ok
        chunk_log.append(f"chunk={index} rc={result.get('rc')} ok={ok} timeout={result.get('timeout')}")
        if not ok:
            break
    append_compact_step(
        store,
        steps,
        "connect-config-write-redacted",
        command=["write-redacted-connect-config", CONNECT_CONFIG_B64, f"chunks={len(chunks)}"],
        ok=all_ok,
        rc=0 if all_ok else 1,
        stdout="\n".join(chunk_log) + "\n",
    )
    if not all_ok:
        fields["connect_config.ok"] = "0"
        fields["connect_config.reason"] = "chunk-write-failed"
        return fields
    decode_script = (
        f"set -e; "
        f"/cache/bin/busybox base64 -d {CONNECT_CONFIG_B64} > {CONNECT_CONFIG}; "
        f"/cache/bin/busybox chown 1010:1010 {CONNECT_CONFIG}; "
        f"/cache/bin/busybox chmod 600 {CONNECT_CONFIG}; "
        f"/cache/bin/busybox rm -f {CONNECT_CONFIG_B64}; "
        f"test -s {CONNECT_CONFIG}; echo connect_config.exists_rc=$?; "
        f"printf 'connect_config.mode='; /cache/bin/busybox stat -c '%a' {CONNECT_CONFIG} 2>/dev/null; "
        f"printf 'connect_config.size='; /cache/bin/busybox stat -c '%s' {CONNECT_CONFIG} 2>/dev/null"
    )
    decode = run_step(
        store,
        steps,
        "connect-config-decode-redacted",
        ["run", "/cache/bin/busybox", "sh", "-c", decode_script],
    )
    fields.update(base.parse_key_values(str(decode.get("stdout") or "")))
    fields["connect_config.ok"] = "1" if decode.get("ok") and fields.get("connect_config.exists_rc") == "0" else "0"
    fields["connect_config.reason"] = "ok" if fields["connect_config.ok"] == "1" else "decode-or-stat-failed"
    return fields


def stage_connect_script(store: base.EvidenceStore,
                         steps: list[dict[str, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {
        "connect_script.begin": "1",
        "connect_script.path": CONNECT_SCRIPT,
        "connect_script.result_path": CONNECT_RESULT,
        "connect_script.raw_values_logged": "0",
        "connect_script.qa_hold_sec": str(QA_HOLD_SEC),
        "connect_script.qa_hold_interval_sec": str(QA_HOLD_INTERVAL_SEC),
        "connect_script.qa_reconnect_on_drop": "1" if QA_RECONNECT_ON_DROP else "0",
        "connect_script.force_power_on": "1" if FORCE_POWER_ON else "0",
        "connect_script.hold_subsys_modem": "1" if CONNECT_HOLD_SUBSYS_MODEM else "0",
    }
    helper_args = [
        HELPER_REMOTE,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-active-session-connect-ping",
        "--target-profile",
        "vendor-wifi-hal-ext",
        "--null-device-mode",
        "dev-null-selinux",
        "--data-wifi-mode",
        "private-empty",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--property-root",
        PROPERTY_REMOTE_ROOT,
        "--connect-config",
        CONNECT_CONFIG,
        "--connect-iface",
        "wlan0",
        "--ping-target",
        PING_TARGET,
        "--timeout-sec",
        "120",
        "--allow-service-manager-start-only",
        "--allow-wifi-hal-start-only",
        "--allow-cnss-start-only",
        "--allow-hal-service-query",
        "--allow-iwifi-start-only",
        "--allow-connect-dhcp-ping",
    ]
    if QA_HOLD_SEC > 0:
        helper_args.extend([
            "--connect-hold-sec",
            str(QA_HOLD_SEC),
            "--connect-hold-interval-sec",
            str(QA_HOLD_INTERVAL_SEC),
        ])
        if QA_RECONNECT_ON_DROP:
            helper_args.append("--connect-reconnect-on-drop")
    if FORCE_POWER_ON:
        helper_args.append("--connect-force-power-on")
    if CONNECT_HOLD_SUBSYS_MODEM:
        helper_args.append("--connect-hold-subsys-modem")
    helper_command = " ".join(shlex.quote(part) for part in helper_args)
    run_step(store, steps, "connect-script-clean", ["run", "/cache/bin/busybox", "rm", "-f", CONNECT_SCRIPT, CONNECT_RESULT])
    run_step(store, steps, "connect-script-touch", ["run", "/cache/bin/busybox", "touch", CONNECT_SCRIPT])
    script_lines = [
        "#!/cache/bin/busybox sh",
        f"out={CONNECT_RESULT}",
        "echo v2167.begin=1 > \"$out\"",
        "echo v2167.raw_values_logged=0 >> \"$out\"",
        "echo v2167.credentials_read=1 >> \"$out\"",
        "echo v2167.connect_attempted=1 >> \"$out\"",
        "echo v2167.dhcp_route_attempted=1 >> \"$out\"",
        "echo v2167.external_ping_attempted=1 >> \"$out\"",
        f"echo v2167.qa_hold_sec={QA_HOLD_SEC} >> \"$out\"",
        f"echo v2167.qa_hold_interval_sec={QA_HOLD_INTERVAL_SEC} >> \"$out\"",
        f"echo v2167.qa_reconnect_on_drop={1 if QA_RECONNECT_ON_DROP else 0} >> \"$out\"",
        f"echo v2167.connect_hold_subsys_modem={1 if CONNECT_HOLD_SUBSYS_MODEM else 0} >> \"$out\"",
        "loop=0",
        "while [ \"$loop\" -lt 1200 ]; do",
        "if [ -e /sys/class/net/wlan0 ]; then echo v2167.wlan0_seen=1 >> \"$out\"; break; fi",
        "loop=$((loop+1))",
        "sleep 0.2",
        "done",
        "if [ ! -e /sys/class/net/wlan0 ]; then echo v2167.wlan0_seen=0 >> \"$out\"; echo v2167.result=wlan0-missing >> \"$out\"; echo v2167.end=1 >> \"$out\"; exit 20; fi",
        "printf 'v2167.pre_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2167.pre_carrier=' >> \"$out\"; cat /sys/class/net/wlan0/carrier >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2167.pre_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "echo v2167.helper_invoked=1 >> \"$out\"",
        f"{helper_command} >> \"$out\" 2>&1",
        "echo v2167.helper_rc=$? >> \"$out\"",
        "printf 'v2167.post_operstate=' >> \"$out\"; cat /sys/class/net/wlan0/operstate >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2167.post_carrier=' >> \"$out\"; cat /sys/class/net/wlan0/carrier >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "printf 'v2167.post_flags=' >> \"$out\"; cat /sys/class/net/wlan0/flags >> \"$out\" 2>/dev/null || echo unreadable >> \"$out\"",
        "echo v2167.end=1 >> \"$out\"",
    ]
    failed_script_lines: list[int] = []
    for index, line in enumerate(script_lines):
        result = run_step(
            store,
            steps,
            f"connect-script-line-{index:02d}",
            ["run", "/cache/bin/busybox", "sh", "-c", f"printf '%s\\n' {shlex.quote(line)} >> {CONNECT_SCRIPT}"],
        )
        if not result.get("ok"):
            failed_script_lines.append(index)
    validate_script = (
        "set -e; "
        f"script={shlex.quote(CONNECT_SCRIPT)}; tmp={shlex.quote(CONNECT_SCRIPT)}.tmp; "
        "shebang='#!/cache/bin/busybox sh'; repaired=0; "
        "first=$(/cache/bin/busybox head -n 1 \"$script\" 2>/dev/null || true); "
        "if [ \"$first\" != \"$shebang\" ]; then "
        "  { printf '%s\\n' \"$shebang\"; /cache/bin/busybox cat \"$script\" 2>/dev/null || true; } > \"$tmp\"; "
        "  /cache/bin/busybox mv \"$tmp\" \"$script\"; repaired=1; "
        "fi; "
        f"expected={len(script_lines)}; "
        "line_count=$(/cache/bin/busybox wc -l < \"$script\" 2>/dev/null || echo 0); "
        "first_after=$(/cache/bin/busybox head -n 1 \"$script\" 2>/dev/null || true); "
        "last_ok=0; /cache/bin/busybox tail -n 1 \"$script\" 2>/dev/null | "
        "/cache/bin/busybox grep -q '^echo v2167.end=1' && last_ok=1; "
        "content_ok=0; "
        "[ \"$first_after\" = \"$shebang\" ] && [ \"$line_count\" -ge \"$expected\" ] && [ \"$last_ok\" = 1 ] && content_ok=1; "
        "echo connect_script.shebang_repaired=$repaired; "
        "echo connect_script.line_count=$line_count; "
        "echo connect_script.expected_lines=$expected; "
        "echo connect_script.last_ok=$last_ok; "
        "echo connect_script.content_ok=$content_ok"
    )
    validate = run_step(
        store,
        steps,
        "connect-script-validate",
        ["run", "/cache/bin/busybox", "sh", "-c", validate_script],
    )
    chmod = run_step(store, steps, "connect-script-chmod", ["run", "/cache/bin/busybox", "chmod", "700", CONNECT_SCRIPT])
    start = run_step(
        store,
        steps,
        "connect-script-start",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"/cache/bin/busybox setsid {CONNECT_SCRIPT} >/dev/null 2>&1 & echo connect_script.started=1",
        ],
    )
    fields.update(base.parse_key_values(str(validate.get("stdout") or "")))
    fields.update(base.parse_key_values(str(start.get("stdout") or "")))
    fields["connect_script.line_fail_count"] = str(len(failed_script_lines))
    fields["connect_script.failed_lines"] = ",".join(str(item) for item in failed_script_lines)
    fields["connect_script.lines_ok"] = "1" if not failed_script_lines else "0"
    fields["connect_script.ok"] = (
        "1"
        if fields.get("connect_script.content_ok") == "1"
        and chmod.get("ok")
        and fields.get("connect_script.started") == "1"
        else "0"
    )
    return fields


def wait_for_connect_result(store: base.EvidenceStore,
                            steps: list[dict[str, Any]],
                            *,
                            max_wait_sec: float = 190.0) -> dict[str, Any]:
    import time

    deadline = time.monotonic() + max_wait_sec
    polls: list[str] = []
    complete = False
    present = False
    last_stdout = ""
    while time.monotonic() <= deadline:
        command = (
            f"present=0; complete=0; test -s {CONNECT_RESULT} && present=1; "
            f"/cache/bin/busybox grep -q '^v2167.end=1' {CONNECT_RESULT} 2>/dev/null && complete=1; "
            f"size=$(/cache/bin/busybox wc -c < {CONNECT_RESULT} 2>/dev/null || echo 0); "
            "echo connect_result.present=$present connect_result.complete=$complete connect_result.size=$size"
        )
        result = base.run_command(
            base.a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", command], timeout=35),
            timeout=45,
        )
        if "[busy]" in str(result.get("stdout") or ""):
            base.run_command(base.a90ctl_command(["hide"], timeout=20), timeout=30)
            result = base.run_command(
                base.a90ctl_command(["run", "/cache/bin/busybox", "sh", "-c", command], timeout=35),
                timeout=45,
            )
        last_stdout = str(result.get("stdout") or "")
        polls.append(f"[{base.now_iso()}] rc={result.get('rc')} timeout={result.get('timeout')} {last_stdout.strip()}")
        present = "connect_result.present=1" in last_stdout
        complete = "connect_result.complete=1" in last_stdout
        if complete:
            break
        time.sleep(3.0)
    stdout_path = store.write_log("host", "connect-result-wait-polls.txt", "\n".join(polls) + "\n")
    stdout_file = str(stdout_path.relative_to(store.run_dir))
    steps.append({
        "name": "connect-result-wait-polls",
        "command": ["poll", CONNECT_RESULT],
        "started": polls[0].split("]")[0].lstrip("[") if polls else base.now_iso(),
        "ended": base.now_iso(),
        "timeout": not complete,
        "rc": 0 if complete else 1,
        "ok": complete,
        "stdout_file": stdout_file,
        "stderr_file": "",
    })
    return {
        "present": present,
        "complete": complete,
        "last_stdout": last_stdout,
        "poll_count": len(polls),
    }


def post_flash_connect(store: base.EvidenceStore,
                       steps: list[dict[str, Any]],
                       helper_fields: dict[str, str],
                       standalone_wpa_fields: dict[str, str],
                       property_fields: dict[str, str],
                       config_fields: dict[str, str]) -> dict[str, Any]:
    script_fields = stage_connect_script(store, steps)
    wait_fields = wait_for_connect_result(store, steps, max_wait_sec=190.0 + float(QA_HOLD_SEC))
    ok = (
        property_fields.get("property_stage.ok") == "1"
        and helper_fields.get("helper_stage.ok") == "1"
        and standalone_wpa_fields.get("standalone_wpa_stage.ok") == "1"
        and config_fields.get("connect_config.ok") == "1"
        and script_fields.get("connect_script.ok") == "1"
        and wait_fields.get("complete") is True
    )
    return {
        "ok": ok,
        "fields": {**property_fields, **helper_fields, **standalone_wpa_fields, **config_fields, **script_fields},
        "wait": wait_fields,
    }


def collect_post_rollback_result(store: base.EvidenceStore,
                                 steps: list[dict[str, Any]]) -> dict[str, Any]:
    fast_transfer = FastTransferSession(store, steps)
    fast_upload: dict[str, Any]
    try:
        fast_upload = FastUploadSession(fast_transfer).upload_v2167_logs()
    finally:
        fast_transfer.close()

    serial_results: list[dict[str, Any]] = []
    result_text = str(fast_upload.get("connect_result_text") or "")
    result_source = "fast-upload" if has_v2167_result(result_text) else ""
    if result_source:
        append_compact_step(
            store,
            steps,
            "post-rollback-connect-ping-result-fast-upload",
            command=["fast-upload", "read", CONNECT_RESULT],
            ok=True,
            rc=0,
            stdout=result_text,
        )
    else:
        for attempt in range(3):
            name = "post-rollback-connect-ping-result" if attempt == 0 else f"post-rollback-connect-ping-result-retry{attempt}"
            result = base.a90ctl_step(
                store,
                steps,
                name,
                ["cat", CONNECT_RESULT],
                timeout=120,
                bridge_timeout=90,
            )
            serial_results.append(result)
            result_text = str(result.get("stdout") or "")
            if has_v2167_result(result_text):
                result_source = "serial-cat" if attempt == 0 else f"serial-cat-retry{attempt}"
                break
            if attempt < 2:
                base.a90ctl_step(
                    store,
                    steps,
                    f"post-rollback-connect-ping-result-hide-retry{attempt + 1}",
                    ["hide"],
                    timeout=15,
                    bridge_timeout=10,
                )
                time.sleep(1.5)
    fields = parse_fields(result_text)
    result_retrieved = has_v2167_result(result_text)
    cleanup_script = (
        "bb=/cache/bin/busybox; "
        "$bb rm -f /cache/a90-v2167-connect-ping.sh /cache/a90-v2167-connect-ping.result "
        "/cache/a90-v2167-helper.b64 /cache/a90-v2167-helper.gz "
        "/cache/a90-wifi-property-v2167.tgz /cache/a90-wifi-property-v2167.b64; "
        "cd /cache/a90-wifi 2>/dev/null && "
        "$bb rm -f v2167.conf v2167.conf.b64 a90_supplicant_execns.log "
        "a90_supplicant_execns_stdio.log a90_supplicant_strace* "
        "a90_hwservicemanager_execns_stdio.log a90_connect_kmsg_stream.log "
        "a90_external_ping_capture.log sockets/wpa_global sockets/wlan0; "
        "$bb rm -rf /cache/a90-wifi-property-v2167"
    )
    cleanup: dict[str, Any] | None = None
    cleanup_skipped_reason = ""
    if result_retrieved:
        cleanup = base.a90ctl_step(
            store,
            steps,
            "post-rollback-connect-ping-cleanup",
            ["run", "/cache/bin/busybox", "sh", "-c", cleanup_script],
            timeout=90,
            bridge_timeout=60,
        )
    else:
        cleanup_skipped_reason = "connect-result-not-retrieved"
        append_compact_step(
            store,
            steps,
            "post-rollback-connect-ping-cleanup-skipped",
            command=["cleanup-skipped", CONNECT_RESULT],
            ok=False,
            rc=1,
            stdout=f"cleanup_skipped.reason={cleanup_skipped_reason}\nresult_left_on_device=1\n",
        )
    return {
        "ok": result_retrieved,
        "fields": fields,
        "fast_upload": {
            key: value
            for key, value in fast_upload.items()
            if key != "connect_result_text"
        },
        "result_source": result_source or "unretrieved",
        "serial_attempt_count": len(serial_results),
        "cleanup_ok": bool(cleanup and cleanup.get("ok")),
        "cleanup_skipped_reason": cleanup_skipped_reason,
        "result_left_on_device": not result_retrieved,
    }


def collect_gate(manifest: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    hook = manifest.get("post_flash_hook") if isinstance(manifest.get("post_flash_hook"), dict) else {}
    hook_fields = hook.get("fields") if isinstance(hook.get("fields"), dict) else {}
    fields = result.get("fields") if isinstance(result.get("fields"), dict) else {}
    fast_upload = result.get("fast_upload") if isinstance(result.get("fast_upload"), dict) else {}
    fast_upload_validation = (
        fast_upload.get("validation")
        if isinstance(fast_upload.get("validation"), dict)
        else {}
    )
    fast_upload_receiver = (
        fast_upload.get("receiver")
        if isinstance(fast_upload.get("receiver"), dict)
        else {}
    )
    rollback_ok = bool((manifest.get("rollback") or {}).get("ok"))
    property_stage_ok = hook_fields.get("property_stage.ok") == "1"
    helper_stage_ok = hook_fields.get("helper_stage.ok") == "1"
    standalone_wpa_stage_ok = hook_fields.get("standalone_wpa_stage.ok") == "1"
    config_ok = hook_fields.get("connect_config.ok") == "1"
    script_ok = hook_fields.get("connect_script.ok") == "1"
    wait_complete = bool((hook.get("wait") or {}).get("complete"))
    wlan0_seen = fields.get("v2167.wlan0_seen") == "1"
    helper_invoked = fields.get("v2167.helper_invoked") == "1"
    helper_rc = intish(fields.get("v2167.helper_rc"))
    executor_result = fields.get("wifi_connect_ping.result", "")
    association_carrier = fields.get("wifi_connect_ping.association_carrier") == "1"
    dhcp_rc = intish(fields.get("wifi_connect_ping.dhcp_rc"))
    ping_target = fields.get("wifi_connect_ping.external_ping_target", "")
    ping_rc = intish(fields.get("wifi_connect_ping.external_ping_rc"))
    hold_enabled = fields.get("wifi_connect_ping.hold.enabled") == "1"
    hold_pass = fields.get("wifi_connect_ping.hold.pass", "1") == "1"
    no_raw = fields.get("v2167.raw_values_logged") == "0" and fields.get("wifi_connect_ping.secret_values_logged", "0") == "0"
    if not manifest.get("test_flash_ok") or not rollback_ok:
        label = "connect-dhcp-ping-handoff-incomplete"
        passed = False
        reason = "test boot or rollback did not complete"
    elif not property_stage_ok or not helper_stage_ok or not standalone_wpa_stage_ok or not config_ok or not script_ok or not wait_complete:
        label = "connect-dhcp-ping-stage-or-wait-failed"
        passed = False
        reason = (
            f"stage/wait failed property={property_stage_ok} helper={helper_stage_ok} standalone_wpa={standalone_wpa_stage_ok} "
            f"config={config_ok} script={script_ok} wait={wait_complete}"
        )
    elif not no_raw:
        label = "connect-dhcp-ping-redaction-violation"
        passed = False
        reason = "result did not preserve redaction markers"
    elif not wlan0_seen:
        label = "connect-dhcp-ping-no-wlan0"
        passed = False
        reason = "wlan0 was absent in the connect window"
    elif not helper_invoked:
        label = "connect-dhcp-ping-helper-not-invoked"
        passed = False
        reason = "connect helper was not invoked"
    elif helper_rc != 0 and not executor_result:
        label = "connect-dhcp-ping-helper-argument-failed"
        passed = False
        reason = f"connect helper exited before executor body rc={helper_rc}"
    elif association_carrier and dhcp_rc == 0 and ping_target == PING_TARGET and ping_rc == 0 and hold_enabled and not hold_pass:
        label = "connect-dhcp-ping-hold-failed"
        passed = False
        reason = f"native wlan0 associated, DHCP and google.com ping succeeded, but hold failed: {fields.get('wifi_connect_ping.hold.reason', 'unknown')}"
    elif executor_result == "connect-dhcp-ping-pass" and helper_rc == 0 and association_carrier and dhcp_rc == 0 and ping_target == PING_TARGET and ping_rc == 0:
        label = "connect-dhcp-google-ping-hold-pass" if hold_enabled else "connect-dhcp-google-ping-pass"
        passed = True
        reason = (
            "native wlan0 associated, DHCP succeeded, google.com ping returned success, and hold stayed stable"
            if hold_enabled
            else "native wlan0 associated, DHCP succeeded, and google.com ping returned success"
        )
    elif not association_carrier:
        label = "connect-dhcp-ping-association-failed"
        passed = False
        reason = f"supplicant did not establish carrier; result={executor_result} helper_rc={helper_rc}"
    elif dhcp_rc != 0:
        label = "connect-dhcp-ping-dhcp-failed"
        passed = False
        reason = f"association carrier came up but DHCP failed rc={dhcp_rc}"
    elif ping_rc != 0:
        label = "connect-dhcp-ping-google-ping-failed"
        passed = False
        reason = f"association and DHCP succeeded but google.com ping failed rc={ping_rc}"
    else:
        label = "connect-dhcp-ping-unclassified-failed"
        passed = False
        reason = f"executor_result={executor_result or 'missing'} helper_rc={helper_rc}"
    return {
        "label": label,
        "decision": f"v2167-{label}",
        "pass": passed,
        "reason": reason,
        "helper_stage_ok": helper_stage_ok,
        "standalone_wpa_stage_ok": standalone_wpa_stage_ok,
        "standalone_wpa_stage_enabled": hook_fields.get("standalone_wpa_stage.enabled", ""),
        "standalone_wpa_stage_reason": hook_fields.get("standalone_wpa_stage.reason", ""),
        "standalone_wpa_stage_remote_wrapper": hook_fields.get("standalone_wpa_stage.remote_wrapper", ""),
        "standalone_wpa_stage_package_count": intish(hook_fields.get("standalone_wpa_stage.package_count")),
        "standalone_wpa_stage_version_rc": intish(hook_fields.get("standalone_wpa_stage.version_rc")),
        "standalone_wpa_stage_version_sample": hook_fields.get("standalone_wpa_stage.version_sample", ""),
        "property_stage_ok": property_stage_ok,
        "property_stage_remote_root": hook_fields.get("property_stage.remote_root", ""),
        "property_stage_runtime_decision": hook_fields.get("property_stage.runtime_decision", ""),
        "property_stage_file_count": intish(hook_fields.get("property_stage.remote_file_count")),
        "property_stage_property_info_size": intish(hook_fields.get("property_stage.property_info_size")),
        "config_ok": config_ok,
        "script_ok": script_ok,
        "wait_complete": wait_complete,
        "wlan0_seen": wlan0_seen,
        "helper_invoked": helper_invoked,
        "helper_rc": helper_rc,
        "executor_result": executor_result,
        "pre_operstate": fields.get("v2167.pre_operstate", ""),
        "pre_carrier": fields.get("v2167.pre_carrier", ""),
        "pre_flags": fields.get("v2167.pre_flags", ""),
        "post_operstate": fields.get("v2167.post_operstate", ""),
        "post_carrier": fields.get("v2167.post_carrier", ""),
        "post_flags": fields.get("v2167.post_flags", ""),
        "association_carrier": association_carrier,
        "association_carrier_errno": intish(fields.get("wifi_connect_ping.association_carrier_errno")),
        "dhcp_rc": dhcp_rc,
        "dhcp_executed": fields.get("wifi_connect_ping.dhcp_executed") == "1",
        "resolv_conf_present": fields.get("wifi_connect_ping.resolv_conf.present") == "1",
        "resolv_conf_errno": intish(fields.get("wifi_connect_ping.resolv_conf.errno")),
        "resolv_conf_size": intish(fields.get("wifi_connect_ping.resolv_conf.size")),
        "resolv_conf_nameserver_count": intish(fields.get("wifi_connect_ping.resolv_conf.nameserver_count")),
        "external_ping_target": ping_target,
        "external_ping_rc": ping_rc,
        "external_ping_executed": fields.get("wifi_connect_ping.external_ping_executed") == "1",
        "external_ping_output_present": fields.get("wifi_connect_ping.external_ping_output.present") == "1",
        "external_ping_output_errno": intish(fields.get("wifi_connect_ping.external_ping_output.errno")),
        "external_ping_output_bytes_from": fields.get("wifi_connect_ping.external_ping_output.bytes_from") == "1",
        "external_ping_output_bad_address": fields.get("wifi_connect_ping.external_ping_output.bad_address") == "1",
        "external_ping_output_unknown_host": fields.get("wifi_connect_ping.external_ping_output.unknown_host") == "1",
        "external_ping_output_network_unreachable": fields.get("wifi_connect_ping.external_ping_output.network_unreachable") == "1",
        "external_ping_output_permission_denied": fields.get("wifi_connect_ping.external_ping_output.permission_denied") == "1",
        "external_ping_output_sendto_error": fields.get("wifi_connect_ping.external_ping_output.sendto_error") == "1",
        "external_ping_output_zero_received": fields.get("wifi_connect_ping.external_ping_output.zero_received") == "1",
        "external_ping_output_packet_loss_100": fields.get("wifi_connect_ping.external_ping_output.packet_loss_100") == "1",
        "external_ping_output_classifier": fields.get("wifi_connect_ping.external_ping_output.classifier", ""),
        "hold_enabled": hold_enabled,
        "hold_executed": fields.get("wifi_connect_ping.hold.executed") == "1",
        "hold_requested_sec": intish(fields.get("wifi_connect_ping.hold.requested_sec")),
        "hold_interval_sec": intish(fields.get("wifi_connect_ping.hold.interval_sec")),
        "hold_reconnect_on_drop": fields.get("wifi_connect_ping.hold.reconnect_on_drop") == "1",
        "hold_samples": intish(fields.get("wifi_connect_ping.hold.samples")),
        "hold_carrier_up_count": intish(fields.get("wifi_connect_ping.hold.carrier_up_count")),
        "hold_carrier_down_count": intish(fields.get("wifi_connect_ping.hold.carrier_down_count")),
        "hold_ping_attempt_count": intish(fields.get("wifi_connect_ping.hold.ping_attempt_count")),
        "hold_ping_success_count": intish(fields.get("wifi_connect_ping.hold.ping_success_count")),
        "hold_ping_fail_count": intish(fields.get("wifi_connect_ping.hold.ping_fail_count")),
        "hold_ip_ping_attempt_count": intish(fields.get("wifi_connect_ping.hold.ip_ping_attempt_count")),
        "hold_ip_ping_success_count": intish(fields.get("wifi_connect_ping.hold.ip_ping_success_count")),
        "hold_ip_ping_fail_count": intish(fields.get("wifi_connect_ping.hold.ip_ping_fail_count")),
        "hold_gateway_ping_attempt_count": intish(fields.get("wifi_connect_ping.hold.gateway_ping_attempt_count")),
        "hold_gateway_ping_success_count": intish(fields.get("wifi_connect_ping.hold.gateway_ping_success_count")),
        "hold_gateway_ping_fail_count": intish(fields.get("wifi_connect_ping.hold.gateway_ping_fail_count")),
        "hold_route_default_present_count": intish(fields.get("wifi_connect_ping.hold.route_default_present_count")),
        "hold_route_gateway_present_count": intish(fields.get("wifi_connect_ping.hold.route_gateway_present_count")),
        "hold_arp_before_entry_count": intish(fields.get("wifi_connect_ping.hold.arp_before_entry_count")),
        "hold_arp_before_complete_count": intish(fields.get("wifi_connect_ping.hold.arp_before_complete_count")),
        "hold_arp_after_entry_count": intish(fields.get("wifi_connect_ping.hold.arp_after_entry_count")),
        "hold_arp_after_complete_count": intish(fields.get("wifi_connect_ping.hold.arp_after_complete_count")),
        "hold_reconnect_attempt_count": intish(fields.get("wifi_connect_ping.hold.reconnect_attempt_count")),
        "hold_reconnect_success_count": intish(fields.get("wifi_connect_ping.hold.reconnect_success_count")),
        "hold_first_fail_sample": intish(fields.get("wifi_connect_ping.hold.first_fail_sample")),
        "hold_first_fail_errno": intish(fields.get("wifi_connect_ping.hold.first_fail_errno")),
        "hold_first_fail_ping_rc": intish(fields.get("wifi_connect_ping.hold.first_fail_ping_rc")),
        "hold_pass": hold_pass,
        "hold_reason": fields.get("wifi_connect_ping.hold.reason", ""),
        "hold_sample_details": collect_hold_sample_details(fields),
        "force_power_on_enabled": fields.get("wifi_connect_ping.force_power_on.enabled") == "1",
        "force_power_on_executed": fields.get("wifi_connect_ping.force_power_on.executed") == "1",
        "force_power_on_reason": fields.get("wifi_connect_ping.force_power_on.reason", ""),
        "force_power_on_class_before": fields.get("wifi_connect_ping.force_power_on.class_before", ""),
        "force_power_on_class_write_rc": intish(fields.get("wifi_connect_ping.force_power_on.class_write_rc")),
        "force_power_on_class_write_errno": intish(fields.get("wifi_connect_ping.force_power_on.class_write_errno")),
        "force_power_on_class_after": fields.get("wifi_connect_ping.force_power_on.class_after", ""),
        "force_power_on_device_before": fields.get("wifi_connect_ping.force_power_on.device_before", ""),
        "force_power_on_device_write_rc": intish(fields.get("wifi_connect_ping.force_power_on.device_write_rc")),
        "force_power_on_device_write_errno": intish(fields.get("wifi_connect_ping.force_power_on.device_write_errno")),
        "force_power_on_device_after": fields.get("wifi_connect_ping.force_power_on.device_after", ""),
        "connect_hold_subsys_modem_requested": fields.get("v2167.connect_hold_subsys_modem") == "1",
        "modem_holder_enabled": fields.get("wifi_connect_ping.modem_holder.enabled") == "1",
        "modem_holder_started": fields.get("wifi_connect_ping.modem_holder.started") == "1",
        "modem_holder_start_attempted": fields.get("wlan_pd_modem_holder.start_attempted") == "1",
        "modem_holder_opened": fields.get("wlan_pd_modem_holder.opened") == "1",
        "modem_holder_open_errno": intish(fields.get("wlan_pd_modem_holder.open_errno")),
        "modem_holder_pid": intish(fields.get("wlan_pd_modem_holder.pid")),
        "modem_holder_stop_attempted": fields.get("wlan_pd_modem_holder.stop_attempted") == "1",
        "modem_holder_reaped": fields.get("wlan_pd_modem_holder.reaped") == "1",
        "modem_holder_postflight_safe": fields.get("wlan_pd_modem_holder.postflight_safe") == "1",
        "modem_holder_subsys_esoc0_open_attempted": fields.get("wlan_pd_modem_holder.subsys_esoc0_open_attempted") == "1",
        "modem_holder_esoc_open_attempted": fields.get("wlan_pd_modem_holder.esoc_open_attempted") == "1",
        "modem_holder_forced_rc1_attempted": fields.get("wlan_pd_modem_holder.forced_rc1_attempted") == "1",
        "secret_values_logged": fields.get("wifi_connect_ping.secret_values_logged", ""),
        "country_code": fields.get("wifi_connect_ping.country_code", ""),
        "driver_ioctl_country_rc": intish(fields.get("wifi_connect_ping.driver_ioctl.country.rc")),
        "driver_ioctl_country_errno": intish(fields.get("wifi_connect_ping.driver_ioctl.country.errno")),
        "driver_ioctl_getcountry_rc": intish(fields.get("wifi_connect_ping.driver_ioctl.getcountry.rc")),
        "driver_ioctl_getcountry_errno": intish(fields.get("wifi_connect_ping.driver_ioctl.getcountry.errno")),
        "driver_ioctl_getcountry_readback": fields.get("wifi_connect_ping.driver_ioctl.getcountry.readback", ""),
        "wpa_ctrl_ready": fields.get("wifi_connect_ping.wpa_ctrl.ready") == "1",
        "wpa_ctrl_dir": fields.get("wifi_connect_ping.wpa_ctrl.dir", ""),
        "wpa_ctrl_interface_path": fields.get("wifi_connect_ping.wpa_ctrl.interface_path", ""),
        "wpa_ctrl_surface": fields.get("wifi_connect_ping.wpa_ctrl.surface", ""),
        "wpa_ctrl_global_path": fields.get("wifi_connect_ping.wpa_ctrl.global_path", ""),
        "wpa_ctrl_global_abstract": fields.get("wifi_connect_ping.wpa_ctrl.global_abstract") == "1",
        "wpa_ctrl_global_preclean_path": fields.get("wifi_connect_ping.wpa_ctrl.global_preclean_path", ""),
        "wpa_ctrl_global_preclean_errno": intish(fields.get("wifi_connect_ping.wpa_ctrl.global_preclean_errno")),
        "wpa_ctrl_ready_errno": intish(fields.get("wifi_connect_ping.wpa_ctrl.ready_errno")),
        "wpa_ctrl_ping_reply": fields.get("wifi_connect_ping.wpa_ctrl.ping_reply", ""),
        "driver_country_reply": fields.get("wifi_connect_ping.wpa_ctrl.driver_country.reply", ""),
        "driver_country_rc": intish(fields.get("wifi_connect_ping.wpa_ctrl.driver_country.rc")),
        "driver_country_errno": intish(fields.get("wifi_connect_ping.wpa_ctrl.driver_country.errno")),
        "interface_add_reply": fields.get("wifi_connect_ping.wpa_ctrl.interface_add.reply", ""),
        "interface_add_rc": intish(fields.get("wifi_connect_ping.wpa_ctrl.interface_add.rc")),
        "interface_add_errno": intish(fields.get("wifi_connect_ping.wpa_ctrl.interface_add.errno")),
        "wpa_ctrl_after_interface_add_ready": fields.get("wifi_connect_ping.wpa_ctrl.after_interface_add.ready") == "1",
        "wpa_ctrl_after_interface_add_surface": fields.get("wifi_connect_ping.wpa_ctrl.after_interface_add.surface", ""),
        "wpa_ctrl_after_interface_add_global_path": fields.get("wifi_connect_ping.wpa_ctrl.after_interface_add.global_path", ""),
        "wpa_ctrl_after_interface_add_global_abstract": fields.get("wifi_connect_ping.wpa_ctrl.after_interface_add.global_abstract") == "1",
        "wpa_ctrl_after_interface_add_errno": intish(fields.get("wifi_connect_ping.wpa_ctrl.after_interface_add.ready_errno")),
        "wpa_ctrl_after_interface_add_ping": fields.get("wifi_connect_ping.wpa_ctrl.after_interface_add.ping_reply", ""),
        "enable_network_reply": fields.get("wifi_connect_ping.wpa_ctrl.enable_network.reply", ""),
        "enable_network_rc": intish(fields.get("wifi_connect_ping.wpa_ctrl.enable_network.rc")),
        "reassociate_reply": fields.get("wifi_connect_ping.wpa_ctrl.reassociate.reply", ""),
        "reassociate_rc": intish(fields.get("wifi_connect_ping.wpa_ctrl.reassociate.rc")),
        "supplicant_driver": fields.get("wifi_connect_ping.supplicant_driver", ""),
        "supplicant_launch_mode": fields.get("wifi_connect_ping.supplicant_launch_mode", ""),
        "supplicant_global_ctrl": fields.get("wifi_connect_ping.supplicant_global_ctrl", ""),
        "supplicant_strace_enabled": fields.get("wifi_connect_ping.supplicant_strace.enabled") == "1",
        "supplicant_strace_output": fields.get("wifi_connect_ping.supplicant_strace.output", ""),
        "supplicant_include_direct_interface": fields.get("wifi_connect_ping.supplicant_include_direct_interface") == "1",
        "supplicant_preexec_path": field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.path"),
        "supplicant_preexec_path_access_x": field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.path_access_x") == "1",
        "supplicant_preexec_path_access_errno": intish(field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.path_access_errno")),
        "supplicant_preexec_loader_access_x": field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.loader_access_x") == "1",
        "supplicant_preexec_loader_access_errno": intish(field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.loader_access_errno")),
        "supplicant_preexec_binary_access_x": field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.binary_access_x") == "1",
        "supplicant_preexec_binary_access_errno": intish(field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.binary_access_errno")),
        "supplicant_preexec_busybox_access_x": field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.busybox_access_x") == "1",
        "supplicant_preexec_busybox_access_errno": intish(field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.busybox_access_errno")),
        "supplicant_preexec_dev_urandom_access_r": field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.dev_urandom_access_r") == "1",
        "supplicant_preexec_dev_urandom_access_errno": intish(field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.dev_urandom_access_errno")),
        "supplicant_preexec_dev_urandom_mode": field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.dev_urandom.mode"),
        "supplicant_preexec_dev_urandom_rdev_major": intish(field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.dev_urandom.rdev_major")),
        "supplicant_preexec_dev_urandom_rdev_minor": intish(field_or_embedded_sample(fields, "wifi_connect_ping.supplicant_preexec.dev_urandom.rdev_minor")),
        "hwservicemanager_started": fields.get("wifi_connect_ping.hwservicemanager_started") == "1",
        "hwservicemanager_start_mode": fields.get("wifi_connect_ping.hwservicemanager_start_mode", ""),
        "hwservicemanager_pid": intish(fields.get("wifi_connect_ping.hwservicemanager_pid")),
        "supplicant_hidl_add_interface_rc": intish(fields.get("wifi_connect_ping.supplicant_hidl_add_interface_rc")),
        "supplicant_hidl_add_interface_result": fields.get("supplicant_hidl_add_interface.result", ""),
        "supplicant_hidl_add_interface_reason": fields.get("supplicant_hidl_add_interface.reason", ""),
        "supplicant_hidl_add_interface_service_found": fields.get("supplicant_hidl_add_interface.service_handle_found") == "1",
        "supplicant_hidl_add_interface_service_descriptor": fields.get("supplicant_hidl_add_interface.service_descriptor", ""),
        "supplicant_hidl_add_interface_service_instance": fields.get("supplicant_hidl_add_interface.service_instance", ""),
        "supplicant_hidl_add_interface_status_name": fields.get("supplicant_hidl_add_interface.status_name", ""),
        "supplicant_hidl_add_interface_transaction_ok": fields.get("supplicant_hidl_add_interface.transaction_ok") == "1",
        "supplicant_hidl_add_interface_iface_handle_found": fields.get("supplicant_hidl_add_interface.iface_handle_found") == "1",
        "supplicant_hidl_vendor_service_found": fields.get("supplicant_hidl_vendor_service_probe.any_found") == "1",
        "supplicant_hidl_vendor_service_descriptor": fields.get("supplicant_hidl_vendor_service_probe.first_descriptor", ""),
        "supplicant_hidl_vendor_service_instance": fields.get("supplicant_hidl_vendor_service_probe.first_instance", ""),
        "android_socket_wpa_wlan0_path": fields.get("wifi_connect_ping.android_socket_wpa_wlan0.path", ""),
        "android_socket_wpa_wlan0_mode": fields.get("wifi_connect_ping.android_socket_wpa_wlan0.mode", ""),
        "android_socket_wpa_wlan0_fd": intish(fields.get("wifi_connect_ping.android_socket_wpa_wlan0.fd")),
        "android_socket_wpa_wlan0_errno": intish(fields.get("wifi_connect_ping.android_socket_wpa_wlan0.errno")),
        "supplicant_alive_after_start": fields.get("wifi_connect_ping.supplicant_alive_after_start") == "1",
        "supplicant_zombie_after_ctrl_wait": fields.get("wifi_connect_ping.supplicant_zombie_after_ctrl_wait") == "1",
        "supplicant_proc_state_after_start": fields.get("wifi_connect_ping.supplicant_proc_state_after_start", ""),
        "supplicant_alive_after_carrier_wait": fields.get("wifi_connect_ping.supplicant_alive_after_carrier_wait") == "1",
        "supplicant_proc_state_after_carrier_wait": fields.get("wifi_connect_ping.supplicant_proc_state_after_carrier_wait", ""),
        "supplicant_proc_start_comm": fields.get("wifi_connect_ping.supplicant_proc_after_start.comm", ""),
        "supplicant_proc_start_exe": fields.get("wifi_connect_ping.supplicant_proc_after_start.exe_basename", ""),
        "supplicant_proc_start_has_wpa": fields.get("wifi_connect_ping.supplicant_proc_after_start.cmdline_has_wpa_supplicant") == "1",
        "supplicant_proc_start_has_helper": fields.get("wifi_connect_ping.supplicant_proc_after_start.cmdline_has_execns_probe") == "1",
        "supplicant_proc_start_has_config": fields.get("wifi_connect_ping.supplicant_proc_after_start.cmdline_has_connect_config") == "1",
        "supplicant_proc_hidl_add_fd_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_hidl_add.fd_count")),
        "supplicant_proc_hidl_add_fd_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_hidl_add.fd_socket_count")),
        "supplicant_proc_hidl_add_fd_netlink_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_hidl_add.fd_netlink_count")),
        "supplicant_proc_hidl_add_fd_generic_netlink_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_hidl_add.fd_generic_netlink_count")),
        "supplicant_proc_hidl_add_fd_wpa_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_hidl_add.fd_wpa_socket_count")),
        "supplicant_proc_carrier_comm": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.comm", ""),
        "supplicant_proc_carrier_exe": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.exe_basename", ""),
        "supplicant_proc_carrier_has_wpa": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.cmdline_has_wpa_supplicant") == "1",
        "supplicant_proc_carrier_has_helper": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.cmdline_has_execns_probe") == "1",
        "supplicant_proc_carrier_has_config": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.cmdline_has_connect_config") == "1",
        "supplicant_log_present": fields.get("wifi_connect_ping.supplicant_log.present") == "1",
        "supplicant_log_size": intish(fields.get("wifi_connect_ping.supplicant_log.size")),
        "supplicant_log_lines": intish(fields.get("wifi_connect_ping.supplicant_log.lines")),
        "supplicant_log_ctrl_iface": intish(fields.get("wifi_connect_ping.supplicant_log.ctrl_iface")),
        "supplicant_log_ctrl_iface_error": intish(fields.get("wifi_connect_ping.supplicant_log.ctrl_iface_error")),
        "supplicant_log_nl80211": intish(fields.get("wifi_connect_ping.supplicant_log.nl80211")),
        "supplicant_log_scan": intish(fields.get("wifi_connect_ping.supplicant_log.scan")),
        "supplicant_log_auth": intish(fields.get("wifi_connect_ping.supplicant_log.auth")),
        "supplicant_log_assoc": intish(fields.get("wifi_connect_ping.supplicant_log.assoc")),
        "supplicant_log_connected": intish(fields.get("wifi_connect_ping.supplicant_log.connected")),
        "supplicant_log_disconnected": intish(fields.get("wifi_connect_ping.supplicant_log.disconnected")),
        "supplicant_log_fail": intish(fields.get("wifi_connect_ping.supplicant_log.fail")),
        "supplicant_log_permission": intish(fields.get("wifi_connect_ping.supplicant_log.permission")),
        "supplicant_log_avc": intish(fields.get("wifi_connect_ping.supplicant_log.avc")),
        "supplicant_log_sample_count": intish(fields.get("wifi_connect_ping.supplicant_log.sample_count")),
        "supplicant_log_tail_sample_count": intish(fields.get("wifi_connect_ping.supplicant_log.tail_sample_count")),
        "supplicant_log_nonproperty_sample_count": intish(fields.get("wifi_connect_ping.supplicant_log.nonproperty_sample_count")),
        "supplicant_log_sensitive_sample_skipped": intish(fields.get("wifi_connect_ping.supplicant_log.sensitive_sample_skipped")),
        "supplicant_log_samples": [
            fields.get(f"wifi_connect_ping.supplicant_log.sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.supplicant_log.sample_{index:02d}", "")
        ],
        "supplicant_log_tail_samples": [
            fields.get(f"wifi_connect_ping.supplicant_log.tail_sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.supplicant_log.tail_sample_{index:02d}", "")
        ],
        "supplicant_log_nonproperty_samples": [
            fields.get(f"wifi_connect_ping.supplicant_log.nonproperty_sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.supplicant_log.nonproperty_sample_{index:02d}", "")
        ],
        "supplicant_stdio_present": fields.get("wifi_connect_ping.supplicant_stdio.present") == "1",
        "supplicant_stdio_size": intish(fields.get("wifi_connect_ping.supplicant_stdio.size")),
        "supplicant_stdio_lines": intish(fields.get("wifi_connect_ping.supplicant_stdio.lines")),
        "supplicant_stdio_ctrl_iface": intish(fields.get("wifi_connect_ping.supplicant_stdio.ctrl_iface")),
        "supplicant_stdio_ctrl_iface_error": intish(fields.get("wifi_connect_ping.supplicant_stdio.ctrl_iface_error")),
        "supplicant_stdio_config_error": intish(fields.get("wifi_connect_ping.supplicant_stdio.config_error")),
        "supplicant_stdio_nl80211": intish(fields.get("wifi_connect_ping.supplicant_stdio.nl80211")),
        "supplicant_stdio_scan": intish(fields.get("wifi_connect_ping.supplicant_stdio.scan")),
        "supplicant_stdio_auth": intish(fields.get("wifi_connect_ping.supplicant_stdio.auth")),
        "supplicant_stdio_assoc": intish(fields.get("wifi_connect_ping.supplicant_stdio.assoc")),
        "supplicant_stdio_connected": intish(fields.get("wifi_connect_ping.supplicant_stdio.connected")),
        "supplicant_stdio_disconnected": intish(fields.get("wifi_connect_ping.supplicant_stdio.disconnected")),
        "supplicant_stdio_fail": intish(fields.get("wifi_connect_ping.supplicant_stdio.fail")),
        "supplicant_stdio_usage": intish(fields.get("wifi_connect_ping.supplicant_stdio.usage")),
        "supplicant_stdio_interface": intish(fields.get("wifi_connect_ping.supplicant_stdio.interface")),
        "supplicant_stdio_socket": intish(fields.get("wifi_connect_ping.supplicant_stdio.socket")),
        "supplicant_stdio_terminate": intish(fields.get("wifi_connect_ping.supplicant_stdio.terminate")),
        "supplicant_stdio_permission": intish(fields.get("wifi_connect_ping.supplicant_stdio.permission")),
        "supplicant_stdio_avc": intish(fields.get("wifi_connect_ping.supplicant_stdio.avc")),
        "supplicant_stdio_sample_count": intish(fields.get("wifi_connect_ping.supplicant_stdio.sample_count")),
        "supplicant_stdio_tail_sample_count": intish(fields.get("wifi_connect_ping.supplicant_stdio.tail_sample_count")),
        "supplicant_stdio_nonproperty_sample_count": intish(fields.get("wifi_connect_ping.supplicant_stdio.nonproperty_sample_count")),
        "supplicant_stdio_sensitive_sample_skipped": intish(fields.get("wifi_connect_ping.supplicant_stdio.sensitive_sample_skipped")),
        "supplicant_stdio_samples": [
            fields.get(f"wifi_connect_ping.supplicant_stdio.sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.supplicant_stdio.sample_{index:02d}", "")
        ],
        "supplicant_stdio_tail_samples": [
            fields.get(f"wifi_connect_ping.supplicant_stdio.tail_sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.supplicant_stdio.tail_sample_{index:02d}", "")
        ],
        "supplicant_stdio_nonproperty_samples": [
            fields.get(f"wifi_connect_ping.supplicant_stdio.nonproperty_sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.supplicant_stdio.nonproperty_sample_{index:02d}", "")
        ],
        "supplicant_proc_start_uid": fields.get("wifi_connect_ping.supplicant_proc_after_start.status_uid", ""),
        "supplicant_proc_start_gid": fields.get("wifi_connect_ping.supplicant_proc_after_start.status_gid", ""),
        "supplicant_proc_start_groups": fields.get("wifi_connect_ping.supplicant_proc_after_start.status_groups", ""),
        "supplicant_proc_start_wchan": fields.get("wifi_connect_ping.supplicant_proc_after_start.wchan", ""),
        "supplicant_proc_start_syscall": fields.get("wifi_connect_ping.supplicant_proc_after_start.syscall", ""),
        "supplicant_proc_start_stack_first": fields.get("wifi_connect_ping.supplicant_proc_after_start.stack_first", ""),
        "supplicant_proc_start_fd_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_count")),
        "supplicant_proc_start_fd_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_socket_count")),
        "supplicant_proc_start_fd_netlink_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_netlink_count")),
        "supplicant_proc_start_fd_generic_netlink_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_generic_netlink_count")),
        "supplicant_proc_start_fd_netlink_lookup_miss": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_netlink_lookup_miss")),
        "supplicant_proc_start_fd_wpa_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_wpa_socket_count")),
        "supplicant_proc_start_fd_stdio_log_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_stdio_log_count")),
        "supplicant_proc_start_fd_samples": [
            fields.get(f"wifi_connect_ping.supplicant_proc_after_start.fd_sample_{index:02d}", "")
            for index in range(16)
            if fields.get(f"wifi_connect_ping.supplicant_proc_after_start.fd_sample_{index:02d}", "")
        ],
        "supplicant_proc_carrier_uid": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.status_uid", ""),
        "supplicant_proc_carrier_gid": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.status_gid", ""),
        "supplicant_proc_carrier_groups": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.status_groups", ""),
        "supplicant_proc_carrier_wchan": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.wchan", ""),
        "supplicant_proc_carrier_syscall": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.syscall", ""),
        "supplicant_proc_carrier_stack_first": fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.stack_first", ""),
        "supplicant_proc_carrier_fd_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_count")),
        "supplicant_proc_carrier_fd_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_socket_count")),
        "supplicant_proc_carrier_fd_netlink_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_netlink_count")),
        "supplicant_proc_carrier_fd_generic_netlink_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_generic_netlink_count")),
        "supplicant_proc_carrier_fd_netlink_lookup_miss": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_netlink_lookup_miss")),
        "supplicant_proc_carrier_fd_wpa_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_wpa_socket_count")),
        "supplicant_proc_carrier_fd_stdio_log_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_stdio_log_count")),
        "supplicant_proc_carrier_fd_samples": [
            fields.get(f"wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_sample_{index:02d}", "")
            for index in range(16)
            if fields.get(f"wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_sample_{index:02d}", "")
        ],
        "kmsg_stream_started": fields.get("wifi_connect_ping.kmsg_stream.started") == "1",
        "kmsg_stream_start_errno": intish(fields.get("wifi_connect_ping.kmsg_stream.start_errno")),
        "kmsg_stream_cleanup_exit": intish(fields.get("wifi_connect_ping.kmsg_stream.cleanup_exit")),
        "kmsg_stream_cleanup_signal": intish(fields.get("wifi_connect_ping.kmsg_stream.cleanup_signal")),
        "kmsg_stream_cleanup_timeout": fields.get("wifi_connect_ping.kmsg_stream.cleanup_timeout") == "1",
        "kmsg_stream_present": fields.get("wifi_connect_ping.kmsg_stream.present") == "1",
        "kmsg_stream_size": intish(fields.get("wifi_connect_ping.kmsg_stream.size")),
        "kmsg_stream_lines": intish(fields.get("wifi_connect_ping.kmsg_stream.lines")),
        "kmsg_stream_permission": intish(fields.get("wifi_connect_ping.kmsg_stream.permission")),
        "kmsg_stream_avc": intish(fields.get("wifi_connect_ping.kmsg_stream.avc")),
        "kmsg_stream_nl80211": intish(fields.get("wifi_connect_ping.kmsg_stream.nl80211")),
        "kmsg_stream_auth": intish(fields.get("wifi_connect_ping.kmsg_stream.auth")),
        "kmsg_stream_assoc": intish(fields.get("wifi_connect_ping.kmsg_stream.assoc")),
        "kmsg_stream_fail": intish(fields.get("wifi_connect_ping.kmsg_stream.fail")),
        "kmsg_stream_sensitive_sample_skipped": intish(fields.get("wifi_connect_ping.kmsg_stream.sensitive_sample_skipped")),
        "kmsg_stream_samples": [
            fields.get(f"wifi_connect_ping.kmsg_stream.sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.kmsg_stream.sample_{index:02d}", "")
        ],
        "kmsg_stream_tail_samples": [
            fields.get(f"wifi_connect_ping.kmsg_stream.tail_sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.kmsg_stream.tail_sample_{index:02d}", "")
        ],
        "logdw_sink_started": fields.get("wifi_connect_ping.logdw_sink.started") == "1",
        "logdw_sink_errno": intish(fields.get("wifi_connect_ping.logdw_sink.errno")),
        "logdw_sink_drain_errno": intish(fields.get("wifi_connect_ping.logdw_sink.drain_errno")),
        "logdw_sink_datagrams": intish(fields.get("wifi_connect_ping.logdw_sink.datagrams")),
        "logdw_sink_bytes": intish(fields.get("wifi_connect_ping.logdw_sink.bytes")),
        "logdw_sink_wpa": intish(fields.get("wifi_connect_ping.logdw_sink.wpa")),
        "logdw_sink_supplicant": intish(fields.get("wifi_connect_ping.logdw_sink.supplicant")),
        "logdw_sink_nl80211": intish(fields.get("wifi_connect_ping.logdw_sink.nl80211")),
        "logdw_sink_ctrl": intish(fields.get("wifi_connect_ping.logdw_sink.ctrl")),
        "logdw_sink_interface": intish(fields.get("wifi_connect_ping.logdw_sink.interface")),
        "logdw_sink_fail": intish(fields.get("wifi_connect_ping.logdw_sink.fail")),
        "logdw_sink_permission": intish(fields.get("wifi_connect_ping.logdw_sink.permission")),
        "logdw_sink_hidl": intish(fields.get("wifi_connect_ping.logdw_sink.hidl")),
        "logdw_sink_service_manager": intish(fields.get("wifi_connect_ping.logdw_sink.service_manager")),
        "logdw_sink_sample_count": intish(fields.get("wifi_connect_ping.logdw_sink.sample_count")),
        "logdw_sink_sensitive_sample_skipped": intish(fields.get("wifi_connect_ping.logdw_sink.sensitive_sample_skipped")),
        "logdw_sink_samples": [
            fields.get(f"wifi_connect_ping.logdw_sink.sample_{index:02d}", "")
            for index in range(24)
            if fields.get(f"wifi_connect_ping.logdw_sink.sample_{index:02d}", "")
        ],
        "no_raw": no_raw,
        "result_source": result.get("result_source", ""),
        "serial_attempt_count": intish(result.get("serial_attempt_count")),
        "result_left_on_device": bool(result.get("result_left_on_device")),
        "fast_upload_ok": bool(fast_upload.get("ok")),
        "fast_upload_reason": str(fast_upload.get("reason") or ""),
        "fast_upload_elapsed_sec": fast_upload.get("elapsed_sec", ""),
        "fast_upload_archive_path": str(fast_upload.get("archive_path") or ""),
        "fast_upload_archive_bytes": intish(fast_upload_validation.get("bytes")),
        "fast_upload_archive_sha256": str(fast_upload_validation.get("sha256") or ""),
        "fast_upload_receiver_bytes": intish(fast_upload_receiver.get("bytes")),
        "fast_upload_entry_count": len(fast_upload_validation.get("entries") or []),
        "fast_upload_forbidden_entries": fast_upload_validation.get("forbidden_entries") or [],
        "fast_upload_secret_hits": fast_upload_validation.get("secret_hits") or [],
        "cleanup_ok": bool(result.get("cleanup_ok")),
        "cleanup_skipped_reason": str(result.get("cleanup_skipped_reason") or ""),
    }


def render_report(manifest: dict[str, Any]) -> str:
    gate = manifest["connect_ping_gate"]
    helper = manifest.get("helper_build") or {}
    standalone_wpa = manifest.get("standalone_wpa_archive") or {}
    standalone_wpa_stage = manifest.get("standalone_wpa_stage") or {}
    property_archive = manifest.get("property_archive") or {}
    property_stage = manifest.get("property_stage") or {}
    config = manifest.get("config_stage") or {}
    steps = manifest["steps"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['stdout_file']}`"
        for step in steps
    ]
    supplicant_log_sample_lines = [
        f"- `log_sample_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_log_samples", []))
    ]
    supplicant_log_tail_sample_lines = [
        f"- `log_tail_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_log_tail_samples", []))
    ]
    supplicant_log_nonproperty_sample_lines = [
        f"- `log_nonproperty_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_log_nonproperty_samples", []))
    ]
    supplicant_stdio_sample_lines = [
        f"- `sample_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_stdio_samples", []))
    ]
    supplicant_stdio_tail_sample_lines = [
        f"- `tail_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_stdio_tail_samples", []))
    ]
    supplicant_stdio_nonproperty_sample_lines = [
        f"- `nonproperty_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_stdio_nonproperty_samples", []))
    ]
    kmsg_sample_lines = [
        f"- `kmsg_sample_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("kmsg_stream_samples", []))
    ]
    kmsg_tail_sample_lines = [
        f"- `kmsg_tail_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("kmsg_stream_tail_samples", []))
    ]
    logdw_sample_lines = [
        f"- `logdw_sample_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("logdw_sink_samples", []))
    ]
    hold_sample_lines = [
        (
            f"- `hold_sample_{sample['index']:02d}` t_ms `{sample['elapsed_ms']}` "
            f"carrier `{sample['carrier']}` route `{sample['route_default']}/{sample['route_gateway']}` err `{sample['route_errno']}` "
            f"arp `{sample['arp_before_present']}:{sample['arp_before_complete']}->{sample['arp_after_present']}:{sample['arp_after_complete']}` "
            f"gw `{sample['gateway_ping_classifier']}` ip `{sample['ip_ping_classifier']}` host `{sample['host_ping_classifier']}` "
            f"stats `{sample['stats_before_ok']}/{sample['stats_after_ok']}` "
            f"pkt_delta rx/tx `{sample['rx_packets_delta']}/{sample['tx_packets_delta']}` "
            f"err_drop `{sample['rx_errors_delta']}/{sample['tx_errors_delta']}/{sample['rx_dropped_delta']}/{sample['tx_dropped_delta']}` "
            f"wpa `{sample['wpa_state']}` rc `{sample['wpa_status_rc']}` freq `{sample['wpa_freq_mhz']}` "
            f"sig `{sample['signal_rssi_dbm']}/{sample['signal_linkspeed_mbps']}` rc `{sample['signal_poll_rc']}` "
            f"power `{sample['power_class']}/{sample['power_device']}/{sample['driver_power_state']}` "
            f"owners cnss/pm/per/wifi/ipacm `{sample['cnss_daemon_count']}/{sample['pm_service_count']}/{sample['per_mgr_count']}/{sample['wifi_hal_count']}/{sample['ipacm_count']}` "
            f"fds ipa/subsys_modem `{sample['fd_dev_ipa_count']}/{sample['fd_subsys_modem_count']}` "
            f"icnss `{sample['icnss_runtime_status']}/{sample['wlan0_device_runtime_status']}` "
            f"wlanpd `{sample['wlan_pd_seen']}:{sample['wlan_pd_state']}:{sample['wlan_pd_crash_count']}` "
            f"modem `{sample['modem_seen']}:{sample['modem_state']}`"
        )
        for sample in gate.get("hold_sample_details", [])
    ]
    phase_timer_lines = [
        f"- `{item.get('name', '')}` elapsed `{item.get('elapsed_sec', 0)}` ok `{item.get('ok', False)}` detail `{item.get('detail', '')}`"
        for item in manifest.get("phase_timers", [])
    ]
    step_phase_order = [
        "preflight_device",
        "helper_stage",
        "connect_config_stage",
        "flash_total",
        "connect_window",
        "artifact_upload",
        "rollback_flash_total",
        "rollback_status",
        "selftest",
        "other",
    ]
    step_phase_summary = manifest.get("step_phase_summary", {})
    step_phase_lines = [
        (
            f"- `{name}` elapsed `{step_phase_summary.get(name, {}).get('elapsed_sec', 0)}` "
            f"steps `{step_phase_summary.get(name, {}).get('step_count', 0)}` "
            f"slow `{render_slow_step_refs(step_phase_summary.get(name, {}).get('slow_steps', []))}`"
        )
        for name in step_phase_order
        if name in step_phase_summary
    ]
    native_flash_phase_lines = [
        f"- `{item.get('step', '')}.{item.get('name', '')}` elapsed `{item.get('elapsed_sec', 0)}` ok `{item.get('ok', False)}`"
        for item in manifest.get("native_init_flash_phase_timers", [])
    ]
    slow_step_lines = [
        f"- `{item.get('name', '')}` elapsed `{item.get('elapsed_sec', 0)}` ok `{item.get('ok', False)}` timeout `{item.get('timeout', False)}`"
        for item in manifest.get("slow_steps", [])
    ]
    supplicant_start_fd_lines = [
        f"- `start_fd_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_proc_start_fd_samples", []))
    ]
    supplicant_wait_fd_lines = [
        f"- `wait_fd_{index:02d}`: `{sample}`"
        for index, sample in enumerate(gate.get("supplicant_proc_carrier_fd_samples", []))
    ]
    return "\n".join([
        "# Native Init V2167 Connect DHCP Google Ping Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2167`",
        f"- Run label: `{manifest.get('run_label', RUN_LABEL)}`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- QA hold config: sec `{manifest.get('qa_hold_config', {}).get('hold_sec', 0)}` interval `{manifest.get('qa_hold_config', {}).get('hold_interval_sec', 0)}` reconnect_on_drop `{manifest.get('qa_hold_config', {}).get('reconnect_on_drop', False)}` force_power_on `{manifest.get('qa_hold_config', {}).get('force_power_on', False)}`",
        f"- Result source: `{gate['result_source']}` serial_attempts `{gate['serial_attempt_count']}` result_left_on_device `{gate['result_left_on_device']}`",
        f"- Fast upload: ok `{gate['fast_upload_ok']}` reason `{gate['fast_upload_reason']}` elapsed `{gate['fast_upload_elapsed_sec']}`",
        f"- Fast upload archive: `{gate['fast_upload_archive_path']}` bytes `{gate['fast_upload_archive_bytes']}` receiver_bytes `{gate['fast_upload_receiver_bytes']}` entries `{gate['fast_upload_entry_count']}` secret_hits `{gate['fast_upload_secret_hits']}` forbidden_entries `{gate['fast_upload_forbidden_entries']}`",
        "",
        "## Phase Timers",
        "",
        *phase_timer_lines,
        *([] if phase_timer_lines else ["- `explicit`: `none`"]),
        "",
        "## Step Phase Summary",
        "",
        *step_phase_lines,
        *([] if step_phase_lines else ["- `step_phase_summary`: `none`"]),
        "",
        "## Native Flash Subphases",
        "",
        *native_flash_phase_lines,
        *([] if native_flash_phase_lines else ["- `native_init_flash`: `no phase markers in this run`"]),
        "",
        "## Slowest Steps",
        "",
        *slow_step_lines,
        *([] if slow_step_lines else ["- `slow_steps`: `none`"]),
        "",
        "## Gate Results",
        "",
        f"- `wlan0_seen`: `{gate['wlan0_seen']}` helper_invoked `{gate['helper_invoked']}` helper_rc `{gate['helper_rc']}`",
        f"- `executor_result`: `{gate['executor_result']}`",
        f"- `association_carrier`: `{gate['association_carrier']}` errno `{gate['association_carrier_errno']}`",
        f"- `country`: `{gate['country_code']}` driver_ioctl_rc `{gate['driver_ioctl_country_rc']}` errno `{gate['driver_ioctl_country_errno']}` readback `{gate['driver_ioctl_getcountry_readback']}` get_rc `{gate['driver_ioctl_getcountry_rc']}`",
        f"- `wpa_ctrl`: ready `{gate['wpa_ctrl_ready']}` surface `{gate['wpa_ctrl_surface']}` global_path `{gate['wpa_ctrl_global_path']}` abstract `{gate['wpa_ctrl_global_abstract']}` preclean `{gate['wpa_ctrl_global_preclean_path']}` preclean_errno `{gate['wpa_ctrl_global_preclean_errno']}` ping `{gate['wpa_ctrl_ping_reply']}` interface_add_rc `{gate['interface_add_rc']}` interface_add `{gate['interface_add_reply']}` after_add_ready `{gate['wpa_ctrl_after_interface_add_ready']}` after_add_surface `{gate['wpa_ctrl_after_interface_add_surface']}` after_add_global `{gate['wpa_ctrl_after_interface_add_global_path']}` after_add_ping `{gate['wpa_ctrl_after_interface_add_ping']}` country_rc `{gate['driver_country_rc']}` reply `{gate['driver_country_reply']}` enable `{gate['enable_network_reply']}` reassociate `{gate['reassociate_reply']}`",
        f"- `wpa_ctrl_path`: dir `{gate['wpa_ctrl_dir']}` interface `{gate['wpa_ctrl_interface_path']}`",
        f"- `supplicant`: launch `{gate['supplicant_launch_mode']}` driver `{gate['supplicant_driver']}` global_ctrl `{gate['supplicant_global_ctrl']}` direct_iface `{gate['supplicant_include_direct_interface']}` strace `{gate['supplicant_strace_enabled']}` strace_output `{gate['supplicant_strace_output']}` android_socket_mode `{gate['android_socket_wpa_wlan0_mode']}` android_socket_fd `{gate['android_socket_wpa_wlan0_fd']}` android_socket_errno `{gate['android_socket_wpa_wlan0_errno']}` alive_start `{gate['supplicant_alive_after_start']}` state_start `{gate['supplicant_proc_state_after_start']}` zombie_after_ctrl `{gate['supplicant_zombie_after_ctrl_wait']}` alive_after_carrier_wait `{gate['supplicant_alive_after_carrier_wait']}` state_after_carrier_wait `{gate['supplicant_proc_state_after_carrier_wait']}`",
        f"- `supplicant_preexec`: path `{gate['supplicant_preexec_path']}` path_x `{gate['supplicant_preexec_path_access_x']}` path_errno `{gate['supplicant_preexec_path_access_errno']}` loader_x `{gate['supplicant_preexec_loader_access_x']}` loader_errno `{gate['supplicant_preexec_loader_access_errno']}` binary_x `{gate['supplicant_preexec_binary_access_x']}` binary_errno `{gate['supplicant_preexec_binary_access_errno']}` busybox_x `{gate['supplicant_preexec_busybox_access_x']}` busybox_errno `{gate['supplicant_preexec_busybox_access_errno']}` urandom_r `{gate['supplicant_preexec_dev_urandom_access_r']}` urandom_errno `{gate['supplicant_preexec_dev_urandom_access_errno']}` urandom_mode `{gate['supplicant_preexec_dev_urandom_mode']}` urandom_rdev `{gate['supplicant_preexec_dev_urandom_rdev_major']}:{gate['supplicant_preexec_dev_urandom_rdev_minor']}`",
        f"- `standalone_wpa`: enabled `{gate['standalone_wpa_stage_enabled']}` staged `{gate['standalone_wpa_stage_ok']}` reason `{gate['standalone_wpa_stage_reason']}` wrapper `{gate['standalone_wpa_stage_remote_wrapper']}` packages `{gate['standalone_wpa_stage_package_count']}` version_rc `{gate['standalone_wpa_stage_version_rc']}` version `{gate['standalone_wpa_stage_version_sample']}`",
        f"- `supplicant_hidl`: hwservicemanager_started `{gate['hwservicemanager_started']}` mode `{gate['hwservicemanager_start_mode']}` pid `{gate['hwservicemanager_pid']}` add_rc `{gate['supplicant_hidl_add_interface_rc']}` service_found `{gate['supplicant_hidl_add_interface_service_found']}` descriptor `{gate['supplicant_hidl_add_interface_service_descriptor']}` instance `{gate['supplicant_hidl_add_interface_service_instance']}` transaction_ok `{gate['supplicant_hidl_add_interface_transaction_ok']}` status `{gate['supplicant_hidl_add_interface_status_name']}` iface_handle `{gate['supplicant_hidl_add_interface_iface_handle_found']}` result `{gate['supplicant_hidl_add_interface_result']}` reason `{gate['supplicant_hidl_add_interface_reason']}` after_add_fd `{gate['supplicant_proc_hidl_add_fd_count']}` after_add_netlink `{gate['supplicant_proc_hidl_add_fd_netlink_count']}` after_add_genl `{gate['supplicant_proc_hidl_add_fd_generic_netlink_count']}`",
        f"- `supplicant_hidl_vendor`: service_found `{gate['supplicant_hidl_vendor_service_found']}` descriptor `{gate['supplicant_hidl_vendor_service_descriptor']}` instance `{gate['supplicant_hidl_vendor_service_instance']}`",
        f"- `supplicant_proc_start`: comm `{gate['supplicant_proc_start_comm']}` exe `{gate['supplicant_proc_start_exe']}` has_wpa `{gate['supplicant_proc_start_has_wpa']}` has_helper `{gate['supplicant_proc_start_has_helper']}` has_config `{gate['supplicant_proc_start_has_config']}`",
        f"- `supplicant_proc_start_runtime`: uid `{gate['supplicant_proc_start_uid']}` gid `{gate['supplicant_proc_start_gid']}` groups `{gate['supplicant_proc_start_groups']}` wchan `{gate['supplicant_proc_start_wchan']}` syscall `{gate['supplicant_proc_start_syscall']}` stack `{gate['supplicant_proc_start_stack_first']}` fd_count `{gate['supplicant_proc_start_fd_count']}` socket_fds `{gate['supplicant_proc_start_fd_socket_count']}` netlink_fds `{gate['supplicant_proc_start_fd_netlink_count']}` generic_netlink_fds `{gate['supplicant_proc_start_fd_generic_netlink_count']}` netlink_miss `{gate['supplicant_proc_start_fd_netlink_lookup_miss']}` wpa_socket_fds `{gate['supplicant_proc_start_fd_wpa_socket_count']}` stdio_fds `{gate['supplicant_proc_start_fd_stdio_log_count']}`",
        f"- `supplicant_proc_after_wait`: comm `{gate['supplicant_proc_carrier_comm']}` exe `{gate['supplicant_proc_carrier_exe']}` has_wpa `{gate['supplicant_proc_carrier_has_wpa']}` has_helper `{gate['supplicant_proc_carrier_has_helper']}` has_config `{gate['supplicant_proc_carrier_has_config']}`",
        f"- `supplicant_proc_after_wait_runtime`: uid `{gate['supplicant_proc_carrier_uid']}` gid `{gate['supplicant_proc_carrier_gid']}` groups `{gate['supplicant_proc_carrier_groups']}` wchan `{gate['supplicant_proc_carrier_wchan']}` syscall `{gate['supplicant_proc_carrier_syscall']}` stack `{gate['supplicant_proc_carrier_stack_first']}` fd_count `{gate['supplicant_proc_carrier_fd_count']}` socket_fds `{gate['supplicant_proc_carrier_fd_socket_count']}` netlink_fds `{gate['supplicant_proc_carrier_fd_netlink_count']}` generic_netlink_fds `{gate['supplicant_proc_carrier_fd_generic_netlink_count']}` netlink_miss `{gate['supplicant_proc_carrier_fd_netlink_lookup_miss']}` wpa_socket_fds `{gate['supplicant_proc_carrier_fd_wpa_socket_count']}` stdio_fds `{gate['supplicant_proc_carrier_fd_stdio_log_count']}`",
        f"- `supplicant_log`: present `{gate['supplicant_log_present']}` size `{gate['supplicant_log_size']}` lines `{gate['supplicant_log_lines']}` ctrl `{gate['supplicant_log_ctrl_iface']}` ctrl_err `{gate['supplicant_log_ctrl_iface_error']}` nl80211 `{gate['supplicant_log_nl80211']}` scan `{gate['supplicant_log_scan']}` auth `{gate['supplicant_log_auth']}` assoc `{gate['supplicant_log_assoc']}` connected `{gate['supplicant_log_connected']}` disconnected `{gate['supplicant_log_disconnected']}` fail `{gate['supplicant_log_fail']}` permission `{gate['supplicant_log_permission']}` avc `{gate['supplicant_log_avc']}` samples `{gate['supplicant_log_sample_count']}` tail_samples `{gate['supplicant_log_tail_sample_count']}` nonproperty_samples `{gate['supplicant_log_nonproperty_sample_count']}` sensitive_skipped `{gate['supplicant_log_sensitive_sample_skipped']}`",
        f"- `supplicant_stdio`: present `{gate['supplicant_stdio_present']}` size `{gate['supplicant_stdio_size']}` lines `{gate['supplicant_stdio_lines']}` ctrl `{gate['supplicant_stdio_ctrl_iface']}` ctrl_err `{gate['supplicant_stdio_ctrl_iface_error']}` config_err `{gate['supplicant_stdio_config_error']}` nl80211 `{gate['supplicant_stdio_nl80211']}` scan `{gate['supplicant_stdio_scan']}` auth `{gate['supplicant_stdio_auth']}` assoc `{gate['supplicant_stdio_assoc']}` connected `{gate['supplicant_stdio_connected']}` disconnected `{gate['supplicant_stdio_disconnected']}` fail `{gate['supplicant_stdio_fail']}` usage `{gate['supplicant_stdio_usage']}` interface `{gate['supplicant_stdio_interface']}` socket `{gate['supplicant_stdio_socket']}` terminate `{gate['supplicant_stdio_terminate']}` permission `{gate['supplicant_stdio_permission']}` avc `{gate['supplicant_stdio_avc']}` samples `{gate['supplicant_stdio_sample_count']}` tail_samples `{gate['supplicant_stdio_tail_sample_count']}` nonproperty_samples `{gate['supplicant_stdio_nonproperty_sample_count']}` sensitive_skipped `{gate['supplicant_stdio_sensitive_sample_skipped']}`",
        f"- `logdw_sink`: started `{gate['logdw_sink_started']}` errno `{gate['logdw_sink_errno']}` datagrams `{gate['logdw_sink_datagrams']}` bytes `{gate['logdw_sink_bytes']}` wpa `{gate['logdw_sink_wpa']}` supplicant `{gate['logdw_sink_supplicant']}` nl80211 `{gate['logdw_sink_nl80211']}` ctrl `{gate['logdw_sink_ctrl']}` interface `{gate['logdw_sink_interface']}` fail `{gate['logdw_sink_fail']}` permission `{gate['logdw_sink_permission']}` hidl `{gate['logdw_sink_hidl']}` service_manager `{gate['logdw_sink_service_manager']}` samples `{gate['logdw_sink_sample_count']}` sensitive_skipped `{gate['logdw_sink_sensitive_sample_skipped']}` drain_errno `{gate['logdw_sink_drain_errno']}`",
        f"- `kmsg_stream`: started `{gate['kmsg_stream_started']}` start_errno `{gate['kmsg_stream_start_errno']}` present `{gate['kmsg_stream_present']}` size `{gate['kmsg_stream_size']}` lines `{gate['kmsg_stream_lines']}` permission `{gate['kmsg_stream_permission']}` avc `{gate['kmsg_stream_avc']}` nl80211 `{gate['kmsg_stream_nl80211']}` auth `{gate['kmsg_stream_auth']}` assoc `{gate['kmsg_stream_assoc']}` fail `{gate['kmsg_stream_fail']}` sensitive_skipped `{gate['kmsg_stream_sensitive_sample_skipped']}` cleanup_exit `{gate['kmsg_stream_cleanup_exit']}` signal `{gate['kmsg_stream_cleanup_signal']}` timeout `{gate['kmsg_stream_cleanup_timeout']}`",
        f"- `dhcp_executed`: `{gate['dhcp_executed']}` dhcp_rc `{gate['dhcp_rc']}` resolv_present `{gate['resolv_conf_present']}` resolv_errno `{gate['resolv_conf_errno']}` resolv_size `{gate['resolv_conf_size']}` nameservers `{gate['resolv_conf_nameserver_count']}`",
        f"- `external_ping_executed`: `{gate['external_ping_executed']}` target `{gate['external_ping_target']}` rc `{gate['external_ping_rc']}` classifier `{gate['external_ping_output_classifier']}` output_present `{gate['external_ping_output_present']}` output_errno `{gate['external_ping_output_errno']}` bytes_from `{gate['external_ping_output_bytes_from']}` bad_address `{gate['external_ping_output_bad_address']}` unknown_host `{gate['external_ping_output_unknown_host']}` net_unreach `{gate['external_ping_output_network_unreachable']}` sendto `{gate['external_ping_output_sendto_error']}` zero_recv `{gate['external_ping_output_zero_received']}` loss100 `{gate['external_ping_output_packet_loss_100']}`",
        f"- `force_power_on`: enabled `{gate['force_power_on_enabled']}` executed `{gate['force_power_on_executed']}` reason `{gate['force_power_on_reason']}` class `{gate['force_power_on_class_before']}->{gate['force_power_on_class_after']}` class_rc `{gate['force_power_on_class_write_rc']}` class_errno `{gate['force_power_on_class_write_errno']}` device `{gate['force_power_on_device_before']}->{gate['force_power_on_device_after']}` device_rc `{gate['force_power_on_device_write_rc']}` device_errno `{gate['force_power_on_device_write_errno']}`",
        f"- `modem_holder`: requested `{gate['connect_hold_subsys_modem_requested']}` enabled `{gate['modem_holder_enabled']}` started `{gate['modem_holder_started']}` start_attempted `{gate['modem_holder_start_attempted']}` opened `{gate['modem_holder_opened']}` open_errno `{gate['modem_holder_open_errno']}` pid `{gate['modem_holder_pid']}` stop_attempted `{gate['modem_holder_stop_attempted']}` reaped `{gate['modem_holder_reaped']}` postflight_safe `{gate['modem_holder_postflight_safe']}` esoc0_attempt `{gate['modem_holder_subsys_esoc0_open_attempted']}` esoc_attempt `{gate['modem_holder_esoc_open_attempted']}` forced_rc1 `{gate['modem_holder_forced_rc1_attempted']}`",
        f"- `hold`: enabled `{gate['hold_enabled']}` executed `{gate['hold_executed']}` requested_sec `{gate['hold_requested_sec']}` interval_sec `{gate['hold_interval_sec']}` pass `{gate['hold_pass']}` reason `{gate['hold_reason']}` samples `{gate['hold_samples']}` carrier_up `{gate['hold_carrier_up_count']}` carrier_down `{gate['hold_carrier_down_count']}` host_ping_success `{gate['hold_ping_success_count']}` host_ping_fail `{gate['hold_ping_fail_count']}` ip_ping_success `{gate['hold_ip_ping_success_count']}` ip_ping_fail `{gate['hold_ip_ping_fail_count']}` reconnect_on_drop `{gate['hold_reconnect_on_drop']}` reconnect_attempts `{gate['hold_reconnect_attempt_count']}` reconnect_success `{gate['hold_reconnect_success_count']}` first_fail_sample `{gate['hold_first_fail_sample']}` first_fail_errno `{gate['hold_first_fail_errno']}` first_fail_ping_rc `{gate['hold_first_fail_ping_rc']}`",
        f"- `hold_path_diag`: gateway_ping `{gate['hold_gateway_ping_success_count']}/{gate['hold_gateway_ping_attempt_count']}` gateway_fail `{gate['hold_gateway_ping_fail_count']}` route_default `{gate['hold_route_default_present_count']}` route_gateway `{gate['hold_route_gateway_present_count']}` arp_before `{gate['hold_arp_before_complete_count']}/{gate['hold_arp_before_entry_count']}` arp_after `{gate['hold_arp_after_complete_count']}/{gate['hold_arp_after_entry_count']}`",
        "",
        "## Hold Sample Diagnostics",
        "",
        *hold_sample_lines,
        *([] if hold_sample_lines else ["- `hold_samples`: `none`"]),
        "",
        "## Interface State",
        "",
        f"- `pre_state`: operstate `{gate['pre_operstate']}` carrier `{gate['pre_carrier']}` flags `{gate['pre_flags']}`",
        f"- `post_state`: operstate `{gate['post_operstate']}` carrier `{gate['post_carrier']}` flags `{gate['post_flags']}`",
        f"- `staging`: property `{gate['property_stage_ok']}` helper `{gate['helper_stage_ok']}` standalone_wpa `{gate['standalone_wpa_stage_ok']}` config `{gate['config_ok']}` script `{gate['script_ok']}` wait_complete `{gate['wait_complete']}`",
        f"- `property_root`: remote `{gate['property_stage_remote_root']}` decision `{gate['property_stage_runtime_decision']}` files `{gate['property_stage_file_count']}` property_info_size `{gate['property_stage_property_info_size']}`",
        f"- `no_raw`: `{gate['no_raw']}` secret_values_logged `{gate['secret_values_logged']}`",
        "",
        "## Redacted Supplicant Samples",
        "",
        *supplicant_log_sample_lines,
        *supplicant_log_tail_sample_lines,
        *supplicant_log_nonproperty_sample_lines,
        *([] if supplicant_log_sample_lines or supplicant_log_tail_sample_lines or supplicant_log_nonproperty_sample_lines else ["- `supplicant_log`: `none`"]),
        "",
        "## Redacted Supplicant Stdio Samples",
        "",
        *supplicant_stdio_sample_lines,
        *([] if supplicant_stdio_sample_lines else ["- `none`"]),
        "",
        "## Redacted Supplicant Tail Samples",
        "",
        *supplicant_stdio_tail_sample_lines,
        *([] if supplicant_stdio_tail_sample_lines else ["- `none`"]),
        "",
        "## Redacted Supplicant Non-Property Samples",
        "",
        *supplicant_stdio_nonproperty_sample_lines,
        *([] if supplicant_stdio_nonproperty_sample_lines else ["- `none`"]),
        "",
        "## Redacted Kernel Stream Samples",
        "",
        *logdw_sample_lines,
        *([] if logdw_sample_lines else ["- `logdw`: `none`"]),
        *kmsg_sample_lines,
        *([] if kmsg_sample_lines else ["- `none`"]),
        *kmsg_tail_sample_lines,
        *([] if kmsg_tail_sample_lines else ["- `tail`: `none`"]),
        "",
        "## Supplicant FD Samples",
        "",
        *supplicant_start_fd_lines,
        *([] if supplicant_start_fd_lines else ["- `start`: `none`"]),
        *supplicant_wait_fd_lines,
        *([] if supplicant_wait_fd_lines else ["- `after_wait`: `none`"]),
        "",
        "## Staging",
        "",
        f"- `property_archive`: `{property_archive.get('path', '')}` bytes `{property_archive.get('bytes', 0)}` chunks `{property_archive.get('chunks', 0)}` staged `{property_stage.get('property_stage.ok', '')}` method `{property_stage.get('property_stage.transfer_method', '')}` fast `{property_stage.get('property_stage.fast_transfer_ok', '')}` elapsed `{property_stage.get('property_stage.fast_transfer_elapsed_sec', '')}`",
        f"- `helper_sha256`: `{helper.get('sha256', '')}` gzip_len `{helper.get('gzip_len', 0)}` chunks `{helper.get('chunks', 0)}` method `{manifest.get('helper_stage', {}).get('helper_stage.transfer_method', '')}` fast `{manifest.get('helper_stage', {}).get('helper_stage.fast_transfer_ok', '')}` elapsed `{manifest.get('helper_stage', {}).get('helper_stage.fast_transfer_elapsed_sec', '')}`",
        f"- `strace_stage`: ok `{manifest.get('strace_stage', {}).get('strace_stage.ok', '')}` reason `{manifest.get('strace_stage', {}).get('strace_stage.reason', '')}` fast `{manifest.get('strace_stage', {}).get('strace_stage.fast_transfer_ok', '')}` elapsed `{manifest.get('strace_stage', {}).get('strace_stage.fast_transfer_elapsed_sec', '')}`",
        f"- `standalone_wpa_archive`: ok `{standalone_wpa.get('ok', False)}` bytes `{standalone_wpa.get('bytes', 0)}` sha `{standalone_wpa.get('sha256', '')}` packages `{standalone_wpa.get('package_count', 0)}` staged `{standalone_wpa_stage.get('standalone_wpa_stage.ok', '')}` fast `{standalone_wpa_stage.get('standalone_wpa_stage.fast_transfer_ok', '')}` elapsed `{standalone_wpa_stage.get('standalone_wpa_stage.fast_transfer_elapsed_sec', '')}`",
        f"- `connect_config`: path `{CONNECT_CONFIG}` size `{config.get('connect_config.size', '')}` mode `{config.get('connect_config.mode', '')}` security `{config.get('connect_config.security_mode', '')}` disabled_initially `{config.get('connect_config.network_initially_disabled', '')}` raw_values_logged `0`",
        "",
        "## Scope",
        "",
        f"- This V2167 unit stages a generated private property root at `{PROPERTY_REMOTE_ROOT}` with the wpa_supplicant loader/log lookup keys, adds private `/dev/random` and `/dev/urandom`, creates `/dev/socket/logdw`, launches `wpa_supplicant` direct as `-dd -i wlan0 -D nl80211 -c <config> -O /cache/a90-wifi/sockets -t`, and observes carrier/DHCP/ping. It records redacted supplicant/logdw/kmsg samples plus `/proc` fd/netlink/syscall counters. This target supplicant does not support `-f`, so stdout/stderr plus logdw are the diagnostic logs.",
        "- Allowed actions: start private Wi-Fi active-session surface, start `wpa_supplicant`, run DHCP, set temporary route/DNS, and run bounded gateway/IP/hostname ping probes.",
        "- Outputs are redacted: no SSID, PSK, BSSID, raw MAC, assigned IP, route, DNS, DHCP lease, or ping transcript is recorded in the report.",
        "- Cleanup removes staged config/result/script artifacts and rollback returns to `v725-fasttransport`.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Cleanup",
        "",
        f"- `cache_artifacts_removed`: `{gate['cleanup_ok']}`",
        f"- `cleanup_skipped_reason`: `{gate['cleanup_skipped_reason']}`",
        "",
        "## Safety",
        "",
        "- Wi-Fi credentials are read only from environment variables and are not committed.",
        "- Raw supplicant, kmsg, DHCP, and ping stdout/stderr are summarized with redacted samples; raw supplicant/kmsg files are removed during helper cleanup.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action is used.",
        "",
    ])


def forbidden_hits(text: str) -> list[str]:
    patterns = [
        re.escape(os.environ.get("A90_WIFI_SSID", "")) if os.environ.get("A90_WIFI_SSID") else r"$^",
        re.escape(os.environ.get("A90_WIFI_PSK", "")) if os.environ.get("A90_WIFI_PSK") else r"$^",
        r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
        r'"(?:ssid|bssid|password|passphrase|psk|pre_shared_key)"\s*:',
    ]
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(pattern)
    return hits


def write_preflight_manifest(store: base.EvidenceStore,
                             steps: list[dict[str, Any]],
                             helper_build: dict[str, Any],
                             helper_stage: dict[str, str],
                             standalone_wpa_archive: dict[str, Any],
                             standalone_wpa_stage: dict[str, str],
                             property_manifest: dict[str, Any],
                             property_archive: dict[str, Any],
                             property_stage: dict[str, str],
                             config_stage: dict[str, str],
                             label: str,
                             reason: str,
                             phase_timer: PhaseTimer | None = None) -> None:
    manifest = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "decision": f"v2167-{label}",
        "label": label,
        "pass": False,
        "reason": reason,
        "out_dir": base.rel(OUT_DIR),
        "helper_build": helper_build,
        "helper_stage": helper_stage,
        "standalone_wpa_archive": standalone_wpa_archive,
        "standalone_wpa_stage": standalone_wpa_stage,
        "property_runtime": property_manifest,
        "property_archive": property_archive,
        "property_stage": property_stage,
        "config_stage": config_stage,
        "steps": steps,
        "test_flash_ok": False,
        "rollback": {"ok": True, "not_needed": True},
    }
    gate = {
        "wlan0_seen": False,
        "result_source": "none",
        "serial_attempt_count": 0,
        "result_left_on_device": False,
        "fast_upload_ok": False,
        "fast_upload_reason": "not-run",
        "fast_upload_elapsed_sec": "",
        "fast_upload_archive_path": "",
        "fast_upload_archive_bytes": 0,
        "fast_upload_archive_sha256": "",
        "fast_upload_receiver_bytes": 0,
        "fast_upload_entry_count": 0,
        "fast_upload_forbidden_entries": [],
        "fast_upload_secret_hits": [],
        "cleanup_ok": False,
        "cleanup_skipped_reason": "",
        "helper_invoked": False,
        "helper_rc": 0,
        "executor_result": "",
        "association_carrier": False,
        "association_carrier_errno": 0,
        "dhcp_executed": False,
        "dhcp_rc": 0,
        "external_ping_executed": False,
        "external_ping_target": "",
        "external_ping_rc": 0,
        "hold_enabled": QA_HOLD_SEC > 0,
        "hold_executed": False,
        "hold_requested_sec": QA_HOLD_SEC,
        "hold_interval_sec": QA_HOLD_INTERVAL_SEC,
        "hold_reconnect_on_drop": QA_RECONNECT_ON_DROP,
        "hold_samples": 0,
        "hold_carrier_up_count": 0,
        "hold_carrier_down_count": 0,
        "hold_ping_attempt_count": 0,
        "hold_ping_success_count": 0,
        "hold_ping_fail_count": 0,
        "hold_ip_ping_attempt_count": 0,
        "hold_ip_ping_success_count": 0,
        "hold_ip_ping_fail_count": 0,
        "hold_gateway_ping_attempt_count": 0,
        "hold_gateway_ping_success_count": 0,
        "hold_gateway_ping_fail_count": 0,
        "hold_route_default_present_count": 0,
        "hold_route_gateway_present_count": 0,
        "hold_arp_before_entry_count": 0,
        "hold_arp_before_complete_count": 0,
        "hold_arp_after_entry_count": 0,
        "hold_arp_after_complete_count": 0,
        "hold_reconnect_attempt_count": 0,
        "hold_reconnect_success_count": 0,
        "hold_first_fail_sample": 0,
        "hold_first_fail_errno": 0,
        "hold_first_fail_ping_rc": 0,
        "hold_pass": True,
        "hold_reason": "not-run",
        "hold_sample_details": [],
        "force_power_on_enabled": FORCE_POWER_ON,
        "force_power_on_executed": False,
        "force_power_on_reason": "not-run",
        "force_power_on_class_before": "",
        "force_power_on_class_write_rc": 0,
        "force_power_on_class_write_errno": 0,
        "force_power_on_class_after": "",
        "force_power_on_device_before": "",
        "force_power_on_device_write_rc": 0,
        "force_power_on_device_write_errno": 0,
        "force_power_on_device_after": "",
        "connect_hold_subsys_modem_requested": CONNECT_HOLD_SUBSYS_MODEM,
        "modem_holder_enabled": False,
        "modem_holder_started": False,
        "modem_holder_start_attempted": False,
        "modem_holder_opened": False,
        "modem_holder_open_errno": 0,
        "modem_holder_pid": -1,
        "modem_holder_stop_attempted": False,
        "modem_holder_reaped": False,
        "modem_holder_postflight_safe": False,
        "modem_holder_subsys_esoc0_open_attempted": False,
        "modem_holder_esoc_open_attempted": False,
        "modem_holder_forced_rc1_attempted": False,
        "country_code": "",
        "driver_ioctl_country_rc": 0,
        "driver_ioctl_country_errno": 0,
        "driver_ioctl_getcountry_rc": 0,
        "driver_ioctl_getcountry_errno": 0,
        "driver_ioctl_getcountry_readback": "",
        "wpa_ctrl_ready": False,
        "wpa_ctrl_dir": "",
        "wpa_ctrl_interface_path": "",
        "wpa_ctrl_surface": "",
        "wpa_ctrl_global_path": "",
        "wpa_ctrl_global_abstract": False,
        "wpa_ctrl_global_preclean_path": "",
        "wpa_ctrl_global_preclean_errno": 0,
        "wpa_ctrl_ready_errno": 0,
        "wpa_ctrl_ping_reply": "",
        "driver_country_reply": "",
        "driver_country_rc": 0,
        "driver_country_errno": 0,
        "interface_add_reply": "",
        "interface_add_rc": 0,
        "interface_add_errno": 0,
        "wpa_ctrl_after_interface_add_ready": False,
        "wpa_ctrl_after_interface_add_surface": "",
        "wpa_ctrl_after_interface_add_global_path": "",
        "wpa_ctrl_after_interface_add_global_abstract": False,
        "wpa_ctrl_after_interface_add_errno": 0,
        "wpa_ctrl_after_interface_add_ping": "",
        "enable_network_reply": "",
        "enable_network_rc": 0,
        "reassociate_reply": "",
        "reassociate_rc": 0,
        "supplicant_driver": "",
        "supplicant_launch_mode": "",
        "supplicant_global_ctrl": "",
        "supplicant_strace_enabled": False,
        "supplicant_strace_output": "",
        "hwservicemanager_started": False,
        "hwservicemanager_start_mode": "",
        "hwservicemanager_pid": -1,
        "supplicant_hidl_add_interface_rc": 0,
        "supplicant_hidl_add_interface_result": "",
        "supplicant_hidl_add_interface_reason": "",
        "supplicant_hidl_add_interface_service_found": False,
        "supplicant_hidl_add_interface_service_descriptor": "",
        "supplicant_hidl_add_interface_service_instance": "",
        "supplicant_hidl_add_interface_status_name": "",
        "supplicant_hidl_add_interface_transaction_ok": False,
        "supplicant_hidl_add_interface_iface_handle_found": False,
        "supplicant_hidl_vendor_service_found": False,
        "supplicant_hidl_vendor_service_descriptor": "",
        "supplicant_hidl_vendor_service_instance": "",
        "supplicant_proc_hidl_add_fd_count": 0,
        "supplicant_proc_hidl_add_fd_socket_count": 0,
        "supplicant_proc_hidl_add_fd_netlink_count": 0,
        "supplicant_proc_hidl_add_fd_generic_netlink_count": 0,
        "supplicant_proc_hidl_add_fd_wpa_socket_count": 0,
        "android_socket_wpa_wlan0_path": "",
        "android_socket_wpa_wlan0_mode": "",
        "android_socket_wpa_wlan0_fd": -1,
        "android_socket_wpa_wlan0_errno": 0,
        "supplicant_alive_after_start": False,
        "supplicant_zombie_after_ctrl_wait": False,
        "supplicant_proc_state_after_start": "",
        "supplicant_alive_after_carrier_wait": False,
        "supplicant_proc_state_after_carrier_wait": "",
        "supplicant_proc_start_comm": "",
        "supplicant_proc_start_exe": "",
        "supplicant_proc_start_has_wpa": False,
        "supplicant_proc_start_has_helper": False,
        "supplicant_proc_start_has_config": False,
        "supplicant_proc_carrier_comm": "",
        "supplicant_proc_carrier_exe": "",
        "supplicant_proc_carrier_has_wpa": False,
        "supplicant_proc_carrier_has_helper": False,
        "supplicant_proc_carrier_has_config": False,
        "supplicant_log_present": False,
        "supplicant_log_size": 0,
        "supplicant_log_lines": 0,
        "supplicant_log_ctrl_iface": 0,
        "supplicant_log_ctrl_iface_error": 0,
        "supplicant_log_nl80211": 0,
        "supplicant_log_scan": 0,
        "supplicant_log_auth": 0,
        "supplicant_log_assoc": 0,
        "supplicant_log_connected": 0,
        "supplicant_log_disconnected": 0,
        "supplicant_log_fail": 0,
        "supplicant_log_permission": 0,
        "supplicant_log_avc": 0,
        "supplicant_log_sample_count": 0,
        "supplicant_log_tail_sample_count": 0,
        "supplicant_log_nonproperty_sample_count": 0,
        "supplicant_log_sensitive_sample_skipped": 0,
        "supplicant_log_samples": [],
        "supplicant_log_tail_samples": [],
        "supplicant_log_nonproperty_samples": [],
        "supplicant_stdio_present": False,
        "supplicant_stdio_size": 0,
        "supplicant_stdio_lines": 0,
        "supplicant_stdio_ctrl_iface": 0,
        "supplicant_stdio_ctrl_iface_error": 0,
        "supplicant_stdio_config_error": 0,
        "supplicant_stdio_nl80211": 0,
        "supplicant_stdio_scan": 0,
        "supplicant_stdio_auth": 0,
        "supplicant_stdio_assoc": 0,
        "supplicant_stdio_connected": 0,
        "supplicant_stdio_disconnected": 0,
        "supplicant_stdio_fail": 0,
        "supplicant_stdio_usage": 0,
        "supplicant_stdio_interface": 0,
        "supplicant_stdio_socket": 0,
        "supplicant_stdio_terminate": 0,
        "supplicant_stdio_permission": 0,
        "supplicant_stdio_avc": 0,
        "supplicant_stdio_sample_count": 0,
        "supplicant_stdio_tail_sample_count": 0,
        "supplicant_stdio_nonproperty_sample_count": 0,
        "supplicant_stdio_sensitive_sample_skipped": 0,
        "supplicant_stdio_samples": [],
        "supplicant_stdio_tail_samples": [],
        "supplicant_stdio_nonproperty_samples": [],
        "supplicant_proc_start_uid": "",
        "supplicant_proc_start_gid": "",
        "supplicant_proc_start_groups": "",
        "supplicant_proc_start_wchan": "",
        "supplicant_proc_start_syscall": "",
        "supplicant_proc_start_stack_first": "",
        "supplicant_proc_start_fd_count": 0,
        "supplicant_proc_start_fd_socket_count": 0,
        "supplicant_proc_start_fd_netlink_count": 0,
        "supplicant_proc_start_fd_generic_netlink_count": 0,
        "supplicant_proc_start_fd_netlink_lookup_miss": 0,
        "supplicant_proc_start_fd_wpa_socket_count": 0,
        "supplicant_proc_start_fd_stdio_log_count": 0,
        "supplicant_proc_start_fd_samples": [],
        "supplicant_proc_carrier_uid": "",
        "supplicant_proc_carrier_gid": "",
        "supplicant_proc_carrier_groups": "",
        "supplicant_proc_carrier_wchan": "",
        "supplicant_proc_carrier_syscall": "",
        "supplicant_proc_carrier_stack_first": "",
        "supplicant_proc_carrier_fd_count": 0,
        "supplicant_proc_carrier_fd_socket_count": 0,
        "supplicant_proc_carrier_fd_netlink_count": 0,
        "supplicant_proc_carrier_fd_generic_netlink_count": 0,
        "supplicant_proc_carrier_fd_netlink_lookup_miss": 0,
        "supplicant_proc_carrier_fd_wpa_socket_count": 0,
        "supplicant_proc_carrier_fd_stdio_log_count": 0,
        "supplicant_proc_carrier_fd_samples": [],
        "kmsg_stream_started": False,
        "kmsg_stream_start_errno": 0,
        "kmsg_stream_cleanup_exit": 0,
        "kmsg_stream_cleanup_signal": 0,
        "kmsg_stream_cleanup_timeout": False,
        "kmsg_stream_present": False,
        "kmsg_stream_size": 0,
        "kmsg_stream_lines": 0,
        "kmsg_stream_permission": 0,
        "kmsg_stream_avc": 0,
        "kmsg_stream_nl80211": 0,
        "kmsg_stream_auth": 0,
        "kmsg_stream_assoc": 0,
        "kmsg_stream_fail": 0,
        "kmsg_stream_sensitive_sample_skipped": 0,
        "kmsg_stream_samples": [],
        "kmsg_stream_tail_samples": [],
        "logdw_sink_started": False,
        "logdw_sink_errno": 0,
        "logdw_sink_drain_errno": 0,
        "logdw_sink_datagrams": 0,
        "logdw_sink_bytes": 0,
        "logdw_sink_wpa": 0,
        "logdw_sink_supplicant": 0,
        "logdw_sink_nl80211": 0,
        "logdw_sink_ctrl": 0,
        "logdw_sink_interface": 0,
        "logdw_sink_fail": 0,
        "logdw_sink_permission": 0,
        "logdw_sink_hidl": 0,
        "logdw_sink_service_manager": 0,
        "logdw_sink_sample_count": 0,
        "logdw_sink_sensitive_sample_skipped": 0,
        "logdw_sink_samples": [],
        "pre_operstate": "",
        "pre_carrier": "",
        "pre_flags": "",
        "post_operstate": "",
        "post_carrier": "",
        "post_flags": "",
        "helper_stage_ok": helper_stage.get("helper_stage.ok") == "1",
        "standalone_wpa_stage_ok": standalone_wpa_stage.get("standalone_wpa_stage.ok") == "1",
        "standalone_wpa_stage_enabled": standalone_wpa_stage.get("standalone_wpa_stage.enabled", ""),
        "standalone_wpa_stage_reason": standalone_wpa_stage.get("standalone_wpa_stage.reason", ""),
        "standalone_wpa_stage_remote_wrapper": standalone_wpa_stage.get("standalone_wpa_stage.remote_wrapper", ""),
        "standalone_wpa_stage_package_count": intish(standalone_wpa_stage.get("standalone_wpa_stage.package_count")),
        "standalone_wpa_stage_version_rc": intish(standalone_wpa_stage.get("standalone_wpa_stage.version_rc")),
        "standalone_wpa_stage_version_sample": standalone_wpa_stage.get("standalone_wpa_stage.version_sample", ""),
        "property_stage_ok": property_stage.get("property_stage.ok") == "1",
        "property_stage_remote_root": property_stage.get("property_stage.remote_root", ""),
        "property_stage_runtime_decision": property_stage.get("property_stage.runtime_decision", ""),
        "property_stage_file_count": intish(property_stage.get("property_stage.remote_file_count")),
        "property_stage_property_info_size": intish(property_stage.get("property_stage.property_info_size")),
        "config_ok": config_stage.get("connect_config.ok") == "1",
        "script_ok": False,
        "wait_complete": False,
        "no_raw": True,
        "secret_values_logged": "",
        "cleanup_ok": True,
    }
    manifest["connect_ping_gate"] = gate
    attach_timing_manifest(store, manifest, phase_timer)
    summary = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": False,
        "out_dir": manifest["out_dir"],
        "reason": reason,
    }, indent=2))


def main() -> int:
    store = base.EvidenceStore(OUT_DIR)
    bootstrap_steps: list[dict[str, Any]] = []
    phase_timer = PhaseTimer()
    with phase_timer.phase("host_property_build"):
        property_manifest = build_supplicant_property_runtime(store)
    with phase_timer.phase("host_property_archive"):
        property_archive = build_property_archive(property_manifest)
    with phase_timer.phase("host_standalone_wpa_bundle"):
        standalone_wpa_archive = build_standalone_wpa_archive(store, bootstrap_steps)
    with phase_timer.phase("prestage_total"):
        fast_transfer = FastTransferSession(store, bootstrap_steps)
        try:
            with phase_timer.phase("property_stage"):
                property_stage = stage_property_runtime(store, bootstrap_steps, property_manifest, property_archive, fast_transfer)
            with phase_timer.phase("host_helper_build"):
                helper_build = build_helper(store, bootstrap_steps)
            with phase_timer.phase("helper_stage"):
                helper_stage = stage_helper_binary(store, bootstrap_steps, helper_build, fast_transfer)
            with phase_timer.phase("strace_stage"):
                strace_stage = stage_strace_binary(store, bootstrap_steps, fast_transfer)
            with phase_timer.phase("standalone_wpa_stage"):
                standalone_wpa_stage = stage_standalone_wpa_bundle(store, bootstrap_steps, standalone_wpa_archive, fast_transfer)
        finally:
            with phase_timer.phase("fast_transfer_close"):
                fast_transfer.close()
    with phase_timer.phase("connect_config_stage"):
        config_stage = stage_connect_config(store, bootstrap_steps)
    if (
        property_stage.get("property_stage.ok") != "1"
        or helper_stage.get("helper_stage.ok") != "1"
        or strace_stage.get("strace_stage.ok") != "1"
        or standalone_wpa_stage.get("standalone_wpa_stage.ok") != "1"
        or config_stage.get("connect_config.ok") != "1"
    ):
        write_preflight_manifest(
            store,
            bootstrap_steps,
            helper_build,
            helper_stage,
            standalone_wpa_archive,
            standalone_wpa_stage,
            property_manifest,
            property_archive,
            property_stage,
            config_stage,
            "connect-dhcp-ping-prestage-failed-no-flash",
            (
                f"prestage failed property={property_stage.get('property_stage.reason')} "
                f"helper={helper_stage.get('helper_stage.reason')} "
                f"strace={strace_stage.get('strace_stage.reason')} "
                f"standalone_wpa={standalone_wpa_stage.get('standalone_wpa_stage.reason')} "
                f"config={config_stage.get('connect_config.reason')}"
            ),
            phase_timer,
        )
        return 1

    def hook(hook_store: base.EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
        steps.extend(bootstrap_steps)
        with phase_timer.phase("connect_window"):
            return post_flash_connect(hook_store, steps, helper_stage, standalone_wpa_stage, property_stage, config_stage)

    with phase_timer.phase("handoff_flash_test_rollback_total"):
        manifest = base.run_handoff(
            cycle=CYCLE,
            out_dir=OUT_DIR,
            report_path=REPORT_PATH,
            test_image=TEST_BOOT_IMAGE,
            test_expect_version=TEST_EXPECT_VERSION,
            rollback_image=ROLLBACK_BOOT_IMAGE,
            rollback_expect_version=ROLLBACK_EXPECT_VERSION,
            post_flash_hook=hook,
            helper_wait_sec=float(HELPER_WAIT_SEC),
        )
    store = base.EvidenceStore(OUT_DIR)
    steps = manifest["steps"]
    with phase_timer.phase("post_rollback_artifact_upload"):
        connect_result = collect_post_rollback_result(store, steps)
    gate = collect_gate(manifest, connect_result)
    manifest = {
        **manifest,
        "run_label": RUN_LABEL,
        "decision": gate["decision"],
        "label": gate["label"],
        "pass": gate["pass"],
        "reason": gate["reason"],
        "helper_build": helper_build,
        "helper_stage": helper_stage,
        "strace_stage": strace_stage,
        "standalone_wpa_archive": standalone_wpa_archive,
        "standalone_wpa_stage": standalone_wpa_stage,
        "property_runtime": property_manifest,
        "property_archive": property_archive,
        "property_stage": property_stage,
        "config_stage": config_stage,
        "post_rollback_connect_result": connect_result,
        "connect_ping_gate": gate,
        "steps": steps,
        "credentials_read": True,
        "connect_executed": True,
        "dhcp_route_executed": gate["dhcp_executed"],
        "external_ping_executed": gate["external_ping_executed"],
        "qa_hold_config": {
            "hold_sec": QA_HOLD_SEC,
            "hold_interval_sec": QA_HOLD_INTERVAL_SEC,
            "reconnect_on_drop": QA_RECONNECT_ON_DROP,
            "force_power_on": FORCE_POWER_ON,
        },
    }
    attach_timing_manifest(store, manifest, phase_timer)
    summary = render_report(manifest)
    hits = forbidden_hits(summary)
    manifest["forbidden_output_hits"] = hits
    if hits:
        manifest["decision"] = "v2167-forbidden-output-hit"
        manifest["label"] = "forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "report contained forbidden credential/MAC/BSS output"
        summary = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "out_dir": manifest["out_dir"],
        "connect_ping_gate": gate,
        "forbidden_output_hits": hits,
    }, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
