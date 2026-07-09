// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ native-init M34 runtime gadget split candidate.
 *
 * M34 starts from the P30-proven full ACM module closure and isolates the stock
 * runtime gadget sequence. Stage 1 creates the configfs gadget/function/config
 * with stock-style UDC=none unbind and no pullup. Stage 2 adds the original two
 * off-stock HS-only/PD-less knobs: max_speed=high-speed and usb_role=device,
 * still with no UDC bind. Stage 3 adds the UDC bind/pullup. Stage 4 replaces the
 * now-proven-dead usb_role path with the stock-kernel-proven ssusb role lever
 * before UDC bind. Stage 5 keeps S4 and adds the UDC soft_connect fallback after
 * bind. Stage 6 removes all high-speed forcing, keeps the ssusb mode role lever,
 * restores the stock QMP/EUD/ucsi module softdep parity through the module list,
 * and does not write EUD sysfs knobs. Stage 7A adds the stock max77705/PDIC/
 * altmode session-producer module chain and read-only TypeC/UDC snapshots while
 * keeping the S6 ACM-only gadget and no soft_connect. Stage 7A2 adds the GENI
 * I2C transport required for the max77705 994000.i2c bus, and if no TypeC
 * partner is visible, writes the same TypeC role nodes the stock USB HAL owns
 * as a bounded host-visible discriminator. Stage 8B1 keeps the S7A2 module
 * recipe but uses reboot(download) as a one-bit beacon for whether the max77705
 * TypeC port or exact Android-observed I2C device appeared. Stage 8B1A keeps
 * the same recipe but scans all I2C adapter entries for any *-0066 max77705
 * device to remove the Android bus-number assumption. S1..S7A2 remain direct-PID1 park
 * candidates with no Android handoff, no reboot request, no persistent mount,
 * and no block writes.
 */

#include <stdint.h>
#include <stddef.h>

#ifndef M34_STAGE
#define M34_STAGE 1
#endif

#ifndef M34_STAGE_NAME
#define M34_STAGE_NAME "S1"
#endif

#ifndef M34_MARKER
#define M34_MARKER "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S1"
#endif

#ifndef M34_MODULE_LIMIT
#define M34_MODULE_LIMIT 0
#endif

#ifndef M34_MODULES_RAMDISK
#define M34_MODULES_RAMDISK "/s22plus_m34_s1_runtime_gadget_split.modules"
#endif

#define STR_INNER(x) #x
#define STR(x) STR_INNER(x)

#define AT_FDCWD (-100)

#define O_RDONLY 00000000
#define O_WRONLY 00000001
#define O_DIRECTORY 00200000
#define O_CLOEXEC 02000000

#define S_IFCHR 0020000

#define MS_NOSUID 2UL
#define MS_NODEV 4UL
#define MS_NOEXEC 8UL

#define EBUSY 16
#define EEXIST 17

#define NR_MKNODAT 33
#define NR_MKDIRAT 34
#define NR_UNLINKAT 35
#define NR_SYMLINKAT 36
#define NR_MOUNT 40
#define NR_OPENAT 56
#define NR_CLOSE 57
#define NR_GETDENTS64 61
#define NR_READ 63
#define NR_WRITE 64
#define NR_NANOSLEEP 101
#if M34_STAGE >= 9
#define NR_REBOOT 142
#define LINUX_REBOOT_MAGIC1 0xfee1deadUL
#define LINUX_REBOOT_MAGIC2 672274793UL
#define LINUX_REBOOT_CMD_RESTART2 0xa1b2c3d4UL
#endif
#define NR_FINIT_MODULE 273

#define MODULES_LOAD_BUF 4096
#define MODULE_NAME_BUF 96

struct linux_dirent64 {
    uint64_t d_ino;
    int64_t d_off;
    unsigned short d_reclen;
    unsigned char d_type;
    char d_name[];
};

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

struct sbuf {
    char data[768];
    size_t len;
};

static const char k_marker[] =
#if M34_STAGE >= 9
    M34_MARKER " version=0.8 pid1=direct runtime=freestanding raw_syscalls=1 "
#else
    M34_MARKER " version=0.6 pid1=direct runtime=freestanding raw_syscalls=1 "
#endif
    "stage=" M34_STAGE_NAME " runtime_step=" M34_STAGE_NAME " "
    "modules_dep_complete=" M34_MODULES_RAMDISK " module_count=" STR(M34_MODULE_LIMIT) " "
    "module_source=stock_vendor_boot_ramdisk module_list=dep_complete_runtime_gadget_split "
#if M34_STAGE == 1
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=0 role_force=0 ssusb_speed_high_speed=0 ssusb_mode_peripheral=0 udc_bind=0 soft_connect=0 stock_softdep_parity=0 qmp_module=0 eud_module=0 ucsi_glink=0 session_producer_parity=0 max77705_session=0 typec_readback=0 geni_i2c_transport=0 role_write_discriminator=0 "
#elif M34_STAGE == 2
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=1 role_force=1 ssusb_speed_high_speed=0 ssusb_mode_peripheral=0 udc_bind=0 soft_connect=0 stock_softdep_parity=0 qmp_module=0 eud_module=0 ucsi_glink=0 session_producer_parity=0 max77705_session=0 typec_readback=0 geni_i2c_transport=0 role_write_discriminator=0 "
#elif M34_STAGE == 3
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=1 role_force=1 ssusb_speed_high_speed=0 ssusb_mode_peripheral=0 udc_bind=1 soft_connect=0 stock_softdep_parity=0 qmp_module=0 eud_module=0 ucsi_glink=0 session_producer_parity=0 max77705_session=0 typec_readback=0 geni_i2c_transport=0 role_write_discriminator=0 "
#elif M34_STAGE == 4
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=1 role_force=0 ssusb_speed_high_speed=1 ssusb_mode_peripheral=1 udc_bind=1 soft_connect=0 stock_softdep_parity=0 qmp_module=0 eud_module=0 ucsi_glink=0 session_producer_parity=0 max77705_session=0 typec_readback=0 geni_i2c_transport=0 role_write_discriminator=0 "
#elif M34_STAGE == 5
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=1 role_force=0 ssusb_speed_high_speed=1 ssusb_mode_peripheral=1 udc_bind=1 soft_connect=1 stock_softdep_parity=0 qmp_module=0 eud_module=0 ucsi_glink=0 session_producer_parity=0 max77705_session=0 typec_readback=0 geni_i2c_transport=0 role_write_discriminator=0 "
#elif M34_STAGE == 6
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=0 role_force=0 ssusb_speed_high_speed=0 ssusb_mode_peripheral=1 udc_bind=1 soft_connect=0 stock_softdep_parity=1 qmp_module=1 eud_module=1 ucsi_glink=1 session_producer_parity=0 max77705_session=0 typec_readback=0 geni_i2c_transport=0 role_write_discriminator=0 "
#elif M34_STAGE == 7
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=0 role_force=0 ssusb_speed_high_speed=0 ssusb_mode_peripheral=1 udc_bind=1 soft_connect=0 stock_softdep_parity=1 qmp_module=1 eud_module=1 ucsi_glink=1 session_producer_parity=1 max77705_session=1 typec_readback=1 functionfs=0 stock_composite=0 geni_i2c_transport=0 role_write_discriminator=0 "
#elif M34_STAGE == 8
    "configfs_gadget=1 stock_order=1 udc_none=1 max_speed_high_speed=0 role_force=0 ssusb_speed_high_speed=0 ssusb_mode_peripheral=1 udc_bind=1 soft_connect=0 stock_softdep_parity=1 qmp_module=1 eud_module=1 ucsi_glink=1 session_producer_parity=1 max77705_session=1 typec_readback=1 functionfs=0 stock_composite=0 geni_i2c_transport=1 i2c_msm_geni=1 gpi_dma=1 msm_geni_se=1 role_write_discriminator=1 "
#elif M34_STAGE == 9
    "configfs_gadget=0 stock_order=0 udc_none=0 max_speed_high_speed=0 role_force=0 ssusb_speed_high_speed=0 ssusb_mode_peripheral=0 udc_bind=0 soft_connect=0 stock_softdep_parity=1 qmp_module=1 eud_module=1 ucsi_glink=1 session_producer_parity=1 max77705_session=1 typec_readback=0 functionfs=0 stock_composite=0 geni_i2c_transport=1 i2c_msm_geni=1 gpi_dma=1 msm_geni_se=1 role_write_discriminator=0 s8_beacon_probe=typec_port_or_i2c_device b1=1 "
#elif M34_STAGE == 10
    "configfs_gadget=0 stock_order=0 udc_none=0 max_speed_high_speed=0 role_force=0 ssusb_speed_high_speed=0 ssusb_mode_peripheral=0 udc_bind=0 soft_connect=0 stock_softdep_parity=1 qmp_module=1 eud_module=1 ucsi_glink=1 session_producer_parity=1 max77705_session=1 typec_readback=0 functionfs=0 stock_composite=0 geni_i2c_transport=1 i2c_msm_geni=1 gpi_dma=1 msm_geni_se=1 role_write_discriminator=0 s8_beacon_probe=typec_port_or_i2c_any_0066 b1a=1 "
#endif
#if M34_STAGE >= 9
    "no_android_handoff=1 reboot_request=download download_beacon=1 "
#else
    "no_android_handoff=1 no_reboot_request=1 no_download_beacon=1 "
#endif
    "persistent_mount=0 block_write=0\n";

static inline long syscall6(long nr, long a0, long a1, long a2, long a3, long a4, long a5) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x5 asm("x5") = a5;
    register long x8 asm("x8") = nr;
    asm volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8) : "memory");
    return x0;
}

static inline long syscall5(long nr, long a0, long a1, long a2, long a3, long a4) {
    return syscall6(nr, a0, a1, a2, a3, a4, 0);
}

static inline long syscall4(long nr, long a0, long a1, long a2, long a3) {
    return syscall6(nr, a0, a1, a2, a3, 0, 0);
}

static inline long syscall3(long nr, long a0, long a1, long a2) {
    return syscall6(nr, a0, a1, a2, 0, 0, 0);
}

static inline long syscall2(long nr, long a0, long a1) {
    return syscall6(nr, a0, a1, 0, 0, 0, 0);
}

static long sys_openat(int dirfd, const char *path, int flags, unsigned int mode) {
    return syscall4(NR_OPENAT, dirfd, (long)(uintptr_t)path, flags, mode);
}

static long sys_close(int fd) {
    return syscall2(NR_CLOSE, fd, 0);
}

static long sys_read(int fd, void *buf, size_t count) {
    return syscall3(NR_READ, fd, (long)(uintptr_t)buf, (long)count);
}

#if M34_STAGE >= 2
static long sys_getdents64(int fd, void *buf, size_t count) {
    return syscall3(NR_GETDENTS64, fd, (long)(uintptr_t)buf, (long)count);
}
#endif

static long sys_write(int fd, const void *buf, size_t count) {
    return syscall3(NR_WRITE, fd, (long)(uintptr_t)buf, (long)count);
}

static long sys_mkdirat(const char *path, unsigned int mode) {
    return syscall3(NR_MKDIRAT, AT_FDCWD, (long)(uintptr_t)path, mode);
}

static long sys_mknodat(const char *path, unsigned int mode, uint64_t dev) {
    return syscall4(NR_MKNODAT, AT_FDCWD, (long)(uintptr_t)path, mode, (long)dev);
}

static long sys_unlinkat(const char *path) {
    return syscall3(NR_UNLINKAT, AT_FDCWD, (long)(uintptr_t)path, 0);
}

static long sys_symlinkat(const char *oldpath, const char *newpath) {
    return syscall3(NR_SYMLINKAT, (long)(uintptr_t)oldpath, AT_FDCWD, (long)(uintptr_t)newpath);
}

static long sys_mount(const char *source, const char *target, const char *fstype, unsigned long flags, const char *data) {
    return syscall5(
        NR_MOUNT,
        (long)(uintptr_t)source,
        (long)(uintptr_t)target,
        (long)(uintptr_t)fstype,
        (long)flags,
        (long)(uintptr_t)data);
}

static long sys_sleep_sec(long sec) {
    struct timespec64 req = {
        .tv_sec = sec,
        .tv_nsec = 0,
    };
    return syscall2(NR_NANOSLEEP, (long)(uintptr_t)&req, 0);
}

#if M34_STAGE >= 9
static long sys_reboot_download(void) {
    return syscall4(
        NR_REBOOT,
        (long)LINUX_REBOOT_MAGIC1,
        (long)LINUX_REBOOT_MAGIC2,
        (long)LINUX_REBOOT_CMD_RESTART2,
        (long)(uintptr_t)"download");
}
#endif

static long sys_finit_module(int fd, const char *params, int flags) {
    return syscall3(NR_FINIT_MODULE, fd, (long)(uintptr_t)params, flags);
}

static size_t cstr_len(const char *s) {
    size_t n = 0;
    while (s[n] != '\0') {
        ++n;
    }
    return n;
}

void *memcpy(void *dst, const void *src, size_t n) {
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    for (size_t i = 0; i < n; ++i) {
        d[i] = s[i];
    }
    return dst;
}

void *memset(void *dst, int value, size_t n) {
    unsigned char *d = (unsigned char *)dst;
    for (size_t i = 0; i < n; ++i) {
        d[i] = (unsigned char)value;
    }
    return dst;
}

static void copy_cstr(char *dst, size_t size, const char *src) {
    if (size == 0) {
        return;
    }
    size_t i = 0;
    while (i + 1 < size && src[i] != '\0') {
        dst[i] = src[i];
        ++i;
    }
    dst[i] = '\0';
}

static void sb_putc(struct sbuf *sb, char ch) {
    if (sb->len + 1 < sizeof(sb->data)) {
        sb->data[sb->len++] = ch;
        sb->data[sb->len] = '\0';
    }
}

static void sb_puts(struct sbuf *sb, const char *s) {
    for (size_t i = 0; s[i] != '\0'; ++i) {
        sb_putc(sb, s[i]);
    }
}

static void sb_put_u64(struct sbuf *sb, uint64_t value) {
    char tmp[32];
    size_t n = 0;
    if (value == 0) {
        sb_putc(sb, '0');
        return;
    }
    while (value > 0 && n < sizeof(tmp)) {
        tmp[n++] = (char)('0' + (value % 10U));
        value /= 10U;
    }
    while (n > 0) {
        sb_putc(sb, tmp[--n]);
    }
}

static void sb_put_i64(struct sbuf *sb, int64_t value) {
    if (value < 0) {
        sb_putc(sb, '-');
        sb_put_u64(sb, (uint64_t)(-value));
        return;
    }
    sb_put_u64(sb, (uint64_t)value);
}

static void emit_buf(const struct sbuf *sb) {
    long fd = sys_openat(AT_FDCWD, "/dev/kmsg", O_WRONLY | O_CLOEXEC, 0);
    if (fd >= 0) {
        (void)sys_write((int)fd, sb->data, sb->len);
        (void)sys_close((int)fd);
    }
}

static void emit(const char *s) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, s);
    emit_buf(&sb);
}

static void emit_path_rc(const char *phase, const char *path, long rc) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=");
    sb_puts(&sb, phase);
    sb_puts(&sb, " path=");
    sb_puts(&sb, path);
    sb_puts(&sb, " rc=");
    sb_put_i64(&sb, rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static long write_all(int fd, const char *buf, size_t len) {
    while (len > 0) {
        long rc = sys_write(fd, buf, len);
        if (rc <= 0) {
            return rc == 0 ? -1 : rc;
        }
        buf += (size_t)rc;
        len -= (size_t)rc;
    }
    return 0;
}

static long write_attr(const char *path, const char *value) {
    long fd = sys_openat(AT_FDCWD, path, O_WRONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        emit_path_rc("write_open", path, fd);
        return fd;
    }
    long rc = write_all((int)fd, value, cstr_len(value));
    (void)sys_close((int)fd);
    emit_path_rc("write", path, rc);
    return rc;
}

#if M34_STAGE >= 7
static void read_attr_emit(const char *phase, const char *path) {
    char value[128];
    long fd = sys_openat(AT_FDCWD, path, O_RDONLY | O_CLOEXEC, 0);
    long rc = fd;
    long n = 0;
    if (fd >= 0) {
        n = sys_read((int)fd, value, sizeof(value) - 1);
        rc = n;
        (void)sys_close((int)fd);
    }
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=");
    sb_puts(&sb, phase);
    sb_puts(&sb, " path=");
    sb_puts(&sb, path);
    sb_puts(&sb, " rc=");
    sb_put_i64(&sb, rc);
    if (fd >= 0 && n > 0) {
        sb_puts(&sb, " value=");
        if (n >= (long)sizeof(value)) {
            n = (long)sizeof(value) - 1;
        }
        for (long i = 0; i < n; ++i) {
            char ch = value[i];
            if (ch == '\n' || ch == '\r' || ch == '\t') {
                ch = ';';
            }
            sb_putc(&sb, ch);
        }
    }
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static void emit_typec_udc_readback(const char *phase) {
    read_attr_emit(phase, "/sys/devices/platform/soc/a600000.ssusb/mode");
    read_attr_emit(phase, "/sys/devices/platform/soc/a600000.ssusb/speed");
    read_attr_emit(phase, "/sys/class/typec/port0/data_role");
    read_attr_emit(phase, "/sys/class/typec/port0/power_role");
    read_attr_emit(phase, "/sys/class/typec/port0/port_type");
    read_attr_emit(phase, "/sys/class/typec/port0-partner/uevent");
    read_attr_emit(phase, "/sys/class/udc/a600000.dwc3/state");
    read_attr_emit(phase, "/sys/class/udc/a600000.dwc3/current_speed");
    read_attr_emit(phase, "/sys/class/udc/a600000.dwc3/function");
}
#endif

#if M34_STAGE == 8
static int typec_partner_present(void) {
    long fd = sys_openat(AT_FDCWD, "/sys/class/typec/port0-partner/uevent", O_RDONLY | O_CLOEXEC, 0);
    long rc = fd;
    long n = 0;
    if (fd >= 0) {
        char value[64];
        n = sys_read((int)fd, value, sizeof(value));
        rc = n;
        (void)sys_close((int)fd);
    }
    int present = (fd >= 0 && n > 0) ? 1 : 0;
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=typec_partner_check rc=");
    sb_put_i64(&sb, rc);
    sb_puts(&sb, " present=");
    sb_put_u64(&sb, present ? 1U : 0U);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
    return present;
}

static void maybe_force_typec_device_sink(void) {
    if (typec_partner_present()) {
        emit(M34_MARKER " phase=typec_role_write skipped=partner_present\n");
        return;
    }
    long data_rc = write_attr("/sys/class/typec/port0/data_role", "device");
    long power_rc = write_attr("/sys/class/typec/port0/power_role", "sink");
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=typec_role_write role_device_rc=");
    sb_put_i64(&sb, data_rc);
    sb_puts(&sb, " role_sink_rc=");
    sb_put_i64(&sb, power_rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}
#endif

#if M34_STAGE >= 9
static int path_present(const char *path) {
    long fd = sys_openat(AT_FDCWD, path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return 0;
    }
    (void)sys_close((int)fd);
    return 1;
}

static int s8_b1_typec_port_or_i2c_present(void) {
    return path_present("/sys/class/typec/port0") || path_present("/sys/bus/i2c/devices/57-0066");
}

#if M34_STAGE == 10
static int cstr_ends_with(const char *s, const char *suffix) {
    size_t slen = cstr_len(s);
    size_t suffix_len = cstr_len(suffix);
    if (slen < suffix_len) {
        return 0;
    }
    for (size_t i = 0; i < suffix_len; ++i) {
        if (s[slen - suffix_len + i] != suffix[i]) {
            return 0;
        }
    }
    return 1;
}

static int cstr_is_dot_or_dotdot(const char *s) {
    return s[0] == '.' && (s[1] == '\0' || (s[1] == '.' && s[2] == '\0'));
}

static int s8_b1a_i2c_any_0066_present(void) {
    long fd = sys_openat(AT_FDCWD, "/sys/bus/i2c/devices", O_RDONLY | O_DIRECTORY | O_CLOEXEC, 0);
    if (fd < 0) {
        return 0;
    }
    char dents[1024];
    int found = 0;
    for (;;) {
        long nread = sys_getdents64((int)fd, dents, sizeof(dents));
        if (nread <= 0) {
            break;
        }
        long pos = 0;
        while (pos < nread) {
            struct linux_dirent64 *de = (struct linux_dirent64 *)(void *)(dents + pos);
            const char *name = de->d_name;
            if (!cstr_is_dot_or_dotdot(name) && cstr_ends_with(name, "-0066")) {
                found = 1;
                break;
            }
            if (de->d_reclen == 0) {
                break;
            }
            pos += de->d_reclen;
        }
        if (found) {
            break;
        }
    }
    (void)sys_close((int)fd);
    return found;
}

static int s8_b1a_typec_port_or_i2c_any_0066_present(void) {
    return path_present("/sys/class/typec/port0") || s8_b1a_i2c_any_0066_present();
}
#endif

static void s8_beacon_probe(void) {
    int present = 0;
    unsigned int waited = 0;
    for (; waited < 10; ++waited) {
#if M34_STAGE == 9
        if (s8_b1_typec_port_or_i2c_present()) {
#else
        if (s8_b1a_typec_port_or_i2c_any_0066_present()) {
#endif
            present = 1;
            break;
        }
        (void)sys_sleep_sec(1);
    }

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
#if M34_STAGE == 9
    sb_puts(&sb, " phase=s8_b1_probe predicate=typec_port_or_i2c_device present=");
#else
    sb_puts(&sb, " phase=s8_b1a_probe predicate=typec_port_or_i2c_any_0066 present=");
#endif
    sb_put_u64(&sb, present ? 1U : 0U);
    sb_puts(&sb, " waited_sec=");
    sb_put_u64(&sb, waited);
#if M34_STAGE == 9
    sb_puts(&sb, " true_action=reboot_download false_action=park paths=/sys/class/typec/port0,/sys/bus/i2c/devices/57-0066\n");
#else
    sb_puts(&sb, " true_action=reboot_download false_action=park paths=/sys/class/typec/port0,/sys/bus/i2c/devices/*-0066\n");
#endif
    emit_buf(&sb);

    if (present) {
        long rc = sys_reboot_download();
        struct sbuf rb = {.data = {0}, .len = 0};
        sb_puts(&rb, M34_MARKER);
#if M34_STAGE == 9
        sb_puts(&rb, " phase=s8_b1_reboot_returned rc=");
#else
        sb_puts(&rb, " phase=s8_b1a_reboot_returned rc=");
#endif
        sb_put_i64(&rb, rc);
        sb_putc(&rb, '\n');
        emit_buf(&rb);
    }
}
#endif

static void mkdir_one(const char *path, unsigned int mode) {
    (void)sys_mkdirat(path, mode);
}

static void mkdir_p(const char *path, unsigned int mode) {
    char tmp[256];
    size_t len = cstr_len(path);
    if (len == 0 || len >= sizeof(tmp)) {
        return;
    }
    copy_cstr(tmp, sizeof(tmp), path);
    for (size_t i = 1; tmp[i] != '\0'; ++i) {
        if (tmp[i] == '/') {
            tmp[i] = '\0';
            mkdir_one(tmp, mode);
            tmp[i] = '/';
        }
    }
    mkdir_one(tmp, mode);
}

static uint64_t make_dev(unsigned int major_num, unsigned int minor_num) {
    return ((uint64_t)(minor_num & 0xffU)) | ((uint64_t)(major_num & 0xfffU) << 8) |
           ((uint64_t)(minor_num & ~0xffU) << 12) | ((uint64_t)(major_num & ~0xfffU) << 32);
}

static void ensure_chr_node(const char *path, unsigned int mode, unsigned int major_num, unsigned int minor_num) {
    (void)sys_unlinkat(path);
    (void)sys_mknodat(path, S_IFCHR | mode, make_dev(major_num, minor_num));
}

static long mount_one(const char *source, const char *target, const char *fstype, unsigned long flags, const char *data) {
    long rc = sys_mount(source, target, fstype, flags, data);
    if (rc == -EBUSY) {
        return 0;
    }
    return rc;
}

static void setup_minimal_fs(void) {
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/dev", 0755);
    mkdir_p("/run", 0755);
    mkdir_p("/config", 0755);

    long proc_rc = mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long sys_rc = mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    long dev_rc = mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755");
    if (dev_rc != 0) {
        dev_rc = mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    long run_rc = mount_one("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");
    long configfs_rc = mount_one("configfs", "/config", "configfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=mounts proc_rc=");
    sb_put_i64(&sb, proc_rc);
    sb_puts(&sb, " sys_rc=");
    sb_put_i64(&sb, sys_rc);
    sb_puts(&sb, " dev_rc=");
    sb_put_i64(&sb, dev_rc);
    sb_puts(&sb, " run_rc=");
    sb_put_i64(&sb, run_rc);
    sb_puts(&sb, " configfs_rc=");
    sb_put_i64(&sb, configfs_rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static int build_module_path(char *out, size_t size, const char *name) {
    const char prefix[] = "/lib/modules/";
    size_t prefix_len = sizeof(prefix) - 1;
    size_t name_len = cstr_len(name);
    if (prefix_len + name_len + 1 > size) {
        return -1;
    }
    for (size_t i = 0; i < prefix_len; ++i) {
        out[i] = prefix[i];
    }
    for (size_t i = 0; i < name_len; ++i) {
        out[prefix_len + i] = name[i];
    }
    out[prefix_len + name_len] = '\0';
    return 0;
}

static long load_one_module(const char *name) {
    char path[160];
    if (build_module_path(path, sizeof(path), name) != 0) {
        return -9999;
    }
    long fd = sys_openat(AT_FDCWD, path, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        return fd;
    }
    long rc = sys_finit_module((int)fd, "", 0);
    (void)sys_close((int)fd);
    return rc;
}

static void emit_module_result(const char *name, long rc) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=module name=");
    sb_puts(&sb, name);
    sb_puts(&sb, " rc=");
    sb_put_i64(&sb, rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static void load_modules_from_list(void) {
    char buf[MODULES_LOAD_BUF];
    long fd = sys_openat(AT_FDCWD, M34_MODULES_RAMDISK, O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) {
        emit(M34_MARKER " phase=modules_open_failed\n");
        return;
    }
    long n = sys_read((int)fd, buf, sizeof(buf) - 1);
    (void)sys_close((int)fd);
    if (n <= 0) {
        emit(M34_MARKER " phase=modules_read_failed\n");
        return;
    }
    buf[n] = '\0';

    char name[MODULE_NAME_BUF];
    size_t name_len = 0;
    unsigned int loaded = 0;
    for (long i = 0; i <= n; ++i) {
        char ch = buf[i];
        if (ch == '\n' || ch == '\0') {
            if (name_len > 0) {
                name[name_len] = '\0';
                long rc = load_one_module(name);
                emit_module_result(name, rc);
                ++loaded;
                name_len = 0;
            }
            if (ch == '\0') {
                break;
            }
            continue;
        }
        if (name_len + 1 < sizeof(name)) {
            name[name_len++] = ch;
        }
    }

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=modules_load_done loaded=");
    sb_put_u64(&sb, loaded);
    sb_puts(&sb, " expected=");
    sb_put_u64(&sb, M34_MODULE_LIMIT);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}

static void create_configfs_gadget(void) {
    mkdir_p("/config/usb_gadget/g1", 0755);
    mkdir_p("/config/usb_gadget/g1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/functions/ss_acm.0", 0755);

    (void)write_attr("/config/usb_gadget/g1/bcdUSB", "0x0200");
    (void)write_attr("/config/usb_gadget/g1/os_desc/use", "1");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/serialnumber", "S22M34RUNTIME01");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/manufacturer", "Codex");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/product", "S22 Native Init M34 Runtime Split");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/MaxPower", "900");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/bmAttributes", "0x80");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "acm");

    (void)write_attr("/config/usb_gadget/g1/UDC", "none");
    (void)write_attr("/config/usb_gadget/g1/idVendor", "0x04E8");
    (void)write_attr("/config/usb_gadget/g1/idProduct", "0x6860");
    (void)write_attr("/config/usb_gadget/g1/bcdDevice", "0x0034");
    (void)write_attr("/config/usb_gadget/g1/bDeviceClass", "0xef");
    (void)write_attr("/config/usb_gadget/g1/bDeviceSubClass", "0x02");
    (void)write_attr("/config/usb_gadget/g1/bDeviceProtocol", "0x01");

    long symlink_rc = sys_symlinkat("../../functions/ss_acm.0", "/config/usb_gadget/g1/configs/b.1/f1");
    if (symlink_rc == -EEXIST) {
        symlink_rc = 0;
    }

    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=configfs_done symlink_rc=");
    sb_put_i64(&sb, symlink_rc);
    sb_puts(&sb, " udc_none=1 max_speed_high_speed=0 role_forced=0 udc_bound=0\n");
    emit_buf(&sb);
}

#if M34_STAGE >= 2
static int cstr_eq(const char *a, const char *b) {
    size_t i = 0;
    while (a[i] != '\0' && b[i] != '\0') {
        if (a[i] != b[i]) {
            return 0;
        }
        ++i;
    }
    return a[i] == b[i];
}
#endif

#if M34_STAGE == 2 || M34_STAGE == 3 || M34_STAGE == 4 || M34_STAGE == 5
static void set_max_speed_high_speed(void) {
    long rc = write_attr("/config/usb_gadget/g1/max_speed", "high-speed");
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=max_speed value=high-speed rc=");
    sb_put_i64(&sb, rc);
    sb_puts(&sb, " udc_bound=0\n");
    emit_buf(&sb);
}

#if M34_STAGE == 2 || M34_STAGE == 3
static void force_usb_roles_device(void) {
    long fd = sys_openat(AT_FDCWD, "/sys/class/usb_role", O_RDONLY | O_DIRECTORY | O_CLOEXEC, 0);
    if (fd < 0) {
        struct sbuf sb = {.data = {0}, .len = 0};
        sb_puts(&sb, M34_MARKER);
        sb_puts(&sb, " phase=usb_role open_rc=");
        sb_put_i64(&sb, fd);
        sb_putc(&sb, '\n');
        emit_buf(&sb);
        return;
    }
    char dents[1024];
    unsigned int count = 0;
    for (;;) {
        long nread = sys_getdents64((int)fd, dents, sizeof(dents));
        if (nread <= 0) {
            break;
        }
        long pos = 0;
        while (pos < nread) {
            struct linux_dirent64 *de = (struct linux_dirent64 *)(void *)(dents + pos);
            const char *name = de->d_name;
            if (!cstr_eq(name, ".") && !cstr_eq(name, "..")) {
                char role_path[192] = "/sys/class/usb_role/";
                size_t base = cstr_len(role_path);
                size_t nlen = cstr_len(name);
                if (base + nlen + sizeof("/role") < sizeof(role_path)) {
                    for (size_t i = 0; i < nlen; ++i) {
                        role_path[base + i] = name[i];
                    }
                    role_path[base + nlen] = '\0';
                    const char suffix[] = "/role";
                    for (size_t i = 0; i < sizeof(suffix); ++i) {
                        role_path[base + nlen + i] = suffix[i];
                    }
                    long rc = write_attr(role_path, "device");
                    struct sbuf sb = {.data = {0}, .len = 0};
                    sb_puts(&sb, M34_MARKER);
                    sb_puts(&sb, " phase=usb_role name=");
                    sb_puts(&sb, name);
                    sb_puts(&sb, " rc=");
                    sb_put_i64(&sb, rc);
                    sb_putc(&sb, '\n');
                    emit_buf(&sb);
                    ++count;
                }
            }
            if (de->d_reclen == 0) {
                break;
            }
            pos += de->d_reclen;
        }
    }
    (void)sys_close((int)fd);
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=usb_role_done count=");
    sb_put_u64(&sb, count);
    sb_puts(&sb, " udc_bound=0\n");
    emit_buf(&sb);
}
#endif
#endif

#if M34_STAGE == 4 || M34_STAGE == 5
static void set_ssusb_speed_high_speed(void) {
    long rc = write_attr("/sys/devices/platform/soc/a600000.ssusb/speed", "high-speed");
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=ssusb_speed value=high-speed rc=");
    sb_put_i64(&sb, rc);
    sb_puts(&sb, " udc_bound=0\n");
    emit_buf(&sb);
}
#endif

#if M34_STAGE >= 4
static void set_ssusb_mode_peripheral(void) {
    long rc = write_attr("/sys/devices/platform/soc/a600000.ssusb/mode", "peripheral");
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=ssusb_mode value=peripheral rc=");
    sb_put_i64(&sb, rc);
    sb_puts(&sb, " udc_bound=0\n");
    emit_buf(&sb);
}
#endif

#if M34_STAGE >= 3
static int choose_real_udc(char *buf, size_t size) {
    long fd = sys_openat(AT_FDCWD, "/sys/class/udc", O_RDONLY | O_DIRECTORY | O_CLOEXEC, 0);
    if (fd < 0) {
        buf[0] = '\0';
        return 0;
    }
    char dents[1024];
    for (;;) {
        long nread = sys_getdents64((int)fd, dents, sizeof(dents));
        if (nread <= 0) {
            break;
        }
        long pos = 0;
        while (pos < nread) {
            struct linux_dirent64 *de = (struct linux_dirent64 *)(void *)(dents + pos);
            const char *name = de->d_name;
            if (cstr_eq(name, "a600000.dwc3")) {
                copy_cstr(buf, size, name);
                (void)sys_close((int)fd);
                return 1;
            }
            if (de->d_reclen == 0) {
                break;
            }
            pos += de->d_reclen;
        }
    }
    (void)sys_close((int)fd);
    buf[0] = '\0';
    return 0;
}

static void bind_udc(void) {
    char udc[128] = "";
    int have_udc = choose_real_udc(udc, sizeof(udc));
    long rc = -1;
    if (have_udc) {
        rc = write_attr("/config/usb_gadget/g1/UDC", udc);
    }
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=udc_bind have_udc=");
    sb_put_u64(&sb, have_udc ? 1U : 0U);
    sb_puts(&sb, " udc=");
    sb_puts(&sb, udc);
    sb_puts(&sb, " rc=");
    sb_put_i64(&sb, rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}
#endif

#if M34_STAGE == 5
static void soft_connect_udc(void) {
    long rc = write_attr("/sys/class/udc/a600000.dwc3/soft_connect", "connect");
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, M34_MARKER);
    sb_puts(&sb, " phase=soft_connect value=connect rc=");
    sb_put_i64(&sb, rc);
    sb_putc(&sb, '\n');
    emit_buf(&sb);
}
#endif

__attribute__((noreturn)) static void park_forever(void) {
    emit(M34_MARKER " phase=park_enter dwell_target_sec=120\n");
    for (;;) {
        (void)sys_sleep_sec(10);
        asm volatile("wfe" ::: "memory");
    }
}

__attribute__((noreturn)) void _start(void) {
    setup_minimal_fs();
    emit(k_marker);
    load_modules_from_list();
#if M34_STAGE >= 9
    s8_beacon_probe();
    park_forever();
#else
    create_configfs_gadget();
#if M34_STAGE >= 2
#if M34_STAGE == 2 || M34_STAGE == 3 || M34_STAGE == 4 || M34_STAGE == 5
    set_max_speed_high_speed();
#endif
#endif
#if M34_STAGE == 2 || M34_STAGE == 3
    force_usb_roles_device();
#endif
#if M34_STAGE == 4 || M34_STAGE == 5
    set_ssusb_speed_high_speed();
#endif
#if M34_STAGE >= 4
    set_ssusb_mode_peripheral();
#endif
#if M34_STAGE >= 7
    emit_typec_udc_readback("typec_pre_bind");
    emit_typec_udc_readback("udc_pre_bind");
#endif
#if M34_STAGE == 8
    maybe_force_typec_device_sink();
    emit_typec_udc_readback("typec_post_role_write");
#endif
#if M34_STAGE >= 3
    bind_udc();
#endif
#if M34_STAGE >= 7
    emit_typec_udc_readback("typec_post_bind");
    emit_typec_udc_readback("udc_post_bind");
#endif
#if M34_STAGE == 5
    soft_connect_udc();
#endif
    park_forever();
#endif
}
