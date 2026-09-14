"""Real host tty syscalls with an explicit fixture-only fixed-node route.

The production owner is unmodified. Descriptor reuse and ioctl/write faults
are injected at the syscall boundary; no real USB/device node is contacted.
"""
import re

import s22plus_native_reconnect_source_v1 as source


def platform_tty_definitions():
    raw=source.common._read(source.NATIVE/'s22plus_fyg8_p260_e3_runtime.inc.c').decode()
    names=('NR_IOCTL','O_NOCTTY','TCGETS','TCSETS','CSIZE','CS8','CREAD','PARENB','CLOCAL')
    definitions='\n'.join(re.search(r'^#define P260_'+name+r' .+$',raw,re.M)[0] for name in names)+'\n'
    start=raw.index('struct p260_termios {');end=raw.index('static const char p260_gadget_root')
    return definitions+raw[start:end]


def native_fixture(raw):
    def swap(before,after):
        nonlocal raw
        raw=source.resident.replace(raw.encode(),before.encode(),after.encode()).decode()
    swap('static long fx_openat(const char *p,int flags,int mode){',r'''
static int fx_transport,fx_tty_generation,fx_tty_alias=-1;
static pid_t fx_owner_pid;
static long fx_openat(const char *p,int flags,int mode){
 if(!strcmp(p,"/dev/ttyGS0")){
  if(flags!=(O_RDWR|O_NOCTTY|O_NONBLOCK|O_CLOEXEC)||mode)_Exit(150);
  fx_mark("tty-open-attempt",0);
  char route[4096],path[256];snprintf(route,sizeof(route),"%s/tty-route",getenv("RC1_WORK"));
  FILE *file=fopen(route,"r");if(!file)return -ENOENT;
  if(fscanf(file,"%255s",path)!=1||fclose(file))_Exit(151);
  int fd=open(path,flags,mode);if(fd<0)return -errno;
  fx_transport=fd;++fx_tty_generation;fx_mark("tty-open",fx_tty_generation);return fd;
 }
''')
    swap('static long fx_close(int fd){',r'''
static long fx_close(int fd){
 if(fd==fx_transport && getpid()==fx_owner_pid){
  fx_mark("tty-close",fx_tty_generation);long rc=neg(close(fd));
  if(fx_case("tty-close-eintr")){
   int fresh=open("/dev/null",O_RDONLY|O_CLOEXEC);if(fresh<0)_Exit(152);
   if(fresh!=fd){if(dup3(fresh,fd,O_CLOEXEC)!=fd||close(fresh))_Exit(152);}
   fx_tty_alias=fd;return -EINTR;
  }
  return rc;
 }
''')
    swap('static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){',r'''
static long fx_syscall(long nr,long a,long b,long c,long d,long e,long f){
 if(nr==29){
  if(d||e||f||a!=fx_transport||(b!=0x5401&&b!=0x5402))_Exit(153);
  if((fx_case("tty-config-initial")&&!fx_tty_generation)||
     (fx_case("tty-config-reopen")&&fx_tty_generation))return -EINVAL;
  static int configuration_drop;
  if(!configuration_drop&&((fx_case("tty-config-loss-initial")&&!fx_tty_generation)||
     (fx_case("tty-config-loss-reopen")&&fx_tty_generation))){configuration_drop=1;return -EIO;}
  long rc=neg(syscall(SYS_ioctl,a,b,c));
  if(!rc&&b==0x5401&&fx_case("tty-readback-reopen")&&fx_tty_generation)
   ((unsigned char*)c)[17+6]=0;
  if(!rc&&b==0x5402)fx_mark("tty-config",fx_tty_generation);
  return rc;
 }
''')
    swap('static void fx_resident_observe(void){',r'''
static void fx_resident_observe(void){
 if(fx_tty_alias>=0&&fcntl(fx_tty_alias,F_GETFD)<0)_Exit(154);
''')
    swap('static long fx_write(int fd,const void*p,size_t n){',r'''
static long fx_write(int fd,const void*p,size_t n){
 static int tty_ack_partial;
 if(tty_ack_partial&&fd==fx_transport)return -EIO;
 if(fd==fx_transport&&n>=6&&((const unsigned char*)p)[5]==167&&fx_case("tty-detach-partial")){
  tty_ack_partial=1;fx_mark("tty-partial-ack",0);return neg(write(fd,p,7));
 }
''')
    swap('#define UR1_IDLE_LINK_LOST (-4096L)',platform_tty_definitions()+r'''
static long p260_ioctl(int fd,unsigned long request,void *argument){
 return syscall6(P260_NR_IOCTL,fd,request,(long)(uintptr_t)argument,0,0,0);
}
#define UR1_IDLE_LINK_LOST (-4096L)''')
    return raw
