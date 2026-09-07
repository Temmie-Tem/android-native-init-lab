/* Exact stock additions, one insertion each, in the supervisor.  The table is
 * generated from the same declaration that packages and audits the ramdisk.
 * There is no unload, retry, firmware command interface or arbitrary NVMEM I/O.
 * download_mode=0 initially requests NODUMP/disable_sdi; Samsung writer probe
 * subsequently requests FULLDUMP. A clean reboot notifier clears it again.
 * This initialization window and the stock NVMEM ERR_PTR bug require attended
 * physical Download recovery. These functions do not establish recovery. */

static long p363_insert_module(const struct p363_return_module *module) {
    long fd=sys_openat(module->path,O_RDONLY|O_CLOEXEC|0400000,0);
    if(fd<0) return fd;
    struct s22_p241_kernel_stat metadata={0};
    long rc=syscall6(80,fd,(long)(uintptr_t)&metadata,0,0,0,0);
    if(rc==0 && (metadata.st_mode!=0100400U || metadata.st_uid || metadata.st_gid ||
        metadata.st_nlink!=1U || metadata.st_size!=(int64_t)module->size)) rc=-P260_EPROTO;
    struct s22plus_max77705_runtime_sha256 context;
    s22plus_max77705_runtime_sha256_init(&context);
    uint8_t bytes[4096],hash[32];uint64_t used=0U;
    while(rc==0) {
        long n=sys_read((int)fd,bytes,sizeof(bytes));
        if(n<0) {rc=n;break;}
        if(n==0) break;
        if((size_t)n>sizeof(bytes) || (uint64_t)n>module->size-used) {rc=-P260_EPROTO;break;}
        s22plus_max77705_runtime_sha256_update(&context,bytes,(size_t)n);
        used+=(uint64_t)n;
    }
    s22plus_max77705_runtime_sha256_final(&context,hash);
    if(rc==0 && (used!=module->size || !p328_constant_time_equal(hash,module->hash,32U))) rc=-P260_EPROTO;
    if(rc==0) rc=syscall6(62,fd,0,0,0,0,0);
    if(rc==0) rc=p241_finit_module((int)fd,module->params);
    long closed=sys_close((int)fd);
    return rc?rc:closed;
}

static int p363_line_equal(const uint8_t *line,size_t length,const char *expected) {
    return length==cstr_len(expected) && p260_bytes_equal((const char *)line,expected,length);
}

/* Return the complete command text after an opaque pointer record.  We neither
 * export nor interpret pointer bytes. Function names cannot match a command. */
static size_t p363_command_offset(const uint8_t *line,size_t length) {
    if(length<6U || line[0]!='[' || line[1]!='<') return 0U;
    for(size_t i=2U;i+2U<length;++i)
        if(line[i]=='>' && line[i+1U]==']' && line[i+2U]==' ') return i+3U;
    return 0U;
}

static int p363_reboot_registry(const uint8_t *bytes,size_t length) {
    unsigned int stage=0U,seen_stage=0U,priority=0U,default_pending=0U;
    unsigned int default_record=0U,default_ok=0U,download_record=0U,download_ok=0U;
    size_t start=0U;
    for(size_t i=0U;i<length;++i) {
        if(bytes[i]!='\n') continue;
        const uint8_t *line=bytes+start;size_t size=i-start;start=i+1U;
        if(size>512U) return 0;
        if(size>=10U && p260_bytes_equal((const char *)line,"* STAGE : ",10U)) {
            if(stage) break;
            stage=p363_line_equal(line,size,"* STAGE : Reboot Notifier");
            if(stage && ++seen_stage!=1U) return 0;
            continue;
        }
        if(!stage || size==0U) continue;
        if(p363_line_equal(line,size,"+ Priority : 250")) {priority=1U;continue;}
        if(p363_line_equal(line,size,"+ Default :")) {default_pending=1U;continue;}
        if(p363_line_equal(line,size,"[WARN] default command is not set")) return 0;
        if(size>=14U && p260_bytes_equal((const char *)line,"  - func : [<",13U)) {
            if(default_record) {default_ok=1U;default_record=default_pending=0U;}
            if(download_record) {download_ok=1U;download_record=0U;}
            continue;
        }
        size_t offset=p363_command_offset(line,size);
        if(offset) {
            if(default_record || download_record) return 0;
            if(default_pending) default_record=1U;
            else if(p363_line_equal(line+offset,size-offset,"download")) download_record=1U;
        }
    }
    return seen_stage==1U && priority && default_ok && download_ok;
}

static long p363_read_reboot_registry(void) {
    long rc=0;
    long fd=sys_openat("/sys/kernel/debug/sec_reboot_cmd",O_RDONLY|O_CLOEXEC,0);
    if(fd<0) return fd;
    uint8_t bytes[32768];size_t used=0U;
    for(;;) {
        if(used==sizeof(bytes)) {rc=-P260_EOVERFLOW;break;}
        long n=sys_read((int)fd,bytes+used,sizeof(bytes)-used);
        if(n<0) {rc=n;break;}
        if(n==0) break;
        if((size_t)n>sizeof(bytes)-used) {rc=-EIO;break;}
        used+=(size_t)n;
    }
    long closed=sys_close((int)fd);
    if(rc || closed) return rc?rc:closed;
    return p363_reboot_registry(bytes,used)?0:-P260_EPROTO;
}

/* The stock rbcmd director registers its table asynchronously. Mount once,
 * then reopen only this metadata file for at most five seconds. This never
 * reinserts a module or retries a control effect. Blocking kernel calls still
 * require attended physical recovery; the timer is not that recovery. */
static long p363_verify_reboot_registry(void) {
    long rc=sys_mount("debugfs","/sys/kernel/debug","debugfs",15UL,NULL);
    if(rc!=0) return rc;
    struct timespec64 deadline={0};
    rc=p282_deadline_after(5LL,&deadline);
    if(rc!=0) return rc;
    for(;;) {
        if(p282_deadline_expired(&deadline)) return -ETIMEDOUT;
        rc=p363_read_reboot_registry();
        if(rc==0) return 0;
        if(rc!=-P260_EPROTO && rc!=-ENOENT) return rc;
        p282_poll_delay();
    }
}

/* Resolve both exact SDAM providers by immutable DT node, not a dynamic
 * spmi_sdamN ordinal. Bounded metadata-only enumeration; never open nvmem data. */
static long p363_nvmem_providers(void) {
    static const char prefix[]="spmi_sdam";
    static const char *const suffixes[]={
        "/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@7100",
        "/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@7200"};
    unsigned int found[2]={0U,0U},entries=0U;
    long fd=sys_openat("/sys/bus/nvmem/devices",O_RDONLY|O_CLOEXEC|0200000,0);
    if(fd<0) return fd;
    uint8_t buffer[4096];long rc=0;unsigned int batches=0U;
    for(;;) {
        if(++batches>16U) {rc=-P260_EOVERFLOW;break;}
        long n=p241_getdents64((int)fd,buffer,sizeof(buffer));
        if(n<0) {rc=n;break;}
        if(n==0) break;
        if((size_t)n>sizeof(buffer)) {rc=-EIO;break;}
        size_t used=0U;
        while(used<(size_t)n) {
            if((size_t)n-used<20U || ++entries>256U) {rc=-P260_EPROTO;break;}
            const struct s22_p241_linux_dirent64 *entry=(const void *)(buffer+used);
            size_t record=entry->d_reclen;
            if(record<20U || record>(size_t)n-used) {rc=-P260_EPROTO;break;}
            size_t size=0U;
            while(size<record-19U && entry->d_name[size]) ++size;
            if(size==record-19U || size>127U) {rc=-P260_EPROTO;break;}
            if(size>sizeof(prefix)-1U && p260_bytes_equal(entry->d_name,prefix,sizeof(prefix)-1U)) {
                for(size_t i=sizeof(prefix)-1U;i<size;++i)
                    if(entry->d_name[i]<'0'||entry->d_name[i]>'9') {rc=-P260_EPROTO;break;}
                if(rc) break;
                char path[256],target[512];
                rc=p282_make_path(path,sizeof(path),"/sys/bus/nvmem/devices/",entry->d_name,"/of_node");
                if(rc) break;
                long length=p241_readlinkat(path,target,sizeof(target));
                if(length<=0 || (size_t)length>=sizeof(target)) {rc=length<0?length:-EIO;break;}
                for(unsigned int i=0U;i<2U;++i) {
                    size_t suffix=cstr_len(suffixes[i]);
                    if((size_t)length>=suffix && p260_bytes_equal(target+(size_t)length-suffix,suffixes[i],suffix))
                        ++found[i];
                }
            }
            used+=record;
        }
        if(rc) break;
    }
    long closed=sys_close((int)fd);
    if(rc || closed) return rc?rc:closed;
    return found[0]==1U && found[1]==1U ? 0 : -P260_EPROTO;
}

static long p363_prepare_return(void) {
    for(size_t i=0U;i<sizeof(p363_return_modules)/sizeof(p363_return_modules[0]);++i) {
        long rc=0;
        if(i==4U) {
            rc=p363_nvmem_providers();
            if(rc==0) rc=p363_verify_reboot_registry();
        }
        if(rc==0) rc=p363_insert_module(&p363_return_modules[i]);
        if(rc!=0) return rc;
    }
    /* Exact DT writer node; insertion is synchronous with already registered
     * NVMEM providers. The link is used after that insertion, not as a polling
     * substitute for an asynchronous completion event. */
    struct s22_p241_kernel_stat metadata={0};
    long rc=p241_newfstatat("/sys/bus/platform/drivers/samsung,qcom-qcom_reboot_reason/soc:samsung,qcom-qcom_reboot_reason",&metadata,0);
    if(rc!=0 || (metadata.st_mode&0170000U)!=0040000U) return rc?rc:-P260_EPROTO;
    return 0;
}
