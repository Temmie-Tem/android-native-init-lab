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
import hashlib
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
DEFAULT_HUD_INTENT = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta132-dpublic-hud-split-prototype-20260705T0750KST"
    / "arm64/a90-dpublic-hud-intent"
)
DEFAULT_HUD_PRESENTER = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta132-dpublic-hud-split-prototype-20260705T0750KST"
    / "arm64/a90-dpublic-hud-presenter"
)
DEFAULT_SECCOMP_POLICY_SOURCE = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta153-seccomp-policy-source-20260705T1207KST"
    / "wsta153_seccomp_policy.json"
)
DEFAULT_SECCOMP_FILTER_MANIFEST = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST"
    / "wsta156_seccomp_filter_manifest.json"
)
DEFAULT_SECCOMP_FILTER_OBJECT = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST"
    / "wsta156_seccomp_filters.o"
)
DEFAULT_SECCOMP_LOADER_HELPER_MANIFEST = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta158-seccomp-loader-checkonly-helper-20260705T1243KST"
    / "wsta158_seccomp_loader_helper_manifest.json"
)
DEFAULT_SECCOMP_LOADER_HELPER = (
    REPO_ROOT
    / "workspace/private/runs/server-distro/wsta158-seccomp-loader-checkonly-helper-20260705T1243KST"
    / "a90-seccomp-loader-checkonly"
)
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
TARGET_NATIVE_UPLINK_PROFILE = Path("usr/local/bin/a90-dpublic-native-uplink-profile")
TARGET_PACKET_FILTER = Path("usr/local/bin/a90-dpublic-packet-filter")
TARGET_SERVICE_LAUNCHER = Path("usr/local/bin/a90-service-launch")
TARGET_SERVICE_HARDENING_POLICY = Path("etc/a90-dpublic/service-hardening.json")
TARGET_SECCOMP_POLICY = Path("etc/a90-dpublic/seccomp-policy.json")
TARGET_SECCOMP_LAUNCHER_MAP = Path("etc/a90-dpublic/seccomp-launcher-map.env")
TARGET_SECCOMP_FILTER_MANIFEST = Path("etc/a90-dpublic/seccomp-filter-manifest.json")
TARGET_SECCOMP_FILTER_OBJECT = Path("usr/lib/a90-dpublic/seccomp/wsta156_seccomp_filters.o")
TARGET_SECCOMP_LOADER_HELPER_MANIFEST = Path("etc/a90-dpublic/seccomp-loader-helper-manifest.json")
TARGET_SECCOMP_LOADER_HELPER = Path("usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly")
TARGET_HUD_INTENT = Path("usr/local/bin/a90-dpublic-hud-intent")
TARGET_HUD_PRESENTER = Path("usr/local/bin/a90-dpublic-hud-presenter")
TARGET_FIRSTBOOT = Path("etc/a90-d3-firstboot")
TARGET_STAGE_MARKER = Path("etc/a90-server-distro-stage")
DPUBLIC_BINARY_TARGETS = {
    "cloudflared": Path("usr/local/bin/cloudflared"),
    "smoke_httpd": Path("usr/local/bin/a90-dpublic-smoke-httpd"),
    "http_get": Path("usr/local/bin/a90-dpublic-http-get"),
    "hud": Path("usr/local/bin/a90-dpublic-hud"),
    "hud_intent": TARGET_HUD_INTENT,
    "hud_presenter": TARGET_HUD_PRESENTER,
}
DPUBLIC_WIFI_STA_HELPER = SCRIPT_DIR / "a90_dpublic_wifi_sta.sh"
DPUBLIC_API_PROBE = SCRIPT_DIR / "a90_dpublic_api_probe.sh"
DPUBLIC_NATIVE_WIFI_SERVICE_CLIENT = SCRIPT_DIR / "a90_native_wifi_service_client.sh"
DPUBLIC_NATIVE_WIFI_UPLINK_CLIENT = SCRIPT_DIR / "a90_native_wifi_uplink_client.sh"
DPUBLIC_NATIVE_UPLINK_PROFILE = SCRIPT_DIR / "a90_dpublic_native_uplink_profile.sh"
DPUBLIC_PACKET_FILTER = SCRIPT_DIR / "a90_dpublic_packet_filter.sh"
DPUBLIC_FIRSTBOOT = SCRIPT_DIR / "a90_dpublic_firstboot.sh"
PRIVATE_FILE_MODE = 0o600
STA_TOOL_PACKAGES = ("wpasupplicant", "isc-dhcp-client", "netcat-openbsd", "iw")
API_PROBE_TOOL_PACKAGES = ("wget",)
PACKET_FILTER_TOOL_PACKAGES = ("iptables",)
SYSCALL_TRACE_TOOL_PACKAGES = ("strace",)
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
PACKET_FILTER_TOOL_CANDIDATES = {
    "iptables_legacy": (Path("usr/sbin/iptables-legacy"), Path("sbin/iptables-legacy")),
    "ip6tables_legacy": (Path("usr/sbin/ip6tables-legacy"), Path("sbin/ip6tables-legacy")),
    "iptables_legacy_restore": (
        Path("usr/sbin/iptables-legacy-restore"),
        Path("sbin/iptables-legacy-restore"),
    ),
    "ip6tables_legacy_restore": (
        Path("usr/sbin/ip6tables-legacy-restore"),
        Path("sbin/ip6tables-legacy-restore"),
    ),
    "iptables_legacy_save": (
        Path("usr/sbin/iptables-legacy-save"),
        Path("sbin/iptables-legacy-save"),
    ),
    "ip6tables_legacy_save": (
        Path("usr/sbin/ip6tables-legacy-save"),
        Path("sbin/ip6tables-legacy-save"),
    ),
}
SYSCALL_TRACE_TOOL_CANDIDATES = {
    "strace": (Path("usr/bin/strace"), Path("bin/strace")),
}
KEY_SSID = "ssid"
KEY_PSK = "psk"
KEY_MGMT = "key_mgmt"
NATIVE_UPLINK_STAGE_MARKERS = (
    "native-uplink-profile=/usr/local/bin/a90-dpublic-native-uplink-profile",
    "native-uplink=operator-controlled via /etc/a90-dpublic/native-uplink-enable",
    "public-exposure-default=off; quick-tunnel requires /etc/a90-dpublic/cloudflared-quick-enable",
)
PACKET_FILTER_STAGE_MARKERS = (
    "packet-filter-backend=legacy-iptables",
    "packet-filter-helper=/usr/local/bin/a90-dpublic-packet-filter",
    "packet-filter-tools=/usr/sbin/iptables-legacy /usr/sbin/ip6tables-legacy",
    "packet-filter-policy=not-enforced; WSTA93 helper staged for manual bounded prototype",
    "packet-filter-default-drop=deferred-WSTA93",
)
SYSCALL_TRACE_STAGE_MARKERS = (
    "syscall-trace-tool=/usr/bin/strace",
    "syscall-trace-target=dpublic-smoke-httpd",
    "syscall-trace-profile-source=deferred-WSTA114",
    "syscall-trace-public-default=off",
)
SERVICE_IDENTITIES = {
    "dpublic-smoke-httpd": {
        "user": "a90www",
        "group": "a90www",
        "uid": 3901,
        "gid": 3901,
        "network_intent": "bind-loopback-127.0.0.1:8080-only",
    },
    "cloudflared-quick-tunnel": {
        "user": "a90tunnel",
        "group": "a90tunnel",
        "uid": 3902,
        "gid": 3902,
        "network_intent": "outbound-only-plus-loopback-origin",
    },
    "dropbear-admin-usb": {
        "user": "a90admin",
        "group": "a90admin",
        "uid": 3903,
        "gid": 3903,
        "network_intent": "usb-ncm-admin-only-192.168.7.2:2222",
    },
    "dpublic-hud": {
        "user": "a90hud",
        "group": "a90hud",
        "uid": 3904,
        "gid": 3904,
        "network_intent": "no-network-intent-producer-only",
    },
}
ROOT_BOUNDARY_SERVICES = ("wsta-native-uplink-helper",)
SERVICE_HARDENING_STAGE_MARKERS = (
    "service-hardening-users=a90www,a90tunnel,a90admin,a90hud",
    "service-hardening-launcher=/usr/local/bin/a90-service-launch",
    "service-hardening-no-new-privs=setpriv-required",
    "service-hardening-root-boundary=wsta-native-uplink-helper",
    "service-hardening-public-default=off",
    "service-seccomp-policy=/etc/a90-dpublic/seccomp-policy.json",
    "service-seccomp-mode=dry-run-before-filter-load",
    "service-seccomp-filter-load=disabled",
    "service-seccomp-filter-manifest=/etc/a90-dpublic/seccomp-filter-manifest.json",
    "service-seccomp-enforce-default=off",
    "service-seccomp-loader-helper=/usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly",
)
HUD_SPLIT_STAGE_MARKERS = (
    "hud-split-intent-producer=/usr/local/bin/a90-dpublic-hud-intent",
    "hud-split-presenter=/usr/local/bin/a90-dpublic-hud-presenter",
    "hud-split-boundary=/run/a90-dpublic/hud-intent.json",
    "hud-split-direct-kms-for-a90hud=disabled",
    "hud-split-presenter-owner=native-init",
    "hud-split-public-default=off",
)
SECCOMP_LAUNCHER_BINDINGS = {
    "dpublic-smoke-httpd": "dpublic-smoke-httpd",
    "cloudflared-quick-tunnel": "cloudflared-quick-tunnel",
    "dropbear-admin-usb": "dropbear-admin-usb",
    "dpublic-hud": "dpublic-hud-intent",
}


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def packet_filter_tool_metadata(rootfs: Path) -> dict[str, Any]:
    meta = tool_metadata(rootfs, PACKET_FILTER_TOOL_CANDIDATES)
    meta["backend"] = "legacy-iptables"
    meta["policy_enforced"] = False
    meta["default_drop_ready_for_source"] = bool(meta["ok"])
    return meta


def syscall_trace_tool_metadata(rootfs: Path) -> dict[str, Any]:
    meta = tool_metadata(rootfs, SYSCALL_TRACE_TOOL_CANDIDATES)
    meta["target_profile"] = "dpublic-smoke-httpd"
    meta["profile_capture_ready_for_source"] = bool(meta["ok"])
    meta["public_default"] = "off"
    return meta


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


def download_packet_filter_tool_packages(rootfs: Path, args: argparse.Namespace) -> list[Path]:
    return download_packages(rootfs, args, PACKET_FILTER_TOOL_PACKAGES)


def download_syscall_trace_tool_packages(rootfs: Path, args: argparse.Namespace) -> list[Path]:
    return download_packages(rootfs, args, SYSCALL_TRACE_TOOL_PACKAGES)


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


def ensure_packet_filter_tools(rootfs: Path, args: argparse.Namespace) -> dict[str, Any]:
    before = packet_filter_tool_metadata(rootfs)
    if before["ok"]:
        usrmerge = restore_usrmerge_links(rootfs)
        return {
            "ok": True,
            "backend": "legacy-iptables",
            "installed": False,
            "policy_enforced": False,
            "before": before,
            "after": packet_filter_tool_metadata(rootfs),
            "usrmerge": usrmerge,
            "secret_values_logged": 0,
        }
    if args.no_packet_filter_tool_install:
        return {
            "ok": False,
            "backend": "legacy-iptables",
            "installed": False,
            "policy_enforced": False,
            "reason": "packet-filter-tools-missing-install-disabled",
            "before": before,
            "secret_values_logged": 0,
        }
    packages = download_packet_filter_tool_packages(rootfs, args)
    for package in packages:
        run_host(["dpkg-deb", "-x", package, rootfs], timeout=args.apt_timeout)
    usrmerge = restore_usrmerge_links(rootfs)
    after = packet_filter_tool_metadata(rootfs)
    return {
        "ok": bool(after["ok"]),
        "backend": "legacy-iptables",
        "installed": True,
        "policy_enforced": False,
        "deb_count": len(packages),
        "packages": [path.name for path in packages],
        "before": before,
        "after": after,
        "usrmerge": usrmerge,
        "secret_values_logged": 0,
    }


def ensure_syscall_trace_tools(rootfs: Path, args: argparse.Namespace) -> dict[str, Any]:
    before = syscall_trace_tool_metadata(rootfs)
    if not args.stage_syscall_trace_tools:
        return {
            "requested": False,
            "ok": True,
            "installed": False,
            "before": before,
            "after": before,
            "profile_capture_ready_for_source": False,
            "secret_values_logged": 0,
        }
    if before["ok"]:
        usrmerge = restore_usrmerge_links(rootfs)
        after = syscall_trace_tool_metadata(rootfs)
        return {
            "requested": True,
            "ok": True,
            "installed": False,
            "before": before,
            "after": after,
            "usrmerge": usrmerge,
            "profile_capture_ready_for_source": bool(after["profile_capture_ready_for_source"]),
            "secret_values_logged": 0,
        }
    packages = download_syscall_trace_tool_packages(rootfs, args)
    for package in packages:
        run_host(["dpkg-deb", "-x", package, rootfs], timeout=args.apt_timeout)
    usrmerge = restore_usrmerge_links(rootfs)
    after = syscall_trace_tool_metadata(rootfs)
    return {
        "requested": True,
        "ok": bool(after["ok"]),
        "installed": True,
        "deb_count": len(packages),
        "packages": [path.name for path in packages],
        "before": before,
        "after": after,
        "usrmerge": usrmerge,
        "profile_capture_ready_for_source": bool(after["profile_capture_ready_for_source"]),
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


def stage_native_uplink_profile(rootfs: Path) -> dict[str, Any]:
    helper_target = rootfs / TARGET_NATIVE_UPLINK_PROFILE
    if not DPUBLIC_NATIVE_UPLINK_PROFILE.is_file():
        raise FileNotFoundError(DPUBLIC_NATIVE_UPLINK_PROFILE)
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DPUBLIC_NATIVE_UPLINK_PROFILE, helper_target)
    helper_target.chmod(0o755)
    text = helper_target.read_text(encoding="utf-8")
    tunnel_phrase = "cloudflared" + " tunnel"
    return {
        "helper_target": str(TARGET_NATIVE_UPLINK_PROFILE),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "latest_helper_staged": True,
        "native_client_delegation_present": ' "$CLIENT" autoconnect-confirmed "$SERVICE_DIR"' in text,
        "operator_enable_gate_present": "/etc/a90-dpublic/native-uplink-enable" in text
        and "native-uplink-profile-enable-missing" in text,
        "confirmed_autoconnect_env_gated": (
            "A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED" in text
            and "A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN" in text
            and "native-uplink-profile-confirmed-disabled" in text
            and "native-uplink-profile-confirm-token-missing" in text
        ),
        "public_default_off_marker": "native_uplink_profile_public_default=off" in text,
        "public_tunnel_not_started": tunnel_phrase not in text and "native-uplink-profile-public-tunnel" in text,
        "wsta43_sequence_marker": "native_uplink_profile_public_runner=wsta43" in text,
        "secret_hygiene_marker": "native_uplink_profile_secret_values_logged=0" in text,
        "secret_values_logged": 0,
    }


def stage_packet_filter_helper(rootfs: Path) -> dict[str, Any]:
    helper_target = rootfs / TARGET_PACKET_FILTER
    if not DPUBLIC_PACKET_FILTER.is_file():
        raise FileNotFoundError(DPUBLIC_PACKET_FILTER)
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DPUBLIC_PACKET_FILTER, helper_target)
    helper_target.chmod(0o755)
    text = helper_target.read_text(encoding="utf-8")
    return {
        "helper_target": str(TARGET_PACKET_FILTER),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "latest_helper_staged": True,
        "preflight_op_present": "preflight)" in text and "packet-filter-preflight-pass" in text,
        "apply_op_present": "apply-loopback-default-drop)" in text
        and "packet-filter-loopback-default-drop-applied" in text,
        "restore_op_present": "restore)" in text and "packet-filter-restored" in text,
        "save_before_apply_present": "save_current_rules" in text and "packet_filter_saved_before=1" in text,
        "failure_restore_present": "packet-filter-apply-failed-restored" in text,
        "loopback_accept_present": "-A INPUT -i lo -j ACCEPT" in text,
        "default_drop_present": ":INPUT DROP" in text and ":FORWARD DROP" in text,
        "output_accept_present": ":OUTPUT ACCEPT" in text,
        "auto_apply_absent": "packet_filter_apply_autostart=0" in text,
        "secret_hygiene_marker": "packet_filter_secret_values_logged=0" in text,
        "secret_values_logged": 0,
    }


def stage_native_uplink_stage_marker(rootfs: Path) -> dict[str, Any]:
    marker = rootfs / TARGET_STAGE_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    existing = marker.read_text(encoding="utf-8") if marker.exists() else ""
    marker_keys = {item.split("=", 1)[0] for item in NATIVE_UPLINK_STAGE_MARKERS}
    lines = [
        line
        for line in existing.splitlines()
        if not any(line.startswith(key + "=") for key in marker_keys)
    ]
    for item in NATIVE_UPLINK_STAGE_MARKERS:
        lines.append(item)
    marker.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return {
        "marker_target": str(TARGET_STAGE_MARKER),
        "profile_marker_present": NATIVE_UPLINK_STAGE_MARKERS[0] in lines,
        "operator_control_marker_present": NATIVE_UPLINK_STAGE_MARKERS[1] in lines,
        "public_default_off_marker": any(line.startswith("public-exposure-default=off") for line in lines),
        "secret_values_logged": 0,
    }


def stage_packet_filter_stage_marker(rootfs: Path) -> dict[str, Any]:
    marker = rootfs / TARGET_STAGE_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    existing = marker.read_text(encoding="utf-8") if marker.exists() else ""
    marker_keys = {item.split("=", 1)[0] for item in PACKET_FILTER_STAGE_MARKERS}
    lines = [
        line
        for line in existing.splitlines()
        if not any(line.startswith(key + "=") for key in marker_keys)
    ]
    for item in PACKET_FILTER_STAGE_MARKERS:
        lines.append(item)
    marker.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return {
        "marker_target": str(TARGET_STAGE_MARKER),
        "backend_marker_present": PACKET_FILTER_STAGE_MARKERS[0] in lines,
        "helper_marker_present": PACKET_FILTER_STAGE_MARKERS[1] in lines,
        "tools_marker_present": PACKET_FILTER_STAGE_MARKERS[2] in lines,
        "policy_not_enforced_marker_present": PACKET_FILTER_STAGE_MARKERS[3] in lines,
        "default_drop_deferred_marker_present": PACKET_FILTER_STAGE_MARKERS[4] in lines,
        "secret_values_logged": 0,
    }


def stage_syscall_trace_stage_marker(rootfs: Path) -> dict[str, Any]:
    marker = rootfs / TARGET_STAGE_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    existing = marker.read_text(encoding="utf-8") if marker.exists() else ""
    marker_keys = {item.split("=", 1)[0] for item in SYSCALL_TRACE_STAGE_MARKERS}
    lines = [
        line
        for line in existing.splitlines()
        if not any(line.startswith(key + "=") for key in marker_keys)
    ]
    for item in SYSCALL_TRACE_STAGE_MARKERS:
        lines.append(item)
    marker.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return {
        "marker_target": str(TARGET_STAGE_MARKER),
        "tool_marker_present": SYSCALL_TRACE_STAGE_MARKERS[0] in lines,
        "target_marker_present": SYSCALL_TRACE_STAGE_MARKERS[1] in lines,
        "profile_deferred_marker_present": SYSCALL_TRACE_STAGE_MARKERS[2] in lines,
        "public_default_off_marker": SYSCALL_TRACE_STAGE_MARKERS[3] in lines,
        "secret_values_logged": 0,
    }


def account_by_name(lines: list[str], name: str) -> list[str] | None:
    for line in lines:
        if line.split(":", 1)[0] == name:
            return line.split(":")
    return None


def ensure_account_line(lines: list[str], expected: str, name: str, field_count: int) -> bool:
    existing = account_by_name(lines, name)
    if existing is None:
        lines.append(expected)
        return True
    if len(existing) != field_count or ":".join(existing) != expected:
        raise ValueError(f"conflicting account entry for {name}")
    return False


def stage_service_identities(rootfs: Path) -> dict[str, Any]:
    etc = rootfs / "etc"
    etc.mkdir(parents=True, exist_ok=True)
    passwd = etc / "passwd"
    group = etc / "group"
    passwd_lines = passwd.read_text(encoding="utf-8").splitlines() if passwd.exists() else []
    group_lines = group.read_text(encoding="utf-8").splitlines() if group.exists() else []
    users_added: list[str] = []
    groups_added: list[str] = []
    for identity in SERVICE_IDENTITIES.values():
        group_line = f"{identity['group']}:x:{identity['gid']}:"
        if ensure_account_line(group_lines, group_line, str(identity["group"]), 4):
            groups_added.append(str(identity["group"]))
        passwd_line = (
            f"{identity['user']}:x:{identity['uid']}:{identity['gid']}:"
            f"A90 service {identity['user']}:/nonexistent:/usr/sbin/nologin"
        )
        if ensure_account_line(passwd_lines, passwd_line, str(identity["user"]), 7):
            users_added.append(str(identity["user"]))
    passwd.write_text("\n".join(passwd_lines).rstrip("\n") + "\n", encoding="utf-8")
    group.write_text("\n".join(group_lines).rstrip("\n") + "\n", encoding="utf-8")
    passwd.chmod(0o644)
    group.chmod(0o644)
    return {
        "passwd_target": "etc/passwd",
        "group_target": "etc/group",
        "users": sorted(identity["user"] for identity in SERVICE_IDENTITIES.values()),
        "groups": sorted(identity["group"] for identity in SERVICE_IDENTITIES.values()),
        "users_added": users_added,
        "groups_added": groups_added,
        "root_boundary_services": list(ROOT_BOUNDARY_SERVICES),
        "secret_values_logged": 0,
    }


def launcher_script() -> str:
    cases = []
    for service, identity in SERVICE_IDENTITIES.items():
        cases.extend([
            f"  {service})",
            f"    A90_USER={identity['user']}",
            f"    A90_GROUP={identity['group']}",
            f"    A90_NETWORK_INTENT={identity['network_intent']}",
            "    ;;",
        ])
    case_text = "\n".join(cases)
    return f"""#!/bin/sh
set -eu

seccomp_dry_run_gate() {{
  if [ "${{A90_SERVICE_LAUNCH_SECCOMP_DRY_RUN:-0}}" != "1" ]; then
    return 0
  fi
  policy_path="${{A90_SERVICE_LAUNCH_SECCOMP_POLICY:-/etc/a90-dpublic/seccomp-policy.json}}"
  map_path="${{A90_SERVICE_LAUNCH_SECCOMP_MAP:-/etc/a90-dpublic/seccomp-launcher-map.env}}"
  filter_manifest_path="${{A90_SERVICE_LAUNCH_SECCOMP_FILTER_MANIFEST:-/etc/a90-dpublic/seccomp-filter-manifest.json}}"
  filter_object_path="${{A90_SERVICE_LAUNCH_SECCOMP_FILTER_OBJECT:-/usr/lib/a90-dpublic/seccomp/wsta156_seccomp_filters.o}}"
  loader_helper_path="${{A90_SERVICE_LAUNCH_SECCOMP_LOADER_HELPER:-/usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly}}"
  loader_helper_check_only="${{A90_SERVICE_LAUNCH_SECCOMP_HELPER_CHECK_ONLY:-1}}"
  enforce_flag="${{A90_SERVICE_LAUNCH_SECCOMP_ENFORCE:-0}}"
  if [ ! -r "$policy_path" ]; then
    echo "a90_service_launcher_decision=blocked-seccomp-policy-missing"
    exit 65
  fi
  if [ ! -r "$map_path" ]; then
    echo "a90_service_launcher_decision=blocked-seccomp-map-missing"
    exit 65
  fi
  seccomp_policy_service=""
  seccomp_profile=""
  seccomp_allowlist_count=""
  while IFS=' ' read -r map_service map_policy_service map_profile map_count; do
    case "$map_service" in
      ""|"#"*) continue ;;
    esac
    if [ "$map_service" = "$SERVICE" ]; then
      seccomp_policy_service="$map_policy_service"
      seccomp_profile="$map_profile"
      seccomp_allowlist_count="$map_count"
      break
    fi
  done < "$map_path"
  if [ -z "$seccomp_profile" ]; then
    echo "a90_service_launcher_decision=blocked-seccomp-profile-missing"
    exit 65
  fi
  if [ -z "$seccomp_allowlist_count" ] || [ "$seccomp_allowlist_count" = "0" ]; then
    echo "a90_service_launcher_decision=blocked-seccomp-allowlist-empty"
    exit 65
  fi
  echo "A90WSTA154_SECCOMP_POLICY_PRESENT=1"
  echo "A90WSTA154_SECCOMP_DRY_RUN_ONLY=1"
  echo "A90WSTA154_SECCOMP_FILTER_LOAD=0"
  echo "A90WSTA154_SECCOMP_SERVICE=$SERVICE"
  echo "A90WSTA154_SECCOMP_POLICY_SERVICE=$seccomp_policy_service"
  echo "A90WSTA154_SECCOMP_PROFILE=$seccomp_profile"
  echo "A90WSTA154_SECCOMP_ALLOWLIST_COUNT=$seccomp_allowlist_count"
  if [ -r "$filter_manifest_path" ] && [ -r "$filter_object_path" ]; then
    echo "A90WSTA157_SECCOMP_ARTIFACT_PRESENT=1"
  else
    echo "A90WSTA157_SECCOMP_ARTIFACT_PRESENT=0"
  fi
  echo "A90WSTA157_SECCOMP_ENFORCE_FLAG=$enforce_flag"
  if [ -x "$loader_helper_path" ]; then
    echo "A90WSTA159_SECCOMP_HELPER_PRESENT=1"
  else
    echo "A90WSTA159_SECCOMP_HELPER_PRESENT=0"
  fi
  echo "A90WSTA159_SECCOMP_HELPER_CHECK_ONLY=$loader_helper_check_only"
  if [ "$enforce_flag" = "1" ]; then
    if [ "$loader_helper_check_only" != "1" ]; then
      echo "a90_service_launcher_decision=blocked-seccomp-helper-check-only-required"
      exit 65
    fi
    if [ -x "$loader_helper_path" ]; then
      if "$loader_helper_path" --service "$SERVICE" --check-only; then
        echo "A90WSTA159_SECCOMP_HELPER_CHECK_ONLY_OK=1"
      else
        echo "a90_service_launcher_decision=blocked-seccomp-helper-check-failed"
        exit 65
      fi
    fi
    echo "a90_service_launcher_decision=blocked-seccomp-enforce-unimplemented"
    exit 65
  fi
}}

SERVICE="${{1:-}}"
if [ -z "$SERVICE" ]; then
  echo "a90_service_launcher_decision=blocked-service-required"
  exit 64
fi
shift
case "$SERVICE" in
{case_text}
  *)
    echo "a90_service_launcher_decision=blocked-unknown-service"
    exit 64
    ;;
esac
if [ "$#" -lt 1 ]; then
  echo "a90_service_launcher_decision=blocked-command-required"
  exit 64
fi
if ! command -v setpriv >/dev/null 2>&1; then
  echo "a90_service_launcher_decision=blocked-setpriv-missing"
  exit 127
fi
seccomp_dry_run_gate
echo "a90_service_launcher_decision=exec"
echo "a90_service_launcher_service=$SERVICE"
echo "a90_service_launcher_user=$A90_USER"
echo "a90_service_launcher_network_intent=$A90_NETWORK_INTENT"
echo "a90_service_launcher_no_new_privs=1"
exec setpriv --no-new-privs --reuid "$A90_USER" --regid "$A90_GROUP" --init-groups -- "$@"
"""


def stage_no_new_privs_launcher(rootfs: Path) -> dict[str, Any]:
    launcher = rootfs / TARGET_SERVICE_LAUNCHER
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(launcher_script(), encoding="utf-8")
    launcher.chmod(0o755)
    text = launcher.read_text(encoding="utf-8")
    return {
        "launcher_target": str(TARGET_SERVICE_LAUNCHER),
        "launcher_mode": oct(launcher.stat().st_mode & 0o777),
        "setpriv_required": "command -v setpriv" in text,
        "no_new_privs_present": "--no-new-privs" in text,
        "seccomp_dry_run_gate_present": "seccomp_dry_run_gate" in text,
        "seccomp_policy_missing_blocks": "blocked-seccomp-policy-missing" in text,
        "seccomp_filter_load_disabled_marker_present": "A90WSTA154_SECCOMP_FILTER_LOAD=0" in text,
        "seccomp_artifact_present_marker_present": "A90WSTA157_SECCOMP_ARTIFACT_PRESENT" in text,
        "seccomp_enforce_unimplemented_blocks": "blocked-seccomp-enforce-unimplemented" in text,
        "seccomp_loader_helper_marker_present": "A90WSTA159_SECCOMP_HELPER_PRESENT" in text,
        "seccomp_helper_check_only_marker_present": "A90WSTA159_SECCOMP_HELPER_CHECK_ONLY" in text,
        "seccomp_helper_check_call_present": "--service \"$SERVICE\" --check-only" in text,
        "unknown_service_blocks": "blocked-unknown-service" in text,
        "command_required_blocks": "blocked-command-required" in text,
        "service_count": len(SERVICE_IDENTITIES),
        "root_boundary_services": list(ROOT_BOUNDARY_SERVICES),
        "secret_values_logged": 0,
    }


def stage_service_hardening_policy(rootfs: Path) -> dict[str, Any]:
    policy_target = rootfs / TARGET_SERVICE_HARDENING_POLICY
    policy_target.parent.mkdir(parents=True, exist_ok=True)
    services = {
        service: {
            "user": identity["user"],
            "group": identity["group"],
            "uid": identity["uid"],
            "gid": identity["gid"],
            "network_intent": identity["network_intent"],
            "no_new_privs": True,
            "ambient_capabilities": [],
            "bounding_capabilities": [],
        }
        for service, identity in SERVICE_IDENTITIES.items()
    }
    payload = {
        "schema": "a90-service-hardening-v1",
        "default_public_off": True,
        "launcher": str(TARGET_SERVICE_LAUNCHER),
        "launcher_requires": ["setpriv", "no-new-privs"],
        "seccomp": {
            "policy": str(TARGET_SECCOMP_POLICY),
            "launcher_map": str(TARGET_SECCOMP_LAUNCHER_MAP),
            "filter_manifest": str(TARGET_SECCOMP_FILTER_MANIFEST),
            "filter_object": str(TARGET_SECCOMP_FILTER_OBJECT),
            "loader_helper_manifest": str(TARGET_SECCOMP_LOADER_HELPER_MANIFEST),
            "loader_helper": str(TARGET_SECCOMP_LOADER_HELPER),
            "mode": "dry-run-before-filter-load",
            "filter_load_enabled": False,
            "enforced": False,
            "enforce_flag": "A90_SERVICE_LAUNCH_SECCOMP_ENFORCE=1",
            "enforce_default": False,
            "loader_helper_check_only_default": True,
        },
        "services": services,
        "root_boundary_services": list(ROOT_BOUNDARY_SERVICES),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    write_json(policy_target, payload)
    policy_target.chmod(0o644)
    return {
        "policy_target": str(TARGET_SERVICE_HARDENING_POLICY),
        "policy_mode": oct(policy_target.stat().st_mode & 0o777),
        "service_count": len(services),
        "default_public_off": True,
        "no_new_privs_default": True,
        "ambient_capabilities_default": [],
        "secret_values_logged": 0,
    }


def load_seccomp_policy_source(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def seccomp_policy_services(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    services = policy.get("services") if isinstance(policy.get("services"), list) else []
    return {
        str(item.get("service")): item
        for item in services
        if isinstance(item, dict) and item.get("service")
    }


def validate_seccomp_policy_source(policy: dict[str, Any]) -> dict[str, bool]:
    services = seccomp_policy_services(policy)
    return {
        "schema_ok": policy.get("schema") == "a90-wsta153-seccomp-policy-source-v1",
        "state_ok": policy.get("state") == "SECCOMP_POLICY_DRAFT_FROM_LIVE_BASELINES",
        "source_only_not_enforced": policy.get("enforcement_state") == "SOURCE_ONLY_NOT_ENFORCED",
        "expected_services_present": set(services) == set(SECCOMP_LAUNCHER_BINDINGS.values()),
        "all_profiles_default_deny": all(
            item.get("deny_by_default") is True
            and item.get("default_action") == "ERRNO(EPERM)"
            for item in services.values()
        ),
        "all_allowlists_nonempty": all(
            isinstance(item.get("allowlist"), list)
            and bool(item.get("allowlist"))
            and item.get("allowlist_count") == len(item.get("allowlist", []))
            for item in services.values()
        ),
        "all_profiles_not_enforced": all(
            isinstance(item.get("enforcement"), dict)
            and item["enforcement"].get("enabled") is False
            for item in services.values()
        ),
        "redaction_clean": policy.get("redaction", {}).get("public_url_value_logged") is False
        and policy.get("redaction", {}).get("secret_values_logged") == 0,
    }


def seccomp_launcher_map_text(policy: dict[str, Any]) -> str:
    services = seccomp_policy_services(policy)
    lines = [
        "# launcher_service policy_service profile_name allowlist_count",
    ]
    for launcher_service, policy_service in SECCOMP_LAUNCHER_BINDINGS.items():
        profile = services[policy_service]
        lines.append(
            " ".join([
                launcher_service,
                policy_service,
                str(profile.get("profile_name")),
                str(profile.get("allowlist_count")),
            ])
        )
    return "\n".join(lines).rstrip("\n") + "\n"


def stage_seccomp_launcher_policy(rootfs: Path,
                                  source: Path | None,
                                  *,
                                  require: bool = False) -> dict[str, Any]:
    if source is None or not source.is_file():
        return {
            "staged": False,
            "required": require,
            "reason": "seccomp-policy-source-missing",
            "policy_target": str(TARGET_SECCOMP_POLICY),
            "map_target": str(TARGET_SECCOMP_LAUNCHER_MAP),
            "filter_load_enabled": False,
            "seccomp_enforced": False,
            "secret_values_logged": 0,
        }
    policy = load_seccomp_policy_source(source)
    checks = validate_seccomp_policy_source(policy)
    if not all(checks.values()):
        if require:
            raise ValueError(f"invalid seccomp policy source: {checks}")
        return {
            "staged": False,
            "required": require,
            "reason": "seccomp-policy-source-invalid",
            "checks": checks,
            "filter_load_enabled": False,
            "seccomp_enforced": False,
            "secret_values_logged": 0,
        }
    policy_target = rootfs / TARGET_SECCOMP_POLICY
    map_target = rootfs / TARGET_SECCOMP_LAUNCHER_MAP
    write_json(policy_target, policy)
    policy_target.chmod(0o644)
    map_target.parent.mkdir(parents=True, exist_ok=True)
    map_target.write_text(seccomp_launcher_map_text(policy), encoding="utf-8")
    map_target.chmod(0o644)
    return {
        "staged": True,
        "required": require,
        "source": rel(source),
        "policy_target": str(TARGET_SECCOMP_POLICY),
        "policy_mode": oct(policy_target.stat().st_mode & 0o777),
        "map_target": str(TARGET_SECCOMP_LAUNCHER_MAP),
        "map_mode": oct(map_target.stat().st_mode & 0o777),
        "service_binding_count": len(SECCOMP_LAUNCHER_BINDINGS),
        "hud_maps_to_intent": SECCOMP_LAUNCHER_BINDINGS["dpublic-hud"] == "dpublic-hud-intent",
        "filter_load_enabled": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "checks": checks,
        "dry_run_markers": [
            "A90WSTA154_SECCOMP_POLICY_PRESENT=1",
            "A90WSTA154_SECCOMP_DRY_RUN_ONLY=1",
            "A90WSTA154_SECCOMP_FILTER_LOAD=0",
        ],
        "secret_values_logged": 0,
    }


def load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def validate_seccomp_filter_manifest(manifest: dict[str, Any], object_path: Path) -> dict[str, bool]:
    services = manifest.get("services") if isinstance(manifest.get("services"), list) else []
    expected_object_sha = (
        manifest.get("artifact_sha256", {}).get("object")
        if isinstance(manifest.get("artifact_sha256"), dict)
        else None
    )
    return {
        "schema_ok": manifest.get("schema") == "a90-wsta156-seccomp-nonloaded-filter-artifact-v1",
        "state_compiled_not_loaded": manifest.get("state") == "SECCOMP_FILTER_ARTIFACT_COMPILED_NOT_LOADED",
        "source_policy_is_wsta153": manifest.get("source_policy_schema") == "a90-wsta153-seccomp-policy-source-v1",
        "source_policy_not_enforced": manifest.get("source_policy_enforcement_state") == "SOURCE_ONLY_NOT_ENFORCED",
        "service_count_four": len(services) == 4,
        "all_missing_syscalls_empty": all(
            isinstance(item, dict) and item.get("missing_syscalls") == []
            for item in services
        ),
        "all_instruction_counts_nonzero": all(
            isinstance(item, dict)
            and isinstance(item.get("instruction_count"), int)
            and item.get("instruction_count") > 0
            for item in services
        ),
        "loaded_false": manifest.get("loaded") is False,
        "enforced_false": manifest.get("enforced") is False,
        "object_present": object_path.is_file(),
        "object_sha_matches_manifest": (
            object_path.is_file()
            and isinstance(expected_object_sha, str)
            and sha256_file(object_path) == expected_object_sha
        ),
        "redaction_clean": manifest.get("redaction", {}).get("public_url_value_logged") is False
        and manifest.get("redaction", {}).get("secret_values_logged") == 0,
    }


def stage_seccomp_filter_artifact(rootfs: Path,
                                  manifest_source: Path | None,
                                  object_source: Path | None,
                                  *,
                                  require: bool = False) -> dict[str, Any]:
    if (
        manifest_source is None
        or object_source is None
        or not manifest_source.is_file()
        or not object_source.is_file()
    ):
        return {
            "staged": False,
            "required": require,
            "reason": "seccomp-filter-artifact-missing",
            "manifest_target": str(TARGET_SECCOMP_FILTER_MANIFEST),
            "object_target": str(TARGET_SECCOMP_FILTER_OBJECT),
            "filter_load_enabled": False,
            "seccomp_enforced": False,
            "secret_values_logged": 0,
        }
    manifest = load_json_object(manifest_source)
    checks = validate_seccomp_filter_manifest(manifest, object_source)
    if not all(checks.values()):
        if require:
            raise ValueError(f"invalid seccomp filter artifact: {checks}")
        return {
            "staged": False,
            "required": require,
            "reason": "seccomp-filter-artifact-invalid",
            "checks": checks,
            "filter_load_enabled": False,
            "seccomp_enforced": False,
            "secret_values_logged": 0,
        }
    manifest_target = rootfs / TARGET_SECCOMP_FILTER_MANIFEST
    object_target = rootfs / TARGET_SECCOMP_FILTER_OBJECT
    write_json(manifest_target, manifest)
    manifest_target.chmod(0o644)
    object_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(object_source, object_target)
    object_target.chmod(0o644)
    return {
        "staged": True,
        "required": require,
        "manifest_source": rel(manifest_source),
        "object_source": rel(object_source),
        "manifest_target": str(TARGET_SECCOMP_FILTER_MANIFEST),
        "manifest_mode": oct(manifest_target.stat().st_mode & 0o777),
        "object_target": str(TARGET_SECCOMP_FILTER_OBJECT),
        "object_mode": oct(object_target.stat().st_mode & 0o777),
        "service_count": manifest.get("service_count"),
        "object_sha256": sha256_file(object_target),
        "filter_load_enabled": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "enforce_default": False,
        "enforce_flag": "A90_SERVICE_LAUNCH_SECCOMP_ENFORCE=1",
        "checks": checks,
        "dry_run_markers": [
            "A90WSTA157_SECCOMP_ARTIFACT_PRESENT=1",
            "A90WSTA157_SECCOMP_ENFORCE_FLAG=0",
        ],
        "secret_values_logged": 0,
    }


def validate_seccomp_loader_helper_manifest(manifest: dict[str, Any], helper_path: Path) -> dict[str, bool]:
    expected_sha = manifest.get("helper_sha256")
    schema = manifest.get("schema")
    is_wsta158 = schema == "a90-wsta158-seccomp-loader-checkonly-helper-v1"
    is_wsta161 = schema == "a90-wsta161-seccomp-loader-gated-apply-helper-v1"
    return {
        "schema_ok": is_wsta158 or is_wsta161,
        "state_ok": (
            (is_wsta158 and manifest.get("state") == "SECCOMP_LOADER_HELPER_CHECK_ONLY_LINKED")
            or (is_wsta161 and manifest.get("state") == "SECCOMP_LOADER_GATED_APPLY_COMPILED_NOT_LOADED")
        ),
        "default_check_only": manifest.get("default_mode") == "check-only",
        "load_disabled": (
            (is_wsta158 and manifest.get("load_enabled") is False)
            or (is_wsta161 and manifest.get("default_load_enabled") is False)
        ),
        "loaded_false": (not is_wsta161) or manifest.get("loaded") is False,
        "enforced_false": manifest.get("enforced") is False,
        "gated_apply_shape_ok": (not is_wsta161) or manifest.get("apply_code_compiled") is True,
        "helper_present": helper_path.is_file(),
        "helper_sha_matches_manifest": (
            helper_path.is_file()
            and isinstance(expected_sha, str)
            and sha256_file(helper_path) == expected_sha
        ),
        "helper_manifest_says_aarch64_static": "ELF 64-bit LSB executable, ARM aarch64" in str(
            manifest.get("helper_file")
        )
        and "statically linked" in str(manifest.get("helper_file")),
        "redaction_clean": manifest.get("redaction", {}).get("public_url_value_logged") is False
        and manifest.get("redaction", {}).get("secret_values_logged") == 0,
    }


def stage_seccomp_loader_helper(rootfs: Path,
                                manifest_source: Path | None,
                                helper_source: Path | None,
                                *,
                                require: bool = False) -> dict[str, Any]:
    if (
        manifest_source is None
        or helper_source is None
        or not manifest_source.is_file()
        or not helper_source.is_file()
    ):
        return {
            "staged": False,
            "required": require,
            "reason": "seccomp-loader-helper-missing",
            "manifest_target": str(TARGET_SECCOMP_LOADER_HELPER_MANIFEST),
            "helper_target": str(TARGET_SECCOMP_LOADER_HELPER),
            "check_only": True,
            "filter_load_enabled": False,
            "seccomp_enforced": False,
            "secret_values_logged": 0,
        }
    manifest = load_json_object(manifest_source)
    checks = validate_seccomp_loader_helper_manifest(manifest, helper_source)
    if not all(checks.values()):
        if require:
            raise ValueError(f"invalid seccomp loader helper: {checks}")
        return {
            "staged": False,
            "required": require,
            "reason": "seccomp-loader-helper-invalid",
            "checks": checks,
            "check_only": True,
            "filter_load_enabled": False,
            "seccomp_enforced": False,
            "secret_values_logged": 0,
        }
    manifest_target = rootfs / TARGET_SECCOMP_LOADER_HELPER_MANIFEST
    helper_target = rootfs / TARGET_SECCOMP_LOADER_HELPER
    write_json(manifest_target, manifest)
    manifest_target.chmod(0o644)
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(helper_source, helper_target)
    helper_target.chmod(0o755)
    return {
        "staged": True,
        "required": require,
        "manifest_source": rel(manifest_source),
        "helper_source": rel(helper_source),
        "helper_schema": manifest.get("schema"),
        "apply_code_compiled": manifest.get("apply_code_compiled") is True,
        "manifest_target": str(TARGET_SECCOMP_LOADER_HELPER_MANIFEST),
        "manifest_mode": oct(manifest_target.stat().st_mode & 0o777),
        "helper_target": str(TARGET_SECCOMP_LOADER_HELPER),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "helper_sha256": sha256_file(helper_target),
        "check_only": True,
        "filter_load_enabled": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "checks": checks,
        "dry_run_markers": [
            "A90WSTA159_SECCOMP_HELPER_PRESENT=1",
            "A90WSTA159_SECCOMP_HELPER_CHECK_ONLY=1",
        ],
        "secret_values_logged": 0,
    }


def stage_service_hardening_stage_marker(rootfs: Path) -> dict[str, Any]:
    marker = rootfs / TARGET_STAGE_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    existing = marker.read_text(encoding="utf-8") if marker.exists() else ""
    marker_keys = {item.split("=", 1)[0] for item in SERVICE_HARDENING_STAGE_MARKERS}
    lines = [
        line
        for line in existing.splitlines()
        if not any(line.startswith(key + "=") for key in marker_keys)
    ]
    for item in SERVICE_HARDENING_STAGE_MARKERS:
        lines.append(item)
    marker.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return {
        "marker_target": str(TARGET_STAGE_MARKER),
        "users_marker_present": SERVICE_HARDENING_STAGE_MARKERS[0] in lines,
        "launcher_marker_present": SERVICE_HARDENING_STAGE_MARKERS[1] in lines,
        "no_new_privs_marker_present": SERVICE_HARDENING_STAGE_MARKERS[2] in lines,
        "root_boundary_marker_present": SERVICE_HARDENING_STAGE_MARKERS[3] in lines,
        "public_default_off_marker": SERVICE_HARDENING_STAGE_MARKERS[4] in lines,
        "seccomp_policy_marker_present": SERVICE_HARDENING_STAGE_MARKERS[5] in lines,
        "seccomp_dry_run_marker_present": SERVICE_HARDENING_STAGE_MARKERS[6] in lines,
        "seccomp_filter_disabled_marker_present": SERVICE_HARDENING_STAGE_MARKERS[7] in lines,
        "seccomp_filter_manifest_marker_present": SERVICE_HARDENING_STAGE_MARKERS[8] in lines,
        "seccomp_enforce_default_off_marker_present": SERVICE_HARDENING_STAGE_MARKERS[9] in lines,
        "seccomp_loader_helper_marker_present": SERVICE_HARDENING_STAGE_MARKERS[10] in lines,
        "secret_values_logged": 0,
    }


def stage_hud_split_stage_marker(rootfs: Path) -> dict[str, Any]:
    marker = rootfs / TARGET_STAGE_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    existing = marker.read_text(encoding="utf-8") if marker.exists() else ""
    marker_keys = {item.split("=", 1)[0] for item in HUD_SPLIT_STAGE_MARKERS}
    lines = [
        line
        for line in existing.splitlines()
        if not any(line.startswith(key + "=") for key in marker_keys)
    ]
    for item in HUD_SPLIT_STAGE_MARKERS:
        lines.append(item)
    marker.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return {
        "marker_target": str(TARGET_STAGE_MARKER),
        "intent_producer_marker_present": HUD_SPLIT_STAGE_MARKERS[0] in lines,
        "presenter_marker_present": HUD_SPLIT_STAGE_MARKERS[1] in lines,
        "boundary_marker_present": HUD_SPLIT_STAGE_MARKERS[2] in lines,
        "direct_kms_disabled_marker_present": HUD_SPLIT_STAGE_MARKERS[3] in lines,
        "presenter_owner_marker_present": HUD_SPLIT_STAGE_MARKERS[4] in lines,
        "public_default_off_marker": HUD_SPLIT_STAGE_MARKERS[5] in lines,
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
        "hud_split_intent_invoked": "/usr/local/bin/a90-dpublic-hud-intent" in text,
        "hud_split_intent_run_dir_group_prepared": "chgrp a90hud /run/a90-dpublic" in text,
        "hud_split_intent_run_dir_sticky_group_write": "chmod 1770 /run/a90-dpublic" in text,
        "hud_split_presenter_not_started_by_debian": "hud_presenter_started=0" in text,
        "legacy_direct_hud_fallback_only": "hud_legacy_direct_kms_fallback=1" in text,
        "native_uplink_profile_marker": "native_uplink_profile_command=/usr/local/bin/a90-dpublic-native-uplink-profile" in text,
        "public_default_off_marker": "native_uplink_public_default=off" in text,
        "secret_values_logged": 0,
    }


def stage_dpublic_binaries(rootfs: Path, args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "cloudflared": args.cloudflared,
        "smoke_httpd": args.smoke_httpd,
        "http_get": args.http_get,
        "hud": args.hud,
        "hud_intent": args.hud_intent,
        "hud_presenter": args.hud_presenter,
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
    result["packet_filter_tools"] = ensure_packet_filter_tools(target_rootfs, args)
    if not result["packet_filter_tools"].get("ok"):
        result.update({
            "ok": False,
            "decision": "wsta3-private-rootfs-blocked-packet-filter-tools-missing",
        })
        write_json(run_dir / "summary.json", result)
        return result
    result["syscall_trace_tools"] = ensure_syscall_trace_tools(target_rootfs, args)
    if not result["syscall_trace_tools"].get("ok"):
        result.update({
            "ok": False,
            "decision": "wsta3-private-rootfs-blocked-syscall-trace-tools-missing",
        })
        write_json(run_dir / "summary.json", result)
        return result
    result["wifi_sta_helper"] = stage_dpublic_wifi_sta_helper(target_rootfs)
    result["api_probe_helper"] = stage_dpublic_api_probe_helper(target_rootfs)
    result["native_wifi_service_client"] = stage_native_wifi_service_client(target_rootfs)
    result["native_wifi_uplink_client"] = stage_native_wifi_uplink_client(target_rootfs)
    result["native_uplink_profile"] = stage_native_uplink_profile(target_rootfs)
    result["packet_filter_helper"] = stage_packet_filter_helper(target_rootfs)
    result["native_uplink_stage_marker"] = stage_native_uplink_stage_marker(target_rootfs)
    result["packet_filter_stage_marker"] = stage_packet_filter_stage_marker(target_rootfs)
    result["syscall_trace_stage_marker"] = stage_syscall_trace_stage_marker(target_rootfs)
    result["service_identities"] = stage_service_identities(target_rootfs)
    result["service_launcher"] = stage_no_new_privs_launcher(target_rootfs)
    result["service_hardening_policy"] = stage_service_hardening_policy(target_rootfs)
    result["seccomp_launcher_policy"] = stage_seccomp_launcher_policy(
        target_rootfs,
        getattr(args, "seccomp_policy_source", None),
        require=bool(getattr(args, "require_seccomp_policy_source", False)),
    )
    if getattr(args, "require_seccomp_policy_source", False) and not result["seccomp_launcher_policy"].get("staged"):
        result.update({
            "ok": False,
            "decision": "wsta3-private-rootfs-blocked-seccomp-policy-source-missing",
        })
        write_json(run_dir / "summary.json", result)
        return result
    result["seccomp_filter_artifact"] = stage_seccomp_filter_artifact(
        target_rootfs,
        getattr(args, "seccomp_filter_manifest", None),
        getattr(args, "seccomp_filter_object", None),
        require=bool(getattr(args, "require_seccomp_filter_artifact", False)),
    )
    if getattr(args, "require_seccomp_filter_artifact", False) and not result["seccomp_filter_artifact"].get("staged"):
        result.update({
            "ok": False,
            "decision": "wsta3-private-rootfs-blocked-seccomp-filter-artifact-missing",
        })
        write_json(run_dir / "summary.json", result)
        return result
    result["seccomp_loader_helper"] = stage_seccomp_loader_helper(
        target_rootfs,
        getattr(args, "seccomp_loader_helper_manifest", None),
        getattr(args, "seccomp_loader_helper", None),
        require=bool(getattr(args, "require_seccomp_loader_helper", False)),
    )
    if getattr(args, "require_seccomp_loader_helper", False) and not result["seccomp_loader_helper"].get("staged"):
        result.update({
            "ok": False,
            "decision": "wsta3-private-rootfs-blocked-seccomp-loader-helper-missing",
        })
        write_json(run_dir / "summary.json", result)
        return result
    result["service_hardening_stage_marker"] = stage_service_hardening_stage_marker(target_rootfs)
    result["hud_split_stage_marker"] = stage_hud_split_stage_marker(target_rootfs)
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
    parser.add_argument("--no-packet-filter-tool-install", action="store_true")
    parser.add_argument("--stage-dpublic-binaries", action="store_true")
    parser.add_argument("--stage-api-probe-tools", action="store_true")
    parser.add_argument("--stage-syscall-trace-tools", action="store_true")
    parser.add_argument("--enable-quick-tunnel", action="store_true")
    parser.add_argument("--cloudflared", type=Path, default=DEFAULT_CLOUDFLARED)
    parser.add_argument("--smoke-httpd", type=Path, default=DEFAULT_SMOKE_HTTPD)
    parser.add_argument("--http-get", type=Path, default=DEFAULT_HTTP_GET)
    parser.add_argument("--hud", type=Path, default=DEFAULT_HUD)
    parser.add_argument("--hud-intent", type=Path, default=DEFAULT_HUD_INTENT)
    parser.add_argument("--hud-presenter", type=Path, default=DEFAULT_HUD_PRESENTER)
    parser.add_argument("--seccomp-policy-source", type=Path, default=DEFAULT_SECCOMP_POLICY_SOURCE)
    parser.add_argument("--require-seccomp-policy-source", action="store_true")
    parser.add_argument("--seccomp-filter-manifest", type=Path, default=DEFAULT_SECCOMP_FILTER_MANIFEST)
    parser.add_argument("--seccomp-filter-object", type=Path, default=DEFAULT_SECCOMP_FILTER_OBJECT)
    parser.add_argument("--require-seccomp-filter-artifact", action="store_true")
    parser.add_argument("--seccomp-loader-helper-manifest", type=Path, default=DEFAULT_SECCOMP_LOADER_HELPER_MANIFEST)
    parser.add_argument("--seccomp-loader-helper", type=Path, default=DEFAULT_SECCOMP_LOADER_HELPER)
    parser.add_argument("--require-seccomp-loader-helper", action="store_true")
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
    args.hud_intent = args.hud_intent.resolve()
    args.hud_presenter = args.hud_presenter.resolve()
    args.seccomp_policy_source = args.seccomp_policy_source.resolve()
    args.seccomp_filter_manifest = args.seccomp_filter_manifest.resolve()
    args.seccomp_filter_object = args.seccomp_filter_object.resolve()
    args.seccomp_loader_helper_manifest = args.seccomp_loader_helper_manifest.resolve()
    args.seccomp_loader_helper = args.seccomp_loader_helper.resolve()
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
