#!/usr/bin/env python3
"""Execute the materialized P3.17 executability-witness seams on the host."""

from __future__ import annotations

import json
from pathlib import Path

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p317_generator as generator


SCHEMA = "s22plus_fyg8_p317_runtime_fixture_v1"
VERDICT = "PASS_P317_EXECUTABILITY_RUNTIME_FIXTURE_HOST_ONLY"


class FixtureError(ValueError):
    pass


def _generated(root: Path) -> bytes:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )["p290_e3_runtime_include"]


def _enum(source: bytes, marker: bytes) -> bytes:
    return support._struct(source, marker)  # noqa: SLF001


def _macro(source: bytes, name: bytes) -> bytes:
    marker = b"#define " + name + b" "
    start = source.find(marker)
    if start < 0 or source.find(marker, start + 1) >= 0:
        raise FixtureError(f"P3.17 macro differs: {name!r}")
    cursor = start
    while True:
        end = source.find(b"\n", cursor)
        if end < 0:
            raise FixtureError(f"P3.17 macro is unterminated: {name!r}")
        if source[cursor:end].rstrip().endswith(b"\\"):
            cursor = end + 1
            continue
        return source[start : end + 1]


def _provider_declarations(runtime: bytes) -> bytes:
    start = runtime.find(b"struct p317_provider_spec {")
    end = runtime.find(
        b"static struct s22plus_max77705_p317_exec_witness g_p317_exec;",
        start,
    )
    if start < 0 or end < 0 or runtime.find(b"struct p317_provider_spec {", start + 1) >= 0:
        raise FixtureError("P3.17 provider declarations differ")
    line_end = runtime.find(b"\n", end)
    if line_end < 0:
        raise FixtureError("P3.17 execution witness declaration is unterminated")
    return runtime[start : line_end + 1]


def _runtime_tu(runtime: bytes) -> bytes:
    macros = b"".join(
        _macro(runtime, name)
        for name in (
            b"S22PLUS_MAX77705_P317_POLICY_STATE_MASK",
            b"S22PLUS_MAX77705_P317_POLICY_GADGET_READY",
            b"S22PLUS_MAX77705_P317_POLICY_VALID",
            b"S22PLUS_MAX77705_P317_PROVIDER_MASK",
            b"S22PLUS_MAX77705_P317_PROVIDER_DUPLICATE_SHIFT",
            b"S22PLUS_MAX77705_P317_PROVIDER_VALID",
            b"S22PLUS_MAX77705_P317_WAITING_MASK",
            b"S22PLUS_MAX77705_P317_SUPPLIER_SHIFT",
            b"S22PLUS_MAX77705_P317_SUPPLIER_MASK",
            b"S22PLUS_MAX77705_P317_LINK_VALID",
            b"P317_PLATFORM_ROOT",
            b"P317_SPMI_ROOT",
            b"P317_PROVIDER_COUNT",
            b"P317_PROVIDER_MASK",
            b"P317_PROVIDER_SETTLE_POLLS",
            b"P317_PROVIDER_SETTLE_NS",
            b"P317_CMDLINE_CAPACITY",
            b"P317_SPMI_CONTROLLER_DT",
            b"P317_PMIC_DT",
            b"P317_GPIO_DT",
        )
    )
    declarations = b"".join(
        (
            _enum(runtime, b"enum s22plus_max77705_p317_policy_state {"),
            _enum(runtime, b"enum s22plus_max77705_p317_waiting_state {"),
            _enum(runtime, b"enum s22plus_max77705_p317_supplier_state {"),
            support._struct(  # noqa: SLF001
                runtime, b"struct s22plus_max77705_p317_exec_witness {"
            ),
            _provider_declarations(runtime),
        )
    )
    functions = b"".join(
        support._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static int s22plus_max77705_p317_provider_ready(",
            b"static int p317_path_suffix(",
            b"static long p317_join_path(",
            b"static long p317_expected_driver(",
            b"static long p317_scan_provider(",
            b"static long p317_provider_snapshot(",
            b"static int p317_provider_ready(",
            b"static long p317_capture_preclient_provider(",
            b"static int p317_token_prefix(",
            b"static long p317_capture_policy(",
            b"static long p317_capture_waiting(",
            b"static long p317_capture_supplier(",
            b"static long p317_capture_post_provider(",
        )
    )
    return (
        br'''
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#define P260_EOVERFLOW EOVERFLOW
#define S22_P241_DIRENT_BUFFER_SIZE 4096U
#define S22_P241_SYMLINK_TARGET_MAX 512U

struct s22_p241_kernel_stat { unsigned int st_mode; };
struct s22_p241_linux_dirent64 {
    uint64_t d_ino;
    int64_t d_off;
    uint16_t d_reclen;
    uint8_t d_type;
    char d_name[];
};

static size_t cstr_len(const char *value) { return strlen(value); }
static int p260_bytes_equal(const void *a, const void *b, size_t n) {
    return memcmp(a, b, n) == 0;
}
static long p282_copy_path_part(
    char *output, size_t capacity, size_t *cursor, const char *part) {
    size_t amount = strlen(part);
    if (*cursor + amount >= capacity) return -EOVERFLOW;
    memcpy(output + *cursor, part, amount + 1U);
    *cursor += amount;
    return 0;
}
static int p241_basename_equals(
    const char *path, size_t length, const char *expected) {
    const char *start = path;
    for (size_t index = 0U; index < length; ++index)
        if (path[index] == '/') start = path + index + 1U;
    size_t offset = (size_t)(start - path);
    return length - offset == strlen(expected)
        && memcmp(start, expected, strlen(expected)) == 0;
}
static int p316_name_has_prefix(
    const char *value, size_t length, const char *prefix) {
    size_t prefix_length = strlen(prefix);
    return length >= prefix_length
        && memcmp(value, prefix, prefix_length) == 0;
}

static long sys_openat(const char *path, int flags, int mode);
static long sys_close(int fd);
static long p241_getdents64(int fd, void *buffer, size_t capacity);
static long p241_newfstatat(
    const char *path, struct s22_p241_kernel_stat *value, int flags);
static long p241_readlinkat(const char *path, char *value, size_t capacity);
static long p282_read_file(
    const char *path, char *value, size_t capacity, size_t *length);
static long sys_nanosleep(long nanoseconds);
static long p316_dir_open(const char *path) {
    return sys_openat(path, O_RDONLY | O_DIRECTORY | O_CLOEXEC, 0);
}
'''
        + macros
        + declarations
        + br'''
enum fake_dir_kind {
    FAKE_DIR_NONE = 0,
    FAKE_DIR_PLATFORM = 10,
    FAKE_DIR_SPMI = 11,
    FAKE_DIR_PARENT = 12,
};

static unsigned int fake_platform_reads;
static unsigned int fake_spmi_reads;
static unsigned int fake_parent_reads;
static uint8_t fake_present = 0x07U;
static uint8_t fake_bound = 0x07U;
static uint8_t fake_wrong;
static uint8_t fake_duplicate;
static int fake_malformed;
static int fake_cmdline_rc;
static const char *fake_cmdline = "console=ttyMSM0 androidboot.mode=normal\n";
static int fake_waiting_kind = 2;
static int fake_supplier_kind;
static unsigned int fake_sleeps;

static const char *fake_names[P317_PROVIDER_COUNT] = {
    "c42d000.spmi", "spmi0-02", "spmi0-02-gpio",
};
static const char *fake_of_paths[P317_PROVIDER_COUNT] = {
    P317_SPMI_CONTROLLER_DT, P317_PMIC_DT, P317_GPIO_DT,
};

static void fake_reset(void) {
    fake_platform_reads = 0U;
    fake_spmi_reads = 0U;
    fake_parent_reads = 0U;
    fake_present = 0x07U;
    fake_bound = 0x07U;
    fake_wrong = 0U;
    fake_duplicate = 0U;
    fake_malformed = 0;
    fake_cmdline_rc = 0;
    fake_cmdline = "console=ttyMSM0 androidboot.mode=normal\n";
    fake_waiting_kind = 2;
    fake_supplier_kind = 0;
    fake_sleeps = 0U;
    memset(&g_p317_exec, 0, sizeof(g_p317_exec));
}

static size_t fake_dirent(
    uint8_t *buffer, size_t capacity, size_t cursor, const char *name) {
    size_t header = offsetof(struct s22_p241_linux_dirent64, d_name);
    size_t length = strlen(name) + 1U;
    size_t record = (header + length + 7U) & ~7U;
    if (cursor + record > capacity) return capacity + 1U;
    struct s22_p241_linux_dirent64 *entry =
        (struct s22_p241_linux_dirent64 *)(buffer + cursor);
    memset(entry, 0, record);
    entry->d_reclen = (uint16_t)record;
    memcpy(entry->d_name, name, length);
    return cursor + record;
}

static long sys_openat(const char *path, int flags, int mode) {
    (void)flags; (void)mode;
    if (strcmp(path, P317_PLATFORM_ROOT) == 0) {
        fake_platform_reads = 0U;
        return FAKE_DIR_PLATFORM;
    }
    if (strcmp(path, P317_SPMI_ROOT) == 0) {
        fake_spmi_reads = 0U;
        return FAKE_DIR_SPMI;
    }
    if (strcmp(path, "/sys/fake/3-0066") == 0) {
        fake_parent_reads = 0U;
        return FAKE_DIR_PARENT;
    }
    return -ENOENT;
}
static long sys_close(int fd) { (void)fd; return 0; }

static long p241_getdents64(int fd, void *raw, size_t capacity) {
    uint8_t *buffer = raw;
    size_t cursor = 0U;
    unsigned int *reads = fd == FAKE_DIR_PLATFORM ? &fake_platform_reads
        : (fd == FAKE_DIR_SPMI ? &fake_spmi_reads : &fake_parent_reads);
    if ((*reads)++ != 0U) return 0;
    if (fake_malformed) {
        memset(buffer, 0, 24U);
        ((struct s22_p241_linux_dirent64 *)buffer)->d_reclen = 1U;
        return 24;
    }
    if (fd == FAKE_DIR_PLATFORM) {
        for (unsigned int index = 0U; index < P317_PROVIDER_COUNT; index += 2U) {
            if (fake_present & (1U << index))
                cursor = fake_dirent(buffer, capacity, cursor, fake_names[index]);
            if (fake_duplicate & (1U << index)) {
                char duplicate[64];
                snprintf(duplicate, sizeof(duplicate), "%s-copy", fake_names[index]);
                cursor = fake_dirent(buffer, capacity, cursor, duplicate);
            }
        }
    } else if (fd == FAKE_DIR_SPMI) {
        if (fake_present & 0x02U)
            cursor = fake_dirent(buffer, capacity, cursor, fake_names[1]);
        if (fake_duplicate & 0x02U)
            cursor = fake_dirent(buffer, capacity, cursor, "spmi0-02-copy");
    } else if (fd == FAKE_DIR_PARENT) {
        if (fake_supplier_kind == 1)
            cursor = fake_dirent(buffer, capacity, cursor, "supplier:platform:gpio");
        else if (fake_supplier_kind == 2)
            cursor = fake_dirent(buffer, capacity, cursor, "supplier:platform:foreign");
        else if (fake_supplier_kind == 3) {
            cursor = fake_dirent(buffer, capacity, cursor, "supplier:platform:gpio");
            cursor = fake_dirent(buffer, capacity, cursor, "supplier:platform:foreign");
        }
    } else return -EBADF;
    return cursor > capacity ? -EOVERFLOW : (long)cursor;
}

static int fake_provider_index(const char *path) {
    char needle[96];
    for (unsigned int index = 0U; index < P317_PROVIDER_COUNT; ++index) {
        snprintf(needle, sizeof(needle), "/%s/", fake_names[index]);
        if (strstr(path, needle) != NULL) return (int)index;
    }
    if (strstr(path, "/spmi0-02-copy/") != NULL) return 1;
    if (strstr(path, "/c42d000.spmi-copy/") != NULL) return 0;
    if (strstr(path, "/spmi0-02-gpio-copy/") != NULL) return 2;
    return -1;
}

static long p241_newfstatat(
    const char *path, struct s22_p241_kernel_stat *value, int flags) {
    (void)flags;
    int index = fake_provider_index(path);
    if (index < 0 || strstr(path, "/driver") == NULL
        || !(fake_bound & (1U << index))) return -ENOENT;
    value->st_mode = S_IFLNK;
    return 0;
}

static long fake_link(char *value, size_t capacity, const char *target) {
    size_t amount = strlen(target);
    if (amount >= capacity) return -EOVERFLOW;
    memcpy(value, target, amount);
    return (long)amount;
}

static long p241_readlinkat(const char *path, char *value, size_t capacity) {
    if (strstr(path, "/of_node") != NULL) {
        if (strstr(path, "supplier:platform:gpio") != NULL)
            return fake_link(value, capacity, "/sys/firmware/devicetree/base" P317_GPIO_DT);
        if (strstr(path, "supplier:platform:foreign") != NULL)
            return fake_link(value, capacity, "/sys/firmware/devicetree/base/soc/foreign@0");
        int index = fake_provider_index(path);
        if (index < 0) return -ENOENT;
        return fake_link(value, capacity, fake_of_paths[index]);
    }
    if (strstr(path, "/driver") != NULL) {
        int index = fake_provider_index(path);
        if (index < 0 || !(fake_bound & (1U << index))) return -ENOENT;
        const char *driver = (fake_wrong & (1U << index))
            ? "wrong_driver" : p317_providers[index].driver;
        char target[128];
        snprintf(target, sizeof(target), "/sys/bus/fake/drivers/%s", driver);
        return fake_link(value, capacity, target);
    }
    return -ENOENT;
}

static long fake_copy(
    char *value, size_t capacity, size_t *length, const char *source) {
    size_t amount = strlen(source);
    if (amount > capacity) return -EOVERFLOW;
    memcpy(value, source, amount);
    *length = amount;
    return 0;
}

static long p282_read_file(
    const char *path, char *value, size_t capacity, size_t *length) {
    if (strcmp(path, "/proc/cmdline") == 0) {
        if (fake_cmdline_rc != 0) return fake_cmdline_rc;
        return fake_copy(value, capacity, length, fake_cmdline);
    }
    if (strcmp(path, "/sys/fake/3-0066/waiting_for_supplier") != 0)
        return -ENOENT;
    if (fake_waiting_kind == 0) return -ENOENT;
    if (fake_waiting_kind == 1) return fake_copy(value, capacity, length, "0\n");
    if (fake_waiting_kind == 2) return fake_copy(value, capacity, length, "1\n");
    return fake_copy(value, capacity, length, "x\n");
}

static long sys_nanosleep(long nanoseconds) {
    if (nanoseconds != P317_PROVIDER_SETTLE_NS) return -EINVAL;
    ++fake_sleeps;
    return 0;
}
'''
        + functions
        + br'''
static long fake_snapshot(uint8_t *present, uint8_t *bound) {
    fake_platform_reads = 0U;
    fake_spmi_reads = 0U;
    return p317_provider_snapshot(present, bound);
}

static long fake_supplier(uint8_t *state) {
    fake_parent_reads = 0U;
    return p317_capture_supplier("/sys/fake/3-0066", state);
}

int main(void) {
    uint8_t present = 0U;
    uint8_t bound = 0U;
    uint8_t state = 0U;
    unsigned int provider_negatives = 0U;
    unsigned int policy_negatives = 0U;
    unsigned int link_cases = 0U;

    fake_reset();
    if (fake_snapshot(&present, &bound) != 0 || present != 0x87U
        || bound != 0x07U || !p317_provider_ready(present, bound)) return 1;

    fake_reset(); fake_present = 0x03U;
    if (fake_snapshot(&present, &bound) != 0 || present != 0x83U
        || bound != 0x03U || p317_provider_ready(present, bound)) return 2;
    ++provider_negatives;
    fake_reset(); fake_wrong = 0x02U;
    if (fake_snapshot(&present, &bound) != 0 || present != 0x87U
        || bound != 0x25U || p317_provider_ready(present, bound)) return 3;
    ++provider_negatives;
    fake_reset(); fake_duplicate = 0x04U;
    if (fake_snapshot(&present, &bound) != 0 || present != 0xc3U
        || bound != 0x03U || p317_provider_ready(present, bound)) return 4;
    ++provider_negatives;
    fake_reset(); fake_malformed = 1;
    if (fake_snapshot(&present, &bound) != -EIO) return 5;
    ++provider_negatives;

    fake_reset(); fake_present = 0x03U;
    if (p317_capture_preclient_provider() != 0 || fake_sleeps != 49U
        || p317_provider_ready(g_p317_exec.pre_present, g_p317_exec.pre_bound))
        return 6;
    fake_reset();
    if (p317_capture_preclient_provider() != 0 || fake_sleeps != 0U
        || !p317_provider_ready(g_p317_exec.pre_present, g_p317_exec.pre_bound))
        return 7;

    fake_reset(); g_p317_exec.policy = S22PLUS_MAX77705_P317_POLICY_GADGET_READY;
    if (p317_capture_policy() != 0
        || g_p317_exec.policy != (S22PLUS_MAX77705_P317_POLICY_VALID
            | S22PLUS_MAX77705_P317_POLICY_GADGET_READY
            | S22PLUS_MAX77705_P317_POLICY_DEFAULT_ON_STRICT)) return 10;
    fake_reset(); fake_cmdline = "fw_devlink=off console=x\n";
    if (p317_capture_policy() != 0
        || (g_p317_exec.policy & S22PLUS_MAX77705_P317_POLICY_STATE_MASK)
            != S22PLUS_MAX77705_P317_POLICY_FW_DEVLINK_TOKEN) return 11;
    ++policy_negatives;
    fake_reset(); fake_cmdline = "fw_devlink.strict=0\n";
    if (p317_capture_policy() != 0
        || (g_p317_exec.policy & S22PLUS_MAX77705_P317_POLICY_STATE_MASK)
            != S22PLUS_MAX77705_P317_POLICY_STRICT_TOKEN) return 12;
    ++policy_negatives;
    fake_reset(); fake_cmdline = "fw_devlink=on fw_devlink.strict=1\n";
    if (p317_capture_policy() != 0
        || (g_p317_exec.policy & S22PLUS_MAX77705_P317_POLICY_STATE_MASK)
            != S22PLUS_MAX77705_P317_POLICY_BOTH_TOKENS) return 13;
    ++policy_negatives;
    fake_reset(); fake_cmdline = "console=x";
    if (p317_capture_policy() != -EIO) return 14;
    ++policy_negatives;
    fake_reset(); fake_cmdline_rc = -EIO;
    if (p317_capture_policy() != -EIO) return 15;
    ++policy_negatives;

    fake_reset(); fake_waiting_kind = 0;
    if (p317_capture_waiting("/sys/fake/3-0066", &state) != 0
        || state != S22PLUS_MAX77705_P317_WAITING_FILE_ABSENT) return 20;
    ++link_cases;
    fake_waiting_kind = 1;
    if (p317_capture_waiting("/sys/fake/3-0066", &state) != 0
        || state != S22PLUS_MAX77705_P317_WAITING_ZERO) return 21;
    ++link_cases;
    fake_waiting_kind = 2;
    if (p317_capture_waiting("/sys/fake/3-0066", &state) != 0
        || state != S22PLUS_MAX77705_P317_WAITING_ONE) return 22;
    ++link_cases;
    fake_waiting_kind = 3;
    if (p317_capture_waiting("/sys/fake/3-0066", &state) != -EIO) return 23;
    ++link_cases;

    fake_reset(); fake_supplier_kind = 0;
    if (fake_supplier(&state) != 0
        || state != S22PLUS_MAX77705_P317_SUPPLIER_LINK_ABSENT) return 30;
    ++link_cases;
    fake_reset(); fake_supplier_kind = 1;
    if (fake_supplier(&state) != 0
        || state != S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE) return 31;
    ++link_cases;
    fake_reset(); fake_supplier_kind = 2;
    if (fake_supplier(&state) != 0
        || state != S22PLUS_MAX77705_P317_SUPPLIER_FOREIGN_OR_MULTIPLE) return 32;
    ++link_cases;
    fake_reset(); fake_supplier_kind = 3;
    if (fake_supplier(&state) != 0
        || state != S22PLUS_MAX77705_P317_SUPPLIER_FOREIGN_OR_MULTIPLE) return 33;
    ++link_cases;

    fake_reset(); fake_waiting_kind = 1; fake_supplier_kind = 1;
    uint8_t final_waiting = S22PLUS_MAX77705_P317_WAITING_UNAVAILABLE;
    uint8_t final_supplier = S22PLUS_MAX77705_P317_SUPPLIER_UNAVAILABLE;
    if (p317_capture_post_provider() != 0
        || p317_capture_waiting("/sys/fake/3-0066", &final_waiting) != 0
        || p317_capture_supplier("/sys/fake/3-0066", &final_supplier) != 0)
        return 34;
    g_p317_exec.link_waiting = (uint8_t)(
        S22PLUS_MAX77705_P317_LINK_VALID | final_waiting |
        (final_supplier << S22PLUS_MAX77705_P317_SUPPLIER_SHIFT));
    if (!p317_provider_ready(g_p317_exec.post_present, g_p317_exec.post_bound)
        || g_p317_exec.link_waiting != (S22PLUS_MAX77705_P317_LINK_VALID
            | S22PLUS_MAX77705_P317_WAITING_ZERO
            | (S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE
                << S22PLUS_MAX77705_P317_SUPPLIER_SHIFT))) return 34;
    ++link_cases;

    printf("providers=3 provider_negatives=%u policy_negatives=%u link_cases=%u sleeps=49\n",
        provider_negatives, policy_negatives, link_cases);
    return 0;
}
'''
    )


def audit(root: Path | None = None) -> dict[str, object]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    runtime = _generated(root)
    output = support._compile(  # noqa: SLF001
        _runtime_tu(runtime), "p317-executability-runtime"
    )
    expected = (
        "providers=3 provider_negatives=4 policy_negatives=5 "
        "link_cases=9 sleeps=49\n"
    )
    if output != expected:
        raise FixtureError(f"P3.17 runtime fixture differs: {output!r}")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "provider_count": 3,
        "provider_negative_cases": 4,
        "policy_negative_cases": 5,
        "waiting_and_supplier_cases": 9,
        "settle_sleep_count": 49,
        "actual_materialized_provider_scan_executed": True,
        "actual_materialized_preclient_settle_executed": True,
        "actual_materialized_cmdline_policy_executed": True,
        "actual_materialized_waiting_state_executed": True,
        "actual_materialized_supplier_identity_executed": True,
        "actual_materialized_post_composition_executed": True,
        "dynamic_bus_device_names_executed": True,
        "verified": True,
    }


def main() -> int:
    try:
        value = audit()
    except (FixtureError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
