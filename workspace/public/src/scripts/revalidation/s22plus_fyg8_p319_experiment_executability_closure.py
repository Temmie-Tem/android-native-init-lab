#!/usr/bin/env python3
"""Qualify the P3.19 stock candidate's Process-v2 executability closure.

This is an H0-only, candidate-specific closure.  It revalidates the exact
P3.17 fixed-point authority only for the unchanged QUP/I2C upstream graph and
then adds the stock MAX77705 MFD/PDIC instantiation chain.  The P3.17
diagnostic driver is deliberately not a P3.19 root or provider.  Runtime
witnesses are recorded as required future outputs; this module never treats
their absence as a successful preflight fact and never creates live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[5]
PRIVATE = ROOT / "workspace/private"

SCHEMA = "s22plus_fyg8_p319_experiment_executability_closure_v1"
VERDICT = "PASS_P319_EXPERIMENT_EXECUTABILITY_CLOSURE_H0"
BLOCKED_VERDICT = "BLOCKED_P319_EXPERIMENT_EXECUTABILITY_CLOSURE_H0"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}

FAMILY_FW = "FW_DEVLINK_DT_SUPPLIER_CLOSURE"
FAMILY_INST = "DEVICE_INSTANTIATION_CLOSURE"
FAMILY_DRIVER = "DRIVER_CONSUMED_DT_REFERENCE_CLOSURE"
FAMILIES = (FAMILY_FW, FAMILY_INST, FAMILY_DRIVER)

P317_WRAPPER = "/soc/qcom,qupv3_0_geni_se@9c0000"
P317_I2C = "/soc/i2c@994000"
P317_DIAGNOSTIC_PARENT = "/soc/i2c@994000/max77705@66"
P319_MFD = "i2c:994000.i2c-0066; compatible=maxim,max77705"
P319_PDIC = "platform-child:max77705-usbc"
P319_ROOTS = (P317_WRAPPER, P317_I2C, P319_MFD, P319_PDIC)
P319_FORBIDDEN_DIAGNOSTIC = (
    P317_DIAGNOSTIC_PARENT,
    "s22plus_max77705_mux_diag",
    "s22plus_max77705_mux_diag.ko",
)

P317_FIXED_POINT = PRIVATE / (
    "outputs/s22plus_fyg8_p317/executability-fixed-point-20260812-01.json"
)
P317_FW = PRIVATE / (
    "outputs/s22plus_fyg8_p317/fw-devlink-contract-20260812-01.json"
)
P317_MUST_BIND = PRIVATE / (
    "outputs/s22plus_fyg8_p317/must-bind-claim-contract-20260812-01.json"
)
P319_IRQ = PRIVATE / (
    "outputs/s22plus_fyg8_p319/max77705-irq-dt-audit-20260820-06/result.json"
)
P319_PDIC_AUDIT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-pdic-probe-boundary-20260820-05/result.json"
)
P319_PLAN = PRIVATE / (
    "outputs/s22plus_fyg8_p319/successor-module-plan-v2-20260820-02/result.json"
)
P319_MATERIALIZATION = PRIVATE / (
    "outputs/s22plus_fyg8_p319/"
    "successor-module-materialization-v1-20260820-04/result.json"
)
P319_QUALIFICATION_INTENT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-qualification-v1-20260821-08/intent.json"
)
P319_QUALIFICATION = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-qualification-v1-20260821-08/qualification.json"
)
PROCESS_CONTRACT = ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
TARGET_CONTRACT = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
AUDITOR = Path(__file__).resolve()

MATERIALIZED_ROOT = P319_MATERIALIZATION.parent
MODULE_ROOT = MATERIALIZED_ROOT / "module-bytes"
I2C_MODULE = PRIVATE / (
    "outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-32/module-bytes/"
    "i2c-msm-geni.ko"
)
IRQ_INPUT_ROOT = P319_IRQ.parent.parent / "max77705-irq-dt-audit-20260820-05/inputs"
KERNEL = PRIVATE / (
    "work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel"
)
DTBO = PRIVATE / (
    "inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/dtbo.img"
)
DT_SOURCE = IRQ_INPUT_ROOT / "g0q_kor_singlex_w00_r12.dts"
MFD_SOURCE = KERNEL / "drivers/mfd/maxim/max77705.c"
MFD_HEADER = KERNEL / "include/linux/mfd/max77705.h"
PDIC_SOURCE = KERNEL / "drivers/usb/typec/maxim/max77705_usbc.c"
MUIC_SOURCE = KERNEL / "drivers/usb/typec/maxim/max77705-muic.c"

EXPECTED_IDS = {
    "p317_fixed_point": {"size": 496664, "sha256": "67042a70a6e023a5ea3382d4fd179fd04b6f0c111ff9430d5e5a1b9410b2a657"},
    "p317_fw": {"size": 14680, "sha256": "88b8247e48a1945c8a5f31544336f942c32f9604787e0cd46de0ba5f70f17609"},
    "p317_must_bind": {"size": 15712, "sha256": "bbb066b0dc8a7492db407a22f9cb1417773ee049a69b232a2ebc02d234418263"},
    "p319_irq": {"size": 16818, "sha256": "48c389e4e9afe369238359c48baba3057680bd1d06bebe76fdd7f254591ef3c6"},
    "p319_pdic": {"size": 15563, "sha256": "7744d9e7c5d76148ad4038f59531dd686d6e8b3a1327e78206ae5c6ad4390025"},
    "p319_plan": {"size": 14833, "sha256": "d8c12396e241e387fe342803eca4537b6728dcda7fb901aa8dc7e591d4745cb2"},
    "p319_materialization": {"size": 10658, "sha256": "8b8c1f5afd8c02693901d3552c221bcc73bafa2543c77dfff4954bdba188f6b5"},
    "p319_intent": {"size": 107147, "sha256": "2e0d67cfecd752f4ebe76ab3176969dc83eec7117e59cae1b5a7c3f18e0c9226"},
    "p319_qualification": {"size": 109705, "sha256": "0b49969f730c4af374a20cac6c3eef4b0a0dcbf136d9ce30eefc4ac7546d5738"},
    "p317_source": {"size": 42902, "sha256": "cdc99e05884b2bd127a36536e349b005322c049e36e9f8582f0f53a3530088f8"},
    "process_contract": {"size": 36163, "sha256": "26d9c8110e19ca4dba09418d07350cd051167423387a684f8deebf76c0843af1"},
    "target_contract": {"size": 14926, "sha256": "e429c80c86f8b122443e56a8d8d3b01605aabb320d2d5ef5e3eb9fcc666a55e0"},
}

# The registry is a restrictive additive change to the binding common
# Process-v2 contract.  Keep the predecessor identity here as provenance: a
# bare replacement of the current hash would make the contract repin
# indistinguishable from an unreviewed drift.
PROCESS_CONTRACT_REPIN = {
    "schema": "s22plus_fyg8_p319_process_v2_contract_repin_v1",
    "change": "restrictive_additive_common_contract",
    "old": {
        "source_commit": "53af56674a7d818086d6ca2297eb903c69ef8f66",
        "size": 33498,
        "sha256": "72f1eb6115872683af6a374b37267193c9c730a51698e5adf30b328b75b68d9b",
    },
    "new": {
        "source_commit": "10cf4c25e0c7d97422b683ef925f9e18b15ace6c",
        "size": 36163,
        "sha256": "26d9c8110e19ca4dba09418d07350cd051167423387a684f8deebf76c0843af1",
    },
    "delta": {"added_lines": 41, "removed_lines": 0, "added_bytes": 2665},
    "independent_review": {
        "status": "INDEPENDENTLY_REVIEWED_H0",
        "review_commit": "eaff1d48d32550674d12d2fa6b456444a60d20ee",
        "scope": "global consumed-candidate registry and common Process-v2 contract addition",
    },
    "authority_expanded": False,
    "ready_or_live_authority_granted": False,
}

MODULE_SPECS = {
    "i2c-msm-geni.ko": {"index": 69, "size": 122248, "sha256": "c90278d222632b6e7f93f45aa40fae18668d9356c4bef374f2899b2263ead9be", "role": "stock_i2c_provider"},
    "spu_verify.ko": {"index": 70, "size": 18608, "sha256": "d670a944288dffcc5fbf67a76550dc8a746665113f6ee4354521e482489f4b84", "role": "link_only_closure"},
    "mfd_max77705.ko": {"index": 71, "size": 125840, "sha256": "26f238730604789293db237b2bcdc4d44c5f63c263e4298f6e8e28b85d0f6f94", "role": "stock_mfd_parent"},
    "pdic_max77705.ko": {"index": 72, "size": 423456, "sha256": "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db", "role": "stock_pdic_child"},
    "dwc3-msm.ko": {"index": 59, "size": 308624, "sha256": "8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1", "role": "stock_dwc3_provider"},
}

SOURCE_TOKENS = {
    "mfd": (
        "static struct mfd_cell max77705_devs[]",
        '.name = "max77705-usbc"',
        "mfd_add_devices(max77705->dev, -1, max77705_devs",
        "max77705_i2c_probe",
    ),
    "pdic": (
        "static struct platform_driver max77705_usbc_driver",
        '.name = "max77705-usbc"',
        "max77705_usbc_probe",
        "max77705_muic_probe",
        "max77705->cc_booting_complete = 1",
        "max77705_usbc_umask_irq(usbc_data)",
    ),
}

RUNTIME_WITNESS_SPECS = {
    "module_results": "one durable finit_module result for i2c-msm-geni, mfd_max77705 and pdic_max77705",
    "vbusdet_irq_tuple": "the source-emitted uiadc/chgtyp/dcdtmo/vbadc/vbusdet tuple with VBUSDET gate outcome",
    "initial_status_classification_probe": "initial USBC1/USBC2/BC status, classification, and probe completion in source order",
    "retained_carrier": "the exact retained Carrier record decoded by the P3.19 stock adapter",
}

# These counts are derived from the exact bound P3.17 receipt plus the three
# P3.19 stock edges below.  Pinning them prevents a root-only replay from
# masquerading as a converged closure when a relation extractor is weakened.
EXPECTED_UPSTREAM_EDGE_COUNT = 44
EXPECTED_CANDIDATE_EDGE_COUNT = 3
EXPECTED_NODE_COUNT = 22
EXPECTED_DEDUPLICATED_EDGE_COUNT = 47
EXPECTED_FAMILY_COUNTS = {
    FAMILY_FW: 25,
    FAMILY_INST: 21,
    FAMILY_DRIVER: 1,
}


class AuditError(RuntimeError):
    """An exact source, receipt, relation, or plan contract differs."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": sha256(data)}


def validate_process_contract_repin(
    process: bytes,
    repin: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind the current contract to its reviewed restrictive additive delta."""
    value = PROCESS_CONTRACT_REPIN if repin is None else repin
    expected_old = {
        "source_commit": "53af56674a7d818086d6ca2297eb903c69ef8f66",
        "size": 33498,
        "sha256": "72f1eb6115872683af6a374b37267193c9c730a51698e5adf30b328b75b68d9b",
    }
    expected_new = {
        "source_commit": "10cf4c25e0c7d97422b683ef925f9e18b15ace6c",
        "size": 36163,
        "sha256": "26d9c8110e19ca4dba09418d07350cd051167423387a684f8deebf76c0843af1",
    }
    if not isinstance(value, Mapping) or value.get("schema") != PROCESS_CONTRACT_REPIN["schema"]:
        raise AuditError("Process-v2 contract repin schema differs")
    if value.get("change") != "restrictive_additive_common_contract":
        raise AuditError("Process-v2 contract repin is not restrictive/additive")
    if value.get("old") != expected_old or value.get("new") != expected_new:
        raise AuditError("Process-v2 contract repin old/new provenance differs")
    review = value.get("independent_review")
    if not isinstance(review, Mapping) or review.get("status") != "INDEPENDENTLY_REVIEWED_H0" or review.get("review_commit") != "eaff1d48d32550674d12d2fa6b456444a60d20ee":
        raise AuditError("Process-v2 contract repin review provenance differs")
    if value.get("authority_expanded") is not False or value.get("ready_or_live_authority_granted") is not False:
        raise AuditError("Process-v2 contract repin expands authority")
    try:
        text = process.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditError("Process-v2 contract is not UTF-8") from exc
    start_marker = b"### Global Consumed-Candidate Registry"
    end_marker = b"Rollback is a normal state-machine transition, not a new experiment."
    if process.count(start_marker) != 1 or process.count(end_marker) != 1:
        raise AuditError("Process-v2 registry section markers are ambiguous")
    start = process.find(start_marker)
    end = process.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0 or start == 0 or end <= start:
        raise AuditError("Process-v2 registry section is missing")
    if process[start - 1:start] != b"\n" or process[end - 1:end] != b"\n":
        raise AuditError("Process-v2 registry section is not line-delimited")
    section_bytes = process[start:end]
    if not section_bytes.endswith(b"\n\n"):
        raise AuditError("Process-v2 registry section boundary differs")
    section = section_bytes.decode("utf-8").splitlines()
    if len(section) != 41:
        raise AuditError("Process-v2 registry section line count differs")
    reconstructed_predecessor = process[:start] + process[end:]
    predecessor_identity = identity(reconstructed_predecessor)
    if predecessor_identity != {key: expected_old[key] for key in ("size", "sha256")}:
        raise AuditError("Process-v2 predecessor reconstruction differs")
    if identity(process) != {key: expected_new[key] for key in ("size", "sha256")}:
        raise AuditError("Process-v2 contract identity differs from reviewed successor")
    derived_delta = {
        "added_lines": len(section),
        "removed_lines": 0,
        "added_bytes": len(section_bytes),
    }
    if value.get("delta") != derived_delta:
        raise AuditError("Process-v2 contract repin delta differs")
    for token in (
        "CONSUMED_UNCERTAIN",
        "BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY",
        "never replays the candidate",
        "not ready, and grants no F1 or live authority",
        "independent review and fresh qualification",
    ):
        if token not in section_bytes.decode("utf-8"):
            raise AuditError(f"Process-v2 registry section lacks required guard: {token}")
    return dict(value)


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size, value.st_mtime_ns)


def stable_bytes(path: Path, label: str, *, expected: Mapping[str, Any] | None = None, maximum: int = 16 * 1024 * 1024, mode: int | None = None) -> bytes:
    try:
        before = path.lstat()
        resolved = path.resolve(strict=True)
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        raise AuditError(f"{label} unavailable: {path}") from exc
    if (resolved != path.resolve() or stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode)
            or len(data) != before.st_size or len(data) > maximum
            or _stat_identity(before) != _stat_identity(inside)
            or _stat_identity(before) != _stat_identity(after)
            or mode is not None and stat.S_IMODE(before.st_mode) != mode
            or expected is not None and identity(data) != dict(expected)):
        raise AuditError(f"{label} identity differs: {path}")
    return data


def strict_object(data: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise AuditError(f"{label} has duplicate JSON key: {key}")
            value[key] = item
        return value

    try:
        value = json.loads(data, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(AuditError(f"{label} has non-finite value: {x}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    return value


def _edge_target(edge: Mapping[str, Any]) -> str | None:
    for key in ("owner", "instantiator", "dependency"):
        value = edge.get(key)
        if isinstance(value, str):
            return value
    return None


def _contains_forbidden(value: Any) -> bool:
    if isinstance(value, str):
        return any(token in value for token in P319_FORBIDDEN_DIAGNOSTIC)
    if isinstance(value, Mapping):
        return any(_contains_forbidden(key) or _contains_forbidden(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden(item) for item in value)
    return False


def _require_tokens(text: str, tokens: Iterable[str], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise AuditError(f"{label} source tokens missing: {missing}")


def derive_mfd_driver_identity(mfd_text: str, header_text: str) -> dict[str, str]:
    """Derive the actual I2C driver name and probe witness from source."""
    macro = re.search(r'^\s*#define\s+MFD_DEV_NAME\s+"([^"]+)"\s*$', header_text, re.MULTILINE)
    if macro is None:
        raise AuditError("MFD_DEV_NAME definition is absent")
    driver = re.search(
        r"static\s+struct\s+i2c_driver\s+max77705_i2c_driver\s*=\s*\{(.*?)"
        r"\n\};\s*\n\s*static\s+int\s+__init\s+max77705_i2c_init",
        mfd_text,
        re.DOTALL,
    )
    if driver is None:
        raise AuditError("max77705_i2c_driver definition is absent")
    body = driver.group(1)
    name_expr = re.search(r"\.driver\s*=\s*\{.*?\.name\s*=\s*([^,\n]+)", body, re.DOTALL)
    probe_expr = re.search(r"\.probe\s*=\s*([^,\n]+)", body)
    if name_expr is None or name_expr.group(1).strip() != "MFD_DEV_NAME":
        raise AuditError("MFD I2C driver name is not bound to MFD_DEV_NAME")
    if probe_expr is None or probe_expr.group(1).strip() != "max77705_i2c_probe":
        raise AuditError("MFD I2C probe is not max77705_i2c_probe")
    return {
        "driver_name": macro.group(1),
        "driver_name_macro": "MFD_DEV_NAME",
        "probe_function": "max77705_i2c_probe",
        "bind_witness": "max77705_i2c_driver.driver.name <- MFD_DEV_NAME",
    }


def validate_stock_source_texts(mfd_text: str, header_text: str, pdic_text: str) -> dict[str, str]:
    """Validate source seams separately so in-memory mutation tests are real."""
    _require_tokens(mfd_text, SOURCE_TOKENS["mfd"], "P3.19 MFD")
    _require_tokens(pdic_text, SOURCE_TOKENS["pdic"], "P3.19 PDIC")
    return derive_mfd_driver_identity(mfd_text, header_text)


def load_exact_authority() -> dict[str, Any]:
    paths = {
        "p317_fixed_point": P317_FIXED_POINT,
        "p317_fw": P317_FW,
        "p317_must_bind": P317_MUST_BIND,
        "p319_irq": P319_IRQ,
        "p319_pdic": P319_PDIC_AUDIT,
        "p319_plan": P319_PLAN,
        "p319_materialization": P319_MATERIALIZATION,
        "p319_intent": P319_QUALIFICATION_INTENT,
        "p319_qualification": P319_QUALIFICATION,
    }
    data: dict[str, Any] = {}
    raw: dict[str, bytes] = {}
    for name, path in paths.items():
        payload = stable_bytes(path, name, expected=EXPECTED_IDS[name], mode=0o400 if name.startswith("p319_") else None, maximum=16 * 1024 * 1024)
        raw[name] = payload
        data[name] = strict_object(payload, name)
    source = stable_bytes(AUDITOR.parent / "s22plus_fyg8_p317_executability_fixed_point.py", "P317 extractor source", expected=EXPECTED_IDS["p317_source"], maximum=128 * 1024)
    process = stable_bytes(PROCESS_CONTRACT, "Process-v2 contract", maximum=2 * 1024 * 1024)
    target = stable_bytes(TARGET_CONTRACT, "S22+ target contract", maximum=128 * 1024)
    process_repin = validate_process_contract_repin(process)
    if identity(target) != EXPECTED_IDS["target_contract"]:
        raise AuditError("S22+ target contract identity differs")
    _require_tokens(process.decode("utf-8"), ("EXPERIMENT_EXECUTABILITY_CLOSURE", "S[n+1]", *FAMILIES, "NO_PROOF_OBSERVER", "NO_PROOF_EXPERIMENT_PRECONDITION"), "Process-v2")
    data["_raw"] = raw
    data["_source_receipt"] = identity(source)
    data["_contract_receipts"] = {
        "process_v2": identity(process),
        "process_v2_repin": process_repin,
        "target": identity(target),
    }
    return data


def validate_p317_authority(p317: Mapping[str, Any], p317_fw: Mapping[str, Any], p317_must: Mapping[str, Any]) -> None:
    if p317.get("schema") != "s22plus_fyg8_p317_executability_fixed_point_v1" or p317.get("status") != "CANDIDATE_NOT_READY":
        raise AuditError("P3.17 fixed-point receipt schema/status differs")
    fixed = p317.get("fixed_point")
    if not isinstance(fixed, Mapping) or tuple(fixed.get("relationship_families", ())) != FAMILIES:
        raise AuditError("P3.17 registered relation families differ")
    if tuple(fixed.get("roots", ())) != (P317_WRAPPER, P317_I2C, P317_DIAGNOSTIC_PARENT):
        raise AuditError("P3.17 predecessor roots differ")
    if fixed.get("converged") is not True or fixed.get("every_frontier_node_evaluated_by_every_family") is not True:
        raise AuditError("P3.17 fixed-point did not converge with all-family evaluation")
    if p317_fw.get("schema") != "s22plus_fyg8_p317_fw_devlink_contract_v1" or p317_must.get("schema") != "s22plus_fyg8_p317_must_bind_claim_contract_v1":
        raise AuditError("P3.17 upstream authority schema differs")
    iterations = fixed.get("iterations")
    edges = fixed.get("deduplicated_edges")
    if not isinstance(iterations, list) or not iterations or not isinstance(edges, list):
        raise AuditError("P3.17 fixed-point receipt lacks iterations/edges")
    seen_keys: set[tuple[str, str, str | None]] = set()
    for item in iterations:
        frontier = item.get("frontier")
        evaluations = item.get("family_evaluations")
        emitted = item.get("new_nodes")
        if not isinstance(frontier, list) or frontier != sorted(set(frontier)) or not isinstance(evaluations, list) or not isinstance(emitted, list) or emitted != sorted(set(emitted)):
            raise AuditError("P3.17 fixed-point frontier/emission grammar differs")
        pairs = {(row.get("node"), row.get("family")) for row in evaluations}
        if len(pairs) != len(frontier) * len(FAMILIES) or any((node, family) not in pairs for node in frontier for family in FAMILIES):
            raise AuditError("P3.17 fixed-point skipped a family or frontier node")
        for edge in item.get("raw_edges", ()):
            if edge.get("family") not in FAMILIES or edge.get("consumer") not in frontier:
                raise AuditError("P3.17 edge is unclassified or outside its frontier")
    for edge in edges:
        key = (str(edge.get("family")), str(edge.get("consumer")), _edge_target(edge))
        if key in seen_keys or edge.get("family") not in FAMILIES:
            raise AuditError("P3.17 deduplicated edge identity differs")
        seen_keys.add(key)


def _upstream_edges(p317: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixed = p317["fixed_point"]
    all_edges = fixed["deduplicated_edges"]
    seeds = {P317_WRAPPER, P317_I2C}
    edges: list[dict[str, Any]] = []
    seen = set(seeds)
    while True:
        changed = False
        for original in all_edges:
            consumer = original.get("consumer")
            target = _edge_target(original)
            if consumer not in seen or target is None:
                continue
            if target == P317_DIAGNOSTIC_PARENT:
                continue
            if target.startswith("/") and target not in seen:
                seen.add(target)
                changed = True
            if original not in edges:
                edges.append(dict(original))
        if not changed:
            break
    if any(_contains_forbidden(edge) for edge in edges):
        raise AuditError("P3.17 diagnostic-driver edge leaked into P3.19 upstream projection")
    if not edges or not any(edge.get("family") == FAMILY_DRIVER for edge in edges) or not any(edge.get("family") == FAMILY_FW for edge in edges) or not any(edge.get("family") == FAMILY_INST for edge in edges):
        raise AuditError("P3.17 upstream projection does not cover all three families")
    return edges


def _regenerate_p317_receipt(expected_bytes: bytes) -> dict[str, Any]:
    """Run the exact P3.17 extractor and require byte identity before reuse."""
    source_path = AUDITOR.parent / "s22plus_fyg8_p317_executability_fixed_point.py"
    source = stable_bytes(source_path, "P317 extractor source", expected=EXPECTED_IDS["p317_source"], maximum=128 * 1024)
    module_name = "s22plus_fyg8_p317_executability_fixed_point_bound_for_p319"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        raise AuditError("P3.17 extractor cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.path.insert(0, str(source_path.parent))
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        root = ROOT
        metadata = module.module_plan.load_metadata(root / module.DEFAULT_METADATA)
        regenerated = module.build_contract(
            extractor_data=source,
            dtbo_data=module.stable_read(root / module.DEFAULT_DTBO, "P3.17 DTBO", 64 * 1024 * 1024),
            vendor_dtb_data=module.stable_read(root / module.DEFAULT_VENDOR_DTB, "P3.17 vendor DTB", 64 * 1024 * 1024),
            property_data=module.stable_read(root / module.DEFAULT_PROPERTY_SOURCE, "P3.17 property source", 512 * 1024),
            core_data=module.stable_read(root / module.DEFAULT_CORE_SOURCE, "P3.17 core source", 1024 * 1024),
            of_base_data=module.stable_read(root / module.DEFAULT_OF_BASE_SOURCE, "P3.17 OF base source", 512 * 1024),
            irq_data=module.stable_read(root / module.DEFAULT_IRQ_SOURCE, "P3.17 IRQ source", 512 * 1024),
            rpmh_data=module.stable_read(root / module.DEFAULT_RPMH_SOURCE, "P3.17 RPMh source", 512 * 1024),
            rpmh_regulator_data=module.stable_read(root / module.DEFAULT_RPMH_REGULATOR_SOURCE, "P3.17 RPMh regulator source", 512 * 1024),
            config_data=module.stable_read(root / module.DEFAULT_CONFIG, "P3.17 config", 512 * 1024),
            predecessor_data=module.stable_read(root / module.DEFAULT_PREDECESSOR, "P3.17 predecessor", 8 * 1024 * 1024),
            must_bind_data=module.stable_read(root / module.DEFAULT_MUST_BIND_RECEIPT, "P3.17 must-bind", 512 * 1024),
            metadata=metadata,
            fdtoverlay=root / module.DEFAULT_FDTOVERLAY,
            libfdt=root / module.DEFAULT_LIBFDT,
        )
        encoded = module.encode_contract(regenerated)
    except AuditError:
        raise
    except Exception as exc:
        raise AuditError("P3.17 exact extractor regeneration failed") from exc
    finally:
        sys.path[:] = old_path
        sys.modules.pop(module_name, None)
    if encoded != expected_bytes:
        raise AuditError("P3.17 regenerated receipt is not byte-identical")
    return regenerated


def reexecute_p317_upstream_projection(p317: Mapping[str, Any], receipt_bytes: bytes | None = None) -> dict[str, Any]:
    """Regenerate P3.17 exactly, then project only unchanged QUP/I2C edges."""
    if receipt_bytes is None:
        receipt_bytes = stable_bytes(P317_FIXED_POINT, "P3.17 fixed-point receipt", expected=EXPECTED_IDS["p317_fixed_point"], maximum=16 * 1024 * 1024)
    regenerated = _regenerate_p317_receipt(receipt_bytes)
    regenerated_value = strict_object(receipt_bytes, "P3.17 regenerated receipt")
    if regenerated_value != dict(p317):
        raise AuditError("P3.17 regenerated value differs from supplied authority")
    edges = _upstream_edges(regenerated)
    return {
        "seed_roots": [P317_WRAPPER, P317_I2C],
        "edge_count": len(edges),
        "edges": edges,
        "reexecuted_from_exact_receipt": True,
        "regenerated_byte_identity": identity(receipt_bytes),
        "diagnostic_root_reused": False,
    }


def validate_stock_evidence(irq: Mapping[str, Any], pdic: Mapping[str, Any], materialization: Mapping[str, Any]) -> dict[str, Any]:
    if irq.get("schema") != "s22plus-fyg8-p319-max77705-irq-dt-audit-v3" or pdic.get("schema") != "s22plus-fyg8-p319-candidate-pdic-probe-boundary-v3":
        raise AuditError("P3.19 stock evidence schema differs")
    dtbo = irq.get("dtbo", {})
    binary = irq.get("binary_semantics", {})
    conclusion = irq.get("conclusion", {})
    if dtbo.get("i2c_address") != 102 or dtbo.get("i2c_controller_fixup") != "qupv3_se5_i2c" or dtbo.get("pdic_child_enabled") is not True:
        raise AuditError("P3.19 DT identity/child enablement differs")
    if binary.get("mfd_max77705", {}).get("mfd_child_count") != 3 or binary.get("mfd_max77705", {}).get("mfd_usbc_child") != "max77705-usbc" or binary.get("pdic_max77705", {}).get("platform_driver_name") != "max77705-usbc":
        raise AuditError("P3.19 MFD/PDIC child identity differs")
    for key in ("mfd_publishes_max77705_usbc_child", "pdic_platform_driver_matches_mfd_child", "pdic_probe_registers_five_muic_nested_irqs", "pdic_probe_completion_unmasks_parent_usbc_source"):
        if conclusion.get(key) is not True:
            raise AuditError(f"P3.19 stock conclusion is not source-proven: {key}")
    probe = pdic.get("probe_source", {})
    for key in ("initial_detect_precedes_parent_usbc_unmask", "initial_detect_sets_ready_then_reads_and_classifies_status", "final_vbusdet_irq_failure_blocks_initial_detect", "muic_probe_error_is_not_propagated_by_usbc_probe"):
        if probe.get(key) is not True:
            raise AuditError(f"P3.19 probe boundary is incomplete: {key}")
    mods = materialization.get("module_bytes", {}).get("modules", {})
    if not isinstance(mods, Mapping):
        raise AuditError("P3.19 materialization module identity is absent")
    for name in ("mfd_max77705.ko", "pdic_max77705.ko", "spu_verify.ko", "dwc3-msm.ko"):
        expected = MODULE_SPECS[name]
        row = mods.get(name)
        if not isinstance(row, Mapping) or row.get("size") != expected["size"] or row.get("sha256") != expected["sha256"]:
            raise AuditError(f"P3.19 module byte identity differs: {name}")
    mfd_text = stable_bytes(MFD_SOURCE, "P3.19 MFD source", expected=irq["inputs"]["max77705_mfd_source"], maximum=128 * 1024).decode("utf-8")
    mfd_header_text = stable_bytes(MFD_HEADER, "P3.19 MFD header", expected=irq["inputs"]["max77705_mfd_header"], maximum=32 * 1024).decode("utf-8")
    pdic_text = stable_bytes(PDIC_SOURCE, "P3.19 PDIC source", expected=irq["inputs"]["max77705_usbc_source"], maximum=192 * 1024).decode("utf-8")
    stable_bytes(MUIC_SOURCE, "P3.19 MUIC source", expected=irq["inputs"]["max77705_muic_source"], maximum=128 * 1024)
    stable_bytes(DT_SOURCE, "P3.19 DT source", expected=irq["inputs"]["active_r12_dts"], maximum=2 * 1024 * 1024)
    stable_bytes(DTBO, "P3.19 stock DTBO", expected=irq["inputs"]["stock_dtbo"], maximum=9 * 1024 * 1024)
    mfd_driver = validate_stock_source_texts(mfd_text, mfd_header_text, pdic_text)
    return {
        "dtbo": dict(dtbo),
        "mfd_binary": dict(binary.get("mfd_max77705", {})),
        "pdic_binary": dict(binary.get("pdic_max77705", {})),
        "mfd_source": dict(irq["inputs"]["max77705_mfd_source"]),
        "mfd_header": dict(irq["inputs"]["max77705_mfd_header"]),
        "pdic_source": dict(irq["inputs"]["max77705_usbc_source"]),
        "dt_source": dict(irq["inputs"]["active_r12_dts"]),
        "mfd_driver": mfd_driver,
    }


def validate_plan(plan: Mapping[str, Any], materialization: Mapping[str, Any], intent: Mapping[str, Any], qualification: Mapping[str, Any]) -> dict[str, Any]:
    rows = plan.get("successor_plan", {}).get("successor_plan_rows")
    if not isinstance(rows, list) or len(rows) != 73 or [row.get("index") for row in rows] != list(range(73)):
        raise AuditError("P3.19 exact 73-row plan is absent or reordered")
    if rows[38] != {"filename": "eud.ko", "index": 38, "params": "", "runtime_name": "eud"}:
        raise AuditError("P3.19 EUD identity/index differs")
    if any(_contains_forbidden(row) for row in rows):
        raise AuditError("P3.17 diagnostic module leaked into P3.19 plan")
    declared = intent.get("module_plan")
    if declared != {"count": 73, "eud_index": 38, "overlay_delta": ["s22plus_dwc3_event_latch.ko"]}:
        raise AuditError("P3.19 declared module plan differs")
    if qualification.get("derived_eud_index") != 38 or qualification.get("diagnostic_absent") is not True:
        raise AuditError("P3.19 candidate qualification does not bind plan/EUD/diagnostic boundary")
    added = materialization.get("materialization", {}).get("added_entries")
    expected_added = [
        {"filename": "spu_verify.ko", "index": 70, "params": "", "runtime_name": "spu_verify"},
        {"filename": "mfd_max77705.ko", "index": 71, "params": "", "runtime_name": "mfd_max77705"},
        {"filename": "pdic_max77705.ko", "index": 72, "params": "", "runtime_name": "pdic_max77705"},
    ]
    if added != expected_added or materialization.get("materialization", {}).get("successor_plan_count") != 73:
        raise AuditError("P3.19 materialized plan delta differs")
    for name, spec in MODULE_SPECS.items():
        module_path = I2C_MODULE if name == "i2c-msm-geni.ko" else MODULE_ROOT / name
        row = rows[spec["index"]]
        if row.get("filename") != name:
            raise AuditError(f"P3.19 module order differs: {name}")
        data = stable_bytes(module_path, f"P3.19 {name}", expected={"size": spec["size"], "sha256": spec["sha256"]}, maximum=512 * 1024, mode=0o400)
        if len(data) != spec["size"]:
            raise AuditError(f"P3.19 module size differs: {name}")
    return {
        "module_count": 73,
        "eud_index": 38,
        "module_order": {name: MODULE_SPECS[name]["index"] for name in MODULE_SPECS},
        "module_roles": {name: MODULE_SPECS[name]["role"] for name in MODULE_SPECS},
        "link_only_closure": ["spu_verify.ko -> spu_firmware_signature_verify -> max77705_firmware_update_sysfs"],
    }


def candidate_edges(stock: Mapping[str, Any]) -> list[dict[str, Any]]:
    dt_owner = "/soc/qcom,spmi@c42d000/qcom,pm8350c@2/pinctrl@8800"
    mfd_driver = stock.get("mfd_driver")
    if not isinstance(mfd_driver, Mapping) or mfd_driver.get("driver_name") != "max77705" or mfd_driver.get("probe_function") != "max77705_i2c_probe":
        raise AuditError("P3.19 MFD driver/provider identity is not source-derived")
    edges = [
        {"family": FAMILY_INST, "consumer": P319_MFD, "instantiator": P317_I2C, "mechanism": "i2c_add_adapter_then_of_i2c_register_devices", "provider_module": "mfd_max77705.ko", "expected_driver": mfd_driver["driver_name"], "probe_function": mfd_driver["probe_function"]},
        {"family": FAMILY_INST, "consumer": P319_PDIC, "instantiator": P319_MFD, "mechanism": "mfd_add_devices(max77705_devs)", "provider_module": "pdic_max77705.ko"},
        {"family": FAMILY_FW, "consumer": P319_MFD, "owner": dt_owner, "supplier_node": dt_owner, "property": "max77705,irq-gpio", "parser": "parse_gpio", "kernel_link_created": True},
    ]
    if any(_contains_forbidden(edge) for edge in edges):
        raise AuditError("candidate relation edge contains forbidden P3.17 diagnostic identity")
    return edges


def derive_fixed_point(p317: Mapping[str, Any], stock: Mapping[str, Any], *, p317_receipt_bytes: bytes | None = None) -> dict[str, Any]:
    upstream_replay = reexecute_p317_upstream_projection(p317, p317_receipt_bytes)
    upstream = upstream_replay["edges"]
    extras = candidate_edges(stock)
    all_edges = upstream + extras
    edge_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for edge in all_edges:
        family = edge.get("family")
        consumer = edge.get("consumer")
        if family not in FAMILIES or not isinstance(consumer, str) or _contains_forbidden(edge):
            raise AuditError("unclassified or forbidden relation reached fixed-point")
        edge_map.setdefault((consumer, family), []).append(dict(edge))
    seen = set(P319_ROOTS)
    frontier = list(P319_ROOTS)
    iterations: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    while frontier:
        emitted: set[str] = set()
        evaluations: list[dict[str, Any]] = []
        iteration_edges: list[dict[str, Any]] = []
        for node in sorted(frontier):
            for family in FAMILIES:
                rows = edge_map.get((node, family), [])
                evaluations.append({"node": node, "family": family, "edge_count": len(rows)})
                for edge in rows:
                    target = _edge_target(edge)
                    if target is None:
                        raise AuditError("required relation has no exact target identity")
                    iteration_edges.append(dict(edge))
                    if target.startswith("/") and target not in seen:
                        emitted.add(target)
        iterations.append({"index": len(iterations), "frontier": sorted(frontier), "family_evaluations": evaluations, "raw_edges": iteration_edges, "new_nodes": sorted(emitted)})
        raw.extend(iteration_edges)
        seen.update(emitted)
        frontier = sorted(emitted)
        if len(iterations) > len(all_edges) + len(P319_ROOTS) + 1:
            raise AuditError("P3.19 fixed-point did not converge")
    dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edge in raw:
        target = _edge_target(edge)
        if target is None:
            raise AuditError("P3.19 edge target is unclassified")
        key = (str(edge["family"]), str(edge["consumer"]), target)
        if key in dedup:
            dedup[key]["raw_evidence_count"] += 1
        else:
            value = dict(edge)
            value["raw_evidence_count"] = 1
            dedup[key] = value
    for item in iterations:
        frontier = item["frontier"]
        pairs = {(row["node"], row["family"]) for row in item["family_evaluations"]}
        if len(pairs) != len(frontier) * len(FAMILIES) or any((node, family) not in pairs for node in frontier for family in FAMILIES):
            raise AuditError("P3.19 fixed-point skipped a family/frontier node")
    result = {
        "roots": list(P319_ROOTS),
        "relationship_families": list(FAMILIES),
        "iterations": iterations,
        "iteration_count": len(iterations),
        "nodes": sorted(seen),
        "node_count": len(seen),
        "raw_edge_count": len(raw),
        "deduplicated_edge_count": len(dedup),
        "deduplicated_edges": [dedup[key] for key in sorted(dedup)],
        "converged": True,
        "family_outputs_reenter_all_families": True,
        "every_frontier_node_evaluated_by_every_family": True,
        "upstream_p317_relation_count": len(upstream),
        "candidate_stock_relation_count": len(extras),
        "p317_upstream_reexecution": upstream_replay,
    }
    if _contains_forbidden(result):
        raise AuditError("P3.17 diagnostic identity leaked into P3.19 fixed point")
    return result


def validate_fixed_point(result: Mapping[str, Any]) -> None:
    if tuple(result.get("relationship_families", ())) != FAMILIES or tuple(result.get("roots", ())) != P319_ROOTS:
        raise AuditError("P3.19 fixed-point roots/families differ")
    if result.get("converged") is not True or result.get("family_outputs_reenter_all_families") is not True or result.get("every_frontier_node_evaluated_by_every_family") is not True:
        raise AuditError("P3.19 fixed-point convergence/re-entry invariant differs")
    if _contains_forbidden(result):
        raise AuditError("P3.19 fixed-point contains diagnostic parent leakage")
    iterations = result.get("iterations")
    if not isinstance(iterations, list) or result.get("iteration_count") != len(iterations):
        raise AuditError("P3.19 fixed-point iteration accounting differs")
    nodes = result.get("nodes")
    if not isinstance(nodes, list) or nodes != sorted(set(nodes)):
        raise AuditError("P3.19 fixed-point node identity accounting differs")
    dedup = result.get("deduplicated_edges")
    if not isinstance(dedup, list) or result.get("deduplicated_edge_count") != len(dedup):
        raise AuditError("P3.19 deduplication accounting differs")
    if (
        result.get("upstream_p317_relation_count") != EXPECTED_UPSTREAM_EDGE_COUNT
        or result.get("candidate_stock_relation_count") != EXPECTED_CANDIDATE_EDGE_COUNT
        or result.get("node_count") != EXPECTED_NODE_COUNT
        or len(result.get("nodes", ())) != EXPECTED_NODE_COUNT
        or len(dedup) != EXPECTED_DEDUPLICATED_EDGE_COUNT
    ):
        raise AuditError("P3.19 fixed-point is root-only or relation output is incomplete")
    keys = {(e.get("family"), e.get("consumer"), _edge_target(e)) for e in dedup}
    if len(keys) != len(dedup) or any(e.get("family") not in FAMILIES or _edge_target(e) is None for e in dedup):
        raise AuditError("P3.19 deduplicated relation is unclassified")
    family_counts = {family: sum(edge.get("family") == family for edge in dedup) for family in FAMILIES}
    if family_counts != EXPECTED_FAMILY_COUNTS:
        raise AuditError("P3.19 registered relation family output is incomplete")
    raw_count = sum(len(item.get("raw_edges", ())) for item in iterations)
    if result.get("raw_edge_count") != raw_count:
        raise AuditError("P3.19 raw edge accounting differs")
    for item in iterations:
        frontier = item.get("frontier", ())
        pairs = {(row.get("node"), row.get("family")) for row in item.get("family_evaluations", ())}
        if len(pairs) != len(frontier) * len(FAMILIES) or any((node, family) not in pairs for node in frontier for family in FAMILIES):
            raise AuditError("P3.19 iteration omitted a family evaluation")


def build_result(authority: Mapping[str, Any] | None = None) -> dict[str, Any]:
    authority = load_exact_authority() if authority is None else authority
    p317 = authority["p317_fixed_point"]
    irq = authority["p319_irq"]
    pdic = authority["p319_pdic"]
    plan = authority["p319_plan"]
    materialization = authority["p319_materialization"]
    intent = authority["p319_intent"]
    qualification = authority["p319_qualification"]
    validate_p317_authority(p317, authority["p317_fw"], authority["p317_must_bind"])
    stock = validate_stock_evidence(irq, pdic, materialization)
    plan_summary = validate_plan(plan, materialization, intent, qualification)
    fixed = derive_fixed_point(p317, stock, p317_receipt_bytes=authority["_raw"]["p317_fixed_point"])
    validate_fixed_point(fixed)
    runtime = {
        name: {"required": True, "status": "PENDING_FRESH_CANDIDATE_RUN", "accepted_as_preflight_fact": False, "requirement": statement}
        for name, statement in RUNTIME_WITNESS_SPECS.items()
    }
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": "PASS_SOURCE_CLOSURE_RUNTIME_GATES_PENDING",
        "target": TARGET,
        "authority": {
            "p317_fixed_point": EXPECTED_IDS["p317_fixed_point"],
            "p317_fw_devlink": EXPECTED_IDS["p317_fw"],
            "p317_must_bind": EXPECTED_IDS["p317_must_bind"],
            "p319_irq_dt": EXPECTED_IDS["p319_irq"],
            "p319_pdic_boundary": EXPECTED_IDS["p319_pdic"],
            "p319_module_plan": EXPECTED_IDS["p319_plan"],
            "p319_materialization": EXPECTED_IDS["p319_materialization"],
            "p319_candidate_intent": EXPECTED_IDS["p319_intent"],
            "p319_candidate_qualification": EXPECTED_IDS["p319_qualification"],
            "p317_extractor_source": authority.get("_source_receipt"),
            "contracts": authority.get("_contract_receipts"),
        },
        "candidate_must_bind_consumers": [
            {"id": "P319_CONSUMER_QUPV3_WRAPPER", "device_identity": P317_WRAPPER, "expected_driver": "qupv3_geni_se", "source_authority": "P317 unchanged DRIVER_CONSUMED_DT_REFERENCE_CLOSURE"},
            {"id": "P319_CONSUMER_TARGET_I2C_CONTROLLER", "device_identity": P317_I2C, "expected_driver": "i2c_geni", "source_authority": "P317 unchanged DEVICE_INSTANTIATION_CLOSURE"},
            {"id": "P319_CONSUMER_MAX77705_MFD", "device_identity": P319_MFD, "expected_driver": stock["mfd_driver"]["driver_name"], "probe_function": stock["mfd_driver"]["probe_function"], "module": {"name": "mfd_max77705.ko", **{key: MODULE_SPECS["mfd_max77705.ko"][key] for key in ("size", "sha256")}}, "source_authority": "P319 IRQ/DT V3 exact MFD binary/source/DT"},
            {"id": "P319_CONSUMER_MAX77705_PDIC_CHILD", "device_identity": P319_PDIC, "expected_driver": "max77705-usbc", "module": {"name": "pdic_max77705.ko", **{key: MODULE_SPECS["pdic_max77705.ko"][key] for key in ("size", "sha256")}}, "source_authority": "P319 IRQ/DT V3 max77705_devs -> max77705-usbc -> max77705_usbc_probe"},
        ],
        "must_bind_root_qualification": {
            "process_contract_section": "DEVICE_ACTION_PROCESS_V2.md:417-438; global registry repin:562-602",
            "roots_are_design_consumers_not_runtime_success": True,
            "roots": [
                {"identity": P317_WRAPPER, "kind": "unchanged_p317_must_bind_root", "reason": "The exact GENI wrapper is required by the i2c-msm-geni driver-consumed qcom,wrapper-core relation."},
                {"identity": P317_I2C, "kind": "unchanged_p317_must_bind_root", "reason": "The exact 994000.i2c controller is the only admissible adapter that can enumerate the 0x66 client."},
                {"identity": P319_MFD, "kind": "candidate_instantiator_root", "reason": "The 0x66 MFD client is a required experiment consumer and its source-bound i2c creator/provider must remain visible in closure."},
                {"identity": P319_PDIC, "kind": "candidate_instantiator_root", "reason": "The max77705-usbc child does not exist until mfd_add_devices(max77705_devs); it is a required consumer whose creator edge must be closed."},
            ],
            "instantiator_edges": [
                "i2c_add_adapter_then_of_i2c_register_devices: 994000.i2c -> 0x66 MFD client",
                "mfd_add_devices(max77705_devs): MFD client -> max77705-usbc child",
            ],
        },
        "candidate_specific_instantiation": {
            "parent": P319_MFD,
            "child": P319_PDIC,
            "child_platform_driver": "max77705-usbc",
            "mfd_driver_name": stock["mfd_driver"]["driver_name"],
            "mfd_probe_function": stock["mfd_driver"]["probe_function"],
            "mfd_publishes_child": True,
            "driver_match": True,
            "module_load_order_required": ["i2c-msm-geni.ko", "spu_verify.ko", "mfd_max77705.ko", "pdic_max77705.ko"],
            "mfd_add_devices_edge": True,
        },
        "registered_relationship_families": list(FAMILIES),
        "fixed_point": fixed,
        "plan": plan_summary,
        "stock_evidence": stock,
        "runtime_evaluability_witnesses": runtime,
        "runtime_gate_satisfied": False,
        "excluded_p317_diagnostic_parent": {"identity": P317_DIAGNOSTIC_PARENT, "excluded_from_roots_edges_and_providers": True, "reason": "P3.19 stock candidate uses mfd_max77705 plus pdic_max77705"},
        "causal_result_allowed": False,
        "candidate_success": False,
        "device_contact": False,
        "scope": {"tier": "H0", "host_only": True, "device_contact": False, "live_authorized": False, "d0_authorized": False, "d1_authorized": False, "f1_authorized": False, "replay_authorized": False, "approval_created": False},
    }


def blocked_result(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "verdict": BLOCKED_VERDICT,
        "status": "BLOCKED_MISSING_AUTHORITY",
        "target": TARGET,
        "blockers": [reason],
        "causal_result_allowed": False,
        "candidate_success": False,
        "device_contact": False,
        "scope": {"tier": "H0", "host_only": True, "device_contact": False, "live_authorized": False, "approval_created": False},
    }


def encode(result: Mapping[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_exclusive(path: Path, payload: bytes) -> None:
    """Publish one complete 0400 receipt and verify the published bytes."""
    if path.exists() or path.is_symlink():
        raise AuditError(f"refusing to clobber closure result: {path}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.lstat()
    if stat.S_IMODE(parent.st_mode) != 0o700 or not stat.S_ISDIR(parent.st_mode):
        raise AuditError("closure output parent is not a private 0700 directory")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            try:
                count = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if count <= 0:
                raise AuditError("closure receipt write did not progress")
            offset += count
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o400
            or info.st_nlink != 1
            or info.st_size != len(payload)
        ):
            raise AuditError("closure receipt publication metadata differs")
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)
    reopened = stable_bytes(
        path,
        "published closure receipt",
        expected=identity(payload),
        maximum=max(len(payload), 1),
        mode=0o400,
    )
    if reopened != payload or path.lstat().st_nlink != 1:
        raise AuditError("published closure receipt bytes differ after reopen")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PRIVATE / "outputs/s22plus_fyg8_p319/experiment-executability-closure-v1-20260821-01/result.json")
    args = parser.parse_args(argv)
    try:
        result = build_result()
        status = 0
    except AuditError as exc:
        result = blocked_result(str(exc))
        status = 3
    encoded = encode(result)
    publish_exclusive(args.out, encoded)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
