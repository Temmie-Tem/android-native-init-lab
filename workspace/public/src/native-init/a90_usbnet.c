#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdbool.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define GADGET_DIR "/config/usb_gadget/g1"
#define CONFIG_DIR GADGET_DIR "/configs/b.1"
#define FUNCTIONS_DIR GADGET_DIR "/functions"
#define UDC_PATH GADGET_DIR "/UDC"
#define ACM_FUNC FUNCTIONS_DIR "/acm.usb0"
#define NCM_FUNC FUNCTIONS_DIR "/ncm.usb0"
#define RNDIS_FUNC FUNCTIONS_DIR "/rndis.usb0"
#define ACM_LINK_TARGET ACM_FUNC
#define NCM_LINK_TARGET NCM_FUNC
#define RNDIS_LINK_TARGET RNDIS_FUNC
#define F1_LINK CONFIG_DIR "/f1"
#define F2_LINK CONFIG_DIR "/f2"
#define LOG_PATH "/cache/usbnet.log"
#define DEFAULT_UDC "a600000.dwc3"

static FILE *log_fp;
static bool console_enabled = true;

static void say(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    if (console_enabled) {
        va_list out_ap;
        va_copy(out_ap, ap);
        vfprintf(stdout, fmt, out_ap);
        fputc('\n', stdout);
        fflush(stdout);
        va_end(out_ap);
    }

    if (log_fp) {
        vfprintf(log_fp, fmt, ap);
        fputc('\n', log_fp);
        fflush(log_fp);
    }
    va_end(ap);
}

static void strip_tail(char *buf)
{
    size_t len = strlen(buf);
    while (len > 0 && (buf[len - 1] == '\n' || buf[len - 1] == '\r' ||
                       buf[len - 1] == ' ' || buf[len - 1] == '\t')) {
        buf[--len] = '\0';
    }
}

static int read_text(const char *path, char *buf, size_t size)
{
    int fd;
    ssize_t n;

    if (size == 0) {
        return -1;
    }

    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        snprintf(buf, size, "<read:%s>", strerror(errno));
        return -1;
    }

    n = read(fd, buf, size - 1);
    if (n < 0) {
        int saved_errno = errno;
        close(fd);
        snprintf(buf, size, "<read:%s>", strerror(saved_errno));
        return -1;
    }

    buf[n] = '\0';
    strip_tail(buf);
    close(fd);
    return 0;
}

static int write_text(const char *path, const char *value)
{
    int fd = open(path, O_WRONLY | O_TRUNC | O_CLOEXEC);
    size_t len = strlen(value);

    if (fd < 0) {
        say("write %s: open failed: %s", path, strerror(errno));
        return -1;
    }

    if (len > 0 && write(fd, value, len) != (ssize_t)len) {
        say("write %s: value failed: %s", path, strerror(errno));
        close(fd);
        return -1;
    }

    if (close(fd) < 0) {
        say("write %s: close failed: %s", path, strerror(errno));
        return -1;
    }

    return 0;
}

static int write_bytes(const char *path, const char *value, size_t len)
{
    int fd = open(path, O_WRONLY | O_TRUNC | O_CLOEXEC);

    if (fd < 0) {
        say("write %s: open failed: %s", path, strerror(errno));
        return -1;
    }

    if (len > 0 && write(fd, value, len) != (ssize_t)len) {
        say("write %s: bytes failed: %s", path, strerror(errno));
        close(fd);
        return -1;
    }

    if (close(fd) < 0) {
        say("write %s: close failed: %s", path, strerror(errno));
        return -1;
    }

    return 0;
}

static void write_best_effort(const char *path, const char *value)
{
    if (write_text(path, value) == 0) {
        say("write %s=%s", path, value[0] ? value : "<empty>");
    }
}

static int ensure_dir(const char *path)
{
    struct stat st;

    if (mkdir(path, 0755) == 0) {
        say("mkdir %s: ok", path);
        return 0;
    }

    if (errno == EEXIST && stat(path, &st) == 0 && S_ISDIR(st.st_mode)) {
        return 0;
    }

    say("mkdir %s: %s", path, strerror(errno));
    return -1;
}

static int ensure_link(const char *target, const char *link_path)
{
    char current[256];
    ssize_t n;

    n = readlink(link_path, current, sizeof(current) - 1);
    if (n >= 0) {
        current[n] = '\0';
        if (strcmp(current, target) == 0) {
            say("link %s -> %s: already set", link_path, target);
            return 0;
        }
        if (unlink(link_path) < 0) {
            say("unlink %s: %s", link_path, strerror(errno));
            return -1;
        }
        say("unlink %s: replaced %s", link_path, current);
    } else if (errno != ENOENT) {
        say("readlink %s: %s", link_path, strerror(errno));
        return -1;
    }

    if (symlink(target, link_path) < 0) {
        say("symlink %s -> %s: %s", link_path, target, strerror(errno));
        return -1;
    }

    say("symlink %s -> %s: ok", link_path, target);
    return 0;
}

static int remove_link(const char *link_path)
{
    if (unlink(link_path) == 0) {
        say("unlink %s: ok", link_path);
        return 0;
    }

    if (errno == ENOENT) {
        say("unlink %s: absent", link_path);
        return 0;
    }

    say("unlink %s: %s", link_path, strerror(errno));
    return -1;
}

static void current_udc(char *buf, size_t size)
{
    if (read_text(UDC_PATH, buf, size) < 0 || buf[0] == '\0') {
        snprintf(buf, size, "%s", DEFAULT_UDC);
    }
}

static int unbind_udc(void)
{
    say("udc: unbind");
    console_enabled = false;
    return write_bytes(UDC_PATH, "\n", 1);
}

static int bind_udc(const char *udc)
{
    say("udc: bind %s", udc);
    return write_text(UDC_PATH, udc);
}

static void set_attr_best_effort(const char *path, const char *value)
{
    if (write_text(path, value) == 0) {
        say("attr %s=%s", path, value);
    }
}

static int configure_acm_base(void)
{
    struct stat st;

    ensure_dir(GADGET_DIR);
    ensure_dir(GADGET_DIR "/strings");
    ensure_dir(GADGET_DIR "/strings/0x409");
    ensure_dir(GADGET_DIR "/configs");
    ensure_dir(CONFIG_DIR);
    ensure_dir(CONFIG_DIR "/strings");
    ensure_dir(CONFIG_DIR "/strings/0x409");
    ensure_dir(FUNCTIONS_DIR);
    ensure_dir(ACM_FUNC);

    write_best_effort(GADGET_DIR "/idVendor", "0x04e8");
    write_best_effort(GADGET_DIR "/idProduct", "0x6861");
    write_best_effort(GADGET_DIR "/bcdUSB", "0x0200");
    write_best_effort(GADGET_DIR "/bcdDevice", "0x0100");
    write_best_effort(GADGET_DIR "/strings/0x409/serialnumber", "RFCM90CFWXA");
    write_best_effort(GADGET_DIR "/strings/0x409/manufacturer", "samsung");
    write_best_effort(GADGET_DIR "/strings/0x409/product", "SM8150-ACM");
    write_best_effort(CONFIG_DIR "/strings/0x409/configuration", "serial");
    write_best_effort(CONFIG_DIR "/MaxPower", "900");

    if (lstat(F1_LINK, &st) == 0) {
        return 0;
    }

    if (errno != ENOENT) {
        say("lstat %s: %s", F1_LINK, strerror(errno));
        return -1;
    }

    if (ensure_dir(ACM_FUNC) < 0) {
        return -1;
    }

    return ensure_link(ACM_LINK_TARGET, F1_LINK);
}

static int configure_net_function(const char *func_dir,
                                  const char *dev_addr,
                                  const char *host_addr)
{
    char path[256];

    if (ensure_dir(func_dir) < 0) {
        return -1;
    }

    snprintf(path, sizeof(path), "%s/dev_addr", func_dir);
    set_attr_best_effort(path, dev_addr);
    snprintf(path, sizeof(path), "%s/host_addr", func_dir);
    set_attr_best_effort(path, host_addr);
    snprintf(path, sizeof(path), "%s/qmult", func_dir);
    set_attr_best_effort(path, "5");

    return 0;
}

static int rollback_acm_only(const char *udc)
{
    say("rollback: ACM only");
    remove_link(F2_LINK);
    configure_acm_base();
    return bind_udc(udc);
}

static int enable_mode(const char *mode, int probe_seconds)
{
    char udc[128];
    const char *func_dir;
    const char *func_link;
    const char *dev_addr;
    const char *host_addr;

    if (strcmp(mode, "ncm") == 0) {
        func_dir = NCM_FUNC;
        func_link = NCM_LINK_TARGET;
        dev_addr = "02:11:22:33:44:56";
        host_addr = "02:11:22:33:44:55";
    } else if (strcmp(mode, "rndis") == 0) {
        func_dir = RNDIS_FUNC;
        func_link = RNDIS_LINK_TARGET;
        dev_addr = "02:11:22:33:44:66";
        host_addr = "02:11:22:33:44:65";
    } else {
        say("unknown mode: %s", mode);
        return 2;
    }

    current_udc(udc, sizeof(udc));
    say("mode: %s", mode);
    say("saved udc: %s", udc);

    if (configure_acm_base() < 0 ||
        configure_net_function(func_dir, dev_addr, host_addr) < 0) {
        rollback_acm_only(udc);
        return 1;
    }

    if (unbind_udc() < 0) {
        say("warning: unbind failed; continuing");
    }
    usleep(300000);

    if (ensure_link(func_link, F2_LINK) < 0) {
        rollback_acm_only(udc);
        return 1;
    }

    if (bind_udc(udc) < 0) {
        say("bind failed; attempting rollback");
        unbind_udc();
        usleep(100000);
        rollback_acm_only(udc);
        return 1;
    }

    say("mode %s: ready", mode);

    if (probe_seconds > 0) {
        say("probe: holding %s for %d seconds", mode, probe_seconds);
        sleep((unsigned int)probe_seconds);
        say("probe: restoring ACM only");
        unbind_udc();
        usleep(300000);
        remove_link(F2_LINK);
        configure_acm_base();
        if (bind_udc(udc) < 0) {
            return 1;
        }
        say("probe: restored ACM only");
    }

    return 0;
}

static int disable_net(void)
{
    char udc[128];

    current_udc(udc, sizeof(udc));
    say("mode: off");
    say("saved udc: %s", udc);

    if (unbind_udc() < 0) {
        say("warning: unbind failed; continuing");
    }
    usleep(300000);

    remove_link(F2_LINK);
    configure_acm_base();

    if (bind_udc(udc) < 0) {
        return 1;
    }

    say("mode off: ACM only ready");
    return 0;
}

static void print_file(const char *label, const char *path)
{
    char buf[256];

    if (read_text(path, buf, sizeof(buf)) == 0) {
        say("%s: %s", label, buf[0] ? buf : "<empty>");
    } else {
        say("%s: %s", label, buf);
    }
}

static void print_link(const char *label, const char *path)
{
    char buf[256];
    ssize_t n = readlink(path, buf, sizeof(buf) - 1);

    if (n < 0) {
        say("%s: <readlink:%s>", label, strerror(errno));
        return;
    }

    buf[n] = '\0';
    say("%s: %s", label, buf);
}

static void print_dir(const char *label, const char *path)
{
    DIR *dir = opendir(path);
    struct dirent *de;
    bool first = true;

    if (!dir) {
        say("%s: <opendir:%s>", label, strerror(errno));
        return;
    }

    printf("%s:", label);
    if (log_fp) {
        fprintf(log_fp, "%s:", label);
    }

    while ((de = readdir(dir)) != NULL) {
        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0) {
            continue;
        }

        printf("%s%s", first ? " " : ",", de->d_name);
        if (log_fp) {
            fprintf(log_fp, "%s%s", first ? " " : ",", de->d_name);
        }
        first = false;
    }

    if (first) {
        printf(" <empty>");
        if (log_fp) {
            fprintf(log_fp, " <empty>");
        }
    }

    printf("\n");
    fflush(stdout);
    if (log_fp) {
        fprintf(log_fp, "\n");
        fflush(log_fp);
    }

    closedir(dir);
}

static int show_status(void)
{
    say("a90_usbnet status");
    print_file("udc", UDC_PATH);
    print_file("idVendor", GADGET_DIR "/idVendor");
    print_file("idProduct", GADGET_DIR "/idProduct");
    print_file("manufacturer", GADGET_DIR "/strings/0x409/manufacturer");
    print_file("product", GADGET_DIR "/strings/0x409/product");
    print_file("serialnumber", GADGET_DIR "/strings/0x409/serialnumber");
    print_dir("functions", FUNCTIONS_DIR);
    print_dir("config b.1", CONFIG_DIR);
    print_link("f1", F1_LINK);
    print_link("f2", F2_LINK);
    print_file("ncm.ifname", NCM_FUNC "/ifname");
    print_file("ncm.dev_addr", NCM_FUNC "/dev_addr");
    print_file("ncm.host_addr", NCM_FUNC "/host_addr");
    print_file("rndis.ifname", RNDIS_FUNC "/ifname");
    print_file("rndis.dev_addr", RNDIS_FUNC "/dev_addr");
    print_file("rndis.host_addr", RNDIS_FUNC "/host_addr");
    return 0;
}

static void usage(const char *argv0)
{
    say("usage: %s status|ncm|rndis|probe-ncm|probe-rndis|off", argv0);
}

static void redirect_stdio_to_null(void)
{
    int fd = open("/dev/null", O_RDWR | O_CLOEXEC);

    if (fd < 0) {
        return;
    }

    dup2(fd, STDIN_FILENO);
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);
    if (fd > STDERR_FILENO) {
        close(fd);
    }
}

static int detached_probe(const char *mode, int probe_seconds)
{
    pid_t pid = fork();

    if (pid < 0) {
        say("probe: fork failed: %s", strerror(errno));
        return 1;
    }

    if (pid > 0) {
        say("probe: detached pid=%ld mode=%s seconds=%d", (long)pid, mode, probe_seconds);
        return 0;
    }

    signal(SIGHUP, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);
    setsid();
    console_enabled = false;
    redirect_stdio_to_null();
    sleep(1);
    return enable_mode(mode, probe_seconds);
}

int main(int argc, char **argv)
{
    const char *cmd = argc >= 2 ? argv[1] : "status";
    int rc;

    signal(SIGHUP, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);
    setsid();

    log_fp = fopen(LOG_PATH, "a");
    say("---- a90_usbnet %s ----", cmd);

    if (strcmp(cmd, "status") == 0) {
        rc = show_status();
    } else if (strcmp(cmd, "ncm") == 0 || strcmp(cmd, "rndis") == 0) {
        rc = enable_mode(cmd, 0);
    } else if (strcmp(cmd, "probe-ncm") == 0) {
        rc = detached_probe("ncm", 15);
    } else if (strcmp(cmd, "probe-rndis") == 0) {
        rc = detached_probe("rndis", 15);
    } else if (strcmp(cmd, "off") == 0 || strcmp(cmd, "acm") == 0) {
        rc = disable_net();
    } else {
        usage(argv[0]);
        rc = 2;
    }

    say("a90_usbnet: rc=%d", rc);
    if (log_fp) {
        fclose(log_fp);
    }
    return rc;
}
