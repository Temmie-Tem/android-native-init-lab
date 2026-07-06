// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ native-init M5 USB-ACM control-channel candidate.
 *
 * M4T2/M4T3 proved that the S22+ kernel executes our custom ramdisk /init and
 * that a raw reboot-download syscall can recover.  M5 moves to the force
 * multiplier: mount the minimal virtual filesystems, insert the measured
 * USB-first vendor module chain, create a minimal ss_acm.0 configfs gadget,
 * then park while probing /dev/ttyGS0.
 *
 * This candidate intentionally does not start Android or Magisk, mount
 * persistent partitions, write block devices, or auto-reboot.
 */

#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef SYS_finit_module
#define SYS_finit_module 273
#endif

#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))

static const char k_marker[] =
    "S22_NATIVE_INIT_USB_ACM_M5 version=0.2 pid1=direct "
    "usb_first_modules=26 gadget=ss_acm.0 tty=/dev/ttyGS0 "
    "no_android_handoff=1 no_auto_reboot=1 udc_bind_retry=1\n";

static const char *const k_usb_modules[] = {
    "phy-msm-ssusb-qmp.ko",
    "phy-msm-snps-eusb2.ko",
    "dwc3-msm.ko",
    "usb_f_diag.ko",
    "usb_f_qdss.ko",
    "usb_f_gsi.ko",
    "usb_f_conn_gadget.ko",
    "usb_f_ss_mon_gadget.ko",
    "usb_f_ss_acm.ko",
    "repeater.ko",
    "redriver.ko",
    "usb_notify_layer.ko",
    "usb_notifier_qcom.ko",
    "ipa_fmwk.ko",
    "usb_bam.ko",
    "sps_drv.ko",
    "switch_class.ko",
    "common_muic.ko",
    "vbus_notifier.ko",
    "usb_typec_manager.ko",
    "if_cb_manager.ko",
    "pdic_notifier_module.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
    "spu_verify.ko",
    "qc_usb_audio.ko",
};

static int write_all(int fd, const char *buf, size_t len) {
    while (len > 0) {
        ssize_t rc = write(fd, buf, len);
        if (rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (rc == 0) {
            errno = EIO;
            return -1;
        }
        buf += (size_t)rc;
        len -= (size_t)rc;
    }
    return 0;
}

static void mkdir_one(const char *path, mode_t mode) {
    if (mkdir(path, mode) != 0 && errno != EEXIST) {
        return;
    }
    (void)chmod(path, mode);
}

static void mkdir_p(const char *path, mode_t mode) {
    char tmp[256];
    size_t len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) {
        return;
    }
    memcpy(tmp, path, len + 1);
    for (char *p = tmp + 1; *p; ++p) {
        if (*p == '/') {
            *p = '\0';
            mkdir_one(tmp, mode);
            *p = '/';
        }
    }
    mkdir_one(tmp, mode);
}

static void ensure_chr_node(const char *path, mode_t mode, unsigned int major_num, unsigned int minor_num) {
    struct stat st;
    if (stat(path, &st) == 0 && S_ISCHR(st.st_mode)) {
        return;
    }
    (void)unlink(path);
    (void)mknod(path, S_IFCHR | mode, makedev(major_num, minor_num));
}

static void write_kmsg(const char *msg) {
    int fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) {
        write_all(fd, msg, strlen(msg));
        close(fd);
    }
}

static void emit(const char *msg) {
    write_kmsg(msg);
}

static void emitf(const char *fmt, ...) {
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n <= 0) {
        return;
    }
    if ((size_t)n >= sizeof(buf)) {
        n = (int)sizeof(buf) - 1;
        buf[n] = '\0';
    }
    emit(buf);
}

static int mount_one(const char *source, const char *target, const char *fstype, unsigned long flags, const char *data) {
    int rc = mount(source, target, fstype, flags, data);
    if (rc != 0 && errno == EBUSY) {
        return 0;
    }
    return rc;
}

static int read_trim(const char *path, char *buf, size_t size) {
    if (size == 0) {
        return -1;
    }
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        buf[0] = '\0';
        return -1;
    }
    ssize_t n = read(fd, buf, size - 1);
    close(fd);
    if (n < 0) {
        buf[0] = '\0';
        return -1;
    }
    buf[n] = '\0';
    while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == '\r' || buf[n - 1] == ' ' || buf[n - 1] == '\t')) {
        buf[n - 1] = '\0';
        --n;
    }
    return 0;
}

static void copy_cstr(char *dst, size_t size, const char *src) {
    if (size == 0) {
        return;
    }
    size_t len = strnlen(src, size - 1);
    memcpy(dst, src, len);
    dst[len] = '\0';
}

static bool choose_udc(char *buf, size_t size) {
    DIR *dir = opendir("/sys/class/udc");
    if (!dir) {
        return false;
    }
    char fallback[128] = "";
    struct dirent *de;
    while ((de = readdir(dir)) != NULL) {
        if (de->d_name[0] == '.') {
            continue;
        }
        if (fallback[0] == '\0') {
            copy_cstr(fallback, sizeof(fallback), de->d_name);
        }
        if (strstr(de->d_name, "dummy") == NULL) {
            copy_cstr(buf, size, de->d_name);
            closedir(dir);
            return true;
        }
    }
    closedir(dir);
    if (fallback[0] != '\0') {
        copy_cstr(buf, size, fallback);
        return true;
    }
    return false;
}

static void setup_minimal_fs(void) {
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/dev", 0755);
    mkdir_p("/run", 0755);
    mkdir_p("/config", 0755);
    mkdir_p("/sys/fs", 0755);

    int proc_rc = mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    int proc_errno = proc_rc == 0 ? 0 : errno;
    int sys_rc = mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    int sys_errno = sys_rc == 0 ? 0 : errno;
    int dev_rc = mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755");
    if (dev_rc != 0) {
        dev_rc = mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    int dev_errno = dev_rc == 0 ? 0 : errno;
    int run_rc = mount_one("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");
    int run_errno = run_rc == 0 ? 0 : errno;

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);

    int configfs_rc = mount_one("configfs", "/config", "configfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    int configfs_errno = configfs_rc == 0 ? 0 : errno;
    emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=mounts proc_rc=%d proc_errno=%d sys_rc=%d sys_errno=%d dev_rc=%d dev_errno=%d run_rc=%d run_errno=%d configfs_rc=%d configfs_errno=%d\n",
          proc_rc,
          proc_errno,
          sys_rc,
          sys_errno,
          dev_rc,
          dev_errno,
          run_rc,
          run_errno,
          configfs_rc,
          configfs_errno);
}

static void load_usb_modules(void) {
    for (size_t idx = 0; idx < ARRAY_SIZE(k_usb_modules); ++idx) {
        char path[256];
        int n = snprintf(path, sizeof(path), "/lib/modules/s22plus-m5/%s", k_usb_modules[idx]);
        if (n <= 0 || (size_t)n >= sizeof(path)) {
            emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=module index=%zu name=%s rc=-1 errno=%d error=path-too-long\n",
                  idx + 1,
                  k_usb_modules[idx],
                  ENAMETOOLONG);
            continue;
        }
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) {
            emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=module index=%zu name=%s open_rc=-1 errno=%d\n",
                  idx + 1,
                  k_usb_modules[idx],
                  errno);
            continue;
        }
        errno = 0;
        long rc = syscall(SYS_finit_module, fd, "", 0);
        int saved_errno = errno;
        close(fd);
        int ok = (rc == 0 || saved_errno == EEXIST) ? 1 : 0;
        emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=module index=%zu name=%s finit_rc=%ld errno=%d ok=%d\n",
              idx + 1,
              k_usb_modules[idx],
              rc,
              saved_errno,
              ok);
        usleep(20000);
    }
}

static int write_attr(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=configfs_write path=%s rc=-1 errno=%d\n", path, errno);
        return -1;
    }
    errno = 0;
    int rc = write_all(fd, value, strlen(value));
    int saved_errno = errno;
    close(fd);
    if (rc != 0) {
        emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=configfs_write path=%s rc=-1 errno=%d\n", path, saved_errno);
        errno = saved_errno;
        return -1;
    }
    return 0;
}

static bool create_acm_gadget(void) {
    char current_udc[128] = "";
    if (read_trim("/config/usb_gadget/g1/UDC", current_udc, sizeof(current_udc)) == 0 && current_udc[0] != '\0') {
        emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=acm_gadget already_bound=1 udc=%s\n", current_udc);
        return true;
    }

    mkdir_p("/config/usb_gadget/g1", 0755);
    mkdir_p("/config/usb_gadget/g1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/functions/ss_acm.0", 0755);

    (void)write_attr("/config/usb_gadget/g1/idVendor", "0x04e8");
    (void)write_attr("/config/usb_gadget/g1/idProduct", "0x685d");
    (void)write_attr("/config/usb_gadget/g1/bcdUSB", "0x0320");
    (void)write_attr("/config/usb_gadget/g1/bcdDevice", "0x0001");
    (void)write_attr("/config/usb_gadget/g1/bDeviceClass", "0xef");
    (void)write_attr("/config/usb_gadget/g1/bDeviceSubClass", "0x02");
    (void)write_attr("/config/usb_gadget/g1/bDeviceProtocol", "0x01");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/manufacturer", "Codex");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/product", "S22 Native Init M5 ACM");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/serialnumber", "S22M5ACM0001");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/MaxPower", "500");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/bmAttributes", "0x80");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "acm");

    errno = 0;
    int symlink_rc = symlink("../../functions/ss_acm.0", "/config/usb_gadget/g1/configs/b.1/f1");
    int symlink_errno = symlink_rc == 0 ? 0 : errno;
    if (symlink_rc != 0 && symlink_errno == EEXIST) {
        symlink_rc = 0;
        symlink_errno = 0;
    }

    char udc[128] = "";
    bool have_udc = choose_udc(udc, sizeof(udc));
    int udc_rc = -1;
    int udc_errno = 0;
    if (have_udc) {
        udc_rc = write_attr("/config/usb_gadget/g1/UDC", udc);
        udc_errno = udc_rc == 0 ? 0 : errno;
    }
    emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=acm_gadget symlink_rc=%d symlink_errno=%d have_udc=%d udc=%s udc_rc=%d udc_errno=%d\n",
          symlink_rc,
          symlink_errno,
          have_udc ? 1 : 0,
          udc,
          udc_rc,
          udc_errno);
    return udc_rc == 0;
}

static bool ensure_ttygs0(void) {
    char dev_text[64] = "";
    if (read_trim("/sys/class/tty/ttyGS0/dev", dev_text, sizeof(dev_text)) != 0 || dev_text[0] == '\0') {
        return access("/dev/ttyGS0", F_OK) == 0;
    }
    unsigned int major_num = 0;
    unsigned int minor_num = 0;
    if (sscanf(dev_text, "%u:%u", &major_num, &minor_num) == 2) {
        ensure_chr_node("/dev/ttyGS0", 0600, major_num, minor_num);
    }
    return access("/dev/ttyGS0", F_OK) == 0;
}

static void serial_probe_loop(void) {
    for (unsigned int tick = 0;; ++tick) {
        if ((tick % 3U) == 0U) {
            bool bound = create_acm_gadget();
            emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=acm_retry tick=%u bound=%d\n", tick, bound ? 1 : 0);
        }
        bool tty_ready = ensure_ttygs0();
        int fd = open("/dev/ttyGS0", O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
        int open_errno = fd >= 0 ? 0 : errno;
        if (fd >= 0) {
            const char *banner = "S22_NATIVE_INIT_USB_ACM_M5 READY\n";
            write_all(fd, banner, strlen(banner));
            close(fd);
        }
        emitf("S22_NATIVE_INIT_USB_ACM_M5 phase=park tick=%u tty_ready=%d tty_open_rc=%d tty_open_errno=%d\n",
              tick,
              tty_ready ? 1 : 0,
              fd >= 0 ? 0 : -1,
              open_errno);
        sleep(2);
    }
}

int main(int argc, char **argv, char **envp) {
    (void)argc;
    (void)argv;
    (void)envp;

    setup_minimal_fs();
    emit(k_marker);
    load_usb_modules();
    (void)create_acm_gadget();
    serial_probe_loop();
}
