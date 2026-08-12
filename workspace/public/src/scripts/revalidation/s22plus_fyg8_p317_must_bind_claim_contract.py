#!/usr/bin/env python3
"""Materialize the reviewable P3.17 must-bind claim authority.

Host-only.  This contract does not decide whether its causal sentences are
true.  It makes every proposed claim-to-consumer judgment explicit, requires
complete coverage, and binds the exact source seams that the human judgment
describes.  Human review remains the authority for causal truth.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_p317_must_bind_claim_contract_v1"
VERDICT = "PASS_P317_MUST_BIND_FIXED_POINT_AUTHORITY_H0_REVIEWED"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
HUMAN_CAUSAL_REVIEW = "SATISFIED_2026_08_12"
CLAIM_AUTHORITY_SHA256 = (
    "49859c0957a15ef25cdad98137c5f178eb790f4689ddeb74553971d1a9ce3070"
)
SUPERSEDED_REVIEWED_CLAIM_AUTHORITY_SHA256 = (
    "fd27d79883cbdc5e6daab937f0b24ab303fdd8a1c91cf63feb5789975e04c1d3"
)

DEFAULT_RUNTIME_SOURCE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_runtime_core.inc.c"
)
DEFAULT_DIAGNOSTIC_SOURCE = Path(
    "workspace/public/src/kernel-modules/s22plus_max77705_mux_diag/"
    "s22plus_max77705_mux_diag.c"
)
DEFAULT_SURFACE_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_custom_surface_contract.py"
)
DEFAULT_LIVE_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py"
)
DEFAULT_KERNEL_ROOT = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform"
)
DEFAULT_QUP_SOURCE = (
    DEFAULT_KERNEL_ROOT / "msm-kernel/drivers/platform/msm/msm-geni-se.c"
)
DEFAULT_I2C_DRIVER_SOURCE = (
    DEFAULT_KERNEL_ROOT / "msm-kernel/drivers/i2c/busses/i2c-msm-geni.c"
)
DEFAULT_I2C_CORE_SOURCE = (
    DEFAULT_KERNEL_ROOT / "common/drivers/i2c/i2c-core-base.c"
)
DEFAULT_I2C_OF_SOURCE = (
    DEFAULT_KERNEL_ROOT / "common/drivers/i2c/i2c-core-of.c"
)
DEFAULT_OF_PLATFORM_SOURCE = (
    DEFAULT_KERNEL_ROOT / "common/drivers/of/platform.c"
)
DEFAULT_QUP_DTS_SOURCE = (
    DEFAULT_KERNEL_ROOT
    / "qcom/proprietary/devicetree/qcom/waipio-qupv3.dtsi"
)
DEFAULT_SPMI_ARB_SOURCE = (
    DEFAULT_KERNEL_ROOT / "msm-kernel/drivers/spmi/spmi-pmic-arb.c"
)
DEFAULT_SPMI_CORE_SOURCE = (
    DEFAULT_KERNEL_ROOT / "common/drivers/spmi/spmi.c"
)
DEFAULT_SPMI_PMIC_SOURCE = (
    DEFAULT_KERNEL_ROOT / "msm-kernel/drivers/mfd/qcom-spmi-pmic.c"
)
DEFAULT_PM8350C_DTS_SOURCE = (
    DEFAULT_KERNEL_ROOT
    / "qcom/proprietary/devicetree/qcom/pm8350c.dtsi"
)


EVALUABILITY_PRECONDITIONS: tuple[dict[str, str], ...] = (
    {
        "id": "P317_EVAL_COMPLETE_EXACT_DIAGNOSTIC_RESULT",
        "statement": (
            "A complete authority-valid device result must bind the exact "
            "dynamic adapter, 0x66 compatible parent, synchronous diagnostic "
            "completion, and retained transaction fields."
        ),
        "current_status": "PENDING_SUCCESSOR_LIVE_RESULT",
    },
    {
        "id": "P317_EVAL_BOTH_WINDOW_ENDPOINTS_COMPLETE",
        "statement": (
            "Both opcode-visible post1 and post2 samples and their retained "
            "poll authority must be complete before a two-boundary result is "
            "interpreted."
        ),
        "current_status": "PENDING_SUCCESSOR_LIVE_RESULT",
    },
    {
        "id": "P317_EVAL_DEVICE_GADGET_PATH_READY_BEFORE_DIAGNOSTIC",
        "statement": (
            "The successor must machine-prove and retain the device-side "
            "gadget-path readiness required to make host silence evaluable, "
            "before diagnostic dispatch."
        ),
        "current_status": "PENDING_SUCCESSOR_REQUALIFICATION_AND_WITNESS",
    },
    {
        "id": "P317_EVAL_HOST_USB_SIDECAR_ARMED_FOR_CANDIDATE_WINDOW",
        "statement": (
            "The Process-v2 host USB sidecar must have an authority-valid arm "
            "receipt covering the candidate correlation window."
        ),
        "current_status": "PENDING_SUCCESSOR_REQUALIFICATION_AND_LIVE_ARM",
    },
)


CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "id": "P317_CLAIM_EXACT_CONTROL1_TRANSACTION",
        "statement": (
            "A complete device result describes one bounded CONTROL1 command "
            "sequence executed on the exact Max77705 at address 0x66 beneath "
            "the adapter dynamically resolved from platform device 994000.i2c."
        ),
        "result_scope": (
            "all device-result rows that interpret pre, post1, post2, write, "
            "response, or retained poll evidence"
        ),
        "evaluability_preconditions": (
            "P317_EVAL_COMPLETE_EXACT_DIAGNOSTIC_RESULT",
        ),
    },
    {
        "id": "P317_CLAIM_CONTROL1_WINDOW_ENDPOINTS",
        "statement": (
            "When post1 and post2 are both opcode-visible COM_USB, the exact "
            "Max77705 command state was observed as COM_USB at both sampled "
            "boundaries of the 30000-ms correlation window; this does not "
            "prove uninterrupted retention or physical switch continuity."
        ),
        "result_scope": (
            "post1/post2 retention and reversion classifications"
        ),
        "evaluability_preconditions": (
            "P317_EVAL_COMPLETE_EXACT_DIAGNOSTIC_RESULT",
            "P317_EVAL_BOTH_WINDOW_ENDPOINTS_COMPLETE",
        ),
    },
    {
        "id": "P317_CLAIM_MUX_CAUSAL_ATTACH_SUPPORT",
        "statement": (
            "A host attach correlated with a pre-non-COM_USB, post1/post2-"
            "COM_USB device result is strong support for the bounded MUX "
            "transition, subject to the explicit physical-interpretation "
            "ceiling."
        ),
        "result_scope": "pre_non_0x09_post1_post2_0x09_attach",
        "evaluability_preconditions": (
            "P317_EVAL_COMPLETE_EXACT_DIAGNOSTIC_RESULT",
            "P317_EVAL_BOTH_WINDOW_ENDPOINTS_COMPLETE",
            "P317_EVAL_DEVICE_GADGET_PATH_READY_BEFORE_DIAGNOSTIC",
            "P317_EVAL_HOST_USB_SIDECAR_ARMED_FOR_CANDIDATE_WINDOW",
        ),
    },
)


CONSUMERS: tuple[dict[str, Any], ...] = (
    {
        "id": "P317_CONSUMER_QUPV3_WRAPPER",
        "device_identity": "platform:9c0000.qcom,qupv3_0_geni_se",
        "expected_driver": "qupv3_geni_se",
        "root_kind": "driver_consumed_dependency",
        "root_reason": (
            "The exact 994000.i2c probe parses qcom,wrapper-core, resolves this "
            "platform device, and passes it to geni_se_resources_init(). If "
            "the wrapper has no bound-driver data, that helper returns "
            "-EPROBE_DEFER before adapter registration."
        ),
    },
    {
        "id": "P317_CONSUMER_TARGET_I2C_CONTROLLER",
        "device_identity": "platform:994000.i2c",
        "expected_driver": "i2c_geni",
        "root_kind": "experiment_endpoint",
        "root_reason": (
            "The runtime resolves the only admissible I2C adapter as a child "
            "of this exact platform device before locating address 0x66."
        ),
    },
    {
        "id": "P317_CONSUMER_EXACT_MAX77705_PARENT",
        "device_identity": (
            "i2c:<adapter-under-platform-994000.i2c>-0066; "
            "compatible=maxim,max77705"
        ),
        "expected_driver": "s22plus_max77705_mux_diag",
        "root_kind": "experiment_endpoint",
        "root_reason": (
            "The synchronous diagnostic probe accepts only the exact address "
            "and compatible and is the sole producer of CONTROL1 evidence."
        ),
    },
)


CLAIM_CONSUMER_EDGES: tuple[dict[str, str], ...] = (
    {
        "claim": "P317_CLAIM_EXACT_CONTROL1_TRANSACTION",
        "consumer": "P317_CONSUMER_QUPV3_WRAPPER",
        "failure_consequence": (
            "If the QUPv3 wrapper is not bound, 994000.i2c can exist as its "
            "OF-platform sibling but geni_se_resources_init() returns "
            "-EPROBE_DEFER before i2c_add_adapter(); no target adapter or "
            "0x66 client exists and the CONTROL1 transaction does not occur."
        ),
    },
    {
        "claim": "P317_CLAIM_EXACT_CONTROL1_TRANSACTION",
        "consumer": "P317_CONSUMER_TARGET_I2C_CONTROLLER",
        "failure_consequence": (
            "If 994000.i2c is not bound, i2c_add_adapter() does not register "
            "the target adapter and of_i2c_register_devices() does not create "
            "the exact 0x66 client; the CONTROL1 transaction does not occur."
        ),
    },
    {
        "claim": "P317_CLAIM_CONTROL1_WINDOW_ENDPOINTS",
        "consumer": "P317_CONSUMER_QUPV3_WRAPPER",
        "failure_consequence": (
            "Without the QUPv3 wrapper binding, the existing 994000.i2c "
            "device defers before adapter registration, so the 0x66 client "
            "is not created and neither post1 nor post2 can be sampled."
        ),
    },
    {
        "claim": "P317_CLAIM_EXACT_CONTROL1_TRANSACTION",
        "consumer": "P317_CONSUMER_EXACT_MAX77705_PARENT",
        "failure_consequence": (
            "If the exact 0x66 client is not bound to the diagnostic, its "
            "probe and bounded CONTROL1 sequence do not execute."
        ),
    },
    {
        "claim": "P317_CLAIM_CONTROL1_WINDOW_ENDPOINTS",
        "consumer": "P317_CONSUMER_TARGET_I2C_CONTROLLER",
        "failure_consequence": (
            "Without the exact controller binding, the adapter is not "
            "registered and the 0x66 client is not created, so post1 and "
            "post2 do not occur and no two-boundary classification exists."
        ),
    },
    {
        "claim": "P317_CLAIM_MUX_CAUSAL_ATTACH_SUPPORT",
        "consumer": "P317_CONSUMER_QUPV3_WRAPPER",
        "failure_consequence": (
            "Without the QUPv3 wrapper binding, the target controller cannot "
            "complete probe or register its adapter, and the 0x66 client is "
            "not created. Any host attach remains an independent host fact "
            "because no MUX transaction occurred."
        ),
    },
    {
        "claim": "P317_CLAIM_CONTROL1_WINDOW_ENDPOINTS",
        "consumer": "P317_CONSUMER_EXACT_MAX77705_PARENT",
        "failure_consequence": (
            "Without the exact diagnostic-bound parent, there is no producer "
            "for the two validated CONTROL1 reads that delimit retention."
        ),
    },
    {
        "claim": "P317_CLAIM_MUX_CAUSAL_ATTACH_SUPPORT",
        "consumer": "P317_CONSUMER_TARGET_I2C_CONTROLLER",
        "failure_consequence": (
            "Without the exact controller binding, no adapter or 0x66 client "
            "is created and no CONTROL1 transaction occurs. Any host attach "
            "remains an independent host fact, not MUX-causal support."
        ),
    },
    {
        "claim": "P317_CLAIM_MUX_CAUSAL_ATTACH_SUPPORT",
        "consumer": "P317_CONSUMER_EXACT_MAX77705_PARENT",
        "failure_consequence": (
            "A host attach without a complete exact-parent diagnostic result "
            "is preserved only as an independent host fact, not MUX-causal "
            "support."
        ),
    },
)


EXCLUDED_ADJACENT_CONSUMERS: tuple[dict[str, str], ...] = (
    {
        "identity": "platform:900000.qcom,gpi-dma",
        "reason": (
            "It is a true fw_devlink supplier selected by the target "
            "controller's dmas property. It must be derived by the registered "
            "supplier closure rather than seeded as an endpoint root."
        ),
    },
    {
        "identity": "qcom,pm8350c-gpio provider selected by phandles 0x7b/0x11",
        "reason": (
            "It is a derived fw_devlink supplier of the exact Max77705 root, "
            "not an independently selected experiment endpoint."
        ),
    },
    {
        "identity": "the twelve non-target P3.16 GENI/GPI/I2C platform devices",
        "reason": (
            "They are negative isolation controls whose binding is forbidden; "
            "none can produce an admissible target CONTROL1 result."
        ),
    },
    {
        "identity": "stock Max77705 MFD, PDIC, MUIC, and child control planes",
        "reason": (
            "The bounded diagnostic intentionally bypasses those control "
            "planes and creates only one 0x25 dummy client."
        ),
    },
    {
        "identity": "inherited DWC3 gadget path and host sidecar",
        "reason": (
            "They are separately qualified runtime/observer prerequisites, "
            "not roots of the CONTROL1 transport dependency closure. Their "
            "absence prevents a causal row but does not expand this root set."
        ),
    },
)


REVIEW_TRIGGERS: tuple[str, ...] = (
    "candidate execution path or result contract changes",
    "an expected must-bind consumer is observed unbound",
    "an excluded consumer is implicated in the result",
    "exact DT, kernel, module mapping, or load-order authority changes",
    "a new non-symbol dependency relationship family is discovered",
)


RELATIONSHIP_FIXED_POINT: dict[str, Any] = {
    "algorithm": "least_fixed_point",
    "initial_node_set": "reviewed must-bind consumers",
    "registered_families": [
        "FW_DEVLINK_DT_SUPPLIER_CLOSURE",
        "DEVICE_INSTANTIATION_CLOSURE",
        "DRIVER_CONSUMED_DT_REFERENCE_CLOSURE",
    ],
    "iteration_equation": (
        "S[n+1] = S[n] union fw_devlink_suppliers(S[n]) union "
        "device_instantiators(S[n]) union "
        "driver_consumed_dt_dependencies(S[n])"
    ),
    "family_input_domain": (
        "every exact node in S[n], including nodes emitted by any registered "
        "relationship family"
    ),
    "family_outputs_reenter_all_registered_families": True,
    "convergence_condition": "no new exact node or required edge",
    "termination_basis": "finite exact candidate firmware/device-node universe",
    "deduplication_key": "exact source-derived device or firmware-node identity",
    "root_only_instantiation_is_forbidden": True,
    "unknown_creator_or_required_relation_blocks_packaging": True,
    "module_plan_membership_is_output_not_seed_assumption": True,
}


class ClaimContractError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise ClaimContractError("repository root not found")


def _identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ClaimContractError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise ClaimContractError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(data) != before.st_size:
        raise ClaimContractError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def source_text(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClaimContractError(f"{label} is not UTF-8") from exc


def require_tokens(text: str, label: str, tokens: Iterable[str]) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise ClaimContractError(f"{label} source contract missing: {missing}")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def authority_sha256(authority: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(authority)).hexdigest()


def proposed_authority() -> dict[str, Any]:
    return {
        "relationship_fixed_point": copy.deepcopy(RELATIONSHIP_FIXED_POINT),
        "evaluability_preconditions": copy.deepcopy(
            list(EVALUABILITY_PRECONDITIONS)
        ),
        "claims": copy.deepcopy(list(CLAIMS)),
        "must_bind_consumers": copy.deepcopy(list(CONSUMERS)),
        "claim_consumer_edges": copy.deepcopy(list(CLAIM_CONSUMER_EDGES)),
        "excluded_adjacent_consumers": copy.deepcopy(
            list(EXCLUDED_ADJACENT_CONSUMERS)
        ),
        "review_triggers": list(REVIEW_TRIGGERS),
    }


def validate_authority(authority: Any) -> dict[str, Any]:
    if not isinstance(authority, dict) or set(authority) != {
        "relationship_fixed_point",
        "evaluability_preconditions",
        "claims",
        "must_bind_consumers",
        "claim_consumer_edges",
        "excluded_adjacent_consumers",
        "review_triggers",
    }:
        raise ClaimContractError("must-bind authority shape differs")
    preconditions = authority["evaluability_preconditions"]
    claims = authority["claims"]
    consumers = authority["must_bind_consumers"]
    edges = authority["claim_consumer_edges"]
    exclusions = authority["excluded_adjacent_consumers"]
    triggers = authority["review_triggers"]
    fixed_point = authority["relationship_fixed_point"]
    if fixed_point != RELATIONSHIP_FIXED_POINT:
        raise ClaimContractError("relationship fixed-point semantics differ")
    list_fields = (
        preconditions, claims, consumers, edges, exclusions, triggers
    )
    if not all(isinstance(value, list) and value for value in list_fields):
        raise ClaimContractError("must-bind authority contains an empty collection")

    precondition_ids: set[str] = set()
    for row in preconditions:
        if not isinstance(row, dict) or set(row) != {
            "id", "statement", "current_status"
        }:
            raise ClaimContractError("evaluability-precondition shape differs")
        if any(not isinstance(row[key], str) or not row[key].strip() for key in row):
            raise ClaimContractError("evaluability-precondition field is empty")
        if row["id"] in precondition_ids:
            raise ClaimContractError("duplicate evaluability-precondition id")
        precondition_ids.add(row["id"])

    claim_ids: set[str] = set()
    referenced_preconditions: set[str] = set()
    for row in claims:
        if not isinstance(row, dict) or set(row) != {
            "id", "statement", "result_scope", "evaluability_preconditions"
        }:
            raise ClaimContractError("claim shape differs")
        if any(
            not isinstance(row[key], str) or not row[key].strip()
            for key in ("id", "statement", "result_scope")
        ):
            raise ClaimContractError("claim field is empty")
        required = row["evaluability_preconditions"]
        if (
            not isinstance(required, (list, tuple))
            or not required
            or any(not isinstance(value, str) or not value for value in required)
            or len(set(required)) != len(required)
            or not set(required).issubset(precondition_ids)
        ):
            raise ClaimContractError(
                "claim evaluability-precondition coverage differs"
            )
        referenced_preconditions.update(required)
        if row["id"] in claim_ids:
            raise ClaimContractError("duplicate claim id")
        claim_ids.add(row["id"])
    if referenced_preconditions != precondition_ids:
        raise ClaimContractError("one or more evaluability preconditions are orphaned")

    consumer_ids: set[str] = set()
    for row in consumers:
        if not isinstance(row, dict) or set(row) != {
            "id", "device_identity", "expected_driver", "root_kind", "root_reason"
        }:
            raise ClaimContractError("consumer shape differs")
        if any(not isinstance(row[key], str) or not row[key].strip() for key in row):
            raise ClaimContractError("consumer field is empty")
        if row["id"] in consumer_ids:
            raise ClaimContractError("duplicate consumer id")
        if row["root_kind"] not in {
            "experiment_endpoint",
            "device_instantiator",
            "driver_consumed_dependency",
        }:
            raise ClaimContractError("must-bind root kind differs")
        consumer_ids.add(row["id"])

    edge_pairs: set[tuple[str, str]] = set()
    claims_with_edges: set[str] = set()
    consumers_with_edges: set[str] = set()
    for row in edges:
        if not isinstance(row, dict) or set(row) != {
            "claim", "consumer", "failure_consequence"
        }:
            raise ClaimContractError("claim-consumer edge shape differs")
        if row["claim"] not in claim_ids or row["consumer"] not in consumer_ids:
            raise ClaimContractError("claim-consumer edge has an unknown endpoint")
        if not isinstance(row["failure_consequence"], str) or not row[
            "failure_consequence"
        ].strip():
            raise ClaimContractError("claim-consumer failure consequence is empty")
        pair = (row["claim"], row["consumer"])
        if pair in edge_pairs:
            raise ClaimContractError("duplicate claim-consumer edge")
        edge_pairs.add(pair)
        claims_with_edges.add(row["claim"])
        consumers_with_edges.add(row["consumer"])
    if claims_with_edges != claim_ids:
        raise ClaimContractError("one or more claims lack a consumer analysis")
    if consumers_with_edges != consumer_ids:
        raise ClaimContractError("one or more consumers lack a causal claim")

    for row in exclusions:
        if not isinstance(row, dict) or set(row) != {"identity", "reason"}:
            raise ClaimContractError("excluded-consumer shape differs")
        if any(not isinstance(row[key], str) or not row[key].strip() for key in row):
            raise ClaimContractError("excluded-consumer reason is empty")
    if len(triggers) != len(REVIEW_TRIGGERS) or any(
        not isinstance(value, str) or not value.strip() for value in triggers
    ):
        raise ClaimContractError("review-trigger coverage differs")
    return copy.deepcopy(authority)


def audit_sources(
    runtime: str,
    diagnostic: str,
    surface: str,
    live: str,
    qup: str,
    i2c_driver: str,
    i2c_core: str,
    i2c_of: str,
    of_platform: str,
    qup_dts: str,
    spmi_arb: str,
    spmi_core: str,
    spmi_pmic: str,
    pm8350c_dts: str,
) -> dict[str, Any]:
    require_tokens(
        runtime,
        "P3.16 runtime",
        (
            '#define P316_TARGET_I2C_DEVICE "994000.i2c"',
            '{"9c0000.qcom,qupv3_0_geni_se", "qupv3_geni_se", 1U}',
            '{"994000.i2c", "i2c_geni", 1U}',
            "rc = p260_bind_udc();",
            "p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);",
            'p282_copy_path_part(\n            topology->adapter_path',
            'entry->d_name, length, value.adapter_name, "0066"',
            'static const char exact[] = "maxim,max77705"',
            "p316_observe_diagnostic(tty_fd, &topology, &observation)",
        ),
    )
    gadget_bind = runtime.index("rc = p260_bind_udc();")
    gadget_fence = runtime.index(
        "p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);"
    )
    diagnostic_dispatch = runtime.index(
        "p316_observe_diagnostic(tty_fd, &topology, &observation)"
    )
    if not gadget_bind < gadget_fence < diagnostic_dispatch:
        raise ClaimContractError(
            "device gadget-path gate is not before diagnostic dispatch"
        )
    require_tokens(
        diagnostic,
        "Max77705 diagnostic",
        (
            "if (parent->addr != S22PLUS_MAX77705_PARENT_ADDR)",
            "devm_i2c_new_dummy_device(&parent->dev, parent->adapter,",
            "rc = s22plus_max77705_diag_run(parent, muic,",
            ".compatible = S22PLUS_MAX77705_PARENT_COMPATIBLE",
            ".name = \"s22plus_max77705_mux_diag\"",
            ".probe_type = PROBE_FORCE_SYNCHRONOUS",
        ),
    )
    require_tokens(
        surface,
        "Max77705 result contract",
        (
            '"pre_non_0x09_post1_post2_0x09_attach": "strong MUX-causal support"',
            '"pre_non_0x09_post1_post2_0x09_silent"',
            '"pre_0x09_post1_post2_0x09_attach"',
            '"post1_0x09_post2_non_0x09"',
            '"host_fact_without_complete_device_result"',
            '"control1_readback_proves_physical_switch_contact": False',
            '"msm-geni-se.ko"',
            '"gpi.ko"',
            '"i2c-msm-geni.ko"',
        ),
    )
    require_tokens(
        live,
        "Process-v2 live runner",
        (
            "trace_session = _P300UsbTraceSession(prepared, journal)",
            "trace_session.start()",
            "backend.request_download(prepared)",
        ),
    )
    if not (
        live.index("trace_session.start()")
        < live.index("backend.request_download(prepared)")
    ):
        raise ClaimContractError("host sidecar arm is not before candidate request")
    require_tokens(
        qup,
        "QUPv3 wrapper driver",
        (
            "static const struct of_device_id geni_se_dt_match[] =",
            '{ .compatible = "qcom,qupv3-geni-se", }',
            '.name = "qupv3_geni_se"',
            ".probe = geni_se_probe",
            "geni_se_dev = dev_get_drvdata(rsc->wrapper_dev);",
            "return -EPROBE_DEFER;",
        ),
    )
    require_tokens(
        i2c_driver,
        "GENI I2C driver",
        (
            'wrapper_ph_node = of_parse_phandle(pdev->dev.of_node,',
            '"qcom,wrapper-core", 0);',
            "wrapper_pdev = of_find_device_by_node(wrapper_ph_node);",
            "gi2c->i2c_rsc.wrapper_dev = &wrapper_pdev->dev;",
            "ret = geni_se_resources_init(&gi2c->i2c_rsc, I2C_CORE2X_VOTE,",
            "gi2c->adap.dev.of_node = pdev->dev.of_node;",
            "ret = i2c_add_adapter(&gi2c->adap);",
            '.name = "i2c_geni"',
            ".probe  = geni_i2c_probe",
        ),
    )
    require_tokens(
        i2c_core,
        "I2C core",
        (
            "static int i2c_register_adapter(struct i2c_adapter *adap)",
            "of_i2c_register_devices(adap);",
        ),
    )
    require_tokens(
        i2c_of,
        "I2C OF core",
        (
            "void of_i2c_register_devices(struct i2c_adapter *adap)",
            "for_each_available_child_of_node(bus, node)",
            "client = of_i2c_register_device(adap, node);",
            "client = i2c_new_client_device(adap, &info);",
        ),
    )
    require_tokens(
        of_platform,
        "OF platform default population",
        (
            "static int __init of_platform_default_populate_init(void)",
            "of_platform_default_populate(NULL, NULL, NULL);",
            "arch_initcall_sync(of_platform_default_populate_init);",
        ),
    )
    require_tokens(
        qup_dts,
        "Waipio QUPv3 DT",
        (
            "qupv3_0: qcom,qupv3_0_geni_se@9c0000 {",
            'compatible = "qcom,qupv3-geni-se";',
            "qupv3_se5_i2c: i2c@994000 {",
            'compatible = "qcom,i2c-geni";',
            "qcom,wrapper-core = <&qupv3_0>;",
        ),
    )
    wrapper_start = qup_dts.index(
        "qupv3_0: qcom,qupv3_0_geni_se@9c0000 {"
    )
    wrapper_end = qup_dts.index("};", wrapper_start)
    controller_start = qup_dts.index("qupv3_se5_i2c: i2c@994000 {")
    if controller_start < wrapper_end or controller_start <= wrapper_start:
        raise ClaimContractError(
            "Waipio DT does not place wrapper and 994000.i2c as siblings"
        )
    require_tokens(
        spmi_arb,
        "SPMI PMIC arbiter driver",
        (
            "static int spmi_pmic_arb_probe(struct platform_device *pdev)",
            "ctrl = spmi_controller_alloc(&pdev->dev, sizeof(*pmic_arb));",
            "err = spmi_controller_add(ctrl);",
            '{ .compatible = "qcom,spmi-pmic-arb", }',
            ".probe\t\t= spmi_pmic_arb_probe",
        ),
    )
    require_tokens(
        spmi_core,
        "SPMI core",
        (
            "static void of_spmi_register_devices(struct spmi_controller *ctrl)",
            "for_each_available_child_of_node(ctrl->dev.of_node, node)",
            "sdev = spmi_device_alloc(ctrl);",
            "err = spmi_device_add(sdev);",
            "of_spmi_register_devices(ctrl);",
        ),
    )
    require_tokens(
        spmi_pmic,
        "SPMI PMIC MFD driver",
        (
            '{ .compatible = "qcom,spmi-pmic", .data = (void *)COMMON_SUBTYPE }',
            "static int pmic_spmi_probe(struct spmi_device *sdev)",
            "return devm_of_platform_populate(&sdev->dev);",
            ".probe = pmic_spmi_probe",
        ),
    )
    require_tokens(
        pm8350c_dts,
        "PM8350C DT",
        (
            "&spmi_bus {",
            "qcom,pm8350c@2 {",
            'compatible = "qcom,spmi-pmic";',
            "pm8350c_gpios: pinctrl@8800 {",
            'compatible = "qcom,pm8350c-gpio";',
        ),
    )
    return {
        "qupv3_wrapper_and_994000_i2c_are_exact_dt_siblings": True,
        "of_platform_default_population_instantiates_both_siblings": True,
        "i2c_probe_consumes_wrapper_core_reference": True,
        "unbound_wrapper_forces_i2c_probe_defer_before_adapter": True,
        "i2c_controller_probe_registers_adapter": True,
        "adapter_registration_instantiates_exact_dt_i2c_children": True,
        "spmi_arbiter_registration_enumerates_pm8350c_device": True,
        "spmi_pmic_probe_populates_pm8350c_gpio_child": True,
        "all_three_relation_families_require_recursive_closure": True,
        "runtime_resolves_adapter_beneath_exact_platform_device": True,
        "runtime_requires_exact_address_and_compatible": True,
        "diagnostic_probe_is_only_control1_evidence_producer": True,
        "current_plan_names_wrapper_dma_and_i2c_modules": True,
        "host_fact_without_complete_device_result_is_noncausal": True,
        "physical_interpretation_ceiling_preserved": True,
        "gadget_path_order_is_source_bound_but_successor_witness_is_pending": True,
        "host_sidecar_arm_precedes_candidate_request": True,
    }


def build_contract(
    *, extractor_data: bytes, runtime_data: bytes,
    diagnostic_data: bytes, surface_data: bytes, live_data: bytes,
    qup_data: bytes, i2c_driver_data: bytes, i2c_core_data: bytes,
    i2c_of_data: bytes, of_platform_data: bytes, qup_dts_data: bytes,
    spmi_arb_data: bytes, spmi_core_data: bytes, spmi_pmic_data: bytes,
    pm8350c_dts_data: bytes,
    authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = validate_authority(
        proposed_authority() if authority is None else authority
    )
    selected_sha256 = authority_sha256(selected)
    if selected_sha256 != CLAIM_AUTHORITY_SHA256:
        raise ClaimContractError("claim authority differs from registered hash")
    source_audit = audit_sources(
        source_text(runtime_data, "P3.16 runtime"),
        source_text(diagnostic_data, "Max77705 diagnostic"),
        source_text(surface_data, "Max77705 surface contract"),
        source_text(live_data, "Process-v2 live runner"),
        source_text(qup_data, "QUPv3 wrapper driver"),
        source_text(i2c_driver_data, "GENI I2C driver"),
        source_text(i2c_core_data, "I2C core"),
        source_text(i2c_of_data, "I2C OF core"),
        source_text(of_platform_data, "OF platform core"),
        source_text(qup_dts_data, "Waipio QUPv3 DT"),
        source_text(spmi_arb_data, "SPMI PMIC arbiter driver"),
        source_text(spmi_core_data, "SPMI core"),
        source_text(spmi_pmic_data, "SPMI PMIC MFD driver"),
        source_text(pm8350c_dts_data, "PM8350C DT"),
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "host_only": True,
        "human_causal_review": HUMAN_CAUSAL_REVIEW,
        "human_review_binding": {
            "superseded_reviewed_claim_authority_sha256": (
                SUPERSEDED_REVIEWED_CLAIM_AUTHORITY_SHA256
            ),
            "invalidation_reason": (
                "the exact merged DT places the wrapper and 994000.i2c as "
                "siblings; the I2C driver consumes qcom,wrapper-core directly "
                "instead of the wrapper instantiating the controller"
            ),
            "reviewed_claim_authority_sha256": CLAIM_AUTHORITY_SHA256,
            "scope": (
                "corrected must-bind causal authority, third relation family, "
                "and three-family fixed-point definition"
            ),
            "review_outcome": "APPROVED",
            "review_date": "2026-08-12",
            "candidate_authority": False,
        },
        "machine_validation_scope": (
            "coverage, referential integrity, source seam presence, and hash "
            "drift only; causal truth is deliberately not machine-proved"
        ),
        "authority": {
            "extractor_source": receipt(extractor_data),
            "runtime_source": receipt(runtime_data),
            "diagnostic_source": receipt(diagnostic_data),
            "surface_contract_source": receipt(surface_data),
            "process_v2_live_source": receipt(live_data),
            "qupv3_wrapper_driver_source": receipt(qup_data),
            "geni_i2c_driver_source": receipt(i2c_driver_data),
            "i2c_core_source": receipt(i2c_core_data),
            "i2c_of_source": receipt(i2c_of_data),
            "of_platform_source": receipt(of_platform_data),
            "waipio_qupv3_dt_source": receipt(qup_dts_data),
            "spmi_pmic_arbiter_driver_source": receipt(spmi_arb_data),
            "spmi_core_source": receipt(spmi_core_data),
            "spmi_pmic_mfd_driver_source": receipt(spmi_pmic_data),
            "pm8350c_dt_source": receipt(pm8350c_dts_data),
        },
        "claim_authority": selected,
        "claim_authority_sha256": selected_sha256,
        "counts": {
            "claims": len(selected["claims"]),
            "evaluability_preconditions": len(
                selected["evaluability_preconditions"]
            ),
            "must_bind_consumers": len(selected["must_bind_consumers"]),
            "claim_consumer_edges": len(selected["claim_consumer_edges"]),
            "excluded_adjacent_consumers": len(
                selected["excluded_adjacent_consumers"]
            ),
            "review_triggers": len(selected["review_triggers"]),
        },
        "source_audit": source_audit,
        "contract": {
            "claim_membership_is_human_causal_judgment": True,
            "machine_enforces_coverage_not_truth": True,
            "evaluability_precondition_presence_is_machine_checked": True,
            "evaluability_precondition_truth_requires_separate_qualification": True,
            "derived_suppliers_must_not_be_seeded_as_endpoint_roots": True,
            "uninstantiated_consumer_requires_explicit_instantiator_root": True,
            "registered_relationship_families": [
                "FW_DEVLINK_DT_SUPPLIER_CLOSURE",
                "DEVICE_INSTANTIATION_CLOSURE",
                "DRIVER_CONSUMED_DT_REFERENCE_CLOSURE",
            ],
            "root_hash_change_invalidates_downstream_closure": True,
            "all_registered_families_iterate_to_fixed_point": True,
            "every_family_output_reenters_every_family": True,
            "arming_precondition_is_not_expanded": True,
            "p317_candidate_ready": False,
            "device_contact": False,
            "live_authority": False,
        },
    }


def encode_contract(result: dict[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=root / DEFAULT_RUNTIME_SOURCE)
    parser.add_argument(
        "--diagnostic", type=Path, default=root / DEFAULT_DIAGNOSTIC_SOURCE
    )
    parser.add_argument("--surface", type=Path, default=root / DEFAULT_SURFACE_SOURCE)
    parser.add_argument("--live", type=Path, default=root / DEFAULT_LIVE_SOURCE)
    parser.add_argument("--qup-source", type=Path, default=root / DEFAULT_QUP_SOURCE)
    parser.add_argument(
        "--i2c-driver-source", type=Path, default=root / DEFAULT_I2C_DRIVER_SOURCE
    )
    parser.add_argument(
        "--i2c-core-source", type=Path, default=root / DEFAULT_I2C_CORE_SOURCE
    )
    parser.add_argument(
        "--i2c-of-source", type=Path, default=root / DEFAULT_I2C_OF_SOURCE
    )
    parser.add_argument(
        "--of-platform-source",
        type=Path,
        default=root / DEFAULT_OF_PLATFORM_SOURCE,
    )
    parser.add_argument(
        "--qup-dts-source", type=Path, default=root / DEFAULT_QUP_DTS_SOURCE
    )
    parser.add_argument(
        "--spmi-arb-source", type=Path, default=root / DEFAULT_SPMI_ARB_SOURCE
    )
    parser.add_argument(
        "--spmi-core-source", type=Path, default=root / DEFAULT_SPMI_CORE_SOURCE
    )
    parser.add_argument(
        "--spmi-pmic-source", type=Path, default=root / DEFAULT_SPMI_PMIC_SOURCE
    )
    parser.add_argument(
        "--pm8350c-dts-source", type=Path, default=root / DEFAULT_PM8350C_DTS_SOURCE
    )
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_contract(
        extractor_data=stable_read(
            Path(__file__).resolve(), "claim-contract source", 2 * 1024 * 1024
        ),
        runtime_data=stable_read(args.runtime, "P3.16 runtime", 2 * 1024 * 1024),
        diagnostic_data=stable_read(
            args.diagnostic, "Max77705 diagnostic", 2 * 1024 * 1024
        ),
        surface_data=stable_read(
            args.surface, "Max77705 surface contract", 4 * 1024 * 1024
        ),
        live_data=stable_read(
            args.live, "Process-v2 live runner", 4 * 1024 * 1024
        ),
        qup_data=stable_read(
            args.qup_source, "QUPv3 wrapper driver", 4 * 1024 * 1024
        ),
        i2c_driver_data=stable_read(
            args.i2c_driver_source, "GENI I2C driver", 4 * 1024 * 1024
        ),
        i2c_core_data=stable_read(
            args.i2c_core_source, "I2C core", 4 * 1024 * 1024
        ),
        i2c_of_data=stable_read(
            args.i2c_of_source, "I2C OF core", 2 * 1024 * 1024
        ),
        of_platform_data=stable_read(
            args.of_platform_source, "OF platform core", 2 * 1024 * 1024
        ),
        qup_dts_data=stable_read(
            args.qup_dts_source, "Waipio QUPv3 DT", 4 * 1024 * 1024
        ),
        spmi_arb_data=stable_read(
            args.spmi_arb_source, "SPMI PMIC arbiter driver", 4 * 1024 * 1024
        ),
        spmi_core_data=stable_read(
            args.spmi_core_source, "SPMI core", 2 * 1024 * 1024
        ),
        spmi_pmic_data=stable_read(
            args.spmi_pmic_source, "SPMI PMIC MFD driver", 2 * 1024 * 1024
        ),
        pm8350c_dts_data=stable_read(
            args.pm8350c_dts_source, "PM8350C DT", 4 * 1024 * 1024
        ),
    )
    encoded = encode_contract(result)
    if args.out is None:
        __import__("sys").stdout.buffer.write(encoded)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
