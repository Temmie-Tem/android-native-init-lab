/* H0 virt-only child verifier. Reuse the existing manifest consumers;
 * the old C PID1 main and its unused functions are removed by --gc-sections. */
#define main unused_old_pid1
#include "../s22plus_v1/handoff.c"
#undef main
#include <linux/fs.h>
#include <sys/ioctl.h>
#include <sys/vfs.h>

int main(int argc, char **argv) {
    if (getpid() == 1 || geteuid() || argc != 2) return 2;
    if (!strcmp(argv[1], "identity")) {
        char compatible[17];
        read_exact("/sys/firmware/devicetree/base/compatible", compatible, sizeof(compatible));
        if (memcmp(compatible, "linux,dummy-virt", 16)) stop("not-h0-virt");
        int fd = open("/dev/vda", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
        struct stat st;
        int ro = 0;
        unsigned char sb[1024];
        if (fd < 0 || fstat(fd, &st) || !S_ISBLK(st.st_mode) ||
            ioctl(fd, BLKROGET, &ro) || ro != 1 ||
            pread(fd, sb, sizeof(sb), 1024) != sizeof(sb) || close(fd))
            stop("root-protection");
        if (memcmp(sb + 0x68, root_uuid, 16)) stop("root-uuid");
        if (little(sb + 0x38, 2) != 0xef53 || little(sb + 0x3a, 2) != 1 ||
            (little(sb + 0x60, 4) & 4) || little(sb + 0xe8, 4))
            stop("root-unclean");
    } else if (!strcmp(argv[1], "tree")) {
        struct statvfs state;
        struct statfs fs;
        if (statvfs("/newroot", &state) || !(state.f_flag & ST_RDONLY) ||
            statfs("/newroot", &fs) || fs.f_type != 0xef53) stop("root-mount");
        verify_metadata();
        verify_contents();
    } else return 2;
    return 0;
}
