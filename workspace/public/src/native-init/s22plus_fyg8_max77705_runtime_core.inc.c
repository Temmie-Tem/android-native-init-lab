/*
 * P3.16 target-only Max77705 runtime integration.
 *
 * This file is appended to the frozen P3.15 runtime after the strict module
 * result parser and the native envelope encoder.  It relies only on the
 * inherited freestanding PID1 helpers.  The twelve platform overrides are
 * applied before any substrate module is loaded; the diagnostic module is
 * loaded exactly once, from a child, only after the gadget/direct fence has
 * closed.  Reboot is the only rollback mechanism for the transient sysfs
 * overrides and the bound diagnostic module.
 */

#define P316_OVERRIDE_SENTINEL "s22plus-max77705-block"
#define P316_OVERRIDE_SENTINEL_LINE P316_OVERRIDE_SENTINEL "\n"
#define P316_PLATFORM_ROOT "/sys/bus/platform/devices/"
#define P316_TARGET_I2C_DEVICE "994000.i2c"
#define P316_DIAG_MODULE_FILE "s22plus_max77705_mux_diag.ko"
#define P316_DIAG_MODULE_NAME "s22plus_max77705_mux_diag"
#define P316_DIAG_RESULT_PATH \
    "/sys/module/s22plus_max77705_mux_diag/parameters/result"
#define P316_DIAG_DEADLINE_SEC 45LL
#define P316_DIAG_REAP_MSEC 1000LL
#define P316_DIAG_HELPER_MAGIC 0x50333136U
#define P316_DIAG_HELPER_VERSION 1U

#define P316_POSITION_SUBSTRATE_VERIFIED 92U
#define P316_POSITION_TOPOLOGY_VERIFIED 93U
#define P316_POSITION_DIAGNOSTIC_DISPATCHED 94U
#define P316_POSITION_DIAGNOSTIC_RETURNED 95U
#define P316_POSITION_BINDING_CAPTURED 96U
#define P316_POSITION_RESULT_PARSED 97U
#define P316_POSITION_RESULT_CLASSIFIED 98U
#define P316_POSITION_ENVELOPE_READY 99U

struct p316_platform_device {
    const char *name;
    const char *driver;
    uint8_t target;
};

static const struct p316_platform_device p316_platform_devices[] = {
    {"9c0000.qcom,qupv3_0_geni_se", "qupv3_geni_se", 1U},
    {"8c0000.qcom,qupv3_2_geni_se", "qupv3_geni_se", 0U},
    {"ac0000.qcom,qupv3_1_geni_se", "qupv3_geni_se", 0U},
    {"900000.qcom,gpi-dma", "gpi_dma", 1U},
    {"800000.qcom,gpi-dma", "gpi_dma", 0U},
    {"a00000.qcom,gpi-dma", "gpi_dma", 0U},
    {"994000.i2c", "i2c_geni", 1U},
    {"884000.i2c", "i2c_geni", 0U},
    {"888000.i2c", "i2c_geni", 0U},
    {"88c000.i2c", "i2c_geni", 0U},
    {"988000.i2c", "i2c_geni", 0U},
    {"990000.i2c", "i2c_geni", 0U},
    {"a84000.i2c", "i2c_geni", 0U},
    {"a90000.i2c", "i2c_geni", 0U},
    {"a94000.i2c", "i2c_geni", 0U},
};

_Static_assert(
    sizeof(p316_platform_devices) / sizeof(p316_platform_devices[0]) == 15U,
    "P3.16 exact platform inventory");

struct p316_i2c_topology {
    char adapter_name[32];
    char adapter_path[192];
    char parent_name[32];
    char parent_path[224];
    char muic_name[32];
    char muic_path[224];
    uint8_t parent_present;
    uint8_t parent_driver_state;
    uint8_t matching_unbound_count;
    uint8_t wrong_address_compatible_count;
    uint8_t muic_count;
};

struct p316_diag_helper_record {
    uint32_t magic;
    uint16_t version;
    uint16_t reserved;
    int32_t result;
};

struct p316_diag_observation {
    struct s22plus_max77705_binding_witness binding;
    struct s22plus_max77705_runtime_result result;
    struct s22plus_max77705_runtime_poll_summary summary;
    uint8_t result_valid;
    uint8_t semantic_kind;
    uint8_t semantic_code;
    uint8_t observer_site;
    uint8_t observer_error_class;
};

static int p316_bytes_equal(
    const char *value, size_t length, const char *expected) {
    size_t expected_length = cstr_len(expected);
    return length == expected_length
        && p260_bytes_equal(value, expected, expected_length);
}

static int p316_name_has_prefix(
    const char *name, size_t length, const char *prefix) {
    size_t prefix_length = cstr_len(prefix);
    return length >= prefix_length
        && p260_bytes_equal(name, prefix, prefix_length);
}

static int p316_decimal_suffix(
    const char *name, size_t length, size_t offset) {
    if (offset >= length) return 0;
    for (size_t index = offset; index < length; ++index) {
        if (!p282_is_digit(name[index])) return 0;
    }
    return 1;
}

static long p316_platform_path(
    char *output, size_t capacity, const char *name, const char *suffix) {
    return p282_make_path(
        output, capacity, P316_PLATFORM_ROOT, name, suffix);
}

static long p316_path_present(const char *path, int *present) {
    struct s22_p241_kernel_stat value = {0};
    long rc = p241_newfstatat(path, &value, AT_SYMLINK_NOFOLLOW);
    if (rc == -ENOENT) {
        *present = 0;
        return 0;
    }
    if (rc != 0) return rc;
    *present = 1;
    return 0;
}

static long p316_driver_state(
    const char *device_path,
    const char *diagnostic_name,
    uint8_t *state) {
    char path[256];
    char target[S22_P241_SYMLINK_TARGET_MAX];
    struct s22_p241_kernel_stat stat_buffer = {0};
    size_t cursor = 0U;
    path[0] = '\0';
    long rc = p282_copy_path_part(
        path, sizeof(path), &cursor, device_path);
    if (rc == 0)
        rc = p282_copy_path_part(path, sizeof(path), &cursor, "/driver");
    if (rc != 0) return rc;
    rc = p241_newfstatat(path, &stat_buffer, AT_SYMLINK_NOFOLLOW);
    if (rc == -ENOENT) {
        *state = S22PLUS_MAX77705_DRIVER_UNBOUND;
        return 0;
    }
    if (rc != 0) return rc;
    if ((stat_buffer.st_mode & S_IFMT) != S_IFLNK)
        return -EIO;
    long amount = p241_readlinkat(path, target, sizeof(target));
    if (amount <= 0 || amount >= (long)sizeof(target))
        return amount < 0 ? amount : -EIO;
    *state = diagnostic_name != NULL && p241_basename_equals(
        target, (size_t)amount, diagnostic_name)
        ? S22PLUS_MAX77705_DRIVER_DIAGNOSTIC
        : S22PLUS_MAX77705_DRIVER_OTHER;
    return 0;
}

static long p316_expect_driver(
    const struct p316_platform_device *device, int should_bind) {
    char driver_path[224];
    char target[S22_P241_SYMLINK_TARGET_MAX];
    struct s22_p241_kernel_stat stat_buffer = {0};
    long rc = p316_platform_path(
        driver_path, sizeof(driver_path), device->name, "/driver");
    if (rc != 0) return rc;
    rc = p241_newfstatat(driver_path, &stat_buffer, AT_SYMLINK_NOFOLLOW);
    if (!should_bind)
        return rc == -ENOENT ? 0 : (rc == 0 ? -EEXIST : rc);
    if (rc != 0 || (stat_buffer.st_mode & S_IFMT) != S_IFLNK)
        return rc != 0 ? rc : -EIO;
    long amount = p241_readlinkat(driver_path, target, sizeof(target));
    if (amount <= 0 || amount >= (long)sizeof(target))
        return amount < 0 ? amount : -EIO;
    return p241_basename_equals(
        target, (size_t)amount, device->driver) ? 0 : -ENODEV;
}

static long p316_expect_override(
    const struct p316_platform_device *device, const char *expected) {
    char path[224];
    char value[64];
    size_t length = 0U;
    long rc = p316_platform_path(
        path, sizeof(path), device->name, "/driver_override");
    if (rc == 0)
        rc = p282_read_file(path, value, sizeof(value), &length);
    if (rc != 0) return rc;
    return p316_bytes_equal(value, length, expected) ? 0 : -ENODEV;
}

static long p316_proc_module_absent(const char *runtime_name) {
    char value[16384];
    size_t length = 0U;
    long rc = p282_read_file(
        "/proc/modules", value, sizeof(value), &length);
    if (rc != 0) return rc;
    size_t name_length = cstr_len(runtime_name);
    size_t cursor = 0U;
    while (cursor < length) {
        size_t start = cursor;
        while (cursor < length && value[cursor] != ' '
            && value[cursor] != '\n') ++cursor;
        if (cursor - start == name_length
            && p260_bytes_equal(value + start, runtime_name, name_length))
            return -EEXIST;
        while (cursor < length && value[cursor] != '\n') ++cursor;
        if (cursor < length) ++cursor;
    }
    return 0;
}

static long p316_prepare_overrides(void) {
    static const char *const substrate[] = {
        "msm_geni_se", "gpi", "i2c_msm_geni",
    };
    for (size_t index = 0U;
         index < sizeof(substrate) / sizeof(substrate[0]); ++index) {
        long rc = p316_proc_module_absent(substrate[index]);
        if (rc != 0) return rc;
    }
    for (size_t index = 0U;
         index < sizeof(p316_platform_devices) /
            sizeof(p316_platform_devices[0]); ++index) {
        const struct p316_platform_device *device =
            &p316_platform_devices[index];
        char root[192];
        char override_path[224];
        int present = 0;
        long rc = p316_platform_path(
            root, sizeof(root), device->name, "");
        if (rc == 0) rc = p316_path_present(root, &present);
        if (rc != 0 || !present) return rc != 0 ? rc : -ENODEV;
        rc = p316_expect_driver(device, 0);
        if (rc != 0) return rc;
        rc = p316_expect_override(device, "(null)\n");
        if (rc != 0) return rc;
        if (device->target) continue;
        rc = p316_platform_path(
            override_path, sizeof(override_path), device->name,
            "/driver_override");
        if (rc == 0)
            rc = p282_write_control(
                override_path, P316_OVERRIDE_SENTINEL_LINE);
        if (rc == 0)
            rc = p316_expect_override(
                device, P316_OVERRIDE_SENTINEL_LINE);
        if (rc != 0) return rc;
    }
    return 0;
}

static long p316_verify_substrate_bindings(void) {
    for (size_t index = 0U;
         index < sizeof(p316_platform_devices) /
            sizeof(p316_platform_devices[0]); ++index) {
        const struct p316_platform_device *device =
            &p316_platform_devices[index];
        long rc = p316_expect_driver(device, device->target != 0U);
        if (rc != 0) return rc;
        rc = p316_expect_override(
            device,
            device->target ? "(null)\n" : P316_OVERRIDE_SENTINEL_LINE);
        if (rc != 0) return rc;
    }
    return 0;
}

static long p316_dir_open(const char *path) {
    return sys_openat(path, O_RDONLY | O_CLOEXEC, 0);
}

static long p316_find_adapter(struct p316_i2c_topology *topology) {
    char root[192];
    uint8_t buffer[S22_P241_DIRENT_BUFFER_SIZE];
    unsigned int count = 0U;
    long rc = p316_platform_path(
        root, sizeof(root), P316_TARGET_I2C_DEVICE, "/");
    if (rc != 0) return rc;
    long fd = p316_dir_open(root);
    if (fd < 0) return fd;
    for (;;) {
        long amount = p241_getdents64((int)fd, buffer, sizeof(buffer));
        if (amount < 0) {
            (void)sys_close((int)fd);
            return amount;
        }
        if (amount == 0) break;
        size_t cursor = 0U;
        while (cursor < (size_t)amount) {
            struct s22_p241_linux_dirent64 *entry =
                (struct s22_p241_linux_dirent64 *)(buffer + cursor);
            size_t header = offsetof(struct s22_p241_linux_dirent64, d_name);
            if (entry->d_reclen < header + 2U
                || cursor + entry->d_reclen > (size_t)amount) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            size_t capacity = entry->d_reclen - header;
            size_t length = 0U;
            while (length < capacity && entry->d_name[length] != '\0')
                ++length;
            if (length == capacity || length == 0U) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            if (p316_name_has_prefix(entry->d_name, length, "i2c-")
                && p316_decimal_suffix(entry->d_name, length, 4U)) {
                if (++count != 1U || length + 1U >
                    sizeof(topology->adapter_name)) {
                    (void)sys_close((int)fd);
                    return -EIO;
                }
                memcpy(topology->adapter_name, entry->d_name, length);
                topology->adapter_name[length] = '\0';
            }
            cursor += entry->d_reclen;
        }
    }
    long close_rc = sys_close((int)fd);
    if (close_rc != 0) return close_rc;
    if (count != 1U) return -ENODEV;
    size_t path_cursor = 0U;
    topology->adapter_path[0] = '\0';
    rc = p282_copy_path_part(
        topology->adapter_path, sizeof(topology->adapter_path),
        &path_cursor, root);
    if (rc == 0)
        rc = p282_copy_path_part(
            topology->adapter_path, sizeof(topology->adapter_path),
            &path_cursor, topology->adapter_name);
    return rc;
}

static int p316_i2c_client_name(
    const char *name, size_t length, const char *adapter_name,
    const char *address) {
    size_t adapter_length = cstr_len(adapter_name);
    size_t address_length = cstr_len(address);
    if (!p316_name_has_prefix(adapter_name, adapter_length, "i2c-")
        || adapter_length <= 4U) return 0;
    const char *number = adapter_name + 4U;
    size_t number_length = adapter_length - 4U;
    return length == number_length + 1U + address_length
        && p260_bytes_equal(name, number, number_length)
        && name[number_length] == '-'
        && p260_bytes_equal(
            name + number_length + 1U, address, address_length);
}

static int p316_hex_digit(char value) {
    return (value >= '0' && value <= '9')
        || (value >= 'a' && value <= 'f');
}

static int p316_i2c_client_on_adapter(
    const char *name, size_t length, const char *adapter_name) {
    size_t adapter_length = cstr_len(adapter_name);
    if (!p316_name_has_prefix(adapter_name, adapter_length, "i2c-")
        || adapter_length <= 4U) return 0;
    const char *number = adapter_name + 4U;
    size_t number_length = adapter_length - 4U;
    if (length != number_length + 5U
        || !p260_bytes_equal(name, number, number_length)
        || name[number_length] != '-') return 0;
    for (size_t index = number_length + 1U; index < length; ++index) {
        if (!p316_hex_digit(name[index])) return 0;
    }
    return 1;
}

static long p316_client_path(
    char *output, size_t capacity,
    const char *adapter_path, const char *name) {
    size_t cursor = 0U;
    output[0] = '\0';
    long rc = p282_copy_path_part(
        output, capacity, &cursor, adapter_path);
    if (rc == 0) rc = p282_copy_path_part(output, capacity, &cursor, "/");
    if (rc == 0) rc = p282_copy_path_part(output, capacity, &cursor, name);
    return rc;
}

static long p316_compatible_is_max77705(
    const char *path, int *compatible) {
    char compatible_path[256];
    char value[128];
    size_t length = 0U;
    size_t cursor = 0U;
    compatible_path[0] = '\0';
    long rc = p282_copy_path_part(
        compatible_path, sizeof(compatible_path), &cursor, path);
    if (rc == 0)
        rc = p282_copy_path_part(
            compatible_path, sizeof(compatible_path), &cursor,
            "/of_node/compatible");
    if (rc != 0) return rc;
    rc = p282_read_file(
        compatible_path, value, sizeof(value), &length);
    if (rc == -ENOENT) {
        *compatible = 0;
        return 0;
    }
    if (rc != 0) return rc;
    static const char exact[] = "maxim,max77705";
    size_t exact_length = sizeof(exact) - 1U;
    size_t start = 0U;
    while (start < length) {
        size_t end = start;
        while (end < length && value[end] != '\0') ++end;
        if (end - start == exact_length
            && p260_bytes_equal(value + start, exact, exact_length)) {
            *compatible = 1;
            return 0;
        }
        start = end + 1U;
    }
    *compatible = 0;
    return 0;
}

static long p316_scan_i2c_topology(
    struct p316_i2c_topology *topology) {
    struct p316_i2c_topology value = {0};
    long rc = p316_find_adapter(&value);
    if (rc != 0) return rc;
    uint8_t buffer[S22_P241_DIRENT_BUFFER_SIZE];
    long fd = p316_dir_open(value.adapter_path);
    if (fd < 0) return fd;
    unsigned int parent_count = 0U;
    unsigned int muic_count = 0U;
    unsigned int wrong_compatible = 0U;
    for (;;) {
        long amount = p241_getdents64((int)fd, buffer, sizeof(buffer));
        if (amount < 0) {
            (void)sys_close((int)fd);
            return amount;
        }
        if (amount == 0) break;
        size_t cursor = 0U;
        while (cursor < (size_t)amount) {
            struct s22_p241_linux_dirent64 *entry =
                (struct s22_p241_linux_dirent64 *)(buffer + cursor);
            size_t header = offsetof(struct s22_p241_linux_dirent64, d_name);
            if (entry->d_reclen < header + 2U
                || cursor + entry->d_reclen > (size_t)amount) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            size_t capacity = entry->d_reclen - header;
            size_t length = 0U;
            while (length < capacity && entry->d_name[length] != '\0')
                ++length;
            if (length == capacity || length == 0U) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            int parent = p316_i2c_client_name(
                entry->d_name, length, value.adapter_name, "0066");
            int muic = p316_i2c_client_name(
                entry->d_name, length, value.adapter_name, "0025");
            if (parent || muic) {
                char path[224];
                rc = p316_client_path(
                    path, sizeof(path), value.adapter_path,
                    entry->d_name);
                if (rc != 0) {
                    (void)sys_close((int)fd);
                    return rc;
                }
                if (parent) {
                    if (++parent_count != 1U || length + 1U >
                        sizeof(value.parent_name)) {
                        (void)sys_close((int)fd);
                        return -EIO;
                    }
                    memcpy(value.parent_name, entry->d_name, length);
                    value.parent_name[length] = '\0';
                    memcpy(value.parent_path, path, cstr_len(path) + 1U);
                } else {
                    if (++muic_count != 1U || length + 1U >
                        sizeof(value.muic_name)) {
                        (void)sys_close((int)fd);
                        return -EIO;
                    }
                    memcpy(value.muic_name, entry->d_name, length);
                    value.muic_name[length] = '\0';
                    memcpy(value.muic_path, path, cstr_len(path) + 1U);
                }
            } else if (p316_i2c_client_on_adapter(
                entry->d_name, length, value.adapter_name)) {
                char path[224];
                int compatible = 0;
                rc = p316_client_path(
                    path, sizeof(path), value.adapter_path,
                    entry->d_name);
                if (rc == 0)
                    rc = p316_compatible_is_max77705(path, &compatible);
                if (rc != 0) {
                    (void)sys_close((int)fd);
                    return rc;
                }
                if (compatible) {
                    if (wrong_compatible == 255U) {
                        (void)sys_close((int)fd);
                        return -P260_EOVERFLOW;
                    }
                    ++wrong_compatible;
                }
            }
            cursor += entry->d_reclen;
        }
    }
    long close_rc = sys_close((int)fd);
    if (close_rc != 0) return close_rc;
    value.parent_present = parent_count == 1U;
    value.muic_count = (uint8_t)muic_count;
    value.wrong_address_compatible_count = (uint8_t)wrong_compatible;
    if (value.parent_present) {
        rc = p316_driver_state(
            value.parent_path, P316_DIAG_MODULE_NAME,
            &value.parent_driver_state);
        if (rc != 0) return rc;
        value.matching_unbound_count =
            value.parent_driver_state == S22PLUS_MAX77705_DRIVER_UNBOUND;
    } else {
        value.parent_driver_state = S22PLUS_MAX77705_DRIVER_ABSENT;
    }
    *topology = value;
    return 0;
}

static void p316_binding_pre(
    struct s22plus_max77705_binding_witness *binding,
    const struct p316_i2c_topology *topology) {
    binding->loader_state = S22PLUS_MAX77705_LOADER_NOT_STARTED;
    binding->pre_exact_parent_present = topology->parent_present;
    binding->pre_exact_parent_driver_state = topology->parent_driver_state;
    binding->pre_matching_unbound_parent_count =
        topology->matching_unbound_count;
    binding->pre_wrong_address_compatible_parent_count =
        topology->wrong_address_compatible_count;
}

static void p316_binding_post(
    struct s22plus_max77705_binding_witness *binding,
    const struct p316_i2c_topology *pre,
    const struct p316_i2c_topology *post) {
    binding->post_exact_parent_driver_state = post->parent_driver_state;
    binding->post_diagnostic_bound_parent_count =
        post->parent_driver_state == S22PLUS_MAX77705_DRIVER_DIAGNOSTIC;
    binding->post_exact_adapter_muic_0x25_client_count = post->muic_count;
    binding->post_foreign_0x25_client_count = pre->muic_count;
}

static __attribute__((noreturn)) void p316_diag_child(
    int pipe_fd, int unrelated_fd, int module_fd) {
    if (unrelated_fd >= 0 && unrelated_fd != pipe_fd)
        (void)sys_close(unrelated_fd);
    struct p316_diag_helper_record record = {
        .magic = P316_DIAG_HELPER_MAGIC,
        .version = P316_DIAG_HELPER_VERSION,
    };
    record.result = (int32_t)p241_finit_module(module_fd, "");
    (void)sys_close(module_fd);
    long amount = sys_write(pipe_fd, &record, sizeof(record));
    (void)sys_close(pipe_fd);
    sys_exit(amount == (long)sizeof(record) ? 0 : 2);
}

static long p316_reap_deadline(long pid, int *status) {
    struct timespec64 deadline = {0};
    long rc = p241_clock_gettime(&deadline);
    if (rc != 0) return rc;
    deadline.tv_sec += P316_DIAG_REAP_MSEC / 1000LL;
    deadline.tv_nsec += (P316_DIAG_REAP_MSEC % 1000LL) * 1000000LL;
    if (deadline.tv_nsec >= 1000000000LL) {
        ++deadline.tv_sec;
        deadline.tv_nsec -= 1000000000LL;
    }
    while (!p282_deadline_expired(&deadline)) {
        long waited = sys_wait4(pid, status, WNOHANG);
        if (waited == pid) return 0;
        if (waited < 0 && waited != -P260_EINTR) return waited;
        p282_poll_delay();
    }
    return -ETIMEDOUT;
}

static int p316_helper_record_valid(
    const struct p316_diag_helper_record *record, int status) {
    return record->magic == P316_DIAG_HELPER_MAGIC
        && record->version == P316_DIAG_HELPER_VERSION
        && record->reserved == 0U && status == 0;
}

static long p316_drain_helper_pipe(
    int pipe_fd, struct p316_diag_helper_record *record,
    size_t *record_bytes) {
    if (record == NULL || record_bytes == NULL
        || *record_bytes > sizeof(*record)) return -EINVAL;
    while (*record_bytes < sizeof(*record)) {
        long amount = sys_read(
            pipe_fd, (uint8_t *)record + *record_bytes,
            sizeof(*record) - *record_bytes);
        if (amount > 0) {
            if ((size_t)amount > sizeof(*record) - *record_bytes)
                return -EIO;
            *record_bytes += (size_t)amount;
            continue;
        }
        if (amount == 0 || amount == -EAGAIN) return 0;
        if (amount == -P260_EINTR) continue;
        return amount;
    }
    return 0;
}

static long p316_abort_and_reap_child(
    long pid, int *child_reaped, int *child_status) {
    if (*child_reaped) return 0;
    (void)sys_kill(pid, SIGKILL);
    long rc = p316_reap_deadline(pid, child_status);
    if (rc == 0) *child_reaped = 1;
    return rc;
}

enum p316_late_evidence_priority {
    P316_LATE_EVIDENCE_NONE = 0,
    P316_LATE_EVIDENCE_LOADER_DEADLINE = 1,
    P316_LATE_EVIDENCE_HELPER_FAILURE = 2,
    P316_LATE_EVIDENCE_RESULT_READ_FAILURE = 3,
};

static uint8_t p316_late_evidence_priority(
    int loader_deadline, int helper_failed, long result_read_error) {
    if (helper_failed) return P316_LATE_EVIDENCE_HELPER_FAILURE;
    if (loader_deadline) return P316_LATE_EVIDENCE_LOADER_DEADLINE;
    if (result_read_error != 0)
        return P316_LATE_EVIDENCE_RESULT_READ_FAILURE;
    return P316_LATE_EVIDENCE_NONE;
}

static void p316_classify_eagain(
    struct p316_diag_observation *observation) {
    if (p316_policy_classify_eagain(
        &observation->binding,
        &observation->semantic_kind,
        &observation->semantic_code) != 0) {
        observation->semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
        observation->semantic_code =
            S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
        observation->observer_site =
            S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY;
        observation->observer_error_class =
            S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT;
    }
}

static void p316_classify_result(
    struct p316_diag_observation *observation) {
    if (p316_policy_classify_result(
        &observation->binding,
        &observation->result,
        &observation->semantic_kind,
        &observation->semantic_code) != 0) {
        observation->semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
        observation->semantic_code =
            S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
        observation->observer_site =
            S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY;
        observation->observer_error_class =
            S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT;
        observation->result_valid = 0U;
    }
}

static long p316_observe_diagnostic(
    int tty_fd, const struct p316_i2c_topology *pre,
    struct p316_diag_observation *observation) {
    (void)tty_fd;
    struct p316_i2c_topology post = {0};
    if (pre == NULL) return -EINVAL;
    p316_binding_pre(&observation->binding, pre);

    char module_path[160];
    long rc = p241_build_module_path(
        module_path, sizeof(module_path), P316_DIAG_MODULE_FILE);
    if (rc != 0) return rc;
    long module_fd = sys_openat(module_path, O_RDONLY | O_CLOEXEC, 0);
    if (module_fd < 0) {
        observation->observer_site =
            S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER;
        return module_fd;
    }
    int pipe_fds[2] = {-1, -1};
    rc = sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK);
    if (rc != 0) {
        (void)sys_close((int)module_fd);
        return rc;
    }
    long pid = sys_clone();
    if (pid < 0) {
        (void)sys_close(pipe_fds[0]);
        (void)sys_close(pipe_fds[1]);
        (void)sys_close((int)module_fd);
        return pid;
    }
    if (pid == 0) {
        (void)sys_close(pipe_fds[0]);
        p316_diag_child(pipe_fds[1], tty_fd, (int)module_fd);
    }
    (void)sys_close(pipe_fds[1]);
    (void)sys_close((int)module_fd);
    observation->binding.loader_state =
        S22PLUS_MAX77705_LOADER_IN_PROGRESS;

    struct timespec64 deadline = {0};
    rc = p282_deadline_after(P316_DIAG_DEADLINE_SEC, &deadline);
    if (rc != 0) {
        int unused_status = 0;
        int child_reaped = 0;
        (void)sys_close(pipe_fds[0]);
        long cleanup_rc = p316_abort_and_reap_child(
            pid, &child_reaped, &unused_status);
        return cleanup_rc != 0 ? cleanup_rc : rc;
    }
    struct p316_diag_helper_record helper = {0};
    size_t helper_bytes = 0U;
    int child_status = 0;
    int child_reaped = 0;
    int result_ready = 0;
    int saw_eagain = 0;
    long result_read_error = 0;
    char result_text[2048];
    size_t result_length = 0U;
    for (;;) {
        if (!result_ready && result_read_error == 0) {
            long read_rc = p282_read_file(
                P316_DIAG_RESULT_PATH,
                result_text, sizeof(result_text), &result_length);
            if (read_rc == 0) {
                result_ready = 1;
            } else if (read_rc == -EAGAIN) {
                saw_eagain = 1;
            } else if (read_rc != -ENOENT) {
                result_read_error = read_rc;
            }
        }
        rc = p316_drain_helper_pipe(
            pipe_fds[0], &helper, &helper_bytes);
        if (rc != 0) {
            (void)sys_close(pipe_fds[0]);
            long cleanup_rc = p316_abort_and_reap_child(
                pid, &child_reaped, &child_status);
            return cleanup_rc != 0 ? cleanup_rc : rc;
        }
        if (!child_reaped) {
            long waited = sys_wait4(pid, &child_status, WNOHANG);
            if (waited == pid) child_reaped = 1;
            else if (waited < 0 && waited != -P260_EINTR) {
                long cleanup_rc = p316_abort_and_reap_child(
                    pid, &child_reaped, &child_status);
                (void)sys_close(pipe_fds[0]);
                return cleanup_rc != 0 ? cleanup_rc : waited;
            }
        }
        if (child_reaped) {
            /*
             * wait4() can observe child exit immediately after the first
             * nonblocking read returned EAGAIN.  Reap is also the proof that
             * no writer can append after this final drain.
             */
            rc = p316_drain_helper_pipe(
                pipe_fds[0], &helper, &helper_bytes);
            if (rc != 0) {
                (void)sys_close(pipe_fds[0]);
                return rc;
            }
            break;
        }
        if (p282_deadline_expired(&deadline)) {
            observation->semantic_kind =
                S22PLUS_MAX77705_SEMANTIC_TERMINAL;
            observation->semantic_code = saw_eagain
                ? S22PLUS_MAX77705_TERMINAL_NOT_READY
                : S22PLUS_MAX77705_TERMINAL_READ_TIMEOUT;
            long cleanup_rc = p316_abort_and_reap_child(
                pid, &child_reaped, &child_status);
            if (cleanup_rc != 0) {
                (void)sys_close(pipe_fds[0]);
                return cleanup_rc;
            }
            if (p316_late_evidence_priority(
                    1, 0, result_read_error)
                != P316_LATE_EVIDENCE_LOADER_DEADLINE) {
                (void)sys_close(pipe_fds[0]);
                return -EIO;
            }
            break;
        }
        p282_poll_delay();
    }
    (void)sys_close(pipe_fds[0]);
    if (observation->semantic_kind != 0U) return 0;
    if (helper_bytes != sizeof(helper)
        || !p316_helper_record_valid(&helper, child_status)) return -EIO;
    if (helper.result > 0) return -EIO;
    uint8_t late_priority = p316_late_evidence_priority(
        0, helper.result < 0, result_read_error);
    if (late_priority == P316_LATE_EVIDENCE_HELPER_FAILURE) {
        observation->binding.loader_state =
            S22PLUS_MAX77705_LOADER_FAILED;
        observation->semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
        observation->semantic_code =
            S22PLUS_MAX77705_TERMINAL_LATE_LOAD_FAILURE;
        return 0;
    }
    if (late_priority != P316_LATE_EVIDENCE_NONE
        && late_priority != P316_LATE_EVIDENCE_RESULT_READ_FAILURE)
        return -EIO;
    observation->binding.loader_state =
        S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS;
    observation->observer_site =
        S22PLUS_MAX77705_OBSERVER_SITE_POST_TOPOLOGY;
    rc = p316_scan_i2c_topology(&post);
    if (rc != 0) return rc;
    observation->observer_site = S22PLUS_MAX77705_OBSERVER_SITE_NONE;
    p316_binding_post(&observation->binding, pre, &post);
    if (late_priority == P316_LATE_EVIDENCE_RESULT_READ_FAILURE) {
        observation->observer_site =
            S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ;
        return result_read_error;
    }
    if (!result_ready) {
        long read_rc = p282_read_file(
            P316_DIAG_RESULT_PATH,
            result_text, sizeof(result_text), &result_length);
        if (read_rc == -EAGAIN) {
            p316_classify_eagain(observation);
            return 0;
        }
        if (read_rc != 0) {
            observation->observer_site =
                S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ;
            return read_rc;
        }
    }
    int parse_rc = s22plus_max77705_runtime_parse_result(
        result_text, result_length,
        &observation->result, &observation->summary);
    if (parse_rc != S22PLUS_MAX77705_RUNTIME_PARSE_OK) {
        observation->semantic_kind =
            S22PLUS_MAX77705_SEMANTIC_TERMINAL;
        observation->semantic_code =
            S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
        observation->observer_site =
            S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY;
        observation->observer_error_class =
            S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT;
        return 0;
    }
    observation->result_valid = 1U;
    p316_classify_result(observation);
    return 0;
}

static void p316_bypass_to_pair(void) {
    if (g_checkpoint.terminal || g_checkpoint.generation > 105U)
        p290_fail_next(P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION);
    while (g_checkpoint.generation < 105U)
        p290_progress_position((uint8_t)g_checkpoint.generation, 0U);
}

static __attribute__((noreturn)) void p316_publish(
    int tty_fd, const struct p316_diag_observation *observation) {
    uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
    uint16_t detail = 0U;
    int rc = s22plus_max77705_encode_envelope(
        &observation->binding,
        observation->semantic_kind,
        observation->semantic_code,
        observation->observer_site,
        observation->observer_error_class,
        observation->result_valid ? &observation->result : NULL,
        observation->result_valid ? &observation->summary : NULL,
        envelope, &detail);
    if (rc != 0)
        p290_fail_next(P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION);
    p316_bypass_to_pair();
    long publish_rc = s22_max77705_checkpoint_payload_progress_position(
        &g_checkpoint, 105U, S22PLUS_MAX77705_A_DETAIL, envelope);
    if (publish_rc == 0)
        publish_rc = s22_max77705_checkpoint_payload_terminal_position(
            &g_checkpoint, 106U, detail, envelope + 64U);
    if (publish_rc != 0) p292_park_after_checkpoint_error(publish_rc);
    if (tty_fd >= 0) (void)p260_write_banner(tty_fd);
    p290_park_after_confirmed_publication();
}

static uint8_t p316_observer_error_class(long operation_error) {
    if (operation_error == -ENOENT || operation_error == -ENODEV)
        return S22PLUS_MAX77705_OBSERVER_ERROR_NOT_FOUND;
    if (operation_error == -P260_EBUSY)
        return S22PLUS_MAX77705_OBSERVER_ERROR_BUSY;
    if (operation_error == -ETIMEDOUT || operation_error == -EAGAIN)
        return S22PLUS_MAX77705_OBSERVER_ERROR_TIMEOUT_RETRY;
    if (operation_error == -EIO || operation_error == -EINVAL
        || operation_error == -P260_EOVERFLOW)
        return S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT;
    if (operation_error == -P260_EINTR)
        return S22PLUS_MAX77705_OBSERVER_ERROR_INTERRUPTED;
    return operation_error < 0
        ? S22PLUS_MAX77705_OBSERVER_ERROR_OTHER_NEGATIVE
        : S22PLUS_MAX77705_OBSERVER_ERROR_NONNEGATIVE;
}

static __attribute__((noreturn)) void p316_fail_observer(
    int tty_fd, unsigned int observer_site, long operation_error,
    const struct p316_diag_observation *prior) {
    struct p316_diag_observation observation = {0};
    if (prior != NULL) observation = *prior;
    if (observer_site < S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE
        || observer_site > S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ)
        observer_site = S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY;
    if (prior == NULL)
        observation.binding.loader_state =
            S22PLUS_MAX77705_LOADER_NOT_STARTED;
    observation.semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
    observation.semantic_code =
        S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
    observation.result_valid = 0U;
    observation.observer_site = (uint8_t)observer_site;
    observation.observer_error_class =
        p316_observer_error_class(operation_error);
    p316_publish(tty_fd, &observation);
}

static __attribute__((noreturn)) void p316_run(void) {
    /* Keep the frozen predecessor entrypoint linked for source-delta audits. */
    (void)p313_run;
    p260_derive_identity();
    long rc = p260_mount_configfs();
    if (rc != 0) fail_at(P260_CONFIG_STAGE, 0U, rc);
    p260_progress(P260_CONFIG_STAGE);
    rc = p260_create_gadget();
    if (rc != 0) fail_at(P260_GADGET_STAGE, 0U, rc);
    p260_progress(P260_GADGET_STAGE);
    unsigned int major_number = 0U;
    unsigned int minor_number = 0U;
    rc = p260_wait_tty_dev(&major_number, &minor_number);
    if (rc != 0) fail_at(P260_TTY_CLASS_STAGE, 0U, rc);
    p260_progress(P260_TTY_CLASS_STAGE);
    rc = p260_prepare_tty_node(major_number, minor_number);
    int tty_fd = -1;
    if (rc == 0) rc = p260_open_raw_tty(&tty_fd);
    if (rc != 0) fail_at(P260_TTY_RAW_STAGE, 0U, rc);
    p260_progress(P260_TTY_RAW_STAGE);

    p290_progress_position(S22_P313_POSITION_BANNER_DEFERRED, 0U);
    uint16_t role_warning = 0U;
    rc = p282_phase_role(&role_warning, tty_fd);
    if (rc != 0 || role_warning != 0U || !g_p313_role_qscratch_valid
        || ((g_p313_role_qscratch >> 20U) & 1U) == 0U
        || ((g_p313_role_qscratch >> 28U) & 1U) == 0U)
        p290_fail_next(rc != 0 ? rc : P313_DETAIL_ROLE_QSCRATCH_VALUE);
    p290_progress_position(S22_P313_POSITION_ROLE_READY, 0U);

    struct p282_trace_control direct_control = {0};
    rc = p282_trace_setup(P282_PHASE_BIND, &direct_control);
    if (rc != 0) p290_fail_next(p313_setup_detail(rc));
    p290_progress_position(S22_P313_POSITION_DIRECT_OBSERVER_READY, 0U);
    rc = p260_bind_udc();
    if (rc != 0) p298_fail_with_trace(&direct_control, rc);
    p290_progress_position(S22_P313_POSITION_DIRECT_BIND_RETURNED, 0U);

    rc = p282_trace_read_snapshot(&direct_control, 0);
    struct p282_bind_trace_result direct_initial = {0};
    if (rc == 0)
        rc = p300_parse_bind_stream(&direct_control, &direct_initial, 0);
    if (rc != 0 || p298_start_result_detail(&direct_initial) != 0)
        p298_fail_with_trace(&direct_control,
            rc != 0 ? rc : P313_DETAIL_DIRECT_STREAM_INTEGRITY);
    p290_progress_position(S22_P313_POSITION_DIRECT_START_CLASSIFIED, 0U);
    p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_STARTED, 0U);
    unsigned int direct_state = 0U;
    unsigned int direct_speed = 0U;
    int direct_configured = 0;
    rc = p313_wait_state_window(P282_FINAL_DEADLINE_SEC,
        &direct_state, &direct_speed, &direct_configured);
    if (rc != 0) p298_fail_with_trace(&direct_control, rc);
    struct p282_bind_trace_result direct = {0};
    long direct_detail = p313_finish_direct(&direct_control, &direct);
    p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);
    if (direct_detail != 0) p290_fail_next(direct_detail);
    if (!direct_configured && !direct.connect_done_seen
        && !p313_direct_known_baseline(&direct))
        p290_fail_next(P313_DIRECT_NONBASELINE_ACTIVITY);
    p290_progress_position(S22_P313_POSITION_BRANCH_SELECTED, 0U);

    rc = p316_verify_substrate_bindings();
    if (rc != 0) p316_fail_observer(
        tty_fd, S22PLUS_MAX77705_OBSERVER_SITE_SUBSTRATE_VERIFY, rc, NULL);
    p290_progress_position(P316_POSITION_SUBSTRATE_VERIFIED, 0U);
    struct p316_i2c_topology topology = {0};
    rc = p316_scan_i2c_topology(&topology);
    if (rc != 0) p316_fail_observer(
        tty_fd, S22PLUS_MAX77705_OBSERVER_SITE_PRE_TOPOLOGY, rc, NULL);
    p290_progress_position(P316_POSITION_TOPOLOGY_VERIFIED, 0U);
    p290_progress_position(P316_POSITION_DIAGNOSTIC_DISPATCHED, 0U);
    struct p316_diag_observation observation = {0};
    rc = p316_observe_diagnostic(tty_fd, &topology, &observation);
    if (rc != 0) p316_fail_observer(
        tty_fd,
        observation.observer_site != S22PLUS_MAX77705_OBSERVER_SITE_NONE
            ? observation.observer_site
            : S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER,
        rc, &observation);
    p290_progress_position(P316_POSITION_DIAGNOSTIC_RETURNED, 0U);
    p290_progress_position(P316_POSITION_BINDING_CAPTURED, 0U);
    p290_progress_position(P316_POSITION_RESULT_PARSED, 0U);
    p290_progress_position(P316_POSITION_RESULT_CLASSIFIED, 0U);
    p290_progress_position(P316_POSITION_ENVELOPE_READY, 0U);
    p316_publish(tty_fd, &observation);
}
