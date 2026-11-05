/* Only the QEMU virt fixture, never a platform or phone MMIO accessor. */
#if !defined(CANARY_H0_VM) || !defined(ML030_QEMU_UFS)
#error "the PCI UFS fixture requires the QEMU-only build"
#endif
#include <sys/mman.h>

#define EMU_BDF "/sys/bus/pci/devices/0000:00:02.0/"
static int emu_attr(const char *path, const char *wanted) {
    char value[32]; size_t n = 0;
    int error = read_small(path, value, sizeof(value), &n);
    if (error) return error;
    return n == strlen(wanted) && !memcmp(value, wanted, n) ? 0 : ENODEV;
}

static uint32_t emu_read(volatile uint32_t *bar, unsigned offset) {
    uint32_t result = bar[offset / 4];
    __asm__ volatile("dmb oshld" ::: "memory");
    return result;
}
static void emu_write(volatile uint32_t *bar, unsigned offset, uint32_t value) {
    __asm__ volatile("dmb oshst" ::: "memory");
    bar[offset / 4] = value;
    __asm__ volatile("dsb osh" ::: "memory");
}
static int emu_link_once(void) {
    static int consumed;
    int error;
    if (consumed) return EALREADY;
    consumed = 1;
    if ((error=emu_attr(EMU_BDF "vendor", "0x1b36\n")) ||
        (error=emu_attr(EMU_BDF "device", "0x0013\n")) ||
        (error=emu_attr(EMU_BDF "class", "0x010901\n"))) return error;
    struct stat st;
    if (!lstat(EMU_BDF "driver", &st) || errno != ENOENT) return EBUSY;
    /* The VM-only PCI host leaves this emulated function disabled. No driver is bound. */
    if ((error=put(EMU_BDF "enable", "1"))) return error;
    int fd=open(EMU_BDF "resource0", O_RDWR|O_CLOEXEC);
    if (fd<0) return errno;
    volatile uint32_t *bar=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    error = bar == MAP_FAILED ? errno : 0;
    close(fd);
    if (error) return error;
    if (now_ms() >= deadline) {error=ETIMEDOUT;goto done;}
    if (emu_read(bar,0x34)!=0 || emu_read(bar,0x20)!=0 || emu_read(bar,0x24)!=0 ||
        emu_read(bar,0x58)!=0 || emu_read(bar,0x60)!=0 || emu_read(bar,0x78)!=0 ||
        emu_read(bar,0x80)!=0) {error=EBUSY;goto done;}
    emu_write(bar,0x34,1);  /* HCE on a fresh emulated controller only. */
    uint32_t before=emu_read(bar,0x30);
    if (emu_read(bar,0x34)!=1 || (before&9)!=8 || emu_read(bar,0x20)!=0) {error=EPROTO;goto done;}
    emu_write(bar,0x94,0);emu_write(bar,0x98,0);emu_write(bar,0x9c,0);
    dprintf(2,"ML030_VM_UIC_INTENT opcode=0x16\n");
    if (now_ms() >= deadline) {error=ETIMEDOUT;goto done;}
    emu_write(bar,0x90,0x16);  /* exactly one DME_LINK_STARTUP */
    uint64_t until=now_ms()+1000;
    if (until>deadline) until=deadline;
    for (;;) {
        if (now_ms()>=until) {error=ETIMEDOUT;break;}
        uint32_t status=emu_read(bar,0x20);
        if (status & ~0x500U) {error=EIO;break;}
        if (status & 0x400U) {
            uint32_t code=emu_read(bar,0x98)&255, after=emu_read(bar,0x30);
            if (code || !(after & 1)) {error=EPROTO;break;}
            dprintf(2,"ML030_VM_UIC_COMPLETE before=0x%x status=0x%x result=%u after=0x%x\n",
                    before,status,code,after);
            break;
        }
        struct timespec delay={0,1000000};nanosleep(&delay,NULL);
    }
done:
    munmap((void *)bar,4096);
    return error;
}
