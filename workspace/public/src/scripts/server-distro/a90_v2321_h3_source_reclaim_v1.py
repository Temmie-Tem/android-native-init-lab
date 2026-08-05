#!/usr/bin/env python3
"""One-shot attended reclaim of the closed H3 SD source from exact V2321.

The H3 source is selected by one fixed absent-only staging receipt and exact
host-preserved bytes.  The H4 incident source is protected.  Live execution
performs one nonrecursive unlink dispatch and never retransmits it; an
interrupted post-dispatch run may resume only through read-only reconciliation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SERVER_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for directory in (SERVER_DIR, REVAL_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import a90_obsolete_rootfs_cleanup_v1 as gc  # noqa: E402
import a90_v3405_retained_work_cleanup as legacy  # noqa: E402


SCHEMA = "a90_v2321_h3_source_reclaim_manifest_v1"
STATUS = "ready-for-attended-h3-source-reclaim"
INVENTORY_SCHEMA = "a90_v2321_h3_source_reclaim_inventory_v1"
RESULT_SCHEMA = "a90_v2321_h3_source_reclaim_result_v1"
CAPABILITY = "A90_ATTENDED_V2321_H3_SOURCE_RECLAIM_V1"
RUN_ID_RE = re.compile(r"^a90-v2321-h3-source-reclaim-[0-9]{8}-[0-9]{2}$")
PRIVATE_ROOT = (REPO_ROOT / "workspace" / "private").resolve()
PRIVATE_BASE = (PRIVATE_ROOT / "runs" / "server-distro").resolve()
RUNNER = Path(__file__).resolve()
COMMON_CONTRACT = (REPO_ROOT / "AGENTS.md").resolve()
TARGET_CONTRACT = (
    REPO_ROOT / "docs" / "operations" / "targets" / "A90_TARGET_CONTRACT.md"
).resolve()

SELECTED_RUN_ID = "a90-v3406-debian-display-f1-20260805-10"
SELECTED_PATH = (
    "/mnt/sdext/a90/runtime/"
    "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-10.img"
)
SELECTED_SHA256 = "34de408d868ff0651d0f6efb1d1d9cc810e3dfe23acaac178e73e2840b2979a4"
PROTECTED_RUN_ID = "a90-v3406-debian-display-f1-20260805-11"
PROTECTED_PATH = (
    "/mnt/sdext/a90/runtime/"
    "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-11.img"
)
PROTECTED_SHA256 = "8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
ROLLBACK_SIZE = 60882944
EXPECTED_VERSION = legacy.EXPECTED_VERSION
EXPECTED_BUILD = legacy.EXPECTED_BUILD
READ_TIMEOUT_SEC = 20.0
HASH_TIMEOUT_SEC = 240.0
CLEANUP_TIMEOUT_SEC = 300.0
MAX_INVENTORY_AGE_SEC = 900
CAPABILITY_EXPIRES_UTC = "2026-08-06T00:00:00Z"
CAPABILITY_STATE_DIR = "a90-v2321-h3-source-reclaim-capability-v1"

SELECTED_FIXED = gc.FixedImage(
    role="obsolete-h3-source-run10",
    device_path=SELECTED_PATH,
    sha256=SELECTED_SHA256,
    host_preservation=(
        PRIVATE_BASE / SELECTED_RUN_ID / "phase3-network-ssh-v1-keyed.img"
    ),
)
PROTECTED_FIXED = gc.FixedImage(
    role="incident-h4-source-run11",
    device_path=PROTECTED_PATH,
    sha256=PROTECTED_SHA256,
    host_preservation=None,
)


class ContractError(RuntimeError):
    """The exact one-shot reclaim contract was not satisfied."""


@dataclass(frozen=True)
class Spec:
    manifest_path: Path
    manifest_sha256: str
    run_id: str
    inventory: legacy.BoundFile
    bridge_realpath: str
    bridge_process: dict[str, Any]
    selected: tuple[gc.ImageRecord, ...]
    protected: tuple[gc.ImageRecord, ...]
    source_closure: dict[str, legacy.BoundFile]
    evidence: dict[str, legacy.BoundFile]
    rollback: legacy.BoundFile
    capability_dispatch_path: Path
    capability_expires_utc: str


def _private_bound(path: Path) -> legacy.BoundFile:
    return gc._bound(path, private=True)  # noqa: SLF001 - reviewed exact primitive


def _public_bound(path: Path) -> legacy.BoundFile:
    return gc._bound(path, private=False)  # noqa: SLF001 - reviewed exact primitive


def _bound_dict(value: legacy.BoundFile) -> dict[str, Any]:
    return {"path": str(value.path), "size": value.size, "sha256": value.sha256}


def _source_paths() -> dict[str, Path]:
    return {
        "runner": RUNNER,
        "rootfs_gc_primitives": gc.RUNNER,
        "v2321_health_and_evidence_primitives": Path(legacy.__file__).resolve(),
        "transport": gc.A90CTL,
        "serial_tcp_bridge": gc.SERIAL_TCP_BRIDGE,
        "common_contract": COMMON_CONTRACT,
        "target_contract": TARGET_CONTRACT,
    }


def capability_dispatch_path() -> Path:
    return (PRIVATE_BASE / CAPABILITY_STATE_DIR / "dispatch-started.json").resolve()


def _require_not_expired(now_epoch: int | None = None) -> None:
    expiry = int(
        dt.datetime.strptime(CAPABILITY_EXPIRES_UTC, "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=dt.UTC)
        .timestamp()
    )
    now = int(time.time()) if now_epoch is None else now_epoch
    if now >= expiry:
        raise ContractError("H3 source reclaim capability has expired")


def _require_capability_unconsumed() -> None:
    if capability_dispatch_path().exists():
        raise ContractError("H3 source reclaim capability is already consumed")


def _load_json(bound: legacy.BoundFile, label: str) -> dict[str, Any]:
    value = json.loads(bound.path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{label} is not an object")
    return value


def _historical_evidence() -> tuple[dict[str, legacy.BoundFile], legacy.BoundFile]:
    selected_dir = PRIVATE_BASE / SELECTED_RUN_ID
    protected_dir = PRIVATE_BASE / PROTECTED_RUN_ID
    evidence = {
        "selected_prepared_manifest": _private_bound(
            selected_dir / "resident-prepared-manifest-install-v2.json"
        ),
        "selected_staging_result": _private_bound(
            selected_dir / "staging-live" / "result.json"
        ),
        "protected_prepared_manifest": _private_bound(
            protected_dir / "prepared-manifest.json"
        ),
        "protected_staging_manifest": _private_bound(
            protected_dir / "resident-prepared-manifest-install-v2.json"
        ),
        "protected_staging_result": _private_bound(
            protected_dir / "staging-live" / "result.json"
        ),
        "incident_result": _private_bound(protected_dir / "f1-live" / "result.json"),
        "incident_candidate_flashed": _private_bound(
            protected_dir / "f1-live" / "journal" / "0007-candidate-flashed.json"
        ),
        "incident_rollback_flashed": _private_bound(
            protected_dir / "f1-live" / "journal" / "0009-rollback-flashed.json"
        ),
        "incident_final_health": _private_bound(
            protected_dir / "f1-live" / "journal" / "0011-health-verified.json"
        ),
        "incident_closed": _private_bound(
            protected_dir / "f1-live" / "journal" / "0012-closed.json"
        ),
    }
    selected_manifest = _load_json(
        evidence["selected_prepared_manifest"], "selected prepared manifest"
    )
    selected_staging = _load_json(
        evidence["selected_staging_result"], "selected staging result"
    )
    protected_manifest = _load_json(
        evidence["protected_prepared_manifest"], "protected prepared manifest"
    )
    protected_staging_manifest = _load_json(
        evidence["protected_staging_manifest"], "protected staging manifest"
    )
    protected_staging = _load_json(
        evidence["protected_staging_result"], "protected staging result"
    )
    result = _load_json(evidence["incident_result"], "incident result")
    candidate = _load_json(
        evidence["incident_candidate_flashed"], "candidate-flashed"
    )
    rollback_record = _load_json(
        evidence["incident_rollback_flashed"], "rollback-flashed"
    )
    health = _load_json(evidence["incident_final_health"], "final health")
    closed = _load_json(evidence["incident_closed"], "closed journal")
    selected_root = selected_manifest.get("debian_rootfs", {}).get("keyed_source", {})
    protected_root = protected_manifest.get("debian_rootfs", {}).get(
        "keyed_source", {}
    )
    staged_root = selected_staging.get("rootfs", {})
    publication = selected_staging.get("publication", {})
    safety = selected_staging.get("safety", {})
    rollback_value = protected_manifest.get("rollback_boot", {})
    recovery_target = protected_manifest.get("target", {})
    protected_staged_root = protected_staging.get("rootfs", {})
    if (
        selected_manifest.get("run_id") != SELECTED_RUN_ID
        or selected_staging.get("schema")
        != "a90_v3403_absent_only_staging_adapter_v1"
        or selected_staging.get("status") != "PASS_ABSENT_ONLY_ROOTFS_STAGED"
        or selected_staging.get("run_id") != SELECTED_RUN_ID
        or selected_staging.get("manifest_sha256")
        != evidence["selected_prepared_manifest"].sha256
        or staged_root
        != {"device_path": SELECTED_PATH, "size": gc.IMAGE_SIZE, "sha256": SELECTED_SHA256}
        or publication
        != {
            "candidate_allowed": True,
            "primitive": "hardlink-no-clobber",
            "stage_dir_removed": True,
        }
        or safety
        != {
            "flash": False,
            "mount": False,
            "reboot": False,
            "switch_root": False,
            "userdata_touched": False,
        }
        or selected_root.get("device_path") != SELECTED_PATH
        or selected_root.get("local_path") != str(SELECTED_FIXED.host_preservation)
        or selected_root.get("size") != gc.IMAGE_SIZE
        or selected_root.get("sha256") != SELECTED_SHA256
        or protected_manifest.get("run_id") != PROTECTED_RUN_ID
        or protected_root.get("device_path") != PROTECTED_PATH
        or protected_root.get("size") != gc.IMAGE_SIZE
        or protected_root.get("sha256") != PROTECTED_SHA256
        or protected_staging_manifest.get("run_id") != PROTECTED_RUN_ID
        or protected_staging.get("schema")
        != "a90_v3403_absent_only_staging_adapter_v1"
        or protected_staging.get("status") != "PASS_ABSENT_ONLY_ROOTFS_STAGED"
        or protected_staging.get("run_id") != PROTECTED_RUN_ID
        or protected_staging.get("manifest_sha256")
        != evidence["protected_staging_manifest"].sha256
        or protected_staged_root
        != {
            "device_path": PROTECTED_PATH,
            "size": gc.IMAGE_SIZE,
            "sha256": PROTECTED_SHA256,
        }
        or protected_staging.get("publication") != publication
        or protected_staging.get("safety") != safety
        or recovery_target.get("recovery")
        != (
            "attended physical Download or TWRP path followed by the exact checked "
            "V2321 rollback"
        )
        or not isinstance(recovery_target.get("recovery_adb_serial_sha256"), str)
        or re.fullmatch(
            r"[0-9a-f]{64}", recovery_target["recovery_adb_serial_sha256"]
        )
        is None
        or result.get("status")
        != "ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK"
        or result.get("candidate_replay") is not False
        or result.get("rollback_transfer_count") != 1
        or result.get("final_health_restored") is not True
        or candidate.get("candidate_transfer_count") != 1
        or candidate.get("candidate_replay") is not False
        or rollback_record.get("rollback_transfer_count") != 1
        or health.get("version") != EXPECTED_VERSION
        or health.get("build") != EXPECTED_BUILD
        or health.get("selftest_fail_zero") is not True
        or health.get("pstore_entries_zero") is not True
        or closed.get("status")
        != "ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK"
        or closed.get("candidate_replay") is not False
        or closed.get("rollback_transfer_count") != 1
        or closed.get("final_health_restored") is not True
        or rollback_value.get("partition") != "boot"
        or rollback_value.get("size") != ROLLBACK_SIZE
        or rollback_value.get("sha256") != ROLLBACK_SHA256
        or rollback_value.get("expected_version") != EXPECTED_VERSION
        or rollback_value.get("expected_build") != EXPECTED_BUILD
    ):
        raise ContractError("historical selected/protected/recovery evidence changed")
    host = _private_bound(SELECTED_FIXED.host_preservation)
    if host.size != gc.IMAGE_SIZE or host.sha256 != SELECTED_SHA256:
        raise ContractError("selected host preservation changed")
    rollback = _private_bound(Path(rollback_value["path"]))
    if rollback.size != ROLLBACK_SIZE or rollback.sha256 != ROLLBACK_SHA256:
        raise ContractError("exact V2321 rollback changed")
    evidence["selected_host_preservation"] = host
    protected_host = _private_bound(
        PRIVATE_BASE / PROTECTED_RUN_ID / "phase3-network-ssh-v1-keyed.img"
    )
    if protected_host.size != gc.IMAGE_SIZE or protected_host.sha256 != PROTECTED_SHA256:
        raise ContractError("protected host preservation changed")
    evidence["protected_host_preservation"] = protected_host
    return evidence, rollback


def _health() -> dict[str, Any]:
    return legacy.health_preflight("127.0.0.1", 54321, READ_TIMEOUT_SEC)


def _require_bridge(
    realpath: str,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    bridge_sha, bridge_state = legacy.hash_open_regular(gc.SERIAL_TCP_BRIDGE)
    matches: list[dict[str, Any]] = []
    for item in proc_root.iterdir():
        if not item.name.isdigit():
            continue
        try:
            argv = [
                part.decode("utf-8", errors="surrogateescape")
                for part in (item / "cmdline").read_bytes().split(b"\0")
                if part
            ]
            interpreter = Path(argv[0]).resolve(strict=True)
            script = Path(argv[1]).resolve(strict=True)
        except (OSError, IndexError):
            continue
        if (
            interpreter != Path(sys.executable).resolve(strict=True)
            or argv[1] != str(gc.SERIAL_TCP_BRIDGE)
            or script != gc.SERIAL_TCP_BRIDGE
            or len(argv) != 15
            or argv[2:12]
            != [
                "--host",
                gc.a90ctl.DEFAULT_HOST,
                "--port",
                str(gc.a90ctl.DEFAULT_PORT),
                "--device",
                str(gc.BRIDGE_DEVICE),
                "--device-glob",
                (
                    str(gc.BRIDGE_DEVICE)
                    + ",/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*"
                ),
                "--capture",
                argv[11],
            ]
            or argv[12:]
            != ["--expect-realpath", realpath, "--assert-dtr-rts"]
        ):
            continue
        capture = Path(argv[11])
        if (
            not capture.is_absolute()
            or not capture.resolve().is_relative_to(PRIVATE_ROOT / "logs" / "bridge")
        ):
            continue
        pid = int(item.name)
        start = gc._process_start_epoch_sec(pid, proc_root)  # noqa: SLF001
        if (bridge_state.st_mtime_ns + 999_999_999) // 1_000_000_000 > start:
            continue
        matches.append(
            {
                "pid": pid,
                "start_epoch_sec": start,
                "script_path": str(gc.SERIAL_TCP_BRIDGE),
                "script_sha256": bridge_sha,
                "script_mtime_ns": bridge_state.st_mtime_ns,
                "argv_sha256": legacy.json_sha256(argv),
                "assert_dtr_rts": True,
                "matching_processes": 1,
                "local_endpoint": "127.0.0.1:54321",
            }
        )
    if len(matches) != 1:
        raise ContractError("exactly one current realpath-pinned A90 bridge is required")
    return matches[0]


def _validated_bridge_process(value: Any) -> dict[str, Any]:
    bridge_sha, bridge_state = legacy.hash_open_regular(gc.SERIAL_TCP_BRIDGE)
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "pid",
            "start_epoch_sec",
            "script_path",
            "script_sha256",
            "script_mtime_ns",
            "argv_sha256",
            "assert_dtr_rts",
            "matching_processes",
            "local_endpoint",
        }
        or type(value.get("pid")) is not int
        or value["pid"] <= 0
        or type(value.get("start_epoch_sec")) is not int
        or value["start_epoch_sec"] <= 0
        or value.get("script_path") != str(gc.SERIAL_TCP_BRIDGE)
        or value.get("script_sha256") != bridge_sha
        or value.get("script_mtime_ns") != bridge_state.st_mtime_ns
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("argv_sha256") or ""))
        is None
        or value.get("assert_dtr_rts") is not True
        or value.get("matching_processes") != 1
        or value.get("local_endpoint") != "127.0.0.1:54321"
        or (bridge_state.st_mtime_ns + 999_999_999) // 1_000_000_000
        > value["start_epoch_sec"]
    ):
        raise ContractError("current A90 bridge process binding changed")
    return value


def _stage_absence() -> None:
    script = "\n".join(
        (
            "set -eu",
            "for x in /mnt/sdext/a90/runtime/.a90-stage-* "
            "/mnt/sdext/a90/runtime/.a90-d1-stage-* "
            "/mnt/sdext/a90/runtime/.a90-cleanup-restore-*; do",
            '  [ ! -e "$x" ] && [ ! -L "$x" ] || exit 60',
            "done",
            "echo A90RECLAIM_STAGE_ABSENT=1",
        )
    )
    text = gc._run_script(script, READ_TIMEOUT_SEC, "reclaim stage absence")  # noqa: SLF001
    if text.count("A90RECLAIM_STAGE_ABSENT=1") != 1:
        raise ContractError("reclaim stage absence marker is not exact")


def capture_inventory(run_id: str, output: Path) -> dict[str, Any]:
    _require_not_expired()
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("reclaim run_id is not exact")
    expected = (PRIVATE_BASE / run_id / "inventory.json").resolve()
    if output.resolve() != expected or output.exists():
        raise ContractError("inventory output is not a new exact private path")
    _historical_evidence()
    realpath, serial_sha = gc._find_target()  # noqa: SLF001
    bridge = _require_bridge(realpath)
    health = _health()
    fixed = (SELECTED_FIXED, PROTECTED_FIXED)
    transcripts = [
        gc._bounded_inventory_read(  # noqa: SLF001
            gc._inventory_work_script(), READ_TIMEOUT_SEC, "work-path inventory"  # noqa: SLF001
        )
    ]
    for index, item in enumerate(fixed):
        transcripts.append(
            gc._bounded_inventory_read(  # noqa: SLF001
                gc._inventory_image_script(index, item),  # noqa: SLF001
                HASH_TIMEOUT_SEC,
                f"reclaim image inventory {index}",
            )
        )
    transcripts.append(
        gc._bounded_inventory_read(  # noqa: SLF001
            gc._inventory_df_script(), READ_TIMEOUT_SEC, "filesystem inventory"  # noqa: SLF001
        )
    )
    images, filesystem = gc._parse_inventory("\n".join(transcripts), fixed)  # noqa: SLF001
    _stage_absence()
    _require_not_expired()
    output.parent.mkdir(mode=0o700, parents=False, exist_ok=False)
    value = {
        "schema": INVENTORY_SCHEMA,
        "created_utc": legacy.utc_now(),
        "captured_epoch_sec": int(time.time()),
        "run_id": run_id,
        "target": {
            "bridge_realpath": realpath,
            "usb_serial_sha256": serial_sha,
            "bridge_process": bridge,
        },
        "health": health,
        "images": images,
        "work_absent": True,
        "stage_absent": True,
        "filesystem_kib": filesystem,
        "device_contact": True,
        "device_write": False,
        "other_target_commands": 0,
    }
    legacy.write_private_json_exclusive(output, value)
    return value


def _record(value: Any, fixed: gc.FixedImage, host: legacy.BoundFile | None) -> gc.ImageRecord:
    if not isinstance(value, dict):
        raise ContractError(f"{fixed.role} inventory record is not an object")
    if (
        value.get("role") != fixed.role
        or value.get("device_path") != fixed.device_path
        or value.get("size") != gc.IMAGE_SIZE
        or value.get("mode") != gc.IMAGE_MODE
        or value.get("nlink") != 1
        or value.get("sha256") != fixed.sha256
        or any(type(value.get(key)) is not int or value[key] <= 0 for key in ("blocks", "st_dev", "st_ino"))
    ):
        raise ContractError(f"{fixed.role} inventory identity changed")
    return gc.ImageRecord(
        role=fixed.role,
        device_path=fixed.device_path,
        size=gc.IMAGE_SIZE,
        blocks=value["blocks"],
        mode=gc.IMAGE_MODE,
        nlink=1,
        st_dev=value["st_dev"],
        st_ino=value["st_ino"],
        sha256=fixed.sha256,
        host_preservation=host,
    )


def _load_inventory(path: Path, sha256: str) -> tuple[legacy.BoundFile, dict[str, Any]]:
    bound = _private_bound(path)
    if bound.sha256 != sha256:
        raise ContractError("inventory SHA256 changed")
    value = _load_json(bound, "inventory")
    images = value.get("images")
    if (
        value.get("schema") != INVENTORY_SCHEMA
        or RUN_ID_RE.fullmatch(str(value.get("run_id") or "")) is None
        or not isinstance(images, list)
        or len(images) != 2
        or value.get("work_absent") is not True
        or value.get("stage_absent") is not True
        or value.get("device_contact") is not True
        or value.get("device_write") is not False
        or value.get("other_target_commands") != 0
        or value.get("health", {}).get("version") != EXPECTED_VERSION
        or value.get("health", {}).get("build") != EXPECTED_BUILD
        or value.get("health", {}).get("proven") is not True
    ):
        raise ContractError("inventory shape or V2321 health changed")
    target = value.get("target")
    if (
        not isinstance(target, dict)
        or set(target) != {"bridge_realpath", "usb_serial_sha256", "bridge_process"}
        or not isinstance(target.get("bridge_realpath"), str)
        or target.get("usb_serial_sha256") != gc.USB_SERIAL_SHA256
    ):
        raise ContractError("inventory target identity changed")
    _record(images[0], SELECTED_FIXED, None)
    _record(images[1], PROTECTED_FIXED, None)
    _validated_bridge_process(target.get("bridge_process"))
    return bound, value


def build_manifest(run_id: str, inventory_path: Path, inventory_sha256: str, output: Path) -> dict[str, Any]:
    _require_not_expired()
    inventory, inventory_value = _load_inventory(inventory_path, inventory_sha256)
    if inventory_value.get("run_id") != run_id:
        raise ContractError("manifest and inventory run IDs differ")
    expected = (PRIVATE_BASE / run_id / "manifest.json").resolve()
    if output.resolve() != expected or output.exists():
        raise ContractError("manifest output is not a new exact private path")
    evidence, rollback = _historical_evidence()
    source_closure = {role: _public_bound(path) for role, path in _source_paths().items()}
    images = inventory_value["images"]
    selected = dict(images[0])
    selected["host_preservation"] = _bound_dict(
        evidence["selected_host_preservation"]
    )
    manifest = {
        "schema": SCHEMA,
        "status": STATUS,
        "created_utc": legacy.utc_now(),
        "run_id": run_id,
        "capability": CAPABILITY,
        "inventory": _bound_dict(inventory),
        "target": inventory_value["target"],
        "selected": selected,
        "protected": images[1],
        "source_closure": {
            role: _bound_dict(bound) for role, bound in sorted(source_closure.items())
        },
        "historical_evidence": {
            role: _bound_dict(bound) for role, bound in sorted(evidence.items())
        },
        "rollback_boot": _bound_dict(rollback),
        "recovery_profile": (
            "attended physical Download or TWRP path followed by the exact checked "
            "V2321 rollback"
        ),
        "capability_lifetime": {
            "dispatch_path": str(capability_dispatch_path()),
            "expires_utc": CAPABILITY_EXPIRES_UTC,
            "consumed_by_first_durable_dispatch": True,
            "cross_run_reuse_forbidden": True,
        },
        "authority": {
            "risk_tier": "TIER_D1_ATTENDED_EXACT_STORAGE_ARTIFACT_CLEANUP",
            "operator_attended_required": True,
            "unlink_dispatch_count_max": 1,
            "unlink_retry_forbidden": True,
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
        },
    }
    _require_not_expired()
    legacy.write_private_json_exclusive(output, manifest)
    return manifest


def load_spec(path: Path, expected_sha256: str) -> Spec:
    manifest = _private_bound(path)
    if manifest.sha256 != expected_sha256:
        raise ContractError("manifest SHA256 changed")
    value = _load_json(manifest, "manifest")
    run_id = value.get("run_id")
    if (
        set(value)
        != {
            "schema",
            "status",
            "created_utc",
            "run_id",
            "capability",
            "inventory",
            "target",
            "selected",
            "protected",
            "source_closure",
            "historical_evidence",
            "rollback_boot",
            "recovery_profile",
            "capability_lifetime",
            "authority",
        }
        or value.get("recovery_profile")
        != (
            "attended physical Download or TWRP path followed by the exact checked "
            "V2321 rollback"
        )
        or value.get("schema") != SCHEMA
        or value.get("status") != STATUS
        or value.get("capability") != CAPABILITY
        or not isinstance(run_id, str)
        or RUN_ID_RE.fullmatch(run_id) is None
        or manifest.path != (PRIVATE_BASE / run_id / "manifest.json").resolve()
    ):
        raise ContractError("manifest header changed")
    inventory_value = value.get("inventory")
    if not isinstance(inventory_value, dict):
        raise ContractError("manifest inventory binding is absent")
    inventory, loaded_inventory = _load_inventory(
        Path(inventory_value["path"]), inventory_value["sha256"]
    )
    if inventory_value != _bound_dict(inventory) or loaded_inventory["run_id"] != run_id:
        raise ContractError("manifest inventory binding changed")
    evidence, rollback = _historical_evidence()
    if value.get("historical_evidence") != {
        role: _bound_dict(bound) for role, bound in sorted(evidence.items())
    } or value.get("rollback_boot") != _bound_dict(rollback):
        raise ContractError("manifest historical evidence changed")
    source_values = value.get("source_closure")
    source_paths = _source_paths()
    if not isinstance(source_values, dict) or set(source_values) != set(source_paths):
        raise ContractError("manifest source closure roles changed")
    source_closure: dict[str, legacy.BoundFile] = {}
    for role, source_path in source_paths.items():
        bound = _public_bound(source_path)
        if source_values[role] != _bound_dict(bound):
            raise ContractError(f"manifest source closure changed for {role}")
        source_closure[role] = bound
    selected_value = value.get("selected")
    protected_value = value.get("protected")
    if not isinstance(selected_value, dict) or not isinstance(protected_value, dict):
        raise ContractError("manifest selected/protected records are absent")
    host_value = selected_value.get("host_preservation")
    if host_value != _bound_dict(evidence["selected_host_preservation"]):
        raise ContractError("manifest host preservation changed")
    selected_identity = {k: v for k, v in selected_value.items() if k != "host_preservation"}
    if (
        selected_identity != loaded_inventory["images"][0]
        or protected_value != loaded_inventory["images"][1]
    ):
        raise ContractError("manifest selected/protected inventory binding changed")
    selected = _record(
        selected_identity, SELECTED_FIXED, evidence["selected_host_preservation"]
    )
    protected = _record(protected_value, PROTECTED_FIXED, None)
    if (selected.st_dev, selected.st_ino) == (protected.st_dev, protected.st_ino):
        raise ContractError("selected and protected inode identities overlap")
    target = value.get("target")
    authority = value.get("authority")
    lifetime = value.get("capability_lifetime")
    if (
        target != loaded_inventory.get("target")
        or not isinstance(target, dict)
        or not isinstance(authority, dict)
        or lifetime
        != {
            "dispatch_path": str(capability_dispatch_path()),
            "expires_utc": CAPABILITY_EXPIRES_UTC,
            "consumed_by_first_durable_dispatch": True,
            "cross_run_reuse_forbidden": True,
        }
        or authority
        != {
            "risk_tier": "TIER_D1_ATTENDED_EXACT_STORAGE_ARTIFACT_CLEANUP",
            "operator_attended_required": True,
            "unlink_dispatch_count_max": 1,
            "unlink_retry_forbidden": True,
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
        }
    ):
        raise ContractError("manifest target or authority changed")
    return Spec(
        manifest_path=manifest.path,
        manifest_sha256=manifest.sha256,
        run_id=run_id,
        inventory=inventory,
        bridge_realpath=target["bridge_realpath"],
        bridge_process=_validated_bridge_process(target["bridge_process"]),
        selected=(selected,),
        protected=(protected,),
        source_closure=source_closure,
        evidence=evidence,
        rollback=rollback,
        capability_dispatch_path=capability_dispatch_path(),
        capability_expires_utc=CAPABILITY_EXPIRES_UTC,
    )


def _inventory_age(spec: Spec) -> None:
    value = _load_json(spec.inventory, "inventory")
    age = int(time.time()) - value["captured_epoch_sec"]
    if age < -5 or age > MAX_INVENTORY_AGE_SEC:
        raise ContractError("reclaim inventory is stale")


def _revalidate_host(spec: Spec) -> None:
    for role, path in _source_paths().items():
        if _public_bound(path) != spec.source_closure[role]:
            raise ContractError(f"source closure changed for {role}")
    evidence, rollback = _historical_evidence()
    if evidence != spec.evidence or rollback != spec.rollback:
        raise ContractError("historical evidence changed before dispatch")


def _live_target(
    spec: Spec,
    *,
    allow_new_bridge_generation: bool = False,
) -> tuple[str, dict[str, Any]]:
    realpath, serial_sha = gc._find_target()  # noqa: SLF001
    if realpath != spec.bridge_realpath or serial_sha != gc.USB_SERIAL_SHA256:
        raise ContractError("live A90 target differs from the manifest")
    bridge = _require_bridge(realpath)
    if bridge != spec.bridge_process and not allow_new_bridge_generation:
        raise ContractError("live A90 bridge generation differs from the manifest")
    return realpath, bridge


def _proxy(spec: Spec) -> SimpleNamespace:
    return SimpleNamespace(
        run_id=spec.run_id,
        manifest_sha256=spec.manifest_sha256,
        selected=spec.selected,
        protected=spec.protected,
    )


def _result(
    spec: Spec,
    *,
    before: dict[str, int],
    response_proven: bool,
    dispatch_error: dict[str, str] | None,
    reconciliation: dict[str, Any],
    reconciliation_error: dict[str, str] | None,
    final_health: dict[str, Any],
    final_health_error: dict[str, str] | None,
    resumed: bool,
) -> dict[str, Any]:
    after = reconciliation.get("filesystem_kib")
    gain = (
        after.get("available") - before["available"]
        if isinstance(after, dict) and type(after.get("available")) is int
        else None
    )
    bounds = gc._free_gain_bounds(_proxy(spec))  # noqa: SLF001
    complete = (
        reconciliation.get("selected") == ["absent"]
        and reconciliation.get("protected") == "exact"
        and reconciliation.get("work") == "absent"
        and final_health.get("proven") is True
        and gain is not None
        and bounds[0] <= gain <= bounds[1]
    )
    if complete:
        outcome = (
            "PASS_H3_SOURCE_RECLAIMED"
            if response_proven
            else "PASS_H3_SOURCE_RECLAIM_PROVEN_AFTER_AMBIGUOUS_RESPONSE"
        )
    else:
        outcome = "RECOVERY_PENDING_PARKED_NO_RETRY"
    return {
        "schema": RESULT_SCHEMA,
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "outcome": outcome,
        "dispatch_count": 1,
        "cleanup_retransmitted": False,
        "response_proven": response_proven,
        "dispatch_error": dispatch_error,
        "reconciliation": reconciliation,
        "reconciliation_error": reconciliation_error,
        "final_health": final_health,
        "final_health_error": final_health_error,
        "before_filesystem_kib": before,
        "free_gain_kib": gain,
        "free_gain_bounds_kib": list(bounds),
        "resumed_from_durable_dispatch": resumed,
        "device_write": True,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "other_target_commands": 0,
    }


def _observe_after_dispatch(spec: Spec, before: dict[str, int], response_proven: bool, dispatch_error: dict[str, str] | None, resumed: bool) -> dict[str, Any]:
    reconciliation_error = None
    try:
        reconciliation = gc._read_reconciliation(_proxy(spec))  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001 - observation never repeats unlink
        reconciliation = {"selected": ["unknown"], "protected": "unknown", "work": "unknown"}
        reconciliation_error = {"type": type(exc).__name__, "message": str(exc)}
    health_error = None
    try:
        health = _health()
    except Exception as exc:  # noqa: BLE001 - health failure never repeats unlink
        health = {"proven": False}
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    return _result(
        spec,
        before=before,
        response_proven=response_proven,
        dispatch_error=dispatch_error,
        reconciliation=reconciliation,
        reconciliation_error=reconciliation_error,
        final_health=health,
        final_health_error=health_error,
        resumed=resumed,
    )


def _observe_expired_before_unlink(
    spec: Spec,
    before: dict[str, int],
    expiry_error: dict[str, str],
    resumed: bool,
) -> dict[str, Any]:
    reconciliation_error = None
    try:
        reconciliation = gc._read_reconciliation(_proxy(spec))  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001 - read-only terminal observation
        reconciliation = {
            "selected": ["unknown"],
            "protected": "unknown",
            "work": "unknown",
        }
        reconciliation_error = {"type": type(exc).__name__, "message": str(exc)}
    health_error = None
    try:
        health = _health()
    except Exception as exc:  # noqa: BLE001 - read-only terminal observation
        health = {"proven": False}
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    after = reconciliation.get("filesystem_kib")
    gain = (
        after.get("available") - before["available"]
        if isinstance(after, dict) and type(after.get("available")) is int
        else None
    )
    exact_unchanged = (
        reconciliation.get("selected") == ["present"]
        and reconciliation.get("protected") == "exact"
        and reconciliation.get("work") == "absent"
        and health.get("proven") is True
        and gain == 0
    )
    return {
        "schema": RESULT_SCHEMA,
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "outcome": (
            "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK"
            if exact_unchanged
            else "RECOVERY_PENDING_PARKED_NO_RETRY"
        ),
        "capability_consumed": True,
        "dispatch_count": 0,
        "cleanup_retransmitted": False,
        "response_proven": False,
        "dispatch_error": expiry_error,
        "reconciliation": reconciliation,
        "reconciliation_error": reconciliation_error,
        "final_health": health,
        "final_health_error": health_error,
        "before_filesystem_kib": before,
        "free_gain_kib": gain,
        "free_gain_bounds_kib": [0, 0],
        "resumed_from_durable_dispatch": resumed,
        "device_write": False,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "other_target_commands": 0,
    }


def execute(spec: Spec, transaction_dir: Path, operator_attended: bool) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("H3 source reclaim is attended-only")
    _require_not_expired()
    _require_capability_unconsumed()
    expected = (PRIVATE_BASE / spec.run_id / "live").resolve()
    if transaction_dir.resolve() != expected or transaction_dir.exists():
        raise ContractError("reclaim transaction must be a new exact private path")
    _inventory_age(spec)
    _revalidate_host(spec)
    realpath, bridge = _live_target(spec)
    before_health = _health()
    before = gc._read_cleanup_preflight(_proxy(spec))  # noqa: SLF001
    _inventory_age(spec)
    _revalidate_host(spec)
    realpath, bridge = _live_target(spec)
    before_health = _health()
    command = gc._cleanup_command(_proxy(spec))  # noqa: SLF001
    _require_not_expired()
    transaction_dir.mkdir(mode=0o700)
    legacy.write_private_json_exclusive(
        transaction_dir / "intent.json",
        {
            "schema": "a90_v2321_h3_source_reclaim_intent_v1",
            "created_utc": legacy.utc_now(),
            "run_id": spec.run_id,
            "manifest_sha256": spec.manifest_sha256,
            "target": {"bridge_realpath": realpath, "bridge_process": bridge},
            "before_health": before_health,
            "before_filesystem_kib": before,
            "selected_path": SELECTED_PATH,
            "protected_path": PROTECTED_PATH,
            "rollback_sha256": spec.rollback.sha256,
            "unlink_dispatch_count_max": 1,
            "unlink_retry_forbidden": True,
        },
    )
    _require_not_expired()
    dispatch_value = {
        "schema": "a90_v2321_h3_source_reclaim_dispatch_v1",
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "selected_path": SELECTED_PATH,
        "selected_sha256": SELECTED_SHA256,
        "protected_path": PROTECTED_PATH,
        "protected_sha256": PROTECTED_SHA256,
        "cleanup_command_sha256": legacy.json_sha256({"argv": command}),
        "dispatch_authorization_count": 1,
        "unlink_dispatch_count_max": 1,
        "retry_forbidden": True,
        "capability_consumed": True,
    }
    legacy.write_private_json_exclusive(
        spec.capability_dispatch_path,
        dispatch_value,
    )
    legacy.write_private_json_exclusive(
        transaction_dir / "dispatch-started.json", dispatch_value
    )
    response_proven = False
    dispatch_error = None
    cleanup_script = gc._cleanup_script(_proxy(spec))  # noqa: SLF001
    cleanup_args = gc._cleanup_args(_proxy(spec))  # noqa: SLF001
    try:
        _require_not_expired()
    except ContractError as exc:
        expiry_error = {"type": type(exc).__name__, "message": str(exc)}
        legacy.write_private_json_exclusive(
            transaction_dir / "effect-not-started.json",
            {
                "schema": "a90_v2321_h3_source_reclaim_effect_not_started_v1",
                "created_utc": legacy.utc_now(),
                "run_id": spec.run_id,
                "manifest_sha256": spec.manifest_sha256,
                "reason": "capability-expired-before-unlink",
                "dispatch_count": 0,
                "device_write": False,
                "capability_consumed": True,
            },
        )
        result = _observe_expired_before_unlink(
            spec, before, expiry_error, False
        )
        legacy.write_private_json_exclusive(transaction_dir / "result.json", result)
        return result
    try:
        text = gc._run_script(  # noqa: SLF001
            cleanup_script,
            CLEANUP_TIMEOUT_SEC,
            "H3 source reclaim dispatch",
            args=cleanup_args,
        )
        response_proven = text.count(
            "A90CLEAN_UNLINKED exact=1 selected_absent=1"
        ) == 1
        if not response_proven:
            dispatch_error = {"type": "ContractError", "message": "unlink marker is not exact"}
    except Exception as exc:  # noqa: BLE001 - unlink is never retransmitted
        dispatch_error = {"type": type(exc).__name__, "message": str(exc)}
    result = _observe_after_dispatch(
        spec, before, response_proven, dispatch_error, False
    )
    legacy.write_private_json_exclusive(transaction_dir / "result.json", result)
    return result


def _load_effect_not_started(spec: Spec, path: Path) -> dict[str, Any]:
    value = _load_json(_private_bound(path), "effect-not-started")
    if (
        value.get("schema")
        != "a90_v2321_h3_source_reclaim_effect_not_started_v1"
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("reason") != "capability-expired-before-unlink"
        or value.get("dispatch_count") != 0
        or value.get("device_write") is not False
        or value.get("capability_consumed") is not True
    ):
        raise ContractError("effect-not-started evidence changed")
    return value


def resume(spec: Spec, transaction_dir: Path) -> dict[str, Any]:
    expected = (PRIVATE_BASE / spec.run_id / "live").resolve()
    if transaction_dir.resolve() != expected or not transaction_dir.is_dir():
        raise ContractError("resume transaction path is not exact")
    result_path = transaction_dir / "result.json"
    existing_result = (
        _load_json(_private_bound(result_path), "existing result")
        if result_path.exists()
        else None
    )
    intent = _load_json(_private_bound(transaction_dir / "intent.json"), "intent")
    dispatch = _load_json(
        _private_bound(transaction_dir / "dispatch-started.json"),
        "dispatch-started",
    )
    capability_dispatch = _load_json(
        _private_bound(spec.capability_dispatch_path),
        "capability dispatch-started",
    )
    command = gc._cleanup_command(_proxy(spec))  # noqa: SLF001
    if (
        intent.get("manifest_sha256") != spec.manifest_sha256
        or intent.get("before_filesystem_kib") is None
        or dispatch.get("dispatch_authorization_count") != 1
        or dispatch.get("unlink_dispatch_count_max") != 1
        or dispatch.get("retry_forbidden") is not True
        or dispatch.get("capability_consumed") is not True
        or capability_dispatch != dispatch
        or dispatch.get("manifest_sha256") != spec.manifest_sha256
        or dispatch.get("selected_path") != SELECTED_PATH
        or dispatch.get("selected_sha256") != SELECTED_SHA256
        or dispatch.get("protected_path") != PROTECTED_PATH
        or dispatch.get("protected_sha256") != PROTECTED_SHA256
        or dispatch.get("cleanup_command_sha256")
        != legacy.json_sha256({"argv": command})
    ):
        raise ContractError("durable reclaim dispatch binding changed")
    effect_not_started_path = transaction_dir / "effect-not-started.json"
    if effect_not_started_path.exists():
        _load_effect_not_started(spec, effect_not_started_path)
        if existing_result is not None:
            if (
                existing_result.get("schema") != RESULT_SCHEMA
                or existing_result.get("run_id") != spec.run_id
                or existing_result.get("manifest_sha256") != spec.manifest_sha256
                or existing_result.get("outcome")
                != "CAPABILITY_CONSUMED_EXPIRED_BEFORE_UNLINK"
                or existing_result.get("capability_consumed") is not True
                or existing_result.get("dispatch_count") != 0
                or existing_result.get("device_write") is not False
                or existing_result.get("cleanup_retransmitted") is not False
            ):
                raise ContractError("expired-before-unlink result changed")
            return existing_result
        _revalidate_host(spec)
        _live_target(spec, allow_new_bridge_generation=True)
        result = _observe_expired_before_unlink(
            spec,
            intent["before_filesystem_kib"],
            {"type": "ContractError", "message": "capability expired before unlink"},
            True,
        )
        legacy.write_private_json_exclusive(result_path, result)
        return result
    if existing_result is not None:
        if (
            existing_result.get("schema") != RESULT_SCHEMA
            or existing_result.get("run_id") != spec.run_id
            or existing_result.get("manifest_sha256") != spec.manifest_sha256
            or existing_result.get("dispatch_count") != 1
            or existing_result.get("device_write") is not True
            or existing_result.get("cleanup_retransmitted") is not False
            or existing_result.get("outcome")
            not in {
                "PASS_H3_SOURCE_RECLAIMED",
                "PASS_H3_SOURCE_RECLAIM_PROVEN_AFTER_AMBIGUOUS_RESPONSE",
                "RECOVERY_PENDING_PARKED_NO_RETRY",
            }
        ):
            raise ContractError("existing reclaim result changed")
        return existing_result
    _revalidate_host(spec)
    _live_target(spec, allow_new_bridge_generation=True)
    result = _observe_after_dispatch(
        spec,
        intent["before_filesystem_kib"],
        False,
        {"type": "Interrupted", "message": "resumed after durable dispatch"},
        True,
    )
    legacy.write_private_json_exclusive(result_path, result)
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--capture-inventory", action="store_true")
    value.add_argument("--build-manifest", action="store_true")
    value.add_argument("--execute", action="store_true")
    value.add_argument("--resume", action="store_true")
    value.add_argument("--operator-attended", action="store_true")
    value.add_argument("--run-id")
    value.add_argument("--output", type=Path)
    value.add_argument("--inventory", type=Path)
    value.add_argument("--inventory-sha256")
    value.add_argument("--manifest", type=Path)
    value.add_argument("--manifest-sha256")
    value.add_argument("--transaction-dir", type=Path)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    modes = sum((args.capture_inventory, args.build_manifest, args.execute, args.resume))
    if modes != 1:
        raise ContractError("select exactly one reclaim mode")
    if args.capture_inventory:
        if not args.run_id or args.output is None:
            raise ContractError("inventory mode requires run-id and output")
        result = capture_inventory(args.run_id, args.output)
    elif args.build_manifest:
        if not args.run_id or args.inventory is None or not args.inventory_sha256 or args.output is None:
            raise ContractError("manifest mode requires exact inputs")
        result = build_manifest(
            args.run_id, args.inventory, args.inventory_sha256, args.output
        )
    else:
        if args.manifest is None or not args.manifest_sha256 or args.transaction_dir is None:
            raise ContractError("live mode requires manifest and transaction")
        spec = load_spec(args.manifest, args.manifest_sha256)
        result = (
            execute(spec, args.transaction_dir, args.operator_attended)
            if args.execute
            else resume(spec, args.transaction_dir)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
