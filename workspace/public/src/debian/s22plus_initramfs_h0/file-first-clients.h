/* Six sealed synchronous module calls. A blocked kernel call needs physical
 * recovery; no userspace deadline is claimed to cancel it. */
#include "file-first-tail.h"
static int fl_present(unsigned index) {
#ifdef S22_ROOT_INSPECT_VIRT_TEST
    extern unsigned fl_test_inserted;
    return index<fl_test_inserted;
#else
    char path[128];struct stat st;
    int n=snprintf(path,sizeof(path),"/sys/module/%s",fl_clients[index].name);
    if(n<=0 || (size_t)n>=sizeof(path))return -1;
    if(!lstat(path,&st))return S_ISDIR(st.st_mode) && st.st_uid==0 ? 1:-1;
    return errno==ENOENT ? 0:-1;
#endif
}
#ifdef S22_ROOT_INSPECT_VIRT_TEST
unsigned fl_test_inserted;
#endif
static int fl_clients_check(void) {
    for(unsigned i=0;i<FF_CLIENT_COUNT;++i) {
        if(fl_present(i)!=0)return EEXIST;
        int fd=fs1_pin_file(fl_clients[i].path,fl_clients[i].size,fl_clients[i].hash,false);
        if(fd<0)return fs1_error();
        if(close(fd))return fs1_error();
    }
    return 0;
}
static int fl_client(unsigned phase) {
    if(!phase || phase>FF_CLIENT_COUNT || fl_checker_pid || fl_unsettled)return EPROTO;
    int guard=fo_guard();if(guard)return guard;
    fo_module(FF_STORAGE_COUNT+phase);
    unsigned index=phase-1;
    for(unsigned i=0;i<FF_CLIENT_COUNT;++i)if(fl_present(i)!=(i<index))return EPROTO;
    int fd=fs1_pin_file(fl_clients[index].path,fl_clients[index].size,fl_clients[index].hash,false);
    if(fd<0)return fs1_error();
    int error=fl_time();
    if(!error) {
        fo_phase(FO_CALL_ARMED);
#ifdef S22_ROOT_INSPECT_VIRT_TEST
        char choice[32];error=fs1_read_text("/lab/client-fault",choice,sizeof(choice));
        if(!error && !strcmp(choice,"module-error\n") && phase==3)error=EIO;
        else if(!error && strcmp(choice,"none\n") && strcmp(choice,"module-error\n"))error=EINVAL;
        if(!error)++fl_test_inserted;
        fo_call(error?-1:0,error);
#else
        _Static_assert(SYS_finit_module==273,"ARM64 module syscall");
        long rc=syscall(SYS_finit_module,fd,"",0);error=rc?fs1_error():0;
        fo_call(rc,error);
#endif
    }
    fo_phase(FO_CLOSE);int closed=close(fd),ce=closed?fs1_error():0;
    fo_close(ce);
    if(!error)error=ce;
    if(!error) {
        fo_phase(FO_PRESENCE_CHECK);int present=fl_present(index),pe=present==1?0:ENODEV;
        fo_presence(present,pe);error=pe;
    }
    return error;
}
