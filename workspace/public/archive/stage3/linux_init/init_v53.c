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
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <sys/utsname.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>

#define INIT_VERSION "v53"
#define INIT_BANNER "A90 Linux init " INIT_VERSION
#define BOOT_TEST_SECONDS 2
#define BOOT_HUD_REFRESH_SECONDS 2
#define NATIVE_LOG_PRIMARY "/cache/native-init.log"
#define NATIVE_LOG_FALLBACK "/tmp/native-init.log"
#define NATIVE_LOG_MAX_BYTES (256 * 1024)
#define BOOT_TIMELINE_MAX 32
#define CONSOLE_POLL_TIMEOUT_MS 1000
#define CONSOLE_IDLE_REATTACH_MS 10000
#define AUTO_MENU_STATE_PATH "/tmp/a90-auto-menu-active"
#define AUTO_MENU_REQUEST_PATH "/tmp/a90-auto-menu-request"

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

static long monotonic_millis(void);
static int ensure_block_node(const char *path, unsigned int major_num, unsigned int minor_num);

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

static bool auto_menu_is_active(void) {
    char state[16];

    if (read_text_file(AUTO_MENU_STATE_PATH, state, sizeof(state)) < 0) {
        return false;
    }
    trim_newline(state);
    return strcmp(state, "1") == 0 ||
           strcmp(state, "active") == 0 ||
           strcmp(state, "menu") == 0;
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

static void kms_fill_color(struct kms_display_state *state, uint32_t color) {
    size_t y;
    uint8_t red = (color >> 16) & 0xff;
    uint8_t green = (color >> 8) & 0xff;
    uint8_t blue = color & 0xff;
    uint32_t pixel = (red << 16) | (green << 8) | blue;
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
    uint8_t red = (color >> 16) & 0xff;
    uint8_t green = (color >> 8) & 0xff;
    uint8_t blue = color & 0xff;
    uint32_t pixel = (red << 16) | (green << 8) | blue;
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
    char gpu_temp[32];
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
    strcpy(snapshot->gpu_temp, "?");
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
    if (read_average_thermal_temp("gpuss", NULL, &value) == 0) {
        format_temp_tenths(snapshot->gpu_temp, sizeof(snapshot->gpu_temp), value);
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

    snprintf(footer, sizeof(footer), "A90v53 UP %.8s", snapshot.uptime);
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

    /* Row 2: "CPU "(gray) cpu_temp(white) " GPU "(gray) gpu_temp(white) */
    off = 0;
    kms_draw_text(state, x + off * char_w, y + slot * 2, "CPU ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 2, snapshot.cpu_temp, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.cpu_temp) + 1;
    kms_draw_text(state, x + off * char_w, y + slot * 2, "GPU ", 0x909090, scale); off += 4;
    kms_draw_text(state, x + off * char_w, y + slot * 2, snapshot.gpu_temp, 0xffffff, scale);

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
enum screen_menu_action {
    SCREEN_MENU_RESUME = 0,
    SCREEN_MENU_STATUS,
    SCREEN_MENU_LOG,
    SCREEN_MENU_RECOVERY,
    SCREEN_MENU_REBOOT,
    SCREEN_MENU_POWEROFF,
};
struct screen_menu_item {
    const char *name;
    const char *summary;
    enum screen_menu_action action;
};
struct key_wait_context { int fd0; int fd3; };
static int open_key_wait_context(struct key_wait_context *ctx, const char *tag);
static void close_key_wait_context(struct key_wait_context *ctx);
static void kms_draw_menu_section(struct kms_display_state *state,
                                  const struct screen_menu_item *items,
                                  size_t count, size_t selected);
static int cmd_statushud(void);
static int cmd_recovery(void);
static int draw_screen_log_summary(void);

static void auto_hud_loop(unsigned int refresh_sec) {
    static const struct screen_menu_item items[] = {
        { "HIDE MENU","HIDE THIS PANEL",  SCREEN_MENU_RESUME   },
        { "STATUS",   "SHOW STATUS",     SCREEN_MENU_STATUS   },
        { "LOG",      "SHOW LOG",        SCREEN_MENU_LOG      },
        { "RECOVERY", "REBOOT TO TWRP",  SCREEN_MENU_RECOVERY },
        { "REBOOT",   "RESTART DEVICE",  SCREEN_MENU_REBOOT   },
        { "POWEROFF", "POWER OFF",       SCREEN_MENU_POWEROFF },
    };
    static const size_t item_count = sizeof(items) / sizeof(items[0]);
    struct key_wait_context ctx;
    bool menu_active = true;
    size_t menu_sel = 0;
    bool has_input;
    int timeout_ms;

    signal(SIGTERM, SIG_DFL);
    has_input = (open_key_wait_context(&ctx, "autohud") == 0);
    timeout_ms = (refresh_sec > 0 && refresh_sec <= 60) ? (int)(refresh_sec * 1000) : 2000;
    set_auto_menu_active(menu_active);

    while (1) {
        struct pollfd fds[2];
        int poll_rc;
        int fi;

        if (consume_auto_menu_hide_request()) {
            menu_active = false;
        }
        set_auto_menu_active(menu_active);

        /* draw */
        if (kms_begin_frame(0x000000) == 0) {
            kms_draw_status_overlay(&kms_state, 0, 0);
            if (menu_active)
                kms_draw_menu_section(&kms_state, items, item_count, menu_sel);
            kms_present_frame_verbose("autohud", false);
        }

        if (!has_input) {
            sleep(refresh_sec);
            continue;
        }

        fds[0].fd = ctx.fd0; fds[0].events = POLLIN;
        fds[1].fd = ctx.fd3; fds[1].events = POLLIN;
        poll_rc = poll(fds, 2, timeout_ms);
        if (poll_rc <= 0)
            continue; /* timeout → redraw */

        for (fi = 0; fi < 2; fi++) {
            struct input_event ev;
            if (!(fds[fi].revents & POLLIN))
                continue;
            while (read(fds[fi].fd, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
                if (ev.type != EV_KEY || ev.value != 1)
                    continue;

                if (ev.code == KEY_VOLUMEUP) {
                    if (!menu_active) {
                        menu_active = true;
                        menu_sel = 0;
                    } else {
                        menu_sel = (menu_sel + item_count - 1) % item_count;
                    }
                } else if (ev.code == KEY_VOLUMEDOWN) {
                    if (!menu_active) {
                        menu_active = true;
                        menu_sel = 0;
                    } else {
                        menu_sel = (menu_sel + 1) % item_count;
                    }
                } else if (ev.code == KEY_POWER && menu_active) {
                    switch (items[menu_sel].action) {
                    case SCREEN_MENU_RESUME:
                        menu_active = false;
                        set_auto_menu_active(false);
                        break;
                    case SCREEN_MENU_STATUS:
                        cmd_statushud();
                        menu_active = false;
                        set_auto_menu_active(false);
                        break;
                    case SCREEN_MENU_LOG:
                        draw_screen_log_summary();
                        menu_active = false;
                        set_auto_menu_active(false);
                        break;
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

static void boot_auto_frame(void) {
    if (kms_begin_frame(0x000000) == 0) {
        kms_draw_giant_test_probe(&kms_state);
        if (kms_present_frame("bootframe") == 0) {
            klogf("<6>A90v53: automatic giant TEST probe applied\n");
            native_logf("boot", "display test probe applied");
            timeline_record(0, 0, "display-probe", "TEST frame applied");
        }
    } else {
        int saved_errno = errno;

        klogf("<6>A90v53: automatic giant TEST probe skipped (%d)\n", saved_errno);
        native_logf("boot", "display test probe skipped errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "display-probe",
                        "TEST frame skipped: %s",
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
        unsigned int code;
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

struct blind_menu_item {
    const char *name;
    const char *summary;
};

static void kms_draw_menu_section(struct kms_display_state *state,
                                  const struct screen_menu_item *items,
                                  size_t count, size_t selected) {
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
    size_t i;

    if (y > glyph_h + glyph_h / 2 + scale * 2)
        y -= glyph_h + glyph_h / 2;

    status_bottom = y + 3 * slot + card_h;
    divider_y = status_bottom + scale * 5;
    menu_y = divider_y + scale * 9;

    kms_fill_rect(state, x, divider_y, card_w, 2, 0x383838);
    kms_draw_text(state, x, divider_y + scale * 2,
                  "VOLUP/DN MOVE  PWR SELECT",
                  0x444444, menu_scale > 1 ? menu_scale - 1 : menu_scale);

    for (i = 0; i < count; ++i) {
        uint32_t iy = menu_y + (uint32_t)i * (item_h + item_gap);
        bool is_sel = (i == selected);
        uint32_t fill = is_sel ? 0x1a3560 : 0x141414;
        uint32_t name_color = is_sel ? 0xffffff : 0x707070;

        kms_fill_rect(state, x - scale, iy - scale, card_w, item_h, fill);
        if (is_sel)
            kms_fill_rect(state, x - scale, iy - scale, scale * 2, item_h, 0xffcc33);
        kms_draw_text(state, x + scale * 3, iy + (item_h - glyph_h) / 2,
                      items[i].name, name_color, menu_scale);
    }
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

static void print_screen_menu_selection(const struct screen_menu_item *items,
                                        size_t count,
                                        size_t selected) {
    cprintf("screenmenu: [%d/%d] %s - %s\r\n",
            (int)(selected + 1),
            (int)count,
            items[selected].name,
            items[selected].summary);
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

static uint32_t shrink_text_scale(const char *text,
                                  uint32_t scale,
                                  uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int draw_screen_menu(const struct screen_menu_item *items,
                            size_t count,
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
    const char *footer = "VOLUP PREV VOLDN NEXT PWR SELECT Q EXIT";

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
    item_h = scale * 17;
    gap = scale * 2;
    title_y = y;
    list_y = title_y + (title_scale * 9) + (scale * 5);

    kms_draw_text(&kms_state, x, title_y, "A90 SCREEN MENU", 0xffcc33, title_scale);
    kms_draw_text(&kms_state, x, title_y + title_scale * 9,
                  "BUTTON ONLY CONTROL", 0xdddddd, scale);

    for (index = 0; index < count; ++index) {
        uint32_t item_y = list_y + index * (item_h + gap);
        uint32_t fill = (index == selected) ? 0x204080 : 0x202020;
        uint32_t name_color = (index == selected) ? 0xffffff : 0xd0d0d0;
        uint32_t summary_color = (index == selected) ? 0xffcc33 : 0x909090;

        kms_fill_rect(&kms_state, x - scale, item_y - scale, card_w, item_h, fill);
        if (index == selected) {
            kms_fill_rect(&kms_state, x - scale, item_y - scale, scale * 2, item_h, 0xffcc33);
        }
        kms_draw_text(&kms_state, x + scale * 3, item_y + scale,
                      items[index].name, name_color, scale);
        kms_draw_text(&kms_state, x + scale * 3, item_y + scale * 9,
                      items[index].summary, summary_color, scale > 1 ? scale - 1 : scale);
    }

    footer_scale = shrink_text_scale(footer, scale, card_w);
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

static int wait_for_menu_return(struct key_wait_context *ctx, const char *tag) {
    unsigned int code;
    int wait_rc = wait_for_key_press(ctx, tag, &code);

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

    cprintf("blindmenu: VOLUP=prev VOLDOWN=next POWER=select q/Ctrl-C=cancel\r\n");
    cprintf("blindmenu: start with a safe default, then move as needed\r\n");
    print_blind_menu_selection(items, count, selected);

    while (1) {
        unsigned int code;

        int wait_rc = wait_for_key_press(&ctx, "blindmenu", &code);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            return wait_rc;
        }

        if (code == KEY_VOLUMEUP) {
            selected = (selected + count - 1) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (code == KEY_VOLUMEDOWN) {
            selected = (selected + 1) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (code != KEY_POWER) {
            cprintf("blindmenu: ignoring key 0x%04x\r\n", code);
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
    static const struct screen_menu_item items[] = {
        { "RESUME", "RETURN TO HUD", SCREEN_MENU_RESUME },
        { "STATUS", "SHOW SYSTEM STATUS", SCREEN_MENU_STATUS },
        { "LOG", "SHOW LOG SUMMARY", SCREEN_MENU_LOG },
        { "RECOVERY", "REBOOT TO TWRP", SCREEN_MENU_RECOVERY },
        { "REBOOT", "RESTART DEVICE", SCREEN_MENU_REBOOT },
        { "POWEROFF", "POWER OFF DEVICE", SCREEN_MENU_POWEROFF },
    };
    struct key_wait_context ctx;
    size_t selected = 0;
    size_t count = sizeof(items) / sizeof(items[0]);
    bool restore_hud;
    int draw_rc;

    reap_hud_child();
    restore_hud = hud_pid > 0;
    stop_auto_hud(false);

    if (open_key_wait_context(&ctx, "screenmenu") < 0) {
        restore_auto_hud_if_needed(restore_hud);
        return negative_errno_or(ENOENT);
    }

    cprintf("screenmenu: VOLUP=prev VOLDOWN=next POWER=select q/Ctrl-C=cancel\r\n");
    native_logf("screenmenu", "start restore_hud=%d", restore_hud ? 1 : 0);
    print_screen_menu_selection(items, count, selected);

    draw_rc = draw_screen_menu(items, count, selected);
    if (draw_rc < 0) {
        close_key_wait_context(&ctx);
        restore_auto_hud_if_needed(restore_hud);
        return draw_rc;
    }

    while (1) {
        unsigned int code;
        int wait_rc = wait_for_key_press(&ctx, "screenmenu", &code);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return wait_rc;
        }

        if (code == KEY_VOLUMEUP) {
            selected = (selected + count - 1) % count;
            print_screen_menu_selection(items, count, selected);
            draw_rc = draw_screen_menu(items, count, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (code == KEY_VOLUMEDOWN) {
            selected = (selected + 1) % count;
            print_screen_menu_selection(items, count, selected);
            draw_rc = draw_screen_menu(items, count, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (code != KEY_POWER) {
            cprintf("screenmenu: ignoring key 0x%04x\r\n", code);
            continue;
        }

        cprintf("screenmenu: selected %s\r\n", items[selected].name);
        native_logf("screenmenu", "selected %s", items[selected].name);

        if (items[selected].action == SCREEN_MENU_RESUME) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return 0;
        }

        if (items[selected].action == SCREEN_MENU_STATUS) {
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
            draw_rc = draw_screen_menu(items, count, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (items[selected].action == SCREEN_MENU_LOG) {
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
            draw_rc = draw_screen_menu(items, count, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        close_key_wait_context(&ctx);

        if (items[selected].action == SCREEN_MENU_RECOVERY) {
            return cmd_recovery();
        }
        if (items[selected].action == SCREEN_MENU_REBOOT) {
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

    if (now_ms > 0 &&
        last_console_reattach_ms > 0 &&
        now_ms - last_console_reattach_ms < 500) {
        return 0;
    }
    last_console_reattach_ms = now_ms;

    native_logf("console", "reattach requested reason=%s old_fd=%d",
                reason, old_fd);
    klogf("<6>A90v53: console reattach requested reason=%s old_fd=%d\n",
          reason, old_fd);

    if (old_fd >= 0) {
        close(old_fd);
    }
    console_fd = -1;

    if (wait_for_tty_gs0() < 0) {
        int saved_errno = errno;
        native_logf("console", "reattach wait failed reason=%s errno=%d error=%s",
                    reason, saved_errno, strerror(saved_errno));
        klogf("<6>A90v53: console reattach wait failed (%d)\n", saved_errno);
        errno = saved_errno;
        return -1;
    }

    if (attach_console() < 0) {
        int saved_errno = errno;
        native_logf("console", "reattach open failed reason=%s errno=%d error=%s",
                    reason, saved_errno, strerror(saved_errno));
        klogf("<6>A90v53: console reattach open failed (%d)\n", saved_errno);
        errno = saved_errno;
        return -1;
    }

    drain_console_input(50, 200);
    native_logf("console", "reattach ok reason=%s fd=%d", reason, console_fd);
    klogf("<6>A90v53: console reattached reason=%s fd=%d\n", reason, console_fd);
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
    cprintf("menu\r\n");
    cprintf("screenmenu\r\n");
    cprintf("blindmenu\r\n");
    cprintf("mkdir <dir>\r\n");
    cprintf("mknodc <path> <major> <minor>\r\n");
    cprintf("mknodb <path> <major> <minor>\r\n");
    cprintf("mountfs <src> <dst> <type> [ro]\r\n");
    cprintf("umount <path>\r\n");
    cprintf("echo <text>\r\n");
    cprintf("writefile <path> <value...>\r\n");
    cprintf("run <path> [args...]\r\n");
    cprintf("runandroid <path> [args...]\r\n");
    cprintf("startadbd\r\n");
    cprintf("stopadbd\r\n");
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
    cprintf("boot: %s\r\n", boot_summary);
    cprintf("uptime: %ss  load=%s\r\n", snapshot.uptime, snapshot.loadavg);
    cprintf("battery: %s %s temp=%s voltage=%s\r\n",
            snapshot.battery_pct,
            snapshot.battery_status,
            snapshot.battery_temp,
            snapshot.battery_voltage);
    cprintf("power: now=%s avg=%s\r\n", snapshot.power_now, snapshot.power_avg);
    cprintf("thermal: cpu=%s gpu=%s\r\n", snapshot.cpu_temp, snapshot.gpu_temp);
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
    { "watchhud", handle_watchhud, "watchhud [sec] [count]", CMD_DISPLAY | CMD_BLOCKING },
    { "autohud", handle_autohud, "autohud [sec]", CMD_BACKGROUND },
    { "stophud", handle_stophud, "stophud", CMD_BACKGROUND },
    { "clear", handle_clear, "clear", CMD_DISPLAY },
    { "inputcaps", handle_inputcaps, "inputcaps <eventX>", CMD_NONE },
    { "readinput", handle_readinput, "readinput <eventX> [count]", CMD_BLOCKING },
    { "waitkey", handle_waitkey, "waitkey [count]", CMD_BLOCKING },
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
    { "run", handle_run, "run <path> [args...]", CMD_BLOCKING },
    { "runandroid", handle_runandroid, "runandroid <path> [args...]", CMD_BLOCKING },
    { "startadbd", handle_startadbd, "startadbd", CMD_BACKGROUND },
    { "stopadbd", handle_stopadbd, "stopadbd", CMD_BACKGROUND },
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

    if (strcmp(name, "help") == 0 ||
        strcmp(name, "version") == 0 ||
        strcmp(name, "status") == 0 ||
        strcmp(name, "bootstatus") == 0 ||
        strcmp(name, "timeline") == 0 ||
        strcmp(name, "last") == 0 ||
        strcmp(name, "logpath") == 0 ||
        strcmp(name, "logcat") == 0 ||
        strcmp(name, "uname") == 0 ||
        strcmp(name, "pwd") == 0 ||
        strcmp(name, "mounts") == 0 ||
        strcmp(name, "reattach") == 0 ||
        strcmp(name, "stophud") == 0) {
        return true;
    }

    return false;
}

static void shell_loop(void) {
    char line[512];

    print_shell_intro();

    while (1) {
        char *argv[32];
        int argc;
        const struct shell_command *command;
        long started_ms;
        long duration_ms;
        int result;
        int result_errno;

        print_prompt();
        if (read_line(line, sizeof(line)) < 0) {
            cprintf("read: %s\r\n", strerror(errno));
            sleep(1);
            continue;
        }
        if (strncmp(line, "a90:", 4) == 0) {
            continue;
        }

        argc = split_args(line, argv, 32);
        if (argc == 0) {
            continue;
        }

        if (auto_menu_is_active() && is_auto_menu_hide_word(argv[0])) {
            request_auto_menu_hide();
            cprintf("[busy] auto menu active; hide requested\r\n");
            native_logf("menu", "hide requested by serial word=%s", argv[0]);
            continue;
        }

        command = find_command(argv[0]);
        if (command == NULL) {
            cprintf("[err] unknown command: %s\r\n", argv[0]);
            save_last_result(argv[0], -ENOENT, ENOENT, 0, CMD_NONE);
            native_logf("cmd", "unknown name=%s rc=%d errno=%d",
                        argv[0], -ENOENT, ENOENT);
            continue;
        }

        if (auto_menu_is_active() && !command_allowed_during_auto_menu(command)) {
            cprintf("[busy] auto menu active; send hide/q or select HIDE MENU\r\n");
            save_last_result(argv[0], -EBUSY, EBUSY, 0, command->flags);
            native_logf("cmd", "busy menu-active name=%s flags=0x%x",
                        argv[0], command->flags);
            continue;
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

        if ((command->flags & CMD_NO_DONE) != 0 && result == 0) {
            continue;
        }
        if (result == 0) {
            cprintf("[done] %s (%ldms)\r\n", argv[0], duration_ms);
        } else if (result < 0) {
            cprintf("[err] %s rc=%d errno=%d (%s) (%ldms)\r\n",
                    argv[0],
                    result,
                    result_errno,
                    strerror(result_errno),
                    duration_ms);
        } else {
            cprintf("[err] %s rc=%d (%ldms)\r\n",
                    argv[0],
                    result,
                    duration_ms);
        }
    }
}

int main(void) {
    timeline_record(0, 0, "init-start", "%s", INIT_BANNER);
    setup_base_mounts();
    native_log_select(NATIVE_LOG_FALLBACK);
    native_logf("boot", "%s start", INIT_BANNER);
    native_logf("boot", "base mounts ready");
    timeline_record(0, 0, "base-mounts", "proc/sys/dev/tmpfs requested");
    klogf("<6>A90v53: base mounts ready\n");
    prepare_early_display_environment();
    native_logf("boot", "early display/input nodes prepared");
    timeline_record(0, 0, "early-nodes", "display/input/graphics nodes prepared");
    timeline_probe_boot_resources();
    klogf("<6>A90v53: early display/input nodes prepared\n");

    if (mount_cache() == 0) {
        native_log_select(NATIVE_LOG_PRIMARY);
        timeline_replay_to_log("cache");
        native_logf("boot", "%s start", INIT_BANNER);
        native_logf("boot", "base mounts ready");
        native_logf("boot", "early display/input nodes prepared");
        native_logf("boot", "cache mounted log=%s", native_log_current_path());
        timeline_record(0, 0, "cache-mount", "/cache mounted log=%s", native_log_current_path());
        mark_step("1_cache_ok_v53\n");
        klogf("<6>A90v53: cache mounted\n");
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
        klogf("<6>A90v53: cache mount failed (%d)\n", saved_errno);
    }

    if (setup_acm_gadget() == 0) {
        mark_step("2_gadget_ok_v53\n");
        native_logf("boot", "ACM gadget configured");
        timeline_record(0, 0, "usb-gadget", "ACM gadget configured");
        klogf("<6>A90v53: ACM gadget configured\n");
    } else {
        int saved_errno = errno;
        native_logf("boot", "ACM gadget failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "usb-gadget",
                        "ACM gadget failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v53: ACM gadget failed (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (wait_for_tty_gs0() == 0) {
        mark_step("3_tty_ready_v53\n");
        native_logf("boot", "ttyGS0 ready");
        timeline_record(0, 0, "ttyGS0", "/dev/ttyGS0 ready");
        klogf("<6>A90v53: ttyGS0 ready\n");
        boot_auto_frame();
        sleep(BOOT_TEST_SECONDS);
    } else {
        int saved_errno = errno;
        native_logf("boot", "ttyGS0 missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "ttyGS0",
                        "/dev/ttyGS0 missing: %s",
                        strerror(saved_errno));
        klogf("<6>A90v53: ttyGS0 missing (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (attach_console() == 0) {
        mark_step("4_console_attached_v53\n");
        native_logf("boot", "console attached");
        timeline_record(0, 0, "console", "serial console attached");
        drain_console_input(250, 1500);
        cprintf("\r\n# %s\r\n", INIT_BANNER);
        cprintf("# USB ACM serial console ready.\r\n");
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) == 0) {
            native_logf("boot", "autohud started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            timeline_record(0, 0, "autohud", "started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            cprintf("# Boot display: TEST %ds -> autohud %ds.\r\n",
                    BOOT_TEST_SECONDS,
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
        klogf("<6>A90v53: console attach failed (%d)\n", saved_errno);
    }

    while (1) {
        sleep(60);
    }
}
