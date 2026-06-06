#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <linux/input.h>
#include <linux/reboot.h>
#include <poll.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <sys/utsname.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>

#define INIT_VERSION "0.8.8"
#define INIT_BUILD "v77"
#define INIT_CREATOR "made by temmie0214"
#define INIT_BANNER "A90 Linux init " INIT_VERSION " (" INIT_BUILD ")"
#define BOOT_SPLASH_SECONDS 2
#define BOOT_HUD_REFRESH_SECONDS 2
#define NATIVE_LOG_PRIMARY "/cache/native-init.log"
#define NATIVE_LOG_FALLBACK "/tmp/native-init.log"
#define NATIVE_LOG_MAX_BYTES (256 * 1024)
#define KMS_LOG_TAIL_MAX_LINES 24
#define KMS_LOG_TAIL_LINE_MAX 96
#define BOOT_TIMELINE_MAX 32
#define CONSOLE_POLL_TIMEOUT_MS 1000
#define CONSOLE_IDLE_REATTACH_MS 60000
#define DISPLAY_TEST_PAGE_COUNT 4
#define AUTO_MENU_STATE_PATH "/tmp/a90-auto-menu-active"
#define AUTO_MENU_REQUEST_PATH "/tmp/a90-auto-menu-request"
#define NETSERVICE_FLAG_PATH "/cache/native-init-netservice"
#define NETSERVICE_LOG_PATH "/cache/native-init-netservice.log"
#define NETSERVICE_USB_HELPER "/cache/bin/a90_usbnet"
#define NETSERVICE_TCPCTL_HELPER "/cache/bin/a90_tcpctl"
#define NETSERVICE_TOYBOX "/cache/bin/toybox"
#define NETSERVICE_IFNAME "ncm0"
#define NETSERVICE_DEVICE_IP "192.168.7.2"
#define NETSERVICE_NETMASK "255.255.255.0"
#define NETSERVICE_TCP_PORT "2325"
#define NETSERVICE_TCP_IDLE_SECONDS "3600"
#define NETSERVICE_TCP_MAX_CLIENTS "0"
#define CMDV1X_MAX_ARGS 32
#define SD_BLOCK_NAME "mmcblk0p1"
#define SD_MOUNT_POINT "/mnt/sdext"
#define SD_FS_TYPE "ext4"
#define SD_WORKSPACE_DIR "/mnt/sdext/a90"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef ECANCELED
#define ECANCELED 125
#endif

static int console_fd = -1;
static long last_console_reattach_ms = 0;
static pid_t adbd_pid = -1;
static pid_t hud_pid = -1;
static pid_t tcpctl_pid = -1;
static bool native_log_ready = false;
static char native_log_path[PATH_MAX] = NATIVE_LOG_FALLBACK;

struct boot_timeline_entry {
    long ms;
    char step[32];
    int code;
    int saved_errno;
    char detail[128];
};

static struct boot_timeline_entry boot_timeline[BOOT_TIMELINE_MAX];
static size_t boot_timeline_count = 0;

enum command_flags {
    CMD_NONE = 0,
    CMD_DISPLAY = 1 << 0,
    CMD_BLOCKING = 1 << 1,
    CMD_DANGEROUS = 1 << 2,
    CMD_BACKGROUND = 1 << 3,
    CMD_NO_DONE = 1 << 4,
};

enum cancel_kind {
    CANCEL_NONE = 0,
    CANCEL_SOFT,
    CANCEL_HARD,
};

struct shell_last_result {
    char command[64];
    int code;
    int saved_errno;
    long duration_ms;
    unsigned int flags;
};

static struct shell_last_result last_result = {
    .command = "<none>",
    .code = 0,
    .saved_errno = 0,
    .duration_ms = 0,
    .flags = CMD_NONE,
};
static unsigned long shell_protocol_seq = 0;

static long monotonic_millis(void);
static int ensure_block_node(const char *path, unsigned int major_num, unsigned int minor_num);
static void reap_tcpctl_child(void);
static bool netservice_enabled_flag(void);
static int cmd_mountsd(char **argv, int argc);

struct kms_display_state {
    int fd;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    uint32_t fb_id[2];
    uint32_t handle[2];
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    size_t map_size;
    void *map[2];
    uint32_t current_buffer;
    struct drm_mode_modeinfo mode;
};

static struct kms_display_state kms_state = {
    .fd = -1,
    .map = { MAP_FAILED, MAP_FAILED },
};

static int ensure_dir(const char *path, mode_t mode) {
    if (mkdir(path, mode) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
}

static int negative_errno_or(int fallback_errno) {
    int saved_errno = errno;

    if (saved_errno == 0) {
        saved_errno = fallback_errno;
    }
    return -saved_errno;
}

static int write_all_checked(int fd, const char *buf, size_t len) {
    while (len > 0) {
        ssize_t written = write(fd, buf, len);
        if (written <= 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        buf += written;
        len -= (size_t)written;
    }
    return 0;
}

static void write_all(int fd, const char *buf, size_t len) {
    (void)write_all_checked(fd, buf, len);
}

static void wf(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        return;
    }
    write_all(fd, value, strlen(value));
    close(fd);
}

static void klogf(const char *fmt, ...) {
    char buf[512];
    va_list ap;
    int fd;
    int len;

    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (len <= 0) {
        return;
    }
    if ((size_t)len >= sizeof(buf)) {
        len = (int)sizeof(buf) - 1;
    }

    fd = open("/dev/kmsg", O_WRONLY);
    if (fd < 0) {
        return;
    }
    write_all(fd, buf, (size_t)len);
    close(fd);
}

static void rotate_native_log_if_needed(const char *path) {
    struct stat st;
    char rotated_path[PATH_MAX];

    if (stat(path, &st) < 0 || st.st_size <= NATIVE_LOG_MAX_BYTES) {
        return;
    }

    if (snprintf(rotated_path, sizeof(rotated_path), "%s.1", path) >= (int)sizeof(rotated_path)) {
        return;
    }

    unlink(rotated_path);
    rename(path, rotated_path);
}

static int select_native_log_path(const char *path) {
    int fd;

    rotate_native_log_if_needed(path);
    fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
    if (fd < 0) {
        return -1;
    }
    close(fd);

    snprintf(native_log_path, sizeof(native_log_path), "%s", path);
    native_log_ready = true;
    return 0;
}

static void native_log_select(const char *preferred_path) {
    if (select_native_log_path(preferred_path) == 0) {
        return;
    }
    if (strcmp(preferred_path, NATIVE_LOG_FALLBACK) != 0) {
        select_native_log_path(NATIVE_LOG_FALLBACK);
    }
}

static const char *native_log_current_path(void) {
    return native_log_ready ? native_log_path : "<none>";
}

static void native_logf(const char *tag, const char *fmt, ...) {
    char message[768];
    char line[1024];
    va_list ap;
    int saved_errno = errno;
    int fd;
    int len;

    if (!native_log_ready) {
        native_log_select(NATIVE_LOG_FALLBACK);
    }
    if (!native_log_ready) {
        errno = saved_errno;
        return;
    }

    va_start(ap, fmt);
    len = vsnprintf(message, sizeof(message), fmt, ap);
    va_end(ap);

    if (len <= 0) {
        errno = saved_errno;
        return;
    }
    if ((size_t)len >= sizeof(message)) {
        message[sizeof(message) - 1] = '\0';
    }

    fd = open(native_log_path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
    if (fd < 0 && strcmp(native_log_path, NATIVE_LOG_FALLBACK) != 0) {
        native_log_select(NATIVE_LOG_FALLBACK);
        fd = open(native_log_path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
    }
    if (fd < 0) {
        errno = saved_errno;
        return;
    }

    len = snprintf(line, sizeof(line), "[%ldms] %s: %s\n",
                   monotonic_millis(), tag, message);
    if (len > 0) {
        if ((size_t)len >= sizeof(line)) {
            len = (int)sizeof(line) - 1;
            line[len] = '\n';
        }
        write_all(fd, line, (size_t)len);
    }
    close(fd);
    errno = saved_errno;
}

static void timeline_record(int code,
                            int saved_errno,
                            const char *step,
                            const char *fmt,
                            ...) {
    struct boot_timeline_entry *entry;
    va_list ap;
    size_t index;

    if (boot_timeline_count < BOOT_TIMELINE_MAX) {
        index = boot_timeline_count++;
    } else {
        index = BOOT_TIMELINE_MAX - 1;
    }

    entry = &boot_timeline[index];
    entry->ms = monotonic_millis();
    entry->code = code;
    entry->saved_errno = saved_errno;
    snprintf(entry->step, sizeof(entry->step), "%s", step);

    va_start(ap, fmt);
    vsnprintf(entry->detail, sizeof(entry->detail), fmt, ap);
    va_end(ap);

    native_logf("timeline", "%s rc=%d errno=%d detail=%s",
                entry->step,
                entry->code,
                entry->saved_errno,
                entry->detail);
}

static void timeline_replay_to_log(const char *reason) {
    size_t index;

    for (index = 0; index < boot_timeline_count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct boot_timeline_entry *entry = &boot_timeline[index];

        native_logf("timeline", "replay=%s %s rc=%d errno=%d ms=%ld detail=%s",
                    reason,
                    entry->step,
                    entry->code,
                    entry->saved_errno,
                    entry->ms,
                    entry->detail);
    }
}

static void timeline_probe_path(const char *step, const char *path) {
    int rc = access(path, F_OK);
    int saved_errno = rc == 0 ? 0 : errno;

    timeline_record(rc == 0 ? 0 : -saved_errno,
                    saved_errno,
                    step,
                    "%s %s",
                    path,
                    rc == 0 ? "ready" : strerror(saved_errno));
}

static void timeline_probe_boot_resources(void) {
    timeline_probe_path("resource-drm", "/sys/class/drm/card0");
    timeline_probe_path("resource-input0", "/sys/class/input/event0");
    timeline_probe_path("resource-input3", "/sys/class/input/event3");
    timeline_probe_path("resource-battery", "/sys/class/power_supply/battery");
    timeline_probe_path("resource-thermal", "/sys/class/thermal");
}

static void timeline_boot_summary(char *out, size_t out_size) {
    const struct boot_timeline_entry *last = NULL;
    const struct boot_timeline_entry *last_error = NULL;
    size_t index;

    if (out_size == 0) {
        return;
    }

    for (index = 0; index < boot_timeline_count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct boot_timeline_entry *entry = &boot_timeline[index];

        last = entry;
        if (entry->code < 0) {
            last_error = entry;
        }
    }

    if (last_error != NULL) {
        snprintf(out, out_size, "BOOT ERR %.10s E%d",
                 last_error->step,
                 last_error->saved_errno);
        return;
    }

    if (last != NULL) {
        snprintf(out, out_size, "BOOT OK %.10s %ldS",
                 last->step,
                 last->ms / 1000);
        return;
    }

    snprintf(out, out_size, "BOOT ?");
}

static void cprintf(const char *fmt, ...) {
    char buf[1024];
    va_list ap;
    int len;

    if (console_fd < 0) {
        return;
    }

    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (len <= 0) {
        return;
    }
    if ((size_t)len >= sizeof(buf)) {
        len = (int)sizeof(buf) - 1;
    }
    write_all(console_fd, buf, (size_t)len);
}

static void mark_step(const char *value) {
    wf("/cache/v5_step", value);
    sync();
}

static int read_text_file(const char *path, char *buf, size_t buf_size) {
    int fd;
    ssize_t rd;

    if (buf_size == 0) {
        errno = EINVAL;
        return -1;
    }

    fd = open(path, O_RDONLY);
    if (fd < 0) {
        return -1;
    }

    rd = read(fd, buf, buf_size - 1);
    close(fd);
    if (rd < 0) {
        return -1;
    }

    buf[rd] = '\0';
    return 0;
}

static void trim_newline(char *buf) {
    size_t len = strlen(buf);

    while (len > 0 && (buf[len - 1] == '\n' || buf[len - 1] == '\r')) {
        buf[len - 1] = '\0';
        --len;
    }
}

static void clear_auto_menu_ipc(void) {
    unlink(AUTO_MENU_STATE_PATH);
    unlink(AUTO_MENU_REQUEST_PATH);
}

static void set_auto_menu_active(bool active) {
    wf(AUTO_MENU_STATE_PATH, active ? "1\n" : "0\n");
}

static void set_auto_menu_state(bool active, bool power_page) {
    if (!active) {
        wf(AUTO_MENU_STATE_PATH, "0\n");
    } else if (power_page) {
        wf(AUTO_MENU_STATE_PATH, "power\n");
    } else {
        wf(AUTO_MENU_STATE_PATH, "1\n");
    }
}

static bool auto_menu_is_active(void) {
    char state[16];

    if (read_text_file(AUTO_MENU_STATE_PATH, state, sizeof(state)) < 0) {
        return false;
    }
    trim_newline(state);
    return strcmp(state, "1") == 0 ||
           strcmp(state, "active") == 0 ||
           strcmp(state, "menu") == 0 ||
           strcmp(state, "power") == 0;
}

static bool auto_menu_power_is_active(void) {
    char state[16];

    if (read_text_file(AUTO_MENU_STATE_PATH, state, sizeof(state)) < 0) {
        return false;
    }
    trim_newline(state);
    return strcmp(state, "power") == 0;
}

static void request_auto_menu_hide(void) {
    wf(AUTO_MENU_REQUEST_PATH, "hide\n");
}

static bool consume_auto_menu_hide_request(void) {
    char request[32];

    if (read_text_file(AUTO_MENU_REQUEST_PATH, request, sizeof(request)) < 0) {
        return false;
    }
    unlink(AUTO_MENU_REQUEST_PATH);
    trim_newline(request);
    return strcmp(request, "hide") == 0 ||
           strcmp(request, "q") == 0 ||
           strcmp(request, "0") == 0;
}

static void flatten_inline_text(char *buf) {
    size_t i;
    bool last_was_space = false;

    for (i = 0; buf[i] != '\0'; ++i) {
        if (buf[i] == '\r' || buf[i] == '\n' || buf[i] == '\t') {
            buf[i] = ' ';
        }

        if (buf[i] == ' ') {
            if (last_was_space) {
                buf[i] = '\a';
            } else {
                last_was_space = true;
            }
        } else {
            last_was_space = false;
        }
    }

    {
        size_t rd = 0;
        size_t wr = 0;

        while (buf[rd] != '\0') {
            if (buf[rd] != '\a') {
                buf[wr++] = buf[rd];
            }
            ++rd;
        }
        buf[wr] = '\0';
    }

    trim_newline(buf);
}

static int read_trimmed_text_file(const char *path, char *buf, size_t buf_size) {
    if (read_text_file(path, buf, buf_size) < 0) {
        return -1;
    }
    trim_newline(buf);
    return 0;
}

static void consume_escape_sequence(void) {
    int index;

    for (index = 0; index < 8; ++index) {
        struct pollfd pfd;
        char ch;

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        pfd.revents = 0;

        if (poll(&pfd, 1, 20) <= 0 || (pfd.revents & POLLIN) == 0) {
            return;
        }

        if (read(STDIN_FILENO, &ch, 1) != 1) {
            return;
        }

        if (index == 0 && ch != '[' && ch != 'O') {
            return;
        }
        if (index > 0 && ch >= 0x40 && ch <= 0x7e) {
            return;
        }
    }
}

static void drain_console_cancel_tail(void) {
    int index;

    for (index = 0; index < 32; ++index) {
        struct pollfd pfd;
        char ch;

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        pfd.revents = 0;

        if (poll(&pfd, 1, 10) <= 0 || (pfd.revents & POLLIN) == 0) {
            return;
        }
        if (read(STDIN_FILENO, &ch, 1) != 1) {
            return;
        }
        if (ch == '\r' || ch == '\n') {
            return;
        }
    }
}

static enum cancel_kind classify_console_cancel_char(char ch) {
    if (ch == 0x03) {
        return CANCEL_HARD;
    }
    if (ch == 'q' || ch == 'Q') {
        drain_console_cancel_tail();
        return CANCEL_SOFT;
    }
    if (ch == 0x1b) {
        consume_escape_sequence();
    }
    return CANCEL_NONE;
}

static enum cancel_kind read_console_cancel_event(void) {
    char ch;
    ssize_t rd = read(STDIN_FILENO, &ch, 1);

    if (rd != 1) {
        return CANCEL_NONE;
    }
    return classify_console_cancel_char(ch);
}

static enum cancel_kind poll_console_cancel(int timeout_ms) {
    struct pollfd pfd;

    pfd.fd = STDIN_FILENO;
    pfd.events = POLLIN;
    pfd.revents = 0;

    if (poll(&pfd, 1, timeout_ms) <= 0 || (pfd.revents & POLLIN) == 0) {
        return CANCEL_NONE;
    }

    return read_console_cancel_event();
}

static int command_cancelled(const char *tag, enum cancel_kind cancel) {
    if (cancel == CANCEL_NONE) {
        return 0;
    }
    if (cancel == CANCEL_HARD) {
        cprintf("%s: cancelled by Ctrl-C\r\n", tag);
        native_logf("cancel", "%s hard Ctrl-C", tag);
    } else {
        cprintf("%s: cancelled by q\r\n", tag);
        native_logf("cancel", "%s soft q", tag);
    }
    return -ECANCELED;
}

static int parse_dev_numbers(const char *dev_info,
                             unsigned int *major_num,
                             unsigned int *minor_num) {
    if (sscanf(dev_info, "%u:%u", major_num, minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int ensure_char_node(const char *path, unsigned int major_num, unsigned int minor_num) {
    if (mknod(path, S_IFCHR | 0600, makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int get_char_device_path(const char *sysfs_dev_path,
                                const char *dev_dir,
                                const char *node_name,
                                char *out,
                                size_t out_size) {
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;

    if (read_trimmed_text_file(sysfs_dev_path, dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }

    if (parse_dev_numbers(dev_info, &major_num, &minor_num) < 0) {
        return -1;
    }

    if (ensure_dir(dev_dir, 0755) < 0) {
        return -1;
    }

    if (snprintf(out, out_size, "%s/%s", dev_dir, node_name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }

    if (ensure_char_node(out, major_num, minor_num) < 0) {
        return -1;
    }

    return 0;
}

static int get_block_device_path(const char *block_name, char *out, size_t out_size) {
    char dev_info_path[PATH_MAX];
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;

    if (snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/block/%s/dev", block_name) >= (int)sizeof(dev_info_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }

    if (read_trimmed_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }

    if (parse_dev_numbers(dev_info, &major_num, &minor_num) < 0) {
        return -1;
    }

    if (ensure_dir("/dev/block", 0755) < 0) {
        return -1;
    }

    if (snprintf(out, out_size, "/dev/block/%s", block_name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }

    if (ensure_block_node(out, major_num, minor_num) < 0) {
        return -1;
    }

    return 0;
}

static int normalize_event_name(const char *arg, char *out, size_t out_size) {
    if (strncmp(arg, "event", 5) == 0) {
        if (snprintf(out, out_size, "%s", arg) >= (int)out_size) {
            errno = ENAMETOOLONG;
            return -1;
        }
        return 0;
    }

    if (snprintf(out, out_size, "event%s", arg) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int get_input_event_path(const char *event_name, char *out, size_t out_size) {
    char dev_info_path[PATH_MAX];

    if (snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }

    return get_char_device_path(dev_info_path, "/dev/input", event_name, out, out_size);
}

static void prepare_input_nodes(void) {
    DIR *dir = opendir("/sys/class/input");
    struct dirent *entry;
    char path[PATH_MAX];

    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strncmp(entry->d_name, "event", 5) != 0) {
            continue;
        }
        get_input_event_path(entry->d_name, path, sizeof(path));
    }

    closedir(dir);
}

static void prepare_drm_nodes(void) {
    DIR *dir = opendir("/sys/class/drm");
    struct dirent *entry;
    char dev_info_path[PATH_MAX];
    char out[PATH_MAX];

    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        const char *name = entry->d_name;

        if (name[0] == '.') {
            continue;
        }

        if (!(((strncmp(name, "card", 4) == 0) && strchr(name, '-') == NULL) ||
              strncmp(name, "renderD", 7) == 0 ||
              strncmp(name, "controlD", 8) == 0)) {
            continue;
        }

        if (snprintf(dev_info_path, sizeof(dev_info_path),
                     "/sys/class/drm/%s/dev", name) >= (int)sizeof(dev_info_path)) {
            continue;
        }

        get_char_device_path(dev_info_path, "/dev/dri", name, out, sizeof(out));
    }

    closedir(dir);
}

static void prepare_graphics_nodes(void) {
    DIR *dir = opendir("/sys/class/graphics");
    struct dirent *entry;
    char dev_info_path[PATH_MAX];
    char out[PATH_MAX];

    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strncmp(entry->d_name, "fb", 2) != 0) {
            continue;
        }

        if (snprintf(dev_info_path, sizeof(dev_info_path),
                     "/sys/class/graphics/%s/dev", entry->d_name) >= (int)sizeof(dev_info_path)) {
            continue;
        }

        get_char_device_path(dev_info_path, "/dev/graphics", entry->d_name, out, sizeof(out));
    }

    closedir(dir);
}

static void prepare_early_display_environment(void) {
    wf("/sys/class/backlight/panel0-backlight/brightness", "200");
    prepare_drm_nodes();
    prepare_graphics_nodes();
    prepare_input_nodes();
}

static int print_input_event_info(const char *event_name) {
    char name_path[PATH_MAX];
    char dev_path[PATH_MAX];
    char name_buf[256];
    char dev_info_path[PATH_MAX];
    char dev_info[64];

    if (snprintf(name_path, sizeof(name_path),
                 "/sys/class/input/%s/device/name", event_name) >= (int)sizeof(name_path) ||
        snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        cprintf("inputinfo: %s: path too long\r\n", event_name);
        return -ENAMETOOLONG;
    }

    if (read_text_file(name_path, name_buf, sizeof(name_buf)) < 0) {
        cprintf("inputinfo: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    trim_newline(name_buf);

    if (read_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        cprintf("inputinfo: %s dev: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    trim_newline(dev_info);

    if (get_input_event_path(event_name, dev_path, sizeof(dev_path)) < 0) {
        cprintf("%s  name=%s  dev=%s  node=<error:%s>\r\n",
                event_name, name_buf, dev_info, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    cprintf("%s  name=%s  dev=%s  node=%s\r\n",
            event_name, name_buf, dev_info, dev_path);
    return 0;
}

static int cmd_inputinfo(char **argv, int argc) {
    if (argc >= 2) {
        char event_name[32];

        if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
            cprintf("inputinfo: invalid event name\r\n");
            return -EINVAL;
        }
        return print_input_event_info(event_name);
    }

    {
        DIR *dir = opendir("/sys/class/input");
        struct dirent *entry;
        int first_error = 0;
        bool printed = false;

        if (dir == NULL) {
            cprintf("inputinfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (strncmp(entry->d_name, "event", 5) == 0) {
                int result = print_input_event_info(entry->d_name);
                if (result == 0) {
                    printed = true;
                } else if (first_error == 0) {
                    first_error = result;
                }
            }
        }

        closedir(dir);
        return printed ? 0 : first_error;
    }
}

static void print_drm_entry_info(const char *entry_name) {
    char base_path[PATH_MAX];
    char path[PATH_MAX];
    char value[1024];
    char node_path[PATH_MAX];
    bool printed_header = false;

    if (snprintf(base_path, sizeof(base_path),
                 "/sys/class/drm/%s", entry_name) >= (int)sizeof(base_path)) {
        cprintf("drminfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (snprintf(path, sizeof(path), "%s/dev", base_path) >= (int)sizeof(path)) {
        cprintf("drminfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        cprintf("%s  dev=%s", entry_name, value);
        printed_header = true;

        if (((strncmp(entry_name, "card", 4) == 0) && strchr(entry_name, '-') == NULL) ||
            strncmp(entry_name, "renderD", 7) == 0 ||
            strncmp(entry_name, "controlD", 8) == 0) {
            if (get_char_device_path(path, "/dev/dri", entry_name,
                                     node_path, sizeof(node_path)) == 0) {
                cprintf("  node=%s", node_path);
            } else {
                cprintf("  node=<error:%s>", strerror(errno));
            }
        }
        cprintf("\r\n");
    }

    if (snprintf(path, sizeof(path), "%s/status", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        cprintf("  status=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/enabled", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        cprintf("  enabled=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/dpms", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        cprintf("  dpms=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/modes", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        flatten_inline_text(value);
        cprintf("  modes=%s\r\n", value);
    }

    if (!printed_header) {
        cprintf("%s\r\n", entry_name);
    }
}

static int cmd_drminfo(char **argv, int argc) {
    if (argc >= 2) {
        print_drm_entry_info(argv[1]);
        return 0;
    }

    {
        DIR *dir = opendir("/sys/class/drm");
        struct dirent *entry;

        if (dir == NULL) {
            cprintf("drminfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (entry->d_name[0] == '.') {
                continue;
            }
            print_drm_entry_info(entry->d_name);
        }

        closedir(dir);
        return 0;
    }
}

static void print_fb_entry_info(const char *entry_name) {
    char base_path[PATH_MAX];
    char path[PATH_MAX];
    char value[1024];
    char node_path[PATH_MAX];
    bool printed_header = false;

    if (snprintf(base_path, sizeof(base_path),
                 "/sys/class/graphics/%s", entry_name) >= (int)sizeof(base_path)) {
        cprintf("fbinfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (snprintf(path, sizeof(path), "%s/dev", base_path) >= (int)sizeof(path)) {
        cprintf("fbinfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        cprintf("%s  dev=%s", entry_name, value);
        printed_header = true;

        if (get_char_device_path(path, "/dev/graphics", entry_name,
                                 node_path, sizeof(node_path)) == 0) {
            cprintf("  node=%s", node_path);
        } else {
            cprintf("  node=<error:%s>", strerror(errno));
        }
        cprintf("\r\n");
    }

    if (snprintf(path, sizeof(path), "%s/name", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        cprintf("  name=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/bits_per_pixel", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        cprintf("  bits_per_pixel=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/virtual_size", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        cprintf("  virtual_size=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/modes", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        flatten_inline_text(value);
        cprintf("  modes=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/blank", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            cprintf("%s\r\n", entry_name);
            printed_header = true;
        }
        cprintf("  blank=%s\r\n", value);
    }

    if (!printed_header) {
        cprintf("%s\r\n", entry_name);
    }
}

static int cmd_fbinfo(char **argv, int argc) {
    if (argc >= 2) {
        print_fb_entry_info(argv[1]);
        return 0;
    }

    {
        DIR *dir = opendir("/sys/class/graphics");
        struct dirent *entry;

        if (dir == NULL) {
            cprintf("fbinfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (strncmp(entry->d_name, "fb", 2) == 0) {
                print_fb_entry_info(entry->d_name);
            }
        }

        closedir(dir);
        return 0;
    }
}

static const char *drm_connection_name(uint32_t status) {
    if (status == 1) {
        return "connected";
    }
    if (status == 2) {
        return "disconnected";
    }
    if (status == 3) {
        return "unknown";
    }
    return "invalid";
}

static int drm_ioctl_retry(int fd, unsigned long request, void *arg) {
    int rc;

    do {
        rc = ioctl(fd, request, arg);
    } while (rc < 0 && errno == EINTR);

    return rc;
}

static int ensure_card0_path(char *out, size_t out_size) {
    return get_char_device_path("/sys/class/drm/card0/dev", "/dev/dri", "card0", out, out_size);
}

static int drm_get_cap_value(int fd, uint64_t capability, uint64_t *value) {
    struct drm_get_cap cap;

    memset(&cap, 0, sizeof(cap));
    cap.capability = capability;
    if (drm_ioctl_retry(fd, DRM_IOCTL_GET_CAP, &cap) < 0) {
        return -1;
    }

    *value = cap.value;
    return 0;
}

static int drm_fetch_resources(int fd,
                               struct drm_mode_card_res *res,
                               uint32_t **crtcs_out,
                               uint32_t **connectors_out,
                               uint32_t **encoders_out) {
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;

    memset(res, 0, sizeof(*res));
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, res) < 0) {
        return -1;
    }

    if (res->count_crtcs > 0) {
        crtcs = calloc(res->count_crtcs, sizeof(*crtcs));
        if (crtcs == NULL) {
            goto oom;
        }
        res->crtc_id_ptr = (uintptr_t)crtcs;
    }

    if (res->count_connectors > 0) {
        connectors = calloc(res->count_connectors, sizeof(*connectors));
        if (connectors == NULL) {
            goto oom;
        }
        res->connector_id_ptr = (uintptr_t)connectors;
    }

    if (res->count_encoders > 0) {
        encoders = calloc(res->count_encoders, sizeof(*encoders));
        if (encoders == NULL) {
            goto oom;
        }
        res->encoder_id_ptr = (uintptr_t)encoders;
    }

    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETRESOURCES, res) < 0) {
        free(crtcs);
        free(connectors);
        free(encoders);
        return -1;
    }

    *crtcs_out = crtcs;
    *connectors_out = connectors;
    *encoders_out = encoders;
    return 0;

oom:
    free(crtcs);
    free(connectors);
    free(encoders);
    errno = ENOMEM;
    return -1;
}

static int drm_fetch_connector(int fd,
                               uint32_t connector_id,
                               struct drm_mode_get_connector *conn,
                               struct drm_mode_modeinfo **modes_out,
                               uint32_t **encoders_out) {
    struct drm_mode_modeinfo *modes = NULL;
    uint32_t *encoders = NULL;
    uint32_t *props = NULL;
    uint64_t *prop_values = NULL;
    struct drm_mode_modeinfo first_mode;

    memset(conn, 0, sizeof(*conn));
    conn->connector_id = connector_id;
    memset(&first_mode, 0, sizeof(first_mode));
    conn->count_modes = 1;
    conn->modes_ptr = (uintptr_t)&first_mode;
    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETCONNECTOR, conn) < 0) {
        return -1;
    }

    if (conn->count_modes > 0) {
        modes = calloc(conn->count_modes, sizeof(*modes));
        if (modes == NULL) {
            goto oom;
        }
        conn->modes_ptr = (uintptr_t)modes;
    }

    if (conn->count_encoders > 0) {
        encoders = calloc(conn->count_encoders, sizeof(*encoders));
        if (encoders == NULL) {
            goto oom;
        }
        conn->encoders_ptr = (uintptr_t)encoders;
    }

    if (conn->count_props > 0) {
        props = calloc(conn->count_props, sizeof(*props));
        prop_values = calloc(conn->count_props, sizeof(*prop_values));
        if (props == NULL || prop_values == NULL) {
            goto oom;
        }
        conn->props_ptr = (uintptr_t)props;
        conn->prop_values_ptr = (uintptr_t)prop_values;
    }

    if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETCONNECTOR, conn) < 0) {
        free(modes);
        free(encoders);
        free(props);
        free(prop_values);
        return -1;
    }

    *modes_out = modes;
    *encoders_out = encoders;
    free(props);
    free(prop_values);
    return 0;

oom:
    free(modes);
    free(encoders);
    free(props);
    free(prop_values);
    errno = ENOMEM;
    return -1;
}

static int drm_pick_crtc_id(const struct drm_mode_get_encoder *encoder,
                            const uint32_t *crtcs,
                            uint32_t count_crtcs,
                            uint32_t *crtc_id_out) {
    uint32_t index;

    if (encoder->crtc_id != 0) {
        *crtc_id_out = encoder->crtc_id;
        return 0;
    }

    for (index = 0; index < count_crtcs; ++index) {
        if ((encoder->possible_crtcs & (1U << index)) != 0) {
            *crtc_id_out = crtcs[index];
            return 0;
        }
    }

    errno = ENODEV;
    return -1;
}

static int drm_find_mode_index(const struct drm_mode_modeinfo *modes, uint32_t count_modes) {
    uint32_t index;

    for (index = 0; index < count_modes; ++index) {
        if ((modes[index].type & DRM_MODE_TYPE_PREFERRED) != 0) {
            return (int)index;
        }
    }

    return (count_modes > 0) ? 0 : -1;
}

static int kms_find_output(int fd,
                           bool verbose,
                           uint32_t *connector_id_out,
                           uint32_t *encoder_id_out,
                           uint32_t *crtc_id_out,
                           struct drm_mode_modeinfo *mode_out) {
    struct drm_mode_card_res res;
    uint32_t *crtcs = NULL;
    uint32_t *connectors = NULL;
    uint32_t *encoders = NULL;
    uint32_t index;
    int rc = -1;

    if (drm_fetch_resources(fd, &res, &crtcs, &connectors, &encoders) < 0) {
        return -1;
    }

    if (verbose) {
        cprintf("kmsprobe: crtcs=%u connectors=%u encoders=%u size=%ux%u..%ux%u\r\n",
                res.count_crtcs, res.count_connectors, res.count_encoders,
                res.min_width, res.min_height, res.max_width, res.max_height);
    }

    for (index = 0; index < res.count_connectors; ++index) {
        struct drm_mode_get_connector conn;
        struct drm_mode_modeinfo *modes = NULL;
        uint32_t *connector_encoders = NULL;
        int mode_index;

        if (drm_fetch_connector(fd, connectors[index], &conn, &modes, &connector_encoders) < 0) {
            if (verbose) {
                cprintf("kmsprobe: connector %u: %s\r\n",
                        connectors[index], strerror(errno));
            }
            continue;
        }

        if (verbose) {
            cprintf("kmsprobe: connector=%u type=%u status=%s encoders=%u modes=%u current_encoder=%u\r\n",
                    conn.connector_id,
                    conn.connector_type,
                    drm_connection_name(conn.connection),
                    conn.count_encoders,
                    conn.count_modes,
                    conn.encoder_id);
        }

        mode_index = drm_find_mode_index(modes, conn.count_modes);
        if (conn.connection == 1 && mode_index >= 0) {
            struct drm_mode_get_encoder encoder;
            uint32_t encoder_id = conn.encoder_id;
            uint32_t crtc_id;

            if (encoder_id == 0 && conn.count_encoders > 0) {
                encoder_id = connector_encoders[0];
            }

            memset(&encoder, 0, sizeof(encoder));
            encoder.encoder_id = encoder_id;

            if (encoder_id == 0 || drm_ioctl_retry(fd, DRM_IOCTL_MODE_GETENCODER, &encoder) < 0) {
                if (verbose) {
                    cprintf("kmsprobe: encoder lookup failed for connector %u: %s\r\n",
                            conn.connector_id, strerror(errno));
                }
                free(modes);
                free(connector_encoders);
                continue;
            }

            if (drm_pick_crtc_id(&encoder, crtcs, res.count_crtcs, &crtc_id) < 0) {
                if (verbose) {
                    cprintf("kmsprobe: no CRTC for encoder %u\r\n", encoder.encoder_id);
                }
                free(modes);
                free(connector_encoders);
                continue;
            }

            *connector_id_out = conn.connector_id;
            *encoder_id_out = encoder.encoder_id;
            *crtc_id_out = crtc_id;
            *mode_out = modes[mode_index];
            rc = 0;

            if (verbose) {
                cprintf("kmsprobe: selected connector=%u encoder=%u crtc=%u mode=%s\r\n",
                        *connector_id_out, *encoder_id_out, *crtc_id_out, mode_out->name);
            }

            free(modes);
            free(connector_encoders);
            break;
        }

        free(modes);
        free(connector_encoders);
    }

    free(crtcs);
    free(connectors);
    free(encoders);

    if (rc < 0 && errno == 0) {
        errno = ENODEV;
    }

    return rc;
}

static int kms_open_card(bool verbose, char *node_path, size_t node_path_size) {
    int fd;

    if (ensure_card0_path(node_path, node_path_size) < 0) {
        return -1;
    }

    fd = open(node_path, O_RDWR);
    if (fd < 0) {
        return -1;
    }
    if (fd >= 0 && fd < STDERR_FILENO + 1) {
        int protected_fd = fcntl(fd, F_DUPFD_CLOEXEC, STDERR_FILENO + 1);
        if (protected_fd < 0) {
            close(fd);
            return -1;
        }
        close(fd);
        fd = protected_fd;
    }

    if (drm_ioctl_retry(fd, DRM_IOCTL_SET_MASTER, NULL) < 0) {
        if (errno != EBUSY && errno != EINVAL) {
            if (verbose) {
                cprintf("kmsprobe: SET_MASTER failed: %s\r\n", strerror(errno));
            }
        }
    }

    return fd;
}

static void *kms_active_map(struct kms_display_state *state) {
    return state->map[state->current_buffer];
}

static uint32_t kms_pack_rgb_for_xbgr8888(uint32_t color) {
    uint8_t red = (color >> 16) & 0xff;
    uint8_t green = (color >> 8) & 0xff;
    uint8_t blue = color & 0xff;

    return ((uint32_t)blue << 16) | ((uint32_t)green << 8) | red;
}

static void kms_fill_color(struct kms_display_state *state, uint32_t color) {
    size_t y;
    uint32_t pixel = kms_pack_rgb_for_xbgr8888(color);
    void *map = kms_active_map(state);

    if (map == NULL || map == MAP_FAILED) {
        return;
    }

    for (y = 0; y < state->height; ++y) {
        uint32_t *row = (uint32_t *)((char *)map + (y * state->stride));
        size_t x;

        for (x = 0; x < state->width; ++x) {
            row[x] = pixel;
        }
    }
}

static void kms_fill_rect(struct kms_display_state *state,
                          uint32_t x,
                          uint32_t y,
                          uint32_t width,
                          uint32_t height,
                          uint32_t color) {
    uint32_t pixel = kms_pack_rgb_for_xbgr8888(color);
    uint32_t y_end;
    void *map = kms_active_map(state);

    if (map == NULL || map == MAP_FAILED || x >= state->width || y >= state->height) {
        return;
    }

    if (x + width > state->width) {
        width = state->width - x;
    }
    if (y + height > state->height) {
        height = state->height - y;
    }

    y_end = y + height;
    while (y < y_end) {
        uint32_t *row = (uint32_t *)((char *)map + (y * state->stride));
        uint32_t x_end = x + width;
        uint32_t cursor = x;

        while (cursor < x_end) {
            row[cursor++] = pixel;
        }
        ++y;
    }
}

static void kms_draw_boot_frame(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
    uint32_t header_h = height / 8;
    uint32_t footer_h = height / 7;
    uint32_t gap = width / 40;
    uint32_t footer_w = (width - (gap * 4)) / 3;
    uint32_t footer_y = height - footer_h - gap;

    kms_fill_color(state, 0x080808);
    kms_fill_rect(state, 0, 0, width, header_h, 0x2a2a2a);
    kms_fill_rect(state, gap, gap, width / 5, gap / 2 + 6, 0x0090ca);
    kms_fill_rect(state, gap, footer_y, footer_w, footer_h, 0x202020);
    kms_fill_rect(state, gap * 2 + footer_w, footer_y, footer_w, footer_h, 0x0090ca);
    kms_fill_rect(state, gap * 3 + footer_w * 2, footer_y, footer_w, footer_h, 0x202020);
}

static void __attribute__((unused)) kms_draw_visibility_probe(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
    uint32_t border = width / 12;
    uint32_t mid_w = width / 3;
    uint32_t mid_h = height / 10;
    uint32_t center_x = (width - mid_w) / 2;
    uint32_t center_y = (height - mid_h) / 2;

    kms_fill_color(state, 0x000000);
    kms_fill_rect(state, 0, 0, width, border, 0xffffff);
    kms_fill_rect(state, 0, height - border, width, border, 0xffffff);
    kms_fill_rect(state, 0, 0, border, height, 0xffffff);
    kms_fill_rect(state, width - border, 0, border, height, 0xffffff);
    kms_fill_rect(state, center_x, center_y, mid_w, mid_h, 0xffffff);
    kms_fill_rect(state, width / 12, height / 6, width / 5, border, 0xff0000);
    kms_fill_rect(state, width / 12, height / 6 + border * 2, width / 5, border, 0x00ff00);
    kms_fill_rect(state, width / 12, height / 6 + border * 4, width / 5, border, 0x0000ff);
}

static void kms_draw_block_t(struct kms_display_state *state,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t stem_x = x + ((width - stroke) / 2);
    kms_fill_rect(state, x, y, width, stroke, color);
    kms_fill_rect(state, stem_x, y, stroke, height, color);
}

static void kms_draw_block_e(struct kms_display_state *state,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t mid_y = y + ((height - stroke) / 2);
    kms_fill_rect(state, x, y, stroke, height, color);
    kms_fill_rect(state, x, y, width, stroke, color);
    kms_fill_rect(state, x, mid_y, width - stroke / 2, stroke, color);
    kms_fill_rect(state, x, y + height - stroke, width, stroke, color);
}

static void kms_draw_block_s(struct kms_display_state *state,
                             uint32_t x,
                             uint32_t y,
                             uint32_t stroke,
                             uint32_t width,
                             uint32_t height,
                             uint32_t color) {
    uint32_t mid_y = y + ((height - stroke) / 2);
    kms_fill_rect(state, x, y, width, stroke, color);
    kms_fill_rect(state, x, y, stroke, mid_y - y + stroke, color);
    kms_fill_rect(state, x, mid_y, width, stroke, color);
    kms_fill_rect(state, x + width - stroke, mid_y, stroke, y + height - mid_y, color);
    kms_fill_rect(state, x, y + height - stroke, width, stroke, color);
}

static void kms_draw_giant_test_probe(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
    uint32_t border = width / 20;
    uint32_t stroke = width / 22;
    uint32_t letter_h = (height * 11) / 32;
    uint32_t t_w = stroke * 5;
    uint32_t e_w = stroke * 4;
    uint32_t s_w = stroke * 4;
    uint32_t gap = stroke;
    uint32_t start_x;
    uint32_t start_y;
    uint32_t label_h = stroke * 2;

    if (stroke < 18) {
        stroke = 18;
    }
    if (letter_h < stroke * 7) {
        letter_h = stroke * 7;
    }
    start_x = (width - (t_w + e_w + s_w + t_w + gap * 3)) / 2;
    start_y = (height - letter_h) / 2;

    kms_fill_color(state, 0x000000);
    kms_fill_rect(state, 0, 0, width, border, 0xffffff);
    kms_fill_rect(state, 0, height - border, width, border, 0xffffff);
    kms_fill_rect(state, 0, 0, border, height, 0xffffff);
    kms_fill_rect(state, width - border, 0, border, height, 0xffffff);
    kms_fill_rect(state, border * 2, border * 2, width - border * 4, label_h, 0x00a0ff);
    kms_fill_rect(state, border * 2, height - border * 3, width - border * 4, stroke, 0xffa000);

    kms_draw_block_t(state, start_x, start_y, stroke, t_w, letter_h, 0xffffff);
    start_x += t_w + gap;
    kms_draw_block_e(state, start_x, start_y, stroke, e_w, letter_h, 0xffffff);
    start_x += e_w + gap;
    kms_draw_block_s(state, start_x, start_y, stroke, s_w, letter_h, 0xffffff);
    start_x += s_w + gap;
    kms_draw_block_t(state, start_x, start_y, stroke, t_w, letter_h, 0xffffff);
}

static const uint8_t *font5x7_rows(char ch) {
    static const uint8_t blank[7] = { 0, 0, 0, 0, 0, 0, 0 };

    if (ch >= 'a' && ch <= 'z') {
        ch = (char)(ch - 'a' + 'A');
    }

    switch (ch) {
    case 'A': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11 }; return g; }
    case 'B': { static const uint8_t g[7] = { 0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E }; return g; }
    case 'C': { static const uint8_t g[7] = { 0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E }; return g; }
    case 'D': { static const uint8_t g[7] = { 0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C }; return g; }
    case 'E': { static const uint8_t g[7] = { 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F }; return g; }
    case 'F': { static const uint8_t g[7] = { 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10 }; return g; }
    case 'G': { static const uint8_t g[7] = { 0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F }; return g; }
    case 'H': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11 }; return g; }
    case 'I': { static const uint8_t g[7] = { 0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E }; return g; }
    case 'J': { static const uint8_t g[7] = { 0x01, 0x01, 0x01, 0x01, 0x11, 0x11, 0x0E }; return g; }
    case 'K': { static const uint8_t g[7] = { 0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11 }; return g; }
    case 'L': { static const uint8_t g[7] = { 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F }; return g; }
    case 'M': { static const uint8_t g[7] = { 0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11 }; return g; }
    case 'N': { static const uint8_t g[7] = { 0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11 }; return g; }
    case 'O': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E }; return g; }
    case 'P': { static const uint8_t g[7] = { 0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10 }; return g; }
    case 'Q': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D }; return g; }
    case 'R': { static const uint8_t g[7] = { 0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11 }; return g; }
    case 'S': { static const uint8_t g[7] = { 0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E }; return g; }
    case 'T': { static const uint8_t g[7] = { 0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04 }; return g; }
    case 'U': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E }; return g; }
    case 'V': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04 }; return g; }
    case 'W': { static const uint8_t g[7] = { 0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A }; return g; }
    case 'X': { static const uint8_t g[7] = { 0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11 }; return g; }
    case 'Y': { static const uint8_t g[7] = { 0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04 }; return g; }
    case 'Z': { static const uint8_t g[7] = { 0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F }; return g; }
    case '0': { static const uint8_t g[7] = { 0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E }; return g; }
    case '1': { static const uint8_t g[7] = { 0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E }; return g; }
    case '2': { static const uint8_t g[7] = { 0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F }; return g; }
    case '3': { static const uint8_t g[7] = { 0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E }; return g; }
    case '4': { static const uint8_t g[7] = { 0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02 }; return g; }
    case '5': { static const uint8_t g[7] = { 0x1F, 0x10, 0x10, 0x1E, 0x01, 0x01, 0x1E }; return g; }
    case '6': { static const uint8_t g[7] = { 0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E }; return g; }
    case '7': { static const uint8_t g[7] = { 0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08 }; return g; }
    case '8': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E }; return g; }
    case '9': { static const uint8_t g[7] = { 0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C }; return g; }
    case '%': { static const uint8_t g[7] = { 0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13 }; return g; }
    case '.': { static const uint8_t g[7] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x06 }; return g; }
    case '/': { static const uint8_t g[7] = { 0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10 }; return g; }
    case ':': { static const uint8_t g[7] = { 0x00, 0x06, 0x06, 0x00, 0x06, 0x06, 0x00 }; return g; }
    case '+': { static const uint8_t g[7] = { 0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00 }; return g; }
    case '-': { static const uint8_t g[7] = { 0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00 }; return g; }
    case ' ': return blank;
    default: return blank;
    }
}

static void kms_draw_char(struct kms_display_state *state,
                          uint32_t x,
                          uint32_t y,
                          char ch,
                          uint32_t color,
                          uint32_t scale) {
    const uint8_t *rows = font5x7_rows(ch);
    uint32_t row;

    for (row = 0; row < 7; ++row) {
        uint32_t col;
        for (col = 0; col < 5; ++col) {
            if ((rows[row] & (1U << (4 - col))) != 0) {
                kms_fill_rect(state,
                              x + (col * scale),
                              y + (row * scale),
                              scale,
                              scale,
                              color);
            }
        }
    }
}

static void kms_draw_text(struct kms_display_state *state,
                          uint32_t x,
                          uint32_t y,
                          const char *text,
                          uint32_t color,
                          uint32_t scale) {
    while (*text != '\0') {
        kms_draw_char(state, x, y, *text, color, scale);
        x += scale * 6;
        ++text;
    }
}

static int read_long_value(const char *path, long *value_out) {
    char buf[128];

    if (read_trimmed_text_file(path, buf, sizeof(buf)) < 0) {
        return -1;
    }

    *value_out = strtol(buf, NULL, 10);
    return 0;
}

static int read_first_token(const char *path, char *out, size_t out_size) {
    char buf[256];
    size_t len = 0;

    if (read_trimmed_text_file(path, buf, sizeof(buf)) < 0) {
        return -1;
    }

    while (buf[len] != '\0' && buf[len] != ' ' && buf[len] != '\t' && len + 1 < out_size) {
        out[len] = buf[len];
        ++len;
    }
    out[len] = '\0';
    return 0;
}

static int read_meminfo_kb(const char *label, long *value_out) {
    FILE *fp;
    char line[256];
    size_t label_len = strlen(label);

    fp = fopen("/proc/meminfo", "r");
    if (fp == NULL) {
        return -1;
    }

    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strncmp(line, label, label_len) == 0) {
            char *cursor = line + label_len;
            while (*cursor == ' ' || *cursor == '\t' || *cursor == ':') {
                ++cursor;
            }
            *value_out = strtol(cursor, NULL, 10);
            fclose(fp);
            return 0;
        }
    }

    fclose(fp);
    errno = ENOENT;
    return -1;
}

static int read_cpu_usage_percent(long *percent_out) {
    static bool have_previous = false;
    static unsigned long long previous_total = 0;
    static unsigned long long previous_idle = 0;
    FILE *fp;
    char line[256];
    unsigned long long user = 0;
    unsigned long long nice = 0;
    unsigned long long system = 0;
    unsigned long long idle = 0;
    unsigned long long iowait = 0;
    unsigned long long irq = 0;
    unsigned long long softirq = 0;
    unsigned long long steal = 0;
    unsigned long long idle_all;
    unsigned long long non_idle;
    unsigned long long total;
    unsigned long long total_delta;
    unsigned long long idle_delta;
    unsigned long long busy_delta;
    long percent;

    fp = fopen("/proc/stat", "r");
    if (fp == NULL) {
        return -1;
    }

    if (fgets(line, sizeof(line), fp) == NULL) {
        fclose(fp);
        return -1;
    }
    fclose(fp);

    if (sscanf(line, "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
               &user,
               &nice,
               &system,
               &idle,
               &iowait,
               &irq,
               &softirq,
               &steal) < 4) {
        return -1;
    }

    idle_all = idle + iowait;
    non_idle = user + nice + system + irq + softirq + steal;
    total = idle_all + non_idle;

    if (!have_previous || total <= previous_total) {
        previous_total = total;
        previous_idle = idle_all;
        have_previous = true;
        return -1;
    }

    total_delta = total - previous_total;
    idle_delta = idle_all - previous_idle;
    previous_total = total;
    previous_idle = idle_all;

    if (total_delta == 0 || idle_delta > total_delta) {
        return -1;
    }

    busy_delta = total_delta - idle_delta;
    percent = (long)((busy_delta * 100ULL + total_delta / 2ULL) / total_delta);
    if (percent < 0) {
        percent = 0;
    } else if (percent > 100) {
        percent = 100;
    }

    *percent_out = percent;
    return 0;
}

static int read_gpu_busy_percent(long *percent_out) {
    char buf[64];
    long percent;

    if (read_trimmed_text_file("/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage",
                               buf,
                               sizeof(buf)) < 0) {
        return -1;
    }

    percent = strtol(buf, NULL, 10);
    if (percent < 0) {
        percent = 0;
    } else if (percent > 100) {
        percent = 100;
    }

    *percent_out = percent;
    return 0;
}

static int read_average_thermal_temp(const char *prefix_a,
                                     const char *prefix_b,
                                     long *temp_out) {
    DIR *dir;
    struct dirent *entry;
    long total = 0;
    long count = 0;

    dir = opendir("/sys/class/thermal");
    if (dir == NULL) {
        return -1;
    }

    while ((entry = readdir(dir)) != NULL) {
        char type_path[PATH_MAX];
        char temp_path[PATH_MAX];
        char type[128];
        long temp_value;

        if (strncmp(entry->d_name, "thermal_zone", 12) != 0) {
            continue;
        }

        if (snprintf(type_path, sizeof(type_path),
                     "/sys/class/thermal/%s/type", entry->d_name) >= (int)sizeof(type_path) ||
            snprintf(temp_path, sizeof(temp_path),
                     "/sys/class/thermal/%s/temp", entry->d_name) >= (int)sizeof(temp_path)) {
            continue;
        }

        if (read_trimmed_text_file(type_path, type, sizeof(type)) < 0 ||
            read_long_value(temp_path, &temp_value) < 0) {
            continue;
        }

        if (strncmp(type, prefix_a, strlen(prefix_a)) == 0 ||
            (prefix_b != NULL && strncmp(type, prefix_b, strlen(prefix_b)) == 0)) {
            total += temp_value;
            ++count;
        }
    }

    closedir(dir);

    if (count == 0) {
        errno = ENOENT;
        return -1;
    }

    *temp_out = total / count;
    return 0;
}

static void format_temp_tenths(char *out, size_t out_size, long milli_c) {
    long tenths = milli_c / 100;
    long whole = tenths / 10;
    long frac = tenths % 10;

    if (frac < 0) {
        frac = -frac;
    }

    snprintf(out, out_size, "%ld.%ldC", whole, frac);
}

struct status_snapshot {
    char battery_status[64];
    char battery_pct[32];
    char battery_temp[32];
    char battery_voltage[32];
    char cpu_temp[32];
    char cpu_usage[16];
    char gpu_temp[32];
    char gpu_usage[16];
    char memory[64];
    char loadavg[32];
    char uptime[32];
    char power_now[32];
    char power_avg[32];
};

static void format_milliwatts_as_watts(char *out, size_t out_size, long milliwatts) {
    long tenths = milliwatts / 100;
    long whole = tenths / 10;
    long frac = tenths % 10;

    if (frac < 0) {
        frac = -frac;
    }

    snprintf(out, out_size, "%ld.%ldW", whole, frac);
}

static void read_status_snapshot(struct status_snapshot *snapshot) {
    long value;
    long mem_total_kb;
    long mem_avail_kb;

    strcpy(snapshot->battery_status, "?");
    strcpy(snapshot->battery_pct, "?");
    strcpy(snapshot->battery_temp, "?");
    strcpy(snapshot->battery_voltage, "?");
    strcpy(snapshot->cpu_temp, "?");
    strcpy(snapshot->cpu_usage, "?");
    strcpy(snapshot->gpu_temp, "?");
    strcpy(snapshot->gpu_usage, "?");
    strcpy(snapshot->memory, "?");
    strcpy(snapshot->loadavg, "?");
    strcpy(snapshot->uptime, "?");
    strcpy(snapshot->power_now, "?");
    strcpy(snapshot->power_avg, "?");

    if (read_long_value("/sys/class/power_supply/battery/capacity", &value) == 0) {
        snprintf(snapshot->battery_pct, sizeof(snapshot->battery_pct), "%ld%%", value);
    }
    if (read_trimmed_text_file("/sys/class/power_supply/battery/status",
                               snapshot->battery_status,
                               sizeof(snapshot->battery_status)) < 0) {
        strcpy(snapshot->battery_status, "?");
    }
    if (read_long_value("/sys/class/power_supply/battery/temp", &value) == 0) {
        format_temp_tenths(snapshot->battery_temp, sizeof(snapshot->battery_temp), value * 100);
    }
    if (read_long_value("/sys/class/power_supply/battery/voltage_now", &value) == 0) {
        snprintf(snapshot->battery_voltage, sizeof(snapshot->battery_voltage), "%ldmV", value / 1000);
    }
    if (read_long_value("/sys/class/power_supply/battery/power_now", &value) == 0) {
        format_milliwatts_as_watts(snapshot->power_now, sizeof(snapshot->power_now), value);
    }
    if (read_long_value("/sys/class/power_supply/battery/power_avg", &value) == 0) {
        format_milliwatts_as_watts(snapshot->power_avg, sizeof(snapshot->power_avg), value);
    }
    if (read_average_thermal_temp("cpu-", "cpuss", &value) == 0) {
        format_temp_tenths(snapshot->cpu_temp, sizeof(snapshot->cpu_temp), value);
    }
    if (read_cpu_usage_percent(&value) == 0) {
        snprintf(snapshot->cpu_usage, sizeof(snapshot->cpu_usage), "%ld%%", value);
    }
    if (read_average_thermal_temp("gpuss", NULL, &value) == 0) {
        format_temp_tenths(snapshot->gpu_temp, sizeof(snapshot->gpu_temp), value);
    }
    if (read_gpu_busy_percent(&value) == 0) {
        snprintf(snapshot->gpu_usage, sizeof(snapshot->gpu_usage), "%ld%%", value);
    }
    if (read_meminfo_kb("MemTotal", &mem_total_kb) == 0 &&
        read_meminfo_kb("MemAvailable", &mem_avail_kb) == 0) {
        snprintf(snapshot->memory, sizeof(snapshot->memory), "%ld/%ldMB",
                 (mem_total_kb - mem_avail_kb) / 1024,
                 mem_total_kb / 1024);
    }
    read_first_token("/proc/loadavg", snapshot->loadavg, sizeof(snapshot->loadavg));
    read_first_token("/proc/uptime", snapshot->uptime, sizeof(snapshot->uptime));
}

static void kms_draw_status_overlay(struct kms_display_state *state,
                                    unsigned int refresh_sec,
                                    unsigned int sequence) {
    struct status_snapshot snapshot;
    char boot_summary[64];
    char bat_tag[8];
    char footer[32];
    uint32_t scale = 5;
    uint32_t x = state->width / 24;
    uint32_t line_h = scale * 10;
    uint32_t card_h = line_h + scale * 4;
    uint32_t card_w = state->width - (x * 2);
    uint32_t footer_y = state->height - (line_h * 4);
    uint32_t footer_scale = scale;
    uint32_t footer_text_y = footer_y;
    uint32_t char_w = scale * 6;
    uint32_t glyph_h = scale * 7;
    uint32_t y = state->height / 16;
    uint32_t slot = line_h + scale * 3;
    uint32_t bat_color;
    uint32_t boot_color;
    uint32_t off;
    long bat_pct_val;

    (void)refresh_sec;
    (void)sequence;

    if (y > glyph_h + glyph_h / 2 + scale * 2)
        y -= glyph_h + glyph_h / 2;

    read_status_snapshot(&snapshot);
    timeline_boot_summary(boot_summary, sizeof(boot_summary));

    bat_tag[0] = '\0';
    if (strncmp(snapshot.battery_status, "Charging", 8) == 0)
        strncpy(bat_tag, "CHG", sizeof(bat_tag) - 1);
    else if (strncmp(snapshot.battery_status, "Full", 4) == 0)
        strncpy(bat_tag, "FUL", sizeof(bat_tag) - 1);
    else if (strncmp(snapshot.battery_status, "Discharging", 11) == 0)
        strncpy(bat_tag, "DSC", sizeof(bat_tag) - 1);

    bat_pct_val = atol(snapshot.battery_pct);
    if (bat_pct_val <= 20)
        bat_color = 0xff4444;
    else if (bat_pct_val <= 50)
        bat_color = 0xffcc33;
    else
        bat_color = 0x88ee88;

    boot_color = (strncmp(boot_summary, "BOOT OK", 7) == 0) ? 0x88ee88 : 0xff6666;

    snprintf(footer, sizeof(footer), "A90 %s %s UP %.8s",
             INIT_VERSION,
             INIT_BUILD,
             snapshot.uptime);
    while (footer_scale > 1 &&
           x + (uint32_t)strlen(footer) * footer_scale * 6 > state->width - x)
        --footer_scale;
    if (footer_scale < scale)
        footer_text_y += ((scale - footer_scale) * 7) / 2;

    /* 4 card backgrounds */
    kms_fill_rect(state, x - scale, y + slot * 0 - scale, card_w, card_h, 0x202020);
    kms_fill_rect(state, x - scale, y + slot * 1 - scale, card_w, card_h, 0x202020);
    kms_fill_rect(state, x - scale, y + slot * 2 - scale, card_w, card_h, 0x202020);
    kms_fill_rect(state, x - scale, y + slot * 3 - scale, card_w, card_h, 0x202020);

    /* Row 0: "A90 INIT "(gray) + boot_summary(colored) */
    kms_draw_text(state, x, y + slot * 0, "A90 INIT ", 0x909090, scale);
    kms_draw_text(state, x + 9 * char_w, y + slot * 0, boot_summary, boot_color, scale);

    /* Row 1: "BAT "(gray) pct(colored) tag(colored) " PWR "(gray) now(white) " AVG "(gray) avg(white) */
    off = 0;
    kms_draw_text(state, x + off * char_w, y + slot * 1, "BAT ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 1, snapshot.battery_pct, bat_color, scale);
    off += (uint32_t)strlen(snapshot.battery_pct) + 1;
    if (bat_tag[0] != '\0') {
        kms_draw_text(state, x + off * char_w, y + slot * 1, bat_tag, bat_color, scale);
        off += 4;
    }
    kms_draw_text(state, x + off * char_w, y + slot * 1, "PWR ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 1, snapshot.power_now, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.power_now) + 1;
    kms_draw_text(state, x + off * char_w, y + slot * 1, "AVG ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 1, snapshot.power_avg, 0xffffff, scale);

    /* Row 2: "CPU "(gray) cpu_temp/usage(white) " GPU "(gray) gpu_temp/usage(white) */
    off = 0;
    kms_draw_text(state, x + off * char_w, y + slot * 2, "CPU ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 2, snapshot.cpu_temp, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.cpu_temp) + 1;
    kms_draw_text(state, x + off * char_w, y + slot * 2, snapshot.cpu_usage, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.cpu_usage) + 1;
    kms_draw_text(state, x + off * char_w, y + slot * 2, "GPU ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 2, snapshot.gpu_temp, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.gpu_temp) + 1;
    kms_draw_text(state, x + off * char_w, y + slot * 2, snapshot.gpu_usage, 0xffffff, scale);

    /* Row 3: "MEM "(gray) memory(white) " LOAD "(gray) loadavg(white) */
    off = 0;
    kms_draw_text(state, x + off * char_w, y + slot * 3, "MEM ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 3, snapshot.memory, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.memory) + 1;
    kms_draw_text(state, x + off * char_w, y + slot * 3, "LOAD ", 0x909090, scale); off += 5;
    kms_draw_text(state, x + off * char_w, y + slot * 3, snapshot.loadavg, 0xffffff, scale);

    kms_draw_text(state, x, footer_text_y, footer, 0xbbbbbb, footer_scale);
}

static int kms_begin_frame(uint32_t color) {
    struct drm_mode_create_dumb create;
    struct drm_mode_fb_cmd2 addfb2;
    struct drm_mode_map_dumb map_dumb;
    char node_path[PATH_MAX];
    int fd;
    uint64_t dumb_cap = 0;
    uint64_t preferred_depth = 0;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    struct drm_mode_modeinfo mode;
    void *map;
    uint32_t next_buffer;

    if (kms_state.fd >= 0 &&
        kms_state.map[0] != MAP_FAILED &&
        kms_state.map[1] != MAP_FAILED) {
        next_buffer = 1U - kms_state.current_buffer;
        kms_state.current_buffer = next_buffer;
        kms_fill_color(&kms_state, color);
        return 0;
    }

    fd = kms_open_card(false, node_path, sizeof(node_path));
    if (fd < 0) {
        cprintf("kmssolid: open card0: %s\r\n", strerror(errno));
        return -1;
    }

    if (drm_get_cap_value(fd, DRM_CAP_DUMB_BUFFER, &dumb_cap) < 0 || dumb_cap == 0) {
        cprintf("kmssolid: DRM_CAP_DUMB_BUFFER unavailable\r\n");
        close(fd);
        return -1;
    }

    if (drm_get_cap_value(fd, DRM_CAP_DUMB_PREFERRED_DEPTH, &preferred_depth) < 0) {
        preferred_depth = 24;
    }

    if (kms_find_output(fd, false, &connector_id, &encoder_id, &crtc_id, &mode) < 0) {
        cprintf("kmssolid: no connected output: %s\r\n", strerror(errno));
        close(fd);
        return -1;
    }

    memset(&create, 0, sizeof(create));
    create.width = mode.hdisplay;
    create.height = mode.vdisplay;
    create.bpp = 32;

    for (next_buffer = 0; next_buffer < 2; ++next_buffer) {
        memset(&create, 0, sizeof(create));
        create.width = mode.hdisplay;
        create.height = mode.vdisplay;
        create.bpp = 32;

        if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_CREATE_DUMB, &create) < 0) {
            cprintf("kmssolid: CREATE_DUMB[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        memset(&addfb2, 0, sizeof(addfb2));
        addfb2.width = create.width;
        addfb2.height = create.height;
        addfb2.pixel_format = DRM_FORMAT_XBGR8888;
        addfb2.handles[0] = create.handle;
        addfb2.pitches[0] = create.pitch;
        addfb2.offsets[0] = 0;

        if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_ADDFB2, &addfb2) < 0) {
            cprintf("kmssolid: ADDFB2[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        memset(&map_dumb, 0, sizeof(map_dumb));
        map_dumb.handle = create.handle;
        if (drm_ioctl_retry(fd, DRM_IOCTL_MODE_MAP_DUMB, &map_dumb) < 0) {
            cprintf("kmssolid: MAP_DUMB[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        map = mmap(NULL, create.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, (off_t)map_dumb.offset);
        if (map == MAP_FAILED) {
            cprintf("kmssolid: mmap[%u] failed: %s\r\n",
                    next_buffer, strerror(errno));
            close(fd);
            return -1;
        }

        kms_state.handle[next_buffer] = create.handle;
        kms_state.fb_id[next_buffer] = addfb2.fb_id;
        kms_state.map[next_buffer] = map;
        kms_state.stride = create.pitch;
        kms_state.map_size = create.size;
    }

    kms_state.fd = fd;
    kms_state.connector_id = connector_id;
    kms_state.encoder_id = encoder_id;
    kms_state.crtc_id = crtc_id;
    kms_state.width = create.width;
    kms_state.height = create.height;
    kms_state.current_buffer = 0;
    kms_state.mode = mode;

    kms_fill_color(&kms_state, color);
    cprintf("kms: prepared %s %ux%u connector=%u crtc=%u\r\n",
            node_path, kms_state.width, kms_state.height,
            kms_state.connector_id, kms_state.crtc_id);
    return 0;
}

static int kms_present_frame_verbose(const char *label, bool verbose) {
    struct drm_mode_crtc setcrtc;
    uint32_t connector_list[1];

    if (kms_state.fd < 0 ||
        kms_state.map[kms_state.current_buffer] == MAP_FAILED) {
        errno = ENODEV;
        return -1;
    }

    connector_list[0] = kms_state.connector_id;
    memset(&setcrtc, 0, sizeof(setcrtc));
    setcrtc.crtc_id = kms_state.crtc_id;
    setcrtc.fb_id = kms_state.fb_id[kms_state.current_buffer];
    setcrtc.set_connectors_ptr = (uintptr_t)connector_list;
    setcrtc.count_connectors = 1;
    setcrtc.mode = kms_state.mode;
    setcrtc.mode_valid = 1;

    if (drm_ioctl_retry(kms_state.fd, DRM_IOCTL_MODE_SETCRTC, &setcrtc) < 0) {
        cprintf("%s: SETCRTC failed: %s\r\n", label, strerror(errno));
        return -1;
    }

    if (verbose) {
        cprintf("%s: presented framebuffer %ux%u on crtc=%u\r\n",
                label, kms_state.width, kms_state.height, kms_state.crtc_id);
    }
    return 0;
}

static int kms_present_frame(const char *label) {
    return kms_present_frame_verbose(label, true);
}

static bool parse_color_arg(const char *arg, uint32_t *color_out) {
    unsigned int value;

    if (strcmp(arg, "black") == 0) {
        *color_out = 0x000000;
        return true;
    }
    if (strcmp(arg, "white") == 0) {
        *color_out = 0xffffff;
        return true;
    }
    if (strcmp(arg, "red") == 0) {
        *color_out = 0xff0000;
        return true;
    }
    if (strcmp(arg, "green") == 0) {
        *color_out = 0x00ff00;
        return true;
    }
    if (strcmp(arg, "blue") == 0) {
        *color_out = 0x0000ff;
        return true;
    }
    if (strcmp(arg, "gray") == 0 || strcmp(arg, "grey") == 0) {
        *color_out = 0x808080;
        return true;
    }
    if (sscanf(arg, "%x", &value) == 1) {
        *color_out = value & 0xffffffU;
        return true;
    }
    return false;
}

static int cmd_kmsprobe(void) {
    char node_path[PATH_MAX];
    int fd;
    int result = 0;
    uint64_t dumb_cap = 0;
    uint64_t preferred_depth = 0;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    struct drm_mode_modeinfo mode;

    fd = kms_open_card(true, node_path, sizeof(node_path));
    if (fd < 0) {
        cprintf("kmsprobe: open card0: %s\r\n", strerror(errno));
        return negative_errno_or(ENODEV);
    }

    cprintf("kmsprobe: node=%s\r\n", node_path);
    if (drm_get_cap_value(fd, DRM_CAP_DUMB_BUFFER, &dumb_cap) == 0) {
        cprintf("kmsprobe: DRM_CAP_DUMB_BUFFER=%llu\r\n",
                (unsigned long long)dumb_cap);
    }
    if (drm_get_cap_value(fd, DRM_CAP_DUMB_PREFERRED_DEPTH, &preferred_depth) == 0) {
        cprintf("kmsprobe: DRM_CAP_DUMB_PREFERRED_DEPTH=%llu\r\n",
                (unsigned long long)preferred_depth);
    }

    if (kms_find_output(fd, true, &connector_id, &encoder_id, &crtc_id, &mode) == 0) {
        cprintf("kmsprobe: chosen connector=%u encoder=%u crtc=%u mode=%s %ux%u@%u\r\n",
                connector_id, encoder_id, crtc_id,
                mode.name, mode.hdisplay, mode.vdisplay, mode.vrefresh);
    } else {
        cprintf("kmsprobe: no usable display path: %s\r\n", strerror(errno));
        result = negative_errno_or(ENODEV);
    }

    close(fd);
    return result;
}

static int cmd_kmssolid(char **argv, int argc) {
    uint32_t color = 0x000000;

    if (argc >= 2 && !parse_color_arg(argv[1], &color)) {
        cprintf("usage: kmssolid [black|white|red|green|blue|gray|0xRRGGBB]\r\n");
        return -EINVAL;
    }

    if (kms_begin_frame(color) < 0) {
        return negative_errno_or(ENODEV);
    }
    if (kms_present_frame("kmssolid") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_kmsframe(void) {
    if (kms_begin_frame(0x080808) < 0) {
        return negative_errno_or(ENODEV);
    }
    kms_draw_boot_frame(&kms_state);
    if (kms_present_frame("kmsframe") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_statusscreen(void) {
    if (kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    cprintf("statusscreen: drawing giant TEST probe\r\n");
    kms_draw_giant_test_probe(&kms_state);
    if (kms_present_frame("statusscreen") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_statushud(void) {
    if (kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    cprintf("statushud: drawing sensor HUD\r\n");
    kms_draw_status_overlay(&kms_state, 0, 1);
    if (kms_present_frame("statushud") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int wait_watch_delay(int refresh_sec) {
    int remaining_ticks = refresh_sec * 10;

    while (remaining_ticks-- > 0) {
        enum cancel_kind cancel = poll_console_cancel(100);

        if (cancel != CANCEL_NONE) {
            return command_cancelled("watchhud", cancel);
        }
    }

    return 0;
}

static int clamp_hud_refresh(int refresh_sec);

static int cmd_watchhud(char **argv, int argc) {
    int refresh_sec = 2;
    int count = 0;
    int index = 0;
    int first_error = 0;
    bool drew_frame = false;

    if (argc >= 2 && sscanf(argv[1], "%d", &refresh_sec) != 1) {
        cprintf("usage: watchhud [sec] [count]\r\n");
        return -EINVAL;
    }
    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        cprintf("usage: watchhud [sec] [count]\r\n");
        return -EINVAL;
    }
    refresh_sec = clamp_hud_refresh(refresh_sec);

    cprintf("watchhud: refresh=%ds count=%s, q/Ctrl-C cancels\r\n",
            refresh_sec,
            count > 0 ? argv[2] : "forever");

    while (count <= 0 || index < count) {
        if (kms_begin_frame(0x000000) == 0) {
            kms_draw_status_overlay(&kms_state, (unsigned int)refresh_sec, (unsigned int)(index + 1));
            if (kms_present_frame("watchhud") == 0) {
                drew_frame = true;
            } else if (first_error == 0) {
                first_error = negative_errno_or(EIO);
            }
        } else if (first_error == 0) {
            first_error = negative_errno_or(ENODEV);
        }
        ++index;
        if (count > 0 && index >= count) {
            break;
        }
        {
            int wait_rc = wait_watch_delay(refresh_sec);

            if (wait_rc < 0) {
                return wait_rc;
            }
        }
    }

    return drew_frame ? 0 : first_error;
}

static int clamp_hud_refresh(int refresh_sec) {
    if (refresh_sec < 1) {
        return 1;
    }
    if (refresh_sec > 60) {
        return 60;
    }
    return refresh_sec;
}

static void reap_hud_child(void) {
    if (hud_pid > 0 && waitpid(hud_pid, NULL, WNOHANG) == hud_pid) {
        hud_pid = -1;
        clear_auto_menu_ipc();
    }
}

static void stop_auto_hud(bool verbose) {
    reap_hud_child();
    if (hud_pid <= 0) {
        if (verbose) {
            cprintf("autohud: not running\r\n");
        }
        return;
    }

    kill(hud_pid, SIGTERM);
    waitpid(hud_pid, NULL, 0);
    hud_pid = -1;
    clear_auto_menu_ipc();
    if (verbose) {
        cprintf("autohud: stopped\r\n");
    }
}

/* forward declarations for auto_hud_loop */
enum screen_menu_page_id {
    SCREEN_MENU_PAGE_MAIN = 0,
    SCREEN_MENU_PAGE_APPS,
    SCREEN_MENU_PAGE_ABOUT,
    SCREEN_MENU_PAGE_CHANGELOG,
    SCREEN_MENU_PAGE_MONITORING,
    SCREEN_MENU_PAGE_TOOLS,
    SCREEN_MENU_PAGE_CPU_STRESS,
    SCREEN_MENU_PAGE_LOGS,
    SCREEN_MENU_PAGE_NETWORK,
    SCREEN_MENU_PAGE_POWER,
    SCREEN_MENU_PAGE_COUNT,
};

enum screen_menu_action {
    SCREEN_MENU_RESUME = 0,
    SCREEN_MENU_STATUS,
    SCREEN_MENU_LOG,
    SCREEN_MENU_NET_STATUS,
    SCREEN_MENU_ABOUT_VERSION,
    SCREEN_MENU_ABOUT_CHANGELOG,
    SCREEN_MENU_ABOUT_CREDITS,
    SCREEN_MENU_CHANGELOG_088,
    SCREEN_MENU_CHANGELOG_087,
    SCREEN_MENU_CHANGELOG_086,
    SCREEN_MENU_CHANGELOG_085,
    SCREEN_MENU_CHANGELOG_084,
    SCREEN_MENU_CHANGELOG_083,
    SCREEN_MENU_CHANGELOG_082,
    SCREEN_MENU_CHANGELOG_081,
    SCREEN_MENU_CHANGELOG_080,
    SCREEN_MENU_CHANGELOG_075,
    SCREEN_MENU_CHANGELOG_074,
    SCREEN_MENU_CHANGELOG_073,
    SCREEN_MENU_CHANGELOG_072,
    SCREEN_MENU_CHANGELOG_071,
    SCREEN_MENU_CHANGELOG_070,
    SCREEN_MENU_CHANGELOG_060,
    SCREEN_MENU_CHANGELOG_051,
    SCREEN_MENU_CHANGELOG_050,
    SCREEN_MENU_CHANGELOG_041,
    SCREEN_MENU_CHANGELOG_040,
    SCREEN_MENU_CHANGELOG_030,
    SCREEN_MENU_CHANGELOG_020,
    SCREEN_MENU_CHANGELOG_010,
    SCREEN_MENU_INPUT_MONITOR,
    SCREEN_MENU_DISPLAY_TEST,
    SCREEN_MENU_CUTOUT_CAL,
    SCREEN_MENU_CPU_STRESS_5,
    SCREEN_MENU_CPU_STRESS_10,
    SCREEN_MENU_CPU_STRESS_30,
    SCREEN_MENU_CPU_STRESS_60,
    SCREEN_MENU_BACK,
    SCREEN_MENU_SUBMENU,
    SCREEN_MENU_RECOVERY,
    SCREEN_MENU_REBOOT,
    SCREEN_MENU_POWEROFF,
};

enum screen_app_id {
    SCREEN_APP_NONE = 0,
    SCREEN_APP_LOG,
    SCREEN_APP_NETWORK,
    SCREEN_APP_ABOUT_VERSION,
    SCREEN_APP_ABOUT_CHANGELOG,
    SCREEN_APP_ABOUT_CREDITS,
    SCREEN_APP_CHANGELOG_088,
    SCREEN_APP_CHANGELOG_087,
    SCREEN_APP_CHANGELOG_086,
    SCREEN_APP_CHANGELOG_085,
    SCREEN_APP_CHANGELOG_084,
    SCREEN_APP_CHANGELOG_083,
    SCREEN_APP_CHANGELOG_082,
    SCREEN_APP_CHANGELOG_081,
    SCREEN_APP_CHANGELOG_080,
    SCREEN_APP_CHANGELOG_075,
    SCREEN_APP_CHANGELOG_074,
    SCREEN_APP_CHANGELOG_073,
    SCREEN_APP_CHANGELOG_072,
    SCREEN_APP_CHANGELOG_071,
    SCREEN_APP_CHANGELOG_070,
    SCREEN_APP_CHANGELOG_060,
    SCREEN_APP_CHANGELOG_051,
    SCREEN_APP_CHANGELOG_050,
    SCREEN_APP_CHANGELOG_041,
    SCREEN_APP_CHANGELOG_040,
    SCREEN_APP_CHANGELOG_030,
    SCREEN_APP_CHANGELOG_020,
    SCREEN_APP_CHANGELOG_010,
    SCREEN_APP_INPUT_MONITOR,
    SCREEN_APP_DISPLAY_TEST,
    SCREEN_APP_CUTOUT_CAL,
    SCREEN_APP_CPU_STRESS,
};

enum cutout_calibration_field {
    CUTOUT_CAL_FIELD_X = 0,
    CUTOUT_CAL_FIELD_Y,
    CUTOUT_CAL_FIELD_SIZE,
    CUTOUT_CAL_FIELD_COUNT,
};

struct cutout_calibration_state {
    int center_x;
    int center_y;
    int size;
    enum cutout_calibration_field field;
};

struct screen_menu_item {
    const char *name;
    const char *summary;
    enum screen_menu_action action;
    enum screen_menu_page_id target;
};

struct screen_menu_page {
    const char *title;
    const struct screen_menu_item *items;
    size_t count;
    enum screen_menu_page_id parent;
};

struct key_wait_context { int fd0; int fd3; };
static int open_key_wait_context(struct key_wait_context *ctx, const char *tag);
static void close_key_wait_context(struct key_wait_context *ctx);
static void kms_draw_menu_section(struct kms_display_state *state,
                                  const struct screen_menu_page *page,
                                  size_t selected);
static void kms_draw_log_tail_panel(struct kms_display_state *state,
                                    uint32_t x,
                                    uint32_t y,
                                    uint32_t width,
                                    uint32_t bottom,
                                    int max_lines,
                                    const char *title,
                                    uint32_t scale);
static void kms_draw_hud_log_tail(struct kms_display_state *state);
static int cmd_statushud(void);
static int cmd_recovery(void);
static int draw_screen_log_summary(void);
static int draw_screen_network_summary(void);
static int draw_screen_about_version(void);
static int draw_screen_about_changelog(void);
static int draw_screen_about_credits(void);
static int draw_screen_changelog_detail(enum screen_app_id app_id);
static int draw_screen_input_monitor_app(void);
static int draw_screen_display_test_page(unsigned int page_index);
static int draw_screen_display_test(void);
static void cutout_calibration_init(struct cutout_calibration_state *cal);
static bool cutout_calibration_feed_key(struct cutout_calibration_state *cal,
                                        const struct input_event *event,
                                        unsigned int *down_mask,
                                        long *power_down_ms,
                                        long *last_power_up_ms);
static int draw_screen_cutout_calibration(const struct cutout_calibration_state *cal,
                                          bool interactive);
static int draw_screen_cpu_hint(void);
static int draw_screen_cpu_stress_app(bool running,
                                      bool done,
                                      bool failed,
                                      long remaining_ms,
                                      long duration_ms);
static uint32_t shrink_text_scale(const char *text, uint32_t scale, uint32_t max_width);
static void cpustress_worker(long deadline_ms, unsigned int worker_index);
static void cpustress_stop_workers(pid_t *pids, unsigned int workers);
static void restore_auto_hud_if_needed(bool restore_hud);
static void input_monitor_app_reset(void);
static void input_monitor_app_tick(void);
static bool input_monitor_app_feed_event(const struct input_event *event,
                                         int source_index);

#define SCREEN_MENU_COUNT(items) (sizeof(items) / sizeof((items)[0]))

static const struct screen_menu_item screen_menu_main_items[] = {
    { "APPS >",    "OPEN APP FOLDERS", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_APPS },
    { "STATUS",    "LIVE SYSTEM VIEW", SCREEN_MENU_STATUS, SCREEN_MENU_PAGE_MAIN },
    { "NETWORK >", "NCM AND TCPCTL",   SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_NETWORK },
    { "POWER >",   "REBOOT OPTIONS",   SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_POWER },
    { "HIDE MENU", "RETURN TO HUD",    SCREEN_MENU_RESUME, SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_item screen_menu_apps_items[] = {
    { "ABOUT >",      "VERSION AND CREDITS", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_ABOUT },
    { "MONITORING >", "STATUS APPLETS", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_MONITORING },
    { "TOOLS >",      "TEST HELPERS",   SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_TOOLS },
    { "LOGS >",       "LOG VIEWERS",    SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_LOGS },
    { "BACK",         "MAIN MENU",      SCREEN_MENU_BACK,    SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_item screen_menu_about_items[] = {
    { "VERSION",     "CURRENT BUILD",   SCREEN_MENU_ABOUT_VERSION,  SCREEN_MENU_PAGE_ABOUT },
    { "CHANGELOG >", "VERSION DETAILS", SCREEN_MENU_SUBMENU,        SCREEN_MENU_PAGE_CHANGELOG },
    { "CREDITS",     "MADE BY",         SCREEN_MENU_ABOUT_CREDITS,  SCREEN_MENU_PAGE_ABOUT },
    { "BACK",        "APPS",            SCREEN_MENU_BACK,           SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_changelog_items[] = {
    { "0.8.8 v77", "DISPLAY TEST PAGES",   SCREEN_MENU_CHANGELOG_088, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.7 v76", "AT FRAGMENT FILTER",    SCREEN_MENU_CHANGELOG_087, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.6 v75", "QUIET IDLE REATTACH",  SCREEN_MENU_CHANGELOG_086, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.5 v74", "CMDV1 ARG ENCODING",   SCREEN_MENU_CHANGELOG_085, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.4 v73", "CMDV1 PROTOCOL",       SCREEN_MENU_CHANGELOG_084, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.3 v72", "DISPLAY TEST FIX",     SCREEN_MENU_CHANGELOG_083, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.2 v71", "MENU LOG TAIL",        SCREEN_MENU_CHANGELOG_082, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.1 v70", "INPUT MONITOR APP",    SCREEN_MENU_CHANGELOG_081, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.0 v69", "INPUT GESTURE LAYOUT", SCREEN_MENU_CHANGELOG_080, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.5 v68", "LOG TAIL + HISTORY",  SCREEN_MENU_CHANGELOG_075, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.4 v67", "DETAIL CHANGELOG UI", SCREEN_MENU_CHANGELOG_074, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.3 v66", "ABOUT + VERSIONING",  SCREEN_MENU_CHANGELOG_073, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.2 v65", "SPLASH SAFE LAYOUT",  SCREEN_MENU_CHANGELOG_072, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.1 v64", "CUSTOM BOOT SPLASH",  SCREEN_MENU_CHANGELOG_071, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.0 v63", "APP MENU",            SCREEN_MENU_CHANGELOG_070, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.6.0 v62", "CPU DIAGNOSTICS",     SCREEN_MENU_CHANGELOG_060, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.5.1 v61", "CPU/GPU USAGE HUD",  SCREEN_MENU_CHANGELOG_051, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.5.0 v60", "NETSERVICE BOOT",    SCREEN_MENU_CHANGELOG_050, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.4.1 v59", "AT SERIAL FILTER",   SCREEN_MENU_CHANGELOG_041, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.4.0 v55", "NCM TCP CONTROL",    SCREEN_MENU_CHANGELOG_040, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.3.0 v53", "MENU BUSY GATE",     SCREEN_MENU_CHANGELOG_030, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.2.0 v40", "SHELL LOG HUD CORE", SCREEN_MENU_CHANGELOG_020, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.1.0 v1",  "NATIVE INIT ORIGIN", SCREEN_MENU_CHANGELOG_010, SCREEN_MENU_PAGE_CHANGELOG },
    { "BACK",      "ABOUT",              SCREEN_MENU_BACK,           SCREEN_MENU_PAGE_ABOUT },
};

static const struct screen_menu_item screen_menu_monitoring_items[] = {
    { "LIVE STATUS", "DRAW STATUS HUD", SCREEN_MENU_STATUS, SCREEN_MENU_PAGE_MONITORING },
    { "BACK",        "APPS",            SCREEN_MENU_BACK,   SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_tools_items[] = {
    { "INPUT MONITOR", "RAW KEY + GESTURE LOG", SCREEN_MENU_INPUT_MONITOR, SCREEN_MENU_PAGE_TOOLS },
    { "DISPLAY TEST",  "COLORS FONT GRID",      SCREEN_MENU_DISPLAY_TEST,  SCREEN_MENU_PAGE_TOOLS },
    { "CUTOUT CAL",    "ALIGN CAMERA HOLE",     SCREEN_MENU_CUTOUT_CAL,   SCREEN_MENU_PAGE_TOOLS },
    { "CPU STRESS >", "SELECT TEST TIME", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_CPU_STRESS },
    { "BACK",         "APPS",             SCREEN_MENU_BACK,    SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_cpu_stress_items[] = {
    { "5 SECONDS",  "QUICK CHECK",     SCREEN_MENU_CPU_STRESS_5,  SCREEN_MENU_PAGE_CPU_STRESS },
    { "10 SECONDS", "DEFAULT CHECK",   SCREEN_MENU_CPU_STRESS_10, SCREEN_MENU_PAGE_CPU_STRESS },
    { "30 SECONDS", "THERMAL SAMPLE",  SCREEN_MENU_CPU_STRESS_30, SCREEN_MENU_PAGE_CPU_STRESS },
    { "60 SECONDS", "LONGER SAMPLE",   SCREEN_MENU_CPU_STRESS_60, SCREEN_MENU_PAGE_CPU_STRESS },
    { "BACK",       "TOOLS",           SCREEN_MENU_BACK,          SCREEN_MENU_PAGE_TOOLS },
};

static const struct screen_menu_item screen_menu_logs_items[] = {
    { "LOG SUMMARY", "BOOT/COMMAND LOG", SCREEN_MENU_LOG,  SCREEN_MENU_PAGE_LOGS },
    { "BACK",        "APPS",             SCREEN_MENU_BACK, SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_network_items[] = {
    { "NET STATUS", "NCM/TCPCTL STATE", SCREEN_MENU_NET_STATUS, SCREEN_MENU_PAGE_NETWORK },
    { "BACK",       "MAIN MENU",        SCREEN_MENU_BACK,       SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_item screen_menu_power_items[] = {
    { "RECOVERY", "REBOOT TO TWRP", SCREEN_MENU_RECOVERY, SCREEN_MENU_PAGE_POWER },
    { "REBOOT",   "RESTART DEVICE", SCREEN_MENU_REBOOT,   SCREEN_MENU_PAGE_POWER },
    { "POWEROFF", "POWER OFF",      SCREEN_MENU_POWEROFF, SCREEN_MENU_PAGE_POWER },
    { "BACK",     "MAIN MENU",      SCREEN_MENU_BACK,     SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_page screen_menu_pages[SCREEN_MENU_PAGE_COUNT] = {
    [SCREEN_MENU_PAGE_MAIN] = {
        "MAIN MENU", screen_menu_main_items,
        SCREEN_MENU_COUNT(screen_menu_main_items), SCREEN_MENU_PAGE_MAIN
    },
    [SCREEN_MENU_PAGE_APPS] = {
        "APPS", screen_menu_apps_items,
        SCREEN_MENU_COUNT(screen_menu_apps_items), SCREEN_MENU_PAGE_MAIN
    },
    [SCREEN_MENU_PAGE_ABOUT] = {
        "APPS / ABOUT", screen_menu_about_items,
        SCREEN_MENU_COUNT(screen_menu_about_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_CHANGELOG] = {
        "ABOUT / CHANGELOG", screen_menu_changelog_items,
        SCREEN_MENU_COUNT(screen_menu_changelog_items), SCREEN_MENU_PAGE_ABOUT
    },
    [SCREEN_MENU_PAGE_MONITORING] = {
        "APPS / MONITORING", screen_menu_monitoring_items,
        SCREEN_MENU_COUNT(screen_menu_monitoring_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_TOOLS] = {
        "APPS / TOOLS", screen_menu_tools_items,
        SCREEN_MENU_COUNT(screen_menu_tools_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_CPU_STRESS] = {
        "TOOLS / CPU STRESS", screen_menu_cpu_stress_items,
        SCREEN_MENU_COUNT(screen_menu_cpu_stress_items), SCREEN_MENU_PAGE_TOOLS
    },
    [SCREEN_MENU_PAGE_LOGS] = {
        "APPS / LOGS", screen_menu_logs_items,
        SCREEN_MENU_COUNT(screen_menu_logs_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_NETWORK] = {
        "NETWORK", screen_menu_network_items,
        SCREEN_MENU_COUNT(screen_menu_network_items), SCREEN_MENU_PAGE_MAIN
    },
    [SCREEN_MENU_PAGE_POWER] = {
        "POWER", screen_menu_power_items,
        SCREEN_MENU_COUNT(screen_menu_power_items), SCREEN_MENU_PAGE_MAIN
    },
};

static const struct screen_menu_page *screen_menu_get_page(enum screen_menu_page_id page_id) {
    if ((int)page_id < 0 || page_id >= SCREEN_MENU_PAGE_COUNT) {
        page_id = SCREEN_MENU_PAGE_MAIN;
    }
    return &screen_menu_pages[page_id];
}

static long screen_menu_cpu_stress_seconds(enum screen_menu_action action) {
    switch (action) {
    case SCREEN_MENU_CPU_STRESS_5:
        return 5;
    case SCREEN_MENU_CPU_STRESS_10:
        return 10;
    case SCREEN_MENU_CPU_STRESS_30:
        return 30;
    case SCREEN_MENU_CPU_STRESS_60:
        return 60;
    default:
        return 0;
    }
}

static enum screen_app_id screen_menu_about_app(enum screen_menu_action action) {
    switch (action) {
    case SCREEN_MENU_ABOUT_VERSION:
        return SCREEN_APP_ABOUT_VERSION;
    case SCREEN_MENU_ABOUT_CHANGELOG:
        return SCREEN_APP_ABOUT_CHANGELOG;
    case SCREEN_MENU_ABOUT_CREDITS:
        return SCREEN_APP_ABOUT_CREDITS;
    case SCREEN_MENU_CHANGELOG_088:
        return SCREEN_APP_CHANGELOG_088;
    case SCREEN_MENU_CHANGELOG_087:
        return SCREEN_APP_CHANGELOG_087;
    case SCREEN_MENU_CHANGELOG_086:
        return SCREEN_APP_CHANGELOG_086;
    case SCREEN_MENU_CHANGELOG_085:
        return SCREEN_APP_CHANGELOG_085;
    case SCREEN_MENU_CHANGELOG_084:
        return SCREEN_APP_CHANGELOG_084;
    case SCREEN_MENU_CHANGELOG_083:
        return SCREEN_APP_CHANGELOG_083;
    case SCREEN_MENU_CHANGELOG_082:
        return SCREEN_APP_CHANGELOG_082;
    case SCREEN_MENU_CHANGELOG_081:
        return SCREEN_APP_CHANGELOG_081;
    case SCREEN_MENU_CHANGELOG_080:
        return SCREEN_APP_CHANGELOG_080;
    case SCREEN_MENU_CHANGELOG_075:
        return SCREEN_APP_CHANGELOG_075;
    case SCREEN_MENU_CHANGELOG_074:
        return SCREEN_APP_CHANGELOG_074;
    case SCREEN_MENU_CHANGELOG_073:
        return SCREEN_APP_CHANGELOG_073;
    case SCREEN_MENU_CHANGELOG_072:
        return SCREEN_APP_CHANGELOG_072;
    case SCREEN_MENU_CHANGELOG_071:
        return SCREEN_APP_CHANGELOG_071;
    case SCREEN_MENU_CHANGELOG_070:
        return SCREEN_APP_CHANGELOG_070;
    case SCREEN_MENU_CHANGELOG_060:
        return SCREEN_APP_CHANGELOG_060;
    case SCREEN_MENU_CHANGELOG_051:
        return SCREEN_APP_CHANGELOG_051;
    case SCREEN_MENU_CHANGELOG_050:
        return SCREEN_APP_CHANGELOG_050;
    case SCREEN_MENU_CHANGELOG_041:
        return SCREEN_APP_CHANGELOG_041;
    case SCREEN_MENU_CHANGELOG_040:
        return SCREEN_APP_CHANGELOG_040;
    case SCREEN_MENU_CHANGELOG_030:
        return SCREEN_APP_CHANGELOG_030;
    case SCREEN_MENU_CHANGELOG_020:
        return SCREEN_APP_CHANGELOG_020;
    case SCREEN_MENU_CHANGELOG_010:
        return SCREEN_APP_CHANGELOG_010;
    default:
        return SCREEN_APP_NONE;
    }
}

static int draw_screen_about_app(enum screen_app_id app_id) {
    switch (app_id) {
    case SCREEN_APP_ABOUT_VERSION:
        return draw_screen_about_version();
    case SCREEN_APP_ABOUT_CHANGELOG:
        return draw_screen_about_changelog();
    case SCREEN_APP_ABOUT_CREDITS:
        return draw_screen_about_credits();
    case SCREEN_APP_CHANGELOG_088:
    case SCREEN_APP_CHANGELOG_087:
    case SCREEN_APP_CHANGELOG_086:
    case SCREEN_APP_CHANGELOG_085:
    case SCREEN_APP_CHANGELOG_084:
    case SCREEN_APP_CHANGELOG_083:
    case SCREEN_APP_CHANGELOG_082:
    case SCREEN_APP_CHANGELOG_081:
    case SCREEN_APP_CHANGELOG_080:
    case SCREEN_APP_CHANGELOG_075:
    case SCREEN_APP_CHANGELOG_074:
    case SCREEN_APP_CHANGELOG_073:
    case SCREEN_APP_CHANGELOG_072:
    case SCREEN_APP_CHANGELOG_071:
    case SCREEN_APP_CHANGELOG_070:
    case SCREEN_APP_CHANGELOG_060:
    case SCREEN_APP_CHANGELOG_051:
    case SCREEN_APP_CHANGELOG_050:
    case SCREEN_APP_CHANGELOG_041:
    case SCREEN_APP_CHANGELOG_040:
    case SCREEN_APP_CHANGELOG_030:
    case SCREEN_APP_CHANGELOG_020:
    case SCREEN_APP_CHANGELOG_010:
        return draw_screen_changelog_detail(app_id);
    default:
        return 0;
    }
}

static void screen_app_reset_stress_pids(pid_t *pids, unsigned int workers) {
    unsigned int index;

    for (index = 0; index < workers; ++index) {
        pids[index] = -1;
    }
}

static int screen_app_start_cpu_stress(pid_t *pids,
                                       unsigned int workers,
                                       long deadline_ms,
                                       unsigned int *running) {
    unsigned int index;

    screen_app_reset_stress_pids(pids, workers);
    *running = 0;
    for (index = 0; index < workers; ++index) {
        pid_t pid = fork();

        if (pid < 0) {
            int saved_errno = errno;

            cpustress_stop_workers(pids, workers);
            *running = 0;
            return -saved_errno;
        }
        if (pid == 0) {
            cpustress_worker(deadline_ms, index);
        }
        pids[index] = pid;
        ++*running;
    }
    return 0;
}

static void screen_app_read_cpu_freq_label(unsigned int cpu,
                                           char *out,
                                           size_t out_size) {
    char path[PATH_MAX];
    long khz;

    snprintf(out, out_size, "?");
    if (snprintf(path, sizeof(path),
                 "/sys/devices/system/cpu/cpu%u/cpufreq/scaling_cur_freq",
                 cpu) >= (int)sizeof(path)) {
        return;
    }
    if (read_long_value(path, &khz) < 0) {
        if (snprintf(path, sizeof(path),
                     "/sys/devices/system/cpu/cpu%u/cpufreq/cpuinfo_cur_freq",
                     cpu) >= (int)sizeof(path) ||
            read_long_value(path, &khz) < 0) {
            return;
        }
    }
    if (khz >= 1000000) {
        long tenths = (khz + 50000) / 100000;
        snprintf(out, out_size, "%ld.%ldG", tenths / 10, tenths % 10);
    } else {
        snprintf(out, out_size, "%ldM", (khz + 500) / 1000);
    }
}

static void screen_app_reap_cpu_stress(pid_t *pids,
                                       unsigned int workers,
                                       unsigned int *running) {
    unsigned int index;

    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            int status;
            pid_t got = waitpid(pids[index], &status, WNOHANG);

            if (got == pids[index]) {
                pids[index] = -1;
                if (*running > 0) {
                    --*running;
                }
            }
        }
    }
}

static void auto_hud_loop(unsigned int refresh_sec) {
    struct key_wait_context ctx;
    bool menu_active = true;
    enum screen_app_id active_app = SCREEN_APP_NONE;
    enum screen_menu_page_id current_page = SCREEN_MENU_PAGE_MAIN;
    size_t menu_sel = 0;
    pid_t app_stress_pids[8];
    unsigned int app_stress_workers = 8;
    unsigned int app_stress_running = 0;
    long app_stress_deadline_ms = 0;
    long app_stress_duration_ms = 10000L;
    bool app_stress_done = false;
    bool app_stress_failed = false;
    unsigned int display_test_page = 0;
    struct cutout_calibration_state cutout_cal;
    unsigned int cutout_down_mask = 0;
    long cutout_power_down_ms = 0;
    long cutout_last_power_up_ms = 0;
    bool has_input;
    int timeout_ms;

    signal(SIGTERM, SIG_DFL);
    has_input = (open_key_wait_context(&ctx, "autohud") == 0);
    timeout_ms = (refresh_sec > 0 && refresh_sec <= 60) ? (int)(refresh_sec * 1000) : 2000;
    screen_app_reset_stress_pids(app_stress_pids, app_stress_workers);
    cutout_calibration_init(&cutout_cal);
    set_auto_menu_active(menu_active);

    while (1) {
        struct pollfd fds[2];
        int poll_rc;
        int fi;

        if (consume_auto_menu_hide_request()) {
            if (active_app == SCREEN_APP_CPU_STRESS && app_stress_running > 0) {
                cpustress_stop_workers(app_stress_pids, app_stress_workers);
                app_stress_running = 0;
            }
            active_app = SCREEN_APP_NONE;
            menu_active = false;
            current_page = SCREEN_MENU_PAGE_MAIN;
            menu_sel = 0;
            display_test_page = 0;
            cutout_calibration_init(&cutout_cal);
            cutout_down_mask = 0;
            cutout_power_down_ms = 0;
            cutout_last_power_up_ms = 0;
        }
        set_auto_menu_state(menu_active || active_app != SCREEN_APP_NONE,
                            menu_active &&
                            active_app == SCREEN_APP_NONE &&
                            current_page == SCREEN_MENU_PAGE_POWER);
        if (active_app == SCREEN_APP_INPUT_MONITOR) {
            input_monitor_app_tick();
        }

        /* draw */
        if (active_app == SCREEN_APP_LOG) {
            draw_screen_log_summary();
        } else if (active_app == SCREEN_APP_NETWORK) {
            draw_screen_network_summary();
        } else if (active_app == SCREEN_APP_INPUT_MONITOR) {
            draw_screen_input_monitor_app();
        } else if (active_app == SCREEN_APP_DISPLAY_TEST) {
            draw_screen_display_test_page(display_test_page);
        } else if (active_app == SCREEN_APP_CUTOUT_CAL) {
            draw_screen_cutout_calibration(&cutout_cal, true);
        } else if (active_app == SCREEN_APP_ABOUT_VERSION ||
                   active_app == SCREEN_APP_ABOUT_CHANGELOG ||
                   active_app == SCREEN_APP_ABOUT_CREDITS ||
                   active_app == SCREEN_APP_CHANGELOG_088 ||
                   active_app == SCREEN_APP_CHANGELOG_087 ||
                   active_app == SCREEN_APP_CHANGELOG_086 ||
                   active_app == SCREEN_APP_CHANGELOG_085 ||
                   active_app == SCREEN_APP_CHANGELOG_084 ||
                   active_app == SCREEN_APP_CHANGELOG_083 ||
                   active_app == SCREEN_APP_CHANGELOG_082 ||
                   active_app == SCREEN_APP_CHANGELOG_081 ||
                   active_app == SCREEN_APP_CHANGELOG_080 ||
                   active_app == SCREEN_APP_CHANGELOG_075 ||
                   active_app == SCREEN_APP_CHANGELOG_074 ||
                   active_app == SCREEN_APP_CHANGELOG_073 ||
                   active_app == SCREEN_APP_CHANGELOG_072 ||
                   active_app == SCREEN_APP_CHANGELOG_071 ||
                   active_app == SCREEN_APP_CHANGELOG_070 ||
                   active_app == SCREEN_APP_CHANGELOG_060 ||
                   active_app == SCREEN_APP_CHANGELOG_051 ||
                   active_app == SCREEN_APP_CHANGELOG_050 ||
                   active_app == SCREEN_APP_CHANGELOG_041 ||
                   active_app == SCREEN_APP_CHANGELOG_040 ||
                   active_app == SCREEN_APP_CHANGELOG_030 ||
                   active_app == SCREEN_APP_CHANGELOG_020 ||
                   active_app == SCREEN_APP_CHANGELOG_010) {
            draw_screen_about_app(active_app);
        } else if (active_app == SCREEN_APP_CPU_STRESS) {
            long now_ms = monotonic_millis();
            long remaining_ms = app_stress_deadline_ms - now_ms;

            screen_app_reap_cpu_stress(app_stress_pids,
                                       app_stress_workers,
                                       &app_stress_running);
            if (app_stress_running == 0 && !app_stress_failed) {
                app_stress_done = true;
            } else if (app_stress_running > 0 && now_ms > app_stress_deadline_ms + 2000L) {
                cpustress_stop_workers(app_stress_pids, app_stress_workers);
                app_stress_running = 0;
                app_stress_done = true;
                app_stress_failed = true;
            }
            if (remaining_ms < 0) {
                remaining_ms = 0;
            }
            draw_screen_cpu_stress_app(app_stress_running > 0,
                                       app_stress_done,
                                       app_stress_failed,
                                       remaining_ms,
                                       app_stress_duration_ms);
        } else if (kms_begin_frame(0x000000) == 0) {
            const struct screen_menu_page *page = screen_menu_get_page(current_page);

            kms_draw_status_overlay(&kms_state, 0, 0);
            if (menu_active)
                kms_draw_menu_section(&kms_state, page, menu_sel);
            else
                kms_draw_hud_log_tail(&kms_state);
            kms_present_frame_verbose("autohud", false);
        }

        if (!has_input) {
            sleep(refresh_sec);
            continue;
        }

        fds[0].fd = ctx.fd0; fds[0].events = POLLIN;
        fds[1].fd = ctx.fd3; fds[1].events = POLLIN;
        poll_rc = poll(fds, 2, active_app == SCREEN_APP_NONE ? timeout_ms : 500);
        if (poll_rc <= 0)
            continue; /* timeout → redraw */

        for (fi = 0; fi < 2; fi++) {
            struct input_event ev;
            if (!(fds[fi].revents & POLLIN))
                continue;
            while (read(fds[fi].fd, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
                if (active_app == SCREEN_APP_INPUT_MONITOR && ev.type == EV_KEY) {
                    if (input_monitor_app_feed_event(&ev, fi)) {
                        active_app = SCREEN_APP_NONE;
                        menu_active = true;
                        set_auto_menu_active(true);
                    }
                    continue;
                }

                if (active_app == SCREEN_APP_CUTOUT_CAL && ev.type == EV_KEY) {
                    if (cutout_calibration_feed_key(&cutout_cal,
                                                    &ev,
                                                    &cutout_down_mask,
                                                    &cutout_power_down_ms,
                                                    &cutout_last_power_up_ms)) {
                        active_app = SCREEN_APP_NONE;
                        menu_active = true;
                        set_auto_menu_active(true);
                        cutout_down_mask = 0;
                        cutout_power_down_ms = 0;
                        cutout_last_power_up_ms = 0;
                    }
                    continue;
                }

                if (ev.type != EV_KEY || ev.value != 1)
                    continue;

                if (active_app != SCREEN_APP_NONE) {
                    if (active_app == SCREEN_APP_DISPLAY_TEST) {
                        if (ev.code == KEY_VOLUMEUP) {
                            display_test_page =
                                (display_test_page + DISPLAY_TEST_PAGE_COUNT - 1) %
                                DISPLAY_TEST_PAGE_COUNT;
                            continue;
                        }
                        if (ev.code == KEY_VOLUMEDOWN) {
                            display_test_page =
                                (display_test_page + 1) % DISPLAY_TEST_PAGE_COUNT;
                            continue;
                        }
                    }
                    if (active_app == SCREEN_APP_CPU_STRESS && app_stress_running > 0) {
                        cpustress_stop_workers(app_stress_pids, app_stress_workers);
                        app_stress_running = 0;
                    }
                    active_app = SCREEN_APP_NONE;
                    menu_active = true;
                    set_auto_menu_active(true);
                    continue;
                }

                if (ev.code == KEY_VOLUMEUP) {
                    const struct screen_menu_page *page = screen_menu_get_page(current_page);

                    if (!menu_active) {
                        menu_active = true;
                        current_page = SCREEN_MENU_PAGE_MAIN;
                        menu_sel = 0;
                    } else {
                        menu_sel = (menu_sel + page->count - 1) % page->count;
                    }
                } else if (ev.code == KEY_VOLUMEDOWN) {
                    const struct screen_menu_page *page = screen_menu_get_page(current_page);

                    if (!menu_active) {
                        menu_active = true;
                        current_page = SCREEN_MENU_PAGE_MAIN;
                        menu_sel = 0;
                    } else {
                        menu_sel = (menu_sel + 1) % page->count;
                    }
                } else if (ev.code == KEY_POWER && menu_active) {
                    const struct screen_menu_page *page = screen_menu_get_page(current_page);
                    const struct screen_menu_item *item = &page->items[menu_sel];

                    switch (item->action) {
                    case SCREEN_MENU_RESUME:
                        menu_active = false;
                        current_page = SCREEN_MENU_PAGE_MAIN;
                        menu_sel = 0;
                        set_auto_menu_active(false);
                        break;
                    case SCREEN_MENU_SUBMENU:
                        current_page = item->target;
                        menu_sel = 0;
                        break;
                    case SCREEN_MENU_BACK:
                        current_page = page->parent;
                        menu_sel = 0;
                        break;
                    case SCREEN_MENU_STATUS:
                        cmd_statushud();
                        menu_active = false;
                        set_auto_menu_active(false);
                        break;
                    case SCREEN_MENU_LOG:
                        active_app = SCREEN_APP_LOG;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_NET_STATUS:
                        active_app = SCREEN_APP_NETWORK;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_INPUT_MONITOR:
                        input_monitor_app_reset();
                        active_app = SCREEN_APP_INPUT_MONITOR;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_DISPLAY_TEST:
                        display_test_page = 0;
                        active_app = SCREEN_APP_DISPLAY_TEST;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_CUTOUT_CAL:
                        cutout_calibration_init(&cutout_cal);
                        cutout_down_mask = 0;
                        cutout_power_down_ms = 0;
                        cutout_last_power_up_ms = 0;
                        active_app = SCREEN_APP_CUTOUT_CAL;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_ABOUT_VERSION:
                    case SCREEN_MENU_ABOUT_CHANGELOG:
                    case SCREEN_MENU_ABOUT_CREDITS:
                    case SCREEN_MENU_CHANGELOG_088:
                    case SCREEN_MENU_CHANGELOG_087:
                    case SCREEN_MENU_CHANGELOG_086:
                    case SCREEN_MENU_CHANGELOG_085:
                    case SCREEN_MENU_CHANGELOG_084:
                    case SCREEN_MENU_CHANGELOG_083:
                    case SCREEN_MENU_CHANGELOG_082:
                    case SCREEN_MENU_CHANGELOG_081:
                    case SCREEN_MENU_CHANGELOG_080:
                    case SCREEN_MENU_CHANGELOG_075:
                    case SCREEN_MENU_CHANGELOG_074:
                    case SCREEN_MENU_CHANGELOG_073:
                    case SCREEN_MENU_CHANGELOG_072:
                    case SCREEN_MENU_CHANGELOG_071:
                    case SCREEN_MENU_CHANGELOG_070:
                    case SCREEN_MENU_CHANGELOG_060:
                    case SCREEN_MENU_CHANGELOG_051:
                    case SCREEN_MENU_CHANGELOG_050:
                    case SCREEN_MENU_CHANGELOG_041:
                    case SCREEN_MENU_CHANGELOG_040:
                    case SCREEN_MENU_CHANGELOG_030:
                    case SCREEN_MENU_CHANGELOG_020:
                    case SCREEN_MENU_CHANGELOG_010:
                        active_app = screen_menu_about_app(item->action);
                        menu_active = false;
                        break;
                    case SCREEN_MENU_CPU_STRESS_5:
                    case SCREEN_MENU_CPU_STRESS_10:
                    case SCREEN_MENU_CPU_STRESS_30:
                    case SCREEN_MENU_CPU_STRESS_60:
                    {
                        long stress_seconds = screen_menu_cpu_stress_seconds(item->action);

                        active_app = SCREEN_APP_CPU_STRESS;
                        menu_active = false;
                        app_stress_done = false;
                        app_stress_failed = false;
                        app_stress_duration_ms = stress_seconds * 1000L;
                        app_stress_deadline_ms = monotonic_millis() + app_stress_duration_ms;
                        if (screen_app_start_cpu_stress(app_stress_pids,
                                                        app_stress_workers,
                                                        app_stress_deadline_ms,
                                                        &app_stress_running) < 0) {
                            app_stress_failed = true;
                            app_stress_done = true;
                        }
                        break;
                    }
                    case SCREEN_MENU_RECOVERY:
                        set_auto_menu_active(false);
                        unlink(AUTO_MENU_REQUEST_PATH);
                        close_key_wait_context(&ctx);
                        cmd_recovery();
                        return;
                    case SCREEN_MENU_REBOOT:
                        set_auto_menu_active(false);
                        unlink(AUTO_MENU_REQUEST_PATH);
                        close_key_wait_context(&ctx);
                        sync();
                        reboot(RB_AUTOBOOT);
                        return;
                    case SCREEN_MENU_POWEROFF:
                        set_auto_menu_active(false);
                        unlink(AUTO_MENU_REQUEST_PATH);
                        close_key_wait_context(&ctx);
                        sync();
                        reboot(RB_POWER_OFF);
                        return;
                    }
                }
            }
        }
    }
}

static int start_auto_hud(int refresh_sec, bool verbose) {
    int saved_errno;

    refresh_sec = clamp_hud_refresh(refresh_sec);

    stop_auto_hud(false);
    unlink(AUTO_MENU_REQUEST_PATH);
    set_auto_menu_active(true);

    hud_pid = fork();
    if (hud_pid < 0) {
        saved_errno = errno;
        clear_auto_menu_ipc();
        if (verbose) {
            cprintf("autohud: fork: %s\r\n", strerror(saved_errno));
        }
        hud_pid = -1;
        return -saved_errno;
    }
    if (hud_pid == 0) {
        auto_hud_loop((unsigned int)refresh_sec);
        _exit(0);
    }

    if (verbose) {
        cprintf("autohud: pid=%ld refresh=%ds\r\n", (long)hud_pid, refresh_sec);
    }
    return 0;
}

static int cmd_autohud(char **argv, int argc) {
    int refresh_sec = 2;

    if (argc >= 2 && sscanf(argv[1], "%d", &refresh_sec) != 1) {
        cprintf("usage: autohud [sec]\r\n");
        return -EINVAL;
    }

    return start_auto_hud(refresh_sec, true);
}

static int cmd_stophud(void) {
    stop_auto_hud(true);
    return 0;
}

static int cmd_clear_display(void) {
    stop_auto_hud(false);
    if (kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    if (kms_present_frame("clear") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void kms_draw_text_fit(struct kms_display_state *state,
                              uint32_t x,
                              uint32_t y,
                              const char *text,
                              uint32_t color,
                              uint32_t scale,
                              uint32_t max_width) {
    kms_draw_text(state, x, y, text, color, shrink_text_scale(text, scale, max_width));
}

static void kms_draw_boot_splash(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
    uint32_t scale = width >= 1080 ? 5 : 4;
    uint32_t title_scale = scale + 2;
    uint32_t x = width / 16;
    uint32_t y = height / 8;
    uint32_t card_w = width - x * 2;
    uint32_t line_h = scale * 11;
    uint32_t card_y;
    uint32_t row_y;
    uint32_t row_gap = scale * 12;
    uint32_t row_x;
    uint32_t row_w;
    uint32_t footer_scale = scale > 3 ? scale - 1 : scale;

    if (x < scale * 10) {
        x = scale * 10;
    }
    card_w = width - x * 2;

    kms_fill_color(state, 0x020713);
    kms_fill_rect(state, 0, 0, width, height / 36, 0x0b2a55);
    kms_fill_rect(state, 0, height - height / 60, width, height / 60, 0x0088cc);
    kms_fill_rect(state, x, y - scale * 3, card_w, scale * 2, 0x0088cc);

    kms_draw_text_fit(state, x, y, "A90 NATIVE INIT", 0xffffff, title_scale, card_w);
    y += title_scale * 10;
    kms_draw_text_fit(state, x, y, INIT_BANNER, 0xffcc33, scale, card_w);
    y += line_h;
    kms_draw_text_fit(state, x, y, INIT_CREATOR, 0x88ee88, scale, card_w);

    card_y = y + line_h + scale * 5;
    kms_fill_rect(state, x - scale, card_y - scale, card_w, row_gap * 4 + scale * 2, 0x101820);
    kms_fill_rect(state, x - scale, card_y - scale, scale * 2, row_gap * 4 + scale * 2, 0xffcc33);

    row_y = card_y + scale;
    row_x = x + scale * 4;
    row_w = width - row_x - x;
    kms_draw_text_fit(state, row_x, row_y, "[ KERNEL ] STOCK LINUX 4.14", 0xffffff, scale, row_w);
    row_y += row_gap;
    kms_draw_text_fit(state, row_x, row_y, "[ DISPLAY] KMS READY", 0xffffff, scale, row_w);
    row_y += row_gap;
    kms_draw_text_fit(state, row_x, row_y, "[ SERIAL ] USB ACM READY", 0xffffff, scale, row_w);
    row_y += row_gap;
    kms_draw_text_fit(state, row_x, row_y, "[ RUNTIME] HUD MENU LOADING", 0xffffff, scale, row_w);

    kms_draw_text_fit(state,
                      x,
                      height - footer_scale * 16,
                      "VOL KEYS OPEN MENU AFTER BOOT",
                      0xbbbbbb,
                      footer_scale,
                      card_w);
}

static void boot_auto_frame(void) {
    if (kms_begin_frame(0x000000) == 0) {
        kms_draw_boot_splash(&kms_state);
        if (kms_present_frame("bootframe") == 0) {
            klogf("<6>A90v77: boot splash applied\n");
            native_logf("boot", "display boot splash applied");
            timeline_record(0, 0, "display-splash", "boot splash applied");
        }
    } else {
        int saved_errno = errno;

        klogf("<6>A90v77: boot splash skipped (%d)\n", saved_errno);
        native_logf("boot", "display boot splash skipped errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "display-splash",
                        "boot splash skipped: %s",
                        strerror(saved_errno));
    }
}

static bool test_key_bit(const char *bitmap, unsigned int code) {
    char copy[1024];
    char *tokens[32];
    char *token;
    char *saveptr = NULL;
    unsigned int bits_per_word = 64;
    unsigned int token_count = 0;
    unsigned int word_index;

    if (strlen(bitmap) >= sizeof(copy)) {
        return false;
    }

    strcpy(copy, bitmap);
    trim_newline(copy);

    for (token = strtok_r(copy, " \t", &saveptr);
         token != NULL;
         token = strtok_r(NULL, " \t", &saveptr)) {
        if (token_count >= (sizeof(tokens) / sizeof(tokens[0]))) {
            return false;
        }
        tokens[token_count++] = token;
    }

    for (word_index = 0; word_index < token_count; ++word_index) {
        unsigned long value = strtoul(tokens[token_count - 1 - word_index], NULL, 16);
        unsigned int bit_base = word_index * bits_per_word;

        if (code >= bit_base && code < bit_base + bits_per_word) {
            unsigned int bit = code - bit_base;
            return ((value >> bit) & 1UL) != 0;
        }
    }

    return false;
}

static int cmd_inputcaps(char **argv, int argc) {
    char event_name[32];
    char key_path[PATH_MAX];
    char bitmap[1024];

    if (argc < 2) {
        cprintf("usage: inputcaps <eventX>\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        cprintf("inputcaps: invalid event name\r\n");
        return -EINVAL;
    }

    if (snprintf(key_path, sizeof(key_path),
                 "/sys/class/input/%s/device/capabilities/key", event_name) >=
        (int)sizeof(key_path)) {
        cprintf("inputcaps: path too long\r\n");
        return -ENAMETOOLONG;
    }

    if (read_text_file(key_path, bitmap, sizeof(bitmap)) < 0) {
        cprintf("inputcaps: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    trim_newline(bitmap);
    cprintf("%s key-bitmap=%s\r\n", event_name, bitmap);
    cprintf("  KEY_VOLUMEDOWN(114)=%s\r\n",
            test_key_bit(bitmap, KEY_VOLUMEDOWN) ? "yes" : "no");
    cprintf("  KEY_VOLUMEUP(115)=%s\r\n",
            test_key_bit(bitmap, KEY_VOLUMEUP) ? "yes" : "no");
    cprintf("  KEY_POWER(116)=%s\r\n",
            test_key_bit(bitmap, KEY_POWER) ? "yes" : "no");
    return 0;
}

static int cmd_readinput(char **argv, int argc) {
    char event_name[32];
    char dev_path[PATH_MAX];
    int count = 16;
    int fd;
    int index;

    if (argc < 2) {
        cprintf("usage: readinput <eventX> [count]\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        cprintf("readinput: invalid event name\r\n");
        return -EINVAL;
    }

    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        cprintf("readinput: invalid count\r\n");
        return -EINVAL;
    }
    if (count <= 0) {
        count = 1;
    }

    if (get_input_event_path(event_name, dev_path, sizeof(dev_path)) < 0) {
        cprintf("readinput: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    fd = open(dev_path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        cprintf("readinput: open %s: %s\r\n", dev_path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    cprintf("readinput: waiting on %s (%d events), q/Ctrl-C cancels\r\n",
            dev_path, count);

    index = 0;
    while (index < count) {
        struct pollfd fds[2];
        int poll_rc;

        fds[0].fd = fd;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = STDIN_FILENO;
        fds[1].events = POLLIN;
        fds[1].revents = 0;

        poll_rc = poll(fds, 2, -1);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            cprintf("readinput: poll: %s\r\n", strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }

        if ((fds[1].revents & POLLIN) != 0) {
            enum cancel_kind cancel = read_console_cancel_event();

            if (cancel != CANCEL_NONE) {
                close(fd);
                return command_cancelled("readinput", cancel);
            }
        }

        if ((fds[0].revents & POLLIN) == 0) {
            continue;
        }

        while (index < count) {
            struct input_event event;
            ssize_t rd = read(fd, &event, sizeof(event));

            if (rd < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK) {
                    break;
                }
                cprintf("readinput: read: %s\r\n", strerror(errno));
                close(fd);
                return negative_errno_or(EIO);
            }
            if (rd != (ssize_t)sizeof(event)) {
                cprintf("readinput: short read %ld\r\n", (long)rd);
                close(fd);
                return -EIO;
            }

            cprintf("event %d: type=0x%04x code=0x%04x value=%d\r\n",
                    index,
                    event.type,
                    event.code,
                    event.value);
            ++index;
        }
        if ((fds[0].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
            cprintf("readinput: poll error revents=0x%x\r\n", fds[0].revents);
            close(fd);
            return -EIO;
        }
    }

    close(fd);
    return 0;
}

static const char *key_name(unsigned int code) {
    switch (code) {
        case KEY_POWER:
            return "POWER";
        case KEY_VOLUMEUP:
            return "VOLUP";
        case KEY_VOLUMEDOWN:
            return "VOLDOWN";
        default:
            return NULL;
    }
}

#define INPUT_BUTTON_VOLUP   0x01u
#define INPUT_BUTTON_VOLDOWN 0x02u
#define INPUT_BUTTON_POWER   0x04u
#define INPUT_DOUBLE_CLICK_MS 350L
#define INPUT_LONG_PRESS_MS 800L
#define INPUT_PAGE_STEP 5

enum input_gesture_id {
    INPUT_GESTURE_NONE = 0,
    INPUT_GESTURE_VOLUP_CLICK,
    INPUT_GESTURE_VOLDOWN_CLICK,
    INPUT_GESTURE_POWER_CLICK,
    INPUT_GESTURE_VOLUP_DOUBLE,
    INPUT_GESTURE_VOLDOWN_DOUBLE,
    INPUT_GESTURE_POWER_DOUBLE,
    INPUT_GESTURE_VOLUP_LONG,
    INPUT_GESTURE_VOLDOWN_LONG,
    INPUT_GESTURE_POWER_LONG,
    INPUT_GESTURE_VOLUP_VOLDOWN,
    INPUT_GESTURE_VOLUP_POWER,
    INPUT_GESTURE_VOLDOWN_POWER,
    INPUT_GESTURE_ALL_BUTTONS,
};

enum input_menu_action {
    INPUT_MENU_ACTION_NONE = 0,
    INPUT_MENU_ACTION_PREV,
    INPUT_MENU_ACTION_NEXT,
    INPUT_MENU_ACTION_SELECT,
    INPUT_MENU_ACTION_BACK,
    INPUT_MENU_ACTION_HIDE,
    INPUT_MENU_ACTION_PAGE_PREV,
    INPUT_MENU_ACTION_PAGE_NEXT,
    INPUT_MENU_ACTION_STATUS,
    INPUT_MENU_ACTION_LOG,
    INPUT_MENU_ACTION_RESERVED,
};

struct input_gesture {
    enum input_gesture_id id;
    unsigned int code;
    unsigned int mask;
    unsigned int clicks;
    long duration_ms;
};

static unsigned int input_button_mask_from_key(unsigned int code) {
    switch (code) {
    case KEY_VOLUMEUP:
        return INPUT_BUTTON_VOLUP;
    case KEY_VOLUMEDOWN:
        return INPUT_BUTTON_VOLDOWN;
    case KEY_POWER:
        return INPUT_BUTTON_POWER;
    default:
        return 0;
    }
}

static unsigned int input_button_count(unsigned int mask) {
    unsigned int count = 0;

    if ((mask & INPUT_BUTTON_VOLUP) != 0) {
        ++count;
    }
    if ((mask & INPUT_BUTTON_VOLDOWN) != 0) {
        ++count;
    }
    if ((mask & INPUT_BUTTON_POWER) != 0) {
        ++count;
    }
    return count;
}

static void input_mask_text(unsigned int mask, char *buf, size_t buf_size) {
    size_t used = 0;

    if (buf_size == 0) {
        return;
    }
    buf[0] = '\0';
    if ((mask & INPUT_BUTTON_VOLUP) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sVOLUP", used > 0 ? "+" : "");
    }
    if ((mask & INPUT_BUTTON_VOLDOWN) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sVOLDOWN", used > 0 ? "+" : "");
    }
    if ((mask & INPUT_BUTTON_POWER) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sPOWER", used > 0 ? "+" : "");
    }
    if (used == 0) {
        snprintf(buf, buf_size, "NONE");
    }
}

static const char *input_gesture_name(enum input_gesture_id id) {
    switch (id) {
    case INPUT_GESTURE_VOLUP_CLICK:
        return "VOLUP_CLICK";
    case INPUT_GESTURE_VOLDOWN_CLICK:
        return "VOLDOWN_CLICK";
    case INPUT_GESTURE_POWER_CLICK:
        return "POWER_CLICK";
    case INPUT_GESTURE_VOLUP_DOUBLE:
        return "VOLUP_DOUBLE";
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
        return "VOLDOWN_DOUBLE";
    case INPUT_GESTURE_POWER_DOUBLE:
        return "POWER_DOUBLE";
    case INPUT_GESTURE_VOLUP_LONG:
        return "VOLUP_LONG";
    case INPUT_GESTURE_VOLDOWN_LONG:
        return "VOLDOWN_LONG";
    case INPUT_GESTURE_POWER_LONG:
        return "POWER_LONG";
    case INPUT_GESTURE_VOLUP_VOLDOWN:
        return "VOLUP+VOLDOWN";
    case INPUT_GESTURE_VOLUP_POWER:
        return "VOLUP+POWER";
    case INPUT_GESTURE_VOLDOWN_POWER:
        return "VOLDOWN+POWER";
    case INPUT_GESTURE_ALL_BUTTONS:
        return "VOLUP+VOLDOWN+POWER";
    default:
        return "NONE";
    }
}

static enum input_gesture_id input_single_gesture(unsigned int code,
                                                  unsigned int clicks,
                                                  long duration_ms) {
    if (duration_ms >= INPUT_LONG_PRESS_MS) {
        switch (code) {
        case KEY_VOLUMEUP:
            return INPUT_GESTURE_VOLUP_LONG;
        case KEY_VOLUMEDOWN:
            return INPUT_GESTURE_VOLDOWN_LONG;
        case KEY_POWER:
            return INPUT_GESTURE_POWER_LONG;
        default:
            return INPUT_GESTURE_NONE;
        }
    }
    if (clicks >= 2) {
        switch (code) {
        case KEY_VOLUMEUP:
            return INPUT_GESTURE_VOLUP_DOUBLE;
        case KEY_VOLUMEDOWN:
            return INPUT_GESTURE_VOLDOWN_DOUBLE;
        case KEY_POWER:
            return INPUT_GESTURE_POWER_DOUBLE;
        default:
            return INPUT_GESTURE_NONE;
        }
    }
    switch (code) {
    case KEY_VOLUMEUP:
        return INPUT_GESTURE_VOLUP_CLICK;
    case KEY_VOLUMEDOWN:
        return INPUT_GESTURE_VOLDOWN_CLICK;
    case KEY_POWER:
        return INPUT_GESTURE_POWER_CLICK;
    default:
        return INPUT_GESTURE_NONE;
    }
}

static enum input_gesture_id input_combo_gesture(unsigned int mask) {
    switch (mask & (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER)) {
    case INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN:
        return INPUT_GESTURE_VOLUP_VOLDOWN;
    case INPUT_BUTTON_VOLUP | INPUT_BUTTON_POWER:
        return INPUT_GESTURE_VOLUP_POWER;
    case INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER:
        return INPUT_GESTURE_VOLDOWN_POWER;
    case INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER:
        return INPUT_GESTURE_ALL_BUTTONS;
    default:
        return INPUT_GESTURE_NONE;
    }
}

static void input_gesture_set(struct input_gesture *gesture,
                              enum input_gesture_id id,
                              unsigned int code,
                              unsigned int mask,
                              unsigned int clicks,
                              long duration_ms) {
    gesture->id = id;
    gesture->code = code;
    gesture->mask = mask;
    gesture->clicks = clicks;
    gesture->duration_ms = duration_ms;
}

struct input_decoder {
    unsigned int down_mask;
    unsigned int pressed_mask;
    unsigned int primary_code;
    unsigned int primary_mask;
    unsigned int pending_code;
    unsigned int pending_mask;
    long first_down_ms;
    long pending_up_ms;
    long pending_duration_ms;
    bool waiting_second;
    bool second_click;
};

static void input_decoder_init(struct input_decoder *decoder) {
    memset(decoder, 0, sizeof(*decoder));
}

static int input_decoder_timeout_ms(const struct input_decoder *decoder) {
    long elapsed_ms;
    long remaining_ms;

    if (!decoder->waiting_second) {
        return -1;
    }

    elapsed_ms = monotonic_millis() - decoder->pending_up_ms;
    if (elapsed_ms >= INPUT_DOUBLE_CLICK_MS) {
        return 0;
    }

    remaining_ms = INPUT_DOUBLE_CLICK_MS - elapsed_ms;
    if (remaining_ms > INT_MAX) {
        return INT_MAX;
    }
    return (int)remaining_ms;
}

static bool input_decoder_emit_pending_if_due(struct input_decoder *decoder,
                                              struct input_gesture *gesture) {
    long elapsed_ms;

    if (!decoder->waiting_second) {
        return false;
    }

    elapsed_ms = monotonic_millis() - decoder->pending_up_ms;
    if (elapsed_ms < INPUT_DOUBLE_CLICK_MS) {
        return false;
    }

    input_gesture_set(gesture,
                      input_single_gesture(decoder->pending_code,
                                           1,
                                           decoder->pending_duration_ms),
                      decoder->pending_code,
                      decoder->pending_mask,
                      1,
                      decoder->pending_duration_ms);
    decoder->waiting_second = false;
    return true;
}

static bool input_decoder_feed(struct input_decoder *decoder,
                               const struct input_event *event,
                               long now_ms,
                               struct input_gesture *gesture) {
    unsigned int mask;

    if (event->type != EV_KEY || event->value == 2) {
        return false;
    }

    mask = input_button_mask_from_key(event->code);
    if (mask == 0) {
        return false;
    }

    if (event->value == 1) {
        if (decoder->waiting_second) {
            if (mask == decoder->pending_mask &&
                decoder->down_mask == 0 &&
                now_ms - decoder->pending_up_ms <= INPUT_DOUBLE_CLICK_MS) {
                decoder->waiting_second = false;
                decoder->second_click = true;
                decoder->down_mask = mask;
                decoder->pressed_mask = mask;
                decoder->primary_code = event->code;
                decoder->primary_mask = mask;
                decoder->first_down_ms = now_ms;
            } else {
                input_gesture_set(gesture,
                                  input_single_gesture(decoder->pending_code,
                                                       1,
                                                       decoder->pending_duration_ms),
                                  decoder->pending_code,
                                  decoder->pending_mask,
                                  1,
                                  decoder->pending_duration_ms);
                decoder->waiting_second = false;
                return true;
            }
        } else if (decoder->down_mask == 0) {
            decoder->second_click = false;
            decoder->down_mask = mask;
            decoder->pressed_mask = mask;
            decoder->primary_code = event->code;
            decoder->primary_mask = mask;
            decoder->first_down_ms = now_ms;
        } else {
            decoder->down_mask |= mask;
            decoder->pressed_mask |= mask;
        }
    } else if (event->value == 0 && (decoder->down_mask & mask) != 0) {
        decoder->down_mask &= ~mask;
        if (decoder->down_mask == 0) {
            long duration_ms = now_ms - decoder->first_down_ms;
            unsigned int count = input_button_count(decoder->pressed_mask);

            if (count > 1) {
                input_gesture_set(gesture,
                                  input_combo_gesture(decoder->pressed_mask),
                                  decoder->primary_code,
                                  decoder->pressed_mask,
                                  1,
                                  duration_ms);
                decoder->pressed_mask = 0;
                return true;
            }
            if (decoder->second_click) {
                input_gesture_set(gesture,
                                  input_single_gesture(decoder->primary_code,
                                                       2,
                                                       duration_ms),
                                  decoder->primary_code,
                                  decoder->primary_mask,
                                  2,
                                  duration_ms);
                decoder->pressed_mask = 0;
                decoder->second_click = false;
                return true;
            }
            if (duration_ms >= INPUT_LONG_PRESS_MS) {
                input_gesture_set(gesture,
                                  input_single_gesture(decoder->primary_code,
                                                       1,
                                                       duration_ms),
                                  decoder->primary_code,
                                  decoder->primary_mask,
                                  1,
                                  duration_ms);
                decoder->pressed_mask = 0;
                return true;
            }
            decoder->waiting_second = true;
            decoder->pending_code = decoder->primary_code;
            decoder->pending_mask = decoder->primary_mask;
            decoder->pending_up_ms = now_ms;
            decoder->pending_duration_ms = duration_ms;
        }
    }

    return false;
}

static enum input_menu_action input_menu_action_from_gesture(
        const struct input_gesture *gesture) {
    switch (gesture->id) {
    case INPUT_GESTURE_VOLUP_CLICK:
        return INPUT_MENU_ACTION_PREV;
    case INPUT_GESTURE_VOLDOWN_CLICK:
        return INPUT_MENU_ACTION_NEXT;
    case INPUT_GESTURE_POWER_CLICK:
        return INPUT_MENU_ACTION_SELECT;
    case INPUT_GESTURE_VOLUP_DOUBLE:
    case INPUT_GESTURE_VOLUP_LONG:
        return INPUT_MENU_ACTION_PAGE_PREV;
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
    case INPUT_GESTURE_VOLDOWN_LONG:
        return INPUT_MENU_ACTION_PAGE_NEXT;
    case INPUT_GESTURE_POWER_DOUBLE:
    case INPUT_GESTURE_VOLUP_VOLDOWN:
        return INPUT_MENU_ACTION_BACK;
    case INPUT_GESTURE_ALL_BUTTONS:
        return INPUT_MENU_ACTION_HIDE;
    case INPUT_GESTURE_VOLUP_POWER:
        return INPUT_MENU_ACTION_STATUS;
    case INPUT_GESTURE_VOLDOWN_POWER:
        return INPUT_MENU_ACTION_LOG;
    case INPUT_GESTURE_POWER_LONG:
        return INPUT_MENU_ACTION_RESERVED;
    default:
        return INPUT_MENU_ACTION_NONE;
    }
}

static const char *input_menu_action_name(enum input_menu_action action) {
    switch (action) {
    case INPUT_MENU_ACTION_PREV:
        return "PREVIOUS";
    case INPUT_MENU_ACTION_NEXT:
        return "NEXT";
    case INPUT_MENU_ACTION_SELECT:
        return "SELECT";
    case INPUT_MENU_ACTION_BACK:
        return "BACK";
    case INPUT_MENU_ACTION_HIDE:
        return "HIDE/EXIT";
    case INPUT_MENU_ACTION_PAGE_PREV:
        return "PAGE UP";
    case INPUT_MENU_ACTION_PAGE_NEXT:
        return "PAGE DOWN";
    case INPUT_MENU_ACTION_STATUS:
        return "STATUS";
    case INPUT_MENU_ACTION_LOG:
        return "LOG";
    case INPUT_MENU_ACTION_RESERVED:
        return "RESERVED";
    default:
        return "NONE";
    }
}

static void print_input_layout(void) {
    cprintf("inputlayout: single click\r\n");
    cprintf("  VOLUP    -> previous item\r\n");
    cprintf("  VOLDOWN  -> next item\r\n");
    cprintf("  POWER    -> select\r\n");
    cprintf("inputlayout: double click / long press\r\n");
    cprintf("  VOLUP    -> page previous (%d items)\r\n", INPUT_PAGE_STEP);
    cprintf("  VOLDOWN  -> page next (%d items)\r\n", INPUT_PAGE_STEP);
    cprintf("  POWER x2 -> back\r\n");
    cprintf("  POWER long -> reserved/ignored for safety\r\n");
    cprintf("inputlayout: combos\r\n");
    cprintf("  VOLUP+VOLDOWN -> back\r\n");
    cprintf("  VOLUP+POWER   -> status shortcut\r\n");
    cprintf("  VOLDOWN+POWER -> log shortcut\r\n");
    cprintf("  all buttons   -> hide/exit menu\r\n");
    cprintf("timing: double=%ldms long=%ldms\r\n",
            INPUT_DOUBLE_CLICK_MS,
            INPUT_LONG_PRESS_MS);
}

static int wait_for_input_gesture(struct key_wait_context *ctx,
                                  const char *tag,
                                  struct input_gesture *gesture) {
    struct pollfd fds[3];
    struct input_decoder decoder;

    input_decoder_init(&decoder);

    fds[0].fd = ctx->fd0;
    fds[0].events = POLLIN;
    fds[1].fd = ctx->fd3;
    fds[1].events = POLLIN;
    fds[2].fd = STDIN_FILENO;
    fds[2].events = POLLIN;

    while (1) {
        int timeout_ms;
        int poll_rc;
        int index;

        if (input_decoder_emit_pending_if_due(&decoder, gesture)) {
            return 0;
        }
        timeout_ms = input_decoder_timeout_ms(&decoder);

        poll_rc = poll(fds, 3, timeout_ms);
        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            cprintf("%s: poll: %s\r\n", tag, strerror(saved_errno));
            return -saved_errno;
        }

        if (poll_rc == 0) {
            if (input_decoder_emit_pending_if_due(&decoder, gesture)) {
                return 0;
            }
            continue;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum cancel_kind cancel = read_console_cancel_event();

            if (cancel != CANCEL_NONE) {
                return command_cancelled(tag, cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if (fds[index].revents & POLLIN) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    long now_ms;

                    now_ms = monotonic_millis();
                    if (input_decoder_feed(&decoder, &event, now_ms, gesture)) {
                        return 0;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    cprintf("%s: read: %s\r\n", tag, strerror(saved_errno));
                    return -saved_errno;
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                cprintf("%s: poll error revents=0x%x\r\n", tag, fds[index].revents);
                return -EIO;
            }
        }
    }
}

static int cmd_recovery(void);

static int open_key_wait_context(struct key_wait_context *ctx, const char *tag) {
    char event0_path[PATH_MAX];
    char event3_path[PATH_MAX];

    ctx->fd0 = -1;
    ctx->fd3 = -1;

    if (get_input_event_path("event0", event0_path, sizeof(event0_path)) < 0 ||
        get_input_event_path("event3", event3_path, sizeof(event3_path)) < 0) {
        cprintf("%s: input node setup failed: %s\r\n", tag, strerror(errno));
        return -1;
    }

    ctx->fd0 = open(event0_path, O_RDONLY | O_NONBLOCK);
    if (ctx->fd0 < 0) {
        cprintf("%s: open %s: %s\r\n", tag, event0_path, strerror(errno));
        return -1;
    }

    ctx->fd3 = open(event3_path, O_RDONLY | O_NONBLOCK);
    if (ctx->fd3 < 0) {
        cprintf("%s: open %s: %s\r\n", tag, event3_path, strerror(errno));
        close(ctx->fd0);
        ctx->fd0 = -1;
        return -1;
    }

    return 0;
}

static void close_key_wait_context(struct key_wait_context *ctx) {
    if (ctx->fd0 >= 0) {
        close(ctx->fd0);
        ctx->fd0 = -1;
    }
    if (ctx->fd3 >= 0) {
        close(ctx->fd3);
        ctx->fd3 = -1;
    }
}

static int wait_for_key_press(struct key_wait_context *ctx,
                              const char *tag,
                              unsigned int *code_out) {
    struct pollfd fds[3];

    fds[0].fd = ctx->fd0;
    fds[0].events = POLLIN;
    fds[1].fd = ctx->fd3;
    fds[1].events = POLLIN;
    fds[2].fd = STDIN_FILENO;
    fds[2].events = POLLIN;

    while (1) {
        int poll_rc = poll(fds, 3, -1);
        int index;

        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            cprintf("%s: poll: %s\r\n", tag, strerror(saved_errno));
            return -saved_errno;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum cancel_kind cancel = read_console_cancel_event();

            if (cancel != CANCEL_NONE) {
                return command_cancelled(tag, cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if (fds[index].revents & POLLIN) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    if (event.type == EV_KEY && event.value == 1) {
                        *code_out = event.code;
                        return 0;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    cprintf("%s: read: %s\r\n", tag, strerror(saved_errno));
                    return -saved_errno;
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                cprintf("%s: poll error revents=0x%x\r\n", tag, fds[index].revents);
                return -EIO;
            }
        }
    }
}

static int cmd_waitkey(char **argv, int argc) {
    struct key_wait_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        cprintf("usage: waitkey [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (open_key_wait_context(&ctx, "waitkey") < 0) {
        return negative_errno_or(ENOENT);
    }

    cprintf("waitkey: waiting for %d key press(es), q/Ctrl-C cancels\r\n", target);

    while (seen < target) {
        unsigned int code = 0;
        const char *name;

        int wait_rc = wait_for_key_press(&ctx, "waitkey", &code);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            return wait_rc;
        }

        name = key_name(code);
        if (name != NULL) {
            cprintf("key %d: %s (0x%04x)\r\n", seen, name, code);
        } else {
            cprintf("key %d: code=0x%04x\r\n", seen, code);
        }
        ++seen;
    }

    close_key_wait_context(&ctx);
    return 0;
}

static int cmd_inputlayout(char **argv, int argc) {
    (void)argv;
    (void)argc;
    print_input_layout();
    return 0;
}

static int cmd_waitgesture(char **argv, int argc) {
    struct key_wait_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        cprintf("usage: waitgesture [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (open_key_wait_context(&ctx, "waitgesture") < 0) {
        return negative_errno_or(ENOENT);
    }

    cprintf("waitgesture: waiting for %d gesture(s), q/Ctrl-C cancels\r\n", target);
    cprintf("waitgesture: double=%ldms long=%ldms\r\n",
            INPUT_DOUBLE_CLICK_MS,
            INPUT_LONG_PRESS_MS);

    while (seen < target) {
        struct input_gesture gesture;
        char mask_text[64];
        int wait_rc = wait_for_input_gesture(&ctx, "waitgesture", &gesture);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            return wait_rc;
        }

        input_mask_text(gesture.mask, mask_text, sizeof(mask_text));
        cprintf("gesture %d: %s mask=%s clicks=%u duration=%ldms action=%d\r\n",
                seen,
                input_gesture_name(gesture.id),
                mask_text,
                gesture.clicks,
                gesture.duration_ms,
                (int)input_menu_action_from_gesture(&gesture));
        ++seen;
    }

    close_key_wait_context(&ctx);
    return 0;
}

#define INPUT_MONITOR_ROWS 9

struct input_monitor_raw_entry {
    char title[64];
    char detail[96];
    int value;
};

struct input_monitor_state {
    struct input_decoder decoder;
    struct input_monitor_raw_entry raw_entries[INPUT_MONITOR_ROWS];
    char gesture_title[80];
    char gesture_detail[128];
    char gesture_mask[64];
    enum input_gesture_id gesture_id;
    enum input_menu_action gesture_action;
    unsigned int gesture_clicks;
    long gesture_duration_ms;
    long gesture_gap_ms;
    long key_down_ms[3];
    long last_raw_ms;
    long last_gesture_ms;
    unsigned int raw_head;
    unsigned int raw_count;
    unsigned int event_count;
    unsigned int gesture_count;
    bool exit_requested;
};

static struct input_monitor_state auto_input_monitor;
static int draw_screen_input_monitor_state(const struct input_monitor_state *monitor);

static int input_monitor_key_index(unsigned int code) {
    switch (code) {
    case KEY_VOLUMEUP:
        return 0;
    case KEY_VOLUMEDOWN:
        return 1;
    case KEY_POWER:
        return 2;
    default:
        return -1;
    }
}

static const char *input_monitor_value_name(int value) {
    switch (value) {
    case 0:
        return "UP";
    case 1:
        return "DOWN";
    case 2:
        return "REPEAT";
    default:
        return "VALUE";
    }
}

static void input_monitor_reset_state(struct input_monitor_state *monitor) {
    input_decoder_init(&monitor->decoder);
    memset(monitor->raw_entries, 0, sizeof(monitor->raw_entries));
    memset(monitor->gesture_title, 0, sizeof(monitor->gesture_title));
    memset(monitor->gesture_detail, 0, sizeof(monitor->gesture_detail));
    memset(monitor->gesture_mask, 0, sizeof(monitor->gesture_mask));
    memset(monitor->key_down_ms, 0, sizeof(monitor->key_down_ms));
    snprintf(monitor->gesture_title, sizeof(monitor->gesture_title),
             "GESTURE waiting");
    snprintf(monitor->gesture_detail, sizeof(monitor->gesture_detail),
             "double=%ldms long=%ldms",
             INPUT_DOUBLE_CLICK_MS,
             INPUT_LONG_PRESS_MS);
    snprintf(monitor->gesture_mask, sizeof(monitor->gesture_mask), "NONE");
    monitor->gesture_id = INPUT_GESTURE_NONE;
    monitor->gesture_action = INPUT_MENU_ACTION_NONE;
    monitor->gesture_clicks = 0;
    monitor->gesture_duration_ms = 0;
    monitor->gesture_gap_ms = -1;
    monitor->last_raw_ms = 0;
    monitor->last_gesture_ms = 0;
    monitor->raw_head = 0;
    monitor->raw_count = 0;
    monitor->event_count = 0;
    monitor->gesture_count = 0;
    monitor->exit_requested = false;
}

static void input_monitor_push_raw(struct input_monitor_state *monitor,
                                   const char *serial_line,
                                   const char *title,
                                   const char *detail,
                                   int value,
                                   bool serial_echo) {
    size_t slot = monitor->raw_head % INPUT_MONITOR_ROWS;

    snprintf(monitor->raw_entries[slot].title,
             sizeof(monitor->raw_entries[slot].title),
             "%s", title);
    snprintf(monitor->raw_entries[slot].detail,
             sizeof(monitor->raw_entries[slot].detail),
             "%s", detail);
    monitor->raw_entries[slot].value = value;
    ++monitor->raw_head;
    if (monitor->raw_count < INPUT_MONITOR_ROWS) {
        ++monitor->raw_count;
    }

    native_logf("inputmonitor", "%s", serial_line);
    if (serial_echo) {
        cprintf("inputmonitor: %s\r\n", serial_line);
    }
}

static void input_monitor_emit_gesture(struct input_monitor_state *monitor,
                                       const struct input_gesture *gesture,
                                       bool serial_echo) {
    char mask_text[64];
    long now_ms = monotonic_millis();
    long gap_ms = monitor->last_gesture_ms > 0 ?
                  now_ms - monitor->last_gesture_ms : -1;

    input_mask_text(gesture->mask, mask_text, sizeof(mask_text));
    ++monitor->gesture_count;
    monitor->gesture_id = gesture->id;
    monitor->gesture_action = input_menu_action_from_gesture(gesture);
    monitor->gesture_clicks = gesture->clicks;
    monitor->gesture_duration_ms = gesture->duration_ms;
    monitor->gesture_gap_ms = gap_ms;
    snprintf(monitor->gesture_mask, sizeof(monitor->gesture_mask),
             "%s", mask_text);
    snprintf(monitor->gesture_title, sizeof(monitor->gesture_title),
             "G%03u %s",
             monitor->gesture_count,
             input_gesture_name(gesture->id));
    snprintf(monitor->gesture_detail, sizeof(monitor->gesture_detail),
             "mask=%s click=%u dur=%ldms gap=%ldms action=%s",
             mask_text,
             gesture->clicks,
             gesture->duration_ms,
             gap_ms,
             input_menu_action_name(monitor->gesture_action));
    monitor->last_gesture_ms = now_ms;

    native_logf("inputmonitor", "%s / %s",
                monitor->gesture_title,
                monitor->gesture_detail);
    if (serial_echo) {
        cprintf("inputmonitor: %s / %s\r\n",
                monitor->gesture_title,
                monitor->gesture_detail);
    }
}

static bool input_monitor_feed_state(struct input_monitor_state *monitor,
                                     const struct input_event *event,
                                     int source_index,
                                     bool serial_echo,
                                     bool exit_on_all_buttons) {
    struct input_gesture gesture;
    char serial_line[128];
    char title[64];
    char detail[96];
    char key_label[32];
    char hold_label[24];
    const char *name;
    long now_ms;
    long gap_ms;
    long hold_ms = -1;
    int key_index;

    if (event->type != EV_KEY) {
        return false;
    }

    key_index = input_monitor_key_index(event->code);
    name = key_name(event->code);
    if (name != NULL) {
        snprintf(key_label, sizeof(key_label), "%s", name);
    } else {
        snprintf(key_label, sizeof(key_label), "KEY%u", event->code);
    }

    now_ms = monotonic_millis();
    gap_ms = monitor->last_raw_ms > 0 ? now_ms - monitor->last_raw_ms : -1;
    monitor->last_raw_ms = now_ms;

    if (key_index >= 0) {
        if (event->value == 1) {
            monitor->key_down_ms[key_index] = now_ms;
        } else if (event->value == 0 && monitor->key_down_ms[key_index] > 0) {
            hold_ms = now_ms - monitor->key_down_ms[key_index];
            monitor->key_down_ms[key_index] = 0;
        } else if (event->value == 2 && monitor->key_down_ms[key_index] > 0) {
            hold_ms = now_ms - monitor->key_down_ms[key_index];
        }
    }

    if (hold_ms >= 0) {
        snprintf(hold_label, sizeof(hold_label), "%ldms", hold_ms);
    } else {
        snprintf(hold_label, sizeof(hold_label), "-");
    }

    ++monitor->event_count;
    snprintf(title, sizeof(title),
             "R%03u %-6s %-7s event%d",
             monitor->event_count,
             input_monitor_value_name(event->value),
             key_label,
             source_index == 0 ? 0 : 3);
    snprintf(detail, sizeof(detail),
             "gap=%ldms hold=%s code=0x%04x",
             gap_ms,
             hold_label,
             event->code);
    snprintf(serial_line, sizeof(serial_line),
             "R%03u event%d %-7s %-6s gap=%ldms hold=%s",
             monitor->event_count,
             source_index == 0 ? 0 : 3,
             key_label,
             input_monitor_value_name(event->value),
             gap_ms,
             hold_label);
    input_monitor_push_raw(monitor,
                           serial_line,
                           title,
                           detail,
                           event->value,
                           serial_echo);

    if (input_decoder_feed(&monitor->decoder, event, now_ms, &gesture)) {
        input_monitor_emit_gesture(monitor, &gesture, serial_echo);
        if (exit_on_all_buttons && gesture.id == INPUT_GESTURE_ALL_BUTTONS) {
            monitor->exit_requested = true;
        }
    }

    if (exit_on_all_buttons &&
        event->value == 1 &&
        (monitor->decoder.down_mask &
         (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER)) ==
        (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER)) {
        long duration_ms = now_ms - monitor->decoder.first_down_ms;

        if (duration_ms < 0) {
            duration_ms = 0;
        }
        input_gesture_set(&gesture,
                          INPUT_GESTURE_ALL_BUTTONS,
                          event->code,
                          INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER,
                          1,
                          duration_ms);
        input_monitor_emit_gesture(monitor, &gesture, serial_echo);
        monitor->exit_requested = true;
    }

    return monitor->exit_requested;
}

static void input_monitor_tick_state(struct input_monitor_state *monitor,
                                     bool serial_echo) {
    struct input_gesture gesture;

    if (input_decoder_emit_pending_if_due(&monitor->decoder, &gesture)) {
        input_monitor_emit_gesture(monitor, &gesture, serial_echo);
    }
}

static void input_monitor_app_reset(void) {
    input_monitor_reset_state(&auto_input_monitor);
    native_logf("inputmonitor", "app reset");
}

static void input_monitor_app_tick(void) {
    input_monitor_tick_state(&auto_input_monitor, false);
}

static bool input_monitor_app_feed_event(const struct input_event *event,
                                         int source_index) {
    return input_monitor_feed_state(&auto_input_monitor,
                                    event,
                                    source_index,
                                    false,
                                    true);
}

static int cmd_inputmonitor(char **argv, int argc) {
    struct input_monitor_state monitor;
    struct key_wait_context ctx;
    int target = 24;
    int seen = 0;
    int draw_rc;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        cprintf("usage: inputmonitor [events]\r\n");
        return -EINVAL;
    }
    if (target < 0) {
        target = 0;
    }

    reap_hud_child();
    stop_auto_hud(false);
    input_monitor_reset_state(&monitor);

    if (open_key_wait_context(&ctx, "inputmonitor") < 0) {
        restore_auto_hud_if_needed(true);
        return negative_errno_or(ENOENT);
    }

    cprintf("inputmonitor: raw DOWN/UP/REPEAT + gesture decode\r\n");
    cprintf("inputmonitor: events=%d, 0 means until all-buttons/q/Ctrl-C\r\n", target);
    cprintf("inputmonitor: all-buttons exits only in events=0 mode\r\n");

    draw_rc = draw_screen_input_monitor_state(&monitor);
    if (draw_rc < 0) {
        close_key_wait_context(&ctx);
        restore_auto_hud_if_needed(true);
        return draw_rc;
    }

    while (target == 0 || seen < target) {
        struct pollfd fds[3];
        int timeout_ms;
        int poll_rc;
        int index;

        input_monitor_tick_state(&monitor, true);
        draw_screen_input_monitor_state(&monitor);

        fds[0].fd = ctx.fd0;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = ctx.fd3;
        fds[1].events = POLLIN;
        fds[1].revents = 0;
        fds[2].fd = STDIN_FILENO;
        fds[2].events = POLLIN;
        fds[2].revents = 0;

        timeout_ms = input_decoder_timeout_ms(&monitor.decoder);
        poll_rc = poll(fds, 3, timeout_ms);
        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            cprintf("inputmonitor: poll: %s\r\n", strerror(saved_errno));
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(true);
            return -saved_errno;
        }

        if (poll_rc == 0) {
            continue;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum cancel_kind cancel = read_console_cancel_event();

            if (cancel != CANCEL_NONE) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(true);
                return command_cancelled("inputmonitor", cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if ((fds[index].revents & POLLIN) != 0) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    unsigned int before_count = monitor.event_count;

                    if (input_monitor_feed_state(&monitor,
                                                 &event,
                                                 index,
                                                 true,
                                                 target == 0)) {
                        draw_screen_input_monitor_state(&monitor);
                        close_key_wait_context(&ctx);
                        restore_auto_hud_if_needed(true);
                        return 0;
                    }
                    if (monitor.event_count > before_count) {
                        ++seen;
                    }
                    draw_screen_input_monitor_state(&monitor);
                    if (target > 0 && seen >= target) {
                        break;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    cprintf("inputmonitor: read: %s\r\n", strerror(saved_errno));
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(true);
                    return -saved_errno;
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                cprintf("inputmonitor: poll error revents=0x%x\r\n",
                        fds[index].revents);
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(true);
                return -EIO;
            }
        }
    }

    input_monitor_tick_state(&monitor, true);
    draw_screen_input_monitor_state(&monitor);
    close_key_wait_context(&ctx);
    restore_auto_hud_if_needed(true);
    return 0;
}

struct blind_menu_item {
    const char *name;
    const char *summary;
};

static void kms_draw_menu_section(struct kms_display_state *state,
                                  const struct screen_menu_page *page,
                                  size_t selected) {
    uint32_t scale = 5;
    uint32_t x = state->width / 24;
    uint32_t line_h = scale * 10;
    uint32_t card_h = line_h + scale * 4;
    uint32_t glyph_h = scale * 7;
    uint32_t slot = line_h + scale * 3;
    uint32_t card_w = state->width - x * 2;
    uint32_t menu_scale = scale;
    uint32_t y = state->height / 16;
    uint32_t status_bottom;
    uint32_t divider_y;
    uint32_t menu_y;
    uint32_t item_h = scale * 14;
    uint32_t item_gap = scale * 2;
    uint32_t log_tail_y;
    uint32_t page_scale;
    size_t i;

    if (y > glyph_h + glyph_h / 2 + scale * 2)
        y -= glyph_h + glyph_h / 2;

    status_bottom = y + 3 * slot + card_h;
    divider_y = status_bottom + scale * 5;
    menu_y = divider_y + scale * 17;

    kms_fill_rect(state, x, divider_y, card_w, 2, 0x383838);
    page_scale = shrink_text_scale(page->title, menu_scale, card_w / 2);
    kms_draw_text(state, x, divider_y + scale * 2,
                  page->title, 0xffcc33, page_scale);
    kms_draw_text(state, x, divider_y + scale * 10,
                  "VOL MOVE  PWR SELECT  COMBO BACK",
                  0x909090, menu_scale > 1 ? menu_scale - 1 : menu_scale);

    for (i = 0; i < page->count; ++i) {
        uint32_t iy = menu_y + (uint32_t)i * (item_h + item_gap);
        bool is_sel = (i == selected);
        uint32_t fill = is_sel ? 0x1a3560 : 0x141414;
        uint32_t name_color = is_sel ? 0xffffff : 0x707070;

        kms_fill_rect(state, x - scale, iy - scale, card_w, item_h, fill);
        if (is_sel)
            kms_fill_rect(state, x - scale, iy - scale, scale * 2, item_h, 0xffcc33);
        kms_draw_text(state, x + scale * 3, iy + (item_h - glyph_h) / 2,
                      page->items[i].name, name_color, menu_scale);
    }

    {
        uint32_t last_y = menu_y + (uint32_t)page->count * (item_h + item_gap);
        uint32_t summary_y = last_y + scale * 6;
        const char *summary = page->items[selected].summary;

        log_tail_y = summary_y;

        if (summary_y + glyph_h < state->height && summary != NULL && summary[0] != '\0') {
            kms_fill_rect(state, x, summary_y - scale, card_w, 1, 0x282828);
            kms_draw_text(state, x, summary_y + scale * 2,
                          summary, 0xffcc33,
                          shrink_text_scale(summary, menu_scale, card_w));
            log_tail_y = summary_y + glyph_h + scale * 8;
        }
    }

    kms_draw_log_tail_panel(state,
                            x,
                            log_tail_y,
                            card_w,
                            state->height - scale * 42,
                            16,
                            "LIVE LOG TAIL",
                            menu_scale > 3 ? menu_scale - 3 : menu_scale);
}

static int kms_read_log_tail(char lines[KMS_LOG_TAIL_MAX_LINES][KMS_LOG_TAIL_LINE_MAX],
                             int max_lines) {
    char ring[KMS_LOG_TAIL_MAX_LINES][KMS_LOG_TAIL_LINE_MAX];
    int index = 0;
    int count;
    int start;
    int i;
    FILE *fp;

    if (max_lines <= 0) {
        return 0;
    }
    if (max_lines > KMS_LOG_TAIL_MAX_LINES) {
        max_lines = KMS_LOG_TAIL_MAX_LINES;
    }

    fp = fopen(native_log_current_path(), "r");
    if (fp == NULL) {
        return 0;
    }

    while (fgets(ring[index % max_lines], KMS_LOG_TAIL_LINE_MAX, fp) != NULL) {
        size_t len = strlen(ring[index % max_lines]);

        while (len > 0 &&
               (ring[index % max_lines][len - 1] == '\n' ||
                ring[index % max_lines][len - 1] == '\r')) {
            ring[index % max_lines][--len] = '\0';
        }
        if (len == 0) {
            continue;
        }
        ++index;
    }
    fclose(fp);

    count = index < max_lines ? index : max_lines;
    start = index >= max_lines ? index % max_lines : 0;
    for (i = 0; i < count; ++i) {
        snprintf(lines[i], KMS_LOG_TAIL_LINE_MAX, "%s",
                 ring[(start + i) % max_lines]);
    }
    return count;
}

static uint32_t kms_log_tail_line_color(const char *line) {
    if (strstr(line, "failed") != NULL ||
        strstr(line, " rc=-") != NULL ||
        strstr(line, " error=") != NULL) {
        return 0xff7777;
    }
    if (strstr(line, "cancel") != NULL ||
        strstr(line, "ignored") != NULL ||
        strstr(line, "busy") != NULL) {
        return 0xffcc33;
    }
    if (strstr(line, "input") != NULL ||
        strstr(line, "screenmenu") != NULL) {
        return 0x66ddff;
    }
    if (strstr(line, "boot") != NULL ||
        strstr(line, "timeline") != NULL) {
        return 0x88ee88;
    }
    return 0x808080;
}

static void kms_log_tail_next_chunk(const char *line,
                                    size_t offset,
                                    size_t max_chars,
                                    char *out,
                                    size_t out_size,
                                    size_t *next_offset) {
    size_t len = strlen(line + offset);
    size_t chunk_len;
    size_t split;

    if (out_size == 0) {
        *next_offset = offset;
        return;
    }
    if (max_chars == 0) {
        out[0] = '\0';
        *next_offset = offset;
        return;
    }

    if (len <= max_chars) {
        snprintf(out, out_size, "%s", line + offset);
        *next_offset = offset + len;
        return;
    }

    chunk_len = max_chars;
    split = chunk_len;
    while (split > 8 && line[offset + split] != ' ' && line[offset + split] != '\t') {
        --split;
    }
    if (split > 8) {
        chunk_len = split;
    }
    if (chunk_len >= out_size) {
        chunk_len = out_size - 1;
    }

    memcpy(out, line + offset, chunk_len);
    out[chunk_len] = '\0';
    offset += chunk_len;
    while (line[offset] == ' ' || line[offset] == '\t') {
        ++offset;
    }
    *next_offset = offset;
}

static int kms_log_tail_wrap_count(const char *line, size_t max_chars) {
    size_t offset = 0;
    int count = 0;

    if (max_chars == 0 || line[0] == '\0') {
        return 0;
    }
    while (line[offset] != '\0' && count < 16) {
        char chunk[KMS_LOG_TAIL_LINE_MAX];
        size_t next_offset;

        kms_log_tail_next_chunk(line,
                                offset,
                                max_chars,
                                chunk,
                                sizeof(chunk),
                                &next_offset);
        if (next_offset <= offset) {
            break;
        }
        offset = next_offset;
        ++count;
    }
    return count;
}

static void kms_draw_log_tail_panel(struct kms_display_state *state,
                                    uint32_t x,
                                    uint32_t y,
                                    uint32_t width,
                                    uint32_t bottom,
                                    int max_lines,
                                    const char *title,
                                    uint32_t scale) {
    char lines[KMS_LOG_TAIL_MAX_LINES][KMS_LOG_TAIL_LINE_MAX];
    uint32_t line_h;
    uint32_t title_h;
    uint32_t title_gap;
    uint32_t panel_h;
    uint32_t available;
    uint32_t text_width;
    size_t max_chars;
    int total;
    int row_budget;
    int visual_rows = 0;
    int start;
    int i;

    if (scale < 1) {
        scale = 1;
    }
    if (max_lines > KMS_LOG_TAIL_MAX_LINES) {
        max_lines = KMS_LOG_TAIL_MAX_LINES;
    }
    if (bottom <= y || width <= scale * 4) {
        return;
    }

    line_h = scale * 9;
    title_h = scale * 10;
    title_gap = scale * 3;
    text_width = width - scale * 2;
    max_chars = text_width / (scale * 6);
    if (max_chars < 8) {
        return;
    }
    if (max_chars >= KMS_LOG_TAIL_LINE_MAX) {
        max_chars = KMS_LOG_TAIL_LINE_MAX - 1;
    }
    available = bottom - y;
    if (available <= title_h + title_gap + scale * 4) {
        return;
    }

    row_budget = (int)((available - title_h - title_gap - scale * 4) / (line_h + 2));
    if (row_budget <= 0) {
        return;
    }

    total = kms_read_log_tail(lines, max_lines);
    if (total <= 0) {
        return;
    }

    start = total;
    while (start > 0) {
        int rows = kms_log_tail_wrap_count(lines[start - 1], max_chars);

        if (rows <= 0) {
            rows = 1;
        }
        if (visual_rows > 0 && visual_rows + rows > row_budget) {
            break;
        }
        if (visual_rows == 0 && rows > row_budget) {
            visual_rows = row_budget;
            --start;
            break;
        }
        visual_rows += rows;
        --start;
    }
    if (visual_rows <= 0) {
        return;
    }

    panel_h = title_h + title_gap + (uint32_t)visual_rows * (line_h + 2) + scale * 2;

    kms_fill_rect(state, x - scale, y - scale, width, panel_h, 0x080808);
    kms_fill_rect(state, x, y, width - scale * 2, 1, 0x303030);
    kms_draw_text(state, x, y + scale * 2, title, 0xffcc33,
                  shrink_text_scale(title, scale, width - scale * 2));
    y += title_h + title_gap;

    visual_rows = 0;
    for (i = start; i < total && visual_rows < row_budget; ++i) {
        const char *line = lines[i];
        size_t offset = 0;
        uint32_t color = kms_log_tail_line_color(line);

        while (line[offset] != '\0' && visual_rows < row_budget) {
            char chunk[KMS_LOG_TAIL_LINE_MAX];
            size_t next_offset;
            uint32_t row_y = y + (uint32_t)visual_rows * (line_h + 2);

            kms_log_tail_next_chunk(line,
                                    offset,
                                    max_chars,
                                    chunk,
                                    sizeof(chunk),
                                    &next_offset);
            kms_draw_text(state, x, row_y, chunk, color, scale);
            offset = next_offset;
            ++visual_rows;
        }
    }
}

static void kms_draw_hud_log_tail(struct kms_display_state *state) {
    uint32_t scale = 3;
    uint32_t hud_scale = 5;
    uint32_t slot = (hud_scale * 10) + hud_scale * 3;
    uint32_t card_h = (hud_scale * 10) + hud_scale * 4;
    uint32_t glyph_h = hud_scale * 7;
    uint32_t x = state->width / 24;
    uint32_t card_w = state->width - x * 2;
    uint32_t y = state->height / 16;
    uint32_t area_y;

    if (y > glyph_h + glyph_h / 2 + hud_scale * 2)
        y -= glyph_h + glyph_h / 2;
    area_y = y + 3 * slot + card_h + hud_scale * 8;

    kms_draw_log_tail_panel(state,
                            x,
                            area_y,
                            card_w,
                            state->height - hud_scale * 16,
                            24,
                            "LOG TAIL",
                            scale);
}

static void print_blind_menu_selection(const struct blind_menu_item *items,
                                       size_t count,
                                       size_t selected) {
    cprintf("blindmenu: [%d/%d] %s - %s\r\n",
            (int)(selected + 1),
            (int)count,
            items[selected].name,
            items[selected].summary);
}

static void print_screen_menu_selection(const struct screen_menu_page *page,
                                        size_t selected) {
    cprintf("screenmenu: %s [%d/%d] %s - %s\r\n",
            page->title,
            (int)(selected + 1),
            (int)page->count,
            page->items[selected].name,
            page->items[selected].summary);
}

static uint32_t menu_text_scale(void) {
    if (kms_state.width >= 1080) {
        return 6;
    }
    if (kms_state.width >= 720) {
        return 4;
    }
    return 3;
}

static uint32_t about_text_scale(void) {
    if (kms_state.width >= 1080) {
        return 4;
    }
    if (kms_state.width >= 720) {
        return 3;
    }
    return 2;
}

static uint32_t shrink_text_scale(const char *text,
                                  uint32_t scale,
                                  uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int draw_screen_menu(const struct screen_menu_page *page,
                            size_t selected) {
    uint32_t scale;
    uint32_t title_scale;
    uint32_t footer_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t item_h;
    uint32_t gap;
    uint32_t title_y;
    uint32_t list_y;
    uint32_t index;
    const char *footer = "VOL MOVE PWR SEL DBL/COMBO BACK";

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = menu_text_scale();
    if (page->count > 15 && scale > 3) {
        scale = 3;
    } else if (page->count > 10 && scale > 4) {
        scale = 4;
    }
    title_scale = scale + 1;
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 10;
    card_w = kms_state.width - (x * 2);
    item_h = scale * 17;
    gap = scale * 2;
    title_y = y;
    list_y = title_y + (title_scale * 9) + (scale * 5);

    kms_draw_text(&kms_state, x, title_y, page->title, 0xffcc33,
                  shrink_text_scale(page->title, title_scale, card_w));
    kms_draw_text(&kms_state, x, title_y + title_scale * 9,
                  "BUTTON ONLY CONTROL / BACK AT BOTTOM", 0xdddddd,
                  shrink_text_scale("BUTTON ONLY CONTROL / BACK AT BOTTOM", scale, card_w));

    for (index = 0; index < page->count; ++index) {
        uint32_t item_y = list_y + index * (item_h + gap);
        uint32_t fill = (index == selected) ? 0x204080 : 0x202020;
        uint32_t name_color = (index == selected) ? 0xffffff : 0xd0d0d0;
        uint32_t summary_color = (index == selected) ? 0xffcc33 : 0x909090;

        kms_fill_rect(&kms_state, x - scale, item_y - scale, card_w, item_h, fill);
        if (index == selected) {
            kms_fill_rect(&kms_state, x - scale, item_y - scale, scale * 2, item_h, 0xffcc33);
        }
        kms_draw_text(&kms_state, x + scale * 3, item_y + scale,
                      page->items[index].name, name_color, scale);
        kms_draw_text(&kms_state, x + scale * 3, item_y + scale * 9,
                      page->items[index].summary, summary_color, scale > 1 ? scale - 1 : scale);
    }

    footer_scale = shrink_text_scale(footer, scale, card_w);
    kms_draw_log_tail_panel(&kms_state,
                            x,
                            list_y + (uint32_t)page->count * (item_h + gap) + scale * 4,
                            card_w,
                            kms_state.height - footer_scale * 16,
                            12,
                            "LIVE LOG TAIL",
                            scale > 3 ? scale - 3 : (scale > 2 ? scale - 1 : scale));
    kms_draw_text(&kms_state, x, kms_state.height - footer_scale * 12,
                  footer, 0xffffff, footer_scale);

    if (kms_present_frame("screenmenu") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_log_summary(void) {
    char boot_summary[64];
    char line1[96];
    char line2[96];
    char line3[96];
    char line4[96];
    uint32_t scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    timeline_boot_summary(boot_summary, sizeof(boot_summary));
    snprintf(line1, sizeof(line1), "BOOT %.40s", boot_summary);
    snprintf(line2, sizeof(line2), "LOG %s", native_log_ready ? "READY" : "NOT READY");
    snprintf(line3, sizeof(line3), "LAST %.24s RC %d E %d",
             last_result.command,
             last_result.code,
             last_result.saved_errno);
    snprintf(line4, sizeof(line4), "PATH %.48s", native_log_current_path());

    scale = menu_text_scale();
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 8;
    card_w = kms_state.width - (x * 2);
    line_h = scale * 12;

    kms_draw_text(&kms_state, x, y, "A90 LOG SUMMARY", 0xffcc33, scale + 1);
    y += line_h + scale * 4;

    kms_fill_rect(&kms_state, x - scale, y - scale, card_w, line_h * 5, 0x202020);
    kms_draw_text(&kms_state, x, y, line1, 0xffffff,
                  shrink_text_scale(line1, scale, card_w - scale * 2));
    y += line_h;
    kms_draw_text(&kms_state, x, y, line2, 0xffffff,
                  shrink_text_scale(line2, scale, card_w - scale * 2));
    y += line_h;
    kms_draw_text(&kms_state, x, y, line3, 0xffffff,
                  shrink_text_scale(line3, scale, card_w - scale * 2));
    y += line_h;
    kms_draw_text(&kms_state, x, y, line4, 0xffffff,
                  shrink_text_scale(line4, scale, card_w - scale * 2));

    kms_draw_text(&kms_state, x, kms_state.height - scale * 12,
                  "PRESS ANY BUTTON TO RETURN", 0xffffff,
                  shrink_text_scale("PRESS ANY BUTTON TO RETURN", scale, card_w));

    if (kms_present_frame("screenlog") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static const struct input_monitor_raw_entry *input_monitor_raw_entry_at(
        const struct input_monitor_state *monitor,
        size_t reverse_index) {
    size_t slot;

    if (reverse_index >= monitor->raw_count || monitor->raw_head == 0) {
        return NULL;
    }

    slot = (monitor->raw_head + INPUT_MONITOR_ROWS - 1 - reverse_index) %
           INPUT_MONITOR_ROWS;
    return &monitor->raw_entries[slot];
}

static uint32_t input_monitor_value_color(int value) {
    switch (value) {
    case 1:
        return 0x88ee88;
    case 0:
        return 0xffcc33;
    case 2:
        return 0x66ddff;
    default:
        return 0xff7777;
    }
}

static const char *input_monitor_gesture_class(enum input_gesture_id id) {
    switch (id) {
    case INPUT_GESTURE_VOLUP_CLICK:
    case INPUT_GESTURE_VOLDOWN_CLICK:
    case INPUT_GESTURE_POWER_CLICK:
        return "SINGLE CLICK";
    case INPUT_GESTURE_VOLUP_DOUBLE:
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
    case INPUT_GESTURE_POWER_DOUBLE:
        return "DOUBLE CLICK";
    case INPUT_GESTURE_VOLUP_LONG:
    case INPUT_GESTURE_VOLDOWN_LONG:
    case INPUT_GESTURE_POWER_LONG:
        return "LONG HOLD";
    case INPUT_GESTURE_VOLUP_VOLDOWN:
    case INPUT_GESTURE_VOLUP_POWER:
    case INPUT_GESTURE_VOLDOWN_POWER:
    case INPUT_GESTURE_ALL_BUTTONS:
        return "COMBO INPUT";
    case INPUT_GESTURE_NONE:
        return "WAITING";
    default:
        return "UNKNOWN";
    }
}

static uint32_t input_monitor_gesture_color(enum input_gesture_id id) {
    switch (id) {
    case INPUT_GESTURE_VOLUP_CLICK:
    case INPUT_GESTURE_VOLDOWN_CLICK:
    case INPUT_GESTURE_POWER_CLICK:
        return 0x88ee88;
    case INPUT_GESTURE_VOLUP_DOUBLE:
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
    case INPUT_GESTURE_POWER_DOUBLE:
        return 0xffcc33;
    case INPUT_GESTURE_VOLUP_LONG:
    case INPUT_GESTURE_VOLDOWN_LONG:
    case INPUT_GESTURE_POWER_LONG:
        return 0xff8844;
    case INPUT_GESTURE_VOLUP_VOLDOWN:
    case INPUT_GESTURE_VOLUP_POWER:
    case INPUT_GESTURE_VOLDOWN_POWER:
    case INPUT_GESTURE_ALL_BUTTONS:
        return 0x66ddff;
    case INPUT_GESTURE_NONE:
        return 0x808080;
    default:
        return 0xff7777;
    }
}

static uint32_t input_monitor_action_color(enum input_menu_action action) {
    switch (action) {
    case INPUT_MENU_ACTION_SELECT:
        return 0x88ee88;
    case INPUT_MENU_ACTION_BACK:
    case INPUT_MENU_ACTION_HIDE:
        return 0xffcc33;
    case INPUT_MENU_ACTION_PAGE_PREV:
    case INPUT_MENU_ACTION_PAGE_NEXT:
    case INPUT_MENU_ACTION_PREV:
    case INPUT_MENU_ACTION_NEXT:
        return 0x66ddff;
    case INPUT_MENU_ACTION_RESERVED:
        return 0xff7777;
    default:
        return 0xffffff;
    }
}

static int draw_screen_input_monitor_state(const struct input_monitor_state *monitor) {
    char summary[96];
    char timing[96];
    char buttons_line[96];
    char action_line[96];
    char metric_line[96];
    uint32_t scale;
    uint32_t title_scale;
    uint32_t big_scale;
    uint32_t left;
    uint32_t top;
    uint32_t content_width;
    uint32_t line_height;
    uint32_t row_gap;
    uint32_t row_height;
    uint32_t card_height;
    uint32_t panel_height;
    uint32_t panel_top;
    uint32_t panel_mid;
    uint32_t half_width;
    uint32_t class_color;
    uint32_t action_color;
    size_t index;

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    if (scale > 3) {
        scale = 3;
    }
    title_scale = scale + 1;
    big_scale = scale * 3;
    left = kms_state.width / 18;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = kms_state.height / 12;
    content_width = kms_state.width - (left * 2);
    line_height = scale * 10;
    row_gap = scale * 3;
    row_height = line_height * 2 + row_gap;
    panel_height = line_height * 9;
    card_height = panel_height + line_height +
                  (uint32_t)INPUT_MONITOR_ROWS * row_height +
                  scale * 4;

    snprintf(summary, sizeof(summary), "RAW %u  GESTURE %u",
             monitor->event_count,
             monitor->gesture_count);
    snprintf(timing, sizeof(timing), "DOWN/UP GAP HOLD / DBL %ld LONG %ld",
             INPUT_DOUBLE_CLICK_MS,
             INPUT_LONG_PRESS_MS);
    snprintf(buttons_line, sizeof(buttons_line), "BUTTONS  %s",
             monitor->gesture_mask);
    snprintf(action_line, sizeof(action_line), "ACTION   %s",
             input_menu_action_name(monitor->gesture_action));
    snprintf(metric_line, sizeof(metric_line),
             "click=%u  duration=%ldms  gap=%ldms",
             monitor->gesture_clicks,
             monitor->gesture_duration_ms,
             monitor->gesture_gap_ms);

    kms_draw_text(&kms_state, left, top, "TOOLS / INPUT MONITOR", 0xffcc33,
                  shrink_text_scale("TOOLS / INPUT MONITOR",
                                    title_scale,
                                    content_width));
    top += line_height;
    kms_draw_text(&kms_state, left, top, summary, 0x88ee88,
                  shrink_text_scale(summary, scale, content_width));
    top += line_height;
    kms_draw_text(&kms_state, left, top, timing, 0xdddddd,
                  shrink_text_scale(timing, scale, content_width));
    top += line_height + scale * 2;

    kms_fill_rect(&kms_state,
                  left - scale,
                  top - scale,
                  content_width,
                  card_height,
                  0x202020);

    panel_top = top;
    half_width = (content_width - scale * 4) / 2;
    class_color = input_monitor_gesture_color(monitor->gesture_id);
    action_color = input_monitor_action_color(monitor->gesture_action);

    kms_fill_rect(&kms_state,
                  left,
                  panel_top,
                  content_width - scale * 2,
                  panel_height,
                  0x101820);
    kms_fill_rect(&kms_state,
                  left,
                  panel_top,
                  scale * 3,
                  panel_height,
                  class_color);

    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + scale * 4,
                  "DECODED INPUT LAYER",
                  0x909090,
                  scale);
    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + line_height + scale * 4,
                  input_monitor_gesture_class(monitor->gesture_id),
                  class_color,
                  shrink_text_scale(input_monitor_gesture_class(monitor->gesture_id),
                                    big_scale,
                                    content_width - scale * 10));
    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + line_height * 4,
                  monitor->gesture_title,
                  0xffffff,
                  shrink_text_scale(monitor->gesture_title,
                                    scale,
                                    content_width - scale * 10));

    panel_mid = panel_top + line_height * 5 + scale * 4;
    kms_fill_rect(&kms_state,
                  left + scale * 5,
                  panel_mid,
                  half_width - scale * 2,
                  line_height * 2,
                  0x182030);
    kms_fill_rect(&kms_state,
                  left + half_width + scale * 3,
                  panel_mid,
                  half_width - scale * 2,
                  line_height * 2,
                  0x182030);
    kms_draw_text(&kms_state,
                  left + scale * 7,
                  panel_mid + scale * 3,
                  buttons_line,
                  0x66ddff,
                  shrink_text_scale(buttons_line,
                                    scale,
                                    half_width - scale * 6));
    kms_draw_text(&kms_state,
                  left + half_width + scale * 5,
                  panel_mid + scale * 3,
                  action_line,
                  action_color,
                  shrink_text_scale(action_line,
                                    scale,
                                    half_width - scale * 6));
    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + panel_height - line_height - scale * 3,
                  metric_line,
                  0xdddddd,
                  shrink_text_scale(metric_line,
                                    scale,
                                    content_width - scale * 10));

    top = panel_top + panel_height + line_height;

    for (index = 0; index < INPUT_MONITOR_ROWS; ++index) {
        const struct input_monitor_raw_entry *entry =
            input_monitor_raw_entry_at(monitor, index);
        uint32_t row_y = top + (uint32_t)index * row_height;
        uint32_t title_color;

        if (entry == NULL) {
            continue;
        }

        title_color = input_monitor_value_color(entry->value);
        kms_fill_rect(&kms_state,
                      left,
                      row_y - scale,
                      content_width - scale * 2,
                      line_height * 2 + scale,
                      index == 0 ? 0x283030 : 0x181818);
        kms_draw_text(&kms_state,
                      left + scale * 2,
                      row_y,
                      entry->title,
                      title_color,
                      shrink_text_scale(entry->title,
                                        scale,
                                        content_width - scale * 4));
        kms_draw_text(&kms_state,
                      left + scale * 5,
                      row_y + line_height,
                      entry->detail,
                      index == 0 ? 0xffffff : 0xa8a8a8,
                      shrink_text_scale(entry->detail,
                                        scale,
                                        content_width - scale * 7));
    }

    kms_draw_text(&kms_state,
                  left,
                  kms_state.height - scale * 12,
                  "ALL BUTTONS EXIT / BRIDGE hide",
                  0xffffff,
                  shrink_text_scale("ALL BUTTONS EXIT / BRIDGE hide",
                                    scale,
                                    content_width));

    if (kms_present_frame_verbose("inputmonitor", false) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_input_monitor_app(void) {
    return draw_screen_input_monitor_state(&auto_input_monitor);
}

static int draw_screen_info_page(const char *title,
                                 const char *line1,
                                 const char *line2,
                                 const char *line3,
                                 const char *line4) {
    const char *footer = "PRESS ANY BUTTON TO RETURN";
    const char *lines[4];
    uint32_t scale;
    uint32_t title_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    size_t index;

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    lines[0] = line1;
    lines[1] = line2;
    lines[2] = line3;
    lines[3] = line4;

    scale = menu_text_scale();
    title_scale = scale + 1;
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 8;
    card_w = kms_state.width - (x * 2);
    line_h = scale * 12;

    kms_draw_text(&kms_state, x, y, title, 0xffcc33,
                  shrink_text_scale(title, title_scale, card_w));
    y += line_h + scale * 4;

    kms_fill_rect(&kms_state, x - scale, y - scale, card_w, line_h * 5, 0x202020);
    for (index = 0; index < 4; ++index) {
        kms_draw_text(&kms_state, x, y + (uint32_t)index * line_h,
                      lines[index] != NULL ? lines[index] : "",
                      0xffffff,
                      shrink_text_scale(lines[index] != NULL ? lines[index] : "",
                                        scale, card_w - scale * 2));
    }

    kms_draw_text(&kms_state, x, kms_state.height - scale * 12,
                  footer, 0xffffff, shrink_text_scale(footer, scale, card_w));

    if (kms_present_frame("screeninfo") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_about_lines(const char *title,
                                   const char *const *lines,
                                   size_t count) {
    const char *footer = "PRESS ANY BUTTON TO RETURN";
    uint32_t scale;
    uint32_t title_scale;
    uint32_t left;
    uint32_t top;
    uint32_t content_width;
    uint32_t line_height;
    size_t index;

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    title_scale = scale + 1;
    left = kms_state.width / 18;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = kms_state.height / 12;
    content_width = kms_state.width - (left * 2);
    line_height = scale * 10;

    kms_draw_text(&kms_state, left, top, title, 0xffcc33,
                  shrink_text_scale(title, title_scale, content_width));
    top += line_height + scale * 4;

    kms_fill_rect(&kms_state,
                  left - scale,
                  top - scale,
                  content_width,
                  line_height * ((uint32_t)count + 1),
                  0x202020);

    for (index = 0; index < count; ++index) {
        const char *line = lines[index] != NULL ? lines[index] : "";
        uint32_t color = index == 0 ? 0x88ee88 : 0xffffff;

        kms_draw_text(&kms_state,
                      left,
                      top + (uint32_t)index * line_height,
                      line,
                      color,
                      shrink_text_scale(line, scale, content_width - scale * 2));
    }

    kms_draw_text(&kms_state,
                  left,
                  kms_state.height - scale * 12,
                  footer,
                  0xffffff,
                  shrink_text_scale(footer, scale, content_width));

    if (kms_present_frame("screenabout") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void kms_draw_rect_outline(struct kms_display_state *state,
                                  uint32_t x,
                                  uint32_t y,
                                  uint32_t width,
                                  uint32_t height,
                                  uint32_t thickness,
                                  uint32_t color) {
    if (thickness == 0) {
        thickness = 1;
    }
    if (width <= thickness * 2 || height <= thickness * 2) {
        kms_fill_rect(state, x, y, width, height, color);
        return;
    }
    kms_fill_rect(state, x, y, width, thickness, color);
    kms_fill_rect(state, x, y + height - thickness, width, thickness, color);
    kms_fill_rect(state, x, y, thickness, height, color);
    kms_fill_rect(state, x + width - thickness, y, thickness, height, color);
}

static int clamp_int_value(int value, int min_value, int max_value) {
    if (value < min_value) {
        return min_value;
    }
    if (value > max_value) {
        return max_value;
    }
    return value;
}

static const char *cutout_calibration_field_name(enum cutout_calibration_field field) {
    switch (field) {
    case CUTOUT_CAL_FIELD_X:
        return "X";
    case CUTOUT_CAL_FIELD_Y:
        return "Y";
    case CUTOUT_CAL_FIELD_SIZE:
        return "SIZE";
    default:
        return "?";
    }
}

static void cutout_calibration_clamp(struct cutout_calibration_state *cal) {
    int width = kms_state.width > 0 ? (int)kms_state.width : 1080;
    int height = kms_state.height > 0 ? (int)kms_state.height : 2400;
    int min_size = width / 40;
    int max_size = width / 8;
    int margin;

    if (min_size < 18) {
        min_size = 18;
    }
    if (max_size < min_size) {
        max_size = min_size;
    }
    cal->size = clamp_int_value(cal->size, min_size, max_size);
    margin = cal->size / 2 + 2;
    cal->center_x = clamp_int_value(cal->center_x, margin, width - margin);
    cal->center_y = clamp_int_value(cal->center_y, margin, height - margin);
    if ((int)cal->field < 0 || cal->field >= CUTOUT_CAL_FIELD_COUNT) {
        cal->field = CUTOUT_CAL_FIELD_Y;
    }
}

static void cutout_calibration_init(struct cutout_calibration_state *cal) {
    int width = kms_state.width > 0 ? (int)kms_state.width : 1080;
    int height = kms_state.height > 0 ? (int)kms_state.height : 2400;

    cal->center_x = width / 2;
    cal->center_y = height / 30;
    cal->size = width / 22;
    cal->field = CUTOUT_CAL_FIELD_Y;
    cutout_calibration_clamp(cal);
}

static void cutout_calibration_adjust(struct cutout_calibration_state *cal,
                                      int direction) {
    int step = 4;

    if (cal->field == CUTOUT_CAL_FIELD_SIZE) {
        step = 2;
    }
    switch (cal->field) {
    case CUTOUT_CAL_FIELD_X:
        cal->center_x += direction * step;
        break;
    case CUTOUT_CAL_FIELD_Y:
        cal->center_y += direction * step;
        break;
    case CUTOUT_CAL_FIELD_SIZE:
        cal->size += direction * step;
        break;
    default:
        break;
    }
    cutout_calibration_clamp(cal);
}

static bool cutout_calibration_feed_key(struct cutout_calibration_state *cal,
                                        const struct input_event *event,
                                        unsigned int *down_mask,
                                        long *power_down_ms,
                                        long *last_power_up_ms) {
    unsigned int mask;
    long now_ms;

    if (event->type != EV_KEY || event->value == 2) {
        return false;
    }

    mask = input_button_mask_from_key(event->code);
    if (mask == 0) {
        return false;
    }

    now_ms = monotonic_millis();
    if (event->value == 1) {
        *down_mask |= mask;
        if ((*down_mask & (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN)) ==
            (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN)) {
            return true;
        }
        if (event->code == KEY_VOLUMEUP) {
            cutout_calibration_adjust(cal, -1);
        } else if (event->code == KEY_VOLUMEDOWN) {
            cutout_calibration_adjust(cal, 1);
        } else if (event->code == KEY_POWER) {
            *power_down_ms = now_ms;
        }
        return false;
    }

    *down_mask &= ~mask;
    if (event->code == KEY_POWER) {
        long duration_ms = *power_down_ms > 0 ? now_ms - *power_down_ms : 0;

        *power_down_ms = 0;
        if (duration_ms >= INPUT_LONG_PRESS_MS) {
            return true;
        }
        if (*last_power_up_ms > 0 &&
            now_ms - *last_power_up_ms <= INPUT_DOUBLE_CLICK_MS) {
            *last_power_up_ms = 0;
            return true;
        }
        *last_power_up_ms = now_ms;
        cal->field = (enum cutout_calibration_field)
                     (((int)cal->field + 1) % CUTOUT_CAL_FIELD_COUNT);
    }
    return false;
}

static int draw_screen_cutout_calibration(const struct cutout_calibration_state *cal,
                                          bool interactive) {
    struct cutout_calibration_state local = *cal;
    char line[96];
    uint32_t scale;
    uint32_t small_scale;
    uint32_t width;
    uint32_t height;
    uint32_t center_x;
    uint32_t center_y;
    uint32_t size;
    uint32_t box_x;
    uint32_t box_y;
    uint32_t box_thick;
    uint32_t gap;
    uint32_t side_margin;
    uint32_t slot_y;
    uint32_t slot_h;
    uint32_t slot_label_y;
    uint32_t camera_zone_w;
    uint32_t camera_zone_x;
    uint32_t left_w;
    uint32_t right_x;
    uint32_t right_w;
    uint32_t safe_y;
    uint32_t safe_h;
    uint32_t panel_y;
    uint32_t panel_h;
    uint32_t panel_w;
    uint32_t footer_y;

    cutout_calibration_clamp(&local);
    if (kms_begin_frame(0x05070c) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    if (scale < 2) {
        scale = 2;
    }
    small_scale = scale > 2 ? scale - 1 : scale;
    width = kms_state.width;
    height = kms_state.height;
    center_x = (uint32_t)local.center_x;
    center_y = (uint32_t)local.center_y;
    size = (uint32_t)local.size;
    box_x = center_x - size / 2;
    box_y = center_y - size / 2;
    box_thick = scale > 3 ? scale / 2 : 1;
    gap = scale * 3;
    side_margin = width / 24;
    if (side_margin < scale * 4) {
        side_margin = scale * 4;
    }
    footer_y = height > scale * 12 ? height - scale * 12 : height;

    slot_y = scale * 2;
    slot_h = center_y + size / 2 + scale * 12;
    if (slot_h < scale * 16) {
        slot_h = scale * 16;
    }
    slot_label_y = center_y + size / 2 + scale * 3;
    if (slot_label_y + scale * 8 > slot_y + slot_h) {
        slot_label_y = slot_y + scale * 2;
    }
    camera_zone_w = size + scale * 16;
    if (camera_zone_w < scale * 28) {
        camera_zone_w = scale * 28;
    }
    camera_zone_x = center_x > camera_zone_w / 2 ? center_x - camera_zone_w / 2 : 0;
    left_w = camera_zone_x > side_margin + gap ?
             camera_zone_x - side_margin - gap : 0;
    right_x = camera_zone_x + camera_zone_w + gap;
    right_w = side_margin + (width - side_margin * 2) > right_x ?
              side_margin + (width - side_margin * 2) - right_x : 0;

    if (left_w > scale * 18) {
        kms_fill_rect(&kms_state, side_margin, slot_y, left_w, slot_h, 0x07182a);
        kms_draw_rect_outline(&kms_state, side_margin, slot_y, left_w, slot_h,
                              box_thick, 0x315080);
        kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                          slot_label_y,
                          "LEFT SAFE", 0x66ddff, small_scale,
                          left_w - scale * 4);
    }
    if (right_w > scale * 18) {
        kms_fill_rect(&kms_state, right_x, slot_y, right_w, slot_h, 0x07182a);
        kms_draw_rect_outline(&kms_state, right_x, slot_y, right_w, slot_h,
                              box_thick, 0x315080);
        kms_draw_text_fit(&kms_state, right_x + scale * 2,
                          slot_label_y,
                          "RIGHT SAFE", 0x66ddff, small_scale,
                          right_w - scale * 4);
    }
    kms_draw_rect_outline(&kms_state, camera_zone_x, slot_y,
                          camera_zone_w, slot_h, box_thick, 0xff8040);
    kms_draw_text_fit(&kms_state, camera_zone_x + scale * 2,
                      slot_label_y,
                      "CAMERA", 0xffcc33, small_scale,
                      camera_zone_w - scale * 4);

    kms_draw_rect_outline(&kms_state, box_x, box_y, size, size,
                          box_thick, 0xff8040);
    if (box_x > scale * 8) {
        kms_fill_rect(&kms_state, box_x - scale * 8, center_y,
                      scale * 8, box_thick, 0x66ddff);
    }
    if (box_x + size + scale * 8 < width) {
        kms_fill_rect(&kms_state, box_x + size, center_y,
                      scale * 8, box_thick, 0x66ddff);
    }
    if (box_y > scale * 8) {
        kms_fill_rect(&kms_state, center_x, box_y - scale * 8,
                      box_thick, scale * 8, 0x66ddff);
    }
    if (box_y + size + scale * 8 < height) {
        kms_fill_rect(&kms_state, center_x, box_y + size,
                      box_thick, scale * 8, 0x66ddff);
    }
    kms_fill_rect(&kms_state, center_x, center_y, box_thick, box_thick, 0xffffff);

    safe_y = center_y + size / 2 + scale * 12;
    if (safe_y < height / 5) {
        safe_y = height / 5;
    }
    if (safe_y + scale * 32 < footer_y) {
        safe_h = footer_y - safe_y - scale * 4;
        kms_draw_rect_outline(&kms_state,
                              side_margin,
                              safe_y,
                              width - side_margin * 2,
                              safe_h,
                              box_thick,
                              0x4060a0);
        kms_fill_rect(&kms_state, width / 2, safe_y,
                      box_thick, safe_h, 0x604020);
        kms_fill_rect(&kms_state, side_margin,
                      safe_y + safe_h / 2,
                      width - side_margin * 2,
                      box_thick,
                      0x604020);
    }

    panel_y = safe_y + scale * 4;
    panel_w = width - side_margin * 2;
    panel_h = scale * 42;
    if (panel_y + panel_h > footer_y) {
        panel_y = height / 3;
    }
    kms_fill_rect(&kms_state, side_margin, panel_y,
                  panel_w, panel_h, 0x101820);
    kms_draw_rect_outline(&kms_state, side_margin, panel_y,
                          panel_w, panel_h, box_thick, 0x315080);
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 2,
                      interactive ? "ALIGN ORANGE BOX TO CAMERA HOLE"
                                  : "REFERENCE: ORANGE BOX SHOULD MATCH CAMERA",
                      0x88ee88, small_scale, panel_w - scale * 4);
    snprintf(line, sizeof(line), "X=%d  Y=%d  SIZE=%d  FIELD=%s",
             local.center_x,
             local.center_y,
             local.size,
             cutout_calibration_field_name(local.field));
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 12,
                      line, 0xffffff, small_scale,
                      panel_w - scale * 4);
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 22,
                      interactive ? "VOL+/- ADJUST  POWER NEXT FIELD"
                                  : "SHELL: cutoutcal [x y size]",
                      0xffcc33, small_scale, panel_w - scale * 4);
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 32,
                      interactive ? "PWR LONG/DBL OR VOL+DN BACK"
                                  : "MENU APP: TOOLS > CUTOUT CAL",
                      0xdddddd, small_scale, panel_w - scale * 4);
    kms_draw_text_fit(&kms_state, side_margin, footer_y,
                      interactive ? "CALIBRATION MODE" : "DISPLAYTEST SAFE",
                      0xffffff, small_scale, width - side_margin * 2);

    if (kms_present_frame("cutoutcal") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static const char *display_test_page_title(unsigned int page_index) {
    switch (page_index % DISPLAY_TEST_PAGE_COUNT) {
    case 0:
        return "COLOR / PIXEL";
    case 1:
        return "FONT / WRAP";
    case 2:
        return "SAFE / CUTOUT";
    case 3:
        return "HUD / MENU";
    default:
        return "DISPLAY";
    }
}

static int draw_screen_display_test_page(unsigned int page_index) {
    struct display_test_color {
        const char *name;
        uint32_t fill;
        uint32_t text;
    };
    static const struct display_test_color palette[] = {
        { "BLACK",  0x000000, 0xffffff },
        { "WHITE",  0xffffff, 0x000000 },
        { "RED",    0xd84040, 0xffffff },
        { "GREEN",  0x30d060, 0x000000 },
        { "BLUE",   0x3080ff, 0xffffff },
        { "YELLOW", 0xffcc33, 0x000000 },
        { "CYAN",   0x40d8ff, 0x000000 },
        { "GRAY",   0x606060, 0xffffff },
    };
    static const char *layout_items[] = {
        "HIDE MENU",
        "STATUS",
        "LOG",
        "TOOLS",
        "POWER",
    };
    const char *wrap_sample =
        "LONG LOG LINE WRAPS INTO SAFE WIDTH WITHOUT CLIPPING AND KEEPS WORD BOUNDARIES";
    char line[96];
    char chunk[96];
    const char *cursor;
    uint32_t scale;
    uint32_t small_scale;
    uint32_t title_scale;
    uint32_t left;
    uint32_t top;
    uint32_t body_top;
    uint32_t content_width;
    uint32_t line_height;
    uint32_t gap;
    uint32_t swatch_width;
    uint32_t swatch_height;
    uint32_t footer_y;
    uint32_t max_chars;
    size_t wrap_offset;
    size_t index;

    page_index %= DISPLAY_TEST_PAGE_COUNT;
    if (page_index == 2) {
        struct cutout_calibration_state cal;

        cutout_calibration_init(&cal);
        return draw_screen_cutout_calibration(&cal, false);
    }

    if (kms_begin_frame(0x05070c) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    if (scale < 2) {
        scale = 2;
    }
    small_scale = scale > 2 ? scale - 1 : scale;
    title_scale = scale + 1;
    left = kms_state.width / 24;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = kms_state.height / 16;
    content_width = kms_state.width > left * 2 ? kms_state.width - (left * 2) : kms_state.width;
    line_height = scale * 10;
    gap = scale * 3;
    footer_y = kms_state.height > scale * 14 ? kms_state.height - scale * 14 : kms_state.height;

    kms_draw_rect_outline(&kms_state, left - scale, top - scale,
                          content_width + scale * 2,
                          footer_y - top + scale,
                          scale,
                          0x315080);

    snprintf(line, sizeof(line), "TOOLS / DISPLAY TEST %u/%u",
             page_index + 1,
             DISPLAY_TEST_PAGE_COUNT);
    kms_draw_text_fit(&kms_state, left, top, line,
                      0xffcc33, title_scale, content_width);
    top += line_height + gap;
    kms_draw_text_fit(&kms_state, left, top, display_test_page_title(page_index),
                      0x88aaff, scale, content_width);
    top += line_height + gap;
    body_top = top;

    if (page_index == 0) {
        swatch_width = (content_width - gap) / 2;
        swatch_height = line_height * 2;
        for (index = 0; index < SCREEN_MENU_COUNT(palette); ++index) {
            uint32_t col = (uint32_t)(index % 2);
            uint32_t row = (uint32_t)(index / 2);
            uint32_t swatch_x = left + col * (swatch_width + gap);
            uint32_t swatch_y = body_top + row * (swatch_height + gap);

            kms_fill_rect(&kms_state, swatch_x, swatch_y,
                          swatch_width, swatch_height, palette[index].fill);
            kms_fill_rect(&kms_state, swatch_x, swatch_y,
                          swatch_width, scale, 0xffffff);
            kms_draw_text_fit(&kms_state,
                              swatch_x + scale * 2,
                              swatch_y + scale * 5,
                              palette[index].name,
                              palette[index].text,
                              scale,
                              swatch_width - scale * 4);
        }
        top = body_top + ((uint32_t)(SCREEN_MENU_COUNT(palette) + 1) / 2) *
              (swatch_height + gap) + gap;
        kms_draw_text_fit(&kms_state, left, top,
                          "PIXEL FORMAT XBGR8888 / RGB LABEL CHECK",
                          0x88ee88, small_scale, content_width);
        top += line_height;
        kms_draw_text_fit(&kms_state, left, top,
                          "WHITE BAR SHOULD BE WHITE, RED/GREEN/BLUE SHOULD MATCH LABELS",
                          0xdddddd, small_scale, content_width);
    } else if (page_index == 1) {
        for (index = 1; index <= 8; ++index) {
            uint32_t row_scale = (uint32_t)index;
            uint32_t row_height = row_scale * 8 + scale * 2;

            if (top + row_height >= footer_y - line_height * 5) {
                break;
            }
            snprintf(line, sizeof(line), "SCALE %u ABC123 0.8.8", row_scale);
            kms_fill_rect(&kms_state, left, top,
                          content_width, row_height,
                          index % 2 ? 0x101620 : 0x182030);
            kms_draw_text_fit(&kms_state, left + scale * 2, top + scale,
                              line, 0xffffff, row_scale,
                              content_width - scale * 4);
            top += row_height + scale;
        }
        top += gap;
        kms_draw_text_fit(&kms_state, left, top, "WRAP SAMPLE",
                          0x88aaff, scale, content_width);
        top += line_height;
        cursor = wrap_sample;
        max_chars = content_width / (small_scale * 6);
        if (max_chars < 8) {
            max_chars = 8;
        }
        wrap_offset = 0;
        for (index = 0; cursor[wrap_offset] != '\0' && index < 5; ++index) {
            size_t next_offset;

            kms_log_tail_next_chunk(cursor,
                                    wrap_offset,
                                    max_chars,
                                    chunk,
                                    sizeof(chunk),
                                    &next_offset);
            kms_draw_text_fit(&kms_state, left + scale * 2, top,
                              chunk, 0xffffff, small_scale,
                              content_width - scale * 4);
            top += small_scale * 10;
            wrap_offset = next_offset;
        }
    } else if (page_index == 2) {
        uint32_t cutout_y = body_top + gap;
        uint32_t cutout_h = line_height * 3;
        uint32_t cutout_w = content_width / 5;
        uint32_t cutout_x;
        uint32_t cutout_center_x = kms_state.width / 2;
        uint32_t cutout_center_y = cutout_y + cutout_h / 2;
        uint32_t pocket_w;
        uint32_t right_x;
        uint32_t right_w;
        uint32_t hole = scale * 10;
        uint32_t grid_y;
        uint32_t grid_h;
        uint32_t center_x;
        uint32_t center_y;
        uint32_t label_y;
        uint32_t legend_y;
        uint32_t chip;

        if (cutout_w < scale * 24) {
            cutout_w = scale * 24;
        }
        if (cutout_w > content_width / 3) {
            cutout_w = content_width / 3;
        }
        cutout_x = (kms_state.width - cutout_w) / 2;
        pocket_w = cutout_x > left + gap ? cutout_x - left - gap : 0;
        right_x = cutout_x + cutout_w + gap;
        right_w = left + content_width > right_x ? left + content_width - right_x : 0;

        if (pocket_w > scale * 16) {
            kms_fill_rect(&kms_state, left, cutout_y, pocket_w, cutout_h, 0x07182a);
            kms_draw_rect_outline(&kms_state, left, cutout_y, pocket_w, cutout_h,
                                  scale, 0x315080);
            kms_draw_text_fit(&kms_state, left + scale * 2, cutout_y + scale * 2,
                              "LEFT SAFE", 0x66ddff, small_scale,
                              pocket_w - scale * 4);
        }
        kms_fill_rect(&kms_state, cutout_x, cutout_y, cutout_w, cutout_h, 0x281018);
        kms_draw_rect_outline(&kms_state, cutout_x, cutout_y, cutout_w, cutout_h,
                              scale, 0xff8040);
        kms_draw_text_fit(&kms_state, cutout_x + scale * 2, cutout_y + scale * 2,
                          "CAMERA", 0xffcc33, small_scale,
                          cutout_w - scale * 4);
        if (hole > cutout_h - scale * 2) {
            hole = cutout_h - scale * 2;
        }
        if (hole >= scale * 4) {
            kms_fill_rect(&kms_state,
                          cutout_center_x - hole / 2,
                          cutout_center_y - hole / 2,
                          hole,
                          hole,
                          0x000000);
            kms_draw_rect_outline(&kms_state,
                                  cutout_center_x - hole / 2,
                                  cutout_center_y - hole / 2,
                                  hole,
                                  hole,
                                  scale,
                                  0xffffff);
        }
        if (right_w > scale * 16) {
            kms_fill_rect(&kms_state, right_x, cutout_y, right_w, cutout_h, 0x07182a);
            kms_draw_rect_outline(&kms_state, right_x, cutout_y, right_w, cutout_h,
                                  scale, 0x315080);
            kms_draw_text_fit(&kms_state, right_x + scale * 2, cutout_y + scale * 2,
                              "RIGHT SAFE", 0x66ddff, small_scale,
                              right_w - scale * 4);
        }

        grid_y = cutout_y + cutout_h + gap * 3;
        grid_h = footer_y > grid_y + line_height ? footer_y - grid_y - line_height : 0;
        if (grid_h >= line_height * 4) {
            center_x = left + content_width / 2;
            center_y = grid_y + grid_h / 2;
            label_y = grid_y + scale * 2;
            kms_fill_rect(&kms_state, left, grid_y, content_width, grid_h, 0x0b1018);
            kms_draw_rect_outline(&kms_state, left, grid_y, content_width, grid_h,
                                  scale, 0xff8040);
            kms_fill_rect(&kms_state, center_x, grid_y, scale, grid_h, 0x604020);
            kms_fill_rect(&kms_state, left, center_y, content_width, scale, 0x604020);
            kms_draw_rect_outline(&kms_state,
                                  left + content_width / 10,
                                  grid_y + grid_h / 7,
                                  content_width * 4 / 5,
                                  grid_h * 5 / 7,
                                  scale,
                                  0x4060a0);
            kms_fill_rect(&kms_state, left + scale, label_y,
                          content_width - scale * 2,
                          line_height * 2 + scale,
                          0x101820);
            kms_draw_text_fit(&kms_state, left + scale * 3, label_y + scale,
                              "SAFE GRID", 0x88ee88, small_scale,
                              content_width - scale * 6);
            kms_draw_text_fit(&kms_state, left + scale * 3,
                              label_y + line_height,
                              "ORANGE EDGE  BLUE CONTENT", 0xdddddd,
                              small_scale, content_width - scale * 6);
            chip = scale * 4;
            legend_y = grid_y + grid_h;
            if (legend_y > line_height * 2 + scale * 6) {
                legend_y -= line_height * 2 + scale * 6;
            }
            if (legend_y > label_y + line_height * 3 && content_width > scale * 28) {
                kms_fill_rect(&kms_state, left + scale * 3, legend_y,
                              chip, chip, 0xff8040);
                kms_draw_text_fit(&kms_state, left + scale * 9,
                                  legend_y - scale,
                                  "EDGE", 0xffcc33, small_scale,
                                  content_width / 3);
                kms_fill_rect(&kms_state, left + content_width / 2,
                              legend_y, chip, chip, 0x4060a0);
                kms_draw_text_fit(&kms_state,
                                  left + content_width / 2 + scale * 6,
                                  legend_y - scale,
                                  "CONTENT", 0x66ddff, small_scale,
                                  content_width / 3);
            }
        }
    } else {
        uint32_t card_y = body_top;
        uint32_t card_h = line_height * 3;
        uint32_t half_w = (content_width - gap) / 2;

        kms_draw_status_overlay(&kms_state, left, card_y);
        card_y += line_height * 5;
        kms_draw_text_fit(&kms_state, left, card_y,
                          "HUD/MENU PREVIEW - CHECK SPACING AND TEXT WEIGHT",
                          0x88ee88, small_scale, content_width);
        card_y += line_height + gap;
        for (index = 0; index < SCREEN_MENU_COUNT(layout_items); ++index) {
            uint32_t col = (uint32_t)(index % 2);
            uint32_t row = (uint32_t)(index / 2);
            uint32_t item_x = left + col * (half_w + gap);
            uint32_t item_y = card_y + row * (card_h + gap);
            uint32_t fill = index == 0 ? 0xd84040 : 0x182030;
            uint32_t edge = index == 0 ? 0x66ddff : 0x315080;

            if (item_y + card_h >= footer_y - line_height) {
                break;
            }
            kms_fill_rect(&kms_state, item_x, item_y, half_w, card_h, fill);
            kms_draw_rect_outline(&kms_state, item_x, item_y, half_w, card_h,
                                  scale, edge);
            kms_draw_text_fit(&kms_state,
                              item_x + scale * 2,
                              item_y + scale * 4,
                              layout_items[index],
                              0xffffff,
                              scale,
                              half_w - scale * 4);
        }
        kms_draw_text_fit(&kms_state,
                          left,
                          footer_y - line_height * 2,
                          "PREVIEW ONLY: REAL MENU STILL USES LIVE STATUS + LOG TAIL",
                          0xdddddd,
                          small_scale,
                          content_width - scale * 4);
    }

    kms_draw_text_fit(&kms_state, left, footer_y, "VOL+/- PAGE  POWER BACK",
                      0xffffff, small_scale, content_width);

    if (kms_present_frame("displaytest") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_display_test(void) {
    return draw_screen_display_test_page(0);
}

static int draw_screen_about_version(void) {
    char version_line[96];
    const char *lines[5];

    snprintf(version_line, sizeof(version_line), "VERSION %s (%s)", INIT_VERSION, INIT_BUILD);
    lines[0] = INIT_BANNER;
    lines[1] = version_line;
    lines[2] = INIT_CREATOR;
    lines[3] = "KERNEL STOCK ANDROID LINUX 4.14";
    lines[4] = "RUNTIME CUSTOM STATIC PID 1";

    return draw_screen_about_lines("ABOUT / VERSION", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_about_changelog(void) {
    const char *lines[] = {
        "0.8.8 v77 DISPLAY TEST PAGES",
        "0.8.7 v76 AT FRAGMENT FILTER",
        "0.8.6 v75 QUIET IDLE REATTACH",
        "0.8.5 v74 CMDV1 ARG ENCODING",
        "0.8.4 v73 CMDV1 PROTOCOL",
        "0.8.3 v72 DISPLAY TEST FIX",
        "0.8.2 v71 MENU LOG TAIL",
        "0.8.1 v70 INPUT MONITOR APP",
        "0.8.0 v69 INPUT GESTURE LAYOUT",
        "0.7.5 v68 LOG TAIL + MORE HISTORY",
        "0.7.4 v67 DETAIL CHANGELOG UI",
        "0.7.3 v66 ABOUT + VERSIONING",
        "0.7.2 v65 SPLASH SAFE LAYOUT",
        "0.7.1 v64 CUSTOM BOOT SPLASH",
        "0.7.0 v63 APP MENU + CPU STRESS",
        "0.6.0 v62 CPU STRESS / DEV NODES",
        "0.5.1 v61 CPU/GPU USAGE HUD",
        "0.5.0 v60 NETSERVICE / RECONNECT",
        "0.4.1 v59 AT SERIAL FILTER",
        "0.4.0 v55 NCM TCP CONTROL",
        "0.3.0 v53 MENU BUSY GATE",
        "0.2.0 v40 SHELL LOG HUD CORE",
        "0.1.0 v1  NATIVE INIT ORIGIN",
    };

    return draw_screen_about_lines("ABOUT / CHANGELOG", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v088(void) {
    const char *lines[] = {
        "0.8.8 v77 DISPLAY TEST PAGES",
        "Split display test into pages",
        "Page 1 color and pixel format",
        "Page 2 font scale and wrap",
        "Page 3 safe/cutout reference",
        "Page 4 HUD/menu preview",
        "Added cutoutcal command/app",
        "VOL adjusts POWER changes field",
        "VOL up/down changes page",
        "displaytest [page] via shell",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.8", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v087(void) {
    const char *lines[] = {
        "0.8.7 v76 AT FRAGMENT FILTER",
        "Ignores short A/T fragments",
        "Covers A T AT ATA ATAT",
        "Keeps full AT probe filter",
        "Prevents unknown command spam",
        "Logs ignored fragment category",
        "Normal lowercase shell remains",
        "Keeps cmdv1/cmdv1x unchanged",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.7", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v086(void) {
    const char *lines[] = {
        "0.8.6 v75 QUIET IDLE REATTACH",
        "Idle serial reattach still active",
        "Interval increased to 60 seconds",
        "Success logs hidden for idle path",
        "Failures remain visible in log tail",
        "Manual reattach logs still visible",
        "Keeps recovery behavior unchanged",
        "Reduces live log tail noise",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.6", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v085(void) {
    const char *lines[] = {
        "0.8.5 v74 CMDV1 ARG ENCODING",
        "Added cmdv1x len:hex argv",
        "Keeps old cmdv1 token path",
        "Host a90ctl auto-selects format",
        "Whitespace args stay framed",
        "Special chars avoid raw fallback",
        "Decoder validates length and hex",
        "Prepared safer automation calls",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.5", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v084(void) {
    const char *lines[] = {
        "0.8.4 v73 CMDV1 PROTOCOL",
        "Added cmdv1 command wrapper",
        "Emits A90P1 BEGIN and END",
        "Reports rc errno duration flags",
        "Keeps normal shell output intact",
        "Unknown/busy states are framed",
        "Host a90ctl can parse results",
        "Bridge automation gets safer",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.4", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v083(void) {
    const char *lines[] = {
        "0.8.3 v72 DISPLAY TEST FIX",
        "Added TOOLS / DISPLAY TEST",
        "Added color/font/wrap grid screen",
        "Added cutout top slot guide",
        "Widened main safe-area grid",
        "Fixed XBGR8888 color packing",
        "Displaytest command draws directly",
        "Validated flash and framebuffer",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.3", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v082(void) {
    const char *lines[] = {
        "0.8.2 v71 MENU LOG TAIL",
        "Shared log tail panel renderer",
        "HUD hidden keeps log tail view",
        "HUD menu also shows live log tail",
        "screenmenu uses spare space too",
        "Log colors highlight failures/input",
        "Long log lines wrap on screen",
        "Busy gate allows safe commands",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.2", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v081(void) {
    const char *lines[] = {
        "0.8.1 v70 INPUT MONITOR APP",
        "Added TOOLS / INPUT MONITOR",
        "Shows raw DOWN/UP/REPEAT events",
        "Shows gap between input events",
        "Shows key hold duration on release",
        "Shows decoded gesture/action",
        "Added inputmonitor shell command",
        "All-buttons exits monitor app",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v080(void) {
    const char *lines[] = {
        "0.8.0 v69 INPUT GESTURE LAYOUT",
        "Added inputlayout command",
        "Added waitgesture debug command",
        "Single click keeps old controls",
        "Double/long volume page moves",
        "POWER double and VOL combo back",
        "POWER long reserved for safety",
        "screenmenu/blindmenu use gestures",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v075(void) {
    const char *lines[] = {
        "0.7.5 v68 LOG TAIL + HISTORY",
        "HUD menu hidden: log tail display",
        "HUD menu visible: item summary shown",
        "Changelog: 14 versions from v1",
        "Added v68 v61 v59 v55 v53 v40 v1",
        "Detail screens for all versions",
        "Log reads /cache/native-init.log",
        "Tail shows last 14 lines",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.5", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v074(void) {
    const char *lines[] = {
        "0.7.4 v67 DETAIL CHANGELOG UI",
        "ABOUT text scale reduced",
        "VERSION/CREDITS use compact text",
        "CHANGELOG opens version list",
        "Each version opens detail screen",
        "Longer notes fit vertical display",
        "Current build remains visible",
        "Footer kept press-any-button",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.4", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v073(void) {
    const char *lines[] = {
        "0.7.3 v66 ABOUT + VERSIONING",
        "Added semantic version display",
        "Added made by temmie0214",
        "Added APPS / ABOUT folder",
        "Added VERSION screen",
        "Added CHANGELOG summary screen",
        "Added CREDITS screen",
        "Updated version command output",
        "Updated status creator output",
        "Added VERSIONING.md and CHANGELOG.md",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.3", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v072(void) {
    const char *lines[] = {
        "0.7.2 v65 SPLASH SAFE LAYOUT",
        "Reduced boot splash text scale",
        "Widened safe screen margins",
        "Shortened status rows",
        "Moved footer into safe area",
        "Avoided punch-hole overlap",
        "Verified visible splash layout",
        "Kept auto HUD transition",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.2", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v071(void) {
    const char *lines[] = {
        "0.7.1 v64 CUSTOM BOOT SPLASH",
        "Replaced TEST boot screen",
        "Added A90 NATIVE INIT splash",
        "Added boot summary text",
        "Recorded display-splash timeline",
        "Kept shell handoff stable",
        "Kept status HUD after boot",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v070(void) {
    const char *lines[] = {
        "0.7.0 v63 APP MENU",
        "Added APPS hierarchy",
        "Added MONITORING folder",
        "Added TOOLS folder",
        "Added LOGS folder",
        "Added CPU STRESS duration menu",
        "Kept app screens persistent",
        "Improved physical button flow",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v060(void) {
    const char *lines[] = {
        "0.6.0 v62 CPU DIAGNOSTICS",
        "Added cpustress command",
        "Added CPU usage display",
        "Added temperature visibility",
        "Validated usage change under load",
        "Added /dev/null guard",
        "Added /dev/zero guard",
    };

    return draw_screen_about_lines("CHANGELOG / 0.6.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v051(void) {
    const char *lines[] = {
        "0.5.1 v61 CPU/GPU USAGE HUD",
        "Added CPU usage percent to HUD",
        "Added GPU usage percent to HUD",
        "Read from /sys/kernel/gpu/gpu_busy",
        "Read /proc/stat for CPU idle delta",
        "Display: CPU temp usage GPU temp usage",
        "Verified readout updates live",
    };

    return draw_screen_about_lines("CHANGELOG / 0.5.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v050(void) {
    const char *lines[] = {
        "0.5.0 v60 NETSERVICE BOOT",
        "Added opt-in boot-time netservice",
        "Flag: /cache/native-init-netservice",
        "Flag absent: ACM only at boot",
        "netservice enable/disable commands",
        "netservice stop/start for reconnect",
        "Validated UDC re-enum + NCM restore",
        "Host NCM interface name may change",
    };

    return draw_screen_about_lines("CHANGELOG / 0.5.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v041(void) {
    const char *lines[] = {
        "0.4.1 v59 AT SERIAL FILTER",
        "Host modem probe sends AT commands",
        "AT/ATE0/AT+... lines ignored by shell",
        "Filter in native init input path",
        "No bridge-side workaround needed",
        "Stable ACM session under NetworkManager",
    };

    return draw_screen_about_lines("CHANGELOG / 0.4.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v040(void) {
    const char *lines[] = {
        "0.4.0 v55 NCM TCP CONTROL",
        "USB NCM persistent composite gadget",
        "IPv6 netcat payload verified (v54)",
        "NCM ops helper: a90_usbnet",
        "TCP test helper: a90_nettest",
        "TCP control server: a90_tcpctl",
        "Host wrapper: a90ctl launch/client",
        "Soak validation: 100 round trips",
    };

    return draw_screen_about_lines("CHANGELOG / 0.4.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v030(void) {
    const char *lines[] = {
        "0.3.0 v53 MENU BUSY GATE",
        "Hardware key menu always visible",
        "VOLUP/DN move POWER select",
        "Menu items: HIDE STATUS LOG",
        "Menu items: RECOVERY REBOOT POWEROFF",
        "Bridge busy gate: hide before recovery",
        "IPC via /tmp/a90-auto-menu-active",
        "bridge hide command clears menu",
    };

    return draw_screen_about_lines("CHANGELOG / 0.3.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v020(void) {
    const char *lines[] = {
        "0.2.0 v40-v45 SHELL LOG HUD CORE",
        "Shell command dispatch stabilized",
        "Structured logging to /cache",
        "Boot timeline recording",
        "KMS/DRM status HUD: 4 rows scale 5",
        "BAT+PWR combined row",
        "Punch-hole camera y offset",
        "Per-segment label/value color split",
    };

    return draw_screen_about_lines("CHANGELOG / 0.2.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v010(void) {
    const char *lines[] = {
        "0.1.0 v1 NATIVE INIT ORIGIN",
        "PID 1 native C init confirmed",
        "KMS/DRM dumb buffer rendering",
        "5x7 bitmap font renderer",
        "USB CDC ACM serial shell",
        "TCP bridge 127.0.0.1:54321",
        "Input event probing (event0/3)",
        "Blind menu for button control",
    };

    return draw_screen_about_lines("CHANGELOG / 0.1.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_detail(enum screen_app_id app_id) {
    switch (app_id) {
    case SCREEN_APP_CHANGELOG_088:
        return draw_screen_changelog_v088();
    case SCREEN_APP_CHANGELOG_087:
        return draw_screen_changelog_v087();
    case SCREEN_APP_CHANGELOG_086:
        return draw_screen_changelog_v086();
    case SCREEN_APP_CHANGELOG_085:
        return draw_screen_changelog_v085();
    case SCREEN_APP_CHANGELOG_084:
        return draw_screen_changelog_v084();
    case SCREEN_APP_CHANGELOG_083:
        return draw_screen_changelog_v083();
    case SCREEN_APP_CHANGELOG_082:
        return draw_screen_changelog_v082();
    case SCREEN_APP_CHANGELOG_081:
        return draw_screen_changelog_v081();
    case SCREEN_APP_CHANGELOG_080:
        return draw_screen_changelog_v080();
    case SCREEN_APP_CHANGELOG_075:
        return draw_screen_changelog_v075();
    case SCREEN_APP_CHANGELOG_074:
        return draw_screen_changelog_v074();
    case SCREEN_APP_CHANGELOG_073:
        return draw_screen_changelog_v073();
    case SCREEN_APP_CHANGELOG_072:
        return draw_screen_changelog_v072();
    case SCREEN_APP_CHANGELOG_071:
        return draw_screen_changelog_v071();
    case SCREEN_APP_CHANGELOG_070:
        return draw_screen_changelog_v070();
    case SCREEN_APP_CHANGELOG_060:
        return draw_screen_changelog_v060();
    case SCREEN_APP_CHANGELOG_051:
        return draw_screen_changelog_v051();
    case SCREEN_APP_CHANGELOG_050:
        return draw_screen_changelog_v050();
    case SCREEN_APP_CHANGELOG_041:
        return draw_screen_changelog_v041();
    case SCREEN_APP_CHANGELOG_040:
        return draw_screen_changelog_v040();
    case SCREEN_APP_CHANGELOG_030:
        return draw_screen_changelog_v030();
    case SCREEN_APP_CHANGELOG_020:
        return draw_screen_changelog_v020();
    case SCREEN_APP_CHANGELOG_010:
        return draw_screen_changelog_v010();
    default:
        return 0;
    }
}

static int draw_screen_about_credits(void) {
    const char *lines[] = {
        INIT_CREATOR,
        "DEVICE SAMSUNG GALAXY A90 5G",
        "MODEL SM-A908N",
        "KERNEL SAMSUNG STOCK 4.14",
        "CONTROL USB ACM + NCM",
        "PROJECT NATIVE INIT USERSPACE",
    };

    return draw_screen_about_lines("ABOUT / CREDITS", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_network_summary(void) {
    char line1[96];
    char line2[96];
    char line3[96];
    char line4[96];

    snprintf(line1, sizeof(line1), "NETSERVICE %s",
             access(NETSERVICE_FLAG_PATH, F_OK) == 0 ? "ENABLED" : "DISABLED");
    snprintf(line2, sizeof(line2), "%s %s %s",
             NETSERVICE_IFNAME,
             access("/sys/class/net/" NETSERVICE_IFNAME, F_OK) == 0 ? "PRESENT" : "ABSENT",
             NETSERVICE_DEVICE_IP);
    snprintf(line3, sizeof(line3), "TCPCTL %s%s%ld",
             tcpctl_pid > 0 ? "RUNNING PID " : "STOPPED",
             tcpctl_pid > 0 ? "" : "",
             tcpctl_pid > 0 ? (long)tcpctl_pid : 0L);
    if (tcpctl_pid <= 0) {
        snprintf(line3, sizeof(line3), "TCPCTL STOPPED");
    }
    snprintf(line4, sizeof(line4), "PORT %s LOG %s", NETSERVICE_TCP_PORT, NETSERVICE_LOG_PATH);

    return draw_screen_info_page("NETWORK STATUS", line1, line2, line3, line4);
}

static int draw_screen_cpu_hint(void) {
    return draw_screen_info_page("TOOLS / CPU STRESS",
                                 "AUTO MENU: CHOOSE 5/10/30/60S",
                                 "SERIAL: cpustress <sec> 8",
                                 "CPU GAUGE SHOULD RISE",
                                 "GPU MAY STAY 0% ON CPU TEST");
}

static long clamp_stress_duration_ms(long duration_ms) {
    if (duration_ms < 1000L) {
        return 1000L;
    }
    if (duration_ms > 120000L) {
        return 120000L;
    }
    return duration_ms;
}

static int draw_screen_cpu_stress_app(bool running,
                                      bool done,
                                      bool failed,
                                      long remaining_ms,
                                      long duration_ms) {
    struct status_snapshot snapshot;
    char online[64];
    char present[64];
    char freq0[32];
    char freq1[32];
    char freq2[32];
    char freq3[32];
    char freq4[32];
    char freq5[32];
    char freq6[32];
    char freq7[32];
    char lines[8][160];
    const char *status_word;
    uint32_t scale;
    uint32_t title_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    size_t index;

    duration_ms = clamp_stress_duration_ms(duration_ms);

    if (failed) {
        status_word = "FAILED";
    } else if (running) {
        status_word = "RUNNING";
    } else if (done) {
        status_word = "DONE";
    } else {
        status_word = "READY";
    }

    read_status_snapshot(&snapshot);
    if (read_trimmed_text_file("/sys/devices/system/cpu/online",
                               online,
                               sizeof(online)) < 0) {
        strcpy(online, "?");
    }
    if (read_trimmed_text_file("/sys/devices/system/cpu/present",
                               present,
                               sizeof(present)) < 0) {
        strcpy(present, "?");
    }
    screen_app_read_cpu_freq_label(0, freq0, sizeof(freq0));
    screen_app_read_cpu_freq_label(1, freq1, sizeof(freq1));
    screen_app_read_cpu_freq_label(2, freq2, sizeof(freq2));
    screen_app_read_cpu_freq_label(3, freq3, sizeof(freq3));
    screen_app_read_cpu_freq_label(4, freq4, sizeof(freq4));
    screen_app_read_cpu_freq_label(5, freq5, sizeof(freq5));
    screen_app_read_cpu_freq_label(6, freq6, sizeof(freq6));
    screen_app_read_cpu_freq_label(7, freq7, sizeof(freq7));

    snprintf(lines[0], sizeof(lines[0]), "STATE %s  REM %ld.%03ldS",
             status_word,
             remaining_ms / 1000L,
             remaining_ms % 1000L);
    snprintf(lines[1], sizeof(lines[1]), "CPU %s  USE %s  LOAD %s",
             snapshot.cpu_temp,
             snapshot.cpu_usage,
             snapshot.loadavg);
    snprintf(lines[2], sizeof(lines[2]), "CORES ONLINE %.24s  PRESENT %.24s", online, present);
    snprintf(lines[3], sizeof(lines[3]), "FREQ 0:%s 1:%s 2:%s 3:%s",
             freq0, freq1, freq2, freq3);
    snprintf(lines[4], sizeof(lines[4]), "FREQ 4:%s 5:%s 6:%s 7:%s",
             freq4, freq5, freq6, freq7);
    snprintf(lines[5], sizeof(lines[5]), "MEM %s  PWR %s",
             snapshot.memory,
             snapshot.power_now);
    snprintf(lines[6], sizeof(lines[6]), "WORKERS 8  TEST %ldS", duration_ms / 1000L);
    snprintf(lines[7], sizeof(lines[7]), "ANY BUTTON BACK / CANCEL");

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = menu_text_scale();
    title_scale = scale + 1;
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 10;
    card_w = kms_state.width - (x * 2);
    line_h = scale * 11;

    kms_draw_text(&kms_state, x, y, "TOOLS / CPU STRESS", 0xffcc33,
                  shrink_text_scale("TOOLS / CPU STRESS", title_scale, card_w));
    y += line_h + scale * 4;

    kms_fill_rect(&kms_state, x - scale, y - scale, card_w, line_h * 9, 0x202020);
    for (index = 0; index < 8; ++index) {
        uint32_t color = 0xffffff;

        if (index == 0) {
            color = failed ? 0xff6666 : (running ? 0x88ee88 : 0xffcc33);
        } else if (index == 7) {
            color = 0xdddddd;
        }
        kms_draw_text(&kms_state, x, y + (uint32_t)index * line_h,
                      lines[index],
                      color,
                      shrink_text_scale(lines[index], scale, card_w - scale * 2));
    }

    if (kms_present_frame("cpustress") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int wait_for_menu_return(struct key_wait_context *ctx, const char *tag) {
    struct input_gesture gesture;
    int wait_rc = wait_for_input_gesture(ctx, tag, &gesture);

    if (wait_rc < 0) {
        return wait_rc;
    }
    return 0;
}

static void restore_auto_hud_if_needed(bool restore_hud) {
    if (restore_hud) {
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) < 0) {
            native_logf("screenmenu", "autohud restore failed errno=%d error=%s",
                        errno, strerror(errno));
        }
    }
}

static int cmd_blindmenu(void) {
    static const struct blind_menu_item items[] = {
        { "resume", "return to shell prompt" },
        { "recovery", "reboot to TWRP recovery" },
        { "reboot", "restart device" },
        { "poweroff", "power off device" },
    };
    struct key_wait_context ctx;
    size_t selected = 0;
    size_t count = sizeof(items) / sizeof(items[0]);

    if (open_key_wait_context(&ctx, "blindmenu") < 0) {
        return negative_errno_or(ENOENT);
    }

    cprintf("blindmenu: VOLUP=prev VOLDOWN=next POWER=select dbl/COMBO=back q/Ctrl-C=cancel\r\n");
    cprintf("blindmenu: start with a safe default, then move as needed\r\n");
    print_blind_menu_selection(items, count, selected);

    while (1) {
        struct input_gesture gesture;
        enum input_menu_action menu_action;

        int wait_rc = wait_for_input_gesture(&ctx, "blindmenu", &gesture);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            return wait_rc;
        }

        menu_action = input_menu_action_from_gesture(&gesture);

        if (menu_action == INPUT_MENU_ACTION_PREV ||
            menu_action == INPUT_MENU_ACTION_PAGE_PREV) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_PREV ?
                          INPUT_PAGE_STEP : 1;

            selected = (selected + count - (step % count)) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_NEXT ||
            menu_action == INPUT_MENU_ACTION_PAGE_NEXT) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_NEXT ?
                          INPUT_PAGE_STEP : 1;

            selected = (selected + step) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_BACK ||
            menu_action == INPUT_MENU_ACTION_HIDE) {
            cprintf("blindmenu: leaving menu\r\n");
            close_key_wait_context(&ctx);
            return 0;
        }

        if (menu_action == INPUT_MENU_ACTION_RESERVED) {
            cprintf("blindmenu: reserved gesture ignored for safety\r\n");
            continue;
        }

        if (menu_action != INPUT_MENU_ACTION_SELECT) {
            cprintf("blindmenu: ignoring gesture %s\r\n",
                    input_gesture_name(gesture.id));
            continue;
        }

        cprintf("blindmenu: selected %s\r\n", items[selected].name);
        close_key_wait_context(&ctx);

        if (selected == 0) {
            cprintf("blindmenu: leaving menu\r\n");
            return 0;
        }
        if (selected == 1) {
            return cmd_recovery();
        }
        if (selected == 2) {
            sync();
            reboot(RB_AUTOBOOT);
            wf("/proc/sysrq-trigger", "b");
            return negative_errno_or(EIO);
        }

        sync();
        reboot(RB_POWER_OFF);
        return negative_errno_or(EIO);
    }

    close_key_wait_context(&ctx);
    return 0;
}

static int cmd_screenmenu(void) {
    struct key_wait_context ctx;
    enum screen_menu_page_id current_page = SCREEN_MENU_PAGE_MAIN;
    const struct screen_menu_page *page = screen_menu_get_page(current_page);
    size_t selected = 0;
    bool restore_hud;
    int draw_rc;

    reap_hud_child();
    restore_hud = hud_pid > 0;
    stop_auto_hud(false);

    if (open_key_wait_context(&ctx, "screenmenu") < 0) {
        restore_auto_hud_if_needed(restore_hud);
        return negative_errno_or(ENOENT);
    }

    cprintf("screenmenu: VOLUP=prev VOLDOWN=next POWER=select dbl/COMBO=back q/Ctrl-C=cancel\r\n");
    native_logf("screenmenu", "start restore_hud=%d", restore_hud ? 1 : 0);
    print_screen_menu_selection(page, selected);

    draw_rc = draw_screen_menu(page, selected);
    if (draw_rc < 0) {
        close_key_wait_context(&ctx);
        restore_auto_hud_if_needed(restore_hud);
        return draw_rc;
    }

    while (1) {
        struct input_gesture gesture;
        enum input_menu_action menu_action;
        int wait_rc = wait_for_input_gesture(&ctx, "screenmenu", &gesture);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return wait_rc;
        }

        menu_action = input_menu_action_from_gesture(&gesture);

        if (menu_action == INPUT_MENU_ACTION_PREV ||
            menu_action == INPUT_MENU_ACTION_PAGE_PREV) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_PREV ?
                          INPUT_PAGE_STEP : 1;

            page = screen_menu_get_page(current_page);
            selected = (selected + page->count - (step % page->count)) % page->count;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_NEXT ||
            menu_action == INPUT_MENU_ACTION_PAGE_NEXT) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_NEXT ?
                          INPUT_PAGE_STEP : 1;

            page = screen_menu_get_page(current_page);
            selected = (selected + step) % page->count;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_BACK) {
            page = screen_menu_get_page(current_page);
            if (current_page == SCREEN_MENU_PAGE_MAIN) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return 0;
            }
            current_page = page->parent;
            page = screen_menu_get_page(current_page);
            selected = 0;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_HIDE) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return 0;
        }

        if (menu_action == INPUT_MENU_ACTION_STATUS) {
            draw_rc = cmd_statushud();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            cprintf("screenmenu: status shortcut shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_LOG) {
            draw_rc = draw_screen_log_summary();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            cprintf("screenmenu: log shortcut shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_RESERVED) {
            cprintf("screenmenu: reserved gesture ignored for safety\r\n");
            continue;
        }

        if (menu_action != INPUT_MENU_ACTION_SELECT) {
            cprintf("screenmenu: ignoring gesture %s\r\n",
                    input_gesture_name(gesture.id));
            continue;
        }

        page = screen_menu_get_page(current_page);
        cprintf("screenmenu: selected %s / %s\r\n", page->title, page->items[selected].name);
        native_logf("screenmenu", "selected page=%s item=%s",
                    page->title, page->items[selected].name);

        if (page->items[selected].action == SCREEN_MENU_RESUME) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return 0;
        }

        if (page->items[selected].action == SCREEN_MENU_SUBMENU) {
            current_page = page->items[selected].target;
            page = screen_menu_get_page(current_page);
            selected = 0;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_BACK) {
            current_page = page->parent;
            page = screen_menu_get_page(current_page);
            selected = 0;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_STATUS) {
            draw_rc = cmd_statushud();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            cprintf("screenmenu: status shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_LOG) {
            draw_rc = draw_screen_log_summary();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            cprintf("screenmenu: log summary shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_NET_STATUS) {
            draw_rc = draw_screen_network_summary();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            cprintf("screenmenu: network shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_INPUT_MONITOR) {
            char *monitor_argv[] = { "inputmonitor", "0" };

            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return cmd_inputmonitor(monitor_argv, 2);
        }

        if (page->items[selected].action == SCREEN_MENU_DISPLAY_TEST) {
            draw_rc = draw_screen_display_test();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            cprintf("screenmenu: display test shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        {
            enum screen_app_id about_app = screen_menu_about_app(page->items[selected].action);

            if (about_app != SCREEN_APP_NONE) {
                draw_rc = draw_screen_about_app(about_app);
                if (draw_rc < 0) {
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(restore_hud);
                    return draw_rc;
                }
                cprintf("screenmenu: about shown, press any button to return\r\n");
                wait_rc = wait_for_menu_return(&ctx, "screenmenu");
                if (wait_rc < 0) {
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(restore_hud);
                    return wait_rc;
                }
                page = screen_menu_get_page(current_page);
                draw_rc = draw_screen_menu(page, selected);
                if (draw_rc < 0) {
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(restore_hud);
                    return draw_rc;
                }
                continue;
            }
        }

        if (screen_menu_cpu_stress_seconds(page->items[selected].action) > 0) {
            draw_rc = draw_screen_cpu_hint();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            cprintf("screenmenu: CPU stress help shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        close_key_wait_context(&ctx);

        if (page->items[selected].action == SCREEN_MENU_RECOVERY) {
            return cmd_recovery();
        }
        if (page->items[selected].action == SCREEN_MENU_REBOOT) {
            cprintf("screenmenu: syncing and restarting\r\n");
            sync();
            reboot(RB_AUTOBOOT);
            wf("/proc/sysrq-trigger", "b");
            return negative_errno_or(EIO);
        }

        cprintf("screenmenu: syncing and powering off\r\n");
        sync();
        reboot(RB_POWER_OFF);
        return negative_errno_or(EIO);
    }
}

static int ensure_tty_node(void) {
    char devbuf[32];
    unsigned int major_num;
    unsigned int minor_num;

    if (access("/dev/ttyGS0", F_OK) == 0) {
        return 0;
    }
    if (read_text_file("/sys/class/tty/ttyGS0/dev", devbuf, sizeof(devbuf)) < 0) {
        return -1;
    }
    if (sscanf(devbuf, "%u:%u", &major_num, &minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    if (mknod("/dev/ttyGS0", S_IFCHR | 0600, makedev(major_num, minor_num)) == 0 ||
        errno == EEXIST) {
        return 0;
    }
    return -1;
}

static int wait_for_tty_gs0(void) {
    int attempt;

    for (attempt = 0; attempt < 50; ++attempt) {
        if (access("/dev/ttyGS0", F_OK) == 0) {
            return 0;
        }
        if (access("/sys/class/tty/ttyGS0/dev", R_OK) == 0 && ensure_tty_node() == 0) {
            return 0;
        }
        usleep(200000);
    }

    errno = ENOENT;
    return -1;
}

static int ensure_char_node_exact(const char *path, unsigned int major_num, unsigned int minor_num) {
    dev_t wanted = makedev(major_num, minor_num);
    struct stat st;

    if (lstat(path, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == wanted) {
            return 0;
        }
        if (unlink(path) < 0) {
            return -1;
        }
    } else if (errno != ENOENT) {
        return -1;
    }

    if (mknod(path, S_IFCHR | 0600, wanted) == 0 || errno == EEXIST) {
        return 0;
    }

    return -1;
}

static int setup_base_mounts(void) {
    ensure_dir("/proc", 0755);
    ensure_dir("/sys", 0755);
    ensure_dir("/dev", 0755);
    ensure_dir("/tmp", 0755);
    ensure_dir("/cache", 0755);
    ensure_dir("/config", 0755);
    ensure_dir("/mnt", 0755);
    ensure_dir("/dev/block", 0755);

    mount("proc", "/proc", "proc", 0, NULL);
    mount("sysfs", "/sys", "sysfs", 0, NULL);
    mount("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755");
    mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777");
    ensure_char_node_exact("/dev/null", 1, 3);
    ensure_char_node_exact("/dev/zero", 1, 5);

    return 0;
}

static int mount_cache(void) {
    char node_path[PATH_MAX];

    if (get_block_device_path("sda31", node_path, sizeof(node_path)) < 0) {
        return -1;
    }

    if (mount(node_path, "/cache", "ext4", 0, NULL) == 0) {
        return 0;
    }
    return -1;
}

static int create_symlink(const char *target, const char *linkpath) {
    if (symlink(target, linkpath) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
}

static bool path_exists(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0;
}

static int ensure_block_node(const char *path, unsigned int major_num, unsigned int minor_num) {
    dev_t wanted = makedev(major_num, minor_num);

    if (mknod(path, S_IFBLK | 0600, wanted) == 0) {
        return 0;
    }
    if (errno == EEXIST) {
        struct stat st;

        if (lstat(path, &st) == 0 &&
            S_ISBLK(st.st_mode) &&
            st.st_rdev == wanted) {
            return 0;
        }

        if (unlink(path) < 0) {
            return -1;
        }
        if (mknod(path, S_IFBLK | 0600, wanted) == 0) {
            return 0;
        }
    }
    return -1;
}

static int bind_mount_dir(const char *src, const char *dst) {
    if (mount(src, dst, NULL, MS_BIND, NULL) == 0 || errno == EBUSY) {
        return 0;
    }
    return -1;
}

static int setup_acm_gadget(void) {
    if (mount("configfs", "/config", "configfs", 0, NULL) != 0 && errno != EBUSY) {
        return -1;
    }

    ensure_dir("/config/usb_gadget", 0770);
    ensure_dir("/config/usb_gadget/g1", 0770);
    ensure_dir("/config/usb_gadget/g1/strings", 0770);
    ensure_dir("/config/usb_gadget/g1/strings/0x409", 0770);
    ensure_dir("/config/usb_gadget/g1/configs", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1/strings", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0770);
    ensure_dir("/config/usb_gadget/g1/functions", 0770);
    ensure_dir("/config/usb_gadget/g1/functions/acm.usb0", 0770);

    wf("/config/usb_gadget/g1/idVendor", "0x04e8");
    wf("/config/usb_gadget/g1/idProduct", "0x6861");
    wf("/config/usb_gadget/g1/bcdUSB", "0x0200");
    wf("/config/usb_gadget/g1/bcdDevice", "0x0100");
    wf("/config/usb_gadget/g1/strings/0x409/serialnumber", "RFCM90CFWXA");
    wf("/config/usb_gadget/g1/strings/0x409/manufacturer", "samsung");
    wf("/config/usb_gadget/g1/strings/0x409/product", "SM8150-ACM");
    wf("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "serial");
    wf("/config/usb_gadget/g1/configs/b.1/MaxPower", "900");

    if (create_symlink("/config/usb_gadget/g1/functions/acm.usb0",
                       "/config/usb_gadget/g1/configs/b.1/f1") < 0) {
        return -1;
    }

    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    return 0;
}

static int attach_console(void) {
    int fd;
    struct termios tio;

    fd = open("/dev/ttyGS0", O_RDWR | O_NOCTTY);
    if (fd < 0) {
        return -1;
    }

    if (tcgetattr(fd, &tio) == 0) {
        tio.c_iflag = IGNBRK;
        tio.c_oflag = 0;
        tio.c_cflag &= ~(CSIZE | PARENB | CSTOPB | CRTSCTS);
        tio.c_cflag |= CS8 | CREAD | CLOCAL;
        tio.c_lflag = 0;
        tio.c_cc[VMIN] = 1;
        tio.c_cc[VTIME] = 0;
        cfsetispeed(&tio, B115200);
        cfsetospeed(&tio, B115200);
        tcsetattr(fd, TCSANOW, &tio);
        tcflush(fd, TCIOFLUSH);
    }

    console_fd = fd;
    dup2(fd, STDIN_FILENO);
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);

    return 0;
}

static void drain_console_input(unsigned int quiet_ms, unsigned int max_ms) {
    long started_ms = monotonic_millis();
    long quiet_started_ms = started_ms;

    while (1) {
        struct pollfd pfd;
        long now_ms = monotonic_millis();
        char ch;

        if (now_ms - started_ms >= (long)max_ms) {
            return;
        }
        if (now_ms - quiet_started_ms >= (long)quiet_ms) {
            return;
        }

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        pfd.revents = 0;

        if (poll(&pfd, 1, 20) <= 0 || (pfd.revents & POLLIN) == 0) {
            continue;
        }

        if (read(STDIN_FILENO, &ch, 1) == 1) {
            quiet_started_ms = monotonic_millis();
        }
    }
}

static long console_monotonic_millis(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }

    return (long)(ts.tv_sec * 1000L) + (long)(ts.tv_nsec / 1000000L);
}

static int reattach_console(const char *reason, bool announce) {
    int old_fd = console_fd;
    long now_ms = console_monotonic_millis();
    bool quiet_success = (strcmp(reason, "idle-timeout") == 0);

    if (now_ms > 0 &&
        last_console_reattach_ms > 0 &&
        now_ms - last_console_reattach_ms < 500) {
        return 0;
    }
    last_console_reattach_ms = now_ms;

    if (!quiet_success) {
        native_logf("console", "reattach requested reason=%s old_fd=%d",
                    reason, old_fd);
        klogf("<6>A90v77: console reattach requested reason=%s old_fd=%d\n",
              reason, old_fd);
    }

    if (old_fd >= 0) {
        close(old_fd);
    }
    console_fd = -1;

    if (wait_for_tty_gs0() < 0) {
        int saved_errno = errno;
        native_logf("console", "reattach wait failed reason=%s errno=%d error=%s",
                    reason, saved_errno, strerror(saved_errno));
        klogf("<6>A90v77: console reattach wait failed (%d)\n", saved_errno);
        errno = saved_errno;
        return -1;
    }

    if (attach_console() < 0) {
        int saved_errno = errno;
        native_logf("console", "reattach open failed reason=%s errno=%d error=%s",
                    reason, saved_errno, strerror(saved_errno));
        klogf("<6>A90v77: console reattach open failed (%d)\n", saved_errno);
        errno = saved_errno;
        return -1;
    }

    drain_console_input(50, 200);
    if (!quiet_success) {
        native_logf("console", "reattach ok reason=%s fd=%d", reason, console_fd);
        klogf("<6>A90v77: console reattached reason=%s fd=%d\n", reason, console_fd);
    }
    if (announce) {
        cprintf("\r\n# serial console reattached: %s\r\n", reason);
    }
    return 0;
}

static ssize_t read_line(char *buf, size_t buf_size) {
    static char pending_newline = '\0';
    static long last_idle_reattach_ms = 0;
    size_t pos = 0;

    while (pos + 1 < buf_size) {
        struct pollfd pfd;
        int poll_rc;
        char ch;
        ssize_t rd;

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN | POLLHUP | POLLERR | POLLNVAL;
        pfd.revents = 0;

        poll_rc = poll(&pfd, 1, CONSOLE_POLL_TIMEOUT_MS);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (poll_rc == 0) {
            long now_ms = console_monotonic_millis();

            if (now_ms > 0 &&
                now_ms - last_idle_reattach_ms >= CONSOLE_IDLE_REATTACH_MS) {
                last_idle_reattach_ms = now_ms;
                if (reattach_console("idle-timeout", false) == 0) {
                    pending_newline = '\0';
                }
            }
            continue;
        }

        if ((pfd.revents & (POLLHUP | POLLERR | POLLNVAL)) != 0) {
            if (reattach_console("poll-fault", true) < 0) {
                return -1;
            }
            pending_newline = '\0';
            continue;
        }
        if ((pfd.revents & POLLIN) == 0) {
            continue;
        }

        rd = read(STDIN_FILENO, &ch, 1);

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (reattach_console("read-error", true) == 0) {
                pending_newline = '\0';
                continue;
            }
            return -1;
        }
        if (rd == 0) {
            if (reattach_console("read-eof", true) == 0) {
                pending_newline = '\0';
            }
            continue;
        }

        if (pending_newline != '\0' && ch == pending_newline) {
            pending_newline = '\0';
            continue;
        }
        pending_newline = '\0';

        if (ch == '\r' || ch == '\n') {
            pending_newline = (ch == '\r') ? '\n' : '\r';
            write_all(console_fd, "\r\n", 2);
            break;
        }

        if (ch == 0x7f || ch == 0x08) {
            if (pos > 0) {
                pos--;
                write_all(console_fd, "\b \b", 3);
            }
            continue;
        }

        if (ch == 0x03) {
            write_all(console_fd, "^C\r\n", 4);
            pos = 0;
            break;
        }

        if (ch == 0x15) {
            while (pos > 0) {
                --pos;
                write_all(console_fd, "\b \b", 3);
            }
            continue;
        }

        if (ch == 0x1b) {
            consume_escape_sequence();
            continue;
        }

        if ((unsigned char)ch < 0x20) {
            continue;
        }

        buf[pos++] = ch;
        write_all(console_fd, &ch, 1);
    }

    buf[pos] = '\0';
    return (ssize_t)pos;
}

static int split_args(char *line, char **argv, int argv_max) {
    int argc = 0;
    char *cursor = line;

    while (*cursor != '\0' && argc < argv_max - 1) {
        while (*cursor == ' ' || *cursor == '\t') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        if (*cursor == '#') {
            break;
        }

        argv[argc++] = cursor;

        while (*cursor != '\0' && *cursor != ' ' && *cursor != '\t') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        *cursor++ = '\0';
    }

    argv[argc] = NULL;
    return argc;
}

static int hex_digit_value(char ch) {
    if (ch >= '0' && ch <= '9') {
        return ch - '0';
    }
    if (ch >= 'a' && ch <= 'f') {
        return ch - 'a' + 10;
    }
    if (ch >= 'A' && ch <= 'F') {
        return ch - 'A' + 10;
    }
    return -1;
}

static int parse_cmdv1x_token(const char *token,
                              char *buf,
                              size_t buf_size,
                              size_t *buf_pos,
                              char **arg_out) {
    const char *cursor = token;
    const char *hex;
    size_t length = 0;
    size_t hex_len;
    size_t index;

    if (*cursor < '0' || *cursor > '9') {
        return -EINVAL;
    }
    while (*cursor >= '0' && *cursor <= '9') {
        size_t digit = (size_t)(*cursor - '0');

        if (length > (SIZE_MAX - digit) / 10) {
            return -EOVERFLOW;
        }
        length = length * 10 + digit;
        ++cursor;
    }
    if (*cursor != ':') {
        return -EINVAL;
    }

    hex = cursor + 1;
    hex_len = strlen(hex);
    if (length > SIZE_MAX / 2 || hex_len != length * 2) {
        return -EINVAL;
    }
    if (length + 1 > buf_size || *buf_pos > buf_size - length - 1) {
        return -E2BIG;
    }

    *arg_out = buf + *buf_pos;
    for (index = 0; index < length; ++index) {
        int high = hex_digit_value(hex[index * 2]);
        int low = hex_digit_value(hex[index * 2 + 1]);
        unsigned int value;

        if (high < 0 || low < 0) {
            return -EINVAL;
        }
        value = (unsigned int)((high << 4) | low);
        if (value == 0) {
            return -EINVAL;
        }
        buf[(*buf_pos)++] = (char)value;
    }
    buf[(*buf_pos)++] = '\0';
    return 0;
}

static int decode_cmdv1x_args(char **tokens,
                              int token_count,
                              char **argv,
                              int argv_max,
                              char *buf,
                              size_t buf_size) {
    int index;
    size_t buf_pos = 0;

    if (token_count <= 0 || token_count >= argv_max) {
        return -EINVAL;
    }

    for (index = 0; index < token_count; ++index) {
        int result = parse_cmdv1x_token(tokens[index],
                                        buf,
                                        buf_size,
                                        &buf_pos,
                                        &argv[index]);

        if (result < 0) {
            argv[0] = NULL;
            return result;
        }
    }

    argv[token_count] = NULL;
    if (argv[0][0] == '\0') {
        return -EINVAL;
    }
    return token_count;
}

static const char *skip_shell_space(const char *line) {
    while (*line == ' ' || *line == '\t') {
        ++line;
    }
    return line;
}

static bool is_at_noise_tail_char(char ch) {
    if (ch == ' ' || ch == '\t') {
        return true;
    }
    if (ch >= 'A' && ch <= 'Z') {
        return true;
    }
    if (ch >= '0' && ch <= '9') {
        return true;
    }
    switch (ch) {
    case '+':
    case '-':
    case '&':
    case '=':
    case '?':
    case '#':
    case '*':
    case '/':
    case '\\':
    case '.':
    case ',':
    case ';':
    case ':':
    case '^':
    case '!':
    case '%':
    case '(':
    case ')':
    case '[':
    case ']':
    case '<':
    case '>':
        return true;
    default:
        return false;
    }
}

static bool is_unsolicited_at_fragment_noise(const char *line) {
    const char *cursor = skip_shell_space(line);
    size_t length = 0;

    if (*cursor == '\0') {
        return false;
    }

    while (*cursor != '\0') {
        if (*cursor != 'A' && *cursor != 'T') {
            return false;
        }
        ++length;
        if (length > 8) {
            return false;
        }
        ++cursor;
    }

    return true;
}

static bool is_unsolicited_at_noise(const char *line) {
    const char *cursor = skip_shell_space(line);

    if (cursor[0] != 'A' || cursor[1] != 'T') {
        return false;
    }

    cursor += 2;
    if (*cursor == '\0') {
        return true;
    }

    while (*cursor != '\0') {
        if (!is_at_noise_tail_char(*cursor)) {
            return false;
        }
        ++cursor;
    }

    return true;
}

static void print_prompt(void) {
    char cwd[PATH_MAX];

    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        strcpy(cwd, "/");
    }

    cprintf("a90:%s# ", cwd);
}

static int cmd_pwd(void) {
    char cwd[PATH_MAX];

    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        cprintf("pwd: %s\r\n", strerror(errno));
        return negative_errno_or(ENOENT);
    }

    cprintf("%s\r\n", cwd);
    return 0;
}

static void cmd_help(void) {
    cprintf("help\r\n");
    cprintf("version\r\n");
    cprintf("status\r\n");
    cprintf("last\r\n");
    cprintf("logpath\r\n");
    cprintf("logcat\r\n");
    cprintf("timeline\r\n");
    cprintf("bootstatus\r\n");
    cprintf("blocking commands: q or Ctrl-C cancels\r\n");
    cprintf("uname\r\n");
    cprintf("pwd\r\n");
    cprintf("cd <dir>\r\n");
    cprintf("ls [dir]\r\n");
    cprintf("cat <file>\r\n");
    cprintf("stat <path>\r\n");
    cprintf("mounts\r\n");
    cprintf("mountsystem [ro|rw]\r\n");
    cprintf("mountsd [status|ro|rw|off|init]\r\n");
    cprintf("prepareandroid\r\n");
    cprintf("inputinfo [eventX]\r\n");
    cprintf("drminfo [entry]\r\n");
    cprintf("fbinfo [fbX]\r\n");
    cprintf("kmsprobe\r\n");
    cprintf("kmssolid [color]\r\n");
    cprintf("kmsframe\r\n");
    cprintf("statusscreen\r\n");
    cprintf("statushud\r\n");
    cprintf("watchhud [sec] [count]\r\n");
    cprintf("autohud [sec]\r\n");
    cprintf("stophud\r\n");
    cprintf("redraw\r\n");
    cprintf("testpattern\r\n");
    cprintf("clear\r\n");
    cprintf("inputcaps <eventX>\r\n");
    cprintf("readinput <eventX> [count]\r\n");
    cprintf("waitkey [count]\r\n");
    cprintf("inputlayout\r\n");
    cprintf("waitgesture [count]\r\n");
    cprintf("inputmonitor [events]\r\n");
    cprintf("displaytest [0-3|colors|font|safe|layout]\r\n");
    cprintf("cutoutcal [x y size]\r\n");
    cprintf("menu\r\n");
    cprintf("screenmenu\r\n");
    cprintf("cmdv1 <command> [args...]\r\n");
    cprintf("cmdv1x <len:hex-utf8-arg>...\r\n");
    cprintf("blindmenu\r\n");
    cprintf("mkdir <dir>\r\n");
    cprintf("mknodc <path> <major> <minor>\r\n");
    cprintf("mknodb <path> <major> <minor>\r\n");
    cprintf("mountfs <src> <dst> <type> [ro]\r\n");
    cprintf("umount <path>\r\n");
    cprintf("echo <text>\r\n");
    cprintf("writefile <path> <value...>\r\n");
    cprintf("cpustress [sec] [workers]\r\n");
    cprintf("run <path> [args...]\r\n");
    cprintf("runandroid <path> [args...]\r\n");
    cprintf("startadbd\r\n");
    cprintf("stopadbd\r\n");
    cprintf("netservice [status|start|stop|enable|disable]\r\n");
    cprintf("reattach\r\n");
    cprintf("usbacmreset\r\n");
    cprintf("sync\r\n");
    cprintf("reboot\r\n");
    cprintf("recovery\r\n");
    cprintf("poweroff\r\n");
}

static int cmd_uname(void) {
    struct utsname uts;

    if (uname(&uts) < 0) {
        cprintf("uname: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    cprintf("%s %s %s %s %s\r\n",
            uts.sysname, uts.nodename, uts.release, uts.version, uts.machine);
    return 0;
}

static void cmd_version(void) {
    struct utsname uts;

    cprintf("%s\r\n", INIT_BANNER);
    cprintf("%s\r\n", INIT_CREATOR);
    cprintf("version: %s build=%s\r\n", INIT_VERSION, INIT_BUILD);
    if (uname(&uts) == 0) {
        cprintf("kernel: %s %s %s\r\n", uts.sysname, uts.release, uts.machine);
    }
    if (kms_state.fd >= 0) {
        cprintf("display: %ux%u connector=%u crtc=%u fb=%u\r\n",
                kms_state.width,
                kms_state.height,
                kms_state.connector_id,
                kms_state.crtc_id,
                kms_state.fb_id[kms_state.current_buffer]);
    } else {
        cprintf("display: not initialized\r\n");
    }
}

static void cmd_status(void) {
    struct status_snapshot snapshot;
    char boot_summary[64];

    read_status_snapshot(&snapshot);
    timeline_boot_summary(boot_summary, sizeof(boot_summary));

    cprintf("init: %s\r\n", INIT_BANNER);
    cprintf("creator: %s\r\n", INIT_CREATOR);
    cprintf("boot: %s\r\n", boot_summary);
    cprintf("uptime: %ss  load=%s\r\n", snapshot.uptime, snapshot.loadavg);
    cprintf("battery: %s %s temp=%s voltage=%s\r\n",
            snapshot.battery_pct,
            snapshot.battery_status,
            snapshot.battery_temp,
            snapshot.battery_voltage);
    cprintf("power: now=%s avg=%s\r\n", snapshot.power_now, snapshot.power_avg);
    cprintf("thermal: cpu=%s %s gpu=%s %s\r\n",
            snapshot.cpu_temp,
            snapshot.cpu_usage,
            snapshot.gpu_temp,
            snapshot.gpu_usage);
    cprintf("memory: %s used\r\n", snapshot.memory);
    if (kms_state.fd >= 0) {
        cprintf("display: %ux%u connector=%u crtc=%u current_buffer=%u\r\n",
                kms_state.width,
                kms_state.height,
                kms_state.connector_id,
                kms_state.crtc_id,
                kms_state.current_buffer);
    } else {
        cprintf("display: not initialized\r\n");
    }
    cprintf("adbd: %s\r\n", adbd_pid > 0 ? "started" : "stopped");
    reap_hud_child();
    cprintf("autohud: %s\r\n", hud_pid > 0 ? "running" : "stopped");
    reap_tcpctl_child();
    cprintf("netservice: %s tcpctl=%s\r\n",
            netservice_enabled_flag() ? "enabled" : "disabled",
            tcpctl_pid > 0 ? "running" : "stopped");
    cmd_mountsd((char *[]){ "mountsd", "status" }, 2);
}

static void cpustress_worker(long deadline_ms, unsigned int worker_index) {
    volatile unsigned long long accumulator =
        0x9e3779b97f4a7c15ULL ^ ((unsigned long long)getpid() << 17) ^ worker_index;

    while (monotonic_millis() < deadline_ms) {
        int index;

        for (index = 0; index < 200000; ++index) {
            accumulator ^= accumulator << 7;
            accumulator ^= accumulator >> 9;
            accumulator += 0x9e3779b97f4a7c15ULL + (unsigned long long)index;
        }
    }

    (void)accumulator;
    _exit(0);
}

static void cpustress_stop_workers(pid_t *pids, unsigned int workers) {
    unsigned int index;

    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            kill(pids[index], SIGTERM);
        }
    }
    usleep(100000);
    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            kill(pids[index], SIGKILL);
        }
    }
    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            waitpid(pids[index], NULL, 0);
            pids[index] = -1;
        }
    }
}

static int cmd_cpustress(char **argv, int argc) {
    pid_t pids[16];
    long seconds = 10;
    long workers_long = 4;
    unsigned int workers;
    unsigned int started = 0;
    long deadline_ms;
    int exit_code = 0;
    unsigned int index;

    if (argc > 1) {
        seconds = strtol(argv[1], NULL, 10);
    }
    if (argc > 2) {
        workers_long = strtol(argv[2], NULL, 10);
    }
    if (argc > 3 || seconds < 1 || seconds > 120 || workers_long < 1 || workers_long > 16) {
        cprintf("usage: cpustress [sec 1-120] [workers 1-16]\r\n");
        return -EINVAL;
    }

    workers = (unsigned int)workers_long;
    for (index = 0; index < workers; ++index) {
        pids[index] = -1;
    }

    deadline_ms = monotonic_millis() + seconds * 1000L;
    cprintf("cpustress: workers=%u sec=%ld, q/Ctrl-C cancels\r\n", workers, seconds);

    for (index = 0; index < workers; ++index) {
        pid_t pid = fork();

        if (pid < 0) {
            int saved_errno = errno;
            cprintf("cpustress: fork worker %u: %s\r\n", index, strerror(saved_errno));
            cpustress_stop_workers(pids, started);
            return -saved_errno;
        }
        if (pid == 0) {
            cpustress_worker(deadline_ms, index);
        }
        pids[index] = pid;
        ++started;
    }

    while (started > 0) {
        enum cancel_kind cancel;

        for (index = 0; index < workers; ++index) {
            if (pids[index] > 0) {
                int status;
                pid_t got = waitpid(pids[index], &status, WNOHANG);

                if (got == pids[index]) {
                    pids[index] = -1;
                    --started;
                    if (WIFSIGNALED(status)) {
                        exit_code = -EINTR;
                    }
                }
            }
        }
        if (started == 0) {
            break;
        }

        cancel = poll_console_cancel(100);
        if (cancel != CANCEL_NONE) {
            cpustress_stop_workers(pids, workers);
            return command_cancelled("cpustress", cancel);
        }

        if (monotonic_millis() > deadline_ms + 2000L) {
            cpustress_stop_workers(pids, workers);
            cprintf("cpustress: timeout cleanup\r\n");
            return -ETIMEDOUT;
        }
    }

    cprintf("cpustress: done workers=%u sec=%ld\r\n", workers, seconds);
    return exit_code;
}

static int cmd_ls(const char *path) {
    DIR *dir;
    struct dirent *entry;
    int first_error = 0;

    dir = opendir(path);
    if (dir == NULL) {
        cprintf("ls: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    while ((entry = readdir(dir)) != NULL) {
        char full[PATH_MAX];
        struct stat st;
        char type = '?';

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }

        if (snprintf(full, sizeof(full), "%s/%s", path, entry->d_name) >= (int)sizeof(full)) {
            continue;
        }

        if (lstat(full, &st) == 0) {
            if (S_ISDIR(st.st_mode)) {
                type = 'd';
            } else if (S_ISLNK(st.st_mode)) {
                type = 'l';
            } else if (S_ISCHR(st.st_mode)) {
                type = 'c';
            } else if (S_ISBLK(st.st_mode)) {
                type = 'b';
            } else if (S_ISREG(st.st_mode)) {
                type = '-';
            }
            cprintf("%c %8ld %s\r\n", type, (long)st.st_size, entry->d_name);
        } else {
            cprintf("? ???????? %s\r\n", entry->d_name);
            if (first_error == 0) {
                first_error = negative_errno_or(EIO);
            }
        }
    }

    closedir(dir);
    return first_error;
}

static int cmd_cat(const char *path) {
    char buf[512];
    int fd = open(path, O_RDONLY);

    if (fd < 0) {
        cprintf("cat: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    while (1) {
        ssize_t rd = read(fd, buf, sizeof(buf));
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            cprintf("cat: %s: %s\r\n", path, strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }
        if (rd == 0) {
            break;
        }
        write_all(console_fd, buf, (size_t)rd);
    }

    close(fd);
    cprintf("\r\n");
    return 0;
}

static int cmd_logpath(void) {
    cprintf("log: path=%s ready=%s max=%d\r\n",
            native_log_current_path(),
            native_log_ready ? "yes" : "no",
            NATIVE_LOG_MAX_BYTES);
    return native_log_ready ? 0 : -EIO;
}

static int cmd_logcat(void) {
    if (!native_log_ready) {
        cprintf("logcat: log is not ready\r\n");
        return -ENOENT;
    }
    return cmd_cat(native_log_path);
}

static int cmd_timeline(void) {
    size_t index;

    cprintf("timeline: count=%ld max=%d\r\n",
            (long)boot_timeline_count,
            BOOT_TIMELINE_MAX);

    for (index = 0; index < boot_timeline_count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct boot_timeline_entry *entry = &boot_timeline[index];

        cprintf("%02ld %8ldms %-18s rc=%d errno=%d %s\r\n",
                (long)index,
                entry->ms,
                entry->step,
                entry->code,
                entry->saved_errno,
                entry->detail);
    }

    return boot_timeline_count > 0 ? 0 : -ENOENT;
}

static int cmd_bootstatus(void) {
    char summary[64];

    timeline_boot_summary(summary, sizeof(summary));
    cprintf("boot: %s\r\n", summary);
    cprintf("timeline_entries: %ld/%d\r\n",
            (long)boot_timeline_count,
            BOOT_TIMELINE_MAX);
    return boot_timeline_count > 0 ? 0 : -ENOENT;
}

static int cmd_stat(const char *path) {
    struct stat st;

    if (lstat(path, &st) < 0) {
        cprintf("stat: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    cprintf("mode=0%o uid=%ld gid=%ld size=%ld\r\n",
            st.st_mode & 07777, (long)st.st_uid, (long)st.st_gid, (long)st.st_size);
    if (S_ISBLK(st.st_mode) || S_ISCHR(st.st_mode)) {
        cprintf("rdev=%u:%u\r\n", major(st.st_rdev), minor(st.st_rdev));
    }
    return 0;
}

static int cmd_mounts(void) {
    return cmd_cat("/proc/mounts");
}

static int cmd_mountsystem(bool read_only) {
    unsigned long flags = read_only ? MS_RDONLY : 0;
    char node_path[PATH_MAX];

    ensure_dir("/mnt", 0755);
    ensure_dir("/mnt/system", 0755);

    if (get_block_device_path("sda28", node_path, sizeof(node_path)) < 0) {
        cprintf("mountsystem: mknod failed: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    if (mount(node_path, "/mnt/system", "ext4", flags, NULL) < 0) {
        if (errno == EBUSY) {
            cprintf("mountsystem: already mounted\r\n");
            return 0;
        } else {
            cprintf("mountsystem: %s\r\n", strerror(errno));
        }
        return negative_errno_or(EIO);
    }

    cprintf("mountsystem: /mnt/system ready (%s)\r\n", read_only ? "ro" : "rw");
    return 0;
}

static bool mount_line_for_path(const char *path,
                                char *out,
                                size_t out_size,
                                bool *read_only_out) {
    FILE *fp;
    char line[512];

    if (out_size > 0) {
        out[0] = '\0';
    }
    if (read_only_out != NULL) {
        *read_only_out = false;
    }
    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return false;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char src[160];
        char dst[160];
        char type[64];
        char opts[192];

        if (sscanf(line, "%159s %159s %63s %191s", src, dst, type, opts) != 4) {
            continue;
        }
        if (strcmp(dst, path) == 0) {
            if (out_size > 0) {
                snprintf(out, out_size, "%s", line);
            }
            if (read_only_out != NULL) {
                char opt_copy[192];
                char *token;
                char *saveptr = NULL;

                snprintf(opt_copy, sizeof(opt_copy), "%s", opts);
                for (token = strtok_r(opt_copy, ",", &saveptr);
                     token != NULL;
                     token = strtok_r(NULL, ",", &saveptr)) {
                    if (strcmp(token, "ro") == 0) {
                        *read_only_out = true;
                        break;
                    }
                }
            }
            fclose(fp);
            return true;
        }
    }
    fclose(fp);
    return false;
}

static int ensure_sd_workspace(void) {
    static const char *dirs[] = {
        SD_WORKSPACE_DIR,
        SD_WORKSPACE_DIR "/bin",
        SD_WORKSPACE_DIR "/logs",
        SD_WORKSPACE_DIR "/tmp",
        SD_WORKSPACE_DIR "/rootfs",
        SD_WORKSPACE_DIR "/images",
        SD_WORKSPACE_DIR "/backups",
    };
    size_t index;

    for (index = 0; index < SCREEN_MENU_COUNT(dirs); ++index) {
        if (ensure_dir(dirs[index], 0755) < 0) {
            int saved_errno = errno;

            cprintf("mountsd: mkdir %s: %s\r\n", dirs[index], strerror(saved_errno));
            return -saved_errno;
        }
    }
    return 0;
}

static int cmd_mountsd_status(void) {
    char node_path[PATH_MAX];
    char line[512];
    bool read_only = false;
    struct statvfs vfs;

    if (get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
        cprintf("mountsd: block=%s missing: %s\r\n", SD_BLOCK_NAME, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    cprintf("mountsd: block=%s path=%s fs=%s mount=%s\r\n",
            SD_BLOCK_NAME,
            node_path,
            SD_FS_TYPE,
            SD_MOUNT_POINT);
    if (!mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
        cprintf("mountsd: state=unmounted workspace=%s\r\n", SD_WORKSPACE_DIR);
        return 0;
    }
    cprintf("mountsd: state=mounted mode=%s workspace=%s\r\n",
            read_only ? "ro" : "rw",
            SD_WORKSPACE_DIR);
    cprintf("mountsd: %s", line);
    if (statvfs(SD_MOUNT_POINT, &vfs) == 0 && vfs.f_frsize > 0) {
        unsigned long long total = (unsigned long long)vfs.f_blocks *
                                   (unsigned long long)vfs.f_frsize;
        unsigned long long avail = (unsigned long long)vfs.f_bavail *
                                   (unsigned long long)vfs.f_frsize;

        cprintf("mountsd: size=%lluMB avail=%lluMB\r\n",
                total / (1024ULL * 1024ULL),
                avail / (1024ULL * 1024ULL));
    }
    return 0;
}

static int cmd_mountsd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "ro";
    char node_path[PATH_MAX];
    char line[512];
    bool read_only = false;
    unsigned long flags;
    int rc;

    if (argc > 2) {
        cprintf("usage: mountsd [status|ro|rw|off|init]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "status") == 0) {
        return cmd_mountsd_status();
    }
    if (strcmp(mode, "off") == 0) {
        if (!mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
            cprintf("mountsd: already unmounted\r\n");
            return 0;
        }
        if (umount(SD_MOUNT_POINT) < 0) {
            int saved_errno = errno;

            cprintf("mountsd: umount %s: %s\r\n",
                    SD_MOUNT_POINT,
                    strerror(saved_errno));
            return -saved_errno;
        }
        cprintf("mountsd: unmounted %s\r\n", SD_MOUNT_POINT);
        return 0;
    }
    if (strcmp(mode, "ro") != 0 &&
        strcmp(mode, "rw") != 0 &&
        strcmp(mode, "init") != 0) {
        cprintf("usage: mountsd [status|ro|rw|off|init]\r\n");
        return -EINVAL;
    }

    ensure_dir("/mnt", 0755);
    ensure_dir(SD_MOUNT_POINT, 0755);
    if (get_block_device_path(SD_BLOCK_NAME, node_path, sizeof(node_path)) < 0) {
        cprintf("mountsd: block=%s missing: %s\r\n", SD_BLOCK_NAME, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    flags = strcmp(mode, "ro") == 0 ? MS_RDONLY : 0;
    if (mount_line_for_path(SD_MOUNT_POINT, line, sizeof(line), &read_only)) {
        if (umount(SD_MOUNT_POINT) < 0) {
            int saved_errno = errno;

            cprintf("mountsd: remount umount %s: %s\r\n",
                    SD_MOUNT_POINT,
                    strerror(saved_errno));
            return -saved_errno;
        }
    }
    if (mount(node_path, SD_MOUNT_POINT, SD_FS_TYPE, flags, NULL) < 0) {
        int saved_errno = errno;

        cprintf("mountsd: mount %s on %s as %s: %s\r\n",
                node_path,
                SD_MOUNT_POINT,
                SD_FS_TYPE,
                strerror(saved_errno));
        return -saved_errno;
    }
    cprintf("mountsd: %s ready (%s)\r\n",
            SD_MOUNT_POINT,
            flags & MS_RDONLY ? "ro" : "rw");
    if (strcmp(mode, "init") == 0) {
        rc = ensure_sd_workspace();
        if (rc < 0) {
            return rc;
        }
        cprintf("mountsd: workspace ready %s\r\n", SD_WORKSPACE_DIR);
    }
    return 0;
}

static int prepare_android_layout(bool verbose) {
    ensure_dir("/mnt", 0755);
    ensure_dir("/mnt/system", 0755);

    if (!path_exists("/mnt/system/system")) {
        char node_path[PATH_MAX];

        if (get_block_device_path("sda28", node_path, sizeof(node_path)) < 0) {
            if (verbose) {
                cprintf("prepareandroid: sda28 mknod failed: %s\r\n", strerror(errno));
            }
            return -1;
        }
        if (mount(node_path, "/mnt/system", "ext4", MS_RDONLY, NULL) < 0 &&
            errno != EBUSY) {
            if (verbose) {
                cprintf("prepareandroid: mountsystem failed: %s\r\n", strerror(errno));
            }
            return -1;
        }
    }

    ensure_dir("/system", 0755);
    ensure_dir("/apex", 0755);
    ensure_dir("/data", 0755);
    ensure_dir("/dev/usb-ffs", 0755);
    ensure_dir("/dev/usb-ffs/adb", 0755);
    ensure_dir("/dev/socket", 0755);

    if (bind_mount_dir("/mnt/system/system", "/system") < 0) {
        if (verbose) {
            cprintf("prepareandroid: bind /system failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/linkerconfig") &&
        create_symlink("/mnt/system/linkerconfig", "/linkerconfig") < 0) {
        if (verbose) {
            cprintf("prepareandroid: linkerconfig symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/vendor") &&
        create_symlink("/mnt/system/vendor", "/vendor") < 0) {
        if (verbose) {
            cprintf("prepareandroid: vendor symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/product") &&
        create_symlink("/mnt/system/product", "/product") < 0) {
        if (verbose) {
            cprintf("prepareandroid: product symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/odm") &&
        create_symlink("/mnt/system/odm", "/odm") < 0) {
        if (verbose) {
            cprintf("prepareandroid: odm symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/mnt/system/system_ext") &&
        create_symlink("/mnt/system/system_ext", "/system_ext") < 0) {
        if (verbose) {
            cprintf("prepareandroid: system_ext symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/system/apex/com.android.runtime") &&
        create_symlink("/system/apex/com.android.runtime", "/apex/com.android.runtime") < 0) {
        if (verbose) {
            cprintf("prepareandroid: runtime apex symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/system/apex/com.android.adbd") &&
        create_symlink("/system/apex/com.android.adbd", "/apex/com.android.adbd") < 0) {
        if (verbose) {
            cprintf("prepareandroid: adbd apex symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    if (path_exists("/system/apex/com.android.tzdata") &&
        create_symlink("/system/apex/com.android.tzdata", "/apex/com.android.tzdata") < 0) {
        if (verbose) {
            cprintf("prepareandroid: tzdata apex symlink failed: %s\r\n", strerror(errno));
        }
        return -1;
    }

    return 0;
}

static int cmd_prepareandroid(void) {
    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }
    cprintf("prepareandroid: ready\r\n");
    return 0;
}

static void cmd_echo(char **argv, int argc) {
    int index;

    for (index = 1; index < argc; ++index) {
        if (index > 1) {
            cprintf(" ");
        }
        cprintf("%s", argv[index]);
    }
    cprintf("\r\n");
}

static int cmd_writefile(char **argv, int argc) {
    const char *path;
    int fd;
    int index;

    if (argc < 3) {
        cprintf("usage: writefile <path> <value...>\r\n");
        return -EINVAL;
    }

    path = argv[1];
    fd = open(path, O_WRONLY);
    if (fd < 0) {
        cprintf("writefile: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    for (index = 2; index < argc; ++index) {
        if (index > 2) {
            if (write_all_checked(fd, " ", 1) < 0) {
                cprintf("writefile: %s: %s\r\n", path, strerror(errno));
                close(fd);
                return negative_errno_or(EIO);
            }
        }
        if (write_all_checked(fd, argv[index], strlen(argv[index])) < 0) {
            cprintf("writefile: %s: %s\r\n", path, strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }
    }
    if (close(fd) < 0) {
        cprintf("writefile: %s: close: %s\r\n", path, strerror(errno));
        return negative_errno_or(EIO);
    }
    cprintf("writefile: ok\r\n");
    return 0;
}

static int report_child_status(const char *tag, int status) {
    if (WIFEXITED(status)) {
        int exit_code = WEXITSTATUS(status);

        cprintf("[exit %d]\r\n", exit_code);
        return exit_code;
    } else if (WIFSIGNALED(status)) {
        int signal_num = WTERMSIG(status);

        cprintf("[signal %d]\r\n", signal_num);
        return 128 + signal_num;
    }

    cprintf("%s: unknown child status\r\n", tag);
    return -ECHILD;
}

static void terminate_child_for_cancel(pid_t pid, const char *tag) {
    int attempt;
    int status;

    cprintf("%s: terminating pid=%ld\r\n", tag, (long)pid);
    kill(pid, SIGTERM);
    for (attempt = 0; attempt < 20; ++attempt) {
        pid_t got = waitpid(pid, &status, WNOHANG);

        if (got == pid) {
            return;
        }
        if (got < 0 && errno == ECHILD) {
            return;
        }
        usleep(100000);
    }

    cprintf("%s: SIGTERM timeout, sending SIGKILL\r\n", tag);
    kill(pid, SIGKILL);
    waitpid(pid, &status, 0);
}

static int wait_child_cancelable(pid_t pid, const char *tag, int *status_out) {
    while (1) {
        pid_t got = waitpid(pid, status_out, WNOHANG);
        enum cancel_kind cancel;

        if (got == pid) {
            return 0;
        }
        if (got < 0) {
            int saved_errno = errno;

            cprintf("%s: waitpid: %s\r\n", tag, strerror(saved_errno));
            return -saved_errno;
        }

        cancel = poll_console_cancel(100);
        if (cancel != CANCEL_NONE) {
            terminate_child_for_cancel(pid, tag);
            return command_cancelled(tag, cancel);
        }
    }
}

static int cmd_run(char **argv, int argc) {
    static char *const envp[] = {
        "PATH=/cache:/cache/bin:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        "LD_LIBRARY_PATH=/cache/adb/lib",
        NULL
    };
    pid_t pid;
    int status;

    if (argc < 2) {
        cprintf("usage: run <path> [args...]\r\n");
        return -EINVAL;
    }

    pid = fork();
    if (pid < 0) {
        cprintf("run: fork: %s\r\n", strerror(errno));
        return negative_errno_or(EAGAIN);
    }

    if (pid == 0) {
        dup2(console_fd, STDIN_FILENO);
        dup2(console_fd, STDOUT_FILENO);
        dup2(console_fd, STDERR_FILENO);
        execve(argv[1], &argv[1], envp);
        cprintf("run: execve(%s): %s\r\n", argv[1], strerror(errno));
        _exit(127);
    }

    cprintf("run: pid=%ld, q/Ctrl-C cancels\r\n", (long)pid);

    {
        int wait_rc = wait_child_cancelable(pid, "run", &status);

        if (wait_rc < 0) {
            return wait_rc;
        }
    }

    return report_child_status("run", status);
}

static int cmd_runandroid(char **argv, int argc) {
    static char *const envp[] = {
        "PATH=/system/bin:/system/xbin",
        "HOME=/",
        "TERM=vt100",
        "ANDROID_ROOT=/system",
        "ANDROID_DATA=/data",
        "LD_LIBRARY_PATH=/system/lib64:/apex/com.android.runtime/lib64/bionic:/system_ext/lib64:/product/lib64:/vendor/lib64:/odm/lib64",
        NULL
    };
    pid_t pid;
    int status;

    if (argc < 2) {
        cprintf("usage: runandroid <path> [args...]\r\n");
        return -EINVAL;
    }

    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }

    pid = fork();
    if (pid < 0) {
        cprintf("runandroid: fork: %s\r\n", strerror(errno));
        return negative_errno_or(EAGAIN);
    }

    if (pid == 0) {
        dup2(console_fd, STDIN_FILENO);
        dup2(console_fd, STDOUT_FILENO);
        dup2(console_fd, STDERR_FILENO);
        execve(argv[1], &argv[1], envp);
        cprintf("runandroid: execve(%s): %s\r\n", argv[1], strerror(errno));
        _exit(127);
    }

    cprintf("runandroid: pid=%ld, q/Ctrl-C cancels\r\n", (long)pid);

    {
        int wait_rc = wait_child_cancelable(pid, "runandroid", &status);

        if (wait_rc < 0) {
            return wait_rc;
        }
    }

    return report_child_status("runandroid", status);
}

static int ensure_adb_function(bool *needs_rebind) {
    int ret;

    ensure_dir("/config/usb_gadget/g1/functions/ffs.adb", 0770);
    ensure_dir("/dev/usb-ffs", 0755);
    ensure_dir("/dev/usb-ffs/adb", 0755);

    if (mount("adb", "/dev/usb-ffs/adb", "functionfs", 0, "uid=2000,gid=2000") < 0 &&
        errno != EBUSY) {
        return -1;
    }

    ret = symlink("/config/usb_gadget/g1/functions/ffs.adb",
                  "/config/usb_gadget/g1/configs/b.1/f2");
    if (ret == 0) {
        *needs_rebind = true;
        return 0;
    }
    if (errno == EEXIST) {
        *needs_rebind = false;
        return 0;
    }

    return -1;
}

static int cmd_startadbd(void) {
    static char *const envp[] = {
        "PATH=/system/bin:/system/xbin:/apex/com.android.adbd/bin",
        "HOME=/",
        "TERM=vt100",
        "ANDROID_ROOT=/system",
        "ANDROID_DATA=/data",
        "LD_LIBRARY_PATH=/system/apex/com.android.adbd/lib64:/system/lib64:/apex/com.android.runtime/lib64/bionic:/system_ext/lib64:/product/lib64:/vendor/lib64:/odm/lib64",
        NULL
    };
    bool needs_rebind = false;

    if (adbd_pid > 0) {
        cprintf("startadbd: already running pid=%ld\r\n", (long)adbd_pid);
        return 0;
    }

    if (prepare_android_layout(true) < 0) {
        return negative_errno_or(EIO);
    }

    if (ensure_adb_function(&needs_rebind) < 0) {
        cprintf("startadbd: functionfs setup failed: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    adbd_pid = fork();
    if (adbd_pid < 0) {
        cprintf("startadbd: fork failed: %s\r\n", strerror(errno));
        adbd_pid = -1;
        return negative_errno_or(EAGAIN);
    }

    if (adbd_pid == 0) {
        dup2(console_fd, STDIN_FILENO);
        dup2(console_fd, STDOUT_FILENO);
        dup2(console_fd, STDERR_FILENO);
        execve("/apex/com.android.adbd/bin/adbd",
               (char *const[]){
                   "/apex/com.android.adbd/bin/adbd",
                   "--root_seclabel=u:r:su:s0",
                   NULL
               },
               envp);
        cprintf("startadbd: execve failed: %s\r\n", strerror(errno));
        _exit(127);
    }

    if (needs_rebind) {
        cprintf("startadbd: rebinding USB, serial may reconnect\r\n");
        usleep(1000000);
        wf("/config/usb_gadget/g1/UDC", "");
        usleep(200000);
        wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
        usleep(500000);
        reattach_console("startadbd-rebind", true);
    }

    cprintf("startadbd: pid=%ld\r\n", (long)adbd_pid);
    return 0;
}

static int cmd_stopadbd(void) {
    if (adbd_pid <= 0) {
        cprintf("stopadbd: not running\r\n");
        return 0;
    }

    kill(adbd_pid, SIGTERM);
    waitpid(adbd_pid, NULL, 0);
    adbd_pid = -1;
    unlink("/config/usb_gadget/g1/configs/b.1/f2");
    umount("/dev/usb-ffs/adb");
    wf("/config/usb_gadget/g1/UDC", "");
    usleep(200000);
    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    usleep(500000);
    reattach_console("stopadbd-rebind", true);
    cprintf("stopadbd: done\r\n");
    return 0;
}

static int netservice_log_fd(void) {
    int fd = open(NETSERVICE_LOG_PATH,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC,
                  0644);

    if (fd >= 0) {
        dprintf(fd, "\n[%ldms] %s\n", monotonic_millis(), INIT_BANNER);
    }
    return fd;
}

static void netservice_redirect_stdio(void) {
    int null_fd = open("/dev/null", O_RDONLY | O_CLOEXEC);
    int log_fd = netservice_log_fd();

    if (null_fd >= 0) {
        dup2(null_fd, STDIN_FILENO);
        if (null_fd > STDERR_FILENO) {
            close(null_fd);
        }
    }

    if (log_fd >= 0) {
        dup2(log_fd, STDOUT_FILENO);
        dup2(log_fd, STDERR_FILENO);
        if (log_fd > STDERR_FILENO) {
            close(log_fd);
        }
    }
}

static int netservice_wait_child(pid_t pid,
                                 const char *tag,
                                 int timeout_ms,
                                 int *status_out) {
    long deadline = monotonic_millis() + timeout_ms;

    while (1) {
        pid_t got = waitpid(pid, status_out, WNOHANG);

        if (got == pid) {
            return 0;
        }
        if (got < 0) {
            int saved_errno = errno;
            native_logf("netservice", "%s waitpid failed errno=%d error=%s",
                        tag, saved_errno, strerror(saved_errno));
            return -saved_errno;
        }
        if (monotonic_millis() >= deadline) {
            native_logf("netservice", "%s timeout; killing pid=%ld",
                        tag, (long)pid);
            kill(pid, SIGKILL);
            waitpid(pid, status_out, 0);
            return -ETIMEDOUT;
        }
        usleep(100000);
    }
}

static int netservice_run_wait(char *const argv[],
                               const char *tag,
                               int timeout_ms) {
    pid_t pid = fork();
    int status = 0;
    int wait_rc;

    if (pid < 0) {
        int saved_errno = errno;
        native_logf("netservice", "%s fork failed errno=%d error=%s",
                    tag, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }

    if (pid == 0) {
        static char *const envp[] = {
            "PATH=/cache/bin:/cache:/bin:/system/bin",
            "HOME=/",
            "TERM=vt100",
            NULL
        };

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        netservice_redirect_stdio();
        execve(argv[0], argv, envp);
        dprintf(STDERR_FILENO, "%s: execve(%s): %s\n",
                tag, argv[0], strerror(errno));
        _exit(127);
    }

    wait_rc = netservice_wait_child(pid, tag, timeout_ms, &status);
    if (wait_rc < 0) {
        return wait_rc;
    }

    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
        native_logf("netservice", "%s ok", tag);
        return 0;
    }
    if (WIFEXITED(status)) {
        native_logf("netservice", "%s exit=%d", tag, WEXITSTATUS(status));
        return -EIO;
    }
    if (WIFSIGNALED(status)) {
        native_logf("netservice", "%s signal=%d", tag, WTERMSIG(status));
        return -EINTR;
    }

    native_logf("netservice", "%s unknown status=0x%x", tag, status);
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

    native_logf("netservice", "interface %s did not appear", ifname);
    return -ETIMEDOUT;
}

static void reap_tcpctl_child(void) {
    if (tcpctl_pid > 0 && waitpid(tcpctl_pid, NULL, WNOHANG) == tcpctl_pid) {
        native_logf("netservice", "tcpctl exited pid=%ld", (long)tcpctl_pid);
        tcpctl_pid = -1;
    }
}

static bool netservice_enabled_flag(void) {
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

static int netservice_set_flag(bool enabled) {
    int fd;

    if (!enabled) {
        if (unlink(NETSERVICE_FLAG_PATH) < 0 && errno != ENOENT) {
            int saved_errno = errno;
            cprintf("netservice: unlink %s: %s\r\n",
                    NETSERVICE_FLAG_PATH, strerror(saved_errno));
            return -saved_errno;
        }
        native_logf("netservice", "disabled flag removed");
        return 0;
    }

    fd = open(NETSERVICE_FLAG_PATH,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC,
              0644);
    if (fd < 0) {
        int saved_errno = errno;
        cprintf("netservice: open %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }
    if (write_all_checked(fd, "enabled\n", 8) < 0) {
        int saved_errno = errno;
        close(fd);
        cprintf("netservice: write %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }
    if (close(fd) < 0) {
        int saved_errno = errno;
        cprintf("netservice: close %s: %s\r\n",
                NETSERVICE_FLAG_PATH, strerror(saved_errno));
        return -saved_errno;
    }

    native_logf("netservice", "enabled flag written");
    return 0;
}

static int netservice_spawn_tcpctl(void) {
    pid_t pid;

    reap_tcpctl_child();
    if (tcpctl_pid > 0) {
        native_logf("netservice", "tcpctl already running pid=%ld", (long)tcpctl_pid);
        return 0;
    }

    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        native_logf("netservice", "tcpctl fork failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        return -saved_errno;
    }

    if (pid == 0) {
        static char *const argv[] = {
            NETSERVICE_TCPCTL_HELPER,
            "listen",
            NETSERVICE_TCP_PORT,
            NETSERVICE_TCP_IDLE_SECONDS,
            NETSERVICE_TCP_MAX_CLIENTS,
            NULL
        };
        static char *const envp[] = {
            "PATH=/cache/bin:/cache:/bin:/system/bin",
            "HOME=/",
            "TERM=vt100",
            NULL
        };

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        netservice_redirect_stdio();
        execve(argv[0], (char *const *)argv, envp);
        dprintf(STDERR_FILENO, "tcpctl: execve(%s): %s\n",
                argv[0], strerror(errno));
        _exit(127);
    }

    usleep(200000);
    if (waitpid(pid, NULL, WNOHANG) == pid) {
        native_logf("netservice", "tcpctl exited immediately pid=%ld", (long)pid);
        return -EIO;
    }

    tcpctl_pid = pid;
    native_logf("netservice", "tcpctl started pid=%ld port=%s",
                (long)tcpctl_pid, NETSERVICE_TCP_PORT);
    return 0;
}

static int netservice_start(void) {
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

    native_logf("netservice", "start requested");
    if (access(NETSERVICE_USB_HELPER, X_OK) < 0 ||
        access(NETSERVICE_TCPCTL_HELPER, X_OK) < 0 ||
        access(NETSERVICE_TOYBOX, X_OK) < 0) {
        int saved_errno = errno;
        native_logf("netservice", "required helper missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        return -ENOENT;
    }

    rc = netservice_run_wait(usbnet_argv, "a90_usbnet ncm", 15000);
    reattach_console("netservice-ncm", false);
    if (rc < 0) {
        return rc;
    }

    rc = netservice_wait_for_ifname(NETSERVICE_IFNAME, 5000);
    if (rc < 0) {
        return rc;
    }

    rc = netservice_run_wait(ifconfig_argv, "ifconfig ncm0", 5000);
    if (rc < 0) {
        return rc;
    }

    rc = netservice_spawn_tcpctl();
    if (rc < 0) {
        return rc;
    }

    timeline_record(0, 0, "netservice", "ncm=%s tcp=%s",
                    NETSERVICE_IFNAME, NETSERVICE_TCP_PORT);
    native_logf("netservice", "ready if=%s ip=%s port=%s",
                NETSERVICE_IFNAME, NETSERVICE_DEVICE_IP, NETSERVICE_TCP_PORT);
    return 0;
}

static int netservice_stop(void) {
    char *const usbnet_argv[] = {
        NETSERVICE_USB_HELPER,
        "off",
        NULL
    };
    int rc = 0;

    native_logf("netservice", "stop requested");
    reap_tcpctl_child();
    if (tcpctl_pid > 0) {
        kill(tcpctl_pid, SIGTERM);
        waitpid(tcpctl_pid, NULL, 0);
        native_logf("netservice", "tcpctl stopped pid=%ld", (long)tcpctl_pid);
        tcpctl_pid = -1;
    }

    if (access(NETSERVICE_USB_HELPER, X_OK) == 0) {
        rc = netservice_run_wait(usbnet_argv, "a90_usbnet off", 15000);
        reattach_console("netservice-off", false);
    }

    return rc;
}

static int cmd_netservice(char **argv, int argc) {
    const char *subcommand = argc >= 2 ? argv[1] : "status";
    bool enabled;
    int rc;

    reap_tcpctl_child();
    enabled = netservice_enabled_flag();

    if (strcmp(subcommand, "status") == 0) {
        cprintf("netservice: flag=%s enabled=%s\r\n",
                NETSERVICE_FLAG_PATH, enabled ? "yes" : "no");
        cprintf("netservice: if=%s ip=%s/%s tcp=%s idle=%ss max_clients=%s\r\n",
                NETSERVICE_IFNAME,
                NETSERVICE_DEVICE_IP,
                NETSERVICE_NETMASK,
                NETSERVICE_TCP_PORT,
                NETSERVICE_TCP_IDLE_SECONDS,
                NETSERVICE_TCP_MAX_CLIENTS);
        cprintf("netservice: helpers usbnet=%s tcpctl=%s toybox=%s\r\n",
                access(NETSERVICE_USB_HELPER, X_OK) == 0 ? "yes" : "no",
                access(NETSERVICE_TCPCTL_HELPER, X_OK) == 0 ? "yes" : "no",
                access(NETSERVICE_TOYBOX, X_OK) == 0 ? "yes" : "no");
        cprintf("netservice: ncm0=%s tcpctl=%s",
                access("/sys/class/net/" NETSERVICE_IFNAME, F_OK) == 0 ? "present" : "absent",
                tcpctl_pid > 0 ? "running" : "stopped");
        if (tcpctl_pid > 0) {
            cprintf(" pid=%ld", (long)tcpctl_pid);
        }
        cprintf("\r\n");
        cprintf("netservice: log=%s\r\n", NETSERVICE_LOG_PATH);
        return 0;
    }

    if (strcmp(subcommand, "start") == 0) {
        rc = netservice_start();
        cprintf("netservice: start %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "stop") == 0) {
        rc = netservice_stop();
        cprintf("netservice: stop %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "enable") == 0) {
        rc = netservice_set_flag(true);
        if (rc < 0) {
            return rc;
        }
        rc = netservice_start();
        cprintf("netservice: enable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    if (strcmp(subcommand, "disable") == 0) {
        int flag_rc = netservice_set_flag(false);
        rc = netservice_stop();
        if (flag_rc < 0) {
            return flag_rc;
        }
        cprintf("netservice: disable %s\r\n", rc == 0 ? "ok" : "failed");
        return rc;
    }

    cprintf("usage: netservice [status|start|stop|enable|disable]\r\n");
    return -EINVAL;
}

static int cmd_reattach(void) {
    if (reattach_console("command", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_usbacmreset(void) {
    cprintf("usbacmreset: rebinding ACM, serial may reconnect\r\n");
    wf("/config/usb_gadget/g1/UDC", "");
    usleep(300000);
    unlink("/config/usb_gadget/g1/configs/b.1/f2");
    setup_acm_gadget();
    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    usleep(700000);
    if (reattach_console("usbacmreset", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_recovery(void) {
    cprintf("recovery: syncing and rebooting to recovery\r\n");
    sync();
    syscall(SYS_reboot,
            LINUX_REBOOT_MAGIC1,
            LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART2,
            "recovery");
    cprintf("recovery: %s\r\n", strerror(errno));
    return negative_errno_or(EIO);
}

typedef int (*command_handler)(char **argv, int argc);

struct shell_command {
    const char *name;
    command_handler handler;
    const char *usage;
    unsigned int flags;
};

static long monotonic_millis(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }

    return (long)(ts.tv_sec * 1000L) + (long)(ts.tv_nsec / 1000000L);
}

static void save_last_result(const char *command,
                             int code,
                             int saved_errno,
                             long duration_ms,
                             unsigned int flags) {
    snprintf(last_result.command, sizeof(last_result.command), "%s", command);
    last_result.code = code;
    last_result.saved_errno = saved_errno;
    last_result.duration_ms = duration_ms;
    last_result.flags = flags;
}

static void print_shell_intro(void) {
    cprintf("# Type 'help' for commands. Serial input was flushed at attach.\r\n");
}

static void cmd_last(void) {
    cprintf("last: command=%s code=%d errno=%d duration=%ldms flags=0x%x\r\n",
            last_result.command,
            last_result.code,
            last_result.saved_errno,
            last_result.duration_ms,
            last_result.flags);
    if (last_result.saved_errno != 0) {
        cprintf("last: error=%s\r\n", strerror(last_result.saved_errno));
    }
}

static int handle_help(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cmd_help();
    return 0;
}

static int handle_cmdv1(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cprintf("usage: cmdv1 <command> [args...]\r\n");
    cprintf("cmdv1: emits A90P1 BEGIN/END records around one command\r\n");
    return -EINVAL;
}

static int handle_cmdv1x(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cprintf("usage: cmdv1x <len:hex-utf8-arg>...\r\n");
    cprintf("cmdv1x: cmdv1 with length-prefixed hex argv tokens\r\n");
    return -EINVAL;
}

static int handle_version(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cmd_version();
    return 0;
}

static int handle_status(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cmd_status();
    return 0;
}

static int handle_last(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cmd_last();
    return 0;
}

static int handle_logpath(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_logpath();
}

static int handle_logcat(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_logcat();
}

static int handle_timeline(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_timeline();
}

static int handle_bootstatus(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_bootstatus();
}

static int handle_uname(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_uname();
}

static int handle_pwd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_pwd();
}

static int handle_cd(char **argv, int argc) {
    const char *path = argc > 1 ? argv[1] : "/";

    if (chdir(path) < 0) {
        int saved_errno = errno;
        cprintf("cd: %s: %s\r\n", path, strerror(saved_errno));
        return -saved_errno;
    }

    return 0;
}

static int handle_ls(char **argv, int argc) {
    return cmd_ls(argc > 1 ? argv[1] : ".");
}

static int handle_cat(char **argv, int argc) {
    if (argc < 2) {
        cprintf("usage: cat <file>\r\n");
        return -EINVAL;
    }
    return cmd_cat(argv[1]);
}

static int handle_stat(char **argv, int argc) {
    if (argc < 2) {
        cprintf("usage: stat <path>\r\n");
        return -EINVAL;
    }
    return cmd_stat(argv[1]);
}

static int handle_mounts(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_mounts();
}

static int handle_mountsystem(char **argv, int argc) {
    bool read_only = true;

    if (argc > 1 && strcmp(argv[1], "rw") == 0) {
        read_only = false;
    } else if (argc > 1 && strcmp(argv[1], "ro") != 0) {
        cprintf("usage: mountsystem [ro|rw]\r\n");
        return -EINVAL;
    }
    return cmd_mountsystem(read_only);
}

static int handle_mountsd(char **argv, int argc) {
    return cmd_mountsd(argv, argc);
}

static int handle_prepareandroid(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_prepareandroid();
}

static int handle_inputinfo(char **argv, int argc) {
    return cmd_inputinfo(argv, argc);
}

static int handle_drminfo(char **argv, int argc) {
    return cmd_drminfo(argv, argc);
}

static int handle_fbinfo(char **argv, int argc) {
    return cmd_fbinfo(argv, argc);
}

static int handle_kmsprobe(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_kmsprobe();
}

static int handle_kmssolid(char **argv, int argc) {
    return cmd_kmssolid(argv, argc);
}

static int handle_kmsframe(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_kmsframe();
}

static int handle_statusscreen(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_statusscreen();
}

static int handle_statushud(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_statushud();
}

static int handle_displaytest(char **argv, int argc) {
    unsigned int page = 0;

    if (argc >= 2) {
        if (strcmp(argv[1], "colors") == 0 || strcmp(argv[1], "color") == 0) {
            page = 0;
        } else if (strcmp(argv[1], "font") == 0 || strcmp(argv[1], "wrap") == 0) {
            page = 1;
        } else if (strcmp(argv[1], "safe") == 0 || strcmp(argv[1], "grid") == 0) {
            page = 2;
        } else if (strcmp(argv[1], "layout") == 0 || strcmp(argv[1], "hud") == 0) {
            page = 3;
        } else if (sscanf(argv[1], "%u", &page) != 1 ||
                   page >= DISPLAY_TEST_PAGE_COUNT) {
            cprintf("usage: displaytest [0-3|colors|font|safe|layout]\r\n");
            return -EINVAL;
        }
    }

    cprintf("displaytest: drawing page %u/%u %s\r\n",
            page + 1,
            DISPLAY_TEST_PAGE_COUNT,
            display_test_page_title(page));
    return draw_screen_display_test_page(page);
}

static int handle_cutoutcal(char **argv, int argc) {
    struct cutout_calibration_state cal;

    cutout_calibration_init(&cal);
    if (argc == 4) {
        if (sscanf(argv[1], "%d", &cal.center_x) != 1 ||
            sscanf(argv[2], "%d", &cal.center_y) != 1 ||
            sscanf(argv[3], "%d", &cal.size) != 1) {
            cprintf("usage: cutoutcal [x y size]\r\n");
            return -EINVAL;
        }
    } else if (argc != 1) {
        cprintf("usage: cutoutcal [x y size]\r\n");
        return -EINVAL;
    }
    cutout_calibration_clamp(&cal);
    cprintf("cutoutcal: x=%d y=%d size=%d\r\n",
            cal.center_x,
            cal.center_y,
            cal.size);
    return draw_screen_cutout_calibration(&cal, false);
}

static int handle_watchhud(char **argv, int argc) {
    return cmd_watchhud(argv, argc);
}

static int handle_autohud(char **argv, int argc) {
    return cmd_autohud(argv, argc);
}

static int handle_stophud(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_stophud();
}

static int handle_clear(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_clear_display();
}

static int handle_inputcaps(char **argv, int argc) {
    return cmd_inputcaps(argv, argc);
}

static int handle_readinput(char **argv, int argc) {
    return cmd_readinput(argv, argc);
}

static int handle_waitkey(char **argv, int argc) {
    return cmd_waitkey(argv, argc);
}

static int handle_inputlayout(char **argv, int argc) {
    return cmd_inputlayout(argv, argc);
}

static int handle_waitgesture(char **argv, int argc) {
    return cmd_waitgesture(argv, argc);
}

static int handle_inputmonitor(char **argv, int argc) {
    return cmd_inputmonitor(argv, argc);
}

static int handle_blindmenu(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_blindmenu();
}

static int handle_screenmenu(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_screenmenu();
}

static int handle_mkdir(char **argv, int argc) {
    if (argc < 2) {
        cprintf("usage: mkdir <dir>\r\n");
        return -EINVAL;
    }
    if (mkdir(argv[1], 0755) < 0 && errno != EEXIST) {
        int saved_errno = errno;
        cprintf("mkdir: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_mknodc(char **argv, int argc) {
    unsigned int major_num;
    unsigned int minor_num;

    if (argc < 4) {
        cprintf("usage: mknodc <path> <major> <minor>\r\n");
        return -EINVAL;
    }
    if (sscanf(argv[2], "%u", &major_num) != 1 ||
        sscanf(argv[3], "%u", &minor_num) != 1) {
        cprintf("mknodc: invalid major/minor\r\n");
        return -EINVAL;
    }
    if (ensure_char_node(argv[1], major_num, minor_num) < 0) {
        int saved_errno = errno;
        cprintf("mknodc: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_mknodb(char **argv, int argc) {
    unsigned int major_num;
    unsigned int minor_num;

    if (argc < 4) {
        cprintf("usage: mknodb <path> <major> <minor>\r\n");
        return -EINVAL;
    }
    if (sscanf(argv[2], "%u", &major_num) != 1 ||
        sscanf(argv[3], "%u", &minor_num) != 1) {
        cprintf("mknodb: invalid major/minor\r\n");
        return -EINVAL;
    }
    if (mknod(argv[1], S_IFBLK | 0600,
              makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        int saved_errno = errno;
        cprintf("mknodb: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_mountfs(char **argv, int argc) {
    unsigned long flags = 0;

    if (argc < 4) {
        cprintf("usage: mountfs <src> <dst> <type> [ro]\r\n");
        return -EINVAL;
    }
    if (argc > 4 && strcmp(argv[4], "ro") == 0) {
        flags |= MS_RDONLY;
    } else if (argc > 4) {
        cprintf("usage: mountfs <src> <dst> <type> [ro]\r\n");
        return -EINVAL;
    }
    if (mount(argv[1], argv[2], argv[3], flags, NULL) < 0) {
        int saved_errno = errno;
        cprintf("mountfs: %s\r\n", strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_umount(char **argv, int argc) {
    if (argc < 2) {
        cprintf("usage: umount <path>\r\n");
        return -EINVAL;
    }
    if (umount(argv[1]) < 0) {
        int saved_errno = errno;
        cprintf("umount: %s: %s\r\n", argv[1], strerror(saved_errno));
        return -saved_errno;
    }
    return 0;
}

static int handle_echo(char **argv, int argc) {
    cmd_echo(argv, argc);
    return 0;
}

static int handle_writefile(char **argv, int argc) {
    return cmd_writefile(argv, argc);
}

static int handle_cpustress(char **argv, int argc) {
    return cmd_cpustress(argv, argc);
}

static int handle_run(char **argv, int argc) {
    return cmd_run(argv, argc);
}

static int handle_runandroid(char **argv, int argc) {
    return cmd_runandroid(argv, argc);
}

static int handle_startadbd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_startadbd();
}

static int handle_stopadbd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_stopadbd();
}

static int handle_netservice(char **argv, int argc) {
    return cmd_netservice(argv, argc);
}

static int handle_reattach(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_reattach();
}

static int handle_usbacmreset(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return cmd_usbacmreset();
}

static int handle_sync(char **argv, int argc) {
    (void)argv;
    (void)argc;
    sync();
    cprintf("synced\r\n");
    return 0;
}

static int handle_reboot(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cprintf("reboot: syncing and restarting\r\n");
    stop_auto_hud(false);
    sync();
    reboot(RB_AUTOBOOT);
    wf("/proc/sysrq-trigger", "b");
    return negative_errno_or(EIO);
}

static int handle_recovery(char **argv, int argc) {
    (void)argv;
    (void)argc;
    stop_auto_hud(false);
    return cmd_recovery();
}

static int handle_poweroff(char **argv, int argc) {
    (void)argv;
    (void)argc;
    cprintf("poweroff: syncing and powering off\r\n");
    stop_auto_hud(false);
    sync();
    reboot(RB_POWER_OFF);
    return negative_errno_or(EIO);
}

static const struct shell_command command_table[] = {
    { "help", handle_help, "help", CMD_NONE },
    { "cmdv1", handle_cmdv1, "cmdv1 <command> [args...]", CMD_NONE },
    { "cmdv1x", handle_cmdv1x, "cmdv1x <len:hex-utf8-arg>...", CMD_NONE },
    { "version", handle_version, "version", CMD_NONE },
    { "status", handle_status, "status", CMD_NONE },
    { "last", handle_last, "last", CMD_NONE },
    { "logpath", handle_logpath, "logpath", CMD_NONE },
    { "logcat", handle_logcat, "logcat", CMD_NONE },
    { "timeline", handle_timeline, "timeline", CMD_NONE },
    { "bootstatus", handle_bootstatus, "bootstatus", CMD_NONE },
    { "uname", handle_uname, "uname", CMD_NONE },
    { "pwd", handle_pwd, "pwd", CMD_NONE },
    { "cd", handle_cd, "cd <dir>", CMD_NONE },
    { "ls", handle_ls, "ls [dir]", CMD_NONE },
    { "cat", handle_cat, "cat <file>", CMD_NONE },
    { "stat", handle_stat, "stat <path>", CMD_NONE },
    { "mounts", handle_mounts, "mounts", CMD_NONE },
    { "mountsystem", handle_mountsystem, "mountsystem [ro|rw]", CMD_NONE },
    { "mountsd", handle_mountsd, "mountsd [status|ro|rw|off|init]", CMD_NONE },
    { "prepareandroid", handle_prepareandroid, "prepareandroid", CMD_NONE },
    { "inputinfo", handle_inputinfo, "inputinfo [eventX]", CMD_NONE },
    { "drminfo", handle_drminfo, "drminfo [entry]", CMD_NONE },
    { "fbinfo", handle_fbinfo, "fbinfo [fbX]", CMD_NONE },
    { "kmsprobe", handle_kmsprobe, "kmsprobe", CMD_NONE },
    { "kmssolid", handle_kmssolid, "kmssolid [color]", CMD_DISPLAY },
    { "kmsframe", handle_kmsframe, "kmsframe", CMD_DISPLAY },
    { "statusscreen", handle_statusscreen, "statusscreen", CMD_DISPLAY },
    { "statushud", handle_statushud, "statushud", CMD_DISPLAY },
    { "redraw", handle_statushud, "redraw", CMD_DISPLAY },
    { "testpattern", handle_statusscreen, "testpattern", CMD_DISPLAY },
    { "displaytest", handle_displaytest, "displaytest [0-3|colors|font|safe|layout]", CMD_DISPLAY },
    { "cutoutcal", handle_cutoutcal, "cutoutcal [x y size]", CMD_DISPLAY },
    { "watchhud", handle_watchhud, "watchhud [sec] [count]", CMD_DISPLAY | CMD_BLOCKING },
    { "autohud", handle_autohud, "autohud [sec]", CMD_BACKGROUND },
    { "stophud", handle_stophud, "stophud", CMD_BACKGROUND },
    { "clear", handle_clear, "clear", CMD_DISPLAY },
    { "inputcaps", handle_inputcaps, "inputcaps <eventX>", CMD_NONE },
    { "readinput", handle_readinput, "readinput <eventX> [count]", CMD_BLOCKING },
    { "waitkey", handle_waitkey, "waitkey [count]", CMD_BLOCKING },
    { "inputlayout", handle_inputlayout, "inputlayout", CMD_NONE },
    { "waitgesture", handle_waitgesture, "waitgesture [count]", CMD_BLOCKING },
    { "inputmonitor", handle_inputmonitor, "inputmonitor [events]", CMD_DISPLAY | CMD_BLOCKING },
    { "screenmenu", handle_screenmenu, "screenmenu", CMD_BLOCKING | CMD_DANGEROUS },
    { "menu", handle_screenmenu, "menu", CMD_BLOCKING | CMD_DANGEROUS },
    { "blindmenu", handle_blindmenu, "blindmenu", CMD_BLOCKING | CMD_DANGEROUS },
    { "mkdir", handle_mkdir, "mkdir <dir>", CMD_NONE },
    { "mknodc", handle_mknodc, "mknodc <path> <major> <minor>", CMD_NONE },
    { "mknodb", handle_mknodb, "mknodb <path> <major> <minor>", CMD_NONE },
    { "mountfs", handle_mountfs, "mountfs <src> <dst> <type> [ro]", CMD_NONE },
    { "umount", handle_umount, "umount <path>", CMD_NONE },
    { "echo", handle_echo, "echo <text>", CMD_NONE },
    { "writefile", handle_writefile, "writefile <path> <value...>", CMD_NONE },
    { "cpustress", handle_cpustress, "cpustress [sec] [workers]", CMD_BLOCKING },
    { "run", handle_run, "run <path> [args...]", CMD_BLOCKING },
    { "runandroid", handle_runandroid, "runandroid <path> [args...]", CMD_BLOCKING },
    { "startadbd", handle_startadbd, "startadbd", CMD_BACKGROUND },
    { "stopadbd", handle_stopadbd, "stopadbd", CMD_BACKGROUND },
    { "netservice", handle_netservice, "netservice [status|start|stop|enable|disable]", CMD_DANGEROUS },
    { "reattach", handle_reattach, "reattach", CMD_NONE },
    { "usbacmreset", handle_usbacmreset, "usbacmreset", CMD_DANGEROUS },
    { "sync", handle_sync, "sync", CMD_NONE },
    { "reboot", handle_reboot, "reboot", CMD_DANGEROUS | CMD_NO_DONE },
    { "recovery", handle_recovery, "recovery", CMD_DANGEROUS | CMD_NO_DONE },
    { "poweroff", handle_poweroff, "poweroff", CMD_DANGEROUS | CMD_NO_DONE },
};

static const struct shell_command *find_command(const char *name) {
    size_t index;

    for (index = 0; index < sizeof(command_table) / sizeof(command_table[0]); ++index) {
        if (strcmp(name, command_table[index].name) == 0) {
            return &command_table[index];
        }
    }

    return NULL;
}

static bool is_auto_menu_hide_word(const char *name) {
    return strcmp(name, "q") == 0 ||
           strcmp(name, "Q") == 0 ||
           strcmp(name, "hide") == 0 ||
           strcmp(name, "hidemenu") == 0 ||
           strcmp(name, "resume") == 0;
}

static bool command_allowed_during_auto_menu(const struct shell_command *command) {
    const char *name = command->name;

    if (!auto_menu_power_is_active()) {
        if ((command->flags & CMD_DANGEROUS) != 0) {
            return false;
        }
        if (strcmp(name, "screenmenu") == 0 ||
            strcmp(name, "menu") == 0 ||
            strcmp(name, "blindmenu") == 0 ||
            strcmp(name, "waitkey") == 0 ||
            strcmp(name, "readinput") == 0 ||
            strcmp(name, "waitgesture") == 0) {
            return false;
        }
        return true;
    }

    if (strcmp(name, "help") == 0 ||
        strcmp(name, "version") == 0 ||
        strcmp(name, "status") == 0 ||
        strcmp(name, "bootstatus") == 0 ||
        strcmp(name, "timeline") == 0 ||
        strcmp(name, "last") == 0 ||
        strcmp(name, "logpath") == 0 ||
        strcmp(name, "logcat") == 0 ||
        strcmp(name, "inputlayout") == 0 ||
        strcmp(name, "inputmonitor") == 0 ||
        strcmp(name, "uname") == 0 ||
        strcmp(name, "pwd") == 0 ||
        strcmp(name, "mounts") == 0 ||
        strcmp(name, "reattach") == 0 ||
        strcmp(name, "stophud") == 0) {
        return true;
    }

    return false;
}

static const char *shell_protocol_status(int result, bool unknown, bool busy) {
    if (unknown) {
        return "unknown";
    }
    if (busy) {
        return "busy";
    }
    if (result == 0) {
        return "ok";
    }
    return "error";
}

static void shell_protocol_begin(unsigned long seq,
                                 const char *command,
                                 int argc,
                                 unsigned int flags) {
    cprintf("A90P1 BEGIN seq=%lu cmd=%s argc=%d flags=0x%x\r\n",
            seq,
            command,
            argc,
            flags);
}

static void shell_protocol_end(unsigned long seq,
                               const char *command,
                               int result,
                               int result_errno,
                               long duration_ms,
                               unsigned int flags,
                               const char *status) {
    cprintf("A90P1 END seq=%lu cmd=%s rc=%d errno=%d duration_ms=%ld flags=0x%x status=%s\r\n",
            seq,
            command,
            result,
            result_errno,
            duration_ms,
            flags,
            status);
}

static void print_cmdv1x_error(int result) {
    int result_errno = -result;
    unsigned long protocol_seq = ++shell_protocol_seq;

    if (result_errno <= 0) {
        result_errno = EINVAL;
        result = -EINVAL;
    }

    shell_protocol_begin(protocol_seq, "cmdv1x", 1, CMD_NONE);
    cprintf("[err] cmdv1x decode rc=%d errno=%d (%s)\r\n",
            result,
            result_errno,
            strerror(result_errno));
    save_last_result("cmdv1x", result, result_errno, 0, CMD_NONE);
    native_logf("cmd", "cmdv1x decode failed rc=%d errno=%d",
                result, result_errno);
    shell_protocol_end(protocol_seq,
                       "cmdv1x",
                       result,
                       result_errno,
                       0,
                       CMD_NONE,
                       "error");
}

static void print_shell_result(const struct shell_command *command,
                               const char *name,
                               int result,
                               int result_errno,
                               long duration_ms) {
    if ((command->flags & CMD_NO_DONE) != 0 && result == 0) {
        return;
    }
    if (result == 0) {
        cprintf("[done] %s (%ldms)\r\n", name, duration_ms);
    } else if (result < 0) {
        cprintf("[err] %s rc=%d errno=%d (%s) (%ldms)\r\n",
                name,
                result,
                result_errno,
                strerror(result_errno),
                duration_ms);
    } else {
        cprintf("[err] %s rc=%d (%ldms)\r\n",
                name,
                result,
                duration_ms);
    }
}

static int execute_shell_command(char **argv, int argc, bool protocol_v1) {
    const struct shell_command *command;
    unsigned long protocol_seq = 0;
    long started_ms;
    long duration_ms;
    int result;
    int result_errno;

    if (argc == 0) {
        return 0;
    }

    command = find_command(argv[0]);
    if (command == NULL) {
        result = -ENOENT;
        result_errno = ENOENT;
        if (protocol_v1) {
            protocol_seq = ++shell_protocol_seq;
            shell_protocol_begin(protocol_seq, argv[0], argc, CMD_NONE);
        }
        cprintf("[err] unknown command: %s\r\n", argv[0]);
        save_last_result(argv[0], result, result_errno, 0, CMD_NONE);
        native_logf("cmd", "unknown name=%s rc=%d errno=%d",
                    argv[0], result, result_errno);
        if (protocol_v1) {
            shell_protocol_end(protocol_seq,
                               argv[0],
                               result,
                               result_errno,
                               0,
                               CMD_NONE,
                               shell_protocol_status(result, true, false));
        }
        return result;
    }

    if (auto_menu_is_active() && !command_allowed_during_auto_menu(command)) {
        result = -EBUSY;
        result_errno = EBUSY;
        if (protocol_v1) {
            protocol_seq = ++shell_protocol_seq;
            shell_protocol_begin(protocol_seq, argv[0], argc, command->flags);
        }
        if (auto_menu_power_is_active()) {
            cprintf("[busy] power menu active; send hide/q before commands\r\n");
        } else if ((command->flags & CMD_DANGEROUS) != 0) {
            cprintf("[busy] auto menu active; hide/q before dangerous command\r\n");
        } else {
            cprintf("[busy] auto menu active; command waits for input/menu control\r\n");
        }
        save_last_result(argv[0], result, result_errno, 0, command->flags);
        native_logf("cmd", "busy menu-active name=%s flags=0x%x",
                    argv[0], command->flags);
        if (protocol_v1) {
            shell_protocol_end(protocol_seq,
                               argv[0],
                               result,
                               result_errno,
                               0,
                               command->flags,
                               shell_protocol_status(result, false, true));
        }
        return result;
    }

    if (protocol_v1) {
        protocol_seq = ++shell_protocol_seq;
        shell_protocol_begin(protocol_seq, argv[0], argc, command->flags);
    }

    native_logf("cmd", "start name=%s argc=%d flags=0x%x",
                argv[0], argc, command->flags);

    if ((command->flags & CMD_DISPLAY) != 0) {
        stop_auto_hud(false);
    }

    errno = 0;
    started_ms = monotonic_millis();
    result = command->handler(argv, argc);
    duration_ms = monotonic_millis() - started_ms;
    if (duration_ms < 0) {
        duration_ms = 0;
    }

    if (result < 0) {
        result_errno = -result;
    } else {
        result_errno = 0;
    }
    save_last_result(argv[0], result, result_errno, duration_ms, command->flags);
    native_logf("cmd", "end name=%s rc=%d errno=%d duration=%ldms flags=0x%x",
                argv[0],
                result,
                result_errno,
                duration_ms,
                command->flags);

    print_shell_result(command, argv[0], result, result_errno, duration_ms);
    if (protocol_v1) {
        shell_protocol_end(protocol_seq,
                           argv[0],
                           result,
                           result_errno,
                           duration_ms,
                           command->flags,
                           shell_protocol_status(result, false, false));
    }
    return result;
}

static void shell_loop(void) {
    char line[512];

    print_shell_intro();

    while (1) {
        char *argv[32];
        int argc;

        print_prompt();
        if (read_line(line, sizeof(line)) < 0) {
            cprintf("read: %s\r\n", strerror(errno));
            sleep(1);
            continue;
        }
        if (strncmp(line, "a90:", 4) == 0) {
            continue;
        }
        if (is_unsolicited_at_fragment_noise(line)) {
            native_logf("serial", "ignored AT fragment line=%.48s", skip_shell_space(line));
            continue;
        }
        if (is_unsolicited_at_noise(line)) {
            native_logf("serial", "ignored AT probe line=%.48s", skip_shell_space(line));
            continue;
        }

        argc = split_args(line, argv, 32);
        if (argc == 0) {
            continue;
        }

        if (auto_menu_is_active() && is_auto_menu_hide_word(argv[0])) {
            request_auto_menu_hide();
            set_auto_menu_active(false);
            cprintf("[busy] auto menu active; hide requested\r\n");
            native_logf("menu", "hide requested by serial word=%s", argv[0]);
            continue;
        }

        if (strcmp(argv[0], "cmdv1") == 0) {
            if (argc < 2) {
                char *usage_argv[] = { "cmdv1", NULL };

                execute_shell_command(usage_argv, 1, false);
            } else {
                execute_shell_command(&argv[1], argc - 1, true);
            }
            continue;
        }

        if (strcmp(argv[0], "cmdv1x") == 0) {
            char *decoded_argv[CMDV1X_MAX_ARGS];
            char decoded_buf[512];
            int decoded_argc;

            decoded_argc = decode_cmdv1x_args(&argv[1],
                                              argc - 1,
                                              decoded_argv,
                                              CMDV1X_MAX_ARGS,
                                              decoded_buf,
                                              sizeof(decoded_buf));
            if (decoded_argc < 0) {
                print_cmdv1x_error(decoded_argc);
            } else {
                execute_shell_command(decoded_argv, decoded_argc, true);
            }
            continue;
        }

        execute_shell_command(argv, argc, false);
    }
}

int main(void) {
    timeline_record(0, 0, "init-start", "%s", INIT_BANNER);
    setup_base_mounts();
    native_log_select(NATIVE_LOG_FALLBACK);
    native_logf("boot", "%s start", INIT_BANNER);
    native_logf("boot", "base mounts ready");
    timeline_record(0, 0, "base-mounts", "proc/sys/dev/tmpfs requested");
    klogf("<6>A90v77: base mounts ready\n");
    prepare_early_display_environment();
    native_logf("boot", "early display/input nodes prepared");
    timeline_record(0, 0, "early-nodes", "display/input/graphics nodes prepared");
    timeline_probe_boot_resources();
    klogf("<6>A90v77: early display/input nodes prepared\n");

    if (mount_cache() == 0) {
        native_log_select(NATIVE_LOG_PRIMARY);
        timeline_replay_to_log("cache");
        native_logf("boot", "%s start", INIT_BANNER);
        native_logf("boot", "base mounts ready");
        native_logf("boot", "early display/input nodes prepared");
        native_logf("boot", "cache mounted log=%s", native_log_current_path());
        timeline_record(0, 0, "cache-mount", "/cache mounted log=%s", native_log_current_path());
        mark_step("1_cache_ok_v77\n");
        klogf("<6>A90v77: cache mounted\n");
    } else {
        int saved_errno = errno;
        native_logf("boot", "cache mount failed errno=%d error=%s log=%s",
                    saved_errno, strerror(saved_errno), native_log_current_path());
        timeline_record(-saved_errno,
                        saved_errno,
                        "cache-mount",
                        "/cache failed: %s log=%s",
                        strerror(saved_errno),
                        native_log_current_path());
        klogf("<6>A90v77: cache mount failed (%d)\n", saved_errno);
    }

    if (setup_acm_gadget() == 0) {
        mark_step("2_gadget_ok_v77\n");
        native_logf("boot", "ACM gadget configured");
        timeline_record(0, 0, "usb-gadget", "ACM gadget configured");
        klogf("<6>A90v77: ACM gadget configured\n");
    } else {
        int saved_errno = errno;
        native_logf("boot", "ACM gadget failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "usb-gadget",
                        "ACM gadget failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v77: ACM gadget failed (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (wait_for_tty_gs0() == 0) {
        mark_step("3_tty_ready_v77\n");
        native_logf("boot", "ttyGS0 ready");
        timeline_record(0, 0, "ttyGS0", "/dev/ttyGS0 ready");
        klogf("<6>A90v77: ttyGS0 ready\n");
        boot_auto_frame();
        sleep(BOOT_SPLASH_SECONDS);
    } else {
        int saved_errno = errno;
        native_logf("boot", "ttyGS0 missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "ttyGS0",
                        "/dev/ttyGS0 missing: %s",
                        strerror(saved_errno));
        klogf("<6>A90v77: ttyGS0 missing (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (attach_console() == 0) {
        mark_step("4_console_attached_v77\n");
        native_logf("boot", "console attached");
        timeline_record(0, 0, "console", "serial console attached");
        drain_console_input(250, 1500);
        cprintf("\r\n# %s\r\n", INIT_BANNER);
        cprintf("# USB ACM serial console ready.\r\n");
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) == 0) {
            native_logf("boot", "autohud started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            timeline_record(0, 0, "autohud", "started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            cprintf("# Boot display: splash %ds -> autohud %ds.\r\n",
                    BOOT_SPLASH_SECONDS,
                    BOOT_HUD_REFRESH_SECONDS);
        } else {
            int saved_errno = errno;

            native_logf("boot", "autohud start failed errno=%d error=%s",
                        saved_errno, strerror(saved_errno));
            timeline_record(-saved_errno,
                            saved_errno,
                            "autohud",
                            "start failed: %s",
                            strerror(saved_errno));
            cprintf("# Boot display: autohud start failed.\r\n");
        }
        if (netservice_enabled_flag()) {
            int net_rc;

            cprintf("# Netservice: enabled, starting NCM/tcpctl.\r\n");
            net_rc = netservice_start();
            if (net_rc == 0) {
                mark_step("5_netservice_ok_v77\n");
                cprintf("# Netservice: NCM %s %s, tcpctl port %s.\r\n",
                        NETSERVICE_IFNAME,
                        NETSERVICE_DEVICE_IP,
                        NETSERVICE_TCP_PORT);
                klogf("<6>A90v77: netservice started\n");
            } else {
                int net_errno = -net_rc;

                if (net_errno < 0) {
                    net_errno = EIO;
                }
                cprintf("# Netservice: start failed rc=%d errno=%d (%s).\r\n",
                        net_rc,
                        net_errno,
                        strerror(net_errno));
                native_logf("boot", "netservice failed rc=%d errno=%d error=%s",
                            net_rc, net_errno, strerror(net_errno));
                timeline_record(net_rc,
                                net_errno,
                                "netservice",
                                "start failed: %s",
                                strerror(net_errno));
                klogf("<6>A90v77: netservice failed (%d)\n", net_errno);
            }
        } else {
            native_logf("boot", "netservice disabled flag=%s", NETSERVICE_FLAG_PATH);
        }
        native_logf("boot", "entering shell");
        timeline_record(0, 0, "shell", "interactive shell ready");
        shell_loop();
    } else {
        int saved_errno = errno;
        native_logf("boot", "console attach failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "console",
                        "attach failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v77: console attach failed (%d)\n", saved_errno);
    }

    while (1) {
        sleep(60);
    }
}
