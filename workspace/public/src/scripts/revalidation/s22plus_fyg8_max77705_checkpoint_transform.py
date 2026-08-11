#!/usr/bin/env python3
"""Add the narrow Carrier-v3 publisher needed by the Max77705 observer.

The fixed kernel already accepts the 100-byte request-v3 ABI.  The inherited
PID1 checkpoint client only constructs request-v2 records, however.  This
transform adds two position-bound payload publishers without changing the
existing request-v2 path or broadening its semantics.
"""

from __future__ import annotations

from typing import Mapping


SCHEMA = "s22plus_fyg8_max77705_checkpoint_transform_v1"


class TransformError(ValueError):
    pass


_VERSION_ANCHOR = b"#define S22_P233_REQUEST_VERSION 2U\n"
_VERSION_REPLACEMENT = _VERSION_ANCHOR + b"""#define S22_MAX77705_REQUEST_VERSION 3U
#define S22_MAX77705_PAYLOAD_RAW_EXCERPT 1U
#define S22_MAX77705_PAYLOAD_SIZE 64U
#define S22_MAX77705_FIRST_POSITION 105U
#define S22_MAX77705_TERMINAL_POSITION 106U
#define S22_MAX77705_FIRST_DETAIL 0xda3U
#define S22_MAX77705_TERMINAL_DETAIL_FIRST 0x6701U
#define S22_MAX77705_TERMINAL_DETAIL_LAST 0x6709U
#define S22_MAX77705_MUX_DETAIL_FIRST 0x6710U
#define S22_MAX77705_MUX_DETAIL_LAST 0x6714U
"""

_STRUCT_ANCHOR = b"""_Static_assert(
    offsetof(struct s22_p233_checkpoint_request, crc32) == 28U,
    "CRC offset");
"""
_STRUCT_REPLACEMENT = _STRUCT_ANCHOR + b"""

struct s22_max77705_checkpoint_request_v3 {
    uint8_t magic[4];
    uint8_t version;
    uint8_t profile;
    uint8_t stage;
    uint8_t outcome;
    uint16_t detail;
    uint8_t item_index;
    uint8_t payload_kind;
    uint8_t payload_len;
    uint8_t reserved[3];
    uint8_t run_id[16];
    uint8_t payload[S22_MAX77705_PAYLOAD_SIZE];
    uint32_t crc32;
} __attribute__((packed));

_Static_assert(
    sizeof(struct s22_max77705_checkpoint_request_v3) == 100U,
    "Max77705 request-v3 size");
_Static_assert(
    offsetof(struct s22_max77705_checkpoint_request_v3, run_id) == 16U,
    "Max77705 request-v3 run ID offset");
_Static_assert(
    offsetof(struct s22_max77705_checkpoint_request_v3, payload) == 32U,
    "Max77705 request-v3 payload offset");
_Static_assert(
    offsetof(struct s22_max77705_checkpoint_request_v3, crc32) == 96U,
    "Max77705 request-v3 CRC offset");
"""

_PUBLISH_ANCHOR = b"""int s22_r4w1e_checkpoint_client_init(
    struct s22_r4w1e_checkpoint_client *client,
    const uint8_t run_id[16]) {
"""
_PUBLISH_HELPERS = b"""static int s22_max77705_detail_allowed(
    uint8_t position_ordinal, uint8_t outcome, uint16_t detail) {
    if (position_ordinal == S22_MAX77705_FIRST_POSITION) {
        return outcome == S22_P233_OUTCOME_PROGRESS
            && detail == S22_MAX77705_FIRST_DETAIL;
    }
    if (position_ordinal != S22_MAX77705_TERMINAL_POSITION
        || outcome != S22_P233_OUTCOME_FAILURE) {
        return 0;
    }
    return (detail >= S22_MAX77705_TERMINAL_DETAIL_FIRST
            && detail <= S22_MAX77705_TERMINAL_DETAIL_LAST)
        || (detail >= S22_MAX77705_MUX_DETAIL_FIRST
            && detail <= S22_MAX77705_MUX_DETAIL_LAST);
}

static long s22_max77705_publish_payload_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint8_t outcome,
    uint16_t detail,
    const uint8_t payload[S22_MAX77705_PAYLOAD_SIZE]) {
    struct s22_max77705_checkpoint_request_v3 request = {0};
    if (client == NULL || !client->initialized || client->terminal) {
        return -EALREADY;
    }
    if (payload == NULL) {
        return -EINVAL;
    }
    size_t count =
        sizeof(k_p248_e2_steps) / sizeof(k_p248_e2_steps[0]);
    size_t ordinal = client->generation;
    if (ordinal >= count || position_ordinal != ordinal
        || !s22_max77705_detail_allowed(position_ordinal, outcome, detail)
        || !p288_detail_allowed(ordinal, outcome, detail)) {
        return -EINVAL;
    }
    const struct s22_p248_step *step = &k_p248_e2_steps[ordinal];

    request.magic[0] = 'S';
    request.magic[1] = '2';
    request.magic[2] = '2';
    request.magic[3] = 'Q';
    request.version = S22_MAX77705_REQUEST_VERSION;
    request.profile = S22PLUS_FYG8_P233_PROFILE;
    request.stage = step->stage;
    request.outcome = outcome;
    request.detail = detail;
    request.item_index = step->item_index;
    request.payload_kind = S22_MAX77705_PAYLOAD_RAW_EXCERPT;
    request.payload_len = S22_MAX77705_PAYLOAD_SIZE;
    copy_bytes(request.run_id, client->run_id, sizeof(request.run_id));
    copy_bytes(request.payload, payload, sizeof(request.payload));
    request.crc32 = checkpoint_crc32(
        &request,
        offsetof(struct s22_max77705_checkpoint_request_v3, crc32));

    long fd = sys_openat("/proc/s22_checkpoint", O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return p292_remember_publication_error(
            client, S22_P292_PUBLICATION_OPERATION_OPEN, fd);
    }
    long written = sys_write((int)fd, &request, sizeof(request));
    long closed = sys_close((int)fd);
    if (written != (long)sizeof(request)) {
        long error = written < 0 ? written : -EIO;
        return p292_remember_publication_error(
            client, S22_P292_PUBLICATION_OPERATION_WRITE, error);
    }
    if (closed != 0) {
        return p292_remember_publication_error(
            client, S22_P292_PUBLICATION_OPERATION_CLOSE, closed);
    }
    client->publication_error_operation =
        S22_P292_PUBLICATION_OPERATION_NONE;
    client->publication_error_errno = 0;
    client->stage = step->stage;
    client->item_index = step->item_index;
    client->generation = (uint8_t)(ordinal + 1U);
    client->terminal = outcome != S22_P233_OUTCOME_PROGRESS;
    return 0;
}

long s22_max77705_checkpoint_payload_progress_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail,
    const uint8_t payload[S22_MAX77705_PAYLOAD_SIZE]) {
    return s22_max77705_publish_payload_position(
        client, position_ordinal, S22_P233_OUTCOME_PROGRESS,
        detail, payload);
}

long s22_max77705_checkpoint_payload_terminal_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail,
    const uint8_t payload[S22_MAX77705_PAYLOAD_SIZE]) {
    return s22_max77705_publish_payload_position(
        client, position_ordinal, S22_P233_OUTCOME_FAILURE,
        detail, payload);
}

""" + _PUBLISH_ANCHOR

_HEADER_ANCHOR = b"""long s22_p294_checkpoint_terminal_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail);
"""
_HEADER_REPLACEMENT = _HEADER_ANCHOR + b"""long s22_max77705_checkpoint_payload_progress_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail,
    const uint8_t payload[64]);
long s22_max77705_checkpoint_payload_terminal_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail,
    const uint8_t payload[64]);
"""


def _replace_once(value: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if value.count(old) != 1:
        raise TransformError(f"Max77705 checkpoint {label} anchor differs")
    return value.replace(old, new, 1)


def transform_checkpoint(source: bytes) -> bytes:
    value = _replace_once(
        source, _VERSION_ANCHOR, _VERSION_REPLACEMENT, "version"
    )
    value = _replace_once(
        value, _STRUCT_ANCHOR, _STRUCT_REPLACEMENT, "request-v3 struct"
    )
    value = _replace_once(
        value, _PUBLISH_ANCHOR, _PUBLISH_HELPERS, "payload publisher"
    )
    return value


def transform_header(source: bytes) -> bytes:
    return _replace_once(
        source, _HEADER_ANCHOR, _HEADER_REPLACEMENT, "public prototypes"
    )


def transform_artifacts(artifacts: Mapping[str, bytes]) -> dict[str, bytes]:
    required = {"checkpoint_client", "p290_checkpoint_header"}
    if not required.issubset(artifacts):
        raise TransformError("Max77705 checkpoint artifacts are incomplete")
    result = dict(artifacts)
    result["checkpoint_client"] = transform_checkpoint(
        artifacts["checkpoint_client"]
    )
    result["p290_checkpoint_header"] = transform_header(
        artifacts["p290_checkpoint_header"]
    )
    return result


def validate_transformed(checkpoint: bytes, header: bytes) -> dict[str, object]:
    required = (
        b"struct s22_max77705_checkpoint_request_v3",
        b"sizeof(struct s22_max77705_checkpoint_request_v3) == 100U",
        b"S22_MAX77705_FIRST_DETAIL 0xda3U",
        b"S22_MAX77705_TERMINAL_DETAIL_FIRST 0x6701U",
        b"S22_MAX77705_TERMINAL_DETAIL_LAST 0x6709U",
        b"S22_MAX77705_MUX_DETAIL_FIRST 0x6710U",
        b"S22_MAX77705_MUX_DETAIL_LAST 0x6714U",
        b"s22_max77705_checkpoint_payload_progress_position",
        b"s22_max77705_checkpoint_payload_terminal_position",
    )
    if any(checkpoint.count(token) < 1 for token in required):
        raise TransformError("Max77705 checkpoint transformed closure is incomplete")
    for name in required[-2:]:
        if header.count(name) != 1:
            raise TransformError("Max77705 checkpoint header prototype differs")
    return {
        "schema": SCHEMA,
        "request_version": 3,
        "request_size": 100,
        "payload_bytes": 64,
        "existing_v2_publisher_unchanged": True,
        "fixed_image_changed": False,
        "verified": True,
    }
