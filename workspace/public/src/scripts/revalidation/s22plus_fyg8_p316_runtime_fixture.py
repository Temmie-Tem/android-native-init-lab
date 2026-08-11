#!/usr/bin/env python3
"""Execute the materialized P3.16 15-device override/bind seam."""

from __future__ import annotations

import json
from pathlib import Path

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p316_generator as generator


SCHEMA = "s22plus_fyg8_p316_runtime_fixture_v1"
VERDICT = "PASS_P316_15_DEVICE_RUNTIME_FIXTURE_HOST_ONLY"


class FixtureError(ValueError):
    pass


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def _inventory(runtime: bytes) -> bytes:
    start = runtime.find(b"struct p316_platform_device {")
    end = runtime.find(b"struct p316_i2c_topology {", start)
    if start < 0 or end < 0 or runtime.find(b"struct p316_platform_device {", start + 1) >= 0:
        raise FixtureError("P3.16 platform inventory extent differs")
    value = runtime[start:end]
    if value.count(b'{"') != 15 or value.count(b", 1U}") != 3:
        raise FixtureError("P3.16 platform inventory cardinality differs")
    return value


def _topology_tu(runtime: bytes) -> bytes:
    macros = b"".join(
        support._macro(runtime, name)  # noqa: SLF001
        for name in (
            b"P316_PLATFORM_ROOT",
            b"P316_TARGET_I2C_DEVICE",
            b"P316_DIAG_MODULE_NAME",
            b"S22PLUS_MAX77705_DRIVER_ABSENT",
            b"S22PLUS_MAX77705_DRIVER_UNBOUND",
            b"S22PLUS_MAX77705_DRIVER_OTHER",
            b"S22PLUS_MAX77705_DRIVER_DIAGNOSTIC",
        )
    )
    topology = support._struct(  # noqa: SLF001
        runtime, b"struct p316_i2c_topology {"
    )
    binding = support._struct(  # noqa: SLF001
        runtime, b"struct s22plus_max77705_binding_witness {"
    )
    functions = b"".join(
        support._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static int p316_name_has_prefix(",
            b"static int p316_decimal_suffix(",
            b"static long p316_platform_path(",
            b"static long p316_driver_state(",
            b"static long p316_dir_open(",
            b"static long p316_find_adapter(",
            b"static int p316_i2c_client_name(",
            b"static int p316_hex_digit(",
            b"static int p316_i2c_client_on_adapter(",
            b"static long p316_client_path(",
            b"static long p316_compatible_is_max77705(",
            b"static long p316_scan_i2c_topology(",
            b"static void p316_binding_pre(",
            b"static void p316_binding_post(",
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
#define S22PLUS_MAX77705_LOADER_NOT_STARTED 0U

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
static int p282_is_digit(char value) {
    return value >= '0' && value <= '9';
}
static long p282_make_path(
    char *output, size_t capacity, const char *root,
    const char *name, const char *suffix) {
    int amount = snprintf(output, capacity, "%s%s%s", root, name, suffix);
    return amount < 0 || (size_t)amount >= capacity ? -EOVERFLOW : 0;
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
    size_t expected_length = strlen(expected);
    return length - offset == expected_length
        && memcmp(start, expected, expected_length) == 0;
}

static long sys_openat(const char *path, int flags, int mode);
static long sys_close(int fd);
static long p241_getdents64(int fd, void *buffer, size_t capacity);
static long p241_newfstatat(
    const char *path, struct s22_p241_kernel_stat *value, int flags);
static long p241_readlinkat(const char *path, char *value, size_t capacity);
static long p282_read_file(
    const char *path, char *value, size_t capacity, size_t *length);
'''
        + macros
        + topology
        + binding
        + br'''
static unsigned int fake_adapter_count;
static unsigned int fake_parent_count;
static unsigned int fake_muic_count;
static unsigned int fake_wrong_compatible_count;
static int fake_malformed_root;
static int fake_malformed_clients;
static uint8_t fake_driver_state;
static unsigned int fake_root_reads;
static unsigned int fake_adapter_reads;

static void fake_reset(void) {
    fake_adapter_count = 1U;
    fake_parent_count = 1U;
    fake_muic_count = 0U;
    fake_wrong_compatible_count = 0U;
    fake_malformed_root = 0;
    fake_malformed_clients = 0;
    fake_driver_state = S22PLUS_MAX77705_DRIVER_UNBOUND;
    fake_root_reads = 0U;
    fake_adapter_reads = 0U;
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
    if (strcmp(path, "/sys/bus/platform/devices/994000.i2c/") == 0)
        return 10;
    if (strcmp(path, "/sys/bus/platform/devices/994000.i2c/i2c-3") == 0)
        return 11;
    return -ENOENT;
}
static long sys_close(int fd) { (void)fd; return 0; }

static long p241_getdents64(int fd, void *raw, size_t capacity) {
    uint8_t *buffer = raw;
    size_t cursor = 0U;
    if (fd == 10) {
        if (fake_root_reads++ != 0U) return 0;
        if (fake_malformed_root) {
            memset(buffer, 0, 24U);
            ((struct s22_p241_linux_dirent64 *)buffer)->d_reclen = 1U;
            return 24;
        }
        for (unsigned int index = 0U; index < fake_adapter_count; ++index) {
            cursor = fake_dirent(
                buffer, capacity, cursor, index == 0U ? "i2c-3" : "i2c-57");
        }
        return cursor > capacity ? -EOVERFLOW : (long)cursor;
    }
    if (fd != 11) return -EBADF;
    if (fake_adapter_reads++ != 0U) return 0;
    if (fake_malformed_clients) {
        memset(buffer, 0, 24U);
        ((struct s22_p241_linux_dirent64 *)buffer)->d_reclen = 1U;
        return 24;
    }
    for (unsigned int index = 0U; index < fake_parent_count; ++index)
        cursor = fake_dirent(buffer, capacity, cursor, "3-0066");
    for (unsigned int index = 0U; index < fake_muic_count; ++index)
        cursor = fake_dirent(buffer, capacity, cursor, "3-0025");
    for (unsigned int index = 0U;
         index < fake_wrong_compatible_count; ++index)
        cursor = fake_dirent(buffer, capacity, cursor, "3-0055");
    return cursor > capacity ? -EOVERFLOW : (long)cursor;
}

static long p241_newfstatat(
    const char *path, struct s22_p241_kernel_stat *value, int flags) {
    (void)flags;
    if (strstr(path, "/3-0066/driver") == NULL) return -ENOENT;
    if (fake_driver_state == S22PLUS_MAX77705_DRIVER_UNBOUND) return -ENOENT;
    value->st_mode = fake_driver_state == 0xffU ? S_IFREG : S_IFLNK;
    return 0;
}
static long p241_readlinkat(const char *path, char *value, size_t capacity) {
    (void)path;
    const char *target = fake_driver_state ==
        S22PLUS_MAX77705_DRIVER_DIAGNOSTIC
        ? "/sys/bus/i2c/drivers/s22plus_max77705_mux_diag"
        : "/sys/bus/i2c/drivers/max77705";
    size_t amount = strlen(target);
    if (amount >= capacity) return -EOVERFLOW;
    memcpy(value, target, amount);
    return (long)amount;
}
static long p282_read_file(
    const char *path, char *value, size_t capacity, size_t *length) {
    static const char compatibles[] = "vendor,other\0maxim,max77705\0";
    if (strstr(path, "/3-0055/of_node/compatible") == NULL) return -ENOENT;
    if (sizeof(compatibles) > capacity) return -EOVERFLOW;
    memcpy(value, compatibles, sizeof(compatibles));
    *length = sizeof(compatibles);
    return 0;
}
'''
        + functions
        + br'''
static long fake_scan(struct p316_i2c_topology *value) {
    fake_root_reads = 0U;
    fake_adapter_reads = 0U;
    memset(value, 0, sizeof(*value));
    return p316_scan_i2c_topology(value);
}

int main(void) {
    struct p316_i2c_topology value;
    struct p316_i2c_topology pre;
    struct p316_i2c_topology post;
    struct s22plus_max77705_binding_witness binding = {0};
    unsigned int negatives = 0U;

    fake_reset();
    if (fake_scan(&value) != 0 || strcmp(value.adapter_name, "i2c-3") != 0
        || strcmp(value.parent_name, "3-0066") != 0
        || value.parent_present != 1U || value.muic_count != 0U
        || value.parent_driver_state != S22PLUS_MAX77705_DRIVER_UNBOUND)
        return 1;
    pre = value;
    p316_binding_pre(&binding, &pre);
    if (binding.loader_state != S22PLUS_MAX77705_LOADER_NOT_STARTED
        || binding.pre_exact_parent_present != 1U
        || binding.pre_exact_parent_driver_state !=
            S22PLUS_MAX77705_DRIVER_UNBOUND
        || binding.pre_matching_unbound_parent_count != 1U
        || binding.pre_wrong_address_compatible_parent_count != 0U)
        return 17;

    fake_muic_count = 1U;
    fake_driver_state = S22PLUS_MAX77705_DRIVER_DIAGNOSTIC;
    if (fake_scan(&post) != 0 || post.muic_count != 1U
        || strcmp(post.muic_name, "3-0025") != 0
        || post.parent_driver_state != S22PLUS_MAX77705_DRIVER_DIAGNOSTIC)
        return 2;
    p316_binding_post(&binding, &pre, &post);
    if (binding.post_exact_parent_driver_state !=
            S22PLUS_MAX77705_DRIVER_DIAGNOSTIC
        || binding.post_diagnostic_bound_parent_count != 1U
        || binding.post_exact_adapter_muic_0x25_client_count != 1U
        || binding.post_foreign_0x25_client_count != 0U)
        return 18;
    pre.muic_count = 1U;
    p316_binding_post(&binding, &pre, &post);
    if (binding.post_foreign_0x25_client_count != 1U) return 19;

    fake_reset(); fake_wrong_compatible_count = 1U;
    if (fake_scan(&value) != 0
        || value.wrong_address_compatible_count != 1U) return 3;
    memset(&binding, 0, sizeof(binding));
    p316_binding_pre(&binding, &value);
    if (binding.pre_wrong_address_compatible_parent_count != 1U)
        return 20;
    fake_driver_state = S22PLUS_MAX77705_DRIVER_OTHER;
    if (fake_scan(&value) != 0
        || value.parent_driver_state != S22PLUS_MAX77705_DRIVER_OTHER)
        return 4;

    fake_reset(); fake_adapter_count = 2U;
    if (fake_scan(&value) != -EIO) return 10;
    ++negatives;
    fake_reset(); fake_adapter_count = 0U;
    if (fake_scan(&value) != -ENODEV) return 11;
    ++negatives;
    fake_reset(); fake_malformed_root = 1;
    if (fake_scan(&value) != -EIO) return 12;
    ++negatives;
    fake_reset(); fake_parent_count = 2U;
    if (fake_scan(&value) != -EIO) return 13;
    ++negatives;
    fake_reset(); fake_muic_count = 2U;
    if (fake_scan(&value) != -EIO) return 14;
    ++negatives;
    fake_reset(); fake_malformed_clients = 1;
    if (fake_scan(&value) != -EIO) return 15;
    ++negatives;
    fake_reset(); fake_driver_state = 0xffU;
    if (fake_scan(&value) != -EIO) return 16;
    ++negatives;

    printf("adapter=i2c-3 parent=3-0066 muic=3-0025 negatives=%u\n",
        negatives);
    return 0;
}
'''
    )


def _runtime_tu(runtime: bytes) -> bytes:
    macros = b"".join(
        support._macro(runtime, name)  # noqa: SLF001
        for name in (
            b"P316_OVERRIDE_SENTINEL",
            b"P316_OVERRIDE_SENTINEL_LINE",
            b"P316_PLATFORM_ROOT",
        )
    )
    functions = b"".join(
        support._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static int p316_bytes_equal(",
            b"static long p316_platform_path(",
            b"static long p316_path_present(",
            b"static long p316_expect_driver(",
            b"static long p316_expect_override(",
            b"static long p316_proc_module_absent(",
            b"static long p316_prepare_overrides(",
            b"static long p316_verify_substrate_bindings(",
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
#define S22_P241_SYMLINK_TARGET_MAX 256U

struct s22_p241_kernel_stat { unsigned int st_mode; };

static size_t cstr_len(const char *value) { return strlen(value); }
static int p260_bytes_equal(const void *a, const void *b, size_t n) {
    return memcmp(a, b, n) == 0;
}
static long p282_make_path(
    char *output, size_t capacity, const char *root,
    const char *name, const char *suffix) {
    int amount = snprintf(output, capacity, "%s%s%s", root, name, suffix);
    return amount < 0 || (size_t)amount >= capacity ? -EOVERFLOW : 0;
}
static long p241_newfstatat(
    const char *path, struct s22_p241_kernel_stat *value, int flags);
static long p241_readlinkat(const char *path, char *value, size_t capacity);
static long p282_read_file(
    const char *path, char *value, size_t capacity, size_t *length);
static long p282_write_control(const char *path, const char *value);
static int p241_basename_equals(
    const char *path, size_t length, const char *expected);
'''
        + macros
        + _inventory(runtime)
        + br'''
static uint8_t fake_present[15];
static uint8_t fake_bound[15];
static uint8_t fake_override[15];
static int fake_wrong_driver;
static int fake_preloaded;

static int fake_path_index(const char *path, const char *suffix) {
    char expected[256];
    for (size_t index = 0U; index < 15U; ++index) {
        if (snprintf(expected, sizeof(expected), "%s%s%s",
                P316_PLATFORM_ROOT, p316_platform_devices[index].name,
                suffix) < 0) return -1;
        if (strcmp(path, expected) == 0) return (int)index;
    }
    return -1;
}

static long p241_newfstatat(
    const char *path, struct s22_p241_kernel_stat *value, int flags) {
    (void)flags;
    int index = fake_path_index(path, "");
    if (index >= 0) {
        if (!fake_present[index]) return -ENOENT;
        value->st_mode = S_IFDIR;
        return 0;
    }
    index = fake_path_index(path, "/driver");
    if (index >= 0) {
        if (!fake_bound[index]) return -ENOENT;
        value->st_mode = S_IFLNK;
        return 0;
    }
    return -ENOENT;
}

static long p241_readlinkat(
    const char *path, char *value, size_t capacity) {
    int index = fake_path_index(path, "/driver");
    if (index < 0 || !fake_bound[index]) return -ENOENT;
    const char *driver = index == fake_wrong_driver
        ? "wrong_driver" : p316_platform_devices[index].driver;
    int amount = snprintf(
        value, capacity, "/sys/bus/platform/drivers/%s", driver);
    return amount < 0 || (size_t)amount >= capacity ? -EOVERFLOW : amount;
}

static int p241_basename_equals(
    const char *path, size_t length, const char *expected) {
    const char *start = path;
    for (size_t index = 0U; index < length; ++index) {
        if (path[index] == '/') start = path + index + 1U;
    }
    return strlen(start) == strlen(expected) && strcmp(start, expected) == 0;
}

static long fake_copy(
    char *value, size_t capacity, size_t *length, const char *source) {
    size_t amount = strlen(source);
    if (amount >= capacity) return -EOVERFLOW;
    memcpy(value, source, amount);
    value[amount] = '\0';
    *length = amount;
    return 0;
}

static long p282_read_file(
    const char *path, char *value, size_t capacity, size_t *length) {
    if (strcmp(path, "/proc/modules") == 0)
        return fake_copy(
            value, capacity, length,
            fake_preloaded ? "gpi 1 0 - Live 0\n" : "");
    int index = fake_path_index(path, "/driver_override");
    if (index < 0) return -ENOENT;
    return fake_copy(
        value, capacity, length,
        fake_override[index]
            ? P316_OVERRIDE_SENTINEL_LINE : "(null)\n");
}

static long p282_write_control(const char *path, const char *value) {
    int index = fake_path_index(path, "/driver_override");
    if (index < 0 || strcmp(value, P316_OVERRIDE_SENTINEL_LINE) != 0)
        return -EINVAL;
    fake_override[index] = 1U;
    return 0;
}

static void fake_reset(void) {
    memset(fake_present, 1, sizeof(fake_present));
    memset(fake_bound, 0, sizeof(fake_bound));
    memset(fake_override, 0, sizeof(fake_override));
    fake_wrong_driver = -1;
    fake_preloaded = 0;
}

static void fake_load_substrate(void) {
    for (size_t index = 0U; index < 15U; ++index)
        fake_bound[index] = p316_platform_devices[index].target;
}
'''
        + functions
        + br'''
int main(void) {
    unsigned int targets = 0U;
    unsigned int blockers = 0U;
    unsigned int negative = 0U;
    for (size_t index = 0U; index < 15U; ++index) {
        if (p316_platform_devices[index].target) ++targets;
        else ++blockers;
    }
    if (targets != 3U || blockers != 12U
        || !p316_platform_devices[0].target
        || !p316_platform_devices[3].target
        || !p316_platform_devices[6].target) return 1;

    fake_reset();
    if (p316_prepare_overrides() != 0) return 2;
    for (size_t index = 0U; index < 15U; ++index) {
        if (fake_override[index] == p316_platform_devices[index].target)
            return 3;
    }
    fake_load_substrate();
    if (p316_verify_substrate_bindings() != 0) return 4;

    fake_reset(); fake_present[4] = 0U;
    if (p316_prepare_overrides() == 0) return 10;
    ++negative;
    fake_reset(); fake_bound[4] = 1U;
    if (p316_prepare_overrides() == 0) return 11;
    ++negative;
    fake_reset(); fake_preloaded = 1;
    if (p316_prepare_overrides() == 0) return 12;
    ++negative;
    fake_reset(); fake_override[0] = 1U;
    if (p316_prepare_overrides() == 0) return 13;
    ++negative;

    fake_reset();
    if (p316_prepare_overrides() != 0) return 20;
    fake_load_substrate(); fake_override[4] = 0U;
    if (p316_verify_substrate_bindings() == 0) return 21;
    ++negative;
    fake_reset();
    if (p316_prepare_overrides() != 0) return 22;
    fake_load_substrate(); fake_bound[4] = 1U;
    if (p316_verify_substrate_bindings() == 0) return 23;
    ++negative;
    fake_reset();
    if (p316_prepare_overrides() != 0) return 24;
    fake_load_substrate(); fake_wrong_driver = 0;
    if (p316_verify_substrate_bindings() == 0) return 25;
    ++negative;

    printf("devices=%u targets=%u blockers=%u negatives=%u\n",
        targets + blockers, targets, blockers, negative);
    return 0;
}
'''
    )


def audit(root: Path | None = None) -> dict[str, object]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    artifacts = _generated(root)
    runtime = artifacts["p290_e3_runtime_include"]
    output = support._compile(  # noqa: SLF001
        _runtime_tu(runtime), "p316-15-device-runtime"
    )
    expected = "devices=15 targets=3 blockers=12 negatives=7\n"
    if output != expected:
        raise FixtureError(f"P3.16 15-device runtime fixture differs: {output!r}")
    topology_output = support._compile(  # noqa: SLF001
        _topology_tu(runtime), "p316-i2c-topology-runtime"
    )
    expected_topology = (
        "adapter=i2c-3 parent=3-0066 muic=3-0025 negatives=7\n"
    )
    if topology_output != expected_topology:
        raise FixtureError(
            f"P3.16 I2C topology runtime fixture differs: {topology_output!r}"
        )
    plan = artifacts["plan_header"]
    expected_tail = (
        b'{"msm-geni-se.ko", "msm_geni_se", ""},',
        b'{"gpi.ko", "gpi", ""},',
        b'{"i2c-msm-geni.ko", "i2c_msm_geni", ""},',
    )
    if plan.count(b'.ko"') != 64 or any(plan.count(row) != 1 for row in expected_tail):
        raise FixtureError("P3.16 64-module substrate tail differs")
    if b"s22plus_max77705_mux_diag.ko" in plan:
        raise FixtureError("P3.16 diagnostic leaked into the early plan")
    wrapper = artifacts["runtime_wrapper"]
    override = wrapper.find(b"p316_prepare_overrides();")
    first_module = wrapper.find(b"p241_load_and_verify_module(index)")
    if override < 0 or first_module < 0 or override >= first_module:
        raise FixtureError("P3.16 override call is not before module loading")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "device_count": 15,
        "target_count": 3,
        "blocked_count": 12,
        "negative_cases": 7,
        "actual_materialized_prepare_executed": True,
        "actual_materialized_binding_verifier_executed": True,
        "override_before_first_module": True,
        "early_module_count": 64,
        "diagnostic_late_only": True,
        "actual_materialized_topology_executed": True,
        "dynamic_adapter_number_executed": "i2c-3",
        "exact_parent_client_executed": "3-0066",
        "post_muic_client_executed": "3-0025",
        "actual_materialized_binding_pre_post_executed": True,
        "foreign_preexisting_muic_case_executed": True,
        "topology_negative_cases": 7,
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
