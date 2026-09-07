/* Host-only syscall fixtures. Never calls a real module loader or reboot. */
#define P260_EOVERFLOW EOVERFLOW
#undef st_atime
#undef st_mtime
#undef st_ctime
struct s22_p241_kernel_stat {
 uint64_t st_dev,st_ino;uint32_t st_mode,st_nlink,st_uid,st_gid;
 uint64_t st_rdev,pad1;int64_t st_size;int32_t st_blksize,pad2;
 int64_t st_blocks,st_atime;uint64_t st_atime_nsec;int64_t st_mtime;
 uint64_t st_mtime_nsec;int64_t st_ctime;uint64_t st_ctime_nsec;uint32_t unused4,unused5;
};
struct s22_p241_linux_dirent64 {uint64_t d_ino;int64_t d_off;uint16_t d_reclen;uint8_t d_type;char d_name[];};
static int fx_pos[5],fx_open[5],fx_registry_pos,fx_registry_opens,fx_dents,fx_prepared,fx_partial,fx_clock_error;
static const char *const fx_names[]={"nvmem_qcom-spmi-sdam.ko","sec_reboot_cmd.ko","sec_qc_rbcmd.ko","qcom-dload-mode.ko","sec_qc_qcom_reboot_reason.ko"};
static const char fx_registry[]="* STAGE : Reboot Notifier\n\n+ Priority : 250\n+ Default :\n[<0000>] (null)\n  - func : [<0000>] default\n\n[<0000>] download\n  - func : [<0000>] strict\n\n* STAGE : Restart Handler\n";
static int fx_case(const char *s){return !strcmp(getenv("P364_CASE"),s);}
static int fx_at(const char *s,int i){char b[64];snprintf(b,sizeof(b),"%s-%d",s,i);return fx_case(b);}
static void fx_mark(const char *s,int i){int f=open(getenv("P364_MARK"),O_WRONLY|O_APPEND|O_CREAT,0600);if(f<0)_Exit(90);dprintf(f,"%s %d\n",s,i);close(f);}
static void fx_park(void){int st;long p=waitpid(-1,&st,WNOHANG);if(p!=-1||errno!=ECHILD)_Exit(91);for(int i=0;i<5;i++)if(fx_open[i])_Exit(92);fx_mark("park",0);_Exit(0);}
static size_t cstr_len(const char*s){return strlen(s);}
static long p345_close_extra_fds(void){return 0;}
static long p345_apply_limits(void){return 0;}
static long p282_make_path(char*out,size_t cap,const char*a,const char*b,const char*c){size_t n=strlen(a)+strlen(b)+strlen(c);if(n>=cap)return -ENAMETOOLONG;memcpy(out,a,strlen(a));memcpy(out+strlen(a),b,strlen(b));memcpy(out+strlen(a)+strlen(b),c,strlen(c)+1);return 0;}
static long fx_openat(const char *p,int flags,int mode){
 for(int i=0;i<5;i++)if(strstr(p,fx_names[i])){if(fx_at("open",i))return -ENOENT;if(fx_open[i])_Exit(93);fx_open[i]=1;fx_pos[i]=0;return 2000+i;}
 if(!strcmp(p,"/sys/bus/nvmem/devices")){fx_dents=0;return 2100;}
 if(!strcmp(p,"/sys/kernel/debug/sec_reboot_cmd")){fx_registry_pos=0;fx_registry_opens++;return 2200;}
 if(!strcmp(p,"/proc/sys/kernel/random/boot_id")){int f=memfd_create("p364-uuid",0);if(f<0)return -errno;const char*u="01234567-89ab-4cde-8fab-0123456789ab\n";if(write(f,u,37)!=37)_Exit(104);if(lseek(f,0,SEEK_SET)!=0)_Exit(105);return f;}
 return neg(open(p,flags,mode));
}
static long fx_read(int fd,void *p,size_t n){
 if(fd>=2000&&fd<2005){int i=fd-2000;char b[32];int len=snprintf(b,sizeof(b),"P364-fixture-%d",i);if(fx_at("read",i))return -EIO;if((int)n>len-fx_pos[i])n=(size_t)(len-fx_pos[i]);memcpy(p,b+fx_pos[i],n);if(n&&fx_pos[i]==0&&fx_at("hash",i))((char*)p)[0]^=1;fx_pos[i]+=(int)n;return (long)n;}
 if(fd==2200){const char*s=(fx_case("registry-timeout")||(fx_case("registry-delay")&&fx_registry_opens<3))?"":fx_registry;size_t left=strlen(s)-(size_t)fx_registry_pos;if(n>left)n=left;memcpy(p,s+fx_registry_pos,n);fx_registry_pos+=(int)n;return (long)n;}
 return neg(read(fd,p,n));
}
static long fx_close(int fd){
 if(fd>=2000&&fd<2005){int i=fd-2000;if(!fx_open[i])_Exit(94);fx_open[i]=0;fx_mark("close",i);return fx_at("close",i)?-EIO:0;}
 if(fd==2100||fd==2200)return 0;
 return neg(close(fd));
}
static long fx_write(int fd,const void*p,size_t n){
 if(fx_partial)return -EIO;
 const unsigned char*b=p;
 if(n==56&&b[5]==0x8b&&fx_case("suppress-diagnostic"))return (long)n;
 if(n==56&&b[5]==0x8b){unsigned stage=b[16]|((unsigned)b[17]<<8),event=b[18];
  if(stage==11&&event==0){if(fx_case("enter-zero"))return 0;if(fx_case("enter-eagain"))return -EAGAIN;if(fx_case("enter-partial")){fx_partial=1;return neg(write(fd,p,7));}}
  if(stage==11&&event==1&&fx_case("return-zero"))return 0;
  if(stage==40&&event==1&&fx_case("pipe-return-zero"))return 0;
  if(stage==42&&event==1&&fx_case("clone-return-zero"))return 0;
  if(stage==41&&event==0&&fx_case("clock")){long rc=neg(write(fd,p,n));if(rc==(long)n)fx_clock_error=1;return rc;}
 }
 return neg(write(fd,p,n));
}
static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){
 (void)e;(void)f;
 if(nr==80&&a>=2000&&a<2005){int i=(int)a-2000;struct s22_p241_kernel_stat*s=(void*)b;memset(s,0,sizeof(*s));s->st_mode=fx_at("mode",i)?0100600:0100400;s->st_nlink=1;s->st_size=14;return 0;}
 if(nr==62&&a>=2000&&a<2005){fx_pos[a-2000]=0;return 0;}
 if(nr==25)return neg(fcntl((int)a,(int)b,c));
 if(nr==142){if((unsigned long)a!=0xfee1deadUL||b!=672274793UL||c!=0xa1b2c3d4UL||!d||strcmp((char*)d,"download"))_Exit(95);fx_mark("download",0);return -EIO;}
 if(nr==157)return neg(setsid());
 if(nr==278)return neg(getrandom((void*)a,(size_t)b,(unsigned)c));
 return -ENOSYS;
}
static long p241_finit_module(int fd,const char*params){int i=fd-2000;if(i<0||i>=5||fx_pos[i]!=0)_Exit(96);if(strcmp(params,i==3?"download_mode=0":""))_Exit(97);fx_mark("finit",i);if(fx_at("hang",i))for(;;)usleep(10000);return fx_at("finit",i)?-ENOEXEC:0;}
static long sys_mount(const char*s,const char*p,const char*t,unsigned long f,const void*d){if(strcmp(s,"debugfs")||strcmp(p,"/sys/kernel/debug")||strcmp(t,"debugfs")||f!=15||d)_Exit(98);fx_mark("mount",0);return fx_case("mount")?-EPERM:0;}
static long p241_getdents64(int fd,void*p,size_t n){if(fd!=2100||n<480)_Exit(99);if(fx_dents++)return 0;for(int i=0;i<12;i++){struct s22_p241_linux_dirent64*d=(void*)((char*)p+i*40);memset(d,0,40);d->d_reclen=40;snprintf(d->d_name,21,"spmi_sdam%d",i);}return 480;}
static long p241_readlinkat(const char*p,char*out,size_t n){const char*s=strstr(p,"/spmi_sdam");if(!s)_Exit(100);int i=atoi(s+10);static const char*nodes[]={"7000","7100","7400","7c00","7d00","8400","8500","8600","9700","9800","9d00","7200"};if(i<0||i>11)_Exit(101);const char*node=(fx_case("provider")&&i==1)?"7300":nodes[i];int len=snprintf(out,n,"../../firmware/devicetree/base/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@%s",node);return len;}
static long p241_newfstatat(const char*p,struct s22_p241_kernel_stat*s,int f){if(strcmp(p,"/sys/bus/platform/drivers/samsung,qcom-qcom_reboot_reason/soc:samsung,qcom-qcom_reboot_reason")||f)_Exit(102);memset(s,0,sizeof(*s));s->st_mode=0040000;if(fx_case("writer"))return -ENOENT;fx_prepared=1;return 0;}
