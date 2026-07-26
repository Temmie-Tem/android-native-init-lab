/* P2.60 E3 one-shot generic ACM banner, included after the E2 helpers. */

#define P260_NR_IOCTL 29
#define P260_NR_SYMLINKAT 36
#define P260_O_NOCTTY 00000400
#define P260_CONFIGFS_MAGIC 0x62656570L
#define P260_EINTR 4
#define P260_EBUSY 16
#define P260_ENOTTY 25
#define P260_EPROTO 71
#define P260_EOVERFLOW 75
#define P260_TCGETS 0x5401U
#define P260_TCSETS 0x5402U
#define P260_CSIZE 0000060U
#define P260_CS8 0000060U
#define P260_CREAD 0000200U
#define P260_PARENB 0000400U
#define P260_CLOCAL 0004000U
#define P260_CONFIG_STAGE 0x88U
#define P260_GADGET_STAGE 0x89U
#define P260_TTY_CLASS_STAGE 0x8aU
#define P260_TTY_RAW_STAGE 0x8bU
#define P260_BANNER_STAGE 0x8cU
#define P260_ROLE_UDC_STAGE 0x8dU
#define P260_UDC_BIND_STAGE 0x8eU
#define P260_CONFIGURED_STAGE 0x8fU
#define P260_POLL_NS 100000000LL
#define P260_SHORT_TIMEOUT_SEC 5LL
#define P260_CONFIGURED_TIMEOUT_SEC 30LL

struct p260_termios {
    uint32_t c_iflag;
    uint32_t c_oflag;
    uint32_t c_cflag;
    uint32_t c_lflag;
    uint8_t c_line;
    uint8_t c_cc[19];
};

_Static_assert(sizeof(struct p260_termios) == 36U, "arm64 termios size");

static const char p260_gadget_root[] = "/config/usb_gadget/g1";
static const char p260_udc_name[] = "a600000.dwc3";
static const char p260_role_path[] =
    "/sys/devices/platform/soc/a600000.ssusb/mode";
static const char p260_link_create_target[] =
    "/config/usb_gadget/g1/functions/acm.usb0";
static const char p260_link_readback_target[] =
    "../../../../usb_gadget/g1/functions/acm.usb0";
static char p260_usb_serial[38];
static char p260_banner[50];

void *memcpy(void *destination, const void *source, size_t count) {
    uint8_t *output = (uint8_t *)destination;
    const uint8_t *input = (const uint8_t *)source;
    for (size_t index = 0; index < count; ++index) {
        output[index] = input[index];
    }
    return destination;
}

static long p260_ioctl(int fd, unsigned long request, void *argument) {
    return syscall6(
        P260_NR_IOCTL,
        fd,
        (long)request,
        (long)(uintptr_t)argument,
        0,
        0,
        0);
}

static long p260_symlinkat(const char *target, const char *path) {
    return syscall6(
        P260_NR_SYMLINKAT,
        (long)(uintptr_t)target,
        AT_FDCWD,
        (long)(uintptr_t)path,
        0,
        0,
        0);
}

static int p260_bytes_equal(
    const char *left, const char *right, size_t length) {
    for (size_t index = 0; index < length; ++index) {
        if (left[index] != right[index]) {
            return 0;
        }
    }
    return 1;
}

static long p260_read_value(
    const char *path, char *buffer, size_t capacity, size_t *length) {
    if (capacity < 2U || length == NULL) {
        return -EINVAL;
    }
    long fd = sys_openat(path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long amount;
    do {
        amount = sys_read((int)fd, buffer, capacity - 1U);
    } while (amount == -P260_EINTR);
    char extra = '\0';
    long extra_amount = amount >= 0 ? sys_read((int)fd, &extra, 1U) : 0;
    long close_rc = sys_close((int)fd);
    if (amount < 0) {
        return amount;
    }
    if (extra_amount < 0) {
        return extra_amount;
    }
    if (close_rc != 0) {
        return close_rc;
    }
    if (extra_amount != 0 || amount == 0) {
        return extra_amount != 0 ? -P260_EOVERFLOW : -EIO;
    }
    size_t used = (size_t)amount;
    if (buffer[used - 1U] != '\n') {
        return -P260_EPROTO;
    }
    --used;
    buffer[used] = '\0';
    *length = used;
    return 0;
}

static long p260_expect_value(const char *path, const char *expected) {
    char value[128];
    size_t length = 0;
    long rc = p260_read_value(path, value, sizeof(value), &length);
    size_t expected_length = cstr_len(expected);
    if (rc != 0) {
        return rc;
    }
    return length == expected_length
            && p260_bytes_equal(value, expected, length)
        ? 0
        : -EIO;
}

static long p260_write_all(
    int fd, const char *data, size_t size, int retry_eagain) {
    struct timespec64 deadline = {0};
    if (retry_eagain) {
        if (p241_clock_gettime(&deadline) != 0) {
            return -EIO;
        }
        deadline.tv_sec += P260_SHORT_TIMEOUT_SEC;
    }
    size_t written = 0;
    while (written < size) {
        long rc = sys_write(fd, data + written, size - written);
        if (rc == -P260_EINTR) {
            continue;
        }
        if (rc == -EAGAIN && retry_eagain) {
            struct timespec64 now = {0};
            if (p241_clock_gettime(&now) != 0) {
                return -EIO;
            }
            if (!p241_timespec_before(&now, &deadline)) {
                return -ETIMEDOUT;
            }
            (void)sys_nanosleep(P260_POLL_NS);
            continue;
        }
        if (rc <= 0 || (size_t)rc > size - written) {
            return rc < 0 ? rc : -EIO;
        }
        written += (size_t)rc;
    }
    return 0;
}

static long p260_write_value(const char *path, const char *value) {
    long fd = sys_openat(path, O_RDWR | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long rc = p260_write_all((int)fd, value, cstr_len(value), 0);
    long close_rc = sys_close((int)fd);
    return rc != 0 ? rc : close_rc;
}

static long p260_write_and_verify(
    const char *path, const char *value, const char *expected) {
    long rc = p260_write_value(path, value);
    return rc != 0 ? rc : p260_expect_value(path, expected);
}

static long p260_mkdir_fresh(const char *path) {
    long rc = sys_mkdirat(path, 0755);
    return rc == 0 ? 0 : rc;
}

static long p260_verify_link(
    const char *path, const char *expected_target) {
    struct s22_p241_kernel_stat stat_buffer = {0};
    long rc = p241_newfstatat(path, &stat_buffer, AT_SYMLINK_NOFOLLOW);
    if (rc != 0) {
        return rc;
    }
    if ((stat_buffer.st_mode & S_IFMT) != S_IFLNK) {
        return -EIO;
    }
    char target[128];
    long size = p241_readlinkat(path, target, sizeof(target));
    size_t expected_size = cstr_len(expected_target);
    if (
        size < 0
        || (size_t)size != expected_size
        || !p260_bytes_equal(target, expected_target, expected_size)
    ) {
        return size < 0 ? size : -EIO;
    }
    return 0;
}

static uint64_t p260_make_dev(
    unsigned int major_number, unsigned int minor_number) {
    return ((uint64_t)(minor_number & 0xffU))
        | ((uint64_t)(major_number & 0xfffU) << 8)
        | ((uint64_t)(minor_number & ~0xffU) << 12)
        | ((uint64_t)(major_number & ~0xfffU) << 32);
}

static void p260_revalidate_or_fail(uint8_t frontier_stage) {
    for (size_t index = 0; index < S22PLUS_O2_BIND_GATE_COUNT; ++index) {
        long rc = p241_check_gate(index);
        if (rc != 0) {
            long detail = rc == -ENODEV
                ? S22_P248_DETAIL_REGRESSION_BASE + (long)index
                : S22_P248_DETAIL_READ_ERROR_BASE + (long)index;
            fail_at(frontier_stage, 0U, detail);
        }
    }
}

static void p260_progress(uint8_t stage) {
    p260_revalidate_or_fail(stage);
    if (s22_r4w1e_checkpoint_progress(&g_checkpoint, stage, 0U) != 0) {
        quiet_park();
    }
}

static long p260_mount_configfs(void) {
    long rc = sys_mkdirat("/config", 0755);
    if (rc != 0 && rc != -EEXIST) {
        return rc;
    }
    rc = sys_mount(
        "configfs",
        "/config",
        "configfs",
        MS_NOSUID | MS_NODEV | MS_NOEXEC,
        "");
    if (rc != 0 && rc != -P260_EBUSY) {
        return rc;
    }
    struct statfs_probe probe = {0};
    rc = sys_statfs("/config", &probe);
    if (rc != 0) {
        return rc;
    }
    return probe.f_type == P260_CONFIGFS_MAGIC ? 0 : -EIO;
}

static char p260_hex_digit(uint8_t value) {
    return value < 10U
        ? (char)('0' + (int)value)
        : (char)('a' + (int)value - 10);
}

static void p260_derive_identity(void) {
    static const char serial_prefix[] = "S22E3";
    static const char banner_prefix[] = "S22PLUS-FYG8-E3:";
    const volatile uint8_t *run_id =
        (const volatile uint8_t *)(const void *)k_run_id;
    size_t cursor = 0;
    for (; cursor < sizeof(serial_prefix) - 1U; ++cursor) {
        p260_usb_serial[cursor] = serial_prefix[cursor];
    }
    for (size_t index = 0; index < sizeof(k_run_id); ++index) {
        uint8_t value = run_id[index];
        p260_usb_serial[cursor++] = p260_hex_digit(value >> 4);
        p260_usb_serial[cursor++] =
            p260_hex_digit(value & 0x0fU);
    }
    p260_usb_serial[cursor] = '\0';

    cursor = 0;
    for (; cursor < sizeof(banner_prefix) - 1U; ++cursor) {
        p260_banner[cursor] = banner_prefix[cursor];
    }
    for (size_t index = 0; index < sizeof(k_run_id); ++index) {
        uint8_t value = run_id[index];
        p260_banner[cursor++] = p260_hex_digit(value >> 4);
        p260_banner[cursor++] = p260_hex_digit(value & 0x0fU);
    }
    p260_banner[cursor++] = '\n';
    p260_banner[cursor] = '\0';
}

static long p260_create_gadget(void) {
    static const char *const directories[] = {
        "/config/usb_gadget/g1",
        "/config/usb_gadget/g1/strings/0x409",
        "/config/usb_gadget/g1/configs/b.1",
        "/config/usb_gadget/g1/configs/b.1/strings/0x409",
        "/config/usb_gadget/g1/functions/acm.usb0",
    };
    for (
        size_t index = 0;
        index < sizeof(directories) / sizeof(directories[0]);
        ++index
    ) {
        long rc = p260_mkdir_fresh(directories[index]);
        if (rc != 0) {
            return rc;
        }
    }
    struct p260_attr {
        const char *path;
        const char *value;
        const char *expected;
    };
    const struct p260_attr attributes[] = {
        {"/config/usb_gadget/g1/idVendor", "0x04e8", "0x04e8"},
        {"/config/usb_gadget/g1/idProduct", "0x6861", "0x6861"},
        {"/config/usb_gadget/g1/bcdUSB", "0x0200", "0x0200"},
        {"/config/usb_gadget/g1/bcdDevice", "0x0003", "0x0003"},
        {"/config/usb_gadget/g1/max_speed", "high-speed", "high-speed"},
        {
            "/config/usb_gadget/g1/strings/0x409/manufacturer",
            "Android Native Init Lab",
            "Android Native Init Lab",
        },
        {
            "/config/usb_gadget/g1/strings/0x409/product",
            "S22+ E3 ACM",
            "S22+ E3 ACM",
        },
        {
            "/config/usb_gadget/g1/strings/0x409/serialnumber",
            p260_usb_serial,
            p260_usb_serial,
        },
        {
            "/config/usb_gadget/g1/configs/b.1/bmAttributes",
            "0x80",
            "0x80",
        },
        {
            "/config/usb_gadget/g1/configs/b.1/MaxPower",
            "500",
            "500",
        },
        {
            "/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration",
            "acm",
            "acm",
        },
    };
    for (
        size_t index = 0;
        index < sizeof(attributes) / sizeof(attributes[0]);
        ++index
    ) {
        long rc = p260_write_and_verify(
            attributes[index].path,
            attributes[index].value,
            attributes[index].expected);
        if (rc != 0) {
            return rc;
        }
    }
    static const char link_path[] =
        "/config/usb_gadget/g1/configs/b.1/acm.usb0";
    long rc = p260_symlinkat(p260_link_create_target, link_path);
    return rc != 0
        ? rc
        : p260_verify_link(link_path, p260_link_readback_target);
}

static long p260_parse_dev(
    const char *text,
    size_t length,
    unsigned int *major_number,
    unsigned int *minor_number) {
    if (length < 3U || major_number == NULL || minor_number == NULL) {
        return -EINVAL;
    }
    uint64_t major_value = 0;
    uint64_t minor_value = 0;
    size_t cursor = 0;
    if (text[cursor] < '0' || text[cursor] > '9') {
        return -EINVAL;
    }
    while (cursor < length && text[cursor] >= '0' && text[cursor] <= '9') {
        major_value = major_value * 10U + (uint64_t)(text[cursor] - '0');
        if (major_value > 0xfffU) {
            return -P260_EOVERFLOW;
        }
        ++cursor;
    }
    if (cursor >= length || text[cursor++] != ':') {
        return -EINVAL;
    }
    if (cursor >= length || text[cursor] < '0' || text[cursor] > '9') {
        return -EINVAL;
    }
    while (cursor < length && text[cursor] >= '0' && text[cursor] <= '9') {
        minor_value = minor_value * 10U + (uint64_t)(text[cursor] - '0');
        if (minor_value > 0xfffffU) {
            return -P260_EOVERFLOW;
        }
        ++cursor;
    }
    if (cursor != length) {
        return -EINVAL;
    }
    *major_number = (unsigned int)major_value;
    *minor_number = (unsigned int)minor_value;
    return 0;
}

static long p260_wait_tty_dev(
    unsigned int *major_number, unsigned int *minor_number) {
    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        return -EIO;
    }
    deadline.tv_sec += P260_SHORT_TIMEOUT_SEC;
    for (;;) {
        char value[32];
        size_t length = 0;
        long rc = p260_read_value(
            "/sys/class/tty/ttyGS0/dev", value, sizeof(value), &length);
        if (rc == 0) {
            return p260_parse_dev(
                value, length, major_number, minor_number);
        }
        if (rc != -ENOENT && rc != -ENODEV) {
            return rc;
        }
        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            return -EIO;
        }
        if (!p241_timespec_before(&now, &deadline)) {
            return -ETIMEDOUT;
        }
        (void)sys_nanosleep(P260_POLL_NS);
    }
}

static long p260_prepare_tty_node(
    unsigned int major_number, unsigned int minor_number) {
    struct s22_p241_kernel_stat stat_buffer = {0};
    uint64_t expected = p260_make_dev(major_number, minor_number);
    long rc = p241_newfstatat("/dev/ttyGS0", &stat_buffer, 0);
    if (rc == -ENOENT) {
        rc = sys_mknodat(
            "/dev/ttyGS0",
            S_IFCHR | 0600U,
            expected);
        if (rc != 0) {
            return rc;
        }
        rc = p241_newfstatat("/dev/ttyGS0", &stat_buffer, 0);
    }
    if (rc != 0) {
        return rc;
    }
    return (stat_buffer.st_mode & S_IFMT) == S_IFCHR
            && stat_buffer.st_rdev == expected
        ? 0
        : -EIO;
}

static long p260_open_raw_tty(int *result_fd) {
    long fd = sys_openat(
        "/dev/ttyGS0",
        O_RDWR | P260_O_NOCTTY | O_NONBLOCK | O_CLOEXEC,
        0);
    if (fd < 0) {
        return fd;
    }
    struct p260_termios termios_value = {0};
    long rc = p260_ioctl((int)fd, P260_TCGETS, &termios_value);
    if (rc == 0) {
        termios_value.c_iflag = 0;
        termios_value.c_oflag = 0;
        termios_value.c_lflag = 0;
        termios_value.c_cflag &=
            ~(P260_CSIZE | P260_PARENB);
        termios_value.c_cflag |= P260_CS8 | P260_CREAD | P260_CLOCAL;
        rc = p260_ioctl((int)fd, P260_TCSETS, &termios_value);
    }
    struct p260_termios readback = {0};
    if (rc == 0) {
        rc = p260_ioctl((int)fd, P260_TCGETS, &readback);
    }
    if (
        rc == 0
        && (
            readback.c_iflag != 0
            || readback.c_oflag != 0
            || readback.c_lflag != 0
            || (
                readback.c_cflag
                & (P260_CSIZE | P260_PARENB | P260_CREAD | P260_CLOCAL)
            ) != (P260_CS8 | P260_CREAD | P260_CLOCAL)
        )
    ) {
        rc = -EIO;
    }
    if (rc != 0) {
        (void)sys_close((int)fd);
        return rc == -P260_ENOTTY ? -EIO : rc;
    }
    *result_fd = (int)fd;
    return 0;
}

static long p260_wait_role_and_udc(void) {
    char value[32];
    size_t length = 0;
    long rc = p260_read_value(
        p260_role_path, value, sizeof(value), &length);
    if (rc != 0) {
        return rc;
    }
    int peripheral = length == 10U
        && p260_bytes_equal(value, "peripheral", 10U);
    int writable = (
        length == 4U && p260_bytes_equal(value, "none", 4U)
    ) || (
        length == 4U && p260_bytes_equal(value, "host", 4U)
    );
    if (!peripheral && !writable) {
        return -P260_EPROTO;
    }
    if (!peripheral) {
        rc = p260_write_value(p260_role_path, "peripheral");
        if (rc != 0) {
            return rc;
        }
    }
    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        return -EIO;
    }
    deadline.tv_sec += P260_SHORT_TIMEOUT_SEC;
    for (;;) {
        rc = p260_expect_value(p260_role_path, "peripheral");
        long udc_rc = p241_check_gate(S22_P258_UDC_GATE_INDEX);
        if (rc == 0 && udc_rc == 0) {
            return 0;
        }
        if (
            rc != 0
            && rc != -ENOENT
            && rc != -ENODEV
            && rc != -EIO
        ) {
            return rc;
        }
        if (
            udc_rc != 0
            && udc_rc != -ENOENT
            && udc_rc != -ENODEV
        ) {
            return udc_rc;
        }
        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            return -EIO;
        }
        if (!p241_timespec_before(&now, &deadline)) {
            return -ETIMEDOUT;
        }
        (void)sys_nanosleep(P260_POLL_NS);
    }
}

static long p260_bind_udc(void) {
    char value[64];
    size_t length = 0;
    long rc = p260_read_value(
        "/config/usb_gadget/g1/UDC", value, sizeof(value), &length);
    if (rc != 0) {
        return rc;
    }
    if (length != 0U) {
        return -EEXIST;
    }
    return p260_write_and_verify(
        "/config/usb_gadget/g1/UDC",
        p260_udc_name,
        p260_udc_name);
}

static long p260_wait_configured(void) {
    struct timespec64 deadline = {0};
    if (p241_clock_gettime(&deadline) != 0) {
        return -EIO;
    }
    deadline.tv_sec += P260_CONFIGURED_TIMEOUT_SEC;
    for (;;) {
        p260_revalidate_or_fail(P260_CONFIGURED_STAGE);
        char state[32];
        char speed[32];
        size_t state_length = 0;
        size_t speed_length = 0;
        long state_rc = p260_read_value(
            "/sys/class/udc/a600000.dwc3/state",
            state,
            sizeof(state),
            &state_length);
        long speed_rc = p260_read_value(
            "/sys/class/udc/a600000.dwc3/current_speed",
            speed,
            sizeof(speed),
            &speed_length);
        if (state_rc != 0) {
            return state_rc;
        }
        if (speed_rc != 0) {
            return speed_rc;
        }
        int configured = state_length == 10U
            && p260_bytes_equal(state, "configured", 10U);
        int high_speed = speed_length == 10U
            && p260_bytes_equal(speed, "high-speed", 10U);
        if (configured) {
            return high_speed ? 0 : -P260_EPROTO;
        }
        struct timespec64 now = {0};
        if (p241_clock_gettime(&now) != 0) {
            return -EIO;
        }
        if (!p241_timespec_before(&now, &deadline)) {
            return -ETIMEDOUT;
        }
        (void)sys_nanosleep(P260_POLL_NS);
    }
}

static __attribute__((noreturn)) void p260_e3_run(void) {
    p260_derive_identity();

    long rc = p260_mount_configfs();
    if (rc != 0) {
        fail_at(P260_CONFIG_STAGE, 0U, rc);
    }
    p260_progress(P260_CONFIG_STAGE);

    rc = p260_create_gadget();
    if (rc != 0) {
        fail_at(P260_GADGET_STAGE, 0U, rc);
    }
    p260_progress(P260_GADGET_STAGE);

    unsigned int major_number = 0;
    unsigned int minor_number = 0;
    rc = p260_wait_tty_dev(&major_number, &minor_number);
    if (rc != 0) {
        fail_at(P260_TTY_CLASS_STAGE, 0U, rc);
    }
    p260_progress(P260_TTY_CLASS_STAGE);

    rc = p260_prepare_tty_node(major_number, minor_number);
    int tty_fd = -1;
    if (rc == 0) {
        rc = p260_open_raw_tty(&tty_fd);
    }
    if (rc != 0) {
        fail_at(P260_TTY_RAW_STAGE, 0U, rc);
    }
    p260_progress(P260_TTY_RAW_STAGE);

    rc = p260_write_all(
        tty_fd, p260_banner, sizeof(p260_banner) - 1U, 1);
    if (rc != 0) {
        fail_at(P260_BANNER_STAGE, 0U, rc);
    }
    p260_progress(P260_BANNER_STAGE);

    rc = p260_wait_role_and_udc();
    if (rc != 0) {
        fail_at(P260_ROLE_UDC_STAGE, 0U, rc);
    }
    p260_progress(P260_ROLE_UDC_STAGE);

    rc = p260_bind_udc();
    if (rc != 0) {
        fail_at(P260_UDC_BIND_STAGE, 0U, rc);
    }
    p260_progress(P260_UDC_BIND_STAGE);

    rc = p260_wait_configured();
    if (rc != 0) {
        fail_at(P260_CONFIGURED_STAGE, 0U, rc);
    }
    p260_progress(P260_CONFIGURED_STAGE);

    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {
        quiet_park();
    }
    quiet_park();
}
