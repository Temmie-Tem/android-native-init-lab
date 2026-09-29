/* Called only by the real native PID1 after its fixed terminal ACK is fully
 * flushed. No return from here can reenter resident/console service. */
static __attribute__((noreturn)) void sw_parent_park(void) {for(;;)p282_poll_delay();}
static __attribute__((noreturn)) void sw_parent_exec(struct rc1_state *s) {
    struct sw_state state={0};uint64_t now=0;
    if(!local_owner() || s->active || s->pid || s->blocked!=1 || s->control!=4 ||
       s->control_seq!=SW_SEQUENCE || s->next!=SW_SEQUENCE+1 || s->qcount || s->flags ||
       s->overload || s->fault_sent || local_display.abandoned_command.pid ||
       rc1_now(&now) || now>s->start+600000U || s->start+600000U-now<SW_TIMEOUT_MS)sw_parent_park();
    state.magic=SW_STATE_MAGIC;state.version=SW_STATE_VERSION;state.sequence=SW_SEQUENCE;
    state.deadline_ms=s->control_start+SW_TIMEOUT_MS;
    if(now>=state.deadline_ms)sw_parent_park();
    memcpy(state.run,p328_run_id_bytes,16);memcpy(state.nonce,s->nonce,32);
    if(@@NAMESPACE@@_kernel_boot_id(state.boot))sw_parent_park();
    for(unsigned i=0;i<3;++i) {
        struct resident_child *child=&local_display.hud.child[i];
        if(child->pid<=1 || child->pid>0x7fffffffL || child->unknown)sw_parent_park();
        state.child[i]=(struct sw_child_state){(int32_t)child->pid,child->reaped,child->status,child->unknown};
    }
    /* Stop all service ticks before transferring ownership of these children. */
    local_display.stopped=local_display.terminal=1;
    long tty=syscall6(25,s->fd,1030,32,0,0,0); /* F_DUPFD_CLOEXEC */
    long original=syscall6(279,(long)(uintptr_t)"s22-switch-state",3,0,0,0,0);
    if(tty<5 || original<0)sw_parent_park();
    long memory=syscall6(25,original,1030,32,0,0,0);
    if(memory<5 || sys_close((int)original))sw_parent_park();
    original=sys_openat("/dev/null",O_CLOEXEC,0);
    if(original<0)sw_parent_park();
    long null=syscall6(25,original,1030,32,0,0,0);
    if(null<5 || sys_close((int)original))sw_parent_park();
    if(sys_write((int)memory,&state,sizeof(state))!=(long)sizeof(state) ||
       syscall6(25,memory,1033,SW_MEMFD_SEALS,0,0,0)!=0)sw_parent_park(); /* F_ADD_SEALS */
    for(int i=0;i<3;++i)if(p328_dup_to((int)null,i)!=i)sw_parent_park();
    if(p328_dup_to((int)tty,3)!=3 || p328_dup_to((int)memory,4)!=4 ||
       syscall6(25,3,2,0,0,0,0)!=0 || syscall6(25,4,2,0,0,0,0)!=0 ||
       syscall6(436,5,0xffffffffU,0,0,0,0)<0)sw_parent_park();
    char *argv[]={"/s22-switch-root",NULL};char *env[]={"PATH=/bin","LC_ALL=C",NULL};
    (void)sys_execve(argv[0],argv,env);sw_parent_park();
}
