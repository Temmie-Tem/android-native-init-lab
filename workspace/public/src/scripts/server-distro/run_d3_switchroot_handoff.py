#!/usr/bin/env python3
"""Run the server-distro D3B checked switch_root handoff.

D3B is non-destructive and SD-backed, but unlike D1/D2 it requires one checked boot
flash because switch_root must run from PID1.  This runner:
  * verifies and flashes the V3369 D3-capable native-init candidate via native_init_flash.py,
  * copies the D3A sysvinit image, injects one per-run SSH public key, and stages that copy on SD,
  * invokes the gated PID1 switch-root-to-distro command,
  * observes A90D3_MARKER and /proc/1/comm=init over NCM SSH,
  * waits for the mandatory D3A auto-reboot back to the candidate,
  * rollback-flashes v2321 and verifies selftest fail=0.

The script writes raw evidence and temporary keys under workspace/private.  It never touches
userdata, never formats storage, and never uses a raw host dd/fastboot path.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90ctl  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402


DEFAULT_RUN_BASE = REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
DEFAULT_D3_SOURCE_IMAGE = (
    REPO_ROOT / "workspace/private/builds/server-distro/d3-sysvinit-20260703T080236Z.img"
)
DEFAULT_REMOTE_IMAGE = "/mnt/sdext/a90/runtime/debian-bookworm-arm64-d3-sysvinit-keyed.img"
DEFAULT_CANDIDATE_BOOT = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v3369_server_distro_switchroot.img"
)
DEFAULT_ROLLBACK_BOOT = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
)
EXPECTED_D3_SOURCE_SHA256 = "2ee61172116be7578fddbfcbe491c1c29e3e4c7cf485376191019417c69880c3"
EXPECTED_CANDIDATE_SHA256 = "13fa09320a42d98af7cc2712347dba0c35283af0085b7f87c12f81691f737505"
EXPECTED_CANDIDATE_VERSION = "0.11.130"
EXPECTED_CANDIDATE_BUILD = "v3369-server-distro-switchroot"
EXPECTED_ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
EXPECTED_ROLLBACK_VERSION = "0.9.285"
SWITCH_ROOT_TOKEN = "SERVER-DISTRO-D3B-SWITCHROOT"
DEFAULT_TRANSFER_DELAY = 2.0
REQUIRED_TIMELINE_EVENTS = (
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "live_session_start",
    "live_session_end",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
)


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add_event(events: list[dict[str, str]], run_dir: Path, name: str) -> None:
    events.append({"name": name, "timestamp_utc": utc_now()})
    write_json(run_dir / "timeline.json", {"events": events})


def run_host(command: list[object],
             *,
             cwd: Path = REPO_ROOT,
             timeout: float,
             check: bool = True) -> dict[str, Any]:
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
    if check and result.returncode != 0:
        raise RuntimeError(
            "host command failed rc="
            f"{result.returncode}: {shlex.join(str(item) for item in command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return payload


def flash_command(image: Path, expected_sha: str, expected_version: str, args: argparse.Namespace) -> list[object]:
    return [
        sys.executable,
        REVAL_DIR / "native_init_flash.py",
        image,
        "--bridge-host",
        args.host,
        "--bridge-port",
        str(args.port),
        "--bridge-timeout",
        str(args.flash_bridge_timeout),
        "--reboot-timeout",
        str(args.flash_reboot_timeout),
        "--expect-sha256",
        expected_sha,
        "--expect-version",
        expected_version,
        "--verify-protocol",
        "selftest",
        "--from-native",
    ]


def verify_local_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    checks = {
        "candidate_boot": (args.candidate_boot, EXPECTED_CANDIDATE_SHA256),
        "rollback_boot": (args.rollback_boot, EXPECTED_ROLLBACK_SHA256),
        "d3_source_image": (args.d3_source_image, EXPECTED_D3_SOURCE_SHA256),
    }
    out: dict[str, Any] = {}
    for name, (path, expected_sha) in checks.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = d1.sha256_file(path)
        out[name] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": actual,
            "expected_sha256": expected_sha,
        }
        if actual != expected_sha:
            raise RuntimeError(f"{name} sha mismatch: actual={actual} expected={expected_sha}")
    return out


def prepare_keyed_image(args: argparse.Namespace, run_dir: Path, public_key: str) -> dict[str, Any]:
    keyed_image = run_dir / "d3-sysvinit-keyed.img"
    pubkey_file = run_dir / "authorized_keys.pub"
    shutil.copy2(args.d3_source_image, keyed_image)
    pubkey_file.write_text(public_key.strip() + "\n", encoding="utf-8")
    commands = [
        ["debugfs", "-w", "-R", f"write {pubkey_file} /root/.ssh/authorized_keys", keyed_image],
        ["debugfs", "-w", "-R", "sif /root/.ssh/authorized_keys mode 0100600", keyed_image],
        ["debugfs", "-R", "stat /root/.ssh/authorized_keys", keyed_image],
    ]
    records = [run_host(command, timeout=args.debugfs_timeout) for command in commands]
    keyed_sha = d1.sha256_file(keyed_image)
    return {
        "keyed_image": str(keyed_image.relative_to(REPO_ROOT)),
        "keyed_sha256": keyed_sha,
        "source_sha256": EXPECTED_D3_SOURCE_SHA256,
        "debugfs": records,
    }


def install_keyed_image(args: argparse.Namespace, keyed_image: Path, keyed_sha: str) -> dict[str, Any]:
    local_image = args.local_image
    try:
        args.local_image = keyed_image
        return d1.install_image(args, keyed_sha)
    finally:
        args.local_image = local_image


def cancel_foreground_run(args: argparse.Namespace) -> dict[str, Any]:
    """Best-effort cancel for a foreground native-init `run` before rollback."""
    data = bytearray()
    try:
        with socket.create_connection((args.host, args.port), timeout=2.0) as sock:
            sock.settimeout(0.5)
            sock.sendall(b"q\n")
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                try:
                    chunk = sock.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                data.extend(chunk)
                if b"cancelled by q" in data or b"a90:/#" in data:
                    break
    except Exception as exc:  # noqa: BLE001 - rollback path records best-effort failure
        return {"ok": False, "error": type(exc).__name__, "message": str(exc)}

    text = data.decode("utf-8", errors="replace")
    return {
        "ok": "cancelled by q" in text or "a90:/#" in text,
        "text": text,
    }


def run_switch_root_command(args: argparse.Namespace, image_sha: str) -> dict[str, Any]:
    command = [
        "switch-root-to-distro",
        SWITCH_ROOT_TOKEN,
        args.remote_image,
        image_sha,
    ]
    line = a90ctl.encode_cmdv1_line(command)
    text = a90ctl.bridge_exchange(
        args.host,
        args.port,
        line,
        args.switch_timeout,
        markers=(b"exec_switch_root_now", b"A90P1 END "),
        require_prompt_after_end=False,
        post_marker_drain_sec=0.2,
    )
    payload = {
        "command": command,
        "text": text,
        "saw_exec_marker": "exec_switch_root_now" in text,
        "saw_sha_match": "expected_sha_match=1" in text,
    }
    if "A90P1 END " in text and "exec_switch_root_now" not in text:
        raise RuntimeError(f"switch-root command returned before handoff\n{text}")
    if not payload["saw_exec_marker"] or not payload["saw_sha_match"]:
        raise RuntimeError(f"switch-root handoff marker missing\n{text}")
    return payload


def ssh_base(args: argparse.Namespace, key_path: Path) -> list[object]:
    return [
        "ssh",
        "-i",
        key_path,
        "-p",
        str(args.ssh_port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        f"ConnectTimeout={int(args.ssh_connect_timeout)}",
        "-o",
        "BatchMode=yes",
        f"root@{args.device_ip}",
    ]


def observe_d3_marker(args: argparse.Namespace, key_path: Path) -> dict[str, Any]:
    deadline = time.monotonic() + args.ssh_wait_timeout
    last: dict[str, Any] | None = None
    remote_script = (
        "cat /run/a90-d3-marker 2>/dev/null; "
        "echo proc1_comm=$(cat /proc/1/comm 2>/dev/null); "
        "echo debian_version=$(cat /etc/debian_version 2>/dev/null)"
    )
    while time.monotonic() < deadline:
        result = run_host(
            [*ssh_base(args, key_path), remote_script],
            timeout=args.ssh_connect_timeout + 10.0,
            check=False,
        )
        last = result
        text = result.get("stdout", "") + result.get("stderr", "")
        if result["returncode"] == 0 and "A90D3_MARKER" in text and "proc1_comm=init" in text:
            return {
                **result,
                "marker_ok": True,
                "proc1_comm_init": True,
                "debian_version": (re.search(r"debian_version=([^\s\r\n]+)", text) or [None, None])[1],
            }
        time.sleep(args.ssh_poll_interval)
    raise RuntimeError(f"D3 marker not observed before timeout; last={last}")


def wait_for_candidate_return(args: argparse.Namespace) -> dict[str, Any]:
    deadline = time.monotonic() + args.autoreboot_wait_timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            version = d1.run_cmd(args.host, args.port, args.timeout, ["version"], allow_error=True)
            text = str(version.get("text") or "")
            if EXPECTED_CANDIDATE_VERSION in text and EXPECTED_CANDIDATE_BUILD in text:
                selftest = d1.run_cmd(args.host, args.port, args.timeout, ["selftest"])
                if "fail=0" not in str(selftest.get("text") or ""):
                    raise RuntimeError("candidate returned but selftest did not report fail=0")
                return {"version": version, "selftest": selftest}
            last = text
        except Exception as exc:  # noqa: BLE001 - device is rebooting; keep polling
            last = str(exc)
        time.sleep(args.autoreboot_poll_interval)
    raise RuntimeError(f"candidate did not return after mandatory auto-reboot; last={last!r}")


def validate_timeline(events: list[dict[str, str]]) -> None:
    names = [event.get("name") for event in events]
    missing = [name for name in REQUIRED_TIMELINE_EVENTS if name not in names]
    if missing:
        raise RuntimeError(f"timeline missing required events: {missing}")


def run_live(args: argparse.Namespace) -> int:
    now = _dt.datetime.now(_dt.UTC).replace(microsecond=0)
    run_id = args.run_id or "d3-switchroot-" + now.strftime("%Y%m%dT%H%M%SZ")
    run_dir = d1.normalize_run_dir(args.run_base / run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    events: list[dict[str, str]] = []
    steps: dict[str, Any] = {"run_id": run_id}
    rollback_needed = False
    handoff_started = False
    staging_started = False
    staging_done = False

    def save_step(name: str, payload: Any) -> None:
        steps[name] = payload
        write_json(run_dir / f"{name}.json", payload)
        write_json(run_dir / "summary.json", steps)

    try:
        save_step("local_artifacts", verify_local_artifacts(args))
        key = d2.generate_ssh_key(run_dir, run_id.replace("d3-switchroot-", "d3-"))
        public_key = d2.read_public_key(run_dir)
        save_step("ssh_key", key)
        keyed = prepare_keyed_image(args, run_dir, public_key)
        save_step("keyed_image", keyed)

        add_event(events, run_dir, "candidate_flash_start")
        save_step(
            "candidate_flash",
            run_host(
                flash_command(args.candidate_boot, EXPECTED_CANDIDATE_SHA256, EXPECTED_CANDIDATE_VERSION, args),
                timeout=args.flash_command_timeout,
            ),
        )
        rollback_needed = True
        add_event(events, run_dir, "candidate_flash_done")
        add_event(events, run_dir, "candidate_boot_ready")

        add_event(events, run_dir, "live_session_start")
        keyed_path = run_dir / "d3-sysvinit-keyed.img"
        staging_started = True
        save_step("stage_keyed_image", install_keyed_image(args, keyed_path, str(keyed["keyed_sha256"])))
        staging_done = True
        remote_sha, remote_sha_record = d1.remote_image_sha(args.host, args.port, args.timeout, args.remote_image)
        save_step("remote_image_sha", {"sha256": remote_sha, "record": remote_sha_record})
        if remote_sha != keyed["keyed_sha256"]:
            raise RuntimeError(f"remote D3 image sha mismatch: remote={remote_sha} local={keyed['keyed_sha256']}")
        save_step("switch_root_command", run_switch_root_command(args, str(keyed["keyed_sha256"])))
        handoff_started = True
        save_step("ssh_marker", observe_d3_marker(args, run_dir / "d2_ssh_key_ed25519"))
        save_step("candidate_return", wait_for_candidate_return(args))
        add_event(events, run_dir, "live_session_end")

        add_event(events, run_dir, "rollback_flash_start")
        save_step(
            "rollback_flash",
            run_host(
                flash_command(args.rollback_boot, EXPECTED_ROLLBACK_SHA256, EXPECTED_ROLLBACK_VERSION, args),
                timeout=args.flash_command_timeout,
            ),
        )
        rollback_needed = False
        add_event(events, run_dir, "rollback_flash_done")
        final = {
            "version": d1.run_cmd(args.host, args.port, args.timeout, ["version"]),
            "selftest": d1.run_cmd(args.host, args.port, args.timeout, ["selftest"]),
        }
        save_step("final_v2321", final)
        if "v2321-usb-clean-identity-rodata" not in final["version"]["text"]:
            raise RuntimeError("final version is not v2321")
        if "fail=0" not in final["selftest"]["text"]:
            raise RuntimeError("final selftest is not fail=0")
        add_event(events, run_dir, "rollback_boot_ready")
        validate_timeline(events)
        save_step("result", {
            "decision": "server-distro-d3b-switchroot-live-pass",
            "run_dir": str(run_dir.relative_to(REPO_ROOT)),
            "timeline_events": [event["name"] for event in events],
            "final_v2321": True,
            "final_selftest_fail0": True,
        })
        print(json.dumps(steps["result"], indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        save_step("error", {"type": type(exc).__name__, "message": str(exc)})
        if rollback_needed:
            if staging_started and not staging_done and not handoff_started:
                save_step("cancel_foreground_run_after_stage_error", cancel_foreground_run(args))
            if handoff_started:
                try:
                    save_step("candidate_return_after_error", wait_for_candidate_return(args))
                    if "live_session_end" not in [event.get("name") for event in events]:
                        add_event(events, run_dir, "live_session_end")
                except Exception as return_exc:  # noqa: BLE001
                    save_step(
                        "candidate_return_after_error_failed",
                        {"type": type(return_exc).__name__, "message": str(return_exc)},
                    )
            add_event(events, run_dir, "rollback_flash_start")
            try:
                save_step(
                    "rollback_flash_after_error",
                    run_host(
                        flash_command(args.rollback_boot, EXPECTED_ROLLBACK_SHA256, EXPECTED_ROLLBACK_VERSION, args),
                        timeout=args.flash_command_timeout,
                        check=False,
                    ),
                )
                add_event(events, run_dir, "rollback_flash_done")
                final = {
                    "version": d1.run_cmd(args.host, args.port, args.timeout, ["version"], allow_error=True),
                    "selftest": d1.run_cmd(args.host, args.port, args.timeout, ["selftest"], allow_error=True),
                }
                save_step("rollback_final_after_error", final)
                add_event(events, run_dir, "rollback_boot_ready")
            except Exception as rollback_exc:  # noqa: BLE001
                save_step("rollback_error", {"type": type(rollback_exc).__name__, "message": str(rollback_exc)})
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--run-base", type=Path, default=DEFAULT_RUN_BASE)
    parser.add_argument("--run-id")
    parser.add_argument("--candidate-boot", type=Path, default=DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--rollback-boot", type=Path, default=DEFAULT_ROLLBACK_BOOT)
    parser.add_argument("--d3-source-image", type=Path, default=DEFAULT_D3_SOURCE_IMAGE)
    parser.add_argument("--remote-image", default=DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--local-image", type=Path, default=DEFAULT_D3_SOURCE_IMAGE)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--bridge-timeout", type=float, default=120.0)
    parser.add_argument("--flash-bridge-timeout", type=float, default=180.0)
    parser.add_argument("--flash-reboot-timeout", type=float, default=180.0)
    parser.add_argument("--flash-command-timeout", type=float, default=480.0)
    parser.add_argument("--switch-timeout", type=float, default=45.0)
    parser.add_argument("--debugfs-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=60.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=DEFAULT_TRANSFER_DELAY)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--ssh-connect-timeout", type=float, default=8.0)
    parser.add_argument("--ssh-wait-timeout", type=float, default=90.0)
    parser.add_argument("--ssh-poll-interval", type=float, default=3.0)
    parser.add_argument("--autoreboot-wait-timeout", type=float, default=180.0)
    parser.add_argument("--autoreboot-poll-interval", type=float, default=5.0)
    args = parser.parse_args(argv)

    args.candidate_boot = args.candidate_boot.resolve()
    args.rollback_boot = args.rollback_boot.resolve()
    args.d3_source_image = args.d3_source_image.resolve()
    return run_live(args)


if __name__ == "__main__":
    raise SystemExit(main())
