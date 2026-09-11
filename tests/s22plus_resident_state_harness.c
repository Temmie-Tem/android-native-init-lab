/* Appended to the production PID1/host syscall join, not a state model. */
static void resident_test_empty_hud(struct hud1_state *h) {
    memset(h,0,sizeof(*h));h->input=h->output=h->log=h->metrics[0]=h->metrics[1]=-1;
}
int main(int argc,char **argv) {
    assert(argc==3);fx_owner_pid=getpid();
    setenv("RC1_WORK",argv[1],1);setenv("P364_MARK","/dev/null",1);setenv("P364_CASE",argv[2],1);
    assert(fcntl(0,F_GETFD)>=0);
    if(!strcmp(argv[2],"root-dir") || !strcmp(argv[2],"root-mount")) {
        assert(local_begin()==0);local_service();local_close();
        assert(local_display.hud.input==-1 && local_display.hud.output==-1 && local_display.hud.log==-1);
        assert(local_display.hud.metrics[0]==-1 && local_display.hud.metrics[1]==-1);
        assert(fcntl(0,F_GETFD)>=0);puts("PASS failed setup keeps fd0 and absent child slots");return 0;
    }
    if(!strcmp(argv[2],"ring")) {
        struct hud1_state *h=&local_display.hud;resident_test_empty_hud(h);
        struct resident_log *r=&h->retained;
        for(unsigned i=0;i<100000;i++) {
            char row[80];int n=snprintf(row,sizeof(row),"EVENT sequence=%u\n",i+1);
            resident_log_feed(r,row,5);resident_log_feed(r,row+5,(unsigned)n-5);
        }
        assert(r->count==64 && r->last==100000 && r->evicted==99936 && !r->dropped && !r->exhausted);
        char over[1024];memset(over,'x',sizeof(over));resident_log_feed(r,over,sizeof(over));resident_log_feed(r,"\n",1);
        assert(r->dropped==1 && r->count==64);
        resident_log_feed(r,"partial",7);resident_log_eof(r);assert(r->dropped==2 && !r->used);
        resident_log_feed(r,"held",4);assert(r->used==4);
        h->log=(int)sys_openat("/s22-root-work/hud.log",00000001|00000100|00000200|0100000|02000000,0400);
        assert(h->log>=0);resident_export(h);assert(h->log>=0);sys_close(h->log);
        r->last=RESIDENT_U64_MAX;resident_log_feed(r,"wrap\n",5);assert(r->exhausted && r->last==RESIDENT_U64_MAX);
        puts("PASS bounded complete-record retention, export and counter exhaustion");return 0;
    }
    local_display.started=1;local_display.owner=1;resident_test_empty_hud(&local_display.hud);
    assert(rc1_now(&local_display.start)==0);local_display.last=local_display.start;
    if(!strcmp(argv[2],"ipc")) {
        struct hud1_state *h=&local_display.hud;int pair[2];assert(socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_NONBLOCK|SOCK_CLOEXEC,0,pair)==0);
        h->metrics[0]=pair[0];h->state[0]=RS_RUNNING;
        uint64_t sequences[]={1,601,602,900,901,3600,86400,0xffffffffULL,0x100000000ULL,RESIDENT_U64_MAX};
        for(unsigned i=0;i<sizeof(sequences)/sizeof(sequences[0]);i++) {
            uint64_t collected=0;assert(rc1_now(&collected)==0 && collected>0);
            struct status_metrics m={.magic=RESIDENT_SAMPLE_MAGIC,.sequence=sequences[i],.source=0,.valid=3,
                .collected_ms=collected,.mem_total_kib=8192000,.mem_available_kib=4096000,.cpu_permille=400};
            memcpy(m.run,p328_run_id_bytes,16);assert(send(pair[1],&m,sizeof(m),MSG_NOSIGNAL)==sizeof(m));
            /* The producer timestamp follows the tick instant but precedes
             * recv completion: a legitimate concurrent arrival, not future data. */
            hud1_tick(h,collected-1,3);assert(h->sample[0].sequence==sequences[i] && h->state[0]==RS_RUNNING);
        }
        assert(resident_valid(&h->sample[0],h->state[0],h->sample[0].collected_ms+6001)==0);
        struct status_metrics invalid=h->sample[0];invalid.sequence=0;
        assert(send(pair[1],&invalid,sizeof(invalid),MSG_NOSIGNAL)==sizeof(invalid));hud1_tick(h,7001,3);
        assert(h->state[0]==RS_FAULT && h->metrics[0]==-1 && h->sample[0].sequence==RESIDENT_U64_MAX);
        close(pair[1]);puts("PASS real IPC wide sequence, stale retention and no-wrap fault");return 0;
    }
    if(!strcmp(argv[2],"lifecycle")) {
        fx_clock_offset_ms=86400000ULL*30;local_service();
        assert(!local_display.terminal && !local_display.stopped);
        baseline_sessions=RESIDENT_U64_MAX-1;assert(baseline_admit()==0);
        uint8_t nonce[32]={0};assert(baseline_nonce(nonce)==0);
        for(unsigned i=24;i<32;i++)assert(nonce[i]==255);
        assert(baseline_admit()<0 && baseline_sessions==RESIDENT_U64_MAX);
        local_finish(7);assert(local_display.terminal && !local_display.stopped);
        local_phase(0);assert(local_display.phase==7 && baseline_check()<0);
        struct resident_child *c=&local_display.hud.child[1];c->pid=RESIDENT_FIXTURE_STUCK_PID;
        for(unsigned i=0;i<100000;i++)local_service();assert(c->pid==RESIDENT_FIXTURE_STUCK_PID && !c->reaped && !c->unknown);
        hud1_stop(&local_display.hud);assert(c->signalled && !c->reaped);
        for(unsigned i=0;i<100000;i++)resident_reap(c);assert(c->pid==RESIDENT_FIXTURE_STUCK_PID && !c->reaped);
        c->pid=RESIDENT_FIXTURE_UNKNOWN_PID;c->signalled=0;resident_reap(c);assert(c->unknown && !c->reaped);
        hud1_stop(&local_display.hud);assert(!c->signalled);
        puts("PASS month-scale service, irreversible command stop and retained unreaped slots");return 0;
    }
    assert(0);return 1;
}
