#include "a90_usb_gadget.h"

#include "a90_config.h"
#include "a90_log.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

#define A90_USB_GADGET_ROOT "/config/usb_gadget/g1"
#define A90_USB_GADGET_CONFIG A90_USB_GADGET_ROOT "/configs/b.1"
#define A90_USB_GADGET_ACM_FUNCTION A90_USB_GADGET_ROOT "/functions/acm.usb0"
#define A90_USB_GADGET_ACM_LINK A90_USB_GADGET_CONFIG "/f1"
#define A90_USB_GADGET_ADB_LINK A90_USB_GADGET_CONFIG "/f2"
#define A90_USB_GADGET_UDC_PATH A90_USB_GADGET_ROOT "/UDC"
#define A90_USB_GADGET_DEFAULT_UDC "a600000.dwc3"

static int write_file(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    int saved_errno;

    if (fd < 0) {
        return -1;
    }
    if (write_all_checked(fd, value, strlen(value)) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (close(fd) < 0) {
        return -1;
    }
    return 0;
}

static int create_symlink_checked(const char *target, const char *linkpath) {
    if (symlink(target, linkpath) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
}

static bool path_exists(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0;
}

static bool path_is_symlink(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0 && S_ISLNK(st.st_mode);
}

static int ensure_configfs(void) {
    if (mount("configfs", "/config", "configfs", 0, NULL) == 0 || errno == EBUSY) {
        return 0;
    }
    return -1;
}

int a90_usb_gadget_unbind(void) {
    if (write_file(A90_USB_GADGET_UDC_PATH, "") < 0) {
        if (errno == EBUSY) {
            a90_logf("usb", "UDC unbind busy; continuing");
            return 0;
        }
        return negative_errno_or(EIO);
    }
    return 0;
}

int a90_usb_gadget_bind_default_udc(void) {
    if (write_file(A90_USB_GADGET_UDC_PATH, A90_USB_GADGET_DEFAULT_UDC) < 0) {
        if (errno == EBUSY) {
            a90_logf("usb", "UDC already busy/bound; continuing");
            return 0;
        }
        return negative_errno_or(EIO);
    }
    return 0;
}

int a90_usb_gadget_setup_acm(void) {
    if (ensure_configfs() < 0) {
        return negative_errno_or(EIO);
    }

    ensure_dir("/config/usb_gadget", 0770);
    ensure_dir(A90_USB_GADGET_ROOT, 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/strings", 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/strings/0x409", 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/configs", 0770);
    ensure_dir(A90_USB_GADGET_CONFIG, 0770);
    ensure_dir(A90_USB_GADGET_CONFIG "/strings", 0770);
    ensure_dir(A90_USB_GADGET_CONFIG "/strings/0x409", 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/functions", 0770);
    ensure_dir(A90_USB_GADGET_ACM_FUNCTION, 0770);

    write_file(A90_USB_GADGET_ROOT "/idVendor", "0x04e8");
    write_file(A90_USB_GADGET_ROOT "/idProduct", "0x6861");
    write_file(A90_USB_GADGET_ROOT "/bcdUSB", "0x0200");
    write_file(A90_USB_GADGET_ROOT "/bcdDevice", "0x0100");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/serialnumber", "RFCM90CFWXA");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/manufacturer", "samsung");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/product", "SM8150-ACM");
    write_file(A90_USB_GADGET_CONFIG "/strings/0x409/configuration", "serial");
    write_file(A90_USB_GADGET_CONFIG "/MaxPower", "900");

    if (create_symlink_checked(A90_USB_GADGET_ACM_FUNCTION, A90_USB_GADGET_ACM_LINK) < 0) {
        return negative_errno_or(EIO);
    }

    return a90_usb_gadget_bind_default_udc();
}

int a90_usb_gadget_reset_acm(void) {
    int rc;

    rc = a90_usb_gadget_unbind();
    if (rc < 0) {
        return rc;
    }
    usleep(300000);
    unlink(A90_USB_GADGET_ADB_LINK);
    return a90_usb_gadget_setup_acm();
}

int a90_usb_gadget_status(struct a90_usb_gadget_status *out) {
    char udc[sizeof(out->udc)];

    if (out == NULL) {
        return -EINVAL;
    }

    memset(out, 0, sizeof(*out));
    out->configfs_mounted = path_exists("/config/usb_gadget");
    out->gadget_dir = path_exists(A90_USB_GADGET_ROOT);
    out->acm_function = path_exists(A90_USB_GADGET_ACM_FUNCTION);
    out->acm_link = path_is_symlink(A90_USB_GADGET_ACM_LINK);
    out->adb_link = path_is_symlink(A90_USB_GADGET_ADB_LINK);
    if (read_trimmed_text_file(A90_USB_GADGET_UDC_PATH, udc, sizeof(udc)) == 0) {
        snprintf(out->udc, sizeof(out->udc), "%s", udc);
        out->udc_bound = out->udc[0] != '\0';
    }
    return 0;
}
