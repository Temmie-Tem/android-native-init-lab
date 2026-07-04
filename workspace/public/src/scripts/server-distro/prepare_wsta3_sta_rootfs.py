#!/usr/bin/env python3
"""Prepare a private WSTA3 Debian rootfs copy with Wi-Fi STA config staged.

This is host-only.  It copies a WSTA-ready D3 sysvinit rootfs into a private run
directory, writes the explicit opt-in files consumed by ``a90-dpublic-wifi-sta``,
and optionally creates a private D4C-compatible tarball.  It never prints SSID,
PSK, raw supplicant config text, or a secret-derived archive digest.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_d4c_userdata_rootfs_tarball as d4c  # noqa: E402


DEFAULT_RUN_BASE = REPO_ROOT / "workspace/private/runs/server-distro"
DEFAULT_SOURCE_ROOTFS = (
    REPO_ROOT
    / "workspace/private/builds/server-distro/d3-sysvinit-usrmerge-wsta-20260704T0225Z-rootfs"
)
DEFAULT_WIFI_ENV = REPO_ROOT / "workspace/private/secrets/a90-wifi-test.env"
DEFAULT_APT_WORK = REPO_ROOT / "workspace/private/builds/server-distro/wsta3-apt-arm64"
DEFAULT_CLOUDFLARED = REPO_ROOT / "workspace/private/builds/server-distro/tunnel/cloudflared-linux-arm64"
DEFAULT_SMOKE_HTTPD = REPO_ROOT / "workspace/private/runs/server-distro/dpublic-live-20260703T150145Z/a90-dpublic-smoke-httpd"
DEFAULT_HTTP_GET = REPO_ROOT / "workspace/private/runs/server-distro/dpublic-live-20260703T150145Z/a90-dpublic-http-get"
DEFAULT_HUD = REPO_ROOT / "workspace/private/runs/server-distro/dpublic-hud-20260703T153322Z/a90-dpublic-hud"
DEFAULT_SUITE = "bookworm"
DEFAULT_ARCH = "arm64"
DEFAULT_MIRROR = "http://deb.debian.org/debian"
TARGET_CONFIG = Path("etc/a90-dpublic/wpa_supplicant-wlan0.conf")
TARGET_ENABLE = Path("etc/a90-dpublic/wifi-sta-enable")
TARGET_IMMEDIATE_SNAPSHOT_ONLY = Path("etc/a90-dpublic/wifi-sta-immediate-snapshot-only")
TARGET_QUICK_TUNNEL_ENABLE = Path("etc/a90-dpublic/cloudflared-quick-enable")
TARGET_HELPER = Path("usr/local/bin/a90-dpublic-wifi-sta")
TARGET_API_PROBE = Path("usr/local/bin/a90-dpublic-api-probe")
TARGET_NATIVE_WIFI_SERVICE_CLIENT = Path("usr/local/bin/a90-native-wifi-service-client")
TARGET_NATIVE_WIFI_UPLINK_CLIENT = Path("usr/local/bin/a90-native-wifi-uplink-client")
TARGET_FIRSTBOOT = Path("etc/a90-d3-firstboot")
DPUBLIC_BINARY_TARGETS = {
    "cloudflared": Path("usr/local/bin/cloudflared"),
    "smoke_httpd": Path("usr/local/bin/a90-dpublic-smoke-httpd"),
    "http_get": Path("usr/local/bin/a90-dpublic-http-get"),
    "hud": Path("usr/local/bin/a90-dpublic-hud"),
}
DPUBLIC_WIFI_STA_HELPER = SCRIPT_DIR / "a90_dpublic_wifi_sta.sh"
DPUBLIC_API_PROBE = SCRIPT_DIR / "a90_dpublic_api_probe.sh"
DPUBLIC_NATIVE_WIFI_SERVICE_CLIENT = SCRIPT_DIR / "a90_native_wifi_service_client.sh"
DPUBLIC_NATIVE_WIFI_UPLINK_CLIENT = SCRIPT_DIR / "a90_native_wifi_uplink_client.sh"
DPUBLIC_FIRSTBOOT = SCRIPT_DIR / "a90_dpublic_firstboot.sh"
PRIVATE_FILE_MODE = 0o600
STA_TOOL_PACKAGES = ("wpasupplicant", "isc-dhcp-client", "netcat-openbsd", "iw")
API_PROBE_TOOL_PACKAGES = ("wget",)
USR_MERGE_LINKS = (("bin", "usr/bin"), ("sbin", "usr/sbin"), ("lib", "usr/lib"))
STA_TOOL_CANDIDATES = {
    "ip": (Path("usr/sbin/ip"), Path("sbin/ip"), Path("bin/ip")),
    "ping": (Path("usr/bin/ping"), Path("bin/ping")),
    "getent": (Path("usr/bin/getent"), Path("bin/getent")),
    "nc": (Path("usr/bin/nc"), Path("bin/nc"), Path("usr/bin/nc.openbsd"), Path("bin/nc.openbsd")),
    "iw": (Path("usr/sbin/iw"), Path("sbin/iw")),
    "wpa_supplicant": (Path("usr/sbin/wpa_supplicant"), Path("sbin/wpa_supplicant")),
    "wpa_cli": (Path("usr/sbin/wpa_cli"), Path("sbin/wpa_cli")),
    "dhclient": (Path("usr/sbin/dhclient"), Path("sbin/dhclient")),
}
API_PROBE_TOOL_CANDIDATES = {
    "wget": (Path("usr/bin/wget"), Path("bin/wget")),
}
KEY_SSID = "ssid"
KEY_PSK = "psk"
KEY_MGMT = "key_mgmt"


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True, ensure_ascii=False)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
    tmp.replace(path)


def run_host(command: list[object], *, timeout: float, cwd: Path = REPO_ROOT) -> dict[str, Any]:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    payload = {
        "command": [str(item) for item in command],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode != 0:
        raise RuntimeError(
            "host command failed rc="
            f"{result.returncode}: {' '.join(str(item) for item in command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return payload


def is_owner_private(path: Path) -> bool:
    return bool(path.exists() and (path.stat().st_mode & 0o077) == 0)


def safe_env_value(raw: str) -> str:
    parts = shlex.split(raw, comments=False, posix=True)
    if len(parts) != 1:
        raise ValueError("env assignment must parse as exactly one shell token")
    if "=" not in parts[0]:
        raise ValueError("env assignment is missing '='")
    return parts[0].split("=", 1)[1]


def load_wifi_env(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "reason": "wifi-env-missing", "path": rel(path)}
    if not is_owner_private(path):
        return {"ok": False, "reason": "wifi-env-not-0600", "path": rel(path)}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if not (line.startswith("A90_WIFI_SSID=") or line.startswith("A90_WIFI_PSK=")):
            continue
        key = line.split("=", 1)[0]
        values[key] = safe_env_value(line)
    ssid = values.get("A90_WIFI_SSID", "")
    psk = values.get("A90_WIFI_PSK", "")
    ssid_len = len(ssid.encode("utf-8"))
    psk_len = len(psk)
    if not (1 <= ssid_len <= 32):
        return {"ok": False, "reason": "wifi-env-invalid-ssid", "path": rel(path), "secret_values_logged": 0}
    if not (8 <= psk_len <= 63 or re.fullmatch(r"[0-9a-fA-F]{64}", psk)):
        return {"ok": False, "reason": "wifi-env-invalid-psk", "path": rel(path), "secret_values_logged": 0}
    return {
        "ok": True,
        "path": rel(path),
        "ssid": ssid,
        "psk": psk,
        "ssid_len": ssid_len,
        "psk_len": psk_len,
        "secret_values_logged": 0,
    }


def quote_wpa(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def supplicant_text_from_env(env: dict[str, Any]) -> str:
    psk = str(env["psk"])
    psk_value = psk if re.fullmatch(r"[0-9a-fA-F]{64}", psk) else quote_wpa(psk)
    return "\n".join([
        "ctrl_interface=/run/wpa_supplicant",
        "update_config=0",
        "network={",
        "    " + KEY_SSID + "=" + quote_wpa(str(env["ssid"])),
        "    scan_ssid=1",
        "    " + KEY_MGMT + "=WPA-PSK",
        "    " + KEY_PSK + "=" + psk_value,
        "}",
        "",
    ])


def supplicant_config_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "reason": "wpa-conf-missing", "path": rel(path)}
    if not is_owner_private(path):
        return {"ok": False, "reason": "wpa-conf-not-0600", "path": rel(path)}
    keys: set[str] = set()
    has_network_block = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "network={":
            has_network_block = True
        if "=" in line and not line.startswith("#"):
            keys.add(line.split("=", 1)[0].strip())
    has_ssid = KEY_SSID in keys
    has_auth = KEY_PSK in keys or KEY_MGMT in keys
    return {
        "ok": bool(has_network_block and has_ssid and has_auth),
        "reason": "ok" if has_network_block and has_ssid and has_auth else "wpa-conf-missing-required-fields",
        "path": rel(path),
        "mode_private": True,
        "has_network_block": has_network_block,
        "has_ssid_field": has_ssid,
        "has_auth_field": has_auth,
        "secret_values_logged": 0,
    }


def copy_rootfs(source: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest, symlinks=True, copy_function=shutil.copy2)


def sta_tool_metadata(rootfs: Path) -> dict[str, Any]:
    tools: dict[str, dict[str, Any]] = {}
    for name, candidates in STA_TOOL_CANDIDATES.items():
        found = next((candidate for candidate in candidates if (rootfs / candidate).exists()), None)
        tools[name] = {
            "present": found is not None,
            "path": str(found) if found else None,
        }
    ok = all(item["present"] for item in tools.values())
    return {
        "ok": ok,
        "tools": tools,
        "secret_values_logged": 0,
    }


def tool_metadata(rootfs: Path, candidates_by_name: dict[str, tuple[Path, ...]]) -> dict[str, Any]:
    tools: dict[str, dict[str, Any]] = {}
    for name, candidates in candidates_by_name.items():
        found = next((candidate for candidate in candidates if (rootfs / candidate).exists()), None)
        tools[name] = {
            "present": found is not None,
            "path": str(found) if found else None,
        }
    ok = all(item["present"] for item in tools.values())
    return {
        "ok": ok,
        "tools": tools,
        "secret_values_logged": 0,
    }


def api_probe_tool_metadata(rootfs: Path) -> dict[str, Any]:
    return tool_metadata(rootfs, API_PROBE_TOOL_CANDIDATES)


def merge_tree_contents(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir(), key=lambda p: p.name):
        target = dst / item.name
        if target.exists() or target.is_symlink():
            if item.is_dir() and not item.is_symlink() and target.is_dir() and not target.is_symlink():
                merge_tree_contents(item, target)
                item.rmdir()
                continue
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(item), str(target))


def restore_usrmerge_links(rootfs: Path) -> dict[str, Any]:
    restored: dict[str, dict[str, Any]] = {}
    for link_name, target_name in USR_MERGE_LINKS:
        link = rootfs / link_name
        target = rootfs / target_name
        if link.is_symlink():
            if os.readlink(link) != target_name:
                link.unlink()
                link.symlink_to(target_name)
            restored[link_name] = {"is_symlink": True, "target": os.readlink(link)}
            continue
        if link.exists():
            if not link.is_dir():
                link.unlink()
            else:
                merge_tree_contents(link, target)
                link.rmdir()
        target.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target_name)
        restored[link_name] = {"is_symlink": True, "target": target_name}
    return restored


def apt_common_args(args: argparse.Namespace, rootfs: Path) -> list[object]:
    apt_root = args.apt_work.resolve()
    sources = apt_root / "etc" / "apt" / "sources.list"
    return [
        "-o", f"APT::Architecture={args.arch}",
        "-o", f"APT::Architectures={args.arch}",
        "-o", f"Dir::Etc::sourcelist={sources}",
        "-o", "Dir::Etc::sourceparts=-",
        "-o", f"Dir::Etc::trustedparts={rootfs.resolve() / 'etc' / 'apt' / 'trusted.gpg.d'}",
        "-o", f"Dir::State={apt_root / 'state'}",
        "-o", f"Dir::State::status={rootfs.resolve() / 'var' / 'lib' / 'dpkg' / 'status'}",
        "-o", f"Dir::Cache={apt_root / 'cache'}",
        "-o", "Debug::NoLocking=1",
    ]


def download_packages(rootfs: Path, args: argparse.Namespace, packages_requested: tuple[str, ...]) -> list[Path]:
    apt_root = args.apt_work.resolve()
    for rel in ("etc/apt", "state/lists/partial", "cache/archives/partial"):
        (apt_root / rel).mkdir(parents=True, exist_ok=True)
    (apt_root / "etc" / "apt" / "sources.list").write_text(
        f"deb [arch={args.arch}] {args.mirror} {args.suite} main\n",
        encoding="utf-8",
    )
    for old in (apt_root / "cache" / "archives").glob("*.deb"):
        old.unlink()
    common = apt_common_args(args, rootfs)
    run_host(["apt-get", *common, "update"], timeout=args.apt_timeout)
    run_host(
        ["apt-get", *common, "--download-only", "-y", "install", *packages_requested],
        timeout=args.apt_timeout,
    )
    packages = sorted((apt_root / "cache" / "archives").glob("*.deb"))
    missing = [pkg for pkg in packages_requested if not any(path.name.startswith(pkg + "_") for path in packages)]
    if missing:
        raise RuntimeError(f"missing downloaded packages: {missing}")
    return packages


def download_sta_tool_packages(rootfs: Path, args: argparse.Namespace) -> list[Path]:
    return download_packages(rootfs, args, STA_TOOL_PACKAGES)


def ensure_sta_tools(rootfs: Path, args: argparse.Namespace) -> dict[str, Any]:
    before = sta_tool_metadata(rootfs)
    if before["ok"]:
        usrmerge = restore_usrmerge_links(rootfs)
        return {
            "ok": True,
            "installed": False,
            "before": before,
            "after": sta_tool_metadata(rootfs),
            "usrmerge": usrmerge,
            "secret_values_logged": 0,
        }
    if args.no_sta_tool_install:
        return {
            "ok": False,
            "installed": False,
            "reason": "sta-tools-missing-install-disabled",
            "before": before,
            "secret_values_logged": 0,
        }
    packages = download_sta_tool_packages(rootfs, args)
    for package in packages:
        run_host(["dpkg-deb", "-x", package, rootfs], timeout=args.apt_timeout)
    usrmerge = restore_usrmerge_links(rootfs)
    after = sta_tool_metadata(rootfs)
    return {
        "ok": bool(after["ok"]),
        "installed": True,
        "deb_count": len(packages),
        "packages": [path.name for path in packages],
        "before": before,
        "after": after,
        "usrmerge": usrmerge,
        "secret_values_logged": 0,
    }


def ensure_api_probe_tools(rootfs: Path, args: argparse.Namespace) -> dict[str, Any]:
    before = api_probe_tool_metadata(rootfs)
    if not args.stage_api_probe_tools:
        return {
            "requested": False,
            "ok": True,
            "installed": False,
            "before": before,
            "after": before,
            "secret_values_logged": 0,
        }
    if before["ok"]:
        usrmerge = restore_usrmerge_links(rootfs)
        return {
            "requested": True,
            "ok": True,
            "installed": False,
            "before": before,
            "after": api_probe_tool_metadata(rootfs),
            "usrmerge": usrmerge,
            "secret_values_logged": 0,
        }
    packages = download_packages(rootfs, args, API_PROBE_TOOL_PACKAGES)
    for package in packages:
        run_host(["dpkg-deb", "-x", package, rootfs], timeout=args.apt_timeout)
    usrmerge = restore_usrmerge_links(rootfs)
    after = api_probe_tool_metadata(rootfs)
    return {
        "requested": True,
        "ok": bool(after["ok"]),
        "installed": True,
        "deb_count": len(packages),
        "packages": [path.name for path in packages],
        "before": before,
        "after": after,
        "usrmerge": usrmerge,
        "secret_values_logged": 0,
    }


def stage_config(rootfs: Path, config: Path) -> dict[str, Any]:
    config_target = rootfs / TARGET_CONFIG
    enable_target = rootfs / TARGET_ENABLE
    config_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config, config_target)
    config_target.chmod(PRIVATE_FILE_MODE)
    enable_target.write_text("1\n", encoding="utf-8")
    enable_target.chmod(PRIVATE_FILE_MODE)
    return {
        "config_target": str(TARGET_CONFIG),
        "enable_target": str(TARGET_ENABLE),
        "config_mode": oct(config_target.stat().st_mode & 0o777),
        "enable_mode": oct(enable_target.stat().st_mode & 0o777),
        "helper_present": (rootfs / TARGET_HELPER).is_file(),
        "secret_values_logged": 0,
    }


def stage_immediate_snapshot_only(rootfs: Path) -> dict[str, Any]:
    enable_target = rootfs / TARGET_ENABLE
    snapshot_target = rootfs / TARGET_IMMEDIATE_SNAPSHOT_ONLY
    enable_target.parent.mkdir(parents=True, exist_ok=True)
    enable_target.write_text("1\n", encoding="utf-8")
    snapshot_target.write_text("1\n", encoding="utf-8")
    enable_target.chmod(PRIVATE_FILE_MODE)
    snapshot_target.chmod(PRIVATE_FILE_MODE)
    return {
        "enable_target": str(TARGET_ENABLE),
        "snapshot_only_target": str(TARGET_IMMEDIATE_SNAPSHOT_ONLY),
        "enable_mode": oct(enable_target.stat().st_mode & 0o777),
        "snapshot_only_mode": oct(snapshot_target.stat().st_mode & 0o777),
        "config_required": False,
        "config_target_present": (rootfs / TARGET_CONFIG).is_file(),
        "helper_present": (rootfs / TARGET_HELPER).is_file(),
        "secret_values_logged": 0,
    }


def stage_dpublic_wifi_sta_helper(rootfs: Path) -> dict[str, Any]:
    helper_target = rootfs / TARGET_HELPER
    if not DPUBLIC_WIFI_STA_HELPER.is_file():
        raise FileNotFoundError(DPUBLIC_WIFI_STA_HELPER)
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DPUBLIC_WIFI_STA_HELPER, helper_target)
    helper_target.chmod(0o755)
    text = helper_target.read_text(encoding="utf-8")
    return {
        "helper_target": str(TARGET_HELPER),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "latest_helper_staged": True,
        "l3_gate_present": "probe_l3_reachability" in text,
        "dwell_gate_present": "dwell_stability_probe" in text and "wifi_sta_dwell_pass" in text,
        "signal_dwell_present": "SIGNAL_POLL" in text and "wifi_sta_dwell_first_fail_reason" in text,
        "gateway_dwell_present": "wifi_sta_dwell_sample_${sample}_gateway_ping_attempts" in text
        and "wifi_sta_dwell_sample_${sample}_lease_router_matches_initial" in text,
        "assoc_retry_present": "wifi_sta_assoc_attempts_max" in text
        and "wifi_sta_assoc_attempt_${attempt}_retry_reassociate_rc" in text,
        "scan_visibility_present": "scan_visibility_probe()" in text
        and "wifi_sta_scan_${label}_final_results_count" in text,
        "linkstate_diag_present": "link_snapshot()" in text
        and "wifi_sta_link_${snapshot_label}_operstate" in text,
        "iw_diag_present": "iw dev \"$IFACE\" scan" in text
        and "wifi_sta_reg_${reg_label}_iw_scan_bss_count" in text,
        "immediate_snapshot_present": "wifi_sta_immediate_snapshot_only=$immediate_snapshot_only" in text
        and "wifi-sta-immediate-snapshot-pass" in text,
        "handoff_materialization_present": "try_handoff_materialization()" in text
        and "wifi-sta-handoff-materialization-scan-failed" in text,
        "tcp_probe_fallback_present": "nc.openbsd" in text,
        "secret_values_logged": 0,
    }


def stage_dpublic_api_probe_helper(rootfs: Path) -> dict[str, Any]:
    helper_target = rootfs / TARGET_API_PROBE
    if not DPUBLIC_API_PROBE.is_file():
        raise FileNotFoundError(DPUBLIC_API_PROBE)
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DPUBLIC_API_PROBE, helper_target)
    helper_target.chmod(0o755)
    text = helper_target.read_text(encoding="utf-8")
    return {
        "helper_target": str(TARGET_API_PROBE),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "latest_helper_staged": True,
        "api_post_present": "POST /tunnel HTTP/1.1" in text,
        "secret_hygiene_marker": "api_probe_secret_values_logged=0" in text,
        "cloudflared_not_started": "/usr/local/bin/cloudflared" not in text,
        "secret_values_logged": 0,
    }


def stage_native_wifi_service_client(rootfs: Path) -> dict[str, Any]:
    helper_target = rootfs / TARGET_NATIVE_WIFI_SERVICE_CLIENT
    if not DPUBLIC_NATIVE_WIFI_SERVICE_CLIENT.is_file():
        raise FileNotFoundError(DPUBLIC_NATIVE_WIFI_SERVICE_CLIENT)
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DPUBLIC_NATIVE_WIFI_SERVICE_CLIENT, helper_target)
    helper_target.chmod(0o755)
    text = helper_target.read_text(encoding="utf-8")
    return {
        "helper_target": str(TARGET_NATIVE_WIFI_SERVICE_CLIENT),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "latest_helper_staged": True,
        "file_protocol_present": "seq=%s\\n" in text and "op=%s\\n" in text,
        "atomic_request_present": "request.tmp.$$" in text and "mv \"$request_tmp\" \"$request\"" in text,
        "status_scan_only": "status|scan" in text,
        "dangerous_ops_denied": "connect|associate|association|dhcp|ping|public-tunnel|tunnel" in text,
        "owner_check_present": "owner\" != \"native-init\"" in text,
        "version_check_present": "a90-native-wifi-service-v1" in text,
        "redacted_response_filter_present": "raw_results_redacted" in text and "scan_result_count" in text,
        "secret_hygiene_marker": "native_wifi_service_client_secret_values_logged=0" in text,
        "secret_values_logged": 0,
    }


def stage_native_wifi_uplink_client(rootfs: Path) -> dict[str, Any]:
    helper_target = rootfs / TARGET_NATIVE_WIFI_UPLINK_CLIENT
    if not DPUBLIC_NATIVE_WIFI_UPLINK_CLIENT.is_file():
        raise FileNotFoundError(DPUBLIC_NATIVE_WIFI_UPLINK_CLIENT)
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DPUBLIC_NATIVE_WIFI_UPLINK_CLIENT, helper_target)
    helper_target.chmod(0o755)
    text = helper_target.read_text(encoding="utf-8")
    return {
        "helper_target": str(TARGET_NATIVE_WIFI_UPLINK_CLIENT),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "latest_helper_staged": True,
        "file_protocol_present": "seq=%s\\n" in text and "op=%s\\n" in text,
        "atomic_request_present": "request.tmp.$$" in text and "mv \"$request_tmp\" \"$request\"" in text,
        "status_no_confirm_and_confirmed_gate": "status|autoconnect-no-confirm|autoconnect-confirmed" in text,
        "confirmed_autoconnect_env_gated": (
            "A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED" in text
            and "A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN" in text
            and "native-wifi-uplink-client-confirmed-disabled" in text
            and "native-wifi-uplink-client-confirm-token-missing" in text
        ),
        "confirmed_autoconnect_fail_closed": "confirmed-autoconnect" in text and "native-wifi-uplink-client-op-denied" in text,
        "dangerous_ops_denied": "connect|associate|association|dhcp|ping|public-tunnel|tunnel" in text,
        "owner_check_present": "owner\" != \"native-init\"" in text,
        "version_check_present": "a90-native-wifi-uplink-service-v1" in text,
        "redacted_profile_filter_present": "config_profile_present" in text and "autoconnect_profile_present" in text,
        "secret_hygiene_marker": "native_wifi_uplink_client_secret_values_logged=0" in text,
        "secret_values_logged": 0,
    }


def stage_dpublic_firstboot(rootfs: Path) -> dict[str, Any]:
    firstboot_target = rootfs / TARGET_FIRSTBOOT
    if not DPUBLIC_FIRSTBOOT.is_file():
        raise FileNotFoundError(DPUBLIC_FIRSTBOOT)
    firstboot_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DPUBLIC_FIRSTBOOT, firstboot_target)
    firstboot_target.chmod(0o755)
    text = firstboot_target.read_text(encoding="utf-8")
    return {
        "firstboot_target": str(TARGET_FIRSTBOOT),
        "firstboot_mode": oct(firstboot_target.stat().st_mode & 0o777),
        "autoreboot_disabled_marker": "autoreboot_sec=disabled" in text,
        "wifi_sta_helper_invoked": "/usr/local/bin/a90-dpublic-wifi-sta" in text,
        "secret_values_logged": 0,
    }


def stage_dpublic_binaries(rootfs: Path, args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "cloudflared": args.cloudflared,
        "smoke_httpd": args.smoke_httpd,
        "http_get": args.http_get,
        "hud": args.hud,
    }
    staged: dict[str, dict[str, Any]] = {}
    for name, source in sources.items():
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        target = rootfs / DPUBLIC_BINARY_TARGETS[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(0o755)
        staged[name] = {
            "target": str(DPUBLIC_BINARY_TARGETS[name]),
            "mode": oct(target.stat().st_mode & 0o777),
            "size_bytes": target.stat().st_size,
        }
    return {
        "staged": True,
        "binaries": staged,
        "secret_values_logged": 0,
    }


def stage_quick_tunnel_enable(rootfs: Path, enabled: bool) -> dict[str, Any]:
    target = rootfs / TARGET_QUICK_TUNNEL_ENABLE
    if not enabled:
        return {"enabled": False, "target": str(TARGET_QUICK_TUNNEL_ENABLE), "secret_values_logged": 0}
    cloudflared = rootfs / DPUBLIC_BINARY_TARGETS["cloudflared"]
    if not cloudflared.is_file():
        raise FileNotFoundError(cloudflared)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("1\n", encoding="utf-8")
    target.chmod(PRIVATE_FILE_MODE)
    return {
        "enabled": True,
        "target": str(TARGET_QUICK_TUNNEL_ENABLE),
        "mode": oct(target.stat().st_mode & 0o777),
        "secret_values_logged": 0,
    }


def create_private_tarball(rootfs: Path, tarball: Path, timeout: float) -> dict[str, Any]:
    tar = d4c.create_tarball(rootfs, tarball, timeout)
    tarball.chmod(PRIVATE_FILE_MODE)
    verified = d4c.verify_tarball(tarball, timeout)
    return {
        "tarball": rel(tarball),
        "size_bytes": tar["size_bytes"],
        "tarball_mode": oct(tarball.stat().st_mode & 0o777),
        "sha256_redacted": True,
        "required_entry_count": len(verified["required_entries_present"]),
        "secret_values_logged": 0,
    }


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or "wsta3-private-rootfs-" + utc_stamp()
    run_dir = (args.run_dir or (args.run_base / run_id))
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=False)
    run_dir.chmod(0o700)
    result: dict[str, Any] = {
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "source_rootfs": rel(args.source_rootfs),
        "target_rootfs": rel(run_dir / "rootfs"),
        "tarball": rel(run_dir / "a90-wsta3-userdata-rootfs.tar"),
        "secret_values_logged": 0,
    }

    if args.immediate_snapshot_only:
        source_config = None
        result["config_source"] = {
            "type": "immediate-snapshot-only",
            "ok": True,
            "config_required": False,
            "secret_values_logged": 0,
        }
    elif args.wpa_conf:
        source_config = args.wpa_conf
        config_meta = supplicant_config_metadata(source_config)
        result["config_source"] = {"type": "wpa-conf", **{k: v for k, v in config_meta.items() if k != "path"}}
        if not config_meta.get("ok"):
            result.update({"ok": False, "decision": "wsta3-private-config-blocked-" + str(config_meta["reason"])})
            write_json(run_dir / "summary.json", result)
            return result
    else:
        env_meta = load_wifi_env(args.wifi_env)
        result["config_source"] = {
            "type": "wifi-env",
            "path": rel(args.wifi_env),
            "ok": bool(env_meta.get("ok")),
            "reason": env_meta.get("reason", "ok"),
            "ssid_len": env_meta.get("ssid_len"),
            "psk_len": env_meta.get("psk_len"),
            "secret_values_logged": 0,
        }
        if not env_meta.get("ok"):
            result.update({"ok": False, "decision": "wsta3-private-config-blocked-" + str(env_meta["reason"])})
            write_json(run_dir / "summary.json", result)
            return result
        source_config = run_dir / "generated-wpa_supplicant-wlan0.conf"
        source_config.write_text(supplicant_text_from_env(env_meta), encoding="utf-8")
        source_config.chmod(PRIVATE_FILE_MODE)
        config_meta = supplicant_config_metadata(source_config)
        if not config_meta.get("ok"):
            result.update({"ok": False, "decision": "wsta3-private-config-blocked-generated-invalid"})
            write_json(run_dir / "summary.json", result)
            return result

    d4c.verify_rootfs(args.source_rootfs)
    target_rootfs = run_dir / "rootfs"
    copy_rootfs(args.source_rootfs, target_rootfs)
    result["sta_tools"] = ensure_sta_tools(target_rootfs, args)
    if not result["sta_tools"].get("ok"):
        result.update({"ok": False, "decision": "wsta3-private-rootfs-blocked-" + str(result["sta_tools"].get("reason", "sta-tools-missing"))})
        write_json(run_dir / "summary.json", result)
        return result
    result["api_probe_tools"] = ensure_api_probe_tools(target_rootfs, args)
    if not result["api_probe_tools"].get("ok"):
        result.update({"ok": False, "decision": "wsta3-private-rootfs-blocked-api-probe-tools-missing"})
        write_json(run_dir / "summary.json", result)
        return result
    result["wifi_sta_helper"] = stage_dpublic_wifi_sta_helper(target_rootfs)
    result["api_probe_helper"] = stage_dpublic_api_probe_helper(target_rootfs)
    result["native_wifi_service_client"] = stage_native_wifi_service_client(target_rootfs)
    result["native_wifi_uplink_client"] = stage_native_wifi_uplink_client(target_rootfs)
    if args.immediate_snapshot_only:
        result["stage"] = stage_immediate_snapshot_only(target_rootfs)
    else:
        assert source_config is not None
        result["stage"] = stage_config(target_rootfs, source_config)
    result["firstboot"] = stage_dpublic_firstboot(target_rootfs)
    result["dpublic_binaries"] = (
        stage_dpublic_binaries(target_rootfs, args)
        if args.stage_dpublic_binaries
        else {"staged": False, "secret_values_logged": 0}
    )
    result["quick_tunnel_enable"] = stage_quick_tunnel_enable(target_rootfs, args.enable_quick_tunnel)
    d4c.verify_rootfs(target_rootfs)
    if not args.no_tarball:
        result["tarball_result"] = create_private_tarball(
            target_rootfs, run_dir / "a90-wsta3-userdata-rootfs.tar", args.tar_timeout
        )
    result.update({
        "ok": True,
        "decision": "wsta3-private-rootfs-prepared",
        "device_action": "none",
        "no_flash": True,
        "no_wifi_association": True,
        "no_dhcp": True,
        "no_ping": True,
        "no_public_tunnel": True,
    })
    write_json(run_dir / "summary.json", result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-rootfs", type=Path, default=DEFAULT_SOURCE_ROOTFS)
    parser.add_argument("--run-base", type=Path, default=DEFAULT_RUN_BASE)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--wifi-env", type=Path, default=DEFAULT_WIFI_ENV)
    parser.add_argument("--wpa-conf", type=Path)
    parser.add_argument("--immediate-snapshot-only", action="store_true")
    parser.add_argument("--no-tarball", action="store_true")
    parser.add_argument("--tar-timeout", type=float, default=900.0)
    parser.add_argument("--apt-work", type=Path, default=DEFAULT_APT_WORK)
    parser.add_argument("--suite", default=DEFAULT_SUITE)
    parser.add_argument("--arch", default=DEFAULT_ARCH)
    parser.add_argument("--mirror", default=DEFAULT_MIRROR)
    parser.add_argument("--apt-timeout", type=float, default=180.0)
    parser.add_argument("--no-sta-tool-install", action="store_true")
    parser.add_argument("--stage-dpublic-binaries", action="store_true")
    parser.add_argument("--stage-api-probe-tools", action="store_true")
    parser.add_argument("--enable-quick-tunnel", action="store_true")
    parser.add_argument("--cloudflared", type=Path, default=DEFAULT_CLOUDFLARED)
    parser.add_argument("--smoke-httpd", type=Path, default=DEFAULT_SMOKE_HTTPD)
    parser.add_argument("--http-get", type=Path, default=DEFAULT_HTTP_GET)
    parser.add_argument("--hud", type=Path, default=DEFAULT_HUD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    args.source_rootfs = args.source_rootfs.resolve()
    args.wifi_env = args.wifi_env.resolve()
    args.apt_work = args.apt_work.resolve()
    args.cloudflared = args.cloudflared.resolve()
    args.smoke_httpd = args.smoke_httpd.resolve()
    args.http_get = args.http_get.resolve()
    args.hud = args.hud.resolve()
    if args.wpa_conf:
        args.wpa_conf = args.wpa_conf.resolve()
    try:
        result = prepare(args)
    except Exception as exc:  # noqa: BLE001 - persist bounded failure metadata.
        result = {
            "ok": False,
            "decision": "wsta3-private-rootfs-error",
            "error": str(exc),
            "secret_values_logged": 0,
        }
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
