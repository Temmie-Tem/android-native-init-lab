#!/usr/bin/env python3
"""Probe which wpa_supplicant runtime dependency can support native Wi-Fi.

Default mode is credential-free: it starts each candidate with an empty
no-connect config, waits for the per-interface control socket, sends PING, and
terminates it. Optional connect mode uses an already prepared remote config and
checks carrier only; it does not run DHCP, install routes, or ping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import a90_ncm_transport as ncm
import a90_transport as transport
from a90harness.evidence import EvidenceStore, safe_artifact_label, wifi_artifact_dir


CTRL_HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_wpa_ctrl_request.c"
REMOTE_CTRL_HELPER = "/cache/a90-wpa-ctrl-request"
REMOTE_PROBE_SCRIPT = "/cache/a90-supplicant-dependency-probe.sh"
DEFAULT_CONNECT_CONFIG = "/cache/a90-wifi/wpa_supplicant.conf"

DEFAULT_CANDIDATES = (
    ("standalone", "/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh"),
    ("vendor_hw", "/vendor/bin/hw/wpa_supplicant"),
    ("vendor", "/vendor/bin/wpa_supplicant"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_ctrl_helper(store: EvidenceStore, steps: list[dict[str, Any]], cross_gcc: str) -> Path:
    out_dir = store.mkdir("host-build")
    binary = out_dir / "a90_wpa_ctrl_request"
    result = transport.run_host_command(
        [
            cross_gcc,
            "-static",
            "-Os",
            "-Wall",
            "-Wextra",
            "-o",
            binary,
            CTRL_HELPER_SOURCE,
        ],
        timeout=60,
    )
    transport.write_step(store, steps, "host-build-wpa-ctrl-request", result)
    if not result.get("ok"):
        raise RuntimeError("failed to build a90_wpa_ctrl_request")
    strip_result = transport.run_host_command(["aarch64-linux-gnu-strip", binary], timeout=20)
    transport.write_step(store, steps, "host-strip-wpa-ctrl-request", strip_result)
    return binary


def remote_probe_script() -> str:
    return r'''#!/cache/bin/busybox sh
set +e

MODE="${1:-no-connect}"
CONNECT_CONFIG="${2:-/cache/a90-wifi/wpa_supplicant.conf}"
KEEP_REMOTE="${3:-0}"
IFACE="${A90_WIFI_PROBE_IFACE:-wlan0}"
ROOT="/cache/a90-wifi/supplicant-dependency-probe"
HELPER="/cache/a90-wpa-ctrl-request"
WAIT_CTRL_SEC="${A90_WIFI_PROBE_WAIT_CTRL_SEC:-15}"
WAIT_CARRIER_SEC="${A90_WIFI_PROBE_WAIT_CARRIER_SEC:-35}"
HAL_CONTEXT="u:r:hal_wifi_supplicant_default:s0"

prefix_file() {
    key_prefix="$1"
    file_path="$2"
    if [ -s "$file_path" ]; then
        while IFS= read -r line; do
            case "$line" in
                *=*) echo "${key_prefix}.${line}" ;;
            esac
        done < "$file_path"
    fi
}

grep_count() {
    pattern="$1"
    file_path="$2"
    if [ -s "$file_path" ]; then
        /cache/bin/busybox grep -ci "$pattern" "$file_path" 2>/dev/null
    else
        echo 0
    fi
}

emit_existing_wpa_count() {
    count=0
    for cmdline in /proc/[0-9]*/cmdline; do
        [ -r "$cmdline" ] || continue
        if /cache/bin/busybox tr '\000' ' ' < "$cmdline" | /cache/bin/busybox grep -q 'wpa_supplicant'; then
            count=$((count + 1))
        fi
    done
    echo "supplicant_probe.existing_wpa_processes=$count"
}

write_no_connect_config() {
    sockdir="$1"
    conf="$2"
    {
        echo "ctrl_interface=DIR=$sockdir GROUP=wifi"
        echo "update_config=0"
        echo "ap_scan=1"
    } > "$conf"
    /cache/bin/busybox chmod 600 "$conf" 2>/dev/null
    /cache/bin/busybox chown 1010:1010 "$conf" 2>/dev/null
}

start_candidate() {
    path="$1"
    conf="$2"
    sockdir="$3"
    log="$4"
    context_mode="$5"

    if [ "$context_mode" = "halctx" ]; then
        (
            /cache/bin/busybox printf 'u:r:hal_wifi_supplicant_default:s0\000' > /proc/self/attr/exec 2>/dev/null
            exec "$path" -dd -i "$IFACE" -D nl80211 -c "$conf" -O "$sockdir" -t
        ) > "$log" 2>&1 &
    else
        "$path" -dd -i "$IFACE" -D nl80211 -c "$conf" -O "$sockdir" -t > "$log" 2>&1 &
    fi
    echo "$!"
}

ctrl_command() {
    socket_path="$1"
    out_path="$2"
    shift 2
    "$HELPER" "$socket_path" "$@" > "$out_path" 2>&1
    return $?
}

cleanup_pid() {
    pid="$1"
    grace="$2"
    i=0
    [ -n "$pid" ] || return
    while [ "$i" -lt "$grace" ]; do
        if ! /cache/bin/busybox kill -0 "$pid" 2>/dev/null; then
            wait "$pid" 2>/dev/null
            return
        fi
        state="$(/cache/bin/busybox awk '/^State:/ { print $2; exit }' "/proc/$pid/status" 2>/dev/null)"
        if [ "$state" = "Z" ]; then
            wait "$pid" 2>/dev/null
            return
        fi
        i=$((i + 1))
        /cache/bin/busybox sleep 1
    done
    if /cache/bin/busybox kill -0 "$pid" 2>/dev/null; then
        /cache/bin/busybox kill "$pid" 2>/dev/null
        /cache/bin/busybox sleep 1
    fi
    if /cache/bin/busybox kill -0 "$pid" 2>/dev/null; then
        /cache/bin/busybox kill -9 "$pid" 2>/dev/null
    fi
    wait "$pid" 2>/dev/null
}

pid_alive_non_zombie() {
    pid="$1"
    [ -n "$pid" ] || return 1
    /cache/bin/busybox kill -0 "$pid" 2>/dev/null || return 1
    state="$(/cache/bin/busybox awk '/^State:/ { print $2; exit }' "/proc/$pid/status" 2>/dev/null)"
    [ "$state" = "Z" ] && return 1
    return 0
}

run_candidate() {
    base_label="$1"
    path="$2"
    context_mode="$3"
    label="${base_label}_${context_mode}"
    dir="$ROOT/$label"
    sockdir="$dir/sockets"
    conf="$dir/no-connect.conf"
    log="$dir/supplicant.log"
    socket_path="$sockdir/$IFACE"
    pid=""
    ping_ok=0
    carrier_up=0
    result="unknown"

    /cache/bin/busybox rm -rf "$dir"
    /cache/bin/busybox mkdir -p "$sockdir"
    /cache/bin/busybox chmod 0770 "$sockdir" 2>/dev/null
    /cache/bin/busybox chown 1010:1010 "$sockdir" 2>/dev/null

    echo "candidate.$label.base=$base_label"
    echo "candidate.$label.context_mode=$context_mode"
    echo "candidate.$label.path=$path"
    echo "candidate.$label.present=$([ -e "$path" ] && echo 1 || echo 0)"
    echo "candidate.$label.executable=$([ -x "$path" ] && echo 1 || echo 0)"

    if [ ! -x "$path" ]; then
        echo "candidate.$label.result=missing-or-not-executable"
        [ "$KEEP_REMOTE" = "1" ] || /cache/bin/busybox rm -rf "$dir"
        return
    fi
    if [ "$MODE" = "connect" ]; then
        conf="$CONNECT_CONFIG"
        if [ ! -s "$conf" ]; then
            echo "candidate.$label.result=connect-config-missing"
            [ "$KEEP_REMOTE" = "1" ] || /cache/bin/busybox rm -rf "$dir"
            return
        fi
    else
        write_no_connect_config "$sockdir" "$conf"
    fi

    pid="$(start_candidate "$path" "$conf" "$sockdir" "$log" "$context_mode")"
    echo "candidate.$label.pid=$pid"
    echo "candidate.$label.started=$([ -n "$pid" ] && echo 1 || echo 0)"
    i=0
    while [ "$i" -lt "$WAIT_CTRL_SEC" ]; do
        alive=0
        [ -n "$pid" ] && /cache/bin/busybox kill -0 "$pid" 2>/dev/null && alive=1
        echo "candidate.$label.wait.$i.alive=$alive"
        if [ -S "$socket_path" ]; then
            ctrl_command "$socket_path" "$dir/ping.out" PING
            ping_rc=$?
            prefix_file "candidate.$label.ping" "$dir/ping.out"
            if [ "$ping_rc" -eq 0 ] && /cache/bin/busybox grep -q 'reply_category=pong' "$dir/ping.out"; then
                ping_ok=1
                break
            fi
        fi
        [ "$alive" -eq 0 ] && break
        i=$((i + 1))
        /cache/bin/busybox sleep 1
    done

    echo "candidate.$label.socket_present=$([ -S "$socket_path" ] && echo 1 || echo 0)"
    echo "candidate.$label.ping_ok=$ping_ok"

    if [ "$ping_ok" -eq 1 ] && [ "$MODE" = "connect" ]; then
        ctrl_command "$socket_path" "$dir/country.out" DRIVER COUNTRY KR
        prefix_file "candidate.$label.driver_country" "$dir/country.out"
        ctrl_command "$socket_path" "$dir/enable.out" ENABLE_NETWORK 0
        prefix_file "candidate.$label.enable_network" "$dir/enable.out"
        ctrl_command "$socket_path" "$dir/reassociate.out" REASSOCIATE
        prefix_file "candidate.$label.reassociate" "$dir/reassociate.out"
        c=0
        while [ "$c" -lt "$WAIT_CARRIER_SEC" ]; do
            carrier="$(/cache/bin/busybox cat /sys/class/net/$IFACE/carrier 2>/dev/null)"
            [ "$carrier" = "1" ] && carrier_up=1 && break
            c=$((c + 1))
            /cache/bin/busybox sleep 1
        done
        echo "candidate.$label.carrier_up=$carrier_up"
        result="$([ "$carrier_up" -eq 1 ] && echo connect-carrier || echo connect-no-carrier)"
    elif [ "$ping_ok" -eq 1 ]; then
        result="no-connect-ctrl-ready"
    else
        result="ctrl-not-ready"
    fi

    echo "candidate.$label.log_bytes=$(/cache/bin/busybox stat -c '%s' "$log" 2>/dev/null || echo 0)"
    echo "candidate.$label.log_nl80211=$(grep_count nl80211 "$log")"
    echo "candidate.$label.log_ctrl=$(grep_count ctrl "$log")"
    echo "candidate.$label.log_fail=$(grep_count fail "$log")"
    echo "candidate.$label.log_permission=$(grep_count permission "$log")"
    echo "candidate.$label.log_avc=$(grep_count 'avc:' "$log")"
    echo "candidate.$label.log_no_such=$(grep_count 'No such' "$log")"

    if [ "$ping_ok" -eq 1 ]; then
        ctrl_command "$socket_path" "$dir/terminate.out" TERMINATE
        prefix_file "candidate.$label.terminate" "$dir/terminate.out"
    fi
    cleanup_pid "$pid" 3
    echo "candidate.$label.alive_after_cleanup=$(pid_alive_non_zombie "$pid" && echo 1 || echo 0)"
    echo "candidate.$label.result=$result"
    [ "$KEEP_REMOTE" = "1" ] || /cache/bin/busybox rm -rf "$dir"
}

echo "supplicant_probe.version=1"
echo "supplicant_probe.mode=$MODE"
echo "supplicant_probe.iface=$IFACE"
echo "supplicant_probe.connect_config=$CONNECT_CONFIG"
echo "supplicant_probe.keep_remote=$KEEP_REMOTE"
echo "supplicant_probe.helper_present=$([ -x "$HELPER" ] && echo 1 || echo 0)"
emit_existing_wpa_count

/cache/bin/busybox mkdir -p "$ROOT"
if [ -d "/sys/class/net/$IFACE" ]; then
    echo "supplicant_probe.wlan0_present=1"
else
    echo "supplicant_probe.wlan0_present=0"
    echo "supplicant_probe.result=precondition-wlan0-missing"
    echo "supplicant_probe.done=1"
    exit 0
fi
/cache/bin/busybox ip link set "$IFACE" up 2>/dev/null
echo "supplicant_probe.link_up_rc=$?"

run_candidate standalone /cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh native
run_candidate standalone /cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh halctx
run_candidate vendor_hw /vendor/bin/hw/wpa_supplicant native
run_candidate vendor_hw /vendor/bin/hw/wpa_supplicant halctx
run_candidate vendor /vendor/bin/wpa_supplicant native
run_candidate vendor /vendor/bin/wpa_supplicant halctx

echo "supplicant_probe.done=1"
[ "$KEEP_REMOTE" = "1" ] || /cache/bin/busybox rm -rf "$ROOT"
'''


def parse_candidate_results(fields: dict[str, str]) -> list[dict[str, Any]]:
    labels = sorted({
        key.split(".")[1]
        for key in fields
        if key.startswith("candidate.") and len(key.split(".")) >= 3
    })
    candidates: list[dict[str, Any]] = []
    for label in labels:
        prefix = f"candidate.{label}."
        candidates.append({
            "label": label,
            "base": fields.get(prefix + "base", ""),
            "context_mode": fields.get(prefix + "context_mode", ""),
            "path": fields.get(prefix + "path", ""),
            "present": fields.get(prefix + "present") == "1",
            "executable": fields.get(prefix + "executable") == "1",
            "socket_present": fields.get(prefix + "socket_present") == "1",
            "ping_ok": fields.get(prefix + "ping_ok") == "1",
            "carrier_up": fields.get(prefix + "carrier_up") == "1",
            "result": fields.get(prefix + "result", "missing"),
            "log_bytes": fields.get(prefix + "log_bytes", "0"),
            "log_nl80211": fields.get(prefix + "log_nl80211", "0"),
            "log_fail": fields.get(prefix + "log_fail", "0"),
            "log_permission": fields.get(prefix + "log_permission", "0"),
            "log_avc": fields.get(prefix + "log_avc", "0"),
            "alive_after_cleanup": fields.get(prefix + "alive_after_cleanup") == "1",
        })
    return candidates


def pick_decision(mode: str, fields: dict[str, str], candidates: list[dict[str, Any]]) -> str:
    if fields.get("supplicant_probe.wlan0_present") == "0":
        return "supplicant-dependency-precondition-wlan0-missing"
    if fields.get("supplicant_probe.helper_present") == "0":
        return "supplicant-dependency-precondition-helper-missing"
    if mode == "connect":
        if any(item.get("carrier_up") for item in candidates if item.get("base") == "vendor_hw"):
            return "supplicant-dependency-vendor-hw-connects"
        if any(item.get("carrier_up") for item in candidates if item.get("base") == "vendor"):
            return "supplicant-dependency-vendor-connects"
        if any(item.get("carrier_up") for item in candidates if item.get("base") == "standalone"):
            return "supplicant-dependency-standalone-connects"
        if any(item.get("ping_ok") for item in candidates):
            return "supplicant-dependency-ctrl-ready-but-no-carrier"
        return "supplicant-dependency-no-connectable-candidate"
    if any(item.get("ping_ok") for item in candidates if item.get("base") in {"vendor_hw", "vendor"}):
        return "supplicant-dependency-vendor-direct-ctrl-ready"
    if any(item.get("ping_ok") for item in candidates if item.get("base") == "standalone"):
        return "supplicant-dependency-standalone-only-ctrl-ready"
    return "supplicant-dependency-no-ctrl-ready-candidate"


def transfer_ok(result: dict[str, Any]) -> bool:
    return bool(result.get("ok")) and not bool(result.get("sha256_mismatch"))


def main() -> int:
    started_monotonic = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="default")
    parser.add_argument("--mode", choices=("no-connect", "connect"), default="no-connect")
    parser.add_argument("--prepare-profile", default="", help="run native `wifi config prepare PROFILE` before connect mode")
    parser.add_argument("--connect-config", default=DEFAULT_CONNECT_CONFIG)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--bridge-device", default=transport.DEFAULT_BRIDGE_DEVICE)
    parser.add_argument("--cross-gcc", default=os.environ.get("A90_CROSS_GCC", "aarch64-linux-gnu-gcc"))
    parser.add_argument("--keep-remote", action="store_true")
    parser.add_argument("--no-bridge-ensure", action="store_true")
    args = parser.parse_args()

    safe_label = safe_artifact_label(args.label)
    out_dir = args.out_dir or wifi_artifact_dir(
        "runs",
        f"native-wifi-supplicant-dependency-probe-{safe_label}",
        timestamp=True,
    )
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []

    selection = transport.select_transport(
        store,
        steps,
        bridge_device=args.bridge_device,
        ensure=not args.no_bridge_ensure,
        prefer_fast=True,
    )
    transport.run_serial_step(store, steps, "pre-probe-hide", ["hide"], bridge_timeout=8)
    transport.run_serial_step(store, steps, "pre-probe-status", ["status"], bridge_timeout=20)
    transport.run_serial_step(store, steps, "pre-probe-wifiinv-summary", ["wifiinv", "summary"], bridge_timeout=30)

    if args.mode == "connect" and args.prepare_profile:
        transport.run_serial_step(
            store,
            steps,
            "prepare-connect-config",
            ["wifi", "config", "prepare", args.prepare_profile],
            bridge_timeout=45,
        )

    helper = build_ctrl_helper(store, steps, args.cross_gcc)
    script_path = store.write_text("host-build/a90-supplicant-dependency-probe.sh", remote_probe_script())
    script_path.chmod(0o700)

    transfer = ncm.FastTransferSession(store, steps, run_step=transport.run_serial_step)
    helper_transfer: dict[str, Any] = {"ok": False, "reason": "not-run"}
    script_transfer: dict[str, Any] = {"ok": False, "reason": "not-run"}
    probe_step: dict[str, Any] = {
        "ok": False,
        "stdout": "",
        "stderr": "transfer validation not completed",
    }
    try:
        helper_transfer = transfer.transfer_file(
            label="wpa-ctrl-helper",
            local_path=helper,
            remote_path=REMOTE_CTRL_HELPER,
            expected_sha256=sha256_file(helper),
            mode="700",
        )
        script_transfer = transfer.transfer_file(
            label="supplicant-probe-script",
            local_path=script_path,
            remote_path=REMOTE_PROBE_SCRIPT,
            expected_sha256=sha256_file(script_path),
            mode="700",
        )
        if transfer_ok(helper_transfer) and transfer_ok(script_transfer):
            probe_step = transport.run_serial_step(
                store,
                steps,
                "run-supplicant-dependency-probe",
                [
                    "run",
                    "/cache/bin/busybox",
                    "sh",
                    "-c",
                    " ".join([
                        shlex.quote(REMOTE_PROBE_SCRIPT),
                        shlex.quote(args.mode),
                        shlex.quote(args.connect_config),
                        "1" if args.keep_remote else "0",
                    ]),
                ],
                timeout=180,
                bridge_timeout=170,
            )
    finally:
        transfer.close()

    post_status = transport.run_serial_step(store, steps, "post-probe-status", ["status"], bridge_timeout=20)
    output = "\n".join([str(probe_step.get("stdout") or ""), str(probe_step.get("stderr") or "")])
    fields = transport.parse_key_values(output)
    candidates = parse_candidate_results(fields)
    transfers_valid = transfer_ok(helper_transfer) and transfer_ok(script_transfer)
    if transfers_valid:
        decision = pick_decision(args.mode, fields, candidates)
        ok = any(item.get("ping_ok") for item in candidates)
        if args.mode == "connect":
            ok = any(item.get("carrier_up") for item in candidates)
    else:
        decision = "supplicant-dependency-probe-transfer-failed"
        ok = False

    manifest = {
        "label": safe_label,
        "mode": args.mode,
        "out_dir": str(out_dir),
        "decision": decision,
        "ok": ok,
        "transport": selection,
        "helper_transfer": helper_transfer,
        "script_transfer": script_transfer,
        "transfer_validated": transfers_valid,
        "probe_executed": transfers_valid,
        "connect_config": args.connect_config,
        "prepare_profile_used": bool(args.prepare_profile),
        "keep_remote": args.keep_remote,
        "secret_values_logged": 0,
        "dhcp_executed": False,
        "routes_changed_by_probe": False,
        "external_ping_executed": False,
        "candidate_order": [
            {"label": label, "path": path}
            for label, path in DEFAULT_CANDIDATES
        ],
        "candidates": candidates,
        "raw_field_count": len(fields),
        "post_status_ok": post_status.get("ok"),
        "steps": steps,
    }
    transport.add_total_phase(
        manifest,
        "supplicant_dependency_probe_total",
        started_monotonic,
        ok=ok,
    )
    transport.set_residual_state(manifest, {
        "remote_helper": REMOTE_CTRL_HELPER,
        "remote_script": REMOTE_PROBE_SCRIPT,
        "keep_remote": args.keep_remote,
        "remote_cleanup_expected": not args.keep_remote,
        "post_status_ok": bool(post_status.get("ok")),
    })
    store.write_json("manifest.json", manifest)
    print(json.dumps({
        "ok": ok,
        "decision": decision,
        "out_dir": str(out_dir),
        "mode": args.mode,
        "transport_selected": selection.get("selected"),
        "candidates": [
            {
                "label": item["label"],
                "result": item["result"],
                "ping_ok": item["ping_ok"],
                "carrier_up": item["carrier_up"],
                "present": item["present"],
                "executable": item["executable"],
            }
            for item in candidates
        ],
    }, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
