/* Final SysV child; never appends disk evidence or calls generic failure cleanup. */
#include "s22plus_debian_download_seal_v1.h"
#include <linux/reboot.h>
static int dl_log=-1;
static unsigned dl_records;
static int dl_note(unsigned stage,int error) {
    if(dl_log<0 || dl_records>=32)return EOVERFLOW;
    uint8_t row[32]={0};memcpy(row,"S22DL01",7);sw_put32(row+8,dl_records++);
    sw_put32(row+12,rb_phase);sw_put32(row+16,stage);sw_put32(row+20,(unsigned)error);
    de_put64(row+24,sw_now());
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dprintf(2,"S22_DOWNLOAD_STAGE phase=%u stage=%u errno=%d\n",rb_phase,stage,error);
#endif
    return write(dl_log,row,sizeof(row))==sizeof(row) && !fsync(dl_log) ? 0 : EIO;
}
static __attribute__((noreturn)) void dl_park(int error) {
    if(dl_log>=0){(void)dl_note(255,error);(void)close(dl_log);dl_log=-1;}
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dprintf(2,"S22_DOWNLOAD_PARK errno=%d\n",error);
#endif
    for(;;){struct timespec delay={1,0};(void)nanosleep(&delay,NULL);}
}
static int dl_time(void) {return sw_now()>=sw.deadline_ms ? ETIMEDOUT : 0;}
static int dl_options_ro(const char *text) {
    const char *p=text;unsigned ro=0,rw=0;
    while(*p) {
        const char *end=strchr(p,',');size_t n=end?(size_t)(end-p):strlen(p);
        if(n==2 && !memcmp(p,"ro",2))ro++;
        if(n==2 && !memcmp(p,"rw",2))rw++;
        if(!end)break;
        p=end+1;
    }
    return ro==1 && !rw;
}
/* mountinfo's post-separator options describe the superblock, not a bind flag. */
static int dl_root_readonly(void) {
    struct stat st;struct statfs fs;
    if(stat("/",&st) || (uint64_t)st.st_dev!=sw.root_device || statfs("/",&fs) ||
       fs.f_type!=0xef53 || !(fs.f_flags&ST_RDONLY))return EPROTO;
    FILE *stream=fopen("/proc/self/mountinfo","re");if(!stream)return fs1_error();
    char line[4096];unsigned rows=0,roots=0;int error=0;
    while(fgets(line,sizeof(line),stream)) {
        if(++rows>512 || !strchr(line,'\n')){error=EOVERFLOW;break;}
        char *save=NULL,*fields[64];unsigned count=0;
        for(char *p=strtok_r(line," \n",&save);p;p=strtok_r(NULL," \n",&save)) {
            if(count==64){error=EOVERFLOW;break;}fields[count++]=p;
        }
        if(error)break;
        if(count<10){error=EPROTO;break;}
        if(strcmp(fields[4],"/"))continue;
        unsigned maj,min;char tail;
        if(++roots!=1 || strcmp(fields[3],"/") || sscanf(fields[2],"%u:%u%c",&maj,&min,&tail)!=2 ||
           (uint64_t)makedev(maj,min)!=sw.root_device || !dl_options_ro(fields[5])){error=EPROTO;break;}
        unsigned sep=6;while(sep<count && strcmp(fields[sep],"-"))sep++;
        if(sep+4!=count || strcmp(fields[sep+1],"ext4") || !dl_options_ro(fields[sep+3])){error=EPROTO;break;}
    }
    if(ferror(stream) && !error)error=EIO;
    if(fclose(stream) && !error)error=fs1_error();
    return error ? error : roots==1 ? 0 : EPROTO;
}
static int dl_suffix(const char *path,const char *suffix) {
    size_t a=strlen(path),b=strlen(suffix);return a>=b && !memcmp(path+a-b,suffix,b);
}
static int dl_providers(void) {
    const char *suffixes[]={"/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@7100",
        "/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@7200"};
    unsigned found[2]={0},count=0;int error=0;
    DIR *dir=opendir("/sys/bus/nvmem/devices");if(!dir)return fs1_error();
    for(;;) {
        errno=0;struct dirent *entry=readdir(dir);
        if(!entry){if(errno)error=errno;break;}
        if(++count>256){error=EOVERFLOW;break;}
        if(strncmp(entry->d_name,"spmi_sdam",9))continue;
        const char *n=entry->d_name+9;if(!*n){error=EPROTO;break;}
        for(;*n;n++)if(*n<'0'||*n>'9'){error=EPROTO;break;}
        if(error)break;
        char path[256],link[512];int length=snprintf(path,sizeof(path),"%s/of_node",entry->d_name);
        if(length<=0 || (size_t)length>=sizeof(path)){error=EOVERFLOW;break;}
        ssize_t size=readlinkat(dirfd(dir),path,link,sizeof(link)-1);
        if(size<=0 || size>=(ssize_t)sizeof(link)-1){error=EPROTO;break;}link[size]=0;
        for(unsigned i=0;i<2;i++)if(dl_suffix(link,suffixes[i]))found[i]++;
    }
    if(closedir(dir) && !error)error=fs1_error();
    return error ? error : found[0]==1 && found[1]==1 ? 0 : EPROTO;
}
static int dl_line_equal(const uint8_t *line,size_t length,const char *expected) {
    return length==strlen(expected) && !memcmp(line,expected,length);
}

/* Return the complete command text after an opaque pointer record.  We neither
 * export nor interpret pointer bytes. Function names cannot match a command. */
static size_t dl_command_offset(const uint8_t *line,size_t length) {
    if(length<6U || line[0]!='[' || line[1]!='<') return 0U;
    for(size_t i=2U;i+2U<length;++i)
        if(line[i]=='>' && line[i+1U]==']' && line[i+2U]==' ') return i+3U;
    return 0U;
}

static int dl_registry_valid(const uint8_t *bytes,size_t length) {
    unsigned int stage=0U,seen_stage=0U,priority=0U,default_pending=0U;
    unsigned int default_record=0U,default_ok=0U,download_record=0U,download_ok=0U;
    size_t start=0U;
    for(size_t i=0U;i<length;++i) {
        if(bytes[i]!='\n') continue;
        const uint8_t *line=bytes+start;size_t size=i-start;start=i+1U;
        if(size>512U) return 0;
        if(size>=10U && !memcmp(line,"* STAGE : ",10U)) {
            if(stage) break;
            stage=dl_line_equal(line,size,"* STAGE : Reboot Notifier");
            if(stage && ++seen_stage!=1U) return 0;
            continue;
        }
        if(!stage || size==0U) continue;
        if(dl_line_equal(line,size,"+ Priority : 250")) {priority=1U;continue;}
        if(dl_line_equal(line,size,"+ Default :")) {default_pending=1U;continue;}
        if(dl_line_equal(line,size,"[WARN] default command is not set")) return 0;
        if(size>=14U && !memcmp(line,"  - func : [<",13U)) {
            if(default_record) {default_ok=1U;default_record=default_pending=0U;}
            if(download_record) {download_ok=1U;download_record=0U;}
            continue;
        }
        size_t offset=dl_command_offset(line,size);
        if(offset) {
            if(default_record || download_record) return 0;
            if(default_pending) default_record=1U;
            else if(dl_line_equal(line+offset,size-offset,"download")) download_record=1U;
        }
    }
    return seen_stage==1U && priority && default_ok && download_ok;
}


static int dl_registry_read(void) {
    int fd=open("/sys/kernel/debug/sec_reboot_cmd",O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0)return fs1_error();
    uint8_t bytes[32768];size_t size=0;int error=0;
    for(;;) {
        if(size==sizeof(bytes)){error=EOVERFLOW;break;}
        ssize_t n=read(fd,bytes+size,sizeof(bytes)-size);
        if(n<0){error=fs1_error();break;}if(!n)break;size+=(size_t)n;
    }
    if(close(fd) && !error)error=fs1_error();
    return error ? error : dl_registry_valid(bytes,size) ? 0 : EPROTO;
}
static int dl_registry(void) {
    int error=dl_time();if(error)return error;
    if(mount("debugfs","/sys/kernel/debug","debugfs",MS_RDONLY|MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))return fs1_error();
    uint64_t end=sw_now()+5000;if(end>sw.deadline_ms)end=sw.deadline_ms;
    while(sw_now()<end) {
        error=dl_registry_read();if(!error)return 0;
        if(error!=ENOENT && error!=EPROTO)return error;
        struct timespec delay={0,100000000};(void)nanosleep(&delay,NULL);
    }
    return ETIMEDOUT;
}
static int dl_insert(unsigned index) {
    const struct dl_module *module=&dl_modules[index];
    int fd=fs1_pin_file(module->path,module->size,module->sha,false);
    if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;int error=fstat(fd,&st) || fstatfs(fd,&fs) ||
        st.st_mode!=(S_IFREG|0400) || fs.f_type!=0x01021994L ? EPROTO : 0;
    if(!error)error=dl_time();
    if(!error && syscall(SYS_finit_module,fd,module->params,0))error=fs1_error();
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int dl_prepare(void) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    /* QEMU has no Samsung platform. The actual loader is separately exercised
     * under ARM64 syscall fixtures; these bytes never enter a physical image. */
    return dl_note(40,0);
#else
    for(unsigned i=0;i<sizeof(dl_modules)/sizeof(dl_modules[0]);i++) {
        int error=dl_time();if(error)return error;
        if(i==4 && ((error=dl_providers()) || (error=dl_registry())))return error;
        if((error=dl_note(10+i*2,0)))return error;
        error=dl_insert(i);int recorded=dl_note(11+i*2,error);
        if(error || recorded)return error ? error : recorded;
    }
    struct stat st;
    return stat("/sys/bus/platform/drivers/samsung,qcom-qcom_reboot_reason/soc:samsung,qcom-qcom_reboot_reason",&st) ||
        !S_ISDIR(st.st_mode) ? EPROTO : 0;
#endif
}
static __attribute__((noreturn)) void dl_final(void) {
    struct dh_state state={0};int error=rb_current_early();
    if(!error)error=dh_load(&state);
    if(!error && memcmp(rb_early_nonce,sw.nonce,32))error=EPROTO;
    if(!error)error=de_load(&state);
    if(!error && (!de.complete || de.stopped || de.off ||
        de.control!=(rb_phase==1?RB_REBOOT_INTENT:RB_SHUTDOWN_INTENT)))error=EPROTO;
    if(error)dl_park(error);
    struct statfs ram;
    if(statfs("/run/s22-debian",&ram) || ram.f_type!=0x01021994L ||
       mkdir("/run/s22-debian/return-claimed",0700))dl_park(EPROTO);
    dl_log=open("/run/s22-debian/return-records",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    if(dl_log<0)dl_park(fs1_error());
    if((error=dl_note(1,0)) || (error=dh_actual_init_mode(&state,true)) ||
       (error=dl_root_readonly()) || (error=dl_note(2,0)))dl_park(error);
    if(rb_phase==2 && (error=dl_prepare()))dl_park(error);
    if((error=dl_root_readonly()) || (error=dl_note(50,0)))dl_park(error);
    if((error=dl_time()))dl_park(error);
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    dprintf(2,"S22_DOWNLOAD_VM_CONTROL phase=%u mode=%s\n",rb_phase,rb_phase==1?"ordinary":"download-substituted-poweroff");
    syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,
        rb_phase==1?LINUX_REBOOT_CMD_RESTART:LINUX_REBOOT_CMD_POWER_OFF,0);
#else
    syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,
        rb_phase==1?LINUX_REBOOT_CMD_RESTART:LINUX_REBOOT_CMD_RESTART2,
        rb_phase==1?NULL:"download");
#endif
    dl_park(fs1_error());
}
