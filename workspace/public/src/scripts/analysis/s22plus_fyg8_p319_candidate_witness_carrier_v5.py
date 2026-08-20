#!/usr/bin/env python3
"""Materialize the P3.19 canonical witness Carrier / Envelope-v5 closure.

This is an H0-only successor of the independently reviewed P3.19 parser
predecessor.  It keeps the Envelope-v4 CRC and encoder byte-identical, adds a
distinct 128-byte Envelope-v5 domain, canonically encodes the structured
witness into the existing 76-byte payload, and publishes the same two 64-byte
Carrier positions.  It also materializes the two source-only producer changes
needed by that ABI: the already-read five-byte initial MAX77705 status and one
post-write register-0x23 readback.

The output is source materialization, not a candidate build.  It performs no
device, ADB, USB, Odin, transfer, recovery, or replay action and grants no live
authority.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import types
from typing import Any
import zlib


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
PREDECESSOR = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_candidate_witness_parser_v2.py"
)
PREDECESSOR_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-witness-parser-v2-20260820-14"
)
PREDECESSOR_RECEIPT = PREDECESSOR_ROOT / "result.json"
OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-witness-carrier-v5-20260820-13"
)

SCHEMA = "s22plus-fyg8-p319-candidate-witness-carrier-v5"
VERDICT = "PASS_P319_CANDIDATE_WITNESS_CARRIER_V5_IMPLEMENTED_H0"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}

PREDECESSOR_SIZE = 101_509
PREDECESSOR_SHA256 = "7078ef471ffb5a1291d40274201b1f71db93f0465348bb9f1135215d65e659e5"
PREDECESSOR_RECEIPT_SIZE = 15_478
PREDECESSOR_RECEIPT_SHA256 = "14ca869c411a5940ecffbc24cd2231bc1d10e0bc410ad379d6914809b0debaf0"

ENVELOPE_SIZE = 128
PAYLOAD_OFFSET = 48
PAYLOAD_SIZE = 76
CRC_OFFSET = 124
V5_VERSION = 5
V5_DOMAIN = b"S22PLUS-FYG8-MAX77705-DIAG-V5\0"
V5_ENCODING = 3
V5_WITNESS_FLAG = 1 << 5
MAX_RECORDS = 4_096
MAX_RECORD_BYTES = 1_048_576
MODULE_COUNT = 73

MASK_PROBE = 1 << 0
MASK_IRQ = 1 << 1
MASK_INITIAL = 1 << 2
MASK_CLASS1 = 1 << 3
MASK_CLASS2 = 1 << 4
MASK_DEFERRED = 1 << 5
MASK_PARENT = 1 << 6
MASK_ALL = 0x7F

VALID_FIRST_SEQUENCE = 1 << 0
VALID_LAST_SEQUENCE = 1 << 1
VALID_PARENT_MASK = 1 << 2
VALID_MODULE_69 = 1 << 3
VALID_MODULE_71 = 1 << 4
VALID_MODULE_72 = 1 << 5
VALID_INITIAL_STATUS = 1 << 6
VALID_CLASSIFICATION = 1 << 7

TARGET_MODULES = (
    (69, "i2c-msm-geni.ko"),
    (71, "mfd_max77705.ko"),
    (72, "pdic_max77705.ko"),
)


class AuditError(RuntimeError):
    """An exact source, transform, ABI, or durable receipt differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_CARRIER_V5_BOUND_SOURCE")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
        value.st_ctime_ns,
    )


def stable_bytes(
    path: Path,
    *,
    label: str,
    maximum: int,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    required_mode: int | None = None,
    required_nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        direct != resolved or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode) or before.st_nlink < 1
        or len(payload) != before.st_size or len(payload) > maximum
        or _stat_identity(before) != _stat_identity(inside)
        or _stat_identity(before) != _stat_identity(after)
    ):
        raise AuditError(f"{label} is not one stable direct regular file")
    if expected_size is not None and len(payload) != expected_size:
        raise AuditError(f"{label} size differs")
    if expected_sha256 is not None and sha256(payload) != expected_sha256:
        raise AuditError(f"{label} SHA-256 differs")
    if required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode:
        raise AuditError(f"{label} mode differs")
    if required_nlink is not None and before.st_nlink != required_nlink:
        raise AuditError(f"{label} link count differs")
    return payload


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _mkdir(path: Path) -> None:
    path.mkdir(mode=0o700)
    if not path.is_dir() or path.is_symlink():
        raise AuditError(f"output directory is not direct: {path}")


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o400) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, mode)
    except OSError as exc:
        raise AuditError(f"exclusive output creation failed: {path}") from exc
    try:
        os.fchmod(fd, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            if written <= 0:
                raise AuditError(f"short output write: {path}")
            offset += written
        current = os.fstat(fd)
        if (
            not stat.S_ISREG(current.st_mode)
            or stat.S_IMODE(current.st_mode) != mode
            or current.st_nlink != 1 or current.st_size != len(payload)
        ):
            raise AuditError(f"output identity differs before fsync: {path}")
        os.fsync(fd)
    finally:
        os.close(fd)
    stable_bytes(
        path, label=f"published {path.name}", maximum=max(len(payload), 1),
        expected_size=len(payload), expected_sha256=sha256(payload),
        required_mode=mode, required_nlink=1,
    )


def _replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if payload.count(old) != 1:
        raise AuditError(f"{label} anchor multiplicity differs")
    return payload.replace(old, new, 1)


def load_predecessor() -> tuple[Any, bytes, bytes]:
    source = stable_bytes(
        PREDECESSOR, label="reviewed parser predecessor source", maximum=256 << 10,
        expected_size=PREDECESSOR_SIZE, expected_sha256=PREDECESSOR_SHA256,
    )
    receipt = stable_bytes(
        PREDECESSOR_RECEIPT, label="reviewed parser predecessor receipt",
        maximum=64 << 10, expected_size=PREDECESSOR_RECEIPT_SIZE,
        expected_sha256=PREDECESSOR_RECEIPT_SHA256,
        required_mode=0o400, required_nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p319_parser_v2_for_carrier_v5")
    module.__file__ = str(PREDECESSOR)
    module.__package__ = ""
    module.__dict__["_P319_WITNESS_PARSER_BOUND_SOURCE"] = source
    sys.modules[module.__name__] = module
    try:
        exec(compile(source.decode("utf-8"), str(PREDECESSOR), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("reviewed parser predecessor bound execution failed") from exc
    return module, source, receipt


def _replace_function(module: Any, source: bytes, name: str, body: bytes) -> bytes:
    old = module._c_function_body(source, name)
    if source.count(old) != 1:
        raise AuditError(f"function {name} multiplicity differs")
    return source.replace(old, body, 1)


P319_INITIAL_V2 = b'''p319_observe_initial(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_detect_dev ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "USBC1:")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    const char *labels[5] = {"USBC1:0x", ", USBC2:0x", ", BC:0x", ", CC0:0x", ", CC1:0x"};
    uint32_t values[5] = {0};
    for (unsigned int i = 0; i < 5U; ++i) {
        long rc = p319_take_literal(&cursor, end, labels[i]);
        if (rc != 0) return rc;
        rc = p319_take_hex(&cursor, end, 1, &values[i]);
        if (rc != 0) return rc;
    }
    if (cursor != end) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (p319_primary_witness_frozen()) return 0;
    for (unsigned int i = 0U; i < 5U; ++i)
        g_p319_witness.initial_status[i] = values[i];
    long rc = p319_count(&g_p319_witness.initial_status_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_INITIAL;
    if (rc == 0) p319_chain_event(2U);
    return rc;
}
'''


P319_PARENT_MASK_V2 = b'''static long p319_observe_parent_mask(const char *message, size_t length) {
    const char *prefix = "max77705: max77705_usbc_umask_irq: ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix),
        "P319_INTSRC_MASK")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    uint32_t value = 0;
    long rc = p319_take_literal(&cursor, end, "P319_INTSRC_MASK:0x");
    if (rc == 0) rc = p319_take_hex(&cursor, end, 1, &value);
    if (rc == 0 && cursor != end) rc = -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (rc == 0 && p319_primary_witness_frozen()) return 0;
    if (rc == 0) rc = p319_count(&g_p319_witness.parent_mask_count);
    if (rc == 0) {
        g_p319_witness.parent_mask_readback = value;
        g_p319_witness.witness_mask |= P319_WITNESS_MASK_PARENT;
        p319_chain_event(4U);
    }
    return rc;
}

'''


P319_CHAIN_V2 = b'''p319_chain_event(unsigned int event) {
    if (!g_p319_witness.active_module_valid) {
        if (g_p319_witness.initial_chain_stage != 0U)
            g_p319_witness.initial_chain_ambiguous = 1U;
        return;
    }
    if (g_p319_witness.active_module_index != 72U) {
        g_p319_witness.initial_chain_ambiguous = 1U;
        return;
    }
    if (event == 1U && g_p319_witness.initial_chain_stage == 0U) {
        g_p319_witness.initial_chain_stage = 1U;
    } else if (event == 2U && g_p319_witness.initial_chain_stage == 1U) {
        g_p319_witness.initial_chain_stage = 2U;
    } else if (event == 3U && g_p319_witness.initial_chain_stage == 2U) {
        g_p319_witness.initial_chain_stage = 3U;
    } else if (event == 4U && g_p319_witness.initial_chain_stage == 3U) {
        g_p319_witness.initial_chain_stage = 4U;
    } else if (event == 5U && g_p319_witness.initial_chain_stage == 4U) {
        g_p319_witness.initial_chain_stage = 5U;
        g_p319_witness.initial_chain_complete = 1U;
        g_p319_witness.initial_chain_module_index = 72U;
    } else {
        g_p319_witness.initial_chain_ambiguous = 1U;
    }
}
'''


P319_PRIMARY_FREEZE_V2 = b'''static int p319_primary_witness_frozen(void) {
    if (g_p319_witness.initial_chain_complete != 0U ||
        (g_p319_witness.initial_chain_stage != 0U &&
         (!g_p319_witness.active_module_valid ||
          g_p319_witness.active_module_index != 72U))) {
        g_p319_witness.initial_chain_ambiguous = 1U;
        return 1;
    }
    return 0;
}

'''


P319_PROBE_V2 = b'''p319_observe_probe(const char *message, size_t length) {
    const char *prefix = "max77705: max77705_usbc_probe: ";
    const char *tail = "probing Complete..";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "probing")) return 0;
    if (!p319_eq(message + cstr_len(prefix), length - cstr_len(prefix), tail)) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (p319_primary_witness_frozen()) return 0;
    long rc = p319_count(&g_p319_witness.probe_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_PROBE;
    if (rc == 0) p319_chain_event(5U);
    return rc;
}
'''


P319_IRQ_V2 = b'''p319_observe_irq(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_irq_init ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "uiadc(")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    const char *labels[5] = {"uiadc(", "), chgtyp(", "), dcdtmo(", "), vbadc(", "), vbusdet("};
    int32_t values[5] = {0};
    for (unsigned int i = 0; i < 5U; ++i) {
        long rc = p319_take_literal(&cursor, end, labels[i]);
        if (rc != 0) return rc;
        int64_t value = 0;
        rc = p319_take_signed(&cursor, end, INT32_MIN, INT32_MAX, &value);
        if (rc != 0) return rc;
        values[i] = (int32_t)value;
    }
    long close_rc = p319_take_literal(&cursor, end, ")");
    if (close_rc != 0) return close_rc;
    if (cursor != end) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (p319_primary_witness_frozen()) return 0;
    for (unsigned int i = 0U; i < 5U; ++i)
        g_p319_witness.irq[i] = values[i];
    long rc = p319_count(&g_p319_witness.irq_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_IRQ;
    if (rc == 0) p319_chain_event(1U);
    return rc;
}
'''


P319_CLASS1_V2 = b'''p319_observe_class1(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_check_new_dev ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "vps table")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    long rc = p319_take_literal(&cursor, end, "vps table match found at i(");
    uint64_t index = 0;
    if (rc == 0) rc = p319_take_decimal(&cursor, end, UINT64_MAX, &index);
    if (rc == 0) rc = p319_take_literal(&cursor, end, "), ");
    const char *name = cursor;
    while (cursor < end) ++cursor;
    if (rc == 0) rc = p319_vps_name(name, end);
    if (rc == 0 && p319_primary_witness_frozen()) return 0;
    if (rc == 0) rc = p319_copy_name(g_p319_witness.classification_form1_name,
        &g_p319_witness.classification_form1_name_length, name, end);
    if (rc == 0) g_p319_witness.classification_form1_index = index;
    if (rc == 0) rc = p319_count(&g_p319_witness.classification_form1_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_CLASS1;
    if (rc == 0) p319_chain_event(3U);
    return rc;
}
'''


P319_V5_C_SOURCE = r'''
/* P3.19 canonical structured-witness envelope v5. */
#define S22PLUS_MAX77705_P319_ENVELOPE_VERSION 5U
#define S22PLUS_MAX77705_P319_WITNESS_ENCODING 3U
#define S22PLUS_MAX77705_P319_WITNESS_FLAG (1U << 5U)
#define S22PLUS_MAX77705_P319_PAYLOAD_ABI 2U
#define S22PLUS_MAX77705_P319_PAYLOAD_USED 76U

#define S22PLUS_MAX77705_P319_VALID_FIRST_SEQUENCE (1U << 0U)
#define S22PLUS_MAX77705_P319_VALID_LAST_SEQUENCE (1U << 1U)
#define S22PLUS_MAX77705_P319_VALID_PARENT_MASK (1U << 2U)
#define S22PLUS_MAX77705_P319_VALID_MODULE69 (1U << 3U)
#define S22PLUS_MAX77705_P319_VALID_MODULE71 (1U << 4U)
#define S22PLUS_MAX77705_P319_VALID_MODULE72 (1U << 5U)
#define S22PLUS_MAX77705_P319_VALID_INITIAL (1U << 6U)
#define S22PLUS_MAX77705_P319_VALID_CLASS1 (1U << 7U)

_Static_assert(S22PLUS_MAX77705_P319_PAYLOAD_USED ==
    S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE,
    "P3.19 witness payload fills the fixed Carrier envelope");

static void s22plus_max77705_p319_store_le24(uint8_t *output, uint32_t value)
{
    output[0] = (uint8_t)value;
    output[1] = (uint8_t)(value >> 8U);
    output[2] = (uint8_t)(value >> 16U);
}

static void s22plus_max77705_p319_store_le64(uint8_t *output, uint64_t value)
{
    for (unsigned int index = 0U; index < 8U; ++index)
        output[index] = (uint8_t)(value >> (index * 8U));
}

static uint32_t s22plus_max77705_p319_envelope_crc32(
        const uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE])
{
    static const uint8_t domain[] =
        "S22PLUS-FYG8-MAX77705-DIAG-V5\0";
    uint32_t crc = ~0U;

    crc = s22plus_max77705_envelope_crc_update(
        crc, domain, sizeof(domain) - 1U);
    crc = s22plus_max77705_envelope_crc_update(
        crc, envelope, S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET);
    return crc ^ ~0U;
}

static int s22plus_max77705_p319_module_exact(
        const struct p319_module_result_state_v1 *module,
        uint32_t index, const char *name)
{
    size_t length = cstr_len(name);
    return module != NULL && module->valid == 1U && module->index == index &&
        module->result == 0 && module->name_length == length &&
        p260_bytes_equal(module->name, name, length);
}

static int s22plus_max77705_p319_encode_envelope_v5(
        const struct s22plus_max77705_binding_witness *binding,
        const struct s22plus_max77705_p317_exec_witness *exec,
        unsigned int semantic_kind, unsigned int semantic_code,
        unsigned int observer_site, unsigned int observer_error_class,
        const struct s22plus_max77705_runtime_result *result,
        const struct s22plus_max77705_runtime_poll_summary *summary,
        const struct s22plus_max77705_p318_latch_snapshot *latch,
        const struct s22plus_p318_banner_result *banner,
        const struct p319_witness_summary_state_v2 *witness,
        uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE],
        uint16_t *terminal_detail)
{
    uint8_t *payload;
    uint8_t validity = 0U;
    uint8_t expected_mask = 0U;
    uint8_t name_digest[32];
    struct s22plus_max77705_runtime_sha256 name_context;
    uint32_t crc;
    int rc;

    if (witness == NULL || envelope == NULL || terminal_detail == NULL ||
        witness->abi_version != P319_WITNESS_ABI_VERSION ||
        witness->probe_count > UINT8_MAX || witness->irq_count > UINT8_MAX ||
        witness->initial_status_count > UINT8_MAX ||
        witness->classification_form1_count > UINT8_MAX ||
        witness->parent_mask_count > UINT8_MAX ||
        witness->malformed_count != 0U ||
        witness->module_loads != P319_KMSG_MAX_MODULES ||
        witness->module_drains != P319_KMSG_MAX_MODULES ||
        witness->record_count > P319_KMSG_MAX_TOTAL_RECORDS ||
        witness->record_bytes > P319_KMSG_MAX_TOTAL_BYTES ||
        witness->initial_chain_stage > 5U ||
        witness->initial_chain_complete > 1U ||
        witness->initial_chain_ambiguous > 1U ||
        witness->active_module_valid != 0U ||
        (witness->initial_chain_complete != 0U) !=
            (witness->initial_chain_stage == 5U) ||
        (witness->initial_chain_complete != 0U &&
            witness->initial_chain_module_index != 72U) ||
        (witness->initial_chain_complete == 0U &&
            witness->initial_chain_module_index != 0U) ||
        (witness->initial_chain_stage >= 1U && witness->irq_count == 0U) ||
        (witness->initial_chain_stage >= 2U &&
            witness->initial_status_count == 0U) ||
        (witness->initial_chain_stage >= 3U &&
            witness->classification_form1_count == 0U) ||
        (witness->initial_chain_stage >= 4U &&
            witness->parent_mask_count == 0U) ||
        (witness->initial_chain_stage >= 5U && witness->probe_count == 0U) ||
        !s22plus_max77705_p319_module_exact(
            &witness->target_modules[0], 69U, "i2c-msm-geni.ko") ||
        !s22plus_max77705_p319_module_exact(
            &witness->target_modules[1], 71U, "mfd_max77705.ko") ||
        !s22plus_max77705_p319_module_exact(
            &witness->target_modules[2], 72U, "pdic_max77705.ko"))
        return -1;
    for (unsigned int index = 0U; index < 5U; ++index) {
        if (witness->initial_status[index] > UINT8_MAX ||
            witness->irq[index] < 0 || witness->irq[index] > UINT16_MAX)
            return -1;
    }
    if (witness->parent_mask_readback > UINT8_MAX)
        return -1;
    if (witness->record_count == 0U) {
        if (witness->first_sequence_valid != 0U ||
            witness->last_sequence_valid != 0U ||
            witness->first_sequence != 0U || witness->last_sequence != 0U ||
            witness->record_bytes != 0U)
            return -1;
    } else if (witness->first_sequence_valid != 1U ||
        witness->last_sequence_valid != 1U ||
        witness->record_bytes < witness->record_count ||
        witness->last_sequence < witness->first_sequence ||
        witness->first_sequence > UINT64_MAX - (witness->record_count - 1U) ||
        witness->last_sequence - witness->first_sequence + 1U !=
            witness->record_count) {
        return -1;
    }
    if (witness->initial_status_count == 0U) {
        for (unsigned int index = 0U; index < 5U; ++index)
            if (witness->initial_status[index] != 0U) return -1;
    }
    if (witness->irq_count == 0U) {
        for (unsigned int index = 0U; index < 5U; ++index)
            if (witness->irq[index] != 0) return -1;
    }
    if (witness->parent_mask_count == 0U &&
        witness->parent_mask_readback != 0U)
        return -1;
    if (witness->classification_form1_count == 0U) {
        if (witness->classification_form1_index != 0U ||
            witness->classification_form1_name_length != 0U)
            return -1;
    } else if (witness->classification_form1_name_length == 0U ||
        witness->classification_form1_name_length > 64U) {
        return -1;
    }

    if (witness->probe_count != 0U) expected_mask |= P319_WITNESS_MASK_PROBE;
    if (witness->irq_count != 0U) expected_mask |= P319_WITNESS_MASK_IRQ;
    if (witness->initial_status_count != 0U) expected_mask |= P319_WITNESS_MASK_INITIAL;
    if (witness->classification_form1_count != 0U) expected_mask |= P319_WITNESS_MASK_CLASS1;
    if (witness->classification_form2_count != 0U) expected_mask |= P319_WITNESS_MASK_CLASS2;
    if (witness->deferred_status_count != 0U) expected_mask |= P319_WITNESS_MASK_DEFERRED;
    if (witness->parent_mask_count != 0U) expected_mask |= P319_WITNESS_MASK_PARENT;
    if (witness->witness_mask != expected_mask ||
        (witness->witness_mask & ~0x7fU) != 0U)
        return -1;

    rc = s22plus_max77705_p318_encode_envelope(
        binding, exec, semantic_kind, semantic_code, observer_site,
        observer_error_class, result, summary, latch, banner, envelope,
        terminal_detail);
    if (rc != 0) return rc;

    /* V4 remains the semantic/header validator, but its poll-capacity
     * overflow rewrite is specific to the V4 payload that V5 deliberately
     * does not retain.  Restore the validated caller semantic before the V5
     * CRC is committed. */
    if (semantic_kind == S22PLUS_MAX77705_SEMANTIC_TERMINAL) {
        envelope[5] = (uint8_t)semantic_code;
        envelope[6] = 0U;
    } else {
        envelope[5] = 0U;
        envelope[6] = (uint8_t)semantic_code;
    }
    *terminal_detail = envelope[5] != 0U
        ? (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + envelope[5] - 1U)
        : (uint16_t)(S22PLUS_MAX77705_B_DETAIL_BASE + 0x0fU +
            envelope[6] - 1U);

    payload = envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET;
    memset(payload, 0, S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE);
    envelope[0] = 'M'; envelope[1] = 'X'; envelope[2] = 'D'; envelope[3] = '5';
    envelope[4] = S22PLUS_MAX77705_P319_ENVELOPE_VERSION;
    envelope[7] = (uint8_t)((envelope[7] &
        (S22PLUS_MAX77705_FLAG_RESULT_PRESENT |
         S22PLUS_MAX77705_FLAG_BINDING_PRESENT |
         S22PLUS_MAX77705_P317_FLAG_EXEC_PRESENT)) |
        S22PLUS_MAX77705_P319_WITNESS_FLAG);
    envelope[43] = S22PLUS_MAX77705_P319_WITNESS_ENCODING;
    envelope[46] = S22PLUS_MAX77705_P319_PAYLOAD_USED;

    if (witness->first_sequence_valid != 0U) validity |=
        S22PLUS_MAX77705_P319_VALID_FIRST_SEQUENCE;
    if (witness->last_sequence_valid != 0U) validity |=
        S22PLUS_MAX77705_P319_VALID_LAST_SEQUENCE;
    if (witness->parent_mask_count != 0U) validity |=
        S22PLUS_MAX77705_P319_VALID_PARENT_MASK;
    validity |= S22PLUS_MAX77705_P319_VALID_MODULE69 |
        S22PLUS_MAX77705_P319_VALID_MODULE71 |
        S22PLUS_MAX77705_P319_VALID_MODULE72;
    if (witness->initial_status_count != 0U) validity |=
        S22PLUS_MAX77705_P319_VALID_INITIAL;
    if (witness->classification_form1_count != 0U) validity |=
        S22PLUS_MAX77705_P319_VALID_CLASS1;

    payload[0] = S22PLUS_MAX77705_P319_PAYLOAD_ABI;
    payload[1] = (uint8_t)witness->witness_mask;
    payload[2] = validity;
    payload[3] = (uint8_t)(witness->initial_chain_stage |
        (witness->initial_chain_complete << 3U) |
        (witness->initial_chain_ambiguous << 4U));
    for (unsigned int index = 0U; index < 3U; ++index)
        s22plus_max77705_store_le16(payload + 4U + index * 2U,
            (uint16_t)(int16_t)witness->target_modules[index].result);
    payload[10] = (uint8_t)witness->probe_count;
    payload[11] = (uint8_t)witness->irq_count;
    payload[12] = (uint8_t)witness->initial_status_count;
    payload[13] = (uint8_t)witness->classification_form1_count;
    payload[14] = (uint8_t)witness->parent_mask_count;
    for (unsigned int index = 0U; index < 5U; ++index)
        payload[15U + index] = (uint8_t)witness->initial_status[index];
    payload[20] = (uint8_t)witness->parent_mask_readback;
    for (unsigned int index = 0U; index < 5U; ++index)
        s22plus_max77705_store_le16(payload + 21U + index * 2U,
            (uint16_t)witness->irq[index]);
    s22plus_max77705_p319_store_le64(
        payload + 31U, witness->classification_form1_index);
    memset(name_digest, 0, sizeof(name_digest));
    if (witness->classification_form1_count != 0U) {
        s22plus_max77705_runtime_sha256_init(&name_context);
        s22plus_max77705_runtime_sha256_update(&name_context,
            (const uint8_t *)witness->classification_form1_name,
            witness->classification_form1_name_length);
        s22plus_max77705_runtime_sha256_final(&name_context, name_digest);
    }
    s22plus_max77705_envelope_copy(payload + 39U, name_digest, 16U);
    s22plus_max77705_store_le16(payload + 55U,
        (uint16_t)witness->record_count);
    s22plus_max77705_p319_store_le24(payload + 57U,
        (uint32_t)witness->record_bytes);
    s22plus_max77705_p319_store_le64(payload + 60U,
        witness->first_sequence);
    s22plus_max77705_p319_store_le64(payload + 68U,
        witness->last_sequence);

    crc = s22plus_max77705_p319_envelope_crc32(envelope);
    s22plus_max77705_store_le32(
        envelope + S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET, crc);
    return 0;
}
'''.encode("ascii")


def transform_runtime(module: Any, base: bytes) -> bytes:
    value = _replace_once(
        base, b"#define P319_WITNESS_ABI_VERSION 1U\n",
        b"#define P319_WITNESS_ABI_VERSION 2U\n", "witness ABI version",
    )
    value = _replace_once(
        value, b"#define P319_WITNESS_MASK_DEFERRED (1U << 5U)\n",
        b"#define P319_WITNESS_MASK_DEFERRED (1U << 5U)\n"
        b"#define P319_WITNESS_MASK_PARENT (1U << 6U)\n",
        "parent-mask witness bit",
    )
    value = value.replace(
        b"struct p319_witness_summary_state_v1",
        b"struct p319_witness_summary_state_v2",
    ).replace(
        b"p319_witness_summary_state_v1_copy",
        b"p319_witness_summary_state_v2_copy",
    ).replace(
        b"p319_witness_observe_v1",
        b"p319_witness_observe_v2",
    )
    value = _replace_once(
        value, b"    uint32_t initial_status_count;\n",
        b"    uint32_t initial_status_count;\n    uint32_t parent_mask_count;\n",
        "parent-mask count state",
    )
    value = _replace_once(
        value, b"    uint32_t initial_status[3];\n",
        b"    uint32_t initial_status[5];\n    uint32_t parent_mask_readback;\n",
        "five-byte status state",
    )
    value = _replace_function(module, value, "p319_chain_event", P319_CHAIN_V2)
    probe_anchor = b"static long p319_observe_probe(const char *message, size_t length) {\n"
    value = _replace_once(
        value, probe_anchor, P319_PRIMARY_FREEZE_V2 + probe_anchor,
        "primary-witness freeze helper",
    )
    value = _replace_function(module, value, "p319_observe_probe", P319_PROBE_V2)
    value = _replace_function(module, value, "p319_observe_irq", P319_IRQ_V2)
    value = _replace_function(module, value, "p319_observe_initial", P319_INITIAL_V2)
    value = _replace_function(module, value, "p319_observe_class1", P319_CLASS1_V2)
    class_anchor = b"static long p319_observe_class1(const char *message, size_t length) {\n"
    value = _replace_once(
        value, class_anchor, P319_PARENT_MASK_V2 + class_anchor,
        "parent-mask parser insertion",
    )
    value = _replace_once(
        value,
        b"    if (rc == 0) rc = p319_observe_class1(message, length);\n"
        b"    if (rc == 0) rc = p319_observe_class2(message, length);\n",
        b"    if (rc == 0) rc = p319_observe_class1(message, length);\n"
        b"    if (rc == 0) rc = p319_observe_parent_mask(message, length);\n"
        b"    if (rc == 0) rc = p319_observe_class2(message, length);\n",
        "parent-mask parser dispatch",
    )
    envelope_anchor = b"\n/* P3.17 boot-specific executability witness. */\n"
    value = _replace_once(
        value, envelope_anchor, b"\n" + P319_V5_C_SOURCE + envelope_anchor,
        "Envelope-v5 insertion",
    )
    value = _replace_once(
        value,
        b"\tstruct s22plus_p318_banner_result banner;\n\tuint8_t envelope",
        b"\tstruct s22plus_p318_banner_result banner;\n"
        b"\tstruct p319_witness_summary_state_v2 witness;\n\tuint8_t envelope",
        "publisher witness local",
    )
    value = _replace_once(
        value,
        b"\trc = s22plus_max77705_p318_encode_envelope(\n",
        b"\tif (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
        b"\t\tp290_fail_next(P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION);\n"
        b"\trc = s22plus_max77705_p319_encode_envelope_v5(\n",
        "publisher V5 call",
    )
    value = _replace_once(
        value,
        b"\t\tlatch_pointer, &banner, envelope, &detail);\n",
        b"\t\tlatch_pointer, &banner, &witness, envelope, &detail);\n",
        "publisher witness argument",
    )
    return value


def transform_muic_driver(base: bytes) -> bytes:
    old = b'''\tpr_info("%s USBC1:0x%02x, USBC2:0x%02x, BC:0x%02x\\n",
\t\t\t__func__, status[0], status[1], status[2]);
'''
    new = b'''\tpr_info("%s USBC1:0x%02x, USBC2:0x%02x, BC:0x%02x, CC0:0x%02x, CC1:0x%02x\\n",
\t\t\t__func__, status[0], status[1], status[2], status[3], status[4]);
'''
    return _replace_once(base, old, new, "five-byte synchronous status emitter")


def transform_usbc_driver(base: bytes) -> bytes:
    old = b'''\ti2c_data &= ~((1 << 3));\t/* Unmask muic interrupt */
\tmax77705_write_reg(usbc_data->i2c, 0x23,
\t\t\t   i2c_data);
'''
    new = b'''\ti2c_data &= ~((1 << 3));\t/* Unmask muic interrupt */
\tret = max77705_write_reg(usbc_data->i2c, 0x23,
\t\t\t   i2c_data);
\tif (ret) {
\t\tpr_err("%s fail to write muic mask reg\\n", __func__);
\t\treturn;
\t}
\tret = max77705_read_reg(usbc_data->i2c, 0x23, &i2c_data);
\tif (ret) {
\t\tpr_err("%s fail to read back muic mask reg\\n", __func__);
\t\treturn;
\t}
\tmsg_maxim("P319_INTSRC_MASK:0x%02x", i2c_data);
'''
    return _replace_once(base, old, new, "parent mask write/readback emitter")


def transform_sources(module: Any, base: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(base)
    runtime = "s22plus_fyg8_p290_e3_runtime.inc.c"
    result[runtime] = transform_runtime(module, base[runtime])
    changed = {name for name in result if result[name] != base[name]}
    if changed != {runtime}:
        raise AuditError(f"unexpected generated-source delta: {sorted(changed)}")
    return result


def patch_bytes(name: str, before: bytes, after: bytes) -> bytes:
    old = before.decode("utf-8").splitlines(keepends=True)
    new = after.decode("utf-8").splitlines(keepends=True)
    return "".join(difflib.unified_diff(
        old, new, fromfile=f"a/{name}", tofile=f"b/{name}", n=3,
    )).encode("utf-8")


def _paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "inputs": root / "inputs",
        "base": root / "base-sources",
        "sources": root / "materialized-sources",
        "drivers": root / "driver-sources",
        "patches": root / "driver-patches",
        "result": root / "result.json",
    }


def expected_materialization() -> dict[str, Any]:
    module, predecessor_source, predecessor_receipt = load_predecessor()
    predecessor_inputs = module.load_inputs(False, PREDECESSOR_ROOT)
    base = module._generated_sources(predecessor_inputs)
    generated = transform_sources(module, base)
    muic_before = predecessor_inputs["max77705-muic.c"]
    usbc_before = predecessor_inputs["max77705_usbc.c"]
    drivers = {
        "max77705-muic.c": transform_muic_driver(muic_before),
        "max77705_usbc.c": transform_usbc_driver(usbc_before),
    }
    originals = {
        "predecessor-auditor.py": predecessor_source,
        "predecessor-result.json": predecessor_receipt,
        "max77705-muic.c": muic_before,
        "max77705_usbc.c": usbc_before,
    }
    patches = {
        "max77705-muic.c.patch": patch_bytes("max77705-muic.c", muic_before, drivers["max77705-muic.c"]),
        "max77705_usbc.c.patch": patch_bytes("max77705_usbc.c", usbc_before, drivers["max77705_usbc.c"]),
    }
    return {
        "module": module, "originals": originals, "base": base,
        "generated": generated, "drivers": drivers, "patches": patches,
    }


def load_inputs(materialize: bool, output_root: Path | None = None) -> dict[str, Any]:
    root = (output_root or OUTPUT_ROOT).absolute()
    expected = expected_materialization()
    paths = _paths(root)
    if materialize:
        if root.exists() or root.is_symlink():
            raise AuditError("Carrier-v5 output root already exists")
        _mkdir(root)
        for key in ("inputs", "base", "sources", "drivers", "patches"):
            _mkdir(paths[key])
        for name, payload in expected["originals"].items():
            _write_exclusive(paths["inputs"] / name, payload)
        for name, payload in expected["base"].items():
            _write_exclusive(paths["base"] / name, payload)
        for name, payload in expected["generated"].items():
            _write_exclusive(paths["sources"] / name, payload)
        for name, payload in expected["drivers"].items():
            _write_exclusive(paths["drivers"] / name, payload)
        for name, payload in expected["patches"].items():
            _write_exclusive(paths["patches"] / name, payload)
        for key in ("inputs", "base", "sources", "drivers", "patches"):
            _fsync_directory(paths[key])
        _fsync_directory(root)
        _fsync_directory(root.parent)
    for group, key in (
        ("originals", "inputs"), ("base", "base"),
        ("generated", "sources"), ("drivers", "drivers"),
        ("patches", "patches"),
    ):
        preserved: dict[str, bytes] = {}
        for name, payload in expected[group].items():
            preserved[name] = stable_bytes(
                paths[key] / name, label=f"preserved {group} {name}",
                maximum=max(len(payload), 1), expected_size=len(payload),
                expected_sha256=sha256(payload), required_mode=0o400,
                required_nlink=1,
            )
        expected[f"preserved_{group}"] = preserved
    return expected


def audit_v4_unchanged(module: Any, base: bytes, generated: bytes) -> dict[str, Any]:
    functions = (
        "s22plus_max77705_p318_envelope_crc32",
        "s22plus_max77705_p318_encode_envelope",
    )
    result: dict[str, Any] = {}
    for name in functions:
        before = module._c_function_body(base, name)
        after = module._c_function_body(generated, name)
        if before != after:
            raise AuditError(f"Envelope-v4 function changed: {name}")
        result[name] = identity(before)
    tokens = (
        b"#define S22PLUS_MAX77705_P318_ENVELOPE_VERSION 4U\n",
        b"#define S22PLUS_MAX77705_P318_TIME_MASK 0xffU\n",
        b'"S22PLUS-FYG8-MAX77705-DIAG-V4\\0"',
    )
    for token in tokens:
        if base.count(token) != 1 or generated.count(token) != 1:
            raise AuditError("Envelope-v4 token changed")
    return {
        "encoder_and_crc_byte_identical": True,
        "functions": result,
        "version": 4,
        "time_mask": "0xffU",
        "reinterpretation": False,
    }


def audit_driver_producers(originals: dict[str, bytes], drivers: dict[str, bytes], module: Any) -> dict[str, Any]:
    muic = drivers["max77705-muic.c"]
    usbc = drivers["max77705_usbc.c"]
    if originals["max77705-muic.c"] == muic or originals["max77705_usbc.c"] == usbc:
        raise AuditError("driver producer delta absent")
    muic_body = module._c_function_body(muic, "max77705_muic_detect_dev")
    if (
        muic_body.count(b"max77705_bulk_read(i2c,") != 1
        or muic_body.count(b"MAX77705_USBC_REG_USBC_STATUS1, 5, status") != 1
        or muic_body.count(b"CC0:0x%02x, CC1:0x%02x") != 1
        or muic_body.find(b"max77705_bulk_read(i2c,") > muic_body.find(b"CC0:0x%02x")
    ):
        raise AuditError("five-byte synchronous producer chain differs")
    usbc_body = module._c_function_body(usbc, "max77705_usbc_umask_irq")
    ordered = (
        b"max77705_read_reg(usbc_data->i2c, 0x23",
        b"i2c_data &= ~((1 << 3))",
        b"ret = max77705_write_reg(usbc_data->i2c, 0x23",
        b"ret = max77705_read_reg(usbc_data->i2c, 0x23, &i2c_data)",
        b'msg_maxim("P319_INTSRC_MASK:0x%02x", i2c_data)',
    )
    positions = [usbc_body.find(token) for token in ordered]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise AuditError("parent-mask write/readback producer order differs")
    if usbc_body.count(b"max77705_read_reg(usbc_data->i2c, 0x23") != 2:
        raise AuditError("parent-mask read transaction count differs")
    if usbc_body.count(b"max77705_write_reg(usbc_data->i2c, 0x23") != 1:
        raise AuditError("parent-mask write transaction count differs")
    return {
        "initial_status_source_read_bytes": 5,
        "initial_status_logged_bytes": 5,
        "initial_status_added_i2c_transactions": 0,
        "parent_mask_register": "0x23",
        "parent_mask_bit": 3,
        "parent_mask_existing_write_checked": True,
        "parent_mask_added_read_transactions": 1,
        "parent_mask_readback_emitter": "P319_INTSRC_MASK",
        "driver_sources_materialized_only": True,
        "compiled_module_created": False,
    }


def _le24(value: int) -> bytes:
    return value.to_bytes(3, "little")


def _expected_mask(state: dict[str, Any]) -> int:
    mask = 0
    for key, bit in (
        ("probe_count", MASK_PROBE), ("irq_count", MASK_IRQ),
        ("initial_status_count", MASK_INITIAL),
        ("classification_form1_count", MASK_CLASS1),
        ("classification_form2_count", MASK_CLASS2),
        ("deferred_status_count", MASK_DEFERRED),
        ("parent_mask_count", MASK_PARENT),
    ):
        if state[key]:
            mask |= bit
    return mask


def encode_payload_v5(state: dict[str, Any]) -> bytes:
    required = {
        "witness_mask", "probe_count", "irq_count", "initial_status_count",
        "classification_form1_count", "classification_form2_count",
        "deferred_status_count", "parent_mask_count", "initial_status",
        "parent_mask_readback", "irq", "classification_form1_index",
        "classification_form1_name", "record_count", "record_bytes",
        "first_sequence", "last_sequence", "first_sequence_valid",
        "last_sequence_valid", "chain_stage", "chain_complete",
        "chain_ambiguous", "module_results",
    }
    if set(state) != required:
        raise AuditError("V5 state key set differs")
    counts = [state[key] for key in (
        "probe_count", "irq_count", "initial_status_count",
        "classification_form1_count", "parent_mask_count",
    )]
    if any(type(value) is not int or not 0 <= value <= 255 for value in counts):
        raise AuditError("V5 count is outside uint8")
    if state["witness_mask"] != _expected_mask(state) or state["witness_mask"] & ~MASK_ALL:
        raise AuditError("V5 witness mask differs from counts")
    status_values = state["initial_status"]
    irq_values = state["irq"]
    if len(status_values) != 5 or any(type(value) is not int or not 0 <= value <= 255 for value in status_values):
        raise AuditError("V5 initial status differs")
    if len(irq_values) != 5 or any(type(value) is not int or not 0 <= value <= 65535 for value in irq_values):
        raise AuditError("V5 IRQ tuple differs")
    parent = state["parent_mask_readback"]
    if type(parent) is not int or not 0 <= parent <= 255:
        raise AuditError("V5 parent mask differs")
    modules = state["module_results"]
    if modules != [0, 0, 0]:
        raise AuditError("V5 module result tuple differs")
    record_count = state["record_count"]
    record_bytes = state["record_bytes"]
    if type(record_count) is not int or not 0 <= record_count <= MAX_RECORDS:
        raise AuditError("V5 record count differs")
    if type(record_bytes) is not int or not 0 <= record_bytes <= MAX_RECORD_BYTES:
        raise AuditError("V5 record byte count differs")
    first_valid = state["first_sequence_valid"]
    last_valid = state["last_sequence_valid"]
    first = state["first_sequence"]
    last = state["last_sequence"]
    if type(first_valid) is not bool or type(last_valid) is not bool:
        raise AuditError("V5 sequence validity type differs")
    if any(type(value) is not int or not 0 <= value <= (1 << 64) - 1 for value in (first, last)):
        raise AuditError("V5 sequence range differs")
    if record_count == 0:
        if first_valid or last_valid or first or last or record_bytes:
            raise AuditError("empty V5 sequence is not canonical")
    elif (not first_valid or not last_valid or record_bytes < record_count
          or last < first or last - first + 1 != record_count):
        raise AuditError("V5 sequence accounting differs")
    for key in ("chain_complete", "chain_ambiguous"):
        if type(state[key]) is not bool:
            raise AuditError("V5 chain boolean type differs")
    stage = state["chain_stage"]
    if type(stage) is not int or not 0 <= stage <= 5 or state["chain_complete"] != (stage == 5):
        raise AuditError("V5 chain state differs")
    if any((
        stage >= 1 and not state["irq_count"],
        stage >= 2 and not state["initial_status_count"],
        stage >= 3 and not state["classification_form1_count"],
        stage >= 4 and not state["parent_mask_count"],
        stage >= 5 and not state["probe_count"],
    )):
        raise AuditError("V5 chain stage lacks its preceding witness")
    name = state["classification_form1_name"]
    if type(name) is not str:
        raise AuditError("V5 classification name differs")
    try:
        name_bytes = name.encode("ascii")
    except UnicodeEncodeError as exc:
        raise AuditError("V5 classification name differs") from exc
    # Keep this byte-for-byte equivalent to the bound native p319_vps_name:
    # nonempty, at most 64 bytes, printable ASCII, and no edge space.
    if (
        not name_bytes or len(name_bytes) > 64
        or name_bytes[0] == 0x20 or name_bytes[-1] == 0x20
        or any(value < 0x20 or value > 0x7E for value in name_bytes)
    ) and state["classification_form1_count"]:
        raise AuditError("V5 classification name differs")
    if state["classification_form1_count"] == 0:
        if state["classification_form1_index"] != 0 or name:
            raise AuditError("absent V5 classification has data")
        name_digest = bytes(16)
    else:
        name_digest = hashlib.sha256(name_bytes).digest()[:16]
    if state["initial_status_count"] == 0 and any(status_values):
        raise AuditError("absent V5 initial status has data")
    if state["irq_count"] == 0 and any(irq_values):
        raise AuditError("absent V5 IRQ tuple has data")
    if state["parent_mask_count"] == 0 and parent:
        raise AuditError("absent V5 parent mask has data")

    validity = VALID_MODULE_69 | VALID_MODULE_71 | VALID_MODULE_72
    if first_valid:
        validity |= VALID_FIRST_SEQUENCE
    if last_valid:
        validity |= VALID_LAST_SEQUENCE
    if state["parent_mask_count"]:
        validity |= VALID_PARENT_MASK
    if state["initial_status_count"]:
        validity |= VALID_INITIAL_STATUS
    if state["classification_form1_count"]:
        validity |= VALID_CLASSIFICATION
    chain = stage | (int(state["chain_complete"]) << 3) | (int(state["chain_ambiguous"]) << 4)
    payload = bytearray(PAYLOAD_SIZE)
    payload[0:4] = bytes((2, state["witness_mask"], validity, chain))
    for index, result in enumerate(modules):
        payload[4 + index * 2:6 + index * 2] = struct.pack("<h", result)
    payload[10:15] = bytes(counts)
    payload[15:20] = bytes(status_values)
    payload[20] = parent
    for index, irq in enumerate(irq_values):
        payload[21 + index * 2:23 + index * 2] = struct.pack("<H", irq)
    payload[31:39] = struct.pack("<Q", state["classification_form1_index"])
    payload[39:55] = name_digest
    payload[55:57] = struct.pack("<H", record_count)
    payload[57:60] = _le24(record_bytes)
    payload[60:68] = struct.pack("<Q", first)
    payload[68:76] = struct.pack("<Q", last)
    return bytes(payload)


def _validate_fixed_result_header(envelope: bytes) -> dict[str, Any]:
    stage = envelope[8]
    rc = struct.unpack_from("<i", envelope, 9)[0]
    pmic_valid = envelope[13]
    initial_valid = envelope[16]
    issued = envelope[18]
    seen = envelope[19]
    write_attempted = envelope[20]
    write_ambiguous = envelope[21]
    opcodes = tuple(envelope[22:26])
    values = tuple(envelope[26:30])
    reachable_masks = {0x00, 0x01, 0x03, 0x05, 0x07, 0x0D, 0x0F}
    if (
        not 2 <= stage <= 10 or stage == 8
        or (rc == 0) != (stage == 10)
        or pmic_valid > 3 or initial_valid > 1
        or write_attempted > 1 or write_ambiguous > 1
        or issued not in reachable_masks or seen not in reachable_masks
        or write_attempted != bool(issued & 0x02)
        or (write_ambiguous and not write_attempted)
    ):
        raise AuditError("Envelope-v5 fixed result header differs")
    if stage in {2, 3, 4}:
        if issued or seen or write_attempted:
            raise AuditError("Envelope-v5 pre-command result differs")
    elif stage == 5:
        if issued != 0x01 or seen not in {0x00, 0x01} or write_attempted:
            raise AuditError("Envelope-v5 pre-read result differs")
    elif stage == 6:
        if (
            issued != 0x03 or seen not in {0x01, 0x03}
            or opcodes[0] != 0x05 or values[0] == 0x09
            or write_attempted != 1 or write_ambiguous != 1
        ):
            raise AuditError("Envelope-v5 write-stage result differs")
    elif stage == 7:
        write_path = values[0] != 0x09
        expected_issued = 0x07 if write_path else 0x05
        prefix_seen = 0x03 if write_path else 0x01
        if (
            issued != expected_issued or seen not in {prefix_seen, expected_issued}
            or opcodes[0] != 0x05 or write_attempted != int(write_path)
            or values[1] != 0
            or (not write_path and opcodes[1] != 0)
            or (write_path and (write_ambiguous != 0 or opcodes[1] != 0x06))
        ):
            raise AuditError("Envelope-v5 post1 result differs")
    elif stage == 9:
        write_path = values[0] != 0x09
        expected_issued = 0x0F if write_path else 0x0D
        prefix_seen = 0x07 if write_path else 0x05
        if (
            issued != expected_issued or seen not in {prefix_seen, expected_issued}
            or opcodes[0] != 0x05 or opcodes[2] != 0x05
            or write_attempted != int(write_path) or values[1] != 0
            or (not write_path and opcodes[1] != 0)
            or (write_path and (write_ambiguous != 0 or opcodes[1] != 0x06))
        ):
            raise AuditError("Envelope-v5 post2 result differs")
    elif stage == 10:
        if (
            issued not in {0x0D, 0x0F} or seen != issued
            or opcodes[0] != 0x05 or opcodes[2] != 0x05 or opcodes[3] != 0x05
            or (issued & 0x02 and opcodes[1] != 0x06)
            or values[1] != 0
            or (values[0] == 0x09) != (not write_attempted)
            or write_ambiguous != 0
        ):
            raise AuditError("Envelope-v5 complete result differs")
    return {
        "stage": stage, "rc": rc, "pmic_valid_mask": pmic_valid,
        "pmic_id": envelope[14], "pmic_rev": envelope[15],
        "initial_uic_valid": initial_valid, "initial_uic": envelope[17],
        "command_issued_mask": issued, "response_seen_mask": seen,
        "write_attempted": write_attempted,
        "write_ambiguous": write_ambiguous,
        "response_opcode": opcodes, "response_value": values,
        "poll_counts": tuple(envelope[30:34]),
    }


def _v5_provider_ready(present: int, bound: int) -> bool:
    """Mirror the bound P3.17 provider-ready predicate."""
    return (
        bool(present & 0x80)
        and (present & 0x07) == 0x07
        and ((present >> 4) & 0x07) == 0
        and (bound & 0x07) == 0x07
        and ((bound >> 4) & 0x07) == 0
    )


def _v5_binding_causal_ready(binding: bytes) -> bool:
    """Mirror binding_causal_ready after the P3.17 three-byte packing."""
    if len(binding) != 3:
        return False
    packed0, packed1, packed2 = binding
    return (
        (packed0 & 0x03) == 2  # finit_module returned success
        and bool(packed0 & 0x04)  # exact parent present
        and ((packed0 >> 3) & 0x03) == 1  # pre exact parent unbound
        and (packed1 & 0x03) == 1  # one matching unbound parent
        and ((packed1 >> 2) & 0x03) == 0  # no wrong-address parent
        and ((packed0 >> 5) & 0x03) == 3  # diagnostic parent driver
        and ((packed1 >> 4) & 0x03) == 1  # one diagnostic bound parent
        and ((packed1 >> 6) & 0x03) == 1  # one exact adapter client
        and (packed2 & 0x03) == 0  # no foreign client
    )


def _v5_exec_valid(values: tuple[int, int, int, int, int, int]) -> bool:
    """Mirror s22plus_max77705_p317_exec_valid exactly."""
    policy, pre_present, pre_bound, post_present, post_bound, link = values
    waiting = link & 0x03
    supplier = (link & 0x0C) >> 2
    return (
        (policy & 0x70) == 0
        and (policy & 0x07) <= 4
        and (pre_present & 0x08) == 0
        and (pre_bound & 0x88) == 0
        and (post_present & 0x08) == 0
        and (post_bound & 0x88) == 0
        and (link & 0x70) == 0
        and waiting <= 3
        and supplier <= 3
    )


def _v5_exec_causal_ready(
    values: tuple[int, int, int, int, int, int],
) -> bool:
    """Mirror the bound P3.17 exec_causal_ready predicate."""
    if not _v5_exec_valid(values):
        return False
    policy, pre_present, pre_bound, post_present, post_bound, link = values
    waiting = link & 0x03
    supplier = (link & 0x0C) >> 2
    return (
        bool(policy & 0x80)
        and (policy & 0x07) == 1
        and bool(policy & 0x08)
        and _v5_provider_ready(pre_present, pre_bound)
        and _v5_provider_ready(post_present, post_bound)
        and bool(link & 0x80)
        and waiting == 2
        and supplier in {1, 2}
    )


def _v5_terminal_witness_consistent(
    terminal_code: int, exec_values: tuple[int, int, int, int, int, int],
) -> bool:
    """Mirror the source terminal>=10 execution-witness predicate."""
    if not _v5_exec_valid(exec_values):
        return False
    policy, pre_present, pre_bound, post_present, post_bound, link = exec_values
    policy_state = policy & 0x07
    waiting = link & 0x03
    supplier = (link & 0x0C) >> 2
    if terminal_code == 10:
        return bool(policy & 0x80) and policy_state != 1
    if terminal_code == 11:
        return bool(pre_present & 0x80) and not _v5_provider_ready(
            pre_present, pre_bound
        )
    if terminal_code == 12:
        return (
            _v5_provider_ready(pre_present, pre_bound)
            and bool(post_present & 0x80)
            and not _v5_provider_ready(post_present, post_bound)
        )
    if terminal_code == 13:
        return bool(link & 0x80) and supplier not in {1, 2}
    if terminal_code == 14:
        return bool(link & 0x80) and waiting != 2
    if terminal_code == 15:
        return True
    return False


def _v5_expected_semantic(
    fixed_result: dict[str, Any], binding: bytes,
) -> tuple[int, int]:
    """Mirror the V2/V3 expected semantic decision at the V4 call seam."""
    rc = fixed_result["rc"]
    stage = fixed_result["stage"]
    if rc > 0:
        return 1, 8
    if rc < 0:
        if stage == 2 and rc == -19:
            return 1, 3
        if stage <= 4:
            return 1, 5
        if stage in {5, 6, 7, 9}:
            return (2, 5) if _v5_binding_causal_ready(binding) else (1, 8)
        raise AuditError("Envelope-v5 negative result stage is not classifiable")
    if stage != 10:
        raise AuditError("Envelope-v5 zero result is not complete")
    if not _v5_binding_causal_ready(binding):
        return 1, 8
    pre, post1, post2 = (
        fixed_result["response_value"][0],
        fixed_result["response_value"][2],
        fixed_result["response_value"][3],
    )
    if post1 == 0x09 and post2 != 0x09:
        return 2, 3
    if pre != 0x09 and post1 == 0x09 and post2 == 0x09:
        return 2, 1
    if pre == 0x09 and post1 == 0x09 and post2 == 0x09:
        return 2, 2
    return 2, 4


def decode_envelope_v5(envelope: bytes) -> dict[str, Any]:
    if len(envelope) != ENVELOPE_SIZE or envelope[:5] != b"MXD5\x05":
        raise AuditError("Envelope-v5 header differs")
    flags = envelope[7]
    if (
        flags & ((1 << 1) | (1 << 3) | (1 << 6) | (1 << 7))
        or not flags & (1 << 2) or not flags & (1 << 4)
        or not flags & V5_WITNESS_FLAG
    ):
        raise AuditError("Envelope-v5 flags differ")
    terminal_code, mux_code = envelope[5], envelope[6]
    if (
        (terminal_code == 0) == (mux_code == 0)
        or terminal_code > 15 or mux_code > 5
    ):
        raise AuditError("Envelope-v5 semantic code differs")
    observer_site = envelope[47] >> 4
    observer_error = envelope[47] & 0x0F
    if (
        observer_site > 14 or observer_error > 7
        or ((observer_site == 0) != (observer_error == 0))
        or (observer_site != 0 and (
            flags & 1 or terminal_code != 8 or mux_code != 0
        ))
    ):
        raise AuditError("Envelope-v5 observer tag differs")
    binding = envelope[34:37]
    if binding[0] & 0x80 or binding[2] & 0xFC:
        raise AuditError("Envelope-v5 compact binding reserved bits differ")
    count_classes = (
        binding[1] & 3, (binding[1] >> 2) & 3,
        (binding[1] >> 4) & 3, (binding[1] >> 6) & 3,
        binding[2] & 3,
    )
    if 3 in count_classes:
        raise AuditError("Envelope-v5 compact binding count class differs")
    policy, pre_present, pre_bound, post_present, post_bound, link = envelope[37:43]
    if (
        policy & 0x70 or (policy & 7) > 4
        or pre_present & 0x08 or pre_bound & 0x88
        or post_present & 0x08 or post_bound & 0x88
        or link & 0x70
    ):
        raise AuditError("Envelope-v5 execution witness reserved bits differ")
    result_present = bool(flags & 1)
    if not result_present and any(envelope[8:34]):
        raise AuditError("Envelope-v5 result-absent header carries result bytes")
    if mux_code and not result_present:
        raise AuditError("Envelope-v5 MUX row lacks a diagnostic result")
    fixed_result = _validate_fixed_result_header(envelope) if result_present else None
    exec_values = tuple(envelope[37:43])
    if not _v5_exec_valid(exec_values):
        raise AuditError("Envelope-v5 execution witness differs")
    if terminal_code >= 10:
        if result_present or observer_site != 0 or not _v5_terminal_witness_consistent(
            terminal_code, exec_values
        ):
            raise AuditError("Envelope-v5 terminal and execution witness disagree")
    if result_present:
        expected_kind, expected_code = _v5_expected_semantic(fixed_result, binding)
        actual = (2, mux_code) if mux_code else (1, terminal_code)
        if actual != (expected_kind, expected_code):
            raise AuditError("Envelope-v5 result and semantic disagree")
        if mux_code and (
            not _v5_binding_causal_ready(binding)
            or not _v5_exec_causal_ready(exec_values)
        ):
            raise AuditError("Envelope-v5 MUX row lacks exact causal witnesses")
    raw_size = struct.unpack_from("<H", envelope, 44)[0]
    if sum(envelope[30:34]) != raw_size or (not result_present and raw_size):
        raise AuditError("Envelope-v5 fixed result count differs")
    if envelope[43] != V5_ENCODING or envelope[46] != PAYLOAD_SIZE:
        raise AuditError("Envelope-v5 encoding header differs")
    expected_crc = zlib.crc32(V5_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF
    if envelope[CRC_OFFSET:] != struct.pack("<I", expected_crc):
        raise AuditError("Envelope-v5 CRC differs")
    payload = envelope[PAYLOAD_OFFSET:CRC_OFFSET]
    if payload[0] != 2 or payload[1] & ~MASK_ALL or payload[3] & 0xE0:
        raise AuditError("Envelope-v5 payload header differs")
    stage = payload[3] & 7
    complete = bool(payload[3] & 8)
    ambiguous = bool(payload[3] & 16)
    if stage > 5 or complete != (stage == 5):
        raise AuditError("Envelope-v5 chain encoding differs")
    modules = [struct.unpack_from("<h", payload, 4 + index * 2)[0] for index in range(3)]
    if modules != [0, 0, 0] or payload[2] & 0x38 != 0x38:
        raise AuditError("Envelope-v5 module tuple differs")
    counts = list(payload[10:15])
    status_values = list(payload[15:20])
    parent = payload[20]
    irqs = [struct.unpack_from("<H", payload, 21 + index * 2)[0] for index in range(5)]
    class_index = struct.unpack_from("<Q", payload, 31)[0]
    name_digest = payload[39:55]
    record_count = struct.unpack_from("<H", payload, 55)[0]
    record_bytes = int.from_bytes(payload[57:60], "little")
    first = struct.unpack_from("<Q", payload, 60)[0]
    last = struct.unpack_from("<Q", payload, 68)[0]
    validity = payload[2]
    if record_count > MAX_RECORDS or record_bytes > MAX_RECORD_BYTES:
        raise AuditError("Envelope-v5 record accounting exceeds boundary")
    if record_count == 0:
        if validity & 3 or first or last or record_bytes:
            raise AuditError("Envelope-v5 empty sequence is noncanonical")
    elif (validity & 3 != 3 or record_bytes < record_count
          or last < first or last - first + 1 != record_count):
        raise AuditError("Envelope-v5 sequence accounting differs")
    if bool(validity & VALID_PARENT_MASK) != (counts[4] != 0) or (counts[4] == 0 and parent):
        raise AuditError("Envelope-v5 parent-mask validity differs")
    if bool(validity & VALID_INITIAL_STATUS) != (counts[2] != 0) or (counts[2] == 0 and any(status_values)):
        raise AuditError("Envelope-v5 initial-status validity differs")
    if counts[1] == 0 and any(irqs):
        raise AuditError("Envelope-v5 absent IRQ tuple has data")
    if bool(validity & VALID_CLASSIFICATION) != (counts[3] != 0):
        raise AuditError("Envelope-v5 classification validity differs")
    if counts[3] == 0 and (class_index or any(name_digest)):
        raise AuditError("Envelope-v5 absent classification has data")
    derived_mask = 0
    for count, bit in zip(counts, (MASK_PROBE, MASK_IRQ, MASK_INITIAL, MASK_CLASS1, MASK_PARENT)):
        if count:
            derived_mask |= bit
    if payload[1] & (MASK_PROBE | MASK_IRQ | MASK_INITIAL | MASK_CLASS1 | MASK_PARENT) != derived_mask:
        raise AuditError("Envelope-v5 primary mask differs from counts")
    if any((
        stage >= 1 and not counts[1], stage >= 2 and not counts[2],
        stage >= 3 and not counts[3], stage >= 4 and not counts[4],
        stage >= 5 and not counts[0],
    )):
        raise AuditError("Envelope-v5 chain stage lacks its preceding witness")
    return {
        "terminal_code": terminal_code, "mux_code": mux_code,
        "observer_site_code": observer_site,
        "observer_error_class": observer_error,
        "result_header_present": result_present,
        "fixed_result_header": fixed_result,
        "result_raw_byte_count": raw_size,
        "causal_result_allowed": False,
        "causal_result_denial": "v5_omits_v4_poll_timing_and_banner_payload",
        "witness_mask": payload[1], "validity": validity,
        "chain_stage": stage, "chain_complete": complete,
        "chain_ambiguous": ambiguous, "module_results": modules,
        "counts": counts, "initial_status": status_values,
        "parent_mask_readback": parent, "irq": irqs,
        "classification_form1_index": class_index,
        "classification_name_sha256_prefix128": name_digest.hex(),
        "record_count": record_count, "record_bytes": record_bytes,
        "first_sequence": first, "last_sequence": last,
    }


def sample_state() -> dict[str, Any]:
    return {
        "witness_mask": MASK_ALL,
        "probe_count": 1, "irq_count": 1, "initial_status_count": 1,
        "classification_form1_count": 1, "classification_form2_count": 1,
        "deferred_status_count": 1, "parent_mask_count": 1,
        "initial_status": [0x27, 0x05, 0x82, 0x01, 0x08],
        "parent_mask_readback": 0x07,
        "irq": [355, 354, 352, 351, 350],
        "classification_form1_index": 9,
        "classification_form1_name": "CDP",
        "record_count": 5, "record_bytes": 777,
        "first_sequence": 100, "last_sequence": 104,
        "first_sequence_valid": True, "last_sequence_valid": True,
        "chain_stage": 5, "chain_complete": True, "chain_ambiguous": False,
        "module_results": [0, 0, 0],
    }


def qualify_python_codec() -> dict[str, Any]:
    state = sample_state()
    payload = encode_payload_v5(state)
    envelope = bytearray(ENVELOPE_SIZE)
    envelope[:5] = b"MXD5\x05"
    envelope[5] = 1
    envelope[7] = V5_WITNESS_FLAG | 0x14
    envelope[43] = V5_ENCODING
    envelope[46] = PAYLOAD_SIZE
    envelope[PAYLOAD_OFFSET:CRC_OFFSET] = payload
    envelope[CRC_OFFSET:] = struct.pack("<I", zlib.crc32(V5_DOMAIN + envelope[:CRC_OFFSET]) & 0xFFFFFFFF)
    decoded = decode_envelope_v5(bytes(envelope))
    if decoded["initial_status"] != state["initial_status"] or decoded["parent_mask_readback"] != 7:
        raise AuditError("Envelope-v5 Python round trip differs")
    for offset in (0, 4, 7, 43, 46, 48, 50, 51, 58, 123, 124):
        mutated = bytearray(envelope)
        mutated[offset] ^= 1
        try:
            decode_envelope_v5(bytes(mutated))
        except AuditError:
            continue
        raise AuditError(f"Envelope-v5 mutation accepted at offset {offset}")
    return {
        "payload_size": len(payload), "envelope_size": len(envelope),
        "split_first_bytes": 64, "split_second_bytes": 64,
        "round_trip": True, "mutation_count": 11,
        "classification_name_digest_bits": 128,
        "codec": decoded,
    }


def _sha_source_chunk(runtime: bytes) -> bytes:
    struct_start = runtime.index(b"struct s22plus_max77705_runtime_sha256 {")
    struct_end = runtime.index(b"\n};", struct_start) + 3
    functions_start = runtime.index(
        b"static uint32_t s22plus_max77705_runtime_rotr", struct_end
    )
    functions_end = runtime.index(
        b"static int s22plus_max77705_runtime_active_timeout_slot",
        functions_start,
    )
    return runtime[struct_start:struct_end] + b"\n\n" + runtime[functions_start:functions_end]


def qualify_native_parser(module: Any, runtime: bytes) -> dict[str, Any]:
    compiler = module.shutil_which("gcc")
    if compiler is None:
        raise AuditError("host C compiler unavailable for P3.19 parser")
    parser_source = module._generated_parser_source(runtime).decode("ascii")
    with tempfile.TemporaryDirectory(prefix="p319-carrier-v5-parser-") as directory:
        root = Path(directory)
        source = root / "fixture.c"
        source.write_text(
            "#include <stdint.h>\n#include <stddef.h>\n#include <string.h>\n#include <stdio.h>\n#include <limits.h>\n"
            "static size_t cstr_len(const char*s){return strlen(s);} static int p260_bytes_equal(const char*a,const char*b,size_t n){return memcmp(a,b,n)==0;}\n"
            "struct p303_kmsg_capture { int fd; uint8_t started; uint8_t final; uint8_t path_seen; uint8_t reset_mask; uint8_t sequence_seen; uint32_t readback_count; uint32_t first_offset; uint64_t previous_sequence; uint64_t first_sequence; uint64_t record_count; uint64_t record_bytes; uint32_t drain_count; uint32_t module_count; uint32_t module_drain_count; uint32_t drain_record_count; uint32_t drain_bytes; }; static struct p303_kmsg_capture g_p303_kmsg;\n"
            + parser_source +
            "static void prepare(void){p319_note_successful_module(69,0,\"i2c-msm-geni.ko\");g_p319_witness.active_module_valid=0;p319_note_successful_module(71,0,\"mfd_max77705.ko\");g_p319_witness.active_module_valid=0;p319_note_successful_module(72,0,\"pdic_max77705.ko\");g_p303_kmsg.module_count=73;g_p303_kmsg.module_drain_count=73;g_p303_kmsg.drain_count=74;g_p303_kmsg.record_count=5;g_p303_kmsg.record_bytes=777;g_p303_kmsg.first_sequence=100;g_p303_kmsg.previous_sequence=104;g_p303_kmsg.sequence_seen=1;}\n"
            "int main(int argc,char**argv){if(argc<3)return 3;prepare();for(int i=2;i<argc;++i){long rc=p319_witness_observe_v2(argv[i],strlen(argv[i]));if(rc!=0)return 2;}if(strcmp(argv[1],\"freeze\")==0){g_p319_witness.active_module_valid=0;const char*later=\"max77705: max77705_usbc_umask_irq: P319_INTSRC_MASK:0x0f\";if(p319_witness_observe_v2(later,strlen(later))!=0)return 4;}struct p319_witness_summary_state_v2 s;if(p319_witness_summary_state_v2_copy(&s)!=0)return 5;printf(\"CHAIN %u %u %u STATUS %u %u %u %u %u PARENT %u COUNTS %u %u %u %u %u MASK %u\\n\",s.initial_chain_stage,s.initial_chain_complete,s.initial_chain_ambiguous,s.initial_status[0],s.initial_status[1],s.initial_status[2],s.initial_status[3],s.initial_status[4],s.parent_mask_readback,s.probe_count,s.irq_count,s.initial_status_count,s.classification_form1_count,s.parent_mask_count,s.witness_mask);return 0;}\n",
            encoding="ascii",
        )
        binary = root / "fixture"
        compiled = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(binary), str(source)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if compiled.returncode != 0:
            detail = (compiled.stdout + compiled.stderr).decode("utf-8", "replace")
            raise AuditError(f"native P3.19 parser compile failed: {detail[-5000:]}")
        chain = (
            "pdic_max77705: max77705_muic_irq_init uiadc(355), chgtyp(354), dcdtmo(352), vbadc(351), vbusdet(350)",
            "pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82, CC0:0x01, CC1:0x08",
            "pdic_max77705: max77705_muic_check_new_dev vps table match found at i(9), CDP",
            "max77705: max77705_usbc_umask_irq: P319_INTSRC_MASK:0x07",
            "max77705: max77705_usbc_probe: probing Complete..",
        )
        accepted = subprocess.run(
            [str(binary), "chain", *chain], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False,
        )
        expected = "CHAIN 5 1 0 STATUS 39 5 130 1 8 PARENT 7 COUNTS 1 1 1 1 1 MASK 79\n"
        if accepted.returncode != 0 or accepted.stdout != expected:
            raise AuditError(f"native P3.19 chain differs: {accepted.stdout}{accepted.stderr}")
        frozen = subprocess.run(
            [str(binary), "freeze", *chain], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False,
        )
        expected_frozen = expected.replace("CHAIN 5 1 0", "CHAIN 5 1 1")
        if frozen.returncode != 0 or frozen.stdout != expected_frozen:
            raise AuditError(f"native P3.19 freeze differs: {frozen.stdout}{frozen.stderr}")
        wrong_order = subprocess.run(
            [str(binary), "wrong", chain[1], chain[0]], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False,
        )
        if wrong_order.returncode != 0 or not wrong_order.stdout.startswith("CHAIN 1 0 1"):
            raise AuditError(f"native P3.19 wrong order accepted: {wrong_order.stdout}")
        malformed = (
            "pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82",
            "pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82, CC0:0x1, CC1:0x08",
            "max77705: max77705_usbc_umask_irq: P319_INTSRC_MASK:0x7",
            "max77705: max77705_usbc_umask_irq: P319_INTSRC_MASK:0X07",
        )
        for value in malformed:
            rejected = subprocess.run(
                [str(binary), "negative", value], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
            if rejected.returncode == 0:
                raise AuditError(f"native P3.19 parser accepted malformed input: {value}")
    return {
        "compiler": Path(compiler).name, "compiled": True, "executed": True,
        "five_byte_status_positive": True, "parent_mask_positive": True,
        "row72_chain_stage": 5, "row72_chain_complete": True,
        "post_complete_primary_value_frozen": True,
        "post_complete_repeat_marks_ambiguous": True,
        "wrong_order_marks_ambiguous": True,
        "malformed_negative_count": len(malformed),
    }


def qualify_native_encoder(module: Any, runtime: bytes) -> dict[str, Any]:
    compiler = module.shutil_which("gcc")
    if compiler is None:
        raise AuditError("host C compiler unavailable")
    v5_start = runtime.index(b"/* P3.19 canonical structured-witness envelope v5. */")
    v5_end = runtime.index(b"/* P3.17 boot-specific executability witness. */", v5_start)
    v5_source = runtime[v5_start:v5_end].decode("ascii")
    sha_source = _sha_source_chunk(runtime).decode("ascii")
    state = sample_state()
    expected_payload = encode_payload_v5(state)
    with tempfile.TemporaryDirectory(prefix="p319-carrier-v5-native-") as directory:
        root = Path(directory)
        source = root / "fixture.c"
        source.write_text(
            "#include <stdint.h>\n#include <stddef.h>\n#include <string.h>\n#include <stdio.h>\n#include <limits.h>\n"
            "#define S22PLUS_MAX77705_ENVELOPE_SIZE 128U\n#define S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET 124U\n#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET 48U\n#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_SIZE 76U\n"
            "#define S22PLUS_MAX77705_FLAG_RESULT_PRESENT (1U<<0U)\n#define S22PLUS_MAX77705_FLAG_POLL_OVERFLOW (1U<<1U)\n#define S22PLUS_MAX77705_FLAG_BINDING_PRESENT (1U<<2U)\n#define S22PLUS_MAX77705_FLAG_POLL_LOSSLESS (1U<<3U)\n#define S22PLUS_MAX77705_P317_FLAG_EXEC_PRESENT (1U<<4U)\n"
            "#define S22PLUS_MAX77705_SEMANTIC_TERMINAL 1U\n#define S22PLUS_MAX77705_B_DETAIL_BASE 0x6701U\n"
            "#define P319_WITNESS_ABI_VERSION 2U\n#define P319_KMSG_MAX_MODULES 73U\n#define P319_KMSG_MAX_TOTAL_RECORDS 4096U\n#define P319_KMSG_MAX_TOTAL_BYTES 1048576ULL\n"
            "#define P319_WITNESS_MASK_PROBE (1U<<0U)\n#define P319_WITNESS_MASK_IRQ (1U<<1U)\n#define P319_WITNESS_MASK_INITIAL (1U<<2U)\n#define P319_WITNESS_MASK_CLASS1 (1U<<3U)\n#define P319_WITNESS_MASK_CLASS2 (1U<<4U)\n#define P319_WITNESS_MASK_DEFERRED (1U<<5U)\n#define P319_WITNESS_MASK_PARENT (1U<<6U)\n"
            "struct s22plus_max77705_binding_witness { int x; }; struct s22plus_max77705_p317_exec_witness { int x; }; struct s22plus_max77705_runtime_result { int x; }; struct s22plus_max77705_runtime_poll_summary { int x; }; struct s22plus_max77705_p318_latch_snapshot { int x; }; struct s22plus_p318_banner_result { int x; };\n"
            "struct p319_module_result_state_v1 { uint32_t index; int32_t result; uint8_t name_length; uint8_t valid; char name[64]; };\n"
            "struct p319_witness_summary_state_v2 { uint32_t abi_version; uint32_t witness_mask; uint32_t probe_count; uint32_t irq_count; uint32_t initial_status_count; uint32_t parent_mask_count; uint32_t classification_form1_count; uint32_t classification_form2_count; uint32_t deferred_status_count; uint32_t malformed_count; uint64_t classification_form1_index; uint64_t classification_form2_index; int32_t classification_form2_attached_dev; uint8_t classification_form1_name_length; uint8_t classification_form2_name_length; char classification_form1_name[64]; char classification_form2_name[64]; uint32_t module_loads; uint32_t module_drains; uint32_t drains; uint32_t initial_status[5]; uint32_t parent_mask_readback; int32_t irq[5]; uint64_t record_count; uint64_t record_bytes; uint64_t first_sequence; uint64_t last_sequence; uint8_t first_sequence_valid; uint8_t last_sequence_valid; uint8_t active_module_valid; uint8_t initial_chain_stage; uint8_t initial_chain_complete; uint8_t initial_chain_ambiguous; uint32_t active_module_index; uint32_t initial_chain_module_index; struct p319_module_result_state_v1 target_modules[3]; };\n"
            "static size_t cstr_len(const char *s){return strlen(s);} static int p260_bytes_equal(const char*a,const char*b,size_t n){return memcmp(a,b,n)==0;} static void s22plus_max77705_envelope_copy(uint8_t*d,const uint8_t*s,size_t n){memcpy(d,s,n);}\n"
            "static uint32_t s22plus_max77705_envelope_crc_update(uint32_t crc,const uint8_t*data,size_t size){for(size_t i=0;i<size;++i){crc^=data[i];for(unsigned int b=0;b<8;++b){uint32_t m=0U-(crc&1U);crc=(crc>>1U)^(0xedb88320U&m);}}return crc;}\n"
            "static void s22plus_max77705_store_le16(uint8_t*o,uint16_t v){o[0]=(uint8_t)v;o[1]=(uint8_t)(v>>8U);} static void s22plus_max77705_store_le32(uint8_t*o,uint32_t v){o[0]=(uint8_t)v;o[1]=(uint8_t)(v>>8U);o[2]=(uint8_t)(v>>16U);o[3]=(uint8_t)(v>>24U);}\n"
            + sha_source +
            "static int s22plus_max77705_p318_encode_envelope(const struct s22plus_max77705_binding_witness*b,const struct s22plus_max77705_p317_exec_witness*e,unsigned int sk,unsigned int sc,unsigned int os,unsigned int oe,const struct s22plus_max77705_runtime_result*r,const struct s22plus_max77705_runtime_poll_summary*s,const struct s22plus_max77705_p318_latch_snapshot*l,const struct s22plus_p318_banner_result*bn,uint8_t out[128],uint16_t*d){(void)b;(void)e;(void)sk;(void)sc;(void)os;(void)oe;(void)r;(void)s;(void)l;(void)bn;memset(out,0,128);memcpy(out,\"MXD4\",4);out[4]=4;out[5]=9;out[7]=0x1e;out[43]=1;out[46]=29;*d=0x6709;return 0;}\n"
            + v5_source +
            "static void set_module(struct p319_module_result_state_v1*m,uint32_t i,const char*n){m->index=i;m->result=0;m->valid=1;m->name_length=(uint8_t)strlen(n);memcpy(m->name,n,m->name_length);}\n"
            "static void init_state(struct p319_witness_summary_state_v2*w){memset(w,0,sizeof(*w));w->abi_version=2;w->witness_mask=0x7f;w->probe_count=w->irq_count=w->initial_status_count=w->parent_mask_count=w->classification_form1_count=w->classification_form2_count=w->deferred_status_count=1;uint32_t st[5]={0x27,5,0x82,1,8};int32_t irq[5]={355,354,352,351,350};memcpy(w->initial_status,st,sizeof(st));memcpy(w->irq,irq,sizeof(irq));w->parent_mask_readback=7;w->classification_form1_index=9;w->classification_form1_name_length=3;memcpy(w->classification_form1_name,\"CDP\",3);w->module_loads=w->module_drains=73;w->record_count=5;w->record_bytes=777;w->first_sequence=100;w->last_sequence=104;w->first_sequence_valid=w->last_sequence_valid=1;w->initial_chain_stage=5;w->initial_chain_complete=1;w->initial_chain_module_index=72;set_module(&w->target_modules[0],69,\"i2c-msm-geni.ko\");set_module(&w->target_modules[1],71,\"mfd_max77705.ko\");set_module(&w->target_modules[2],72,\"pdic_max77705.ko\");}\n"
            "int main(int argc,char**argv){struct p319_witness_summary_state_v2 w;uint8_t e[128];uint16_t d=0;init_state(&w);int negative=argc==2;if(negative){if(strcmp(argv[1],\"module\")==0)w.target_modules[1].result=-1;else if(strcmp(argv[1],\"sequence\")==0)w.last_sequence=105;else if(strcmp(argv[1],\"irq\")==0){w.irq_count=0;w.witness_mask&=~P319_WITNESS_MASK_IRQ;}else if(strcmp(argv[1],\"status\")==0){w.initial_status_count=0;w.witness_mask&=~P319_WITNESS_MASK_INITIAL;}else if(strcmp(argv[1],\"parent\")==0){w.parent_mask_count=0;w.witness_mask&=~P319_WITNESS_MASK_PARENT;}else if(strcmp(argv[1],\"chain\")==0)w.initial_chain_stage=4;else if(strcmp(argv[1],\"limit\")==0)w.record_count=4097;else if(strcmp(argv[1],\"mask\")==0)w.witness_mask&=~P319_WITNESS_MASK_PARENT;else if(strcmp(argv[1],\"bytes\")==0)w.record_bytes=0;else if(strcmp(argv[1],\"incomplete-index\")==0){w.initial_chain_stage=4;w.initial_chain_complete=0;}else return 9;}int rc=s22plus_max77705_p319_encode_envelope_v5(NULL,NULL,1,1,0,0,NULL,NULL,NULL,NULL,&w,e,&d);if(negative)return rc!=0?0:5;if(rc!=0||d!=0x6701||e[5]!=1)return 2;if(fwrite(e,1,128,stdout)!=128)return 3;return 0;}\n",
            encoding="ascii",
        )
        binary = root / "fixture"
        compiled = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(binary), str(source)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if compiled.returncode != 0:
            detail = (compiled.stdout + compiled.stderr).decode("utf-8", "replace")
            raise AuditError(f"native Envelope-v5 fixture compile failed: {detail[-5000:]}")
        executed = subprocess.run([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if executed.returncode != 0 or len(executed.stdout) != ENVELOPE_SIZE:
            raise AuditError(f"native Envelope-v5 fixture failed: rc={executed.returncode}")
        envelope = executed.stdout
        negative_modes = (
            "module", "sequence", "irq", "status", "parent", "chain",
            "limit", "mask", "bytes", "incomplete-index",
        )
        for mode in negative_modes:
            rejected = subprocess.run(
                [str(binary), mode], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
            if rejected.returncode != 0 or rejected.stdout:
                raise AuditError(f"native Envelope-v5 accepted mutation: {mode}")
    decoded = decode_envelope_v5(envelope)
    if envelope[PAYLOAD_OFFSET:CRC_OFFSET] != expected_payload:
        raise AuditError("native and Python Envelope-v5 payloads differ")
    if envelope[:4] != b"MXD5" or len(envelope[:64]) != 64 or len(envelope[64:]) != 64:
        raise AuditError("native Envelope-v5 geometry differs")
    return {
        "compiler": Path(compiler).name, "compiled": True, "executed": True,
        "native_python_payload_byte_identical": True,
        "native_negative_mutations": len(negative_modes),
        "v4_poll_overflow_semantic_restored": True,
        "carrier_first_position_bytes": len(envelope[:64]),
        "carrier_second_position_bytes": len(envelope[64:]),
        "decoded": decoded,
    }


def build_result(inputs: dict[str, Any]) -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("unbound Carrier-v5 auditor cannot build receipt")
    module = inputs["module"]
    base = inputs["preserved_base"]
    generated = inputs["preserved_generated"]
    drivers = inputs["preserved_drivers"]
    if base != inputs["base"] or generated != inputs["generated"] or drivers != inputs["drivers"]:
        raise AuditError("preserved Carrier-v5 materialization differs")
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    runtime = generated[runtime_name]
    v4 = audit_v4_unchanged(module, base[runtime_name], runtime)
    producers = audit_driver_producers(inputs["preserved_originals"], drivers, module)
    with tempfile.TemporaryDirectory(prefix="p319-carrier-v5-syntax-") as directory:
        source_root = Path(directory)
        for name, payload in generated.items():
            (source_root / name).write_bytes(payload)
        syntax = module.syntax_compile(source_root)
    python_codec = qualify_python_codec()
    native_parser = qualify_native_parser(module, runtime)
    native_codec = qualify_native_encoder(module, runtime)
    if runtime.count(b"s22plus_max77705_p319_encode_envelope_v5(") != 2:
        raise AuditError("Envelope-v5 definition/call multiplicity differs")
    if runtime.count(b"s22plus_max77705_p318_encode_envelope(") != 2:
        raise AuditError("Envelope-v4 definition/delegation multiplicity differs")
    if runtime.count(b"p319_witness_summary_state_v2_copy(&witness)") != 1:
        raise AuditError("publisher summary copy differs")
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": "IMPLEMENTED_REVIEW_PENDING",
        "target": TARGET,
        "scope": {
            "tier": "H0", "host_only": True, "device_contact": False,
            "adb_commands": 0, "usb_actions": 0, "odin_invocations": 0,
            "candidate_builds": 0, "candidate_transfers": 0,
            "rollback_transfers": 0, "recovery_actions": 0,
            "replay": False, "live_authority_created": False,
        },
        "inputs": {
            "predecessor_auditor": identity(inputs["preserved_originals"]["predecessor-auditor.py"]),
            "predecessor_receipt": identity(inputs["preserved_originals"]["predecessor-result.json"]),
            "base_sources": {name: identity(payload) for name, payload in sorted(base.items())},
            "driver_sources": {
                name: identity(inputs["preserved_originals"][name])
                for name in ("max77705-muic.c", "max77705_usbc.c")
            },
        },
        "implementation": {
            "auditor": identity(_BOUND_AUDITOR_SOURCE),
            "materialized_sources": {name: identity(payload) for name, payload in sorted(generated.items())},
            "materialized_driver_sources": {name: identity(payload) for name, payload in sorted(drivers.items())},
            "driver_patches": {name: identity(payload) for name, payload in sorted(inputs["preserved_patches"].items())},
        },
        "envelope_v4": v4,
        "envelope_v5": {
            "envelope_size": ENVELOPE_SIZE, "payload_offset": PAYLOAD_OFFSET,
            "payload_size": PAYLOAD_SIZE, "crc_offset": CRC_OFFSET,
            "version": V5_VERSION, "crc_domain": V5_DOMAIN.decode("ascii"),
            "encoding": V5_ENCODING, "witness_flag": V5_WITNESS_FLAG,
            "payload_abi": 2, "carrier_positions": [105, 106],
            "carrier_split_bytes": [64, 64],
            "poll_flags_cleared": True,
            "fixed_result_header_validated": True,
            "poll_bytes_retained": False,
            "decoded_causal_result_allowed": False,
            "v4_timing_banner_and_poll_payload_inherited": False,
            "v4_causal_timing_authority_created": False,
            "classification_name_digest": "sha256-prefix-128",
            "module_result_rows": [69, 71, 72],
            "module_load_and_drain_gate": MODULE_COUNT,
            "record_count_limit": MAX_RECORDS,
            "record_byte_limit": MAX_RECORD_BYTES,
        },
        "producer_changes": producers,
        "static_validation": syntax,
        "python_codec_qualification": python_codec,
        "native_parser_qualification": native_parser,
        "native_codec_qualification": native_codec,
        "conclusion": {
            "canonical_carrier_encoding_defined": True,
            "structured_witness_published_by_generated_runtime": True,
            "five_byte_initial_status_has_source_producer": True,
            "parent_0x23_bit3_readback_has_source_producer": True,
            "parent_readback_is_one_new_future_i2c_read": True,
            "driver_sources_only_not_compiled_module_bytes": True,
            "candidate_build_exists": False,
            "existing_candidate_witness_transport_obligation_resolved": False,
            "independent_changed_closure_review_required": True,
            "no_device_or_live_authority": True,
            "next_step": "independent H0 changed-closure review before any candidate build",
        },
    }
    if stable_bytes(AUDITOR, label="post-run Carrier-v5 auditor", maximum=256 << 10) != _BOUND_AUDITOR_SOURCE:
        raise AuditError("Carrier-v5 auditor changed during execution")
    return result


def encode_result(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def run(materialize: bool, output_root: Path = OUTPUT_ROOT) -> tuple[dict[str, Any], bytes]:
    inputs = load_inputs(materialize, output_root)
    result = build_result(inputs)
    return result, encode_result(result)


def publish_result(root: Path, payload: bytes) -> None:
    path = _paths(root.absolute())["result"]
    _write_exclusive(path, payload)
    _fsync_directory(root.absolute())
    stable_bytes(
        path, label="Carrier-v5 result receipt", maximum=128 << 10,
        expected_size=len(payload), expected_sha256=sha256(payload),
        required_mode=0o400, required_nlink=1,
    )


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="Carrier-v5 auditor bootstrap", maximum=256 << 10)
    module = types.ModuleType("s22plus_fyg8_p319_candidate_witness_carrier_v5_bound")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P319_CARRIER_V5_BOUND_SOURCE"] = payload
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("Carrier-v5 auditor bound execution failed") from exc
    return module


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--audit-only", action="store_true")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    root = args.output_root.absolute()
    _, payload = run(args.write, root)
    if args.write:
        publish_result(root, payload)
    else:
        existing = stable_bytes(
            _paths(root)["result"], label="Carrier-v5 result receipt",
            maximum=128 << 10, expected_size=len(payload),
            expected_sha256=sha256(payload), required_mode=0o400,
            required_nlink=1,
        )
        if existing != payload:
            raise AuditError("Carrier-v5 receipt bytes differ")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
