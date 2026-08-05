#!/usr/bin/env python3
"""One-shot attended reclaim of the obsolete H4 source from healthy H5.

The H4 source is selected by its exact closed incident and absent-only staging
evidence.  The installed H5 source is one exact protected identity.  This
adapter configures the reviewed one-shot reclaim engine; it does not add a
second unlink implementation.
"""

from __future__ import annotations

import json
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SERVER_DIR = Path(__file__).resolve().parent
for directory in (SERVER_DIR,):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import a90_auto_handoff_benchmark_runner_v1 as auto  # noqa: E402
import a90_obsolete_rootfs_cleanup_v1 as gc  # noqa: E402
import a90_transition_d1_session_v1 as resident  # noqa: E402
import a90_v3405_retained_work_cleanup as legacy  # noqa: E402

ENGINE_PATH = SERVER_DIR / "a90_v2321_h3_source_reclaim_v1.py"
_ENGINE_SPEC = importlib.util.spec_from_file_location(f"{__name__}_engine", ENGINE_PATH)
if _ENGINE_SPEC is None or _ENGINE_SPEC.loader is None:
    raise ImportError(f"cannot load one-shot reclaim engine: {ENGINE_PATH}")
engine = importlib.util.module_from_spec(_ENGINE_SPEC)
sys.modules[_ENGINE_SPEC.name] = engine
_ENGINE_SPEC.loader.exec_module(engine)


RUNNER = Path(__file__).resolve()
PRIVATE_BASE = (
    REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
).resolve()

SCHEMA = "a90_h5_h4_source_reclaim_manifest_v1"
STATUS = "ready-for-attended-h5-h4-source-reclaim"
INVENTORY_SCHEMA = "a90_h5_h4_source_reclaim_inventory_v1"
RESULT_SCHEMA = "a90_h5_h4_source_reclaim_result_v1"
INTENT_SCHEMA = "a90_h5_h4_source_reclaim_intent_v1"
DISPATCH_SCHEMA = "a90_h5_h4_source_reclaim_dispatch_v1"
EFFECT_NOT_STARTED_SCHEMA = "a90_h5_h4_source_reclaim_effect_not_started_v1"
CAPABILITY = "A90_ATTENDED_H5_H4_SOURCE_RECLAIM_V1"
RUN_ID_RE = re.compile(r"^a90-h5-h4-source-reclaim-[0-9]{8}-[0-9]{2}$")
CAPABILITY_EXPIRES_UTC = "2026-08-07T00:00:00Z"
CAPABILITY_STATE_DIR = "a90-h5-h4-source-reclaim-capability-v1"
PASS_OUTCOME = "PASS_H4_SOURCE_RECLAIMED_FROM_HEALTHY_H5"
PASS_AMBIGUOUS_OUTCOME = (
    "PASS_H4_SOURCE_RECLAIM_PROVEN_AFTER_AMBIGUOUS_RESPONSE"
)

SELECTED_RUN_ID = "a90-v3406-debian-display-f1-20260805-11"
SELECTED_PATH = (
    "/mnt/sdext/a90/runtime/"
    "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-11.img"
)
SELECTED_SHA256 = "8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa"
PROTECTED_RUN_ID = "a90-v3406-debian-display-f1-20260805-12"
PROTECTED_PATH = (
    "/mnt/sdext/a90/runtime/"
    "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-12.img"
)
PROTECTED_SHA256 = "874291801573d96bf7731b2cdc27deca066221450534365eddfa2acf41ab681e"
RESIDENT_RUN_ID = "a90-v3406-debian-display-f1-20260805-13"
D1_RUN_ID = "a90-d1-attended-20260805-09"
D1_MANIFEST_SHA256 = "f7f86b10f44b56d8434776ca090c7b3ce3fe14389679530b7cb9cf4f64a72763"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
ROLLBACK_SIZE = 60882944
EXPECTED_VERSION = auto.EXPECTED_VERSION
EXPECTED_BUILD = auto.EXPECTED_BUILD
RECOVERY_PROFILE = (
    "attended physical Download or TWRP path followed by the exact checked "
    "V2321 rollback"
)

SELECTED_FIXED = gc.FixedImage(
    role="obsolete-h4-incident-source-run11",
    device_path=SELECTED_PATH,
    sha256=SELECTED_SHA256,
    host_preservation=(
        PRIVATE_BASE / SELECTED_RUN_ID / "phase3-network-ssh-v1-keyed.img"
    ),
)
PROTECTED_FIXED = gc.FixedImage(
    role="installed-h5-source-run12",
    device_path=PROTECTED_PATH,
    sha256=PROTECTED_SHA256,
    host_preservation=None,
)


def _bound(path: Path) -> legacy.BoundFile:
    return engine._private_bound(path)  # noqa: SLF001 - exact engine primitive


def _load(bound: legacy.BoundFile, label: str) -> dict[str, Any]:
    value = json.loads(bound.path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise engine.ContractError(f"{label} is not an object")
    return value


def _exact_staging(
    value: dict[str, Any],
    *,
    run_id: str,
    manifest: legacy.BoundFile,
    path: str,
    sha256: str,
) -> bool:
    return (
        value.get("schema") == "a90_v3403_absent_only_staging_adapter_v1"
        and value.get("status") == "PASS_ABSENT_ONLY_ROOTFS_STAGED"
        and value.get("run_id") == run_id
        and value.get("manifest_sha256") == manifest.sha256
        and value.get("rootfs")
        == {"device_path": path, "size": gc.IMAGE_SIZE, "sha256": sha256}
        and value.get("publication")
        == {
            "candidate_allowed": True,
            "primitive": "hardlink-no-clobber",
            "stage_dir_removed": True,
        }
        and value.get("safety")
        == {
            "flash": False,
            "mount": False,
            "reboot": False,
            "switch_root": False,
            "userdata_touched": False,
        }
    )


def _historical_evidence() -> tuple[dict[str, legacy.BoundFile], legacy.BoundFile]:
    selected_dir = PRIVATE_BASE / SELECTED_RUN_ID
    protected_dir = PRIVATE_BASE / PROTECTED_RUN_ID
    resident_dir = PRIVATE_BASE / RESIDENT_RUN_ID
    d1_dir = PRIVATE_BASE / D1_RUN_ID
    evidence = {
        "selected_prepared_manifest": _bound(
            selected_dir / "resident-prepared-manifest-install-v2.json"
        ),
        "selected_staging_result": _bound(selected_dir / "staging-live" / "result.json"),
        "selected_incident_result": _bound(selected_dir / "f1-live" / "result.json"),
        "selected_candidate_flashed": _bound(
            selected_dir / "f1-live" / "journal" / "0007-candidate-flashed.json"
        ),
        "selected_incident_closed": _bound(
            selected_dir / "f1-live" / "journal" / "0012-closed.json"
        ),
        "protected_prepared_manifest": _bound(
            protected_dir / "resident-prepared-manifest-install-v2.json"
        ),
        "protected_staging_result": _bound(
            protected_dir / "staging-live" / "result.json"
        ),
        "resident_manifest": _bound(resident_dir / "h5-existing-source-manifest.json"),
        "resident_result": _bound(resident_dir / "f1-live" / "result.json"),
        "resident_closed": _bound(
            resident_dir / "f1-live" / "journal" / "0009-closed.json"
        ),
        "d1_manifest": _bound(d1_dir / "manifest.json"),
        "d1_closed": _bound(d1_dir / "d1-live" / "0008-result.json"),
    }
    selected_manifest = _load(
        evidence["selected_prepared_manifest"], "selected prepared manifest"
    )
    protected_manifest = _load(
        evidence["protected_prepared_manifest"], "protected prepared manifest"
    )
    selected_staging = _load(
        evidence["selected_staging_result"], "selected staging result"
    )
    protected_staging = _load(
        evidence["protected_staging_result"], "protected staging result"
    )
    incident = _load(evidence["selected_incident_result"], "selected incident result")
    candidate_flashed = _load(
        evidence["selected_candidate_flashed"], "selected candidate-flashed"
    )
    incident_closed = _load(
        evidence["selected_incident_closed"], "selected incident close"
    )
    installed_manifest = _load(evidence["resident_manifest"], "H5 resident manifest")
    installed = _load(evidence["resident_result"], "H5 resident result")
    installed_closed = _load(evidence["resident_closed"], "H5 resident close")
    d1_closed = _load(evidence["d1_closed"], "H5 D1 close")

    selected_root = selected_manifest.get("debian_rootfs", {}).get("keyed_source", {})
    protected_root = protected_manifest.get("debian_rootfs", {}).get("keyed_source", {})
    rollback_value = protected_manifest.get("rollback_boot", {})
    installed_root = installed_manifest.get("debian_rootfs", {}).get("keyed_source", {})
    candidate = installed_manifest.get("candidate_boot", {})
    installed_rollback = installed_manifest.get("rollback_boot", {})
    installed_recovery = installed_manifest.get("recovery", {})
    d1_result = d1_closed.get("result", {})
    final_preflight = d1_result.get("final_preflight", {})
    final_health = final_preflight.get("resident_health", {})
    auto_status = d1_result.get("auto_handoff_status", {})
    if (
        selected_manifest.get("run_id") != SELECTED_RUN_ID
        or selected_root.get("device_path") != SELECTED_PATH
        or selected_root.get("local_path") != str(SELECTED_FIXED.host_preservation)
        or selected_root.get("size") != gc.IMAGE_SIZE
        or selected_root.get("sha256") != SELECTED_SHA256
        or selected_manifest.get("target", {}).get("recovery") != RECOVERY_PROFILE
        or not _exact_staging(
            selected_staging,
            run_id=SELECTED_RUN_ID,
            manifest=evidence["selected_prepared_manifest"],
            path=SELECTED_PATH,
            sha256=SELECTED_SHA256,
        )
        or incident.get("status")
        != "ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK"
        or incident.get("candidate_replay") is not False
        or incident.get("rollback_transfer_count") != 1
        or incident.get("final_health_restored") is not True
        or incident_closed.get("status")
        != "ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK"
        or incident_closed.get("candidate_replay") is not False
        or incident_closed.get("rollback_transfer_count") != 1
        or incident_closed.get("final_health_restored") is not True
        or candidate_flashed.get("candidate_transfer_count") != 1
        or candidate_flashed.get("candidate_replay") is not False
        or protected_manifest.get("run_id") != PROTECTED_RUN_ID
        or protected_root.get("device_path") != PROTECTED_PATH
        or protected_root.get("local_path")
        != str(PRIVATE_BASE / PROTECTED_RUN_ID / "phase3-network-ssh-v1-keyed.img")
        or protected_root.get("size") != gc.IMAGE_SIZE
        or protected_root.get("sha256") != PROTECTED_SHA256
        or protected_manifest.get("target", {}).get("recovery") != RECOVERY_PROFILE
        or not _exact_staging(
            protected_staging,
            run_id=PROTECTED_RUN_ID,
            manifest=evidence["protected_prepared_manifest"],
            path=PROTECTED_PATH,
            sha256=PROTECTED_SHA256,
        )
        or installed_manifest.get("run_id") != RESIDENT_RUN_ID
        or installed_root.get("device_path") != PROTECTED_PATH
        or installed_root.get("size") != gc.IMAGE_SIZE
        or installed_root.get("sha256") != PROTECTED_SHA256
        or candidate.get("partition") != "boot"
        or candidate.get("expected_version") != EXPECTED_VERSION
        or candidate.get("expected_build") != EXPECTED_BUILD
        or installed_rollback.get("partition") != "boot"
        or installed_rollback.get("size") != ROLLBACK_SIZE
        or installed_rollback.get("sha256") != ROLLBACK_SHA256
        or installed_recovery.get("physical_path")
        != "operator-attended Download or TWRP"
        or installed.get("status") != "PASS_A90_RESIDENT_INSTALLED"
        or installed.get("device_safety_state") != "RESIDENT_HEALTHY"
        or installed.get("candidate_transfer_count") != 1
        or installed.get("rollback_transfer_count") != 0
        or installed.get("candidate_replay") is not False
        or installed.get("rollback_required") is not False
        or installed_closed.get("status") != "PASS_A90_RESIDENT_INSTALLED"
        or installed_closed.get("candidate_transfer_count") != 1
        or installed_closed.get("rollback_transfer_count") != 0
        or installed_closed.get("candidate_replay") is not False
        or evidence["d1_manifest"].sha256 != D1_MANIFEST_SHA256
        or d1_closed.get("action") != "closed"
        or d1_closed.get("result_sha256") != legacy.json_sha256(d1_result)
        or d1_result.get("schema") != "a90-auto-handoff-benchmark-result-v2"
        or d1_result.get("terminal") != "NO_PROOF_OBSERVER_RESIDENT_HEALTHY"
        or d1_result.get("resident_healthy") is not True
        or d1_result.get("candidate_replay") is not False
        or d1_result.get("arm_dispatch_count") != 1
        or d1_result.get("reboot_dispatch_count") != 1
        or d1_result.get("work_cleanup", {}).get("dispatch_count") != 1
        or d1_result.get("payload_transfer") is not False
        or d1_result.get("partition_write") is not False
        or d1_result.get("flash") is not False
        or auto_status
        != {"binding": 1, "enable": 1, "latch": 1, "build": EXPECTED_BUILD}
        or final_health.get("facts", {}).get("fail") != 0
        or final_health.get("facts", {}).get("pstore_entries") != 0
        or rollback_value.get("partition") != "boot"
        or rollback_value.get("size") != ROLLBACK_SIZE
        or rollback_value.get("sha256") != ROLLBACK_SHA256
    ):
        raise engine.ContractError("H4/H5 historical evidence changed")

    d1_spec = resident.load_spec(evidence["d1_manifest"].path, D1_MANIFEST_SHA256)
    if (
        d1_spec.resident_run_id != RESIDENT_RUN_ID
        or d1_spec.candidate_version != EXPECTED_VERSION
        or d1_spec.candidate_build != EXPECTED_BUILD
        or d1_spec.remote_final != PROTECTED_PATH
        or d1_spec.remote_work != gc.WORK_PATH
        or d1_spec.rootfs.size != gc.IMAGE_SIZE
        or d1_spec.rootfs.sha256 != PROTECTED_SHA256
        or d1_spec.rollback.size != ROLLBACK_SIZE
        or d1_spec.rollback.sha256 != ROLLBACK_SHA256
    ):
        raise engine.ContractError("H5 D1 resident binding changed")

    selected_host = _bound(SELECTED_FIXED.host_preservation)
    protected_host = _bound(
        PRIVATE_BASE / PROTECTED_RUN_ID / "phase3-network-ssh-v1-keyed.img"
    )
    if (
        selected_host.size != gc.IMAGE_SIZE
        or selected_host.sha256 != SELECTED_SHA256
        or protected_host.size != gc.IMAGE_SIZE
        or protected_host.sha256 != PROTECTED_SHA256
    ):
        raise engine.ContractError("H4/H5 host preservation changed")
    rollback = _bound(Path(rollback_value["path"]))
    if rollback.size != ROLLBACK_SIZE or rollback.sha256 != ROLLBACK_SHA256:
        raise engine.ContractError("exact V2321 boot rollback changed")
    evidence["selected_host_preservation"] = selected_host
    evidence["protected_host_preservation"] = protected_host
    return evidence, rollback


def _health() -> dict[str, Any]:
    d1_manifest = PRIVATE_BASE / D1_RUN_ID / "manifest.json"
    spec = resident.load_spec(d1_manifest, D1_MANIFEST_SHA256)
    args = auto._effect_args()  # noqa: SLF001 - reviewed exact D1 read adapter
    health = resident.verify_resident_health_exact(
        spec,
        auto._f1_spec(spec),  # noqa: SLF001 - reviewed exact D1 projection
        args,
    )
    status_record, status = auto.require_auto_status(args, enable=1, latch=1)
    return {
        "version": EXPECTED_VERSION,
        "build": EXPECTED_BUILD,
        "proven": True,
        "resident_health": health,
        "auto_handoff_status_record": status_record,
        "auto_handoff_status": status,
    }


def _validate_inventory_health(value: Any) -> dict[str, Any]:
    engine._default_validate_inventory_health(value)  # type: ignore[attr-defined]
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "version",
            "build",
            "proven",
            "resident_health",
            "auto_handoff_status_record",
            "auto_handoff_status",
        }
    ):
        raise engine.ContractError("H5 inventory health shape changed")
    health = value.get("resident_health")
    if (
        not isinstance(health, dict)
        or set(health)
        != {
            "exact_bridge",
            "selected_realpath",
            "version",
            "status",
            "selftest",
            "facts",
        }
        or health.get("exact_bridge") is not True
        or not isinstance(health.get("selected_realpath"), str)
    ):
        raise engine.ContractError("H5 inventory resident health changed")
    receipts = {
        "version": health.get("version"),
        "status": health.get("status"),
        "selftest": health.get("selftest"),
    }
    try:
        facts = resident.staging.validate_native_health_receipts(
            receipts,
            expected_version=EXPECTED_VERSION,
            expected_build=EXPECTED_BUILD,
        )
        auto_record = auto.base.require_exact_f1_command_receipt(
            value.get("auto_handoff_status_record"),
            ["auto-handoff-status"],
            "inventory auto-handoff status",
        )
        parsed_status = auto.parse_auto_status(auto_record)
    except Exception as exc:
        raise engine.ContractError("H5 inventory health receipt changed") from exc
    required_status = {
        "binding": 1,
        "enable": 1,
        "latch": 1,
        "build": EXPECTED_BUILD,
    }
    if health.get("facts") != facts or parsed_status != required_status:
        raise engine.ContractError("H5 inventory health facts changed")
    if value.get("auto_handoff_status") != required_status:
        raise engine.ContractError("H5 inventory auto-handoff state changed")
    return value


def _validate_inventory_target_health(
    health: dict[str, Any],
    target: dict[str, Any],
) -> None:
    if health["resident_health"].get("selected_realpath") != target.get(
        "bridge_realpath"
    ):
        raise engine.ContractError("H5 inventory health bridge changed")


def _source_paths() -> dict[str, Path]:
    paths = engine._default_source_paths()  # type: ignore[attr-defined]
    paths.update(
        {
            "runner": RUNNER,
            "one_shot_reclaim_engine": Path(engine.__file__).resolve(),
            "h5_resident_health": Path(resident.__file__).resolve(),
            "h5_auto_status": Path(auto.__file__).resolve(),
        }
    )
    return paths


# Configure one process-local instance of the reviewed one-shot engine.  The
# original H3 entry point keeps its default values when invoked directly.
engine._default_source_paths = engine._source_paths  # type: ignore[attr-defined]  # noqa: SLF001
engine._default_validate_inventory_health = engine._validate_inventory_health  # type: ignore[attr-defined]  # noqa: SLF001
for name, value in {
    "RUNNER": RUNNER,
    "SCHEMA": SCHEMA,
    "STATUS": STATUS,
    "INVENTORY_SCHEMA": INVENTORY_SCHEMA,
    "RESULT_SCHEMA": RESULT_SCHEMA,
    "INTENT_SCHEMA": INTENT_SCHEMA,
    "DISPATCH_SCHEMA": DISPATCH_SCHEMA,
    "EFFECT_NOT_STARTED_SCHEMA": EFFECT_NOT_STARTED_SCHEMA,
    "CAPABILITY": CAPABILITY,
    "RUN_ID_RE": RUN_ID_RE,
    "CAPABILITY_EXPIRES_UTC": CAPABILITY_EXPIRES_UTC,
    "CAPABILITY_STATE_DIR": CAPABILITY_STATE_DIR,
    "PASS_OUTCOME": PASS_OUTCOME,
    "PASS_AMBIGUOUS_OUTCOME": PASS_AMBIGUOUS_OUTCOME,
    "DISPATCH_LABEL": "H4 source reclaim dispatch from healthy H5",
    "SELECTED_RUN_ID": SELECTED_RUN_ID,
    "SELECTED_PATH": SELECTED_PATH,
    "SELECTED_SHA256": SELECTED_SHA256,
    "PROTECTED_RUN_ID": PROTECTED_RUN_ID,
    "PROTECTED_PATH": PROTECTED_PATH,
    "PROTECTED_SHA256": PROTECTED_SHA256,
    "ROLLBACK_SHA256": ROLLBACK_SHA256,
    "ROLLBACK_SIZE": ROLLBACK_SIZE,
    "EXPECTED_VERSION": EXPECTED_VERSION,
    "EXPECTED_BUILD": EXPECTED_BUILD,
    "SELECTED_FIXED": SELECTED_FIXED,
    "PROTECTED_FIXED": PROTECTED_FIXED,
    "_historical_evidence": _historical_evidence,
    "_health": _health,
    "_validate_inventory_health": _validate_inventory_health,
    "_validate_inventory_target_health": _validate_inventory_target_health,
    "_source_paths": _source_paths,
}.items():
    setattr(engine, name, value)

ContractError = engine.ContractError
Spec = engine.Spec
capture_inventory = engine.capture_inventory
build_manifest = engine.build_manifest
load_spec = engine.load_spec
execute = engine.execute
resume = engine.resume
capability_dispatch_path = engine.capability_dispatch_path
parser = engine.parser
main = engine.main


if __name__ == "__main__":
    raise SystemExit(main())
