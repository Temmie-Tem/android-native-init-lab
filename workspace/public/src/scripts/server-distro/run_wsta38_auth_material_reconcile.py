#!/usr/bin/env python3
"""Run WSTA38 secret-safe Wi-Fi credential reconciliation.

This is a read-only diagnostic.  It compares the private host Wi-Fi env, the
known-good WSTA7 Debian supplicant config, and the resident native-generated
supplicant config without writing or printing SSID, PSK, PSK-hex, BSSID, IP, or
token values.  The output records only lengths, formats, and equality booleans.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WIFI_ENV = wsta3.DEFAULT_WIFI_ENV
DEFAULT_NATIVE_CONF = "/cache/a90-wifi/wpa_supplicant.conf"
DEFAULT_NATIVE_AUTOCONNECT_CONF = "/mnt/sdext/a90/config/wifi/autoconnect.conf"
DEFAULT_NATIVE_PROFILE_ROOT = "/mnt/sdext/a90/config/wifi/profiles"
DEFAULT_A90CTL = REPO_ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"
PASS_DECISION = "wsta38-credential-material-consistent"


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
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


def classify_psk(value: str) -> str:
    if re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return "hex64"
    if 8 <= len(value) <= 63:
        return "passphrase"
    return "invalid"


def pbkdf2_psk_hex(ssid: str, psk: str) -> str | None:
    if classify_psk(psk) == "hex64":
        return psk.lower()
    if classify_psk(psk) != "passphrase":
        return None
    return hashlib.pbkdf2_hmac(
        "sha1",
        psk.encode("utf-8"),
        ssid.encode("utf-8"),
        4096,
        32,
    ).hex()


def native_expected_ssid_hex(ssid: str) -> str:
    return ssid.encode("utf-8").hex()


def parse_wpa_quoted(value: str) -> str:
    if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
        return value
    out: list[str] = []
    escaped = False
    for ch in value[1:-1]:
        if escaped:
            out.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        else:
            out.append(ch)
    if escaped:
        out.append("\\")
    return "".join(out)


def parse_supplicant_config(text: str) -> dict[str, Any]:
    raw: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        raw[key.strip()] = value.strip()

    ssid_value = raw.get("ssid", "")
    psk_value = raw.get("psk", "")
    ssid_unquoted = parse_wpa_quoted(ssid_value)
    psk_unquoted = parse_wpa_quoted(psk_value)
    ssid_format = "quoted" if ssid_value.startswith('"') else (
        "hex" if re.fullmatch(r"[0-9a-fA-F]+", ssid_value or "") else "missing"
    )
    psk_format = "quoted-passphrase" if psk_value.startswith('"') else (
        "hex64" if re.fullmatch(r"[0-9a-fA-F]{64}", psk_value or "") else "missing"
    )
    return {
        "raw": raw,
        "ssid": ssid_unquoted,
        "psk": psk_unquoted,
        "metadata": {
            "has_network_block": "network={" in {line.strip() for line in text.splitlines()},
            "ctrl_interface_class": classify_ctrl_interface(raw.get("ctrl_interface", "")),
            "update_config": raw.get("update_config", "-"),
            "ap_scan": raw.get("ap_scan", "-"),
            "scan_ssid": raw.get("scan_ssid", "-"),
            "disabled": raw.get("disabled", "-"),
            "key_mgmt": raw.get("key_mgmt", "-"),
            "ssid_format": ssid_format,
            "ssid_len": len(ssid_unquoted.encode("utf-8")) if ssid_unquoted else 0,
            "psk_format": psk_format,
            "psk_len": len(psk_unquoted) if psk_unquoted else 0,
            "secret_values_logged": 0,
        },
    }


def parse_kv_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def redact_device_path_arg(path: str) -> str:
    if path.startswith(DEFAULT_NATIVE_PROFILE_ROOT + "/"):
        return DEFAULT_NATIVE_PROFILE_ROOT + "/<profile>.conf"
    secret_root = "/mnt/sdext/a90/secrets/wifi/"
    if path.startswith(secret_root):
        if path.endswith(".ssid"):
            return secret_root + "<profile>.ssid"
        if path.endswith(".psk"):
            return secret_root + "<profile>.psk"
        return secret_root + "<secret>"
    return path


def classify_ctrl_interface(value: str) -> str:
    if value == "/run/wpa_supplicant":
        return "run-wpa-supplicant"
    if value.startswith("DIR=/tmp/a90-wifi/sockets"):
        return "tmp-a90-wifi-sockets"
    if value.startswith("DIR="):
        return "dir-other"
    if value:
        return "other"
    return "missing"


def find_latest_wsta7_config() -> Path | None:
    candidates = sorted(DEFAULT_RUN_BASE.glob("wsta7-assoc-live-*/prepare/generated-wpa_supplicant-wlan0.conf"))
    return candidates[-1] if candidates else None


def redacted_wifi_env_status(path: Path, loaded: dict[str, Any]) -> dict[str, Any]:
    status: dict[str, Any] = {
        "path": rel(path),
        "exists": path.is_file(),
        "owner_private": wsta3.is_owner_private(path),
        "secret_values_logged": 0,
    }
    if not loaded.get("ok"):
        status.update({
            "ok": False,
            "reason": loaded.get("reason", "wifi-env-invalid"),
            "ssid_len": loaded.get("ssid_len"),
            "psk_len": loaded.get("psk_len"),
        })
        return status
    status.update({
        "ok": True,
        "reason": "ok",
        "ssid_present": True,
        "psk_present": True,
        "ssid_len": loaded.get("ssid_len"),
        "psk_len": loaded.get("psk_len"),
        "psk_format": classify_psk(str(loaded["psk"])),
    })
    return status


def read_text_private(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, ""
    return True, path.read_text(encoding="utf-8")


def extract_cmdv1_cat_payload(text: str) -> str:
    lines = text.splitlines()
    begin_index = None
    end_index = None
    for index, line in enumerate(lines):
        if line.startswith("A90P1 BEGIN "):
            begin_index = index
        elif line.startswith("[done] ") or line.startswith("A90P1 END "):
            end_index = index
            break
    if begin_index is None or end_index is None or end_index <= begin_index:
        return ""
    return "\n".join(lines[begin_index + 1:end_index]) + "\n"


def run_a90ctl_cat(args: argparse.Namespace, path: str) -> dict[str, Any]:
    command = [
        sys.executable,
        str(args.a90ctl),
        "--timeout",
        str(args.timeout),
        "cat",
        path,
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout + 5.0,
        check=False,
    )
    end_rc = None
    match = re.search(r"^A90P1 END .*\brc=([-0-9]+)\b", completed.stdout, re.MULTILINE)
    if match:
        end_rc = int(match.group(1), 10)
    payload = extract_cmdv1_cat_payload(completed.stdout)
    return {
        "returncode": completed.returncode,
        "end_rc": end_rc,
        "payload": payload,
        "metadata": {
            "command": [sys.executable, rel(args.a90ctl), "--timeout", str(args.timeout), "cat", redact_device_path_arg(path)],
            "returncode": completed.returncode,
            "end_rc": end_rc,
            "payload_present": bool(payload),
            "stderr_present": bool(completed.stderr.strip()),
            "secret_values_logged": 0,
        },
    }


def read_device_profile_material(args: argparse.Namespace) -> dict[str, Any]:
    autoconnect = run_a90ctl_cat(args, args.native_autoconnect_conf)
    autoconnect_kv = parse_kv_text(autoconnect.get("payload", ""))
    profile = autoconnect_kv.get("default_profile", "")
    profile_path = f"{args.native_profile_root}/{profile}.conf" if re.fullmatch(r"[A-Za-z0-9_.-]+", profile) else ""
    profile_read = run_a90ctl_cat(args, profile_path) if profile_path else {
        "payload": "",
        "metadata": {"payload_present": False, "secret_values_logged": 0},
    }
    profile_kv = parse_kv_text(profile_read.get("payload", ""))

    ssid_file = profile_kv.get("ssid_file", "")
    psk_file = profile_kv.get("psk_file", "")
    ssid_read = run_a90ctl_cat(args, ssid_file) if ssid_file.startswith("/") else {
        "payload": "",
        "metadata": {"payload_present": False, "secret_values_logged": 0},
    }
    psk_read = run_a90ctl_cat(args, psk_file) if psk_file.startswith("/") else {
        "payload": "",
        "metadata": {"payload_present": False, "secret_values_logged": 0},
    }
    ssid_secret = ssid_read.get("payload", "").strip("\r\n")
    psk_secret = psk_read.get("payload", "").strip("\r\n")
    return {
        "raw": {
            "ssid": ssid_secret,
            "psk": psk_secret,
        },
        "metadata": {
            "autoconnect_read": autoconnect["metadata"],
            "profile_read": profile_read["metadata"],
            "ssid_secret_read": {
                **ssid_read["metadata"],
                "secret_len": len(ssid_secret.encode("utf-8")) if ssid_secret else 0,
            },
            "psk_secret_read": {
                **psk_read["metadata"],
                "secret_len": len(psk_secret) if psk_secret else 0,
            },
            "default_profile_present": bool(profile),
            "profile_path_present": bool(profile_path),
            "key_mgmt": profile_kv.get("key_mgmt", "-"),
            "ssid_file_configured": bool(ssid_file),
            "psk_file_configured": bool(psk_file),
            "secret_values_logged": 0,
        },
    }


def compare_material(env: dict[str, Any],
                     wsta7_config: dict[str, Any] | None,
                     native_config: dict[str, Any] | None,
                     device_profile: dict[str, Any] | None) -> dict[str, Any]:
    ssid = str(env["ssid"])
    psk = str(env["psk"])
    expected_ssid_hex = native_expected_ssid_hex(ssid)
    expected_psk_hex = pbkdf2_psk_hex(ssid, psk)
    device_ssid = ""
    device_psk = ""
    if device_profile is not None:
        raw_profile = device_profile.get("raw", {})
        device_ssid = str(raw_profile.get("ssid", ""))
        device_psk = str(raw_profile.get("psk", ""))
    device_psk_hex = pbkdf2_psk_hex(device_ssid, device_psk) if device_ssid and device_psk else None

    wsta7_ssid_matches = False
    wsta7_psk_matches = False
    if wsta7_config is not None:
        wsta7_ssid_matches = wsta7_config.get("ssid") == ssid
        wsta7_psk_matches = wsta7_config.get("psk") == psk

    native_ssid_matches = False
    native_psk_matches = False
    if native_config is not None:
        native_raw = native_config.get("raw", {})
        native_ssid_matches = str(native_raw.get("ssid", "")).lower() == expected_ssid_hex.lower()
        native_psk_matches = (
            expected_psk_hex is not None and
            str(native_raw.get("psk", "")).lower() == expected_psk_hex.lower()
        )
        native_psk_matches_device_secret = (
            device_psk_hex is not None and
            str(native_raw.get("psk", "")).lower() == device_psk_hex.lower()
        )
    else:
        native_psk_matches_device_secret = False

    device_ssid_matches = bool(device_ssid) and device_ssid == ssid
    device_psk_matches = bool(device_psk) and device_psk == psk

    return {
        "python_pbkdf2_reference": "hashlib.pbkdf2_hmac_sha1_4096_32",
        "native_expected_ssid_format": "hex",
        "native_expected_psk_format": "hex64",
        "wsta7_ssid_matches_env": wsta7_ssid_matches,
        "wsta7_psk_matches_env": wsta7_psk_matches,
        "device_ssid_secret_matches_env": device_ssid_matches,
        "device_psk_secret_matches_env": device_psk_matches,
        "native_ssid_hex_matches_env": native_ssid_matches,
        "native_psk_hex_matches_python_reference": native_psk_matches,
        "native_psk_hex_matches_device_secret_reference": native_psk_matches_device_secret,
        "credential_material_consistent": (
            wsta7_ssid_matches and
            wsta7_psk_matches and
            device_ssid_matches and
            device_psk_matches and
            native_ssid_matches and
            native_psk_matches
        ),
        "secret_values_logged": 0,
    }


def classify(result: dict[str, Any]) -> str:
    if not result.get("wifi_env", {}).get("ok"):
        return "wsta38-blocked-wifi-env"
    if not result.get("wsta7_config", {}).get("present"):
        return "wsta38-blocked-wsta7-config-missing"
    if not result.get("native_config_read", {}).get("payload_present"):
        return "wsta38-blocked-native-config-read"
    if not result.get("device_profile", {}).get("ssid_secret_read", {}).get("payload_present"):
        return "wsta38-blocked-device-ssid-secret-read"
    if not result.get("device_profile", {}).get("psk_secret_read", {}).get("payload_present"):
        return "wsta38-blocked-device-psk-secret-read"
    if not result.get("comparison", {}).get("wsta7_ssid_matches_env"):
        return "wsta38-wsta7-ssid-mismatch"
    if not result.get("comparison", {}).get("wsta7_psk_matches_env"):
        return "wsta38-wsta7-psk-mismatch"
    if not result.get("comparison", {}).get("device_ssid_secret_matches_env"):
        return "wsta38-device-ssid-secret-mismatch"
    if not result.get("comparison", {}).get("device_psk_secret_matches_env"):
        return "wsta38-device-psk-secret-mismatch"
    if not result.get("comparison", {}).get("native_ssid_hex_matches_env"):
        return "wsta38-native-ssid-mismatch"
    if not result.get("comparison", {}).get("native_psk_hex_matches_python_reference"):
        return "wsta38-native-psk-mismatch"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta38-credential-reconciliation-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    out_path = run_dir / "wsta38_result.json"

    loaded_env = wsta3.load_wifi_env(args.wifi_env)
    wsta7_path = args.wsta7_config or find_latest_wsta7_config()
    wsta7_present = bool(wsta7_path and wsta7_path.is_file())
    wsta7_text = ""
    if wsta7_path is not None:
        wsta7_present, wsta7_text = read_text_private(wsta7_path)

    native_read = run_a90ctl_cat(args, args.native_conf) if args.read_native else {
        "payload": "",
        "metadata": {
            "skipped": True,
            "payload_present": False,
            "secret_values_logged": 0,
        },
    }
    device_profile = read_device_profile_material(args) if args.read_native else {
        "raw": {},
        "metadata": {
            "skipped": True,
            "ssid_secret_read": {"payload_present": False, "secret_values_logged": 0},
            "psk_secret_read": {"payload_present": False, "secret_values_logged": 0},
            "secret_values_logged": 0,
        },
    }

    wsta7_parsed = parse_supplicant_config(wsta7_text) if wsta7_present else None
    native_parsed = parse_supplicant_config(native_read.get("payload", "")) if native_read.get("payload") else None

    result: dict[str, Any] = {
        "scope": "WSTA38 credential/AP-side reconciliation",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "device_contact": bool(args.read_native),
        "association_attempted": False,
        "dhcp_attempted": False,
        "ping_attempted": False,
        "public_tunnel": False,
        "secret_values_logged": 0,
        "wifi_env": redacted_wifi_env_status(args.wifi_env, loaded_env),
        "wsta7_config": {
            "path": rel(wsta7_path) if wsta7_path is not None else "-",
            "present": wsta7_present,
            **(wsta7_parsed["metadata"] if wsta7_parsed is not None else {"secret_values_logged": 0}),
        },
        "native_config_read": native_read["metadata"],
        "native_config": (
            native_parsed["metadata"] if native_parsed is not None else {"present": False, "secret_values_logged": 0}
        ),
        "device_profile": device_profile["metadata"],
    }
    if loaded_env.get("ok"):
        result["comparison"] = compare_material(loaded_env, wsta7_parsed, native_parsed, device_profile)
    else:
        result["comparison"] = {"credential_material_consistent": False, "secret_values_logged": 0}
    result["decision"] = classify(result)
    result["interpretation"] = (
        "credential-material-consistent-wrong-key-points-past-config-generation"
        if result["decision"] == PASS_DECISION else
        "credential-material-mismatch-or-read-blocked"
    )
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--wifi-env", type=Path, default=DEFAULT_WIFI_ENV)
    parser.add_argument("--wsta7-config", type=Path)
    parser.add_argument("--a90ctl", type=Path, default=DEFAULT_A90CTL)
    parser.add_argument("--native-conf", default=DEFAULT_NATIVE_CONF)
    parser.add_argument("--native-autoconnect-conf", default=DEFAULT_NATIVE_AUTOCONNECT_CONF)
    parser.add_argument("--native-profile-root", default=DEFAULT_NATIVE_PROFILE_ROOT)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--read-native", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
