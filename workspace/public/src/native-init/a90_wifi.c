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
#include "a90_helper.h"
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
#define A90_WIFI_CTRL_ROOT "/tmp/a90-wifi"
#define A90_WIFI_CTRL_DIR A90_WIFI_CTRL_ROOT "/sockets"
#define A90_WIFI_CTRL_SOCKET A90_WIFI_CTRL_DIR "/wlan0"
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
#define A90_WIFI_CONNECT_WPA_COMPLETE_WAIT_MS 25000
#define A90_WIFI_CONNECT_WPA_SAMPLE_MS 1000
#define A90_WIFI_CONNECT_WPA_RETRY_MS 5000
#define A90_WIFI_SUPPLICANT_TERMINATE_WAIT_MS 3000
#define A90_WIFI_SUPPLICANT_KILL_WAIT_MS 1500
#define A90_WIFI_DHCP_TIMEOUT_MS 30000
#define A90_WIFI_PING_COUNT 3
#define A90_WIFI_PING_TIMEOUT_SEC 2
#define A90_WIFI_PING_TIMEOUT_MS 10000
#define A90_WIFI_PING_GATEWAY_LOG "/cache/a90-wifi/ping-gateway.log"
#define A90_WIFI_PING_INTERNET_LOG "/cache/a90-wifi/ping-internet.log"
#define A90_WIFI_PING_INTERNET_TARGET "1.1.1.1"
#define A90_WIFI_SOFTAP_VERSION "a90-native-wifi-softap-v2"
#define A90_WIFI_SOFTAP_ROOT "/cache/a90-softap"
#define A90_WIFI_SOFTAP_PROBE_IFACE "a90ap0"
#define A90_WIFI_SOFTAP_CTRL_DIR "/cache/a90-softap/sockets"
#define A90_WIFI_SOFTAP_CTRL_SOCKET "/cache/a90-softap/sockets/a90ap0"
#define A90_WIFI_SOFTAP_SUPPLICANT_CONF "/cache/a90-softap/wpa_supplicant-softap.conf"
#define A90_WIFI_SOFTAP_SUPPLICANT_LOG "/cache/a90-softap/wpa_supplicant-softap.log"
#define A90_WIFI_SOFTAP_SUPPLICANT_PID "/cache/a90-softap/wpa_supplicant-softap.pid"
#define A90_WIFI_SOFTAP_UDHCPD_CONF "/cache/a90-softap/udhcpd.conf"
#define A90_WIFI_SOFTAP_UDHCPD_LOG "/cache/a90-softap/udhcpd.log"
#define A90_WIFI_SOFTAP_UDHCPD_PID "/cache/a90-softap/udhcpd.pid"
#define A90_WIFI_SOFTAP_UDHCPD_LEASES "/cache/a90-softap/udhcpd.leases"
#define A90_WIFI_SOFTAP_PRIVATE_CREDENTIALS "/cache/a90-softap/credentials.private"
#define A90_WIFI_SOFTAP_CTRL_WAIT_MS 20000
#define A90_WIFI_SOFTAP_DHCP_SETTLE_MS 1200
#define A90_WIFI_SOFTAP_NET_A 10
#define A90_WIFI_SOFTAP_NET_B 47
#define A90_WIFI_SOFTAP_NET_C 43
#define A90_WIFI_SOFTAP_WLAN0_WAIT_MS 220000
#define A90_WIFI_SOFTAP_IFTYPE_PROBE_MAX_WAIT_MS 240000
#define A90_WIFI_SOFTAP_TRANSFER_VERSION "a90-native-wifi-softap-transfer-v1"
#define A90_WIFI_SOFTAP_WWW_ROOT "/cache/a90-softap/www"
#define A90_WIFI_SOFTAP_DOWNLOAD_FILE "/cache/a90-softap/www/download.bin"
#define A90_WIFI_SOFTAP_DOWNLOAD_TMP "/cache/a90-softap/www/download.bin.tmp"
#define A90_WIFI_SOFTAP_HTTPD_LOG "/cache/a90-softap/httpd.log"
#define A90_WIFI_SOFTAP_HTTPD_PID "/cache/a90-softap/httpd.pid"
#define A90_WIFI_SOFTAP_UPLOAD_FILE "/cache/a90-softap/upload.bin"
#define A90_WIFI_SOFTAP_UPLOAD_TMP "/cache/a90-softap/upload.bin.tmp"
#define A90_WIFI_SOFTAP_UPLOAD_RESULT "/cache/a90-softap/upload.result"
#define A90_WIFI_SOFTAP_UPLOAD_PID "/cache/a90-softap/upload-receiver.pid"
#define A90_WIFI_SOFTAP_HTTP_PORT 8080
#define A90_WIFI_SOFTAP_UPLOAD_PORT 9001
#define A90_WIFI_SOFTAP_DOWNLOAD_BYTES (1024U * 1024U)
#define A90_WIFI_SOFTAP_UPLOAD_MAX_BYTES (1024U * 1024U)
#define A90_WIFI_SOFTAP_UPLOAD_ACCEPT_TIMEOUT_MS 180000
#define A90_WIFI_SOFTAP_UPLOAD_IDLE_TIMEOUT_MS 30000
#define A90_WIFI_SERVICE_VERSION "a90-native-wifi-service-v1"
#define A90_WIFI_SERVICE_REQUEST_FILE "request"
#define A90_WIFI_SERVICE_RESPONSE_FILE "response"
#define A90_WIFI_SERVICE_PID_FILE "pid"
#define A90_WIFI_SERVICE_STATE_FILE "state"
#define A90_WIFI_SERVICE_MAX_ROOT 192
#define A90_WIFI_SERVICE_MAX_PATH 256
#define A90_WIFI_SERVICE_MAX_REQUEST 1024
#define A90_WIFI_SERVICE_DEFAULT_SCAN_DELAY_MS 5000
#define A90_WIFI_SERVICE_DEFAULT_LIFETIME_MS 120000
#define A90_WIFI_SERVICE_MAX_LIFETIME_MS 600000
#define A90_WIFI_SERVICE_DEFAULT_POLL_MS 250
#define A90_WIFI_SERVICE_MIN_POLL_MS 50
#define A90_WIFI_SERVICE_MAX_POLL_MS 5000
#define A90_WIFI_UPLINK_SERVICE_VERSION "a90-native-wifi-uplink-service-v1"
#define A90_WIFI_UPLINK_SERVICE_CONFIRM "A90_NATIVE_UPLINK_AUTOCONNECT_V1"

struct wifi_autoconnect_scan_recovery_state {
    int attempted;
    int first_scan_rc;
    int rc;
    int rescan_rc;
    int success;
    char decision[64];
};

static struct wifi_autoconnect_scan_recovery_state g_autoconnect_scan_recovery;

struct wifi_autoconnect_connect_diag_state {
    int attempted;
    int wlan0_wait_rc;
    int wlan0_wait_elapsed_ms;
    int link_up_rc;
    int link_up_errno;
    int prepare_rc;
    int runtime_prepare_rc;
    int supplicant_root_exec_rc;
    int supplicant_process_count_before;
    int supplicant_start_rc;
    int ctrl_wait_rc;
    int ctrl_wait_errno;
    int ctrl_wait_elapsed_ms;
    char ctrl_wait_category[32];
    int ctrl_driver_country_rc;
    int ctrl_scan_rc;
    int ctrl_enable_network_rc;
    int ctrl_select_network_rc;
    int ctrl_reassociate_rc;
    int carrier_wait_rc;
    int carrier_wait_elapsed_ms;
    int carrier_up_at_wait;
    int wpa_complete_wait_rc;
    int wpa_complete_wait_elapsed_ms;
    int wpa_complete_samples;
    int wpa_complete_completed;
    int wpa_complete_retry_count;
    char wpa_complete_first_state[32];
    char wpa_complete_last_state[32];
    int wpa_monitor_attach_rc;
    int wpa_monitor_attach_errno;
    int wpa_monitor_event_count;
    int wpa_monitor_connected_seen;
    int wpa_monitor_disconnected_seen;
    int wpa_monitor_scan_results_seen;
    int wpa_monitor_assoc_reject_seen;
    int wpa_monitor_auth_reject_seen;
    int wpa_monitor_temp_disabled_seen;
    int wpa_monitor_eap_failure_seen;
    char wpa_monitor_last_event[48];
    char wpa_monitor_disconnect_reason_class[64];
    char wpa_monitor_temp_disabled_reason_class[64];
    char wpa_monitor_assoc_reject_status_class[32];
    int ctrl_status_rc;
    int ctrl_status_errno;
    int ctrl_status_completed;
    char ctrl_status_wpa_state[32];
    char ctrl_status_network_id[16];
    int ctrl_status_network_selected;
    char ctrl_status_key_mgmt[64];
    char ctrl_status_pairwise_cipher[64];
    char ctrl_status_group_cipher[64];
    char ctrl_status_mode[32];
    char ctrl_status_freq_mhz[32];
    int ctrl_signal_rc;
    int ctrl_signal_errno;
    int supplicant_spawned;
    int supplicant_left_running;
    int cleanup_status;
    char decision[64];
};

static struct wifi_autoconnect_connect_diag_state g_autoconnect_connect_diag;

static int wifi_softap_iftype_probe(int wait_timeout_ms);

static void wifi_autoconnect_reset_scan_recovery(void) {
    memset(&g_autoconnect_scan_recovery, 0, sizeof(g_autoconnect_scan_recovery));
    snprintf(g_autoconnect_scan_recovery.decision,
             sizeof(g_autoconnect_scan_recovery.decision),
             "%s",
             "wifi-autoconnect-scan-recovery-not-attempted");
}

static void wifi_autoconnect_reset_connect_diag(void) {
    memset(&g_autoconnect_connect_diag, 0, sizeof(g_autoconnect_connect_diag));
    g_autoconnect_connect_diag.wlan0_wait_rc = 0;
    g_autoconnect_connect_diag.link_up_errno = 0;
    g_autoconnect_connect_diag.prepare_rc = 0;
    g_autoconnect_connect_diag.runtime_prepare_rc = 0;
    g_autoconnect_connect_diag.supplicant_root_exec_rc = 0;
    g_autoconnect_connect_diag.supplicant_process_count_before = -1;
    g_autoconnect_connect_diag.supplicant_start_rc = 0;
    g_autoconnect_connect_diag.ctrl_wait_rc = 0;
    g_autoconnect_connect_diag.ctrl_wait_errno = 0;
    snprintf(g_autoconnect_connect_diag.ctrl_wait_category,
             sizeof(g_autoconnect_connect_diag.ctrl_wait_category),
             "%s",
             "not-run");
    g_autoconnect_connect_diag.ctrl_driver_country_rc = 0;
    g_autoconnect_connect_diag.ctrl_scan_rc = 0;
    g_autoconnect_connect_diag.ctrl_enable_network_rc = 0;
    g_autoconnect_connect_diag.ctrl_select_network_rc = 0;
    g_autoconnect_connect_diag.ctrl_reassociate_rc = 0;
    g_autoconnect_connect_diag.carrier_wait_rc = 0;
    g_autoconnect_connect_diag.wpa_complete_wait_rc = 0;
    g_autoconnect_connect_diag.wpa_complete_wait_elapsed_ms = 0;
    g_autoconnect_connect_diag.wpa_complete_samples = 0;
    g_autoconnect_connect_diag.wpa_complete_completed = 0;
    g_autoconnect_connect_diag.wpa_complete_retry_count = 0;
    snprintf(g_autoconnect_connect_diag.wpa_complete_first_state,
             sizeof(g_autoconnect_connect_diag.wpa_complete_first_state),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.wpa_complete_last_state,
             sizeof(g_autoconnect_connect_diag.wpa_complete_last_state),
             "%s",
             "-");
    g_autoconnect_connect_diag.wpa_monitor_attach_rc = -ENOENT;
    g_autoconnect_connect_diag.wpa_monitor_attach_errno = 0;
    snprintf(g_autoconnect_connect_diag.wpa_monitor_last_event,
             sizeof(g_autoconnect_connect_diag.wpa_monitor_last_event),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.wpa_monitor_disconnect_reason_class,
             sizeof(g_autoconnect_connect_diag.wpa_monitor_disconnect_reason_class),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.wpa_monitor_temp_disabled_reason_class,
             sizeof(g_autoconnect_connect_diag.wpa_monitor_temp_disabled_reason_class),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.wpa_monitor_assoc_reject_status_class,
             sizeof(g_autoconnect_connect_diag.wpa_monitor_assoc_reject_status_class),
             "%s",
             "-");
    g_autoconnect_connect_diag.ctrl_status_rc = -ENOENT;
    g_autoconnect_connect_diag.ctrl_status_errno = 0;
    g_autoconnect_connect_diag.ctrl_signal_rc = -ENOENT;
    g_autoconnect_connect_diag.ctrl_signal_errno = 0;
    snprintf(g_autoconnect_connect_diag.ctrl_status_wpa_state,
             sizeof(g_autoconnect_connect_diag.ctrl_status_wpa_state),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_network_id,
             sizeof(g_autoconnect_connect_diag.ctrl_status_network_id),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_key_mgmt,
             sizeof(g_autoconnect_connect_diag.ctrl_status_key_mgmt),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_pairwise_cipher,
             sizeof(g_autoconnect_connect_diag.ctrl_status_pairwise_cipher),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_group_cipher,
             sizeof(g_autoconnect_connect_diag.ctrl_status_group_cipher),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_mode,
             sizeof(g_autoconnect_connect_diag.ctrl_status_mode),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_freq_mhz,
             sizeof(g_autoconnect_connect_diag.ctrl_status_freq_mhz),
             "%s",
             "-");
    snprintf(g_autoconnect_connect_diag.decision,
             sizeof(g_autoconnect_connect_diag.decision),
             "%s",
             "wifi-connect-not-attempted");
}

static void wifi_autoconnect_set_connect_decision(const char *decision) {
    snprintf(g_autoconnect_connect_diag.decision,
             sizeof(g_autoconnect_connect_diag.decision),
             "%s",
             decision != NULL && decision[0] != '\0' ? decision : "wifi-connect-unknown");
}

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

static int wifi_service_join_path(const char *root,
                                  const char *leaf,
                                  char *out,
                                  size_t out_size) {
    if (root == NULL || root[0] != '/' || leaf == NULL || leaf[0] == '\0' ||
        strchr(leaf, '/') != NULL || out == NULL || out_size == 0) {
        return -EINVAL;
    }
    if (snprintf(out, out_size, "%s/%s", root, leaf) >= (int)out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

static int wifi_service_read_file_no_follow(const char *path, char *out, size_t out_size) {
    int fd;
    ssize_t rd;

    if (path == NULL || out == NULL || out_size == 0) {
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rd = read(fd, out, out_size - 1);
    if (close(fd) < 0 && rd >= 0) {
        return -errno;
    }
    if (rd < 0) {
        return -errno;
    }
    out[rd] = '\0';
    return 0;
}

static int wifi_service_write_file_no_follow(const char *path,
                                             const char *text,
                                             mode_t mode) {
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
    if (rc == 0 && fsync(fd) < 0) {
        rc = -errno;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int wifi_service_append(char *out, size_t out_size, size_t *offset, const char *format, ...) {
    va_list ap;
    int written;

    if (out == NULL || offset == NULL || *offset >= out_size || format == NULL) {
        return -EINVAL;
    }
    va_start(ap, format);
    written = vsnprintf(out + *offset, out_size - *offset, format, ap);
    va_end(ap);
    if (written < 0) {
        return -EINVAL;
    }
    if ((size_t)written >= out_size - *offset) {
        *offset = out_size - 1;
        out[*offset] = '\0';
        return -ENOSPC;
    }
    *offset += (size_t)written;
    return 0;
}

static int wifi_service_request_value(const char *request,
                                      const char *key,
                                      char *out,
                                      size_t out_size) {
    size_t key_len;
    const char *cursor;

    if (request == NULL || key == NULL || out == NULL || out_size == 0) {
        return -EINVAL;
    }
    out[0] = '\0';
    key_len = strlen(key);
    cursor = request;
    while (*cursor != '\0') {
        const char *line_end = strchr(cursor, '\n');
        size_t line_len = line_end == NULL ? strlen(cursor) : (size_t)(line_end - cursor);

        if (line_len >= key_len &&
            strncmp(cursor, key, key_len) == 0 &&
            cursor[key_len] == '=') {
            size_t value_len = line_len - key_len - 1;

            if (value_len >= out_size) {
                value_len = out_size - 1;
            }
            memcpy(out, cursor + key_len + 1, value_len);
            out[value_len] = '\0';
            trim_newline(out);
            return 0;
        }
        if (line_end == NULL) {
            break;
        }
        cursor = line_end + 1;
    }
    return -ENOENT;
}

static int wifi_service_parse_long(const char *text, long *out) {
    char *end = NULL;
    long value;

    if (text == NULL || text[0] == '\0' || out == NULL) {
        return -EINVAL;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || (end != NULL && *end != '\0')) {
        return -EINVAL;
    }
    *out = value;
    return 0;
}

static int wifi_service_write_response(const char *root, const char *response) {
    char tmp_path[A90_WIFI_SERVICE_MAX_PATH];
    char response_path[A90_WIFI_SERVICE_MAX_PATH];
    int rc;

    rc = wifi_service_join_path(root, "response.tmp", tmp_path, sizeof(tmp_path));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_RESPONSE_FILE, response_path, sizeof(response_path));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_service_write_file_no_follow(tmp_path, response, 0644);
    if (rc < 0) {
        unlink(tmp_path);
        return rc;
    }
    if (rename(tmp_path, response_path) < 0) {
        rc = -errno;
        unlink(tmp_path);
        return rc;
    }
    return 0;
}

static int wifi_service_format_status_response(char *response,
                                               size_t response_size,
                                               size_t *offset,
                                               const char *seq,
                                               const char *op) {
    struct a90_wifi_status_snapshot status;
    int rc = a90_wifi_status_snapshot(&status);

    wifi_service_append(response, response_size, offset, "version=%s\n", A90_WIFI_SERVICE_VERSION);
    wifi_service_append(response, response_size, offset, "seq=%s\n", seq);
    wifi_service_append(response, response_size, offset, "op=%s\n", op);
    wifi_service_append(response, response_size, offset, "owner=native-init\n");
    wifi_service_append(response, response_size, offset, "credentials=0\n");
    wifi_service_append(response, response_size, offset, "dhcp_routing=0\n");
    wifi_service_append(response, response_size, offset, "public_tunnel=0\n");
    wifi_service_append(response, response_size, offset, "raw_values_redacted=1\n");
    wifi_service_append(response, response_size, offset, "rc=%d\n", rc);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "wlan0_present=%d\n",
                        status.wlan0_present ? 1 : 0);
    wifi_service_append(response, response_size, offset, "operstate=%s\n", status.operstate);
    wifi_service_append(response, response_size, offset, "carrier=%s\n", status.carrier);
    wifi_service_append(response, response_size, offset, "flags=%s\n", status.flags);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "default_route_present=%d\n",
                        status.route_default_present ? 1 : 0);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "supplicant_process_count=%d\n",
                        status.supplicant_process_count);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "decision=%s\n",
                        status.wlan0_present ? "wifi-service-status-pass" : "wifi-service-status-wlan0-missing");
    return rc;
}

static int wifi_service_format_scan_response(char *response,
                                             size_t response_size,
                                             size_t *offset,
                                             const char *seq,
                                             const char *op,
                                             int scan_delay_ms) {
    struct a90_wifi_scan_snapshot scan;
    int rc;

    if (scan_delay_ms < 0) {
        scan_delay_ms = A90_WIFI_SERVICE_DEFAULT_SCAN_DELAY_MS;
    }
    if (scan_delay_ms > 30000) {
        scan_delay_ms = 30000;
    }
    rc = a90_wifi_scan_collect(scan_delay_ms, &scan);

    wifi_service_append(response, response_size, offset, "version=%s\n", A90_WIFI_SERVICE_VERSION);
    wifi_service_append(response, response_size, offset, "seq=%s\n", seq);
    wifi_service_append(response, response_size, offset, "op=%s\n", op);
    wifi_service_append(response, response_size, offset, "owner=native-init\n");
    wifi_service_append(response, response_size, offset, "credentials=0\n");
    wifi_service_append(response, response_size, offset, "connect=0\n");
    wifi_service_append(response, response_size, offset, "dhcp_routing=0\n");
    wifi_service_append(response, response_size, offset, "public_tunnel=0\n");
    wifi_service_append(response, response_size, offset, "raw_results_redacted=1\n");
    wifi_service_append(response, response_size, offset, "rc=%d\n", rc);
    wifi_service_append(response, response_size, offset, "link_up_rc=%d\n", scan.link_up_rc);
    wifi_service_append(response, response_size, offset, "link_up_errno=%d\n", scan.link_up_errno);
    wifi_service_append(response, response_size, offset, "ifindex=%u\n", scan.ifindex);
    wifi_service_append(response, response_size, offset, "netlink_open=%d\n", scan.netlink_open);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "family_id=%d\n",
                        scan.family_id < 0 ? 0 : scan.family_id);
    wifi_service_append(response, response_size, offset, "trigger_rc=%d\n", scan.trigger_rc);
    wifi_service_append(response, response_size, offset, "trigger_errno=%d\n", scan.trigger_errno);
    wifi_service_append(response, response_size, offset, "delay_ms=%d\n", scan.delay_ms);
    wifi_service_append(response, response_size, offset, "scan_result_count=%d\n", scan.scan_result_count);
    wifi_service_append(response, response_size, offset, "decision=%s\n", scan.decision);
    return rc;
}

static int wifi_service_process_once(const char *root,
                                     int default_scan_delay_ms,
                                     long skip_seq,
                                     long *seq_out) {
    char request_path[A90_WIFI_SERVICE_MAX_PATH];
    char request[A90_WIFI_SERVICE_MAX_REQUEST];
    char response[4096];
    char seq[64] = "";
    char op[32] = "";
    char delay_text[32] = "";
    long seq_value = -1;
    long parsed_delay = default_scan_delay_ms;
    size_t offset = 0;
    int rc;

    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_REQUEST_FILE, request_path, sizeof(request_path));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_service_read_file_no_follow(request_path, request, sizeof(request));
    if (rc < 0) {
        return rc;
    }
    if (wifi_service_request_value(request, "seq", seq, sizeof(seq)) < 0 ||
        wifi_service_parse_long(seq, &seq_value) < 0 ||
        wifi_service_request_value(request, "op", op, sizeof(op)) < 0) {
        snprintf(response,
                 sizeof(response),
                 "version=%s\nseq=-1\nop=invalid\nowner=native-init\nrc=-22\ndecision=wifi-service-request-invalid\n",
                 A90_WIFI_SERVICE_VERSION);
        (void)wifi_service_write_response(root, response);
        return -EINVAL;
    }
    if (seq_value == skip_seq) {
        if (seq_out != NULL) {
            *seq_out = seq_value;
        }
        return 1;
    }
    if (wifi_service_request_value(request, "scan_delay_ms", delay_text, sizeof(delay_text)) == 0) {
        (void)wifi_service_parse_long(delay_text, &parsed_delay);
    }

    if (strcmp(op, "status") == 0) {
        rc = wifi_service_format_status_response(response, sizeof(response), &offset, seq, op);
    } else if (strcmp(op, "scan") == 0) {
        rc = wifi_service_format_scan_response(response,
                                               sizeof(response),
                                               &offset,
                                               seq,
                                               op,
                                               (int)parsed_delay);
    } else {
        wifi_service_append(response,
                            sizeof(response),
                            &offset,
                            "version=%s\nseq=%s\nop=%s\nowner=native-init\nrc=-22\ndecision=wifi-service-op-denied\n",
                            A90_WIFI_SERVICE_VERSION,
                            seq,
                            op);
        rc = -EINVAL;
    }
    if (wifi_service_write_response(root, response) < 0 && rc == 0) {
        rc = -EIO;
    }
    if (seq_out != NULL) {
        *seq_out = seq_value;
    }
    return rc;
}

static void wifi_service_daemon_run(const char *root,
                                    int lifetime_ms,
                                    int poll_ms,
                                    int scan_delay_ms) {
    char state_path[A90_WIFI_SERVICE_MAX_PATH] = "";
    long deadline_ms = monotonic_millis() + lifetime_ms;
    long last_seq = -1;

    if (wifi_service_join_path(root, A90_WIFI_SERVICE_STATE_FILE, state_path, sizeof(state_path)) == 0) {
        (void)wifi_service_write_file_no_follow(state_path,
                                                "version=" A90_WIFI_SERVICE_VERSION "\nstate=running\n",
                                                0644);
    }
    while (monotonic_millis() <= deadline_ms) {
        long seq = -1;
        int rc = wifi_service_process_once(root, scan_delay_ms, last_seq, &seq);

        if (rc != -ENOENT && rc != 1 && seq >= 0 && seq != last_seq) {
            last_seq = seq;
        }
        usleep((useconds_t)poll_ms * 1000U);
    }
    if (state_path[0] != '\0') {
        (void)wifi_service_write_file_no_follow(state_path,
                                                "version=" A90_WIFI_SERVICE_VERSION "\nstate=stopped\n",
                                                0644);
    }
    _exit(0);
}

static int wifi_service_start(const char *root,
                              int lifetime_ms,
                              int poll_ms,
                              int scan_delay_ms) {
    char pid_path[A90_WIFI_SERVICE_MAX_PATH];
    char pid_text[64];
    pid_t pid;
    int rc;

    if (root == NULL || root[0] != '/') {
        return -EINVAL;
    }
    if (strlen(root) >= A90_WIFI_SERVICE_MAX_ROOT) {
        return -ENAMETOOLONG;
    }
    rc = ensure_dir(root, 0755);
    if (rc < 0) {
        return negative_errno_or(EIO);
    }
    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_PID_FILE, pid_path, sizeof(pid_path));
    if (rc < 0) {
        return rc;
    }
    if (lifetime_ms <= 0) {
        lifetime_ms = A90_WIFI_SERVICE_DEFAULT_LIFETIME_MS;
    }
    if (lifetime_ms > A90_WIFI_SERVICE_MAX_LIFETIME_MS) {
        lifetime_ms = A90_WIFI_SERVICE_MAX_LIFETIME_MS;
    }
    if (poll_ms < A90_WIFI_SERVICE_MIN_POLL_MS) {
        poll_ms = A90_WIFI_SERVICE_MIN_POLL_MS;
    }
    if (poll_ms > A90_WIFI_SERVICE_MAX_POLL_MS) {
        poll_ms = A90_WIFI_SERVICE_MAX_POLL_MS;
    }
    if (scan_delay_ms < 0) {
        scan_delay_ms = A90_WIFI_SERVICE_DEFAULT_SCAN_DELAY_MS;
    }
    if (scan_delay_ms > 30000) {
        scan_delay_ms = 30000;
    }

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        (void)setsid();
        wifi_service_daemon_run(root, lifetime_ms, poll_ms, scan_delay_ms);
    }
    snprintf(pid_text,
             sizeof(pid_text),
             "version=%s\npid=%ld\n",
             A90_WIFI_SERVICE_VERSION,
             (long)pid);
    rc = wifi_service_write_file_no_follow(pid_path, pid_text, 0644);
    if (rc < 0) {
        (void)kill(pid, SIGTERM);
        return rc;
    }
    return (int)pid;
}

static int wifi_service_stop(const char *root) {
    char pid_path[A90_WIFI_SERVICE_MAX_PATH];
    char text[128];
    char pid_text[32];
    long pid_value;
    int rc;

    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_PID_FILE, pid_path, sizeof(pid_path));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_service_read_file_no_follow(pid_path, text, sizeof(text));
    if (rc < 0) {
        return rc;
    }
    if (wifi_service_request_value(text, "pid", pid_text, sizeof(pid_text)) < 0 ||
        wifi_service_parse_long(pid_text, &pid_value) < 0 ||
        pid_value <= 1) {
        return -EINVAL;
    }
    if (kill((pid_t)pid_value, SIGTERM) < 0 && errno != ESRCH) {
        return -errno;
    }
    unlink(pid_path);
    return 0;
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

static unsigned long g_wifi_ctrl_local_seq;

static unsigned long wifi_ctrl_next_local_seq(void) {
    return __sync_add_and_fetch(&g_wifi_ctrl_local_seq, 1);
}

static int wifi_ctrl_bind_local_abstract(int socket_fd) {
    struct sockaddr_un local;
    char name[80];
    unsigned long seq;
    size_t name_len;

    seq = wifi_ctrl_next_local_seq();
    if (snprintf(name,
                 sizeof(name),
                 "a90-wifi-%ld-%ld-%lu",
                 (long)getpid(),
                 monotonic_millis(),
                 seq) >= (int)sizeof(name)) {
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

static int wifi_ctrl_request_at(const char *remote_path,
                                const char *command,
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
    if (remote_path == NULL || remote_path[0] == '\0' ||
        command == NULL || command[0] == '\0') {
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
        wifi_ctrl_connect_remote(socket_fd, remote_path) < 0) {
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

static int wifi_ctrl_request(const char *command,
                             char *category,
                             size_t category_size,
                             long *reply_len_out,
                             int *saved_errno_out,
                             char *reply_out,
                             size_t reply_out_size) {
    return wifi_ctrl_request_at(A90_WIFI_CTRL_SOCKET,
                                command,
                                category,
                                category_size,
                                reply_len_out,
                                saved_errno_out,
                                reply_out,
                                reply_out_size);
}

struct wifi_ctrl_monitor {
    int socket_fd;
    bool attached;
};

static char wifi_safe_metric_char(char value);

static void wifi_ctrl_monitor_reset(struct wifi_ctrl_monitor *monitor) {
    if (monitor == NULL) {
        return;
    }
    monitor->socket_fd = -1;
    monitor->attached = false;
}

static const char *wifi_wpa_event_category(const char *event) {
    if (event == NULL || event[0] == '\0') {
        return "empty";
    }
    if (strstr(event, "CTRL-EVENT-CONNECTED") != NULL) {
        return "connected";
    }
    if (strstr(event, "CTRL-EVENT-DISCONNECTED") != NULL) {
        return "disconnected";
    }
    if (strstr(event, "CTRL-EVENT-SCAN-RESULTS") != NULL) {
        return "scan-results";
    }
    if (strstr(event, "CTRL-EVENT-ASSOC-REJECT") != NULL) {
        return "assoc-reject";
    }
    if (strstr(event, "CTRL-EVENT-AUTH-REJECT") != NULL) {
        return "auth-reject";
    }
    if (strstr(event, "CTRL-EVENT-SSID-TEMP-DISABLED") != NULL) {
        return "ssid-temp-disabled";
    }
    if (strstr(event, "CTRL-EVENT-EAP-FAILURE") != NULL ||
        strstr(event, "Authentication with") != NULL) {
        return "eap-failure";
    }
    if (strstr(event, "CTRL-EVENT-REGDOM-CHANGE") != NULL) {
        return "regdom-change";
    }
    if (strstr(event, "CTRL-EVENT-SCAN-STARTED") != NULL) {
        return "scan-started";
    }
    return "other";
}

static void wifi_event_value_class(const char *event,
                                   const char *key,
                                   const char *fallback,
                                   char *out,
                                   size_t out_size) {
    char pattern[48];
    const char *cursor;
    const char *value;
    size_t index = 0;

    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "%s", fallback != NULL && fallback[0] != '\0' ? fallback : "not-present");
    if (event == NULL || key == NULL || key[0] == '\0') {
        return;
    }
    if (snprintf(pattern, sizeof(pattern), "%s=", key) >= (int)sizeof(pattern)) {
        return;
    }
    cursor = strstr(event, pattern);
    if (cursor == NULL) {
        return;
    }
    value = cursor + strlen(pattern);
    if (*value == '"') {
        value++;
    }
    while (*value != '\0' &&
           *value != '"' &&
           *value != ' ' &&
           *value != '\n' &&
           *value != '\r' &&
           index + 1 < out_size) {
        out[index++] = wifi_safe_metric_char(*value);
        value++;
    }
    out[index] = '\0';
    if (index == 0) {
        snprintf(out, out_size, "%s", fallback != NULL && fallback[0] != '\0' ? fallback : "not-present");
    }
}

static void wifi_record_wpa_event_category(const char *category, const char *event) {
    const char *selected = category != NULL && category[0] != '\0' ? category : "other";

    g_autoconnect_connect_diag.wpa_monitor_event_count++;
    snprintf(g_autoconnect_connect_diag.wpa_monitor_last_event,
             sizeof(g_autoconnect_connect_diag.wpa_monitor_last_event),
             "%s",
             selected);
    if (strcmp(selected, "connected") == 0) {
        g_autoconnect_connect_diag.wpa_monitor_connected_seen = 1;
    } else if (strcmp(selected, "disconnected") == 0) {
        g_autoconnect_connect_diag.wpa_monitor_disconnected_seen = 1;
        wifi_event_value_class(event,
                               "reason",
                               "not-present",
                               g_autoconnect_connect_diag.wpa_monitor_disconnect_reason_class,
                               sizeof(g_autoconnect_connect_diag.wpa_monitor_disconnect_reason_class));
    } else if (strcmp(selected, "scan-results") == 0) {
        g_autoconnect_connect_diag.wpa_monitor_scan_results_seen = 1;
    } else if (strcmp(selected, "assoc-reject") == 0) {
        g_autoconnect_connect_diag.wpa_monitor_assoc_reject_seen = 1;
        wifi_event_value_class(event,
                               "status_code",
                               "not-present",
                               g_autoconnect_connect_diag.wpa_monitor_assoc_reject_status_class,
                               sizeof(g_autoconnect_connect_diag.wpa_monitor_assoc_reject_status_class));
    } else if (strcmp(selected, "auth-reject") == 0) {
        g_autoconnect_connect_diag.wpa_monitor_auth_reject_seen = 1;
    } else if (strcmp(selected, "ssid-temp-disabled") == 0) {
        g_autoconnect_connect_diag.wpa_monitor_temp_disabled_seen = 1;
        wifi_event_value_class(event,
                               "reason",
                               "not-present",
                               g_autoconnect_connect_diag.wpa_monitor_temp_disabled_reason_class,
                               sizeof(g_autoconnect_connect_diag.wpa_monitor_temp_disabled_reason_class));
    } else if (strcmp(selected, "eap-failure") == 0) {
        g_autoconnect_connect_diag.wpa_monitor_eap_failure_seen = 1;
    }
}

static void wifi_ctrl_monitor_drain(struct wifi_ctrl_monitor *monitor, int timeout_ms) {
    char event[1024];
    struct pollfd poll_fd;
    long deadline_ms;

    if (monitor == NULL || monitor->socket_fd < 0 || !monitor->attached) {
        return;
    }
    if (timeout_ms < 0) {
        timeout_ms = 0;
    }
    deadline_ms = monotonic_millis() + timeout_ms;
    do {
        int wait_ms = 0;
        int poll_rc;
        ssize_t received;

        if (timeout_ms > 0) {
            long remaining_ms = deadline_ms - monotonic_millis();

            if (remaining_ms <= 0) {
                wait_ms = 0;
            } else if (remaining_ms > 250) {
                wait_ms = 250;
            } else {
                wait_ms = (int)remaining_ms;
            }
        }
        memset(&poll_fd, 0, sizeof(poll_fd));
        poll_fd.fd = monitor->socket_fd;
        poll_fd.events = POLLIN;
        poll_rc = poll(&poll_fd, 1, wait_ms);
        if (poll_rc <= 0) {
            return;
        }
        received = recv(monitor->socket_fd, event, sizeof(event) - 1, 0);
        if (received <= 0) {
            return;
        }
        event[received] = '\0';
        wifi_record_wpa_event_category(wifi_wpa_event_category(event), event);
    } while (monotonic_millis() < deadline_ms);
}

static int wifi_ctrl_monitor_attach(struct wifi_ctrl_monitor *monitor,
                                    const char *remote_path,
                                    int *saved_errno_out) {
    char reply[128];
    struct pollfd poll_fd;
    ssize_t received;
    int saved_errno = 0;
    int socket_fd;
    static const char attach_cmd[] = "ATTACH";

    if (saved_errno_out != NULL) {
        *saved_errno_out = 0;
    }
    if (monitor == NULL) {
        if (saved_errno_out != NULL) {
            *saved_errno_out = EINVAL;
        }
        return -EINVAL;
    }
    wifi_ctrl_monitor_reset(monitor);
    socket_fd = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (socket_fd < 0) {
        saved_errno = errno;
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }
    if (wifi_ctrl_bind_local_abstract(socket_fd) < 0 ||
        wifi_ctrl_connect_remote(socket_fd, remote_path) < 0) {
        saved_errno = errno;
        close(socket_fd);
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }
    monitor->socket_fd = socket_fd;
    if (send(socket_fd, attach_cmd, strlen(attach_cmd), 0) != (ssize_t)strlen(attach_cmd)) {
        saved_errno = errno == 0 ? EIO : errno;
        close(socket_fd);
        wifi_ctrl_monitor_reset(monitor);
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }
    memset(&poll_fd, 0, sizeof(poll_fd));
    poll_fd.fd = socket_fd;
    poll_fd.events = POLLIN;
    if (poll(&poll_fd, 1, 2500) <= 0) {
        saved_errno = errno == 0 ? ETIMEDOUT : errno;
        close(socket_fd);
        wifi_ctrl_monitor_reset(monitor);
        if (saved_errno_out != NULL) {
            *saved_errno_out = saved_errno;
        }
        return -saved_errno;
    }
    received = recv(socket_fd, reply, sizeof(reply) - 1, 0);
    if (received < 0) {
        saved_errno = errno == 0 ? EIO : errno;
        close(socket_fd);
        wifi_ctrl_monitor_reset(monitor);
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
    if (strncmp(reply, "OK", 2) != 0) {
        close(socket_fd);
        wifi_ctrl_monitor_reset(monitor);
        return -EIO;
    }
    monitor->attached = true;
    if (saved_errno_out != NULL) {
        *saved_errno_out = saved_errno;
    }
    return 0;
}

static void wifi_ctrl_monitor_close(struct wifi_ctrl_monitor *monitor) {
    static const char detach_cmd[] = "DETACH";

    if (monitor == NULL || monitor->socket_fd < 0) {
        return;
    }
    if (monitor->attached) {
        wifi_ctrl_monitor_drain(monitor, 100);
        (void)send(monitor->socket_fd, detach_cmd, strlen(detach_cmd), 0);
    }
    close(monitor->socket_fd);
    wifi_ctrl_monitor_reset(monitor);
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
    rc = wifi_prepare_dir_owned(A90_WIFI_CTRL_ROOT, 0755, 0, 0);
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

static int wifi_wait_ctrl_ready_at(const char *remote_path,
                                   pid_t pid,
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
        if (remote_path != NULL && access(remote_path, F_OK) == 0) {
            rc = wifi_ctrl_request_at(remote_path,
                                      "PING",
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

static int wifi_wait_ctrl_ready(pid_t pid,
                                bool spawned,
                                int timeout_ms,
                                int *elapsed_ms_out,
                                char *category,
                                size_t category_size,
                                int *ctrl_errno_out) {
    return wifi_wait_ctrl_ready_at(A90_WIFI_CTRL_SOCKET,
                                   pid,
                                   spawned,
                                   timeout_ms,
                                   elapsed_ms_out,
                                   category,
                                   category_size,
                                   ctrl_errno_out);
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

static int wifi_print_ctrl_result_at(const char *label, const char *remote_path, const char *command) {
    char category[32];
    char reply[4096];
    long reply_len = 0;
    int saved_errno = 0;
    int rc;

    rc = wifi_ctrl_request_at(remote_path,
                              command,
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

static int wifi_print_ctrl_result(const char *label, const char *command) {
    return wifi_print_ctrl_result_at(label, A90_WIFI_CTRL_SOCKET, command);
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
    char network_id[16];
    int network_selected;
    char key_mgmt[64];
    char pairwise_cipher[64];
    char group_cipher[64];
    char mode[32];
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
        (void)wifi_ctrl_reply_value(reply, "id", info->network_id, sizeof(info->network_id));
        (void)wifi_ctrl_reply_value(reply, "key_mgmt", info->key_mgmt, sizeof(info->key_mgmt));
        (void)wifi_ctrl_reply_value(reply, "pairwise_cipher", info->pairwise_cipher, sizeof(info->pairwise_cipher));
        (void)wifi_ctrl_reply_value(reply, "group_cipher", info->group_cipher, sizeof(info->group_cipher));
        (void)wifi_ctrl_reply_value(reply, "mode", info->mode, sizeof(info->mode));
        (void)wifi_ctrl_reply_value(reply, "freq", info->freq_mhz, sizeof(info->freq_mhz));
        info->network_selected = wifi_value_missing(info->network_id) ? 0 : 1;
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

static void wifi_autoconnect_record_wpa_state_sample(const char *state) {
    const char *selected = state != NULL && state[0] != '\0' ? state : "-";

    if (g_autoconnect_connect_diag.wpa_complete_samples == 0) {
        snprintf(g_autoconnect_connect_diag.wpa_complete_first_state,
                 sizeof(g_autoconnect_connect_diag.wpa_complete_first_state),
                 "%s",
                 selected);
    }
    g_autoconnect_connect_diag.wpa_complete_samples++;
    snprintf(g_autoconnect_connect_diag.wpa_complete_last_state,
             sizeof(g_autoconnect_connect_diag.wpa_complete_last_state),
             "%s",
             selected);
    if (strcmp(selected, "COMPLETED") == 0) {
        g_autoconnect_connect_diag.wpa_complete_completed = 1;
    }
}

static int wifi_wait_wpa_completed(struct wifi_ctrl_monitor *monitor,
                                   int timeout_ms,
                                   int *elapsed_ms_out) {
    long started_ms = monotonic_millis();
    long deadline_ms = started_ms + timeout_ms;
    long next_retry_ms = started_ms + A90_WIFI_CONNECT_WPA_RETRY_MS;

    if (elapsed_ms_out != NULL) {
        *elapsed_ms_out = 0;
    }
    if (timeout_ms <= 0) {
        return -ETIMEDOUT;
    }
    while (monotonic_millis() <= deadline_ms) {
        struct wifi_ctrl_link_info info;
        long now_ms;

        wifi_ctrl_monitor_drain(monitor, 0);
        wifi_collect_ctrl_link_info(&info);
        wifi_autoconnect_record_wpa_state_sample(info.wpa_state);
        if (strcmp(info.wpa_state, "COMPLETED") == 0) {
            if (elapsed_ms_out != NULL) {
                *elapsed_ms_out = (int)(monotonic_millis() - started_ms);
            }
            wifi_ctrl_monitor_drain(monitor, 0);
            return 0;
        }

        now_ms = monotonic_millis();
        if (now_ms >= next_retry_ms) {
            g_autoconnect_connect_diag.wpa_complete_retry_count++;
            (void)wifi_print_ctrl_result("ctrl.wpa_retry.enable_network", "ENABLE_NETWORK 0");
            (void)wifi_print_ctrl_result("ctrl.wpa_retry.select_network", "SELECT_NETWORK 0");
            (void)wifi_print_ctrl_result("ctrl.wpa_retry.reassociate", "REASSOCIATE");
            next_retry_ms = now_ms + A90_WIFI_CONNECT_WPA_RETRY_MS;
        }

        wifi_ctrl_monitor_drain(monitor, A90_WIFI_CONNECT_WPA_SAMPLE_MS);
    }
    if (elapsed_ms_out != NULL) {
        *elapsed_ms_out = timeout_ms;
    }
    return -ETIMEDOUT;
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

static int wifi_send_nl80211_iftype_new(int socket_fd,
                                        int family_id,
                                        uint32_t seq,
                                        uint32_t parent_ifindex,
                                        const char *ifname,
                                        uint32_t iftype) {
    char buffer[1024];
    struct nlmsghdr *nlh = (struct nlmsghdr *)buffer;
    struct genlmsghdr *genlh;
    struct sockaddr_nl addr;
    size_t offset;

    memset(buffer, 0, sizeof(buffer));
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(*genlh));
    nlh->nlmsg_type = (uint16_t)family_id;
    nlh->nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK;
    nlh->nlmsg_seq = seq;
    nlh->nlmsg_pid = 0;
    genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
    genlh->cmd = NL80211_CMD_NEW_INTERFACE;
    genlh->version = 1;
    offset = NLMSG_ALIGN(nlh->nlmsg_len);
    if (wifi_add_attr(buffer, sizeof(buffer), &offset, NL80211_ATTR_IFINDEX,
                      &parent_ifindex, sizeof(parent_ifindex)) < 0 ||
        wifi_add_attr(buffer, sizeof(buffer), &offset, NL80211_ATTR_IFNAME,
                      ifname, strlen(ifname) + 1) < 0 ||
        wifi_add_attr(buffer, sizeof(buffer), &offset, NL80211_ATTR_IFTYPE,
                      &iftype, sizeof(iftype)) < 0) {
        return -1;
    }
    nlh->nlmsg_len = (uint32_t)offset;

    memset(&addr, 0, sizeof(addr));
    addr.nl_family = AF_NETLINK;
    if (sendto(socket_fd, buffer, nlh->nlmsg_len, 0, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        return -1;
    }
    return wifi_recv_ack(socket_fd, seq);
}

static int wifi_send_nl80211_if_delete(int socket_fd,
                                       int family_id,
                                       uint32_t seq,
                                       uint32_t ifindex) {
    char buffer[512];
    struct nlmsghdr *nlh = (struct nlmsghdr *)buffer;
    struct genlmsghdr *genlh;
    struct sockaddr_nl addr;
    size_t offset;

    memset(buffer, 0, sizeof(buffer));
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(*genlh));
    nlh->nlmsg_type = (uint16_t)family_id;
    nlh->nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK;
    nlh->nlmsg_seq = seq;
    nlh->nlmsg_pid = 0;
    genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
    genlh->cmd = NL80211_CMD_DEL_INTERFACE;
    genlh->version = 1;
    offset = NLMSG_ALIGN(nlh->nlmsg_len);
    if (wifi_add_attr(buffer, sizeof(buffer), &offset, NL80211_ATTR_IFINDEX,
                      &ifindex, sizeof(ifindex)) < 0) {
        return -1;
    }
    nlh->nlmsg_len = (uint32_t)offset;

    memset(&addr, 0, sizeof(addr));
    addr.nl_family = AF_NETLINK;
    if (sendto(socket_fd, buffer, nlh->nlmsg_len, 0, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
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
    int wpa_complete_wait_elapsed_ms = 0;
    int wpa_complete_wait_rc = -ENOENT;
    int monitor_errno = 0;
    int ctrl_errno = 0;
    int wlan0_wait_rc;
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
    struct wifi_ctrl_monitor monitor;

    wifi_ctrl_monitor_reset(&monitor);
    wifi_autoconnect_reset_connect_diag();
    g_autoconnect_connect_diag.attempted = 1;
    wifi_autoconnect_set_connect_decision("wifi-connect-running");

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

    wlan0_wait_rc = wifi_wait_wlan0(A90_WIFI_CONNECT_WLAN0_WAIT_MS, &wlan0_wait_elapsed_ms);
    g_autoconnect_connect_diag.wlan0_wait_rc = wlan0_wait_rc;
    g_autoconnect_connect_diag.wlan0_wait_elapsed_ms = wlan0_wait_elapsed_ms;
    if (wlan0_wait_rc < 0) {
        a90_console_printf("wlan0_present=0\r\n");
        a90_console_printf("wlan0_wait_elapsed_ms=%d\r\n", wlan0_wait_elapsed_ms);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-wlan0-timeout\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-wlan0-timeout");
        return -ETIMEDOUT;
    }
    a90_console_printf("wlan0_present=1\r\n");
    a90_console_printf("wlan0_wait_elapsed_ms=%d\r\n", wlan0_wait_elapsed_ms);

    link_up_rc = wifi_link_set_up(A90_WIFI_IFACE, &link_up_errno);
    g_autoconnect_connect_diag.link_up_rc = link_up_rc;
    g_autoconnect_connect_diag.link_up_errno = link_up_errno;
    a90_console_printf("link_up_rc=%d\r\n", link_up_rc);
    a90_console_printf("link_up_errno=%d\r\n", link_up_errno);
    if (link_up_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-link-up-failed\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-link-up-failed");
        return -link_up_errno;
    }

    prepare_rc = a90_wificfg_prepare_supplicant_config(profile_name,
                                                       supplicant_config,
                                                       sizeof(supplicant_config));
    g_autoconnect_connect_diag.prepare_rc = prepare_rc;
    a90_console_printf("prepare_rc=%d\r\n", prepare_rc);
    a90_console_printf("supplicant_config.path=%s\r\n", A90_WIFICFG_SUPPLICANT_CONF);
    a90_console_printf("supplicant_config.present=%d\r\n",
                       access(A90_WIFICFG_SUPPLICANT_CONF, R_OK) == 0 ? 1 : 0);
    if (prepare_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-config-prepare-failed\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-config-prepare-failed");
        return prepare_rc;
    }

    runtime_rc = wifi_prepare_runtime_dirs();
    g_autoconnect_connect_diag.runtime_prepare_rc = runtime_rc;
    a90_console_printf("runtime_prepare_rc=%d\r\n", runtime_rc);
    a90_console_printf("ctrl_socket.dir=%s\r\n", A90_WIFI_CTRL_DIR);
    if (runtime_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-runtime-prepare-failed\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-runtime-prepare-failed");
        return runtime_rc;
    }

    a90_console_printf("supplicant.path=%s\r\n", A90_WIFI_STANDALONE_SUPPLICANT);
    a90_console_printf("supplicant.executable=%d\r\n",
                       access(A90_WIFI_STANDALONE_SUPPLICANT, X_OK) == 0 ? 1 : 0);
    supplicant_root_exec_rc = wifi_verify_root_exec_file(A90_WIFI_STANDALONE_SUPPLICANT, true);
    g_autoconnect_connect_diag.supplicant_root_exec_rc = supplicant_root_exec_rc;
    a90_console_printf("supplicant.root_exec_rc=%d\r\n", supplicant_root_exec_rc);
    a90_console_printf("supplicant.root_exec_ok=%d\r\n", supplicant_root_exec_rc == 0 ? 1 : 0);
    a90_console_printf("supplicant_log.path=%s\r\n", A90_WIFI_SUPPLICANT_LOG);
    if (access(A90_WIFI_STANDALONE_SUPPLICANT, X_OK) < 0) {
        int saved_errno = errno;

        a90_console_printf("supplicant_errno=%d\r\n", saved_errno);
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-supplicant-missing\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-supplicant-missing");
        return -saved_errno;
    }
    if (supplicant_root_exec_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-supplicant-unsafe\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-supplicant-unsafe");
        return supplicant_root_exec_rc;
    }

    supplicant_process_count = wifi_count_processes_with_token("wpa_supplicant");
    g_autoconnect_connect_diag.supplicant_process_count_before = supplicant_process_count;
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
                wifi_autoconnect_set_connect_decision("wifi-connect-supplicant-terminate-timeout");
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
    g_autoconnect_connect_diag.supplicant_start_rc = supplicant_start_rc;
    a90_console_printf("supplicant_start_rc=%d\r\n", supplicant_start_rc);
    a90_console_printf("supplicant_pid=%ld\r\n", supplicant_start_rc == 0 ? (long)supplicant_pid : -1L);
    if (supplicant_start_rc < 0) {
        a90_console_printf("secret_values_logged=0\r\n");
        a90_console_printf("decision=wifi-connect-supplicant-start-failed\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-supplicant-start-failed");
        return supplicant_start_rc;
    }
    spawned_supplicant = true;
    g_autoconnect_connect_diag.supplicant_spawned = 1;
    ctrl_ready_rc = wifi_wait_ctrl_ready(supplicant_pid,
                                         true,
                                         A90_WIFI_CONNECT_CTRL_WAIT_MS,
                                         &ctrl_wait_elapsed_ms,
                                         ctrl_category,
                                         sizeof(ctrl_category),
                                         &ctrl_errno);
    g_autoconnect_connect_diag.ctrl_wait_rc = ctrl_ready_rc;
    g_autoconnect_connect_diag.ctrl_wait_errno = ctrl_errno;
    g_autoconnect_connect_diag.ctrl_wait_elapsed_ms = ctrl_wait_elapsed_ms;
    snprintf(g_autoconnect_connect_diag.ctrl_wait_category,
             sizeof(g_autoconnect_connect_diag.ctrl_wait_category),
             "%s",
             ctrl_ready_rc == 0 ? ctrl_category : "error");
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
        g_autoconnect_connect_diag.cleanup_status = terminate_status;
        wifi_autoconnect_set_connect_decision("wifi-connect-ctrl-timeout");
        return ctrl_ready_rc;
    }

    g_autoconnect_connect_diag.wpa_monitor_attach_rc =
        wifi_ctrl_monitor_attach(&monitor, A90_WIFI_CTRL_SOCKET, &monitor_errno);
    g_autoconnect_connect_diag.wpa_monitor_attach_errno = monitor_errno;
    a90_console_printf("ctrl.monitor_attach_rc=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_attach_rc);
    a90_console_printf("ctrl.monitor_attach_errno=%d\r\n", monitor_errno);

    g_autoconnect_connect_diag.ctrl_driver_country_rc =
        wifi_print_ctrl_result("ctrl.driver_country", "DRIVER COUNTRY KR");
    g_autoconnect_connect_diag.ctrl_scan_rc = wifi_print_ctrl_result("ctrl.scan", "SCAN");
    g_autoconnect_connect_diag.ctrl_enable_network_rc =
        wifi_print_ctrl_result("ctrl.enable_network", "ENABLE_NETWORK 0");
    g_autoconnect_connect_diag.ctrl_select_network_rc =
        wifi_print_ctrl_result("ctrl.select_network", "SELECT_NETWORK 0");
    g_autoconnect_connect_diag.ctrl_reassociate_rc =
        wifi_print_ctrl_result("ctrl.reassociate", "REASSOCIATE");

    if (carrier_wait_timeout_ms <= 0) {
        carrier_wait_timeout_ms = A90_WIFI_CONNECT_CARRIER_WAIT_MS;
    }
    a90_console_printf("carrier_wait_timeout_ms=%d\r\n", carrier_wait_timeout_ms);
    carrier_rc = wifi_wait_carrier(carrier_wait_timeout_ms, &carrier_wait_elapsed_ms);
    g_autoconnect_connect_diag.carrier_wait_rc = carrier_rc;
    g_autoconnect_connect_diag.carrier_wait_elapsed_ms = carrier_wait_elapsed_ms;
    g_autoconnect_connect_diag.carrier_up_at_wait = carrier_rc == 0 ? 1 : 0;
    a90_console_printf("carrier_wait_rc=%d\r\n", carrier_rc);
    a90_console_printf("carrier_wait_elapsed_ms=%d\r\n", carrier_wait_elapsed_ms);
    a90_console_printf("carrier_up=%d\r\n", carrier_rc == 0 ? 1 : 0);
    if (carrier_rc == 0) {
        wpa_complete_wait_rc = wifi_wait_wpa_completed(&monitor,
                                                       A90_WIFI_CONNECT_WPA_COMPLETE_WAIT_MS,
                                                       &wpa_complete_wait_elapsed_ms);
    } else {
        wpa_complete_wait_rc = carrier_rc;
        wpa_complete_wait_elapsed_ms = carrier_wait_elapsed_ms;
    }
    g_autoconnect_connect_diag.wpa_complete_wait_rc = wpa_complete_wait_rc;
    g_autoconnect_connect_diag.wpa_complete_wait_elapsed_ms = wpa_complete_wait_elapsed_ms;
    a90_console_printf("wpa_complete_wait_timeout_ms=%d\r\n",
                       A90_WIFI_CONNECT_WPA_COMPLETE_WAIT_MS);
    a90_console_printf("wpa_complete_wait_rc=%d\r\n", wpa_complete_wait_rc);
    a90_console_printf("wpa_complete_wait_elapsed_ms=%d\r\n", wpa_complete_wait_elapsed_ms);
    a90_console_printf("wpa_complete_samples=%d\r\n",
                       g_autoconnect_connect_diag.wpa_complete_samples);
    a90_console_printf("wpa_complete_first_state=%s\r\n",
                       g_autoconnect_connect_diag.wpa_complete_first_state);
    a90_console_printf("wpa_complete_last_state=%s\r\n",
                       g_autoconnect_connect_diag.wpa_complete_last_state);
    a90_console_printf("wpa_complete_completed=%d\r\n",
                       g_autoconnect_connect_diag.wpa_complete_completed);
    a90_console_printf("wpa_complete_retry_count=%d\r\n",
                       g_autoconnect_connect_diag.wpa_complete_retry_count);
    a90_console_printf("wpa_monitor_event_count=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_event_count);
    a90_console_printf("wpa_monitor_connected_seen=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_connected_seen);
    a90_console_printf("wpa_monitor_disconnected_seen=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_disconnected_seen);
    a90_console_printf("wpa_monitor_scan_results_seen=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_scan_results_seen);
    a90_console_printf("wpa_monitor_assoc_reject_seen=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_assoc_reject_seen);
    a90_console_printf("wpa_monitor_auth_reject_seen=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_auth_reject_seen);
    a90_console_printf("wpa_monitor_temp_disabled_seen=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_temp_disabled_seen);
    a90_console_printf("wpa_monitor_eap_failure_seen=%d\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_eap_failure_seen);
    a90_console_printf("wpa_monitor_last_event=%s\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_last_event);
    a90_console_printf("wpa_monitor_disconnect_reason_class=%s\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_disconnect_reason_class);
    a90_console_printf("wpa_monitor_temp_disabled_reason_class=%s\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_temp_disabled_reason_class);
    a90_console_printf("wpa_monitor_assoc_reject_status_class=%s\r\n",
                       g_autoconnect_connect_diag.wpa_monitor_assoc_reject_status_class);
    status_rc = wifi_print_ctrl_result("ctrl.status", "STATUS");
    wifi_collect_ctrl_link_info(&status_info);
    (void)status_rc;
    g_autoconnect_connect_diag.ctrl_status_rc = status_info.status_rc;
    g_autoconnect_connect_diag.ctrl_status_errno = status_info.status_errno;
    g_autoconnect_connect_diag.ctrl_signal_rc = status_info.signal_rc;
    g_autoconnect_connect_diag.ctrl_signal_errno = status_info.signal_errno;
    snprintf(g_autoconnect_connect_diag.ctrl_status_wpa_state,
             sizeof(g_autoconnect_connect_diag.ctrl_status_wpa_state),
             "%s",
             status_info.wpa_state[0] != '\0' ? status_info.wpa_state : "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_network_id,
             sizeof(g_autoconnect_connect_diag.ctrl_status_network_id),
             "%s",
             status_info.network_id[0] != '\0' ? status_info.network_id : "-");
    g_autoconnect_connect_diag.ctrl_status_network_selected = status_info.network_selected;
    snprintf(g_autoconnect_connect_diag.ctrl_status_key_mgmt,
             sizeof(g_autoconnect_connect_diag.ctrl_status_key_mgmt),
             "%s",
             status_info.key_mgmt[0] != '\0' ? status_info.key_mgmt : "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_pairwise_cipher,
             sizeof(g_autoconnect_connect_diag.ctrl_status_pairwise_cipher),
             "%s",
             status_info.pairwise_cipher[0] != '\0' ? status_info.pairwise_cipher : "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_group_cipher,
             sizeof(g_autoconnect_connect_diag.ctrl_status_group_cipher),
             "%s",
             status_info.group_cipher[0] != '\0' ? status_info.group_cipher : "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_mode,
             sizeof(g_autoconnect_connect_diag.ctrl_status_mode),
             "%s",
             status_info.mode[0] != '\0' ? status_info.mode : "-");
    snprintf(g_autoconnect_connect_diag.ctrl_status_freq_mhz,
             sizeof(g_autoconnect_connect_diag.ctrl_status_freq_mhz),
             "%s",
             status_info.freq_mhz[0] != '\0' ? status_info.freq_mhz : "-");
    g_autoconnect_connect_diag.ctrl_status_completed =
        strcmp(status_info.wpa_state, "COMPLETED") == 0 ? 1 : 0;
    a90_console_printf("ctrl.status_confirm.rc=%d\r\n", status_info.status_rc);
    a90_console_printf("ctrl.status_confirm.errno=%d\r\n", status_info.status_errno);
    a90_console_printf("ctrl.status_confirm.field.wpa_state=%s\r\n",
                       status_info.wpa_state[0] != '\0' ? status_info.wpa_state : "-");
    a90_console_printf("ctrl.status_confirm.field.freq=%s\r\n",
                       status_info.freq_mhz[0] != '\0' ? status_info.freq_mhz : "-");
    a90_console_printf("ctrl.status_confirm.field.id=%s\r\n",
                       status_info.network_id[0] != '\0' ? status_info.network_id : "-");
    a90_console_printf("ctrl.status_confirm.network_selected=%d\r\n",
                       status_info.network_selected);
    a90_console_printf("ctrl.status_confirm.field.key_mgmt=%s\r\n",
                       status_info.key_mgmt[0] != '\0' ? status_info.key_mgmt : "-");
    a90_console_printf("ctrl.status_confirm.field.pairwise_cipher=%s\r\n",
                       status_info.pairwise_cipher[0] != '\0' ? status_info.pairwise_cipher : "-");
    a90_console_printf("ctrl.status_confirm.field.group_cipher=%s\r\n",
                       status_info.group_cipher[0] != '\0' ? status_info.group_cipher : "-");
    a90_console_printf("ctrl.status_confirm.field.mode=%s\r\n",
                       status_info.mode[0] != '\0' ? status_info.mode : "-");
    a90_console_printf("ctrl.status_confirm.completed=%d\r\n",
                       strcmp(status_info.wpa_state, "COMPLETED") == 0 ? 1 : 0);
    a90_console_printf("supplicant.reused=%d\r\n", reusing_supplicant ? 1 : 0);
    a90_console_printf("supplicant.spawned=%d\r\n", spawned_supplicant ? 1 : 0);
    a90_console_printf("supplicant.left_running=%d\r\n",
                       carrier_rc == 0 && strcmp(status_info.wpa_state, "COMPLETED") == 0 ? 1 : 0);
    g_autoconnect_connect_diag.supplicant_left_running =
        carrier_rc == 0 && strcmp(status_info.wpa_state, "COMPLETED") == 0 ? 1 : 0;
    a90_console_printf("status_request_rc=%d\r\n", status_rc);
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("dhcp_routing=0\r\n");
    a90_console_printf("external_ping=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");

    if (carrier_rc == 0 && strcmp(status_info.wpa_state, "COMPLETED") == 0) {
        wifi_ctrl_monitor_close(&monitor);
        a90_logf("wifi",
                 "connect profile=%s carrier=1 wpa_state=COMPLETED reused=%d spawned=%d secret_values_logged=0",
                 profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
                 reusing_supplicant ? 1 : 0,
                 spawned_supplicant ? 1 : 0);
        a90_console_printf("decision=wifi-connect-carrier-up\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-carrier-up");
        return 0;
    }

    if (carrier_rc == 0) {
        wifi_ctrl_monitor_close(&monitor);
        (void)wifi_print_ctrl_result("ctrl.terminate", "TERMINATE");
        (void)a90_run_stop_pid_ex(supplicant_pid,
                                  "wifi-supplicant",
                                  3000,
                                  true,
                                  &terminate_status);
        g_autoconnect_connect_diag.cleanup_status = terminate_status;
        a90_console_printf("supplicant_cleanup_status=%d\r\n", terminate_status);
        a90_logf("wifi",
                 "connect profile=%s carrier=1 wpa_state=%s reused=%d spawned=%d secret_values_logged=0",
                 profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
                 status_info.wpa_state[0] != '\0' ? status_info.wpa_state : "-",
                 reusing_supplicant ? 1 : 0,
                 spawned_supplicant ? 1 : 0);
        a90_console_printf("decision=wifi-connect-status-not-completed\r\n");
        wifi_autoconnect_set_connect_decision("wifi-connect-status-not-completed");
        return -ENOTCONN;
    }

    if (spawned_supplicant) {
        wifi_ctrl_monitor_close(&monitor);
        (void)wifi_print_ctrl_result("ctrl.terminate", "TERMINATE");
        (void)a90_run_stop_pid_ex(supplicant_pid,
                                  "wifi-supplicant",
                                  3000,
                                  true,
                                  &terminate_status);
        g_autoconnect_connect_diag.cleanup_status = terminate_status;
        a90_console_printf("supplicant_cleanup_status=%d\r\n", terminate_status);
    }
    wifi_ctrl_monitor_close(&monitor);
    a90_logf("wifi",
             "connect profile=%s carrier=0 reused=%d spawned=%d secret_values_logged=0",
             profile_name != NULL && profile_name[0] != '\0' ? profile_name : "default",
             reusing_supplicant ? 1 : 0,
             spawned_supplicant ? 1 : 0);
    a90_console_printf("decision=wifi-connect-no-carrier\r\n");
    wifi_autoconnect_set_connect_decision("wifi-connect-no-carrier");
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
    char text[12288];
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
                   "scan_recovery_attempted=%d\n"
                   "scan_recovery_first_scan_rc=%d\n"
                   "scan_recovery_rc=%d\n"
                   "scan_recovery_rescan_rc=%d\n"
                   "scan_recovery_success=%d\n"
                   "scan_recovery_decision=%s\n"
                   "connect_diag_attempted=%d\n"
                   "connect_diag_decision=%s\n"
                   "connect_wlan0_wait_rc=%d\n"
                   "connect_wlan0_wait_elapsed_ms=%d\n"
                   "connect_link_up_rc=%d\n"
                   "connect_link_up_errno=%d\n"
                   "connect_prepare_rc=%d\n"
                   "connect_runtime_prepare_rc=%d\n"
                   "connect_supplicant_root_exec_rc=%d\n"
                   "connect_supplicant_process_count_before=%d\n"
                   "connect_supplicant_start_rc=%d\n"
                   "connect_ctrl_wait_rc=%d\n"
                   "connect_ctrl_wait_errno=%d\n"
                   "connect_ctrl_wait_elapsed_ms=%d\n"
                   "connect_ctrl_wait_category=%s\n"
                   "connect_ctrl_driver_country_rc=%d\n"
                   "connect_ctrl_scan_rc=%d\n"
                   "connect_ctrl_enable_network_rc=%d\n"
                   "connect_ctrl_select_network_rc=%d\n"
                   "connect_ctrl_reassociate_rc=%d\n"
                   "connect_carrier_wait_rc=%d\n"
                   "connect_carrier_wait_elapsed_ms=%d\n"
                   "connect_carrier_up_at_wait=%d\n"
                   "connect_wpa_complete_wait_rc=%d\n"
                   "connect_wpa_complete_wait_elapsed_ms=%d\n"
                   "connect_wpa_complete_samples=%d\n"
                   "connect_wpa_complete_completed=%d\n"
                   "connect_wpa_complete_retry_count=%d\n"
                   "connect_wpa_complete_first_state=%s\n"
                   "connect_wpa_complete_last_state=%s\n"
                   "connect_wpa_monitor_attach_rc=%d\n"
                   "connect_wpa_monitor_attach_errno=%d\n"
                   "connect_wpa_monitor_event_count=%d\n"
                   "connect_wpa_monitor_connected_seen=%d\n"
                   "connect_wpa_monitor_disconnected_seen=%d\n"
                   "connect_wpa_monitor_scan_results_seen=%d\n"
                   "connect_wpa_monitor_assoc_reject_seen=%d\n"
                   "connect_wpa_monitor_auth_reject_seen=%d\n"
                   "connect_wpa_monitor_temp_disabled_seen=%d\n"
                   "connect_wpa_monitor_eap_failure_seen=%d\n"
                   "connect_wpa_monitor_last_event=%s\n"
                   "connect_wpa_monitor_disconnect_reason_class=%s\n"
                   "connect_wpa_monitor_temp_disabled_reason_class=%s\n"
                   "connect_wpa_monitor_assoc_reject_status_class=%s\n"
                   "connect_ctrl_status_rc=%d\n"
                   "connect_ctrl_status_errno=%d\n"
                   "connect_ctrl_status_wpa_state=%s\n"
                   "connect_ctrl_status_network_id=%s\n"
                   "connect_ctrl_status_network_selected=%d\n"
                   "connect_ctrl_status_key_mgmt=%s\n"
                   "connect_ctrl_status_pairwise_cipher=%s\n"
                   "connect_ctrl_status_group_cipher=%s\n"
                   "connect_ctrl_status_mode=%s\n"
                   "connect_ctrl_status_freq_mhz=%s\n"
                   "connect_ctrl_status_completed=%d\n"
                   "connect_ctrl_signal_rc=%d\n"
                   "connect_ctrl_signal_errno=%d\n"
                   "connect_supplicant_spawned=%d\n"
                   "connect_supplicant_left_running=%d\n"
                   "connect_cleanup_status=%d\n"
                   "secret_values_logged=0\n",
                   decision != NULL ? decision : "wifi-autoconnect-unknown",
                   profile != NULL && profile[0] != '\0' ? profile : "default",
                   connect_rc,
                   dhcp_rc,
                   final_rc,
                   wifi_carrier_up() ? 1 : 0,
                   wifi_default_route_present() ? 1 : 0,
                   wifi_count_resolv_nameservers(),
                   g_autoconnect_scan_recovery.attempted,
                   g_autoconnect_scan_recovery.first_scan_rc,
                   g_autoconnect_scan_recovery.rc,
                   g_autoconnect_scan_recovery.rescan_rc,
                   g_autoconnect_scan_recovery.success,
                   g_autoconnect_scan_recovery.decision,
                   g_autoconnect_connect_diag.attempted,
                   g_autoconnect_connect_diag.decision,
                   g_autoconnect_connect_diag.wlan0_wait_rc,
                   g_autoconnect_connect_diag.wlan0_wait_elapsed_ms,
                   g_autoconnect_connect_diag.link_up_rc,
                   g_autoconnect_connect_diag.link_up_errno,
                   g_autoconnect_connect_diag.prepare_rc,
                   g_autoconnect_connect_diag.runtime_prepare_rc,
                   g_autoconnect_connect_diag.supplicant_root_exec_rc,
                   g_autoconnect_connect_diag.supplicant_process_count_before,
                   g_autoconnect_connect_diag.supplicant_start_rc,
                   g_autoconnect_connect_diag.ctrl_wait_rc,
                   g_autoconnect_connect_diag.ctrl_wait_errno,
                   g_autoconnect_connect_diag.ctrl_wait_elapsed_ms,
                   g_autoconnect_connect_diag.ctrl_wait_category,
                   g_autoconnect_connect_diag.ctrl_driver_country_rc,
                   g_autoconnect_connect_diag.ctrl_scan_rc,
                   g_autoconnect_connect_diag.ctrl_enable_network_rc,
                   g_autoconnect_connect_diag.ctrl_select_network_rc,
                   g_autoconnect_connect_diag.ctrl_reassociate_rc,
                   g_autoconnect_connect_diag.carrier_wait_rc,
                   g_autoconnect_connect_diag.carrier_wait_elapsed_ms,
                   g_autoconnect_connect_diag.carrier_up_at_wait,
                   g_autoconnect_connect_diag.wpa_complete_wait_rc,
                   g_autoconnect_connect_diag.wpa_complete_wait_elapsed_ms,
                   g_autoconnect_connect_diag.wpa_complete_samples,
                   g_autoconnect_connect_diag.wpa_complete_completed,
                   g_autoconnect_connect_diag.wpa_complete_retry_count,
                   g_autoconnect_connect_diag.wpa_complete_first_state,
                   g_autoconnect_connect_diag.wpa_complete_last_state,
                   g_autoconnect_connect_diag.wpa_monitor_attach_rc,
                   g_autoconnect_connect_diag.wpa_monitor_attach_errno,
                   g_autoconnect_connect_diag.wpa_monitor_event_count,
                   g_autoconnect_connect_diag.wpa_monitor_connected_seen,
                   g_autoconnect_connect_diag.wpa_monitor_disconnected_seen,
                   g_autoconnect_connect_diag.wpa_monitor_scan_results_seen,
                   g_autoconnect_connect_diag.wpa_monitor_assoc_reject_seen,
                   g_autoconnect_connect_diag.wpa_monitor_auth_reject_seen,
                   g_autoconnect_connect_diag.wpa_monitor_temp_disabled_seen,
                   g_autoconnect_connect_diag.wpa_monitor_eap_failure_seen,
                   g_autoconnect_connect_diag.wpa_monitor_last_event,
                   g_autoconnect_connect_diag.wpa_monitor_disconnect_reason_class,
                   g_autoconnect_connect_diag.wpa_monitor_temp_disabled_reason_class,
                   g_autoconnect_connect_diag.wpa_monitor_assoc_reject_status_class,
                   g_autoconnect_connect_diag.ctrl_status_rc,
                   g_autoconnect_connect_diag.ctrl_status_errno,
                   g_autoconnect_connect_diag.ctrl_status_wpa_state,
                   g_autoconnect_connect_diag.ctrl_status_network_id,
                   g_autoconnect_connect_diag.ctrl_status_network_selected,
                   g_autoconnect_connect_diag.ctrl_status_key_mgmt,
                   g_autoconnect_connect_diag.ctrl_status_pairwise_cipher,
                   g_autoconnect_connect_diag.ctrl_status_group_cipher,
                   g_autoconnect_connect_diag.ctrl_status_mode,
                   g_autoconnect_connect_diag.ctrl_status_freq_mhz,
                   g_autoconnect_connect_diag.ctrl_status_completed,
                   g_autoconnect_connect_diag.ctrl_signal_rc,
                   g_autoconnect_connect_diag.ctrl_signal_errno,
                   g_autoconnect_connect_diag.supplicant_spawned,
                   g_autoconnect_connect_diag.supplicant_left_running,
                   g_autoconnect_connect_diag.cleanup_status);
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
    wifi_autoconnect_reset_scan_recovery();
    wifi_autoconnect_reset_connect_diag();
    wifi_reset_autoconnect_log(profile, boot_background);
    (void)wifi_write_autoconnect_result(selected_decision, profile, 0, 0, final_rc);
    (void)wifi_write_runtime_summary(selected_decision);
}

static int wifi_autoconnect_recover_scan_state(int failed_scan_rc,
                                               const char *profile,
                                               int attempt,
                                               bool boot_background) {
    int recovery_rc;
    int rescan_rc;

    g_autoconnect_scan_recovery.attempted = 1;
    g_autoconnect_scan_recovery.first_scan_rc = failed_scan_rc;
    g_autoconnect_scan_recovery.rc = 0;
    g_autoconnect_scan_recovery.rescan_rc = 0;
    g_autoconnect_scan_recovery.success = 0;
    snprintf(g_autoconnect_scan_recovery.decision,
             sizeof(g_autoconnect_scan_recovery.decision),
             "%s",
             "wifi-autoconnect-scan-recovery-running");

    wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                          "event=scan-recovery-start profile=%s attempt=%d first_scan_rc=%d\n",
                          profile != NULL && profile[0] != '\0' ? profile : "default",
                          attempt,
                          failed_scan_rc);
    if (!boot_background) {
        a90_console_printf("autoconnect.scan_recovery_attempted=1\r\n");
        a90_console_printf("autoconnect.scan_recovery_first_scan_rc=%d\r\n", failed_scan_rc);
    }

    (void)a90_wifi_cleanup();
    recovery_rc = wifi_softap_iftype_probe(A90_WIFI_SOFTAP_WLAN0_WAIT_MS);
    g_autoconnect_scan_recovery.rc = recovery_rc;
    if (!boot_background) {
        a90_console_printf("autoconnect.scan_recovery_rc=%d\r\n", recovery_rc);
    }
    if (recovery_rc < 0) {
        snprintf(g_autoconnect_scan_recovery.decision,
                 sizeof(g_autoconnect_scan_recovery.decision),
                 "%s",
                 "wifi-autoconnect-scan-recovery-probe-failed");
        wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                              "event=scan-recovery-probe-failed profile=%s attempt=%d rc=%d\n",
                              profile != NULL && profile[0] != '\0' ? profile : "default",
                              attempt,
                              recovery_rc);
        if (!boot_background) {
            a90_console_printf("autoconnect.scan_recovery_success=0\r\n");
            a90_console_printf("autoconnect.scan_recovery_decision=%s\r\n",
                               g_autoconnect_scan_recovery.decision);
        }
        return failed_scan_rc;
    }

    rescan_rc = a90_wifi_scan_once(5000);
    g_autoconnect_scan_recovery.rescan_rc = rescan_rc;
    g_autoconnect_scan_recovery.success = rescan_rc >= 0 ? 1 : 0;
    snprintf(g_autoconnect_scan_recovery.decision,
             sizeof(g_autoconnect_scan_recovery.decision),
             "%s",
             rescan_rc >= 0 ?
             "wifi-autoconnect-scan-recovery-pass" :
             "wifi-autoconnect-scan-recovery-rescan-failed");
    wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                          "event=scan-recovery-rescan profile=%s attempt=%d rc=%d success=%d\n",
                          profile != NULL && profile[0] != '\0' ? profile : "default",
                          attempt,
                          rescan_rc,
                          g_autoconnect_scan_recovery.success);
    if (!boot_background) {
        a90_console_printf("autoconnect.scan_recovery_rescan_rc=%d\r\n", rescan_rc);
        a90_console_printf("autoconnect.scan_recovery_success=%d\r\n",
                           g_autoconnect_scan_recovery.success);
        a90_console_printf("autoconnect.scan_recovery_decision=%s\r\n",
                           g_autoconnect_scan_recovery.decision);
    }
    return rescan_rc;
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
    wifi_autoconnect_reset_scan_recovery();
    wifi_autoconnect_reset_connect_diag();
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
                if (!g_autoconnect_scan_recovery.attempted) {
                    scan_rc = wifi_autoconnect_recover_scan_state(scan_rc,
                                                                  selected_profile,
                                                                  attempt,
                                                                  boot_background);
                    if (!boot_background) {
                        a90_console_printf("autoconnect.scan_rc_after_recovery=%d\r\n", scan_rc);
                    }
                    if (scan_rc >= 0) {
                        wifi_append_text_file(A90_WIFI_AUTOCONNECT_LOG,
                                              "event=scan-recovered profile=%s attempt=%d rc=%d\n",
                                              selected_profile != NULL && selected_profile[0] != '\0' ?
                                              selected_profile : "default",
                                              attempt,
                                              scan_rc);
                    }
                }
            }
            if (scan_rc < 0) {
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

static int wifi_softap_channel_to_freq(int channel) {
    if (channel == 1) {
        return 2412;
    }
    if (channel == 6) {
        return 2437;
    }
    if (channel == 11) {
        return 2462;
    }
    return -EINVAL;
}

static int wifi_softap_parse_channel(const char *text, int *channel_out, int *freq_out) {
    char *endptr = NULL;
    long channel;
    int freq;

    if (channel_out == NULL || freq_out == NULL) {
        return -EINVAL;
    }
    if (text == NULL || text[0] == '\0') {
        *channel_out = 6;
        *freq_out = wifi_softap_channel_to_freq(*channel_out);
        return 0;
    }
    errno = 0;
    channel = strtol(text, &endptr, 10);
    if (errno != 0 || endptr == text || *endptr != '\0' ||
        channel < 1 || channel > 11) {
        return -EINVAL;
    }
    freq = wifi_softap_channel_to_freq((int)channel);
    if (freq < 0) {
        return freq;
    }
    *channel_out = (int)channel;
    *freq_out = freq;
    return 0;
}

static int wifi_softap_format_ipv4(int host, char *out, size_t out_size) {
    int len;

    if (out == NULL || out_size == 0 || host < 1 || host > 254) {
        return -EINVAL;
    }
    len = snprintf(out,
                   out_size,
                   "%d.%d.%d.%d",
                   A90_WIFI_SOFTAP_NET_A,
                   A90_WIFI_SOFTAP_NET_B,
                   A90_WIFI_SOFTAP_NET_C,
                   host);
    if (len < 0 || (size_t)len >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

static int wifi_random_bytes(unsigned char *buffer, size_t buffer_size) {
    size_t offset = 0;
    int fd;

    if (buffer == NULL || buffer_size == 0) {
        return -EINVAL;
    }
    fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -errno;
    }
    while (offset < buffer_size) {
        ssize_t got = read(fd, buffer + offset, buffer_size - offset);

        if (got < 0) {
            int saved_errno = errno;

            close(fd);
            return -saved_errno;
        }
        if (got == 0) {
            close(fd);
            return -EIO;
        }
        offset += (size_t)got;
    }
    close(fd);
    return 0;
}

static int wifi_hex_encode(const unsigned char *input,
                           size_t input_size,
                           char *out,
                           size_t out_size) {
    static const char hex[] = "0123456789abcdef";
    size_t index;

    if (input == NULL || out == NULL || out_size < input_size * 2U + 1U) {
        return -EINVAL;
    }
    for (index = 0; index < input_size; ++index) {
        out[index * 2U] = hex[(input[index] >> 4) & 0x0fU];
        out[index * 2U + 1U] = hex[input[index] & 0x0fU];
    }
    out[input_size * 2U] = '\0';
    return 0;
}

static int wifi_write_pid_file(const char *path, pid_t pid) {
    char text[32];
    int len;

    if (path == NULL || pid <= 0) {
        return -EINVAL;
    }
    len = snprintf(text, sizeof(text), "%ld\n", (long)pid);
    if (len < 0 || (size_t)len >= sizeof(text)) {
        return -ENAMETOOLONG;
    }
    return wifi_write_text_file(path, text, 0600);
}

static int wifi_read_pid_file(const char *path, pid_t *pid_out) {
    char text[64];
    char *endptr = NULL;
    long value;

    if (path == NULL || pid_out == NULL) {
        return -EINVAL;
    }
    if (read_trimmed_text_file(path, text, sizeof(text)) < 0) {
        return -errno;
    }
    errno = 0;
    value = strtol(text, &endptr, 10);
    if (errno != 0 || endptr == text || *endptr != '\0' || value <= 1) {
        return -EINVAL;
    }
    *pid_out = (pid_t)value;
    return 0;
}

static int wifi_stop_pid_file(const char *path, const char *label, bool kill_process_group) {
    pid_t pid = -1;
    int read_rc;
    int stop_rc = 0;
    int status = 0;

    read_rc = wifi_read_pid_file(path, &pid);
    a90_console_printf("%s.pid_read_rc=%d\r\n", label, read_rc);
    a90_console_printf("%s.pid=%ld\r\n", label, read_rc == 0 ? (long)pid : -1L);
    if (read_rc == 0) {
        stop_rc = a90_run_stop_pid_ex(pid, label, 3000, kill_process_group, &status);
        a90_console_printf("%s.stop_attempted=1\r\n", label);
        a90_console_printf("%s.stop_rc=%d\r\n", label, stop_rc);
        a90_console_printf("%s.stop_status=%d\r\n", label, status);
    } else {
        a90_console_printf("%s.stop_attempted=0\r\n", label);
        a90_console_printf("%s.stop_rc=0\r\n", label);
        a90_console_printf("%s.stop_status=0\r\n", label);
    }
    (void)unlink(path);
    return read_rc == -ENOENT ? 0 : (stop_rc < 0 ? stop_rc : 0);
}

static int wifi_stop_process_token(const char *token, const char *label) {
    int before_count = wifi_count_processes_with_token(token);
    int term_rc = 0;
    int term_wait_rc = 0;
    int term_wait_elapsed_ms = 0;
    int kill_rc = 0;
    int kill_wait_rc = 0;
    int kill_wait_elapsed_ms = 0;
    int final_count;

    a90_console_printf("%s.token_process_count_before=%d\r\n", label, before_count);
    if (before_count <= 0) {
        a90_console_printf("%s.token_term_attempted=0\r\n", label);
        a90_console_printf("%s.token_kill_attempted=0\r\n", label);
        a90_console_printf("%s.token_process_count_final=%d\r\n",
                           label,
                           before_count < 0 ? before_count : 0);
        return before_count < 0 ? before_count : 0;
    }

    term_rc = wifi_signal_processes_with_token(token, SIGTERM);
    term_wait_rc = wifi_wait_processes_gone(token, 3000, &term_wait_elapsed_ms);
    a90_console_printf("%s.token_term_attempted=1\r\n", label);
    a90_console_printf("%s.token_term_rc=%d\r\n", label, term_rc);
    a90_console_printf("%s.token_term_wait_rc=%d\r\n", label, term_wait_rc);
    a90_console_printf("%s.token_term_wait_elapsed_ms=%d\r\n", label, term_wait_elapsed_ms);
    if (term_wait_rc < 0) {
        kill_rc = wifi_signal_processes_with_token(token, SIGKILL);
        kill_wait_rc = wifi_wait_processes_gone(token, 1500, &kill_wait_elapsed_ms);
        a90_console_printf("%s.token_kill_attempted=1\r\n", label);
        a90_console_printf("%s.token_kill_rc=%d\r\n", label, kill_rc);
        a90_console_printf("%s.token_kill_wait_rc=%d\r\n", label, kill_wait_rc);
        a90_console_printf("%s.token_kill_wait_elapsed_ms=%d\r\n", label, kill_wait_elapsed_ms);
    } else {
        a90_console_printf("%s.token_kill_attempted=0\r\n", label);
        a90_console_printf("%s.token_kill_rc=0\r\n", label);
        a90_console_printf("%s.token_kill_wait_rc=0\r\n", label);
    }
    final_count = wifi_count_processes_with_token(token);
    a90_console_printf("%s.token_process_count_final=%d\r\n", label, final_count);
    if (final_count != 0) {
        return -EBUSY;
    }
    if (term_rc < 0) {
        return term_rc;
    }
    if (kill_rc < 0) {
        return kill_rc;
    }
    if (kill_wait_rc < 0) {
        return kill_wait_rc;
    }
    return 0;
}

static int wifi_softap_prepare_dirs(void) {
    int rc;

    rc = wifi_prepare_dir_owned(A90_WIFI_SOFTAP_ROOT, 0700, 0, 0);
    if (rc < 0) {
        return rc;
    }
    return wifi_prepare_dir_owned(A90_WIFI_SOFTAP_CTRL_DIR, 0770, A90_WIFI_UID, A90_WIFI_GID);
}

static int wifi_softap_write_private_config(int channel, int freq_mhz) {
    unsigned char random[32];
    char psk_hex[65];
    char ssid_tail[13];
    char ssid[32];
    char ap_ip[32];
    char lease_start[32];
    char lease_end[32];
    char supplicant_conf[1024];
    char credentials[256];
    char udhcpd_conf[512];
    int len;
    int rc;

    rc = wifi_random_bytes(random, sizeof(random));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_hex_encode(random, sizeof(random), psk_hex, sizeof(psk_hex));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_hex_encode(random, 6, ssid_tail, sizeof(ssid_tail));
    if (rc < 0) {
        return rc;
    }
    len = snprintf(ssid, sizeof(ssid), "A90_%s", ssid_tail);
    if (len < 0 || (size_t)len >= sizeof(ssid)) {
        return -ENAMETOOLONG;
    }
    rc = wifi_softap_format_ipv4(1, ap_ip, sizeof(ap_ip));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_softap_format_ipv4(20, lease_start, sizeof(lease_start));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_softap_format_ipv4(40, lease_end, sizeof(lease_end));
    if (rc < 0) {
        return rc;
    }

    len = snprintf(supplicant_conf,
                   sizeof(supplicant_conf),
                   "ctrl_interface=%s\n"
                   "update_config=0\n"
                   "ap_scan=2\n"
                   "network={\n"
                   "\tssid=\"%s\"\n"
                   "\tmode=2\n"
                   "\tfrequency=%d\n"
                   "\tkey_mgmt=WPA-PSK\n"
                   "\tproto=RSN\n"
                   "\tpairwise=CCMP\n"
                   "\tgroup=CCMP\n"
                   "\tpsk=%s\n"
                   "}\n",
                   A90_WIFI_SOFTAP_CTRL_DIR,
                   ssid,
                   freq_mhz,
                   psk_hex);
    if (len < 0 || (size_t)len >= sizeof(supplicant_conf)) {
        return -ENAMETOOLONG;
    }

    len = snprintf(credentials,
                   sizeof(credentials),
                   "version=a90-native-wifi-softap-private-credentials-v1\n"
                   "private_runtime_file=1\n"
                   "public_output_secret_values_logged=0\n"
                   "ssid=%s\n"
                   "psk=%s\n"
                   "channel=%d\n"
                   "frequency_mhz=%d\n",
                   ssid,
                   psk_hex,
                   channel,
                   freq_mhz);
    if (len < 0 || (size_t)len >= sizeof(credentials)) {
        return -ENAMETOOLONG;
    }

    len = snprintf(udhcpd_conf,
                   sizeof(udhcpd_conf),
                   "start %s\n"
                   "end %s\n"
                   "interface %s\n"
                   "max_leases 20\n"
                   "lease_file %s\n"
                   "pidfile %s\n"
                   "option subnet 255.255.255.0\n",
                   lease_start,
                   lease_end,
                   A90_WIFI_SOFTAP_PROBE_IFACE,
                   A90_WIFI_SOFTAP_UDHCPD_LEASES,
                   A90_WIFI_SOFTAP_UDHCPD_PID);
    if (len < 0 || (size_t)len >= sizeof(udhcpd_conf)) {
        return -ENAMETOOLONG;
    }

    rc = wifi_write_text_file(A90_WIFI_SOFTAP_SUPPLICANT_CONF, supplicant_conf, 0600);
    if (rc < 0) {
        return rc;
    }
    rc = wifi_write_text_file(A90_WIFI_SOFTAP_PRIVATE_CREDENTIALS, credentials, 0600);
    if (rc < 0) {
        return rc;
    }
    rc = wifi_write_text_file(A90_WIFI_SOFTAP_UDHCPD_CONF, udhcpd_conf, 0600);
    if (rc < 0) {
        return rc;
    }
    return wifi_write_text_file(A90_WIFI_SOFTAP_UDHCPD_LEASES, "", 0600);
}

static int wifi_set_ipv4_address(const char *ifname,
                                 const char *ipv4,
                                 const char *netmask,
                                 int *saved_errno) {
    struct ifreq request;
    struct sockaddr_in *addr;
    int socket_fd;
    short flags;

    if (saved_errno != NULL) {
        *saved_errno = 0;
    }
    if (ifname == NULL || ipv4 == NULL || netmask == NULL) {
        if (saved_errno != NULL) {
            *saved_errno = EINVAL;
        }
        return -1;
    }
    socket_fd = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (socket_fd < 0) {
        if (saved_errno != NULL) {
            *saved_errno = errno;
        }
        return -1;
    }

    memset(&request, 0, sizeof(request));
    snprintf(request.ifr_name, sizeof(request.ifr_name), "%s", ifname);
    addr = (struct sockaddr_in *)&request.ifr_addr;
    addr->sin_family = AF_INET;
    if (inet_pton(AF_INET, ipv4, &addr->sin_addr) != 1 ||
        ioctl(socket_fd, SIOCSIFADDR, &request) < 0) {
        if (saved_errno != NULL) {
            *saved_errno = errno == 0 ? EINVAL : errno;
        }
        close(socket_fd);
        return -1;
    }

    memset(&request, 0, sizeof(request));
    snprintf(request.ifr_name, sizeof(request.ifr_name), "%s", ifname);
    addr = (struct sockaddr_in *)&request.ifr_netmask;
    addr->sin_family = AF_INET;
    if (inet_pton(AF_INET, netmask, &addr->sin_addr) != 1 ||
        ioctl(socket_fd, SIOCSIFNETMASK, &request) < 0) {
        if (saved_errno != NULL) {
            *saved_errno = errno == 0 ? EINVAL : errno;
        }
        close(socket_fd);
        return -1;
    }

    memset(&request, 0, sizeof(request));
    snprintf(request.ifr_name, sizeof(request.ifr_name), "%s", ifname);
    if (ioctl(socket_fd, SIOCGIFFLAGS, &request) < 0) {
        if (saved_errno != NULL) {
            *saved_errno = errno;
        }
        close(socket_fd);
        return -1;
    }
    flags = request.ifr_flags;
    request.ifr_flags = (short)(request.ifr_flags | IFF_UP);
    if (ioctl(socket_fd, SIOCSIFFLAGS, &request) < 0) {
        if (saved_errno != NULL) {
            *saved_errno = errno;
        }
        close(socket_fd);
        return -1;
    }
    close(socket_fd);
    return (flags & IFF_UP) != 0 ? 1 : 0;
}

static int wifi_start_softap_supplicant(pid_t *pid_out) {
    char *const argv[] = {
        (char *)A90_WIFI_STANDALONE_SUPPLICANT,
        (char *)"-dd",
        (char *)"-i",
        (char *)A90_WIFI_SOFTAP_PROBE_IFACE,
        (char *)"-D",
        (char *)"nl80211",
        (char *)"-c",
        (char *)A90_WIFI_SOFTAP_SUPPLICANT_CONF,
        (char *)"-O",
        (char *)A90_WIFI_SOFTAP_CTRL_DIR,
        (char *)"-t",
        NULL,
    };
    struct a90_run_config config = {
        .tag = "wifi-softap-supplicant",
        .argv = argv,
        .envp = NULL,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_WIFI_SOFTAP_SUPPLICANT_LOG,
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

static int wifi_start_softap_udhcpd(pid_t *pid_out) {
    char *const argv[] = {
        (char *)"/cache/bin/busybox",
        (char *)"udhcpd",
        (char *)"-f",
        (char *)A90_WIFI_SOFTAP_UDHCPD_CONF,
        NULL,
    };
    struct a90_run_config config = {
        .tag = "wifi-softap-udhcpd",
        .argv = argv,
        .envp = NULL,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_WIFI_SOFTAP_UDHCPD_LOG,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = 0,
        .stop_timeout_ms = 3000,
    };

    if (access("/cache/bin/busybox", X_OK) < 0) {
        return -errno;
    }
    return a90_run_spawn(&config, pid_out);
}

static int wifi_softap_prepare_transfer_dirs(void) {
    int rc = wifi_softap_prepare_dirs();

    if (rc < 0) {
        return rc;
    }
    return wifi_prepare_dir_owned(A90_WIFI_SOFTAP_WWW_ROOT, 0700, 0, 0);
}

static int wifi_softap_file_size(const char *path, long *size_out) {
    struct stat st;

    if (size_out != NULL) {
        *size_out = -1;
    }
    if (path == NULL) {
        return -EINVAL;
    }
    if (stat(path, &st) < 0) {
        return -errno;
    }
    if (!S_ISREG(st.st_mode)) {
        return -EINVAL;
    }
    if (size_out != NULL) {
        *size_out = (long)st.st_size;
    }
    return 0;
}

static int wifi_softap_write_download_payload(char *sha_out,
                                              size_t sha_out_size,
                                              long *bytes_out) {
    unsigned char buffer[4096];
    size_t written_total = 0;
    int fd;
    int rc = 0;

    if (sha_out != NULL && sha_out_size > 0) {
        snprintf(sha_out, sha_out_size, "-");
    }
    if (bytes_out != NULL) {
        *bytes_out = 0;
    }

    (void)unlink(A90_WIFI_SOFTAP_DOWNLOAD_TMP);
    fd = open(A90_WIFI_SOFTAP_DOWNLOAD_TMP,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -errno;
    }

    while (written_total < A90_WIFI_SOFTAP_DOWNLOAD_BYTES) {
        size_t chunk = A90_WIFI_SOFTAP_DOWNLOAD_BYTES - written_total;
        size_t i;

        if (chunk > sizeof(buffer)) {
            chunk = sizeof(buffer);
        }
        for (i = 0; i < chunk; ++i) {
            size_t absolute = written_total + i;

            buffer[i] = (unsigned char)(((absolute * 33U) ^ (absolute >> 7U) ^ 0x5aU) & 0xffU);
        }
        if (write_all_checked(fd, (const char *)buffer, chunk) < 0) {
            rc = -errno;
            break;
        }
        written_total += chunk;
    }
    if (rc == 0 && fsync(fd) < 0) {
        rc = -errno;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    if (rc < 0) {
        (void)unlink(A90_WIFI_SOFTAP_DOWNLOAD_TMP);
        return rc;
    }
    if (rename(A90_WIFI_SOFTAP_DOWNLOAD_TMP, A90_WIFI_SOFTAP_DOWNLOAD_FILE) < 0) {
        rc = -errno;
        (void)unlink(A90_WIFI_SOFTAP_DOWNLOAD_TMP);
        return rc;
    }
    if (bytes_out != NULL) {
        *bytes_out = (long)written_total;
    }
    if (sha_out != NULL && sha_out_size > 0) {
        rc = a90_helper_sha256_file(A90_WIFI_SOFTAP_DOWNLOAD_FILE, sha_out, sha_out_size);
        if (rc < 0) {
            snprintf(sha_out, sha_out_size, "hash-error:%d", -rc);
            return rc;
        }
    }
    return 0;
}

static int wifi_start_softap_httpd(const char *bind_ip, pid_t *pid_out) {
    char bind_arg[64];
    char *const argv[] = {
        (char *)"/cache/bin/busybox",
        (char *)"httpd",
        (char *)"-f",
        (char *)"-p",
        bind_arg,
        (char *)"-h",
        (char *)A90_WIFI_SOFTAP_WWW_ROOT,
        NULL,
    };
    struct a90_run_config config = {
        .tag = "wifi-softap-httpd",
        .argv = argv,
        .envp = NULL,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_WIFI_SOFTAP_HTTPD_LOG,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = 0,
        .stop_timeout_ms = 3000,
    };
    int len;

    if (bind_ip == NULL || bind_ip[0] == '\0') {
        return -EINVAL;
    }
    if (access("/cache/bin/busybox", X_OK) < 0) {
        return -errno;
    }
    len = snprintf(bind_arg, sizeof(bind_arg), "%s:%d", bind_ip, A90_WIFI_SOFTAP_HTTP_PORT);
    if (len < 0 || (size_t)len >= sizeof(bind_arg)) {
        return -ENAMETOOLONG;
    }
    return a90_run_spawn(&config, pid_out);
}

static void wifi_softap_redirect_stdio_null(void) {
    int null_fd = open("/dev/null", O_RDWR | O_CLOEXEC);

    if (null_fd < 0) {
        return;
    }
    (void)dup2(null_fd, STDIN_FILENO);
    (void)dup2(null_fd, STDOUT_FILENO);
    (void)dup2(null_fd, STDERR_FILENO);
    if (null_fd > STDERR_FILENO) {
        close(null_fd);
    }
}

static void wifi_softap_write_upload_result(const char *result,
                                            long bytes,
                                            int truncated,
                                            int errnum,
                                            const char *sha256) {
    char text[512];
    int len;

    if (result == NULL || result[0] == '\0') {
        result = "error";
    }
    if (sha256 == NULL || sha256[0] == '\0') {
        sha256 = "-";
    }
    len = snprintf(text,
                   sizeof(text),
                   "version=%s\n"
                   "upload_result=%s\n"
                   "upload_bytes=%ld\n"
                   "upload_truncated=%d\n"
                   "upload_errno=%d\n"
                   "upload_sha256=%s\n"
                   "server_bind_private_ap_only=1\n"
                   "client_identity_logged=0\n"
                   "peer_address_logged=0\n",
                   A90_WIFI_SOFTAP_TRANSFER_VERSION,
                   result,
                   bytes,
                   truncated,
                   errnum,
                   sha256);
    if (len < 0 || (size_t)len >= sizeof(text)) {
        return;
    }
    (void)wifi_write_text_file(A90_WIFI_SOFTAP_UPLOAD_RESULT, text, 0600);
}

static int wifi_softap_upload_receiver_run(const char *bind_ip) {
    unsigned char buffer[4096];
    struct sockaddr_in addr;
    struct pollfd pfd;
    long total = 0;
    long idle_deadline;
    int listen_fd = -1;
    int client_fd = -1;
    int upload_fd = -1;
    int one = 1;
    int rc = 0;
    int errnum = 0;
    int truncated = 0;
    const char *result = "error";
    char sha256[65];

    snprintf(sha256, sizeof(sha256), "-");
    (void)unlink(A90_WIFI_SOFTAP_UPLOAD_TMP);
    (void)unlink(A90_WIFI_SOFTAP_UPLOAD_FILE);

    listen_fd = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (listen_fd < 0) {
        errnum = errno;
        goto out;
    }
    (void)setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)A90_WIFI_SOFTAP_UPLOAD_PORT);
    if (inet_pton(AF_INET, bind_ip, &addr.sin_addr) != 1) {
        errnum = EINVAL;
        goto out;
    }
    if (bind(listen_fd, (const struct sockaddr *)&addr, sizeof(addr)) < 0) {
        errnum = errno;
        goto out;
    }
    if (listen(listen_fd, 1) < 0) {
        errnum = errno;
        goto out;
    }

    memset(&pfd, 0, sizeof(pfd));
    pfd.fd = listen_fd;
    pfd.events = POLLIN;
    do {
        rc = poll(&pfd, 1, A90_WIFI_SOFTAP_UPLOAD_ACCEPT_TIMEOUT_MS);
    } while (rc < 0 && errno == EINTR);
    if (rc == 0) {
        result = "timeout";
        errnum = ETIMEDOUT;
        goto out;
    }
    if (rc < 0) {
        errnum = errno;
        goto out;
    }

    client_fd = accept(listen_fd, NULL, NULL);
    if (client_fd < 0) {
        errnum = errno;
        goto out;
    }
    (void)fcntl(client_fd, F_SETFD, FD_CLOEXEC);

    upload_fd = open(A90_WIFI_SOFTAP_UPLOAD_TMP,
                     O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
                     0600);
    if (upload_fd < 0) {
        errnum = errno;
        goto out;
    }

    idle_deadline = monotonic_millis() + A90_WIFI_SOFTAP_UPLOAD_IDLE_TIMEOUT_MS;
    for (;;) {
        long now = monotonic_millis();
        int timeout_ms = (int)(idle_deadline - now);
        ssize_t rd;

        if (timeout_ms <= 0) {
            result = "timeout";
            errnum = ETIMEDOUT;
            goto out;
        }
        memset(&pfd, 0, sizeof(pfd));
        pfd.fd = client_fd;
        pfd.events = POLLIN;
        do {
            rc = poll(&pfd, 1, timeout_ms);
        } while (rc < 0 && errno == EINTR);
        if (rc == 0) {
            result = "timeout";
            errnum = ETIMEDOUT;
            goto out;
        }
        if (rc < 0) {
            errnum = errno;
            goto out;
        }

        rd = read(client_fd, buffer, sizeof(buffer));
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            errnum = errno;
            goto out;
        }
        if (rd == 0) {
            result = "pass";
            errnum = 0;
            break;
        }
        idle_deadline = monotonic_millis() + A90_WIFI_SOFTAP_UPLOAD_IDLE_TIMEOUT_MS;
        if (total + rd > (long)A90_WIFI_SOFTAP_UPLOAD_MAX_BYTES) {
            size_t allowed = 0;

            if (total < (long)A90_WIFI_SOFTAP_UPLOAD_MAX_BYTES) {
                allowed = (size_t)((long)A90_WIFI_SOFTAP_UPLOAD_MAX_BYTES - total);
            }
            if (allowed > 0 &&
                write_all_checked(upload_fd, (const char *)buffer, allowed) < 0) {
                errnum = errno;
                goto out;
            }
            total += (long)allowed;
            truncated = 1;
            result = "truncated";
            errnum = EFBIG;
            break;
        }
        if (write_all_checked(upload_fd, (const char *)buffer, (size_t)rd) < 0) {
            errnum = errno;
            goto out;
        }
        total += (long)rd;
    }

    if (fsync(upload_fd) < 0) {
        result = "error";
        errnum = errno;
        goto out;
    }
    if (close(upload_fd) < 0) {
        upload_fd = -1;
        result = "error";
        errnum = errno;
        goto out;
    }
    upload_fd = -1;
    if (rename(A90_WIFI_SOFTAP_UPLOAD_TMP, A90_WIFI_SOFTAP_UPLOAD_FILE) < 0) {
        result = "error";
        errnum = errno;
        goto out;
    }
    if (a90_helper_sha256_file(A90_WIFI_SOFTAP_UPLOAD_FILE, sha256, sizeof(sha256)) < 0) {
        snprintf(sha256, sizeof(sha256), "hash-error");
    }

out:
    if (upload_fd >= 0) {
        (void)close(upload_fd);
    }
    if (client_fd >= 0) {
        (void)close(client_fd);
    }
    if (listen_fd >= 0) {
        (void)close(listen_fd);
    }
    if (strcmp(result, "pass") != 0 && strcmp(result, "truncated") != 0) {
        (void)unlink(A90_WIFI_SOFTAP_UPLOAD_TMP);
    }
    wifi_softap_write_upload_result(result, total, truncated, errnum, sha256);
    return strcmp(result, "pass") == 0 ? 0 : -errnum;
}

static int wifi_start_softap_upload_receiver(const char *bind_ip, pid_t *pid_out) {
    pid_t pid;

    if (bind_ip == NULL || bind_ip[0] == '\0') {
        return -EINVAL;
    }
    wifi_softap_write_upload_result("pending", 0, 0, 0, "-");
    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        int rc;

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        (void)setsid();
        wifi_softap_redirect_stdio_null();
        rc = wifi_softap_upload_receiver_run(bind_ip);
        _exit(rc == 0 ? 0 : 1);
    }
    if (pid_out != NULL) {
        *pid_out = pid;
    }
    a90_logf("wifi-softap", "upload receiver spawned pid=%ld", (long)pid);
    return 0;
}

static void wifi_softap_print_file_meta(const char *label, const char *path) {
    long bytes = -1;
    char sha256[65];
    int size_rc;
    int sha_rc = -ENOENT;

    snprintf(sha256, sizeof(sha256), "-");
    size_rc = wifi_softap_file_size(path, &bytes);
    if (size_rc == 0) {
        sha_rc = a90_helper_sha256_file(path, sha256, sizeof(sha256));
        if (sha_rc < 0) {
            snprintf(sha256, sizeof(sha256), "hash-error:%d", -sha_rc);
        }
    }
    a90_console_printf("%s.present=%d\r\n", label, size_rc == 0 ? 1 : 0);
    a90_console_printf("%s.bytes=%ld\r\n", label, size_rc == 0 ? bytes : -1L);
    a90_console_printf("%s.sha256_rc=%d\r\n", label, sha_rc);
    a90_console_printf("%s.sha256=%s\r\n", label, sha_rc == 0 ? sha256 : "-");
}

static int wifi_softap_transfer_status_command(void) {
    pid_t http_pid = -1;
    pid_t upload_pid = -1;
    int http_pid_rc;
    int upload_pid_rc;
    char upload_result[32];
    char upload_bytes[32];
    char upload_truncated[32];
    char upload_sha256[80];

    wifi_key_value_file_value(A90_WIFI_SOFTAP_UPLOAD_RESULT,
                              "upload_result=",
                              upload_result,
                              sizeof(upload_result));
    wifi_key_value_file_value(A90_WIFI_SOFTAP_UPLOAD_RESULT,
                              "upload_bytes=",
                              upload_bytes,
                              sizeof(upload_bytes));
    wifi_key_value_file_value(A90_WIFI_SOFTAP_UPLOAD_RESULT,
                              "upload_truncated=",
                              upload_truncated,
                              sizeof(upload_truncated));
    wifi_key_value_file_value(A90_WIFI_SOFTAP_UPLOAD_RESULT,
                              "upload_sha256=",
                              upload_sha256,
                              sizeof(upload_sha256));

    http_pid_rc = wifi_read_pid_file(A90_WIFI_SOFTAP_HTTPD_PID, &http_pid);
    upload_pid_rc = wifi_read_pid_file(A90_WIFI_SOFTAP_UPLOAD_PID, &upload_pid);

    a90_console_printf("[wifi softap transfer-status]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SOFTAP_VERSION);
    a90_console_printf("transfer_version=%s\r\n", A90_WIFI_SOFTAP_TRANSFER_VERSION);
    a90_console_printf("scope=s4-local-transfer-server-status\r\n");
    a90_console_printf("server_bind_private_ap_only=1\r\n");
    a90_console_printf("http_port=%d\r\n", A90_WIFI_SOFTAP_HTTP_PORT);
    a90_console_printf("upload_port=%d\r\n", A90_WIFI_SOFTAP_UPLOAD_PORT);
    a90_console_printf("ssid_psk_logged=0\r\n");
    a90_console_printf("client_identity_logged=0\r\n");
    a90_console_printf("peer_address_logged=0\r\n");
    a90_console_printf("address_value_logged=0\r\n");
    a90_console_printf("wan_nat_attempted=0\r\n");
    a90_console_printf("default_route_export_attempted=0\r\n");
    a90_console_printf("httpd.pid_read_rc=%d\r\n", http_pid_rc);
    a90_console_printf("httpd.pid=%ld\r\n", http_pid_rc == 0 ? (long)http_pid : -1L);
    a90_console_printf("httpd.alive=%d\r\n",
                       http_pid_rc == 0 && wifi_process_alive(http_pid) ? 1 : 0);
    a90_console_printf("upload_receiver.pid_read_rc=%d\r\n", upload_pid_rc);
    a90_console_printf("upload_receiver.pid=%ld\r\n",
                       upload_pid_rc == 0 ? (long)upload_pid : -1L);
    a90_console_printf("upload_receiver.pid_alive_or_unreaped=%d\r\n",
                       upload_pid_rc == 0 && wifi_process_alive(upload_pid) ? 1 : 0);
    a90_console_printf("upload_result_file_present=%d\r\n",
                       access(A90_WIFI_SOFTAP_UPLOAD_RESULT, F_OK) == 0 ? 1 : 0);
    a90_console_printf("upload_result=%s\r\n", upload_result);
    a90_console_printf("upload_result.bytes=%s\r\n", upload_bytes);
    a90_console_printf("upload_result.truncated=%s\r\n", upload_truncated);
    a90_console_printf("upload_result.sha256=%s\r\n", upload_sha256);
    wifi_softap_print_file_meta("download_file", A90_WIFI_SOFTAP_DOWNLOAD_FILE);
    wifi_softap_print_file_meta("upload_file", A90_WIFI_SOFTAP_UPLOAD_FILE);
    a90_console_printf("decision=softap-transfer-status-pass\r\n");
    return 0;
}

static int wifi_softap_delete_iface(const char *label) {
    unsigned int ifindex = if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE);
    int socket_fd;
    int family_id;
    int delete_rc = 0;
    int delete_errno = 0;

    a90_console_printf("%s.iface_present_before=%d\r\n", label, ifindex != 0 ? 1 : 0);
    if (ifindex == 0) {
        a90_console_printf("%s.delete_attempted=0\r\n", label);
        a90_console_printf("%s.delete_rc=0\r\n", label);
        a90_console_printf("%s.delete_errno=0\r\n", label);
        a90_console_printf("%s.iface_present_after=0\r\n", label);
        return 0;
    }

    socket_fd = wifi_open_genl_socket();
    if (socket_fd < 0) {
        delete_errno = errno;
        a90_console_printf("%s.netlink_open=0\r\n", label);
        a90_console_printf("%s.delete_attempted=0\r\n", label);
        a90_console_printf("%s.delete_rc=-1\r\n", label);
        a90_console_printf("%s.delete_errno=%d\r\n", label, delete_errno);
        a90_console_printf("%s.iface_present_after=1\r\n", label);
        return -delete_errno;
    }
    a90_console_printf("%s.netlink_open=1\r\n", label);
    family_id = wifi_get_family_id(socket_fd, "nl80211");
    a90_console_printf("%s.family_id=%d\r\n", label, family_id < 0 ? 0 : family_id);
    if (family_id < 0) {
        delete_errno = errno;
        close(socket_fd);
        a90_console_printf("%s.delete_attempted=0\r\n", label);
        a90_console_printf("%s.delete_rc=-1\r\n", label);
        a90_console_printf("%s.delete_errno=%d\r\n", label, delete_errno);
        a90_console_printf("%s.iface_present_after=1\r\n", label);
        return -delete_errno;
    }
    delete_rc = wifi_send_nl80211_if_delete(socket_fd, family_id, 20, ifindex);
    if (delete_rc < 0) {
        delete_errno = errno;
    }
    close(socket_fd);
    a90_console_printf("%s.delete_attempted=1\r\n", label);
    a90_console_printf("%s.delete_rc=%d\r\n", label, delete_rc);
    a90_console_printf("%s.delete_errno=%d\r\n", label, delete_errno);
    a90_console_printf("%s.iface_present_after=%d\r\n",
                       label,
                       if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE) != 0 ? 1 : 0);
    return delete_rc < 0 ? -delete_errno : 0;
}

static int wifi_softap_cleanup_internal(const char *prefix) {
    char label[80];
    int http_pid_stop_rc;
    int http_token_stop_rc;
    int upload_pid_stop_rc;
    int supp_pid_stop_rc;
    int supp_token_stop_rc;
    int dhcp_pid_stop_rc;
    int dhcp_token_stop_rc;
    int delete_rc;
    int final_http_count;
    int final_supp_count;
    int final_dhcp_count;
    int final_iface_present;

    if (prefix == NULL || prefix[0] == '\0') {
        prefix = "softap_cleanup";
    }
    if (access(A90_WIFI_SOFTAP_CTRL_SOCKET, F_OK) == 0) {
        snprintf(label, sizeof(label), "%s.ctrl_terminate", prefix);
        (void)wifi_print_ctrl_result_at(label, A90_WIFI_SOFTAP_CTRL_SOCKET, "TERMINATE");
        a90_console_printf("%s.ctrl_terminate_attempted=1\r\n", prefix);
    } else {
        a90_console_printf("%s.ctrl_terminate_attempted=0\r\n", prefix);
        a90_console_printf("%s.ctrl_terminate_rc=0\r\n", prefix);
    }

    snprintf(label, sizeof(label), "%s.httpd_pid", prefix);
    http_pid_stop_rc = wifi_stop_pid_file(A90_WIFI_SOFTAP_HTTPD_PID, label, true);
    snprintf(label, sizeof(label), "%s.httpd_token", prefix);
    http_token_stop_rc = wifi_stop_process_token(A90_WIFI_SOFTAP_WWW_ROOT, label);
    snprintf(label, sizeof(label), "%s.upload_receiver_pid", prefix);
    upload_pid_stop_rc = wifi_stop_pid_file(A90_WIFI_SOFTAP_UPLOAD_PID, label, false);
    snprintf(label, sizeof(label), "%s.supplicant_pid", prefix);
    supp_pid_stop_rc = wifi_stop_pid_file(A90_WIFI_SOFTAP_SUPPLICANT_PID, label, true);
    snprintf(label, sizeof(label), "%s.supplicant_token", prefix);
    supp_token_stop_rc = wifi_stop_process_token(A90_WIFI_SOFTAP_SUPPLICANT_CONF, label);
    snprintf(label, sizeof(label), "%s.udhcpd_pid", prefix);
    dhcp_pid_stop_rc = wifi_stop_pid_file(A90_WIFI_SOFTAP_UDHCPD_PID, label, true);
    snprintf(label, sizeof(label), "%s.udhcpd_token", prefix);
    dhcp_token_stop_rc = wifi_stop_process_token(A90_WIFI_SOFTAP_UDHCPD_CONF, label);
    snprintf(label, sizeof(label), "%s.ap_iface", prefix);
    delete_rc = wifi_softap_delete_iface(label);

    (void)unlink(A90_WIFI_SOFTAP_CTRL_SOCKET);
    (void)unlink(A90_WIFI_SOFTAP_SUPPLICANT_CONF);
    (void)unlink(A90_WIFI_SOFTAP_PRIVATE_CREDENTIALS);
    (void)unlink(A90_WIFI_SOFTAP_UDHCPD_CONF);
    (void)unlink(A90_WIFI_SOFTAP_UDHCPD_LEASES);
    (void)unlink(A90_WIFI_SOFTAP_DOWNLOAD_FILE);
    (void)unlink(A90_WIFI_SOFTAP_DOWNLOAD_TMP);
    (void)unlink(A90_WIFI_SOFTAP_UPLOAD_FILE);
    (void)unlink(A90_WIFI_SOFTAP_UPLOAD_TMP);
    (void)unlink(A90_WIFI_SOFTAP_UPLOAD_RESULT);
    final_http_count = wifi_count_processes_with_token(A90_WIFI_SOFTAP_WWW_ROOT);
    final_supp_count = wifi_count_processes_with_token(A90_WIFI_SOFTAP_SUPPLICANT_CONF);
    final_dhcp_count = wifi_count_processes_with_token(A90_WIFI_SOFTAP_UDHCPD_CONF);
    final_iface_present = if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE) != 0 ? 1 : 0;
    a90_console_printf("%s.transfer_runtime_removed=1\r\n", prefix);
    a90_console_printf("%s.private_config_removed=1\r\n", prefix);
    a90_console_printf("%s.final_httpd_count=%d\r\n", prefix, final_http_count);
    a90_console_printf("%s.final_supplicant_count=%d\r\n", prefix, final_supp_count);
    a90_console_printf("%s.final_udhcpd_count=%d\r\n", prefix, final_dhcp_count);
    a90_console_printf("%s.final_iface_present=%d\r\n", prefix, final_iface_present);
    if (http_pid_stop_rc < 0 || http_token_stop_rc < 0 ||
        upload_pid_stop_rc < 0 ||
        supp_pid_stop_rc < 0 || supp_token_stop_rc < 0 ||
        dhcp_pid_stop_rc < 0 || dhcp_token_stop_rc < 0 ||
        delete_rc < 0 || final_iface_present != 0 ||
        final_http_count != 0 || final_supp_count != 0 || final_dhcp_count != 0) {
        return -EBUSY;
    }
    return 0;
}

static int wifi_softap_cleanup_command(void) {
    int cleanup_rc;

    a90_console_printf("[wifi softap cleanup]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SOFTAP_VERSION);
    a90_console_printf("scope=s3-mode2-ap-cleanup\r\n");
    a90_console_printf("credentials_logged=0\r\n");
    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("hostapd_start_attempted=0\r\n");
    a90_console_printf("server_exposure_attempted=0\r\n");
    a90_console_printf("server_cleanup_attempted=1\r\n");
    a90_console_printf("wan_nat_attempted=0\r\n");
    a90_console_printf("default_route_export_attempted=0\r\n");
    cleanup_rc = wifi_softap_cleanup_internal("cleanup");
    a90_console_printf("cleanup.rc=%d\r\n", cleanup_rc);
    a90_console_printf("decision=%s\r\n",
                       cleanup_rc == 0 ? "softap-cleanup-pass" : "softap-cleanup-incomplete");
    return cleanup_rc;
}

static int wifi_softap_stop_sta_supplicant_if_needed(void);

static int wifi_softap_start(int channel, int freq_mhz) {
    int wlan0_wait_elapsed_ms = 0;
    int wlan0_wait_rc;
    int link_up_errno = 0;
    int link_up_rc;
    int supplicant_stop_rc;
    int precleanup_rc;
    int prepare_rc;
    int config_rc;
    int socket_fd;
    int family_id;
    unsigned int parent_ifindex;
    unsigned int ap_ifindex = 0;
    int add_rc = -1;
    int add_errno = 0;
    char ap_ip[32];
    int address_errno = 0;
    int address_rc;
    int ap_link_errno = 0;
    int ap_link_rc;
    pid_t supplicant_pid = -1;
    int supplicant_spawn_rc;
    int supplicant_pid_write_rc = 0;
    int ctrl_wait_elapsed_ms = 0;
    char ctrl_category[32];
    int ctrl_errno = 0;
    int ctrl_wait_rc;
    pid_t dhcp_pid = -1;
    int dhcp_spawn_rc;
    int dhcp_pid_write_rc = 0;
    int dhcp_alive;

    a90_console_printf("[wifi softap start]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SOFTAP_VERSION);
    a90_console_printf("scope=s3-mode2-ap-bringup-dhcp-no-server\r\n");
    a90_console_printf("iface=%s\r\n", A90_WIFI_IFACE);
    a90_console_printf("ap_iface=%s\r\n", A90_WIFI_SOFTAP_PROBE_IFACE);
    a90_console_printf("channel=%d\r\n", channel);
    a90_console_printf("frequency_mhz=%d\r\n", freq_mhz);
    a90_console_printf("credentials=private-generated\r\n");
    a90_console_printf("credential_file_private=1\r\n");
    a90_console_printf("ssid_psk_logged=0\r\n");
    a90_console_printf("hostapd_start_attempted=0\r\n");
    a90_console_printf("listener_start_attempted=0\r\n");
    a90_console_printf("server_exposure_attempted=0\r\n");
    a90_console_printf("wan_nat_attempted=0\r\n");
    a90_console_printf("ip_forward_write_attempted=0\r\n");
    a90_console_printf("nat_attempted=0\r\n");
    a90_console_printf("default_route_export_attempted=0\r\n");
    a90_console_printf("dhcp_router_option_exported=0\r\n");
    a90_console_printf("dhcp_dns_option_exported=0\r\n");
    a90_console_printf("start_supported=1\r\n");
    a90_console_printf("start_allowed=1\r\n");

    precleanup_rc = wifi_softap_cleanup_internal("precleanup");
    a90_console_printf("precleanup.rc=%d\r\n", precleanup_rc);
    if (precleanup_rc < 0) {
        a90_console_printf("decision=softap-start-precleanup-failed\r\n");
        return precleanup_rc;
    }

    a90_console_printf("wlan0_wait_timeout_ms=%d\r\n", A90_WIFI_SOFTAP_WLAN0_WAIT_MS);
    wlan0_wait_rc = wifi_wait_wlan0(A90_WIFI_SOFTAP_WLAN0_WAIT_MS, &wlan0_wait_elapsed_ms);
    a90_console_printf("wlan0_wait_rc=%d\r\n", wlan0_wait_rc);
    a90_console_printf("wlan0_wait_elapsed_ms=%d\r\n", wlan0_wait_elapsed_ms);
    a90_console_printf("wlan0_present=%d\r\n", wlan0_wait_rc == 0 ? 1 : 0);
    if (wlan0_wait_rc < 0) {
        a90_console_printf("decision=softap-start-wlan0-timeout\r\n");
        return wlan0_wait_rc;
    }

    link_up_rc = wifi_link_set_up(A90_WIFI_IFACE, &link_up_errno);
    a90_console_printf("parent_link_up_attempted=1\r\n");
    a90_console_printf("parent_link_up_rc=%d\r\n", link_up_rc);
    a90_console_printf("parent_link_up_errno=%d\r\n", link_up_errno);
    if (link_up_rc < 0) {
        a90_console_printf("decision=softap-start-parent-link-up-failed\r\n");
        return -link_up_errno;
    }

    supplicant_stop_rc = wifi_softap_stop_sta_supplicant_if_needed();
    a90_console_printf("sta_supplicant.stop_rc=%d\r\n", supplicant_stop_rc);
    if (supplicant_stop_rc < 0) {
        a90_console_printf("decision=softap-start-sta-supplicant-busy\r\n");
        return supplicant_stop_rc;
    }

    prepare_rc = wifi_softap_prepare_dirs();
    a90_console_printf("runtime_prepare_rc=%d\r\n", prepare_rc);
    if (prepare_rc < 0) {
        a90_console_printf("decision=softap-start-runtime-prepare-failed\r\n");
        return prepare_rc;
    }
    config_rc = wifi_softap_write_private_config(channel, freq_mhz);
    a90_console_printf("config_write_attempted=1\r\n");
    a90_console_printf("config_write_rc=%d\r\n", config_rc);
    if (config_rc < 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-config-write-failed\r\n");
        return config_rc;
    }

    parent_ifindex = if_nametoindex(A90_WIFI_IFACE);
    a90_console_printf("parent_ifindex=%u\r\n", parent_ifindex);
    if (parent_ifindex == 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-parent-interface-missing\r\n");
        return -ENODEV;
    }

    socket_fd = wifi_open_genl_socket();
    if (socket_fd < 0) {
        int saved_errno = errno;

        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("netlink_open=0\r\n");
        a90_console_printf("netlink_errno=%d\r\n", saved_errno);
        a90_console_printf("decision=softap-start-nl80211-unavailable\r\n");
        return -saved_errno;
    }
    a90_console_printf("netlink_open=1\r\n");
    family_id = wifi_get_family_id(socket_fd, "nl80211");
    a90_console_printf("family_id=%d\r\n", family_id < 0 ? 0 : family_id);
    if (family_id < 0) {
        int saved_errno = errno;

        close(socket_fd);
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("family_errno=%d\r\n", saved_errno);
        a90_console_printf("decision=softap-start-family-missing\r\n");
        return -saved_errno;
    }

    a90_console_printf("ap_iftype_add_attempted=1\r\n");
    add_rc = wifi_send_nl80211_iftype_new(socket_fd,
                                          family_id,
                                          21,
                                          parent_ifindex,
                                          A90_WIFI_SOFTAP_PROBE_IFACE,
                                          (uint32_t)NL80211_IFTYPE_AP);
    if (add_rc < 0) {
        add_errno = errno;
    }
    ap_ifindex = if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE);
    close(socket_fd);
    a90_console_printf("ap_iftype_add_rc=%d\r\n", add_rc);
    a90_console_printf("ap_iftype_add_errno=%d\r\n", add_errno);
    a90_console_printf("ap_iftype_iface_created=%d\r\n", ap_ifindex != 0 ? 1 : 0);
    a90_console_printf("ap_ifindex=%u\r\n", ap_ifindex);
    if (add_rc < 0 || ap_ifindex == 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-ap-iftype-add-failed\r\n");
        return add_rc < 0 ? -add_errno : -ENODEV;
    }

    if (wifi_softap_format_ipv4(1, ap_ip, sizeof(ap_ip)) < 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-address-format-failed\r\n");
        return -EINVAL;
    }
    address_rc = wifi_set_ipv4_address(A90_WIFI_SOFTAP_PROBE_IFACE,
                                       ap_ip,
                                       "255.255.255.0",
                                       &address_errno);
    a90_console_printf("address_assign_attempted=1\r\n");
    a90_console_printf("address_assign_rc=%d\r\n", address_rc);
    a90_console_printf("address_assign_errno=%d\r\n", address_errno);
    a90_console_printf("address_value_logged=0\r\n");
    a90_console_printf("ap_local_subnet_private=1\r\n");
    if (address_rc < 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-address-assign-failed\r\n");
        return -address_errno;
    }

    ap_link_rc = wifi_link_set_up(A90_WIFI_SOFTAP_PROBE_IFACE, &ap_link_errno);
    a90_console_printf("ap_link_up_attempted=1\r\n");
    a90_console_printf("ap_link_up_rc=%d\r\n", ap_link_rc);
    a90_console_printf("ap_link_up_errno=%d\r\n", ap_link_errno);
    if (ap_link_rc < 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-ap-link-up-failed\r\n");
        return -ap_link_errno;
    }

    a90_console_printf("wpa_supplicant_mode2_start_attempted=1\r\n");
    supplicant_spawn_rc = wifi_start_softap_supplicant(&supplicant_pid);
    a90_console_printf("wpa_supplicant_mode2_spawn_rc=%d\r\n", supplicant_spawn_rc);
    a90_console_printf("wpa_supplicant_mode2_pid=%ld\r\n",
                       supplicant_spawn_rc == 0 ? (long)supplicant_pid : -1L);
    if (supplicant_spawn_rc == 0) {
        supplicant_pid_write_rc = wifi_write_pid_file(A90_WIFI_SOFTAP_SUPPLICANT_PID,
                                                      supplicant_pid);
    }
    a90_console_printf("wpa_supplicant_mode2_pid_write_rc=%d\r\n", supplicant_pid_write_rc);
    if (supplicant_spawn_rc < 0 || supplicant_pid_write_rc < 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-supplicant-spawn-failed\r\n");
        return supplicant_spawn_rc < 0 ? supplicant_spawn_rc : supplicant_pid_write_rc;
    }

    ctrl_wait_rc = wifi_wait_ctrl_ready_at(A90_WIFI_SOFTAP_CTRL_SOCKET,
                                           supplicant_pid,
                                           true,
                                           A90_WIFI_SOFTAP_CTRL_WAIT_MS,
                                           &ctrl_wait_elapsed_ms,
                                           ctrl_category,
                                           sizeof(ctrl_category),
                                           &ctrl_errno);
    a90_console_printf("softap_ctrl_wait_timeout_ms=%d\r\n", A90_WIFI_SOFTAP_CTRL_WAIT_MS);
    a90_console_printf("softap_ctrl_wait_rc=%d\r\n", ctrl_wait_rc);
    a90_console_printf("softap_ctrl_wait_elapsed_ms=%d\r\n", ctrl_wait_elapsed_ms);
    a90_console_printf("softap_ctrl_errno=%d\r\n", ctrl_errno);
    a90_console_printf("softap_ctrl_reply_category=%s\r\n",
                       ctrl_wait_rc == 0 ? ctrl_category : "error");
    if (ctrl_wait_rc < 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-supplicant-ctrl-timeout\r\n");
        return ctrl_wait_rc;
    }
    (void)wifi_print_ctrl_result_at("softap.ctrl_status", A90_WIFI_SOFTAP_CTRL_SOCKET, "STATUS");

    a90_console_printf("dhcp_server_start_attempted=1\r\n");
    dhcp_spawn_rc = wifi_start_softap_udhcpd(&dhcp_pid);
    a90_console_printf("dhcp_server_spawn_rc=%d\r\n", dhcp_spawn_rc);
    a90_console_printf("dhcp_server_pid=%ld\r\n", dhcp_spawn_rc == 0 ? (long)dhcp_pid : -1L);
    if (dhcp_spawn_rc == 0) {
        dhcp_pid_write_rc = wifi_write_pid_file(A90_WIFI_SOFTAP_UDHCPD_PID, dhcp_pid);
    }
    a90_console_printf("dhcp_server_pid_write_rc=%d\r\n", dhcp_pid_write_rc);
    if (dhcp_spawn_rc < 0 || dhcp_pid_write_rc < 0) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-dhcp-spawn-failed\r\n");
        return dhcp_spawn_rc < 0 ? dhcp_spawn_rc : dhcp_pid_write_rc;
    }
    usleep((useconds_t)A90_WIFI_SOFTAP_DHCP_SETTLE_MS * 1000U);
    dhcp_alive = wifi_process_alive(dhcp_pid) ? 1 : 0;
    a90_console_printf("dhcp_server_settle_ms=%d\r\n", A90_WIFI_SOFTAP_DHCP_SETTLE_MS);
    a90_console_printf("dhcp_server_alive=%d\r\n", dhcp_alive);
    if (!dhcp_alive) {
        (void)wifi_softap_cleanup_internal("rollback_cleanup");
        a90_console_printf("decision=softap-start-dhcp-exited\r\n");
        return -ECHILD;
    }

    a90_logf("wifi-softap",
             "mode2 start pass iface=%s channel=%d freq=%d",
             A90_WIFI_SOFTAP_PROBE_IFACE,
             channel,
             freq_mhz);
    a90_console_printf("decision=softap-start-pass\r\n");
    return 0;
}

static int wifi_softap_transfer_start(int channel, int freq_mhz) {
    char ap_ip[32];
    char download_sha256[65];
    long download_bytes = -1;
    int ap_start_rc;
    int transfer_prepare_rc;
    int payload_rc;
    pid_t http_pid = -1;
    int http_spawn_rc;
    int http_pid_write_rc = 0;
    int http_alive;
    pid_t upload_pid = -1;
    int upload_spawn_rc;
    int upload_pid_write_rc = 0;
    int upload_alive;

    snprintf(download_sha256, sizeof(download_sha256), "-");

    a90_console_printf("[wifi softap transfer-start]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SOFTAP_VERSION);
    a90_console_printf("transfer_version=%s\r\n", A90_WIFI_SOFTAP_TRANSFER_VERSION);
    a90_console_printf("scope=s4-local-transfer-server-private-ap\r\n");
    a90_console_printf("channel=%d\r\n", channel);
    a90_console_printf("frequency_mhz=%d\r\n", freq_mhz);
    a90_console_printf("http_port=%d\r\n", A90_WIFI_SOFTAP_HTTP_PORT);
    a90_console_printf("upload_port=%d\r\n", A90_WIFI_SOFTAP_UPLOAD_PORT);
    a90_console_printf("http_download_path=/download.bin\r\n");
    a90_console_printf("server_bind_private_ap_only=1\r\n");
    a90_console_printf("server_exposure_attempted=1\r\n");
    a90_console_printf("listener_start_attempted=1\r\n");
    a90_console_printf("hostapd_start_attempted=0\r\n");
    a90_console_printf("ssid_psk_logged=0\r\n");
    a90_console_printf("client_identity_logged=0\r\n");
    a90_console_printf("peer_address_logged=0\r\n");
    a90_console_printf("address_value_logged=0\r\n");
    a90_console_printf("wan_nat_attempted=0\r\n");
    a90_console_printf("ip_forward_write_attempted=0\r\n");
    a90_console_printf("nat_attempted=0\r\n");
    a90_console_printf("default_route_export_attempted=0\r\n");
    a90_console_printf("dhcp_router_option_exported=0\r\n");
    a90_console_printf("dhcp_dns_option_exported=0\r\n");

    if (wifi_softap_format_ipv4(1, ap_ip, sizeof(ap_ip)) < 0) {
        a90_console_printf("decision=softap-transfer-address-format-failed\r\n");
        return -EINVAL;
    }

    ap_start_rc = wifi_softap_start(channel, freq_mhz);
    a90_console_printf("ap_start.rc=%d\r\n", ap_start_rc);
    if (ap_start_rc < 0) {
        a90_console_printf("decision=softap-transfer-ap-start-failed\r\n");
        return ap_start_rc;
    }

    transfer_prepare_rc = wifi_softap_prepare_transfer_dirs();
    a90_console_printf("transfer_runtime_prepare_rc=%d\r\n", transfer_prepare_rc);
    if (transfer_prepare_rc < 0) {
        (void)wifi_softap_cleanup_internal("transfer_rollback_cleanup");
        a90_console_printf("decision=softap-transfer-runtime-prepare-failed\r\n");
        return transfer_prepare_rc;
    }

    payload_rc = wifi_softap_write_download_payload(download_sha256,
                                                   sizeof(download_sha256),
                                                   &download_bytes);
    a90_console_printf("download_payload_write_rc=%d\r\n", payload_rc);
    a90_console_printf("download_payload_bytes=%ld\r\n", download_bytes);
    a90_console_printf("download_payload_sha256=%s\r\n",
                       payload_rc == 0 ? download_sha256 : "-");
    if (payload_rc < 0) {
        (void)wifi_softap_cleanup_internal("transfer_rollback_cleanup");
        a90_console_printf("decision=softap-transfer-download-payload-failed\r\n");
        return payload_rc;
    }

    a90_console_printf("httpd_start_attempted=1\r\n");
    http_spawn_rc = wifi_start_softap_httpd(ap_ip, &http_pid);
    a90_console_printf("httpd_spawn_rc=%d\r\n", http_spawn_rc);
    a90_console_printf("httpd_pid=%ld\r\n", http_spawn_rc == 0 ? (long)http_pid : -1L);
    if (http_spawn_rc == 0) {
        http_pid_write_rc = wifi_write_pid_file(A90_WIFI_SOFTAP_HTTPD_PID, http_pid);
    }
    a90_console_printf("httpd_pid_write_rc=%d\r\n", http_pid_write_rc);
    if (http_spawn_rc < 0 || http_pid_write_rc < 0) {
        (void)wifi_softap_cleanup_internal("transfer_rollback_cleanup");
        a90_console_printf("decision=softap-transfer-httpd-spawn-failed\r\n");
        return http_spawn_rc < 0 ? http_spawn_rc : http_pid_write_rc;
    }
    usleep(250000);
    http_alive = wifi_process_alive(http_pid) ? 1 : 0;
    a90_console_printf("httpd_alive=%d\r\n", http_alive);
    if (!http_alive) {
        (void)wifi_softap_cleanup_internal("transfer_rollback_cleanup");
        a90_console_printf("decision=softap-transfer-httpd-exited\r\n");
        return -ECHILD;
    }

    a90_console_printf("upload_receiver_start_attempted=1\r\n");
    upload_spawn_rc = wifi_start_softap_upload_receiver(ap_ip, &upload_pid);
    a90_console_printf("upload_receiver_spawn_rc=%d\r\n", upload_spawn_rc);
    a90_console_printf("upload_receiver_pid=%ld\r\n",
                       upload_spawn_rc == 0 ? (long)upload_pid : -1L);
    if (upload_spawn_rc == 0) {
        upload_pid_write_rc = wifi_write_pid_file(A90_WIFI_SOFTAP_UPLOAD_PID, upload_pid);
    }
    a90_console_printf("upload_receiver_pid_write_rc=%d\r\n", upload_pid_write_rc);
    if (upload_spawn_rc < 0 || upload_pid_write_rc < 0) {
        (void)wifi_softap_cleanup_internal("transfer_rollback_cleanup");
        a90_console_printf("decision=softap-transfer-upload-receiver-spawn-failed\r\n");
        return upload_spawn_rc < 0 ? upload_spawn_rc : upload_pid_write_rc;
    }
    usleep(250000);
    upload_alive = wifi_process_alive(upload_pid) ? 1 : 0;
    a90_console_printf("upload_receiver_alive=%d\r\n", upload_alive);
    if (!upload_alive) {
        (void)wifi_softap_cleanup_internal("transfer_rollback_cleanup");
        a90_console_printf("decision=softap-transfer-upload-receiver-exited\r\n");
        return -ECHILD;
    }

    a90_logf("wifi-softap",
             "transfer start pass iface=%s http=%d upload=%d",
             A90_WIFI_SOFTAP_PROBE_IFACE,
             A90_WIFI_SOFTAP_HTTP_PORT,
             A90_WIFI_SOFTAP_UPLOAD_PORT);
    a90_console_printf("decision=softap-transfer-start-pass\r\n");
    return 0;
}

static int wifi_softap_stop_sta_supplicant_if_needed(void) {
    int before_count = wifi_count_processes_with_token("wpa_supplicant");
    int terminate_wait_rc = 0;
    int terminate_wait_elapsed_ms = 0;
    int kill_rc = 0;
    int kill_wait_rc = 0;
    int kill_wait_elapsed_ms = 0;
    int after_terminate_count;
    int final_count;

    a90_console_printf("sta_supplicant.process_count_before=%d\r\n", before_count);
    if (before_count <= 0) {
        a90_console_printf("sta_supplicant.stop_attempted=0\r\n");
        a90_console_printf("sta_supplicant.terminate_wait_rc=0\r\n");
        a90_console_printf("sta_supplicant.kill_attempted=0\r\n");
        a90_console_printf("sta_supplicant.process_count_final=%d\r\n", before_count < 0 ? before_count : 0);
        a90_console_printf("sta_supplicant.stoppable=%d\r\n", before_count < 0 ? 0 : 1);
        return before_count < 0 ? before_count : 0;
    }

    a90_console_printf("sta_supplicant.stop_attempted=1\r\n");
    (void)wifi_print_ctrl_result("sta_supplicant.ctrl_terminate", "TERMINATE");
    terminate_wait_rc = wifi_wait_processes_gone("wpa_supplicant",
                                                 A90_WIFI_SUPPLICANT_TERMINATE_WAIT_MS,
                                                 &terminate_wait_elapsed_ms);
    after_terminate_count = wifi_count_processes_with_token("wpa_supplicant");
    a90_console_printf("sta_supplicant.terminate_wait_timeout_ms=%d\r\n",
                       A90_WIFI_SUPPLICANT_TERMINATE_WAIT_MS);
    a90_console_printf("sta_supplicant.terminate_wait_rc=%d\r\n", terminate_wait_rc);
    a90_console_printf("sta_supplicant.terminate_wait_elapsed_ms=%d\r\n",
                       terminate_wait_elapsed_ms);
    a90_console_printf("sta_supplicant.process_count_after_terminate=%d\r\n",
                       after_terminate_count);
    if (terminate_wait_rc < 0) {
        a90_console_printf("sta_supplicant.kill_attempted=1\r\n");
        kill_rc = wifi_signal_processes_with_token("wpa_supplicant", SIGKILL);
        kill_wait_rc = wifi_wait_processes_gone("wpa_supplicant",
                                                A90_WIFI_SUPPLICANT_KILL_WAIT_MS,
                                                &kill_wait_elapsed_ms);
        a90_console_printf("sta_supplicant.kill_rc=%d\r\n", kill_rc);
        a90_console_printf("sta_supplicant.kill_wait_timeout_ms=%d\r\n",
                           A90_WIFI_SUPPLICANT_KILL_WAIT_MS);
        a90_console_printf("sta_supplicant.kill_wait_rc=%d\r\n", kill_wait_rc);
        a90_console_printf("sta_supplicant.kill_wait_elapsed_ms=%d\r\n",
                           kill_wait_elapsed_ms);
    } else {
        a90_console_printf("sta_supplicant.kill_attempted=0\r\n");
        a90_console_printf("sta_supplicant.kill_rc=0\r\n");
        a90_console_printf("sta_supplicant.kill_wait_rc=0\r\n");
    }
    final_count = wifi_count_processes_with_token("wpa_supplicant");
    a90_console_printf("sta_supplicant.process_count_final=%d\r\n", final_count);
    a90_console_printf("sta_supplicant.stoppable=%d\r\n", final_count == 0 ? 1 : 0);
    if (final_count != 0) {
        return -EBUSY;
    }
    if (kill_rc < 0) {
        return kill_rc;
    }
    if (kill_wait_rc < 0) {
        return kill_wait_rc;
    }
    return 0;
}

static int wifi_softap_iftype_probe(int wait_timeout_ms) {
    int wlan0_wait_elapsed_ms = 0;
    int wlan0_wait_rc;
    int link_up_errno = 0;
    int link_up_rc;
    int socket_fd;
    int family_id;
    unsigned int parent_ifindex;
    unsigned int preexisting_ifindex;
    unsigned int created_ifindex = 0;
    int precleanup_rc = 0;
    int precleanup_errno = 0;
    int add_rc = -1;
    int add_errno = 0;
    int cleanup_rc = 0;
    int cleanup_errno = 0;
    int supplicant_stop_rc;

    if (wait_timeout_ms < 0) {
        wait_timeout_ms = A90_WIFI_SOFTAP_WLAN0_WAIT_MS;
    }
    if (wait_timeout_ms > A90_WIFI_SOFTAP_IFTYPE_PROBE_MAX_WAIT_MS) {
        wait_timeout_ms = A90_WIFI_SOFTAP_IFTYPE_PROBE_MAX_WAIT_MS;
    }

    a90_console_printf("[wifi softap iftype-probe]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SOFTAP_VERSION);
    a90_console_printf("scope=s3-ap-iftype-add-delete-probe-no-ap-start\r\n");
    a90_console_printf("iface=%s\r\n", A90_WIFI_IFACE);
    a90_console_printf("ap_probe_iface=%s\r\n", A90_WIFI_SOFTAP_PROBE_IFACE);
    a90_console_printf("ap_iftype=AP\r\n");
    a90_console_printf("credentials=0\r\n");
    a90_console_printf("ssid_psk_logged=0\r\n");
    a90_console_printf("config_write_attempted=0\r\n");
    a90_console_printf("wpa_supplicant_mode2_start_attempted=0\r\n");
    a90_console_printf("dhcp_server_start_attempted=0\r\n");
    a90_console_printf("listener_start_attempted=0\r\n");
    a90_console_printf("address_assign_attempted=0\r\n");
    a90_console_printf("server_exposure_attempted=0\r\n");
    a90_console_printf("wlan0_wait_timeout_ms=%d\r\n", wait_timeout_ms);

    wlan0_wait_rc = wifi_wait_wlan0(wait_timeout_ms, &wlan0_wait_elapsed_ms);
    a90_console_printf("wlan0_wait_rc=%d\r\n", wlan0_wait_rc);
    a90_console_printf("wlan0_wait_elapsed_ms=%d\r\n", wlan0_wait_elapsed_ms);
    a90_console_printf("wlan0_present=%d\r\n", wlan0_wait_rc == 0 ? 1 : 0);
    if (wlan0_wait_rc < 0) {
        a90_console_printf("ap_iftype_add_attempted=0\r\n");
        a90_console_printf("ap_iftype_cleanup_attempted=0\r\n");
        a90_console_printf("decision=softap-iftype-probe-wlan0-timeout\r\n");
        return wlan0_wait_rc;
    }

    link_up_rc = wifi_link_set_up(A90_WIFI_IFACE, &link_up_errno);
    a90_console_printf("link_up_attempted=1\r\n");
    a90_console_printf("link_up_rc=%d\r\n", link_up_rc);
    a90_console_printf("link_up_errno=%d\r\n", link_up_errno);
    if (link_up_rc < 0) {
        a90_console_printf("ap_iftype_add_attempted=0\r\n");
        a90_console_printf("ap_iftype_cleanup_attempted=0\r\n");
        a90_console_printf("decision=softap-iftype-probe-link-up-failed\r\n");
        return -link_up_errno;
    }

    supplicant_stop_rc = wifi_softap_stop_sta_supplicant_if_needed();
    a90_console_printf("sta_supplicant.stop_rc=%d\r\n", supplicant_stop_rc);
    if (supplicant_stop_rc < 0) {
        a90_console_printf("ap_iftype_add_attempted=0\r\n");
        a90_console_printf("ap_iftype_cleanup_attempted=0\r\n");
        a90_console_printf("decision=softap-iftype-probe-sta-supplicant-busy\r\n");
        return supplicant_stop_rc;
    }

    parent_ifindex = if_nametoindex(A90_WIFI_IFACE);
    a90_console_printf("ifindex=%u\r\n", parent_ifindex);
    if (parent_ifindex == 0) {
        a90_console_printf("ap_iftype_add_attempted=0\r\n");
        a90_console_printf("ap_iftype_cleanup_attempted=0\r\n");
        a90_console_printf("decision=softap-iftype-probe-interface-missing\r\n");
        return -ENODEV;
    }

    socket_fd = wifi_open_genl_socket();
    if (socket_fd < 0) {
        int saved_errno = errno;

        a90_console_printf("netlink_open=0\r\n");
        a90_console_printf("netlink_errno=%d\r\n", saved_errno);
        a90_console_printf("ap_iftype_add_attempted=0\r\n");
        a90_console_printf("ap_iftype_cleanup_attempted=0\r\n");
        a90_console_printf("decision=softap-iftype-probe-nl80211-unavailable\r\n");
        return -saved_errno;
    }
    a90_console_printf("netlink_open=1\r\n");

    family_id = wifi_get_family_id(socket_fd, "nl80211");
    a90_console_printf("family_id=%d\r\n", family_id < 0 ? 0 : family_id);
    if (family_id < 0) {
        int saved_errno = errno;

        close(socket_fd);
        a90_console_printf("family_errno=%d\r\n", saved_errno);
        a90_console_printf("ap_iftype_add_attempted=0\r\n");
        a90_console_printf("ap_iftype_cleanup_attempted=0\r\n");
        a90_console_printf("decision=softap-iftype-probe-family-missing\r\n");
        return -saved_errno;
    }

    preexisting_ifindex = if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE);
    a90_console_printf("ap_iftype_preexisting=%d\r\n", preexisting_ifindex != 0 ? 1 : 0);
    if (preexisting_ifindex != 0) {
        precleanup_rc = wifi_send_nl80211_if_delete(socket_fd,
                                                    family_id,
                                                    10,
                                                    preexisting_ifindex);
        if (precleanup_rc < 0) {
            precleanup_errno = errno;
        }
    }
    a90_console_printf("ap_iftype_precleanup_attempted=%d\r\n", preexisting_ifindex != 0 ? 1 : 0);
    a90_console_printf("ap_iftype_precleanup_rc=%d\r\n", precleanup_rc);
    a90_console_printf("ap_iftype_precleanup_errno=%d\r\n", precleanup_errno);
    if (precleanup_rc < 0) {
        close(socket_fd);
        a90_console_printf("ap_iftype_add_attempted=0\r\n");
        a90_console_printf("ap_iftype_cleanup_attempted=1\r\n");
        a90_console_printf("ap_iftype_cleanup_ok=0\r\n");
        a90_console_printf("decision=softap-iftype-probe-precleanup-failed\r\n");
        return -precleanup_errno;
    }

    a90_console_printf("ap_iftype_add_attempted=1\r\n");
    add_rc = wifi_send_nl80211_iftype_new(socket_fd,
                                          family_id,
                                          11,
                                          parent_ifindex,
                                          A90_WIFI_SOFTAP_PROBE_IFACE,
                                          (uint32_t)NL80211_IFTYPE_AP);
    if (add_rc < 0) {
        add_errno = errno;
    }
    created_ifindex = if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE);
    a90_console_printf("ap_iftype_add_rc=%d\r\n", add_rc);
    a90_console_printf("ap_iftype_add_errno=%d\r\n", add_errno);
    a90_console_printf("ap_iftype_iface_created=%d\r\n", created_ifindex != 0 ? 1 : 0);
    a90_console_printf("ap_iftype_created_ifindex=%u\r\n", created_ifindex);

    if (created_ifindex != 0) {
        a90_console_printf("ap_iftype_cleanup_attempted=1\r\n");
        cleanup_rc = wifi_send_nl80211_if_delete(socket_fd,
                                                 family_id,
                                                 12,
                                                 created_ifindex);
        if (cleanup_rc < 0) {
            cleanup_errno = errno;
        }
    } else {
        a90_console_printf("ap_iftype_cleanup_attempted=0\r\n");
    }
    a90_console_printf("ap_iftype_cleanup_rc=%d\r\n", cleanup_rc);
    a90_console_printf("ap_iftype_cleanup_errno=%d\r\n", cleanup_errno);
    a90_console_printf("ap_iftype_cleanup_ok=%d\r\n",
                       if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE) == 0 ? 1 : 0);
    close(socket_fd);

    if (add_rc < 0) {
        a90_console_printf("decision=softap-iftype-probe-add-failed\r\n");
        return -add_errno;
    }
    if (cleanup_rc < 0 ||
        if_nametoindex(A90_WIFI_SOFTAP_PROBE_IFACE) != 0) {
        a90_console_printf("decision=softap-iftype-probe-cleanup-failed\r\n");
        return cleanup_rc < 0 ? -cleanup_errno : -EBUSY;
    }

    a90_console_printf("decision=softap-iftype-probe-pass\r\n");
    a90_logf("wifi-softap",
             "iftype-probe parent=%u created=%u cleanup=ok",
             parent_ifindex,
             created_ifindex);
    return 0;
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
               "softap-prepare-start-supported" :
               "softap-status-start-supported";
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
    a90_console_printf("scope=status-plan-start-supported-no-ap-start\r\n");
    a90_console_printf("runtime_root=%s\r\n", A90_WIFI_SOFTAP_ROOT);
    a90_console_printf("ssid_psk_logged=0\r\n");
    a90_console_printf("config_write_attempted=0\r\n");
    a90_console_printf("hostapd_start_attempted=0\r\n");
    a90_console_printf("wpa_supplicant_mode2_start_attempted=0\r\n");
    a90_console_printf("dhcp_server_start_attempted=0\r\n");
    a90_console_printf("listener_start_attempted=0\r\n");
    a90_console_printf("interface_mode_change_attempted=0\r\n");
    a90_console_printf("address_assign_attempted=0\r\n");
    a90_console_printf("server_exposure_attempted=0\r\n");
    a90_console_printf("wan_nat_attempted=0\r\n");
    a90_console_printf("default_route_export_attempted=0\r\n");
    a90_console_printf("start_supported=1\r\n");
    a90_console_printf("start_allowed=%d\r\n",
                       feasibility.decision == A90_WIFI_FEAS_GO_READ_ONLY_ONLY ? 1 : 0);
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
        a90_console_printf("plan.s3=mode2-ap-start-and-dhcp-done\r\n");
        a90_console_printf("plan.s4=transfer-start-status-cleanup-next\r\n");
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
        a90_console_printf("usage: wifi softap [status|plan|prepare [profile]|iftype-probe [timeout_ms]|start [channel]|transfer-start [channel]|transfer-status|cleanup]\r\n");
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
    if (strcmp(subcommand, "iftype-probe") == 0 && (argc == 3 || argc == 4)) {
        int timeout_ms = A90_WIFI_SOFTAP_WLAN0_WAIT_MS;

        if (argc == 4 &&
            wifi_parse_delay_ms_max(argv[3],
                                    &timeout_ms,
                                    A90_WIFI_SOFTAP_IFTYPE_PROBE_MAX_WAIT_MS) < 0) {
            a90_console_printf("usage: wifi softap iftype-probe [timeout_ms]\r\n");
            return -EINVAL;
        }
        return wifi_softap_iftype_probe(timeout_ms);
    }
    if (strcmp(subcommand, "start") == 0 && (argc == 3 || argc == 4)) {
        int channel = 6;
        int freq_mhz = 2437;

        if (wifi_softap_parse_channel(argc == 4 ? argv[3] : NULL, &channel, &freq_mhz) < 0) {
            a90_console_printf("usage: wifi softap start [1|6|11]\r\n");
            return -EINVAL;
        }
        return wifi_softap_start(channel, freq_mhz);
    }
    if (strcmp(subcommand, "transfer-start") == 0 && (argc == 3 || argc == 4)) {
        int channel = 6;
        int freq_mhz = 2437;

        if (wifi_softap_parse_channel(argc == 4 ? argv[3] : NULL, &channel, &freq_mhz) < 0) {
            a90_console_printf("usage: wifi softap transfer-start [1|6|11]\r\n");
            return -EINVAL;
        }
        return wifi_softap_transfer_start(channel, freq_mhz);
    }
    if (strcmp(subcommand, "transfer-status") == 0 && argc == 3) {
        return wifi_softap_transfer_status_command();
    }
    if (strcmp(subcommand, "cleanup") == 0 && argc == 3) {
        return wifi_softap_cleanup_command();
    }

    a90_console_printf("usage: wifi softap [status|plan|prepare [profile]|iftype-probe [timeout_ms]|start [channel]|transfer-start [channel]|transfer-status|cleanup]\r\n");
    return -EINVAL;
}

static int wifi_service_status_command(const char *root) {
    char pid_path[A90_WIFI_SERVICE_MAX_PATH];
    char state_path[A90_WIFI_SERVICE_MAX_PATH];
    char pid_file[128] = "";
    char state_file[256] = "";
    char pid_text[32] = "";
    long pid_value = -1;
    int pid_rc;
    int state_rc;
    int alive = 0;
    int rc;

    a90_console_printf("[wifi service status]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_SERVICE_VERSION);
    a90_console_printf("root=%s\r\n", root != NULL ? root : "-");
    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_PID_FILE, pid_path, sizeof(pid_path));
    if (rc < 0) {
        a90_console_printf("pidfile_present=0\r\n");
        a90_console_printf("alive=0\r\n");
        a90_console_printf("decision=wifi-service-status-invalid-root\r\n");
        return rc;
    }
    pid_rc = wifi_service_read_file_no_follow(pid_path, pid_file, sizeof(pid_file));
    if (pid_rc == 0 &&
        wifi_service_request_value(pid_file, "pid", pid_text, sizeof(pid_text)) == 0 &&
        wifi_service_parse_long(pid_text, &pid_value) == 0 &&
        pid_value > 1) {
        alive = (kill((pid_t)pid_value, 0) == 0 || errno == EPERM) ? 1 : 0;
    }
    a90_console_printf("pidfile_present=%d\r\n", pid_rc == 0 ? 1 : 0);
    a90_console_printf("pid=%ld\r\n", pid_value);
    a90_console_printf("alive=%d\r\n", alive);

    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_STATE_FILE, state_path, sizeof(state_path));
    state_rc = rc == 0 ? wifi_service_read_file_no_follow(state_path, state_file, sizeof(state_file)) : rc;
    a90_console_printf("statefile_present=%d\r\n", state_rc == 0 ? 1 : 0);
    if (state_rc == 0) {
        flatten_inline_text(state_file);
        a90_console_printf("state_inline=%s\r\n", state_file);
    }
    a90_console_printf("decision=%s\r\n", alive ? "wifi-service-status-running" : "wifi-service-status-stopped");
    return 0;
}

static int wifi_service_cmd(char **argv, int argc) {
    const char *subcommand;

    if (argv == NULL || argc < 3 || argv[2] == NULL) {
        a90_console_printf("usage: wifi service [status|start|stop|once] <dir> [lifetime_ms poll_ms scan_delay_ms]\r\n");
        return -EINVAL;
    }
    subcommand = argv[2];

    if (strcmp(subcommand, "status") == 0) {
        if (argc != 4) {
            a90_console_printf("usage: wifi service status <dir>\r\n");
            return -EINVAL;
        }
        return wifi_service_status_command(argv[3]);
    }
    if (strcmp(subcommand, "stop") == 0) {
        int rc;

        if (argc != 4) {
            a90_console_printf("usage: wifi service stop <dir>\r\n");
            return -EINVAL;
        }
        a90_console_printf("[wifi service stop]\r\n");
        a90_console_printf("version=%s\r\n", A90_WIFI_SERVICE_VERSION);
        a90_console_printf("root=%s\r\n", argv[3]);
        rc = wifi_service_stop(argv[3]);
        a90_console_printf("stop_rc=%d\r\n", rc);
        a90_console_printf("decision=%s\r\n",
                           rc == 0 ? "wifi-service-stop-pass" : "wifi-service-stop-failed");
        return rc;
    }
    if (strcmp(subcommand, "once") == 0) {
        int scan_delay_ms = A90_WIFI_SERVICE_DEFAULT_SCAN_DELAY_MS;
        long seq = -1;
        int rc;

        if (argc != 4 && argc != 5) {
            a90_console_printf("usage: wifi service once <dir> [scan_delay_ms]\r\n");
            return -EINVAL;
        }
        if (argc == 5 && wifi_parse_delay_ms(argv[4], &scan_delay_ms) < 0) {
            a90_console_printf("usage: wifi service once <dir> [scan_delay_ms]\r\n");
            return -EINVAL;
        }
        a90_console_printf("[wifi service once]\r\n");
        a90_console_printf("version=%s\r\n", A90_WIFI_SERVICE_VERSION);
        a90_console_printf("root=%s\r\n", argv[3]);
        rc = wifi_service_process_once(argv[3], scan_delay_ms, -1, &seq);
        a90_console_printf("request_seq=%ld\r\n", seq);
        a90_console_printf("process_rc=%d\r\n", rc);
        a90_console_printf("response_file=%s/%s\r\n", argv[3], A90_WIFI_SERVICE_RESPONSE_FILE);
        a90_console_printf("decision=%s\r\n",
                           rc == 0 ? "wifi-service-once-pass" : "wifi-service-once-failed");
        return rc;
    }
    if (strcmp(subcommand, "start") == 0) {
        int lifetime_ms = A90_WIFI_SERVICE_DEFAULT_LIFETIME_MS;
        int poll_ms = A90_WIFI_SERVICE_DEFAULT_POLL_MS;
        int scan_delay_ms = A90_WIFI_SERVICE_DEFAULT_SCAN_DELAY_MS;
        int pid_or_rc;

        if (argc < 4 || argc > 7) {
            a90_console_printf("usage: wifi service start <dir> [lifetime_ms poll_ms scan_delay_ms]\r\n");
            return -EINVAL;
        }
        if (argc >= 5 &&
            wifi_parse_delay_ms_max(argv[4], &lifetime_ms, A90_WIFI_SERVICE_MAX_LIFETIME_MS) < 0) {
            a90_console_printf("usage: wifi service start <dir> [lifetime_ms poll_ms scan_delay_ms]\r\n");
            return -EINVAL;
        }
        if (argc >= 6 &&
            wifi_parse_delay_ms_max(argv[5], &poll_ms, A90_WIFI_SERVICE_MAX_POLL_MS) < 0) {
            a90_console_printf("usage: wifi service start <dir> [lifetime_ms poll_ms scan_delay_ms]\r\n");
            return -EINVAL;
        }
        if (argc >= 7 && wifi_parse_delay_ms(argv[6], &scan_delay_ms) < 0) {
            a90_console_printf("usage: wifi service start <dir> [lifetime_ms poll_ms scan_delay_ms]\r\n");
            return -EINVAL;
        }
        a90_console_printf("[wifi service start]\r\n");
        a90_console_printf("version=%s\r\n", A90_WIFI_SERVICE_VERSION);
        a90_console_printf("root=%s\r\n", argv[3]);
        a90_console_printf("lifetime_ms=%d\r\n", lifetime_ms);
        a90_console_printf("poll_ms=%d\r\n", poll_ms);
        a90_console_printf("scan_delay_ms=%d\r\n", scan_delay_ms);
        a90_console_printf("credentials=0\r\n");
        a90_console_printf("connect=0\r\n");
        a90_console_printf("dhcp_routing=0\r\n");
        a90_console_printf("public_tunnel=0\r\n");
        pid_or_rc = wifi_service_start(argv[3], lifetime_ms, poll_ms, scan_delay_ms);
        a90_console_printf("pid=%d\r\n", pid_or_rc > 0 ? pid_or_rc : -1);
        a90_console_printf("start_rc=%d\r\n", pid_or_rc > 0 ? 0 : pid_or_rc);
        a90_console_printf("request_file=%s/%s\r\n", argv[3], A90_WIFI_SERVICE_REQUEST_FILE);
        a90_console_printf("response_file=%s/%s\r\n", argv[3], A90_WIFI_SERVICE_RESPONSE_FILE);
        a90_console_printf("decision=%s\r\n",
                           pid_or_rc > 0 ? "wifi-service-start-pass" : "wifi-service-start-failed");
        return pid_or_rc > 0 ? 0 : pid_or_rc;
    }

    a90_console_printf("usage: wifi service [status|start|stop|once] <dir> [lifetime_ms poll_ms scan_delay_ms]\r\n");
    return -EINVAL;
}

static void wifi_uplink_service_append_autoconnect_result(char *response,
                                                          size_t response_size,
                                                          size_t *offset) {
    char result[8192];
    char value[128];
    int rc = wifi_service_read_file_no_follow(A90_WIFI_AUTOCONNECT_RESULT,
                                              result,
                                              sizeof(result));

    wifi_service_append(response,
                        response_size,
                        offset,
                        "autoconnect_result_present=%d\n",
                        rc == 0 ? 1 : 0);
    if (rc < 0) {
        wifi_service_append(response, response_size, offset, "autoconnect_result_rc=%d\n", rc);
        return;
    }
    if (wifi_service_request_value(result, "decision", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "autoconnect_decision=%s\n", value);
    }
    wifi_service_append(response,
                        response_size,
                        offset,
                        "autoconnect_profile_present=%d\n",
                        wifi_service_request_value(result, "profile", value, sizeof(value)) == 0 &&
                        value[0] != '\0' ? 1 : 0);
    if (wifi_service_request_value(result, "connect_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "dhcp_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "dhcp_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "final_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "final_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "carrier_up", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "carrier_up=%s\n", value);
    }
    if (wifi_service_request_value(result, "default_route_present", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "default_route_present=%s\n", value);
    }
    if (wifi_service_request_value(result, "nameserver_count", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "nameserver_count=%s\n", value);
    }
    if (wifi_service_request_value(result, "scan_recovery_attempted", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "scan_recovery_attempted=%s\n", value);
    }
    if (wifi_service_request_value(result, "scan_recovery_first_scan_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "scan_recovery_first_scan_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "scan_recovery_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "scan_recovery_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "scan_recovery_rescan_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "scan_recovery_rescan_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "scan_recovery_success", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "scan_recovery_success=%s\n", value);
    }
    if (wifi_service_request_value(result, "scan_recovery_decision", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "scan_recovery_decision=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_diag_attempted", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_diag_attempted=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_diag_decision", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_diag_decision=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wlan0_wait_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wlan0_wait_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wlan0_wait_elapsed_ms", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wlan0_wait_elapsed_ms=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_link_up_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_link_up_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_link_up_errno", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_link_up_errno=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_prepare_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_prepare_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_runtime_prepare_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_runtime_prepare_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_supplicant_root_exec_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_supplicant_root_exec_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_supplicant_process_count_before", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_supplicant_process_count_before=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_supplicant_start_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_supplicant_start_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_wait_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_wait_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_wait_errno", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_wait_errno=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_wait_elapsed_ms", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_wait_elapsed_ms=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_wait_category", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_wait_category=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_driver_country_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_driver_country_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_scan_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_scan_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_enable_network_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_enable_network_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_select_network_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_select_network_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_reassociate_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_reassociate_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_carrier_wait_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_carrier_wait_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_carrier_wait_elapsed_ms", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_carrier_wait_elapsed_ms=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_carrier_up_at_wait", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_carrier_up_at_wait=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_complete_wait_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_complete_wait_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_complete_wait_elapsed_ms", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_complete_wait_elapsed_ms=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_complete_samples", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_complete_samples=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_complete_completed", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_complete_completed=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_complete_retry_count", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_complete_retry_count=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_complete_first_state", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_complete_first_state=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_complete_last_state", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_complete_last_state=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_attach_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_attach_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_attach_errno", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_attach_errno=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_event_count", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_event_count=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_connected_seen", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_connected_seen=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_disconnected_seen", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_disconnected_seen=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_scan_results_seen", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_scan_results_seen=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_assoc_reject_seen", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_assoc_reject_seen=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_auth_reject_seen", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_auth_reject_seen=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_temp_disabled_seen", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_temp_disabled_seen=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_eap_failure_seen", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_eap_failure_seen=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_last_event", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_last_event=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_disconnect_reason_class", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_disconnect_reason_class=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_temp_disabled_reason_class", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_temp_disabled_reason_class=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_wpa_monitor_assoc_reject_status_class", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_wpa_monitor_assoc_reject_status_class=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_errno", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_errno=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_wpa_state", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_wpa_state=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_network_id", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_network_id=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_network_selected", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_network_selected=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_key_mgmt", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_key_mgmt=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_pairwise_cipher", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_pairwise_cipher=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_group_cipher", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_group_cipher=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_mode", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_mode=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_freq_mhz", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_freq_mhz=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_status_completed", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_status_completed=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_signal_rc", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_signal_rc=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_ctrl_signal_errno", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_ctrl_signal_errno=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_supplicant_spawned", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_supplicant_spawned=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_supplicant_left_running", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_supplicant_left_running=%s\n", value);
    }
    if (wifi_service_request_value(result, "connect_cleanup_status", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "connect_cleanup_status=%s\n", value);
    }
    if (wifi_service_request_value(result, "secret_values_logged", value, sizeof(value)) == 0) {
        wifi_service_append(response, response_size, offset, "secret_values_logged=%s\n", value);
    }
}

static void wifi_uplink_service_append_autoconnect_config(char *response,
                                                          size_t response_size,
                                                          size_t *offset,
                                                          const char *profile) {
    struct a90_wificfg_autoconnect config;
    int rc = a90_wificfg_get_autoconnect(&config, profile);

    wifi_service_append(response, response_size, offset, "autoconnect_config_rc=%d\n", rc);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "autoconnect_ready=%d\n",
                        rc == 0 ? 1 : 0);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "autoconnect_enabled=%d\n",
                        config.enabled ? 1 : 0);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "config_profile_present=%d\n",
                        config.profile[0] != '\0' ||
                        (profile != NULL && profile[0] != '\0') ? 1 : 0);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "profile_valid=%d\n",
                        config.profile_valid ? 1 : 0);
    wifi_service_append(response, response_size, offset, "connect_timeout_sec=%d\n", config.connect_timeout_sec);
    wifi_service_append(response, response_size, offset, "dhcp=%d\n", config.dhcp);
    wifi_service_append(response, response_size, offset, "scan_before_connect=%d\n", config.scan_before_connect);
    wifi_service_append(response, response_size, offset, "retry_count=%d\n", config.retry_count);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "external_ping_blocked=%d\n",
                        config.external_ping != 0 ? 1 : 0);
    wifi_service_append(response, response_size, offset, "autoconnect_config_decision=%s\n", config.decision);
}

static int wifi_uplink_service_format_status_response(char *response,
                                                      size_t response_size,
                                                      size_t *offset,
                                                      const char *seq,
                                                      const char *op,
                                                      const char *profile) {
    struct a90_wifi_status_snapshot status;
    int rc = a90_wifi_status_snapshot(&status);

    wifi_service_append(response, response_size, offset, "version=%s\n", A90_WIFI_UPLINK_SERVICE_VERSION);
    wifi_service_append(response, response_size, offset, "seq=%s\n", seq);
    wifi_service_append(response, response_size, offset, "op=%s\n", op);
    wifi_service_append(response, response_size, offset, "owner=native-init\n");
    wifi_service_append(response, response_size, offset, "credentials=0\n");
    wifi_service_append(response, response_size, offset, "connect=0\n");
    wifi_service_append(response, response_size, offset, "dhcp_routing=observed-only\n");
    wifi_service_append(response, response_size, offset, "external_ping_execution=0\n");
    wifi_service_append(response, response_size, offset, "public_tunnel=0\n");
    wifi_service_append(response, response_size, offset, "raw_values_redacted=1\n");
    wifi_service_append(response, response_size, offset, "secret_values_logged=0\n");
    wifi_service_append(response, response_size, offset, "rc=%d\n", rc);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "wlan0_present=%d\n",
                        status.wlan0_present ? 1 : 0);
    wifi_service_append(response, response_size, offset, "operstate=%s\n", status.operstate);
    wifi_service_append(response, response_size, offset, "carrier=%s\n", status.carrier);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "default_route_present=%d\n",
                        status.route_default_present ? 1 : 0);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "nameserver_count=%d\n",
                        status.nameserver_count >= 0 ? status.nameserver_count : 0);
    wifi_uplink_service_append_autoconnect_config(response, response_size, offset, profile);
    wifi_uplink_service_append_autoconnect_result(response, response_size, offset);
    wifi_service_append(response, response_size, offset, "decision=wifi-uplink-service-status-pass\n");
    return rc;
}

static int wifi_uplink_service_format_autoconnect_response(char *response,
                                                           size_t response_size,
                                                           size_t *offset,
                                                           const char *seq,
                                                           const char *op,
                                                           const char *profile,
                                                           int autoconnect_rc) {
    wifi_service_append(response, response_size, offset, "version=%s\n", A90_WIFI_UPLINK_SERVICE_VERSION);
    wifi_service_append(response, response_size, offset, "seq=%s\n", seq);
    wifi_service_append(response, response_size, offset, "op=%s\n", op);
    wifi_service_append(response, response_size, offset, "owner=native-init\n");
    wifi_service_append(response, response_size, offset, "credentials=private-config-gated\n");
    wifi_service_append(response, response_size, offset, "connect=confirm-gated\n");
    wifi_service_append(response, response_size, offset, "dhcp_routing=config-gated\n");
    wifi_service_append(response, response_size, offset, "external_ping_execution=0\n");
    wifi_service_append(response, response_size, offset, "public_tunnel=0\n");
    wifi_service_append(response, response_size, offset, "raw_values_redacted=1\n");
    wifi_service_append(response, response_size, offset, "rc=%d\n", autoconnect_rc);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "requested_profile_present=%d\n",
                        profile != NULL && profile[0] != '\0' ? 1 : 0);
    wifi_uplink_service_append_autoconnect_result(response, response_size, offset);
    wifi_service_append(response,
                        response_size,
                        offset,
                        "decision=%s\n",
                        autoconnect_rc == 0 ?
                        "wifi-uplink-service-autoconnect-pass" :
                        "wifi-uplink-service-autoconnect-failed");
    return autoconnect_rc;
}

static int wifi_uplink_service_process_once(const char *root, long skip_seq, long *seq_out) {
    char request_path[A90_WIFI_SERVICE_MAX_PATH];
    char request[A90_WIFI_SERVICE_MAX_REQUEST];
    char response[12288];
    char seq[64] = "";
    char op[32] = "";
    char profile[96] = "";
    char confirm[96] = "";
    long seq_value = -1;
    size_t offset = 0;
    int rc;

    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_REQUEST_FILE, request_path, sizeof(request_path));
    if (rc < 0) {
        return rc;
    }
    rc = wifi_service_read_file_no_follow(request_path, request, sizeof(request));
    if (rc < 0) {
        return rc;
    }
    if (wifi_service_request_value(request, "seq", seq, sizeof(seq)) < 0 ||
        wifi_service_parse_long(seq, &seq_value) < 0 ||
        wifi_service_request_value(request, "op", op, sizeof(op)) < 0) {
        snprintf(response,
                 sizeof(response),
                 "version=%s\nseq=-1\nop=invalid\nowner=native-init\nrc=-22\ndecision=wifi-uplink-service-request-invalid\n",
                 A90_WIFI_UPLINK_SERVICE_VERSION);
        (void)wifi_service_write_response(root, response);
        return -EINVAL;
    }
    if (seq_value == skip_seq) {
        if (seq_out != NULL) {
            *seq_out = seq_value;
        }
        return 1;
    }
    (void)wifi_service_request_value(request, "profile", profile, sizeof(profile));

    if (strcmp(op, "status") == 0) {
        rc = wifi_uplink_service_format_status_response(response,
                                                        sizeof(response),
                                                        &offset,
                                                        seq,
                                                        op,
                                                        profile[0] != '\0' ? profile : NULL);
    } else if (strcmp(op, "autoconnect") == 0) {
        int autoconnect_rc;

        if (wifi_service_request_value(request, "confirm", confirm, sizeof(confirm)) < 0 ||
            strcmp(confirm, A90_WIFI_UPLINK_SERVICE_CONFIRM) != 0) {
            wifi_service_append(response,
                                sizeof(response),
                                &offset,
                                "version=%s\nseq=%s\nop=%s\nowner=native-init\ncredentials=private-config-gated\nconnect=confirm-gated\ndhcp_routing=config-gated\nexternal_ping_execution=0\npublic_tunnel=0\nsecret_values_logged=0\nrc=-13\ndecision=wifi-uplink-service-confirm-required\n",
                                A90_WIFI_UPLINK_SERVICE_VERSION,
                                seq,
                                op);
            rc = -EACCES;
        } else {
            autoconnect_rc = wifi_run_autoconnect_sequence(profile[0] != '\0' ? profile : NULL, true);
            rc = wifi_uplink_service_format_autoconnect_response(response,
                                                                 sizeof(response),
                                                                 &offset,
                                                                 seq,
                                                                 op,
                                                                 profile[0] != '\0' ? profile : NULL,
                                                                 autoconnect_rc);
        }
    } else {
        wifi_service_append(response,
                            sizeof(response),
                            &offset,
                            "version=%s\nseq=%s\nop=%s\nowner=native-init\ncredentials=0\nconnect=0\ndhcp_routing=0\nexternal_ping_execution=0\npublic_tunnel=0\nsecret_values_logged=0\nrc=-22\ndecision=wifi-uplink-service-op-denied\n",
                            A90_WIFI_UPLINK_SERVICE_VERSION,
                            seq,
                            op);
        rc = -EINVAL;
    }
    if (wifi_service_write_response(root, response) < 0 && rc == 0) {
        rc = -EIO;
    }
    if (seq_out != NULL) {
        *seq_out = seq_value;
    }
    return rc;
}

static void wifi_uplink_service_daemon_run(const char *root, int lifetime_ms, int poll_ms) {
    char state_path[A90_WIFI_SERVICE_MAX_PATH] = "";
    long deadline_ms = monotonic_millis() + lifetime_ms;
    long last_seq = -1;

    if (wifi_service_join_path(root, A90_WIFI_SERVICE_STATE_FILE, state_path, sizeof(state_path)) == 0) {
        (void)wifi_service_write_file_no_follow(state_path,
                                                "version=" A90_WIFI_UPLINK_SERVICE_VERSION "\nstate=running\n",
                                                0644);
    }
    while (monotonic_millis() <= deadline_ms) {
        long seq = -1;
        int rc = wifi_uplink_service_process_once(root, last_seq, &seq);

        if (rc != -ENOENT && rc != 1 && seq >= 0 && seq != last_seq) {
            last_seq = seq;
        }
        usleep((useconds_t)poll_ms * 1000U);
    }
    if (state_path[0] != '\0') {
        (void)wifi_service_write_file_no_follow(state_path,
                                                "version=" A90_WIFI_UPLINK_SERVICE_VERSION "\nstate=stopped\n",
                                                0644);
    }
    _exit(0);
}

static int wifi_uplink_service_start(const char *root, int lifetime_ms, int poll_ms) {
    char pid_path[A90_WIFI_SERVICE_MAX_PATH];
    char pid_text[64];
    pid_t pid;
    int rc;

    if (root == NULL || root[0] != '/') {
        return -EINVAL;
    }
    if (strlen(root) >= A90_WIFI_SERVICE_MAX_ROOT) {
        return -ENAMETOOLONG;
    }
    rc = ensure_dir(root, 0755);
    if (rc < 0) {
        return negative_errno_or(EIO);
    }
    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_PID_FILE, pid_path, sizeof(pid_path));
    if (rc < 0) {
        return rc;
    }
    if (lifetime_ms <= 0) {
        lifetime_ms = A90_WIFI_SERVICE_DEFAULT_LIFETIME_MS;
    }
    if (lifetime_ms > A90_WIFI_SERVICE_MAX_LIFETIME_MS) {
        lifetime_ms = A90_WIFI_SERVICE_MAX_LIFETIME_MS;
    }
    if (poll_ms < A90_WIFI_SERVICE_MIN_POLL_MS) {
        poll_ms = A90_WIFI_SERVICE_MIN_POLL_MS;
    }
    if (poll_ms > A90_WIFI_SERVICE_MAX_POLL_MS) {
        poll_ms = A90_WIFI_SERVICE_MAX_POLL_MS;
    }

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        (void)setsid();
        wifi_uplink_service_daemon_run(root, lifetime_ms, poll_ms);
    }
    snprintf(pid_text,
             sizeof(pid_text),
             "version=%s\npid=%ld\n",
             A90_WIFI_UPLINK_SERVICE_VERSION,
             (long)pid);
    rc = wifi_service_write_file_no_follow(pid_path, pid_text, 0644);
    if (rc < 0) {
        (void)kill(pid, SIGTERM);
        return rc;
    }
    return (int)pid;
}

static int wifi_uplink_service_status_command(const char *root) {
    char pid_path[A90_WIFI_SERVICE_MAX_PATH];
    char state_path[A90_WIFI_SERVICE_MAX_PATH];
    char text[128];
    char pid_text[32];
    char state_file[256] = "";
    long pid_value = -1;
    int pid_rc;
    int state_rc;
    int alive = 0;
    int rc;

    if (root == NULL || root[0] != '/') {
        return -EINVAL;
    }
    a90_console_printf("[wifi uplink-service status]\r\n");
    a90_console_printf("version=%s\r\n", A90_WIFI_UPLINK_SERVICE_VERSION);
    a90_console_printf("root=%s\r\n", root);
    a90_console_printf("confirm_token=%s\r\n", A90_WIFI_UPLINK_SERVICE_CONFIRM);
    a90_console_printf("credentials=private-config-gated\r\n");
    a90_console_printf("connect=confirm-gated\r\n");
    a90_console_printf("dhcp_routing=config-gated\r\n");
    a90_console_printf("external_ping_execution=0\r\n");
    a90_console_printf("public_tunnel=0\r\n");
    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_PID_FILE, pid_path, sizeof(pid_path));
    pid_rc = rc == 0 ? wifi_service_read_file_no_follow(pid_path, text, sizeof(text)) : rc;
    if (pid_rc == 0 &&
        wifi_service_request_value(text, "pid", pid_text, sizeof(pid_text)) == 0 &&
        wifi_service_parse_long(pid_text, &pid_value) == 0 &&
        pid_value > 1 &&
        kill((pid_t)pid_value, 0) == 0) {
        alive = 1;
    }
    a90_console_printf("pidfile_present=%d\r\n", pid_rc == 0 ? 1 : 0);
    a90_console_printf("pid=%ld\r\n", pid_value);
    a90_console_printf("alive=%d\r\n", alive);

    rc = wifi_service_join_path(root, A90_WIFI_SERVICE_STATE_FILE, state_path, sizeof(state_path));
    state_rc = rc == 0 ? wifi_service_read_file_no_follow(state_path, state_file, sizeof(state_file)) : rc;
    a90_console_printf("statefile_present=%d\r\n", state_rc == 0 ? 1 : 0);
    if (state_rc == 0) {
        flatten_inline_text(state_file);
        a90_console_printf("state_inline=%s\r\n", state_file);
    }
    a90_console_printf("decision=%s\r\n",
                       alive ? "wifi-uplink-service-status-running" : "wifi-uplink-service-status-stopped");
    return 0;
}

static int wifi_uplink_service_cmd(char **argv, int argc) {
    const char *subcommand;

    if (argv == NULL || argc < 3 || argv[2] == NULL) {
        a90_console_printf("usage: wifi uplink-service [status|start|stop|once] <dir> [lifetime_ms poll_ms]\r\n");
        return -EINVAL;
    }
    subcommand = argv[2];

    if (strcmp(subcommand, "status") == 0) {
        if (argc != 4) {
            a90_console_printf("usage: wifi uplink-service status <dir>\r\n");
            return -EINVAL;
        }
        return wifi_uplink_service_status_command(argv[3]);
    }
    if (strcmp(subcommand, "stop") == 0) {
        int rc;

        if (argc != 4) {
            a90_console_printf("usage: wifi uplink-service stop <dir>\r\n");
            return -EINVAL;
        }
        a90_console_printf("[wifi uplink-service stop]\r\n");
        a90_console_printf("version=%s\r\n", A90_WIFI_UPLINK_SERVICE_VERSION);
        a90_console_printf("root=%s\r\n", argv[3]);
        rc = wifi_service_stop(argv[3]);
        a90_console_printf("stop_rc=%d\r\n", rc);
        a90_console_printf("decision=%s\r\n",
                           rc == 0 ? "wifi-uplink-service-stop-pass" : "wifi-uplink-service-stop-failed");
        return rc;
    }
    if (strcmp(subcommand, "once") == 0) {
        long seq = -1;
        int rc;

        if (argc != 4) {
            a90_console_printf("usage: wifi uplink-service once <dir>\r\n");
            return -EINVAL;
        }
        a90_console_printf("[wifi uplink-service once]\r\n");
        a90_console_printf("version=%s\r\n", A90_WIFI_UPLINK_SERVICE_VERSION);
        a90_console_printf("root=%s\r\n", argv[3]);
        rc = wifi_uplink_service_process_once(argv[3], -1, &seq);
        a90_console_printf("request_seq=%ld\r\n", seq);
        a90_console_printf("process_rc=%d\r\n", rc);
        a90_console_printf("response_file=%s/%s\r\n", argv[3], A90_WIFI_SERVICE_RESPONSE_FILE);
        a90_console_printf("decision=%s\r\n",
                           rc == 0 ? "wifi-uplink-service-once-pass" : "wifi-uplink-service-once-failed");
        return rc;
    }
    if (strcmp(subcommand, "start") == 0) {
        int lifetime_ms = A90_WIFI_SERVICE_DEFAULT_LIFETIME_MS;
        int poll_ms = A90_WIFI_SERVICE_DEFAULT_POLL_MS;
        int pid_or_rc;

        if (argc < 4 || argc > 6) {
            a90_console_printf("usage: wifi uplink-service start <dir> [lifetime_ms poll_ms]\r\n");
            return -EINVAL;
        }
        if (argc >= 5 &&
            wifi_parse_delay_ms_max(argv[4], &lifetime_ms, A90_WIFI_SERVICE_MAX_LIFETIME_MS) < 0) {
            a90_console_printf("usage: wifi uplink-service start <dir> [lifetime_ms poll_ms]\r\n");
            return -EINVAL;
        }
        if (argc >= 6 &&
            wifi_parse_delay_ms_max(argv[5], &poll_ms, A90_WIFI_SERVICE_MAX_POLL_MS) < 0) {
            a90_console_printf("usage: wifi uplink-service start <dir> [lifetime_ms poll_ms]\r\n");
            return -EINVAL;
        }
        a90_console_printf("[wifi uplink-service start]\r\n");
        a90_console_printf("version=%s\r\n", A90_WIFI_UPLINK_SERVICE_VERSION);
        a90_console_printf("root=%s\r\n", argv[3]);
        a90_console_printf("lifetime_ms=%d\r\n", lifetime_ms);
        a90_console_printf("poll_ms=%d\r\n", poll_ms);
        a90_console_printf("request_file=%s/%s\r\n", argv[3], A90_WIFI_SERVICE_REQUEST_FILE);
        a90_console_printf("response_file=%s/%s\r\n", argv[3], A90_WIFI_SERVICE_RESPONSE_FILE);
        a90_console_printf("confirm_token=%s\r\n", A90_WIFI_UPLINK_SERVICE_CONFIRM);
        a90_console_printf("credentials=private-config-gated\r\n");
        a90_console_printf("connect=confirm-gated\r\n");
        a90_console_printf("dhcp_routing=config-gated\r\n");
        a90_console_printf("external_ping_execution=0\r\n");
        a90_console_printf("public_tunnel=0\r\n");
        pid_or_rc = wifi_uplink_service_start(argv[3], lifetime_ms, poll_ms);
        a90_console_printf("pid=%d\r\n", pid_or_rc > 0 ? pid_or_rc : -1);
        a90_console_printf("start_rc=%d\r\n", pid_or_rc > 0 ? 0 : pid_or_rc);
        a90_console_printf("decision=%s\r\n",
                           pid_or_rc > 0 ?
                           "wifi-uplink-service-start-pass" :
                           "wifi-uplink-service-start-failed");
        return pid_or_rc > 0 ? 0 : pid_or_rc;
    }

    a90_console_printf("usage: wifi uplink-service [status|start|stop|once] <dir> [lifetime_ms poll_ms]\r\n");
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
    if (argc >= 2 &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "service") == 0) {
        return wifi_service_cmd(argv, argc);
    }
    if (argc >= 2 &&
        argv != NULL &&
        argv[1] != NULL &&
        strcmp(argv[1], "uplink-service") == 0) {
        return wifi_uplink_service_cmd(argv, argc);
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

    a90_console_printf("usage: wifi [status|scan [delay_ms]|events [timeout_ms]|netevents [timeout_ms]|connect [profile]|dhcp [profile]|ping [gateway|internet|all]|cleanup|softap [status|plan|prepare [profile]|iftype-probe [timeout_ms]|start [channel]|transfer-start [channel]|transfer-status|cleanup]|service [status|start|stop|once] <dir>|uplink-service [status|start|stop|once] <dir>|profile [list|status [profile]]|autoconnect [status|enable [profile]|disable|once [profile]]|config [status|prepare [profile]]]\r\n");
    return -EINVAL;
}
