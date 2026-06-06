#include <fcntl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include <string.h>

static void wf(const char *path, const char *s) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return;
    write(fd, s, strlen(s));
    close(fd);
}

int main(void) {
    mkdir("/proc",  0755);
    mkdir("/sys",   0755);
    mkdir("/dev",   0755);
    mkdir("/cache", 0755);

    mount("proc",     "/proc", "proc",    0, NULL);
    mount("sysfs",    "/sys",  "sysfs",   0, NULL);
    mount("devtmpfs", "/dev",  "devtmpfs",0, "mode=0755");

    wf("/dev/kmsg", "<6>A90_LINUX_INIT: step1 mounts done\n");

    /* devtmpfs async 초기화 우회 — sda31(259:15) 직접 생성 */
    mkdir("/dev/block", 0755);
    mknod("/dev/block/sda31", S_IFBLK | 0600, makedev(259, 15));

    wf("/dev/kmsg", "<6>A90_LINUX_INIT: step2 mknod done\n");

    if (mount("/dev/block/sda31", "/cache", "ext4", 0, "") == 0) {
        wf("/dev/kmsg",             "<6>A90_LINUX_INIT: step3 cache mounted OK\n");
        wf("/cache/linux_init_ran", "ok\n");
        sync();
        wf("/dev/kmsg",             "<6>A90_LINUX_INIT: step4 marker written\n");
    } else {
        wf("/dev/kmsg", "<6>A90_LINUX_INIT: step3 cache mount FAILED\n");
    }

    /* 재부팅하지 않고 대기 — TWRP 강제 진입으로 확인 */
    while (1) { sleep(60); }
}
