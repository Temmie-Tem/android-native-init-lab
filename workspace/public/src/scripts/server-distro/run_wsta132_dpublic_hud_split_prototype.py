#!/usr/bin/env python3
"""WSTA132 host-only split HUD prototype builder.

This unit starts the implementation ladder for the WSTA130/WSTA131 display
architecture.  It builds a minimal Debian-side intent producer and a
root/native presenter prototype, proves the producer can atomically write a
bounded intent file, proves the presenter parser accepts that intent, and stages
the arm64 binaries into a private rootfs-like tree.

No device action, boot flash, native reboot, Wi-Fi association, DHCP, public
tunnel, packet-filter mutation, userdata write, DRM open, KMS operation, or
switch-root is performed.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta130_dpublic_hud_presenter_model as wsta130  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
PASS_DECISION = "wsta132-dpublic-hud-split-prototype-source-pass"
RESULT_NAME = "wsta132_dpublic_hud_split_prototype.json"

INTENT_SOURCE = SCRIPT_DIR / "a90_dpublic_hud_intent.c"
PRESENTER_SOURCE = SCRIPT_DIR / "a90_dpublic_hud_presenter.c"
INTENT_TARGET = Path("usr/local/bin/a90-dpublic-hud-intent")
PRESENTER_TARGET = Path("usr/local/bin/a90-dpublic-hud-presenter")
INTENT_FILE = Path("run/a90-dpublic/hud-intent.json")


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safety() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "drm_open": False,
        "kms_setcrtc": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def run_host(command: list[object], *, timeout: float, cwd: Path = REPO_ROOT) -> dict[str, Any]:
    proc = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": [str(item) for item in command],
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def compile_c(
    compiler: str,
    source: Path,
    output: Path,
    *,
    timeout: float,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        compiler,
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-o",
        output,
        source,
    ]
    record = run_host(command, timeout=timeout)
    record["ok"] = record["returncode"] == 0 and output.is_file()
    if output.is_file():
        output.chmod(0o755)
        record["path"] = rel(output)
        record["sha256"] = sha256_file(output)
        record["size_bytes"] = output.stat().st_size
    return record


def source_contract() -> dict[str, Any]:
    intent = INTENT_SOURCE.read_text(encoding="utf-8")
    presenter = PRESENTER_SOURCE.read_text(encoding="utf-8")
    generated_schema = wsta130.intent_schema()
    return {
        "intent_source_present": INTENT_SOURCE.is_file(),
        "presenter_source_present": PRESENTER_SOURCE.is_file(),
        "intent_uses_atomic_rename": "rename(tmp, path)" in intent and "fsync(fd)" in intent,
        "intent_chmod_0640": "fchmod(fd, 0640)" in intent,
        "intent_no_drm": "/dev/dri" not in intent and "DRM_IOCTL_MODE_SETCRTC" not in intent,
        "intent_no_network_api": all(token not in intent for token in ("socket(", "bind(", "listen(", "connect(")),
        "presenter_has_strict_parser": "reject_unknown_top_level_keys" in presenter
        and "forbidden key" in presenter,
        "presenter_bounds_intent": "MAX_INTENT_BYTES 4096U" in presenter,
        "presenter_kms_owner_contract": "DRM_IOCTL_MODE_SETCRTC" in presenter
        and "A90WSTA132_PRESENTER_KMS_MASTER=1" in presenter,
        "presenter_no_exec_shell_network": all(
            token not in presenter for token in ("system(", "popen(", "execve(", "socket(", "bind(", "listen(", "connect(")
        ),
        "schema_matches_wsta130": generated_schema.get("schema") == "a90-dpublic-hud-intent-v1"
        and generated_schema.get("max_bytes") == 4096,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def parse_intent_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("intent JSON must be object")
    return payload


def run_host_selftest(host_intent: Path, host_presenter: Path, run_dir: Path, timeout: float) -> dict[str, Any]:
    intent_path = run_dir / INTENT_FILE
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    producer = run_host(
        [
            host_intent,
            "--output",
            intent_path,
            "--sequence",
            "1",
        ],
        timeout=timeout,
    )
    presenter = run_host([host_presenter, "--validate-intent", intent_path], timeout=timeout)
    payload = parse_intent_json(intent_path) if intent_path.is_file() else {}
    forbidden = {"command", "argv", "path", "shell", "url", "ssid", "psk", "token", "secret"}
    return {
        "intent_path": rel(intent_path),
        "producer": producer,
        "presenter": presenter,
        "intent_sha256": sha256_file(intent_path) if intent_path.is_file() else None,
        "intent_size_bytes": intent_path.stat().st_size if intent_path.is_file() else 0,
        "intent_payload": payload,
        "intent_schema_ok": payload.get("schema") == "a90-dpublic-hud-intent-v1",
        "intent_sequence_ok": payload.get("sequence") == 1,
        "intent_public_default_off": payload.get("public_state") == "PUBLIC_OFF",
        "intent_forbidden_fields_absent": not any(key in payload for key in forbidden),
        "producer_marker": "A90WSTA132_INTENT_WRITTEN=1" in producer.get("stdout", ""),
        "presenter_marker": "A90WSTA132_PRESENTER_INTENT_VALID=1" in presenter.get("stdout", ""),
        "presenter_kms_owner_marker": "A90WSTA132_PRESENTER_KMS_MASTER=1" in presenter.get("stdout", ""),
        "secret_values_logged": 0,
    }


def stage_arm64_binaries(arm_intent: Path, arm_presenter: Path, run_dir: Path) -> dict[str, Any]:
    stage_root = run_dir / "rootfs-stage"
    intent_target = stage_root / INTENT_TARGET
    presenter_target = stage_root / PRESENTER_TARGET
    intent_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(arm_intent, intent_target)
    shutil.copy2(arm_presenter, presenter_target)
    intent_target.chmod(0o755)
    presenter_target.chmod(0o755)
    return {
        "stage_root": rel(stage_root),
        "intent_target": str(INTENT_TARGET),
        "presenter_target": str(PRESENTER_TARGET),
        "intent_mode": oct(intent_target.stat().st_mode & 0o777),
        "presenter_mode": oct(presenter_target.stat().st_mode & 0o777),
        "intent_sha256": sha256_file(intent_target),
        "presenter_sha256": sha256_file(presenter_target),
        "staged": True,
        "secret_values_logged": 0,
    }


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks") if isinstance(result.get("checks"), dict) else {}
    for key, decision in (
        ("explicit_gate", "wsta132-blocked-emit-split-prototype-required"),
        ("private_run_dir", "wsta132-blocked-nonprivate-run-dir"),
        ("source_contract_ok", "wsta132-blocked-source-contract"),
        ("host_build_ok", "wsta132-blocked-host-build"),
        ("arm64_build_ok", "wsta132-blocked-arm64-build"),
        ("host_selftest_ok", "wsta132-blocked-host-selftest"),
        ("rootfs_stage_ok", "wsta132-blocked-rootfs-stage"),
        ("default_public_off", "wsta132-blocked-public-default"),
    ):
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta132-dpublic-hud-split-prototype-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA132 host-only D-public HUD split prototype",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta132-blocked",
        "gate_decision": "not-run",
        "safety": safety(),
        "checks": {
            "explicit_gate": bool(args.emit_split_prototype),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / RESULT_NAME
    if not args.emit_split_prototype:
        result["decision"] = classify(result)
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    contract = source_contract()
    result["source_contract"] = contract
    result["checks"]["source_contract_ok"] = all(
        value is True for key, value in contract.items() if key not in ("public_url_value_logged", "secret_values_logged")
    )

    host_dir = run_dir / "host"
    arm_dir = run_dir / "arm64"
    host_intent = host_dir / "a90-dpublic-hud-intent"
    host_presenter = host_dir / "a90-dpublic-hud-presenter"
    arm_intent = arm_dir / "a90-dpublic-hud-intent"
    arm_presenter = arm_dir / "a90-dpublic-hud-presenter"

    result["host_build"] = {
        "intent": compile_c(args.host_cc, INTENT_SOURCE, host_intent, timeout=args.build_timeout),
        "presenter": compile_c(args.host_cc, PRESENTER_SOURCE, host_presenter, timeout=args.build_timeout),
    }
    result["checks"]["host_build_ok"] = bool(
        result["host_build"]["intent"].get("ok") and result["host_build"]["presenter"].get("ok")
    )
    result["arm64_build"] = {
        "intent": compile_c(args.arm64_cc, INTENT_SOURCE, arm_intent, timeout=args.build_timeout),
        "presenter": compile_c(args.arm64_cc, PRESENTER_SOURCE, arm_presenter, timeout=args.build_timeout),
    }
    result["checks"]["arm64_build_ok"] = bool(
        result["arm64_build"]["intent"].get("ok") and result["arm64_build"]["presenter"].get("ok")
    )

    if result["checks"]["host_build_ok"]:
        result["host_selftest"] = run_host_selftest(host_intent, host_presenter, run_dir, args.run_timeout)
    else:
        result["host_selftest"] = {"skipped": True, "reason": "host-build-failed"}
    selftest = result["host_selftest"]
    result["checks"]["host_selftest_ok"] = bool(
        selftest.get("producer", {}).get("returncode") == 0
        and selftest.get("presenter", {}).get("returncode") == 0
        and selftest.get("intent_schema_ok")
        and selftest.get("intent_sequence_ok")
        and selftest.get("intent_public_default_off")
        and selftest.get("intent_forbidden_fields_absent")
        and selftest.get("producer_marker")
        and selftest.get("presenter_marker")
        and selftest.get("presenter_kms_owner_marker")
    )

    if result["checks"]["arm64_build_ok"]:
        result["rootfs_stage"] = stage_arm64_binaries(arm_intent, arm_presenter, run_dir)
    else:
        result["rootfs_stage"] = {"staged": False, "reason": "arm64-build-failed"}
    result["checks"]["rootfs_stage_ok"] = bool(
        result["rootfs_stage"].get("staged")
        and result["rootfs_stage"].get("intent_mode") == "0o755"
        and result["rootfs_stage"].get("presenter_mode") == "0o755"
    )
    result["checks"]["default_public_off"] = bool(
        result.get("host_selftest", {}).get("intent_public_default_off")
        and not result["safety"]["public_tunnel"]
        and not result["safety"]["public_smoke"]
    )
    result["checks"]["public_url_value_logged"] = False
    result["checks"]["secret_values_logged"] = 0

    result["decision"] = classify(result)
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--emit-split-prototype", action="store_true")
    parser.add_argument("--host-cc", default="gcc")
    parser.add_argument("--arm64-cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--build-timeout", type=float, default=30.0)
    parser.add_argument("--run-timeout", type=float, default=10.0)
    parser.add_argument("--print-template", action="store_true")
    return parser


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA132 host-only D-public HUD split prototype",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-split-prototype",
        ],
        "device_action": False,
        "public_tunnel": False,
        "drm_open": False,
        "kms_setcrtc": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "checks": result.get("checks", {}),
        "rootfs_stage": result.get("rootfs_stage", {}),
        "safety": result.get("safety", {}),
    }


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta132-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    print(json.dumps(public_summary(result), indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
