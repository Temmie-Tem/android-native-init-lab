// SPDX-License-Identifier: MIT
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>

#include "build-id.h"

#define UDC "a600000.usb"
#define GADGET "/config/usb_gadget/y2q"
#define FUNCTION GADGET "/functions/acm.usb0"
#define CONFIGURATION GADGET "/configs/c.1"
#define WITNESS "S20PLUS_Y2Q_MAINLINE_V1 id=" Y2Q_BUILD_ID " pid=1"

static int write_attribute(const char *path, const char *value)
{
    const int fd = open(path, O_WRONLY | O_CLOEXEC);
    const size_t length = strlen(value);
    int error = 0;

    if (fd < 0)
        return errno;
    const ssize_t written = write(fd, value, length);
    if (written < 0)
        error = errno;
    else if ((size_t)written != length)
        error = EIO;
    if (close(fd) < 0 && !error)
        error = errno;
    return error;
}

static _Noreturn void park(const char *stage, int error)
{
    dprintf(STDERR_FILENO, WITNESS " stage=%s errno=%d\n", stage, error);
    for (;;)
        pause();
}

static void mount_runtime(void)
{
    if (mount("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, NULL) < 0)
        park("DEVTMPFS_FAILED", errno);
    if (mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) < 0)
        park("SYSFS_FAILED", errno);
    if (mount("configfs", "/config", "configfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) < 0)
        park("CONFIGFS_FAILED", errno);
}

static void create_gadget(void)
{
    const char *const directories[] = {
        GADGET, GADGET "/strings/0x409", CONFIGURATION, FUNCTION,
    };
    for (size_t i = 0; i < sizeof(directories) / sizeof(directories[0]); ++i) {
        if (mkdir(directories[i], 0700) < 0)
            park("GADGET_MKDIR_FAILED", errno);
    }

    const struct {
        const char *path;
        const char *value;
    } attributes[] = {
        { GADGET "/idVendor", "0x1d6b" },
        { GADGET "/idProduct", "0x0104" },
        { GADGET "/strings/0x409/product", "S20+ y2q mainline witness" },
        { GADGET "/strings/0x409/serialnumber", "y2q-" Y2Q_BUILD_ID },
    };
    for (size_t i = 0; i < sizeof(attributes) / sizeof(attributes[0]); ++i) {
        const int error = write_attribute(attributes[i].path, attributes[i].value);
        if (error)
            park("GADGET_ATTRIBUTE_FAILED", error);
    }
    if (symlink(FUNCTION, CONFIGURATION "/acm.usb0") < 0)
        park("ACM_LINK_FAILED", errno);

    const int error = write_attribute(GADGET "/UDC", UDC);
    if (error)
        park("UDC_BIND_FAILED", error);
}

static _Noreturn void send_witness(void)
{
    /* The only ACM function in this initramfs allocated the first port. */
    static const char marker[] = "\n" WITNESS " stage=ACM_READY\n";
    const int fd = open("/dev/ttyGS0", O_WRONLY | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    struct termios mode;
    unsigned int complete_writes = 0;

    if (fd < 0)
        park("ACM_OPEN_FAILED", errno);
    if (tcgetattr(fd, &mode) < 0)
        park("ACM_TERMIOS_FAILED", errno);
    cfmakeraw(&mode);
    if (tcsetattr(fd, TCSANOW, &mode) < 0)
        park("ACM_TERMIOS_FAILED", errno);
    for (unsigned int attempt = 0; attempt < 120; ++attempt) {
        if (write(fd, marker, sizeof(marker) - 1) == (ssize_t)sizeof(marker) - 1)
            ++complete_writes;
        sleep(1);
    }
    park(complete_writes ? "ACM_WRITE_WINDOW_CLOSED" : "ACM_NO_COMPLETE_WRITE", 0);
}

int main(void)
{
    if (getpid() != 1) {
        fputs("The y2q witness requires PID 1.\n", stderr);
        return 1;
    }
    dprintf(STDERR_FILENO, WITNESS " stage=INIT_ENTERED\n");
    mount_runtime();
    for (unsigned int attempt = 0; attempt < 20; ++attempt) {
        if (access("/sys/class/udc/" UDC, F_OK) == 0) {
            create_gadget();
            send_witness();
        }
        sleep(1);
    }
    park("UDC_NOT_PRESENT", ENODEV);
}
