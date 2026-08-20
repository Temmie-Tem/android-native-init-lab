#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <time.h>
#include <unistd.h>

#define N3U0_MARKER "S20PLUS_N3U0_ACM_WITNESS_V1"
#define N3U0_BANNER "S20PLUS_N3U0_ACM_V1\n"
#define N3U0_UDC "a600000.dwc3"
#define N3U0_CONFIGFS_MAGIC 0x62656570L
#define N3U0_GADGET_ROOT "/config/usb_gadget"
#define N3U0_STOCK_GADGET N3U0_GADGET_ROOT "/g1"
#define N3U0_STOCK_UDC N3U0_STOCK_GADGET "/UDC"
#define N3U0_OWN_GADGET N3U0_GADGET_ROOT "/s20plus_n3u0"
#define N3U0_OWN_UDC N3U0_OWN_GADGET "/UDC"
#define N3U0_OWN_STRINGS N3U0_OWN_GADGET "/strings/0x409"
#define N3U0_OWN_CONFIG N3U0_OWN_GADGET "/configs/c.1"
#define N3U0_OWN_CONFIG_STRINGS N3U0_OWN_CONFIG "/strings/0x409"
#define N3U0_OWN_FUNCTION N3U0_OWN_GADGET "/functions/acm.usb0"
#define N3U0_OWN_FUNCTION_PORT N3U0_OWN_FUNCTION "/port_num"
#define N3U0_OWN_LINK N3U0_OWN_CONFIG "/f1"
#define N3U0_OWN_LINK_TARGET "../../functions/acm.usb0"
#define N3U0_UDC_CLASS "/sys/class/udc"
#define N3U0_MAX_PORT 3
#define N3U0_TTY_WAIT_ATTEMPTS 100
#define N3U0_BANNER_ATTEMPTS 40
#define N3U0_TTY_WAIT_NS 50000000L
#define N3U0_BANNER_INTERVAL_NS 250000000L

struct n3u0_ops {
    int (*preflight)(void *context);
    int (*stock_unbind)(void *context);
    int (*owned_create)(void *context);
    int (*owned_bind)(void *context);
    int (*banner)(void *context);
    int (*owned_cleanup)(void *context);
    int (*stock_restore)(void *context);
};

#ifndef S20PLUS_N3U0_HOST_TEST
static volatile sig_atomic_t stop_requested;

static void handle_signal(int signal_number) {
    (void)signal_number;
    stop_requested = 1;
}

static void sleep_ns(long nanoseconds) {
    struct timespec request;
    struct timespec remaining;
    request.tv_sec = nanoseconds / 1000000000L;
    request.tv_nsec = nanoseconds % 1000000000L;
    while (nanosleep(&request, &remaining) != 0 && errno == EINTR && !stop_requested) {
        request = remaining;
    }
}

static void write_best_effort(int fd, const char *text, size_t length) {
    size_t offset = 0;
    while (offset < length) {
        ssize_t amount = write(fd, text + offset, length - offset);
        if (amount > 0) {
            offset += (size_t)amount;
        } else if (amount < 0 && errno == EINTR) {
            continue;
        } else {
            break;
        }
    }
}

static void log_line(const char *format, ...) {
    char buffer[512];
    va_list arguments;
    int length;
    int fd;
    va_start(arguments, format);
    length = vsnprintf(buffer, sizeof(buffer), format, arguments);
    va_end(arguments);
    if (length <= 0) {
        return;
    }
    if ((size_t)length >= sizeof(buffer)) {
        length = (int)sizeof(buffer) - 1;
    }
    fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC | O_NONBLOCK);
    if (fd >= 0) {
        write_best_effort(fd, buffer, (size_t)length);
        (void)close(fd);
    }
    write_best_effort(STDERR_FILENO, buffer, (size_t)length);
}

static int direct_directory(const char *path) {
    struct stat state;
    if (lstat(path, &state) != 0) {
        return -errno;
    }
    return S_ISDIR(state.st_mode) ? 0 : -ENOTDIR;
}

static int path_must_be_absent(const char *path) {
    struct stat state;
    if (lstat(path, &state) == 0) {
        return -EEXIST;
    }
    return errno == ENOENT ? 0 : -errno;
}

static int read_attr(const char *path, char *buffer, size_t capacity) {
    size_t used = 0;
    int fd;
    if (capacity < 2) {
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    while (used < capacity - 1) {
        ssize_t amount = read(fd, buffer + used, capacity - 1 - used);
        if (amount > 0) {
            used += (size_t)amount;
        } else if (amount == 0) {
            break;
        } else if (errno == EINTR) {
            continue;
        } else {
            int saved = errno;
            (void)close(fd);
            return -saved;
        }
    }
    if (used == capacity - 1) {
        char extra;
        ssize_t amount;
        do {
            amount = read(fd, &extra, 1);
        } while (amount < 0 && errno == EINTR);
        if (amount != 0) {
            (void)close(fd);
            return -EOVERFLOW;
        }
    }
    if (close(fd) != 0) {
        return -errno;
    }
    while (used > 0 && (buffer[used - 1] == '\n' || buffer[used - 1] == '\r')) {
        --used;
    }
    buffer[used] = '\0';
    return (int)used;
}

static int write_attr(const char *path, const char *value) {
    size_t length = strlen(value);
    size_t offset = 0;
    int fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    while (offset < length) {
        ssize_t amount = write(fd, value + offset, length - offset);
        if (amount > 0) {
            offset += (size_t)amount;
        } else if (amount < 0 && errno == EINTR) {
            continue;
        } else {
            int saved = errno != 0 ? errno : EIO;
            (void)close(fd);
            return -saved;
        }
    }
    if (close(fd) != 0) {
        return -errno;
    }
    return 0;
}

static int exact_single_udc(void) {
    DIR *directory = opendir(N3U0_UDC_CLASS);
    struct dirent *entry;
    unsigned int count = 0;
    int result = 0;
    if (directory == NULL) {
        return -errno;
    }
    errno = 0;
    while ((entry = readdir(directory)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        ++count;
        if (strcmp(entry->d_name, N3U0_UDC) != 0) {
            result = -EXDEV;
            break;
        }
        errno = 0;
    }
    if (entry == NULL && errno != 0 && result == 0) {
        result = -errno;
    }
    if (closedir(directory) != 0 && result == 0) {
        result = -errno;
    }
    if (result == 0 && count != 1) {
        result = -ENODEV;
    }
    return result;
}

static int real_preflight(void *context) {
    struct statfs fs;
    char value[64];
    int result;
    (void)context;
    if (statfs("/config", &fs) != 0 || fs.f_type != N3U0_CONFIGFS_MAGIC) {
        return -ENODEV;
    }
    if ((result = direct_directory(N3U0_GADGET_ROOT)) != 0 ||
        (result = direct_directory(N3U0_STOCK_GADGET)) != 0 ||
        (result = path_must_be_absent(N3U0_OWN_GADGET)) != 0 ||
        (result = exact_single_udc()) != 0) {
        return result;
    }
    result = read_attr(N3U0_STOCK_UDC, value, sizeof(value));
    if (result < 0 || strcmp(value, N3U0_UDC) != 0) {
        return result < 0 ? result : -EBUSY;
    }
    return 0;
}

static int real_stock_unbind(void *context) {
    char value[64];
    int result;
    (void)context;
    result = read_attr(N3U0_STOCK_UDC, value, sizeof(value));
    if (result < 0 || strcmp(value, N3U0_UDC) != 0) {
        return result < 0 ? result : -EBUSY;
    }
    result = write_attr(N3U0_STOCK_UDC, "\n");
    if (result != 0) {
        return result;
    }
    result = read_attr(N3U0_STOCK_UDC, value, sizeof(value));
    return result < 0 ? result : (value[0] == '\0' ? 0 : -EBUSY);
}

static int mkdir_exclusive(const char *path) {
    return mkdir(path, 0755) == 0 ? 0 : -errno;
}

static int real_owned_create(void *context) {
    int result;
    (void)context;
    if ((result = mkdir_exclusive(N3U0_OWN_GADGET)) != 0 ||
        (result = write_attr(N3U0_OWN_GADGET "/idVendor", "0x04e8")) != 0 ||
        (result = write_attr(N3U0_OWN_GADGET "/idProduct", "0x6861")) != 0 ||
        (result = write_attr(N3U0_OWN_GADGET "/bcdUSB", "0x0200")) != 0 ||
        (result = write_attr(N3U0_OWN_GADGET "/bcdDevice", "0x0001")) != 0 ||
        (result = mkdir_exclusive(N3U0_OWN_STRINGS)) != 0 ||
        (result = write_attr(N3U0_OWN_STRINGS "/manufacturer", "Samsung")) != 0 ||
        (result = write_attr(N3U0_OWN_STRINGS "/product", "S20Plus-N3U0")) != 0 ||
        (result = mkdir_exclusive(N3U0_OWN_CONFIG)) != 0 ||
        (result = mkdir_exclusive(N3U0_OWN_CONFIG_STRINGS)) != 0 ||
        (result = write_attr(N3U0_OWN_CONFIG_STRINGS "/configuration", "N3U0 ACM")) != 0 ||
        (result = write_attr(N3U0_OWN_CONFIG "/MaxPower", "2")) != 0 ||
        (result = mkdir_exclusive(N3U0_OWN_FUNCTION)) != 0) {
        return result;
    }
    if (symlink(N3U0_OWN_LINK_TARGET, N3U0_OWN_LINK) != 0) {
        return -errno;
    }
    return 0;
}

static int real_owned_bind(void *context) {
    char value[64];
    int result;
    (void)context;
    result = exact_single_udc();
    if (result != 0) {
        return result;
    }
    result = read_attr(N3U0_STOCK_UDC, value, sizeof(value));
    if (result < 0 || value[0] != '\0') {
        return result < 0 ? result : -EBUSY;
    }
    result = write_attr(N3U0_OWN_UDC, N3U0_UDC);
    if (result != 0) {
        return result;
    }
    result = read_attr(N3U0_OWN_UDC, value, sizeof(value));
    return result < 0 ? result : (strcmp(value, N3U0_UDC) == 0 ? 0 : -EIO);
}

static int owned_tty_path(char *path, size_t capacity) {
    char value[16];
    int result = read_attr(N3U0_OWN_FUNCTION_PORT, value, sizeof(value));
    int port;
    if (result != 1 || value[0] < '0' || value[0] > '9') {
        return result < 0 ? result : -ERANGE;
    }
    port = value[0] - '0';
    if (port < 0 || port > N3U0_MAX_PORT) {
        return -ERANGE;
    }
    result = snprintf(path, capacity, "/dev/ttyGS%d", port);
    return result > 0 && (size_t)result < capacity ? 0 : -ENAMETOOLONG;
}

static int write_banner_once(const char *path) {
    int fd = open(path, O_WRONLY | O_NOCTTY | O_CLOEXEC | O_NONBLOCK | O_NOFOLLOW);
    size_t offset = 0;
    if (fd < 0) {
        return -errno;
    }
    while (offset < sizeof(N3U0_BANNER) - 1) {
        ssize_t amount = write(fd, N3U0_BANNER + offset, sizeof(N3U0_BANNER) - 1 - offset);
        if (amount > 0) {
            offset += (size_t)amount;
        } else if (amount < 0 && errno == EINTR) {
            continue;
        } else {
            int saved = errno != 0 ? errno : EIO;
            (void)close(fd);
            return -saved;
        }
    }
    return close(fd) == 0 ? 0 : -errno;
}

static int real_banner(void *context) {
    char path[32];
    struct stat state;
    int result;
    int attempt;
    int success = 0;
    (void)context;
    result = owned_tty_path(path, sizeof(path));
    if (result != 0) {
        return result;
    }
    for (attempt = 0; attempt < N3U0_TTY_WAIT_ATTEMPTS && !stop_requested; ++attempt) {
        if (lstat(path, &state) == 0 && S_ISCHR(state.st_mode)) {
            break;
        }
        sleep_ns(N3U0_TTY_WAIT_NS);
    }
    if (attempt == N3U0_TTY_WAIT_ATTEMPTS || stop_requested) {
        return -ETIMEDOUT;
    }
    for (attempt = 0; attempt < N3U0_BANNER_ATTEMPTS && !stop_requested; ++attempt) {
        if (write_banner_once(path) == 0) {
            success = 1;
        }
        sleep_ns(N3U0_BANNER_INTERVAL_NS);
    }
    return success && !stop_requested ? 0 : -EIO;
}

static int remove_symlink_exact(const char *path, const char *target) {
    char current[128];
    struct stat state;
    ssize_t amount;
    if (lstat(path, &state) != 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    if (!S_ISLNK(state.st_mode)) {
        return -EINVAL;
    }
    amount = readlink(path, current, sizeof(current) - 1);
    if (amount < 0 || (size_t)amount >= sizeof(current) - 1) {
        return amount < 0 ? -errno : -EOVERFLOW;
    }
    current[amount] = '\0';
    if (strcmp(current, target) != 0) {
        return -EXDEV;
    }
    return unlink(path) == 0 ? 0 : -errno;
}

static int remove_directory_if_present(const char *path) {
    struct stat state;
    if (lstat(path, &state) != 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    if (!S_ISDIR(state.st_mode)) {
        return -ENOTDIR;
    }
    return rmdir(path) == 0 ? 0 : -errno;
}

static int real_owned_cleanup(void *context) {
    const char *directories[] = {
        N3U0_OWN_CONFIG_STRINGS,
        N3U0_OWN_CONFIG,
        N3U0_OWN_FUNCTION,
        N3U0_OWN_STRINGS,
        N3U0_OWN_GADGET,
    };
    size_t index;
    int first_error = 0;
    int result;
    char value[64];
    (void)context;
    if (lstat(N3U0_OWN_GADGET, &(struct stat){0}) == 0) {
        result = write_attr(N3U0_OWN_UDC, "\n");
        if (result != 0 && result != -ENOENT && first_error == 0) {
            first_error = result;
        }
        result = read_attr(N3U0_OWN_UDC, value, sizeof(value));
        if (result >= 0 && value[0] != '\0' && first_error == 0) {
            first_error = -EBUSY;
        }
    }
    result = remove_symlink_exact(N3U0_OWN_LINK, N3U0_OWN_LINK_TARGET);
    if (result != 0 && first_error == 0) {
        first_error = result;
    }
    for (index = 0; index < sizeof(directories) / sizeof(directories[0]); ++index) {
        result = remove_directory_if_present(directories[index]);
        if (result != 0 && first_error == 0) {
            first_error = result;
        }
    }
    return first_error;
}

static int real_stock_restore(void *context) {
    char value[64];
    int result;
    (void)context;
    result = read_attr(N3U0_STOCK_UDC, value, sizeof(value));
    if (result < 0) {
        return result;
    }
    if (strcmp(value, N3U0_UDC) == 0) {
        return 0;
    }
    if (value[0] != '\0') {
        return -EBUSY;
    }
    result = exact_single_udc();
    if (result != 0) {
        return result;
    }
    result = write_attr(N3U0_STOCK_UDC, N3U0_UDC);
    if (result != 0) {
        return result;
    }
    result = read_attr(N3U0_STOCK_UDC, value, sizeof(value));
    return result < 0 ? result : (strcmp(value, N3U0_UDC) == 0 ? 0 : -EIO);
}
#endif

static int run_transaction(const struct n3u0_ops *operations, void *context) {
    int result;
    int cleanup_result = 0;
    int restore_result = 0;
    bool stock_restore_required = false;
    bool owned_touched = false;
    result = operations->preflight(context);
    if (result != 0) {
        return result;
    }
    /*
     * Once stock_unbind is invoked, an error can occur after the configfs
     * write took effect (including readback or close failure).  Treat every
     * return from that boundary as potentially consumed and always attempt
     * the exact stock restore.  A pre-effect failure is harmless because the
     * restore operation accepts an already-bound exact stock gadget.
     */
    stock_restore_required = true;
    result = operations->stock_unbind(context);
    if (result != 0) {
        restore_result = operations->stock_restore(context);
        return result != 0 ? result : restore_result;
    }
    owned_touched = true;
    result = operations->owned_create(context);
    if (result == 0) {
        result = operations->owned_bind(context);
    }
    if (result == 0) {
        result = operations->banner(context);
    }
    if (owned_touched) {
        cleanup_result = operations->owned_cleanup(context);
    }
    if (stock_restore_required) {
        restore_result = operations->stock_restore(context);
    }
    if (result != 0) {
        return result;
    }
    if (cleanup_result != 0) {
        return cleanup_result;
    }
    return restore_result;
}

#ifdef S20PLUS_N3U0_HOST_TEST
struct fake_state {
    int fail_step;
    int calls[7];
    int stock_unbind_effect;
};

static int fake_call(void *context, int step) {
    struct fake_state *state = context;
    state->calls[step] += 1;
    return state->fail_step == step ? -(100 + step) : 0;
}

static int fake_preflight(void *context) { return fake_call(context, 0); }
static int fake_stock_unbind(void *context) {
    struct fake_state *state = context;
    int result;
    state->calls[1] += 1;
    state->stock_unbind_effect = 1;
    result = state->fail_step == 1 ? -101 : 0;
    return result;
}
static int fake_owned_create(void *context) { return fake_call(context, 2); }
static int fake_owned_bind(void *context) { return fake_call(context, 3); }
static int fake_banner(void *context) { return fake_call(context, 4); }
static int fake_owned_cleanup(void *context) { return fake_call(context, 5); }
static int fake_stock_restore(void *context) { return fake_call(context, 6); }

static int host_selftest(void) {
    const struct n3u0_ops operations = {
        fake_preflight, fake_stock_unbind, fake_owned_create, fake_owned_bind,
        fake_banner, fake_owned_cleanup, fake_stock_restore,
    };
    int fail_step;
    for (fail_step = -1; fail_step < 7; ++fail_step) {
        struct fake_state state = {0};
        int result;
        state.fail_step = fail_step;
        result = run_transaction(&operations, &state);
        if ((fail_step < 0 && result != 0) || (fail_step >= 0 && result == 0)) {
            return 1;
        }
        if (state.calls[0] != 1) {
            return 2;
        }
        if (fail_step == 0 && (state.calls[1] != 0 || state.calls[5] != 0 || state.calls[6] != 0)) {
            return 3;
        }
        if (fail_step == 1 &&
            (state.stock_unbind_effect != 1 || state.calls[5] != 0 || state.calls[6] != 1)) {
            return 4;
        }
        if (fail_step >= 2 && (state.calls[5] != 1 || state.calls[6] != 1)) {
            return 5;
        }
    }
    puts("s20plus_n3u0_host_selftest=PASS");
    return 0;
}
#endif

int main(int argc, char **argv) {
#ifdef S20PLUS_N3U0_HOST_TEST
    (void)argc;
    (void)argv;
    return host_selftest();
#else
    const struct n3u0_ops operations = {
        real_preflight, real_stock_unbind, real_owned_create, real_owned_bind,
        real_banner, real_owned_cleanup, real_stock_restore,
    };
    struct sigaction action;
    int result;
    (void)argv;
    if (argc != 1) {
        return 64;
    }
    memset(&action, 0, sizeof(action));
    action.sa_handler = handle_signal;
    sigemptyset(&action.sa_mask);
    (void)sigaction(SIGTERM, &action, NULL);
    (void)sigaction(SIGINT, &action, NULL);
    (void)sigaction(SIGHUP, &action, NULL);
    log_line(N3U0_MARKER " phase=start\n");
    result = run_transaction(&operations, NULL);
    log_line(N3U0_MARKER " phase=terminal rc=%d\n", result);
    return result == 0 ? 0 : 1;
#endif
}
