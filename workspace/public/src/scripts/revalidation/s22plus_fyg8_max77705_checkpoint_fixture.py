#!/usr/bin/env python3
"""Execute the transformed Max77705 request-v3 publisher on the host."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_max77705_checkpoint_transform as transform
import s22plus_fyg8_max77705_telemetry as telemetry
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p315_generator as parent


SCHEMA = "s22plus_fyg8_max77705_checkpoint_fixture_v1"
VERDICT = "PASS_MAX77705_ACTUAL_C_PUBLISHER_V3_REQUESTS_AND_GATES_HOST_ONLY"


class FixtureError(ValueError):
    pass


def _definition(source: bytes, signature: bytes) -> bytes:
    start = source.index(signature)
    brace = source.index(b"{", start)
    depth = 0
    cursor = brace
    while cursor < len(source):
        byte = source[cursor]
        if byte == ord("{"):
            depth += 1
        elif byte == ord("}"):
            depth -= 1
            if depth == 0:
                end = source.index(b"\n", cursor) + 1
                return source[start:end]
        cursor += 1
    raise FixtureError(f"unterminated C definition: {signature!r}")


def _baseline(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = parent.frozen_identity(root)
    return parent.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def _host_source(checkpoint: bytes) -> bytes:
    syscall_start = checkpoint.index(b"static inline long syscall6(")
    syscall_end = checkpoint.index(b"static void copy_bytes(", syscall_start)
    stubs = br'''static uint8_t captured_request[100];
static size_t captured_count;
static unsigned int captured_writes;
static long sys_openat(const char *path, int flags) {
    (void)path; (void)flags; return 7;
}
static long sys_write(int fd, const void *buffer, size_t count) {
    const uint8_t *bytes = (const uint8_t *)buffer;
    if (fd != 7 || count > sizeof(captured_request)) return -EIO;
    for (size_t index = 0; index < count; ++index) {
        captured_request[index] = bytes[index];
    }
    captured_count = count;
    ++captured_writes;
    return (long)count;
}
static long sys_close(int fd) { return fd == 7 ? 0 : -EIO; }

'''
    source = checkpoint[:syscall_start] + stubs + checkpoint[syscall_end:]
    source = source.replace(
        b'#include "s22plus_r4w1e_checkpoint.h"\n',
        b'#include "s22plus_r4w1e_checkpoint.h"\n#include <stdio.h>\n',
        1,
    )
    details = sorted(
        {
            *telemetry.TERMINAL_DETAIL_BY_KEY.values(),
            *telemetry.MUX_DETAIL_BY_NAME.values(),
        }
    )
    detail_text = ",".join(f"0x{value:04x}U" for value in details).encode()
    main = br'''
static const uint16_t max77705_details[] = {''' + detail_text + br'''};
static int emit_bytes(void) {
    const uint8_t run_id[16] = {
        0x10U,0x11U,0x12U,0x13U,0x14U,0x15U,0x16U,0x17U,
        0x18U,0x19U,0x1aU,0x1bU,0x1cU,0x1dU,0x1eU,0x1fU,
    };
    uint8_t first_payload[64];
    uint8_t second_payload[64];
    struct s22_r4w1e_checkpoint_client client = {0};
    for (size_t index = 0; index < 64U; ++index) {
        first_payload[index] = (uint8_t)index;
        second_payload[index] = (uint8_t)(0xffU - index);
    }
    if (s22_r4w1e_checkpoint_client_init(&client, run_id) != 0) return 10;
    client.generation = S22_MAX77705_FIRST_POSITION;
    if (s22_max77705_checkpoint_payload_progress_position(
            &client, S22_MAX77705_FIRST_POSITION,
            S22_MAX77705_FIRST_DETAIL, first_payload) != 0
        || captured_count != 100U || captured_writes != 1U
        || fwrite(captured_request, 1U, captured_count, stdout) != captured_count) {
        return 11;
    }
    for (size_t index = 0;
         index < sizeof(max77705_details) / sizeof(max77705_details[0]);
         ++index) {
        client.generation = S22_MAX77705_TERMINAL_POSITION;
        client.terminal = 0U;
        if (s22_max77705_checkpoint_payload_terminal_position(
                &client, S22_MAX77705_TERMINAL_POSITION,
                max77705_details[index], second_payload) != 0
            || captured_count != 100U
            || !client.terminal
            || client.generation != 107U
            || fwrite(captured_request, 1U, captured_count, stdout)
                != captured_count) {
            return 12;
        }
    }
    const uint16_t rejected[] = {0x6700U,0x670aU,0x670fU,0x6715U,0x673fU};
    unsigned int before = captured_writes;
    for (size_t index = 0; index < sizeof(rejected) / sizeof(rejected[0]); ++index) {
        client.generation = S22_MAX77705_TERMINAL_POSITION;
        client.terminal = 0U;
        if (s22_max77705_checkpoint_payload_terminal_position(
                &client, S22_MAX77705_TERMINAL_POSITION,
                rejected[index], second_payload) != -EINVAL) return 13;
    }
    client.generation = S22_MAX77705_FIRST_POSITION;
    client.terminal = 0U;
    if (s22_max77705_checkpoint_payload_progress_position(
            &client, S22_MAX77705_FIRST_POSITION,
            S22_MAX77705_FIRST_DETAIL, NULL) != -EINVAL
        || captured_writes != before) return 14;
    return 0;
}
int main(void) { return emit_bytes(); }
'''
    return source + main


def _compile_and_run(checkpoint: bytes, header: bytes, positions: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="s22-max77705-publisher-") as temp:
        root = Path(temp)
        (root / "s22plus_r4w1e_checkpoint.h").write_bytes(header)
        (root / "s22plus_fyg8_p290_positions.h").write_bytes(positions)
        source = root / "publisher.c"
        binary = root / "publisher"
        source.write_bytes(_host_source(checkpoint))
        completed = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-DS22PLUS_FYG8_P233_PROFILE=3",
                str(source),
                "-o",
                str(binary),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise FixtureError(
                "Max77705 C publisher fixture compile failed: "
                + completed.stderr.decode("utf-8", "replace")
            )
        executed = subprocess.run(
            [str(binary)], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if executed.returncode != 0:
            raise FixtureError(
                f"Max77705 C publisher fixture returned {executed.returncode}: "
                + executed.stderr.decode("utf-8", "replace")
            )
        return executed.stdout


def _expected_requests() -> list[bytes]:
    run_id = bytes(range(0x10, 0x20))
    first_payload = bytes(range(64))
    second_payload = bytes(0xFF - index for index in range(64))
    result = [
        carrier.encode_request(
            "E2",
            0x92,
            outcome=carrier.OUTCOME_PROGRESS,
            item_index=1,
            detail=telemetry.A_DETAIL,
            run_id=run_id,
            payload_kind=carrier.PAYLOAD_RAW_EXCERPT,
            payload=first_payload,
            version=carrier.REQUEST_VERSION_V3,
        )
    ]
    for detail in sorted(
        {
            *telemetry.TERMINAL_DETAIL_BY_KEY.values(),
            *telemetry.MUX_DETAIL_BY_NAME.values(),
        }
    ):
        result.append(
            carrier.encode_request(
                "E2",
                0x93,
                outcome=carrier.OUTCOME_FAILURE,
                item_index=0,
                detail=detail,
                run_id=run_id,
                payload_kind=carrier.PAYLOAD_RAW_EXCERPT,
                payload=second_payload,
                version=carrier.REQUEST_VERSION_V3,
            )
        )
    return result


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    baseline = _baseline(root)
    transformed = transform.transform_artifacts(baseline)
    transform_result = transform.validate_transformed(
        transformed["checkpoint_client"], transformed["p290_checkpoint_header"]
    )
    before_v2 = _definition(
        baseline["checkpoint_client"], b"static long p288_publish_next("
    )
    after_v2 = _definition(
        transformed["checkpoint_client"], b"static long p288_publish_next("
    )
    if before_v2 != after_v2:
        raise FixtureError("inherited request-v2 publisher changed")
    actual = _compile_and_run(
        transformed["checkpoint_client"],
        transformed["p290_checkpoint_header"],
        transformed["p290_position_header"],
    )
    expected = b"".join(_expected_requests())
    if actual != expected:
        raise FixtureError("actual C request-v3 bytes differ from Carrier model")
    expected_count = 1 + len(telemetry.TERMINAL_DETAIL_BY_KEY) + len(
        telemetry.MUX_DETAIL_BY_NAME
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "transform": transform_result,
        "request_count": expected_count,
        "request_bytes": len(actual),
        "request_sha256": hashlib.sha256(actual).hexdigest(),
        "terminal_bucket_preimages": len(telemetry.TERMINAL_DETAIL_BY_KEY),
        "mux_class_preimages": len(telemetry.MUX_DETAIL_BY_NAME),
        "out_of_family_details_rejected": 5,
        "null_payload_rejected": True,
        "existing_v2_publisher_byte_identical": True,
        "actual_c_bytes_equal_carrier_model": True,
        "fixed_image_changed": False,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
