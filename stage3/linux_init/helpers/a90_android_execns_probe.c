#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>

#ifndef MNT_DETACH
#define MNT_DETACH 2
#endif

#define EXECNS_VERSION "a90_android_execns_probe v1"
#define MAX_PATH_LEN 512
#define MAX_CAPTURE_SIZE (1024 * 1024)

struct config {
    const char *system_root;
    const char *vendor_block;
    const char *vendor_fstype;
    const char *target;
    const char *linker;
    const char *mode;
    int timeout_sec;
};

struct buffer {
    char *data;
    size_t len;
    size_t cap;
    bool truncated;
};

struct paths {
    char base[MAX_PATH_LEN];
    char root[MAX_PATH_LEN];
    char system[MAX_PATH_LEN];
    char vendor[MAX_PATH_LEN];
    char vendor_source[MAX_PATH_LEN];
    char proc[MAX_PATH_LEN];
    char apex[MAX_PATH_LEN];
    char linkerconfig[MAX_PATH_LEN];
};

static void usage(FILE *out) {
    fprintf(out, "%s\n", EXECNS_VERSION);
    fprintf(out,
            "usage: a90_android_execns_probe "
            "--system-root /mnt/system/system "
            "--vendor-block /dev/block/sda29 "
            "--vendor-fstype ext4 "
            "--target /vendor/bin/cnss-daemon "
            "--linker /system/bin/linker64 "
            "--mode linker-list "
            "--timeout-sec <1..30>\n");
}

static bool streq(const char *a, const char *b) {
    return a != NULL && b != NULL && strcmp(a, b) == 0;
}

static bool parse_int_range(const char *value, int min_value, int max_value, int *out) {
    char *end = NULL;
    long parsed;

    if (value == NULL || value[0] == '\0') {
        return false;
    }
    errno = 0;
    parsed = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0') {
        return false;
    }
    if (parsed < min_value || parsed > max_value) {
        return false;
    }
    *out = (int)parsed;
    return true;
}

static int parse_args(int argc, char **argv, struct config *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    cfg->timeout_sec = 10;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0) {
            usage(stdout);
            exit(0);
        }
        if (i + 1 >= argc) {
            fprintf(stderr, "missing value for %s\n", argv[i]);
            return 2;
        }
        if (strcmp(argv[i], "--system-root") == 0) {
            cfg->system_root = argv[++i];
        } else if (strcmp(argv[i], "--vendor-block") == 0) {
            cfg->vendor_block = argv[++i];
        } else if (strcmp(argv[i], "--vendor-fstype") == 0) {
            cfg->vendor_fstype = argv[++i];
        } else if (strcmp(argv[i], "--target") == 0) {
            cfg->target = argv[++i];
        } else if (strcmp(argv[i], "--linker") == 0) {
            cfg->linker = argv[++i];
        } else if (strcmp(argv[i], "--mode") == 0) {
            cfg->mode = argv[++i];
        } else if (strcmp(argv[i], "--timeout-sec") == 0) {
            if (!parse_int_range(argv[++i], 1, 30, &cfg->timeout_sec)) {
                fprintf(stderr, "invalid --timeout-sec\n");
                return 2;
            }
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]);
            return 2;
        }
    }

    if (!streq(cfg->system_root, "/mnt/system/system") ||
        !streq(cfg->vendor_block, "/dev/block/sda29") ||
        !streq(cfg->vendor_fstype, "ext4") ||
        !streq(cfg->target, "/vendor/bin/cnss-daemon") ||
        !streq(cfg->linker, "/system/bin/linker64") ||
        !streq(cfg->mode, "linker-list")) {
        fprintf(stderr, "arguments do not match v231 allowlist\n");
        return 2;
    }
    return 0;
}

static int append_path(char *out, size_t out_size, const char *a, const char *b) {
    int rc = snprintf(out, out_size, "%s/%s", a, b);

    if (rc < 0 || (size_t)rc >= out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int mkdir_one(const char *path, mode_t mode) {
    if (mkdir(path, mode) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int mkdir_p(const char *path, mode_t mode) {
    char tmp[MAX_PATH_LEN];
    size_t len;

    len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    memcpy(tmp, path, len + 1);
    for (char *p = tmp + 1; *p != '\0'; p++) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir_one(tmp, mode) < 0) {
                return -1;
            }
            *p = '/';
        }
    }
    return mkdir_one(tmp, mode);
}

static int init_paths(struct paths *paths) {
    int rc;

    rc = snprintf(paths->base, sizeof(paths->base), "/tmp/a90-v231-%ld", (long)getpid());
    if (rc < 0 || (size_t)rc >= sizeof(paths->base)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (append_path(paths->root, sizeof(paths->root), paths->base, "root") < 0 ||
        append_path(paths->system, sizeof(paths->system), paths->root, "system") < 0 ||
        append_path(paths->vendor, sizeof(paths->vendor), paths->root, "vendor") < 0 ||
        append_path(paths->vendor_source, sizeof(paths->vendor_source), paths->base, "vendor-block-sda29") < 0 ||
        append_path(paths->proc, sizeof(paths->proc), paths->root, "proc") < 0 ||
        append_path(paths->apex, sizeof(paths->apex), paths->root, "apex") < 0 ||
        append_path(paths->linkerconfig, sizeof(paths->linkerconfig), paths->root, "linkerconfig") < 0) {
        return -1;
    }
    if (mkdir_p(paths->base, 0700) < 0 ||
        mkdir_p(paths->root, 0755) < 0 ||
        mkdir_p(paths->system, 0755) < 0 ||
        mkdir_p(paths->vendor, 0755) < 0 ||
        mkdir_p(paths->proc, 0755) < 0 ||
        mkdir_p(paths->apex, 0755) < 0 ||
        mkdir_p(paths->linkerconfig, 0755) < 0) {
        return -1;
    }
    return 0;
}

static int bind_ro(const char *source, const char *target) {
    if (mount(source, target, NULL, MS_BIND | MS_REC, NULL) < 0) {
        return -1;
    }
    if (mount(NULL, target, NULL, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL) < 0) {
        return -1;
    }
    return 0;
}

static void cleanup_paths(const struct paths *paths) {
    if (paths->apex[0] != '\0') {
        umount2(paths->apex, MNT_DETACH);
    }
    if (paths->linkerconfig[0] != '\0') {
        umount2(paths->linkerconfig, MNT_DETACH);
    }
    umount2(paths->proc, MNT_DETACH);
    umount2(paths->vendor, MNT_DETACH);
    umount2(paths->system, MNT_DETACH);
    if (paths->apex[0] != '\0') {
        rmdir(paths->apex);
    }
    if (paths->linkerconfig[0] != '\0') {
        rmdir(paths->linkerconfig);
    }
    rmdir(paths->proc);
    rmdir(paths->vendor);
    rmdir(paths->system);
    rmdir(paths->root);
    unlink(paths->vendor_source);
    rmdir(paths->base);
}

static int buffer_init(struct buffer *buf) {
    buf->data = calloc(1, 1);
    if (buf->data == NULL) {
        return -1;
    }
    buf->len = 0;
    buf->cap = 1;
    buf->truncated = false;
    return 0;
}

static void buffer_free(struct buffer *buf) {
    free(buf->data);
    buf->data = NULL;
    buf->len = 0;
    buf->cap = 0;
}

static int buffer_append(struct buffer *buf, const char *data, size_t len) {
    size_t allowed = len;

    if (buf->len >= MAX_CAPTURE_SIZE) {
        buf->truncated = true;
        return 0;
    }
    if (buf->len + allowed > MAX_CAPTURE_SIZE) {
        allowed = MAX_CAPTURE_SIZE - buf->len;
        buf->truncated = true;
    }
    if (buf->len + allowed + 1 > buf->cap) {
        size_t new_cap = buf->cap;
        char *new_data;

        while (new_cap < buf->len + allowed + 1) {
            new_cap *= 2;
        }
        new_data = realloc(buf->data, new_cap);
        if (new_data == NULL) {
            return -1;
        }
        buf->data = new_data;
        buf->cap = new_cap;
    }
    memcpy(buf->data + buf->len, data, allowed);
    buf->len += allowed;
    buf->data[buf->len] = '\0';
    return 0;
}

static int set_nonblock(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);

    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int drain_fd(int fd, struct buffer *buf, bool *open_flag) {
    char tmp[4096];

    for (;;) {
        ssize_t nread = read(fd, tmp, sizeof(tmp));

        if (nread > 0) {
            if (buffer_append(buf, tmp, (size_t)nread) < 0) {
                return -1;
            }
            continue;
        }
        if (nread == 0) {
            close(fd);
            *open_flag = false;
            return 0;
        }
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return 0;
        }
        close(fd);
        *open_flag = false;
        return -1;
    }
}

static long monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static int run_linker_list(const struct config *cfg,
                           const struct paths *paths,
                           struct buffer *stdout_buf,
                           struct buffer *stderr_buf,
                           int *child_exit_code,
                           int *child_signal,
                           bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    long deadline;
    pid_t pid;
    int status = 0;
    bool child_done = false;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        perror("pipe2");
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        perror("fork");
        goto fail;
    }
    if (pid == 0) {
        char *const child_argv[] = {
            (char *)cfg->linker,
            (char *)"--list",
            (char *)cfg->target,
            NULL,
        };

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        execv(cfg->linker, child_argv);
        perror("execv linker");
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 100;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            kill(-pid, SIGKILL);
            kill(pid, SIGKILL);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(100000);
        }

        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            }
        }
    }
    return 0;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int setup_namespace(const struct config *cfg, struct paths *paths, char *error_buf, size_t error_size) {
    char system_apex[MAX_PATH_LEN];
    const char *vendor_mount_source = cfg->vendor_block;
    const char *linkerconfig_source = "/mnt/system/linkerconfig";

    if (unshare(CLONE_NEWNS) < 0) {
        snprintf(error_buf, error_size, "unshare: %s", strerror(errno));
        return -1;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        snprintf(error_buf, error_size, "make-rprivate: %s", strerror(errno));
        return -1;
    }
    if (init_paths(paths) < 0) {
        snprintf(error_buf, error_size, "init paths: %s", strerror(errno));
        return -1;
    }
    if (bind_ro(cfg->system_root, paths->system) < 0) {
        snprintf(error_buf, error_size, "bind system: %s", strerror(errno));
        return -1;
    }
    if (access(cfg->vendor_block, F_OK) < 0) {
        FILE *dev_file;
        unsigned int major_no;
        unsigned int minor_no;

        if (errno != ENOENT) {
            snprintf(error_buf, error_size, "stat vendor block: %s", strerror(errno));
            return -1;
        }
        dev_file = fopen("/sys/class/block/sda29/dev", "re");
        if (dev_file == NULL) {
            snprintf(error_buf, error_size, "open sda29 dev: %s", strerror(errno));
            return -1;
        }
        if (fscanf(dev_file, "%u:%u", &major_no, &minor_no) != 2) {
            fclose(dev_file);
            snprintf(error_buf, error_size, "parse sda29 dev: invalid");
            return -1;
        }
        fclose(dev_file);
        if (mknod(paths->vendor_source, S_IFBLK | 0600, makedev(major_no, minor_no)) < 0) {
            snprintf(error_buf, error_size, "mknod vendor block: %s", strerror(errno));
            return -1;
        }
        vendor_mount_source = paths->vendor_source;
    }
    if (mount(vendor_mount_source,
              paths->vendor,
              cfg->vendor_fstype,
              MS_RDONLY | MS_NOSUID | MS_NODEV,
              "noload") < 0) {
        snprintf(error_buf, error_size, "mount vendor: %s", strerror(errno));
        return -1;
    }
    if (mount("proc", paths->proc, "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) < 0) {
        snprintf(error_buf, error_size, "mount proc: %s", strerror(errno));
        return -1;
    }
    if (append_path(system_apex, sizeof(system_apex), cfg->system_root, "apex") < 0) {
        snprintf(error_buf, error_size, "system apex path: %s", strerror(errno));
        return -1;
    }
    if (access(system_apex, R_OK | X_OK) == 0) {
        if (bind_ro(system_apex, paths->apex) < 0) {
            snprintf(error_buf, error_size, "bind apex: %s", strerror(errno));
            return -1;
        }
    } else {
        rmdir(paths->apex);
        paths->apex[0] = '\0';
    }
    if (access(linkerconfig_source, R_OK | X_OK) == 0) {
        if (bind_ro(linkerconfig_source, paths->linkerconfig) < 0) {
            snprintf(error_buf, error_size, "bind linkerconfig: %s", strerror(errno));
            return -1;
        }
    } else {
        rmdir(paths->linkerconfig);
        paths->linkerconfig[0] = '\0';
    }
    return 0;
}

static void print_section(const char *name, const struct buffer *buf) {
    printf("A90_EXECNS_%s_BEGIN\n", name);
    if (buf->data != NULL && buf->len > 0) {
        fwrite(buf->data, 1, buf->len, stdout);
        if (buf->data[buf->len - 1] != '\n') {
            putchar('\n');
        }
    }
    printf("A90_EXECNS_%s_END truncated=%d bytes=%zu\n", name, buf->truncated ? 1 : 0, buf->len);
}

int main(int argc, char **argv) {
    struct config cfg;
    struct paths paths;
    struct buffer stdout_buf;
    struct buffer stderr_buf;
    char setup_error[256] = "";
    int child_exit_code = -1;
    int child_signal = 0;
    bool timed_out = false;
    int parse_rc;
    int run_rc;

    memset(&paths, 0, sizeof(paths));
    parse_rc = parse_args(argc, argv, &cfg);
    if (parse_rc != 0) {
        usage(stderr);
        return parse_rc;
    }
    if (buffer_init(&stdout_buf) < 0 || buffer_init(&stderr_buf) < 0) {
        perror("buffer init");
        return 20;
    }

    printf("A90_EXECNS_BEGIN version=\"%s\"\n", EXECNS_VERSION);
    printf("mode=%s\n", cfg.mode);
    printf("system_root=%s\n", cfg.system_root);
    printf("vendor_block=%s\n", cfg.vendor_block);
    printf("vendor_fstype=%s\n", cfg.vendor_fstype);
    printf("target=%s\n", cfg.target);
    printf("linker=%s\n", cfg.linker);
    printf("timeout_sec=%d\n", cfg.timeout_sec);

    if (setup_namespace(&cfg, &paths, setup_error, sizeof(setup_error)) < 0) {
        printf("helper_status=setup-error\n");
        printf("setup_error=%s\n", setup_error);
        cleanup_paths(&paths);
        printf("cleanup_status=attempted\n");
        printf("A90_EXECNS_END rc=20\n");
        buffer_free(&stdout_buf);
        buffer_free(&stderr_buf);
        return 20;
    }

    printf("helper_status=namespace-ready\n");
    printf("temp_base=%s\n", paths.base);
    printf("temp_root=%s\n", paths.root);
    printf("vendor_mount_source=%s\n",
           access(paths.vendor_source, F_OK) == 0 ? paths.vendor_source : cfg.vendor_block);
    printf("linkerconfig_mount_source=%s\n",
           paths.linkerconfig[0] != '\0' ? "/mnt/system/linkerconfig" : "<absent>");
    run_rc = run_linker_list(&cfg, &paths, &stdout_buf, &stderr_buf, &child_exit_code, &child_signal, &timed_out);
    printf("probe_run_rc=%d\n", run_rc);
    printf("child_exit_code=%d\n", child_exit_code);
    printf("child_signal=%d\n", child_signal);
    printf("timed_out=%d\n", timed_out ? 1 : 0);
    print_section("STDOUT", &stdout_buf);
    print_section("STDERR", &stderr_buf);
    cleanup_paths(&paths);
    printf("cleanup_status=attempted\n");
    printf("A90_EXECNS_END rc=0\n");

    buffer_free(&stdout_buf);
    buffer_free(&stderr_buf);
    return 0;
}
