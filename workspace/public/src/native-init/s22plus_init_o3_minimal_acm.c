#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>

#include "s22plus_o2_loader_core.h"
#include "module-plan.generated.h"

#define O3_MARKER "S22_NATIVE_INIT_O3_MINIMAL_ACM"
#define O3_VERSION "0.1"
#define O3_STATUS_PATH "/dev/.s22plus_o3_status"
#define O3_DAEMON_PATH "/s22plus_o3_tty_control"
#define O3_MODULE_DIR "/lib/modules/"
#define O3_GATE_ATTEMPTS 100U
#define O3_GATE_SLEEP_NS 100000000L
#define O3_TTY_ATTEMPTS 100U

struct o3_state {
    struct s22plus_o2_module_load_result load;
    struct s22plus_o2_proc_scan_result scan;
    uint64_t gate_mask;
    int setup_rc;
    int registration_rc;
    int configfs_rc;
    int mode_write_rc;
    int mode_readback_ok;
    int udc_bind_rc;
    int udc_readback_ok;
    int tty_ready;
};

static void write_all_best_effort(int fd, const char *text, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        ssize_t amount = write(fd, text + offset, size - offset);
        if (amount > 0) {
            offset += (size_t)amount;
            continue;
        }
        if (amount < 0 && errno == EINTR) {
            continue;
        }
        break;
    }
}

static void emit_text(const char *text) {
    const char *paths[] = {"/dev/kmsg", "/dev/pmsg0"};
    size_t index;
    size_t length = strlen(text);
    for (index = 0; index < sizeof(paths) / sizeof(paths[0]); ++index) {
        int fd = open(paths[index], O_WRONLY | O_CLOEXEC | O_NONBLOCK);
        if (fd >= 0) {
            write_all_best_effort(fd, text, length);
            (void)close(fd);
        }
    }
    write_all_best_effort(STDERR_FILENO, text, length);
}

static void emitf(const char *format, ...) {
    char buffer[1024];
    va_list args;
    int length;
    va_start(args, format);
    length = vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);
    if (length <= 0) {
        return;
    }
    if ((size_t)length >= sizeof(buffer)) {
        length = (int)sizeof(buffer) - 1;
    }
    emit_text(buffer);
}

static int ensure_dir(const char *path, mode_t mode) {
    if (mkdir(path, mode) == 0 || errno == EEXIST) {
        return 0;
    }
    return -errno;
}

static int ensure_chr(const char *path, mode_t mode, unsigned int major_num, unsigned int minor_num) {
    if (mknod(path, S_IFCHR | mode, makedev(major_num, minor_num)) == 0 || errno == EEXIST) {
        return 0;
    }
    return -errno;
}

static int mount_once(const char *source, const char *target, const char *type, unsigned long flags) {
    if (mount(source, target, type, flags, NULL) == 0 || errno == EBUSY) {
        return 0;
    }
    return -errno;
}

static int setup_minimal_fs(void) {
    int rc;
    rc = ensure_dir("/proc", 0555);
    if (rc != 0) {
        return rc;
    }
    rc = ensure_dir("/sys", 0555);
    if (rc != 0) {
        return rc;
    }
    rc = ensure_dir("/dev", 0755);
    if (rc != 0) {
        return rc;
    }
    rc = ensure_dir("/config", 0755);
    if (rc != 0) {
        return rc;
    }
    rc = mount_once("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC);
    if (rc != 0) {
        return rc;
    }
    rc = mount_once("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC);
    if (rc != 0) {
        return rc;
    }
    rc = mount_once("devtmpfs", "/dev", "devtmpfs", MS_NOSUID);
    if (rc != 0) {
        return rc;
    }
    (void)ensure_chr("/dev/console", 0600, 5, 1);
    (void)ensure_chr("/dev/null", 0666, 1, 3);
    (void)ensure_chr("/dev/zero", 0666, 1, 5);
    (void)ensure_chr("/dev/kmsg", 0600, 1, 11);
    (void)ensure_chr("/dev/pmsg0", 0220, 1, 12);
    return 0;
}

static void setup_stdio(void) {
    int fd = open("/dev/console", O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        fd = open("/dev/null", O_RDWR | O_CLOEXEC);
    }
    if (fd >= 0) {
        (void)dup2(fd, STDIN_FILENO);
        (void)dup2(fd, STDOUT_FILENO);
        (void)dup2(fd, STDERR_FILENO);
        if (fd > STDERR_FILENO) {
            (void)close(fd);
        }
    }
}

static int write_text_file(const char *path, const char *text) {
    size_t length = strlen(text);
    size_t offset = 0;
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return -errno;
    }
    while (offset < length) {
        ssize_t amount = write(fd, text + offset, length - offset);
        if (amount > 0) {
            offset += (size_t)amount;
            continue;
        }
        if (amount < 0 && errno == EINTR) {
            continue;
        }
        {
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

static int read_text_file(const char *path, char *buffer, size_t size) {
    ssize_t amount;
    int fd;
    if (size < 2) {
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -errno;
    }
    do {
        amount = read(fd, buffer, size - 1);
    } while (amount < 0 && errno == EINTR);
    if (amount < 0) {
        int saved = errno;
        (void)close(fd);
        return -saved;
    }
    buffer[amount] = '\0';
    (void)close(fd);
    return (int)amount;
}

static int text_value_is(const char *actual, const char *expected) {
    size_t length = strlen(expected);
    if (strncmp(actual, expected, length) != 0) {
        return 0;
    }
    return actual[length] == '\0' || actual[length] == '\n' || actual[length] == '\r';
}

static int module_filename_valid(const char *filename) {
    size_t length;
    if (filename == NULL || strchr(filename, '/') != NULL || strstr(filename, "..") != NULL) {
        return 0;
    }
    length = strlen(filename);
    return length > 3 && strcmp(filename + length - 3, ".ko") == 0;
}

static long module_open_callback(void *context, const char *filename) {
    char path[256];
    int length;
    int fd;
    (void)context;
    if (!module_filename_valid(filename)) {
        return -EINVAL;
    }
    length = snprintf(path, sizeof(path), "%s%s", O3_MODULE_DIR, filename);
    if (length <= 0 || (size_t)length >= sizeof(path)) {
        return -ENAMETOOLONG;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    return fd >= 0 ? fd : -errno;
}

static long module_finit_callback(void *context, int fd, const char *params) {
    long rc;
    (void)context;
    errno = 0;
    rc = syscall(SYS_finit_module, fd, params, 0);
    return rc == 0 ? 0 : -errno;
}

static long module_close_callback(void *context, int fd) {
    (void)context;
    return close(fd) == 0 ? 0 : -errno;
}

struct fd_reader_context {
    int fd;
};

static long fd_read_callback(void *context, void *buffer, size_t size) {
    struct fd_reader_context *reader = (struct fd_reader_context *)context;
    ssize_t amount;
    do {
        amount = read(reader->fd, buffer, size);
    } while (amount < 0 && errno == EINTR);
    return amount >= 0 ? amount : -errno;
}

static int path_present_callback(void *context, const char *path) {
    (void)context;
    return access(path, F_OK) == 0 ? 1 : 0;
}

static void sleep_gate_interval(void) {
    struct timespec request = {.tv_sec = 0, .tv_nsec = O3_GATE_SLEEP_NS};
    while (nanosleep(&request, &request) != 0 && errno == EINTR) {
    }
}

static int wait_for_bind_gates(struct o3_state *state) {
    struct s22plus_o2_gate_ops ops = {.context = NULL, .path_present = path_present_callback};
    size_t prefix;
    for (prefix = 1; prefix <= S22PLUS_O2_BIND_GATE_COUNT; ++prefix) {
        unsigned int attempt;
        int passed = 0;
        for (attempt = 0; attempt < O3_GATE_ATTEMPTS; ++attempt) {
            struct s22plus_o2_gate_result result;
            int rc = s22plus_o2_check_bind_gates(s22plus_o2_bind_gates, prefix, &ops, &result);
            if (rc == S22PLUS_O2_OK) {
                passed = 1;
                break;
            }
            if (rc < 0 || result.first_missing_index + 1 < prefix) {
                emitf(
                    O3_MARKER " phase=gate_error gate=%s index=%zu rc=%d missing=%zu\n",
                    s22plus_o2_bind_gates[prefix - 1].id,
                    prefix - 1,
                    rc,
                    result.first_missing_index
                );
                return rc < 0 ? rc : -EIO;
            }
            sleep_gate_interval();
        }
        if (!passed) {
            emitf(
                O3_MARKER " phase=gate_timeout gate=%s index=%zu attempts=%u\n",
                s22plus_o2_bind_gates[prefix - 1].id,
                prefix - 1,
                O3_GATE_ATTEMPTS
            );
            return -ETIMEDOUT;
        }
        state->gate_mask |= UINT64_C(1) << (prefix - 1);
        emitf(
            O3_MARKER " phase=gate_pass gate=%s index=%zu path=%s\n",
            s22plus_o2_bind_gates[prefix - 1].id,
            prefix - 1,
            s22plus_o2_bind_gates[prefix - 1].path
        );
    }
    return 0;
}

static int make_gadget_paths(void) {
    const char *paths[] = {
        "/config/usb_gadget",
        "/config/usb_gadget/g1",
        "/config/usb_gadget/g1/strings",
        "/config/usb_gadget/g1/strings/0x409",
        "/config/usb_gadget/g1/configs",
        "/config/usb_gadget/g1/configs/c.1",
        "/config/usb_gadget/g1/configs/c.1/strings",
        "/config/usb_gadget/g1/configs/c.1/strings/0x409",
        "/config/usb_gadget/g1/functions",
        "/config/usb_gadget/g1/functions/acm.usb0",
    };
    size_t index;
    for (index = 0; index < sizeof(paths) / sizeof(paths[0]); ++index) {
        int rc = ensure_dir(paths[index], 0755);
        if (rc != 0) {
            return rc;
        }
    }
    return 0;
}

static int create_minimal_acm_gadget(void) {
    struct attr {
        const char *path;
        const char *value;
    };
    const struct attr attrs[] = {
        {"/config/usb_gadget/g1/idVendor", "0x04e8"},
        {"/config/usb_gadget/g1/idProduct", "0x6861"},
        {"/config/usb_gadget/g1/bcdUSB", "0x0200"},
        {"/config/usb_gadget/g1/bcdDevice", "0x0001"},
        {"/config/usb_gadget/g1/strings/0x409/serialnumber", "S22O3ACM01"},
        {"/config/usb_gadget/g1/strings/0x409/manufacturer", "S22 Native"},
        {"/config/usb_gadget/g1/strings/0x409/product", "S22 O3 Minimal ACM"},
        {"/config/usb_gadget/g1/configs/c.1/MaxPower", "500"},
        {"/config/usb_gadget/g1/configs/c.1/bmAttributes", "0x80"},
        {"/config/usb_gadget/g1/configs/c.1/strings/0x409/configuration", "acm"},
    };
    size_t index;
    int rc = mount_once("configfs", "/config", "configfs", MS_NOSUID | MS_NODEV | MS_NOEXEC);
    if (rc != 0) {
        return rc;
    }
    rc = make_gadget_paths();
    if (rc != 0) {
        return rc;
    }
    for (index = 0; index < sizeof(attrs) / sizeof(attrs[0]); ++index) {
        rc = write_text_file(attrs[index].path, attrs[index].value);
        if (rc != 0) {
            emitf(O3_MARKER " phase=config_attr_fail path=%s rc=%d\n", attrs[index].path, rc);
            return rc;
        }
    }
    if (symlink("../../functions/acm.usb0", "/config/usb_gadget/g1/configs/c.1/f1") != 0 &&
        errno != EEXIST) {
        return -errno;
    }
    return 0;
}

static int wait_for_tty(void) {
    unsigned int attempt;
    for (attempt = 0; attempt < O3_TTY_ATTEMPTS; ++attempt) {
        struct stat info;
        if (stat("/dev/ttyGS0", &info) == 0 && S_ISCHR(info.st_mode)) {
            return 1;
        }
        sleep_gate_interval();
    }
    return 0;
}

static void format_status(
    char *buffer,
    size_t size,
    const char *phase,
    const char *result,
    int rc,
    const struct o3_state *state
) {
    (void)snprintf(
        buffer,
        size,
        "marker=%s\n"
        "version=%s\n"
        "phase=%s\n"
        "result=%s\n"
        "rc=%d\n"
        "plan_count=%zu\n"
        "module_attempted=%zu\n"
        "module_loaded=%zu\n"
        "module_eexist=%zu\n"
        "module_failed=%zu\n"
        "module_first_failure_index=%zu\n"
        "module_first_failure_rc=%ld\n"
        "proc_registration_rc=%d\n"
        "proc_eof=%d\n"
        "proc_bytes=%llu\n"
        "proc_found=%zu\n"
        "gate_mask=0x%llx\n"
        "gate_count=%zu\n"
        "configfs_rc=%d\n"
        "ssusb_mode_write_rc=%d\n"
        "ssusb_mode_readback_ok=%d\n"
        "udc_bind_rc=%d\n"
        "udc_readback_ok=%d\n"
        "ttyGS0_ready=%d\n"
        "gadget_function=acm.usb0\n"
        "udc=a600000.dwc3\n",
        O3_MARKER,
        O3_VERSION,
        phase,
        result,
        rc,
        (size_t)S22PLUS_O2_MODULE_PLAN_COUNT,
        state->load.attempted,
        state->load.loaded,
        state->load.already_loaded,
        state->load.failed,
        state->load.first_failure_index,
        state->load.first_failure_rc,
        state->registration_rc,
        state->scan.eof_seen,
        (unsigned long long)state->scan.bytes_read,
        state->scan.found_count,
        (unsigned long long)state->gate_mask,
        (size_t)S22PLUS_O2_BIND_GATE_COUNT,
        state->configfs_rc,
        state->mode_write_rc,
        state->mode_readback_ok,
        state->udc_bind_rc,
        state->udc_readback_ok,
        state->tty_ready
    );
}

static void write_status(
    const char *phase,
    const char *result,
    int rc,
    const struct o3_state *state
) {
    char buffer[2048];
    int fd;
    format_status(buffer, sizeof(buffer), phase, result, rc, state);
    fd = open(O3_STATUS_PATH, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd >= 0) {
        write_all_best_effort(fd, buffer, strlen(buffer));
        (void)fsync(fd);
        (void)close(fd);
    }
    emitf(O3_MARKER " phase=%s result=%s rc=%d\n", phase, result, rc);
}

__attribute__((noreturn)) static void park_forever(void) {
    struct timespec delay = {.tv_sec = 10, .tv_nsec = 0};
    for (;;) {
        (void)nanosleep(&delay, NULL);
    }
}

__attribute__((noreturn)) static void fail_and_park(
    const char *phase,
    int rc,
    const struct o3_state *state
) {
    write_status(phase, "fail", rc, state);
    park_forever();
}

int main(void) {
    struct o3_state state;
    struct s22plus_o2_module_loader_ops loader_ops;
    const char *runtime_names[S22PLUS_O2_MODULE_PLAN_COUNT];
    unsigned char found[S22PLUS_O2_MODULE_PLAN_COUNT];
    struct fd_reader_context fd_context;
    struct s22plus_o2_reader reader;
    char value[128];
    char *daemon_argv[] = {
        (char *)O3_DAEMON_PATH,
        (char *)"--device",
        (char *)"/dev/ttyGS0",
        (char *)"--status-file",
        (char *)O3_STATUS_PATH,
        (char *)"--max-requests",
        (char *)"128",
        (char *)"--idle-timeout-ms",
        (char *)"180000",
        NULL,
    };
    char *daemon_env[] = {(char *)"PATH=/sbin:/bin", NULL};
    size_t index;
    int proc_fd;
    int rc;

    memset(&state, 0, sizeof(state));
    state.load.first_failure_index = S22PLUS_O2_MODULE_PLAN_COUNT;
    state.setup_rc = setup_minimal_fs();
    setup_stdio();
    emitf(
        O3_MARKER " version=%s pid1=direct plan_count=%zu generic_acm=1 no_android_handoff=1\n",
        O3_VERSION,
        (size_t)S22PLUS_O2_MODULE_PLAN_COUNT
    );
    if (state.setup_rc != 0) {
        fail_and_park("setup", state.setup_rc, &state);
    }

    loader_ops.context = NULL;
    loader_ops.open_module = module_open_callback;
    loader_ops.finit_module = module_finit_callback;
    loader_ops.close_module = module_close_callback;
    rc = s22plus_o2_execute_module_plan(
        s22plus_o2_module_plan,
        S22PLUS_O2_MODULE_PLAN_COUNT,
        &loader_ops,
        &state.load
    );
    emitf(
        O3_MARKER " phase=module_plan rc=%d attempted=%zu loaded=%zu eexist=%zu failed=%zu first=%zu first_rc=%ld\n",
        rc,
        state.load.attempted,
        state.load.loaded,
        state.load.already_loaded,
        state.load.failed,
        state.load.first_failure_index,
        state.load.first_failure_rc
    );
    if (rc != S22PLUS_O2_OK) {
        fail_and_park("module-plan", rc, &state);
    }

    for (index = 0; index < S22PLUS_O2_MODULE_PLAN_COUNT; ++index) {
        runtime_names[index] = s22plus_o2_module_plan[index].runtime_name;
    }
    proc_fd = open("/proc/modules", O_RDONLY | O_CLOEXEC);
    if (proc_fd < 0) {
        fail_and_park("proc-modules-open", -errno, &state);
    }
    fd_context.fd = proc_fd;
    reader.context = &fd_context;
    reader.read = fd_read_callback;
    state.registration_rc = s22plus_o2_scan_proc_modules(
        &reader,
        runtime_names,
        S22PLUS_O2_MODULE_PLAN_COUNT,
        found,
        &state.scan
    );
    (void)close(proc_fd);
    if (state.registration_rc != S22PLUS_O2_OK || !state.scan.eof_seen ||
        state.scan.found_count != S22PLUS_O2_MODULE_PLAN_COUNT) {
        for (index = 0; index < S22PLUS_O2_MODULE_PLAN_COUNT; ++index) {
            if (!found[index]) {
                emitf(
                    O3_MARKER " phase=proc_module_missing index=%zu name=%s\n",
                    index,
                    runtime_names[index]
                );
                break;
            }
        }
        fail_and_park("proc-modules", state.registration_rc, &state);
    }
    emitf(
        O3_MARKER " phase=proc_modules_pass bytes=%llu reads=%llu found=%zu eof=%d\n",
        (unsigned long long)state.scan.bytes_read,
        (unsigned long long)state.scan.read_calls,
        state.scan.found_count,
        state.scan.eof_seen
    );

    rc = wait_for_bind_gates(&state);
    if (rc != 0) {
        fail_and_park("bind-gates", rc, &state);
    }

    state.configfs_rc = create_minimal_acm_gadget();
    if (state.configfs_rc != 0) {
        fail_and_park("configfs-acm", state.configfs_rc, &state);
    }
    state.mode_write_rc = write_text_file(
        "/sys/devices/platform/soc/a600000.ssusb/mode",
        "peripheral"
    );
    if (state.mode_write_rc != 0) {
        fail_and_park("ssusb-mode-write", state.mode_write_rc, &state);
    }
    rc = read_text_file("/sys/devices/platform/soc/a600000.ssusb/mode", value, sizeof(value));
    state.mode_readback_ok = rc >= 0 && text_value_is(value, "peripheral");
    if (!state.mode_readback_ok) {
        fail_and_park("ssusb-mode-readback", rc < 0 ? rc : -EIO, &state);
    }
    state.udc_bind_rc = write_text_file("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    if (state.udc_bind_rc != 0) {
        fail_and_park("udc-bind", state.udc_bind_rc, &state);
    }
    rc = read_text_file("/config/usb_gadget/g1/UDC", value, sizeof(value));
    state.udc_readback_ok = rc >= 0 && text_value_is(value, "a600000.dwc3");
    if (!state.udc_readback_ok) {
        fail_and_park("udc-readback", rc < 0 ? rc : -EIO, &state);
    }
    state.tty_ready = wait_for_tty();
    if (!state.tty_ready) {
        fail_and_park("ttyGS0", -ETIMEDOUT, &state);
    }

    write_status("control-ready", "ready", 0, &state);
    emitf(O3_MARKER " phase=exec_control path=%s\n", O3_DAEMON_PATH);
    (void)execve(O3_DAEMON_PATH, daemon_argv, daemon_env);
    fail_and_park("exec-control", -errno, &state);
}
