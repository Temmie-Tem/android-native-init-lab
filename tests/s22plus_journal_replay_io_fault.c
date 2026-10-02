/* H0 link-time syscall faults. Never linked into a device tool. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern ssize_t __real_pwrite(int, const void *, size_t, off_t);
extern ssize_t __real_pread(int, void *, size_t, off_t);
extern int __real_fsync(int);
extern int __real_close(int);
static unsigned writes, flushes, after_error;
static int failed, selected_fd = -1;

static int selected(const char *kind, unsigned count)
{
    char wanted[64];
    snprintf(wanted, sizeof(wanted), "%s:%u", kind, count);
    const char *s = getenv("S22_H0_IO_FAULT");
    return s && !strcmp(s, wanted);
}

ssize_t __wrap_pwrite(int fd, const void *data, size_t size, off_t offset)
{
    selected_fd = fd;
    ++writes;
    if (failed) ++after_error;
    if (selected("write", writes)) { failed = 1; errno = EIO; return -1; }
    if (selected("short", writes)) {
        failed = 1;
        return __real_pwrite(fd, data, size / 2, offset);
    }
    return __real_pwrite(fd, data, size, offset);
}

ssize_t __wrap_pread(int fd, void *data, size_t size, off_t offset)
{
    ssize_t rc = __real_pread(fd, data, size, offset);
    if (!failed && rc > 0 && selected("readback", writes) && writes >= 2) {
        ((unsigned char *)data)[0] ^= 1;
        failed = 1;
    }
    return rc;
}

int __wrap_fsync(int fd)
{
    selected_fd = fd;
    ++flushes;
    if (failed) ++after_error;
    if (selected("flush", flushes)) { failed = 1; errno = EIO; return -1; }
    return __real_fsync(fd);
}

int __wrap_close(int fd)
{
    int rc = __real_close(fd);
    if (fd == selected_fd && selected("close", 1)) { failed = 1; errno = EIO; return -1; }
    return rc;
}

__attribute__((destructor)) static void evidence(void)
{
    fprintf(stderr, "H0_IO_FAULT writes=%u flushes=%u fired=%d after_error=%u\n",
            writes, flushes, failed, after_error);
}
