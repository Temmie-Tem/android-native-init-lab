#!/usr/bin/env python3
"""Define the host-only V3436 S22+ ramoops positive-control contract.

This module validates the pinned V3435 DTBO artifacts and defines a resumable,
evidence-first state machine for a future Android sysrq-panic positive control.
It has no device transport, flash, reboot, panic, or live execution path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import tarfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_v3436_ramoops_positive_control_design_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
VERDICT = "HOST_DESIGN_PASS_NO_LIVE"

V3435_CONTRACT = Path(
    "docs/plans/s22plus-v3435-ramoops-console-dtbo-contract.json"
)
CANDIDATE_AP = Path(
    "workspace/private/outputs/s22plus_v3435_ramoops_console_dtbo_v0_1/"
    "candidate_odin4/AP.tar.md5"
)
ROLLBACK_AP = Path(
    "workspace/private/outputs/s22plus_v3435_ramoops_console_dtbo_v0_1/"
    "stock_rollback_odin4/AP.tar.md5"
)
CANDIDATE_RAW = Path(
    "workspace/private/outputs/s22plus_v3435_ramoops_console_dtbo_v0_1/"
    "build/dtbo.img"
)
STOCK_RAW = Path(
    "workspace/private/outputs/s22plus_v3435_ramoops_console_dtbo_v0_1/"
    "build/stock_dtbo.img"
)
OUTPUT = Path("docs/plans/s22plus-v3436-ramoops-positive-control-contract.json")

PINS = {
    V3435_CONTRACT: "ee5761c22f590ec01a398dc75bdb31e87e4c983d34b813d94b1428ca7b4e1680",
    CANDIDATE_AP: "622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264",
    ROLLBACK_AP: "6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa",
    CANDIDATE_RAW: "3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281",
    STOCK_RAW: "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c",
}

EXPECTED_MAGISK_BOOT_RAW_SHA256 = (
    "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
)
EXPECTED_MEMBER = "dtbo.img.lz4"

REGION_SIZE = 0x200000
PMSG_SIZE = 0x100000
CONSOLE_SIZE = 0x80000
RECORD_SIZE = 0x40000
DMESG_SIZE = 0x80000
DMESG_RECORD_COUNT = 2

PROTOCOL = "S22RPC1"
FRAME_START = f"[[{PROTOCOL}|".encode("ascii")
FRAME_END = b"]]"
RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PHASE_SEQUENCE = {
    "PREPANIC_KMSG": 1,
    "PREPANIC_PMSG": 2,
    "TRIGGER_KMSG": 3,
}

REQUIRED_TIMELINE_EVENTS = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "backend_proven",
    "markers_written",
    "panic_trigger_start",
    "panic_transport_lost",
    "patched_recovery_boot_ready",
    "evidence_collect_start",
    "evidence_collect_done",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)

STATE_ORDER = (
    "STOCK_BASELINE",
    "CANDIDATE_TRANSFER",
    "PATCHED_BOOT_WAIT",
    "PATCHED_PREFLIGHT",
    "BACKEND_PROVEN",
    "MARKERS_WRITTEN",
    "PANIC_TRIGGERED",
    "RECOVERY_WAIT",
    "PATCHED_ANDROID_RETURNED",
    "EVIDENCE_COLLECTED",
    "ROLLBACK_TRANSFER",
    "ROLLBACK_BOOT_WAIT",
    "STOCK_RESTORED",
    "CLASSIFIED",
)

ALLOWED_TRANSITIONS = {
    "STOCK_BASELINE": ("CANDIDATE_TRANSFER",),
    "CANDIDATE_TRANSFER": ("PATCHED_BOOT_WAIT", "ROLLBACK_TRANSFER"),
    "PATCHED_BOOT_WAIT": ("PATCHED_PREFLIGHT", "ROLLBACK_TRANSFER"),
    "PATCHED_PREFLIGHT": ("BACKEND_PROVEN", "ROLLBACK_TRANSFER"),
    "BACKEND_PROVEN": ("MARKERS_WRITTEN", "ROLLBACK_TRANSFER"),
    "MARKERS_WRITTEN": ("PANIC_TRIGGERED", "ROLLBACK_TRANSFER"),
    "PANIC_TRIGGERED": ("RECOVERY_WAIT", "ROLLBACK_TRANSFER"),
    "RECOVERY_WAIT": ("PATCHED_ANDROID_RETURNED",),
    "PATCHED_ANDROID_RETURNED": ("EVIDENCE_COLLECTED",),
    "EVIDENCE_COLLECTED": ("ROLLBACK_TRANSFER",),
    "ROLLBACK_TRANSFER": ("ROLLBACK_BOOT_WAIT",),
    "ROLLBACK_BOOT_WAIT": ("STOCK_RESTORED",),
    "STOCK_RESTORED": ("CLASSIFIED",),
    "CLASSIFIED": (),
}


class DesignError(ValueError):
    pass


@dataclass(frozen=True)
class Marker:
    run_id: str
    phase: str
    sequence: int
    dtbo_sha256: str
    contract_sha256: str
    crc32: str
    offset: int = -1


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise DesignError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_pins(root: Path) -> dict[str, str]:
    verified: dict[str, str] = {}
    for relative, expected in PINS.items():
        path = resolve(root, relative)
        if not path.is_file():
            raise DesignError(f"missing pinned input: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise DesignError(f"pin mismatch for {relative}: {actual} != {expected}")
        verified[str(relative)] = actual
    return verified


def tar_members(path: Path) -> list[str]:
    with tarfile.open(path, "r:") as archive:
        return [member.name for member in archive.getmembers()]


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


CONTRACT_CORE: dict[str, Any] = {
    "schema": SCHEMA,
    "target": TARGET,
    "verdict": VERDICT,
    "safety": {
        "host_only": True,
        "device_contact": False,
        "image_build": False,
        "flash": False,
        "panic": False,
        "reboot": False,
        "live_authorized": False,
        "agents_modified": False,
    },
    "objective": {
        "final_state": "native/Debian without Android userspace",
        "purpose": "prove ramoops console/dmesg retention before direct PID1",
        "first_live_target": "known-good Android/Magisk positive control",
    },
    "policy_split": {
        "dtbo_exception": (
            "one candidate DTBO flash plus one stock DTBO rollback, exact SHA pins"
        ),
        "panic_exception": (
            "one marker sequence plus one sysrq-trigger-c intentional panic"
        ),
        "both_required_before_live": True,
        "independent_ack_tokens_required": True,
        "currently_active": False,
    },
    "artifacts": {
        "candidate_ap": str(CANDIDATE_AP),
        "candidate_ap_sha256": PINS[CANDIDATE_AP],
        "candidate_raw_sha256": PINS[CANDIDATE_RAW],
        "rollback_ap": str(ROLLBACK_AP),
        "rollback_ap_sha256": PINS[ROLLBACK_AP],
        "stock_raw_sha256": PINS[STOCK_RAW],
        "expected_member": EXPECTED_MEMBER,
        "magisk_boot_raw_sha256": EXPECTED_MAGISK_BOOT_RAW_SHA256,
    },
    "layout": {
        "region_size": REGION_SIZE,
        "pmsg_size": PMSG_SIZE,
        "console_size": CONSOLE_SIZE,
        "record_size": RECORD_SIZE,
        "dmesg_size": DMESG_SIZE,
        "dmesg_record_count": DMESG_RECORD_COUNT,
    },
    "preflight": {
        "stock_baseline": [
            "single Android ADB target",
            "SM-S906N/g0q/S906NKSS7FYG8 identity",
            "boot_completed=1 and root available",
            f"boot raw SHA256={EXPECTED_MAGISK_BOOT_RAW_SHA256}",
            f"stock DTBO raw SHA256={PINS[STOCK_RAW]}",
            "live ramoops status=disabled",
            "four bounded Android stability samples",
        ],
        "patched_backend": [
            f"candidate DTBO raw SHA256={PINS[CANDIDATE_RAW]}",
            "live status=okay",
            f"live size=0x{REGION_SIZE:x}",
            f"live pmsg-size=0x{PMSG_SIZE:x}",
            f"live console-size=0x{CONSOLE_SIZE:x}",
            f"live record-size=0x{RECORD_SIZE:x}",
            "ramoops module parameters equal live DT sizes",
            "pstore backend registration visible in dmesg/sysfs",
            "/sys/fs/pstore is mounted",
            "/dev/pmsg0 exists",
            "current run ID absent from baseline pstore and current ring",
        ],
    },
    "marker": {
        "protocol": PROTOCOL,
        "run_id_bits": 128,
        "phases": PHASE_SEQUENCE,
        "kmsg_priority": "<0> emergency prefix before the frame",
        "integrity": "CRC32 over canonical ASCII payload",
        "candidate_identity_bound": True,
        "contract_identity_bound": True,
    },
    "state_order": STATE_ORDER,
    "allowed_transitions": ALLOWED_TRANSITIONS,
    "evidence_first_rule": (
        "after panic, patched Android evidence collection must complete before stock DTBO rollback"
    ),
    "recovery": {
        "pre_panic_failure": "restore stock DTBO immediately when a single Odin path exists",
        "post_panic_android_return": (
            "collect every pstore file twice and flush host artifacts before rollback"
        ),
        "post_panic_no_android": (
            "require operator recovery to patched Android; do not auto-rollback over unread evidence"
        ),
        "safety_override": (
            "if patched Android cannot be recovered and exactly one Odin path exists, "
            "operator may choose stock rollback; classify NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY"
        ),
        "collection_retry_limit": 2,
        "rollback_failure": "stop in Download and require operator recovery",
    },
    "timeline": {
        "schema": "events:[{name,timestamp_utc}]",
        "required_order": REQUIRED_TIMELINE_EVENTS,
        "ad_hoc_shapes_forbidden": True,
        "flush_after_every_event": True,
    },
    "classification": {
        "pass": (
            "valid current-run PREPANIC_KMSG or TRIGGER_KMSG frame in "
            "console-ramoops* or dmesg-ramoops* after reset"
        ),
        "partial": "current-run frame only in pmsg-ramoops*; no console/dmesg proof",
        "no_proof": "no valid current-run frame and no malformed/current-run identity conflict",
        "fail": "stale collision, malformed frame, bad CRC, or wrong bound identity",
        "pass_effect": "reopen a minimal module-free direct-PID1 witness",
        "fail_effect": "retire ramoops after a proven backend and move to EUD/UART",
    },
    "next_implementation": {
        "live_helper_created": False,
        "agents_exception_created": False,
        "required_modes": [
            "offline-check",
            "dry-run",
            "live-session",
            "resume-after-manual-recovery",
            "restore-from-android",
            "restore-from-download",
        ],
        "session_is_resumable_from_disk": True,
    },
}

CONTRACT_SHA256 = hashlib.sha256(canonical_json(CONTRACT_CORE)).hexdigest()


def marker_payload(run_id: str, phase: str) -> bytes:
    if not RUN_ID_RE.fullmatch(run_id):
        raise DesignError("run ID must be 128-bit lowercase hex")
    if phase not in PHASE_SEQUENCE:
        raise DesignError(f"unknown marker phase: {phase}")
    return (
        f"run={run_id};phase={phase};seq={PHASE_SEQUENCE[phase]:08x};"
        f"dtbo={PINS[CANDIDATE_RAW]};contract={CONTRACT_SHA256}"
    ).encode("ascii")


def encode_marker(run_id: str, phase: str) -> bytes:
    payload = marker_payload(run_id, phase)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return (
        FRAME_START
        + f"{len(payload):04x}|".encode("ascii")
        + payload
        + f"|crc={crc:08x}".encode("ascii")
        + FRAME_END
    )


def decode_frame(frame: bytes, offset: int = -1) -> Marker:
    if not frame.startswith(FRAME_START) or not frame.endswith(FRAME_END):
        raise DesignError("marker framing mismatch")
    body = frame[len(FRAME_START) : -len(FRAME_END)]
    try:
        length_text, remainder = body.split(b"|", 1)
        payload, crc_text = remainder.rsplit(b"|crc=", 1)
    except ValueError as error:
        raise DesignError("marker fields are incomplete") from error
    if len(length_text) != 4 or not re.fullmatch(rb"[0-9a-f]{4}", length_text):
        raise DesignError("marker length is not four lowercase hex digits")
    if int(length_text, 16) != len(payload):
        raise DesignError("marker payload length mismatch")
    if not re.fullmatch(rb"[0-9a-f]{8}", crc_text):
        raise DesignError("marker CRC is malformed")
    actual_crc = f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}".encode("ascii")
    if crc_text != actual_crc:
        raise DesignError("marker CRC mismatch")

    fields: dict[str, str] = {}
    for item in payload.decode("ascii").split(";"):
        if "=" not in item:
            raise DesignError("marker payload item lacks equals")
        key, value = item.split("=", 1)
        if key in fields:
            raise DesignError("marker payload has duplicate field")
        fields[key] = value
    if set(fields) != {"run", "phase", "seq", "dtbo", "contract"}:
        raise DesignError("marker payload field set mismatch")
    if not RUN_ID_RE.fullmatch(fields["run"]):
        raise DesignError("marker run ID malformed")
    if fields["phase"] not in PHASE_SEQUENCE:
        raise DesignError("marker phase malformed")
    if not re.fullmatch(r"[0-9a-f]{8}", fields["seq"]):
        raise DesignError("marker sequence malformed")
    sequence = int(fields["seq"], 16)
    if sequence != PHASE_SEQUENCE[fields["phase"]]:
        raise DesignError("marker phase/sequence mismatch")
    if not SHA256_RE.fullmatch(fields["dtbo"]) or not SHA256_RE.fullmatch(
        fields["contract"]
    ):
        raise DesignError("marker identity malformed")
    return Marker(
        run_id=fields["run"],
        phase=fields["phase"],
        sequence=sequence,
        dtbo_sha256=fields["dtbo"],
        contract_sha256=fields["contract"],
        crc32=crc_text.decode("ascii"),
        offset=offset,
    )


def scan_markers(payload: bytes) -> tuple[list[Marker], list[str]]:
    markers: list[Marker] = []
    errors: list[str] = []
    position = 0
    while True:
        start = payload.find(FRAME_START, position)
        if start < 0:
            break
        end = payload.find(FRAME_END, start + len(FRAME_START))
        if end < 0:
            errors.append(f"truncated frame at offset {start}")
            break
        frame = payload[start : end + len(FRAME_END)]
        try:
            markers.append(decode_frame(frame, start))
        except DesignError as error:
            errors.append(f"offset {start}: {error}")
        position = end + len(FRAME_END)
    return markers, errors


def classify_retained(
    run_id: str,
    baseline_payloads: dict[str, bytes],
    retained_payloads: dict[str, bytes],
) -> dict[str, Any]:
    if not RUN_ID_RE.fullmatch(run_id):
        raise DesignError("run ID must be 128-bit lowercase hex")
    token = run_id.encode("ascii")
    baseline_hits = [name for name, payload in baseline_payloads.items() if token in payload]
    if baseline_hits:
        return {
            "result": "FAIL_STALE_OR_COLLISION",
            "baseline_hits": baseline_hits,
            "valid_frames": [],
            "errors": [],
        }

    valid: list[tuple[str, Marker]] = []
    errors: list[str] = []
    raw_token_files: list[str] = []
    for name, payload in retained_payloads.items():
        markers, scan_errors = scan_markers(payload)
        errors.extend(f"{name}: {error}" for error in scan_errors if run_id in error or token in payload)
        if token in payload:
            raw_token_files.append(name)
        for marker in markers:
            if marker.run_id != run_id:
                continue
            if (
                marker.dtbo_sha256 != PINS[CANDIDATE_RAW]
                or marker.contract_sha256 != CONTRACT_SHA256
            ):
                errors.append(f"{name}: current-run bound identity mismatch")
                continue
            valid.append((name, marker))
    if errors:
        return {
            "result": "FAIL_MALFORMED_OR_IDENTITY",
            "baseline_hits": [],
            "valid_frames": [asdict(marker) | {"file": name} for name, marker in valid],
            "errors": errors,
        }

    console_dmesg = [
        (name, marker)
        for name, marker in valid
        if name.lower().startswith(("console-ramoops", "dmesg-ramoops"))
        and marker.phase in ("PREPANIC_KMSG", "TRIGGER_KMSG")
    ]
    if console_dmesg:
        result = "PASS_RAMOOPS_CONSOLE_DMESG_RETENTION"
    elif any(
        name.lower().startswith("pmsg-ramoops")
        and marker.phase == "PREPANIC_PMSG"
        for name, marker in valid
    ):
        result = "PARTIAL_PMSG_ONLY_NO_CONSOLE_DMESG_PROOF"
    elif raw_token_files:
        result = "FAIL_RAW_TOKEN_WITHOUT_VALID_FRAME"
    else:
        result = "NO_PROOF_NO_CURRENT_RUN_FRAME"
    return {
        "result": result,
        "baseline_hits": [],
        "valid_frames": [asdict(marker) | {"file": name} for name, marker in valid],
        "errors": [],
        "raw_token_files": raw_token_files,
    }


def validate_transition_path(path: list[str]) -> None:
    if not path or path[0] != "STOCK_BASELINE" or path[-1] != "CLASSIFIED":
        raise DesignError("state path must run from STOCK_BASELINE to CLASSIFIED")
    for before, after in zip(path, path[1:]):
        if after not in ALLOWED_TRANSITIONS.get(before, ()):
            raise DesignError(f"forbidden state transition: {before} -> {after}")


def validate_v3435_contract(root: Path) -> dict[str, Any]:
    contract = json.loads(resolve(root, V3435_CONTRACT).read_text(encoding="utf-8"))
    if contract.get("verdict") != "HOST_BUILD_PASS_NO_LIVE":
        raise DesignError("V3435 contract verdict drift")
    if contract.get("candidate", {}).get("raw_sha256") != PINS[CANDIDATE_RAW]:
        raise DesignError("V3435 candidate raw identity drift")
    layout = contract.get("candidate_layout", {})
    expected = {
        "region_size": REGION_SIZE,
        "pmsg_size": PMSG_SIZE,
        "console_size": CONSOLE_SIZE,
        "record_size": RECORD_SIZE,
        "dmesg_size": DMESG_SIZE,
        "dmesg_record_count": DMESG_RECORD_COUNT,
    }
    for key, value in expected.items():
        if layout.get(key) != value:
            raise DesignError(f"V3435 layout drift for {key}: {layout.get(key)}")
    if contract.get("safety", {}).get("live_authorized") is not False:
        raise DesignError("V3435 unexpectedly authorizes live work")
    return {"path": str(V3435_CONTRACT), "sha256": PINS[V3435_CONTRACT]}


def build_contract(root: Path) -> dict[str, Any]:
    verified = verify_pins(root)
    if tar_members(resolve(root, CANDIDATE_AP)) != [EXPECTED_MEMBER]:
        raise DesignError("candidate AP is not DTBO-only")
    if tar_members(resolve(root, ROLLBACK_AP)) != [EXPECTED_MEMBER]:
        raise DesignError("rollback AP is not DTBO-only")
    predecessor = validate_v3435_contract(root)
    full_path = list(STATE_ORDER)
    validate_transition_path(full_path)
    return {
        **CONTRACT_CORE,
        "contract_sha256": CONTRACT_SHA256,
        "pins": verified,
        "predecessor": predecessor,
        "marker_examples": {
            phase: encode_marker("0123456789abcdef0123456789abcdef", phase).decode(
                "ascii"
            )
            for phase in PHASE_SEQUENCE
        },
        "full_path_validated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    root = repo_root()
    contract = build_contract(root)
    rendered = json.dumps(contract, indent=2, sort_keys=True) + "\n"
    if args.write:
        output = resolve(root, args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(output.relative_to(root))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
