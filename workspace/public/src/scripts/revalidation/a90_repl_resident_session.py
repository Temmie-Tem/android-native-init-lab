#!/usr/bin/env python3
"""Run REPL proof/observation batches in one resident v1-repl flash session.

Resident-session mode:
  flash v1-repl once,
  repeat: warm reboot resident v1-repl, health check, run one bounded batch,
  rollback v2321 once at the end.

The script never flashes directly; boot writes go through native_init_flash.py.
Private per-target evidence is flushed after each completed target so a crash
loses only the in-flight target and unrun remainder. Batch items are either
plain call-proof targets or vfs-bundle:<name> observation bundles.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
SCRIPT_DIR = Path(__file__).resolve().parent

import a90_bridge  # noqa: E402
import a90_repl  # noqa: E402
import a90ctl  # noqa: E402


DEFAULT_MAP = REPO_ROOT / "workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map"
DEFAULT_CANDIDATE_IMAGE = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img"
)
DEFAULT_CANDIDATE_SHA256 = "b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65"
DEFAULT_ROLLBACK_IMAGE = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
)
DEFAULT_ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
DEFAULT_DEEP_FALLBACK_IMAGE = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
)
DEFAULT_DEEP_FALLBACK_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
DEFAULT_FINAL_FALLBACK_IMAGE = REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
DEFAULT_RUNS_DIR = REPO_ROOT / "workspace/private/runs/kernel"
NATIVE_FLASH = SCRIPT_DIR / "native_init_flash.py"
BRIDGE_TOOL = SCRIPT_DIR / "a90_bridge.py"

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
VFS_BUNDLE_PREFIX = "vfs-bundle:"
MIN_RESIDENT_SESSION_TARGETS = 2


class ResidentSessionError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_label() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
    tmp.replace(path)
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def append_jsonl_flush(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, sort_keys=True) + "\n")
        fp.flush()
        os.fsync(fp.fileno())


def mark_event(run_dir: Path, events: list[dict[str, str]], name: str) -> None:
    events.append({"name": name, "timestamp_utc": utc_now()})
    atomic_write_json(run_dir / "timeline.json", {"events": events})


def validate_timeline(events: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen = {item.get("name") for item in events}
    missing = [name for name in REQUIRED_TIMELINE_EVENTS if name not in seen]
    if missing:
        errors.append("missing required events: " + ", ".join(missing))
    for index, item in enumerate(events):
        if set(item) != {"name", "timestamp_utc"}:
            errors.append(f"events[{index}] keys must be exactly name,timestamp_utc")
    return errors


def has_event(events: list[dict[str, str]], name: str) -> bool:
    return any(item.get("name") == name for item in events)


def mark_live_end_on_exception(run_dir: Path, events: list[dict[str, str]]) -> None:
    if not has_event(events, "live_session_start") or has_event(events, "live_session_end"):
        return
    for item in reversed(events):
        name = item.get("name", "")
        if name.startswith("batch_") and name.endswith("_live_start"):
            batch_end = name[:-len("_live_start")] + "_live_end"
            if not has_event(events, batch_end):
                mark_event(run_dir, events, batch_end)
            break
    mark_event(run_dir, events, "live_session_end")


def flash_command(args: argparse.Namespace,
                  image: Path,
                  sha256: str,
                  *,
                  from_native: bool = True) -> list[str]:
    command = [
        sys.executable,
        str(NATIVE_FLASH),
    ]
    if from_native:
        command.append("--from-native")
    command.extend([
        "--verify-protocol",
        "selftest",
        "--adb",
        getattr(args, "adb", "adb"),
    ])
    serial = getattr(args, "serial", None)
    if serial:
        command.extend(["--serial", serial])
    command.extend([
        "--bridge-host",
        args.host,
        "--bridge-port",
        str(args.port),
        "--bridge-timeout",
        str(args.flash_bridge_timeout),
        "--recovery-timeout",
        str(args.recovery_timeout),
        "--expect-sha256",
        sha256,
        "--expect-readback-sha256",
        sha256,
        str(image),
    ])
    return command


def bridge_restart_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(BRIDGE_TOOL),
        "restart",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--discovered",
        "--allow-device-change",
        "--wait-timeout",
        str(args.bridge_restart_timeout),
    ]


def run_subprocess(command: list[str], *, cwd: Path, timeout: float, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    payload = {
        "command": command,
        "started_utc": started,
        "ended_utc": utc_now(),
        "returncode": completed.returncode,
        "output": completed.stdout,
    }
    atomic_write_json(output_path, payload)
    if completed.returncode != 0:
        raise ResidentSessionError(
            f"command failed rc={completed.returncode}: {' '.join(command)}"
        )


def adb_recovery_present(args: argparse.Namespace) -> bool:
    command = [getattr(args, "adb", "adb"), "devices"]
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10.0,
        check=False,
    )
    serial = getattr(args, "serial", None)
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if serial and parts[0] != serial:
            continue
        if parts[1] == "recovery":
            return True
    return False


def run_flash(args: argparse.Namespace,
              image: Path,
              sha256: str,
              *,
              output_path: Path,
              from_native: bool) -> None:
    run_subprocess(
        flash_command(args, image, sha256, from_native=from_native),
        cwd=REPO_ROOT,
        timeout=args.flash_timeout,
        output_path=output_path,
    )


def run_rollback_flash(args: argparse.Namespace, run_dir: Path, stem: str) -> None:
    try:
        run_flash(
            args,
            args.rollback_image,
            args.rollback_sha256,
            output_path=run_dir / f"{stem}.json",
            from_native=True,
        )
        return
    except Exception as exc:
        atomic_write_json(
            run_dir / f"{stem}-from-native-error.json",
            {
                "ok": False,
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "recovery_present_after_error": adb_recovery_present(args),
            },
        )
    if not adb_recovery_present(args):
        raise ResidentSessionError("rollback from-native failed and recovery ADB is not present")
    run_flash(
        args,
        args.rollback_image,
        args.rollback_sha256,
        output_path=run_dir / f"{stem}-recovery-direct.json",
        from_native=False,
    )


def parse_batches(batch_args: list[list[str]] | None, *, max_batch_size: int) -> tuple[tuple[str, ...], ...]:
    if not batch_args:
        raise ResidentSessionError("at least one --batch is required")
    out: list[tuple[str, ...]] = []
    supported = set(a90_repl.CALL_PROOF_TARGETS)
    supported.update(f"{VFS_BUNDLE_PREFIX}{name}" for name in a90_repl.VFS_READ_BUNDLES)
    for raw_batch in batch_args:
        targets: list[str] = []
        for token in raw_batch:
            targets.extend(part for part in token.split(",") if part)
        if not targets:
            raise ResidentSessionError("empty --batch is not allowed")
        if len(targets) > max_batch_size:
            raise ResidentSessionError(
                f"batch has {len(targets)} targets; max bounded size is {max_batch_size}"
            )
        unknown = [target for target in targets if target not in supported]
        if unknown:
            raise ResidentSessionError(
                "unsupported call-proof target(s): "
                + ", ".join(unknown)
                + "; supported="
                + ", ".join(sorted(supported))
            )
        out.append(tuple(targets))
    target_count = sum(len(batch) for batch in out)
    if target_count < MIN_RESIDENT_SESSION_TARGETS:
        raise ResidentSessionError(
            f"resident sessions require at least {MIN_RESIDENT_SESSION_TARGETS} targets; "
            "single-target resident runs are forbidden because flash-once cost is not amortized"
        )
    return tuple(out)


def is_vfs_bundle_item(target: str) -> bool:
    return target.startswith(VFS_BUNDLE_PREFIX)


def vfs_bundle_name(target: str) -> str:
    if not is_vfs_bundle_item(target):
        raise ResidentSessionError(f"not a vfs-bundle batch item: {target!r}")
    name = target[len(VFS_BUNDLE_PREFIX):]
    if name not in a90_repl.VFS_READ_BUNDLES:
        raise ResidentSessionError(
            f"unsupported vfs-read bundle {name!r}; supported={sorted(a90_repl.VFS_READ_BUNDLES)}"
        )
    return name


def validate_image(path: Path, expected_sha256: str, *, label: str) -> dict[str, object]:
    if not path.is_file():
        raise ResidentSessionError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ResidentSessionError(
            f"{label} sha256 mismatch: expected={expected_sha256} actual={actual}"
        )
    return {"path": str(path), "sha256": actual, "size": path.stat().st_size}


def preflight(args: argparse.Namespace, batches: tuple[tuple[str, ...], ...]) -> dict[str, object]:
    candidate = validate_image(args.candidate_image, args.candidate_sha256, label="candidate image")
    rollback = validate_image(args.rollback_image, args.rollback_sha256, label="rollback image")
    deep = validate_image(args.deep_fallback_image, args.deep_fallback_sha256, label="deep fallback image")
    if not args.final_fallback_image.is_file():
        raise ResidentSessionError(f"final fallback image missing: {args.final_fallback_image}")
    if not args.map.is_file():
        raise ResidentSessionError(f"System.map missing: {args.map}")
    if not args.image.is_file():
        raise ResidentSessionError(f"static image missing: {args.image}")
    if not NATIVE_FLASH.is_file():
        raise ResidentSessionError(f"native flash helper missing: {NATIVE_FLASH}")
    if not BRIDGE_TOOL.is_file():
        raise ResidentSessionError(f"bridge helper missing: {BRIDGE_TOOL}")
    return {
        "candidate": candidate,
        "rollback": rollback,
        "deep_fallback": deep,
        "final_fallback": {"path": str(args.final_fallback_image), "size": args.final_fallback_image.stat().st_size},
        "map": str(args.map),
        "static_image": str(args.image),
        "batch_count": len(batches),
        "target_count": sum(len(batch) for batch in batches),
        "batches": [list(batch) for batch in batches],
        "max_batch_size": args.max_batch_size,
        "resident_session_mode": True,
    }


def run_health_check(args: argparse.Namespace, out_dir: Path, label: str) -> dict[str, object]:
    out: dict[str, object] = {"label": label, "commands": {}, "retry_errors": {}}
    for command in ("version", "status", "selftest"):
        result = None
        last_error = ""
        for attempt in range(1, args.health_retries + 2):
            try:
                result = a90ctl.run_cmdv1_command(
                    args.host,
                    args.port,
                    args.health_timeout,
                    [command],
                )
            except Exception as exc:  # noqa: BLE001 - safe health commands may retry after serial noise
                last_error = str(exc)
                out["retry_errors"].setdefault(command, []).append({
                    "attempt": attempt,
                    "exception_type": type(exc).__name__,
                    "exception": last_error,
                })
                if attempt > args.health_retries:
                    atomic_write_json(out_dir / f"{label}-health.json", out)
                    raise
                run_subprocess(
                    bridge_restart_command(args),
                    cwd=REPO_ROOT,
                    timeout=max(5.0, args.bridge_restart_timeout + 5.0),
                    output_path=out_dir / f"{label}-{command}-health-bridge-restart-{attempt:02d}.json",
                )
                continue
            if result.rc == 0 and result.status == "ok" and (
                command != "selftest" or "fail=0" in result.text
            ):
                break
            if result.rc != 0 or result.status != "ok":
                last_error = (
                    f"{label} health command {command} failed "
                    f"rc={result.rc} status={result.status}"
                )
            else:
                last_error = f"{label} selftest did not report fail=0"
            out["retry_errors"].setdefault(command, []).append({
                "attempt": attempt,
                "exception_type": "ResidentSessionError",
                "exception": last_error,
                "rc": result.rc,
                "status": result.status,
                "text_tail": result.text[-240:],
            })
            if attempt > args.health_retries:
                break
            run_subprocess(
                bridge_restart_command(args),
                cwd=REPO_ROOT,
                timeout=max(5.0, args.bridge_restart_timeout + 5.0),
                output_path=out_dir / f"{label}-{command}-health-bridge-restart-{attempt:02d}.json",
            )
        if result is None:
            raise ResidentSessionError(f"{label} health command {command} produced no result")
        out["commands"][command] = {
            "rc": result.rc,
            "status": result.status,
            "text": result.text,
        }
        if result.rc != 0 or result.status != "ok" or (command == "selftest" and "fail=0" not in result.text):
            atomic_write_json(out_dir / f"{label}-health.json", out)
            raise ResidentSessionError(last_error)
    atomic_write_json(out_dir / f"{label}-health.json", out)
    return out


def send_warm_reboot(args: argparse.Namespace, out_dir: Path, batch_index: int) -> None:
    text = ""
    error = ""
    hide_text = ""
    started = utc_now()
    try:
        hide_text = a90ctl.bridge_exchange(
            args.host,
            args.port,
            "hide",
            min(args.warm_reboot_command_timeout, 8.0),
            markers=(b"[busy]", b"[done]", b"[err]"),
            require_prompt_after_end=False,
            post_marker_drain_sec=0.0,
        )
    except Exception as exc:  # noqa: BLE001 - hide is best effort before reboot
        hide_text = f"hide_error={exc!r}"
    try:
        text = a90ctl.bridge_exchange(
            args.host,
            args.port,
            "reboot",
            args.warm_reboot_command_timeout,
            markers=(b"reboot: syncing", b"[busy]", b"[err]"),
            require_prompt_after_end=False,
            post_marker_drain_sec=0.0,
        )
    except Exception as exc:  # noqa: BLE001 - reboot commonly drops the transport
        error = repr(exc)
    payload = {
        "batch_index": batch_index,
        "started_utc": started,
        "ended_utc": utc_now(),
        "hide_text": hide_text,
        "text": text,
        "transport_error": error,
        "accepted_no_end_marker": True,
    }
    atomic_write_json(out_dir / f"batch-{batch_index:03d}-warm-reboot-send.json", payload)
    if "[busy]" in text or "[err]" in text:
        raise ResidentSessionError(f"warm reboot was rejected by native shell: {text!r}")


def restart_bridge_and_wait_health(args: argparse.Namespace, out_dir: Path, label: str) -> dict[str, object]:
    deadline = time.monotonic() + args.warm_reboot_total_timeout
    attempt = 0
    last_error = ""
    while time.monotonic() < deadline:
        attempt += 1
        try:
            run_subprocess(
                bridge_restart_command(args),
                cwd=REPO_ROOT,
                timeout=max(5.0, args.bridge_restart_timeout + 5.0),
                output_path=out_dir / f"{label}-bridge-restart-{attempt:02d}.json",
            )
            return run_health_check(args, out_dir, f"{label}-post-reboot")
        except Exception as exc:  # noqa: BLE001 - loop until bounded warm-reboot timeout
            last_error = repr(exc)
            time.sleep(args.warm_reboot_poll_sec)
    raise ResidentSessionError(f"{label} did not return healthy after warm reboot: {last_error}")


def target_result_path(batch_dir: Path, ordinal: int, target: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "_.+-" else "_" for ch in target)
    return batch_dir / "target-results" / f"{ordinal:03d}-{safe}.json"


def flush_target_result(batch_dir: Path,
                        batch_index: int,
                        ordinal: int,
                        target: str,
                        summary: dict[str, object],
                        private: dict[str, object]) -> None:
    payload = {
        "batch_index": batch_index,
        "target_ordinal": ordinal,
        "target": target,
        "flushed_utc": utc_now(),
        "summary": summary,
        "_private": private,
        "raw_runtime_values_private_only": True,
    }
    out_path = target_result_path(batch_dir, ordinal, target)
    atomic_write_json(out_path, payload)
    append_jsonl_flush(
        batch_dir / "target-results.jsonl",
        {
            "batch_index": batch_index,
            "target_ordinal": ordinal,
            "target": target,
            "ok": bool(summary.get("ok")),
            "path": str(out_path.relative_to(batch_dir)),
            "timestamp_utc": payload["flushed_utc"],
        },
    )


def run_repl_selftest(args: argparse.Namespace,
                      symbols: dict[str, a90_repl.Symbol],
                      image: a90_repl.StaticImage,
                      out_dir: Path,
                      *,
                      prefix: str = "candidate") -> None:
    for attempt in (1, 2):
        session = a90_repl.ReplSession(a90_repl.ReplConfig(
            host=args.host,
            port=args.port,
            timeout=args.repl_timeout,
            dmesg_tail=args.dmesg_tail,
            safe_op_retries=args.safe_op_retries,
            retry_delay_sec=args.retry_delay_sec,
        ))
        try:
            summary = a90_repl.run_selftest(
                session,
                symbols,
                image,
                peek_symbols=("kgsl_pwrctrl_force_no_nap_store", "__kmalloc"),
                call_symbol="printk",
            )
        except Exception as exc:  # noqa: BLE001 - bounded retry for serial fragmentation only
            atomic_write_json(
                out_dir / f"{prefix}-repl-selftest-attempt-{attempt}-error.json",
                {
                    "ok": False,
                    "attempt": attempt,
                    "exception_type": type(exc).__name__,
                    "exception": str(exc),
                },
            )
            if attempt >= 2:
                raise
            run_subprocess(
                bridge_restart_command(args),
                cwd=REPO_ROOT,
                timeout=max(5.0, args.bridge_restart_timeout + 5.0),
                output_path=out_dir / f"{prefix}-repl-selftest-bridge-restart.json",
            )
            run_health_check(args, out_dir, f"{prefix}-repl-selftest-retry")
            continue
        atomic_write_json(out_dir / f"{prefix}-repl-selftest.json", summary)
        if not summary.get("ok"):
            raise ResidentSessionError(f"{prefix} REPL selftest failed")
        return


def run_one_batch(args: argparse.Namespace,
                  symbols: dict[str, a90_repl.Symbol],
                  image: a90_repl.StaticImage,
                  batch: tuple[str, ...],
                  batch_index: int,
                  run_dir: Path) -> dict[str, object]:
    batch_dir = run_dir / f"batch-{batch_index:03d}"
    session = a90_repl.ReplSession(a90_repl.ReplConfig(
        host=args.host,
        port=args.port,
        timeout=args.repl_timeout,
        dmesg_tail=args.dmesg_tail,
        safe_op_retries=args.safe_op_retries,
        retry_delay_sec=args.retry_delay_sec,
    ))
    flushed: list[str] = []
    target_summaries: list[dict[str, object]] = []
    private_by_target: dict[str, object] = {}

    try:
        for target in batch:
            if is_vfs_bundle_item(target):
                summary, private = a90_repl.run_vfs_read_bundle(
                    session,
                    symbols,
                    image,
                    vfs_bundle_name(target),
                    alloc_size=args.alloc_size,
                    source_root=args.source_root,
                    gfp_header=args.gfp_header,
                    gfp_value=args.gfp,
                )
            else:
                summary, private = a90_repl.run_call_proof(
                    session,
                    symbols,
                    image,
                    target,
                    alloc_size=args.alloc_size,
                    max_expected_return=args.max_expected_return,
                    source_root=args.source_root,
                    gfp_header=args.gfp_header,
                    gfp_value=args.gfp,
                )
            flushed.append(target)
            target_summaries.append(summary)
            private_by_target[target] = private
            flush_target_result(batch_dir, batch_index, len(flushed), target, summary, private)
            if not summary.get("ok"):
                break
    except Exception as exc:  # noqa: BLE001 - preserve completed target evidence, attribute failure
        failure = {
            "ok": False,
            "decision": "a90-repl-resident-session-batch-exception",
            "batch_index": batch_index,
            "targets": list(batch),
            "completed_targets": flushed,
            "in_flight_or_next_target": batch[len(flushed)] if len(flushed) < len(batch) else None,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
        }
        atomic_write_json(batch_dir / "batch-summary.json", failure)
        raise

    ok = len(target_summaries) == len(batch) and all(bool(item.get("ok")) for item in target_summaries)
    payload = {
        "ok": ok,
        "decision": f"a90-repl-resident-session-batch-{'pass' if ok else 'fail'}",
        "target_count": len(batch),
        "targets": list(batch),
        "completed_target_count": len(target_summaries),
        "stopped_after_failure": len(target_summaries) < len(batch) or any(
            not bool(item.get("ok")) for item in target_summaries
        ),
        "target_summaries": target_summaries,
        "batch_index": batch_index,
        "resident_session_mode": True,
        "_private": {"targets": private_by_target},
    }
    atomic_write_json(batch_dir / "batch-summary.json", payload)
    return payload


def dry_run(args: argparse.Namespace, batches: tuple[tuple[str, ...], ...], plan: dict[str, object]) -> int:
    payload = {
        "ok": True,
        "dry_run": True,
        "plan": plan,
        "candidate_flash_command": flash_command(
            args, args.candidate_image, args.candidate_sha256, from_native=True
        ),
        "rollback_flash_command": flash_command(
            args, args.rollback_image, args.rollback_sha256, from_native=True
        ),
        "rollback_recovery_direct_fallback_command": flash_command(
            args, args.rollback_image, args.rollback_sha256, from_native=False
        ),
        "bridge_restart_command": bridge_restart_command(args),
        "timeline_schema": {"top_level_keys": ["events"], "required_events": list(REQUIRED_TIMELINE_EVENTS)},
        "batches": [list(batch) for batch in batches],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def run_resident_session(args: argparse.Namespace, batches: tuple[tuple[str, ...], ...]) -> int:
    run_dir = args.run_dir or (DEFAULT_RUNS_DIR / f"repl-resident-session-{run_label()}")
    run_dir.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, str]] = []
    plan = preflight(args, batches)
    atomic_write_json(run_dir / "resident-session-plan.json", plan)

    if args.dry_run:
        return dry_run(args, batches, plan)

    symbols = a90_repl.load_system_map(args.map)
    image = a90_repl.load_static_image(args.image)
    candidate_flashed = False
    rolled_back = False
    session_ok = False
    batch_summaries: list[dict[str, object]] = []
    try:
        run_health_check(args, run_dir, "baseline")

        mark_event(run_dir, events, "candidate_flash_start")
        run_flash(
            args,
            args.candidate_image,
            args.candidate_sha256,
            output_path=run_dir / "candidate-flash.json",
            from_native=True,
        )
        candidate_flashed = True
        mark_event(run_dir, events, "candidate_flash_done")
        run_health_check(args, run_dir, "candidate")
        run_repl_selftest(args, symbols, image, run_dir, prefix="candidate")
        mark_event(run_dir, events, "candidate_boot_ready")

        mark_event(run_dir, events, "live_session_start")
        for batch_index, batch in enumerate(batches, start=1):
            mark_event(run_dir, events, f"batch_{batch_index:03d}_warm_reboot_start")
            send_warm_reboot(args, run_dir, batch_index)
            restart_bridge_and_wait_health(args, run_dir, f"batch-{batch_index:03d}")
            mark_event(run_dir, events, f"batch_{batch_index:03d}_warm_reboot_done")
            mark_event(run_dir, events, f"batch_{batch_index:03d}_boot_ready")
            run_repl_selftest(args, symbols, image, run_dir, prefix=f"batch-{batch_index:03d}")
            mark_event(run_dir, events, f"batch_{batch_index:03d}_repl_selftest_ready")
            mark_event(run_dir, events, f"batch_{batch_index:03d}_live_start")
            summary = run_one_batch(args, symbols, image, batch, batch_index, run_dir)
            batch_summaries.append(summary)
            mark_event(run_dir, events, f"batch_{batch_index:03d}_live_end")
            run_health_check(args, run_dir, f"batch-{batch_index:03d}-post-batch")
            mark_event(run_dir, events, f"batch_{batch_index:03d}_health_ready")
            if not summary.get("ok"):
                break
        mark_event(run_dir, events, "live_session_end")

        mark_event(run_dir, events, "rollback_flash_start")
        run_rollback_flash(args, run_dir, "rollback-flash")
        rolled_back = True
        mark_event(run_dir, events, "rollback_flash_done")
        run_health_check(args, run_dir, "rollback")
        mark_event(run_dir, events, "rollback_boot_ready")
        session_ok = bool(batch_summaries) and all(bool(item.get("ok")) for item in batch_summaries)
        timeline_errors = validate_timeline(events)
        summary_payload = {
            "ok": session_ok and not timeline_errors,
            "decision": "a90-repl-resident-session-pass" if session_ok and not timeline_errors
            else "a90-repl-resident-session-fail",
            "run_dir": str(run_dir),
            "batch_count": len(batches),
            "completed_batch_count": len(batch_summaries),
            "target_count": sum(len(batch) for batch in batches),
            "completed_target_count": sum(int(item.get("completed_target_count", 0)) for item in batch_summaries),
            "flash_count": 2,
            "candidate_flashed_once": True,
            "rollback_flashed_once": True,
            "warm_reboot_between_batches": True,
            "timeline_errors": timeline_errors,
            "raw_runtime_values_private_only": True,
        }
        atomic_write_json(run_dir / "resident-session-summary.json", summary_payload)
        print(json.dumps({k: v for k, v in summary_payload.items() if k != "run_dir"}, indent=2, sort_keys=True))
        return 0 if summary_payload["ok"] else 1
    finally:
        if candidate_flashed and not rolled_back:
            try:
                mark_live_end_on_exception(run_dir, events)
                if not has_event(events, "rollback_flash_start"):
                    mark_event(run_dir, events, "rollback_flash_start")
                run_rollback_flash(args, run_dir, "rollback-flash-finally")
                rolled_back = True
                if not has_event(events, "rollback_flash_done"):
                    mark_event(run_dir, events, "rollback_flash_done")
                run_health_check(args, run_dir, "rollback-finally")
                if not has_event(events, "rollback_boot_ready"):
                    mark_event(run_dir, events, "rollback_boot_ready")
            except Exception as exc:  # noqa: BLE001 - leave an incident artifact before bubbling
                atomic_write_json(
                    run_dir / "resident-session-rollback-incident.json",
                    {
                        "ok": False,
                        "candidate_flashed": candidate_flashed,
                        "rolled_back": rolled_back,
                        "exception_type": type(exc).__name__,
                        "exception": str(exc),
                    },
                )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--image", type=Path, default=DEFAULT_CANDIDATE_IMAGE,
                        help="static image matching the map; defaults to the v1-repl boot image")
    parser.add_argument("--candidate-image", type=Path, default=DEFAULT_CANDIDATE_IMAGE)
    parser.add_argument("--candidate-sha256", default=DEFAULT_CANDIDATE_SHA256)
    parser.add_argument("--rollback-image", type=Path, default=DEFAULT_ROLLBACK_IMAGE)
    parser.add_argument("--rollback-sha256", default=DEFAULT_ROLLBACK_SHA256)
    parser.add_argument("--deep-fallback-image", type=Path, default=DEFAULT_DEEP_FALLBACK_IMAGE)
    parser.add_argument("--deep-fallback-sha256", default=DEFAULT_DEEP_FALLBACK_SHA256)
    parser.add_argument("--final-fallback-image", type=Path, default=DEFAULT_FINAL_FALLBACK_IMAGE)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--batch", action="append", nargs="+", default=[],
                        help="one bounded batch; may be repeated; tokens may be comma-separated")
    parser.add_argument("--max-batch-size", type=int, default=30)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default=None)
    parser.add_argument("--health-timeout", type=float, default=45.0)
    parser.add_argument("--health-retries", type=int, default=1,
                        help="safe version/status/selftest retry count after bridge restart")
    parser.add_argument("--repl-timeout", type=float, default=25.0)
    parser.add_argument("--flash-timeout", type=float, default=600.0)
    parser.add_argument("--flash-bridge-timeout", type=float, default=180.0)
    parser.add_argument("--recovery-timeout", type=float, default=180.0)
    parser.add_argument("--bridge-restart-timeout", type=float, default=12.0)
    parser.add_argument("--warm-reboot-command-timeout", type=float, default=6.0)
    parser.add_argument("--warm-reboot-total-timeout", type=float, default=90.0)
    parser.add_argument("--warm-reboot-poll-sec", type=float, default=2.0)
    parser.add_argument("--dmesg-tail", type=int, default=a90_repl.DEFAULT_DMESG_TAIL)
    parser.add_argument("--safe-op-retries", type=int, default=2)
    parser.add_argument("--retry-delay-sec", type=float, default=0.2)
    parser.add_argument("--alloc-size", type=a90_repl.parse_int_auto, default=a90_repl.KMALLOC_ROUNDTRIP_SIZE)
    parser.add_argument("--max-expected-return", type=a90_repl.parse_int_auto, default=None)
    parser.add_argument("--source-root", type=Path, default=a90_repl.DEFAULT_KERNEL_SOURCE_ROOT)
    parser.add_argument("--gfp-header", type=Path, default=a90_repl.DEFAULT_GFP_HEADER)
    parser.add_argument("--gfp", type=a90_repl.parse_int_auto, default=None)
    parser.add_argument("--dry-run", action="store_true", help="validate plan and print commands without device action")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.max_batch_size <= 0:
        parser.error("--max-batch-size must be positive")
    try:
        batches = parse_batches(args.batch, max_batch_size=args.max_batch_size)
        return run_resident_session(args, batches)
    except ResidentSessionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
