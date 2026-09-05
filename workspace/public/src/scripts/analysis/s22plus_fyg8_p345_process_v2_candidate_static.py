#!/usr/bin/env python3
"""P345 minimal host-only qualification static and promotion payloads."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(REVALIDATION))
import s22plus_fyg8_p345_artifact_identity as artifact
import s22plus_fyg8_p345_stock_process_v2_adapter as adapter
import s22plus_fyg8_p345_research_shell_observer as observer

SCHEMA = "s22plus_fyg8_p345_process_v2_candidate_static_v1"
VERDICT = "PASS_P345_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_SCHEMA = "s22plus_fyg8_p345_process_v2_run_manifest_v1"
CHECK_SCHEMA = "s22plus_fyg8_p345_process_v2_static_result_v1"
CHECK_VERDICT = "PASS_P345_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
RUN_ID = adapter.P345_RUN_ID_HEX
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
DEFAULT_OUTPUT = ROOT / "workspace/private/outputs/s22plus_fyg8_p345/process-v2-candidate-static-20260906-01.json"
SOURCE_FILES = {
    "p345_ap_byte_verifier": REVALIDATION / "s22plus_boot_verify.py",
    "p345_ap_receipt_helper": REVALIDATION / "s22plus_fyg8_p242_e2_stock_closure.py",
    "p345_artifact_identity": REVALIDATION / "s22plus_fyg8_p345_artifact_identity.py",
    "p345_stock_process_v2_adapter": REVALIDATION / "s22plus_fyg8_p345_stock_process_v2_adapter.py",
    "p345_research_shell_observer": REVALIDATION / "s22plus_fyg8_p345_research_shell_observer.py",
    "p345_research_shell_runtime": REVALIDATION / "s22plus_fyg8_p345_research_shell_runtime.py",
    "p345_readonly_child": REVALIDATION / "s22plus_fyg8_p345_readonly_child.py",
    "p345_readonly_child_c": ROOT / "workspace/public/src/native-init/s22plus_fyg8_p345_readonly_child.inc.c",
    "p345_shell_exchange": REVALIDATION / "s22plus_fyg8_research_shell_exchange.py",
    "p345_child_drain": REVALIDATION / "s22plus_fyg8_research_shell_child.py",
    "p345_stock_candidate_build": Path(__file__).with_name("s22plus_fyg8_p345_stock_candidate_build.py"),
    "p345_candidate_static": Path(__file__).resolve(),
}
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {"size": 23367721, "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"}

class StaticContractError(ValueError):
    pass

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}

def receipt(path: Path, maximum: int = 2 << 20) -> dict[str, Any]:
    payload = artifact.stable_bytes(path, str(path), maximum=maximum, nlink=1)
    return {"path": str(path.relative_to(ROOT)), **identity(payload)}

def source_receipts() -> dict[str, Any]:
    values = {key: receipt(path) for key, path in SOURCE_FILES.items()}
    values.update({"p345_carrier_" + key: receipt(ROOT / str(path))
                   for key, path in adapter.SOURCE_PATHS.items()})
    values["p345_carrier_parser"] = receipt(adapter.RAW_PARSER_SOURCE)
    values["p345_artifact_parent"] = receipt(artifact.SOURCE)
    values["p345_adapter_parent"] = receipt(adapter.SOURCE)
    return values

def build_result() -> dict[str, Any]:
    import s22plus_fyg8_p345_stock_candidate_build as builder
    built = builder.audit_existing(builder.DEFAULT_OUTPUT_ROOT)
    if built.get("schema") != builder.SCHEMA or built.get("run_id_hex") != RUN_ID or built.get("target") != TARGET:
        raise StaticContractError("P345 builder identity differs")
    if built.get("scope", {}).get("tier") != "H0" or built["scope"].get("device_contact") is not False:
        raise StaticContractError("P345 builder scope differs")
    phase = built["phase2"]
    candidate = copy.deepcopy(phase["candidate"])
    join = candidate["run_id_join"]
    if (candidate["a"] != candidate["b"] or candidate.get("byte_identical") is not True
        or candidate.get("ab_artifact_identity_equal") is not True
        or join.get("joined") is not True or any(join.get(key) != RUN_ID for key in
            ("run_id_hex", "image_run_id_hex", "init_run_id_hex"))
        or candidate["a"]["package"]["members"] != ["boot.img.lz4"]
        or candidate["a"]["ap_tar_md5"] in artifact.STALE_AP_IDENTITIES):
        raise StaticContractError("P345 actual A/B AP join differs")
    candidate.update({"image": candidate["fixed_image_identity"],
        "init": phase["userspace"]["a"]["init"], "child": phase["userspace"]["a"]["child"],
        "busybox": candidate["a"]["busybox"], "boot_only": True})
    artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    return {"schema": SCHEMA, "verdict": VERDICT, "target": TARGET, "run_id": RUN_ID,
        "predecessor_run_id": artifact.P344_PREDECESSOR_RUN_ID_HEX,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID, "profile": adapter.PROFILE,
        "authority_source": receipt(Path(__file__).resolve()),
        "builder_result": receipt(builder.DEFAULT_OUTPUT_ROOT / "result.json"),
        "candidate": candidate, "source_closure": source_receipts(),
        "rollback_ap": {"path": str(ROLLBACK_AP.relative_to(ROOT)), **ROLLBACK_IDENTITY},
        "auth_key": artifact.auth_key_identity(),
        "adapter": adapter.audit(), "qualification": adapter.acceptance_fixture()["qualification_commands"],
        "observer_binding": observer.audit_binding(),
        "safety": {"host_only": True, "device_contact": False, "live_authorized": False,
                   "later_action_lease_active": False, "mandatory_rollback": True}}

def validate_result(value: Any) -> dict[str, Any]:
    if canonical(value) != canonical(build_result()):
        raise StaticContractError("P345 static does not regenerate exactly")
    return value

validate_bound_result = validate_result

def promotion_payloads(static: dict[str, Any], static_receipt: dict[str, Any], *, run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Single exact promotion shape shared by preparer and offline verifier."""
    common = {"run_id": RUN_ID, "target": TARGET,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
        "decoder": adapter.DECODER_ID, "policy_id": adapter.POLICY_ID,
        "profile": adapter.PROFILE, "candidate_static": dict(static_receipt),
        "candidate_ap": static["candidate"]["a"]["ap_tar_md5"],
        "qualification": static["qualification"], "host_only": True,
        "device_contact": False, "live_authorized": False,
        "later_action_lease_active": False, "mandatory_rollback": True}
    return ({**common, "schema": RUN_SCHEMA, "promotion_run_id": run_id},
            {**common, "schema": CHECK_SCHEMA, "verdict": CHECK_VERDICT, "promotion_run_id": run_id})

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    value = build_result(); payload = canonical(value)
    if not args.audit_only:
        args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            directory = os.open(args.output.parent, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(directory)
            finally: os.close(directory)
        except BaseException:
            raise
    print(canonical({"verdict": VERDICT, "created": not args.audit_only, **identity(payload)}).decode())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
