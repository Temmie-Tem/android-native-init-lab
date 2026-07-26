#!/usr/bin/env python3
"""Versioned P2.60 E3 exact CDC-ACM banner source contract."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p248_source_contract as p248
import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p258_source_contract as p258
import s22plus_fyg8_p260_contract_spec as spec
import s22plus_fyg8_p260_e1_decoder as decoder


CONTRACT_ID = "s22plus-fyg8-p260-e3-exact-acm-banner-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P260-E3-EXACT-ACM-BANNER-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p260_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p260_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P260_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p260_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P260_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P260_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P260_E3_ACM_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P260-E3-ACM-SOURCE-CHECK-V1"
).digest()[:16]

MODULE_PLAN_COUNT = spec.MODULE_PLAN_COUNT
GENERATED_KEYS = p258.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p258.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p260_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p260_e3_runtime.c",
    "plan_header": "s22plus_fyg8_p260_e3_plan.h",
    "e3_runtime_include": "s22plus_fyg8_p260_e3_runtime.inc.c",
}

COMMON_SOURCE_PATHS = dict(p258.COMMON_SOURCE_PATHS)
COMMON_SOURCE_PATHS["p258_source_contract"] = COMMON_SOURCE_PATHS.pop(
    "source_contract"
)
COMMON_SOURCE_PATHS["p258_contract_spec"] = COMMON_SOURCE_PATHS.pop(
    "contract_spec"
)
COMMON_SOURCE_PATHS["p258_stock_closure_adapter"] = (
    COMMON_SOURCE_PATHS.pop("stock_closure_adapter")
)
COMMON_SOURCE_PATHS["p258_linked_validator_adapter"] = (
    COMMON_SOURCE_PATHS.pop("linked_validator_adapter")
)
COMMON_SOURCE_PATHS.update(
    {
        "source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p260_source_contract.py"
        ),
        "contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p260_contract_spec.py"
        ),
        "decoder_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p260_e1_decoder.py"
        ),
        "stock_closure_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p260_e2_stock_closure.py"
        ),
        "linked_validator_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p260_linked_audit.py"
        ),
        "e3_runtime_include": Path(
            "workspace/public/src/native-init/"
            "s22plus_fyg8_p260_e3_runtime.inc.c"
        ),
    }
)
SOURCE_KEYS = frozenset((*GENERATED_KEYS, *COMMON_SOURCE_PATHS))
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
REACHABLE_VARIANTS = 1 + sum(
    1 + len(spec.failure_details(step))
    for step in spec.STEPS
    if step.kind != spec.KIND_TERMINAL
)


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P260 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p258.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P260


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return spec.candidate_observer(run_id)


def _validate_authoritative_runtime_constants(include: bytes) -> None:
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
                f"P2.60 authoritative constant {name} cardinality drifted"
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
                f"P2.60 authoritative constant {name} value drifted"
            )


def _validate_authoritative_runtime_strings(include: bytes) -> None:
    for name, expected_value in spec.RUNTIME_EXTERNAL_STRINGS:
        pattern = re.compile(
            rb"static[ \t]+const[ \t]+char[ \t]+"
            + re.escape(name.encode("ascii"))
            + rb"\[\][ \t]*=[ \t\r\n]*\"([^\"]*)\"[ \t]*;",
            re.MULTILINE,
        )
        matches = pattern.findall(include)
        if len(matches) != 1:
            raise SourceContractError(
                f"P2.60 authoritative string {name} cardinality drifted"
            )
        if matches[0].decode("ascii") != expected_value:
            raise SourceContractError(
                f"P2.60 authoritative string {name} value drifted"
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


def _checkpoint_detail_helper() -> bytes:
    first = spec.E3_LOCAL_STAGES[0]
    last = spec.E3_LOCAL_STAGES[-1]
    return f"""static int p252_detail_allowed(
    uint8_t stage, uint8_t outcome, uint16_t detail) {{
#if S22PLUS_FYG8_P233_PROFILE == 3
    const struct s22_p248_step *step = NULL;
    for (size_t index = 0;
         index < sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]);
         ++index) {{
        if (k_p248_e2_steps[index].stage == stage) {{
            step = &k_p248_e2_steps[index];
            break;
        }}
    }}
    if (step == NULL) {{
        return 0;
    }}
    if (step->kind == S22_P248_STEP_TERMINAL) {{
        return outcome == S22_P233_OUTCOME_SUCCESS && detail == 0U;
    }}
    if (outcome == S22_P233_OUTCOME_PROGRESS) {{
        return detail == 0U;
    }}
    if (outcome != S22_P233_OUTCOME_FAILURE || detail == 0U) {{
        return 0;
    }}
    if (detail <= S22_P248_DETAIL_ERRNO_MAX) {{
        return 1;
    }}
    uint8_t encoded_index = (uint8_t)(detail & 0xffU);
    if (encoded_index >= {spec.GATE_COUNT}U) {{
        return 0;
    }}
    if (stage >= 0x{first:02x}U && stage <= 0x{last:02x}U) {{
        return (detail >= S22_P248_DETAIL_REGRESSION_BASE &&
                detail <= S22_P248_DETAIL_REGRESSION_MAX) ||
            (detail >= S22_P248_DETAIL_READ_ERROR_BASE &&
             detail <= S22_P248_DETAIL_READ_ERROR_MAX);
    }}
    if (step->kind == S22_P248_STEP_GATE &&
        detail >= S22_P248_DETAIL_REGRESSION_BASE &&
        detail <= S22_P248_DETAIL_REGRESSION_MAX) {{
        return encoded_index < step->item_index;
    }}
    if (step->kind == S22_P248_STEP_GATE &&
        detail >= S22_P248_DETAIL_READ_ERROR_BASE &&
        detail <= S22_P248_DETAIL_READ_ERROR_MAX) {{
        return encoded_index <= step->item_index;
    }}
    for (size_t index = 0;
         index < sizeof(k_p252_classifier_stages); ++index) {{
        if (stage == k_p252_classifier_stages[index] &&
            detail == k_p252_classifier_details[index]) {{
            return 1;
        }}
    }}
    return 0;
#else
    uint8_t terminal = terminal_stage();
    return (outcome == S22_P233_OUTCOME_PROGRESS &&
            stage != terminal && detail == 0U) ||
        (outcome == S22_P233_OUTCOME_SUCCESS &&
         stage == terminal && detail == 0U) ||
        (outcome == S22_P233_OUTCOME_FAILURE &&
         stage != terminal && detail != 0U);
#endif
}}

""".encode("ascii")


def _kernel_detail_validator() -> bytes:
    first_ordinal = spec.ordinal_for_stage(spec.E3_LOCAL_STAGES[0])
    terminal_ordinal = spec.TERMINAL_ORDINAL
    return p252._kernel_prefixed(
        [
            "static noinline __used bool s22_fyg8_e1_detail_allowed(",
            "\t\tu8 profile, size_t ordinal, size_t count,",
            "\t\tu8 outcome, u16 detail)",
            "{",
            "\tu8 gate_index;",
            "\tu8 encoded_index;",
            "\tsize_t index;",
            "\tbool e3_local;",
            "",
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
            f"\te3_local = ordinal >= {first_ordinal} &&",
            f"\t\tordinal < {terminal_ordinal};",
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
        ]
    )


def _transform_checkpoint(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p248._render_checkpoint_steps(p258.spec.STEPS),
        p248._render_checkpoint_steps(spec.STEPS),
        label="P2.60 checkpoint descriptor table",
    )
    return _replace_exact(
        value,
        p252._render_checkpoint_detail_helper(p258.spec),
        _checkpoint_detail_helper(),
        label="P2.60 checkpoint detail validator",
    )


def _transform_patch(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        p248._render_kernel_tables(p258.spec.STEPS),
        p248._render_kernel_tables(spec.STEPS),
        label="P2.60 kernel descriptor tables",
    )
    value = _replace_exact(
        value,
        p252._render_kernel_detail_validator(p258.spec),
        _kernel_detail_validator(),
        label="P2.60 kernel detail validator",
    )
    return p252._recount_kernel_patch_hunks(value)


def _transform_runtime(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b'#include "s22plus_fyg8_p258a_e2_plan.h"',
        b'#include "s22plus_fyg8_p260_e3_plan.h"',
        label="P2.60 runtime plan include",
    )
    value = _replace_exact(
        value,
        b"static __attribute__((noreturn)) void p241_run(void) {\n",
        b'#include "s22plus_fyg8_p260_e3_runtime.inc.c"\n\n'
        b"static __attribute__((noreturn)) void p241_run(void) {\n",
        label="P2.60 E3 runtime include",
    )
    old_terminal = (
        b"    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {\n"
        b"        quiet_park();\n"
        b"    }\n"
        b"    quiet_park();\n"
    )
    return _replace_exact(
        value,
        old_terminal,
        b"    p260_e3_run();\n",
        label="P2.60 E3 handoff",
    )


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    historical = p258.generate(repository)
    return {
        "plan": historical["plan"],
        "runtime": _transform_runtime(historical["runtime"]),
        "checkpoint": _transform_checkpoint(historical["checkpoint"]),
        "patch": _transform_patch(historical["patch"]),
    }


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.60 source {name}"
        )
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.60 source inventory changed")
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
        raise SourceContractError("P2.60 changed the P2.58A module plan")
    runtime = generated["runtime"].decode("ascii")
    checkpoint = generated["checkpoint"].decode("ascii")
    patch = generated["patch"].decode("ascii")
    required_runtime = (
        '#include "s22plus_fyg8_p260_e3_plan.h"',
        '#include "s22plus_fyg8_p260_e3_runtime.inc.c"',
        "p260_e3_run();",
    )
    if any(runtime.count(token) != 1 for token in required_runtime):
        raise SourceContractError("P2.60 runtime handoff drifted")
    required_validator = (
        "stage >= 0x88U && stage <= 0x8fU",
        "encoded_index >= 12U",
    )
    if any(token not in checkpoint for token in required_validator):
        raise SourceContractError("P2.60 checkpoint validator drifted")
    required_kernel = (
        "e3_local = ordinal >= 80 &&",
        "ordinal < 88;",
        "encoded_index >= 12",
    )
    if any(token not in patch for token in required_kernel):
        raise SourceContractError("P2.60 kernel validator drifted")
    tables = linked_table_bytes()
    if (
        len(tables["s22_fyg8_e2_sequence"]) != 89
        or tables["s22_fyg8_e2_sequence"][-2:] != bytes((0x8F, 0x90))
        or tables["s22_fyg8_e2_items"][-9:] != bytes(9)
    ):
        raise SourceContractError("P2.60 linked geometry drifted")
    include = source_bytes_for_runtime_include()
    _validate_authoritative_runtime_constants(include)
    _validate_authoritative_runtime_strings(include)
    if hashlib.sha256(include).hexdigest() != spec.E3_RUNTIME_INCLUDE_SHA256:
        raise SourceContractError("P2.60 E3 runtime source identity drifted")
    required_include = (
        b"p260_derive_identity();",
        b"p260_write_all(\n        tty_fd, p260_banner",
        b'p260_write_value(p260_role_path, "peripheral")',
        b'p260_write_and_verify(\n        "/config/usb_gadget/g1/UDC"',
        b'"/sys/class/udc/a600000.dwc3/state"',
        b'"/sys/class/udc/a600000.dwc3/current_speed"',
    )
    if any(include.count(token) != 1 for token in required_include):
        raise SourceContractError("P2.60 E3 runtime semantics drifted")
    if (
        include.count(b"p260_ioctl((int)fd, P260_TCGETS") != 2
        or include.count(b"p260_ioctl((int)fd, P260_TCSETS") != 1
    ):
        raise SourceContractError("P2.60 raw termios sequence drifted")
    forbidden = (
        b"TCIOFLUSH",
        b"soft_connect",
        b"/speed",
        b"ss_acm",
        b"sys_unlink",
    )
    if any(token in include for token in forbidden):
        raise SourceContractError("P2.60 E3 runtime contains forbidden path")
    return {
        "p258_prefix_preserved": True,
        "module_plan_byte_identical": True,
        "step_count": len(spec.STEPS),
        "terminal_generation": spec.TERMINAL_ORDINAL + 1,
        "runtime_handoff_once": True,
        "raw_tty_no_flush": True,
        "one_shot_udc_bind": True,
        "descriptor_derived": True,
        "verified": True,
    }


def source_bytes_for_runtime_include(
    root: Path | None = None,
) -> bytes:
    repository = p243.repo_root() if root is None else root
    return p252.p233.read_direct(
        repository / COMMON_SOURCE_PATHS["e3_runtime_include"],
        "P2.60 E3 runtime include",
    )


def _registration_audit(root: Path) -> dict[str, Any]:
    sources = source_bytes(root)
    required = {
        "source_contract_selector": (
            b"import s22plus_fyg8_p260_source_contract as p260",
            b"p260.CONTRACT_ID: p260",
        ),
        "stock_closure_adapter": (
            b'source_contract.require(source_contract_id, "E2")',
            b"_call_with_p260_entrypoints",
        ),
        "linked_validator_adapter": (
            b'ADAPTER_ID = "s22plus-fyg8-p260-linked-audit-v1"',
            b"source_contract_module=p260",
        ),
        "linked_adapter_dispatch": (
            CONTRACT_ID.encode("ascii"),
            b"s22plus_fyg8_p260_linked_audit",
        ),
        "candidate_repro_enforcement": (
            CONTRACT_ID.encode("ascii"),
            b"P2.60 linked audit adapter mismatch",
            b"def artifact_safety(",
            b"source-contract-bound-p260-e3-acm-and-peripheral-role",
            b"bounded-configfs-cdc-acm-banner-and-peripheral-role",
        ),
    }
    for name, tokens in required.items():
        if any(token not in sources[name] for token in tokens):
            raise SourceContractError(
                f"P2.60 execution registration is incomplete: {name}"
            )
    try:
        candidate_tree = ast.parse(
            sources["candidate_repro_enforcement"].decode("ascii")
        )
    except (UnicodeError, SyntaxError) as exc:
        raise SourceContractError(
            "P2.60 candidate enforcement is not valid Python"
        ) from exc
    build_functions = [
        node
        for node in candidate_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "build_candidate"
    ]
    if len(build_functions) != 1:
        raise SourceContractError("P2.60 candidate build function drifted")
    safety_calls = [
        node
        for node in ast.walk(build_functions[0])
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "safety"
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "artifact_safety"
        and len(node.value.args) == 1
        and isinstance(node.value.args[0], ast.Name)
        and node.value.args[0].id == "exact_contract"
        and not node.value.keywords
    ]
    if len(safety_calls) != 1:
        raise SourceContractError(
            "P2.60 candidate build does not consume exact artifact safety"
        )
    return {
        name: receipt(sources[name]) for name in sorted(required)
    } | {
        "artifact_safety_callsite_verified": True,
        "verified": True,
    }


def implementation_result(root: Path) -> dict[str, Any]:
    historical = p258.generate(root)
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.60 generation is not deterministic")
    semantics = _generated_semantics(first, historical)
    with tempfile.TemporaryDirectory(prefix="s22-p260-") as temporary:
        directory = Path(temporary)
        try:
            patch = p252._audit_patch(root, first["patch"], directory)
            userspace = p252._audit_userspace(
                root,
                first,
                directory,
                materialized_filenames=MATERIALIZED_FILENAMES,
                source_check_run_id=SOURCE_CHECK_RUN_ID,
            )
        except p252.SourceContractError as exc:
            raise SourceContractError(str(exc)) from exc
    return {
        "schema": "s22plus_fyg8_p260_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "generated_semantics": semantics,
        "registrations": _registration_audit(root),
        "patch": patch,
        "linked_userspace": userspace,
        "observer": {
            "serial_size": spec.USB_SERIAL_SIZE,
            "banner_size": spec.BANNER_SIZE,
            "source_check": candidate_observer(SOURCE_CHECK_RUN_ID),
        },
        "descriptor": {
            "step_count": len(spec.STEPS),
            "gate_count": spec.GATE_COUNT,
            "terminal_ordinal": spec.TERMINAL_ORDINAL,
            "terminal_stage": spec.TERMINAL_STAGE,
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
        return p252.validate_reachable_records(
            run_id,
            contract_spec=spec,
            decoder_module=decoder,
            expected_variants=REACHABLE_VARIANTS,
        )
    except p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def linked_table_bytes() -> dict[str, bytes]:
    return p252.linked_table_bytes_for(spec)


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.60 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "classifier_whitelist_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = p252.LINKED_VALIDATOR_SYMBOLS


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (
        SourceContractError,
        p252.SourceContractError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
