#!/usr/bin/env python3
"""Qualify the retained FYG8 R4W1-A stream-oracle evidence host-only.

This validator does not contact a device and does not create a live promotion
record.  It independently reopens the consumed zero-flash oracle run, verifies
its pinned raw evidence, and reruns the marker parser against the exact streamed
ZIP.  A PASS only qualifies the baseline observer for a separately reviewed
candidate policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_fyg8_r4w1a_marker_oracle as oracle


SCHEMA = "s22plus_fyg8_r4w1a_stream_oracle_qualification_v1"
VERDICT = "PASS_R4W1A_STREAM_ORACLE_EVIDENCE_QUALIFIED_HOST_ONLY"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
ROOT = Path(__file__).resolve().parents[5]

RUN_RELATIVE = Path(
    "workspace/private/runs/"
    "s22plus_fyg8_r4w1a_oracle_dry_run_20260713T095754Z"
)
CONSUMED_RELATIVE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_consumed.json"
)
ORACLE_PASS_RELATIVE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_pass.json"
)
CANDIDATE_CONSUMED_RELATIVE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1a_live_exception_consumed.json"
)
HISTORICAL_HELPER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_live_gate.py"
)
HISTORICAL_TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1a_live_gate.py")
PARSER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_marker_oracle.py"
)
AGENTS_RELATIVE = Path("AGENTS.md")

HISTORICAL_HELPER_SIZE = 61_238
HISTORICAL_HELPER_SHA256 = (
    "d541397c823b7c6311dbec950dd3a82dc6a5881984b45838c99ffedebc2d3d14"
)
HISTORICAL_TEST_SIZE = 27_278
HISTORICAL_TEST_SHA256 = (
    "314b3efc9fec555b31bf6b926bcdbe4b34ebe75ad17bf1172d0e3027e52bf145"
)
PARSER_SIZE = 27_543
PARSER_SHA256 = "bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462"
RETIRED_SENTINEL = "S22PLUS_FYG8_R4W1A_ORACLE_DRY_POLICY_STATE=RETIRED"
ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1A_ORACLE_DRY_POLICY_STATE=ACTIVE"
CANDIDATE_ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1A_POLICY_STATE=ACTIVE"

PINNED_RUN_FILES = {
    "baseline_ap_klog.bin": (
        2_097_136,
        "87d4cad2c3fe385cb114d9f58de9d3962b01633a9fc8af510e8fd50b74cbd949",
    ),
    "baseline_last_kmsg.bin": (
        2_097_136,
        "9a58a0c8486723c31f9cf8ac7d8b8be2586969bb8f167cd76907e3b82db0c7cb",
    ),
    "bugreport.stderr": (
        0,
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ),
    "bugreport.zip": (
        14_461_892,
        "0935e3215ea39c5c9113f71a1de71e7a63de60f947878527a9926ba86aa071b1",
    ),
    "bugreports_after.json": (
        3,
        "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    ),
    "bugreports_before.json": (
        3,
        "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    ),
    "connected.log": (
        65,
        "e5420e5bbdae5396bfe8c259c8018409f1dd22d4e85c75b0686d6c99105ca35b",
    ),
    "connected_preflight.json": (
        1_733,
        "f871e14e0fa831550c2b1f66da5027ad2b8a9bfd553820be5daf70d9da937b97",
    ),
    "forensic_parser.json": (
        1_159,
        "ff5a229a0c1ebb93b71bf8ec589a80b15488773bcd7bf9b3b01ec23c40d28a1f",
    ),
    "oracle.log": (
        68,
        "a9eebcdf5192d4db763583d17f88ce6d6b230f4d4339bc5fc22ad1bf639fa5a6",
    ),
    "oracle_capture.json": (
        766,
        "cbf3ec64874686cb35a404264e6d557c8fa16b1214d0d30a5d1802c765008778",
    ),
    "result.json": (
        5_524,
        "3d0e470d457241808dbcf5b24ba9bde37710905a7feb20943f21605230fe2af4",
    ),
    "timeline.json": (
        846,
        "a8e575090827a72d7732e34cc568f06229e5205ac2d3bb55481973f0959dd581",
    ),
}
CONSUMED_SIZE = 366
CONSUMED_SHA256 = (
    "61b613c87ebadcd1694d6c61f1b3569a7506902f3b257bc9965e25a1ef02da77"
)

TIMELINE_NAMES = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
TIMELINE_SEMANTICS = {
    "candidate_flash_start": "zero-flash-one-bugreport-capture-start",
    "candidate_flash_done": "zero-flash-one-bugreport-capture-finished",
    "candidate_boot_ready": "baseline-android-revalidated",
    "rollback_flash_start": "zero-flash-no-rollback-required",
    "rollback_flash_done": "zero-flash-no-rollback-required",
    "rollback_boot_ready": "baseline-android-revalidated",
}
EXPECTED_ANDROID = {
    "boot_completed": "1",
    "boot_sha256": "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e",
    "bootanim": "stopped",
    "bootloader": "S906NKSS7FYG8",
    "device": "g0q",
    "dtbo_sha256": "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c",
    "incremental": "S906NKSS7FYG8",
    "model": "SM-S906N",
    "recovery_sha256": "93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4",
    "root": "uid=0(root)",
    "verified_boot_state": "orange",
}


class QualificationError(ValueError):
    pass


def read_pinned_file(
    path: Path, size: int, sha256: str
) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink():
        raise QualificationError(f"symlink evidence refused: {path}")
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise QualificationError(f"evidence missing: {path}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise QualificationError(f"evidence is not a regular file: {path}")
    if info.st_size != size:
        raise QualificationError(f"evidence size mismatch for {path}: {info.st_size} != {size}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read()
        actual = hashlib.sha256(data).hexdigest()
        closed = os.fstat(stream.fileno())
    identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
    final_identity = (closed.st_dev, closed.st_ino, closed.st_size, closed.st_mtime_ns)
    if identity != final_identity:
        raise QualificationError(f"evidence changed while hashing: {path}")
    if actual != sha256:
        raise QualificationError(f"evidence SHA256 mismatch for {path}: {actual} != {sha256}")
    return {"path": str(path.resolve()), "size": size, "sha256": actual}, data


def load_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"invalid JSON evidence: {label}") from exc


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise QualificationError(f"timestamp is not canonical UTC: {value!r}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise QualificationError(f"invalid UTC timestamp: {value!r}") from exc
    if parsed.tzinfo != timezone.utc:
        raise QualificationError(f"timestamp is not UTC: {value!r}")
    return parsed


def validate_timeline(payload: Any) -> tuple[list[datetime], dict[str, str]]:
    if not isinstance(payload, dict) or set(payload) != {"events"}:
        raise QualificationError("timeline must contain only events")
    events = payload["events"]
    if not isinstance(events, list) or len(events) != len(TIMELINE_NAMES):
        raise QualificationError("timeline event count mismatch")
    if [event.get("name") for event in events if isinstance(event, dict)] != list(
        TIMELINE_NAMES
    ):
        raise QualificationError("timeline event order mismatch")
    timestamps: list[datetime] = []
    encoded: dict[str, str] = {}
    for expected, event in zip(TIMELINE_NAMES, events, strict=True):
        if not isinstance(event, dict) or set(event) != {"name", "timestamp_utc"}:
            raise QualificationError("timeline event shape mismatch")
        timestamp = parse_utc(event["timestamp_utc"])
        timestamps.append(timestamp)
        encoded[expected] = event["timestamp_utc"]
    if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
        raise QualificationError("timeline timestamps are not strictly increasing")
    return timestamps, encoded


def validate_marker_absence(data: bytes, label: str) -> dict[str, int]:
    tokens = {
        "family_prefix": oracle.MARKER_FAMILY_PREFIX,
        "marker_id": b"9ed5923b08c5eedbbdb0aaa6f6a5200c",
        "phase": b"RAMDISK_EXEC_ACCEPTED",
        "pid_path": b"pid=1|path=/init",
    }
    counts = {name: data.count(token) for name, token in tokens.items()}
    if any(counts.values()) or oracle.EXPECTED_MARKER in data:
        raise QualificationError(f"R4W1 marker evidence present in {label}: {counts}")
    return counts


def validate_android(value: Any, label: str) -> None:
    if value != EXPECTED_ANDROID:
        raise QualificationError(f"{label} Android identity mismatch")


def validate_capture(capture: Any) -> None:
    if not isinstance(capture, dict):
        raise QualificationError("capture is not an object")
    expected_delta = {
        "added": [],
        "changed_preexisting": [],
        "missing_preexisting": [],
        "preexisting_unchanged": True,
    }
    expected_stream = {
        "argv": ["adb", "-s", "<S22_SERIAL_REDACTED>", "exec-out", "bugreportz", "-s"],
        "bytes": PINNED_RUN_FILES["bugreport.zip"][0],
        "read_to_eof": True,
        "returncode": 0,
        "sha256": PINNED_RUN_FILES["bugreport.zip"][1],
        "stderr_bytes": 0,
    }
    checks = (
        capture.get("before") == {},
        capture.get("after") == {},
        capture.get("inventory_delta") == expected_delta,
        capture.get("stream") == expected_stream,
        capture.get("expectation") == "absent",
        capture.get("errors") == ["expected exactly one created bugreport file, got []"],
        capture.get("success") is False,
        capture.get("cleanup_attempted") is False,
        capture.get("cleanup_verified") is False,
        capture.get("remote_created_file") is None,
        capture.get("parser") is None,
        capture.get("parser_stream_identity_match") is False,
    )
    if not all(checks):
        raise QualificationError("consumed capture does not match the exact stream-only failure")


def validate_policy_state(root: Path) -> None:
    agents = (root / AGENTS_RELATIVE).read_text(encoding="utf-8")
    if f"`{RETIRED_SENTINEL}`" not in agents:
        raise QualificationError("binding oracle policy is not RETIRED")
    if f"`{ACTIVE_SENTINEL}`" in agents or f"`{CANDIDATE_ACTIVE_SENTINEL}`" in agents:
        raise QualificationError("a retired oracle or candidate policy is ACTIVE")
    for path in (root / ORACLE_PASS_RELATIVE, root / CANDIDATE_CONSUMED_RELATIVE):
        if path.exists() or path.is_symlink():
            raise QualificationError(f"unexpected promotion or candidate state exists: {path}")


def qualify(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    run = root / RUN_RELATIVE
    inputs: dict[str, dict[str, Any]] = {}
    evidence: dict[str, bytes] = {}
    for name, (size, digest) in PINNED_RUN_FILES.items():
        inputs[name], evidence[name] = read_pinned_file(run / name, size, digest)
    inputs["consumed_state"], evidence["consumed_state"] = read_pinned_file(
        root / CONSUMED_RELATIVE, CONSUMED_SIZE, CONSUMED_SHA256
    )
    inputs["historical_helper"], _ = read_pinned_file(
        root / HISTORICAL_HELPER_RELATIVE,
        HISTORICAL_HELPER_SIZE,
        HISTORICAL_HELPER_SHA256,
    )
    inputs["historical_test"], _ = read_pinned_file(
        root / HISTORICAL_TEST_RELATIVE,
        HISTORICAL_TEST_SIZE,
        HISTORICAL_TEST_SHA256,
    )
    inputs["parser_source"], _ = read_pinned_file(
        root / PARSER_RELATIVE, PARSER_SIZE, PARSER_SHA256
    )

    validate_policy_state(root)
    result = load_json_bytes(evidence["result.json"], "result.json")
    capture = load_json_bytes(evidence["oracle_capture.json"], "oracle_capture.json")
    preflight = load_json_bytes(
        evidence["connected_preflight.json"], "connected_preflight.json"
    )
    before = load_json_bytes(evidence["bugreports_before.json"], "bugreports_before.json")
    after = load_json_bytes(evidence["bugreports_after.json"], "bugreports_after.json")
    persisted_parser = load_json_bytes(
        evidence["forensic_parser.json"], "forensic_parser.json"
    )
    consumed = load_json_bytes(evidence["consumed_state"], "consumed_state")
    timeline = load_json_bytes(evidence["timeline.json"], "timeline.json")

    if before != {} or after != {} or before != capture.get("before") or after != capture.get("after"):
        raise QualificationError("direct /bugreports inventory was not unchanged and empty")
    validate_capture(capture)
    if result.get("capture") != capture:
        raise QualificationError("result capture does not match the separately flushed capture")
    if (
        result.get("schema") != "s22plus_fyg8_r4w1a_live_gate_v1"
        or result.get("mode") != "oracle-dry-run"
        or result.get("target") != TARGET
        or result.get("verdict") != "FAIL_R4W1A_ORACLE_DRY_RUN_CLEANUP_OR_SHAPE"
    ):
        raise QualificationError("consumed live result identity mismatch")
    if (
        result.get("artifacts", {}).get("oracle_source_sha256") != PARSER_SHA256
        or result.get("artifacts", {}).get("live_test_sha256")
        != HISTORICAL_TEST_SHA256
    ):
        raise QualificationError("consumed result source identity mismatch")
    if result.get("timeline_phase_semantics") != TIMELINE_SEMANTICS:
        raise QualificationError("zero-flash timeline semantics mismatch")
    if result.get("pstore_console_absent") != {
        "/sys/fs/pstore/console-ramoops": True,
        "/sys/fs/pstore/console-ramoops-0": True,
    }:
        raise QualificationError("pstore fallback precondition mismatch")

    if preflight != result.get("baseline"):
        raise QualificationError("flushed connected preflight does not match result baseline")
    validate_android(preflight.get("android"), "baseline")
    validate_android(result.get("final"), "final")
    if preflight.get("target") != TARGET or preflight.get("device_writes") is not False:
        raise QualificationError("baseline target or device-write contract mismatch")
    if preflight.get("no_odin_endpoint") is not True or preflight.get("sec_log_buf_live") is not True:
        raise QualificationError("baseline observer or no-Odin gate mismatch")
    if preflight.get("one_shot_consumed") is not False:
        raise QualificationError("baseline unexpectedly started after one-shot consumption")

    raw_observers = {}
    for name, field in (
        ("baseline_ap_klog.bin", "ap_klog"),
        ("baseline_last_kmsg.bin", "last_kmsg"),
    ):
        data = evidence[name]
        raw_observers[field] = validate_marker_absence(data, field)
        metadata = preflight.get(field, {})
        if (
            metadata.get("bytes") != len(data)
            or metadata.get("sha256") != PINNED_RUN_FILES[name][1]
            or metadata.get("read_to_eof") is not True
            or metadata.get("marker", {}).get("classification") != "MARKER_FAMILY_ABSENT"
            or metadata.get("marker", {}).get("pass") is not True
        ):
            raise QualificationError(f"baseline {field} metadata mismatch")

    timestamps, timeline_map = validate_timeline(timeline)
    consumed_at = parse_utc(consumed.get("consumed_at_utc"))
    if not (timestamps[0] < consumed_at < timestamps[1]):
        raise QualificationError("one-shot consumption is outside the pre-capture interval")
    if consumed != {
        "consumed_at_utc": "2026-07-13T09:57:55.901663Z",
        "helper_sha256": HISTORICAL_HELPER_SHA256,
        "reason": "bugreport_capture_start",
        "run_dir": str(RUN_RELATIVE),
        "schema": "s22plus_fyg8_r4w1a_oracle_consumed_v1",
        "target": TARGET,
    }:
        raise QualificationError("one-shot consumed record mismatch")

    if evidence["bugreport.stderr"] != b"":
        raise QualificationError("bugreport stderr is not empty")
    connected_log = evidence["connected.log"].decode("ascii")
    oracle_log = evidence["oracle.log"].decode("ascii")
    if "rc=0 devices=[]" not in connected_log or "rc=0 devices=[]" not in oracle_log:
        raise QualificationError("no-Odin endpoint evidence mismatch")

    reparsed = oracle.parse_bugreport(run / "bugreport.zip", "absent")
    if reparsed != persisted_parser:
        raise QualificationError("fresh parser result does not match retained forensic result")
    if reparsed.get("marker", {}).get("classification") != "MARKER_FAMILY_ABSENT":
        raise QualificationError("baseline stream marker classification mismatch")
    if reparsed.get("input", {}).get("sha256") != PINNED_RUN_FILES["bugreport.zip"][1]:
        raise QualificationError("parser did not consume the pinned stream")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "inputs": inputs,
        "contract": {
            "historical_live_verdict_preserved": result["verdict"],
            "one_shot_consumed": True,
            "timeline": timeline_map,
            "zero_flash_semantics": True,
            "before_inventory": before,
            "after_inventory": after,
            "inventory_unchanged": True,
            "remote_cleanup_required": False,
            "stream": capture["stream"],
            "fresh_parser": reparsed,
            "baseline_raw_marker_counts": raw_observers,
            "baseline_android_equals_final": preflight["android"] == result["final"],
            "no_odin_before_and_after": True,
        },
        "decision": {
            "baseline_observer_qualified": True,
            "second_live_baseline_required": False,
            "candidate_clause_design_ready": True,
            "candidate_live_authorized": False,
            "old_oracle_pass_record_created": False,
            "qualification_is_not_retroactive_old_policy_pass": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "flash": False,
            "policy_activation": False,
            "promotion_record_created": False,
        },
    }


def write_new(path: Path, result: dict[str, Any]) -> None:
    if path.is_symlink() or path.exists():
        raise QualificationError(f"refusing to replace qualification output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = qualify(args.root)
        if args.out is not None:
            write_new(args.out, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (QualificationError, oracle.OracleError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
