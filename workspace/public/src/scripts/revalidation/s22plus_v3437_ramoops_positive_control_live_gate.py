#!/usr/bin/env python3
"""Guarded, resumable S22+ V3437 ramoops Android positive-control helper.

Only --offline-check and --print-plan are usable while the two V3437 AGENTS
exceptions are inactive. Every device-facing mode fails before device contact
unless the independent DTBO-maintenance and intentional-panic policies are both
active as required by that mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import s22plus_v3436_ramoops_positive_control_design as design
from s22plus_m3_observable_live_gate import (
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    adb_exec_out,
    adb_rows,
    adb_shell,
    flash_ap,
    odin_devices,
    repo_root,
    require_current_android,
    resolve,
    sha256_file,
    tar_members,
    utc_now,
    wait_for_odin,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability
from s22plus_ramoops_dtbo_m18_capture_live_gate import (
    reboot_android_to_download,
    wait_for_android_root,
)


DTBO_POLICY_MARKER = "S22+ V3437 ramoops DTBO maintenance live gate"
PANIC_POLICY_MARKER = "S22+ V3437 ramoops intentional-panic live gate"
DTBO_ACK_TOKEN = "S22PLUS-V3437-RAMOOPS-DTBO-MAINTENANCE"
PANIC_ACK_TOKEN = "S22PLUS-V3437-RAMOOPS-INTENTIONAL-PANIC"
RESTORE_ACK_TOKEN = "S22PLUS-V3437-RAMOOPS-STOCK-DTBO-RESTORE"
DTBO_ACTIVE_SENTINEL = "S22PLUS_V3437_DTBO_POLICY_STATE=ACTIVE"
PANIC_ACTIVE_SENTINEL = "S22PLUS_V3437_PANIC_POLICY_STATE=ACTIVE"

DTBO_POLICY_DRAFT = Path(
    "docs/operations/"
    "S22PLUS_V3437_RAMOOPS_DTBO_MAINTENANCE_AGENTS_EXCEPTION_DRAFT_2026-07-11.md"
)
PANIC_POLICY_DRAFT = Path(
    "docs/operations/"
    "S22PLUS_V3437_RAMOOPS_INTENTIONAL_PANIC_AGENTS_EXCEPTION_DRAFT_2026-07-11.md"
)
V3436_CONTRACT = design.OUTPUT
V3436_CONTRACT_SHA256 = (
    "c96ac1ce196e3584fab2af13f728655486d27ea4f417c93fd9b6558707d86de7"
)
DTBO_POLICY_DRAFT_SHA256 = (
    "5209cac861eae21c2ca52c8aab99603cebd128e2b7effa3d01984273caca1d9f"
)
PANIC_POLICY_DRAFT_SHA256 = (
    "cf519fc8caa111373dbe500b984ab9ebd351fe6c6fbff67c560bfb51a904c761"
)

SESSION_SCHEMA = "s22plus_v3437_ramoops_positive_control_session_v1"
TIMELINE_SCHEMA = "events:[{name,timestamp_utc}]"
HELPER_PATH = (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3437_ramoops_positive_control_live_gate.py"
)

RESULT_CODES = {
    "PASS_RAMOOPS_CONSOLE_DMESG_RETENTION": 0,
    "PARTIAL_PMSG_ONLY_NO_CONSOLE_DMESG_PROOF": 10,
    "NO_PROOF_NO_CURRENT_RUN_FRAME": 11,
    "FAIL_STALE_OR_COLLISION": 20,
    "FAIL_MALFORMED_OR_IDENTITY": 21,
    "FAIL_RAW_TOKEN_WITHOUT_VALID_FRAME": 22,
    "FAIL_PREPANIC_GATE_ROLLBACK": 23,
    "FAIL_PANIC_TRANSPORT_NOT_LOST": 24,
    "NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY": 30,
}

PSTORE_NAME_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


class GateError(RuntimeError):
    pass


def durable_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def durable_write_json(path: Path, value: Any) -> None:
    durable_write_bytes(
        path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )


def durable_append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(text)
        if not text.endswith("\n"):
            stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


@dataclass
class Timeline:
    path: Path
    events: list[dict[str, str]]

    @classmethod
    def create(cls, path: Path) -> "Timeline":
        timeline = cls(path=path, events=[])
        timeline.flush()
        return timeline

    @classmethod
    def load(cls, path: Path) -> "Timeline":
        value = json.loads(path.read_text(encoding="utf-8"))
        if set(value) != {"events"} or not isinstance(value["events"], list):
            raise GateError("timeline does not use the single events schema")
        timeline = cls(path=path, events=value["events"])
        timeline.validate()
        return timeline

    def validate(self) -> None:
        allowed = list(design.REQUIRED_TIMELINE_EVENTS)
        names: list[str] = []
        for event in self.events:
            if set(event) != {"name", "timestamp_utc"}:
                raise GateError("timeline event field set mismatch")
            if event["name"] not in allowed:
                raise GateError(f"unknown timeline event: {event['name']}")
            if event["name"] in names:
                raise GateError(f"duplicate timeline event: {event['name']}")
            names.append(event["name"])
        positions = [allowed.index(name) for name in names]
        if positions != sorted(positions):
            raise GateError("timeline event order mismatch")

    def append(self, name: str) -> None:
        candidate = Timeline(self.path, [*self.events, {"name": name, "timestamp_utc": utc_now()}])
        candidate.validate()
        self.events = candidate.events
        self.flush()

    def flush(self) -> None:
        durable_write_json(self.path, {"events": self.events})


@dataclass
class Session:
    path: Path
    value: dict[str, Any]

    @classmethod
    def create(cls, run_dir: Path, serial: str) -> "Session":
        value = {
            "schema": SESSION_SCHEMA,
            "run_id": secrets.token_hex(16),
            "state": "STOCK_BASELINE",
            "serial": serial,
            "created_at_utc": utc_now(),
            "contract_sha256": design.CONTRACT_SHA256,
            "candidate_dtbo_sha256": design.PINS[design.CANDIDATE_RAW],
            "classification": None,
            "panic_attempted": False,
        }
        session = cls(run_dir / "session.json", value)
        session.flush()
        return session

    @classmethod
    def load(cls, path: Path) -> "Session":
        value = json.loads(path.read_text(encoding="utf-8"))
        session = cls(path, value)
        session.validate()
        return session

    def validate(self) -> None:
        if self.value.get("schema") != SESSION_SCHEMA:
            raise GateError("session schema mismatch")
        if not design.RUN_ID_RE.fullmatch(str(self.value.get("run_id", ""))):
            raise GateError("session run ID malformed")
        if self.value.get("state") not in design.ALLOWED_TRANSITIONS:
            raise GateError("session state invalid")
        if self.value.get("contract_sha256") != design.CONTRACT_SHA256:
            raise GateError("session contract identity mismatch")
        if self.value.get("candidate_dtbo_sha256") != design.PINS[design.CANDIDATE_RAW]:
            raise GateError("session candidate identity mismatch")

    def advance(self, state: str) -> None:
        before = self.value["state"]
        if state not in design.ALLOWED_TRANSITIONS[before]:
            raise GateError(f"forbidden session transition: {before} -> {state}")
        self.value["state"] = state
        self.value["updated_at_utc"] = utc_now()
        self.flush()

    def set(self, key: str, value: Any) -> None:
        self.value[key] = value
        self.value["updated_at_utc"] = utc_now()
        self.flush()

    def abandon_evidence_for_recovery(
        self, result: str = "NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY"
    ) -> None:
        if self.value["state"] not in (
            "CANDIDATE_TRANSFER",
            "PATCHED_BOOT_WAIT",
            "PATCHED_PREFLIGHT",
            "BACKEND_PROVEN",
            "MARKERS_WRITTEN",
            "PANIC_TRIGGERED",
            "RECOVERY_WAIT",
            "PATCHED_ANDROID_RETURNED",
        ):
            raise GateError(
                f"cannot abandon evidence from state {self.value['state']}"
            )
        self.value["classification"] = {"result": result}
        self.value["state"] = "EVIDENCE_COLLECTED"
        self.value["evidence_abandoned_for_recovery"] = True
        self.value["updated_at_utc"] = utc_now()
        self.flush()

    def flush(self) -> None:
        self.validate()
        durable_write_json(self.path, self.value)


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_v3437_ramoops_{stamp}")
    for index in range(100):
        candidate = base if index == 0 else Path(f"{base}_{index:02d}")
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise GateError("could not allocate run directory")


def verify_artifacts(root: Path) -> dict[str, Any]:
    contract = design.build_contract(root)
    expected_contract = resolve(root, V3436_CONTRACT)
    if sha256_file(expected_contract) != V3436_CONTRACT_SHA256:
        raise GateError("V3436 contract file hash mismatch")
    candidate = resolve(root, design.CANDIDATE_AP)
    rollback = resolve(root, design.ROLLBACK_AP)
    if tar_members(candidate) != [design.EXPECTED_MEMBER]:
        raise GateError("candidate AP is not DTBO-only")
    if tar_members(rollback) != [design.EXPECTED_MEMBER]:
        raise GateError("rollback AP is not DTBO-only")
    return contract


def required_draft_markers() -> dict[Path, list[str]]:
    return {
        DTBO_POLICY_DRAFT: [
            "INERT DRAFT",
            DTBO_POLICY_MARKER,
            DTBO_ACTIVE_SENTINEL,
            HELPER_PATH,
            DTBO_ACK_TOKEN,
            RESTORE_ACK_TOKEN,
            design.PINS[design.CANDIDATE_AP],
            design.PINS[design.ROLLBACK_AP],
            design.PINS[design.CANDIDATE_RAW],
            design.PINS[design.STOCK_RAW],
            "exactly one candidate DTBO flash",
            "no panic",
        ],
        PANIC_POLICY_DRAFT: [
            "INERT DRAFT",
            PANIC_POLICY_MARKER,
            PANIC_ACTIVE_SENTINEL,
            HELPER_PATH,
            PANIC_ACK_TOKEN,
            design.CONTRACT_SHA256,
            design.PINS[design.CANDIDATE_RAW],
            "exactly one `S22RPC1`",
            "sysrq-trigger-c",
            "authorizes no partition write",
        ],
    }


def verify_policy_drafts(root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for relative, required in required_draft_markers().items():
        path = resolve(root, relative)
        if not path.is_file():
            raise GateError(f"missing policy draft: {relative}")
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        missing = [marker for marker in required if marker not in normalized]
        if missing:
            raise GateError(f"policy draft {relative} missing markers: {missing}")
        result[str(relative)] = missing
    hashes = {
        DTBO_POLICY_DRAFT: DTBO_POLICY_DRAFT_SHA256,
        PANIC_POLICY_DRAFT: PANIC_POLICY_DRAFT_SHA256,
    }
    for relative, expected in hashes.items():
        if expected == "TO_BE_PINNED":
            raise GateError(f"policy draft hash has not been pinned: {relative}")
        actual = sha256_file(resolve(root, relative))
        if actual != expected:
            raise GateError(f"policy draft hash mismatch for {relative}: {actual}")
    return result


def policy_status(root: Path) -> dict[str, bool]:
    agents = " ".join((root / "AGENTS.md").read_text(encoding="utf-8").split())
    return {
        "dtbo_active": all(
            marker in agents
            for marker in (
                DTBO_POLICY_MARKER,
                DTBO_ACTIVE_SENTINEL,
                HELPER_PATH,
                DTBO_ACK_TOKEN,
                RESTORE_ACK_TOKEN,
                design.PINS[design.CANDIDATE_AP],
                design.PINS[design.ROLLBACK_AP],
            )
        ),
        "panic_active": all(
            marker in agents
            for marker in (
                PANIC_POLICY_MARKER,
                PANIC_ACTIVE_SENTINEL,
                HELPER_PATH,
                PANIC_ACK_TOKEN,
                design.CONTRACT_SHA256,
                "sysrq-trigger-c",
            )
        ),
    }


def require_active_policies(root: Path, *, panic: bool) -> None:
    status = policy_status(root)
    if not status["dtbo_active"]:
        raise GateError("V3437 DTBO maintenance policy is inactive")
    if panic and not status["panic_active"]:
        raise GateError("V3437 intentional-panic policy is inactive")


def verify_acks(args: argparse.Namespace, *, panic: bool, restore: bool = False) -> None:
    if args.dtbo_ack != DTBO_ACK_TOKEN:
        raise GateError(f"DTBO action requires --dtbo-ack {DTBO_ACK_TOKEN}")
    if panic and args.panic_ack != PANIC_ACK_TOKEN:
        raise GateError(f"panic action requires --panic-ack {PANIC_ACK_TOKEN}")
    if restore and args.restore_ack != RESTORE_ACK_TOKEN:
        raise GateError(f"restore action requires --restore-ack {RESTORE_ACK_TOKEN}")


def root_bytes(serial: str, command: str, timeout: float = 30.0) -> bytes:
    result = adb_exec_out(command, serial=serial, timeout=timeout)
    if result.returncode != 0:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise GateError(f"root command failed rc={result.returncode}: {output}")
    return result.stdout


def current_partition_hash(serial: str, partition: str) -> str:
    payload = root_bytes(
        serial,
        f"dd if=/dev/block/by-name/{shlex.quote(partition)} bs=4096 2>/dev/null | sha256sum",
        timeout=60.0,
    ).decode("ascii", errors="replace")
    words = payload.split()
    if not words or not re.fullmatch(r"[0-9a-f]{64}", words[0]):
        raise GateError(f"could not parse {partition} partition hash")
    return words[0]


def live_dt_hex(serial: str, name: str) -> str:
    path = f"/proc/device-tree/reserved-memory/ramoops_region/{name}"
    payload = root_bytes(
        serial,
        f"od -An -tx1 {shlex.quote(path)} 2>/dev/null | tr -d ' \\n'",
    )
    return payload.decode("ascii", errors="replace").strip().lower()


def verify_stock_baseline(serial: str, log_path: Path, stability_samples: int) -> None:
    verify_android_stability(log_path, serial, stability_samples, 3.0)
    boot_hash = current_partition_hash(serial, "boot")
    dtbo_hash = current_partition_hash(serial, "dtbo")
    status = bytes.fromhex(live_dt_hex(serial, "status")).rstrip(b"\0").decode("ascii")
    durable_append(log_path, f"stock_boot_sha256={boot_hash}")
    durable_append(log_path, f"stock_dtbo_sha256={dtbo_hash}")
    durable_append(log_path, f"stock_ramoops_status={status}")
    if boot_hash != design.EXPECTED_MAGISK_BOOT_RAW_SHA256:
        raise GateError("Magisk boot baseline mismatch")
    if dtbo_hash != design.PINS[design.STOCK_RAW]:
        raise GateError("stock DTBO baseline mismatch")
    if status != "disabled":
        raise GateError("stock ramoops status is not disabled")


def verify_patched_backend(serial: str, log_path: Path) -> dict[str, Any]:
    dtbo_hash = current_partition_hash(serial, "dtbo")
    expected_hex = {
        "status": "6f6b617900",
        "size": "0000000000200000",
        "pmsg-size": "00100000",
        "console-size": "00080000",
        "record-size": "00040000",
    }
    live = {name: live_dt_hex(serial, name) for name in expected_hex}
    parameters_text = root_bytes(
        serial,
        "for n in mem_size pmsg_size console_size record_size; do "
        "p=/sys/module/ramoops/parameters/$n; "
        "printf '%s=' \"$n\"; [ -r \"$p\" ] && cat \"$p\" || echo __MISSING__; done",
    ).decode("utf-8", errors="replace")
    parameters = dict(
        line.split("=", 1) for line in parameters_text.splitlines() if "=" in line
    )
    expected_parameters = {
        "mem_size": str(design.REGION_SIZE),
        "pmsg_size": str(design.PMSG_SIZE),
        "console_size": str(design.CONSOLE_SIZE),
        "record_size": str(design.RECORD_SIZE),
    }
    backend_text = root_bytes(
        serial,
        "printf 'pstore_mount='; grep -c ' /sys/fs/pstore pstore ' /proc/mounts || true; "
        "printf 'pmsg0='; [ -c /dev/pmsg0 ] && echo 1 || echo 0; "
        "dmesg | grep -E 'Registered ramoops as persistent store backend|ramoops: using' | tail -10",
    ).decode("utf-8", errors="replace")
    durable_append(log_path, f"candidate_dtbo_sha256={dtbo_hash}")
    durable_append(log_path, f"candidate_live_dt={json.dumps(live, sort_keys=True)}")
    durable_append(log_path, f"candidate_ramoops_parameters={json.dumps(parameters, sort_keys=True)}")
    durable_append(log_path, f"candidate_backend_text={backend_text}")
    if dtbo_hash != design.PINS[design.CANDIDATE_RAW]:
        raise GateError("candidate DTBO readback mismatch")
    if live != expected_hex:
        raise GateError(f"candidate live DT properties mismatch: {live}")
    if parameters != expected_parameters:
        raise GateError(f"ramoops module parameters mismatch: {parameters}")
    if "pstore_mount=1" not in backend_text or "pmsg0=1" not in backend_text:
        raise GateError("pstore mount or pmsg0 readiness missing")
    if "Registered ramoops as persistent store backend" not in backend_text:
        raise GateError("ramoops backend registration marker missing")
    return {"live_dt": live, "parameters": parameters, "backend": backend_text}


def remote_pstore_names(serial: str) -> list[str]:
    payload = root_bytes(
        serial,
        "for f in /sys/fs/pstore/*; do [ -f \"$f\" ] && echo \"${f##*/}\"; done",
    ).decode("utf-8", errors="replace")
    names = [line.strip() for line in payload.splitlines() if line.strip()]
    if any(not PSTORE_NAME_RE.fullmatch(name) for name in names):
        raise GateError(f"unsafe pstore filename returned: {names}")
    return sorted(set(names))


def collect_pstore_once(serial: str, output_dir: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for name in remote_pstore_names(serial):
        payload = root_bytes(serial, f"cat /sys/fs/pstore/{shlex.quote(name)}", 45.0)
        durable_write_bytes(output_dir / name, payload)
        result[name] = payload
    return result


def collect_pstore_twice(serial: str, run_dir: Path, attempt: int) -> dict[str, bytes]:
    first = collect_pstore_once(serial, run_dir / "evidence" / f"attempt-{attempt}" / "read-1")
    second = collect_pstore_once(serial, run_dir / "evidence" / f"attempt-{attempt}" / "read-2")
    if set(first) != set(second):
        raise GateError("pstore filename set changed between duplicate reads")
    for name in first:
        if first[name] != second[name]:
            raise GateError(f"pstore file changed between duplicate reads: {name}")
    summary = {
        name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in first.items()
    }
    durable_write_json(run_dir / "evidence" / f"attempt-{attempt}" / "summary.json", summary)
    return first


def assert_run_absent(run_id: str, payloads: dict[str, bytes]) -> None:
    token = run_id.encode("ascii")
    hits = [name for name, payload in payloads.items() if token in payload]
    if hits:
        raise GateError(f"fresh run ID already present in baseline: {hits}")


def direct_adb_su(serial: str, script: str, timeout: float) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["adb", "-s", serial, "exec-out", "su", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def arm_markers(serial: str, run_id: str, log_path: Path) -> None:
    kmsg = "<0>" + design.encode_marker(run_id, "PREPANIC_KMSG").decode("ascii")
    pmsg = design.encode_marker(run_id, "PREPANIC_PMSG").decode("ascii")
    script = "\n".join(
        [
            "set -eu",
            "printf '1\\n' > /proc/sys/kernel/sysrq",
            f"printf '%s\\n' {shlex.quote(kmsg)} > /dev/kmsg",
            f"printf '%s\\n' {shlex.quote(pmsg)} > /dev/pmsg0",
            f"dmesg | tail -400 | grep -F {shlex.quote(run_id)} >/dev/null",
        ]
    )
    result = direct_adb_su(serial, script, 20.0)
    durable_append(log_path, f"arm_markers_rc={result.returncode}")
    if result.returncode != 0:
        raise GateError(
            "marker arm failed: "
            + (result.stdout + result.stderr).decode("utf-8", errors="replace")
        )


def trigger_panic_once(serial: str, run_id: str, log_path: Path) -> None:
    marker = "<0>" + design.encode_marker(run_id, "TRIGGER_KMSG").decode("ascii")
    script = "\n".join(
        [
            "set -eu",
            f"printf '%s\\n' {shlex.quote(marker)} > /dev/kmsg",
            "sync",
            "printf 'c\\n' > /proc/sysrq-trigger",
            "exit 99",
        ]
    )
    try:
        result = direct_adb_su(serial, script, 20.0)
    except subprocess.TimeoutExpired:
        durable_append(log_path, "panic_command_timeout_after_trigger=1")
        return
    durable_append(log_path, f"panic_command_rc={result.returncode}")
    durable_append(
        log_path,
        (result.stdout + result.stderr).decode("utf-8", errors="replace"),
    )
    if result.returncode == 99:
        raise GateError("sysrq panic trigger returned without crashing")


def wait_for_transport_loss(serial: str, log_path: Path, seconds: int = 30) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rows = adb_rows(log_path, "panic-transport-loss", serial)
        if not any(row[0] == serial and row[1] == "device" for row in rows):
            return
        time.sleep(1.0)
    raise GateError("ADB transport did not disappear after panic trigger")


def wait_for_early_root(serial: str, log_path: Path, seconds: int) -> str | None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rows = adb_rows(log_path, "patched-android-early-root", serial)
        if any(row[0] == serial and row[1] == "device" for row in rows):
            result = adb_shell("su -c id", serial=serial, timeout=15.0)
            if result.returncode == 0 and "uid=0(root)" in result.stdout + result.stderr:
                return serial
        time.sleep(2.0)
    return None


def flash_selected_ap(
    odin: Path,
    ap: Path,
    log_path: Path,
    label: str,
    wait_seconds: int,
) -> int:
    device = wait_for_odin(odin, log_path, f"{label}-wait", wait_seconds)
    if device is None:
        raise GateError(f"{label} requires exactly one Odin device")
    return flash_ap(odin, ap, device, log_path, label)


def rollback_from_android(
    root: Path,
    serial: str,
    odin: Path,
    run_dir: Path,
    log_path: Path,
    session: Session,
    timeline: Timeline,
    wait_seconds: int,
) -> None:
    session.advance("ROLLBACK_TRANSFER")
    reboot_android_to_download(serial, log_path, "v3437-stock-dtbo-rollback")
    timeline.append("rollback_flash_start")
    rc = flash_selected_ap(
        odin, resolve(root, design.ROLLBACK_AP), log_path, "v3437-stock-dtbo-rollback", wait_seconds
    )
    if rc != 0:
        raise GateError(f"stock DTBO rollback transfer failed rc={rc}")
    timeline.append("rollback_flash_done")
    session.advance("ROLLBACK_BOOT_WAIT")
    android = wait_for_android_root(log_path, wait_seconds, serial)
    if android is None:
        raise GateError("Android/root did not return after stock DTBO rollback")
    verify_stock_baseline(android, log_path, 4)
    timeline.append("rollback_boot_ready")
    session.advance("STOCK_RESTORED")


def rollback_from_download_transport(
    root: Path,
    serial: str,
    odin: Path,
    log_path: Path,
    session: Session,
    timeline: Timeline,
    wait_seconds: int,
) -> None:
    if session.value["state"] != "ROLLBACK_TRANSFER":
        session.abandon_evidence_for_recovery("FAIL_PREPANIC_GATE_ROLLBACK")
        session.advance("ROLLBACK_TRANSFER")
    timeline.append("rollback_flash_start")
    rc = flash_selected_ap(
        odin,
        resolve(root, design.ROLLBACK_AP),
        log_path,
        "v3437-stock-dtbo-rollback",
        wait_seconds,
    )
    if rc != 0:
        raise GateError(f"stock rollback failed rc={rc}")
    timeline.append("rollback_flash_done")
    session.advance("ROLLBACK_BOOT_WAIT")
    android = wait_for_android_root(log_path, wait_seconds, serial)
    if android is None:
        raise GateError("Android did not return after download rollback")
    verify_stock_baseline(android, log_path, 4)
    timeline.append("rollback_boot_ready")
    session.advance("STOCK_RESTORED")


def attempt_prep_failure_rollback(
    root: Path,
    serial: str,
    odin: Path,
    log_path: Path,
    session: Session,
    timeline: Timeline,
    wait_seconds: int,
    result: str = "FAIL_PREPANIC_GATE_ROLLBACK",
) -> bool:
    durable_append(log_path, "prepanic_failure_rollback_attempted=1")
    rows = adb_rows(log_path, "prepanic-rollback-adb", serial)
    if any(row[0] == serial and row[1] == "device" for row in rows):
        current = current_partition_hash(serial, "dtbo")
        if current == design.PINS[design.STOCK_RAW]:
            durable_append(log_path, "prepanic_failure_already_stock=1")
            return True
        if current != design.PINS[design.CANDIDATE_RAW]:
            raise GateError(
                f"prepanic rollback refuses unexpected DTBO hash {current}"
            )
        session.abandon_evidence_for_recovery(result)
        rollback_from_android(
            root,
            serial,
            odin,
            session.path.parent,
            log_path,
            session,
            timeline,
            wait_seconds,
        )
        if "live_session_end" not in [event["name"] for event in timeline.events]:
            timeline.append("live_session_end")
        session.advance("CLASSIFIED")
        return True

    devices = odin_devices(odin, log_path, "prepanic-rollback-odin")
    if len(devices) == 1:
        session.abandon_evidence_for_recovery(result)
        session.advance("ROLLBACK_TRANSFER")
        rollback_from_download_transport(
            root, serial, odin, log_path, session, timeline, wait_seconds
        )
        if "live_session_end" not in [event["name"] for event in timeline.events]:
            timeline.append("live_session_end")
        session.advance("CLASSIFIED")
        return True
    if len(devices) > 1:
        raise GateError(f"prepanic rollback found ambiguous Odin devices: {devices}")
    durable_append(log_path, "prepanic_failure_rollback_transport_missing=1")
    return False


def collect_classify_and_rollback(
    root: Path,
    serial: str,
    odin: Path,
    run_dir: Path,
    log_path: Path,
    session: Session,
    timeline: Timeline,
    wait_seconds: int,
) -> int:
    verify_patched_backend(serial, log_path)
    timeline.append("evidence_collect_start")
    retained: dict[str, bytes] | None = None
    errors: list[str] = []
    for attempt in (1, 2):
        try:
            retained = collect_pstore_twice(serial, run_dir, attempt)
            break
        except GateError as error:
            errors.append(str(error))
            durable_append(log_path, f"evidence_attempt_{attempt}_error={error}")
    if retained is None:
        raise GateError(f"pstore collection failed twice: {errors}")
    timeline.append("evidence_collect_done")
    session.advance("EVIDENCE_COLLECTED")
    baseline_dir = run_dir / "baseline"
    baseline: dict[str, bytes] = {}
    if baseline_dir.is_dir():
        baseline = {
            path.name: path.read_bytes() for path in baseline_dir.iterdir() if path.is_file()
        }
    classification = design.classify_retained(session.value["run_id"], baseline, retained)
    durable_write_json(run_dir / "classification.json", classification)
    session.set("classification", classification)
    rollback_from_android(
        root, serial, odin, run_dir, log_path, session, timeline, wait_seconds
    )
    timeline.append("live_session_end")
    session.advance("CLASSIFIED")
    result = classification["result"]
    return RESULT_CODES.get(result, 40)


def run_live_session(
    args: argparse.Namespace,
    root: Path,
    odin: Path,
) -> int:
    run_dir = allocate_run_dir(root, args.run_dir)
    log_path = run_dir / "v3437_live_gate.log"
    serial = require_current_android(log_path, args.serial)
    session = Session.create(run_dir, serial)
    timeline = Timeline.create(run_dir / "timeline.json")
    timeline.append("live_session_start")
    verify_stock_baseline(serial, log_path, args.stability_samples)
    baseline = collect_pstore_once(serial, run_dir / "baseline")
    dmesg = root_bytes(serial, "dmesg | tail -2000", 30.0)
    durable_write_bytes(run_dir / "baseline" / "current-dmesg.txt", dmesg)
    baseline["current-dmesg.txt"] = dmesg
    assert_run_absent(session.value["run_id"], baseline)

    candidate_started = False
    try:
        session.advance("CANDIDATE_TRANSFER")
        reboot_android_to_download(serial, log_path, "v3437-candidate-dtbo")
        timeline.append("candidate_flash_start")
        candidate_started = True
        rc = flash_selected_ap(
            odin,
            resolve(root, design.CANDIDATE_AP),
            log_path,
            "v3437-candidate-dtbo",
            args.wait_seconds,
        )
        if rc != 0:
            raise GateError(f"candidate DTBO transfer failed rc={rc}")
        timeline.append("candidate_flash_done")
        session.advance("PATCHED_BOOT_WAIT")
        patched = wait_for_android_root(log_path, args.wait_seconds, serial)
        if patched is None:
            raise GateError("patched Android/root did not return")
        timeline.append("candidate_boot_ready")
        session.advance("PATCHED_PREFLIGHT")
        verify_patched_backend(patched, log_path)
        timeline.append("backend_proven")
        session.advance("BACKEND_PROVEN")
        patched_baseline = collect_pstore_once(
            patched, run_dir / "patched-baseline"
        )
        patched_ring = root_bytes(patched, "dmesg | tail -2000", 30.0)
        patched_baseline["current-dmesg.txt"] = patched_ring
        assert_run_absent(session.value["run_id"], patched_baseline)

        arm_markers(patched, session.value["run_id"], log_path)
        timeline.append("markers_written")
        session.advance("MARKERS_WRITTEN")
        timeline.append("panic_trigger_start")
        session.set("panic_attempted", True)
        trigger_panic_once(patched, session.value["run_id"], log_path)
    except BaseException:
        if candidate_started and session.value["state"] in (
            "CANDIDATE_TRANSFER",
            "PATCHED_BOOT_WAIT",
            "PATCHED_PREFLIGHT",
            "BACKEND_PROVEN",
            "MARKERS_WRITTEN",
        ):
            attempt_prep_failure_rollback(
                root,
                serial,
                odin,
                log_path,
                session,
                timeline,
                args.wait_seconds,
            )
        raise
    session.advance("PANIC_TRIGGERED")
    try:
        wait_for_transport_loss(patched, log_path)
    except GateError:
        attempt_prep_failure_rollback(
            root,
            serial,
            odin,
            log_path,
            session,
            timeline,
            args.wait_seconds,
            "FAIL_PANIC_TRANSPORT_NOT_LOST",
        )
        raise
    timeline.append("panic_transport_lost")
    session.advance("RECOVERY_WAIT")
    recovered = wait_for_early_root(patched, log_path, args.wait_seconds)
    if recovered is None:
        durable_append(log_path, "manual_recovery_required=1")
        print(
            f"manual recovery to patched Android required; resume with --run-dir {run_dir}",
            file=sys.stderr,
        )
        return 31
    timeline.append("patched_recovery_boot_ready")
    session.advance("PATCHED_ANDROID_RETURNED")
    return collect_classify_and_rollback(
        root, recovered, odin, run_dir, log_path, session, timeline, args.wait_seconds
    )


def load_resume(run_dir: Path) -> tuple[Session, Timeline, Path]:
    session = Session.load(run_dir / "session.json")
    timeline = Timeline.load(run_dir / "timeline.json")
    return session, timeline, run_dir / "v3437_live_gate.log"


def print_plan() -> None:
    print("V3437 ramoops positive-control plan (policy-gated)")
    print("1. offline-check artifacts, contracts, policy drafts")
    print("2. activate separate DTBO and panic AGENTS exceptions")
    print("3. dry-run stock Android/Magisk/DTBO baseline")
    print("4. live-session: candidate -> backend proof -> markers -> one panic")
    print("5. patched Android recovery -> evidence -> stock rollback")
    print("6. resume after manual recovery when automatic Android return fails")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--print-plan", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--live-session", action="store_true")
    modes.add_argument("--resume-after-manual-recovery", action="store_true")
    modes.add_argument("--restore-from-android", action="store_true")
    modes.add_argument("--restore-from-download", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--wait-seconds", type=int, default=300)
    parser.add_argument("--stability-samples", type=int, default=4)
    parser.add_argument("--dtbo-ack")
    parser.add_argument("--panic-ack")
    parser.add_argument("--restore-ack")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = repo_root()
    verify_artifacts(root)
    verify_policy_drafts(root)
    if args.offline_check:
        status = policy_status(root)
        print(
            "offline-check ok: artifacts, contracts, and inert policy drafts verified; "
            f"policy_status={json.dumps(status, sort_keys=True)}; device_action=0"
        )
        return 0
    if args.print_plan:
        print_plan()
        return 0

    panic_required = (
        args.dry_run or args.live_session or args.resume_after_manual_recovery
    )
    require_active_policies(root, panic=panic_required)
    if args.live_session:
        verify_acks(args, panic=True)
    elif args.resume_after_manual_recovery:
        verify_acks(args, panic=True, restore=True)
    elif args.restore_from_android or args.restore_from_download:
        verify_acks(args, panic=False, restore=True)
    else:
        verify_acks(args, panic=False)

    odin = resolve(root, args.odin)
    if not odin.is_file():
        raise GateError(f"odin4 missing: {odin}")

    if args.dry_run:
        run_dir = allocate_run_dir(root, args.run_dir)
        log_path = run_dir / "v3437_dry_run.log"
        serial = require_current_android(log_path, args.serial)
        verify_stock_baseline(serial, log_path, args.stability_samples)
        print(f"dry-run ok: active policies and stock baseline verified; {run_dir}")
        return 0
    if args.live_session:
        return run_live_session(args, root, odin)

    if args.run_dir is None:
        raise GateError("resume/restore mode requires --run-dir")
    run_dir = resolve(root, args.run_dir)
    session, timeline, log_path = load_resume(run_dir)
    serial = args.serial or str(session.value["serial"])
    if args.resume_after_manual_recovery:
        if session.value["state"] != "RECOVERY_WAIT":
            raise GateError("resume requires RECOVERY_WAIT state")
        recovered = wait_for_early_root(serial, log_path, args.wait_seconds)
        if recovered is None:
            raise GateError("patched Android/root is still unavailable")
        verify_patched_backend(recovered, log_path)
        timeline.append("patched_recovery_boot_ready")
        session.advance("PATCHED_ANDROID_RETURNED")
        return collect_classify_and_rollback(
            root, recovered, odin, run_dir, log_path, session, timeline, args.wait_seconds
        )

    if args.restore_from_android:
        android = require_current_android(log_path, serial)
        current = current_partition_hash(android, "dtbo")
        if current == design.PINS[design.STOCK_RAW]:
            print("restore-from-android: DTBO already stock")
            return 0
        if current != design.PINS[design.CANDIDATE_RAW]:
            raise GateError(f"refusing rollback from unexpected DTBO {current}")
        session.abandon_evidence_for_recovery()
        rollback_from_android(
            root, android, odin, run_dir, log_path, session, timeline, args.wait_seconds
        )
        if "live_session_end" not in [event["name"] for event in timeline.events]:
            timeline.append("live_session_end")
        session.advance("CLASSIFIED")
        return RESULT_CODES["NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY"]

    if args.restore_from_download:
        if session.value["state"] not in (
            "CANDIDATE_TRANSFER",
            "PATCHED_BOOT_WAIT",
            "PATCHED_PREFLIGHT",
            "BACKEND_PROVEN",
            "MARKERS_WRITTEN",
            "PANIC_TRIGGERED",
            "RECOVERY_WAIT",
        ):
            raise GateError(f"restore-from-download not valid in {session.value['state']}")
        rollback_from_download_transport(
            root, serial, odin, log_path, session, timeline, args.wait_seconds
        )
        if "live_session_end" not in [event["name"] for event in timeline.events]:
            timeline.append("live_session_end")
        session.advance("CLASSIFIED")
        return RESULT_CODES["NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY"]

    raise GateError("unhandled mode")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except GateError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
