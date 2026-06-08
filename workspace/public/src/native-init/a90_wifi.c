#include "a90_wifi.h"

#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/genetlink.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <net/if.h>
#include <poll.h>
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

#define A90_WIFI_IFACE "wlan0"
#define A90_WIFI_RUNTIME_SUMMARY "/cache/native-init-wifi-runtime.summary"
#define A90_WIFI_RUNTIME_INPUT "/cache/native-init-wifi-runtime-input.summary"
#define A90_WIFI_STANDALONE_SUPPLICANT "/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh"
#define A90_WIFI_RUNTIME_ROOT "/cache/a90-wifi"
#define A90_WIFI_CTRL_DIR "/cache/a90-wifi/sockets"
#define A90_WIFI_CTRL_SOCKET "/cache/a90-wifi/sockets/wlan0"
#define A90_WIFI_SUPPLICANT_LOG "/cache/a90-wifi/wpa_supplicant-connect.log"
#define A90_WIFI_SCAN_RECV_SIZE 65536
#define A90_WIFI_SCAN_VERSION "a90-native-wifi-scan-v1"
#define A90_WIFI_CONNECT_VERSION "a90-native-wifi-connect-v1"
#define A90_WIFI_UID 1010
#define A90_WIFI_GID 1010
#define A90_WIFI_CONNECT_WLAN0_WAIT_MS 180000
#define A90_WIFI_CONNECT_CTRL_WAIT_MS 15000
#define A90_WIFI_CONNECT_CARRIER_WAIT_MS 35000

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
    if (ensure_dir(A90_WIFI_RUNTIME_ROOT, 0700) < 0 ||
        ensure_dir(A90_WIFI_CTRL_DIR, 0770) < 0) {
        return negative_errno_or(EIO);
    }
    if (chown(A90_WIFI_RUNTIME_ROOT, A90_WIFI_UID, A90_WIFI_GID) < 0 ||
        chown(A90_WIFI_CTRL_DIR, A90_WIFI_UID, A90_WIFI_GID) < 0 ||
        chmod(A90_WIFI_CTRL_DIR, 0770) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
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

static char wifi_status_value_char(char value) {
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

static void wifi_runtime_value(const char *key, char *out, size_t out_size) {
    char text[1024];
    char *cursor;
    size_t key_len;

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "-");
    if (read_text_file(A90_WIFI_RUNTIME_SUMMARY, text, sizeof(text)) < 0) {
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

int a90_wifi_print_status(void) {
    char iface_path[128];
    char address[80];
    char operstate[80];
    char carrier[32];
    char flags[32];
    char rx_bytes[64];
    char tx_bytes[64];
    char ipv4[64];
    char kind[32];
    char runtime_wlan0[32];
    char runtime_mac[80];
    char runtime_ip[80];
    char runtime_ssid_label[96];
    char runtime_rssi[32];
    char runtime_linkspeed[32];
    int supplicant_process_count;
    int ipv4_rc;
    bool wlan0_present;

    snprintf(iface_path, sizeof(iface_path), "/sys/class/net/%s", A90_WIFI_IFACE);
    wlan0_present = access(iface_path, F_OK) == 0;
    wifi_read_attr(iface_path, "address", address, sizeof(address));
    wifi_read_attr(iface_path, "operstate", operstate, sizeof(operstate));
    wifi_read_attr(iface_path, "carrier", carrier, sizeof(carrier));
    wifi_read_attr(iface_path, "flags", flags, sizeof(flags));
    wifi_read_attr(iface_path, "statistics/rx_bytes", rx_bytes, sizeof(rx_bytes));
    wifi_read_attr(iface_path, "statistics/tx_bytes", tx_bytes, sizeof(tx_bytes));
    ipv4_rc = wifi_ipv4_addr(A90_WIFI_IFACE, ipv4, sizeof(ipv4));
    supplicant_process_count = wifi_count_processes_with_token("wpa_supplicant");
    wifi_runtime_value("wlan0_present=", runtime_wlan0, sizeof(runtime_wlan0));
    wifi_runtime_value("mac=", runtime_mac, sizeof(runtime_mac));
    wifi_runtime_value("ipv4=", runtime_ip, sizeof(runtime_ip));
    wifi_runtime_value("ssid_label=", runtime_ssid_label, sizeof(runtime_ssid_label));
    wifi_runtime_value("rssi_dbm=", runtime_rssi, sizeof(runtime_rssi));
    wifi_runtime_value("linkspeed_mbps=", runtime_linkspeed, sizeof(runtime_linkspeed));

    a90_console_printf("[wifi status]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SCAN_VERSION);
    a90_console_printf("iface=%s\r\n", A90_WIFI_IFACE);
    a90_console_printf("wlan0_present=%d\r\n", wlan0_present ? 1 : 0);
    a90_console_printf("mac=%s\r\n", address);
    a90_console_printf("operstate=%s\r\n", operstate);
    a90_console_printf("carrier=%s\r\n", carrier);
    a90_console_printf("flags=%s\r\n", flags);
    a90_console_printf("rx_bytes=%s\r\n", rx_bytes);
    a90_console_printf("tx_bytes=%s\r\n", tx_bytes);
    a90_console_printf("ipv4=%s\r\n", ipv4_rc == 0 ? ipv4 : "-");
    a90_console_printf("ipv4_rc=%d\r\n", ipv4_rc);
    a90_console_printf("runtime_summary.path=%s\r\n", A90_WIFI_RUNTIME_SUMMARY);
    a90_console_printf("runtime_summary.present=%d\r\n", access(A90_WIFI_RUNTIME_SUMMARY, R_OK) == 0 ? 1 : 0);
    a90_console_printf("runtime_input.path=%s\r\n", A90_WIFI_RUNTIME_INPUT);
    a90_console_printf("runtime_input.present=%d\r\n", access(A90_WIFI_RUNTIME_INPUT, R_OK) == 0 ? 1 : 0);
    a90_console_printf("runtime.wlan0_present=%s\r\n", runtime_wlan0);
    a90_console_printf("runtime.mac=%s\r\n", runtime_mac);
    a90_console_printf("runtime.ipv4=%s\r\n", runtime_ip);
    a90_console_printf("runtime.ssid_label=%s\r\n", runtime_ssid_label);
    a90_console_printf("runtime.rssi_dbm=%s\r\n", runtime_rssi);
    a90_console_printf("runtime.linkspeed_mbps=%s\r\n", runtime_linkspeed);
    a90_console_printf("supplicant.provider=standalone\r\n");
    a90_console_printf("supplicant.path=%s\r\n", A90_WIFI_STANDALONE_SUPPLICANT);
    a90_console_printf("supplicant.kind=%s\r\n",
                       wifi_path_kind(A90_WIFI_STANDALONE_SUPPLICANT, false, kind, sizeof(kind)) == 0 ? kind : kind);
    a90_console_printf("supplicant.executable=%d\r\n", access(A90_WIFI_STANDALONE_SUPPLICANT, X_OK) == 0 ? 1 : 0);
    a90_console_printf("supplicant.process_count=%d\r\n", supplicant_process_count);
    a90_console_printf("ctrl_socket.path=%s\r\n", A90_WIFI_CTRL_SOCKET);
    a90_console_printf("ctrl_socket.kind=%s\r\n",
                       wifi_path_kind(A90_WIFI_CTRL_SOCKET, false, kind, sizeof(kind)) == 0 ? kind : kind);
    a90_console_printf("supplicant_config.path=%s\r\n", A90_WIFICFG_SUPPLICANT_CONF);
    a90_console_printf("supplicant_config.present=%d\r\n", access(A90_WIFICFG_SUPPLICANT_CONF, R_OK) == 0 ? 1 : 0);
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("decision=%s\r\n", wlan0_present ? "wifi-status-wlan0-present" : "wifi-status-wlan0-missing");
    a90_logf("wifi", "status wlan0=%d operstate=%s carrier=%s supplicant_count=%d",
             wlan0_present ? 1 : 0,
             operstate,
             carrier,
             supplicant_process_count);
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

static int wifi_dump_scan_count(int socket_fd, int family_id, uint32_t ifindex, int *scan_count) {
    char buffer[A90_WIFI_SCAN_RECV_SIZE];
    const uint32_t seq = 3;
    bool done = false;

    *scan_count = 0;
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
                ++(*scan_count);
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

int a90_wifi_scan_once(int delay_ms) {
    unsigned int ifindex;
    int socket_fd;
    int family_id;
    int scan_count = 0;
    int saved_errno = 0;
    int link_up_rc;

    if (delay_ms < 0) {
        delay_ms = 0;
    }
    if (delay_ms > 30000) {
        delay_ms = 30000;
    }

    a90_console_printf("[wifi scan]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SCAN_VERSION);
    a90_console_printf("iface=%s\r\n", A90_WIFI_IFACE);
    a90_console_printf("credentials=0\r\n");
    a90_console_printf("connect=0\r\n");
    a90_console_printf("dhcp_routing=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("raw_results_redacted=1\r\n");
    a90_console_printf("link_up_attempted=1\r\n");

    link_up_rc = wifi_link_set_up(A90_WIFI_IFACE, &saved_errno);
    a90_console_printf("link_up_rc=%d\r\n", link_up_rc);
    a90_console_printf("link_up_errno=%d\r\n", saved_errno);
    if (link_up_rc < 0) {
        a90_console_printf("decision=wifi-scan-link-up-failed\r\n");
        return -saved_errno;
    }

    ifindex = if_nametoindex(A90_WIFI_IFACE);
    if (ifindex == 0) {
        saved_errno = errno;
        a90_console_printf("ifindex=0\r\n");
        a90_console_printf("errno=%d\r\n", saved_errno);
        a90_console_printf("decision=wifi-scan-interface-missing\r\n");
        return -saved_errno;
    }
    a90_console_printf("ifindex=%u\r\n", ifindex);

    socket_fd = wifi_open_genl_socket();
    if (socket_fd < 0) {
        saved_errno = errno;
        a90_console_printf("netlink_open=0\r\n");
        a90_console_printf("errno=%d\r\n", saved_errno);
        a90_console_printf("decision=wifi-scan-nl80211-unavailable\r\n");
        return -saved_errno;
    }
    a90_console_printf("netlink_open=1\r\n");

    family_id = wifi_get_family_id(socket_fd, "nl80211");
    if (family_id < 0) {
        saved_errno = errno;
        close(socket_fd);
        a90_console_printf("family_id=0\r\n");
        a90_console_printf("errno=%d\r\n", saved_errno);
        a90_console_printf("decision=wifi-scan-family-missing\r\n");
        return -saved_errno;
    }
    a90_console_printf("family_id=%d\r\n", family_id);
    a90_console_printf("trigger_attempted=1\r\n");

    if (wifi_trigger_scan(socket_fd, family_id, ifindex) < 0) {
        saved_errno = errno;
        a90_console_printf("trigger_rc=-1\r\n");
        a90_console_printf("trigger_errno=%d\r\n", saved_errno);
        if (saved_errno != EBUSY) {
            close(socket_fd);
            a90_console_printf("decision=wifi-scan-trigger-failed\r\n");
            return -saved_errno;
        }
        a90_console_printf("trigger_busy_continue=1\r\n");
    } else {
        a90_console_printf("trigger_rc=0\r\n");
        a90_console_printf("trigger_errno=0\r\n");
    }
    a90_console_printf("delay_ms=%d\r\n", delay_ms);
    usleep((useconds_t)delay_ms * 1000U);

    if (wifi_dump_scan_count(socket_fd, family_id, ifindex, &scan_count) < 0) {
        saved_errno = errno;
        close(socket_fd);
        a90_console_printf("scan_result_count=0\r\n");
        a90_console_printf("errno=%d\r\n", saved_errno);
        a90_console_printf("decision=wifi-scan-dump-failed\r\n");
        return -saved_errno;
    }
    close(socket_fd);
    a90_console_printf("scan_result_count=%d\r\n", scan_count);
    a90_console_printf("decision=%s\r\n", scan_count > 0 ? "wifi-scan-pass" : "wifi-scan-zero-bss");
    a90_logf("wifi", "scan count=%d delay_ms=%d", scan_count, delay_ms);
    return scan_count > 0 ? 0 : -ENODATA;
}

int a90_wifi_connect_profile(const char *profile_name) {
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
    pid_t supplicant_pid = -1;
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
    a90_console_printf("supplicant_log.path=%s\r\n", A90_WIFI_SUPPLICANT_LOG);
    if (access(A90_WIFI_STANDALONE_SUPPLICANT, X_OK) < 0) {
        int saved_errno = errno;

        a90_console_printf("supplicant_errno=%d\r\n", saved_errno);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-supplicant-missing\r\n");
        return -saved_errno;
    }

    supplicant_process_count = wifi_count_processes_with_token("wpa_supplicant");
    a90_console_printf("supplicant.process_count_before=%d\r\n", supplicant_process_count);
    if (supplicant_process_count > 0) {
        ctrl_ready_rc = wifi_wait_ctrl_ready(0,
                                             false,
                                             5000,
                                             &ctrl_wait_elapsed_ms,
                                             ctrl_category,
                                             sizeof(ctrl_category),
                                             &ctrl_errno);
        a90_console_printf("supplicant.reuse_attempted=1\r\n");
        a90_console_printf("ctrl_wait_elapsed_ms=%d\r\n", ctrl_wait_elapsed_ms);
        a90_console_printf("ctrl_ping_rc=%d\r\n", ctrl_ready_rc);
        a90_console_printf("ctrl_ping_errno=%d\r\n", ctrl_errno);
        a90_console_printf("ctrl_ping.reply_category=%s\r\n",
                           ctrl_ready_rc == 0 ? ctrl_category : "error");
        if (ctrl_ready_rc < 0) {
            a90_console_printf("secret_values_logged=0\r\n");
            a90_console_printf("decision=wifi-connect-supplicant-busy-no-ctrl\r\n");
            return -EBUSY;
        }
        reusing_supplicant = true;
    } else {
        (void)unlink(A90_WIFI_CTRL_SOCKET);
        (void)unlink(A90_WIFI_SUPPLICANT_LOG);
        supplicant_start_rc = wifi_start_supplicant(&supplicant_pid);
        a90_console_printf("supplicant.reuse_attempted=0\r\n");
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
    }

    (void)wifi_print_ctrl_result("ctrl.driver_country", "DRIVER COUNTRY KR");
    (void)wifi_print_ctrl_result("ctrl.scan", "SCAN");
    (void)wifi_print_ctrl_result("ctrl.enable_network", "ENABLE_NETWORK 0");
    (void)wifi_print_ctrl_result("ctrl.select_network", "SELECT_NETWORK 0");
    (void)wifi_print_ctrl_result("ctrl.reassociate", "REASSOCIATE");

    a90_console_printf("carrier_wait_timeout_ms=%d\r\n", A90_WIFI_CONNECT_CARRIER_WAIT_MS);
    carrier_rc = wifi_wait_carrier(A90_WIFI_CONNECT_CARRIER_WAIT_MS, &carrier_wait_elapsed_ms);
    a90_console_printf("carrier_wait_rc=%d\r\n", carrier_rc);
    a90_console_printf("carrier_wait_elapsed_ms=%d\r\n", carrier_wait_elapsed_ms);
    a90_console_printf("carrier_up=%d\r\n", carrier_rc == 0 ? 1 : 0);
    status_rc = wifi_print_ctrl_result("ctrl.status", "STATUS");
    a90_console_printf("supplicant.reused=%d\r\n", reusing_supplicant ? 1 : 0);
    a90_console_printf("supplicant.spawned=%d\r\n", spawned_supplicant ? 1 : 0);
    a90_console_printf("supplicant.left_running=%d\r\n", carrier_rc == 0 ? 1 : 0);
    a90_console_printf("status_request_rc=%d\r\n", status_rc);
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("dhcp_routing=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");

    if (carrier_rc == 0) {
        a90_logf("wifi",
                 "connect profile=%s carrier=1 reused=%d spawned=%d secret_values_logged=0",
                 profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
                 reusing_supplicant ? 1 : 0,
                 spawned_supplicant ? 1 : 0);
        a90_console_printf("decision=wifi-connect-carrier-up\r\n");
        return 0;
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

static int wifi_parse_delay_ms(const char *text, int *delay_ms) {
    char *end = NULL;
    long value;

    if (text == NULL || delay_ms == NULL) {
        return -EINVAL;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 0 || value > 30000) {
        return -EINVAL;
    }
    *delay_ms = (int)value;
    return 0;
}

int a90_wifi_cmd(char **argv, int argc) {
    if (argc == 1 ||
        (argc == 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "status") == 0)) {
        return a90_wifi_print_status();
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
        strcmp(argv[1], "connect") == 0) {
        return a90_wifi_connect_profile(argc == 3 ? argv[2] : NULL);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "config") == 0) {
        return a90_wificfg_cmd(argv, argc);
    }

    a90_console_printf("usage: wifi [status|scan [delay_ms]|connect [profile]|config [status|prepare [profile]]]\r\n");
    return -EINVAL;
}
