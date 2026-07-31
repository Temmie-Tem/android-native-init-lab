#!/usr/bin/env python3
"""Host-only closure for the P2.94 DWC3 value-telemetry successor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p292_accept_to_resume as inherited
import s22plus_fyg8_p292_identity_tiers as baseline_identity
import s22plus_fyg8_p292_repair_spec as repair
import s22plus_fyg8_p294_telemetry_decoder as decoder
import s22plus_fyg8_p294_telemetry_generator as generator
import s22plus_fyg8_p294_telemetry_model as model
import s22plus_fyg8_p294_telemetry_spec as spec
import s22plus_fyg8_p294_telemetry_transform as transform


SCHEMA = "s22plus_fyg8_p294_telemetry_closure_v1"
VERDICT = "PASS_P294_DWC3_VALUE_TELEMETRY_CLOSURE_HOST_ONLY"


class ClosureError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _generated(root: Path) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=baseline_identity.SOURCE_CHECK_RUN_ID,
        unsat_tag=baseline_identity.SOURCE_CHECK_UNSAT_TAG,
        profile=repair.PROFILE,
    )


def _fnv_update(value: int, word: int) -> int:
    return ((value ^ word) * 1099511628211) & ((1 << 64) - 1)


def _expected_classifier_result() -> dict[str, Any]:
    value = 1469598103934665603
    details = set()
    count = 0
    for run_stop in range(2):
        for devctrlhlt in range(2):
            for coreidle in range(2):
                for prtcap in range(4):
                    for susphy in range(2):
                        for connect_speed in range(8):
                            for vbus_valid in range(2):
                                for state in range(len(spec.UDC_STATES)):
                                    for speed in range(len(spec.USB_SPEEDS)):
                                        result = spec.classify(
                                            spec.Snapshot(
                                                0,
                                                run_stop,
                                                devctrlhlt,
                                                coreidle,
                                                prtcap,
                                                susphy,
                                                connect_speed,
                                                vbus_valid,
                                                state,
                                                speed,
                                            )
                                        )
                                        word = result.detail | (
                                            result.outcome << 16
                                        )
                                        value = _fnv_update(value, word)
                                        details.add(result.detail)
                                        count += 1
    return {
        "case_count": count,
        "detail_count": len(details),
        "fnv64": f"{value:016x}",
    }


def _classifier_tu(runtime: bytes) -> bytes:
    struct_start = runtime.find(b"struct p294_capture_values {\n")
    struct_end_marker = b"static struct p294_capture_values g_p294_capture;\n"
    struct_end = runtime.find(struct_end_marker, struct_start)
    if struct_start < 0 or struct_end < 0:
        raise ClosureError("P2.94 capture state source is absent")
    struct_end += len(struct_end_marker)
    start, end = transform._function_span(  # noqa: SLF001
        runtime, b"p294_terminal_detail"
    )
    classifier = runtime[start:end]
    for token in (
        b"P294_FINAL_DETAIL_BASE 0xc70U",
        b"P294_MISMATCH_DETAIL_BASE 0xf40U",
        b"P294_STATE_SPEED_CONTRADICTION 0xf4fU",
        b"P294_CONNECT_SPEED_CONTRADICTION 0xf50U",
    ):
        if runtime.count(token) != 1:
            raise ClosureError(f"P2.94 classifier constant differs: {token!r}")
    return (
        b"#include <stdint.h>\n#include <stdio.h>\n"
        b"#define P260_EPROTO 71\n"
        b"#define P282_STATE_COUNT 9U\n"
        b"#define P282_SPEED_HIGH 3U\n"
        b"#define P294_FINAL_DETAIL_BASE 0xc70U\n"
        b"#define P294_MISMATCH_DETAIL_BASE 0xf40U\n"
        b"#define P294_STATE_SPEED_CONTRADICTION 0xf4fU\n"
        b"#define P294_CONNECT_SPEED_CONTRADICTION 0xf50U\n"
        + runtime[struct_start:struct_end]
        + classifier
        + b"""
static uint64_t update(uint64_t value, uint32_t word) {
    return (value ^ word) * UINT64_C(1099511628211);
}

int main(void) {
    uint64_t hash = UINT64_C(1469598103934665603);
    uint8_t seen[65536] = {0};
    unsigned int cases = 0;
    unsigned int details = 0;
    g_p294_capture.wrapper_seen = 1U;
    g_p294_capture.dwc3_seen = 1U;
    for (unsigned int run_stop = 0; run_stop < 2; ++run_stop)
    for (unsigned int devctrlhlt = 0; devctrlhlt < 2; ++devctrlhlt)
    for (unsigned int coreidle = 0; coreidle < 2; ++coreidle)
    for (unsigned int prtcap = 0; prtcap < 4; ++prtcap)
    for (unsigned int susphy = 0; susphy < 2; ++susphy)
    for (unsigned int connect_speed = 0; connect_speed < 8; ++connect_speed)
    for (unsigned int vbus_valid = 0; vbus_valid < 2; ++vbus_valid)
    for (unsigned int state = 0; state < 9; ++state)
    for (unsigned int speed = 0; speed < 7; ++speed) {
        g_p294_capture.run_stop = (uint8_t)run_stop;
        g_p294_capture.devctrlhlt = (uint8_t)devctrlhlt;
        g_p294_capture.coreidle = (uint8_t)coreidle;
        g_p294_capture.prtcap = (uint8_t)prtcap;
        g_p294_capture.susphy = (uint8_t)susphy;
        g_p294_capture.connect_speed = (uint8_t)connect_speed;
        g_p294_capture.vbus_valid = (uint8_t)vbus_valid;
        uint16_t detail = 0;
        long rc = p294_terminal_detail(state, speed, &detail);
        if (rc != 0) return 2;
        unsigned int outcome = detail >= 0xcc0U && detail <= 0xcc3U ? 1U : 2U;
        hash = update(hash, (uint32_t)detail | (outcome << 16));
        if (!seen[detail]) { seen[detail] = 1U; ++details; }
        ++cases;
    }
    printf("cases=%u details=%u fnv64=%016llx\\n",
        cases, details, (unsigned long long)hash);
    return 0;
}
"""
    )


def audit_runtime_classifier(runtime: bytes) -> dict[str, Any]:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise ClosureError("host C compiler is unavailable")
    expected = _expected_classifier_result()
    expected_line = (
        f"cases={expected['case_count']} details={expected['detail_count']} "
        f"fnv64={expected['fnv64']}\n"
    )
    with tempfile.TemporaryDirectory(prefix="s22-p294-classifier-") as tmp:
        directory = Path(tmp)
        source = directory / "classifier.c"
        output = directory / "classifier"
        source.write_bytes(_classifier_tu(runtime))
        compiled = subprocess.run(
            [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compiled.returncode != 0:
            raise ClosureError(
                "P2.94 classifier host compile failed: "
                + compiled.stderr.decode("utf-8", "replace")[-2000:]
            )
        executed = subprocess.run(
            [str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    actual = executed.stdout.decode("ascii", "replace")
    if executed.returncode != 0 or actual != expected_line:
        raise ClosureError(
            f"P2.94 classifier SoT differs: expected={expected_line!r}, "
            f"actual={actual!r}, rc={executed.returncode}"
        )
    return {
        **expected,
        "compiler": str(Path(compiler).resolve()),
        "runtime_matches_python_sot": True,
        "verified": True,
    }


def audit_pair_adjacency(runtime: bytes) -> dict[str, Any]:
    return inherited.audit_pair_publication_adjacency(
        runtime,
        helper_name="p294_publish_final_pair",
        first_publish_expression=(
            b"s22_p294_checkpoint_progress_position(\n"
            b"        &g_checkpoint, "
            b"S22_P294_POSITION_USBLNKST, first_detail)"
        ),
        terminal_publish_expression=(
            b"s22_p294_checkpoint_terminal_position(\n"
            b"        &g_checkpoint, "
            b"S22_P294_POSITION_FINAL_STATE, terminal_detail)"
        ),
    )


def run_closure(root: Path) -> dict[str, Any]:
    artifacts = _generated(root)
    adjacency = audit_pair_adjacency(
        artifacts["p290_e3_runtime_include"]
    )
    classifier = audit_runtime_classifier(
        artifacts["p290_e3_runtime_include"]
    )
    verifier_paths = (
        Path(__file__).resolve(),
        Path(__file__).with_name(
            "test_s22plus_fyg8_p294_telemetry.py"
        ),
    )
    api = tuple(
        inherited.audit_repository_module_attributes(
            path.read_bytes(),
            filename=str(path.relative_to(root)),
            repository_root=root,
        )
        for path in verifier_paths
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry_sot": spec.validate(),
        "generator": {
            "artifact_count": len(artifacts),
            "changed_artifact_keys": sorted(
                generator.TELEMETRY_ARTIFACT_KEYS
            ),
            "candidate_patch": _receipt(artifacts["candidate_patch"]),
            "verified": True,
        },
        "runtime_classifier": classifier,
        "pair_adjacency": adjacency,
        "repository_module_attribute_closure": {
            "files": api,
            "file_count": len(api),
            "all_references_resolve": True,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "payload_write": False,
            "live_authorized": False,
        },
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(run_closure(Path.cwd()), indent=2, sort_keys=True))
