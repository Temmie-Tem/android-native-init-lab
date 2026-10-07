/* H0-only Debian early-userspace child. No PID1 loop, filesystem mount,
 * block-data writer, repair, installed-init exec, gadget or reboot operation. */
#define FS1_READONLY_BINDING_ONLY
#ifdef FYG8_VM_TEST
#define fs1_resolve fs1_physical_resolve_unused
#endif
#include "s22plus_native_ext4_v1.c"
#ifdef FYG8_VM_TEST
#undef fs1_resolve
#include "../s22plus_v1/device/virt-binding.inc.c"
#endif
#include <stdarg.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <time.h>
#include "fyg8-plan.h"
#ifdef FYG8_USB_FIRST
#include "usb-first-retained.h"
#endif

_Static_assert(SYS_finit_module == 273, "ARM64 module syscall");
static int events = -1;
static unsigned sequence, event_bytes;
#ifdef FYG8_VM_TEST
static unsigned fake_insertions;
static int fault;
#endif

static int record(const char *format, ...) {
    char line[384];
    int n = snprintf(line, sizeof(line), "FYG8_H0 seq=%u ", ++sequence);
    va_list args; va_start(args, format);
    int more = vsnprintf(line+n, sizeof(line)-(size_t)n, format, args);
    va_end(args);
    if (more < 0 || (size_t)more >= sizeof(line)-(size_t)n-1 || sequence > 256) return EOVERFLOW;
    n += more; line[n++] = '\n';
    if (event_bytes + (unsigned)n > 65536) return EOVERFLOW;
    /* No later effect follows a short/failed evidence write. Do not retry. */
    if (write(events, line, (size_t)n) != n || fsync(events)) return EIO;
    event_bytes += (unsigned)n;
#ifdef FYG8_USB_FIRST
    return usb_retained(sequence,line,(size_t)n);
#else
    return 0;
#endif
}

static int target(void) {
    char model[128]; struct utsname name;
#ifdef FYG8_VM_TEST
    if (fs1_read_text("/sys/firmware/devicetree/base/compatible", model, sizeof(model)) ||
        strcmp(model,"linux,dummy-virt")) return EXDEV;
    char choice[16];
    if (fs1_read_text("/lab/fault", choice, sizeof(choice))) return EINVAL;
    if (!strcmp(choice,"none\n")) fault=0;
    else if (!strcmp(choice,"insert-error\n")) fault=1;
    else if (!strcmp(choice,"existing\n")) fault=2;
    else if (!strcmp(choice,"ro-error\n")) fault=3;
    else if (!strcmp(choice,"no-console\n")) fault=4;
    else return EINVAL;
    if (fault==4) {
        /* VM-only assertion runs inside the active helper, before modules. */
        for (unsigned i=0;i<3;++i) {
            char path[64], destination[64];
            snprintf(path,sizeof(path),"/proc/1/fd/%u",i);
            ssize_t n=readlink(path,destination,sizeof(destination)-1);
            if(n<0 || (size_t)n>=sizeof(destination)-1) return EPROTO;
            destination[n]=0;
            if(strcmp(destination,"/dev/null")) return EPROTO;
        }
        int error=record("VM_PID1_NULL_FDS descriptors=3");
        if(error) return error;
    }
    (void)name;
#else
    if (uname(&name) || strcmp(name.release,fyg8_release) ||
        fs1_read_text("/sys/firmware/devicetree/base/model",model,sizeof(model)) ||
        strcmp(model,fyg8_model)) return EXDEV;
#endif
    return 0;
}

static int module_present(unsigned i) {
#ifdef FYG8_VM_TEST
    return i < fake_insertions;
#else
    char path[PATH_MAX]; struct stat st;
    int n=snprintf(path,sizeof(path),"/sys/module/%s",fyg8_modules[i].runtime);
    if (n < 0 || (size_t)n >= sizeof(path)) return -1;
    if (!lstat(path,&st)) return S_ISDIR(st.st_mode) && st.st_uid==0 ? 1 : -1;
    return errno==ENOENT ? 0 : -1;
#endif
}

static int insert(int fd, const char *parameters) {
#ifdef FYG8_VM_TEST
    (void)fd; (void)parameters;
    if (fault==1) return EIO;
    if (fault==2) return EEXIST;
    ++fake_insertions; return 0;
#else
    return syscall(SYS_finit_module,fd,parameters,0) ? fs1_error() : 0;
#endif
}

static int modules(void) {
    const unsigned count=sizeof(fyg8_modules)/sizeof(fyg8_modules[0]);
    /* Check the entire immutable set before the first insertion. Each file is
     * reopened, hashed and inserted through the same fd at the actual effect. */
    for (unsigned i=0;i<count;++i) {
        if (module_present(i)!=0) return EEXIST;
        int fd=fs1_pin_file(fyg8_modules[i].path,fyg8_modules[i].size,fyg8_modules[i].hash,false);
        if (fd<0) return fs1_error();
        if (close(fd)) return fs1_error();
    }
    for (unsigned i=0;i<count;++i) {
        const struct fyg8_module *m=&fyg8_modules[i];
        int fd=fs1_pin_file(m->path,m->size,m->hash,false);
        if (fd<0) return fs1_error();
        int error=record("MODULE_BEGIN ordinal=%u name=%s",i+1,m->runtime);
        if (!error && module_present(i)!=0) error=EEXIST;
        if (!error) error=insert(fd,m->parameters);
        if (close(fd) && !error) error=fs1_error();
        if (!error && module_present(i)!=1) error=ENODEV;
#ifdef FYG8_USB_FIRST
        if (!error && i==0) error=logger_bound();
#endif
        if (error) return error;  /* Including EEXIST: no reinsertion/replay. */
        if ((error=record("MODULE_DONE ordinal=%u name=%s",i+1,m->runtime))) return error;
    }
    return record("MODULE_SET_READY count=%u",count);
}

static int partition_ro(struct fs1_endpoint *e, bool set) {
    int fd=fs1_open_block(fs1_node,e->partition,FS1_BYTES);
    if (fd<0) return fs1_error();
    int value=1, actual=-1, error=0;
#ifdef FYG8_VM_TEST
    if (set && fault==3) error=EIO;
#endif
    if (!error && set && ioctl(fd,BLKROSET,&value)) error=fs1_error();
    if (!error && (ioctl(fd,BLKROGET,&actual) || actual!=1)) error=EPROTO;
    uint64_t ro=0;
    if (!error && (fs1_number(e->sys_partition,"ro",&ro) || ro!=1)) error=EPROTO;
    if (close(fd) && !error) error=fs1_error();
    return error;
}

/* Same identity rule as the protected inspector: verify the original CRC,
 * normalize only a RAM copy's state/recover/orphan bits, then validate identity.
 * A dirty classification never permits mount or repair. */
static int super_identity(const uint8_t raw[1024]) {
    uint8_t clean[1024]; memcpy(clean,raw,sizeof(clean));
    if (fs1_u32(raw+0x3fc)!=fs1_crc32c(raw,0x3fc)) return EPROTO;
    clean[0x3a]=1; clean[0x3b]=0; clean[0x60]&=~4U; memset(clean+0xe8,0,4);
    uint32_t crc=fs1_crc32c(clean,0x3fc);
    for(unsigned i=0;i<4;++i) clean[0x3fc+i]=(uint8_t)(crc>>(i*8));
    return fs1_superblock(clean,sizeof(clean),fs1_uuid,FS1_BLOCKS) ? 0 : EPROTO;
}

static int storage(bool *clean) {
    struct fs1_endpoint e={.node_fd=-1};
    int error=ENODEV, cleanup=0; bool directory=false, ro=false;
    /* Only absent discovery is retried; no module/control retry. nanosleep is
     * checked. This deadline cannot recover a stalled kernel/module syscall. */
    for(unsigned i=0;i<100;++i) {
        error=fs1_resolve(&e);
        if(error!=ENODEV) break;
        struct timespec delay={0,100000000};
        if(nanosleep(&delay,NULL)) { error=fs1_error(); break; }
    }
    if(error) return error;
    if((error=record("STORAGE_BOUND"))) return error;
    if(mkdir("/dev/.s22-ext4-v1",0700)) return fs1_error();
    directory=true;
    e.node_fd=open("/dev/.s22-ext4-v1",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(e.node_fd<0) {error=fs1_error();goto done;}
    error=fs1_make_node(&e,"native",e.partition,0400);
    if(!error) error=fs1_make_node(&e,"lu0",e.disk,0400);
    if(!error) error=fs1_gpt_exact(&e);
    if(!error) error=record("RO_BEGIN");
    if(!error) error=partition_ro(&e,true);
    if(!error) {ro=true;error=record("RO_DONE");}
    if(!error) error=fs1_read_super(&e,false);
    if(!error) error=super_identity(e.superblock);
    if(!error) {
        uint8_t before[1024];memcpy(before,e.superblock,sizeof(before));
        *clean=fs1_superblock(before,sizeof(before),fs1_uuid,FS1_BLOCKS);
        error=fs1_gpt_exact(&e);
        if(!error) error=fs1_read_super(&e,false);
        if(!error && memcmp(before,e.superblock,sizeof(before))) error=ESTALE;
        if(!error) error=partition_ro(&e,false);
        if(!error) error=record("METADATA state=%s complete_root_admission=0",*clean?"clean":"dirty");
    }
done:
    if(e.node_created && unlinkat(e.node_fd,"native",0)) cleanup=fs1_error();
    if(e.disk_created && unlinkat(e.node_fd,"lu0",0)) cleanup=fs1_error();
    if(e.node_fd>=0 && close(e.node_fd)) cleanup=fs1_error();
    if(directory && rmdir("/dev/.s22-ext4-v1")) cleanup=fs1_error();
    if(ro) {
        uint64_t state=0;
        if(fs1_number(e.sys_partition,"ro",&state) || state!=1) cleanup=EPROTO;
    }
    int logged=record("STORAGE_CLOSED protected=%u cleanup_error=%d",(unsigned)ro,cleanup);
    return error?error:cleanup?cleanup:logged;
}

int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getuid() || geteuid() || getgid() || getegid() || getppid()!=1) return 100;
    umask(077);
    struct stat st; struct statfs fs;
    int dir=open("/run/initramfs",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(dir<0 || fstat(dir,&st) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0700 ||
        fstatfs(dir,&fs) || (unsigned long)fs.f_type!=0x01021994UL) return 101;
    events=openat(dir,"fyg8-events",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(events<0 || close(dir)) return 102;
    char boot[64];
    int error=fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot));
    if(!error && (strlen(boot)!=37 || boot[36]!='\n')) error=EPROTO;
    if(!error) {boot[36]=0;error=record("BEGIN run=%s boot=%s parent=1",fs1_run_id,boot);}
    if(!error) error=target();
    if(!error) error=record("TARGET_GUARD_OK");
    if(!error) error=modules();
    bool clean=false;
    if(!error) error=storage(&clean);
    int logged=record("TERMINAL result=%s error=%d",error?"REJECTED":clean?"METADATA_CLEAN":"METADATA_DIRTY",error);
    if(close(events) && !error) error=EIO;
    return error || logged ? 1 : clean ? 0 : 2;
}
