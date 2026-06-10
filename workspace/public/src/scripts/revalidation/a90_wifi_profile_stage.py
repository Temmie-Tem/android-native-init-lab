#!/usr/bin/env python3
"""Stage native-init Wi-Fi profile files without logging raw secrets."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import EvidenceStore, WORKSPACE_PRIVATE_ROOT  # noqa: E402
import a90_transport as transport  # noqa: E402
import native_wifi_connect_carrier_handoff_v2174 as v2174  # noqa: E402


RUN_LABEL = "a90-wifi-profile-stage"
PERSISTENT_CONFIG_ROOT = "/mnt/sdext/a90/config/wifi"
PERSISTENT_PROFILE_ROOT = PERSISTENT_CONFIG_ROOT + "/profiles"
PERSISTENT_SECRET_ROOT = "/mnt/sdext/a90/secrets/wifi"
CACHE_CONFIG_ROOT = "/cache/a90-wifi/config"
CACHE_PROFILE_ROOT = CACHE_CONFIG_ROOT + "/profiles"
CACHE_SECRET_ROOT = CACHE_CONFIG_ROOT + "/secrets"


def timestamp_label() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def write_private_file(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def root_paths(root: str) -> dict[str, str]:
    if root == "persistent":
        return {
            "config": PERSISTENT_CONFIG_ROOT,
            "profiles": PERSISTENT_PROFILE_ROOT,
            "secrets": PERSISTENT_SECRET_ROOT,
        }
    if root == "cache":
        return {
            "config": CACHE_CONFIG_ROOT,
            "profiles": CACHE_PROFILE_ROOT,
            "secrets": CACHE_SECRET_ROOT,
        }
    raise ValueError(f"unknown root: {root}")


def build_stage_files(store: EvidenceStore, args: argparse.Namespace) -> dict[str, Any]:
    profile = v2174.selected_profile_name(args.profile)
    status = v2174.wifi_secret_status(profile)
    if not status.get("valid"):
        return {
            "ok": False,
            "reason": "wifi-env-invalid",
            "profile": profile,
            "secret_values_logged": 0,
            "secret_status": status,
        }

    paths = root_paths(args.root)
    stage_dir = store.mkdir("wifi-profile-stage")
    autoconnect_path = stage_dir / "autoconnect.conf"
    profile_path = stage_dir / f"{profile}.conf"
    ssid_path = stage_dir / f"{profile}.ssid"
    psk_path = stage_dir / f"{profile}.psk"
    remote_ssid_path = f"{paths['secrets']}/{profile}.ssid"
    remote_psk_path = f"{paths['secrets']}/{profile}.psk"
    autoconnect = 1 if args.autoconnect else 0

    write_private_file(
        autoconnect_path,
        "\n".join([
            "version=1",
            f"autoconnect={autoconnect}",
            f"default_profile={profile}",
            f"connect_timeout_sec={args.connect_timeout_sec}",
            f"dhcp={1 if args.dhcp else 0}",
            "external_ping=0",
            f"scan_before_connect={1 if args.scan_before_connect else 0}",
            f"retry_count={args.retry_count}",
            "",
        ]),
    )
    write_private_file(
        profile_path,
        "\n".join([
            "version=1",
            "enabled=1",
            f"ssid_file={remote_ssid_path}",
            f"psk_file={remote_psk_path}",
            f"band={args.band}",
            f"priority={args.priority}",
            "key_mgmt=WPA-PSK",
            "",
        ]),
    )
    write_private_file(ssid_path, os.environ["A90_WIFI_SSID"] + "\n")
    write_private_file(psk_path, os.environ["A90_WIFI_PSK"] + "\n")

    return {
        "ok": True,
        "reason": "ok",
        "profile": profile,
        "root": args.root,
        "autoconnect": autoconnect,
        "dhcp": 1 if args.dhcp else 0,
        "band": args.band,
        "priority": args.priority,
        "files": {
            "autoconnect": autoconnect_path,
            "profile": profile_path,
            "ssid": ssid_path,
            "psk": psk_path,
        },
        "remote": {
            "autoconnect": f"{paths['config']}/autoconnect.conf",
            "profile": f"{paths['profiles']}/{profile}.conf",
            "ssid": remote_ssid_path,
            "psk": remote_psk_path,
        },
        "remote_roots": paths,
        "ssid_len": status["ssid_len"],
        "psk_len": status["psk_len"],
        "secret_values_logged": 0,
    }


def compact_stage(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in stage.items()
        if key not in {"files"}
    }


def finalize_manifest(store: EvidenceStore,
                      manifest: dict[str, Any],
                      started_monotonic: float) -> dict[str, Any]:
    transport.add_total_phase(
        manifest,
        "wifi_profile_stage_total",
        started_monotonic,
        ok=bool(manifest.get("pass")),
    )
    stage = manifest.get("stage") if isinstance(manifest.get("stage"), dict) else {}
    transfers = manifest.get("transfer_results") if isinstance(manifest.get("transfer_results"), dict) else {}
    transport.set_residual_state(manifest, {
        "profile": stage.get("profile", ""),
        "root": stage.get("root", ""),
        "remote_root": stage.get("remote_roots", {}),
        "staged": bool(manifest.get("pass")),
        "partial_transfer_count": len(transfers),
        "persistent_state_expected": bool(manifest.get("pass")),
        "cleanup_required": bool((not manifest.get("pass")) and transfers),
    })
    store.write_json("manifest.json", manifest)
    return manifest


def run(args: argparse.Namespace) -> dict[str, Any]:
    started_monotonic = time.monotonic()
    out_dir = Path(args.out_dir) if args.out_dir else (
        WORKSPACE_PRIVATE_ROOT / "runs" / "wifi" / f"{RUN_LABEL}-{timestamp_label()}"
    )
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    env_load = v2174.load_wifi_env()
    stage = build_stage_files(store, args)
    manifest: dict[str, Any] = {
        "run_label": RUN_LABEL,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "env_load": env_load,
        "stage": compact_stage(stage),
        "steps": steps,
    }
    store.write_json("preflight.json", manifest)
    if not stage.get("ok"):
        manifest["decision"] = "wifi-profile-stage-preflight-failed"
        manifest["pass"] = False
        return finalize_manifest(store, manifest, started_monotonic)

    netservice = v2174.ensure_netservice_tcpctl(store, steps)
    host_ncm = {}
    token = ""
    tcp_args = None
    if netservice.get("ok"):
        host_ncm = v2174.ensure_host_ncm_ipv4(store, steps)
    if netservice.get("ok") and host_ncm.get("ok") and v2174.ping_device_over_ncm(store, steps):
        try:
            token = v2174.fetch_tcpctl_token_redacted(store, steps)
            tcp_args = v2174.tcpctl_args(token)
        except Exception as exc:
            steps.append({"name": "tcpctl_token", "ok": False, "reason": str(exc)})
            manifest.update({
                "decision": "wifi-profile-stage-tcpctl-token-failed",
                "pass": False,
                "reason": str(exc),
                "netservice": netservice,
                "host_ncm": host_ncm,
            })
            return finalize_manifest(store, manifest, started_monotonic)
    if tcp_args is None or not v2174.wait_for_tcpctl_ready(store, steps, tcp_args, timeout_sec=30.0):
        manifest.update({
            "decision": "wifi-profile-stage-transport-not-ready",
            "pass": False,
            "netservice": netservice,
            "host_ncm": host_ncm,
        })
        return finalize_manifest(store, manifest, started_monotonic)

    roots = stage["remote_roots"]
    if args.root == "persistent":
        prep = [
            ["mkdir", "-p", "/mnt/sdext/a90", "/mnt/sdext/a90/config", roots["config"], roots["profiles"],
             "/mnt/sdext/a90/secrets", roots["secrets"]],
            ["chmod", "700", "/mnt/sdext/a90", "/mnt/sdext/a90/config", roots["config"], roots["profiles"],
             "/mnt/sdext/a90/secrets", roots["secrets"]],
        ]
    else:
        prep = [
            ["mkdir", "-p", roots["config"], roots["profiles"], roots["secrets"]],
            ["chmod", "700", "/cache/a90-wifi", roots["config"], roots["profiles"], roots["secrets"]],
        ]
    for index, argv in enumerate(prep):
        step = v2174.tcpctl_step(
            store,
            steps,
            f"wifi-profile-stage-prep-{index}",
            tcp_args,
            v2174.tcpctl_run_line([v2174.TOYBOX, *argv]),
            timeout=30.0,
        )
        if not step.get("ok"):
            manifest.update({"decision": "wifi-profile-stage-prep-failed", "pass": False})
            return finalize_manifest(store, manifest, started_monotonic)

    transfer_results: dict[str, Any] = {}
    for index, key in enumerate(("autoconnect", "profile", "ssid", "psk")):
        result = v2174.tcpctl_transfer_file(
            store,
            steps,
            tcp_args,
            label=f"profile-stage-{key}",
            local_path=stage["files"][key],
            remote_path=stage["remote"][key],
            transfer_port=v2174.TCPCTL_TRANSFER_BASE_PORT + 40 + index,
            mode="600",
            secret_file=key in {"ssid", "psk"},
        )
        transfer_results[key] = {
            "ok": bool(result.get("ok")),
            "reason": str(result.get("reason") or ""),
            "method": str(result.get("method") or ""),
            "remote_size": str(result.get("remote_size") or ""),
        }
        if not result.get("ok"):
            manifest.update({
                "decision": f"wifi-profile-stage-{key}-transfer-failed",
                "pass": False,
                "transfer_results": transfer_results,
            })
            return finalize_manifest(store, manifest, started_monotonic)

    profile_status = v2174.a90ctl_step(
        store,
        steps,
        "wifi-profile-stage-profile-status",
        ["wifi", "profile", "status", stage["profile"]],
        timeout=90,
        bridge_timeout=60,
    )
    prepare = v2174.a90ctl_step(
        store,
        steps,
        "wifi-profile-stage-config-prepare",
        ["wifi", "config", "prepare", stage["profile"]],
        timeout=90,
        bridge_timeout=60,
    )
    output = "\n".join([
        str(profile_status.get("stdout") or ""),
        str(prepare.get("stdout") or ""),
    ])
    ok = (
        bool(profile_status.get("ok"))
        and bool(prepare.get("ok"))
        and "secret_values_logged=1" not in output
        and "decision=wifi-profile-ready" in output
        and "decision=wifi-config-supplicant-prepared" in output
    )
    manifest.update({
        "decision": "wifi-profile-stage-pass" if ok else "wifi-profile-stage-verify-failed",
        "pass": ok,
        "transfer_results": transfer_results,
        "profile_status_ok": bool(profile_status.get("ok")),
        "prepare_ok": bool(prepare.get("ok")),
        "secret_values_logged": 0 if "secret_values_logged=1" not in output else 1,
    })
    return finalize_manifest(store, manifest, started_monotonic)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--root", choices=("persistent", "cache"), default="persistent")
    parser.add_argument("--band", choices=("2.4g", "5g", "6g", "any"), default="any")
    parser.add_argument("--priority", type=int, default=100)
    parser.add_argument("--connect-timeout-sec", type=int, default=35)
    parser.add_argument("--retry-count", type=int, default=1)
    parser.add_argument("--dhcp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--scan-before-connect", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--autoconnect", action="store_true")
    parser.add_argument("--out-dir", default="")
    return parser.parse_args()


def main() -> int:
    manifest = run(parse_args())
    print(json.dumps({
        "decision": manifest.get("decision"),
        "ok": bool(manifest.get("pass")),
        "out_dir": manifest.get("out_dir"),
        "secret_values_logged": manifest.get("secret_values_logged", 0),
    }, indent=2, sort_keys=True))
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
