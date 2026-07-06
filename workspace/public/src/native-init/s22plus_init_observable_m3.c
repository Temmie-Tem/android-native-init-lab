// SPDX-License-Identifier: MIT
/*
 * Samsung S22+ observable native-init M3 candidate.
 *
 * This is a direct /init PID1 candidate, not an Android/Magisk handoff.  The
 * first goal is observability: emit reboot-surviving markers, insert the
 * measured USB-first vendor modules, create a minimal NCM configfs gadget, and
 * park with heartbeat logs.  It intentionally does not mount writable
 * partitions, touch block devices, start Android, or auto-reboot.
 */

#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
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
    "S22_NATIVE_INIT_OBSERVABLE_M3 version=0.1 pid1=direct "
    "proof=kmsg-pmsg usb_first_modules=26 gadget=ncm link_only=1 park=1 no_android_handoff=1\n";

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

static void write_all(int fd, const char *buf, size_t len) {
    while (len > 0) {
        ssize_t rc = write(fd, buf, len);
        if (rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return;
        }
        if (rc == 0) {
            return;
        }
        buf += (size_t)rc;
        len -= (size_t)rc;
    }
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

static void write_regular_file(const char *path, const char *msg) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0) {
        return;
    }
    write_all(fd, msg, strlen(msg));
    (void)fsync(fd);
    close(fd);
}

static void write_kmsg(const char *msg) {
    int fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) {
        write_all(fd, msg, strlen(msg));
        close(fd);
    }
}

static void write_pmsg(const char *msg) {
    int fd = open("/dev/pmsg0", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) {
        write_all(fd, msg, strlen(msg));
        close(fd);
    }
}

static void emit(const char *msg) {
    write_kmsg(msg);
    write_pmsg(msg);
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

static unsigned int find_char_major(const char *name) {
    FILE *f = fopen("/proc/devices", "re");
    if (!f) {
        return 0;
    }
    char line[128];
    unsigned int major = 0;
    char devname[80];
    while (fgets(line, sizeof(line), f)) {
        major = 0;
        devname[0] = '\0';
        if (sscanf(line, " %u %79s", &major, devname) == 2 && strcmp(devname, name) == 0) {
            fclose(f);
            return major;
        }
    }
    fclose(f);
    return 0;
}

static void setup_minimal_fs(void) {
    mkdir_p("/proc", 0755);
    mkdir_p("/sys", 0755);
    mkdir_p("/dev", 0755);
    mkdir_p("/run", 0755);
    mkdir_p("/tmp", 01777);
    mkdir_p("/config", 0755);
    mkdir_p("/debug_ramdisk", 0755);
    mkdir_p("/sys/fs", 0755);
    mkdir_p("/sys/fs/pstore", 0755);

    (void)mount_one("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    (void)mount_one("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    if (mount_one("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755") != 0) {
        (void)mount_one("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
    }
    (void)mount_one("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");

    ensure_chr_node("/dev/kmsg", 0600, 1, 11);
    ensure_chr_node("/dev/console", 0600, 5, 1);
    ensure_chr_node("/dev/null", 0666, 1, 3);
    ensure_chr_node("/dev/zero", 0666, 1, 5);

    unsigned int pmsg_major = find_char_major("pmsg");
    if (pmsg_major != 0) {
        ensure_chr_node("/dev/pmsg0", 0222, pmsg_major, 0);
    }

    int pstore_rc = mount_one("pstore", "/sys/fs/pstore", "pstore", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    int pstore_errno = pstore_rc == 0 ? 0 : errno;
    int configfs_rc = mount_one("configfs", "/config", "configfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "");
    int configfs_errno = configfs_rc == 0 ? 0 : errno;
    emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=mounts pmsg_major=%u pstore_rc=%d pstore_errno=%d configfs_rc=%d configfs_errno=%d\n",
          pmsg_major,
          pstore_rc,
          pstore_errno,
          configfs_rc,
          configfs_errno);
}

static void write_markers(void) {
    emit(k_marker);
    write_regular_file("/s22_native_init_observable_m3_ran", k_marker);
    write_regular_file("/debug_ramdisk/s22_native_init_observable_m3_ran", k_marker);
    write_regular_file("/run/s22_native_init_observable_m3_ran", k_marker);
}

static void load_usb_modules(void) {
    for (size_t idx = 0; idx < ARRAY_SIZE(k_usb_modules); ++idx) {
        char path[256];
        int n = snprintf(path, sizeof(path), "/lib/modules/s22plus-m3/%s", k_usb_modules[idx]);
        if (n <= 0 || (size_t)n >= sizeof(path)) {
            emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=module index=%zu name=%s rc=-1 errno=%d error=path-too-long\n",
                  idx + 1,
                  k_usb_modules[idx],
                  ENAMETOOLONG);
            continue;
        }
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) {
            emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=module index=%zu name=%s open_rc=-1 errno=%d\n",
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
        emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=module index=%zu name=%s finit_rc=%ld errno=%d ok=%d\n",
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
        emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=configfs_write path=%s rc=-1 errno=%d\n", path, errno);
        return -1;
    }
    write_all(fd, value, strlen(value));
    close(fd);
    return 0;
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

static void create_ncm_gadget(void) {
    const char *g = "/config/usb_gadget/g1";
    mkdir_p(g, 0755);
    mkdir_p("/config/usb_gadget/g1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0755);
    mkdir_p("/config/usb_gadget/g1/functions/ncm.0", 0755);

    (void)write_attr("/config/usb_gadget/g1/idVendor", "0x04e8");
    (void)write_attr("/config/usb_gadget/g1/idProduct", "0x6860");
    (void)write_attr("/config/usb_gadget/g1/bcdUSB", "0x0320");
    (void)write_attr("/config/usb_gadget/g1/bcdDevice", "0x0001");
    (void)write_attr("/config/usb_gadget/g1/bDeviceClass", "0xef");
    (void)write_attr("/config/usb_gadget/g1/bDeviceSubClass", "0x02");
    (void)write_attr("/config/usb_gadget/g1/bDeviceProtocol", "0x01");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/manufacturer", "Codex");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/product", "S22 Native Init M3 NCM");
    (void)write_attr("/config/usb_gadget/g1/strings/0x409/serialnumber", "S22M3OBS0001");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/MaxPower", "500");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/bmAttributes", "0x80");
    (void)write_attr("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "ncm");
    (void)write_attr("/config/usb_gadget/g1/functions/ncm.0/qmult", "5");

    errno = 0;
    int symlink_rc = symlink("../../functions/ncm.0", "/config/usb_gadget/g1/configs/b.1/f1");
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
    emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=ncm_gadget symlink_rc=%d symlink_errno=%d have_udc=%d udc=%s udc_rc=%d udc_errno=%d\n",
          symlink_rc,
          symlink_errno,
          have_udc ? 1 : 0,
          udc,
          udc_rc,
          udc_errno);

    char ifname[64] = "";
    for (int i = 0; i < 30; ++i) {
        if (read_trim("/config/usb_gadget/g1/functions/ncm.0/ifname", ifname, sizeof(ifname)) == 0 &&
            ifname[0] != '\0' && ifname[0] != '(') {
            break;
        }
        usleep(100000);
    }
    emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=ncm_ifname ifname=%s\n", ifname);
    emit("S22_NATIVE_INIT_OBSERVABLE_M3 phase=ncm_ipv4 skip=link-only-no-committed-addresses\n");
}

int main(int argc, char **argv, char **envp) {
    (void)argc;
    (void)argv;
    (void)envp;

    setup_minimal_fs();
    write_markers();
    load_usb_modules();
    create_ncm_gadget();

    for (unsigned int tick = 0;; ++tick) {
        emitf("S22_NATIVE_INIT_OBSERVABLE_M3 phase=heartbeat tick=%u\n", tick);
        sleep(5);
    }
}
