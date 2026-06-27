#include "a90_wifi.h"

#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/genetlink.h>
#include <linux/if_addr.h>
#include <linux/if_link.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <linux/rtnetlink.h>
#include <net/if.h>
#include <poll.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <stddef.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#include "a90_console.h"
#include "a90_log.h"
#include "a90_run.h"
#include "a90_util.h"
#include "a90_wificfg.h"
#include "a90_wififeas.h"

#ifndef SOCK_CLOEXEC
#define SOCK_CLOEXEC 02000000
#endif

#ifndef NLA_ALIGNTO
#define NLA_ALIGNTO 4
#endif

#ifndef NLA_ALIGN
#define NLA_ALIGN(len) (((len) + NLA_ALIGNTO - 1) & ~(NLA_ALIGNTO - 1))
#endif

#ifndef NLA_HDRLEN
#define NLA_HDRLEN ((int)NLA_ALIGN(sizeof(struct nlattr)))
#endif

#ifndef NLA_TYPE_MASK
#define NLA_TYPE_MASK ~(NLA_F_NESTED | NLA_F_NET_BYTEORDER)
#endif

#ifndef O_DIRECTORY
#define O_DIRECTORY 0
#endif

#define A90_WIFI_IFACE "wlan0"
#define A90_WIFI_RUNTIME_SUMMARY "/cache/native-init-wifi-runtime.summary"
#define A90_WIFI_RUNTIME_INPUT "/cache/native-init-wifi-runtime-input.summary"
#define A90_WIFI_STANDALONE_SUPPLICANT "/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh"
#define A90_WIFI_RUNTIME_ROOT "/cache/a90-wifi"
#define A90_WIFI_CTRL_DIR "/cache/a90-wifi/sockets"
#define A90_WIFI_CTRL_SOCKET "/cache/a90-wifi/sockets/wlan0"
#define A90_WIFI_SUPPLICANT_LOG "/cache/a90-wifi/wpa_supplicant-connect.log"
#define A90_WIFI_UDHCPC_SCRIPT "/cache/a90-wifi/udhcpc-wlan0.script"
#define A90_WIFI_UDHCPC_LOG "/cache/a90-wifi/udhcpc-wlan0.log"
#define A90_WIFI_UDHCPC_PID "/cache/a90-wifi/udhcpc-wlan0.pid"
#define A90_WIFI_RESOLV_CONF "/cache/a90-wifi/resolv.conf"
#define A90_WIFI_AUTOCONNECT_LOG "/cache/a90-wifi/autoconnect.log"
#define A90_WIFI_AUTOCONNECT_RESULT "/cache/a90-wifi/autoconnect.result"
#define A90_WIFI_AUTOCONNECT_PID "/cache/a90-wifi/autoconnect.pid"
#define A90_WIFI_SCAN_RECV_SIZE 65536
#define A90_WIFI_SCAN_VERSION "a90-native-wifi-scan-v1"
#define A90_WIFI_CONNECT_VERSION "a90-native-wifi-connect-v1"
#define A90_WIFI_DHCP_VERSION "a90-native-wifi-dhcp-v1"
#define A90_WIFI_PING_VERSION "a90-native-wifi-ping-v1"
#define A90_WIFI_UID 1010
#define A90_WIFI_GID 1010
#define A90_WIFI_CONNECT_WLAN0_WAIT_MS 180000
#define A90_WIFI_CONNECT_CTRL_WAIT_MS 15000
#define A90_WIFI_CONNECT_CARRIER_WAIT_MS 35000
#define A90_WIFI_SUPPLICANT_TERMINATE_WAIT_MS 3000
#define A90_WIFI_SUPPLICANT_KILL_WAIT_MS 1500
#define A90_WIFI_DHCP_TIMEOUT_MS 30000
#define A90_WIFI_PING_COUNT 3
#define A90_WIFI_PING_TIMEOUT_SEC 2
#define A90_WIFI_PING_TIMEOUT_MS 10000
#define A90_WIFI_PING_GATEWAY_LOG "/cache/a90-wifi/ping-gateway.log"
#define A90_WIFI_PING_INTERNET_LOG "/cache/a90-wifi/ping-internet.log"
#define A90_WIFI_PING_INTERNET_TARGET "1.1.1.1"
#define A90_WIFI_SOFTAP_VERSION "a90-native-wifi-softap-v1"
#define A90_WIFI_SOFTAP_ROOT "/cache/a90-softap"

static int wifi_open_dir_no_follow(const char *path) {
    return open(path, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
}

static int wifi_prepare_dir_owned(const char *path, mode_t mode, uid_t uid, gid_t gid) {
    int fd;
    int rc = 0;

    if (ensure_dir(path, mode) < 0) {
        return negative_errno_or(EIO);
    }
    fd = wifi_open_dir_no_follow(path);
    if (fd < 0) {
        return -errno;
    }
    if (fchown(fd, uid, gid) < 0) {
        rc = -errno;
    }
    if (rc == 0 && fchmod(fd, mode) < 0) {
        rc = -errno;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int wifi_verify_root_exec_dir(const char *path) {
    struct stat st;
    int fd;
    int rc = 0;

    fd = wifi_open_dir_no_follow(path);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &st) < 0) {
        rc = -errno;
    } else if (!S_ISDIR(st.st_mode) ||
               st.st_uid != 0 ||
               (st.st_mode & (S_IWGRP | S_IWOTH)) != 0) {
        rc = -EACCES;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int wifi_verify_root_exec_parents(const char *path) {
    char current[256];
    size_t root_len;
    size_t index;
    int rc;

    if (path == NULL) {
        return -EINVAL;
    }
    root_len = strlen(A90_WIFI_RUNTIME_ROOT);
    if (strncmp(path, A90_WIFI_RUNTIME_ROOT, root_len) != 0 ||
        path[root_len] != '/') {
        return -EINVAL;
    }
    if (root_len >= sizeof(current)) {
        return -ENAMETOOLONG;
    }
    memcpy(current, A90_WIFI_RUNTIME_ROOT, root_len);
    current[root_len] = '\0';
    rc = wifi_verify_root_exec_dir(current);
    if (rc < 0) {
        return rc;
    }
    for (index = root_len + 1; path[index] != '\0'; ++index) {
        if (path[index] != '/') {
            continue;
        }
        if (index >= sizeof(current)) {
            return -ENAMETOOLONG;
        }
        memcpy(current, path, index);
        current[index] = '\0';
        rc = wifi_verify_root_exec_dir(current);
        if (rc < 0) {
            return rc;
        }
    }
    return 0;
}

static int wifi_verify_root_exec_file(const char *path, bool require_exec) {
    struct stat st;
    int fd;
    int rc;

    rc = wifi_verify_root_exec_parents(path);
    if (rc < 0) {
        return rc;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rc = 0;
    if (fstat(fd, &st) < 0) {
        rc = -errno;
    } else if (!S_ISREG(st.st_mode) ||
               st.st_uid != 0 ||
               (st.st_mode & (S_IWGRP | S_IWOTH)) != 0 ||
               (require_exec && (st.st_mode & S_IXUSR) == 0)) {
        rc = -EACCES;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int wifi_write_text_file(const char *path, const char *text, mode_t mode) {
    int fd;
    int rc;

    if (path == NULL || text == NULL) {
        return -EINVAL;
    }
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, mode);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, text, strlen(text));
    if (rc == 0 && fchown(fd, 0, 0) < 0) {
        rc = -errno;
    }
    if (rc == 0 && fchmod(fd, mode) < 0) {
        rc = -errno;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static void wifi_append_text_file(const char *path, const char *format, ...) {
    char buffer[512];
    va_list ap;
    int len;
    int fd;

    if (path == NULL || format == NULL) {
        return;
    }

    va_start(ap, format);
    len = vsnprintf(buffer, sizeof(buffer), format, ap);
    va_end(ap);
    if (len < 0) {
        return;
    }
    if ((size_t)len >= sizeof(buffer)) {
        len = (int)sizeof(buffer) - 1;
        buffer[len] = '\0';
    }

    (void)wifi_prepare_dir_owned(A90_WIFI_RUNTIME_ROOT, 0755, 0, 0);
    fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0644);
    if (fd < 0) {
        return;
    }
    (void)write_all_checked(fd, buffer, (size_t)len);
    (void)close(fd);
}

static void wifi_reset_autoconnect_log(const char *profile, bool boot_background) {
    char text[256];
    int len;

    len = snprintf(text,
                   sizeof(text),
                   "version=a90-native-wifi-autoconnect-log-v1\n"
                   "profile=%s\n"
                   "boot_background=%d\n"
                   "secret_values_logged=0\n",
                   profile != NULL && profile[0] != '\0' ? profile : "default",
                   boot_background ? 1 : 0);
    if (len < 0 || (size_t)len >= sizeof(text)) {
        return;
    }
    (void)wifi_write_text_file(A90_WIFI_AUTOCONNECT_LOG, text, 0600);
}

static void wifi_read_attr(const char *path, const char *name, char *out, size_t out_size) {
    char attr_path[256];

    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (snprintf(attr_path, sizeof(attr_path), "%s/%s", path, name) >= (int)sizeof(attr_path) ||
        read_trimmed_text_file(attr_path, out, out_size) < 0) {
        snprintf(out, out_size, "-");
    }
}

static int wifi_path_kind(const char *path, bool executable, char *out, size_t out_size) {
    struct stat path_stat;

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    out[0] = '\0';
    if (lstat(path, &path_stat) < 0) {
        snprintf(out, out_size, "missing");
        return -errno;
    }
    if (S_ISLNK(path_stat.st_mode)) {
        snprintf(out, out_size, "symlink");
    } else if (S_ISDIR(path_stat.st_mode)) {
        snprintf(out, out_size, "dir");
    } else if (S_ISREG(path_stat.st_mode)) {
        snprintf(out, out_size, "file");
    } else if (S_ISSOCK(path_stat.st_mode)) {
        snprintf(out, out_size, "socket");
    } else {
        snprintf(out, out_size, "other");
    }
    if (executable && access(path, X_OK) < 0) {
        return -errno;
    }
    return 0;
}

static int wifi_count_processes_with_token(const char *token) {
    int count = 0;
    char proc_path[320];
    char cmdline[512];
    int proc_dir_fd;
    DIR *proc_dir;
    struct dirent *entry;

    proc_dir = opendir("/proc");
    if (proc_dir == NULL) {
        return -errno;
    }
    proc_dir_fd = dirfd(proc_dir);
    while ((entry = readdir(proc_dir)) != NULL) {
        char *cursor = entry->d_name;
        int fd;
        ssize_t bytes_read;

        if (*cursor == '\0') {
            continue;
        }
        while (*cursor != '\0') {
            if (*cursor < '0' || *cursor > '9') {
                break;
            }
            ++cursor;
        }
        if (*cursor != '\0') {
            continue;
        }
        snprintf(proc_path, sizeof(proc_path), "%s/cmdline", entry->d_name);
        fd = openat(proc_dir_fd, proc_path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) {
            continue;
        }
        bytes_read = read(fd, cmdline, sizeof(cmdline) - 1);
        close(fd);
        if (bytes_read <= 0) {
            continue;
        }
        cmdline[bytes_read] = '\0';
        {
            size_t token_len = strlen(token);
            ssize_t offset;

            for (offset = 0; offset + (ssize_t)token_len <= bytes_read; ++offset) {
                if (memcmp(cmdline + offset, token, token_len) == 0) {
                    ++count;
                    break;
                }
            }
        }
    }
    closedir(proc_dir);
    return count;
}

static int wifi_signal_processes_with_token(const char *token, int signal_number) {
    int signaled = 0;
    int first_errno = 0;
    char proc_path[320];
    char cmdline[512];
    int proc_dir_fd;
    DIR *proc_dir;
    struct dirent *entry;

    proc_dir = opendir("/proc");
    if (proc_dir == NULL) {
        return -errno;
    }
    proc_dir_fd = dirfd(proc_dir);
    while ((entry = readdir(proc_dir)) != NULL) {
        char *cursor = entry->d_name;
        char *endptr;
        long pid_value;
        int fd;
        ssize_t bytes_read;
        bool matched = false;

        if (*cursor == '\0') {
            continue;
        }
        while (*cursor != '\0') {
            if (*cursor < '0' || *cursor > '9') {
                break;
            }
            ++cursor;
        }
        if (*cursor != '\0') {
            continue;
        }
        snprintf(proc_path, sizeof(proc_path), "%s/cmdline", entry->d_name);
        fd = openat(proc_dir_fd, proc_path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) {
            continue;
        }
        bytes_read = read(fd, cmdline, sizeof(cmdline) - 1);
        close(fd);
        if (bytes_read <= 0) {
            continue;
        }
        cmdline[bytes_read] = '\0';
        {
            size_t token_len = strlen(token);
            ssize_t offset;

            for (offset = 0; offset + (ssize_t)token_len <= bytes_read; ++offset) {
                if (memcmp(cmdline + offset, token, token_len) == 0) {
                    matched = true;
                    break;
                }
            }
        }
        if (!matched) {
            continue;
        }
        errno = 0;
        pid_value = strtol(entry->d_name, &endptr, 10);
        if (errno != 0 || endptr == entry->d_name || *endptr != '\0' || pid_value <= 1) {
            continue;
        }
        if (kill((pid_t)pid_value, signal_number) == 0) {
            ++signaled;
        } else if (errno != ESRCH && first_errno == 0) {
            first_errno = errno;
        }
    }
    closedir(proc_dir);
    if (first_errno != 0) {
        return -first_errno;
    }
    return signaled;
}

static int wifi_wait_processes_gone(const char *token, int timeout_ms, int *elapsed_ms_out) {
    long started_ms = monotonic_millis();
    long deadline_ms = started_ms + timeout_ms;

    while (monotonic_millis() <= deadline_ms) {
        int count = wifi_count_processes_with_token(token);

        if (count <= 0) {
            if (elapsed_ms_out != NULL) {
                *elapsed_ms_out = (int)(monotonic_millis() - started_ms);
            }
            return count < 0 ? count : 0;
        }
        usleep(100000);
    }
    if (elapsed_ms_out != NULL) {
        *elapsed_ms_out = timeout_ms;
    }
    return -ETIMEDOUT;
}

static int wifi_ipv4_addr(const char *ifname, char *out, size_t out_size) {
    struct ifreq request;
    struct sockaddr_in *addr;
    int socket_fd;

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    snprintf(out, out_size, "-");
    socket_fd = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (socket_fd < 0) {
        return -errno;
    }
    memset(&request, 0, sizeof(request));
    snprintf(request.ifr_name, sizeof(request.ifr_name), "%s", ifname);
    if (ioctl(socket_fd, SIOCGIFADDR, &request) < 0) {
        int saved_errno = errno;

        close(socket_fd);
        return -saved_errno;
    }
    addr = (struct sockaddr_in *)&request.ifr_addr;
    if (inet_ntop(AF_INET, &addr->sin_addr, out, (socklen_t)out_size) == NULL) {
        int saved_errno = errno;

        close(socket_fd);
        return -saved_errno;
    }
    close(socket_fd);
    return 0;
}

static bool wifi_iface_present(void) {
    char iface_path[128];

    snprintf(iface_path, sizeof(iface_path), "/sys/class/net/%s", A90_WIFI_IFACE);
    return access(iface_path, F_OK) == 0;
}

static int wifi_wait_wlan0(int timeout_ms, int *elapsed_ms_out) {
    long started_ms = monotonic_millis();
    long deadline_ms = started_ms + timeout_ms;

    while (monotonic_millis() <= deadline_ms) {
        if (wifi_iface_present()) {
            if (elapsed_ms_out != NULL) {
                *elapsed_ms_out = (int)(monotonic_millis() - started_ms);
            }
            return 0;
        }
        usleep(200000);
    }
    if (elapsed_ms_out != NULL) {
        *elapsed_ms_out = timeout_ms;
    }
    return -ETIMEDOUT;
}

static const char *wifi_ctrl_reply_category(const char *reply) {
    if (reply == NULL || reply[0] == '\0') {
        return "empty";
    }
    if (strncmp(reply, "OK", 2) == 0) {
        return "ok";
    }
    if (strncmp(reply, "FAIL", 4) == 0) {
        return "fail";
    }
    if (strncmp(reply, "PONG", 4) == 0) {
        return "pong";
    }
    if (strncmp(reply, "UNKNOWN", 7) == 0) {
        return "unknown";
    }
    return "other";
}

static int wifi_ctrl_bind_local_abstract(int socket_fd) {
    struct sockaddr_un local;
    char name[80];
    size_t name_len;

    if (snprintf(name,
                 sizeof(name),
                 "a90-wifi-%ld-%ld",
                 (long)getpid(),
                 monotonic_millis()) >= (int)sizeof(name)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    name_len = strlen(name);
    memset(&local, 0, sizeof(local));
    local.sun_family = AF_UNIX;
    local.sun_path[0] = '\0';
    memcpy(local.sun_path + 1, name, name_len);
    return bind(socket_fd,
                (const struct sockaddr *)&local,
                (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 1 + name_len));
}

static int wifi_ctrl_connect_remote(int socket_fd, const char *remote_path) {
    struct sockaddr_un remote;
    size_t remote_len = strlen(remote_path);

    if (remote_len == 0 || remote_len >= sizeof(remote.sun_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    memset(&remote, 0, sizeof(remote));
    remote.sun_family = AF_UNIX;
    memcpy(remote.sun_path, remote_path, remote_len + 1);
    return connect(socket_fd,
                   (const struct sockaddr *)&remote,
                   (socklen_t)(offsetof(struct sockaddr_un, sun_path) + remote_len + 1));
}

static int wifi_ctrl_request(const char *command,
                             char *category,
                             size_t category_size,
                             long *reply_len_out,
                             int *saved_errno_out,
                             char *reply_out,
                             size_t reply_out_size) {
    char reply[4096];
    struct pollfd poll_fd;
    ssize_t received;
    size_t command_len;
    int socket_fd;

    if (category != NULL && category_size > 0) {
        snprintf(category, category_size, "error");
    }
    if (reply_len_out != NULL) {
        *reply_len_out = 0;
    }
    if (saved_errno_out != NULL) {
        *saved_errno_out = 0;
    }
    if (reply_out != NULL && reply_out_size > 0) {
        reply_out[0] = '\0';
    }
    if (command == NULL || command[0] == '\0') {
        if (saved_errno_out != NULL) {
            *saved_errno_out = EINVAL;
        }
        return -EINVAL;
    }

    socket_fd = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (socket_fd < 0) {
        int saved_errno = errno;

        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }
    if (wifi_ctrl_bind_local_abstract(socket_fd) < 0 ||
        wifi_ctrl_connect_remote(socket_fd, A90_WIFI_CTRL_SOCKET) < 0) {
        int saved_errno = errno;

        close(socket_fd);
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }

    command_len = strlen(command);
    if (send(socket_fd, command, command_len, 0) != (ssize_t)command_len) {
        int saved_errno = errno == 0 ? EIO : errno;

        close(socket_fd);
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }

    memset(&poll_fd, 0, sizeof(poll_fd));
    poll_fd.fd = socket_fd;
    poll_fd.events = POLLIN;
    if (poll(&poll_fd, 1, 2500) <= 0) {
        int saved_errno = errno == 0 ? ETIMEDOUT : errno;

        close(socket_fd);
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }
    received = recv(socket_fd, reply, sizeof(reply) - 1, 0);
    if (received < 0) {
        int saved_errno = errno;

        close(socket_fd);
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }
    reply[received] = '\0';
    while (received > 0 && (reply[received - 1] == '\n' || reply[received - 1] == '\r')) {
        reply[received - 1] = '\0';
        --received;
    }
    if (category != NULL && category_size > 0) {
        snprintf(category, category_size, "%s", wifi_ctrl_reply_category(reply));
    }
    if (reply_len_out != NULL) {
        *reply_len_out = (long)received;
    }
    if (reply_out != NULL && reply_out_size > 0) {
        snprintf(reply_out, reply_out_size, "%s", reply);
    }
    close(socket_fd);
    return 0;
}

static bool wifi_process_alive(pid_t pid) {
    return pid > 0 && (kill(pid, 0) == 0 || errno == EPERM);
}

static int wifi_prepare_runtime_dirs(void) {
    int rc;

    rc = wifi_prepare_dir_owned(A90_WIFI_RUNTIME_ROOT, 0755, 0, 0);
    if (rc < 0) {
        return rc;
    }
    return wifi_prepare_dir_owned(A90_WIFI_CTRL_DIR, 0770, A90_WIFI_UID, A90_WIFI_GID);
}

static int wifi_start_supplicant(pid_t *pid_out) {
    char *const argv[] = {
        (char *)A90_WIFI_STANDALONE_SUPPLICANT,
        (char *)"-dd",
        (char *)"-i",
        (char *)A90_WIFI_IFACE,
        (char *)"-D",
        (char *)"nl80211",
        (char *)"-c",
        (char *)A90_WIFICFG_SUPPLICANT_CONF,
        (char *)"-O",
        (char *)A90_WIFI_CTRL_DIR,
        (char *)"-t",
        NULL,
    };
    struct a90_run_config config = {
        .tag = "wifi-supplicant",
        .argv = argv,
        .envp = NULL,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_WIFI_SUPPLICANT_LOG,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = 0,
        .stop_timeout_ms = 3000,
    };
    int verify_rc;

    verify_rc = wifi_verify_root_exec_file(A90_WIFI_STANDALONE_SUPPLICANT, true);
    if (verify_rc < 0) {
        return verify_rc;
    }
    return a90_run_spawn(&config, pid_out);
}

static int wifi_wait_ctrl_ready(pid_t pid,
                                bool spawned,
                                int timeout_ms,
                                int *elapsed_ms_out,
                                char *category,
                                size_t category_size,
                                int *ctrl_errno_out) {
    long started_ms = monotonic_millis();
    long deadline_ms = started_ms + timeout_ms;

    if (category != NULL && category_size > 0) {
        snprintf(category, category_size, "error");
    }
    if (ctrl_errno_out != NULL) {
        *ctrl_errno_out = 0;
    }
    while (monotonic_millis() <= deadline_ms) {
        long reply_len = 0;
        int saved_errno = 0;
        int rc;

        if (spawned && !wifi_process_alive(pid)) {
            if (elapsed_ms_out != NULL) {
                *elapsed_ms_out = (int)(monotonic_millis() - started_ms);
            }
            if (ctrl_errno_out != NULL) {
                *ctrl_errno_out = ESRCH;
            }
            return -ESRCH;
        }
        if (access(A90_WIFI_CTRL_SOCKET, F_OK) == 0) {
            rc = wifi_ctrl_request("PING",
                                   category,
                                   category_size,
                                   &reply_len,
                                   &saved_errno,
                                   NULL,
                                   0);
            (void)reply_len;
            if (ctrl_errno_out != NULL) {
                *ctrl_errno_out = saved_errno;
            }
            if (rc == 0 && category != NULL && strcmp(category, "pong") == 0) {
                if (elapsed_ms_out != NULL) {
                    *elapsed_ms_out = (int)(monotonic_millis() - started_ms);
                }
                return 0;
            }
        }
        usleep(250000);
    }
    if (elapsed_ms_out != NULL) {
        *elapsed_ms_out = timeout_ms;
    }
    if (ctrl_errno_out != NULL && *ctrl_errno_out == 0) {
        *ctrl_errno_out = ETIMEDOUT;
    }
    return -ETIMEDOUT;
}

static bool wifi_status_field_allowed(const char *key) {
    return strcmp(key, "wpa_state") == 0 ||
           strcmp(key, "key_mgmt") == 0 ||
           strcmp(key, "pairwise_cipher") == 0 ||
           strcmp(key, "group_cipher") == 0 ||
           strcmp(key, "mode") == 0 ||
           strcmp(key, "freq") == 0 ||
           strcmp(key, "id") == 0;
}

static char wifi_safe_metric_char(char value);

static char wifi_status_value_char(char value) {
    return wifi_safe_metric_char(value);
}

static void wifi_print_status_fields(const char *label, const char *reply) {
    const char *cursor = reply;

    if (label == NULL || reply == NULL || reply[0] == '\0') {
        return;
    }
    while (*cursor != '\0') {
        char line[256];
        char value[128];
        const char *line_end = strchr(cursor, '\n');
        size_t line_len = line_end != NULL ? (size_t)(line_end - cursor) : strlen(cursor);
        char *separator;
        size_t index;

        if (line_len >= sizeof(line)) {
            line_len = sizeof(line) - 1;
        }
        memcpy(line, cursor, line_len);
        line[line_len] = '\0';
        separator = strchr(line, '=');
        if (separator != NULL) {
            *separator = '\0';
            if (wifi_status_field_allowed(line)) {
                const char *raw_value = separator + 1;
                size_t value_len = strlen(raw_value);

                if (value_len >= sizeof(value)) {
                    value_len = sizeof(value) - 1;
                }
                for (index = 0; index < value_len; ++index) {
                    value[index] = wifi_status_value_char(raw_value[index]);
                }
                value[value_len] = '\0';
                a90_console_printf("%s.field.%s=%s\r\n", label, line, value);
            }
        }
        if (line_end == NULL) {
            break;
        }
        cursor = line_end + 1;
    }
}

static int wifi_print_ctrl_result(const char *label, const char *command) {
    char category[32];
    char reply[4096];
    long reply_len = 0;
    int saved_errno = 0;
    int rc;

    rc = wifi_ctrl_request(command,
                           category,
                           sizeof(category),
                           &reply_len,
                           &saved_errno,
                           reply,
                           sizeof(reply));
    a90_console_printf("%s.rc=%d\r\n", label, rc);
    a90_console_printf("%s.errno=%d\r\n", label, saved_errno);
    a90_console_printf("%s.reply_category=%s\r\n", label, rc == 0 ? category : "error");
    a90_console_printf("%s.reply_len=%ld\r\n", label, rc == 0 ? reply_len : 0L);
    if (rc == 0 && strcmp(command, "STATUS") == 0) {
        wifi_print_status_fields(label, reply);
    }
    return rc;
}

static bool wifi_carrier_up(void) {
    char carrier[32];

    if (read_trimmed_text_file("/sys/class/net/" A90_WIFI_IFACE "/carrier",
                               carrier,
                               sizeof(carrier)) < 0) {
        return false;
    }
    return strcmp(carrier, "1") == 0;
}

static int wifi_count_resolv_nameservers(void) {
    char text[1024];
    char *cursor;
    int count = 0;

    if (read_text_file(A90_WIFI_RESOLV_CONF, text, sizeof(text)) < 0) {
        return -errno;
    }
    cursor = text;
    while (cursor != NULL && *cursor != '\0') {
        char *line_end = strchr(cursor, '\n');

        if (line_end != NULL) {
            *line_end = '\0';
        }
        if (strncmp(cursor, "nameserver ", 11) == 0) {
            ++count;
        }
        cursor = line_end == NULL ? NULL : line_end + 1;
    }
    return count;
}

static bool wifi_default_route_present(void) {
    char text[4096];
    char *cursor;
    bool first = true;

    if (read_text_file("/proc/net/route", text, sizeof(text)) < 0) {
        return false;
    }
    cursor = text;
    while (cursor != NULL && *cursor != '\0') {
        char *line_end = strchr(cursor, '\n');
        char iface[32] = "";
        char destination[32] = "";
        char gateway[32] = "";

        if (line_end != NULL) {
            *line_end = '\0';
        }
        if (first) {
            first = false;
            cursor = line_end == NULL ? NULL : line_end + 1;
            continue;
        }
        if (sscanf(cursor, "%31s %31s %31s", iface, destination, gateway) == 3 &&
            strcmp(iface, A90_WIFI_IFACE) == 0 &&
            strcmp(destination, "00000000") == 0 &&
            strcmp(gateway, "00000000") != 0) {
            return true;
        }
        cursor = line_end == NULL ? NULL : line_end + 1;
    }
    return false;
}

static int wifi_default_gateway_ipv4(char *out, size_t out_size) {
    char text[4096];
    char *cursor;
    bool first = true;

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    snprintf(out, out_size, "-");
    if (read_text_file("/proc/net/route", text, sizeof(text)) < 0) {
        return -ENOENT;
    }
    cursor = text;
    while (cursor != NULL && *cursor != '\0') {
        char *line_end = strchr(cursor, '\n');
        char iface[32] = "";
        char destination[32] = "";
        char gateway[32] = "";
        unsigned long gateway_value;
        struct in_addr address;

        if (line_end != NULL) {
            *line_end = '\0';
        }
        if (first) {
            first = false;
            cursor = line_end == NULL ? NULL : line_end + 1;
            continue;
        }
        if (sscanf(cursor, "%31s %31s %31s", iface, destination, gateway) == 3 &&
            strcmp(iface, A90_WIFI_IFACE) == 0 &&
            strcmp(destination, "00000000") == 0 &&
            strcmp(gateway, "00000000") != 0) {
            errno = 0;
            gateway_value = strtoul(gateway, NULL, 16);
            if (errno != 0) {
                return -errno;
            }
            address.s_addr = (in_addr_t)gateway_value;
            if (inet_ntop(AF_INET, &address, out, (socklen_t)out_size) == NULL) {
                return -errno;
            }
            return 0;
        }
        cursor = line_end == NULL ? NULL : line_end + 1;
    }
    return -ENOENT;
}

static int wifi_run_wait(char *const argv[],
                         const char *tag,
                         const char *log_path,
                         int timeout_ms,
                         struct a90_run_result *result) {
    struct a90_run_config config = {
        .tag = tag,
        .argv = argv,
        .envp = NULL,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = log_path,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = timeout_ms,
        .stop_timeout_ms = 3000,
    };
    pid_t pid = -1;
    int spawn_rc;

    spawn_rc = a90_run_spawn(&config, &pid);
    if (spawn_rc < 0) {
        if (result != NULL) {
            memset(result, 0, sizeof(*result));
            result->pid = -1;
            result->rc = spawn_rc;
            result->saved_errno = -spawn_rc;
        }
        return spawn_rc;
    }
    return a90_run_wait(pid, &config, result);
}

struct wifi_ctrl_link_info {
    int status_rc;
    int status_errno;
    int signal_rc;
    int signal_errno;
    char ssid_label[32];
    char wpa_state[32];
    char rssi_dbm[32];
    char linkspeed_mbps[32];
    char freq_mhz[32];
};

static char wifi_safe_metric_char(char value) {
    if ((value >= 'A' && value <= 'Z') ||
        (value >= 'a' && value <= 'z') ||
        (value >= '0' && value <= '9') ||
        value == '_' ||
        value == '-' ||
        value == '.' ||
        value == '/') {
        return value;
    }
    return '_';
}

static bool wifi_value_missing(const char *value) {
    return value == NULL || value[0] == '\0' || strcmp(value, "-") == 0;
}

static void wifi_mac_label(const char *mac, char *out, size_t out_size) {
    size_t mac_len;

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "%s", "none");
    if (wifi_value_missing(mac)) {
        return;
    }
    mac_len = strlen(mac);
    if (mac_len < 5) {
        snprintf(out, out_size, "%s", "redacted");
        return;
    }
    snprintf(out, out_size, "xx:%s", mac + mac_len - 5);
}

static void wifi_ipv4_label(const char *ipv4, char *out, size_t out_size) {
    struct in_addr address;
    uint32_t value;

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "%s", "none");
    if (wifi_value_missing(ipv4)) {
        return;
    }
    if (inet_pton(AF_INET, ipv4, &address) != 1) {
        return;
    }
    value = ntohl(address.s_addr);
    snprintf(out,
             out_size,
             "%u.%u.%u.x",
             (unsigned int)((value >> 24) & 0xffU),
             (unsigned int)((value >> 16) & 0xffU),
             (unsigned int)((value >> 8) & 0xffU));
}

static bool wifi_ctrl_reply_value(const char *reply, const char *key, char *out, size_t out_size) {
    const char *cursor = reply;
    size_t key_len;

    if (out == NULL || out_size == 0) {
        return false;
    }
    out[0] = '\0';
    if (reply == NULL || key == NULL || key[0] == '\0') {
        return false;
    }
    key_len = strlen(key);
    while (*cursor != '\0') {
        const char *line_end = strchr(cursor, '\n');
        size_t line_len = line_end != NULL ? (size_t)(line_end - cursor) : strlen(cursor);

        if (line_len > key_len &&
            strncmp(cursor, key, key_len) == 0 &&
            cursor[key_len] == '=') {
            const char *raw_value = cursor + key_len + 1;
            size_t value_len = line_len - key_len - 1;
            size_t index;

            if (value_len >= out_size) {
                value_len = out_size - 1;
            }
            for (index = 0; index < value_len; ++index) {
                out[index] = wifi_safe_metric_char(raw_value[index]);
            }
            out[value_len] = '\0';
            return true;
        }
        if (line_end == NULL) {
            break;
        }
        cursor = line_end + 1;
    }
    return false;
}

static bool wifi_ctrl_reply_has_key(const char *reply, const char *key) {
    char value[8];

    return wifi_ctrl_reply_value(reply, key, value, sizeof(value));
}

static void wifi_collect_ctrl_link_info(struct wifi_ctrl_link_info *info) {
    char category[32];
    char reply[4096];
    long reply_len = 0;

    if (info == NULL) {
        return;
    }
    memset(info, 0, sizeof(*info));
    info->status_rc = -ENOENT;
    info->signal_rc = -ENOENT;
    if (access(A90_WIFI_CTRL_SOCKET, F_OK) != 0) {
        info->status_errno = ENOENT;
        info->signal_errno = ENOENT;
        return;
    }

    info->status_rc = wifi_ctrl_request("STATUS",
                                        category,
                                        sizeof(category),
                                        &reply_len,
                                        &info->status_errno,
                                        reply,
                                        sizeof(reply));
    (void)reply_len;
    if (info->status_rc == 0) {
        (void)wifi_ctrl_reply_value(reply, "wpa_state", info->wpa_state, sizeof(info->wpa_state));
        (void)wifi_ctrl_reply_value(reply, "freq", info->freq_mhz, sizeof(info->freq_mhz));
        if (wifi_ctrl_reply_has_key(reply, "ssid") &&
            strcmp(info->wpa_state, "COMPLETED") == 0) {
            snprintf(info->ssid_label, sizeof(info->ssid_label), "%s", "connected");
        }
    }

    info->signal_rc = wifi_ctrl_request("SIGNAL_POLL",
                                        category,
                                        sizeof(category),
                                        &reply_len,
                                        &info->signal_errno,
                                        reply,
                                        sizeof(reply));
    (void)reply_len;
    if (info->signal_rc == 0) {
        (void)wifi_ctrl_reply_value(reply, "RSSI", info->rssi_dbm, sizeof(info->rssi_dbm));
        (void)wifi_ctrl_reply_value(reply, "LINKSPEED", info->linkspeed_mbps, sizeof(info->linkspeed_mbps));
        if (wifi_value_missing(info->freq_mhz)) {
            (void)wifi_ctrl_reply_value(reply, "FREQUENCY", info->freq_mhz, sizeof(info->freq_mhz));
        }
    }
}

static int wifi_write_runtime_summary(const char *decision) {
    struct wifi_ctrl_link_info link_info;
    char operstate[80];
    char carrier[32];
    char mac[80];
    char mac_label[32];
    char ipv4[64];
    char ip4_label[32];
    char text[1600];
    const char *ssid_label;
    int ipv4_rc;

    wifi_collect_ctrl_link_info(&link_info);
    wifi_read_attr("/sys/class/net/" A90_WIFI_IFACE, "operstate", operstate, sizeof(operstate));
    wifi_read_attr("/sys/class/net/" A90_WIFI_IFACE, "carrier", carrier, sizeof(carrier));
    wifi_read_attr("/sys/class/net/" A90_WIFI_IFACE, "address", mac, sizeof(mac));
    ipv4_rc = wifi_ipv4_addr(A90_WIFI_IFACE, ipv4, sizeof(ipv4));
    wifi_mac_label(mac, mac_label, sizeof(mac_label));
    wifi_ipv4_label(ipv4_rc == 0 ? ipv4 : "-", ip4_label, sizeof(ip4_label));
    ssid_label = link_info.ssid_label[0] != '\0' ?
        link_info.ssid_label : (wifi_carrier_up() ? "connected" : "");
    snprintf(text,
             sizeof(text),
             "wlan0_present=%d\n"
             "operstate=%s\n"
             "carrier=%s\n"
             "mac_label=%s\n"
             "mac=%s\n"
             "mac_raw_redacted=1\n"
             "ssid_label=%s\n"
             "wpa_state=%s\n"
             "rssi_dbm=%s\n"
             "linkspeed_mbps=%s\n"
             "freq_mhz=%s\n"
             "ipv4=%s\n"
             "ip4_label=%s\n"
             "ip4_masked=1\n"
             "dhcp_ready=%d\n"
             "route_default=%d\n"
             "ctrl_status_rc=%d\n"
             "ctrl_status_errno=%d\n"
             "ctrl_signal_rc=%d\n"
             "ctrl_signal_errno=%d\n"
             "decision=%s\n",
             wifi_iface_present() ? 1 : 0,
             operstate,
             carrier,
             mac_label,
             mac_label,
             ssid_label,
             link_info.wpa_state,
             link_info.rssi_dbm,
             link_info.linkspeed_mbps,
             link_info.freq_mhz,
             ip4_label,
             ip4_label,
             ipv4_rc == 0 ? 1 : 0,
             wifi_default_route_present() ? 1 : 0,
             link_info.status_rc,
             link_info.status_errno,
             link_info.signal_rc,
             link_info.signal_errno,
             decision != NULL ? decision : "-");
    return wifi_write_text_file(A90_WIFI_RUNTIME_SUMMARY, text, 0600);
}

static int wifi_write_udhcpc_script(void) {
    static const char script[] =
        "#!/cache/bin/busybox sh\n"
        "BB=/cache/bin/busybox\n"
        "IFACE=\"${interface:-wlan0}\"\n"
        "ROOT=/cache/a90-wifi\n"
        "RES=\"$ROOT/resolv.conf\"\n"
        "case \"$1\" in\n"
        "deconfig)\n"
        "  $BB ifconfig \"$IFACE\" 0.0.0.0 >/dev/null 2>&1 || true\n"
        "  ;;\n"
        "bound|renew)\n"
        "  $BB ifconfig \"$IFACE\" \"$ip\" netmask \"${subnet:-255.255.255.0}\" >/dev/null 2>&1 || exit 1\n"
        "  $BB route del default dev \"$IFACE\" >/dev/null 2>&1 || true\n"
        "  for router_item in $router; do\n"
        "    $BB route add default gw \"$router_item\" dev \"$IFACE\" >/dev/null 2>&1 || exit 1\n"
        "    break\n"
        "  done\n"
        "  echo \"# a90-wifi-temporary\" > \"$RES\"\n"
        "  for dns_item in $dns; do\n"
        "    echo \"nameserver $dns_item\" >> \"$RES\"\n"
        "  done\n"
        "  $BB mkdir -p /etc >/dev/null 2>&1 || true\n"
        "  if [ -d /etc ]; then $BB cp \"$RES\" /etc/resolv.conf >/dev/null 2>&1 || true; fi\n"
        "  ;;\n"
        "esac\n"
        "exit 0\n";
    int rc;

    rc = wifi_prepare_runtime_dirs();
    if (rc < 0) {
        return rc;
    }
    rc = wifi_write_text_file(A90_WIFI_UDHCPC_SCRIPT, script, 0700);
    if (rc < 0) {
        return rc;
    }
    return wifi_verify_root_exec_file(A90_WIFI_UDHCPC_SCRIPT, true);
}

static int wifi_run_dhcp_client(struct a90_run_result *result) {
    char *const argv[] = {
        (char *)"/cache/bin/busybox",
        (char *)"udhcpc",
        (char *)"-i",
        (char *)A90_WIFI_IFACE,
        (char *)"-n",
        (char *)"-q",
        (char *)"-t",
        (char *)"5",
        (char *)"-T",
        (char *)"3",
        (char *)"-p",
        (char *)A90_WIFI_UDHCPC_PID,
        (char *)"-s",
        (char *)A90_WIFI_UDHCPC_SCRIPT,
        NULL,
    };
    int verify_rc;

    verify_rc = wifi_verify_root_exec_file(A90_WIFI_UDHCPC_SCRIPT, true);
    if (verify_rc < 0) {
        return verify_rc;
    }
    return wifi_run_wait(argv, "wifi-dhcp", A90_WIFI_UDHCPC_LOG, A90_WIFI_DHCP_TIMEOUT_MS, result);
}

int a90_wifi_dhcp_profile(const char *profile_name) {
    struct a90_run_result dhcp_result;
    struct stat resolv_stat;
    char ipv4[64];
    char ip4_label[32];
    int script_rc;
    int dhcp_wait_rc;
    int dhcp_rc;
    int ipv4_rc;
    int nameservers = -1;
    bool route_default;

    memset(&dhcp_result, 0, sizeof(dhcp_result));
    a90_console_printf("[wifi dhcp]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_DHCP_VERSION);
    a90_console_printf("iface=%s\r\n", A90_WIFI_IFACE);
    a90_console_printf("profile=%s\r\n",
                       profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default");
    a90_console_printf("credentials=private\r\n");
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("connect_required=1\r\n");
    a90_console_printf("dhcp_executed=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("udhcpc.path=/cache/bin/busybox\r\n");
    a90_console_printf("udhcpc.script=%s\r\n", A90_WIFI_UDHCPC_SCRIPT);
    a90_console_printf("udhcpc.log=%s\r\n", A90_WIFI_UDHCPC_LOG);
    a90_console_printf("udhcpc.timeout_ms=%d\r\n", A90_WIFI_DHCP_TIMEOUT_MS);

    if (!wifi_iface_present()) {
        a90_console_printf("wlan0_present=0\r\n");
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-dhcp-wlan0-missing\r\n");
        return -ENODEV;
    }
    a90_console_printf("wlan0_present=1\r\n");
    a90_console_printf("carrier_up=%d\r\n", wifi_carrier_up() ? 1 : 0);
    if (!wifi_carrier_up()) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-dhcp-no-carrier\r\n");
        return -ENOTCONN;
    }

    if (access("/cache/bin/busybox", X_OK) < 0) {
        int saved_errno = errno;

        a90_console_printf("busybox_executable=0\r\n");
        a90_console_printf("busybox_errno=%d\r\n", saved_errno);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-dhcp-busybox-missing\r\n");
        return -saved_errno;
    }
    a90_console_printf("busybox_executable=1\r\n");

    script_rc = wifi_write_udhcpc_script();
    a90_console_printf("script_prepare_rc=%d\r\n", script_rc);
    if (script_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-dhcp-script-prepare-failed\r\n");
        return script_rc;
    }

    (void)unlink(A90_WIFI_UDHCPC_LOG);
    a90_console_printf("dhcp_executed=1\r\n");
    dhcp_wait_rc = wifi_run_dhcp_client(&dhcp_result);
    dhcp_rc = dhcp_result.rc;
    a90_console_printf("dhcp_wait_rc=%d\r\n", dhcp_wait_rc);
    a90_console_printf("dhcp_rc=%d\r\n", dhcp_rc);
    a90_console_printf("dhcp_status=%d\r\n", dhcp_result.status);
    a90_console_printf("dhcp_duration_ms=%ld\r\n", dhcp_result.duration_ms);
    a90_console_printf("dhcp_timed_out=%d\r\n", dhcp_result.timed_out ? 1 : 0);

    ipv4_rc = wifi_ipv4_addr(A90_WIFI_IFACE, ipv4, sizeof(ipv4));
    wifi_ipv4_label(ipv4_rc == 0 ? ipv4 : "-", ip4_label, sizeof(ip4_label));
    route_default = wifi_default_route_present();
    nameservers = wifi_count_resolv_nameservers();
    a90_console_printf("ipv4_assigned=%d\r\n", ipv4_rc == 0 ? 1 : 0);
    a90_console_printf("ipv4_rc=%d\r\n", ipv4_rc);
    a90_console_printf("ipv4=%s\r\n", ip4_label);
    a90_console_printf("ip4_label=%s\r\n", ip4_label);
    a90_console_printf("ip4_masked=1\r\n");
    a90_console_printf("route_default_present=%d\r\n", route_default ? 1 : 0);
    a90_console_printf("resolv_conf.path=%s\r\n", A90_WIFI_RESOLV_CONF);
    a90_console_printf("resolv_conf.present=%d\r\n", stat(A90_WIFI_RESOLV_CONF, &resolv_stat) == 0 ? 1 : 0);
    a90_console_printf("resolv_conf.size=%ld\r\n",
                       stat(A90_WIFI_RESOLV_CONF, &resolv_stat) == 0 ? (long)resolv_stat.st_size : -1L);
    a90_console_printf("resolv_conf.nameserver_count=%d\r\n", nameservers >= 0 ? nameservers : 0);
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");

    if (dhcp_wait_rc == 0 && dhcp_rc == 0 && ipv4_rc == 0 && route_default) {
        (void)wifi_write_runtime_summary("wifi-dhcp-pass");
        a90_logf("wifi", "dhcp profile=%s ipv4=1 route=1 secret_values_logged=0",
                 profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default");
        a90_console_printf("decision=wifi-dhcp-pass\r\n");
        return 0;
    }
    (void)wifi_write_runtime_summary("wifi-dhcp-failed");
    a90_logf("wifi", "dhcp profile=%s rc=%d ipv4_rc=%d route=%d secret_values_logged=0",
             profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
             dhcp_rc,
             ipv4_rc,
             route_default ? 1 : 0);
    a90_console_printf("decision=wifi-dhcp-failed\r\n");
    return dhcp_wait_rc < 0 ? dhcp_wait_rc : (dhcp_rc != 0 ? -EIO : -ENETUNREACH);
}

static void wifi_ping_init_target(struct a90_wifi_ping_target_result *result,
                                  const char *kind,
                                  const char *target,
                                  const char *log_path,
                                  bool target_redacted) {
    if (result == NULL) {
        return;
    }
    memset(result, 0, sizeof(*result));
    result->requested = true;
    result->packets_transmitted = -1;
    result->packets_received = -1;
    result->packet_loss_percent = -1;
    snprintf(result->kind, sizeof(result->kind), "%s", kind != NULL ? kind : "-");
    snprintf(result->target, sizeof(result->target), "%s", target != NULL ? target : "-");
    snprintf(result->log_path, sizeof(result->log_path), "%s", log_path != NULL ? log_path : "-");
    snprintf(result->rtt_avg_ms, sizeof(result->rtt_avg_ms), "%s", "-");
    snprintf(result->decision, sizeof(result->decision), "wifi-ping-%s-pending", result->kind);
    result->target_redacted = target_redacted;
}

static void wifi_ping_parse_log(const char *log_path, struct a90_wifi_ping_target_result *result) {
    char text[4096];
    char *line;

    if (log_path == NULL || result == NULL || read_text_file(log_path, text, sizeof(text)) < 0) {
        return;
    }
    line = text;
    while (line != NULL && *line != '\0') {
        char *line_end = strchr(line, '\n');
        char *packets;
        char *equals;

        if (line_end != NULL) {
            *line_end = '\0';
        }
        packets = strstr(line, " packets transmitted");
        if (packets != NULL) {
            int transmitted = -1;
            int received = -1;
            int loss = -1;

            if (sscanf(line,
                       "%d packets transmitted, %d received, %d%% packet loss",
                       &transmitted,
                       &received,
                       &loss) == 3 ||
                sscanf(line,
                       "%d packets transmitted, %d packets received, %d%% packet loss",
                       &transmitted,
                       &received,
                       &loss) == 3) {
                result->packets_transmitted = transmitted;
                result->packets_received = received;
                result->packet_loss_percent = loss;
            }
        }
        if (strstr(line, "rtt ") != NULL || strstr(line, "round-trip ") != NULL) {
            char min_ms[32] = "";
            char avg_ms[32] = "";
            char max_ms[32] = "";
            char tail[32] = "";

            equals = strchr(line, '=');
            if (equals != NULL &&
                sscanf(equals + 1, " %31[^/]/%31[^/]/%31[^/]/%31s", min_ms, avg_ms, max_ms, tail) >= 2) {
                trim_newline(avg_ms);
                snprintf(result->rtt_avg_ms, sizeof(result->rtt_avg_ms), "%s", avg_ms);
            }
        }
        line = line_end == NULL ? NULL : line_end + 1;
    }
}

static int wifi_run_ping_target(struct a90_wifi_ping_target_result *target,
                                const char *actual_target,
                                const char *log_path) {
    char *const argv[] = {
        (char *)"/cache/bin/busybox",
        (char *)"ping",
        (char *)"-c",
        (char *)"3",
        (char *)"-W",
        (char *)"2",
        (char *)actual_target,
        NULL,
    };
    struct a90_run_result run_result;

    if (target == NULL || actual_target == NULL || actual_target[0] == '\0' || log_path == NULL) {
        return -EINVAL;
    }
    memset(&run_result, 0, sizeof(run_result));
    target->resolved = true;
    target->executed = true;
    (void)unlink(log_path);
    target->run_wait_rc = wifi_run_wait(argv, "wifi-ping", log_path, A90_WIFI_PING_TIMEOUT_MS, &run_result);
    target->ping_rc = run_result.rc;
    target->ping_status = run_result.status;
    target->ping_timed_out = run_result.timed_out ? 1 : 0;
    target->saved_errno = run_result.saved_errno;
    target->duration_ms = run_result.duration_ms;
    wifi_ping_parse_log(log_path, target);
    target->success = (target->run_wait_rc == 0 && target->ping_rc == 0);
    snprintf(target->decision,
             sizeof(target->decision),
             "wifi-ping-%s-%s",
             target->kind,
             target->success ? "pass" : "failed");
    return target->success ? 0 : -EIO;
}

static bool wifi_ping_mode_requests_gateway(const char *mode) {
    return mode == NULL || mode[0] == '\0' || strcmp(mode, "all") == 0 || strcmp(mode, "gateway") == 0;
}

static bool wifi_ping_mode_requests_internet(const char *mode) {
    return mode == NULL || mode[0] == '\0' || strcmp(mode, "all") == 0 || strcmp(mode, "internet") == 0;
}

int a90_wifi_ping_collect(const char *mode, struct a90_wifi_ping_snapshot *out) {
    char gateway[64];
    bool request_gateway;
    bool request_internet;
    int gateway_rc = 0;
    int internet_rc = 0;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    out->count = A90_WIFI_PING_COUNT;
    out->timeout_sec = A90_WIFI_PING_TIMEOUT_SEC;
    snprintf(out->mode, sizeof(out->mode), "%s", mode != NULL && mode[0] != '\0' ? mode : "all");
    snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-not-run");

    request_gateway = wifi_ping_mode_requests_gateway(mode);
    request_internet = wifi_ping_mode_requests_internet(mode);
    if (!request_gateway && !request_internet) {
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-invalid-mode");
        out->rc = -EINVAL;
        return out->rc;
    }

    out->wlan0_present = wifi_iface_present();
    out->carrier_up = wifi_carrier_up();
    out->route_default_present = wifi_default_route_present();
    out->busybox_executable = access("/cache/bin/busybox", X_OK) == 0;

    if (!out->wlan0_present) {
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-wlan0-missing");
        out->rc = -ENODEV;
        return out->rc;
    }
    if (!out->carrier_up) {
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-no-carrier");
        out->rc = -ENOTCONN;
        return out->rc;
    }
    if (!out->route_default_present) {
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-no-default-route");
        out->rc = -ENETUNREACH;
        return out->rc;
    }
    if (!out->busybox_executable) {
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-busybox-missing");
        out->rc = -ENOENT;
        return out->rc;
    }

    if (request_gateway) {
        int route_rc;

        wifi_ping_init_target(&out->gateway,
                              "gateway",
                              "private-gateway",
                              A90_WIFI_PING_GATEWAY_LOG,
                              true);
        route_rc = wifi_default_gateway_ipv4(gateway, sizeof(gateway));
        if (route_rc < 0) {
            gateway_rc = route_rc;
            snprintf(out->gateway.decision,
                     sizeof(out->gateway.decision),
                     "%s",
                     "wifi-ping-gateway-unresolved");
        } else {
            gateway_rc = wifi_run_ping_target(&out->gateway, gateway, A90_WIFI_PING_GATEWAY_LOG);
        }
    }
    if (request_internet) {
        wifi_ping_init_target(&out->internet,
                              "internet",
                              A90_WIFI_PING_INTERNET_TARGET,
                              A90_WIFI_PING_INTERNET_LOG,
                              false);
        internet_rc = wifi_run_ping_target(&out->internet,
                                           A90_WIFI_PING_INTERNET_TARGET,
                                           A90_WIFI_PING_INTERNET_LOG);
    }

    if ((request_gateway && gateway_rc < 0) || (request_internet && internet_rc < 0)) {
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-failed");
        out->rc = gateway_rc < 0 ? gateway_rc : internet_rc;
        return out->rc;
    }
    snprintf(out->decision, sizeof(out->decision), "%s", "wifi-ping-pass");
    out->rc = 0;
    return 0;
}

static void wifi_print_ping_target(const char *prefix,
                                   const struct a90_wifi_ping_target_result *target) {
    if (prefix == NULL || target == NULL) {
        return;
    }
    a90_console_printf("%s.requested=%d\r\n", prefix, target->requested ? 1 : 0);
    a90_console_printf("%s.resolved=%d\r\n", prefix, target->resolved ? 1 : 0);
    a90_console_printf("%s.executed=%d\r\n", prefix, target->executed ? 1 : 0);
    a90_console_printf("%s.target=%s\r\n", prefix, target->target);
    a90_console_printf("%s.target_redacted=%d\r\n", prefix, target->target_redacted ? 1 : 0);
    a90_console_printf("%s.log=%s\r\n", prefix, target->log_path);
    a90_console_printf("%s.run_wait_rc=%d\r\n", prefix, target->run_wait_rc);
    a90_console_printf("%s.rc=%d\r\n", prefix, target->ping_rc);
    a90_console_printf("%s.status=%d\r\n", prefix, target->ping_status);
    a90_console_printf("%s.timed_out=%d\r\n", prefix, target->ping_timed_out);
    a90_console_printf("%s.duration_ms=%ld\r\n", prefix, target->duration_ms);
    a90_console_printf("%s.packets_transmitted=%d\r\n", prefix, target->packets_transmitted);
    a90_console_printf("%s.packets_received=%d\r\n", prefix, target->packets_received);
    a90_console_printf("%s.packet_loss_percent=%d\r\n", prefix, target->packet_loss_percent);
    a90_console_printf("%s.rtt_avg_ms=%s\r\n", prefix, target->rtt_avg_ms);
    a90_console_printf("%s.decision=%s\r\n", prefix, target->decision);
}

int a90_wifi_ping_once(const char *mode) {
    struct a90_wifi_ping_snapshot snapshot;
    int rc;

    a90_console_printf("[wifi ping]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_PING_VERSION);
    a90_console_printf("mode=%s\r\n", mode != NULL && mode[0] != '\0' ? mode : "all");
    a90_console_printf("count=%d\r\n", A90_WIFI_PING_COUNT);
    a90_console_printf("timeout_sec=%d\r\n", A90_WIFI_PING_TIMEOUT_SEC);
    a90_console_printf("external_ping=%d\r\n",
                       mode == NULL || mode[0] == '\0' || strcmp(mode, "all") == 0 ||
                       strcmp(mode, "internet") == 0 ? 1 : 0);
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");
    rc = a90_wifi_ping_collect(mode, &snapshot);
    a90_console_printf("wlan0_present=%d\r\n", snapshot.wlan0_present ? 1 : 0);
    a90_console_printf("carrier_up=%d\r\n", snapshot.carrier_up ? 1 : 0);
    a90_console_printf("route_default_present=%d\r\n", snapshot.route_default_present ? 1 : 0);
    a90_console_printf("busybox_executable=%d\r\n", snapshot.busybox_executable ? 1 : 0);
    wifi_print_ping_target("gateway", &snapshot.gateway);
    wifi_print_ping_target("internet", &snapshot.internet);
    a90_console_printf("decision=%s\r\n", snapshot.decision);
    a90_logf("wifi",
             "ping mode=%s rc=%d decision=%s gateway=%s internet=%s secret_values_logged=0",
             snapshot.mode,
             rc,
             snapshot.decision,
             snapshot.gateway.decision,
             snapshot.internet.decision);
    return rc;
}

int a90_wifi_cleanup(void) {
    char *const cleanup_argv[] = {
        (char *)"/cache/bin/busybox",
        (char *)"sh",
        (char *)"-c",
        (char *)"BB=/cache/bin/busybox; "
                "if [ -s /cache/a90-wifi/udhcpc-wlan0.pid ]; then $BB kill $($BB cat /cache/a90-wifi/udhcpc-wlan0.pid) 2>/dev/null || true; fi; "
                "$BB route del default dev wlan0 >/dev/null 2>&1 || true; "
                "$BB ifconfig wlan0 0.0.0.0 >/dev/null 2>&1 || true; "
                "if [ -f /etc/resolv.conf ] && $BB grep -q '^# a90-wifi-temporary' /etc/resolv.conf 2>/dev/null; then $BB rm -f /etc/resolv.conf; fi; "
                "$BB rm -f /cache/a90-wifi/udhcpc-wlan0.pid /cache/a90-wifi/resolv.conf 2>/dev/null || true",
        NULL,
    };
    struct a90_run_result cleanup_result;
    int ctrl_rc;
    int run_rc;

    memset(&cleanup_result, 0, sizeof(cleanup_result));
    a90_console_printf("[wifi cleanup]\r\n");
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");
    ctrl_rc = wifi_print_ctrl_result("ctrl.terminate", "TERMINATE");
    a90_console_printf("cleanup.terminate_attempted=1\r\n");
    a90_console_printf("cleanup.terminate_rc=%d\r\n", ctrl_rc);
    run_rc = wifi_run_wait(cleanup_argv, "wifi-cleanup", A90_WIFI_UDHCPC_LOG, 10000, &cleanup_result);
    a90_console_printf("cleanup.run_wait_rc=%d\r\n", run_rc);
    a90_console_printf("cleanup.run_rc=%d\r\n", cleanup_result.rc);
    a90_console_printf("cleanup.duration_ms=%ld\r\n", cleanup_result.duration_ms);
    (void)wifi_write_runtime_summary("wifi-cleanup");
    a90_console_printf("decision=wifi-cleanup-done\r\n");
    return 0;
}

static int wifi_wait_carrier(int timeout_ms, int *elapsed_ms_out) {
    long started_ms = monotonic_millis();
    long deadline_ms = started_ms + timeout_ms;

    while (monotonic_millis() <= deadline_ms) {
        if (wifi_carrier_up()) {
            if (elapsed_ms_out != NULL) {
                *elapsed_ms_out = (int)(monotonic_millis() - started_ms);
            }
            return 0;
        }
        usleep(500000);
    }
    if (elapsed_ms_out != NULL) {
        *elapsed_ms_out = timeout_ms;
    }
    return -ETIMEDOUT;
}

static void wifi_key_value_file_value(const char *path, const char *key, char *out, size_t out_size) {
    char text[1024];
    char *cursor;
    size_t key_len;

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "-");
    if (read_text_file(path, text, sizeof(text)) < 0) {
        return;
    }
    key_len = strlen(key);
    cursor = text;
    while (cursor != NULL && *cursor != '\0') {
        char *line_end = strchr(cursor, '\n');

        if (line_end != NULL) {
            *line_end = '\0';
        }
        if (strncmp(cursor, key, key_len) == 0) {
            snprintf(out, out_size, "%s", cursor + key_len);
            trim_newline(out);
            return;
        }
        cursor = line_end == NULL ? NULL : line_end + 1;
    }
}

static void wifi_runtime_value(const char *key, char *out, size_t out_size) {
    wifi_key_value_file_value(A90_WIFI_RUNTIME_SUMMARY, key, out, out_size);
}

int a90_wifi_status_snapshot(struct a90_wifi_status_snapshot *out) {
    char iface_path[128];
    char kind[32];
    char raw_mac[80];
    char raw_ipv4[64];
    char raw_gateway[64];

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    snprintf(out->iface, sizeof(out->iface), "%s", A90_WIFI_IFACE);
    snprintf(iface_path, sizeof(iface_path), "/sys/class/net/%s", A90_WIFI_IFACE);
    out->wlan0_present = access(iface_path, F_OK) == 0;
    wifi_read_attr(iface_path, "address", raw_mac, sizeof(raw_mac));
    wifi_mac_label(raw_mac, out->mac, sizeof(out->mac));
    wifi_read_attr(iface_path, "operstate", out->operstate, sizeof(out->operstate));
    wifi_read_attr(iface_path, "carrier", out->carrier, sizeof(out->carrier));
    wifi_read_attr(iface_path, "flags", out->flags, sizeof(out->flags));
    wifi_read_attr(iface_path, "statistics/rx_bytes", out->rx_bytes, sizeof(out->rx_bytes));
    wifi_read_attr(iface_path, "statistics/tx_bytes", out->tx_bytes, sizeof(out->tx_bytes));
    out->ipv4_rc = wifi_ipv4_addr(A90_WIFI_IFACE, raw_ipv4, sizeof(raw_ipv4));
    if (out->ipv4_rc < 0) {
        snprintf(raw_ipv4, sizeof(raw_ipv4), "%s", "-");
    }
    wifi_ipv4_label(raw_ipv4, out->ipv4, sizeof(out->ipv4));
    out->route_default_present = wifi_default_route_present();
    out->gateway_rc = wifi_default_gateway_ipv4(raw_gateway, sizeof(raw_gateway));
    if (out->gateway_rc < 0) {
        snprintf(raw_gateway, sizeof(raw_gateway), "%s", "-");
    }
    wifi_ipv4_label(raw_gateway, out->gateway, sizeof(out->gateway));
    out->nameserver_count = wifi_count_resolv_nameservers();
    out->supplicant_process_count = wifi_count_processes_with_token("wpa_supplicant");
    wifi_runtime_value("wlan0_present=", out->runtime_wlan0, sizeof(out->runtime_wlan0));
    wifi_runtime_value("mac_label=", out->runtime_mac, sizeof(out->runtime_mac));
    wifi_runtime_value("ip4_label=", out->runtime_ip, sizeof(out->runtime_ip));
    wifi_runtime_value("ssid_label=", out->runtime_ssid_label, sizeof(out->runtime_ssid_label));
    wifi_runtime_value("wpa_state=", out->runtime_wpa_state, sizeof(out->runtime_wpa_state));
    wifi_runtime_value("rssi_dbm=", out->runtime_rssi, sizeof(out->runtime_rssi));
    wifi_runtime_value("linkspeed_mbps=", out->runtime_linkspeed, sizeof(out->runtime_linkspeed));
    wifi_runtime_value("freq_mhz=", out->runtime_freq_mhz, sizeof(out->runtime_freq_mhz));
    wifi_runtime_value("decision=", out->runtime_decision, sizeof(out->runtime_decision));
    if (access(A90_WIFI_CTRL_SOCKET, F_OK) == 0 &&
        (wifi_value_missing(out->runtime_wpa_state) ||
         wifi_value_missing(out->runtime_rssi) ||
         wifi_value_missing(out->runtime_linkspeed) ||
         wifi_value_missing(out->runtime_freq_mhz))) {
        struct wifi_ctrl_link_info link_info;

        wifi_collect_ctrl_link_info(&link_info);
        if (wifi_value_missing(out->runtime_ssid_label) && link_info.ssid_label[0] != '\0') {
            snprintf(out->runtime_ssid_label, sizeof(out->runtime_ssid_label), "%s", link_info.ssid_label);
        }
        if (wifi_value_missing(out->runtime_wpa_state) && link_info.wpa_state[0] != '\0') {
            snprintf(out->runtime_wpa_state, sizeof(out->runtime_wpa_state), "%s", link_info.wpa_state);
        }
        if (wifi_value_missing(out->runtime_rssi) && link_info.rssi_dbm[0] != '\0') {
            snprintf(out->runtime_rssi, sizeof(out->runtime_rssi), "%s", link_info.rssi_dbm);
        }
        if (wifi_value_missing(out->runtime_linkspeed) && link_info.linkspeed_mbps[0] != '\0') {
            snprintf(out->runtime_linkspeed, sizeof(out->runtime_linkspeed), "%s", link_info.linkspeed_mbps);
        }
        if (wifi_value_missing(out->runtime_freq_mhz) && link_info.freq_mhz[0] != '\0') {
            snprintf(out->runtime_freq_mhz, sizeof(out->runtime_freq_mhz), "%s", link_info.freq_mhz);
        }
    }
    wifi_key_value_file_value(A90_WIFI_AUTOCONNECT_RESULT,
                              "profile=",
                              out->autoconnect_profile,
                              sizeof(out->autoconnect_profile));
    wifi_key_value_file_value(A90_WIFI_AUTOCONNECT_RESULT,
                              "decision=",
                              out->autoconnect_decision,
                              sizeof(out->autoconnect_decision));
    wifi_key_value_file_value(A90_WIFI_AUTOCONNECT_RESULT,
                              "final_rc=",
                              out->autoconnect_final_rc,
                              sizeof(out->autoconnect_final_rc));
    wifi_key_value_file_value(A90_WIFI_AUTOCONNECT_RESULT,
                              "carrier_up=",
                              out->autoconnect_carrier_up,
                              sizeof(out->autoconnect_carrier_up));
    wifi_key_value_file_value(A90_WIFI_AUTOCONNECT_RESULT,
                              "nameserver_count=",
                              out->autoconnect_nameserver_count,
                              sizeof(out->autoconnect_nameserver_count));
    out->runtime_summary_present = access(A90_WIFI_RUNTIME_SUMMARY, R_OK) == 0;
    out->runtime_input_present = access(A90_WIFI_RUNTIME_INPUT, R_OK) == 0;
    out->autoconnect_result_present = access(A90_WIFI_AUTOCONNECT_RESULT, R_OK) == 0;
    out->resolv_conf_present = access(A90_WIFI_RESOLV_CONF, R_OK) == 0;
    out->supplicant_executable = access(A90_WIFI_STANDALONE_SUPPLICANT, X_OK) == 0;
    snprintf(kind, sizeof(kind), "%s", "missing");
    (void)wifi_path_kind(A90_WIFI_CTRL_SOCKET, false, kind, sizeof(kind));
    snprintf(out->ctrl_socket_kind, sizeof(out->ctrl_socket_kind), "%s", kind);
    return 0;
}

int a90_wifi_print_status(void) {
    char kind[32];
    struct a90_wifi_status_snapshot status;

    (void)a90_wifi_status_snapshot(&status);

    a90_console_printf("[wifi status]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SCAN_VERSION);
    a90_console_printf("iface=%s\r\n", status.iface);
    a90_console_printf("wlan0_present=%d\r\n", status.wlan0_present ? 1 : 0);
    a90_console_printf("mac=%s\r\n", status.mac);
    a90_console_printf("mac_label=%s\r\n", status.mac);
    a90_console_printf("mac_raw_redacted=1\r\n");
    a90_console_printf("operstate=%s\r\n", status.operstate);
    a90_console_printf("carrier=%s\r\n", status.carrier);
    a90_console_printf("flags=%s\r\n", status.flags);
    a90_console_printf("rx_bytes=%s\r\n", status.rx_bytes);
    a90_console_printf("tx_bytes=%s\r\n", status.tx_bytes);
    a90_console_printf("ipv4=%s\r\n", status.ipv4);
    a90_console_printf("ip4_label=%s\r\n", status.ipv4);
    a90_console_printf("ip4_masked=1\r\n");
    a90_console_printf("ipv4_rc=%d\r\n", status.ipv4_rc);
    a90_console_printf("default_route_present=%d\r\n", status.route_default_present ? 1 : 0);
    a90_console_printf("gateway=%s\r\n", status.gateway);
    a90_console_printf("gateway_label=%s\r\n", status.gateway);
    a90_console_printf("gateway_masked=1\r\n");
    a90_console_printf("gateway_rc=%d\r\n", status.gateway_rc);
    a90_console_printf("resolv_conf.path=%s\r\n", A90_WIFI_RESOLV_CONF);
    a90_console_printf("resolv_conf.present=%d\r\n", status.resolv_conf_present ? 1 : 0);
    a90_console_printf("resolv_conf.nameserver_count=%d\r\n",
                       status.nameserver_count >= 0 ? status.nameserver_count : 0);
    a90_console_printf("runtime_summary.path=%s\r\n", A90_WIFI_RUNTIME_SUMMARY);
    a90_console_printf("runtime_summary.present=%d\r\n", status.runtime_summary_present ? 1 : 0);
    a90_console_printf("runtime_input.path=%s\r\n", A90_WIFI_RUNTIME_INPUT);
    a90_console_printf("runtime_input.present=%d\r\n", status.runtime_input_present ? 1 : 0);
    a90_console_printf("runtime.wlan0_present=%s\r\n", status.runtime_wlan0);
    a90_console_printf("runtime.mac=%s\r\n", status.runtime_mac);
    a90_console_printf("runtime.ipv4=%s\r\n", status.runtime_ip);
    a90_console_printf("runtime.ssid_label=%s\r\n", status.runtime_ssid_label);
    a90_console_printf("runtime.wpa_state=%s\r\n", status.runtime_wpa_state);
    a90_console_printf("runtime.rssi_dbm=%s\r\n", status.runtime_rssi);
    a90_console_printf("runtime.linkspeed_mbps=%s\r\n", status.runtime_linkspeed);
    a90_console_printf("runtime.freq_mhz=%s\r\n", status.runtime_freq_mhz);
    a90_console_printf("runtime.decision=%s\r\n", status.runtime_decision);
    a90_console_printf("autoconnect_result.path=%s\r\n", A90_WIFI_AUTOCONNECT_RESULT);
    a90_console_printf("autoconnect_result.present=%d\r\n", status.autoconnect_result_present ? 1 : 0);
    a90_console_printf("autoconnect.profile=%s\r\n", status.autoconnect_profile);
    a90_console_printf("autoconnect.decision=%s\r\n", status.autoconnect_decision);
    a90_console_printf("autoconnect.final_rc=%s\r\n", status.autoconnect_final_rc);
    a90_console_printf("autoconnect.carrier_up=%s\r\n", status.autoconnect_carrier_up);
    a90_console_printf("autoconnect.nameserver_count=%s\r\n", status.autoconnect_nameserver_count);
    a90_console_printf("supplicant.provider=standalone\r\n");
    a90_console_printf("supplicant.path=%s\r\n", A90_WIFI_STANDALONE_SUPPLICANT);
    a90_console_printf("supplicant.kind=%s\r\n",
                       wifi_path_kind(A90_WIFI_STANDALONE_SUPPLICANT, false, kind, sizeof(kind)) == 0 ? kind : kind);
    a90_console_printf("supplicant.executable=%d\r\n", status.supplicant_executable ? 1 : 0);
    {
        int root_exec_rc = wifi_verify_root_exec_file(A90_WIFI_STANDALONE_SUPPLICANT, true);

        a90_console_printf("supplicant.root_exec_rc=%d\r\n", root_exec_rc);
        a90_console_printf("supplicant.root_exec_ok=%d\r\n", root_exec_rc == 0 ? 1 : 0);
    }
    a90_console_printf("supplicant.process_count=%d\r\n", status.supplicant_process_count);
    a90_console_printf("ctrl_socket.path=%s\r\n", A90_WIFI_CTRL_SOCKET);
    a90_console_printf("ctrl_socket.kind=%s\r\n", status.ctrl_socket_kind);
    a90_console_printf("supplicant_config.path=%s\r\n", A90_WIFICFG_SUPPLICANT_CONF);
    a90_console_printf("supplicant_config.present=%d\r\n", access(A90_WIFICFG_SUPPLICANT_CONF, R_OK) == 0 ? 1 : 0);
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("decision=%s\r\n",
                       status.wlan0_present ? "wifi-status-wlan0-present" : "wifi-status-wlan0-missing");
    a90_logf("wifi", "status wlan0=%d operstate=%s carrier=%s supplicant_count=%d",
             status.wlan0_present ? 1 : 0,
             status.operstate,
             status.carrier,
             status.supplicant_process_count);
    return 0;
}

static void *wifi_nla_data(const struct nlattr *attr) {
    return (void *)((const char *)attr + NLA_HDRLEN);
}

static bool wifi_nla_ok(const struct nlattr *attr, int remaining) {
    return remaining >= (int)sizeof(*attr) &&
           attr->nla_len >= sizeof(*attr) &&
           attr->nla_len <= remaining;
}

static struct nlattr *wifi_nla_next(struct nlattr *attr, int *remaining) {
    int aligned_len = NLA_ALIGN(attr->nla_len);

    *remaining -= aligned_len;
    return (struct nlattr *)((char *)attr + aligned_len);
}

static unsigned int wifi_nla_type(const struct nlattr *attr) {
    return attr->nla_type & NLA_TYPE_MASK;
}

static void wifi_parse_attrs(struct nlattr **attrs, int max_attr, struct nlattr *attr, int len) {
    memset(attrs, 0, sizeof(struct nlattr *) * (size_t)(max_attr + 1));
    while (wifi_nla_ok(attr, len)) {
        unsigned int attr_type = wifi_nla_type(attr);

        if (attr_type <= (unsigned int)max_attr) {
            attrs[attr_type] = attr;
        }
        attr = wifi_nla_next(attr, &len);
    }
}

static int wifi_add_attr(char *buf, size_t buf_size, size_t *offset, int type, const void *data, size_t len) {
    struct nlattr *attr;
    size_t attr_len = NLA_HDRLEN + len;
    size_t aligned_len = NLA_ALIGN(attr_len);

    if (*offset + aligned_len > buf_size) {
        errno = EMSGSIZE;
        return -1;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)type;
    attr->nla_len = (unsigned short)attr_len;
    if (len > 0 && data != NULL) {
        memcpy((char *)attr + NLA_HDRLEN, data, len);
    }
    memset(buf + *offset + attr_len, 0, aligned_len - attr_len);
    *offset += aligned_len;
    return 0;
}

static struct nlattr *wifi_nest_start(char *buf, size_t buf_size, size_t *offset, int type) {
    struct nlattr *attr;
    size_t aligned_len = NLA_ALIGN((size_t)NLA_HDRLEN);

    if (*offset + aligned_len > buf_size) {
        errno = EMSGSIZE;
        return NULL;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)(type | NLA_F_NESTED);
    attr->nla_len = (unsigned short)NLA_HDRLEN;
    memset(buf + *offset + NLA_HDRLEN, 0, aligned_len - (size_t)NLA_HDRLEN);
    *offset += aligned_len;
    return attr;
}

static void wifi_nest_end(struct nlattr *attr, size_t offset, const char *buf) {
    attr->nla_len = (unsigned short)((buf + offset) - (const char *)attr);
}

static int wifi_open_genl_socket(void) {
    struct sockaddr_nl local;
    struct timeval timeout;
    int socket_fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_GENERIC);

    if (socket_fd < 0) {
        return -1;
    }
    memset(&local, 0, sizeof(local));
    local.nl_family = AF_NETLINK;
    if (bind(socket_fd, (struct sockaddr *)&local, sizeof(local)) < 0) {
        close(socket_fd);
        return -1;
    }
    memset(&timeout, 0, sizeof(timeout));
    timeout.tv_sec = 5;
    if (setsockopt(socket_fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0) {
        close(socket_fd);
        return -1;
    }
    return socket_fd;
}

static int wifi_send_genl(int socket_fd,
                          uint16_t family_id,
                          uint8_t command,
                          uint16_t flags,
                          uint32_t seq,
                          const char *family_name,
                          uint32_t ifindex,
                          bool include_ifindex,
                          bool include_wildcard_ssid) {
    char buffer[1024];
    struct nlmsghdr *nlh = (struct nlmsghdr *)buffer;
    struct genlmsghdr *genlh;
    struct sockaddr_nl addr;
    size_t offset;

    memset(buffer, 0, sizeof(buffer));
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(*genlh));
    nlh->nlmsg_type = family_id;
    nlh->nlmsg_flags = NLM_F_REQUEST | flags;
    nlh->nlmsg_seq = seq;
    nlh->nlmsg_pid = 0;
    genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
    genlh->cmd = command;
    genlh->version = 1;
    offset = NLMSG_ALIGN(nlh->nlmsg_len);
    if (family_name != NULL &&
        wifi_add_attr(buffer, sizeof(buffer), &offset, CTRL_ATTR_FAMILY_NAME,
                      family_name, strlen(family_name) + 1) < 0) {
        return -1;
    }
    if (include_ifindex &&
        wifi_add_attr(buffer, sizeof(buffer), &offset, NL80211_ATTR_IFINDEX,
                      &ifindex, sizeof(ifindex)) < 0) {
        return -1;
    }
    if (include_wildcard_ssid) {
        struct nlattr *scan_ssids = wifi_nest_start(buffer, sizeof(buffer), &offset, NL80211_ATTR_SCAN_SSIDS);

        if (scan_ssids == NULL ||
            wifi_add_attr(buffer, sizeof(buffer), &offset, 1, NULL, 0) < 0) {
            return -1;
        }
        wifi_nest_end(scan_ssids, offset, buffer);
    }
    nlh->nlmsg_len = (uint32_t)offset;

    memset(&addr, 0, sizeof(addr));
    addr.nl_family = AF_NETLINK;
    if (sendto(socket_fd, buffer, nlh->nlmsg_len, 0, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        return -1;
    }
    return 0;
}

static int wifi_recv_family_id(int socket_fd, uint32_t seq) {
    char buffer[A90_WIFI_SCAN_RECV_SIZE];
    ssize_t received = recv(socket_fd, buffer, sizeof(buffer), 0);
    struct nlmsghdr *nlh;
    int remaining;

    if (received < 0) {
        return -1;
    }
    for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
         NLMSG_OK(nlh, remaining);
         nlh = NLMSG_NEXT(nlh, remaining)) {
        struct genlmsghdr *genlh;
        struct nlattr *attrs[CTRL_ATTR_MAX + 1];
        int attr_len;

        if (nlh->nlmsg_seq != seq) {
            continue;
        }
        if (nlh->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

            errno = err->error < 0 ? -err->error : EIO;
            return -1;
        }
        if (nlh->nlmsg_type == NLMSG_DONE) {
            break;
        }
        genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
        attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
        if (attr_len < 0) {
            continue;
        }
        wifi_parse_attrs(attrs,
                         CTRL_ATTR_MAX,
                         (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                         attr_len);
        if (attrs[CTRL_ATTR_FAMILY_ID] != NULL) {
            return (int)*(uint16_t *)wifi_nla_data(attrs[CTRL_ATTR_FAMILY_ID]);
        }
    }
    errno = ENOENT;
    return -1;
}

static int wifi_get_family_id(int socket_fd, const char *name) {
    const uint32_t seq = 1;

    if (wifi_send_genl(socket_fd, GENL_ID_CTRL, CTRL_CMD_GETFAMILY, 0, seq, name, 0, false, false) < 0) {
        return -1;
    }
    return wifi_recv_family_id(socket_fd, seq);
}

static int wifi_recv_ack(int socket_fd, uint32_t seq) {
    char buffer[A90_WIFI_SCAN_RECV_SIZE];

    for (;;) {
        ssize_t received = recv(socket_fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

                if (err->error == 0) {
                    return 0;
                }
                errno = err->error < 0 ? -err->error : EIO;
                return -1;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                return 0;
            }
        }
    }
}

static int wifi_trigger_scan(int socket_fd, int family_id, uint32_t ifindex) {
    const uint32_t seq = 2;

    if (wifi_send_genl(socket_fd,
                       (uint16_t)family_id,
                       NL80211_CMD_TRIGGER_SCAN,
                       NLM_F_ACK,
                       seq,
                       NULL,
                       ifindex,
                       true,
                       true) < 0) {
        return -1;
    }
    return wifi_recv_ack(socket_fd, seq);
}

static int wifi_attr_payload_len(const struct nlattr *attr) {
    if (attr == NULL || attr->nla_len < NLA_HDRLEN) {
        return 0;
    }
    return (int)attr->nla_len - NLA_HDRLEN;
}

static bool wifi_ie_is_hidden_ssid(const unsigned char *ssid, size_t ssid_len) {
    size_t index;

    if (ssid_len == 0) {
        return true;
    }
    for (index = 0; index < ssid_len; ++index) {
        if (ssid[index] != 0) {
            return false;
        }
    }
    return true;
}

static void wifi_scan_copy_ssid(const unsigned char *ssid,
                                size_t ssid_len,
                                char *out,
                                size_t out_size,
                                bool *hidden_out) {
    size_t index;
    size_t limit;
    bool hidden = wifi_ie_is_hidden_ssid(ssid, ssid_len);

    if (out == NULL || out_size == 0) {
        return;
    }
    if (hidden) {
        snprintf(out, out_size, "%s", "<hidden>");
        if (hidden_out != NULL) {
            *hidden_out = true;
        }
        return;
    }
    limit = ssid_len;
    if (limit > out_size - 1) {
        limit = out_size - 1;
    }
    for (index = 0; index < limit; ++index) {
        unsigned char value = ssid[index];

        out[index] = value >= 32 && value < 127 ? (char)value : '?';
    }
    out[limit] = '\0';
    if (hidden_out != NULL) {
        *hidden_out = false;
    }
}

static void wifi_scan_parse_ies(const unsigned char *ies,
                                size_t ies_len,
                                struct a90_wifi_scan_result *result,
                                bool privacy_capable) {
    bool has_rsn = false;
    bool has_wpa = false;
    size_t offset = 0;

    while (offset + 2 <= ies_len) {
        unsigned char element_id = ies[offset];
        unsigned char element_len = ies[offset + 1];
        const unsigned char *payload = ies + offset + 2;

        if (offset + 2 + (size_t)element_len > ies_len) {
            break;
        }
        if (element_id == 0) {
            result->ssid_present = true;
            wifi_scan_copy_ssid(payload,
                                element_len,
                                result->ssid,
                                sizeof(result->ssid),
                                &result->hidden);
        } else if (element_id == 48) {
            has_rsn = true;
        } else if (element_id == 221 &&
                   element_len >= 4 &&
                   payload[0] == 0x00 &&
                   payload[1] == 0x50 &&
                   payload[2] == 0xf2 &&
                   payload[3] == 0x01) {
            has_wpa = true;
        }
        offset += 2 + (size_t)element_len;
    }

    if (has_rsn) {
        snprintf(result->security, sizeof(result->security), "%s", "WPA2/RSN");
    } else if (has_wpa) {
        snprintf(result->security, sizeof(result->security), "%s", "WPA");
    } else if (privacy_capable) {
        snprintf(result->security, sizeof(result->security), "%s", "PRIVACY");
    } else {
        snprintf(result->security, sizeof(result->security), "%s", "OPEN");
    }
    if (!result->ssid_present) {
        snprintf(result->ssid, sizeof(result->ssid), "%s", "<unknown>");
    }
}

static void wifi_scan_parse_bss(struct nlattr *bss_attr,
                                struct a90_wifi_scan_result *result) {
    struct nlattr *bss_attrs[NL80211_BSS_MAX + 1];
    int bss_len;
    bool privacy_capable = false;

    memset(result, 0, sizeof(*result));
    result->freq_mhz = 0;
    result->signal_dbm = 0;
    snprintf(result->ssid, sizeof(result->ssid), "%s", "<unknown>");
    snprintf(result->security, sizeof(result->security), "%s", "UNKNOWN");

    if (bss_attr == NULL) {
        return;
    }
    bss_len = wifi_attr_payload_len(bss_attr);
    wifi_parse_attrs(bss_attrs,
                     NL80211_BSS_MAX,
                     (struct nlattr *)wifi_nla_data(bss_attr),
                     bss_len);
    if (bss_attrs[NL80211_BSS_FREQUENCY] != NULL &&
        wifi_attr_payload_len(bss_attrs[NL80211_BSS_FREQUENCY]) >= (int)sizeof(uint32_t)) {
        result->freq_mhz = (int)*(uint32_t *)wifi_nla_data(bss_attrs[NL80211_BSS_FREQUENCY]);
    }
    if (bss_attrs[NL80211_BSS_SIGNAL_MBM] != NULL &&
        wifi_attr_payload_len(bss_attrs[NL80211_BSS_SIGNAL_MBM]) >= (int)sizeof(int32_t)) {
        int32_t signal_mbm = *(int32_t *)wifi_nla_data(bss_attrs[NL80211_BSS_SIGNAL_MBM]);

        result->signal_dbm = signal_mbm / 100;
        result->signal_valid = true;
    }
    if (bss_attrs[NL80211_BSS_CAPABILITY] != NULL &&
        wifi_attr_payload_len(bss_attrs[NL80211_BSS_CAPABILITY]) >= (int)sizeof(uint16_t)) {
        uint16_t capability = *(uint16_t *)wifi_nla_data(bss_attrs[NL80211_BSS_CAPABILITY]);

        privacy_capable = (capability & 0x0010U) != 0;
    }
    if (bss_attrs[NL80211_BSS_INFORMATION_ELEMENTS] != NULL) {
        wifi_scan_parse_ies((const unsigned char *)wifi_nla_data(
                                bss_attrs[NL80211_BSS_INFORMATION_ELEMENTS]),
                            (size_t)wifi_attr_payload_len(
                                bss_attrs[NL80211_BSS_INFORMATION_ELEMENTS]),
                            result,
                            privacy_capable);
    } else {
        snprintf(result->security, sizeof(result->security),
                 "%s", privacy_capable ? "PRIVACY" : "OPEN");
    }
}

static int wifi_dump_scan_results(int socket_fd,
                                  int family_id,
                                  uint32_t ifindex,
                                  struct a90_wifi_scan_snapshot *snapshot) {
    char buffer[A90_WIFI_SCAN_RECV_SIZE];
    const uint32_t seq = 4;
    bool done = false;

    snapshot->scan_result_count = 0;
    snapshot->stored_count = 0;
    if (wifi_send_genl(socket_fd,
                       (uint16_t)family_id,
                       NL80211_CMD_GET_SCAN,
                       NLM_F_DUMP,
                       seq,
                       NULL,
                       ifindex,
                       true,
                       false) < 0) {
        return -1;
    }
    while (!done) {
        ssize_t received = recv(socket_fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            struct genlmsghdr *genlh;
            struct nlattr *attrs[NL80211_ATTR_MAX + 1];
            int attr_len;

            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                done = true;
                break;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

                if (err->error == 0) {
                    done = true;
                    break;
                }
                errno = err->error < 0 ? -err->error : EIO;
                return -1;
            }
            genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
            attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
            if (attr_len < 0) {
                continue;
            }
            wifi_parse_attrs(attrs,
                             NL80211_ATTR_MAX,
                             (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                             attr_len);
            if (attrs[NL80211_ATTR_BSS] != NULL) {
                int stored_index = snapshot->stored_count;

                ++snapshot->scan_result_count;
                if (stored_index < A90_WIFI_UI_MAX_SCAN_RESULTS) {
                    wifi_scan_parse_bss(attrs[NL80211_ATTR_BSS],
                                        &snapshot->results[stored_index]);
                    snapshot->stored_count++;
                }
            }
        }
    }
    return 0;
}

static int wifi_link_set_up(const char *ifname, int *saved_errno) {
    struct ifreq request;
    int socket_fd;
    short flags;

    *saved_errno = 0;
    socket_fd = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (socket_fd < 0) {
        *saved_errno = errno;
        return -1;
    }
    memset(&request, 0, sizeof(request));
    snprintf(request.ifr_name, sizeof(request.ifr_name), "%s", ifname);
    if (ioctl(socket_fd, SIOCGIFFLAGS, &request) < 0) {
        *saved_errno = errno;
        close(socket_fd);
        return -1;
    }
    flags = request.ifr_flags;
    request.ifr_flags = (short)(request.ifr_flags | IFF_UP);
    if (ioctl(socket_fd, SIOCSIFFLAGS, &request) < 0) {
        *saved_errno = errno;
        close(socket_fd);
        return -1;
    }
    close(socket_fd);
    *saved_errno = 0;
    return (flags & IFF_UP) != 0 ? 1 : 0;
}

int a90_wifi_scan_collect(int delay_ms, struct a90_wifi_scan_snapshot *out) {
    unsigned int ifindex;
    int socket_fd;
    int family_id;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    if (delay_ms < 0) {
        delay_ms = 0;
    }
    if (delay_ms > 30000) {
        delay_ms = 30000;
    }
    out->delay_ms = delay_ms;
    out->family_id = -1;
    out->trigger_rc = -1;
    snprintf(out->decision, sizeof(out->decision), "%s", "wifi-scan-not-run");

    out->link_up_rc = wifi_link_set_up(A90_WIFI_IFACE, &out->link_up_errno);
    if (out->link_up_rc < 0) {
        out->saved_errno = out->link_up_errno;
        out->rc = -out->saved_errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-scan-link-up-failed");
        return out->rc;
    }

    ifindex = if_nametoindex(A90_WIFI_IFACE);
    if (ifindex == 0) {
        out->saved_errno = errno;
        out->rc = -out->saved_errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-scan-interface-missing");
        return out->rc;
    }
    out->ifindex = ifindex;

    socket_fd = wifi_open_genl_socket();
    if (socket_fd < 0) {
        out->saved_errno = errno;
        out->rc = -out->saved_errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-scan-nl80211-unavailable");
        return out->rc;
    }
    out->netlink_open = 1;

    family_id = wifi_get_family_id(socket_fd, "nl80211");
    if (family_id < 0) {
        out->saved_errno = errno;
        close(socket_fd);
        out->rc = -out->saved_errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-scan-family-missing");
        return out->rc;
    }
    out->family_id = family_id;

    if (wifi_trigger_scan(socket_fd, family_id, ifindex) < 0) {
        out->trigger_errno = errno;
        if (out->trigger_errno != EBUSY) {
            out->saved_errno = out->trigger_errno;
            close(socket_fd);
            out->rc = -out->saved_errno;
            snprintf(out->decision, sizeof(out->decision), "%s", "wifi-scan-trigger-failed");
            return out->rc;
        }
    } else {
        out->trigger_rc = 0;
    }

    usleep((useconds_t)delay_ms * 1000U);

    if (wifi_dump_scan_results(socket_fd, family_id, ifindex, out) < 0) {
        out->saved_errno = errno;
        close(socket_fd);
        out->rc = -out->saved_errno;
        snprintf(out->decision, sizeof(out->decision), "%s", "wifi-scan-dump-failed");
        return out->rc;
    }
    close(socket_fd);
    out->rc = 0;
    snprintf(out->decision,
             sizeof(out->decision),
             "%s",
             out->scan_result_count > 0 ? "wifi-scan-pass" : "wifi-scan-zero-bss");
    return 0;
}

int a90_wifi_scan_once(int delay_ms) {
    struct a90_wifi_scan_snapshot snapshot;
    int rc;

    a90_console_printf("[wifi scan]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SCAN_VERSION);
    a90_console_printf("iface=%s\r\n", A90_WIFI_IFACE);
    a90_console_printf("credentials=0\r\n");
    a90_console_printf("connect=0\r\n");
    a90_console_printf("dhcp_routing=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("raw_results_redacted=1\r\n");
    a90_console_printf("link_up_attempted=1\r\n");

    rc = a90_wifi_scan_collect(delay_ms, &snapshot);
    a90_console_printf("link_up_rc=%d\r\n", snapshot.link_up_rc);
    a90_console_printf("link_up_errno=%d\r\n", snapshot.link_up_errno);
    if (strcmp(snapshot.decision, "wifi-scan-link-up-failed") == 0) {
        a90_console_printf("decision=%s\r\n", snapshot.decision);
        return rc;
    }
    if (snapshot.ifindex == 0) {
        a90_console_printf("ifindex=0\r\n");
        if (strcmp(snapshot.decision, "wifi-scan-interface-missing") == 0) {
            a90_console_printf("errno=%d\r\n", snapshot.saved_errno);
            a90_console_printf("decision=%s\r\n", snapshot.decision);
            return rc;
        }
    } else {
        a90_console_printf("ifindex=%u\r\n", snapshot.ifindex);
    }
    a90_console_printf("netlink_open=%d\r\n", snapshot.netlink_open);
    if (strcmp(snapshot.decision, "wifi-scan-nl80211-unavailable") == 0) {
        a90_console_printf("errno=%d\r\n", snapshot.saved_errno);
        a90_console_printf("decision=%s\r\n", snapshot.decision);
        return rc;
    }
    a90_console_printf("family_id=%d\r\n", snapshot.family_id < 0 ? 0 : snapshot.family_id);
    if (strcmp(snapshot.decision, "wifi-scan-family-missing") == 0) {
        a90_console_printf("errno=%d\r\n", snapshot.saved_errno);
        a90_console_printf("decision=%s\r\n", snapshot.decision);
        return rc;
    }
    a90_console_printf("trigger_attempted=1\r\n");
    a90_console_printf("trigger_rc=%d\r\n", snapshot.trigger_rc);
    a90_console_printf("trigger_errno=%d\r\n", snapshot.trigger_errno);
    if (snapshot.trigger_rc < 0 && snapshot.trigger_errno == EBUSY) {
        a90_console_printf("trigger_busy_continue=1\r\n");
    }
    if (strcmp(snapshot.decision, "wifi-scan-trigger-failed") == 0) {
        a90_console_printf("decision=%s\r\n", snapshot.decision);
        return rc;
    }
    a90_console_printf("delay_ms=%d\r\n", snapshot.delay_ms);
    if (rc < 0) {
        a90_console_printf("scan_result_count=0\r\n");
        a90_console_printf("errno=%d\r\n", snapshot.saved_errno);
        a90_console_printf("decision=%s\r\n", snapshot.decision);
        return rc;
    }
    a90_console_printf("scan_result_count=%d\r\n", snapshot.scan_result_count);
    a90_console_printf("decision=%s\r\n", snapshot.decision);
    a90_logf("wifi", "scan count=%d delay_ms=%d", snapshot.scan_result_count, snapshot.delay_ms);
    return snapshot.scan_result_count > 0 ? 0 : -ENODATA;
}

static int wifi_connect_profile_with_carrier_timeout(const char *profile_name, int carrier_wait_timeout_ms) {
    char supplicant_config[256] = "";
    char ctrl_category[32];
    int wlan0_wait_elapsed_ms = 0;
    int ctrl_wait_elapsed_ms = 0;
    int carrier_wait_elapsed_ms = 0;
    int ctrl_errno = 0;
    int link_up_errno = 0;
    int link_up_rc;
    int prepare_rc;
    int runtime_rc;
    int supplicant_process_count;
    int supplicant_start_rc = 0;
    int ctrl_ready_rc;
    int carrier_rc;
    int status_rc;
    int terminate_status = 0;
    int supplicant_root_exec_rc;
    pid_t supplicant_pid = -1;
    struct wifi_ctrl_link_info status_info;
    int existing_terminate_wait_rc = 0;
    int existing_terminate_wait_elapsed_ms = 0;
    int existing_kill_rc = 0;
    int existing_kill_wait_rc = 0;
    int existing_kill_wait_elapsed_ms = 0;
    bool spawned_supplicant = false;
    bool reusing_supplicant = false;

    a90_console_printf("[wifi connect]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_CONNECT_VERSION);
    a90_console_printf("iface=%s\r\n", A90_WIFI_IFACE);
    a90_console_printf("profile=%s\r\n",
                       profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default");
    a90_console_printf("credentials=private\r\n");
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("connect_attempted=1\r\n");
    a90_console_printf("dhcp_routing=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("wlan0_wait_timeout_ms=%d\r\n", A90_WIFI_CONNECT_WLAN0_WAIT_MS);

    if (wifi_wait_wlan0(A90_WIFI_CONNECT_WLAN0_WAIT_MS, &wlan0_wait_elapsed_ms) < 0) {
        a90_console_printf("wlan0_present=0\r\n");
        a90_console_printf("wlan0_wait_elapsed_ms=%d\r\n", wlan0_wait_elapsed_ms);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-wlan0-timeout\r\n");
        return -ETIMEDOUT;
    }
    a90_console_printf("wlan0_present=1\r\n");
    a90_console_printf("wlan0_wait_elapsed_ms=%d\r\n", wlan0_wait_elapsed_ms);

    link_up_rc = wifi_link_set_up(A90_WIFI_IFACE, &link_up_errno);
    a90_console_printf("link_up_rc=%d\r\n", link_up_rc);
    a90_console_printf("link_up_errno=%d\r\n", link_up_errno);
    if (link_up_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-link-up-failed\r\n");
        return -link_up_errno;
    }

    prepare_rc = a90_wificfg_prepare_supplicant_config(profile_name,
                                                       supplicant_config,
                                                       sizeof(supplicant_config));
    a90_console_printf("prepare_rc=%d\r\n", prepare_rc);
    a90_console_printf("supplicant_config.path=%s\r\n", A90_WIFICFG_SUPPLICANT_CONF);
    a90_console_printf("supplicant_config.present=%d\r\n",
                       access(A90_WIFICFG_SUPPLICANT_CONF, R_OK) == 0 ? 1 : 0);
    if (prepare_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-config-prepare-failed\r\n");
        return prepare_rc;
    }

    runtime_rc = wifi_prepare_runtime_dirs();
    a90_console_printf("runtime_prepare_rc=%d\r\n", runtime_rc);
    a90_console_printf("ctrl_socket.dir=%s\r\n", A90_WIFI_CTRL_DIR);
    if (runtime_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-runtime-prepare-failed\r\n");
        return runtime_rc;
    }

    a90_console_printf("supplicant.path=%s\r\n", A90_WIFI_STANDALONE_SUPPLICANT);
    a90_console_printf("supplicant.executable=%d\r\n",
                       access(A90_WIFI_STANDALONE_SUPPLICANT, X_OK) == 0 ? 1 : 0);
    supplicant_root_exec_rc = wifi_verify_root_exec_file(A90_WIFI_STANDALONE_SUPPLICANT, true);
    a90_console_printf("supplicant.root_exec_rc=%d\r\n", supplicant_root_exec_rc);
    a90_console_printf("supplicant.root_exec_ok=%d\r\n", supplicant_root_exec_rc == 0 ? 1 : 0);
    a90_console_printf("supplicant_log.path=%s\r\n", A90_WIFI_SUPPLICANT_LOG);
    if (access(A90_WIFI_STANDALONE_SUPPLICANT, X_OK) < 0) {
        int saved_errno = errno;

        a90_console_printf("supplicant_errno=%d\r\n", saved_errno);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-supplicant-missing\r\n");
        return -saved_errno;
    }
    if (supplicant_root_exec_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-supplicant-unsafe\r\n");
        return supplicant_root_exec_rc;
    }

    supplicant_process_count = wifi_count_processes_with_token("wpa_supplicant");
    a90_console_printf("supplicant.process_count_before=%d\r\n", supplicant_process_count);
    if (supplicant_process_count > 0) {
        a90_console_printf("supplicant.reuse_attempted=0\r\n");
        a90_console_printf("supplicant.existing_terminate_attempted=1\r\n");
        (void)wifi_print_ctrl_result("ctrl.terminate_existing", "TERMINATE");
        existing_terminate_wait_rc = wifi_wait_processes_gone("wpa_supplicant",
                                                              A90_WIFI_SUPPLICANT_TERMINATE_WAIT_MS,
                                                              &existing_terminate_wait_elapsed_ms);
        a90_console_printf("supplicant.existing_terminate_wait_timeout_ms=%d\r\n",
                           A90_WIFI_SUPPLICANT_TERMINATE_WAIT_MS);
        a90_console_printf("supplicant.existing_terminate_wait_rc=%d\r\n",
                           existing_terminate_wait_rc);
        a90_console_printf("supplicant.existing_terminate_wait_elapsed_ms=%d\r\n",
                           existing_terminate_wait_elapsed_ms);
        a90_console_printf("supplicant.process_count_after_terminate=%d\r\n",
                           wifi_count_processes_with_token("wpa_supplicant"));
        if (existing_terminate_wait_rc < 0) {
            a90_console_printf("supplicant.existing_kill_attempted=1\r\n");
            existing_kill_rc = wifi_signal_processes_with_token("wpa_supplicant", SIGKILL);
            a90_console_printf("supplicant.existing_kill_rc=%d\r\n", existing_kill_rc);
            existing_kill_wait_rc = wifi_wait_processes_gone("wpa_supplicant",
                                                             A90_WIFI_SUPPLICANT_KILL_WAIT_MS,
                                                             &existing_kill_wait_elapsed_ms);
            a90_console_printf("supplicant.existing_kill_wait_timeout_ms=%d\r\n",
                               A90_WIFI_SUPPLICANT_KILL_WAIT_MS);
            a90_console_printf("supplicant.existing_kill_wait_rc=%d\r\n",
                               existing_kill_wait_rc);
            a90_console_printf("supplicant.existing_kill_wait_elapsed_ms=%d\r\n",
                               existing_kill_wait_elapsed_ms);
            a90_console_printf("supplicant.process_count_after_kill=%d\r\n",
                               wifi_count_processes_with_token("wpa_supplicant"));
            if (existing_kill_rc < 0 || existing_kill_wait_rc < 0) {
                a90_console_printf("secret_values_logged=0\r\n");
                a90_console_printf("decision=wifi-connect-supplicant-terminate-timeout\r\n");
                return existing_kill_rc < 0 ? existing_kill_rc : -EBUSY;
            }
        } else {
            a90_console_printf("supplicant.existing_kill_attempted=0\r\n");
        }
    } else {
        a90_console_printf("supplicant.reuse_attempted=0\r\n");
        a90_console_printf("supplicant.existing_terminate_attempted=0\r\n");
        a90_console_printf("supplicant.existing_kill_attempted=0\r\n");
    }
    (void)unlink(A90_WIFI_CTRL_SOCKET);
    (void)unlink(A90_WIFI_SUPPLICANT_LOG);
    supplicant_start_rc = wifi_start_supplicant(&supplicant_pid);
    a90_console_printf("supplicant_start_rc=%d\r\n", supplicant_start_rc);
    a90_console_printf("supplicant_pid=%ld\r\n", supplicant_start_rc == 0 ? (long)supplicant_pid : -1L);
    if (supplicant_start_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-supplicant-start-failed\r\n");
        return supplicant_start_rc;
    }
    spawned_supplicant = true;
    ctrl_ready_rc = wifi_wait_ctrl_ready(supplicant_pid,
                                         true,
                                         A90_WIFI_CONNECT_CTRL_WAIT_MS,
                                         &ctrl_wait_elapsed_ms,
                                         ctrl_category,
                                         sizeof(ctrl_category),
                                         &ctrl_errno);
    a90_console_printf("ctrl_wait_timeout_ms=%d\r\n", A90_WIFI_CONNECT_CTRL_WAIT_MS);
    a90_console_printf("ctrl_wait_elapsed_ms=%d\r\n", ctrl_wait_elapsed_ms);
    a90_console_printf("ctrl_ping_rc=%d\r\n", ctrl_ready_rc);
    a90_console_printf("ctrl_ping_errno=%d\r\n", ctrl_errno);
    a90_console_printf("ctrl_ping.reply_category=%s\r\n",
                       ctrl_ready_rc == 0 ? ctrl_category : "error");
    if (ctrl_ready_rc < 0) {
        (void)a90_run_stop_pid_ex(supplicant_pid,
                                  "wifi-supplicant",
                                  3000,
                                  true,
                                  &terminate_status);
        a90_console_printf("supplicant_cleanup_status=%d\r\n", terminate_status);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-ctrl-timeout\r\n");
        return ctrl_ready_rc;
    }

    (void)wifi_print_ctrl_result("ctrl.driver_country", "DRIVER COUNTRY KR");
    (void)wifi_print_ctrl_result("ctrl.scan", "SCAN");
    (void)wifi_print_ctrl_result("ctrl.enable_network", "ENABLE_NETWORK 0");
    (void)wifi_print_ctrl_result("ctrl.select_network", "SELECT_NETWORK 0");
    (void)wifi_print_ctrl_result("ctrl.reassociate", "REASSOCIATE");

    if (carrier_wait_timeout_ms <= 0) {
        carrier_wait_timeout_ms = A90_WIFI_CONNECT_CARRIER_WAIT_MS;
    }
    a90_console_printf("carrier_wait_timeout_ms=%d\r\n", carrier_wait_timeout_ms);
    carrier_rc = wifi_wait_carrier(carrier_wait_timeout_ms, &carrier_wait_elapsed_ms);
    a90_console_printf("carrier_wait_rc=%d\r\n", carrier_rc);
    a90_console_printf("carrier_wait_elapsed_ms=%d\r\n", carrier_wait_elapsed_ms);
    a90_console_printf("carrier_up=%d\r\n", carrier_rc == 0 ? 1 : 0);
    status_rc = wifi_print_ctrl_result("ctrl.status", "STATUS");
    wifi_collect_ctrl_link_info(&status_info);
    a90_console_printf("ctrl.status_confirm.rc=%d\r\n", status_info.status_rc);
    a90_console_printf("ctrl.status_confirm.errno=%d\r\n", status_info.status_errno);
    a90_console_printf("ctrl.status_confirm.field.wpa_state=%s\r\n",
                       status_info.wpa_state[0] != '\0' ? status_info.wpa_state : "-");
    a90_console_printf("ctrl.status_confirm.field.freq=%s\r\n",
                       status_info.freq_mhz[0] != '\0' ? status_info.freq_mhz : "-");
    a90_console_printf("ctrl.status_confirm.completed=%d\r\n",
                       strcmp(status_info.wpa_state, "COMPLETED") == 0 ? 1 : 0);
    a90_console_printf("supplicant.reused=%d\r\n", reusing_supplicant ? 1 : 0);
    a90_console_printf("supplicant.spawned=%d\r\n", spawned_supplicant ? 1 : 0);
    a90_console_printf("supplicant.left_running=%d\r\n",
                       carrier_rc == 0 && strcmp(status_info.wpa_state, "COMPLETED") == 0 ? 1 : 0);
    a90_console_printf("status_request_rc=%d\r\n", status_rc);
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("dhcp_routing=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");

    if (carrier_rc == 0 && strcmp(status_info.wpa_state, "COMPLETED") == 0) {
        a90_logf("wifi",
                 "connect profile=%s carrier=1 wpa_state=COMPLETED reused=%d spawned=%d secret_values_logged=0",
                 profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
                 reusing_supplicant ? 1 : 0,
                 spawned_supplicant ? 1 : 0);
        a90_console_printf("decision=wifi-connect-carrier-up\r\n");
        return 0;
    }

    if (carrier_rc == 0) {
        (void)wifi_print_ctrl_result("ctrl.terminate", "TERMINATE");
        (void)a90_run_stop_pid_ex(supplicant_pid,
                                  "wifi-supplicant",
                                  3000,
                                  true,
                                  &terminate_status);
        a90_console_printf("supplicant_cleanup_status=%d\r\n", terminate_status);
        a90_logf("wifi",
                 "connect profile=%s carrier=1 wpa_state=%s reused=%d spawned=%d secret_values_logged=0",
                 profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
                 status_info.wpa_state[0] != '\0' ? status_info.wpa_state : "-",
                 reusing_supplicant ? 1 : 0,
                 spawned_supplicant ? 1 : 0);
        a90_console_printf("decision=wifi-connect-status-not-completed\r\n");
        return -ENOTCONN;
    }

    if (spawned_supplicant) {
        (void)wifi_print_ctrl_result("ctrl.terminate", "TERMINATE");
        (void)a90_run_stop_pid_ex(supplicant_pid,
                                  "wifi-supplicant",
                                  3000,
                                  true,
                                  &terminate_status);
        a90_console_printf("supplicant_cleanup_status=%d\r\n", terminate_status);
    }
    a90_logf("wifi",
             "connect profile=%s carrier=0 reused=%d spawned=%d secret_values_logged=0",
             profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
             reusing_supplicant ? 1 : 0,
             spawned_supplicant ? 1 : 0);
    a90_console_printf("decision=wifi-connect-no-carrier\r\n");
    return carrier_rc;
}

int a90_wifi_connect_profile(const char *profile_name) {
    return wifi_connect_profile_with_carrier_timeout(profile_name, A90_WIFI_CONNECT_CARRIER_WAIT_MS);
}

static int wifi_write_autoconnect_result(const char *decision,
                                         const char *profile,
                                         int connect_rc,
                                         int dhcp_rc,
                                         int final_rc) {
    char text[1024];
    int len;

    len = snprintf(text,
                   sizeof(text),
                   "version=a90-native-wifi-autoconnect-v1\n"
                   "decision=%s\n"
                   "profile=%s\n"
                   "connect_rc=%d\n"
                   "dhcp_rc=%d\n"
                   "final_rc=%d\n"
                   "carrier_up=%d\n"
                   "default_route_present=%d\n"
                   "nameserver_count=%d\n"
                   "secret_values_logged=0\n",
                   decision != NULL ? decision : "wifi-autoconnect-unknown",
                   profile != NULL && profile[0] != '\0' ? profile : "default",
                   connect_rc,
                   dhcp_rc,
                   final_rc,
                   wifi_carrier_up() ? 1 : 0,
                   wifi_default_route_present() ? 1 : 0,
                   wifi_count_resolv_nameservers());
    if (len < 0 || (size_t)len >= sizeof(text)) {
        return -ENOSPC;
    }
    return wifi_write_text_file(A90_WIFI_AUTOCONNECT_RESULT, text, 0600);
}

static void wifi_write_autoconnect_inactive_state(const char *decision,
                                                  const char *profile,
                                                  bool boot_background,
                                                  int final_rc) {
    const char *selected_decision = decision != NULL && decision[0] != '\0' ?
        decision : "wifi-autoconnect-disabled";

    (void)wifi_prepare_runtime_dirs();
    wifi_reset_autoconnect_log(profile, boot_background);
    (void)wifi_write_autoconnect_result(selected_decision, profile, 0, 0, final_rc);
    (void)wifi_write_runtime_summary(selected_decision);
}

static int wifi_run_autoconnect_sequence(const char *profile_name, bool boot_background) {
    struct a90_wificfg_autoconnect config;
    int config_rc;
    int scan_rc = 0;
    int connect_rc = -ENOTCONN;
    int dhcp_rc = 0;
    int final_rc;
    int attempt;
    int attempts;
    int carrier_wait_timeout_ms;
    int wlan0_wait_elapsed_ms = 0;
    const char *selected_profile;

    config_rc = a90_wificfg_get_autoconnect(&config, profile_name);
    selected_profile = config.profile[0] != '\0' ? config.profile : profile_name;
    attempts = config.retry_count > 0 ? config.retry_count + 1 : 1;
    carrier_wait_timeout_ms = config.connect_timeout_sec > 0 ?
        config.connect_timeout_sec * 1000 : A90_WIFI_CONNECT_CARRIER_WAIT_MS;
    wifi_reset_autoconnect_log(selected_profile, boot_background);
    if (!boot_background) {
        a90_console_printf("[wifi autoconnect once]\r\n");
        a90_console_printf("profile=%s\r\n",
                           selected_profile != NULL && selected_profile[0] != '\0' ?
                           selected_profile : "default");
        a90_console_printf("config_rc=%d\r\n", config_rc);
        a90_console_printf("config_decision=%s\r\n", config.decision);
        a90_console_printf("dhcp=%d\r\n", config.dhcp);
        a90_console_printf("scan_before_connect=%d\r\n", config.scan_before_connect);
        a90_console_printf("retry_count=%d\r\n", config.retry_count);
        a90_console_printf("external_ping=0\r\n");
        a90_console_printf("secret_values_logged=0\r\n");
    }
    if (config_rc < 0) {
        (void)wifi_write_autoconnect_result(config.decision, selected_profile, config_rc, 0, config_rc);
        (void)wifi_write_runtime_summary(config.decision);
        if (!boot_background) {
            a90_console_printf("decision=%s\r\n", config.decision);
        }
        return config_rc;
    }
    if (config.external_ping != 0) {
        (void)wifi_write_autoconnect_result("wifi-autoconnect-external-ping-blocked",
                                            selected_profile,
                                            -EACCES,
                                            0,
                                            -EACCES);
        (void)wifi_write_runtime_summary("wifi-autoconnect-external-ping-blocked");
        if (!boot_background) {
            a90_console_printf("decision=wifi-autoconnect-external-ping-blocked\r\n");
        }
        return -EACCES;
    }

    (void)wifi_write_autoconnect_result("wifi-autoconnect-running",
                                        selected_profile,
                                        -EINPROGRESS,
                                        0,
                                        -EINPROGRESS);
    (void)wifi_write_runtime_summary("wifi-autoconnect-running");
    wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                          "event=start profile=%s attempts=%d boot_background=%d secret_values_logged=0\n",
                          selected_profile != NULL && selected_profile[0] != '\0' ? selected_profile : "default",
                          attempts,
                          boot_background ? 1 : 0);
    if (config.scan_before_connect) {
        if (wifi_wait_wlan0(A90_WIFI_CONNECT_WLAN0_WAIT_MS, &wlan0_wait_elapsed_ms) < 0) {
            wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                                  "event=wlan0-timeout profile=%s elapsed_ms=%d\n",
                                  selected_profile != NULL && selected_profile[0] != '\0' ?
                                  selected_profile : "default",
                                  wlan0_wait_elapsed_ms);
            (void)wifi_write_autoconnect_result("wifi-autoconnect-wlan0-timeout",
                                                selected_profile,
                                                -ETIMEDOUT,
                                                0,
                                                -ETIMEDOUT);
            (void)wifi_write_runtime_summary("wifi-autoconnect-wlan0-timeout");
            if (!boot_background) {
                a90_console_printf("autoconnect.wlan0_wait_timeout_ms=%d\r\n",
                                   A90_WIFI_CONNECT_WLAN0_WAIT_MS);
                a90_console_printf("autoconnect.wlan0_wait_elapsed_ms=%d\r\n",
                                   wlan0_wait_elapsed_ms);
                a90_console_printf("decision=wifi-autoconnect-wlan0-timeout\r\n");
            }
            return -ETIMEDOUT;
        }
        if (!boot_background) {
            a90_console_printf("autoconnect.wlan0_wait_timeout_ms=%d\r\n",
                               A90_WIFI_CONNECT_WLAN0_WAIT_MS);
            a90_console_printf("autoconnect.wlan0_wait_elapsed_ms=%d\r\n",
                               wlan0_wait_elapsed_ms);
        }
    }
    for (attempt = 1; attempt <= attempts; attempt++) {
        wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                              "event=attempt profile=%s attempt=%d attempts=%d\n",
                              selected_profile != NULL && selected_profile[0] != '\0' ? selected_profile : "default",
                              attempt,
                              attempts);
        if (config.scan_before_connect) {
            scan_rc = a90_wifi_scan_once(5000);
            if (!boot_background) {
                a90_console_printf("autoconnect.scan_rc=%d\r\n", scan_rc);
            }
            if (scan_rc < 0) {
                wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                                      "event=scan-failed profile=%s attempt=%d rc=%d\n",
                                      selected_profile != NULL && selected_profile[0] != '\0' ?
                                      selected_profile : "default",
                                      attempt,
                                      scan_rc);
                if (attempt < attempts) {
                    (void)a90_wifi_cleanup();
                    continue;
                }
                (void)wifi_write_autoconnect_result("wifi-autoconnect-scan-failed",
                                                    selected_profile,
                                                    scan_rc,
                                                    0,
                                                    scan_rc);
                (void)wifi_write_runtime_summary("wifi-autoconnect-scan-failed");
                if (!boot_background) {
                    a90_console_printf("decision=wifi-autoconnect-scan-failed\r\n");
                }
                return scan_rc;
            }
        }

        connect_rc = wifi_connect_profile_with_carrier_timeout(selected_profile, carrier_wait_timeout_ms);
        if (connect_rc >= 0) {
            break;
        }
        wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                              "event=connect-failed profile=%s attempt=%d rc=%d\n",
                              selected_profile != NULL && selected_profile[0] != '\0' ? selected_profile : "default",
                              attempt,
                              connect_rc);
        if (attempt < attempts) {
            (void)a90_wifi_cleanup();
            continue;
        }
        (void)wifi_write_autoconnect_result("wifi-autoconnect-connect-failed",
                                            selected_profile,
                                            connect_rc,
                                            0,
                                            connect_rc);
        (void)wifi_write_runtime_summary("wifi-autoconnect-connect-failed");
        if (!boot_background) {
            a90_console_printf("decision=wifi-autoconnect-connect-failed\r\n");
        }
        return connect_rc;
    }

    if (config.dhcp) {
        dhcp_rc = a90_wifi_dhcp_profile(selected_profile);
    }
    final_rc = dhcp_rc < 0 ? dhcp_rc : 0;
    (void)wifi_write_autoconnect_result(final_rc == 0 ? "wifi-autoconnect-pass" : "wifi-autoconnect-dhcp-failed",
                                        selected_profile,
                                        connect_rc,
                                        dhcp_rc,
                                        final_rc);
    (void)wifi_write_runtime_summary(final_rc == 0 ? "wifi-autoconnect-pass" : "wifi-autoconnect-dhcp-failed");
    if (!boot_background) {
        a90_console_printf("autoconnect.connect_rc=%d\r\n", connect_rc);
        a90_console_printf("autoconnect.dhcp_rc=%d\r\n", dhcp_rc);
        a90_console_printf("autoconnect.scan_rc=%d\r\n", scan_rc);
        a90_console_printf("autoconnect.attempts=%d\r\n", attempt);
        a90_console_printf("decision=%s\r\n",
                           final_rc == 0 ? "wifi-autoconnect-pass" : "wifi-autoconnect-dhcp-failed");
    }
    wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                          "event=%s profile=%s attempt=%d connect_rc=%d dhcp_rc=%d final_rc=%d\n",
                          final_rc == 0 ? "success" : "dhcp-failed",
                          selected_profile != NULL && selected_profile[0] != '\0' ? selected_profile : "default",
                          attempt,
                          connect_rc,
                          dhcp_rc,
                          final_rc);
    a90_logf("wifi",
             "autoconnect profile=%s connect_rc=%d dhcp_rc=%d final_rc=%d secret_values_logged=0",
             selected_profile != NULL && selected_profile[0] != '\0' ? selected_profile : "default",
             connect_rc,
             dhcp_rc,
             final_rc);
    return final_rc;
}

static int wifi_print_autoconnect_set_result(bool enabled, const char *profile_name) {
    int rc = a90_wificfg_set_autoconnect(enabled, profile_name);

    a90_console_printf("[wifi autoconnect %s]\r\n", enabled ? "enable" : "disable");
    a90_console_printf("profile=%s\r\n",
                       profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default");
    a90_console_printf("set_rc=%d\r\n", rc);
    a90_console_printf("secret_values_logged=0\r\n");
    if (rc == 0) {
        if (!enabled) {
            wifi_write_autoconnect_inactive_state("wifi-autoconnect-disabled",
                                                  profile_name,
                                                  false,
                                                  0);
        }
        a90_console_printf("decision=%s\r\n",
                           enabled ? "wifi-autoconnect-enabled" : "wifi-autoconnect-disabled");
        return 0;
    }
    a90_console_printf("decision=%s\r\n",
                       enabled ? "wifi-autoconnect-enable-failed" : "wifi-autoconnect-disable-failed");
    return rc;
}

int a90_wifi_start_boot_autoconnect_once(void) {
    struct a90_wificfg_autoconnect config;
    char pid_text[64];
    int config_rc;
    pid_t pid;

    config_rc = a90_wificfg_get_autoconnect(&config, NULL);
    if (config_rc < 0) {
        wifi_write_autoconnect_inactive_state(config.decision,
                                              config.profile,
                                              true,
                                              strcmp(config.decision, "wifi-autoconnect-no-config") == 0 ||
                                              strcmp(config.decision, "wifi-autoconnect-disabled") == 0 ? 0 : config_rc);
        a90_logf("wifi", "boot autoconnect inactive decision=%s", config.decision);
        return 0;
    }
    if (!config.enabled) {
        wifi_write_autoconnect_inactive_state("wifi-autoconnect-disabled",
                                              config.profile,
                                              true,
                                              0);
        return 0;
    }

    if (wifi_prepare_runtime_dirs() < 0) {
        return negative_errno_or(EIO);
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        (void)wifi_write_autoconnect_result("wifi-autoconnect-fork-failed",
                                            config.profile,
                                            -saved_errno,
                                            0,
                                            -saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        int rc;

        a90_console_silence_child();
        (void)setsid();
        rc = wifi_run_autoconnect_sequence(config.profile, true);
        _exit(rc == 0 ? 0 : 1);
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)wifi_write_text_file(A90_WIFI_AUTOCONNECT_PID, pid_text, 0600);
    a90_logf("wifi", "boot autoconnect started pid=%ld profile=%s", (long)pid, config.profile);
    return 0;
}

static int wifi_parse_delay_ms_max(const char *text, int *delay_ms, long max_ms) {
    char *end = NULL;
    long value;

    if (text == NULL || delay_ms == NULL) {
        return -EINVAL;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 0 || value > max_ms) {
        return -EINVAL;
    }
    *delay_ms = (int)value;
    return 0;
}

static int wifi_parse_delay_ms(const char *text, int *delay_ms) {
    return wifi_parse_delay_ms_max(text, delay_ms, 30000);
}

static const char *wifi_softap_decision_for(const char *subcommand,
                                            enum a90_wififeas_decision decision) {
    bool prepare = subcommand != NULL && strcmp(subcommand, "prepare") == 0;

    if (decision == A90_WIFI_FEAS_BASELINE_REQUIRED) {
        return prepare ?
               "softap-prepare-baseline-required" :
               "softap-status-baseline-required";
    }
    if (decision == A90_WIFI_FEAS_GO_READ_ONLY_ONLY) {
        return prepare ?
               "softap-prepare-start-not-implemented" :
               "softap-status-prereq-visible-start-not-implemented";
    }
    return prepare ?
           "softap-prepare-blocked-wlan-gate" :
           "softap-status-blocked-wlan-gate";
}

static int wifi_softap_print_surface(const char *subcommand) {
    struct a90_wififeas_result feasibility;
    char busybox_kind[32];
    int feasibility_rc;
    int busybox_rc;
    bool include_plan = subcommand != NULL && strcmp(subcommand, "status") != 0;
    bool prepare = subcommand != NULL && strcmp(subcommand, "prepare") == 0;

    feasibility_rc = a90_wififeas_evaluate(&feasibility);
    if (feasibility_rc < 0) {
        return feasibility_rc;
    }

    busybox_rc = wifi_path_kind("/cache/bin/busybox", true, busybox_kind, sizeof(busybox_kind));

    a90_console_printf("[wifi softap %s]\r\n", subcommand != NULL ? subcommand : "status");
    a90_console_printf("version=%s\r\n", A90_WIFI_SOFTAP_VERSION);
    a90_console_printf("scope=read-only-status-plan-no-ap-start\r\n");
    a90_console_printf("runtime_root=%s\r\n", A90_WIFI_SOFTAP_ROOT);
    a90_console_printf("ssid_psk_logged=0\r\n");
    a90_console_printf("config_write_attempted=0\r\n");
    a90_console_printf("hostapd_start_attempted=0\r\n");
    a90_console_printf("dhcp_server_start_attempted=0\r\n");
    a90_console_printf("listener_start_attempted=0\r\n");
    a90_console_printf("interface_mode_change_attempted=0\r\n");
    a90_console_printf("address_assign_attempted=0\r\n");
    a90_console_printf("server_exposure_attempted=0\r\n");
    a90_console_printf("start_supported=0\r\n");
    a90_console_printf("start_allowed=0\r\n");
    a90_console_printf("prepare_dry_run=%d\r\n", prepare ? 1 : 0);
    a90_console_printf("busybox.kind=%s\r\n", busybox_kind[0] != '\0' ? busybox_kind : "unknown");
    a90_console_printf("busybox.executable=%d\r\n", busybox_rc == 0 ? 1 : 0);
    a90_console_printf("wififeas.decision=%s\r\n",
                       a90_wififeas_decision_name(feasibility.decision));
    a90_console_printf("wififeas.reason=%s\r\n", feasibility.reason);
    a90_console_printf("wififeas.next=%s\r\n", feasibility.next_step);
    a90_console_printf("gates.wlan=%d\r\n", feasibility.has_wlan_iface ? 1 : 0);
    a90_console_printf("gates.rfkill=%d\r\n", feasibility.has_wifi_rfkill ? 1 : 0);
    a90_console_printf("gates.module=%d\r\n", feasibility.has_driver_module ? 1 : 0);
    a90_console_printf("gates.candidates=%d\r\n", feasibility.has_candidate_files ? 1 : 0);
    a90_console_printf("inventory.net_total=%d\r\n", feasibility.inventory.net_total);
    a90_console_printf("inventory.wlan_like=%d\r\n", feasibility.inventory.wlan_ifaces);
    a90_console_printf("inventory.rfkill_wifi=%d\r\n", feasibility.inventory.rfkill_wifi);
    a90_console_printf("inventory.module_matches=%d\r\n", feasibility.inventory.module_matches);
    a90_console_printf("inventory.file_matches=%d\r\n", feasibility.inventory.file_matches);
    if (include_plan) {
        a90_console_printf("plan.s0=charter-done\r\n");
        a90_console_printf("plan.s1=readonly-inventory-done\r\n");
        a90_console_printf("plan.s2=status-plan-prepare-no-start\r\n");
        a90_console_printf("plan.s3=blocked-until-wlan-ap-prereq-visible\r\n");
        a90_console_printf("plan.s4=blocked-until-ap-and-server-start-pass\r\n");
    }
    a90_console_printf("decision=%s\r\n",
                       wifi_softap_decision_for(subcommand, feasibility.decision));
    a90_logf("wifi-softap",
             "sub=%s decision=%s wlan=%d rfkill=%d modules=%d candidates=%d",
             subcommand != NULL ? subcommand : "status",
             wifi_softap_decision_for(subcommand, feasibility.decision),
             feasibility.inventory.wlan_ifaces,
             feasibility.inventory.rfkill_wifi,
             feasibility.inventory.module_matches,
             feasibility.inventory.file_matches);
    return 0;
}

static int wifi_softap_cmd(char **argv, int argc) {
    const char *subcommand = argc > 2 ? argv[2] : "status";

    if (argc < 2 || argc > 4) {
        a90_console_printf("usage: wifi softap [status|plan|prepare [profile]|cleanup]\r\n");
        return -EINVAL;
    }
    if (strcmp(subcommand, "status") == 0 && (argc == 2 || argc == 3)) {
        return wifi_softap_print_surface("status");
    }
    if (strcmp(subcommand, "plan") == 0 && argc == 3) {
        return wifi_softap_print_surface("plan");
    }
    if (strcmp(subcommand, "prepare") == 0 && (argc == 3 || argc == 4)) {
        (void)argv;
        return wifi_softap_print_surface("prepare");
    }
    if (strcmp(subcommand, "cleanup") == 0 && argc == 3) {
        return wifi_softap_print_surface("cleanup");
    }

    a90_console_printf("usage: wifi softap [status|plan|prepare [profile]|cleanup]\r\n");
    return -EINVAL;
}

int a90_wifi_cmd(char **argv, int argc) {
    if (argc == 1 ||
        (argc == 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "status") == 0)) {
        return a90_wifi_print_status();
    }
    if (argc >= 2 &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "softap") == 0) {
        return wifi_softap_cmd(argv, argc);
    }
    if ((argc == 2 || argc == 3) &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "scan") == 0) {
        int delay_ms = 5000;

        if (argc == 3 && wifi_parse_delay_ms(argv[2], &delay_ms) < 0) {
            a90_console_printf("usage: wifi scan [delay_ms]\r\n");
            return -EINVAL;
        }
        return a90_wifi_scan_once(delay_ms);
    }
    if ((argc == 2 || argc == 3) &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "events") == 0) {
        int timeout_ms = A90_WIFI_NL80211_EVENT_DEFAULT_MS;

        if (argc == 3 && wifi_parse_delay_ms(argv[2], &timeout_ms) < 0) {
            a90_console_printf("usage: wifi events [timeout_ms]\r\n");
            return -EINVAL;
        }
        return a90_wifi_events_once(timeout_ms);
    }
    if ((argc == 2 || argc == 3) &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "netevents") == 0) {
        int timeout_ms = A90_WIFI_NETEVENT_DEFAULT_MS;

        if (argc == 3 && wifi_parse_delay_ms(argv[2], &timeout_ms) < 0) {
            a90_console_printf("usage: wifi netevents [timeout_ms]\r\n");
            return -EINVAL;
        }
        return a90_wifi_netevents_once(timeout_ms);
    }
    if ((argc == 2 || argc == 3) &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "connect") == 0) {
        return a90_wifi_connect_profile(argc == 3 ? argv[2] : NULL);
    }
    if ((argc >= 2 && argc <= 4) &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "connect-event") == 0) {
        int timeout_ms = A90_WIFI_CONNECT_EVENT_DEFAULT_MS;

        if (argc == 4 &&
            wifi_parse_delay_ms_max(argv[3], &timeout_ms, A90_WIFI_CONNECT_EVENT_MAX_MS) < 0) {
            a90_console_printf("usage: wifi connect-event [profile] [timeout_ms]\r\n");
            return -EINVAL;
        }
        return a90_wifi_connect_event_once(argc >= 3 ? argv[2] : NULL, timeout_ms);
    }
    if ((argc == 2 || argc == 3) &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "dhcp") == 0) {
        return a90_wifi_dhcp_profile(argc == 3 ? argv[2] : NULL);
    }
    if ((argc == 2 || argc == 3) &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "ping") == 0) {
        return a90_wifi_ping_once(argc == 3 ? argv[2] : "all");
    }
    if (argc == 2 &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "cleanup") == 0) {
        return a90_wifi_cleanup();
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "profile") == 0) {
        if (argc == 3 && strcmp(argv[2], "list") == 0) {
            return a90_wificfg_print_profile_list();
        }
        if ((argc == 3 || argc == 4) && strcmp(argv[2], "status") == 0) {
            return a90_wificfg_print_profile_status(argc == 4 ? argv[3] : NULL);
        }
        a90_console_printf("usage: wifi profile [list|status [profile]]\r\n");
        return -EINVAL;
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "autoconnect") == 0) {
        if (argc == 3 && strcmp(argv[2], "status") == 0) {
            return a90_wificfg_print_autoconnect_status();
        }
        if ((argc == 3 || argc == 4) && strcmp(argv[2], "enable") == 0) {
            return wifi_print_autoconnect_set_result(true, argc == 4 ? argv[3] : NULL);
        }
        if (argc == 3 && strcmp(argv[2], "disable") == 0) {
            return wifi_print_autoconnect_set_result(false, NULL);
        }
        if ((argc == 3 || argc == 4) && strcmp(argv[2], "once") == 0) {
            return wifi_run_autoconnect_sequence(argc == 4 ? argv[3] : NULL, false);
        }
        a90_console_printf("usage: wifi autoconnect [status|enable [profile]|disable|once [profile]]\r\n");
        return -EINVAL;
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "config") == 0) {
        return a90_wificfg_cmd(argv, argc);
    }

    a90_console_printf("usage: wifi [status|scan [delay_ms]|events [timeout_ms]|netevents [timeout_ms]|connect [profile]|dhcp [profile]|ping [gateway|internet|all]|cleanup|softap [status|plan|prepare [profile]|cleanup]|profile [list|status [profile]]|autoconnect [status|enable [profile]|disable|once [profile]]|config [status|prepare [profile]]]\r\n");
    return -EINVAL;
}
