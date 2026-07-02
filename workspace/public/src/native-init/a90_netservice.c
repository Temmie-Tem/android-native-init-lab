#include "a90_netservice.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_run.h"
#include "a90_service.h"
#include "a90_timeline.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

static int netservice_run_wait(char *const argv[], const char *tag, int timeout_ms) {
    static char *const envp[] = {
        "PATH=/cache/bin:/cache:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        NULL
    };
    struct a90_run_config config = {
        .tag = tag,
        .argv = argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = NETSERVICE_LOG_PATH,
        .setsid = true,
        .ignore_hup_pipe = true,
        .timeout_ms = timeout_ms,
        .stop_timeout_ms = 2000,
    };
    struct a90_run_result result;
    pid_t pid;
    int child_rc;
    int wait_rc;

    wait_rc = a90_run_spawn(&config, &pid);
    if (wait_rc < 0) {
        return wait_rc;
    }

    wait_rc = a90_run_wait(pid, &config, &result);
    if (wait_rc < 0) {
        return wait_rc;
    }

    child_rc = a90_run_result_to_rc(&result);
    if (child_rc == 0) {
        a90_logf("netservice", "%s ok", tag);
        return 0;
    }
    if (WIFEXITED(result.status)) {
        a90_logf("netservice", "%s exit=%d", tag, WEXITSTATUS(result.status));
        return -EIO;
    }
    if (WIFSIGNALED(result.status)) {
        a90_logf("netservice", "%s signal=%d", tag, WTERMSIG(result.status));
        return -EINTR;
    }

    a90_logf("netservice", "%s unknown status=0x%x", tag, result.status);
    return -ECHILD;
}

static int netservice_wait_for_ifname(const char *ifname, int timeout_ms) {
    char path[PATH_MAX];
    long deadline = monotonic_millis() + timeout_ms;

    snprintf(path, sizeof(path), "/sys/class/net/%s", ifname);
    while (monotonic_millis() < deadline) {
        if (access(path, F_OK) == 0) {
            return 0;
        }
        usleep(100000);
    }

    a90_logf("netservice", "interface %s did not appear", ifname);
    return -ETIMEDOUT;
}

void a90_netservice_reap(void) {
    if (a90_service_reap(A90_SERVICE_TCPCTL, NULL) > 0) {
        a90_logf("netservice", "tcpctl exited");
    }
}

static bool netservice_token_valid(const char *token) {
    size_t len;
    size_t index;

    if (token == NULL) {
        return false;
    }
    len = strlen(token);
    if (len < 32 || len >= 64) {
        return false;
    }
    for (index = 0; index < len; ++index) {
        char ch = token[index];

        if (!((ch >= '0' && ch <= '9') ||
              (ch >= 'a' && ch <= 'f') ||
              (ch >= 'A' && ch <= 'F'))) {
            return false;
        }
    }
    return true;
}

static int netservice_write_token(const char *token) {
    int fd;

    fd = open(NETSERVICE_TCP_TOKEN_PATH,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -errno;
    }
    if (fchmod(fd, 0600) < 0) {
        int saved_errno = errno;

        close(fd);
        return -saved_errno;
    }
    if (write_all_checked(fd, token, strlen(token)) < 0 ||
        write_all_checked(fd, "\n", 1) < 0) {
        int saved_errno = errno;

        close(fd);
        return -saved_errno;
    }
    if (close(fd) < 0) {
        return -errno;
    }
    return 0;
}

static int netservice_generate_token(char *out, size_t out_size) {
    static const char hex[] = "0123456789abcdef";
    unsigned char random_bytes[16];
    size_t offset = 0;
    size_t index;

    if (out == NULL || out_size < 33) {
        return -EINVAL;
    }

    while (offset < sizeof(random_bytes)) {
        ssize_t rd = getrandom(random_bytes + offset,
                               sizeof(random_bytes) - offset,
                               0);

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        if (rd == 0) {
            break;
        }
        offset += (size_t)rd;
    }

    if (offset < sizeof(random_bytes)) {
        int fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);

        if (fd < 0) {
            return -errno;
        }
        while (offset < sizeof(random_bytes)) {
            ssize_t rd = read(fd,
                              random_bytes + offset,
                              sizeof(random_bytes) - offset);

            if (rd < 0) {
                int saved_errno = errno != 0 ? errno : EIO;

                close(fd);
                return -saved_errno;
            }
            if (rd == 0) {
                close(fd);
                return -EIO;
            }
            offset += (size_t)rd;
        }
        close(fd);
    }

    for (index = 0; index < sizeof(random_bytes); ++index) {
        out[index * 2] = hex[random_bytes[index] >> 4];
        out[index * 2 + 1] = hex[random_bytes[index] & 0x0f];
    }
    out[32] = '\0';
    return 0;
}

int a90_netservice_rotate_token(char *out, size_t out_size) {
    char token[64];
    int rc;

    rc = netservice_generate_token(token, sizeof(token));
    if (rc < 0) {
        return rc;
    }
    rc = netservice_write_token(token);
    if (rc < 0) {
        return rc;
    }
    if (out != NULL && out_size > 0) {
        snprintf(out, out_size, "%s", token);
    }
    a90_logf("netservice", "tcpctl token rotated path=%s", NETSERVICE_TCP_TOKEN_PATH);
    return 0;
}

int a90_netservice_token(char *out, size_t out_size) {
    char token[64];

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    if (read_trimmed_text_file(NETSERVICE_TCP_TOKEN_PATH, token, sizeof(token)) == 0 &&
        netservice_token_valid(token)) {
        snprintf(out, out_size, "%s", token);
        return 0;
    }
    return a90_netservice_rotate_token(out, out_size);
}

bool a90_netservice_enabled(void) {
    char state[64];

    if (read_trimmed_text_file(NETSERVICE_FLAG_PATH, state, sizeof(state)) < 0) {
        return false;
    }

    return strcmp(state, "1") == 0 ||
           strcmp(state, "on") == 0 ||
           strcmp(state, "enable") == 0 ||
           strcmp(state, "enabled") == 0 ||
           strcmp(state, "ncm") == 0 ||
           strcmp(state, "tcpctl") == 0;
}

static bool netservice_tcpctl_requested(void) {
    char state[64];

    if (read_trimmed_text_file(NETSERVICE_FLAG_PATH, state, sizeof(state)) < 0) {
        return true;
    }
    return strcmp(state, "ncm") != 0;
}

static bool netservice_parse_pid_dir(const char *name, pid_t *out) {
    char *end = NULL;
    long value;

    if (name == NULL || *name == '\0' || out == NULL) {
        return false;
    }
    value = strtol(name, &end, 10);
    if (end == name || *end != '\0' || value <= 1 || value > INT_MAX) {
        return false;
    }
    *out = (pid_t)value;
    return true;
}

static bool netservice_read_cmdline(pid_t pid, char *out, size_t out_size) {
    char path[PATH_MAX];
    ssize_t rd;
    int fd;

    if (out == NULL || out_size == 0) {
        return false;
    }
    out[0] = '\0';
    if (snprintf(path, sizeof(path), "/proc/%ld/cmdline", (long)pid) >= (int)sizeof(path)) {
        return false;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return false;
    }
    rd = read(fd, out, out_size - 1);
    close(fd);
    if (rd <= 0) {
        out[0] = '\0';
        return false;
    }
    for (ssize_t index = 0; index < rd; ++index) {
        if (out[index] == '\0') {
            out[index] = ' ';
        }
    }
    out[rd] = '\0';
    return true;
}

static pid_t netservice_find_existing_tcpctl_listener(void) {
    DIR *dir;
    struct dirent *entry;
    char cmdline[512];
    pid_t pid;

    dir = opendir("/proc");
    if (dir == NULL) {
        return -1;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (!netservice_parse_pid_dir(entry->d_name, &pid) || pid == getpid()) {
            continue;
        }
        if (!netservice_read_cmdline(pid, cmdline, sizeof(cmdline))) {
            continue;
        }
        if (strstr(cmdline, NETSERVICE_TCPCTL_HELPER) != NULL &&
            strstr(cmdline, " listen ") != NULL &&
            strstr(cmdline, NETSERVICE_TCP_BIND_ADDR) != NULL &&
            strstr(cmdline, NETSERVICE_TCP_PORT) != NULL &&
            strstr(cmdline, NETSERVICE_TCP_TOKEN_PATH) != NULL) {
            closedir(dir);
            return pid;
        }
    }
    closedir(dir);
    return -1;
}

int a90_netservice_set_enabled(bool enabled) {
    int fd;

    if (!enabled) {
        if (unlink(NETSERVICE_FLAG_PATH) < 0 && errno != ENOENT) {
            int saved_errno = errno;
            a90_console_printf("netservice: unlink %s: %s\r\n",
                    NETSERVICE_FLAG_PATH, strerror(saved_errno));
            return -saved_errno;
        }
        a90_logf("netservice", "disabled flag removed");
        return 0;
    }

    fd = open(NETSERVICE_FLAG_PATH,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        int saved_errno = errno;
        a90_console_printf("netservice: open %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }
    if (write_all_checked(fd, "enabled\n", 8) < 0) {
        int saved_errno = errno;
        close(fd);
        a90_console_printf("netservice: write %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }
    if (close(fd) < 0) {
        int saved_errno = errno;
        a90_console_printf("netservice: close %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }

    a90_logf("netservice", "enabled flag written");
    return 0;
}

static int netservice_spawn_tcpctl(void) {
    char token[64];
    char *const argv[] = {
        NETSERVICE_TCPCTL_HELPER,
        "listen",
        NETSERVICE_TCP_BIND_ADDR,
        NETSERVICE_TCP_PORT,
        NETSERVICE_TCP_IDLE_SECONDS,
        NETSERVICE_TCP_MAX_CLIENTS,
        NETSERVICE_TCP_TOKEN_PATH,
        NULL
    };
    static char *const envp[] = {
        "PATH=/cache/bin:/cache:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        NULL
    };
    struct a90_run_config config = {
        .tag = "tcpctl",
        .argv = argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = NETSERVICE_LOG_PATH,
        .setsid = true,
        .ignore_hup_pipe = true,
        .stop_timeout_ms = 2000,
    };
    pid_t pid;
    int status = 0;
    int rc;

    a90_netservice_reap();
    if (a90_service_pid(A90_SERVICE_TCPCTL) > 0) {
        a90_logf("netservice", "tcpctl already running pid=%ld",
                    (long)a90_service_pid(A90_SERVICE_TCPCTL));
        return 0;
    }
    pid = netservice_find_existing_tcpctl_listener();
    if (pid > 0) {
        a90_service_set_pid(A90_SERVICE_TCPCTL, pid);
        a90_timeline_record(0, 0, "tcpctl-adopt", "pid=%ld", (long)pid);
        a90_logf("netservice", "adopt existing tcpctl pid=%ld bind=%s port=%s",
                    (long)pid, NETSERVICE_TCP_BIND_ADDR, NETSERVICE_TCP_PORT);
        return 0;
    }

    rc = a90_netservice_token(token, sizeof(token));
    if (rc < 0) {
        a90_logf("netservice", "tcpctl token unavailable rc=%d", rc);
        return rc;
    }

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        return rc;
    }
    a90_service_set_pid(A90_SERVICE_TCPCTL, pid);

    usleep(200000);
    if (a90_service_reap(A90_SERVICE_TCPCTL, &status) > 0) {
        a90_logf("netservice", "tcpctl exited immediately pid=%ld", (long)pid);
        return -EIO;
    }

    a90_logf("netservice", "tcpctl started pid=%ld bind=%s port=%s auth=required",
                (long)pid, NETSERVICE_TCP_BIND_ADDR, NETSERVICE_TCP_PORT);
    return 0;
}

int a90_netservice_start(void) {
    char *const usbnet_argv[] = {
        NETSERVICE_USB_HELPER,
        "ncm",
        NULL
    };
    char *const ifconfig_argv[] = {
        NETSERVICE_TOYBOX,
        "ifconfig",
        NETSERVICE_IFNAME,
        NETSERVICE_DEVICE_IP,
        "netmask",
        NETSERVICE_NETMASK,
        "up",
        NULL
    };
    int rc;
    bool ncm_present;

    a90_logf("netservice", "start requested");
    if (access(NETSERVICE_USB_HELPER, X_OK) < 0 ||
        access(NETSERVICE_TOYBOX, X_OK) < 0 ||
        (netservice_tcpctl_requested() && access(NETSERVICE_TCPCTL_HELPER, X_OK) < 0)) {
        int saved_errno = errno;
        a90_logf("netservice", "required helper missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        return -ENOENT;
    }

    ncm_present = access("/sys/class/net/" NETSERVICE_IFNAME, F_OK) == 0;
    if (ncm_present) {
        a90_logf("netservice", "ncm already present; skip usb gadget reconfigure");
    } else {
        rc = netservice_run_wait(usbnet_argv, "a90_usbnet ncm", 15000);
        a90_console_reattach("netservice-ncm", false);
        if (rc < 0) {
            return rc;
        }
    }

    rc = netservice_wait_for_ifname(NETSERVICE_IFNAME, 5000);
    if (rc < 0) {
        return rc;
    }

    rc = netservice_run_wait(ifconfig_argv, "ifconfig ncm0", 5000);
    if (rc < 0) {
        return rc;
    }

    if (netservice_tcpctl_requested()) {
        rc = netservice_spawn_tcpctl();
        if (rc < 0) {
            return rc;
        }
    } else {
        a90_logf("netservice", "tcpctl skipped by ncm-only flag");
    }

    a90_timeline_record(0, 0, "netservice", "ncm=%s tcp=%s",
                    NETSERVICE_IFNAME,
                    netservice_tcpctl_requested() ? NETSERVICE_TCP_PORT : "disabled");
    a90_logf("netservice", "ready if=%s ip=%s port=%s",
                NETSERVICE_IFNAME,
                NETSERVICE_DEVICE_IP,
                netservice_tcpctl_requested() ? NETSERVICE_TCP_PORT : "disabled");
    return 0;
}

int a90_netservice_stop(void) {
    char *const usbnet_argv[] = {
        NETSERVICE_USB_HELPER,
        "off",
        NULL
    };
    int rc = 0;

    a90_logf("netservice", "stop requested");
    a90_netservice_reap();
    if (a90_service_pid(A90_SERVICE_TCPCTL) > 0) {
        pid_t pid = a90_service_pid(A90_SERVICE_TCPCTL);

        (void)a90_service_stop(A90_SERVICE_TCPCTL, 2000);
        a90_logf("netservice", "tcpctl stopped pid=%ld", (long)pid);
    }

    if (access(NETSERVICE_USB_HELPER, X_OK) == 0) {
        rc = netservice_run_wait(usbnet_argv, "a90_usbnet off", 15000);
        a90_console_reattach("netservice-off", false);
    }

    return rc;
}

int a90_netservice_status(struct a90_netservice_status *out) {
    if (out == NULL) {
        return -EINVAL;
    }

    a90_netservice_reap();
    memset(out, 0, sizeof(*out));
    out->enabled = a90_netservice_enabled();
    out->usbnet_helper = access(NETSERVICE_USB_HELPER, X_OK) == 0;
    out->tcpctl_helper = access(NETSERVICE_TCPCTL_HELPER, X_OK) == 0;
    out->toybox_helper = access(NETSERVICE_TOYBOX, X_OK) == 0;
    out->ncm_present = access("/sys/class/net/" NETSERVICE_IFNAME, F_OK) == 0;
    out->tcpctl_pid = a90_service_pid(A90_SERVICE_TCPCTL);
    out->tcpctl_running = out->tcpctl_pid > 0;
    out->flag_path = NETSERVICE_FLAG_PATH;
    out->log_path = NETSERVICE_LOG_PATH;
    out->ifname = NETSERVICE_IFNAME;
    out->device_ip = NETSERVICE_DEVICE_IP;
    out->netmask = NETSERVICE_NETMASK;
    out->tcp_port = NETSERVICE_TCP_PORT;
    out->tcp_idle_seconds = NETSERVICE_TCP_IDLE_SECONDS;
    out->tcp_max_clients = NETSERVICE_TCP_MAX_CLIENTS;
    out->tcp_bind_addr = NETSERVICE_TCP_BIND_ADDR;
    out->tcp_token_path = NETSERVICE_TCP_TOKEN_PATH;
    out->tcp_token_present = access(NETSERVICE_TCP_TOKEN_PATH, R_OK) == 0;
    return 0;
}
