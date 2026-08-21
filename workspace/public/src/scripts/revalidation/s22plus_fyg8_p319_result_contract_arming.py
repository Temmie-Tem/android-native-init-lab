#!/usr/bin/env python3
"""Host-only arming auditor for the P3.19 stock result contract.

This module executes the exact stock-emitter C encoder from the bound P3.19
candidate source in a temporary native fixture.  It deliberately does not
load or contact a device, build a boot artifact, or grant Process-v2
authority.  The caller receives the emitted envelopes so the adapter can put
those bytes through the real Carrier encoder and decoder.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
BOUND_RUNTIME_RELATIVE = (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-49/stock-sources/"
    "s22plus_fyg8_p290_e3_runtime.inc.c"
)
BOUND_RUNTIME_SIZE = 435_334
BOUND_RUNTIME_SHA256 = "0a12a9c0f148d58009ebc378b667733b5913d46ebf6466dff3f37bbb850c51a9"
RUNTIME_MARKER = "/* P3.19 stock-emitter envelope"
PUBLISHER_SYMBOL = "p319_stock_publish"
ENCODER_SYMBOL = "s22plus_max77705_p319_stock_encode"
ENVELOPE_SIZE = 128
STATE_COUNT = 3
DETAIL_BY_STATE = {0: 0x6724, 1: 0x6725, 2: 0x6726}
PINNED_COMPILER_REALPATH = "/usr/bin/x86_64-linux-gnu-gcc-15"
PINNED_COMPILER_SIZE = 1_305_304
PINNED_COMPILER_SHA256 = (
    "b5f1b773a7c733738352000c92a077dc5852a1a2fc6d836b1e411be1e9ec5f88"
)
PINNED_COMPILER_VERSION_SHA256 = (
    "60f7dc07ed00e918c903d995b6f86bfcd5452856f75f2816cc8ca379ce2b5344"
)


class ArmingError(ValueError):
    """The bound C encoder or its publisher-state harness failed closed."""


_C_HEADER = r'''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

#define S22PLUS_MAX77705_ENVELOPE_SIZE 128U
#define S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET 124U
#define S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET 48U
#define S22PLUS_MAX77705_P319_WITNESS_FLAG (1U << 5U)
#define S22PLUS_MAX77705_P319_PAYLOAD_USED 76U
#define S22PLUS_MAX77705_P319_STOCK_ENCODING 4U
#define S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH 3U
#define S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI 3U
#define S22PLUS_MAX77705_P319_VALID_MODULE69 (1U << 3U)
#define S22PLUS_MAX77705_P319_VALID_MODULE71 (1U << 4U)
#define S22PLUS_MAX77705_P319_VALID_MODULE72 (1U << 5U)
#define S22PLUS_MAX77705_P319_VALID_INITIAL (1U << 6U)
#define S22PLUS_MAX77705_P319_VALID_CLASS1 (1U << 7U)
#define P319_WITNESS_ABI_VERSION 2U
#define P319_WITNESS_MASK_PROBE (1U << 0U)
#define P319_WITNESS_MASK_IRQ (1U << 1U)
#define P319_WITNESS_MASK_INITIAL (1U << 2U)
#define P319_WITNESS_MASK_CLASS1 (1U << 3U)
#define P319_WITNESS_MASK_CLASS2 (1U << 4U)
#define P319_WITNESS_MASK_DEFERRED (1U << 5U)
#define P319_WITNESS_MASK_PARENT (1U << 6U)
#define P319_KMSG_MAX_MODULES 73U
#define P319_KMSG_MAX_TOTAL_RECORDS 4096U
#define P319_KMSG_MAX_TOTAL_BYTES 1048576ULL

static size_t cstr_len(const char *s) { return strlen(s); }
static int p260_bytes_equal(const char *a, const char *b, size_t n) {
    return memcmp(a, b, n) == 0;
}
static uint32_t s22plus_max77705_envelope_crc_update(
        uint32_t c, const uint8_t *d, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        c ^= d[i];
        for (unsigned int b = 0; b < 8U; ++b)
            c = (c >> 1) ^ (0xedb88320U & (0U - (c & 1U)));
    }
    return c;
}
static void s22plus_max77705_store_le16(uint8_t *o, uint16_t v) {
    o[0] = v; o[1] = v >> 8;
}
static void s22plus_max77705_store_le32(uint8_t *o, uint32_t v) {
    o[0] = v; o[1] = v >> 8; o[2] = v >> 16; o[3] = v >> 24;
}
static void s22plus_max77705_p319_store_le24(uint8_t *o, uint32_t v) {
    o[0] = v; o[1] = v >> 8; o[2] = v >> 16;
}
static void s22plus_max77705_p319_store_le64(uint8_t *o, uint64_t v) {
    for (unsigned int i = 0; i < 8U; ++i) o[i] = v >> (i * 8U);
}

struct p319_module_result_state_v1 {
    uint32_t index;
    int32_t result;
    uint8_t name_length;
    uint8_t valid;
    char name[64];
};
struct p319_witness_summary_state_v2 {
    uint32_t abi_version, witness_mask, probe_count, irq_count;
    uint32_t initial_status_count, parent_mask_count;
    uint32_t classification_form1_count, classification_form2_count;
    uint32_t deferred_status_count, malformed_count;
    uint64_t classification_form1_index, classification_form2_index;
    int32_t classification_form2_attached_dev;
    uint8_t classification_form1_name_length, classification_form2_name_length;
    char classification_form1_name[64], classification_form2_name[64];
    uint32_t module_loads, module_drains, drains, initial_status[5];
    uint32_t parent_mask_readback;
    int32_t irq[5];
    uint64_t record_count, record_bytes, first_sequence, last_sequence;
    uint8_t first_sequence_valid, last_sequence_valid, active_module_valid;
    uint8_t initial_chain_stage, initial_chain_complete, initial_chain_ambiguous;
    uint32_t active_module_index, initial_chain_module_index;
    struct p319_module_result_state_v1 target_modules[3];
};
'''


_C_MAIN = r'''
static void fill_fixture(struct p319_witness_summary_state_v2 *w,
                         uint8_t state) {
    static const char *names[3] = {
        "i2c-msm-geni.ko", "mfd_max77705.ko", "pdic_max77705.ko"
    };
    static const uint32_t indexes[3] = {69U, 71U, 72U};
    memset(w, 0, sizeof(*w));
    w->abi_version = P319_WITNESS_ABI_VERSION;
    w->module_loads = P319_KMSG_MAX_MODULES;
    w->module_drains = P319_KMSG_MAX_MODULES;
    w->witness_mask = P319_WITNESS_MASK_PROBE |
        P319_WITNESS_MASK_IRQ | P319_WITNESS_MASK_INITIAL |
        P319_WITNESS_MASK_CLASS1;
    w->probe_count = 1U;
    w->irq_count = 1U;
    w->initial_status_count = 1U;
    w->classification_form1_count = 1U;
    w->initial_status[0] = 0x27U;
    w->initial_status[1] = 5U;
    w->initial_status[2] = 0x82U;
    w->irq[0] = 22;
    w->irq[1] = 23;
    w->irq[2] = 26;
    w->classification_form1_index = 7U;
    w->record_count = 1U;
    w->record_bytes = 1U;
    w->first_sequence = 1U;
    w->last_sequence = 1U;
    w->first_sequence_valid = 1U;
    w->last_sequence_valid = 1U;
    w->initial_chain_stage = state == 0U ? 4U : 3U;
    w->initial_chain_complete = state == 0U ? 1U : 0U;
    w->initial_chain_ambiguous = state == 2U ? 1U : 0U;
    w->initial_chain_module_index = state == 0U ? 72U : 0U;
    for (unsigned int i = 0U; i < 3U; ++i) {
        w->target_modules[i].index = indexes[i];
        w->target_modules[i].result = 0;
        w->target_modules[i].name_length = (uint8_t)strlen(names[i]);
        w->target_modules[i].valid = 1U;
        memcpy(w->target_modules[i].name, names[i],
               w->target_modules[i].name_length);
    }
}

static int emit_state(uint8_t state) {
    struct p319_witness_summary_state_v2 witness;
    uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
    uint16_t detail = 0U;
    uint8_t terminal_state;
    fill_fixture(&witness, state);
    /* This is the exact selector used by p319_stock_publish. */
    terminal_state = witness.initial_chain_ambiguous != 0U ? 2U
        : (witness.initial_chain_complete != 0U ? 0U : 1U);
    if (terminal_state != state ||
        s22plus_max77705_p319_stock_encode(
            &witness, terminal_state, envelope, &detail) != 0 ||
        detail != (uint16_t)(state == 0U ? 0x6724U
            : (state == 1U ? 0x6725U : 0x6726U))) return 10;
    if (fwrite(&terminal_state, 1U, 1U, stdout) != 1U ||
        fwrite(&detail, sizeof(detail), 1U, stdout) != 1U ||
        fwrite(envelope, 1U, sizeof(envelope), stdout) != sizeof(envelope))
        return 11;
    return 0;
}

static int reject_impossible_direct_state_combinations(void) {
    struct p319_witness_summary_state_v2 witness;
    uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
    uint16_t detail = 0U;
    fill_fixture(&witness, 0U);
    if (s22plus_max77705_p319_stock_encode(
            &witness, 1U, envelope, &detail) == 0) return 20;
    if (s22plus_max77705_p319_stock_encode(
            &witness, 2U, envelope, &detail) == 0) return 21;
    fill_fixture(&witness, 1U);
    if (s22plus_max77705_p319_stock_encode(
            &witness, 0U, envelope, &detail) == 0) return 22;
    fill_fixture(&witness, 1U);
    if (s22plus_max77705_p319_stock_encode(
            &witness, 2U, envelope, &detail) == 0) return 23;
    return 0;
}

static int prove_ambiguous_direct_combinations(uint8_t flags[4]) {
    struct p319_witness_summary_state_v2 witness;
    uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
    uint16_t detail = 0U;
    uint8_t selected_state;
    int direct_rc;
    int selected_rc;

    fill_fixture(&witness, 1U);
    witness.initial_chain_ambiguous = 1U;
    selected_state = witness.initial_chain_ambiguous != 0U ? 2U
        : (witness.initial_chain_complete != 0U ? 0U : 1U);
    if (selected_state != 2U) return 30;
    direct_rc = s22plus_max77705_p319_stock_encode(
        &witness, 1U, envelope, &detail);
    flags[0] = direct_rc == 0 ? 1U : 0U;
    selected_rc = s22plus_max77705_p319_stock_encode(
        &witness, selected_state, envelope, &detail);
    flags[1] = selected_rc == 0 ? 1U : 0U;

    fill_fixture(&witness, 0U);
    witness.initial_chain_ambiguous = 1U;
    selected_state = witness.initial_chain_ambiguous != 0U ? 2U
        : (witness.initial_chain_complete != 0U ? 0U : 1U);
    if (selected_state != 2U) return 31;
    direct_rc = s22plus_max77705_p319_stock_encode(
        &witness, 0U, envelope, &detail);
    flags[2] = direct_rc == 0 ? 1U : 0U;
    selected_rc = s22plus_max77705_p319_stock_encode(
        &witness, selected_state, envelope, &detail);
    flags[3] = selected_rc == 0 ? 1U : 0U;
    return 0;
}

int main(void) {
    for (uint8_t state = 0U; state < 3U; ++state) {
        int rc = emit_state(state);
        if (rc != 0) return rc;
    }
    if (reject_impossible_direct_state_combinations() != 0) return 40;
    uint8_t flags[4] = {0};
    if (prove_ambiguous_direct_combinations(flags) != 0) return 41;
    if (fwrite("URCH", 1U, 4U, stdout) != 4U ||
        fwrite(flags, 1U, sizeof(flags), stdout) != sizeof(flags)) return 42;
    return 0;
}
'''


def _bound_runtime_source(root: Path = ROOT) -> tuple[Path, bytes]:
    path = root / BOUND_RUNTIME_RELATIVE
    try:
        info = path.lstat()
    except OSError as exc:
        raise ArmingError("P3.19 bound C runtime source is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ArmingError("P3.19 bound C runtime source is not a regular file")
    data = path.read_bytes()
    if len(data) != BOUND_RUNTIME_SIZE or hashlib.sha256(data).hexdigest() != BOUND_RUNTIME_SHA256:
        raise ArmingError("P3.19 bound C runtime source identity differs")
    return path, data


def _function_span(source: str, symbol: str) -> tuple[int, int]:
    token = f"{symbol}("
    position = source.find(token)
    if position < 0:
        raise ArmingError(f"P3.19 bound C source lacks {symbol}")
    brace = source.find("{", position)
    if brace < 0:
        raise ArmingError(f"P3.19 bound C source lacks {symbol} body")
    start = source.rfind("\n", 0, position) + 1
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char in "\"'":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
        index += 1
    raise ArmingError(f"P3.19 bound C source has an unterminated {symbol}")


def _encoder_source(runtime: str) -> str:
    start = runtime.find(RUNTIME_MARKER)
    if start < 0:
        raise ArmingError("P3.19 bound C source lacks stock-emitter marker")
    publish_position = runtime.find(f"{PUBLISHER_SYMBOL}(", start)
    if publish_position < 0:
        raise ArmingError("P3.19 bound C source lacks stock publisher")
    publish_start, _ = _function_span(runtime, PUBLISHER_SYMBOL)
    if not start < publish_start:
        raise ArmingError("P3.19 bound C stock encoder range is inverted")
    block = runtime[start:publish_start]
    bypass_start, bypass_end = _function_span(block, "p319_stock_bypass_to_pair")
    block = block[:bypass_start] + block[bypass_end:]
    if f"{ENCODER_SYMBOL}(" not in block:
        raise ArmingError("P3.19 bound C stock encoder is outside the publisher range")
    if "s22plus_max77705_p319_encode_envelope_v5(" in block:
        raise ArmingError("P3.19 stock arming accidentally included diagnostic encoder")
    return block


def _verify_publisher_reachability(runtime: str) -> None:
    """Bind the three fixture states to the source's actual selector logic."""
    chain_start, chain_end = _function_span(runtime, "p319_chain_event")
    chain = runtime[chain_start:chain_end]
    for fragment in (
        "event == 1U && g_p319_witness.initial_chain_stage == 0U",
        "event == 2U && g_p319_witness.initial_chain_stage == 1U",
        "event == 3U && g_p319_witness.initial_chain_stage == 2U",
        "event == 5U && g_p319_witness.initial_chain_stage == 3U",
        "g_p319_witness.initial_chain_ambiguous = 1U",
    ):
        if fragment not in chain:
            raise ArmingError("P3.19 publisher chain-state source proof differs")
    note_start, note_end = _function_span(runtime, "p319_note_successful_module")
    note = runtime[note_start:note_end]
    if "result != 0" not in note or "target_modules[slot].valid" not in note:
        raise ArmingError("P3.19 publisher module-success source proof differs")
    observer_start, observer_end = _function_span(runtime, "p319_witness_observe_v2")
    observer = runtime[observer_start:observer_end]
    order = [
        "p319_observe_irq(message, length)",
        "p319_observe_initial(message, length)",
        "p319_observe_class1(message, length)",
        "p319_observe_probe(message, length)",
    ]
    positions = [observer.find(fragment) for fragment in order]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ArmingError("P3.19 publisher observer stage order differs")
    for symbol in ("p319_observe_class2", "p319_observe_deferred"):
        start, end = _function_span(runtime, symbol)
        if "p319_primary_witness_frozen" in runtime[start:end]:
            raise ArmingError("P3.19 auxiliary publisher path can mutate primary state")


def _compiler_identity(requested_name: str) -> tuple[str, dict[str, Any]]:
    compiler = shutil.which(requested_name)
    if compiler is None:
        raise ArmingError("P3.19 C compiler is unavailable for arming")
    try:
        realpath = Path(compiler).resolve(strict=True)
        if str(realpath) != PINNED_COMPILER_REALPATH:
            raise ArmingError(
                "P3.19 C compiler realpath is not the pinned qualification tool"
            )
        before = realpath.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise ArmingError("P3.19 resolved C compiler is not a regular file")
        compiler_bytes = realpath.read_bytes()
        after = realpath.lstat()
    except OSError as exc:
        raise ArmingError("P3.19 C compiler identity could not be read") from exc
    if (
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        raise ArmingError("P3.19 C compiler changed while being bound")
    compiler_sha256 = hashlib.sha256(compiler_bytes).hexdigest()
    if len(compiler_bytes) != PINNED_COMPILER_SIZE or compiler_sha256 != PINNED_COMPILER_SHA256:
        raise ArmingError("P3.19 C compiler byte identity differs from pinned qualification tool")
    try:
        version = subprocess.run(
            [str(realpath), "--version"],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ArmingError("P3.19 C compiler version query failed") from exc
    version_bytes = version.stdout + version.stderr
    if version.returncode != 0 or not version_bytes or len(version_bytes) > 64 * 1024:
        raise ArmingError("P3.19 C compiler version query failed")
    version_sha256 = hashlib.sha256(version_bytes).hexdigest()
    if version_sha256 != PINNED_COMPILER_VERSION_SHA256:
        raise ArmingError(
            "P3.19 C compiler version identity differs from pinned qualification tool"
        )
    return str(realpath), {
        "requested": requested_name,
        "realpath": str(realpath),
        "size": len(compiler_bytes),
        "sha256": compiler_sha256,
        "version": version_bytes.decode("utf-8", "replace"),
        "version_sha256": version_sha256,
    }


def _compile_and_execute(source: str) -> tuple[bytes, dict[str, Any]]:
    compiler_name = os.environ.get("CC", "cc")
    compiler, compiler_identity = _compiler_identity(compiler_name)
    with tempfile.TemporaryDirectory(prefix="p319-result-contract-c-") as directory:
        root = Path(directory)
        source_path = root / "arming.c"
        binary_path = root / "arming"
        source_path.write_text(_C_HEADER + source + _C_MAIN, encoding="utf-8")
        try:
            compiled = subprocess.run(
                [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", source_path, "-o", binary_path],
                capture_output=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ArmingError("P3.19 exact C stock encoder compile failed") from exc
        if compiled.returncode != 0:
            raise ArmingError(
                "P3.19 exact C stock encoder did not compile: "
                + compiled.stderr.decode("utf-8", "replace")[-4000:]
            )
        try:
            executed = subprocess.run(
                [binary_path], capture_output=True, check=False, timeout=10
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ArmingError("P3.19 exact C publisher-state harness failed") from exc
        if executed.returncode != 0:
            raise ArmingError(
                f"P3.19 exact C publisher-state harness failed ({executed.returncode})"
            )
        try:
            after = Path(compiler).read_bytes()
        except OSError as exc:
            raise ArmingError("P3.19 C compiler disappeared after execution") from exc
        if hashlib.sha256(after).hexdigest() != compiler_identity["sha256"]:
            raise ArmingError("P3.19 C compiler changed during arming")
        return executed.stdout, compiler_identity


def execute_actual_stock_encoder(root: Path = ROOT) -> dict[str, Any]:
    """Execute the bound C encoder for the publisher-reachable state set."""
    source_path, source_bytes = _bound_runtime_source(root)
    runtime = source_bytes.decode("utf-8")
    publisher_start, publisher_end = _function_span(runtime, PUBLISHER_SYMBOL)
    publisher = runtime[publisher_start:publisher_end]
    selector = (
        "terminal_state = witness.initial_chain_ambiguous != 0U ? 2U\n"
        "        : (witness.initial_chain_complete != 0U ? 0U : 1U);"
    )
    if selector not in publisher:
        raise ArmingError("P3.19 publisher terminal-state selector differs")
    _verify_publisher_reachability(runtime)
    encoder = _encoder_source(runtime)
    output, compiler_identity = _compile_and_execute(encoder)
    record_size = 1 + 2 + ENVELOPE_SIZE
    state_output_size = STATE_COUNT * record_size
    if len(output) != state_output_size + 8:
        raise ArmingError("P3.19 exact C encoder emitted an unexpected byte count")
    states: list[dict[str, Any]] = []
    seen: set[int] = set()
    for offset in range(0, state_output_size, record_size):
        state = output[offset]
        detail = struct.unpack_from("<H", output, offset + 1)[0]
        envelope = output[offset + 3:offset + record_size]
        if state not in DETAIL_BY_STATE or state in seen:
            raise ArmingError("P3.19 exact C encoder emitted an unsupported state")
        if detail != DETAIL_BY_STATE[state] or len(envelope) != ENVELOPE_SIZE:
            raise ArmingError("P3.19 exact C encoder state/detail mapping differs")
        seen.add(state)
        states.append({
            "publisher_terminal_state": state,
            "terminal_detail": detail,
            "envelope": envelope,
            "envelope_sha256": hashlib.sha256(envelope).hexdigest(),
        })
    if seen != set(DETAIL_BY_STATE):
        raise ArmingError("P3.19 exact C encoder did not cover publisher states")
    trailer = output[state_output_size:]
    if trailer[:4] != b"URCH" or len(trailer) != 8:
        raise ArmingError("P3.19 C arming unreachable-state proof trailer differs")
    flags = tuple(trailer[4:])
    if any(flag not in (0, 1) for flag in flags):
        raise ArmingError("P3.19 C arming unreachable-state proof flags differ")
    unreachable = {
        "INCOMPLETE_PLUS_AMBIGUOUS": {
            "direct_encoder_accepts_terminal_incomplete": bool(flags[0]),
            "publisher_selected_state": 2,
            "selected_encoder_accepts_terminal_ambiguous": bool(flags[1]),
            "publisher_unreachable": True,
        },
        "COMPLETE_PLUS_AMBIGUOUS": {
            "direct_encoder_accepts_terminal_complete": bool(flags[2]),
            "publisher_selected_state": 2,
            "selected_encoder_accepts_terminal_ambiguous": bool(flags[3]),
            "publisher_unreachable": True,
        },
    }
    return {
        "executed": True,
        "encoder": ENCODER_SYMBOL,
        "states": states,
        "publisher_selector_verified": True,
        "publisher_reachability_verified": True,
        "encoder_rejected_checked_mismatches": True,
        "publisher_selector_proves_unreachable": True,
        "publisher_unreachable_direct_combinations": unreachable,
        "compiler_identity": compiler_identity,
        "source_identity": {
            "path": BOUND_RUNTIME_RELATIVE,
            "size": len(source_bytes),
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
            "encoder_symbol": ENCODER_SYMBOL,
            "publisher_symbol": PUBLISHER_SYMBOL,
        },
    }
