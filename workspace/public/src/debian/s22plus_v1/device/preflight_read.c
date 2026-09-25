/* Read only the sealed bootstrap record retained by the initial PID 1. */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "preflight_record.h"
#include "preflight-plan.h"

int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], bp_run_hex)) return 2;
    int fd = open("/proc/1/fd/198", O_RDONLY | O_CLOEXEC);
    struct stat st;
    struct bp_record record;
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid ||
        st.st_nlink || (st.st_mode & 07777) != 0400 ||
        fcntl(fd, F_GET_SEALS) != BP_SEALS ||
        pread(fd, &record, sizeof(record), 0) != sizeof(record) ||
        !bp_valid(&record, bp_run_id, 0) || st.st_size != (off_t)(sizeof(record) + record.log_size)) return 3;
    char boot[38];
    int source = open("/proc/sys/kernel/random/boot_id", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (source < 0 || read(source, boot, sizeof(boot)) != 37 || close(source) ||
        memcmp(boot, record.boot_id, 37)) return 4;
    unsigned char bytes[4096];
    off_t position = 0;
    while (position < st.st_size) {
        size_t amount = st.st_size - position < (off_t)sizeof(bytes) ?
            (size_t)(st.st_size - position) : sizeof(bytes);
        if (pread(fd, bytes, amount, position) != (ssize_t)amount) return 5;
        size_t sent = 0;
        while (sent < amount) {
            ssize_t n = write(1, bytes + sent, amount - sent);
            if (n <= 0) return 6;
            sent += (size_t)n;
        }
        position += (off_t)amount;
    }
    return close(fd) ? 7 : 0;
}
