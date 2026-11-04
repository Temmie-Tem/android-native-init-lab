/* Fixed Debian-managed service and rc evidence, only in the rc-cycle image. */
#ifndef G0Q_SERVICE_CYCLE_H
#define G0Q_SERVICE_CYCLE_H
enum cycle_stage {C_START,C_RC2,C_STOP,C_RC6};
static const char *const cycle_paths[]={
    "/run/g0q-ssh-start","/run/g0q-rc2","/run/g0q-ssh-stop","/run/g0q-rc6"
};
struct cycle_record {
    unsigned stage,level,previous,rc,master,ticks,pid,parent;
    uint64_t began,ended;
    char boot[37];
};
static int cycle_boot(char out[37]) {
    char bytes[38];size_t n;int e=read_small("/proc/sys/kernel/random/boot_id",bytes,sizeof(bytes),&n);
    if(e||n!=37||bytes[36]!='\n')return EPROTO;
    memcpy(out,bytes,36);out[36]=0;return 0;
}
static int cycle_env(unsigned level) {
    const char *l=getenv("RUNLEVEL"),*p=getenv("PREVLEVEL");
    return l && p && !strcmp(l,level==2?"2":"6") && !strcmp(p,level==2?"N":"2") ? 0:EPROTO;
}
static int cycle_name(char path[96],unsigned stage,const char *suffix) {
    int n=snprintf(path,96,"%s%s",cycle_paths[stage],suffix);
    return n>0&&n<96?0:ENAMETOOLONG;
}
static int cycle_write(const char *path,const void *p,size_t size) {
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(fd<0)return errno;
    size_t used=0;int e=0;
    while(used<size) {
        ssize_t n=write(fd,(const char*)p+used,size-used);
        if(n<0&&errno==EINTR)continue;
        if(n<=0){e=n<0?errno:EIO;break;} used+=(size_t)n;
    }
    if(close(fd)&&!e)e=errno;
    return e;
}
static int cycle_begin(unsigned stage,struct cycle_record *v) {
    memset(v,0,sizeof(*v));v->stage=stage;v->level=stage<=C_RC2?2:6;
    v->previous=v->level==2?'N':'2';v->pid=(unsigned)getpid();v->parent=(unsigned)getppid();
    v->began=now_ms();if(v->began>=deadline)return ETIMEDOUT;
    int e=cycle_env(v->level);if(e)return e;
    if((e=cycle_boot(v->boot)))return e;
    char path[96];if((e=cycle_name(path,stage,".intent")))return e;
    return cycle_write(path,v,sizeof(*v));
}
static int cycle_finish(struct cycle_record *v,int rc) {
    v->ended=now_ms();
    if(v->ended>=deadline&&!rc)rc=ETIMEDOUT;
    v->rc=(unsigned)rc;char path[96];int e=cycle_name(path,v->stage,".tmp");
    if(!e)e=cycle_write(path,v,sizeof(*v));
    if(!e&&link(path,cycle_paths[v->stage]))e=errno;
    if(!e&&unlink(path))e=errno;
    dprintf(2,"G0Q_RC_STAGE stage=%u rc=%d\n",v->stage,rc?rc:e);
    return rc?rc:e;
}
static int cycle_record(unsigned stage,struct cycle_record *v) {
    int fd=open(cycle_paths[stage],O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)return errno;
    struct stat st;int e=0;char boot[37];
    if(fstat(fd,&st)||!S_ISREG(st.st_mode)||(st.st_mode&07777)!=0400||
       st.st_uid||st.st_size!=(off_t)sizeof(*v))e=EPROTO;
    if(!e&&read(fd,v,sizeof(*v))!=(ssize_t)sizeof(*v))e=EIO;
    if(close(fd)&&!e)e=errno;
    if(e)return e;
    if((e=cycle_boot(boot)))return e;
    if(v->stage!=stage||v->level!=(stage<=C_RC2?2U:6U)||v->previous!=(stage<=C_RC2?'N':'2')||
       memcmp(boot,v->boot,sizeof(boot))||!v->began||v->began>v->ended||v->ended>=deadline||
       v->pid<=1||!v->parent||v->rc)return EPROTO;
    return 0;
}
static int cycle_proc(pid_t pid,unsigned *parent,unsigned *ticks) {
    char path[64],data[4096];size_t n;
    snprintf(path,sizeof(path),"/proc/%ld/stat",(long)pid);
    int e=read_small(path,data,sizeof(data)-1,&n);if(e)return e;
    data[n]=0;char *end=strrchr(data,')'),*save=NULL;
    if(!end||end[1]!=' ')return EPROTO;
    char *field=strtok_r(end+2," ",&save);
    for(unsigned i=3;i<=22;i++) {
        if(!field)return EPROTO;
        if(i==4||i==22) {
            char *tail;errno=0;unsigned long x=strtoul(field,&tail,10);
            if(errno||*tail||x>UINT32_MAX||field[0]<'0'||field[0]>'9')return EPROTO;
            if(i==4)*parent=(unsigned)x;else *ticks=(unsigned)x;
        }
        field=strtok_r(NULL," ",&save);
    }
    return 0;
}
static int cycle_args(pid_t pid,const char *const *expected,size_t count) {
    char name[64],data[512];size_t size,used=0;snprintf(name,sizeof(name),"/proc/%ld/cmdline",(long)pid);
    int e=read_small(name,data,sizeof(data),&size);if(e)return e;
    for(size_t i=0;i<count;i++) {
        size_t n=strlen(expected[i])+1;
        if(n>size-used||memcmp(data+used,expected[i],n))return EPROTO;
        used+=n;
    }
    return used==size?0:EPROTO;
}
static int cycle_service_parent(unsigned level) {
    unsigned wrapper=0,ticks=0,init=0;pid_t rc=getppid();int e;
    if((e=cycle_proc(rc,&wrapper,&ticks))||(e=cycle_proc((pid_t)wrapper,&init,&ticks)))return e;
    const char *l=level==2?"2":"6";
    const char *dispatch[]={"/bin/sh","/usr/lib/init/rc",l};
    const char *entry[]={"/usr/libexec/g0q-ram-observer","rc",l};
    if(init!=1)return EPROTO;
    if((e=cycle_args(rc,dispatch,3)))return e;
    return cycle_args((pid_t)wrapper,entry,3);
}
static int cycle_master(unsigned *pid,unsigned *ticks) {
    char data[32],path[64];size_t n;int e=read_small("/run/sshd.pid",data,sizeof(data)-1,&n);
    if(e)return e;
    if(n<2||data[n-1]!='\n'||data[0]<'1'||data[0]>'9')return EPROTO;
    data[n-1]=0;char *tail;errno=0;unsigned long x=strtoul(data,&tail,10);
    if(errno||*tail||x<2||x>INT_MAX)return EPROTO;
    struct stat actual,wanted;snprintf(path,sizeof(path),"/proc/%lu/exe",x);
    if(stat(path,&actual)||stat("/usr/sbin/sshd",&wanted))return errno;
    if(actual.st_dev!=wanted.st_dev||actual.st_ino!=wanted.st_ino)return EPROTO;
    unsigned parent=0;if((e=cycle_proc((pid_t)x,&parent,ticks)))return e;
    if(parent!=1||!*ticks)return EPROTO;
    *pid=(unsigned)x;return 0;
}
static int cycle_processes(unsigned *count) {
    const char *files[]={"/usr/sbin/sshd","/usr/lib/openssh/sshd-auth","/usr/lib/openssh/sshd-session"};
    struct stat wanted[3];for(unsigned i=0;i<3;i++)if(stat(files[i],wanted+i))return errno;
    DIR *d=opendir("/proc");if(!d)return errno;int e=0;*count=0;
    for(;;) {
        if(now_ms()>=deadline){e=ETIMEDOUT;break;}
        errno=0;struct dirent *ent=readdir(d);if(!ent){e=errno;break;}
        if(ent->d_name[0]<'0'||ent->d_name[0]>'9')continue;
        char path[64];int n=snprintf(path,sizeof(path),"/proc/%s/exe",ent->d_name);struct stat st;
        if(n<0||(size_t)n>=sizeof(path)){e=EOVERFLOW;break;}
        if(stat(path,&st)){if(errno==ENOENT||errno==ESRCH)continue;e=errno;break;}
        for(unsigned i=0;i<3;i++)if(st.st_dev==wanted[i].st_dev&&st.st_ino==wanted[i].st_ino)(*count)++;
    }
    if(closedir(d)&&!e)e=errno;
    return e;
}
static void cycle_tick(void) {struct timespec t={0,20000000};nanosleep(&t,NULL);}
static int cycle_call(char *const argv[]) {
    if(now_ms()>=deadline)return ETIMEDOUT;
    pid_t pid=fork();if(pid<0)return errno;
    if(!pid) {
        if(now_ms()>=deadline)_exit(124);
        execv(argv[0],argv);_exit(126);
    }
    for(;;) {
        int status=0;pid_t result=waitpid(pid,&status,WNOHANG);
        if(result==pid)return WIFEXITED(status)?WEXITSTATUS(status):EINTR;
        if(result<0&&errno!=EINTR)return errno;
        if(now_ms()>=deadline) {
            /* Only this invocation's still-owned child; an init FIFO submission
             * may already have taken effect. Never submit or reset again. */
            (void)kill(pid,SIGKILL);(void)waitpid(pid,&status,WNOHANG);return ETIMEDOUT;
        }
        cycle_tick();
    }
}
static int cycle_service(const char *action) {
    int start=!strcmp(action,"start"),e;unsigned count=0;
    if(!start&&strcmp(action,"stop"))return EINVAL;
    if((e=cycle_service_parent(start?2:6)))return e;
    struct cycle_record v,previous;if((e=cycle_begin(start?C_START:C_STOP,&v)))return e;
    if(start) {
        if(!(e=cycle_processes(&count))&&count)e=EEXIST;
        struct stat st;if(!e&&(!lstat("/run/sshd.pid",&st)||errno!=ENOENT))e=EEXIST;
    } else {
        if(!(e=cycle_record(C_START,&previous)))e=cycle_master(&v.master,&v.ticks);
        if(!e&&(v.master!=previous.master||v.ticks!=previous.ticks))e=ESRCH;
    }
    char *const argv[]={"/etc/init.d/ssh",(char*)action,NULL};
    if(!e)e=cycle_call(argv);
    if(start&&!e) {
        uint64_t until=now_ms()+10000;if(until>deadline)until=deadline;
        do {e=cycle_master(&v.master,&v.ticks);if(!e)break;cycle_tick();}while(now_ms()<until);
    }
    return cycle_finish(&v,e);
}
static int cycle_level(const char *selected) {
    int start=!strcmp(selected,"2"),e;
    if((!start&&strcmp(selected,"6"))||getppid()!=1)return EINVAL;
    struct statfs fs;if(statfs("/proc",&fs)||fs.f_type!=PROC_SUPER_MAGIC)return EPROTO;
    struct cycle_record v,service;
    if((e=cycle_begin(start?C_RC2:C_RC6,&v)))return e;
    char *const argv[]={"/usr/lib/init/rc",(char*)selected,NULL};
    e=cycle_call(argv);
    if(!e)e=cycle_record(start?C_START:C_STOP,&service);
    if(!e&&(service.began<v.began||service.ended>now_ms()))e=EPROTO;
    if(!e){v.master=service.master;v.ticks=service.ticks;}
    return cycle_finish(&v,e);
}
static int cycle_started(unsigned *master,unsigned *ticks) {
    struct cycle_record start,level;int e;
    if((e=cycle_record(C_START,&start))||(e=cycle_record(C_RC2,&level))||(e=cycle_master(master,ticks)))return e;
    if(level.parent!=1||level.began>start.began||start.ended>level.ended||
       *master!=start.master||*ticks!=start.ticks||*master!=level.master||*ticks!=level.ticks)return EPROTO;
    return 0;
}
static int cycle_transition(const uint8_t response[G0Q_RESPONSE_SIZE],uint8_t *fields) {
    unsigned master=0,ticks=0,count=0;int e=cycle_started(&master,&ticks);
    if(e||master!=g_u32(response+280)||ticks!=g_u32(response+284))return e?e:EPROTO;
    struct stat st;
    for(unsigned stage=C_STOP;stage<=C_RC6;stage++) {
        char path[96];if((e=cycle_name(path,stage,".intent")))return e;
        if(!lstat(path,&st)||errno!=ENOENT||!lstat(cycle_paths[stage],&st)||errno!=ENOENT)return EEXIST;
    }
    struct cycle_record stop,level;uint64_t began=now_ms();
    char *const argv[]={"/usr/sbin/init","6",NULL};
    if((e=cycle_call(argv)))return e; /* CLI exit alone never proves runlevel 6. */
    while((e=cycle_record(C_RC6,&level))==ENOENT&&now_ms()<deadline)cycle_tick();
    if(e)return e;
    if((e=cycle_record(C_STOP,&stop)))return e;
    if(master!=stop.master||ticks!=stop.ticks||master!=level.master||ticks!=level.ticks||
       level.parent!=1||level.began<began||level.began>stop.began||stop.ended>level.ended)return EPROTO;
    for(;;) {
        unsigned p=0,t=0;int old=cycle_proc((pid_t)master,&p,&t);
        if(old&&old!=ENOENT&&old!=ESRCH)return old;
        if((e=cycle_processes(&count)))return e;
        int absent=lstat("/run/sshd.pid",&st);
        if(absent&&errno!=ENOENT)return errno;
        if((old||t!=ticks)&&!count&&absent)break;
        if(now_ms()>=deadline)return ETIMEDOUT;
        cycle_tick();
    }
    if(now_ms()>=deadline||getppid()!=1)return ETIMEDOUT;
    g_put32(fields,master);g_put32(fields+4,ticks);
    g_put32(fields+8,2);g_put32(fields+12,6);g_put32(fields+16,stop.rc);
    g_put32(fields+20,level.rc);g_put32(fields+24,count);g_put32(fields+28,(unsigned)getpid());
    g_put64(fields+32,stop.ended);g_put64(fields+40,level.ended);
    return 0;
}
#endif
