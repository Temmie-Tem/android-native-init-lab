#!/usr/bin/env python3
"""Cross-check frozen Carrier selection against exact retained bytes host-only."""

from __future__ import annotations

import argparse
import ast
import binascii
import hashlib
import json
import os
import stat
import struct
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
PARENT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "historical-eud-index-sweep-20260817-02.json"
)
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "carrier-version-crosscheck-20260817-02.json"
)
SCHEMA = "s22plus_fyg8_p318_carrier_version_crosscheck_v2"
VERDICT = "PASS_P318_P310_P314_P317_CARRIER_VERSION_CROSSCHECK_H0_V2"
PARENT_SIZE = 34_667
PARENT_SHA256 = "0c8880ab4b3e28c2d4f287e158fc235972af6a8570004c006e247bfd44252a4e"
RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")
FROZEN_SOURCE_DIR = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/carrier-version-frozen-sources"
)
P232_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p232_e1_latest_stage_design.py"
)
P232_SOURCE_SIZE = 25_340
P232_SOURCE_SHA256 = "68d510ea79f72a53ffa2c60978387acf05deeb0515d657c85a4d2313ec84ba06"
P232_DEPENDENCY = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_retained_snapshot_model.py"
)
P232_DEPENDENCY_SIZE = 11_141
P232_DEPENDENCY_SHA256 = (
    "cafab0dfbe8df06984a307d9ae24841d78842db3126bcbbf7f3d1e14ad3c8cd5"
)

V1_LONG = b"S22E1L1|"
V1_UNSAT = b"S22E1U1|"
V1_SIZE = 45
V1_HEADER_SIZE = 25
V1_SLOT_SIZE = 10
V1_SLOT_BODY = struct.Struct("<BBBBH")
V1_SLOT_CRC_DOMAIN = b"S22PLUS-FYG8-P232-SLOT-V1\0"
V2_LONG = b"S22E1L2|"
V2_UNSAT = b"S22E1U2|"


class CrosscheckError(RuntimeError):
    """A frozen binding or exact retained Carrier relation differs."""


_BOUND_SOURCE = globals().get("_P318_CARRIER_CROSSCHECK_BOUND_SOURCE")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _file_identity(state: os.stat_result) -> tuple[int, ...]:
    return (
        state.st_dev,
        state.st_ino,
        state.st_mode,
        state.st_nlink,
        state.st_uid,
        state.st_gid,
        state.st_size,
        state.st_mtime_ns,
        state.st_ctime_ns,
    )


def stable_bytes(
    path: Path,
    *,
    label: str,
    maximum: int,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    required_mode: int | None = None,
    required_nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise CrosscheckError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_nlink < 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or _file_identity(before) != _file_identity(inside)
        or _file_identity(before) != _file_identity(after)
        or (expected_size is not None and len(payload) != expected_size)
        or (expected_sha256 is not None and sha256(payload) != expected_sha256)
        or (required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode)
        or (required_nlink is not None and before.st_nlink != required_nlink)
    ):
        raise CrosscheckError(f"{label} identity differs")
    return payload


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="carrier cross-check bootstrap", maximum=1 << 20)
    module = types.ModuleType("s22plus_fyg8_p318_carrier_version_crosscheck_bound")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P318_CARRIER_CROSSCHECK_BOUND_SOURCE"] = payload
    try:
        code = compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise CrosscheckError("carrier cross-check bound-source execution failed") from exc
    return module


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CrosscheckError("carrier cross-check JSON contains a duplicate key")
        value[key] = item
    return value


def strict_json(payload: bytes, label: str) -> Any:
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CrosscheckError(f"{label} contains {token}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CrosscheckError(f"{label} is not strict JSON") from exc


def _path(value: Any, path: tuple[str, ...], label: str) -> Any:
    current = value
    for key in path:
        if type(current) is not dict or key not in current:
            raise CrosscheckError(f"{label} path differs")
        current = current[key]
    return current


CAMPAIGNS: tuple[dict[str, Any], ...] = (
    {
        "name": "p310",
        "run": "p310-ready1-prepared-20260807-2",
        "prepared_size": 8240,
        "prepared_sha256": "a53b549b9775775840265c60e7528f6eea2dd3fb6b8bbd0e56122f7753e1ed6e",
        "manifest": "s22plus-fyg8-p310-process-v2-ready-1",
        "decoder": "s22plus_fyg8_p310_carrier_v2_p308_telemetry_v1",
        "policy_id": "e412fca023c34ad361a785e8c99a9084",
        "overlay": None,
        "selected_version": 2,
        "expected_v2_records": 1,
        "expect_match": True,
        "typed_evidence": {
            "size": 167696,
            "sha256": "3d3aa1b37c7e13e919852d15f70d7285f18d42a0cb371b3035ec3f3f0b7c25ed",
        },
        "frozen_source_file": "p310_device_action_f1_evidence_v2.py",
        "selection": {
            "mode": "source-contract-decoder",
            "overlay_constant": None,
            "decoder_symbol": "p310_source_contract",
        },
        "critical_functions": {
            "_selected_contract": {"size": 1557, "sha256": "488c664b9f648b64853de3df594f466afb740640f4ec71095540c759500d4ac3"},
            "_latest_stage_decoder": {"size": 211, "sha256": "f11121e381a2480ac7b3daf7501a91727238f6d3951117f105ca4eacd709b32f"},
            "_latest_stage_observation_decoder": {"size": 1051, "sha256": "743b2014dbfccacc0d57f5383caaf260a5060e4c913479eed097fedaa8264403"},
            "validate_acceptance": {"size": 10342, "sha256": "8a9f9e324d4dd8ebaca18083954503f0e9e0f9bb711021b8d39c25279514498d"},
            "classify_e1_latest_stage": {"size": 4554, "sha256": "1a0e75957d0539605bf5cb1031ff5e7415ac3bc8acfc5c05682b72b492c5399b"},
        },
    },
    {
        "name": "p311",
        "run": "s22plus-fyg8-p311-run-1",
        "prepared_size": 8286,
        "prepared_sha256": "a8cab5cbeda2b64e89b8984faccf31d5d670807d2288294a61dd197f2041486b",
        "manifest": "s22plus-fyg8-p311-process-v2-ready-1",
        "decoder": "s22plus_fyg8_p311_early_hsphy_clock_v1",
        "policy_id": "c9acfb253d9236c759b4c8f9c7bedad2",
        "overlay": "s22plus-fyg8-p311-early-hsphy-clock-observer-v1",
        "selected_version": 1,
        "expected_v2_records": 1,
        "expect_match": False,
        "typed_evidence": {
            "size": 174404,
            "sha256": "6231255b9c275da362e0cb51a1f76917dbdeb158ada66db84a67dcc754176c02",
        },
        "frozen_source_file": "p311_device_action_f1_evidence_v2.py",
        "selection": {
            "mode": "direct-return",
            "overlay_constant": "P311_OVERLAY_CONTRACT_ID",
            "decoder_symbol": "p311_decoder",
        },
        "critical_functions": {
            "_selected_contract": {"size": 1557, "sha256": "488c664b9f648b64853de3df594f466afb740640f4ec71095540c759500d4ac3"},
            "_latest_stage_decoder": {"size": 211, "sha256": "f11121e381a2480ac7b3daf7501a91727238f6d3951117f105ca4eacd709b32f"},
            "_latest_stage_observation_decoder": {"size": 1360, "sha256": "571465d017c8d078a4d353e8a08196888b5295cdcb0cd928a95868d9c252c776"},
            "validate_acceptance": {"size": 10342, "sha256": "8a9f9e324d4dd8ebaca18083954503f0e9e0f9bb711021b8d39c25279514498d"},
            "classify_e1_latest_stage": {"size": 4554, "sha256": "1a0e75957d0539605bf5cb1031ff5e7415ac3bc8acfc5c05682b72b492c5399b"},
        },
    },
    {
        "name": "p314",
        "run": "p314-ready1-prepared-20260810-2",
        "prepared_size": 9662,
        "prepared_sha256": "5c66a63d4e5ec493ad9d5281af6c240d9ace50919ff5bd6276d94e7d9095a84a",
        "manifest": "s22plus-fyg8-p314-process-v2-ready-1",
        "decoder": "s22plus_fyg8_p314_carrier_v2_source_normalized_cycle_v1",
        "policy_id": "04eaceb6a2edc7cf186252382dfcf81e",
        "overlay": "s22plus-fyg8-p314-source-normalized-cycle-carrier-v2-observer-v1",
        "selected_version": 2,
        "expected_v2_records": 1,
        "expect_match": True,
        "typed_evidence": {
            "size": 201932,
            "sha256": "fc074db27b244203e77da1bafe601d1d8959e1903f4dc261c4439bf1af3c2c7e",
        },
        "frozen_source_file": "p314_device_action_f1_evidence_v2.py",
        "selection": {
            "mode": "validated-assignment",
            "overlay_constant": "P314_OVERLAY_CONTRACT_ID",
            "decoder_symbol": "p314_decoder",
        },
        "critical_functions": {
            "_selected_contract": {"size": 1557, "sha256": "488c664b9f648b64853de3df594f466afb740640f4ec71095540c759500d4ac3"},
            "_latest_stage_decoder": {"size": 211, "sha256": "f11121e381a2480ac7b3daf7501a91727238f6d3951117f105ca4eacd709b32f"},
            "_latest_stage_observation_decoder": {"size": 2525, "sha256": "d3a6489fcaa690a900c2d5e1034be61883bcf2dbbb822fbb7d72c01424b7b4ad"},
            "_validate_decoder_carrier_authority": {"size": 1290, "sha256": "b7d3bd6a689af87415b3f126c15d3861a232095d402ec94ca35016aefcc14453"},
            "validate_acceptance": {"size": 10342, "sha256": "8a9f9e324d4dd8ebaca18083954503f0e9e0f9bb711021b8d39c25279514498d"},
            "classify_e1_latest_stage": {"size": 4668, "sha256": "8980236100ce7cec3ecad1f38b32a85b11fbf7d3362adf9a831615424cc92532"},
        },
    },
    {
        "name": "p317",
        "run": "f1-2026-08-12T165954582328Z-1786553994582372233",
        "prepared_size": 9725,
        "prepared_sha256": "08350b4629a57a90986e77001d5d6fddacb41b09aa74b16bf83a108fcb96de47",
        "manifest": "s22plus-fyg8-p317-process-v2-ready-1",
        "decoder": "s22plus_fyg8_p317_max77705_carrier_v2_envelope_v3",
        "policy_id": "326a3c6f740e028015526f862f880b58",
        "overlay": "s22plus-fyg8-p317-executability-max77705-envelope-v3",
        "selected_version": 2,
        "expected_v2_records": 3,
        "expect_match": True,
        "typed_evidence": {
            "size": 230280,
            "sha256": "167955461f512ff6dc18f8d6cf6c1e38d4ae0942aa531b7466136621ce779927",
        },
        "frozen_source_file": "p317_device_action_f1_evidence_v2.py",
        "selection": {
            "mode": "validated-assignment",
            "overlay_constant": "P317_MAX77705_OVERLAY_CONTRACT_ID",
            "decoder_symbol": "p317_max77705_decoder",
        },
        "critical_functions": {
            "_selected_contract": {"size": 1557, "sha256": "488c664b9f648b64853de3df594f466afb740640f4ec71095540c759500d4ac3"},
            "_latest_stage_decoder": {"size": 211, "sha256": "f11121e381a2480ac7b3daf7501a91727238f6d3951117f105ca4eacd709b32f"},
            "_latest_stage_observation_decoder": {"size": 3636, "sha256": "2815bc7f3c8f81c765d4c5cb9ca700233fa314cf1c06a9a8923635f87f9de582"},
            "_validate_decoder_carrier_authority": {"size": 1290, "sha256": "b7d3bd6a689af87415b3f126c15d3861a232095d402ec94ca35016aefcc14453"},
            "validate_acceptance": {"size": 10755, "sha256": "a1fadc7a2f6e54cbb8f477411a738942e56c62ca1fbbc9b46515e8b74081cfac"},
            "classify_e1_latest_stage": {"size": 4668, "sha256": "8980236100ce7cec3ecad1f38b32a85b11fbf7d3362adf9a831615424cc92532"},
        },
    },
)


def _exec_bound_module(name: str, payload: bytes, source: Path) -> Any:
    module = types.ModuleType(name)
    module.__file__ = str(source)
    module.__package__ = ""
    missing = object()
    previous = sys.modules.get(name, missing)
    sys.modules[name] = module
    try:
        code = compile(payload.decode("utf-8"), str(source), "exec", dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise CrosscheckError(f"bound Python authority {name} failed") from exc
    finally:
        if previous is missing:
            del sys.modules[name]
        else:
            sys.modules[name] = previous
    return module


def load_p232_authority() -> tuple[Any, dict[str, Any]]:
    dependency_payload = stable_bytes(
        P232_DEPENDENCY,
        label="P2.32 retained-snapshot dependency",
        maximum=1 << 20,
        expected_size=P232_DEPENDENCY_SIZE,
        expected_sha256=P232_DEPENDENCY_SHA256,
    )
    source_payload = stable_bytes(
        P232_SOURCE,
        label="P2.32 Carrier-v1 authority",
        maximum=1 << 20,
        expected_size=P232_SOURCE_SIZE,
        expected_sha256=P232_SOURCE_SHA256,
    )
    dependency_name = "s22plus_fyg8_retained_snapshot_model"
    dependency = _exec_bound_module(
        dependency_name,
        dependency_payload,
        P232_DEPENDENCY,
    )
    missing = object()
    previous_dependency = sys.modules.get(dependency_name, missing)
    previous_path = list(sys.path)
    sys.modules[dependency_name] = dependency
    try:
        authority = _exec_bound_module(
            "s22plus_fyg8_p232_e1_latest_stage_design_bound",
            source_payload,
            P232_SOURCE,
        )
    finally:
        sys.path[:] = previous_path
        if previous_dependency is missing:
            del sys.modules[dependency_name]
        else:
            sys.modules[dependency_name] = previous_dependency
    if (
        authority.LONG_FAMILY != V1_LONG
        or authority.UNSAT_FAMILY != V1_UNSAT
        or authority.LONG_RECORD_SIZE != V1_SIZE
        or authority.LONG_HEADER_SIZE != V1_HEADER_SIZE
        or authority.SLOT_SIZE != V1_SLOT_SIZE
        or authority.SLOT_BODY_STRUCT.format != V1_SLOT_BODY.format
        or stable_bytes(
            P232_SOURCE,
            label="post-execution P2.32 Carrier-v1 authority",
            maximum=1 << 20,
        )
        != source_payload
        or stable_bytes(
            P232_DEPENDENCY,
            label="post-execution P2.32 retained-snapshot dependency",
            maximum=1 << 20,
        )
        != dependency_payload
    ):
        raise CrosscheckError("P2.32 Carrier-v1 authority differs")
    return authority, {
        "design_source": identity(source_payload),
        "retained_snapshot_dependency": identity(dependency_payload),
        "role": "external Carrier-v1 ABI and positive-control authority",
    }


def _top_function(tree: ast.Module, name: str, label: str) -> ast.FunctionDef:
    found = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(found) != 1:
        raise CrosscheckError(f"{label} function {name} differs")
    return found[0]


def _function_payload(source: str, node: ast.FunctionDef, label: str) -> bytes:
    segment = ast.get_source_segment(source, node)
    if not isinstance(segment, str):
        raise CrosscheckError(f"{label} function source differs")
    return segment.encode("utf-8")


def _call_name(node: ast.Call) -> str | None:
    current: ast.expr = node.func
    parts: list[str] = []
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _call_count(node: ast.AST, name: str) -> int:
    return sum(
        isinstance(item, ast.Call) and _call_name(item) == name
        for item in ast.walk(node)
    )


def _overlay_branch(
    node: ast.FunctionDef,
    overlay_constant: str,
) -> ast.If | None:
    for item in ast.walk(node):
        if not isinstance(item, ast.If) or not isinstance(item.test, ast.Compare):
            continue
        test = item.test
        if (
            isinstance(test.left, ast.Name)
            and test.left.id == "userspace_overlay_contract_id"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Name)
            and test.comparators[0].id == overlay_constant
        ):
            return item
    return None


def audit_frozen_consumer_source(
    payload: bytes,
    config: dict[str, Any],
    *,
    enforce_identity: bool = True,
) -> dict[str, Any]:
    label = f"{config['name']} frozen evidence consumer"
    if enforce_identity and identity(payload) != config["typed_evidence"]:
        raise CrosscheckError(f"{label} identity differs")
    try:
        source = payload.decode("utf-8")
        tree = ast.parse(source, filename=config["frozen_source_file"])
    except (UnicodeError, SyntaxError) as exc:
        raise CrosscheckError(f"{label} is not exact Python") from exc
    functions: dict[str, dict[str, Any]] = {}
    nodes: dict[str, ast.FunctionDef] = {}
    for name, expected in config["critical_functions"].items():
        node = _top_function(tree, name, label)
        function_payload = _function_payload(source, node, label)
        actual = identity(function_payload)
        if actual != expected:
            raise CrosscheckError(f"{label} critical function {name} differs")
        nodes[name] = node
        functions[name] = actual

    selected_contract = _function_payload(
        source, nodes["_selected_contract"], label
    ).decode("utf-8")
    latest_decoder = _function_payload(
        source, nodes["_latest_stage_decoder"], label
    ).decode("utf-8")
    validate = _function_payload(
        source, nodes["validate_acceptance"], label
    ).decode("utf-8")
    classify = _function_payload(
        source, nodes["classify_e1_latest_stage"], label
    ).decode("utf-8")
    if (
        "if source_contract_id == P310_SOURCE_CONTRACT_ID:" not in selected_contract
        or "module=p310_source_contract" not in selected_contract
        or "return _selected_contract(source_contract_id, profile).decoder"
        not in latest_decoder
        or _call_count(nodes["validate_acceptance"], "_latest_stage_observation_decoder")
        != 1
        or _call_count(
            nodes["classify_e1_latest_stage"],
            "_latest_stage_observation_decoder",
        )
        != 1
        or _call_count(
            nodes["classify_e1_latest_stage"],
            "selected_decoder.classify_observation",
        )
        != 1
        or "item[\"decoder\"] != selected_decoder.DECODER_ID" not in validate
        or "item[\"policy_id\"] != selected_decoder.POLICY_ID" not in validate
        or "item[\"long_family_hex\"] != model.LONG_FAMILY.hex()" not in validate
        or "item[\"unsat_family_hex\"] != model.UNSAT_FAMILY.hex()" not in validate
        or "result[\"policy_id\"] = item[\"policy_id\"]" not in classify
        or "result[\"profile\"] = item[\"profile\"]" not in classify
        or "result[\"run_id\"] = item[\"run_id\"]" not in classify
    ):
        raise CrosscheckError(f"{label} acceptance-to-classification chain differs")

    selection = config["selection"]
    observation = nodes["_latest_stage_observation_decoder"]
    mode = selection["mode"]
    if mode == "source-contract-decoder":
        matching = False
        for item in observation.body:
            if (
                isinstance(item, ast.If)
                and isinstance(item.test, ast.Compare)
                and isinstance(item.test.left, ast.Name)
                and item.test.left.id == "userspace_overlay_contract_id"
                and len(item.test.ops) == 1
                and isinstance(item.test.ops[0], ast.Is)
                and len(item.test.comparators) == 1
                and isinstance(item.test.comparators[0], ast.Constant)
                and item.test.comparators[0].value is None
                and len(item.body) == 1
                and isinstance(item.body[0], ast.Return)
                and isinstance(item.body[0].value, ast.Call)
                and _call_name(item.body[0].value) == "_latest_stage_decoder"
            ):
                matching = True
        if not matching:
            raise CrosscheckError(f"{label} base decoder selection differs")
    else:
        branch = _overlay_branch(observation, selection["overlay_constant"])
        if branch is None:
            raise CrosscheckError(f"{label} overlay selection branch differs")
        if mode == "direct-return":
            matching = any(
                isinstance(item, ast.Return)
                and isinstance(item.value, ast.Name)
                and item.value.id == selection["decoder_symbol"]
                for item in branch.body
            )
        elif mode == "validated-assignment":
            matching = any(
                isinstance(item, ast.Assign)
                and len(item.targets) == 1
                and isinstance(item.targets[0], ast.Name)
                and item.targets[0].id == "selected"
                and isinstance(item.value, ast.Name)
                and item.value.id == selection["decoder_symbol"]
                for item in branch.body
            )
            matching = matching and _call_count(
                observation, "_validate_decoder_carrier_authority"
            ) == 1
            validator = _function_payload(
                source,
                nodes["_validate_decoder_carrier_authority"],
                label,
            ).decode("utf-8")
            matching = matching and all(
                fragment in validator
                for fragment in (
                    "source_decoder = _latest_stage_decoder(source_contract_id, profile)",
                    '"LONG_FAMILY",',
                    '"UNSAT_FAMILY",',
                    '"LONG_RECORD_SIZE",',
                    '"FORMAT_VERSION",',
                    "return selected_decoder",
                )
            )
        else:
            raise CrosscheckError(f"{label} selection mode differs")
        if not matching:
            raise CrosscheckError(f"{label} selected decoder differs")
    return {
        "source": identity(payload),
        "source_storage": {"mode": "0400", "nlink": 1},
        "critical_functions": functions,
        "selection_mode": mode,
        "selected_decoder_symbol": selection["decoder_symbol"],
        "acceptance_selects_decoder_family_and_policy": True,
        "classification_invokes_selected_decoder": True,
        "classification_preserves_policy_profile_run_id": True,
    }


def _crc32(payload: bytes) -> int:
    return binascii.crc32(payload) & 0xFFFFFFFF


def v1_positive_record() -> bytes:
    authority, _closure = load_p232_authority()
    try:
        record = authority.initialize_record("E2", RUN_ID)
        decoded = authority.decode_record(
            record,
            expected_profile="E2",
            expected_run_id=RUN_ID,
        )
    except authority.DesignError as exc:
        raise CrosscheckError("P2.32 Carrier-v1 positive control failed") from exc
    if (
        len(record) != V1_SIZE
        or decoded.get("profile") != "E2"
        or decoded.get("run_id") != RUN_ID.hex()
        or decoded.get("slot_status") != ["valid", "uncommitted"]
    ):
        raise CrosscheckError("P2.32 Carrier-v1 positive control differs")
    return record


def decode_v1_record(record: bytes) -> dict[str, Any]:
    if (
        len(record) != V1_SIZE
        or not record.startswith(V1_LONG)
        or record[8] != 0x13
        or record[9:25] != RUN_ID
    ):
        raise CrosscheckError("Carrier-v1 record identity differs")
    valid = 0
    statuses = []
    header = record[:V1_HEADER_SIZE]
    for slot_id in (0, 1):
        start = V1_HEADER_SIZE + slot_id * V1_SLOT_SIZE
        slot = record[start : start + V1_SLOT_SIZE]
        body = slot[: V1_SLOT_BODY.size]
        recorded = int.from_bytes(slot[V1_SLOT_BODY.size :], "little")
        if recorded == 0:
            statuses.append("uncommitted")
            continue
        expected = _crc32(V1_SLOT_CRC_DOMAIN + header + bytes([slot_id]) + body)
        generation, _stage, _outcome, _item, _detail = V1_SLOT_BODY.unpack(body)
        if recorded != expected or generation % 2 != slot_id:
            raise CrosscheckError("Carrier-v1 slot differs")
        valid += 1
        statuses.append("valid")
    if valid == 0:
        raise CrosscheckError("Carrier-v1 record has no committed slot")
    return {"valid_slot_count": valid, "slot_status": statuses}


def scan_v1(payload: bytes) -> list[dict[str, Any]]:
    records = []
    position = 0
    while True:
        position = payload.find(V1_LONG, position)
        if position < 0:
            break
        records.append({"offset": position, **decode_v1_record(payload[position : position + V1_SIZE])})
        position += 1
    return records


def _parent_campaigns(parent: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = parent.get("campaigns")
    if type(rows) is not list:
        raise CrosscheckError("parent campaign rows differ")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if type(row) is not dict or type(row.get("campaign")) is not str:
            raise CrosscheckError("parent campaign row differs")
        if row["campaign"] in result:
            raise CrosscheckError("parent campaign row is duplicated")
        result[row["campaign"]] = row
    return result


def audit_version_relation(
    *,
    selected_version: int,
    v2_offsets: list[int],
    v1_records: list[dict[str, Any]],
    expected_count: int,
    expect_match: bool,
    label: str,
) -> dict[str, Any]:
    selected_count = len(v1_records) if selected_version == 1 else len(v2_offsets)
    opposite_count = len(v2_offsets) if selected_version == 1 else len(v1_records)
    actual_version = 2 if v2_offsets and not v1_records else None
    version_match = actual_version == selected_version
    if (
        selected_version not in (1, 2)
        or actual_version != 2
        or version_match is not expect_match
        or (
            expect_match
            and (selected_count != expected_count or opposite_count != 0)
        )
        or (
            not expect_match
            and (selected_count != 0 or opposite_count != expected_count)
        )
    ):
        raise CrosscheckError(f"{label} Carrier-version cross-check differs")
    return {
        "selected_carrier_version": selected_version,
        "actual_retained_carrier_version": actual_version,
        "selected_parser_record_count": selected_count,
        "opposite_parser_record_count": opposite_count,
        "carrier_version_match": version_match,
    }


def audit_classification_binding(
    classification: Any,
    acceptance: dict[str, Any],
    *,
    expected_count: int,
    label: str,
) -> None:
    if (
        type(classification) is not dict
        or type(classification.get("long_record_count")) is not int
        or classification["long_record_count"] != expected_count
        or type(classification.get("family_count")) is not int
        or classification["family_count"] != expected_count
        or type(classification.get("exact_record_count")) is not int
        or classification["exact_record_count"] != expected_count
        or type(classification.get("policy_id")) is not str
        or classification["policy_id"] != acceptance["policy_id"]
        or type(classification.get("profile")) is not str
        or classification["profile"] != acceptance["profile"]
        or type(classification.get("run_id")) is not str
        or classification["run_id"] != acceptance["run_id"]
    ):
        raise CrosscheckError(f"{label} frozen classification binding differs")


def audit_campaign(config: dict[str, Any], parent_row: dict[str, Any]) -> dict[str, Any]:
    run = ROOT / "workspace/private/runs/device-action-f1-live-v2" / config["run"]
    prepared_payload = stable_bytes(
        run / "prepared.json",
        label=f"{config['name']} prepared binding",
        maximum=1 << 20,
        expected_size=config["prepared_size"],
        expected_sha256=config["prepared_sha256"],
    )
    prepared = strict_json(prepared_payload, f"{config['name']} prepared binding")
    if (
        type(prepared) is not dict
        or prepared.get("manifest_id") != config["manifest"]
        or type(prepared.get("approval_binding_sha256")) is not str
    ):
        raise CrosscheckError(f"{config['name']} prepared identity differs")
    acceptance = _path(
        prepared,
        ("approval_binding", "base_binding", "observation", "acceptance"),
        f"{config['name']} acceptance",
    )
    if type(acceptance) is not dict:
        raise CrosscheckError(f"{config['name']} acceptance differs")
    expected_long = V1_LONG if config["selected_version"] == 1 else V2_LONG
    expected_unsat = V1_UNSAT if config["selected_version"] == 1 else V2_UNSAT
    if (
        type(acceptance.get("decoder")) is not str
        or acceptance["decoder"] != config["decoder"]
        or type(acceptance.get("policy_id")) is not str
        or acceptance["policy_id"] != config["policy_id"]
        or type(acceptance.get("long_family_hex")) is not str
        or bytes.fromhex(acceptance["long_family_hex"]) != expected_long
        or type(acceptance.get("unsat_family_hex")) is not str
        or bytes.fromhex(acceptance["unsat_family_hex"]) != expected_unsat
        or type(acceptance.get("source_contract_id")) is not str
        or acceptance.get("source_contract_id")
        != "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
        or type(acceptance.get("profile")) is not str
        or acceptance.get("profile") != "E2"
        or type(acceptance.get("run_id")) is not str
        or acceptance.get("run_id") != RUN_ID.hex()
    ):
        raise CrosscheckError(f"{config['name']} frozen Carrier selection differs")
    overlay = acceptance.get("userspace_overlay_contract_id")
    if overlay != config["overlay"] or (
        config["overlay"] is None and "userspace_overlay_contract_id" in acceptance
    ):
        raise CrosscheckError(f"{config['name']} frozen overlay selection differs")

    typed = _path(
        prepared,
        ("execution_closure", "sources", "typed_evidence"),
        f"{config['name']} typed evidence",
    )
    expected_typed = {
        "path": str(
            (
                ROOT
                / "workspace/public/src/scripts/revalidation/"
                "device_action_f1_evidence_v2.py"
            ).absolute()
        ),
        **config["typed_evidence"],
    }
    if type(typed) is not dict or typed != expected_typed:
        raise CrosscheckError(f"{config['name']} frozen evidence source differs")
    frozen_source_payload = stable_bytes(
        FROZEN_SOURCE_DIR / config["frozen_source_file"],
        label=f"{config['name']} frozen evidence consumer",
        maximum=1 << 20,
        expected_size=config["typed_evidence"]["size"],
        expected_sha256=config["typed_evidence"]["sha256"],
        required_mode=0o400,
        required_nlink=1,
    )
    consumer = audit_frozen_consumer_source(frozen_source_payload, config)
    if (
        prepared["execution_closure"].get("sha256")
        != prepared["approval_binding"].get("execution_closure_sha256")
    ):
        raise CrosscheckError(f"{config['name']} execution closure differs")

    live_identity = parent_row.get("live_result")
    if type(live_identity) is not dict or set(live_identity) != {"sha256", "size"}:
        raise CrosscheckError(f"{config['name']} parent live-result identity differs")
    live_payload = stable_bytes(
        run / "live-result.json",
        label=f"{config['name']} live result",
        maximum=1 << 20,
        expected_size=live_identity["size"],
        expected_sha256=live_identity["sha256"],
    )
    live = strict_json(live_payload, f"{config['name']} live result")
    if (
        type(live) is not dict
        or live.get("schema") != "device_action_f1_live_result_v2"
        or live.get("manifest_id") != config["manifest"]
        or live.get("current_state") != "CLOSED"
        or live.get("approval_binding_sha256") != prepared["approval_binding_sha256"]
    ):
        raise CrosscheckError(f"{config['name']} live-result binding differs")
    classification = _path(
        live,
        ("live_state", "final_evidence", "observer", "classification"),
        f"{config['name']} live classification",
    )
    expected_count = config["expected_v2_records"]
    audit_classification_binding(
        classification,
        acceptance,
        expected_count=expected_count,
        label=config["name"],
    )

    reads = parent_row.get("final_observer_reads")
    records = parent_row.get("carrier_records")
    if type(reads) is not list or len(reads) != 2 or type(records) is not list:
        raise CrosscheckError(f"{config['name']} parent raw authority differs")
    raw_payloads = []
    for index, read in enumerate(reads, 1):
        if (
            type(read) is not dict
            or read.get("path")
            != str((run / f"rollback-observer-{index}.bin").relative_to(ROOT))
            or type(read.get("bytes")) is not int
            or read["bytes"] != 2_097_136
            or type(read.get("sha256")) is not str
            or read.get("read_to_eof") is not True
            or type(read.get("stderr_bytes")) is not int
            or read["stderr_bytes"] != 0
        ):
            raise CrosscheckError(f"{config['name']} parent raw receipt differs")
        raw_payloads.append(
            stable_bytes(
                ROOT / read["path"],
                label=f"{config['name']} retained raw {index}",
                maximum=2_097_136,
                expected_size=read["bytes"],
                expected_sha256=read["sha256"],
            )
        )
    if raw_payloads[0] != raw_payloads[1]:
        raise CrosscheckError(f"{config['name']} final reads differ")
    raw = raw_payloads[0]
    v2_offsets = []
    position = 0
    while True:
        position = raw.find(V2_LONG, position)
        if position < 0:
            break
        v2_offsets.append(position)
        position += 1
    expected_offsets = [row.get("offset") for row in records]
    if (
        v2_offsets != expected_offsets
        or len(v2_offsets) != expected_count
        or raw.count(V2_UNSAT) != 0
    ):
        raise CrosscheckError(f"{config['name']} Carrier-v2 raw count differs")
    v1_records = scan_v1(raw)
    if raw.count(V1_UNSAT) != 0:
        raise CrosscheckError(f"{config['name']} Carrier-v1 UNSAT is present")

    relation = audit_version_relation(
        selected_version=config["selected_version"],
        v2_offsets=v2_offsets,
        v1_records=v1_records,
        expected_count=expected_count,
        expect_match=config["expect_match"],
        label=config["name"],
    )
    return {
        "campaign": config["name"],
        "prepared": identity(prepared_payload),
        "live_result": identity(live_payload),
        "manifest_id": config["manifest"],
        "approval_binding_sha256": prepared["approval_binding_sha256"],
        "frozen_decoder": config["decoder"],
        "frozen_policy_id": config["policy_id"],
        "frozen_typed_evidence_source": typed,
        "frozen_consumer_execution_path": consumer,
        **relation,
        "final_read_identity": identity(raw),
        "v2_record_offsets": v2_offsets,
        "v1_record_offsets": [row["offset"] for row in v1_records],
    }


def build_receipt() -> dict[str, Any]:
    if type(_BOUND_SOURCE) is not bytes:
        raise CrosscheckError("carrier cross-check requires bound-source execution")
    if stable_bytes(AUDITOR, label="bound carrier cross-check", maximum=1 << 20) != _BOUND_SOURCE:
        raise CrosscheckError("executed carrier cross-check differs")
    parent_payload = stable_bytes(
        PARENT,
        label="reviewed historical EUD sweep receipt",
        maximum=1 << 20,
        expected_size=PARENT_SIZE,
        expected_sha256=PARENT_SHA256,
        required_mode=0o400,
        required_nlink=1,
    )
    parent = strict_json(parent_payload, "reviewed historical EUD sweep receipt")
    if (
        type(parent) is not dict
        or parent.get("schema") != "s22plus_fyg8_p318_historical_eud_index_sweep_v2"
        or parent.get("verdict")
        != "PASS_P318_HISTORICAL_EUD_INDEX_AND_RETAINED_SWEEP_H0_V2"
    ):
        raise CrosscheckError("parent historical EUD sweep differs")
    parent_rows = _parent_campaigns(parent)
    campaigns = [audit_campaign(config, parent_rows[config["name"]]) for config in CAMPAIGNS]
    p232_authority, p232_closure = load_p232_authority()
    try:
        fixture = p232_authority.initialize_record("E2", RUN_ID)
        p232_classification = p232_authority.classify_observation(
            b"",
            b"prefix" + fixture + b"suffix",
            expected_profile="E2",
            expected_run_id=RUN_ID,
        )
    except p232_authority.DesignError as exc:
        raise CrosscheckError("external Carrier-v1 control failed") from exc
    fixture_rows = scan_v1(b"prefix" + fixture + b"suffix")
    if (
        len(fixture_rows) != 1
        or fixture_rows[0]["offset"] != len(b"prefix")
        or p232_classification.get("long_record_count") != 1
        or p232_classification.get("integrity_issue") is not False
        or p232_classification.get("records", [{}])[0].get("observer_offset")
        != len(b"prefix")
        or fixture_rows[0].get("slot_status")
        != p232_classification["records"][0].get("slot_status")
    ):
        raise CrosscheckError("Carrier-v1 positive control differs")
    by_name = {row["campaign"]: row for row in campaigns}
    if (
        by_name["p311"]["carrier_version_match"] is not False
        or by_name["p311"]["selected_parser_record_count"] != 0
        or by_name["p311"]["opposite_parser_record_count"] != 1
        or any(
            by_name[name]["carrier_version_match"] is not True
            or by_name[name]["opposite_parser_record_count"] != 0
            for name in ("p310", "p314", "p317")
        )
    ):
        raise CrosscheckError("Carrier-version result partition differs")
    receipt = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "auditor": identity(_BOUND_SOURCE),
        "parent_historical_sweep": identity(parent_payload),
        "campaigns": campaigns,
        "controls": {
            "p311_known_mismatch_detected": True,
            "p232_external_v1_authority": p232_closure,
            "p232_external_v1_fixture": identity(fixture),
            "p232_external_decoder_record_count": 1,
            "v1_parser_positive_control_count": 1,
            "local_v1_scanner_agrees_with_external_authority": True,
        },
        "conclusion": {
            "p310_p314_p317_carrier_version_agreement_audited": True,
            "historical_executed_consumer_selection_audited": True,
            "p310_p314_p317_selected_v2_actual_v2": True,
            "p310_p314_p317_opposite_v1_record_count": 0,
            "p311_selected_v1_actual_v2_mismatch_detected": True,
            "new_campaign_reclassifications": 0,
            "carrier_version_mismatch_exemption_supported_for": [
                "p310", "p314", "p317"
            ],
        },
        "scope": {
            "host_only": True,
            "device_contact": False,
            "adb_commands": 0,
            "usb_actions": 0,
            "odin_invocations": 0,
            "candidate_transfers": 0,
            "rollback_transfers": 0,
            "recovery_actions": 0,
            "replay": False,
            "live_authority_created": False,
        },
    }
    if stable_bytes(AUDITOR, label="post-run carrier cross-check", maximum=1 << 20) != _BOUND_SOURCE:
        raise CrosscheckError("carrier cross-check changed during execution")
    return receipt


def encode_receipt(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        try:
            amount = os.write(fd, payload[offset:])
        except InterruptedError:
            continue
        if amount <= 0:
            raise CrosscheckError("carrier cross-check receipt write did not progress")
        offset += amount


def write_receipt(value: dict[str, Any]) -> None:
    payload = encode_receipt(value)
    OUTPUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        existing = stable_bytes(
            OUTPUT,
            label="carrier cross-check receipt",
            maximum=1 << 20,
            expected_size=len(payload),
            expected_sha256=sha256(payload),
            required_mode=0o400,
            required_nlink=1,
        )
        if existing != payload:
            raise CrosscheckError("carrier cross-check receipt differs")
        return
    fd = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o400)
    try:
        os.fchmod(fd, 0o400)
        _write_all(fd, payload)
        os.fsync(fd)
        state = os.fstat(fd)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != 0o400
            or state.st_nlink != 1
            or state.st_size != len(payload)
        ):
            raise CrosscheckError("carrier cross-check receipt publication differs")
    finally:
        os.close(fd)
    directory = os.open(OUTPUT.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    stable_bytes(
        OUTPUT,
        label="carrier cross-check receipt",
        maximum=1 << 20,
        expected_size=len(payload),
        expected_sha256=sha256(payload),
        required_mode=0o400,
        required_nlink=1,
    )


def main() -> int:
    if type(_BOUND_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit-only", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    value = build_receipt()
    if args.write:
        write_receipt(value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
