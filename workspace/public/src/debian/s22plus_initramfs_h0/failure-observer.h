/* Included after the fixed worker function and its sealed evidence protocol. */
#ifdef S22_FAILURE_OBSERVER
#include "checked-kmsg.h"
#include "pid1-measure.h"
/* No chain: a terminal record authenticates even when START is missing. */
static int fo_publish(unsigned helper,unsigned sequence,unsigned outcome,unsigned status,int wait_error) {
    unsigned fields[FO_FIELDS]={0},stable=0;
    for(unsigned attempt=0;attempt<8;++attempt) {
        unsigned before=atomic_load(&fo_state->generation);
        if(before&1U)continue;
        for(unsigned i=0;i<FO_FIELDS;++i)fields[i]=atomic_load(&fo_state->field[i]);
        if(before==atomic_load(&fo_state->generation)){stable=1;break;}
    }
    if(!stable)memset(fields,0,sizeof(fields));
    uint8_t raw[(FO_FIELDS+5)*4],nonce[32],mac[32];
    early_put32(raw,outcome);early_put32(raw+4,status);early_put32(raw+8,(unsigned)wait_error);
    early_put32(raw+12,stable);early_put32(raw+16,(unsigned)fo_deadline);
    for(unsigned i=0;i<FO_FIELDS;++i)early_put32(raw+20+4*i,fields[i]);
    char boot[38],run[33],tag[65],data[sizeof(raw)*2+1],line[768];
    if(fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot)) ||
        strlen(boot)!=37 || boot[36]!='\n')return EPROTO;
    boot[36]=0;early_hash(boot,36,nonce);early_tag(mac,nonce,250+helper,sequence,raw,sizeof(raw));
    for(unsigned i=0;i<16;++i)snprintf(run+2*i,3,"%02x",early_run[i]);
    for(unsigned i=0;i<32;++i)snprintf(tag+2*i,3,"%02x",mac[i]);
    for(unsigned i=0;i<sizeof(raw);++i)snprintf(data+2*i,3,"%02x",raw[i]);
    int n=snprintf(line,sizeof(line),"<14>S22DIAG1 run=%s boot=%s helper=%u seq=%u mac=%s data=%s\n",
        run,boot,helper,sequence,tag,data);
    if(n<0 || (size_t)n>=sizeof(line))return EOVERFLOW;
    return checked_kmsg(line,n);
}
static void fo_park(void) {
    for(;;){struct timespec delay={1,0};(void)nanosleep(&delay,NULL);}
}
static int fo_supervise(unsigned helper,int (*work)(int,char **),int argc,char **argv) {
    if(argc!=1 || getpid()==1 || getppid()!=1 || getuid() || geteuid() || getgid() || getegid())return 110;
    fo_state=mmap(NULL,sizeof(*fo_state),PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
    if(fo_state==MAP_FAILED){fo_state=NULL;return 111;}
    atomic_init(&fo_state->generation,0);atomic_init(&fo_state->stop,0);
    for(unsigned i=0;i<FO_FIELDS;++i)atomic_init(&fo_state->field[i],0);
    fo_parent=getpid();fo_phase(FO_START);
    uint8_t shell[32],init[32];int measured=measure_pid1(shell,init);
    if(measured){(void)fo_publish(helper,1,5,0,measured);return 112;}
    fo_set(FO_PID1_VALID,1);
    uint64_t now=fo_now();
    if(now==UINT64_MAX || now>=fo_deadline){(void)fo_publish(helper,1,5,0,now==UINT64_MAX?EIO:ETIMEDOUT);return 112;}
    pid_t worker=fork();
    if(worker<0){int error=fs1_error();(void)fo_publish(helper,1,5,0,error);return 113;}
    if(!worker) {
        /* Fail the race between fork, parent death and PDEATHSIG setup. */
        if(prctl(PR_SET_PDEATHSIG,SIGKILL) || !fo_parent_ok())_exit(114);
        int result=fo_guard();if(!result)result=work(argc,argv);
        fo_set(FO_RESULT,(unsigned)result);fo_phase(FO_FINISHED);fo_set(FO_DONE,1);
        _exit(result?1:0);
    }
#ifdef S22_AUTOBOOT_TRACE
    at_select(5);
#endif
    (void)fo_publish(helper,1,0,0,0);
    for(;;) {
        int status=0;pid_t got=waitpid(worker,&status,WNOHANG);
        if(got==worker) {
            unsigned outcome=WIFEXITED(status)?1:WIFSIGNALED(status)?2:5;
            uint64_t finished=fo_now();int boundary=finished==UINT64_MAX?EIO:finished>=fo_deadline?ETIMEDOUT:0;
            (void)fo_publish(helper,2,outcome,(unsigned)status,boundary);
            int result=!boundary && outcome==1 && WEXITSTATUS(status)==0 &&
                atomic_load(&fo_state->field[FO_DONE])==1 &&
                atomic_load(&fo_state->field[FO_RESULT])==0?0:1;
#ifdef S22_AUTOBOOT_TRACE
            at_emit(AT_WAIT_RESULT,4,3,result,(unsigned)boundary,(unsigned)worker,(unsigned)status,
                atomic_load(&fo_state->field[FO_DONE]),atomic_load(&fo_state->field[FO_RESULT]));
#endif
            (void)munmap(fo_state,sizeof(*fo_state));fo_state=NULL;return result;
        }
        int error=got<0 && errno!=EINTR?fs1_error():0;
        now=fo_now();if(now==UINT64_MAX && !error)error=EIO;
        if(error || now>=fo_deadline) {
            atomic_store(&fo_state->stop,1);
            (void)fo_publish(helper,2,error?4:3,0,error);
            /* Never release the shell to its next helper after pending state.
             * No signal asserts cancellation of a blocked module syscall. */
#ifdef S22_AUTOBOOT_TRACE
            at_emit(AT_WAIT_STOP,4,3,-1,(unsigned)(error?error:ETIMEDOUT),(unsigned)worker,0,0,0);
#endif
            fo_park();
        }
        struct timespec delay={0,10000000};
        if(nanosleep(&delay,NULL) && errno!=EINTR) {
            error=fs1_error();atomic_store(&fo_state->stop,1);
            (void)fo_publish(helper,2,4,0,error);
#ifdef S22_AUTOBOOT_TRACE
            at_emit(AT_WAIT_STOP,4,3,-1,(unsigned)error,(unsigned)worker,0,0,0);
#endif
            fo_park();
        }
    }
}
#endif
