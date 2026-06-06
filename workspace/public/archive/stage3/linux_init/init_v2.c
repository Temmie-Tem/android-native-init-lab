/*
 * A90 5G Linux init v2c — ADB over USB (exec from /cache)
 *
 * initramfs(tmpfs)가 noexec인 경우 userspace execve가 EACCES 반환.
 * 해결: /cache (ext4, exec 가능)에 파일 배치 후 거기서 exec.
 *
 * /cache/adb/ 에 TWRP에서 미리 배치:
 *   adbd      linker64    lib/*.so
 *
 * ramdisk에는 /system/bin/linker64 → /cache/adb/linker64 심링크만 추가.
 * (ELF INTERP 경로 해결 용)
 *
 * 순서:
 *   1. proc / sys / devtmpfs
 *   2. sda31(cache) mknod + mount → 진단 마커
 *   3. /system/bin/linker64 → /cache/adb/linker64 심링크
 *   4. configfs + USB gadget (g1, ffs.adb)
 *   5. functionfs mount
 *   6. adbd fork/exec from /cache/adb/adbd
 *   7. 3초 대기 → UDC 활성화
 *   8. sleep loop
 */

#include <fcntl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

static void wf(const char *path, const char *s) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return;
    write(fd, s, strlen(s));
    close(fd);
}

static void klog(const char *msg) {
    wf("/dev/kmsg", msg);
}

int main(void) {
    /* ── 1. 기본 마운트 ── */
    mkdir("/proc",   0755);
    mkdir("/sys",    0755);
    mkdir("/dev",    0755);
    mkdir("/cache",  0755);
    mkdir("/config", 0755);
    mkdir("/system", 0755);
    mkdir("/system/bin", 0755);

    mount("proc",     "/proc", "proc",     0, NULL);
    mount("sysfs",    "/sys",  "sysfs",    0, NULL);
    mount("devtmpfs", "/dev",  "devtmpfs", 0, "mode=0755");

    klog("<6>A90v2c: step1 base mounts done\n");

    /* ── 2. /cache 마운트 ── */
    mkdir("/dev/block", 0755);
    mknod("/dev/block/sda31", S_IFBLK | 0600, makedev(259, 15));

    if (mount("/dev/block/sda31", "/cache", "ext4", 0, NULL) == 0) {
        wf("/cache/v2c_step", "2_cache_ok\n");
        klog("<6>A90v2c: step2 cache mounted OK\n");
    } else {
        klog("<6>A90v2c: step2 cache mount FAILED\n");
    }

    /* ── 3. ELF INTERP 경로 해결용 심링크
     *    adbd ELF INTERP = /system/bin/linker64
     *    → /cache/adb/linker64 (ext4, exec 가능)
     */
    symlink("/cache/adb/linker64", "/system/bin/linker64");
    klog("<6>A90v2c: step3 linker64 symlink done\n");

    /* ── 4. configfs ── */
    if (mount("configfs", "/config", "configfs", 0, NULL) == 0) {
        klog("<6>A90v2c: step4 configfs mounted\n");
    } else {
        klog("<6>A90v2c: step4 configfs FAILED\n");
    }

    /* ── 5. USB gadget 설정 ── */
    mkdir("/config/usb_gadget",                              0770);
    mkdir("/config/usb_gadget/g1",                           0770);
    mkdir("/config/usb_gadget/g1/strings",                   0770);
    mkdir("/config/usb_gadget/g1/strings/0x409",             0770);
    wf("/config/usb_gadget/g1/idVendor",                     "0x04e8");
    wf("/config/usb_gadget/g1/idProduct",                    "0x6860");
    wf("/config/usb_gadget/g1/bcdUSB",                       "0x0200");
    wf("/config/usb_gadget/g1/strings/0x409/serialnumber",   "RFCM90CFWXA");
    wf("/config/usb_gadget/g1/strings/0x409/manufacturer",   "samsung");
    wf("/config/usb_gadget/g1/strings/0x409/product",        "SM8150-ADB");

    mkdir("/config/usb_gadget/g1/functions",                 0770);
    mkdir("/config/usb_gadget/g1/functions/ffs.adb",         0770);

    mkdir("/config/usb_gadget/g1/configs",                   0770);
    mkdir("/config/usb_gadget/g1/configs/b.1",               0770);
    mkdir("/config/usb_gadget/g1/configs/b.1/strings",       0770);
    mkdir("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0770);
    wf("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "adb");
    wf("/config/usb_gadget/g1/configs/b.1/MaxPower",         "900");

    klog("<6>A90v2c: step5 gadget configured\n");

    /* ── 6. functionfs 마운트 ── */
    mkdir("/dev/usb-ffs",     0770);
    mkdir("/dev/usb-ffs/adb", 0770);

    if (mount("adb", "/dev/usb-ffs/adb", "functionfs", 0, "uid=2000,gid=2000") == 0) {
        wf("/cache/v2c_step", "6_ffs_ok\n");
        klog("<6>A90v2c: step6 functionfs OK\n");
    } else {
        wf("/cache/v2c_step", "6_ffs_FAIL\n");
        klog("<6>A90v2c: step6 functionfs FAILED\n");
    }

    mkdir("/dev/socket", 0755);

    /* ── 7. adbd 실행 (/cache/adb/ — ext4, exec 가능) ── */
    pid_t pid = fork();
    if (pid == 0) {
        char *argv[] = {
            "/cache/adb/adbd",
            "--root_seclabel=u:r:su:s0",
            NULL
        };
        char *envp[] = {
            "PATH=/cache/adb",
            "LD_LIBRARY_PATH=/cache/adb/lib",
            "HOME=/",
            "ANDROID_DATA=/cache",
            "ANDROID_ROOT=/system",
            NULL
        };
        execve("/cache/adb/adbd", argv, envp);
        /* exec 실패 → errno 기록 */
        {
            char buf[4];
            buf[0] = '0' + (errno / 100) % 10;
            buf[1] = '0' + (errno / 10) % 10;
            buf[2] = '0' + (errno % 10);
            buf[3] = '\n';
            int fd = open("/cache/adbd_exec_failed",
                          O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (fd >= 0) { write(fd, buf, 4); close(fd); }
        }
        _exit(1);
    }

    wf("/cache/v2c_step", "7_adbd_forked\n");
    klog("<6>A90v2c: step7 adbd forked\n");

    /* ── 8. adbd ep0 기록 대기 ── */
    sleep(3);

    /* ── 9. UDC 활성화 ── */
    symlink("/config/usb_gadget/g1/functions/ffs.adb",
            "/config/usb_gadget/g1/configs/b.1/f1");
    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");

    wf("/cache/v2c_step", "9_udc_set\n");
    klog("<6>A90v2c: step9 UDC activated\n");
    sync();

    while (1) { sleep(60); }
}
