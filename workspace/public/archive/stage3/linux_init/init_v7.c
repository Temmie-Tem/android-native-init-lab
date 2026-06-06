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
#include <linux/reboot.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <sys/utsname.h>
#include <termios.h>
#include <unistd.h>

static int console_fd = -1;
static pid_t adbd_pid = -1;

static int ensure_dir(const char *path, mode_t mode) {
    if (mkdir(path, mode) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
}

static void write_all(int fd, const char *buf, size_t len) {
    while (len > 0) {
        ssize_t written = write(fd, buf, len);
        if (written <= 0) {
            if (errno == EINTR) {
                continue;
            }
            return;
        }
        buf += written;
        len -= (size_t)written;
    }
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
    mknod("/dev/block/sda31", S_IFBLK | 0600, makedev(259, 15));
    if (mount("/dev/block/sda31", "/cache", "ext4", 0, NULL) == 0) {
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
    if (mknod(path, S_IFBLK | 0600, makedev(major_num, minor_num)) == 0 ||
        errno == EEXIST) {
        return 0;
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

static ssize_t read_line(char *buf, size_t buf_size) {
    static char pending_newline = '\0';
    size_t pos = 0;

    while (pos + 1 < buf_size) {
        char ch;
        ssize_t rd = read(STDIN_FILENO, &ch, 1);

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (rd == 0) {
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

static void cmd_pwd(void) {
    char cwd[PATH_MAX];

    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        cprintf("/\r\n");
        return;
    }

    cprintf("%s\r\n", cwd);
}

static void cmd_help(void) {
    cprintf("help\r\n");
    cprintf("uname\r\n");
    cprintf("pwd\r\n");
    cprintf("cd <dir>\r\n");
    cprintf("ls [dir]\r\n");
    cprintf("cat <file>\r\n");
    cprintf("stat <path>\r\n");
    cprintf("mounts\r\n");
    cprintf("mountsystem [ro|rw]\r\n");
    cprintf("prepareandroid\r\n");
    cprintf("mkdir <dir>\r\n");
    cprintf("mknodb <path> <major> <minor>\r\n");
    cprintf("mountfs <src> <dst> <type> [ro]\r\n");
    cprintf("umount <path>\r\n");
    cprintf("echo <text>\r\n");
    cprintf("run <path> [args...]\r\n");
    cprintf("runandroid <path> [args...]\r\n");
    cprintf("startadbd\r\n");
    cprintf("stopadbd\r\n");
    cprintf("sync\r\n");
    cprintf("reboot\r\n");
    cprintf("recovery\r\n");
    cprintf("poweroff\r\n");
}

static void cmd_uname(void) {
    struct utsname uts;

    if (uname(&uts) < 0) {
        cprintf("uname: %s\r\n", strerror(errno));
        return;
    }

    cprintf("%s %s %s %s %s\r\n",
            uts.sysname, uts.nodename, uts.release, uts.version, uts.machine);
}

static void cmd_ls(const char *path) {
    DIR *dir;
    struct dirent *entry;

    dir = opendir(path);
    if (dir == NULL) {
        cprintf("ls: %s: %s\r\n", path, strerror(errno));
        return;
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
        }
    }

    closedir(dir);
}

static void cmd_cat(const char *path) {
    char buf[512];
    int fd = open(path, O_RDONLY);

    if (fd < 0) {
        cprintf("cat: %s: %s\r\n", path, strerror(errno));
        return;
    }

    while (1) {
        ssize_t rd = read(fd, buf, sizeof(buf));
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            cprintf("cat: %s: %s\r\n", path, strerror(errno));
            break;
        }
        if (rd == 0) {
            break;
        }
        write_all(console_fd, buf, (size_t)rd);
    }

    close(fd);
    cprintf("\r\n");
}

static void cmd_stat(const char *path) {
    struct stat st;

    if (lstat(path, &st) < 0) {
        cprintf("stat: %s: %s\r\n", path, strerror(errno));
        return;
    }

    cprintf("mode=0%o uid=%ld gid=%ld size=%ld\r\n",
            st.st_mode & 07777, (long)st.st_uid, (long)st.st_gid, (long)st.st_size);
    if (S_ISBLK(st.st_mode) || S_ISCHR(st.st_mode)) {
        cprintf("rdev=%u:%u\r\n", major(st.st_rdev), minor(st.st_rdev));
    }
}

static void cmd_mounts(void) {
    cmd_cat("/proc/mounts");
}

static void cmd_mountsystem(bool read_only) {
    unsigned long flags = read_only ? MS_RDONLY : 0;

    ensure_dir("/mnt", 0755);
    ensure_dir("/mnt/system", 0755);

    if (ensure_block_node("/dev/block/sda28", 259, 12) < 0) {
        cprintf("mountsystem: mknod failed: %s\r\n", strerror(errno));
        return;
    }

    if (mount("/dev/block/sda28", "/mnt/system", "ext4", flags, NULL) < 0) {
        if (errno == EBUSY) {
            cprintf("mountsystem: already mounted\r\n");
        } else {
            cprintf("mountsystem: %s\r\n", strerror(errno));
        }
        return;
    }

    cprintf("mountsystem: /mnt/system ready (%s)\r\n", read_only ? "ro" : "rw");
}

static int prepare_android_layout(bool verbose) {
    ensure_dir("/mnt", 0755);
    ensure_dir("/mnt/system", 0755);

    if (!path_exists("/mnt/system/system")) {
        if (ensure_block_node("/dev/block/sda28", 259, 12) < 0) {
            if (verbose) {
                cprintf("prepareandroid: sda28 mknod failed: %s\r\n", strerror(errno));
            }
            return -1;
        }
        if (mount("/dev/block/sda28", "/mnt/system", "ext4", MS_RDONLY, NULL) < 0 &&
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

static void cmd_prepareandroid(void) {
    if (prepare_android_layout(true) == 0) {
        cprintf("prepareandroid: ready\r\n");
    }
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

static void cmd_run(char **argv, int argc) {
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
        return;
    }

    pid = fork();
    if (pid < 0) {
        cprintf("run: fork: %s\r\n", strerror(errno));
        return;
    }

    if (pid == 0) {
        dup2(console_fd, STDIN_FILENO);
        dup2(console_fd, STDOUT_FILENO);
        dup2(console_fd, STDERR_FILENO);
        execve(argv[1], &argv[1], envp);
        cprintf("run: execve(%s): %s\r\n", argv[1], strerror(errno));
        _exit(127);
    }

    if (waitpid(pid, &status, 0) < 0) {
        cprintf("run: waitpid: %s\r\n", strerror(errno));
        return;
    }

    if (WIFEXITED(status)) {
        cprintf("[exit %d]\r\n", WEXITSTATUS(status));
    } else if (WIFSIGNALED(status)) {
        cprintf("[signal %d]\r\n", WTERMSIG(status));
    }
}

static void cmd_runandroid(char **argv, int argc) {
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
        return;
    }

    if (prepare_android_layout(true) < 0) {
        return;
    }

    pid = fork();
    if (pid < 0) {
        cprintf("runandroid: fork: %s\r\n", strerror(errno));
        return;
    }

    if (pid == 0) {
        dup2(console_fd, STDIN_FILENO);
        dup2(console_fd, STDOUT_FILENO);
        dup2(console_fd, STDERR_FILENO);
        execve(argv[1], &argv[1], envp);
        cprintf("runandroid: execve(%s): %s\r\n", argv[1], strerror(errno));
        _exit(127);
    }

    if (waitpid(pid, &status, 0) < 0) {
        cprintf("runandroid: waitpid: %s\r\n", strerror(errno));
        return;
    }

    if (WIFEXITED(status)) {
        cprintf("[exit %d]\r\n", WEXITSTATUS(status));
    } else if (WIFSIGNALED(status)) {
        cprintf("[signal %d]\r\n", WTERMSIG(status));
    }
}

static int ensure_adb_function(bool *needs_rebind) {
    int ret;

    ensure_dir("/config/usb_gadget/g1/functions/ffs.adb", 0770);
    ensure_dir("/dev/usb-ffs", 0755);
    ensure_dir("/dev/usb-ffs/adb", 0755);

    if (mount("adb", "/dev/usb-ffs/adb", "functionfs", 0, NULL) < 0 && errno != EBUSY) {
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

static void cmd_startadbd(void) {
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
        return;
    }

    if (prepare_android_layout(true) < 0) {
        return;
    }

    if (ensure_adb_function(&needs_rebind) < 0) {
        cprintf("startadbd: functionfs setup failed: %s\r\n", strerror(errno));
        return;
    }

    adbd_pid = fork();
    if (adbd_pid < 0) {
        cprintf("startadbd: fork failed: %s\r\n", strerror(errno));
        adbd_pid = -1;
        return;
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
    }

    cprintf("startadbd: pid=%ld\r\n", (long)adbd_pid);
}

static void cmd_stopadbd(void) {
    if (adbd_pid <= 0) {
        cprintf("stopadbd: not running\r\n");
        return;
    }

    kill(adbd_pid, SIGTERM);
    waitpid(adbd_pid, NULL, 0);
    adbd_pid = -1;
    unlink("/config/usb_gadget/g1/configs/b.1/f2");
    umount("/dev/usb-ffs/adb");
    wf("/config/usb_gadget/g1/UDC", "");
    usleep(200000);
    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    cprintf("stopadbd: done\r\n");
}

static void cmd_recovery(void) {
    sync();
    syscall(SYS_reboot,
            LINUX_REBOOT_MAGIC1,
            LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART2,
            "recovery");
    cprintf("recovery: %s\r\n", strerror(errno));
}

static void shell_loop(void) {
    char line[512];

    cmd_help();

    while (1) {
        char *argv[32];
        int argc;

        print_prompt();
        if (read_line(line, sizeof(line)) < 0) {
            cprintf("read: %s\r\n", strerror(errno));
            sleep(1);
            continue;
        }

        argc = split_args(line, argv, 32);
        if (argc == 0) {
            continue;
        }

        if (strcmp(argv[0], "help") == 0) {
            cmd_help();
        } else if (strcmp(argv[0], "uname") == 0) {
            cmd_uname();
        } else if (strcmp(argv[0], "pwd") == 0) {
            cmd_pwd();
        } else if (strcmp(argv[0], "cd") == 0) {
            const char *path = argc > 1 ? argv[1] : "/";
            if (chdir(path) < 0) {
                cprintf("cd: %s: %s\r\n", path, strerror(errno));
            }
        } else if (strcmp(argv[0], "ls") == 0) {
            cmd_ls(argc > 1 ? argv[1] : ".");
        } else if (strcmp(argv[0], "cat") == 0) {
            if (argc < 2) {
                cprintf("usage: cat <file>\r\n");
            } else {
                cmd_cat(argv[1]);
            }
        } else if (strcmp(argv[0], "stat") == 0) {
            if (argc < 2) {
                cprintf("usage: stat <path>\r\n");
            } else {
                cmd_stat(argv[1]);
            }
        } else if (strcmp(argv[0], "mounts") == 0) {
            cmd_mounts();
        } else if (strcmp(argv[0], "mountsystem") == 0) {
            bool read_only = true;

            if (argc > 1 && strcmp(argv[1], "rw") == 0) {
                read_only = false;
            }
            cmd_mountsystem(read_only);
        } else if (strcmp(argv[0], "prepareandroid") == 0) {
            cmd_prepareandroid();
        } else if (strcmp(argv[0], "mkdir") == 0) {
            if (argc < 2) {
                cprintf("usage: mkdir <dir>\r\n");
            } else if (mkdir(argv[1], 0755) < 0 && errno != EEXIST) {
                cprintf("mkdir: %s: %s\r\n", argv[1], strerror(errno));
            }
        } else if (strcmp(argv[0], "mknodb") == 0) {
            unsigned int major_num;
            unsigned int minor_num;

            if (argc < 4) {
                cprintf("usage: mknodb <path> <major> <minor>\r\n");
            } else if (sscanf(argv[2], "%u", &major_num) != 1 ||
                       sscanf(argv[3], "%u", &minor_num) != 1) {
                cprintf("mknodb: invalid major/minor\r\n");
            } else if (mknod(argv[1], S_IFBLK | 0600,
                             makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
                cprintf("mknodb: %s: %s\r\n", argv[1], strerror(errno));
            }
        } else if (strcmp(argv[0], "mountfs") == 0) {
            unsigned long flags = 0;

            if (argc < 4) {
                cprintf("usage: mountfs <src> <dst> <type> [ro]\r\n");
            } else {
                if (argc > 4 && strcmp(argv[4], "ro") == 0) {
                    flags |= MS_RDONLY;
                }
                if (mount(argv[1], argv[2], argv[3], flags, NULL) < 0) {
                    cprintf("mountfs: %s\r\n", strerror(errno));
                }
            }
        } else if (strcmp(argv[0], "umount") == 0) {
            if (argc < 2) {
                cprintf("usage: umount <path>\r\n");
            } else if (umount(argv[1]) < 0) {
                cprintf("umount: %s: %s\r\n", argv[1], strerror(errno));
            }
        } else if (strcmp(argv[0], "echo") == 0) {
            cmd_echo(argv, argc);
        } else if (strcmp(argv[0], "run") == 0) {
            cmd_run(argv, argc);
        } else if (strcmp(argv[0], "runandroid") == 0) {
            cmd_runandroid(argv, argc);
        } else if (strcmp(argv[0], "startadbd") == 0) {
            cmd_startadbd();
        } else if (strcmp(argv[0], "stopadbd") == 0) {
            cmd_stopadbd();
        } else if (strcmp(argv[0], "sync") == 0) {
            sync();
            cprintf("synced\r\n");
        } else if (strcmp(argv[0], "reboot") == 0) {
            sync();
            reboot(RB_AUTOBOOT);
            wf("/proc/sysrq-trigger", "b");
        } else if (strcmp(argv[0], "recovery") == 0) {
            cmd_recovery();
        } else if (strcmp(argv[0], "poweroff") == 0) {
            sync();
            reboot(RB_POWER_OFF);
        } else {
            cprintf("unknown command: %s\r\n", argv[0]);
        }
    }
}

int main(void) {
    setup_base_mounts();
    klogf("<6>A90v7: base mounts ready\n");

    if (mount_cache() == 0) {
        mark_step("1_cache_ok_v7\n");
        klogf("<6>A90v7: cache mounted\n");
    } else {
        klogf("<6>A90v7: cache mount failed (%d)\n", errno);
    }

    if (setup_acm_gadget() == 0) {
        mark_step("2_gadget_ok_v7\n");
        klogf("<6>A90v7: ACM gadget configured\n");
    } else {
        klogf("<6>A90v7: ACM gadget failed (%d)\n", errno);
        while (1) {
            sleep(60);
        }
    }

    if (wait_for_tty_gs0() == 0) {
        mark_step("3_tty_ready_v7\n");
        klogf("<6>A90v7: ttyGS0 ready\n");
    } else {
        klogf("<6>A90v7: ttyGS0 missing (%d)\n", errno);
        while (1) {
            sleep(60);
        }
    }

    if (attach_console() == 0) {
        mark_step("4_console_attached_v7\n");
        cprintf("\r\nA90 Linux init v7\r\n");
        cprintf("USB ACM serial console ready.\r\n");
        shell_loop();
    }

    while (1) {
        sleep(60);
    }
}
