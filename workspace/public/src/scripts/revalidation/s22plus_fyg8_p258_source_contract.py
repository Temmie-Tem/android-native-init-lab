#!/usr/bin/env python3
"""Versioned P2.58A exact-UDC-membership source contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p257_source_contract as p257
import s22plus_fyg8_p258_contract_spec as spec


CONTRACT_ID = "s22plus-fyg8-p258a-e2-exact-udc-membership-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P258A-E2-EXACT-UDC-MEMBERSHIP-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p258a_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p258a_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P258A_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p258a_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P258A_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P258A_E2_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P258A_UDC_PREDICATE_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P258A-UDC-PREDICATE-SOURCE-CHECK-V1"
).digest()[:16]

MODULE_PLAN_COUNT = spec.MODULE_PLAN_COUNT
GENERATED_KEYS = p257.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p257.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p258a_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p258a_e2_runtime.c",
    "plan_header": "s22plus_fyg8_p258a_e2_plan.h",
}
P257_GENERATED_SHA256 = {
    "checkpoint": (
        "00c98bce5cdedf16718269667490a2f09"
        "f33894a8ab5469d02d80a6cdf5ca644"
    ),
    "patch": (
        "f0b355de0fb82a7f18ed4b744fe4f925"
        "b72fcf736b120dbd313099cf0b32ae2a"
    ),
    "plan": (
        "b68a6c4d5bafa864f91e0be21c53aefc"
        "5a288741c0b8870833ea603a26e3f015"
    ),
    "runtime": (
        "76015e246fe27d2b6f6ac07772ebacd2c"
        "b84f146d4739d8e1ac38eaff68fe10e"
    ),
}

COMMON_SOURCE_PATHS = dict(p257.COMMON_SOURCE_PATHS)
COMMON_SOURCE_PATHS["p257_source_contract"] = COMMON_SOURCE_PATHS.pop(
    "source_contract"
)
COMMON_SOURCE_PATHS["p257_contract_spec"] = COMMON_SOURCE_PATHS.pop(
    "contract_spec"
)
COMMON_SOURCE_PATHS["p257_stock_closure_adapter"] = COMMON_SOURCE_PATHS.pop(
    "stock_closure_adapter"
)
COMMON_SOURCE_PATHS["p257_linked_validator_adapter"] = (
    COMMON_SOURCE_PATHS.pop("linked_validator_adapter")
)
COMMON_SOURCE_PATHS.update(
    {
        "source_contract": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p258_source_contract.py"
        ),
        "contract_spec": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p258_contract_spec.py"
        ),
        "stock_closure_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p258_e2_stock_closure.py"
        ),
        "linked_validator_adapter": Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p258_linked_audit.py"
        ),
    }
)
SOURCE_KEYS = frozenset((*GENERATED_KEYS, *COMMON_SOURCE_PATHS))
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
REACHABLE_VARIANTS = p257.REACHABLE_VARIANTS


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P258 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)
decoder = p257.decoder


def receipt(data: bytes) -> dict[str, Any]:
    return p257.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P258


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


def _replace_span(
    data: bytes,
    start: bytes,
    end: bytes,
    replacement: bytes,
    *,
    label: str,
) -> bytes:
    if data.count(start) != 1 or data.count(end) != 1:
        raise SourceContractError(f"{label} boundary count changed")
    first = data.index(start)
    last = data.index(end, first)
    if last <= first:
        raise SourceContractError(f"{label} boundaries are reversed")
    return data[:first] + replacement + data[last:]


def _render_udc_predicate() -> bytes:
    target = spec.UDC_TARGET_NAME
    path = spec.UDC_TARGET_PATH
    return f"""static long p241_check_udc(void) {{
    uint8_t buffer[S22_P241_DIRENT_BUFFER_SIZE];
    unsigned int exact = 0;
    long fd = sys_openat("/sys/class/udc", O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {{
        return fd == -ENOENT ? -ENODEV : fd;
    }}
    for (;;) {{
        long amount = p241_getdents64((int)fd, buffer, sizeof(buffer));
        if (amount < 0) {{
            (void)sys_close((int)fd);
            return amount;
        }}
        if (amount == 0) {{
            break;
        }}
        size_t cursor = 0;
        while (cursor < (size_t)amount) {{
            struct s22_p241_linux_dirent64 *entry =
                (struct s22_p241_linux_dirent64 *)(buffer + cursor);
            size_t header_size = offsetof(
                struct s22_p241_linux_dirent64, d_name);
            if (entry->d_reclen < header_size + 2U ||
                cursor + entry->d_reclen > (size_t)amount) {{
                (void)sys_close((int)fd);
                return -EIO;
            }}
            size_t name_capacity = entry->d_reclen - header_size;
            size_t name_size = 0;
            while (name_size < name_capacity &&
                   entry->d_name[name_size] != '\\0') {{
                ++name_size;
            }}
            if (name_size == name_capacity || name_size == 0U) {{
                (void)sys_close((int)fd);
                return -EIO;
            }}
            if (!p241_is_dot_name(entry->d_name, name_size) &&
                token_equals(entry->d_name, name_size, "{target}")) {{
                ++exact;
            }}
            cursor += entry->d_reclen;
        }}
    }}
    long close_rc = sys_close((int)fd);
    if (close_rc != 0) {{
        return close_rc;
    }}
    if (exact == 0U) {{
        return -ENODEV;
    }}
    if (exact != 1U) {{
        return -EIO;
    }}

    struct s22_p241_kernel_stat stat_buffer = {{0}};
    char link_target[S22_P241_SYMLINK_TARGET_MAX];
    long stat_rc = p241_newfstatat(
        "{path}", &stat_buffer, AT_SYMLINK_NOFOLLOW);
    if (stat_rc != 0) {{
        return stat_rc == -ENOENT ? -ENODEV : stat_rc;
    }}
    if ((stat_buffer.st_mode & S_IFMT) != S_IFLNK) {{
        return -EIO;
    }}
    long target_size = p241_readlinkat(
        "{path}", link_target, sizeof(link_target));
    if (target_size == -ENOENT) {{
        return -ENODEV;
    }}
    if (target_size <= 0 || target_size >= (long)sizeof(link_target)) {{
        return target_size < 0 ? target_size : -EIO;
    }}
    return p241_basename_equals(
        link_target, (size_t)target_size, "{target}") ? 0 : -EIO;
}}

""".encode("ascii")


def _transform_runtime(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b'#include "s22plus_fyg8_p257_e2_plan.h"',
        b'#include "s22plus_fyg8_p258a_e2_plan.h"',
        label="P2.58A runtime plan include",
    )
    value = _replace_span(
        value,
        b"static long p241_check_udc(void) {\n",
        b"struct s22_p252_bind_classifier {\n",
        _render_udc_predicate(),
        label="P2.58A UDC predicate",
    )
    definitions = (
        f"#define S22_P258_UDC_GATE_INDEX {spec.UDC_GATE_INDEX}U\n"
        f"#define S22_P258_UDC_STAGE 0x{spec.UDC_STAGE:02x}U\n"
        f"#define S22_P258_UDC_DWELL_SEC "
        f"{spec.UDC_DWELL_SECONDS}LL\n"
    ).encode("ascii")
    value = _replace_exact(
        value,
        b"#define S22_P252_GRACE_SEC 5LL\n",
        b"#define S22_P252_GRACE_SEC 5LL\n" + definitions,
        label="P2.58A UDC dwell definitions",
    )
    old_progress = (
        b"                ++completed;\n"
        b"                advanced = 1;\n"
    )
    new_progress = (
        b"                ++completed;\n"
        b"                if (completed == S22_P258_UDC_GATE_INDEX) {\n"
        b"                    if (p241_clock_gettime(&deadline) != 0 ||\n"
        b"                        deadline.tv_sec > 0x7fffffffffffffffLL -\n"
        b"                            S22_P258_UDC_DWELL_SEC) {\n"
        b"                        fail_at(\n"
        b"                            S22_P258_UDC_STAGE,\n"
        b"                            S22_P258_UDC_GATE_INDEX,\n"
        b"                            -EIO);\n"
        b"                    }\n"
        b"                    deadline.tv_sec += S22_P258_UDC_DWELL_SEC;\n"
        b"                    post_grace_drain = 0;\n"
        b"                }\n"
        b"                advanced = 1;\n"
    )
    return _replace_exact(
        value,
        old_progress,
        new_progress,
        label="P2.58A dedicated UDC dwell",
    )


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p243.repo_root() if root is None else root
    historical = p257.generate(repository)
    return {
        "plan": historical["plan"],
        "runtime": _transform_runtime(historical["runtime"]),
        "checkpoint": historical["checkpoint"],
        "patch": historical["patch"],
    }


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = {
        key: generated[GENERATED_OUTPUT_NAMES[key]]
        for key in GENERATED_KEYS
    }
    for name, path in COMMON_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.58A source {name}"
        )
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.58A source inventory changed")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def _historical_audit(root: Path) -> dict[str, Any]:
    generated = p257.generate(root)
    actual = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in sorted(generated.items())
    }
    if actual != P257_GENERATED_SHA256:
        raise SourceContractError("P2.57 generated baseline changed")
    return {
        name: receipt(data) for name, data in sorted(generated.items())
    } | {"verified": True}


def _topology_oracle_audit(root: Path) -> dict[str, Any]:
    path = root / spec.STOCK_TOPOLOGY_PATH
    data = p252.p233.read_direct(path, "P2.58A stock topology oracle")
    try:
        value = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SourceContractError(
            "P2.58A stock topology oracle is not ASCII JSON"
        ) from exc
    entries = value.get("sysfs", {}).get("udc_entries")
    expected = [spec.UDC_TARGET_NAME, spec.UDC_STOCK_PEER]
    if entries != expected:
        raise SourceContractError(
            "P2.58A stock topology does not pin the two-UDC oracle"
        )
    cases = []
    for case in spec.UDC_ORACLE_CASES:
        actual = spec.evaluate_udc_oracle(case)
        if actual is not case.expected:
            raise SourceContractError(
                f"P2.58A semantic oracle mismatch: {case.name}"
            )
        cases.append(
            {
                "name": case.name,
                "entries": list(case.entries),
                "target_is_symlink": case.target_is_symlink,
                "target_basename": case.target_basename,
                "expected": case.expected,
                "actual": actual,
            }
        )
    return {
        "topology": receipt(data),
        "known_good_entries": entries,
        "cases": cases,
        "case_count": len(cases),
        "known_good_passed": True,
        "unrelated_peer_passed": True,
        "verified": True,
    }


def _generated_semantics(
    generated: dict[str, bytes], historical: dict[str, bytes]
) -> dict[str, Any]:
    for name in ("plan", "checkpoint", "patch"):
        if generated[name] != historical[name]:
            raise SourceContractError(
                f"P2.58A unexpectedly changed P2.57 {name}"
            )
    if generated["runtime"] == historical["runtime"]:
        raise SourceContractError("P2.58A runtime did not change")
    runtime = generated["runtime"].decode("ascii")
    required = (
        "unsigned int exact = 0;",
        'token_equals(entry->d_name, name_size, "a600000.dwc3")',
        '"/sys/class/udc/a600000.dwc3", &stat_buffer,',
        "if (exact == 0U) {",
        "if (exact != 1U) {",
        "#define S22_P258_UDC_GATE_INDEX 11U",
        "#define S22_P258_UDC_STAGE 0x87U",
        "#define S22_P258_UDC_DWELL_SEC 5LL",
        "if (completed == S22_P258_UDC_GATE_INDEX) {",
        "deadline.tv_sec += S22_P258_UDC_DWELL_SEC;",
    )
    if any(runtime.count(token) != 1 for token in required):
        raise SourceContractError("P2.58A runtime semantics drifted")
    forbidden = (
        "return entries == 1U && exact == 1U",
        "entries == 1U",
    )
    if any(token in runtime for token in forbidden):
        raise SourceContractError("P2.58A retained global UDC cardinality")
    if runtime.count("post_grace_drain = 0;") != 2:
        raise SourceContractError("P2.58A UDC drain reset drifted")
    reset = runtime.index(
        "if (completed == S22_P258_UDC_GATE_INDEX) {"
    )
    clear = runtime.index("post_grace_drain = 0;", reset)
    advanced = runtime.index("advanced = 1;", clear)
    if not reset < clear < advanced:
        raise SourceContractError("P2.58A UDC dwell reset order changed")
    return {
        "runtime_only_delta": True,
        "plan_byte_identical_to_p257": True,
        "checkpoint_byte_identical_to_p257": True,
        "kernel_patch_byte_identical_to_p257": True,
        "global_udc_cardinality_removed": True,
        "exact_membership_and_identity_required": True,
        "dedicated_udc_dwell_seconds": spec.UDC_DWELL_SECONDS,
        "verified": True,
    }


def _registration_audit(root: Path) -> dict[str, Any]:
    sources = source_bytes(root)
    required = {
        "source_contract_selector": (
            b"import s22plus_fyg8_p258_source_contract as p258",
            b"p258.CONTRACT_ID: p258",
        ),
        "stock_closure_adapter": (
            b"source_contract.require(source_contract_id, \"E2\")",
            b"p257.validate_module_closure",
        ),
        "linked_validator_adapter": (
            b'ADAPTER_ID = "s22plus-fyg8-p258-linked-audit-v1"',
            b"source_contract_module=p258",
        ),
        "linked_adapter_dispatch": (
            CONTRACT_ID.encode("ascii"),
            b"s22plus_fyg8_p258_linked_audit",
        ),
        "candidate_repro_enforcement": (
            CONTRACT_ID.encode("ascii"),
            b"P2.58A linked audit adapter mismatch",
        ),
    }
    for name, tokens in required.items():
        if any(token not in sources[name] for token in tokens):
            raise SourceContractError(
                f"P2.58A execution registration is incomplete: {name}"
            )
    return {
        name: receipt(sources[name]) for name in sorted(required)
    } | {"verified": True}


def implementation_result(root: Path) -> dict[str, Any]:
    historical = p257.generate(root)
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.58A generation is not deterministic")
    semantics = _generated_semantics(first, historical)
    topology = _topology_oracle_audit(root)
    with tempfile.TemporaryDirectory(prefix="s22-p258a-") as temporary:
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
        "schema": "s22plus_fyg8_p258a_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "p257_generated_baseline": _historical_audit(root),
        "generated_semantics": semantics,
        "semantic_oracle": topology,
        "registrations": _registration_audit(root),
        "patch": patch,
        "linked_userspace": userspace,
        "descriptor": {
            "step_count": len(spec.STEPS),
            "gate_count": spec.GATE_COUNT,
            "udc_stage": spec.UDC_STAGE,
            "udc_gate_index": spec.UDC_GATE_INDEX,
            "udc_dwell_seconds": spec.UDC_DWELL_SECONDS,
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
        raise SourceContractError("P2.58A linked descriptor tables differ")
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
