#!/usr/bin/env python3
"""Typed observation contracts for Device Action Process v2."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint
import s22plus_fyg8_p219_same_ring_decoder as same_ring
import s22plus_fyg8_p230_same_ring_multiboot_decoder as same_ring_multiboot
import s22plus_fyg8_p233_e1_decoder as e1_latest_stage
import s22plus_fyg8_p242_e2_stock_closure as e2_closure
import s22plus_fyg8_p253_e2_stock_closure as e2_closure_selector
import s22plus_fyg8_source_contracts as source_contracts


MARKER_KIND = "retained_marker_after_rollback"
CHECKPOINT_KIND = "retained_checkpoint_after_rollback"
PID1_USERSPACE_KIND = "retained_pid1_userspace_after_rollback"
SAME_RING_KIND = "retained_pid1_same_ring_discriminator_after_rollback"
SAME_RING_MULTIBOOT_KIND = (
    "retained_pid1_same_ring_multiboot_discriminator_after_rollback"
)
E1_LATEST_STAGE_KIND = "retained_e1_latest_stage_multiboot_after_rollback"
CHECKPOINT_DECODER = "s22plus_fyg8_r4w1e_checkpoint_v1"
PID1_USERSPACE_DECODER = "s22plus_fyg8_r4w1e0_pid1_userspace_v1"
SAME_RING_DECODER = "s22plus_fyg8_p219_same_ring_v1"
SAME_RING_MULTIBOOT_DECODER = "s22plus_fyg8_p230_same_ring_multiboot_v1"
E1_LATEST_STAGE_DECODER = e1_latest_stage.DECODER_ID
E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p234_run_manifest_v1"
E1_LATEST_STAGE_STATIC_SCHEMA = "s22plus_fyg8_p234_process_v2_static_result_v1"
E1_LATEST_STAGE_STATIC_VERDICT = "PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION"
E1_LATEST_STAGE_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p234_candidate_static_checker_v1"
)
E1_LATEST_STAGE_CANDIDATE_STATIC_VERDICT = (
    "PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA = (
    "s22plus_fyg8_p234_candidate_contract_v1"
)
E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT = (
    "PASS_P234_CANDIDATE_CONTRACT_HOST_ONLY"
)
E1_LATEST_STAGE_PREIMAGE_SCHEMA = (
    "s22plus_fyg8_p234_candidate_identity_preimage_v1"
)
E1_LATEST_STAGE_RUN_ID_DOMAINS = {
    "E1A": b"S22PLUS-FYG8-P234-E1A-RUN-ID-V1\0",
    "E1B": b"S22PLUS-FYG8-P239-E1B-RUN-ID-V1\0",
    "E2": b"S22PLUS-FYG8-P242-E2-RUN-ID-V1\0",
}
E1_LATEST_STAGE_SOURCE_KEYS = {
    "E1A": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
    },
    "E1B": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
    },
    "E2": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "plan_header",
        "loader_core",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
        "planner",
        "dtbo_contract",
        "stock_closure",
    },
}
E1_LATEST_STAGE_KERNEL_INTERVAL = (4096, 41495040)
CHECKPOINT_SOURCE = "/proc/last_kmsg"
PID1_USERSPACE_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PID1_USERSPACE_ENTRY = b"\n[[S22P1U|ba234c7de4105b2a23222436284605f2]]\n"
PID1_USERSPACE_PROOF = b"\n[[S22P1U|ec8d029b05288644bbe7b5f7c7af190c]]\n"
PID1_USERSPACE_FAMILY = b"[[S22P1U|"
PID1_USERSPACE_PROBE_ID = "64554e8469385878c5bf8d57c44edeea"
SAME_RING_CONTRACT_ID = same_ring.CONTRACT_ID.hex()
SAME_RING_MULTIBOOT_POLICY_ID = same_ring_multiboot.POLICY_ID.hex()
SAME_RING_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p219_run_manifest_v1"
SAME_RING_STATIC_SCHEMA = "s22plus_fyg8_p219_candidate_static_checker_v1"
SAME_RING_STATIC_VERDICT = "PASS_P219_OFFLINE_CANDIDATE_STATIC_CONTRACT"
OUTCOME_NAMES = {
    checkpoint.OUTCOME_PROGRESS: "progress",
    checkpoint.OUTCOME_SUCCESS: "success",
    checkpoint.OUTCOME_FAILURE: "failure",
}
HEX32_RE = re.compile(r"[0-9a-f]{32}")
HASH_RE = re.compile(r"[0-9a-f]{64}")
E1_LATEST_STAGE_BASE_FILES = {
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "12661b7d249fb8f80135c3fdcd331733b86d5215f2f4e88e356d1516831ab493"
    ),
    "kernel_platform/common/init/Kconfig": (
        "8273d233a441c21df2fcb1d5d17a590321d758205fd5babd8b8dcb4e6a334019"
    ),
    "kernel_platform/common/init/main.c": (
        "7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a"
    ),
}
E1B_MODULE_SPECS = [
    {
        "file": "smem.ko",
        "runtime": "smem",
        "size": 28_704,
        "sha256": "27a80d5598329d6a526384d09806de63983204988748ea4e7d3fccfafc24a524",
    },
    {
        "file": "minidump.ko",
        "runtime": "minidump",
        "size": 37_312,
        "sha256": "e5e6f4dfe1ddac2cd4f8d15c11a50d4d32b6e9de278fedbed44747630a5c554d",
    },
    {
        "file": "qcom-scm.ko",
        "runtime": "qcom_scm",
        "size": 218_384,
        "sha256": "e12ba8661808c2c47acf42c9939157e509fcdb5b98f6e650f79b92dba18a1af3",
    },
    {
        "file": "qcom_wdt_core.ko",
        "runtime": "qcom_wdt_core",
        "size": 48_640,
        "sha256": "ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599",
    },
    {
        "file": "gh_virt_wdt.ko",
        "runtime": "gh_virt_wdt",
        "size": 18_944,
        "sha256": "f030c5486a41b1fbe4b0ea3aa85a401dd16daa1f1a551a626f6ea424ee90dd39",
    },
]
E1B_MODULE_FILES = [row["file"] for row in E1B_MODULE_SPECS]
E1B_MODULE_RUNTIME_NAMES = [row["runtime"] for row in E1B_MODULE_SPECS]
E1B_MODULE_ORDER_MODEL = (
    "modules.dep topological order with stock modules.load.recovery tie-breaks"
)
E1B_STOCK_RECOVERY_POSITIONS = {
    "gh_virt_wdt.ko": 5,
    "minidump.ko": 51,
    "qcom-scm.ko": 83,
    "qcom_wdt_core.ko": 6,
    "smem.ko": 124,
}
E1B_VENDOR_METADATA_HASHES = {
    "modules.alias": "5679e647fcdcb6a13bd4f20d24a901f158e641fbd0a813274c99006ec8fa2c20",
    "modules.dep": "21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27",
    "modules.load": "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232",
    "modules.load.recovery": "616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10",
    "modules.softdep": "21d6a678d186356c2fb0349a8a9a5190e6e225dab0feb5012e495a100c33afb0",
}
E1B_COMPOSITION_ORDER = ["generic", "vendor[0]/"]
E1B_EFFECTIVE_ENTRY_COUNT = 474
E1B_EFFECTIVE_MODULE_ROWS = [
    {"file": name, "runtime": runtime, "layer": "vendor[0]/"}
    for name, runtime in zip(E1B_MODULE_FILES, E1B_MODULE_RUNTIME_NAMES)
]
E1B_ELF_ENTRYPOINTS = {"init": 4_198_200, "child": 4_194_508}
E1B_STOCK_VENDOR_BOOT = {
    "size": 100_663_296,
    "sha256": "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7",
}


def _e1_reachable_slot_variant_count(
    profile: str, source_contract_id: str | None = None
) -> int:
    if source_contract_id is not None:
        return _selected_contract(
            source_contract_id, profile
        ).contract.reachable_variants
    model = e1_latest_stage.model
    sequence = model.PROFILE_STAGE_SEQUENCES.get(profile)
    terminal = model.PROFILE_TERMINALS.get(profile)
    if not sequence or sequence[-1] != terminal or sequence.count(terminal) != 1:
        raise EvidenceError("E1 profile stage sequence is not terminal-bound")
    return sum(1 if stage == terminal else 1 + 4095 for stage in sequence)


class EvidenceError(ValueError):
    pass


def _selected_contract(
    source_contract_id: str | None, profile: str
) -> source_contracts.SelectedSourceContract:
    try:
        return source_contracts.select(source_contract_id, profile)
    except source_contracts.SourceContractSelectionError as exc:
        raise EvidenceError(str(exc)) from exc


def _latest_stage_decoder(
    source_contract_id: str | None, profile: str
):
    if source_contract_id is None:
        return e1_latest_stage
    return _selected_contract(source_contract_id, profile).decoder


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise EvidenceError(f"{label} keys do not match the evidence schema")
    return value


def _artifact(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"path", "size", "sha256"}, label)
    if (
        not isinstance(item["path"], str)
        or not item["path"]
        or isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= 1024 * 1024
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def _artifact_matches(value: Any, expected: dict[str, Any]) -> bool:
    return (
        isinstance(value, dict)
        and value.get("size") == expected.get("size")
        and value.get("sha256") == expected.get("sha256")
    )


def _binary_identity(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"size", "sha256"}, label)
    if (
        isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= 2**40
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def validate_candidate_source_preimage(
    contract: dict[str, Any], profile: str, run_id: str
) -> dict[str, dict[str, Any]]:
    source_contract_id = contract.get("source_contract_id")
    selected_decoder = _latest_stage_decoder(source_contract_id, profile)
    preimage_keys = {
        "schema",
        "target",
        "profile",
        "profile_number",
        "nonce",
        "decoder_id",
        "decoder_policy_id",
        "record_layout",
        "sources",
    }
    if source_contract_id is not None:
        _selected_contract(source_contract_id, profile)
        preimage_keys.add("source_contract_id")
    preimage = _exact(
        contract.get("identity_preimage"),
        preimage_keys,
        "candidate identity preimage",
    )
    source_keys = (
        _selected_contract(source_contract_id, profile).source_keys
        if source_contract_id is not None
        else E1_LATEST_STAGE_SOURCE_KEYS.get(profile)
    )
    sources = preimage.get("sources")
    if source_keys is None or not isinstance(sources, dict) or set(sources) != source_keys:
        raise EvidenceError("candidate identity source set is invalid")
    normalized_sources = {
        name: _binary_identity(value, f"candidate source {name}")
        for name, value in sources.items()
    }
    preimage_sha256 = hashlib.sha256(_canonical(preimage)).hexdigest()
    nonce = preimage.get("nonce")
    expected_schema = (
        _selected_contract(source_contract_id, profile).preimage_schema
        if source_contract_id is not None
        else E1_LATEST_STAGE_PREIMAGE_SCHEMA
    )
    run_id_domain = (
        _selected_contract(source_contract_id, profile).run_id_domain
        if source_contract_id is not None
        else E1_LATEST_STAGE_RUN_ID_DOMAINS[profile]
    )
    if (
        preimage.get("schema") != expected_schema
        or preimage.get("source_contract_id") != source_contract_id
        or preimage.get("target") != PID1_USERSPACE_TARGET
        or preimage.get("profile") != profile
        or type(preimage.get("profile_number")) is not int
        or preimage.get("profile_number")
        != selected_decoder.model.PROFILE_NUMBERS[profile]
        or not isinstance(nonce, str)
        or HEX32_RE.fullmatch(nonce) is None
        or nonce == "0" * 32
        or preimage.get("decoder_id") != selected_decoder.DECODER_ID
        or preimage.get("decoder_policy_id") != selected_decoder.POLICY_ID
        or preimage.get("record_layout") != "S22E1L1-45-ab-crc32"
        or contract.get("identity_preimage_sha256") != preimage_sha256
        or hashlib.sha256(
            run_id_domain + _canonical(preimage)
        ).digest()[:16].hex()
        != run_id
    ):
        raise EvidenceError("candidate source preimage or run ID derivation is invalid")
    return normalized_sources


def validate_e2_ap_payload(
    frame: bytes, closure: Any
) -> dict[str, Any]:
    source_contract_id = (
        closure.get("source_contract_id") if isinstance(closure, dict) else None
    )
    expected_keys = {
        "boot_img_lz4",
        "boot_image",
        "image",
        "init",
        "child",
        "run_id",
        "module_closure",
        "effective_rootfs",
    }
    if source_contract_id is not None:
        _selected_contract(source_contract_id, "E2")
        expected_keys.add("source_contract_id")
    closure_api = e2_closure_selector.select(source_contract_id)
    expected = _exact(
        closure,
        expected_keys,
        "E2 AP payload closure",
    )
    identities = {
        name: _binary_identity(value, f"E2 AP {name}")
        for name, value in expected.items()
        if name in {"boot_img_lz4", "boot_image", "image", "init", "child"}
    }
    run_id = expected.get("run_id")
    if not isinstance(run_id, str) or HEX32_RE.fullmatch(run_id) is None:
        raise EvidenceError("E2 AP run ID is invalid")
    try:
        module_closure = closure_api.validate_module_closure(
            expected.get("module_closure")
        )
        effective_rootfs = closure_api.validate_effective_rootfs(
            expected.get("effective_rootfs"),
            expected_init=identities["init"],
            expected_child=identities["child"],
            module_closure=module_closure,
        )
    except e2_closure.ClosureError as exc:
        raise EvidenceError("E2 AP semantic closure is invalid") from exc
    if e2_closure.receipt(frame) != identities["boot_img_lz4"]:
        raise EvidenceError("E2 AP boot member identity mismatch")
    try:
        boot_payload = e2_closure.boot_verify.decompress_lz4_frame_python(
            frame,
            expected_size=identities["boot_image"]["size"],
        )
        if e2_closure.receipt(boot_payload) != identities["boot_image"]:
            raise EvidenceError("E2 AP decoded boot identity mismatch")
        boot = e2_closure.boot_verify.parse_boot_v4(boot_payload)
        if e2_closure.receipt(boot.kernel) != identities["image"]:
            raise EvidenceError("E2 AP kernel identity mismatch")
        ramdisk = e2_closure.boot_verify.decompress_lz4_stream_python(
            boot.ramdisk, maximum=128 * 1024 * 1024
        )
        entries = e2_closure.boot_verify.parse_newc(ramdisk)
        generic_rootfs = closure_api.audit_candidate_generic_rootfs(
            boot,
            entries,
            expected_init=identities["init"],
            expected_child=identities["child"],
            run_id=bytes.fromhex(run_id),
            module_closure=module_closure,
        )
    except e2_closure.boot_verify.BootVerifyError as exc:
        raise EvidenceError("E2 AP payload cannot be independently decoded") from exc
    except e2_closure.ClosureError as exc:
        raise EvidenceError("E2 AP executable semantics mismatch") from exc
    if _canonical(generic_rootfs) != _canonical(effective_rootfs["generic_rootfs"]):
        raise EvidenceError("E2 AP generic rootfs differs from static closure")
    return {"verified": True, **identities, "generic_rootfs": generic_rootfs}


def validate_e1b_stock_closure(
    *,
    module_closure: Any,
    effective_rootfs: Any,
    stock_vendor_boot: Any,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
) -> None:
    closure = _exact(
        module_closure,
        {
            "files",
            "runtime_names",
            "count",
            "modules",
            "order_model",
            "stock_recovery_positions",
            "vendor_metadata_hashes",
        },
        "E1B module closure",
    )
    expected_closure = {
        "files": E1B_MODULE_FILES,
        "runtime_names": E1B_MODULE_RUNTIME_NAMES,
        "count": len(E1B_MODULE_FILES),
        "modules": E1B_MODULE_SPECS,
        "order_model": E1B_MODULE_ORDER_MODEL,
        "stock_recovery_positions": E1B_STOCK_RECOVERY_POSITIONS,
        "vendor_metadata_hashes": E1B_VENDOR_METADATA_HASHES,
    }
    if closure != expected_closure:
        raise EvidenceError("E1B stock module derivation differs from the pinned closure")

    rootfs = _exact(
        effective_rootfs,
        {
            "composition_order",
            "entry_count",
            "no_duplicate_override_or_alias",
            "init",
            "child",
            "modules",
            "module_count",
            "rdinit_override_absent",
            "verified",
        },
        "E1B effective rootfs",
    )
    init = _exact(
        rootfs["init"],
        {"size", "sha256", "elf", "run_id_count"},
        "E1B effective init",
    )
    child = _exact(
        rootfs["child"], {"size", "sha256", "elf"}, "E1B effective child"
    )
    init_elf = _exact(
        init["elf"],
        {
            "machine",
            "entrypoint",
            "interpreter",
            "dynamic",
            "executable_stack",
            "entrypoint_mapped",
            "verified",
        },
        "E1B effective init ELF",
    )
    child_elf = _exact(
        child["elf"],
        {
            "machine",
            "entrypoint",
            "interpreter",
            "dynamic",
            "executable_stack",
            "entrypoint_mapped",
            "verified",
        },
        "E1B effective child ELF",
    )
    expected_elf = {
        "machine": "AArch64",
        "interpreter": False,
        "dynamic": False,
        "executable_stack": False,
        "entrypoint_mapped": True,
        "verified": True,
    }
    if (
        _binary_identity(
            {name: init[name] for name in ("size", "sha256")},
            "E1B effective init",
        )
        != expected_init
        or _binary_identity(
            {name: child[name] for name in ("size", "sha256")},
            "E1B effective child",
        )
        != expected_child
        or init.get("run_id_count") != 1
        or init_elf
        != {**expected_elf, "entrypoint": E1B_ELF_ENTRYPOINTS["init"]}
        or child_elf
        != {**expected_elf, "entrypoint": E1B_ELF_ENTRYPOINTS["child"]}
        or rootfs.get("composition_order") != E1B_COMPOSITION_ORDER
        or rootfs.get("entry_count") != E1B_EFFECTIVE_ENTRY_COUNT
        or rootfs.get("no_duplicate_override_or_alias") is not True
        or rootfs.get("modules") != E1B_EFFECTIVE_MODULE_ROWS
        or rootfs.get("module_count") != len(E1B_EFFECTIVE_MODULE_ROWS)
        or rootfs.get("rdinit_override_absent") is not True
        or rootfs.get("verified") is not True
    ):
        raise EvidenceError("E1B effective stock rootfs differs from the pinned closure")

    if _binary_identity(stock_vendor_boot, "E1B stock vendor_boot") != E1B_STOCK_VENDOR_BOOT:
        raise EvidenceError("E1B stock vendor_boot identity changed")


def _record_blob_claim(
    value: Any, label: str, artifact: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "label",
            "size",
            "sha256",
            "entry_count",
            "userspace_count",
            "unsat_count",
            "long_family_count",
            "unsat_family_count",
            "old_e0_entry_count",
            "old_e0_userspace_count",
            "verified",
        },
        label,
    )
    expected_counts = {
        "entry_count": 1,
        "userspace_count": 1,
        "unsat_count": 1,
        "long_family_count": 2,
        "unsat_family_count": 1,
        "old_e0_entry_count": 0,
        "old_e0_userspace_count": 0,
    }
    if (
        item["label"] != label
        or not _artifact_matches(item, artifact)
        or any(item[key] != count for key, count in expected_counts.items())
        or item["verified"] is not True
    ):
        raise EvidenceError(f"{label} record claim is invalid")
    return item


def _bounded_text(value: Any, label: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or "\x00" in value
    ):
        raise EvidenceError(f"{label} must be a bounded string")
    return value


def validate_acceptance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("acceptance must be an object")
    kind = value.get("kind")
    if kind == MARKER_KIND:
        item = _exact(
            value,
            {"kind", "source", "marker", "family", "exact_count"},
            "marker acceptance",
        )
        if item["source"] != CHECKPOINT_SOURCE or item["exact_count"] != 1:
            raise EvidenceError("marker acceptance source or count is invalid")
        _bounded_text(item["marker"], "acceptance.marker", 512)
        _bounded_text(item["family"], "acceptance.family", 128)
        return item
    if kind == SAME_RING_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "records",
                "families",
                "accepted_identity",
                "exact_count",
                "contract",
            },
            "same-ring acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"] != "USERSPACE_CALLBACK_REACHED"
            or item["exact_count"] != 1
        ):
            raise EvidenceError("same-ring acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring contract",
        )
        _artifact(contract["run_manifest"], "same-ring contract run_manifest")
        _artifact(contract["static_check"], "same-ring contract static_check")
        return item
    if kind == SAME_RING_MULTIBOOT_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "policy_id",
                "records",
                "families",
                "accepted_identity",
                "minimum_exact_count",
                "contract",
            },
            "same-ring multiboot acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_MULTIBOOT_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["policy_id"] != SAME_RING_MULTIBOOT_POLICY_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"]
            != "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS"
            or item["minimum_exact_count"] != 1
        ):
            raise EvidenceError("same-ring multiboot acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring multiboot contract",
        )
        _artifact(
            contract["run_manifest"],
            "same-ring multiboot contract run_manifest",
        )
        _artifact(
            contract["static_check"],
            "same-ring multiboot contract static_check",
        )
        return item
    if kind == E1_LATEST_STAGE_KIND:
        source_contract_id = value.get("source_contract_id")
        expected_keys = {
            "kind",
            "source",
            "decoder",
            "policy_id",
            "profile",
            "run_id",
            "long_family_hex",
            "unsat_family_hex",
            "terminal_stage",
            "minimum_success_count",
            "clean_baseline_required",
            "contract",
        }
        if source_contract_id is not None:
            expected_keys.add("source_contract_id")
        item = _exact(
            value,
            expected_keys,
            "E1 latest-stage acceptance",
        )
        profile = item["profile"]
        selected_decoder = _latest_stage_decoder(source_contract_id, profile)
        model = selected_decoder.model
        model_ids = {model.model_run_id(name).hex() for name in model.PROFILE_NUMBERS}
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != selected_decoder.DECODER_ID
            or item["policy_id"] != selected_decoder.POLICY_ID
            or profile not in model.PROFILE_NUMBERS
            or not isinstance(item["run_id"], str)
            or HEX32_RE.fullmatch(item["run_id"]) is None
            or item["run_id"] == "0" * 32
            or item["run_id"] in model_ids
            or item["long_family_hex"] != model.LONG_FAMILY.hex()
            or item["unsat_family_hex"] != model.UNSAT_FAMILY.hex()
            or item["terminal_stage"] != model.PROFILE_TERMINALS.get(profile)
            or item["minimum_success_count"] != 1
            or item["clean_baseline_required"] is not True
        ):
            raise EvidenceError("E1 latest-stage acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"candidate_static", "run_manifest", "static_check"},
            "E1 latest-stage contract",
        )
        _artifact(contract["candidate_static"], "E1 latest-stage candidate_static")
        _artifact(contract["run_manifest"], "E1 latest-stage run_manifest")
        _artifact(contract["static_check"], "E1 latest-stage static_check")
        return item
    if kind == PID1_USERSPACE_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "marker",
                "family",
                "exact_count",
                "decoder",
                "probe_id",
                "entry_marker",
                "contract",
            },
            "PID1 userspace acceptance",
        )
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["marker"] != PID1_USERSPACE_PROOF.decode("ascii")
            or item["entry_marker"] != PID1_USERSPACE_ENTRY.decode("ascii")
            or item["family"] != PID1_USERSPACE_FAMILY.decode("ascii")
            or item["exact_count"] != 1
            or item["decoder"] != PID1_USERSPACE_DECODER
            or item["probe_id"] != PID1_USERSPACE_PROBE_ID
        ):
            raise EvidenceError("PID1 userspace acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "PID1 userspace contract",
        )
        _artifact(contract["run_manifest"], "PID1 userspace contract run_manifest")
        _artifact(contract["static_check"], "PID1 userspace contract static_check")
        return item
    if kind != CHECKPOINT_KIND:
        raise EvidenceError("acceptance kind is not allowlisted")

    item = _exact(
        value,
        {
            "kind",
            "source",
            "marker",
            "family",
            "exact_count",
            "decoder",
            "profile",
            "run_id",
            "terminal_stage",
            "terminal_outcome",
            "require_two_valid_slots",
            "contract",
        },
        "checkpoint acceptance",
    )
    if (
        item["source"] != CHECKPOINT_SOURCE
        or item["marker"] != checkpoint.ENTRY_PROOF.decode("ascii")
        or item["family"] != checkpoint.ENTRY_FAMILY.decode("ascii")
        or item["exact_count"] != 1
        or item["decoder"] != CHECKPOINT_DECODER
        or item["profile"] != "E1"
        or item["terminal_stage"] != checkpoint.PROFILE_TERMINAL_STAGE["E1"]
        or item["terminal_outcome"] != "success"
        or item["require_two_valid_slots"] is not True
        or not isinstance(item["run_id"], str)
        or HEX32_RE.fullmatch(item["run_id"]) is None
        or item["run_id"] == "0" * 32
        or item["run_id"]
        == checkpoint.MODEL_RUN_IDS["E1"].hex()
    ):
        raise EvidenceError("checkpoint acceptance identity is invalid")
    contract = _exact(
        item["contract"], {"run_manifest", "static_check"}, "checkpoint contract"
    )
    _artifact(contract["run_manifest"], "checkpoint contract run_manifest")
    _artifact(contract["static_check"], "checkpoint contract static_check")
    return item


def contract_artifacts(acceptance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    item = validate_acceptance(acceptance)
    if item["kind"] not in {
        CHECKPOINT_KIND,
        PID1_USERSPACE_KIND,
        SAME_RING_KIND,
        SAME_RING_MULTIBOOT_KIND,
        E1_LATEST_STAGE_KIND,
    }:
        return {}
    return {
        name: dict(value)
        for name, value in item["contract"].items()
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceError(f"duplicate evidence JSON key: {key}")
        value[key] = item
    return value


def _json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} is not an object")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EvidenceError("run manifest is not canonical ASCII JSON") from exc


def _verify_checkpoint_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("offline checkpoint contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline checkpoint contract artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline checkpoint contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    run_id = canonical_sha256[:32]
    if (
        run_manifest.get("schema")
        != "s22plus_fyg8_r4w1e_e1_run_manifest_v1"
        or run_manifest.get("target") != checkpoint.TARGET
        or run_manifest.get("profile") != item["profile"]
        or run_manifest.get("checkpoint_carrier_sha256")
        != checkpoint.CARRIER_SHA256
        or run_manifest.get("checkpoint_patch_sha256") != checkpoint.PATCH_SHA256
        or run_id != item["run_id"]
    ):
        raise EvidenceError("run manifest does not bind the checkpoint acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e_e1_candidate_static_checker_v1"
        or static_result.get("target") != checkpoint.TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E_E1_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["run_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fresh_non_model_id") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
        or candidate.get("boot_only_ap") is not True
        or not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "device_write",
                "odin_invoked",
                "odin_transfer",
                "flash",
                "partition_write",
                "live_authorized",
            )
        )
    ):
        raise EvidenceError("static checker result does not bind the candidate")
    return {
        "schema": "device_action_f1_checkpoint_offline_contract_v2",
        "decoder": item["decoder"],
        "profile": item["profile"],
        "run_id": item["run_id"],
        "terminal_stage": item["terminal_stage"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "verified": True,
    }
def _verify_pid1_userspace_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("offline PID1 userspace contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline PID1 userspace artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline PID1 userspace contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    observation = run_manifest.get("observation_contract")
    if (
        run_manifest.get("schema") != "s22plus_fyg8_r4w1e0_run_manifest_v1"
        or run_manifest.get("target") != PID1_USERSPACE_TARGET
        or run_manifest.get("profile") != "E0"
        or run_manifest.get("probe_id") != item["probe_id"]
        or run_manifest.get("entry_proof")
        != PID1_USERSPACE_ENTRY.decode("ascii").strip()
        or run_manifest.get("userspace_proof")
        != PID1_USERSPACE_PROOF.decode("ascii").strip()
        or observation
        != {
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "baseline_family_count": 0,
            "post_family_count": 1,
        }
    ):
        raise EvidenceError("run manifest does not bind PID1 userspace acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e0_candidate_static_checker_v1"
        or static_result.get("target") != PID1_USERSPACE_TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E0_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["probe_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fixed_probe_id") is not True
        or binding.get("clean_baseline_required") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
        or candidate.get("boot_only_ap") is not True
        or not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "device_write",
                "odin_invoked",
                "odin_transfer",
                "flash",
                "partition_write",
                "live_authorized",
            )
        )
    ):
        raise EvidenceError("static checker result does not bind E0 candidate")
    return {
        "schema": "device_action_f1_pid1_userspace_offline_contract_v2",
        "decoder": item["decoder"],
        "probe_id": item["probe_id"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "verified": True,
    }


def _same_ring_records() -> dict[str, str]:
    return {
        "entry_hex": same_ring.ENTRY_PROOF.hex(),
        "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
        "unsat_hex": same_ring.UNSAT_PROOF.hex(),
    }


def _verify_same_ring_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] not in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        raise EvidenceError("offline same-ring contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline same-ring artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline same-ring contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "same-ring run manifest")
    static_result = _json(payloads["static_check"], "same-ring static result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    records = _same_ring_records()
    expected_observation = {
        "accepted_identity": "USERSPACE_CALLBACK_REACHED",
        "zero_classification": "ZERO_AMBIGUOUS",
        "entry_threshold": same_ring.ENTRY_SIZE,
        "unsat_threshold": same_ring.UNSAT_SIZE,
        "clean_baseline_required": True,
    }
    if (
        set(run_manifest)
        != {
            "schema",
            "target",
            "profile",
            "contract_id",
            "contract_sha256",
            "records",
            "observation_contract",
            "candidate_ap",
        }
        or run_manifest.get("schema") != SAME_RING_RUN_MANIFEST_SCHEMA
        or run_manifest.get("target") != same_ring.TARGET
        or run_manifest.get("profile") != "P219"
        or run_manifest.get("contract_id") != SAME_RING_CONTRACT_ID
        or run_manifest.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or run_manifest.get("records") != records
        or run_manifest.get("observation_contract") != expected_observation
        or not _artifact_matches(run_manifest.get("candidate_ap"), candidate_ap)
        or payloads["run_manifest"] != canonical
    ):
        raise EvidenceError("run manifest does not bind the same-ring candidate")

    if (
        set(static_result)
        != {
            "schema",
            "target",
            "verdict",
            "contract_id",
            "contract_sha256",
            "records",
            "run_binding",
            "candidate",
            "safety",
        }
        or static_result.get("schema") != SAME_RING_STATIC_SCHEMA
        or static_result.get("target") != same_ring.TARGET
        or static_result.get("verdict") != SAME_RING_STATIC_VERDICT
        or static_result.get("contract_id") != SAME_RING_CONTRACT_ID
        or static_result.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or static_result.get("records") != records
        or static_result.get("run_binding")
        != {
            "canonical_manifest_size": len(canonical),
            "canonical_manifest_sha256": canonical_sha256,
            "verified": True,
        }
    ):
        raise EvidenceError("static checker header does not bind P2.19 candidate")

    candidate = _exact(
        static_result["candidate"],
        {"artifacts", "record_verification"},
        "same-ring candidate",
    )
    artifacts = _exact(
        candidate["artifacts"],
        {"ap", "run_manifest", "image", "vmlinux", "boot_image"},
        "same-ring candidate artifacts",
    )
    identities = {
        name: _binary_identity(value, f"same-ring {name}")
        for name, value in artifacts.items()
    }
    verification = _exact(
        candidate["record_verification"],
        {
            "image",
            "vmlinux",
            "boot_image",
            "boot_kernel",
            "ap_members",
            "boot_only_ap",
            "verified",
        },
        "same-ring record verification",
    )
    image_claim = _record_blob_claim(
        verification["image"], "Image", identities["image"]
    )
    _record_blob_claim(
        verification["vmlinux"], "vmlinux", identities["vmlinux"]
    )
    boot_image_claim = _binary_identity(
        verification["boot_image"], "verified boot image"
    )
    boot_kernel_claim = _exact(
        verification["boot_kernel"],
        {"size", "sha256", "equals_image"},
        "verified boot kernel",
    )
    if (
        not _artifact_matches(identities["ap"], candidate_ap)
        or not _artifact_matches(
            identities["run_manifest"], receipts["run_manifest"]
        )
        or boot_image_claim != identities["boot_image"]
        or boot_kernel_claim
        != {
            "size": image_claim["size"],
            "sha256": image_claim["sha256"],
            "equals_image": True,
        }
        or verification["ap_members"]
        != [{"name": "boot.img.lz4", "type": "regular"}]
        or verification["boot_only_ap"] is not True
        or verification["verified"] is not True
        or static_result.get("safety")
        != {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        }
    ):
        raise EvidenceError("static checker result does not bind P2.19 candidate")
    multiboot = item["kind"] == SAME_RING_MULTIBOOT_KIND
    result = {
        "schema": (
            "device_action_f1_same_ring_multiboot_offline_contract_v1"
            if multiboot
            else "device_action_f1_same_ring_offline_contract_v2"
        ),
        "decoder": (
            SAME_RING_MULTIBOOT_DECODER if multiboot else SAME_RING_DECODER
        ),
        "contract_id": SAME_RING_CONTRACT_ID,
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "zero_is_ambiguous": True,
        "verified": True,
    }
    if multiboot:
        result["policy_id"] = SAME_RING_MULTIBOOT_POLICY_ID
        result["minimum_exact_count"] = 1
    return result


def _verify_e1_latest_stage_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != E1_LATEST_STAGE_KIND:
        raise EvidenceError("offline E1 latest-stage contract is not applicable")
    profile = item["profile"]
    source_contract_id = item.get("source_contract_id")
    selected_decoder = _latest_stage_decoder(source_contract_id, profile)
    if set(payloads) != {
        "candidate_static",
        "run_manifest",
        "static_check",
    } or set(receipts) != set(payloads):
        raise EvidenceError(
            "P2.34 E1 latest-stage evidence has no candidate-bound offline contract"
        )
    for name, payload in payloads.items():
        pin = item["contract"][name]
        value = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or value.get("size") != pin["size"]
            or value.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline E1 latest-stage contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "E1 latest-stage run manifest")
    static_result = _json(payloads["static_check"], "E1 latest-stage static result")
    if (
        run_manifest.get("schema") != E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA
        or static_result.get("schema") != E1_LATEST_STAGE_STATIC_SCHEMA
    ):
        raise EvidenceError(
            "P2.34 E1 latest-stage evidence has no candidate-bound offline contract"
        )
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    expected_records = {
        "long_family_hex": selected_decoder.model.LONG_FAMILY.hex(),
        "unsat_family_hex": selected_decoder.model.UNSAT_FAMILY.hex(),
        "terminal_stage": item["terminal_stage"],
    }
    expected_observation = {
        "accepted_identity": f"{profile}_TERMINAL_SUCCESS_REACHED",
        "minimum_success_count": 1,
        "clean_baseline_required": True,
    }
    run_manifest_keys = {
        "schema",
        "target",
        "profile",
        "run_id",
        "decoder",
        "policy_id",
        "records",
        "observation_contract",
        "candidate_ap",
        "candidate_static",
    }
    if source_contract_id is not None:
        run_manifest_keys.add("source_contract_id")
    if (
        set(run_manifest) != run_manifest_keys
        or run_manifest.get("schema") != E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA
        or run_manifest.get("target") != PID1_USERSPACE_TARGET
        or run_manifest.get("profile") != item["profile"]
        or run_manifest.get("source_contract_id") != source_contract_id
        or run_manifest.get("run_id") != item["run_id"]
        or run_manifest.get("decoder") != selected_decoder.DECODER_ID
        or run_manifest.get("policy_id") != selected_decoder.POLICY_ID
        or run_manifest.get("records") != expected_records
        or run_manifest.get("observation_contract") != expected_observation
        or not _artifact_matches(run_manifest.get("candidate_ap"), candidate_ap)
        or payloads["run_manifest"] != canonical
    ):
        raise EvidenceError("run manifest does not bind the E1 candidate")
    candidate_static = _binary_identity(
        run_manifest.get("candidate_static"), "E1A candidate static result"
    )
    if not _artifact_matches(receipts["candidate_static"], candidate_static):
        raise EvidenceError("run manifest does not bind the candidate static payload")

    candidate_static_result = _json(
        payloads["candidate_static"], "E1A candidate static result"
    )
    if (
        set(candidate_static_result)
        != {
            "schema",
            "target",
            "verdict",
            "candidate_contract",
            "build_repro",
            "candidate",
            "tools",
            "limits",
            "safety",
        }
        or candidate_static_result.get("schema")
        != E1_LATEST_STAGE_CANDIDATE_STATIC_SCHEMA
        or candidate_static_result.get("target") != PID1_USERSPACE_TARGET
        or candidate_static_result.get("verdict")
        != E1_LATEST_STAGE_CANDIDATE_STATIC_VERDICT
    ):
        raise EvidenceError("candidate static result header is not accepted")
    source_contract_keys = {
        "schema",
        "target",
        "verdict",
        "profile",
        "profile_number",
        "run_id",
        "unsat_record_hex",
        "unsat_tag_hex",
        "decoder_id",
        "decoder_policy_id",
        "identity_preimage",
        "identity_preimage_sha256",
        "intent",
        "patch",
        "base_files",
        "patched_files",
        "config_lines",
        "reachable_record_contract",
        "verified",
        "safety",
    }
    if source_contract_id is not None:
        source_contract_keys.update(
            {"source_contract_id", "materialized_sources"}
        )
    source_contract = _exact(
        candidate_static_result.get("candidate_contract"),
        source_contract_keys,
        "E1A candidate source contract",
    )
    if source_contract.get("source_contract_id") != source_contract_id:
        raise EvidenceError("candidate source contract selector mismatch")
    run_id = bytes.fromhex(item["run_id"])
    candidate_source_receipts = validate_candidate_source_preimage(
        source_contract, profile, item["run_id"]
    )
    if source_contract_id is not None:
        selected_contract = _selected_contract(source_contract_id, profile)
        materialized = _exact(
            source_contract.get("materialized_sources"),
            set(selected_contract.materialized_filenames),
            "versioned materialized source contract",
        )
        for name, filename in selected_contract.materialized_filenames.items():
            row = _exact(
                materialized.get(name),
                {"path", "size", "sha256"},
                f"versioned materialized source {name}",
            )
            if (
                row.get("path") != f"materialized-sources/{filename}"
                or {
                    key: row.get(key) for key in ("size", "sha256")
                }
                != candidate_source_receipts[name]
            ):
                raise EvidenceError(
                    f"versioned materialized source identity mismatch: {name}"
                )
    unsat_record = selected_decoder.model.unsat_record(profile, run_id)
    unsat_tag = unsat_record[len(selected_decoder.model.UNSAT_FAMILY) :]
    expected_config_lines = [
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={selected_decoder.model.PROFILE_NUMBERS[profile]}",
        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{item["run_id"]}"',
        f'CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{unsat_tag.hex()}"',
    ]
    source_intent = _binary_identity(
        source_contract["intent"], "E1A candidate intent"
    )
    source_base_files = _exact(
        source_contract["base_files"],
        set(E1_LATEST_STAGE_BASE_FILES),
        "E1A candidate base files",
    )
    source_patched_files = _exact(
        source_contract["patched_files"],
        set(E1_LATEST_STAGE_BASE_FILES),
        "E1A candidate patched files",
    )
    source_patch = _exact(
        source_contract["patch"],
        {
            "size",
            "sha256",
            "targets",
            "base_files",
            "patched_files",
            "config_lines",
            "clean_apply",
            "verified",
        },
        "E1A candidate patch",
    )
    _binary_identity(
        {name: source_patch[name] for name in ("size", "sha256")},
        "E1A candidate patch",
    )
    source_reachable = _exact(
        source_contract["reachable_record_contract"],
        {
            "reachable_slot_variants",
            "profiles",
            "checked_run_ids",
            "adjacent_slot_combinations_verified",
            "zero_crc_count",
            "family_collision_count",
            "decoder_policy_id",
            "verified",
        },
        "E1A reachable-record contract",
    )
    source_contract_safety = _exact(
        source_contract["safety"],
        {
            "host_only",
            "device_contact",
            "device_write",
            "odin_invoked",
            "live_authorized",
        },
        "E1A candidate contract safety",
    )
    expected_contract_schema = (
        _selected_contract(
            source_contract_id, profile
        ).contract_schema
        if source_contract_id is not None
        else E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA
    )
    expected_contract_verdict = (
        _selected_contract(
            source_contract_id, profile
        ).contract_verdict
        if source_contract_id is not None
        else E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT
    )
    if (
        source_contract.get("schema") != expected_contract_schema
        or source_contract.get("target") != PID1_USERSPACE_TARGET
        or source_contract.get("verdict") != expected_contract_verdict
        or source_contract.get("profile") != item["profile"]
        or type(source_contract.get("profile_number")) is not int
        or source_contract.get("profile_number")
        != selected_decoder.model.PROFILE_NUMBERS[profile]
        or source_contract.get("run_id") != item["run_id"]
        or source_contract.get("unsat_record_hex") != unsat_record.hex()
        or source_contract.get("unsat_tag_hex") != unsat_tag.hex()
        or source_contract.get("decoder_id") != selected_decoder.DECODER_ID
        or source_contract.get("decoder_policy_id")
        != selected_decoder.POLICY_ID
        or source_base_files != E1_LATEST_STAGE_BASE_FILES
        or any(
            not isinstance(value, str) or HASH_RE.fullmatch(value) is None
            for value in source_patched_files.values()
        )
        or source_patch["targets"] != sorted(E1_LATEST_STAGE_BASE_FILES)
        or source_patch["base_files"] != source_base_files
        or source_patch["patched_files"] != source_patched_files
        or source_patch["config_lines"] != expected_config_lines
        or source_patch["clean_apply"] is not True
        or source_patch["verified"] is not True
        or source_contract["config_lines"] != expected_config_lines
        or any(
            type(source_reachable[name]) is not int
            for name in (
                "reachable_slot_variants",
                "zero_crc_count",
                "family_collision_count",
            )
        )
        or source_reachable
        != {
            "reachable_slot_variants": _e1_reachable_slot_variant_count(
                profile, source_contract_id
            ),
            "profiles": [profile],
            "checked_run_ids": {profile: item["run_id"]},
            "adjacent_slot_combinations_verified": True,
            "zero_crc_count": 0,
            "family_collision_count": 0,
            "decoder_policy_id": selected_decoder.POLICY_ID,
            "verified": True,
        }
        or any(type(value) is not bool for value in source_contract_safety.values())
        or source_contract_safety
        != {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        }
        or source_contract.get("verified") is not True
    ):
        raise EvidenceError(
            "candidate static source contract is not E1A-bound, E1B-bound, or E2-bound"
        )
    source_build = _exact(
        candidate_static_result.get("build_repro"),
        {
            "result",
            "image",
            "fresh_reverification",
            "two_clean_builds_byte_identical",
            "linked_audit_verified",
        },
        "E1A candidate static build closure",
    )
    if (
        not isinstance(source_build, dict)
        or source_build.get("fresh_reverification") is not True
        or source_build.get("two_clean_builds_byte_identical") is not True
        or source_build.get("linked_audit_verified") is not True
    ):
        raise EvidenceError("candidate static build closure is incomplete")
    source_result_identity = _binary_identity(
        source_build.get("result"), "E1A build reproducibility result"
    )
    source_image_identity = _binary_identity(
        source_build.get("image"), "E1A kernel Image"
    )
    candidate_keys = {
        "artifacts",
        "candidate_b_artifacts",
        "base_boot",
        "ap",
        "fixed_interval",
        "userspace",
        "independent_reconstruction",
        "independent_lz4_roundtrip",
        "independent_magiskboot_unpack",
        "writer_exclusion_verified",
        "two_package_builds_byte_identical",
        "manifest_absent",
        "boot_only_ap",
        "verified",
    }
    if profile in {"E1B", "E2"}:
        candidate_keys.update(
            {"module_closure", "effective_rootfs", "stock_vendor_boot"}
        )
    source_candidate = _exact(
        candidate_static_result.get("candidate"),
        candidate_keys,
        "E1A candidate static artifact closure",
    )
    source_artifacts = _exact(
        source_candidate["artifacts"],
        {"artifact_result", "boot_img", "boot_img_lz4", "ap_tar_md5"},
        "E1A source artifacts",
    )
    source_b_artifacts = _exact(
        source_candidate["candidate_b_artifacts"],
        set(source_artifacts),
        "E1A source candidate-B artifacts",
    )
    normalized_source_artifacts = {
        name: _binary_identity(value, f"E1A source {name}")
        for name, value in source_artifacts.items()
    }
    normalized_source_b_artifacts = {
        name: _binary_identity(value, f"E1A source candidate-B {name}")
        for name, value in source_b_artifacts.items()
    }
    source_userspace = _exact(
        source_candidate["userspace"],
        {"result", "init", "child", "two_build_byte_identical", "verified"},
        "E1A source userspace",
    )
    normalized_source_userspace = {
        name: _binary_identity(source_userspace[name], f"E1A userspace {name}")
        for name in ("result", "init", "child")
    }
    source_base_boot = _binary_identity(
        source_candidate["base_boot"], "E1A source base boot"
    )
    source_ap = _exact(
        source_candidate["ap"], {"tar_md5", "member"}, "E1A source AP"
    )
    source_member = _exact(
        source_ap["member"],
        {"name", "size", "mode", "uid", "gid", "mtime", "uname", "gname"},
        "E1A source AP member",
    )
    source_fixed_interval = _exact(
        source_candidate["fixed_interval"],
        {
            "kernel_start",
            "kernel_end_exclusive",
            "header_preserved",
            "ramdisk_preserved",
            "outside_interval_changed_byte_count",
            "verified",
        },
        "E1A source fixed interval",
    )
    if profile == "E1B":
        validate_e1b_stock_closure(
            module_closure=source_candidate.get("module_closure"),
            effective_rootfs=source_candidate.get("effective_rootfs"),
            stock_vendor_boot=source_candidate.get("stock_vendor_boot"),
            expected_init=normalized_source_userspace["init"],
            expected_child=normalized_source_userspace["child"],
        )
    elif profile == "E2":
        closure_api = e2_closure_selector.select(source_contract_id)
        try:
            closure = closure_api.validate_module_closure(
                source_candidate.get("module_closure")
            )
            closure_api.validate_effective_rootfs(
                source_candidate.get("effective_rootfs"),
                expected_init=normalized_source_userspace["init"],
                expected_child=normalized_source_userspace["child"],
                module_closure=closure,
            )
        except e2_closure.ClosureError as exc:
            raise EvidenceError("E2 stock rootfs closure is invalid") from exc
        if (
            _binary_identity(
                source_candidate.get("stock_vendor_boot"),
                "E2 stock vendor_boot",
            )
            != E1B_STOCK_VENDOR_BOOT
        ):
            raise EvidenceError("E2 stock vendor_boot identity mismatch")
    source_tools = _exact(
        candidate_static_result["tools"],
        {"lz4", "magiskboot", "qemu_aarch64"},
        "E1A candidate static tools",
    )
    for name, value in source_tools.items():
        _binary_identity(value, f"E1A source tool {name}")
    expected_limits = [
        "host-only artifact qualification grants no D0, D1, F1, or live authority",
        "candidate execution and retained observation remain unproved",
    ]
    if (
        normalized_source_b_artifacts != normalized_source_artifacts
        or not _artifact_matches(source_artifacts["ap_tar_md5"], candidate_ap)
        or (
            profile == "E2"
            and candidate_ap.get("member")
            != {
                "name": "boot.img.lz4",
                **normalized_source_artifacts["boot_img_lz4"],
            }
        )
        or source_member
        != {
            "name": "boot.img.lz4",
            "size": normalized_source_artifacts["boot_img_lz4"]["size"],
            "mode": 0o644,
            "uid": 0,
            "gid": 0,
            "mtime": 0,
            "uname": "",
            "gname": "",
        }
        or not isinstance(source_ap["tar_md5"], str)
        or HEX32_RE.fullmatch(source_ap["tar_md5"]) is None
        or source_fixed_interval
        != {
            "kernel_start": E1_LATEST_STAGE_KERNEL_INTERVAL[0],
            "kernel_end_exclusive": E1_LATEST_STAGE_KERNEL_INTERVAL[1],
            "header_preserved": True,
            "ramdisk_preserved": True,
            "outside_interval_changed_byte_count": 0,
            "verified": True,
        }
        or source_userspace.get("two_build_byte_identical") is not True
        or source_userspace.get("verified") is not True
        or source_candidate.get("boot_only_ap") is not True
        or source_candidate.get("independent_reconstruction") is not True
        or source_candidate.get("independent_lz4_roundtrip") is not True
        or source_candidate.get("independent_magiskboot_unpack") is not True
        or source_candidate.get("writer_exclusion_verified") is not True
        or source_candidate.get("two_package_builds_byte_identical") is not True
        or source_candidate.get("manifest_absent") is not True
        or source_candidate.get("verified") is not True
        or candidate_static_result.get("limits") != expected_limits
    ):
        raise EvidenceError("candidate static artifact closure is not accepted")
    source_safety = candidate_static_result.get("safety")
    expected_source_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "manifest_created": False,
        "live_authorized": False,
    }
    if source_safety != expected_source_safety:
        raise EvidenceError("candidate static safety contract changed")

    static_result_keys = {
        "schema",
        "target",
        "verdict",
        "profile",
        "run_id",
        "decoder",
        "policy_id",
        "run_binding",
        "candidate",
        "safety",
    }
    if source_contract_id is not None:
        static_result_keys.add("source_contract_id")
    if (
        set(static_result) != static_result_keys
        or static_result.get("schema") != E1_LATEST_STAGE_STATIC_SCHEMA
        or static_result.get("target") != PID1_USERSPACE_TARGET
        or static_result.get("verdict") != E1_LATEST_STAGE_STATIC_VERDICT
        or static_result.get("profile") != item["profile"]
        or static_result.get("source_contract_id") != source_contract_id
        or static_result.get("run_id") != item["run_id"]
        or static_result.get("decoder") != selected_decoder.DECODER_ID
        or static_result.get("policy_id") != selected_decoder.POLICY_ID
        or static_result.get("run_binding")
        != {
            "canonical_manifest_size": len(canonical),
            "canonical_manifest_sha256": canonical_sha256,
            "verified": True,
        }
    ):
        raise EvidenceError("static checker header does not bind the E1A candidate")
    candidate_result = _exact(
        static_result["candidate"],
        {
            "artifacts",
            "boot_only_ap",
            "two_clean_builds_byte_identical",
            "two_package_builds_byte_identical",
            "linked_audit_verified",
            "independent_reconstruction",
            "writer_exclusion_verified",
            "verified",
        },
        "E1A candidate result",
    )
    artifacts = _exact(
        candidate_result["artifacts"],
        {
            "ap",
            "candidate_static",
            "image",
            "boot_image",
            "boot_img_lz4",
            "init",
            "child",
        },
        "E1A candidate artifacts",
    )
    for name, value in artifacts.items():
        artifacts[name] = _binary_identity(value, f"E1A {name}")
    expected_artifacts = {
        "ap": normalized_source_artifacts["ap_tar_md5"],
        "candidate_static": candidate_static,
        "image": source_image_identity,
        "boot_image": normalized_source_artifacts["boot_img"],
        "boot_img_lz4": normalized_source_artifacts["boot_img_lz4"],
        "init": normalized_source_userspace["init"],
        "child": normalized_source_userspace["child"],
    }
    safety = _exact(
        static_result["safety"],
        {
            "host_only",
            "device_contact",
            "device_write",
            "odin_invoked",
            "odin_transfer",
            "flash",
            "partition_write",
            "live_authorized",
        },
        "E1A static safety",
    )
    if (
        artifacts != expected_artifacts
        or source_result_identity["size"] <= 0
        or source_base_boot["size"] <= 0
        or candidate_result["boot_only_ap"] is not True
        or candidate_result["two_clean_builds_byte_identical"] is not True
        or candidate_result["two_package_builds_byte_identical"] is not True
        or candidate_result["linked_audit_verified"] is not True
        or candidate_result["independent_reconstruction"] is not True
        or candidate_result["writer_exclusion_verified"] is not True
        or candidate_result["verified"] is not True
        or safety["host_only"] is not True
        or any(value is not False for name, value in safety.items() if name != "host_only")
    ):
        raise EvidenceError("static checker result does not bind the E1A candidate")
    result = {
        "schema": "device_action_f1_e1_latest_stage_offline_contract_v1",
        "decoder": item["decoder"],
        "policy_id": item["policy_id"],
        "profile": item["profile"],
        "run_id": item["run_id"],
        "terminal_stage": item["terminal_stage"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "candidate_static_sha256": candidate_static["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_source_receipts": candidate_source_receipts,
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "verified": True,
    }
    if source_contract_id is not None:
        result["source_contract_id"] = source_contract_id
    if profile == "E2":
        result["ap_payload_closure"] = {
            "boot_img_lz4": normalized_source_artifacts["boot_img_lz4"],
            "boot_image": normalized_source_artifacts["boot_img"],
            "image": source_image_identity,
            "init": normalized_source_userspace["init"],
            "child": normalized_source_userspace["child"],
            "run_id": item["run_id"],
            "module_closure": source_candidate["module_closure"],
            "effective_rootfs": source_candidate["effective_rootfs"],
        }
        if source_contract_id is not None:
            result["ap_payload_closure"][
                "source_contract_id"
            ] = source_contract_id
    return result


def verify_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    if acceptance.get("kind") == E1_LATEST_STAGE_KIND:
        return _verify_e1_latest_stage_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    if acceptance.get("kind") in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        return _verify_same_ring_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    if acceptance.get("kind") == PID1_USERSPACE_KIND:
        return _verify_pid1_userspace_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    return _verify_checkpoint_offline_contract(
        acceptance,
        payloads=payloads,
        receipts=receipts,
        candidate_ap=candidate_ap,
    )


def _base_classification(
    *,
    classification: str,
    exact_count: int,
    family_count: int,
    integrity_issue: bool,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "exact_count": exact_count,
        "exact_record_count": exact_count,
        "family_count": family_count,
        "foreign_count": max(0, family_count - exact_count),
        "foreign_records_hex": [],
        "unterminated_offsets": [],
        "delimiter_mismatch_count": 0,
        "partial_at_head": False,
        "partial_at_tail": False,
        "historical_family_count": 0,
        "integrity_issue": integrity_issue,
        "baseline_absent": family_count == 0 and exact_count == 0,
        "acceptance_present": False,
        "accepted": False,
        "checkpoint": None,
    }


def classify_checkpoint(payload: bytes, acceptance: dict[str, Any]) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("checkpoint classifier received another evidence kind")
    marker = checkpoint.ENTRY_PROOF
    family = checkpoint.ENTRY_FAMILY
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    prefix_counts = [payload.count(prefix) for prefix in checkpoint.ENTRY_PREFIXES]
    partial_head = any(
        payload.startswith(marker[-length:])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if not any(prefix_counts) and exact_count == 0 and not partial_head and not partial_tail:
        return _base_classification(
            classification="CHECKPOINT_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    if (
        exact_count != item["exact_count"]
        or family_count != item["exact_count"]
        or any(count != item["exact_count"] for count in prefix_counts)
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="CHECKPOINT_FAMILY_INTEGRITY_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
        return result

    position = payload.index(marker)
    region = payload[position : position + checkpoint.REGION_SIZE]
    try:
        decoded = checkpoint.decode_region(
            region,
            item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except checkpoint.CheckError as exc:
        result = _base_classification(
            classification="CHECKPOINT_DECODE_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["checkpoint"] = {"error": str(exc), "observer_offset": position}
        return result

    active = decoded["active"]
    outcome_name = OUTCOME_NAMES.get(active["outcome"], "unknown")
    two_slots = len(decoded["valid_slots"]) == 2
    accepted = (
        decoded["terminal"] is True
        and active["stage"] == item["terminal_stage"]
        and outcome_name == item["terminal_outcome"]
        and (two_slots or item["require_two_valid_slots"] is not True)
    )
    if accepted:
        classification = "CHECKPOINT_TERMINAL_SUCCESS"
    elif decoded["terminal"] and outcome_name == "failure":
        classification = "CHECKPOINT_TERMINAL_FAILURE"
    elif decoded["terminal"]:
        classification = "CHECKPOINT_TERMINAL_MISMATCH"
    else:
        classification = "CHECKPOINT_PROGRESS_ONLY"
    result = _base_classification(
        classification=classification,
        exact_count=exact_count,
        family_count=family_count,
        integrity_issue=False,
    )
    result["acceptance_present"] = accepted
    result["accepted"] = accepted
    result["checkpoint"] = {
        **decoded,
        "observer_offset": position,
        "outcome_name": outcome_name,
        "two_valid_slots": two_slots,
        "boot_identity_self_consistent": two_slots,
    }
    return result


def classify_pid1_userspace(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("PID1 userspace classifier received another evidence kind")
    entry_count = payload.count(PID1_USERSPACE_ENTRY)
    userspace_count = payload.count(PID1_USERSPACE_PROOF)
    family_count = payload.count(PID1_USERSPACE_FAMILY)
    markers = (PID1_USERSPACE_ENTRY, PID1_USERSPACE_PROOF)
    partial_head = any(
        payload.startswith(marker[-length:])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if family_count == 0 and not partial_head and not partial_tail:
        result = _base_classification(
            classification="PID1_USERSPACE_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    elif (
        family_count != 1
        or entry_count + userspace_count != 1
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="PID1_USERSPACE_FAMILY_INTEGRITY_FAILURE",
            exact_count=userspace_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
    elif userspace_count == 1:
        result = _base_classification(
            classification="PID1_USERSPACE_CALLBACK_REACHED",
            exact_count=1,
            family_count=1,
            integrity_issue=False,
        )
        result["acceptance_present"] = True
        result["accepted"] = True
    else:
        result = _base_classification(
            classification="PID1_ENTRY_ONLY",
            exact_count=0,
            family_count=1,
            integrity_issue=False,
        )
    result["entry_count"] = entry_count
    result["userspace_count"] = userspace_count
    result["probe_id"] = item["probe_id"]
    return result


def classify_same_ring(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_KIND:
        raise EvidenceError("same-ring classifier received another evidence kind")
    try:
        decoded = same_ring.classify_observation(payload)
    except same_ring.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    exact_record_count = (
        decoded["entry_count"]
        + decoded["userspace_count"]
        + decoded["unsat_count"]
    )
    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = max(0, family_count - exact_record_count)
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["contract_id"] = item["contract_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_same_ring_multiboot(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_MULTIBOOT_KIND:
        raise EvidenceError("same-ring multiboot classifier received another kind")
    try:
        decoded = same_ring_multiboot.classify_observation(payload)
    except same_ring_multiboot.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = decoded["exact_record_count"]
    result["foreign_count"] = max(0, family_count - decoded["exact_record_count"])
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["contract_id"] = item["contract_id"]
    result["policy_id"] = item["policy_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_e1_latest_stage(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != E1_LATEST_STAGE_KIND:
        raise EvidenceError("E1 latest-stage classifier received another kind")
    selected_decoder = _latest_stage_decoder(
        item.get("source_contract_id"), item["profile"]
    )
    try:
        decoded = selected_decoder.classify_observation(
            payload,
            expected_profile=item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except selected_decoder.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    model = selected_decoder.model
    long_family_count = payload.count(model.LONG_FAMILY)
    unsat_family_count = payload.count(model.UNSAT_FAMILY)
    family_count = long_family_count + unsat_family_count
    exact_record_count = decoded["long_record_count"] + decoded["unsat_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["success_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = max(0, family_count - exact_record_count)
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["long_record_count"] = decoded["long_record_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["entry_count"] = decoded["entry_count"]
    result["progress_count"] = decoded["progress_count"]
    result["failure_count"] = decoded["failure_count"]
    result["success_count"] = decoded["success_count"]
    result["fallback_record_count"] = decoded["fallback_record_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["records"] = decoded["records"]
    result["integrity_issues"] = decoded["integrity_issues"]
    result["policy_id"] = item["policy_id"]
    result["profile"] = item["profile"]
    result["run_id"] = item["run_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_clean_baseline(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] == E1_LATEST_STAGE_KIND:
        selected_decoder = _latest_stage_decoder(
            item.get("source_contract_id"), item["profile"]
        )
        baseline = selected_decoder.classify_clean_baseline(
            payload,
            expected_profile=item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
        return {
            "classification": baseline["classification"],
            "exact_record_count": 0,
            "family_count": 0 if baseline["baseline_clean"] else 1,
            "integrity_issue": baseline["integrity_issue"],
            "baseline_clean": baseline["baseline_clean"],
        }
    if item["kind"] in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        result = (
            classify_same_ring_multiboot(payload, item)
            if item["kind"] == SAME_RING_MULTIBOOT_KIND
            else classify_same_ring(payload, item)
        )
        exact_count = result["exact_record_count"]
        family_count = result["family_count"]
        clean = (
            result["classification"] == "ZERO_AMBIGUOUS"
            and result["integrity_issue"] is False
            and exact_count == 0
            and family_count == 0
        )
        return {
            "classification": result["classification"],
            "exact_record_count": exact_count,
            "family_count": family_count,
            "integrity_issue": result["integrity_issue"],
            "baseline_clean": clean,
        }

    marker = item["marker"].encode("ascii")
    family = item["family"].encode("ascii")
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    return {
        "classification": (
            "BASELINE_CLEAN"
            if exact_count == 0 and family_count == 0
            else "BASELINE_FAMILY_PRESENT"
        ),
        "exact_record_count": exact_count,
        "family_count": family_count,
        "integrity_issue": False,
        "baseline_clean": exact_count == 0 and family_count == 0,
    }
