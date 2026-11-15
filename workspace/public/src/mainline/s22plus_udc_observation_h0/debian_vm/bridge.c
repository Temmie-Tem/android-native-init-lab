/* VM-only /init overlay. PID 1 execs packaged Debian SysVinit. The child
 * provides an Ethernet bridge between a PC TAP and the dummy USB host. */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/sockios.h>
#include <net/if.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define BRIDGE "vmbridge"
#define HISTORY "/proc/g0q_udc_history"

static unsigned long boot_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_BOOTTIME, &t)) _exit(1);
    return (unsigned long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void fail(const char *step)
{
    dprintf(STDERR_FILENO, "VM_BRIDGE_FAIL step=%s errno=%d\n", step, errno);
    _exit(1);
}

static void wait_for_guest(const char *what)
{
    if (boot_ms() >= 115000) fail(what);
    usleep(10000);
}

static void write_one(const char *path, const char *value)
{
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0 || write(fd, value, strlen(value)) != (ssize_t)strlen(value) || close(fd))
        fail(path);
}

/* The fixture observes the kernel's sample clock independently of the PC
 * response. It neither supplies observation values nor changes the writer. */
static void wait_sample(unsigned long after, int configured)
{
    for (;;) {
        uint8_t data[136];
        int fd = open(HISTORY, O_RDONLY | O_CLOEXEC);
        if (fd >= 0) {
            ssize_t n = read(fd, data, sizeof(data));
            close(fd);
            if (n == sizeof(data)) {
                uint32_t bind_end, seen;
                memcpy(&bind_end, data + 44, 4);
                memcpy(&seen, data + 88, 4);
                for (unsigned i = 0; bind_end && i < 6; ++i) {
                    uint32_t measured;
                    int16_t state;
                    memcpy(&measured, data + 52 + 6*i, 4);
                    memcpy(&state, data + 56 + 6*i, 2);
                    if ((seen & (1U << i)) && measured > bind_end && measured > after &&
                        boot_ms() > measured && (!configured || state == 7))
                        return;
                }
            }
        }
        wait_for_guest("post-bind UDC sample");
    }
}

static void host_interface(char result[IFNAMSIZ])
{
    for (;;) {
        struct if_nameindex *list = if_nameindex();
        if (!list) fail("interfaces");
        for (struct if_nameindex *i = list; i->if_index; ++i) {
            char path[96], target[256];
            snprintf(path, sizeof(path), "/sys/class/net/%s/device/driver", i->if_name);
            ssize_t n = readlink(path, target, sizeof(target)-1);
            if (n < 0 || n == sizeof(target)-1) continue;
            target[n] = 0;
            const char *base = strrchr(target, '/');
            if (base && !strcmp(base, "/cdc_ncm")) {
                snprintf(result, IFNAMSIZ, "%s", i->if_name);
                if_freenameindex(list);
                return;
            }
        }
        if_freenameindex(list);
        wait_for_guest("CDC-NCM enumeration");
    }
}

static void link_up(int fd, const char *name)
{
    struct ifreq r = {0};
    snprintf(r.ifr_name, IFNAMSIZ, "%s", name);
    if (ioctl(fd, SIOCGIFFLAGS, &r)) fail("get link flags");
    r.ifr_flags |= IFF_UP;
    if (ioctl(fd, SIOCSIFFLAGS, &r)) fail("link up");
}

static void bridge_port(int fd, const char *name)
{
    struct ifreq r = {0};
    snprintf(r.ifr_name, IFNAMSIZ, "%s", BRIDGE);
    r.ifr_ifindex = if_nametoindex(name);
    if (!r.ifr_ifindex || ioctl(fd, SIOCBRADDIF, &r)) fail("bridge port");
    link_up(fd, name);
}

int main(void)
{
    if (getpid() != 1) return 1;
    pid_t child = fork();
    if (child < 0) return 2;
    if (child) {
        execl("/usr/sbin/init", "init", (char *)NULL);
        return 3;
    }
    int tty = open("/dev/ttyAMA0", O_WRONLY | O_NOCTTY);
    if (tty < 0 || dup2(tty, 2) < 0) return 4;
    if (access("/vm-no-peer", F_OK) == 0) return 0;
    wait_sample(0, 0);
    unsigned long before = boot_ms();
    write_one("/sys/module/dummy_hcd/parameters/vm_cable", "1");
    unsigned long after = boot_ms();
    dprintf(2, "VM_CABLE before=%lu after=%lu\n", before, after);
    char host[IFNAMSIZ];
    host_interface(host);
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0 || ioctl(fd, SIOCBRADDBR, BRIDGE)) fail("create bridge");
    write_one("/sys/class/net/" BRIDGE "/bridge/forward_delay", "0");
    bridge_port(fd, "eth0");
    bridge_port(fd, host);
    link_up(fd, BRIDGE);
    wait_sample(after, 1);
    dprintf(2, "VM_NCM_BRIDGE_READY guest_ms=%lu\n", boot_ms());
    return 0;
}
