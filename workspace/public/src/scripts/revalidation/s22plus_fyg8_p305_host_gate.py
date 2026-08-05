#!/usr/bin/env python3
"""Compile and audit the P3.05 generic folded-tail runtime host-only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import s22plus_fyg8_p304_candidate_contract as candidate_contract
import s22plus_fyg8_p304_userspace_build as parent_build
import s22plus_fyg8_p305_generator as generator


SCHEMA = "s22plus_fyg8_p305_folded_tail_host_gate_v1"
VERDICT = "PASS_P305_GENERIC_FOLDED_TAIL_HOST_ONLY"


class GateError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, object]:
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def run() -> dict[str, object]:
    root = candidate_contract.intent.repo_root()
    exact = candidate_contract.verify(
        root,
        candidate_contract.intent.resolve(root, candidate_contract.DEFAULT_SOURCE),
        candidate_contract.intent.resolve(root, candidate_contract.DEFAULT_INTENT),
        candidate_contract.intent.resolve(root, candidate_contract.DEFAULT_PATCH),
    )
    tools = parent_build.base.require_tools()
    builds: list[dict[str, bytes]] = []
    metadata: list[dict[str, object]] = []
    generated_receipts: dict[str, object] | None = None
    for label in ("a", "b"):
        with tempfile.TemporaryDirectory(prefix=f"s22-p305-{label}-") as name:
            directory = Path(name)
            intent_directory = directory / "intent"
            generated = generator.materialize(
                root,
                intent_directory,
                run_id=bytes.fromhex(exact["run_id"]),
                unsat_tag=bytes.fromhex(exact["unsat_tag_hex"]),
                profile=exact["profile"],
            )
            materialized = intent_directory / "materialized-sources"
            build_directory = directory / "build"
            build_directory.mkdir(mode=0o700)
            compiled = parent_build._compile(  # noqa: SLF001
                root, build_directory, exact, materialized, tools
            )
            current = {
                "init": (build_directory / "init").read_bytes(),
                "child": (build_directory / "s22-e1-child").read_bytes(),
            }
            if generated_receipts is None:
                generated_receipts = generated
            elif generated_receipts != generated:
                raise GateError("P3.05 generated source receipts differ")
            builds.append(current)
            metadata.append(compiled)
    if builds[0] != builds[1] or metadata[0] != metadata[1]:
        raise GateError("P3.05 two-build reproducibility differs")
    init = builds[0]["init"]
    child = builds[0]["child"]
    if (
        init.count(b"usb_notifier_qcom.ko") != 1
        or init.count(b"ucsi_glink.ko") != 1
        or init.count(b"/proc/s22_checkpoint") != 1
        or b"/dev/block" in init
        or b"/dev/mem" in init
    ):
        raise GateError("P3.05 binary closure differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": "Samsung Galaxy S22+ FYG8",
        "parent_run_id": exact["run_id"],
        "generated": generated_receipts,
        "outputs": {
            "init": _receipt(init),
            "child": _receipt(child),
        },
        "compile_metadata": metadata[0],
        "module_plan_count": 61,
        "folded_tail": {
            "first_index": 59,
            "last_index": 60,
            "notifier_failure_detail": "0x73b",
            "ucsi_failure_detail": "0x73c",
            "success_checkpoint": {"stage": "0x7b", "item_index": 59},
            "first_bind_gate": {"stage": "0x7c", "item_index": 0},
            "generic_max_module_count": 256,
        },
        "two_build_byte_identical": True,
        "host_only": True,
        "device_contact": False,
        "verified": True,
    }


def main() -> int:
    try:
        result = run()
    except (
        GateError,
        candidate_contract.ContractError,
        generator.GeneratorError,
        parent_build.BuildError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
