/* Prospective headless FYG8 UFS preparation. Compile-only in this H0 unit.
 * A future target PID 1 must first validate its exact target/boot authority.
 * No display, USB gadget, partition write, formatter or recovery operation.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <unistd.h>
#include "../../native-init/s22plus_fyg8_max77705_result_parser.inc.c"
#include "storage-plan.h"

_Static_assert(O_DIRECTORY == 16384 && O_NOFOLLOW == 32768 && O_CLOEXEC == 524288,
               "ARM64 UAPI required");

int s22plus_debian_prepare_storage(void) {
    struct utsname u;
    if (getpid() != 1 || geteuid() || uname(&u) || strcmp(u.machine, "aarch64") ||
        strcmp(u.release, "5.10.226-android12-9-30958166-abS906NKSS7FYG8"))
        return EPERM;
    int root = open("/s22-storage", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (root < 0) return errno;
    for (unsigned i = 0; i < sizeof(storage_plan) / sizeof(storage_plan[0]); ++i) {
        const struct storage_module *m = storage_plan + i;
        int fd = openat(root, m->name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
        if (fd < 0) { int error = errno; close(root); return error; }
        struct stat st;
        int error = 0;
        if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid ||
            st.st_nlink != 1 || (st.st_mode & 07777) != 0644 ||
            st.st_size < 0 || (uint64_t)st.st_size != m->size) error = EPROTO;
        struct s22plus_max77705_runtime_sha256 hash;
        s22plus_max77705_runtime_sha256_init(&hash);
        unsigned char buffer[8192], actual[32];
        uint64_t count = 0;
        while (!error && count < m->size) {
            size_t amount = m->size - count < sizeof(buffer) ? m->size - count : sizeof(buffer);
            ssize_t n = read(fd, buffer, amount);
            if (n <= 0) { error = EIO; break; }
            s22plus_max77705_runtime_sha256_update(&hash, buffer, (size_t)n);
            count += (uint64_t)n;
        }
        if (!error && read(fd, buffer, 1) != 0) error = EPROTO;
        s22plus_max77705_runtime_sha256_final(&hash, actual);
        if (!error && memcmp(actual, m->sha256, 32)) error = EPROTO;
        if (!error && lseek(fd, 0, SEEK_SET)) error = EIO;
        /* Exactly once; EEXIST and every other insertion failure stop the plan. */
        if (!error && syscall(SYS_finit_module, fd, "", 0)) error = errno;
        if (close(fd) && !error) error = errno;
        if (error) { close(root); return error; }
        printf("STORAGE_MODULE_DONE ordinal=%u\n", i + 1U);
        fflush(stdout);
    }
    return close(root) ? errno : 0;
}
