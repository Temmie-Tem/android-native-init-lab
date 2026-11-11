/* ARM64 VM fixture. The client runs in its own network namespace with only
 * the CDC-NCM host interface. The responder owns the gadget interface. */
#define main canary_unused_main
#include "../../s22plus_canary_h0/init.c"
#undef main
#include <linux/rtnetlink.h>
#include <sched.h>
#include <sys/reboot.h>
#include <sys/klog.h>

enum { FIELDS = 7, BODY_BYTES = 8 + 32 + 32 + (FIELDS + 2) * 4, FRAME_BYTES = BODY_BYTES + 32 };
#define SAMPLE "/proc/g0q_udc_vm_sample"
#define UDC "/sys/class/udc/a600000.usb/"

static void failed(const char *step, int error)
{
    char log[16384];
    int size = klogctl(3, log, sizeof(log) - 1);
    if (size > 0) {
        log[size] = 0;
        dprintf(2, "%s\n", log);
    }
    dprintf(2, "VM_FAIL %s error=%d\n", step, error);
    _exit(1);
}

static void check(int error, const char *step)
{
    if (error) failed(step, error);
}

static void syscall_ok(int value, const char *step)
{
    if (value < 0) failed(step, errno);
}

static void brief_wait(const char *step)
{
    if (now_ms() >= deadline) failed(step, ETIMEDOUT);
    usleep(25000);
}

static void freeze_sample(uint32_t words[FIELDS])
{
    for (;;) {
        char text[160] = {0};
        size_t used;
        unsigned ms, binds, end, attempt_ms, result;
        int state, rc;
        check(read_small(SAMPLE, text, sizeof(text) - 1, &used), "read RAM sample");
        if (sscanf(text, "%u %d %u %u %d %u %u", &ms, &state, &binds, &end,
                   &rc, &attempt_ms, &result) != FIELDS) failed("sample format", EPROTO);
        if (binds == 1 && end && ms > end) {
            const uint32_t frozen[] = {ms, (uint32_t)state, binds, end,
                                       (uint32_t)rc, attempt_ms, result};
            memcpy(words, frozen, sizeof(frozen));
            return;
        }
        brief_wait("waiting for post-bind RAM sample");
    }
}

static void find_host_interface(char name[IFNAMSIZ])
{
    for (;;) {
        struct if_nameindex *list = if_nameindex();
        if (!list) failed("interfaces", errno);
        for (struct if_nameindex *i = list; i->if_index; ++i) {
            char path[128], driver[256];
            snprintf(path, sizeof(path), "/sys/class/net/%s/device/driver", i->if_name);
            ssize_t n = readlink(path, driver, sizeof(driver) - 1);
            if (n < 0 || n == (ssize_t)sizeof(driver) - 1) continue;
            driver[n] = 0;
            const char *last = strrchr(driver, '/');
            if (last && !strcmp(last, "/cdc_ncm")) {
                snprintf(name, IFNAMSIZ, "%s", i->if_name);
                if_freenameindex(list);
                return;
            }
        }
        if_freenameindex(list);
        brief_wait("waiting for CDC-NCM host driver");
    }
}

static void move_interface(const char *name, pid_t child)
{
    int fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_ROUTE);
    syscall_ok(fd, "netlink socket");
    struct {
        struct nlmsghdr header;
        struct ifinfomsg device;
        struct rtattr attribute;
        int pid;
    } request = {
        .header = {.nlmsg_len = sizeof(request), .nlmsg_type = RTM_NEWLINK,
                   .nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK, .nlmsg_seq = 1},
        .device = {.ifi_family = AF_UNSPEC, .ifi_index = (int)if_nametoindex(name)},
        .attribute = {.rta_type = IFLA_NET_NS_PID, .rta_len = RTA_LENGTH(sizeof(int))},
        .pid = child,
    };
    struct sockaddr_nl kernel = {.nl_family = AF_NETLINK};
    if (!request.device.ifi_index) failed("host ifindex", ENODEV);
    syscall_ok(sendto(fd, &request, sizeof(request), 0, (void *)&kernel, sizeof(kernel)),
               "move host interface");
    struct { struct nlmsghdr hdr; struct nlmsgerr ack; char extra[128]; } reply;
    ssize_t n = recv(fd, &reply, sizeof(reply), 0);
    if (n < (ssize_t)NLMSG_LENGTH(sizeof(struct nlmsgerr)) ||
        reply.hdr.nlmsg_type != NLMSG_ERROR || reply.hdr.nlmsg_seq != 1)
        failed("netlink ACK", EPROTO);
    check(-reply.ack.error, "host interface namespace");
    close(fd);
}

static void address_host(const char *name)
{
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    syscall_ok(fd, "host configuration");
    struct ifreq iface = {0};
    snprintf(iface.ifr_name, sizeof(iface.ifr_name), "%s", name);
    struct sockaddr_in *addr = (void *)&iface.ifr_addr;
    addr->sin_family = AF_INET;
    if (inet_pton(AF_INET, canary_host_ip, &addr->sin_addr) != 1) failed("host address", EINVAL);
    syscall_ok(ioctl(fd, SIOCSIFADDR, &iface), "set host address");
    if (inet_pton(AF_INET, canary_netmask, &addr->sin_addr) != 1) failed("netmask", EINVAL);
    syscall_ok(ioctl(fd, SIOCSIFNETMASK, &iface), "set host netmask");
    syscall_ok(ioctl(fd, SIOCGIFFLAGS, &iface), "get host flags");
    iface.ifr_flags |= IFF_UP;
    syscall_ok(ioctl(fd, SIOCSIFFLAGS, &iface), "host link up");
    close(fd);
}

static struct sockaddr_in destination(void)
{
    struct sockaddr_in addr = {.sin_family = AF_INET, .sin_port = htons(CANARY_PORT)};
    if (inet_pton(AF_INET, canary_device_ip, &addr.sin_addr) != 1) failed("device address", EINVAL);
    return addr;
}

static void exchange_client(const char *name, int syncfd, int listener)
{
    close(listener);
    syscall_ok(unshare(CLONE_NEWNET), "client network namespace");
    char ready = 'R';
    if (write(syncfd, &ready, 1) != 1 || read(syncfd, &ready, 1) != 1) failed("client sync", EPIPE);
    close(syncfd);
    address_host(name);
    int client = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    syscall_ok(client, "client socket");
    syscall_ok(setsockopt(client, SOL_SOCKET, SO_BINDTODEVICE, name, strlen(name) + 1),
               "bind to CDC-NCM");
    struct sockaddr_in addr = destination();
    syscall_ok(connect(client, (struct sockaddr *)&addr, sizeof(addr)), "NCM TCP connect");
    uint8_t request[G0Q_REQUEST_SIZE], response[FRAME_BYTES], tag[32];
    size_t bytes;
    check(read_small("/challenge", request, sizeof(request), &bytes), "client challenge");
    if (bytes != sizeof(request)) failed("challenge length", EPROTO);
    check(transfer(client, request, sizeof(request), 1), "client write");
    check(transfer(client, response, sizeof(response), 0), "client read");
    g_tag(tag, canary_key, canary_id, 1, response, BODY_BYTES);
    if (!g_equal(tag, response + BODY_BYTES, 32) || memcmp(response, "UDCLIVE1", 8) ||
        memcmp(response + 8, canary_id, 32) || memcmp(response + 40, request + 8, 32))
        failed("client authentication", EACCES);
    char hex[2 * FRAME_BYTES + 1];
    for (size_t i = 0; i < sizeof(response); i++) snprintf(hex + 2*i, 3, "%02x", response[i]);
    dprintf(2, "VM_NCM_RECEIVED %s\n", hex);
    close(client);
}

int main(void)
{
    if (getpid() != 1) return 1;
    int tty = open("/dev/ttyAMA0", O_RDWR | O_NOCTTY);
    if (tty < 0 || dup2(tty, 2) < 0) return 2;
    syscall_ok(mount("proc", "/proc", "proc", 0, NULL), "mount proc");
    syscall_ok(mount("sysfs", "/sys", "sysfs", 0, NULL), "mount sys");
    deadline = 120000;
    check(usb(), "bind NCM gadget");
    uint32_t sample[FIELDS];
    freeze_sample(sample);
    dprintf(2, "VM_PRE_SAMPLE time=%u bind_end=%u\n", sample[0], sample[3]);
    uint32_t opened = now_ms();
    check(put("/sys/module/dummy_hcd/parameters/vm_cable", "1"), "connect virtual peer");
    char host[IFNAMSIZ];
    dprintf(2, "VM_CABLE_CONNECTED\n");
    find_host_interface(host);
    int listenfd = socket(AF_INET, SOCK_STREAM, 0);
    syscall_ok(listenfd, "gadget socket");
    struct sockaddr_in addr = destination();
    syscall_ok(bind(listenfd, (void *)&addr, sizeof(addr)), "bind gadget address");
    syscall_ok(listen(listenfd, 1), "listen");
    int syncfd[2];
    syscall_ok(socketpair(AF_UNIX, SOCK_STREAM, 0, syncfd), "namespace sync");
    pid_t child = fork();
    syscall_ok(child, "start client");
    if (!child) {
        close(syncfd[0]); exchange_client(host, syncfd[1], listenfd); _exit(0);
    }
    close(syncfd[1]);
    char ready;
    if (read(syncfd[0], &ready, 1) != 1) failed("namespace ready", EPIPE);
    move_interface(host, child);
    if (write(syncfd[0], &ready, 1) != 1) failed("release client", EPIPE);
    close(syncfd[0]);
    struct sockaddr_in peer;
    socklen_t len = sizeof(peer);
    int client = accept(listenfd, (void *)&peer, &len);
    syscall_ok(client, "NCM TCP accept");
    struct in_addr expected;
    if (inet_pton(AF_INET, canary_host_ip, &expected) != 1 || peer.sin_addr.s_addr != expected.s_addr)
        failed("NCM peer address", EACCES);
    uint8_t request[G0Q_REQUEST_SIZE], response[FRAME_BYTES] = {0};
    check(transfer(client, request, sizeof(request), 0), "gadget request");
    if (!g_request(request, canary_key, canary_id)) failed("request authentication", EACCES);
    char state[32] = {0};
    size_t bytes;
    check(read_small(UDC "state", state, sizeof(state) - 1, &bytes), "post-connect UDC state");
    if (strcmp(state, "configured\n")) failed("post-connect configuration", EPROTO);
    memcpy(response, "UDCLIVE1", 8);
    memcpy(response + 8, canary_id, 32);
    memcpy(response + 40, request + 8, 32);
    for (unsigned i = 0; i < FIELDS; i++) g_put32(response + 72 + i*4, sample[i]);
    g_put32(response + 72 + FIELDS*4, opened);
    g_put32(response + 76 + FIELDS*4, now_ms());
    g_tag(response + BODY_BYTES, canary_key, canary_id, 1, response, BODY_BYTES);
    check(transfer(client, response, sizeof(response), 1), "gadget response");
    close(client); close(listenfd);
    int status;
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status))
        failed("client exit", EIO);
    dprintf(2, "VM_NCM_DONE\n");
    reboot(RB_POWER_OFF);
    return 0;
}
