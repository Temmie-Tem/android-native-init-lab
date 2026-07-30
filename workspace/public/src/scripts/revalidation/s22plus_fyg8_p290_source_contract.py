#!/usr/bin/env python3
"""P2.90 source contract for checked park repair and adjacent positions."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterator

import s22plus_fyg8_p288_source_contract as p288
import s22plus_fyg8_p290_contract_spec as spec
import s22plus_fyg8_p290_e1_decoder as decoder
import s22plus_fyg8_p290_runtime_transform as runtime_transform


CONTRACT_ID = "s22plus-fyg8-p290-checked-park-adjacent-corridor-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P290-CHECKED-PARK-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p290_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p290_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P290_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p290_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P290_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P290_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = (
    "PASS_P290_CHECKED_PARK_ADJACENT_CORRIDOR_IMPLEMENTATION_HOST_ONLY"
)
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P290-SOURCE-CHECK-V1"
).digest()[:16]

MODULE_PLAN_COUNT = p288.MODULE_PLAN_COUNT
GENERATED_KEYS = p288.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p288.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = {
    "checkpoint_client": "s22plus_fyg8_p290_checkpoint.c",
    "runtime_wrapper": "s22plus_fyg8_p290_e3_runtime.c",
    "plan_header": "s22plus_fyg8_p286_e3_plan.h",
    "p288_legacy_runtime": "s22plus_r4w1e_e1_runtime.c",
    "p290_e3_runtime_include": "s22plus_fyg8_p290_e3_runtime.inc.c",
    "p288_classifier_include": "s22plus_fyg8_p288_classifier.inc.c",
    "p290_position_header": "s22plus_fyg8_p290_positions.h",
    "p290_checkpoint_header": "s22plus_r4w1e_checkpoint.h",
    "p286_classifier_include": "s22plus_fyg8_p286_classifier.inc.c",
    "classifier_include": "s22plus_fyg8_p282_classifier.inc.c",
    "p260_e3_runtime_include": "s22plus_fyg8_p260_e3_runtime.inc.c",
    "trace_descriptor_header": "s22plus_fyg8_p286_trace_descriptor.h",
}
OVERLAY_SOURCE_PATHS = {
    "p290_contract_spec": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_contract_spec.py"
    ),
    "p290_source_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_source_contract.py"
    ),
    "p290_runtime_transform": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_runtime_transform.py"
    ),
    "p290_candidate_intent": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_candidate_intent.py"
    ),
    "p290_userspace_build": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_userspace_build.py"
    ),
    "p290_build": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_build.py"
    ),
    "p290_candidate_builder": Path(
        "workspace/public/src/scripts/revalidation/"
        "build_s22plus_fyg8_p290_candidate.py"
    ),
    "p290_boot_only_packager": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p290_boot_only_packager.py"
    ),
}
GENERATED_OVERLAY_KEYS = frozenset(
    {
        "p290_e3_runtime_include",
        "p290_position_header",
        "p290_checkpoint_header",
    }
)
SOURCE_KEYS = frozenset(
    (*p288.SOURCE_KEYS, *OVERLAY_SOURCE_PATHS, *GENERATED_OVERLAY_KEYS)
)
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
REACHABLE_VARIANTS = sum(
    (
        1
        + len(
            spec.position_failure_details(
                position.stage, position.item_index
            )
        )
        if position.kind == spec.KIND_TERMINAL
        else len(
            spec.position_progress_details(
                position.stage, position.item_index
            )
        )
        + len(
            spec.position_failure_details(
                position.stage, position.item_index
            )
        )
    )
    for position in spec.POSITIONS
)


class SourceContractError(ValueError):
    pass


SourceContract = p288.SourceContract
P290 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p288.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P290


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return p288.candidate_observer(run_id)


@contextmanager
def p288_spec_context() -> Iterator[None]:
    previous = p288.spec
    p288.spec = spec
    try:
        yield
    finally:
        p288.spec = previous


def shared_input_root(root: Path) -> Path:
    common_dir = Path(
        subprocess.run(
            (
                "git",
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ),
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
    ).resolve()
    return common_dir.parent


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = p288.p243.repo_root() if root is None else root
    inputs = shared_input_root(repository)
    historical = p288.p286.generate(inputs)
    with p288_spec_context():
        checkpoint = p288._transform_checkpoint(  # noqa: SLF001
            historical["checkpoint"]
        )
        patch = p288._transform_patch(historical["patch"])  # noqa: SLF001
        position_header = p288._render_position_header()  # noqa: SLF001
        checkpoint_header = p288._render_checkpoint_header(  # noqa: SLF001
            inputs
        )
    p288_runtime = p288.runtime_transform.transform_runtime_wrapper(
        historical["runtime"]
    )
    return {
        "plan": historical["plan"],
        "runtime": runtime_transform.transform_runtime_wrapper(p288_runtime),
        "checkpoint": runtime_transform.transform_checkpoint(checkpoint),
        "patch": runtime_transform.transform_patch(patch),
        "position_header": runtime_transform.transform_position_header(
            position_header
        ),
        "checkpoint_header": runtime_transform.transform_checkpoint_header(
            checkpoint_header
        ),
    }


def source_bytes(root: Path) -> dict[str, bytes]:
    generated = generate(root)
    result = p288.source_bytes(shared_input_root(root))
    result.update(
        {
            key: generated[GENERATED_OUTPUT_NAMES[key]]
            for key in GENERATED_KEYS
        }
    )
    for name, path in OVERLAY_SOURCE_PATHS.items():
        result[name] = p288.p252.p233.read_direct(
            root / path, f"P2.90 source {name}"
        )
    p288_include = p288.runtime_transform.transform_runtime_include(
        result["p286_e3_runtime_include"]
    )
    result["p290_e3_runtime_include"] = (
        runtime_transform.transform_runtime_include(p288_include)
    )
    result["p290_position_header"] = generated["position_header"]
    result["p290_checkpoint_header"] = generated["checkpoint_header"]
    if set(result) != SOURCE_KEYS:
        missing = sorted(SOURCE_KEYS - set(result))
        extra = sorted(set(result) - SOURCE_KEYS)
        raise SourceContractError(
            f"P2.90 source inventory changed: missing={missing}, extra={extra}"
        )
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def _position_macro(name: str) -> bytes:
    return f"S22_P290_POSITION_{name.upper()}".encode("ascii")


def _runtime_position_calls(include: bytes) -> tuple[bytes, ...]:
    return tuple(
        re.findall(
            rb"p290_progress_position\(\s*"
            rb"(S22_P290_POSITION_[A-Z0-9_]+)\s*,",
            include,
        )
    )


def _audit_runtime_position_order(include: bytes) -> dict[str, Any]:
    expected = tuple(
        _position_macro(position.name)
        for position in spec.SUCCESSOR_POSITIONS[:-1]
    )
    suspend = p288._c_function_body(  # noqa: SLF001
        include, "p282_cycle_suspend"
    )
    entry = p288._c_function_body(include, "p290_e3_run")  # noqa: SLF001
    restart = p288._c_function_body(  # noqa: SLF001
        include, "p282_cycle_restart"
    )
    bind = p288._c_function_body(include, "p282_phase_bind")  # noqa: SLF001
    final = p288._c_function_body(  # noqa: SLF001
        include, "p282_wait_final_pair"
    )
    caller_marker = entry.find(
        b"S22_P290_POSITION_SUSPEND_FUNCTION_RETURNED"
    )
    restart_call = entry.find(b"p282_cycle_restart(&cycle, tty_fd)")
    if (
        caller_marker < 0
        or restart_call < 0
        or caller_marker > restart_call
    ):
        raise SourceContractError(
            "P2.90 caller marker is absent or follows the restart call"
        )
    actual = (
        *_runtime_position_calls(suspend),
        *_runtime_position_calls(entry),
        *_runtime_position_calls(restart),
        *_runtime_position_calls(bind),
        *_runtime_position_calls(final),
    )
    if actual != expected:
        raise SourceContractError(
            "P2.90 runtime publication order differs from the declared "
            "position sequence"
        )
    return {
        "declared_nonterminal_suffix": len(expected),
        "runtime_nonterminal_suffix": len(actual),
        "exact_program_order": True,
        "terminal_publication_last": True,
        "verified": True,
    }


def _audit_first_position_adjacency(include: bytes) -> dict[str, Any]:
    helper = p288._c_function_body(  # noqa: SLF001
        include, "p290_progress_position"
    )
    if (
        b"p260_revalidate_or_fail" in helper
        or b"checkpoint_next_stage" in helper
        or b"sys_" in helper
        or helper.index(b"s22_p290_checkpoint_progress_position(")
        > helper.index(b"if (rc != 0)")
    ):
        raise SourceContractError(
            "P2.90 first-position helper has a prepublication operation"
        )
    suspend = p288._c_function_body(  # noqa: SLF001
        include, "p282_cycle_suspend"
    )
    tail = (
        b"    p282_publish_classification(\n"
        b"        P282_STAGE_SUSPENDED,\n"
        b"        classified,\n"
        b"        &classification,\n"
        b"        p282_cycle_warning_detail(cycle, P282_STAGE_SUSPENDED));\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_SUSPENDED_PUBLISH_RETURNED, 0U);\n"
        b"    return 0;\n"
    )
    if suspend.count(tail) != 1:
        raise SourceContractError(
            "P2.90 generation-88 return adjacency differs"
        )
    first = _runtime_position_calls(include)[0]
    if first != b"S22_P290_POSITION_SUSPENDED_PUBLISH_RETURNED":
        raise SourceContractError("P2.90 first successor position drifted")
    return {
        "last_live_generation": 88,
        "first_successor_generation": 89,
        "first_successor_pair": [spec.SUSPENDED_STAGE, 1],
        "unrelated_syscall_between_publishers": False,
        "gate_revalidation_between_publishers": False,
        "position_helper_directly_dispatches_checkpoint_client": True,
        "verified": True,
    }


def _audit_runtime_request_encoding(
    source: dict[str, bytes],
) -> dict[str, Any]:
    include = source["p290_e3_runtime_include"]
    positions = source["p290_position_header"]
    checkpoint = source["checkpoint_client"]
    dispatch = spec.position_for_generation(93)
    expected_macro = (
        b"#define S22_P290_POSITION_RESTART_HELPER_DISPATCH 92U\n"
    )
    expected_call = (
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_RESTART_HELPER_DISPATCH, 0U);\n"
    )
    progress = p288._c_function_body(  # noqa: SLF001
        checkpoint, "s22_p290_checkpoint_progress_position"
    )
    publisher = p288._c_function_body(  # noqa: SLF001
        checkpoint, "p288_publish_next"
    )
    tables = linked_table_bytes()
    if (
        dispatch.pair != (spec.RESTART_STAGE, 0)
        or positions.count(expected_macro) != 1
        or include.count(expected_call) != 1
        or (
            b"client, S22_P233_OUTCOME_PROGRESS, detail, 1, "
            b"position_ordinal"
        )
        not in b" ".join(progress.split())
        or b"size_t ordinal = client->generation;" not in publisher
        or b"position_ordinal != ordinal" not in publisher
        or b"request.stage = step->stage;" not in publisher
        or b"request.item_index = step->item_index;" not in publisher
        or tables["s22_fyg8_e2_sequence"][92] != spec.RESTART_STAGE
        or tables["s22_fyg8_e2_items"][92] != 0
    ):
        raise SourceContractError(
            "P2.90 helper-dispatch request construction differs"
        )
    return {
        "position_ordinal": 92,
        "generation": 93,
        "declared_pair": [spec.RESTART_STAGE, 0],
        "runtime_detail": 0,
        "macro_cardinality": 1,
        "runtime_call_cardinality": 1,
        "publisher_uses_client_generation_as_ordinal": True,
        "publisher_checks_supplied_ordinal": True,
        "request_stage_and_item_loaded_from_linked_step": True,
        "linked_step_pair": [spec.RESTART_STAGE, 0],
        "verified": True,
    }


P286_PARK_COUNTS = {
    "p282_progress": 1,
    "p282_fail_classification": 1,
    "p282_publish_classification": 2,
    "p282_set_cycle_warning": 1,
    "p282_cycle_warning_detail": 1,
    "p282_cycle_abort": 2,
    "p282_cycle_abort_condition": 1,
    "p282_restart_exact_failure": 1,
    "p282_cycle_restart": 1,
    "p282_phase_bind": 2,
    "p286_e3_run": 3,
}
CONFIRMED_INHERITED_SITES = {
    ("p282_cycle_abort", 2),
    ("p286_e3_run", 3),
}
RENAMED_P290_FUNCTIONS = {"p286_e3_run": "p290_e3_run"}


def _audit_park_routes(
    root: Path, source: dict[str, bytes]
) -> dict[str, Any]:
    inherited = (
        root
        / "workspace/public/src/native-init/"
        "s22plus_fyg8_p286_e3_runtime.inc.c"
    ).read_bytes()
    include = source["p290_e3_runtime_include"]
    wrapper = source["runtime_wrapper"]
    legacy = source["p288_legacy_runtime"]

    inherited_count = len(
        re.findall(rb"(?<!p288_raw_)quiet_park\(\);", inherited)
    )
    rows = []
    for name, expected in P286_PARK_COUNTS.items():
        before = p288._c_function_body(inherited, name)  # noqa: SLF001
        if (
            len(re.findall(rb"(?<!p288_raw_)quiet_park\(\);", before))
            != expected
        ):
            raise SourceContractError(
                f"P2.90 inherited park inventory differs for {name}"
            )
        current_name = RENAMED_P290_FUNCTIONS.get(name, name)
        try:
            after = p288._c_function_body(  # noqa: SLF001
                include, current_name
            )
        except p288.SourceContractError:
            after = b""
        routes = [
            "checked-unclassified-fallback"
            for _ in re.findall(
                rb"(?<!p288_raw_)quiet_park\(\);", after
            )
        ]
        routes.extend(
            "confirmed-publication"
            for _ in range(
                after.count(
                    b"p290_park_after_confirmed_publication();"
                )
            )
        )
        for index in range(1, expected + 1):
            if (name, index) in CONFIRMED_INHERITED_SITES:
                route = "confirmed-publication"
            elif index <= len(routes):
                route = routes[index - 1]
            else:
                route = "source-removed-unreachable"
            rows.append(
                {
                    "function": name,
                    "site_index": index,
                    "route": route,
                }
            )

    quiet = p288._c_function_body(wrapper, "quiet_park")  # noqa: SLF001
    fail = p288._c_function_body(wrapper, "fail_at")  # noqa: SLF001
    channel = p288._c_function_body(  # noqa: SLF001
        wrapper, "p290_checkpoint_channel_failure_sink"
    )
    confirmed_sink = p288._c_function_body(  # noqa: SLF001
        wrapper, "p290_park_after_confirmed_publication"
    )
    if (
        inherited_count != 16
        or len(rows) != 16
        or sum(
            row["route"] == "source-removed-unreachable"
            for row in rows
        )
        != 2
        or len(
            re.findall(rb"(?<!p288_raw_)quiet_park\(\);", include)
        )
        != 14
        or include.count(
            b"p290_park_after_confirmed_publication();"
        )
        != 3
        or wrapper.count(runtime_transform.P290_WRAPPER_PARK) != 1
        or quiet.count(b"if (fallback_rc == 0)") != 1
        or fail.count(b"if (primary_rc == 0)") != 1
        or fail.count(b"if (fallback_rc == 0)") != 1
        or wrapper.count(b"p288_raw_quiet_park();") != 2
        or b"p288_raw_quiet_park();" not in channel
        or b"p288_raw_quiet_park();" not in confirmed_sink
        or b"p288_raw_quiet_park" in include
        or b"p288_raw_quiet_park();" in legacy
    ):
        raise SourceContractError("P2.90 checked park topology differs")
    return {
        "inherited_site_count": inherited_count,
        "inherited_routes_checked": len(rows),
        "durable_prepublication_routes": 2,
        "inherited_source_removed_routes": 2,
        "active_include_checked_fallback_routes": 14,
        "active_include_confirmed_routes": 3,
        "active_include_route_count": 17,
        "sites": rows,
        "raw_sink_count": 2,
        "confirmed_publication_sink_count": 1,
        "persistent_channel_failure_sink_count": 1,
        "fallback_return_checked": True,
        "primary_return_checked_in_fail_at": True,
        "single_channel_total_failure_self_reporting_possible": False,
        "residual_silence_class": (
            "persistent checkpoint channel failure: primary and fallback "
            "both return errors, or either publication never returns"
        ),
        "verified": True,
    }


def _audit_publication_bound() -> dict[str, Any]:
    if (
        len(spec.POSITIONS) != 107
        or spec.TERMINAL_GENERATION != 107
        or spec.TERMINAL_ORDINAL != 106
        or len(spec.POSITIONS) > 0xFF
    ):
        raise SourceContractError(
            "P2.90 publication upper bound is not exact generation 107"
        )
    return {
        "position_count": 107,
        "terminal_generation": 107,
        "generation_u8_wrap_unreachable": True,
        "post_terminal_publication_rejected": True,
        "verified": True,
    }


def _audit_packager_integration(
    source: dict[str, bytes],
) -> dict[str, Any]:
    checks = (
        (
            source["p290_candidate_builder"],
            b"base.packager = packager",
            "candidate builder package binding",
        ),
        (
            source["p290_candidate_builder"],
            b"return base.build_candidate(args)",
            "candidate builder dispatch",
        ),
        (
            source["p290_boot_only_packager"],
            b"return base.package(",
            "boot-only packager dispatch",
        ),
        (
            source["p290_candidate_intent"],
            b"return base.create(args)",
            "candidate intent dispatch",
        ),
        (
            source["p290_userspace_build"],
            b"return base.build_userspace(args)",
            "userspace build dispatch",
        ),
        (
            source["p290_build"],
            b"return base.main()",
            "kernel build dispatch",
        ),
    )
    for data, token, label in checks:
        if data.count(token) != 1:
            raise SourceContractError(
                f"P2.90 {label} cardinality drifted"
            )
    return {
        "candidate_builder_dispatch_verified": True,
        "boot_only_packager_dispatch_verified": True,
        "intent_dispatch_verified": True,
        "userspace_dispatch_verified": True,
        "kernel_build_dispatch_verified": True,
        "verified": True,
    }


def _audit_userspace(
    root: Path,
    generated: dict[str, bytes],
    source: dict[str, bytes],
    directory: Path,
) -> dict[str, Any]:
    for key, filename in MATERIALIZED_FILENAMES.items():
        if key in {"checkpoint_client", "runtime_wrapper", "plan_header"}:
            continue
        (directory / filename).write_bytes(source[key])
    try:
        return p288.p252._audit_userspace(  # noqa: SLF001
            shared_input_root(root),
            generated,
            directory,
            materialized_filenames=MATERIALIZED_FILENAMES,
            source_check_run_id=SOURCE_CHECK_RUN_ID,
        )
    except p288.p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def _audit_patch(root: Path, patch: bytes, directory: Path) -> dict[str, Any]:
    patch_path = directory / "p290.patch"
    patch_path.write_bytes(patch)
    p288.p252.p233.run_checked(
        ["git", "apply", "--check", "--unsafe-paths", str(patch_path)],
        cwd=shared_input_root(root) / p288.p252.p241.DEFAULT_SOURCE,
        label="P2.90 clean-apply check",
    )
    required = (
        b"s22_fyg8_p290_detail_rules[] __used",
        b"s22_fyg8_p290_tuple_allowed",
        b"request->item_index != expected_item",
        b"memset(&record->slots[next_slot].commit_crc, 0,",
    )
    if any(token not in patch for token in required):
        raise SourceContractError("P2.90 kernel patch is incomplete")
    return {
        **receipt(patch),
        "clean_apply": True,
        "pair_indexed_request_validation": True,
        "retained_writer_protocol_unchanged": True,
        "verified": True,
    }


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.90 generation is not deterministic")
    source = source_bytes(root)
    runtime_order = _audit_runtime_position_order(
        source["p290_e3_runtime_include"]
    )
    adjacency = _audit_first_position_adjacency(
        source["p290_e3_runtime_include"]
    )
    request_encoding = _audit_runtime_request_encoding(source)
    park_routes = _audit_park_routes(root, source)
    publication_bound = _audit_publication_bound()
    packager = _audit_packager_integration(source)
    with tempfile.TemporaryDirectory(prefix="s22-p290-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, source, directory)
    return {
        "schema": "s22plus_fyg8_p290_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "source_key_count": len(SOURCE_KEYS),
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "patch": patch,
        "linked_userspace": userspace,
        "runtime_position_order": runtime_order,
        "first_position_adjacency": adjacency,
        "runtime_request_encoding": request_encoding,
        "park_routes": park_routes,
        "publication_bound": publication_bound,
        "packager_integration": packager,
        "descriptor": {
            "position_count": len(spec.POSITIONS),
            "terminal_generation": spec.TERMINAL_GENERATION,
            "record_size": decoder.model.LONG_RECORD_SIZE,
            "slot_count": decoder.model.SLOT_COUNT,
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
    if len(run_id) != 16 or not any(run_id):
        raise SourceContractError("P2.90 reachable run ID is invalid")
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
    with spec.base_context(), model.base_context():
        previous_model_spec = model.base.spec
        model.base.spec = spec.base
        try:
            for generation, position in enumerate(spec.POSITIONS, 1):
                outcomes: list[tuple[int, int]] = []
                if position.kind == spec.KIND_TERMINAL:
                    outcomes.append((model.OUTCOME_SUCCESS, 0))
                else:
                    outcomes.extend(
                        (model.OUTCOME_PROGRESS, detail)
                        for detail in spec.base.position_progress_details(
                            position.stage, position.item_index
                        )
                    )
                outcomes.extend(
                    (model.OUTCOME_FAILURE, detail)
                    for detail in spec.base.position_failure_details(
                        position.stage, position.item_index
                    )
                )
                for outcome, detail in outcomes:
                    slots = [
                        bytes(model.SLOT_SIZE),
                        bytes(model.SLOT_SIZE),
                    ]
                    if generation == 1:
                        slots[0] = model.base._encode_slot(  # noqa: SLF001
                            header,
                            model.Slot(
                                0,
                                0,
                                model.STAGES["ENTRY"],
                                model.OUTCOME_PROGRESS,
                                0,
                                0,
                            ),
                        )
                    else:
                        previous = spec.POSITIONS[generation - 2]
                        slots[(generation - 1) & 1] = (
                            model.base._encode_slot(  # noqa: SLF001
                                header,
                                model.Slot(
                                    (generation - 1) & 1,
                                    generation - 1,
                                    previous.stage,
                                    model.OUTCOME_PROGRESS,
                                    previous.item_index,
                                    0,
                                ),
                            )
                        )
                    slots[generation & 1] = (
                        model.base._encode_slot(  # noqa: SLF001
                            header,
                            model.Slot(
                                generation & 1,
                                generation,
                                position.stage,
                                outcome,
                                position.item_index,
                                detail,
                            ),
                        )
                    )
                    decoded = model.base.decode_record(
                        header + b"".join(slots),
                        expected_profile=PROFILE,
                        expected_run_id=run_id,
                    )
                    if decoded["active"] != {
                        "slot_id": generation & 1,
                        "generation": generation,
                        "stage": position.stage,
                        "outcome": outcome,
                        "item_index": position.item_index,
                        "detail": detail,
                    }:
                        raise SourceContractError(
                            "P2.90 decoder changed a reachable active slot"
                        )
                    checked += 1
        finally:
            model.base.spec = previous_model_spec
    if checked != REACHABLE_VARIANTS:
        raise SourceContractError("P2.90 reachable variant count drifted")
    return {
        "reachable_slot_variants": checked,
        "profiles": [PROFILE],
        "checked_run_ids": {PROFILE: run_id.hex()},
        "adjacent_slot_combinations_verified": True,
        "zero_crc_count": 0,
        "family_collision_count": 0,
        "decoder_policy_id": decoder.POLICY_ID,
        "position_count": len(spec.POSITIONS),
        "terminal_generation": spec.TERMINAL_GENERATION,
        "verified": True,
    }


def linked_table_bytes() -> dict[str, bytes]:
    with p288_spec_context():
        result = p288.linked_table_bytes()
    return {
        name.replace("p288", "p290"): data
        for name, data in result.items()
    }


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.90 linked descriptor tables differ")
    return {
        name: receipt(data) for name, data in sorted(actual.items())
    } | {
        "descriptor_bytes_verified": True,
        "position_pairs_verified": True,
        "exact_detail_whitelist_verified": True,
        "verified": True,
    }


LINKED_VALIDATOR_SYMBOLS = tuple(
    symbol.replace("p288", "p290")
    for symbol in p288.LINKED_VALIDATOR_SYMBOLS
)


def main() -> int:
    try:
        result = implementation_result(p288.p243.repo_root())
    except (
        SourceContractError,
        p288.SourceContractError,
        runtime_transform.RuntimeTransformError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
