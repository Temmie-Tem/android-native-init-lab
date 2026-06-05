#!/usr/bin/env python3
"""V2167 native wlan0 connect, DHCP, and google.com ping handoff."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import re
import shlex
import shutil
import tarfile
from pathlib import Path
from typing import Any

import native_wifi_qcacld_fwclass_clean_recapture_handoff_v2144 as base
import native_property_runtime_overlay_v471 as propbase
import native_property_runtime_overlay_v535 as prop535


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V2167"
RAW_RUN_LABEL = os.environ.get("A90_WIFI_RUN_LABEL", "").strip().lower()
RUN_LABEL = re.sub(r"[^a-z0-9_.-]+", "-", RAW_RUN_LABEL).strip(".-")[:48] or "default"
RUN_SUFFIX = "" if RUN_LABEL == "default" else f"-{RUN_LABEL}"
REPORT_SUFFIX = "" if RUN_LABEL == "default" else f"_{RUN_LABEL.upper().replace('-', '_').replace('.', '_')}"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / f"v2167-connect-dhcp-google-ping-handoff{RUN_SUFFIX}"
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
CONNECT_DIR = "/cache/a90-wifi"
CONNECT_CONFIG = f"{CONNECT_DIR}/v2167.conf"
CONNECT_CONFIG_B64 = f"{CONNECT_CONFIG}.b64"
CONNECT_SCRIPT = "/cache/a90-v2167-connect-ping.sh"
CONNECT_RESULT = "/cache/a90-v2167-connect-ping.result"
PROPERTY_LAYOUT_DIR = OUT_DIR / "layout"
PROPERTY_ROOT = PROPERTY_LAYOUT_DIR / "dev" / "__properties__"
PROPERTY_REMOTE_BASE = "/cache/a90-wifi-property-v2167"
PROPERTY_REMOTE_ROOT = f"{PROPERTY_REMOTE_BASE}/dev/__properties__"
PROPERTY_REMOTE_TGZ = "/cache/a90-property-v2167.tgz"
PROPERTY_REMOTE_B64 = f"{PROPERTY_REMOTE_TGZ}.b64"
PING_TARGET = "google.com"
CHUNK_SIZE = 1536
RAW_SECRET_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")
SUPPLICANT_PROPERTY_KEYS = (
    "debug.ld.app.wpa_supplicant",
    "arm64.memtag.process.wpa_supplicant",
    "persist.log.tag.wpa_supplicant",
    "log.tag.wpa_supplicant",
)


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


def intish(value: object) -> int:
    return base.intish(value)


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
        "scripts/revalidation/build_android_execns_probe_helper.sh",
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
        "chunks": (len(base64.b64encode(gzip_bytes)) + CHUNK_SIZE - 1) // CHUNK_SIZE,
    }


def stage_helper_binary(store: base.EvidenceStore,
                        steps: list[dict[str, Any]],
                        helper_build: dict[str, Any]) -> dict[str, str]:
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
        timeout=60,
        bridge_timeout=45,
    )
    existing = base.parse_key_values(str(verify.get("stdout") or ""))
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
    run_step(
        store,
        steps,
        "execns-helper-stage-touch",
        ["run", "/cache/bin/busybox", "touch", HELPER_REMOTE_B64],
    )
    gzip_bytes = gzip.compress(HELPER_LOCAL.read_bytes(), compresslevel=9)
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
                           archive_info: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {
        "property_stage.begin": "1",
        "property_stage.remote_root": PROPERTY_REMOTE_ROOT,
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
        f"/cache/bin/busybox rm -rf {PROPERTY_REMOTE_BASE} {PROPERTY_REMOTE_TGZ} {PROPERTY_REMOTE_B64}; "
        f"/cache/bin/busybox mkdir -p {PROPERTY_REMOTE_ROOT}"
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
        f"/cache/bin/busybox chmod 755 {PROPERTY_REMOTE_BASE} {PROPERTY_REMOTE_BASE}/dev {PROPERTY_REMOTE_ROOT}; "
        f"/cache/bin/busybox chmod 644 {PROPERTY_REMOTE_ROOT}/*; "
        f"/cache/bin/busybox rm -f {PROPERTY_REMOTE_B64}; "
        f"printf 'property_stage.remote_sha256='; /cache/bin/busybox sha256sum {PROPERTY_REMOTE_TGZ} | /cache/bin/busybox awk '{{print $1}}'; "
        f"printf 'property_stage.remote_file_count='; /cache/bin/busybox find {PROPERTY_REMOTE_ROOT} -type f | /cache/bin/busybox wc -l; "
        f"printf 'property_stage.property_info_size='; /cache/bin/busybox stat -c '%s' {PROPERTY_REMOTE_ROOT}/property_info 2>/dev/null"
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
            f"umask 077; /cache/bin/busybox mkdir -p {CONNECT_DIR}; /cache/bin/busybox chmod 700 {CONNECT_DIR}",
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
    }
    helper_command = " ".join(shlex.quote(part) for part in [
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
        "--allow-iwifi-start-only",
        "--allow-connect-dhcp-ping",
    ])
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
    line_ok = True
    for index, line in enumerate(script_lines):
        result = run_step(
            store,
            steps,
            f"connect-script-line-{index:02d}",
            ["run", "/cache/bin/busybox", "sh", "-c", f"printf '%s\\n' {shlex.quote(line)} >> {CONNECT_SCRIPT}"],
        )
        line_ok = line_ok and bool(result.get("ok"))
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
    fields.update(base.parse_key_values(str(start.get("stdout") or "")))
    fields["connect_script.lines_ok"] = "1" if line_ok else "0"
    fields["connect_script.ok"] = (
        "1"
        if line_ok and chmod.get("ok") and fields.get("connect_script.started") == "1"
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
    store.write_text("connect-result-wait-polls.txt", "\n".join(polls) + "\n")
    steps.append({
        "name": "connect-result-wait-polls",
        "command": ["poll", CONNECT_RESULT],
        "started": polls[0].split("]")[0].lstrip("[") if polls else base.now_iso(),
        "ended": base.now_iso(),
        "timeout": not complete,
        "rc": 0 if complete else 1,
        "ok": complete,
        "stdout_file": "connect-result-wait-polls.txt",
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
                       property_fields: dict[str, str],
                       config_fields: dict[str, str]) -> dict[str, Any]:
    script_fields = stage_connect_script(store, steps)
    wait_fields = wait_for_connect_result(store, steps)
    ok = (
        property_fields.get("property_stage.ok") == "1"
        and helper_fields.get("helper_stage.ok") == "1"
        and config_fields.get("connect_config.ok") == "1"
        and script_fields.get("connect_script.ok") == "1"
        and wait_fields.get("complete") is True
    )
    return {
        "ok": ok,
        "fields": {**property_fields, **helper_fields, **config_fields, **script_fields},
        "wait": wait_fields,
    }


def collect_post_rollback_result(store: base.EvidenceStore,
                                 steps: list[dict[str, Any]]) -> dict[str, Any]:
    result = base.a90ctl_step(
        store,
        steps,
        "post-rollback-connect-ping-result",
        ["cat", CONNECT_RESULT],
        timeout=120,
        bridge_timeout=90,
    )
    fields = parse_fields(str(result.get("stdout") or ""))
    cleanup_script = " ".join([
        "/cache/bin/busybox rm -f",
        shlex.quote(CONNECT_SCRIPT),
        shlex.quote(CONNECT_RESULT),
        shlex.quote(CONNECT_CONFIG),
        shlex.quote(CONNECT_CONFIG_B64),
        shlex.quote(f"{CONNECT_DIR}/a90_supplicant_execns.log"),
        shlex.quote(f"{CONNECT_DIR}/a90_supplicant_execns_stdio.log"),
        shlex.quote(f"{CONNECT_DIR}/sockets/wlan0"),
        shlex.quote(HELPER_REMOTE_B64),
        shlex.quote(HELPER_REMOTE_GZ),
        shlex.quote(PROPERTY_REMOTE_TGZ),
        shlex.quote(PROPERTY_REMOTE_B64),
        "; /cache/bin/busybox rm -rf",
        shlex.quote(PROPERTY_REMOTE_BASE),
    ])
    cleanup = base.a90ctl_step(
        store,
        steps,
        "post-rollback-connect-ping-cleanup",
        ["run", "/cache/bin/busybox", "sh", "-c", cleanup_script],
        timeout=90,
        bridge_timeout=60,
    )
    return {
        "ok": bool(result.get("ok")),
        "fields": fields,
        "cleanup_ok": bool(cleanup.get("ok")),
    }


def collect_gate(manifest: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    hook = manifest.get("post_flash_hook") if isinstance(manifest.get("post_flash_hook"), dict) else {}
    hook_fields = hook.get("fields") if isinstance(hook.get("fields"), dict) else {}
    fields = result.get("fields") if isinstance(result.get("fields"), dict) else {}
    rollback_ok = bool((manifest.get("rollback") or {}).get("ok"))
    property_stage_ok = hook_fields.get("property_stage.ok") == "1"
    helper_stage_ok = hook_fields.get("helper_stage.ok") == "1"
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
    no_raw = fields.get("v2167.raw_values_logged") == "0" and fields.get("wifi_connect_ping.secret_values_logged", "0") == "0"
    if not manifest.get("test_flash_ok") or not rollback_ok:
        label = "connect-dhcp-ping-handoff-incomplete"
        passed = False
        reason = "test boot or rollback did not complete"
    elif not property_stage_ok or not helper_stage_ok or not config_ok or not script_ok or not wait_complete:
        label = "connect-dhcp-ping-stage-or-wait-failed"
        passed = False
        reason = (
            f"stage/wait failed property={property_stage_ok} helper={helper_stage_ok} "
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
    elif executor_result == "connect-dhcp-ping-pass" and helper_rc == 0 and association_carrier and dhcp_rc == 0 and ping_target == PING_TARGET and ping_rc == 0:
        label = "connect-dhcp-google-ping-pass"
        passed = True
        reason = "native wlan0 associated, DHCP succeeded, and google.com ping returned success"
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
        "external_ping_target": ping_target,
        "external_ping_rc": ping_rc,
        "external_ping_executed": fields.get("wifi_connect_ping.external_ping_executed") == "1",
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
        "supplicant_alive_after_start": fields.get("wifi_connect_ping.supplicant_alive_after_start") == "1",
        "supplicant_proc_state_after_start": fields.get("wifi_connect_ping.supplicant_proc_state_after_start", ""),
        "supplicant_alive_after_carrier_wait": fields.get("wifi_connect_ping.supplicant_alive_after_carrier_wait") == "1",
        "supplicant_proc_state_after_carrier_wait": fields.get("wifi_connect_ping.supplicant_proc_state_after_carrier_wait", ""),
        "supplicant_proc_start_comm": fields.get("wifi_connect_ping.supplicant_proc_after_start.comm", ""),
        "supplicant_proc_start_exe": fields.get("wifi_connect_ping.supplicant_proc_after_start.exe_basename", ""),
        "supplicant_proc_start_has_wpa": fields.get("wifi_connect_ping.supplicant_proc_after_start.cmdline_has_wpa_supplicant") == "1",
        "supplicant_proc_start_has_helper": fields.get("wifi_connect_ping.supplicant_proc_after_start.cmdline_has_execns_probe") == "1",
        "supplicant_proc_start_has_config": fields.get("wifi_connect_ping.supplicant_proc_after_start.cmdline_has_connect_config") == "1",
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
        "supplicant_proc_start_fd_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_count")),
        "supplicant_proc_start_fd_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_start.fd_socket_count")),
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
        "supplicant_proc_carrier_fd_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_count")),
        "supplicant_proc_carrier_fd_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_socket_count")),
        "supplicant_proc_carrier_fd_wpa_socket_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_wpa_socket_count")),
        "supplicant_proc_carrier_fd_stdio_log_count": intish(fields.get("wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_stdio_log_count")),
        "supplicant_proc_carrier_fd_samples": [
            fields.get(f"wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_sample_{index:02d}", "")
            for index in range(16)
            if fields.get(f"wifi_connect_ping.supplicant_proc_after_carrier_wait.fd_sample_{index:02d}", "")
        ],
        "no_raw": no_raw,
        "cleanup_ok": bool(result.get("cleanup_ok")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    gate = manifest["connect_ping_gate"]
    helper = manifest.get("helper_build") or {}
    property_archive = manifest.get("property_archive") or {}
    property_stage = manifest.get("property_stage") or {}
    config = manifest.get("config_stage") or {}
    steps = manifest["steps"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['stdout_file']}`"
        for step in steps
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
        "",
        "## Gate Results",
        "",
        f"- `wlan0_seen`: `{gate['wlan0_seen']}` helper_invoked `{gate['helper_invoked']}` helper_rc `{gate['helper_rc']}`",
        f"- `executor_result`: `{gate['executor_result']}`",
        f"- `association_carrier`: `{gate['association_carrier']}` errno `{gate['association_carrier_errno']}`",
        f"- `country`: `{gate['country_code']}` driver_ioctl_rc `{gate['driver_ioctl_country_rc']}` errno `{gate['driver_ioctl_country_errno']}` readback `{gate['driver_ioctl_getcountry_readback']}` get_rc `{gate['driver_ioctl_getcountry_rc']}`",
        f"- `wpa_ctrl`: ready `{gate['wpa_ctrl_ready']}` surface `{gate['wpa_ctrl_surface']}` global_path `{gate['wpa_ctrl_global_path']}` abstract `{gate['wpa_ctrl_global_abstract']}` ping `{gate['wpa_ctrl_ping_reply']}` interface_add_rc `{gate['interface_add_rc']}` interface_add `{gate['interface_add_reply']}` after_add_ready `{gate['wpa_ctrl_after_interface_add_ready']}` after_add_surface `{gate['wpa_ctrl_after_interface_add_surface']}` after_add_global `{gate['wpa_ctrl_after_interface_add_global_path']}` after_add_ping `{gate['wpa_ctrl_after_interface_add_ping']}` country_rc `{gate['driver_country_rc']}` reply `{gate['driver_country_reply']}` enable `{gate['enable_network_reply']}` reassociate `{gate['reassociate_reply']}`",
        f"- `wpa_ctrl_path`: dir `{gate['wpa_ctrl_dir']}` interface `{gate['wpa_ctrl_interface_path']}`",
        f"- `supplicant`: launch `{gate['supplicant_launch_mode']}` driver `{gate['supplicant_driver']}` global_ctrl `{gate['supplicant_global_ctrl']}` alive_start `{gate['supplicant_alive_after_start']}` state_start `{gate['supplicant_proc_state_after_start']}` alive_after_carrier_wait `{gate['supplicant_alive_after_carrier_wait']}` state_after_carrier_wait `{gate['supplicant_proc_state_after_carrier_wait']}`",
        f"- `supplicant_proc_start`: comm `{gate['supplicant_proc_start_comm']}` exe `{gate['supplicant_proc_start_exe']}` has_wpa `{gate['supplicant_proc_start_has_wpa']}` has_helper `{gate['supplicant_proc_start_has_helper']}` has_config `{gate['supplicant_proc_start_has_config']}`",
        f"- `supplicant_proc_start_runtime`: uid `{gate['supplicant_proc_start_uid']}` gid `{gate['supplicant_proc_start_gid']}` groups `{gate['supplicant_proc_start_groups']}` wchan `{gate['supplicant_proc_start_wchan']}` fd_count `{gate['supplicant_proc_start_fd_count']}` socket_fds `{gate['supplicant_proc_start_fd_socket_count']}` wpa_socket_fds `{gate['supplicant_proc_start_fd_wpa_socket_count']}` stdio_fds `{gate['supplicant_proc_start_fd_stdio_log_count']}`",
        f"- `supplicant_proc_after_wait`: comm `{gate['supplicant_proc_carrier_comm']}` exe `{gate['supplicant_proc_carrier_exe']}` has_wpa `{gate['supplicant_proc_carrier_has_wpa']}` has_helper `{gate['supplicant_proc_carrier_has_helper']}` has_config `{gate['supplicant_proc_carrier_has_config']}`",
        f"- `supplicant_proc_after_wait_runtime`: uid `{gate['supplicant_proc_carrier_uid']}` gid `{gate['supplicant_proc_carrier_gid']}` groups `{gate['supplicant_proc_carrier_groups']}` wchan `{gate['supplicant_proc_carrier_wchan']}` fd_count `{gate['supplicant_proc_carrier_fd_count']}` socket_fds `{gate['supplicant_proc_carrier_fd_socket_count']}` wpa_socket_fds `{gate['supplicant_proc_carrier_fd_wpa_socket_count']}` stdio_fds `{gate['supplicant_proc_carrier_fd_stdio_log_count']}`",
        f"- `supplicant_log`: present `{gate['supplicant_log_present']}` size `{gate['supplicant_log_size']}` lines `{gate['supplicant_log_lines']}` ctrl `{gate['supplicant_log_ctrl_iface']}` ctrl_err `{gate['supplicant_log_ctrl_iface_error']}` nl80211 `{gate['supplicant_log_nl80211']}` scan `{gate['supplicant_log_scan']}` auth `{gate['supplicant_log_auth']}` assoc `{gate['supplicant_log_assoc']}` connected `{gate['supplicant_log_connected']}` disconnected `{gate['supplicant_log_disconnected']}` fail `{gate['supplicant_log_fail']}`",
        f"- `supplicant_stdio`: present `{gate['supplicant_stdio_present']}` size `{gate['supplicant_stdio_size']}` lines `{gate['supplicant_stdio_lines']}` ctrl `{gate['supplicant_stdio_ctrl_iface']}` ctrl_err `{gate['supplicant_stdio_ctrl_iface_error']}` config_err `{gate['supplicant_stdio_config_error']}` nl80211 `{gate['supplicant_stdio_nl80211']}` scan `{gate['supplicant_stdio_scan']}` auth `{gate['supplicant_stdio_auth']}` assoc `{gate['supplicant_stdio_assoc']}` connected `{gate['supplicant_stdio_connected']}` disconnected `{gate['supplicant_stdio_disconnected']}` fail `{gate['supplicant_stdio_fail']}` usage `{gate['supplicant_stdio_usage']}` interface `{gate['supplicant_stdio_interface']}` socket `{gate['supplicant_stdio_socket']}` terminate `{gate['supplicant_stdio_terminate']}` permission `{gate['supplicant_stdio_permission']}` samples `{gate['supplicant_stdio_sample_count']}` tail_samples `{gate['supplicant_stdio_tail_sample_count']}` nonproperty_samples `{gate['supplicant_stdio_nonproperty_sample_count']}` sensitive_skipped `{gate['supplicant_stdio_sensitive_sample_skipped']}`",
        f"- `dhcp_executed`: `{gate['dhcp_executed']}` dhcp_rc `{gate['dhcp_rc']}`",
        f"- `external_ping_executed`: `{gate['external_ping_executed']}` target `{gate['external_ping_target']}` rc `{gate['external_ping_rc']}`",
        f"- `pre_state`: operstate `{gate['pre_operstate']}` carrier `{gate['pre_carrier']}` flags `{gate['pre_flags']}`",
        f"- `post_state`: operstate `{gate['post_operstate']}` carrier `{gate['post_carrier']}` flags `{gate['post_flags']}`",
        f"- `staging`: property `{gate['property_stage_ok']}` helper `{gate['helper_stage_ok']}` config `{gate['config_ok']}` script `{gate['script_ok']}` wait_complete `{gate['wait_complete']}`",
        f"- `property_root`: remote `{gate['property_stage_remote_root']}` decision `{gate['property_stage_runtime_decision']}` files `{gate['property_stage_file_count']}` property_info_size `{gate['property_stage_property_info_size']}`",
        f"- `no_raw`: `{gate['no_raw']}` secret_values_logged `{gate['secret_values_logged']}`",
        "",
        "## Redacted Supplicant Samples",
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
        "## Supplicant FD Samples",
        "",
        *supplicant_start_fd_lines,
        *([] if supplicant_start_fd_lines else ["- `start`: `none`"]),
        *supplicant_wait_fd_lines,
        *([] if supplicant_wait_fd_lines else ["- `after_wait`: `none`"]),
        "",
        "## Staging",
        "",
        f"- `property_archive`: `{property_archive.get('path', '')}` bytes `{property_archive.get('bytes', 0)}` chunks `{property_archive.get('chunks', 0)}` staged `{property_stage.get('property_stage.ok', '')}`",
        f"- `helper_sha256`: `{helper.get('sha256', '')}` gzip_len `{helper.get('gzip_len', 0)}` chunks `{helper.get('chunks', 0)}`",
        f"- `connect_config`: path `{CONNECT_CONFIG}` size `{config.get('connect_config.size', '')}` mode `{config.get('connect_config.mode', '')}` security `{config.get('connect_config.security_mode', '')}` disabled_initially `{config.get('connect_config.network_initially_disabled', '')}` raw_values_logged `0`",
        "",
        "## Scope",
        "",
        f"- This V2167 unit stages a generated private property root at `{PROPERTY_REMOTE_ROOT}` with the wpa_supplicant loader/log lookup keys, adds private `/dev/random` and `/dev/urandom`, launches `wpa_supplicant` root-start direct `-i wlan0 -D nl80211 -c <private-config> -O /cache/a90-wifi/sockets`, and records redacted first/tail/non-property stdio samples plus `/proc` exec-state counters.",
        "- Allowed actions: start private Wi-Fi active-session surface, start `wpa_supplicant`, run DHCP, set temporary route/DNS, and ping `google.com`.",
        "- Outputs are redacted: no SSID, PSK, BSSID, raw MAC, assigned IP, route, DNS, DHCP lease, or ping transcript is recorded in the report.",
        "- Cleanup removes staged config/result/script artifacts and rollback returns to `v724`.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Cleanup",
        "",
        f"- `cache_artifacts_removed`: `{gate['cleanup_ok']}`",
        "",
        "## Safety",
        "",
        "- Wi-Fi credentials are read only from environment variables and are not committed.",
        "- Raw supplicant, DHCP, and ping stdout/stderr are redirected to `/dev/null` by the helper.",
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
                             property_manifest: dict[str, Any],
                             property_archive: dict[str, Any],
                             property_stage: dict[str, str],
                             config_stage: dict[str, str],
                             label: str,
                             reason: str) -> None:
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
        "supplicant_alive_after_start": False,
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
        "supplicant_proc_start_fd_count": 0,
        "supplicant_proc_start_fd_socket_count": 0,
        "supplicant_proc_start_fd_wpa_socket_count": 0,
        "supplicant_proc_start_fd_stdio_log_count": 0,
        "supplicant_proc_start_fd_samples": [],
        "supplicant_proc_carrier_uid": "",
        "supplicant_proc_carrier_gid": "",
        "supplicant_proc_carrier_groups": "",
        "supplicant_proc_carrier_wchan": "",
        "supplicant_proc_carrier_fd_count": 0,
        "supplicant_proc_carrier_fd_socket_count": 0,
        "supplicant_proc_carrier_fd_wpa_socket_count": 0,
        "supplicant_proc_carrier_fd_stdio_log_count": 0,
        "supplicant_proc_carrier_fd_samples": [],
        "pre_operstate": "",
        "pre_carrier": "",
        "pre_flags": "",
        "post_operstate": "",
        "post_carrier": "",
        "post_flags": "",
        "helper_stage_ok": helper_stage.get("helper_stage.ok") == "1",
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
    property_manifest = build_supplicant_property_runtime(store)
    property_archive = build_property_archive(property_manifest)
    property_stage = stage_property_runtime(store, bootstrap_steps, property_manifest, property_archive)
    helper_build = build_helper(store, bootstrap_steps)
    helper_stage = stage_helper_binary(store, bootstrap_steps, helper_build)
    config_stage = stage_connect_config(store, bootstrap_steps)
    if (
        property_stage.get("property_stage.ok") != "1"
        or helper_stage.get("helper_stage.ok") != "1"
        or config_stage.get("connect_config.ok") != "1"
    ):
        write_preflight_manifest(
            store,
            bootstrap_steps,
            helper_build,
            helper_stage,
            property_manifest,
            property_archive,
            property_stage,
            config_stage,
            "connect-dhcp-ping-prestage-failed-no-flash",
            (
                f"prestage failed property={property_stage.get('property_stage.reason')} "
                f"helper={helper_stage.get('helper_stage.reason')} "
                f"config={config_stage.get('connect_config.reason')}"
            ),
        )
        return 1

    def hook(hook_store: base.EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
        steps.extend(bootstrap_steps)
        return post_flash_connect(hook_store, steps, helper_stage, property_stage, config_stage)

    manifest = base.run_handoff(
        cycle=CYCLE,
        out_dir=OUT_DIR,
        report_path=REPORT_PATH,
        post_flash_hook=hook,
        helper_wait_sec=280.0,
    )
    store = base.EvidenceStore(OUT_DIR)
    steps = manifest["steps"]
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
    }
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
