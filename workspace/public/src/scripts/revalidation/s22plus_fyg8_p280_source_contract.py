#!/usr/bin/env python3
"""Versioned P2.80 parent-worker and pull-up source contract."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p260_source_contract as p260
import s22plus_fyg8_p280_contract_spec as spec
import s22plus_fyg8_p280_e1_decoder as decoder
import s22plus_fyg8_p280_trace_contract as trace_contract


CONTRACT_ID = "s22plus-fyg8-p280-parent-pullup-discriminator-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P280-PARENT-PULLUP-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p280_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p280_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P280_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p280_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P280_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P280_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P280_DISCRIMINATOR_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P280-SOURCE-CHECK-V1"
).digest()[:16]

DEFAULT_DWC3_MSM_MODULE = Path(
    "workspace/private/inputs/s22plus_firmware/"
    "S906NKSS7FYG8_SKC/extracted-images/ramdisk-list/vendor/extract/"
    "lib/modules/dwc3-msm.ko"
)

MODULE_PLAN_COUNT = p260.MODULE_PLAN_COUNT
GENERATED_KEYS = p260.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p260.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p280_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p280_e3_runtime.c",
    "plan_header": "s22plus_fyg8_p280_e3_plan.h",
    "e3_runtime_include": "s22plus_fyg8_p280_e3_runtime.inc.c",
    "p260_e3_runtime_include": "s22plus_fyg8_p260_e3_runtime.inc.c",
    "trace_descriptor_header": "s22plus_fyg8_p280_trace_descriptor.h",
}

COMMON_SOURCE_PATHS = {
    f"p260_{name}": path
    for name, path in p260.COMMON_SOURCE_PATHS.items()
}
COMMON_SOURCE_PATHS.update(
    {
        "source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p280_source_contract.py"
        ),
        "contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p280_contract_spec.py"
        ),
        "decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p280_e1_decoder.py"
        ),
        "trace_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p280_trace_contract.py"
        ),
        "e3_runtime_include": Path(
            "workspace/public/src/native-init/"
            "s22plus_fyg8_p280_e3_runtime.inc.c"
        ),
        "p260_e3_runtime_include": Path(
            "workspace/public/src/native-init/"
            "s22plus_fyg8_p260_e3_runtime.inc.c"
        ),
    }
)
SOURCE_KEYS = frozenset(
    (*GENERATED_KEYS, *COMMON_SOURCE_PATHS, "trace_descriptor_header")
)
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
FAILURE_REACHABLE_VARIANTS = p260.REACHABLE_VARIANTS + sum(
    len(detail.stages)
    for detail in spec.DIAGNOSTIC_DETAILS
    if spec.OUTCOME_FAILURE in detail.outcomes
)
WARNING_VARIANTS = sum(
    len(detail.stages)
    for detail in spec.DIAGNOSTIC_DETAILS
    if spec.OUTCOME_PROGRESS in detail.outcomes
)
REACHABLE_VARIANTS = FAILURE_REACHABLE_VARIANTS + WARNING_VARIANTS


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P280 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p260.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P280


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return p260.candidate_observer(run_id)


def _validate_runtime_authority_source(include: bytes) -> None:
    for name, expected_value in spec.RUNTIME_EXTERNAL_CONSTANTS:
        pattern = re.compile(
            rb"^#define[ \t]+"
            + re.escape(name.encode("ascii"))
            + rb"[ \t]+(0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)"
            + rb"[lLuU]*[ \t]*$",
            re.MULTILINE,
        )
        matches = pattern.findall(include)
        if len(matches) != 1:
            raise SourceContractError(
                f"P2.80 runtime constant {name} cardinality drifted"
            )
        literal = matches[0].decode("ascii")
        if literal.lower().startswith("0x"):
            actual_value = int(literal, 16)
        elif len(literal) > 1 and literal.startswith("0"):
            actual_value = int(literal, 8)
        else:
            actual_value = int(literal, 10)
        if actual_value != expected_value:
            raise SourceContractError(
                f"P2.80 runtime constant {name} value drifted"
            )

    for forbidden in (
        b'"/sys/kernel/debug/tracing',
        b'"/sys/kernel/tracing/current_tracer"',
        b'"/sys/kernel/tracing/set_ftrace_filter"',
        b'"function_graph"',
        b'"function"',
    ):
        if forbidden in include:
            raise SourceContractError(
                "P2.80 runtime broadened beyond exact Kprobe authority"
            )

    tracefs_paths = {
        value.decode("ascii")
        for value in re.findall(
            rb'"(/sys/kernel/tracing[^"\\]*)"',
            include,
        )
    }
    if tracefs_paths != set(spec.TRACEFS_ABSOLUTE_PATHS):
        raise SourceContractError("P2.80 tracefs absolute path set drifted")

    for name, token, expected_count in spec.RUNTIME_OPERATION_TOKENS:
        count = include.count(token.encode("ascii"))
        if count != expected_count:
            raise SourceContractError(
                f"P2.80 runtime operation {name} cardinality drifted"
            )

def _replace_exact(
    data: bytes,
    old: bytes,
    new: bytes,
    *,
    count: int = 1,
    label: str,
) -> bytes:
    actual = data.count(old)
    if actual != count:
        raise SourceContractError(
            f"{label} replacement count {actual}, expected {count}"
        )
    return data.replace(old, new)


def _checkpoint_exact_detail_table() -> bytes:
    lines = [
        "struct p280_checkpoint_detail_rule {",
        "    uint16_t value;",
        "    uint8_t outcome;",
        "    uint8_t stage_first;",
        "    uint8_t stage_last;",
        "};",
        "",
        "static const struct p280_checkpoint_detail_rule",
        "k_p280_checkpoint_details[] = {",
    ]
    for detail in spec.DIAGNOSTIC_DETAILS:
        if len(detail.outcomes) != 1:
            raise SourceContractError("P2.80 detail outcome is not singular")
        lines.append(
            "    {"
            f"0x{detail.value:03x}U, {detail.outcomes[0]}U, "
            f"0x{min(detail.stages):02x}U, 0x{max(detail.stages):02x}U"
            "},"
        )
    lines.extend(
        (
            "};",
            "",
            "static int p280_exact_detail_allowed(",
            "    uint8_t stage, uint8_t outcome, uint16_t detail) {",
            "    for (size_t index = 0;",
            "         index < sizeof(k_p280_checkpoint_details) /",
            "             sizeof(k_p280_checkpoint_details[0]);",
            "         ++index) {",
            "        const struct p280_checkpoint_detail_rule *rule =",
            "            &k_p280_checkpoint_details[index];",
            "        if (detail == rule->value && outcome == rule->outcome &&",
            "            stage >= rule->stage_first &&",
            "            stage <= rule->stage_last) {",
            "            return 1;",
            "        }",
            "    }",
            "    return 0;",
            "}",
            "",
        )
    )
    return ("\n".join(lines) + "\n").encode("ascii")


def _checkpoint_detail_helper() -> bytes:
    base = p260._checkpoint_detail_helper()
    anchor = (
        b"static int p252_detail_allowed(\n"
        b"    uint8_t stage, uint8_t outcome, uint16_t detail) {\n"
    )
    value = _replace_exact(
        base,
        anchor,
        _checkpoint_exact_detail_table() + anchor,
        label="P2.80 checkpoint exact detail table",
    )
    insertion = (
        b"    if (step == NULL) {\n"
        b"        return 0;\n"
        b"    }\n"
    )
    replacement = insertion + (
        b"    if (p280_exact_detail_allowed(stage, outcome, detail)) {\n"
        b"        return 1;\n"
        b"    }\n"
        b"    if (detail >= 0xb00U) {\n"
        b"        return 0;\n"
        b"    }\n"
    )
    return _replace_exact(
        value,
        insertion,
        replacement,
        label="P2.80 checkpoint exact detail dispatch",
    )


def _kernel_detail_validator() -> bytes:
    lines = [
        "struct s22_fyg8_p280_detail_rule {",
        "\tu16 value;",
        "\tu8 outcome;",
        "\tu8 stage_first;",
        "\tu8 stage_last;",
        "};",
        "",
        "static const struct s22_fyg8_p280_detail_rule",
        "s22_fyg8_p280_details[] __used = {",
    ]
    for detail in spec.DIAGNOSTIC_DETAILS:
        if len(detail.outcomes) != 1:
            raise SourceContractError("P2.80 kernel detail outcome drifted")
        lines.append(
            "\t{"
            f"0x{detail.value:03x}, {detail.outcomes[0]}, "
            f"0x{min(detail.stages):02x}, 0x{max(detail.stages):02x}"
            "},"
        )
    lines.extend(
        (
            "};",
            "",
            "static noinline __used bool s22_fyg8_p280_detail_allowed(",
            "\t\tu8 stage, u8 outcome, u16 detail)",
            "{",
            "\tsize_t index;",
            "",
            "\tfor (index = 0; index < ARRAY_SIZE(s22_fyg8_p280_details);",
            "\t\t\t++index) {",
            "\t\tconst struct s22_fyg8_p280_detail_rule *rule =",
            "\t\t\t&s22_fyg8_p280_details[index];",
            "\t\tif (detail == READ_ONCE(rule->value) &&",
            "\t\t\toutcome == READ_ONCE(rule->outcome) &&",
            "\t\t\tstage >= READ_ONCE(rule->stage_first) &&",
            "\t\t\tstage <= READ_ONCE(rule->stage_last))",
            "\t\t\treturn true;",
            "\t}",
            "\treturn false;",
            "}",
            "",
            "static noinline __used bool s22_fyg8_e1_detail_allowed(",
            "\t\tu8 profile, size_t ordinal, size_t count,",
            "\t\tu8 outcome, u16 detail)",
            "{",
            "\tu8 gate_index;",
            "\tu8 encoded_index;",
            "\tsize_t index;",
            "\tbool e3_local;",
            "",
            "\tif (profile == S22_FYG8_E1_PROFILE_E2 && ordinal < count &&",
            "\t\t\ts22_fyg8_p280_detail_allowed(",
            "\t\t\t\tREAD_ONCE(s22_fyg8_e2_sequence[ordinal]),",
            "\t\t\t\toutcome, detail))",
            "\t\treturn true;",
            "\tif (detail >= 0xb00)",
            "\t\treturn false;",
            "\tif (ordinal + 1 == count)",
            "\t\treturn outcome == S22_FYG8_E1_SUCCESS && !detail;",
            "\tif (outcome == S22_FYG8_E1_PROGRESS)",
            "\t\treturn !detail;",
            "\tif (outcome != S22_FYG8_E1_FAILURE || !detail)",
            "\t\treturn false;",
            "\tif (profile != S22_FYG8_E1_PROFILE_E2)",
            "\t\treturn detail <= 4095;",
            "\tif (detail <= 0x7ff)",
            "\t\treturn true;",
            "\tif (ordinal >= count)",
            "\t\treturn false;",
            "\te3_local = ordinal >= 80 &&",
            "\t\tordinal < 88;",
            "\tencoded_index = detail & 0xff;",
            f"\tif (encoded_index >= {spec.GATE_COUNT})",
            "\t\treturn false;",
            "\tif (e3_local)",
            "\t\treturn (detail >= 0x800 && detail <= 0x8ff) ||",
            "\t\t\t(detail >= 0x900 && detail <= 0x9ff);",
            "\tif (s22_fyg8_e2_kinds[ordinal] == 1) {",
            "\t\tgate_index = s22_fyg8_e2_items[ordinal];",
            "\t\tif (detail >= 0x800 && detail <= 0x8ff)",
            "\t\t\treturn encoded_index < gate_index;",
            "\t\tif (detail >= 0x900 && detail <= 0x9ff)",
            "\t\t\treturn encoded_index <= gate_index;",
            "\t}",
            "\tfor (index = 0;",
            "\t\t\tindex < ARRAY_SIZE(s22_fyg8_e2_classifier_stages);",
            "\t\t\t++index) {",
            "\t\tif (s22_fyg8_e2_sequence[ordinal] ==",
            "\t\t\t\tREAD_ONCE(s22_fyg8_e2_classifier_stages[index]) &&",
            "\t\t\t\tdetail ==",
            "\t\t\t\tREAD_ONCE(s22_fyg8_e2_classifier_details[index]))",
            "\t\t\treturn true;",
            "\t}",
            "\treturn false;",
            "}",
            "",
        )
    )
    return p252._kernel_prefixed(lines)


def _progress_detail_api() -> bytes:
    return (
        b"long s22_r4w1e_checkpoint_progress_detail(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
        b"    uint8_t stage,\n"
        b"    uint8_t item_index,\n"
        b"    uint16_t detail) {\n"
        b"    return publish(\n"
        b"        client, stage, S22_P233_OUTCOME_PROGRESS, "
        b"item_index, detail);\n"
        b"}\n\n"
    )


def _transform_checkpoint(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p260._checkpoint_detail_helper(),
        _checkpoint_detail_helper(),
        label="P2.80 checkpoint detail validator",
    )
    anchor = (
        b"long s22_r4w1e_checkpoint_failure(\n"
        b"    struct s22_r4w1e_checkpoint_client *client,\n"
    )
    return _replace_exact(
        value,
        anchor,
        _progress_detail_api() + anchor,
        label="P2.80 progress-detail publisher",
    )


def _transform_patch(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p260._kernel_detail_validator(),
        _kernel_detail_validator(),
        label="P2.80 kernel detail validator",
    )
    return p252._recount_kernel_patch_hunks(value)


def _transform_runtime(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b'#include "s22plus_fyg8_p260_e3_plan.h"',
        b'#include "s22plus_fyg8_p280_e3_plan.h"',
        label="P2.80 runtime plan include",
    )
    value = _replace_exact(
        value,
        b'#include "s22plus_fyg8_p260_e3_runtime.inc.c"',
        b'#include "s22plus_fyg8_p280_e3_runtime.inc.c"',
        label="P2.80 runtime include",
    )
    return _replace_exact(
        value,
        b"    p260_e3_run();\n",
        b"    p280_e3_run();\n",
        label="P2.80 runtime handoff",
    )


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    historical = p260.generate(repository)
    return {
        "plan": historical["plan"],
        "runtime": _transform_runtime(historical["runtime"]),
        "checkpoint": _transform_checkpoint(historical["checkpoint"]),
        "patch": _transform_patch(historical["patch"]),
    }


def trace_descriptor_header(root: Path) -> bytes:
    derived = trace_contract.derive_module_contract(
        module=root / DEFAULT_DWC3_MSM_MODULE
    )
    return trace_contract.render_c_header(derived)


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.80 source {name}"
        )
    result["trace_descriptor_header"] = trace_descriptor_header(root)
    _validate_runtime_authority_source(result["e3_runtime_include"])
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.80 source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def _generated_semantics(
    generated: dict[str, bytes], historical: dict[str, bytes]
) -> dict[str, Any]:
    if generated["plan"] != historical["plan"]:
        raise SourceContractError("P2.80 changed the P2.60 module plan")
    runtime = generated["runtime"]
    checkpoint = generated["checkpoint"]
    patch = generated["patch"]
    required_runtime = (
        b'#include "s22plus_fyg8_p280_e3_runtime.inc.c"',
        b"p280_e3_run();",
    )
    if any(runtime.count(token) != 1 for token in required_runtime):
        raise SourceContractError("P2.80 runtime handoff drifted")
    required_checkpoint = (
        b"k_p280_checkpoint_details[]",
        b"s22_r4w1e_checkpoint_progress_detail(",
        b"if (detail >= 0xb00U)",
    )
    if any(checkpoint.count(token) != 1 for token in required_checkpoint):
        raise SourceContractError("P2.80 checkpoint contract drifted")
    required_patch = (
        (b"s22_fyg8_p280_details[] __used", 1),
        (b"s22_fyg8_p280_detail_allowed(", 2),
        (b"if (detail >= 0xb00)", 1),
    )
    if any(
        patch.count(token) != count for token, count in required_patch
    ):
        raise SourceContractError("P2.80 kernel contract drifted")
    if b"p260_e3_run();" in runtime:
        raise SourceContractError("P2.80 retained the P2.60 handoff")
    return {
        "p260_plan_preserved": True,
        "step_count": len(spec.STEPS),
        "terminal_generation": spec.TERMINAL_ORDINAL + 1,
        "runtime_handoff_once": True,
        "exact_detail_count": len(spec.DIAGNOSTIC_DETAILS),
        "verified": True,
    }


def _audit_userspace(
    root: Path,
    generated: dict[str, bytes],
    source: dict[str, bytes],
    directory: Path,
) -> dict[str, Any]:
    for key in (
        "e3_runtime_include",
        "p260_e3_runtime_include",
        "trace_descriptor_header",
    ):
        (directory / MATERIALIZED_FILENAMES[key]).write_bytes(source[key])
    return p252._audit_userspace(
        root,
        generated,
        directory,
        materialized_filenames=MATERIALIZED_FILENAMES,
        source_check_run_id=SOURCE_CHECK_RUN_ID,
    )


def implementation_result(root: Path) -> dict[str, Any]:
    historical = p260.generate(root)
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.80 generation is not deterministic")
    semantics = _generated_semantics(first, historical)
    source = source_bytes(root)
    with tempfile.TemporaryDirectory(prefix="s22-p280-") as temporary:
        directory = Path(temporary)
        try:
            patch = p252._audit_patch(root, first["patch"], directory)
            userspace = _audit_userspace(root, first, source, directory)
        except p252.SourceContractError as exc:
            raise SourceContractError(str(exc)) from exc
    return {
        "schema": "s22plus_fyg8_p280_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "generated_semantics": semantics,
        "patch": patch,
        "linked_userspace": userspace,
        "trace_descriptor": receipt(source["trace_descriptor_header"]),
        "runtime_authority": dict(spec.RUNTIME_AUTHORITY),
        "descriptor": {
            "step_count": len(spec.STEPS),
            "gate_count": spec.GATE_COUNT,
            "terminal_ordinal": spec.TERMINAL_ORDINAL,
            "terminal_stage": spec.TERMINAL_STAGE,
            "diagnostic_detail_count": len(spec.DIAGNOSTIC_DETAILS),
        },
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    try:
        result = p252.validate_reachable_records(
            run_id,
            contract_spec=spec,
            decoder_module=decoder,
            expected_variants=FAILURE_REACHABLE_VARIANTS,
        )
    except p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc
    model = decoder.model
    header = (
        model.LONG_FAMILY
        + bytes(
            [
                (model.FORMAT_VERSION << 4)
                | model.PROFILE_NUMBERS[PROFILE]
            ]
        )
        + run_id
    )
    checked = 0
    for detail in spec.DIAGNOSTIC_DETAILS:
        if spec.OUTCOME_PROGRESS not in detail.outcomes:
            continue
        for stage in detail.stages:
            generation = spec.ordinal_for_stage(stage) + 1
            previous = spec.STEPS[generation - 2]
            slots = [bytes(model.SLOT_SIZE), bytes(model.SLOT_SIZE)]
            slots[(generation - 1) & 1] = decoder.encode_slot(
                header,
                generation=generation - 1,
                stage=previous.stage,
                outcome=model.OUTCOME_PROGRESS,
                item_index=previous.item_index,
                detail=0,
            )
            slots[generation & 1] = decoder.encode_slot(
                header,
                generation=generation,
                stage=stage,
                outcome=model.OUTCOME_PROGRESS,
                item_index=0,
                detail=detail.value,
            )
            decoded = decoder.decode_record(
                header + b"".join(slots),
                expected_profile=PROFILE,
                expected_run_id=run_id,
            )
            if (
                decoded["active"]["detail"] != detail.value
                or decoded["progress_warning"] is None
                or decoded["progress_warning"]["origin_phase"] != "unknown"
            ):
                raise SourceContractError(
                    "P2.80 progress-warning decode drifted"
                )
            checked += 1
    if checked != WARNING_VARIANTS:
        raise SourceContractError("P2.80 warning variant count mismatch")
    result["reachable_slot_variants"] += checked
    result["progress_warning_variants"] = checked
    result["exact_diagnostic_detail_count"] = len(
        spec.DIAGNOSTIC_DETAILS
    )
    if result["reachable_slot_variants"] != REACHABLE_VARIANTS:
        raise SourceContractError("P2.80 reachable total drifted")
    return result


def linked_table_bytes() -> dict[str, bytes]:
    base = p260.linked_table_bytes()
    rules = bytearray()
    for detail in spec.DIAGNOSTIC_DETAILS:
        rules.extend(detail.value.to_bytes(2, "little"))
        rules.append(detail.outcomes[0])
        rules.append(min(detail.stages))
        rules.append(max(detail.stages))
    return {
        **base,
        "s22_fyg8_p280_details": bytes(rules),
    }


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.80 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "exact_detail_whitelist_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = (
    *p260.LINKED_VALIDATOR_SYMBOLS,
    "s22_fyg8_p280_details",
)


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (
        SourceContractError,
        p252.SourceContractError,
        trace_contract.TraceContractError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
