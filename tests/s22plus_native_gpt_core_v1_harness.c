/* Pure memory I/O faults around the actual prospective GPT core. H0 only. */
#define _GNU_SOURCE
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>
#include "../workspace/public/src/native-init/s22plus_native_gpt_core_v1.h"

static uint8_t original[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)));
static uint8_t proposed[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)));
static uint8_t current[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)));
static uint8_t work[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)));
static uint8_t expected[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)));
struct model { unsigned reads,writes,syncs,events; int fail_write,fail_sync,fail_read;
    unsigned cut,wrong_read; uint64_t written[4]; };
static struct model model;
static int read_model(void *ctx, uint8_t *out) {
    struct model *m=ctx;
    unsigned ordinal=m->reads++;
    if ((int)ordinal==m->fail_read) return -1;
    memcpy(out,current,GPT1_BYTES);
    if (m->wrong_read && ordinal) out[0]^=1;
    return 0;
}
static int write_model(void *ctx,uint64_t lba,const uint8_t *data) {
    struct model *m=ctx;
    assert(m->writes<4 && (uintptr_t)data%GPT1_BLOCK==0);
    unsigned index=4;
    for (unsigned i=0;i<4;i++) if(lba==gpt1_lbas[i]) index=i;
    assert(index<4);
    unsigned ordinal=m->writes++;
    m->written[ordinal]=lba;
    if ((int)ordinal==m->fail_write) {
        assert(m->cut<=GPT1_BLOCK);
        memcpy(current+gpt1_offsets[index],data,m->cut);
        return -1;
    }
    memcpy(current+gpt1_offsets[index],data,GPT1_BLOCK);
    return 0;
}
static int sync_model(void *ctx) {
    struct model *m=ctx;
    return (int)m->syncs++==m->fail_sync ? -1 : 0;
}
static void event_model(void *ctx,unsigned event,unsigned ordinal,uint64_t lba) {
    struct model *m=ctx;
    assert(event>=GPT1_INTENT && event<=GPT1_SKIP && ordinal<4);
    assert(lba==gpt1_lbas[0] || lba==gpt1_lbas[1] || lba==gpt1_lbas[2] || lba==gpt1_lbas[3]);
    assert(++m->events<=8);
}
static struct gpt1_io io={&model,read_model,write_model,sync_model,event_model};
static void reset_model(void) {
    memset(&model,0,sizeof(model));
    model.fail_write=model.fail_sync=model.fail_read=-1;
}
static enum gpt1_error execute(enum gpt1_mode mode,struct gpt1_result *r) {
    return gpt1_execute(mode,&io,original,proposed,work,expected,r);
}
static void restored(void) {
    struct gpt1_result r;
    reset_model();
    assert(execute(GPT1_RESTORE,&r)==GPT1_OK);
    assert(!memcmp(current,original,GPT1_BYTES) && r.final_kind==1);
    assert(r.writes_attempted==r.writes_completed && r.writes_completed<=4);
}
static void input(const char *path,uint8_t *out) {
    int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    assert(fd>=0);
    struct stat st;
    assert(!fstat(fd,&st) && S_ISREG(st.st_mode) && st.st_nlink==1 && st.st_size==GPT1_BYTES);
    size_t used=0;
    while(used<GPT1_BYTES) { ssize_t n=read(fd,out+used,GPT1_BYTES-used);assert(n>0);used+=(size_t)n; }
    assert(!close(fd));
}
int main(int argc,char **argv) {
    assert(argc==3);
    input(argv[1],original);input(argv[2],proposed);
    assert(memcmp(original,proposed,GPT1_BYTES));
    assert(gpt1_scope(proposed,original,proposed));
    struct gpt1_result r;
    unsigned faults=0,mixed=0,restore_faults=0;
    memcpy(current,original,GPT1_BYTES);reset_model();
    assert(execute(GPT1_APPLY,&r)==GPT1_OK && r.writes_completed==4 && r.final_kind==2);
    assert(!memcmp(current,proposed,GPT1_BYTES));
    reset_model();assert(execute(GPT1_APPLY,&r)==GPT1_NOT_ORIGINAL && !model.writes);
    restored();reset_model();assert(execute(GPT1_RESTORE,&r)==GPT1_OK && !model.writes && r.skipped==4);
    /* Every distinct prefix cut in each serial four-block application stops
     * after one failed call. Fresh one-shot restoration preserves a survivor. */
    for(unsigned ordinal=0;ordinal<4;ordinal++) {
        unsigned off=gpt1_offsets[ordinal];
        for(unsigned cut=0;cut<=GPT1_BLOCK;cut++) {
            if(cut && cut<GPT1_BLOCK && original[off+cut-1]==proposed[off+cut-1]) continue;
            memcpy(current,original,GPT1_BYTES);reset_model();
            model.fail_write=(int)ordinal;model.cut=cut;
            assert(execute(GPT1_APPLY,&r)==GPT1_WRITE);
            assert(model.writes==ordinal+1 && r.writes_completed==ordinal);
            assert(gpt1_scope(current,original,proposed));
            assert(gpt1_copies(current,original,proposed,&r));
            unsigned primary=r.primary_kind;
            restored();
            if(!primary) assert(model.written[0]==3 || model.written[0]==1);
            faults++;
        }
        memcpy(current,original,GPT1_BYTES);reset_model();model.fail_sync=(int)ordinal;
        assert(execute(GPT1_APPLY,&r)==GPT1_SYNC && model.writes==ordinal+1);
        restored();faults++;
    }
    /* Every mixed firmware-prefix state in either direction is independently
     * restorable, including a bad primary with the backup as its sole copy. */
    for(unsigned direction=0;direction<2;direction++) {
        const uint8_t *before=direction?proposed:original,*after=direction?original:proposed;
        for(unsigned ordinal=0;ordinal<4;ordinal++) {
            unsigned off=gpt1_offsets[ordinal];
            for(unsigned cut=0;cut<=GPT1_BLOCK;cut++) {
                if(cut && cut<GPT1_BLOCK && before[off+cut-1]==after[off+cut-1]) continue;
                memcpy(current,before,GPT1_BYTES);
                for(unsigned done=0;done<ordinal;done++)
                    memcpy(current+gpt1_offsets[done],after+gpt1_offsets[done],GPT1_BLOCK);
                memcpy(current+off,after+off,cut);
                assert(gpt1_copies(current,original,proposed,&r));
                restored();mixed++;
            }
        }
    }
    /* Compact regression for interruption of restoration itself, from both
     * complete proposal and sole-backup states. Each failure stops this call;
     * a separate memory-only recovery verifies the remaining source. */
    uint8_t restore_start[GPT1_BYTES];
    for(unsigned state=0;state<2;state++) {
        memcpy(restore_start,proposed,GPT1_BYTES);
        if(state) memcpy(restore_start+GPT1_BLOCK,original+GPT1_BLOCK,GPT1_BLOCK);
        memcpy(current,restore_start,GPT1_BYTES);restored();
        unsigned count=model.writes;
        for(unsigned ordinal=0;ordinal<count;ordinal++) {
            const unsigned cuts[]={0,7,512,GPT1_BLOCK};
            for(unsigned i=0;i<4;i++) {
                memcpy(current,restore_start,GPT1_BYTES);reset_model();
                model.fail_write=(int)ordinal;model.cut=cuts[i];
                assert(execute(GPT1_RESTORE,&r)==GPT1_WRITE && model.writes==ordinal+1);
                assert(gpt1_copies(current,original,proposed,&r));
                restored();restore_faults++;
            }
            memcpy(current,restore_start,GPT1_BYTES);reset_model();model.fail_sync=(int)ordinal;
            assert(execute(GPT1_RESTORE,&r)==GPT1_SYNC && model.writes==ordinal+1);
            assert(gpt1_copies(current,original,proposed,&r));
            restored();restore_faults++;
        }
    }
    memcpy(current,original,GPT1_BYTES);reset_model();model.fail_read=0;
    assert(execute(GPT1_APPLY,&r)==GPT1_READ && !model.writes);
    memcpy(current,original,GPT1_BYTES);reset_model();model.fail_read=1;
    assert(execute(GPT1_APPLY,&r)==GPT1_READ && model.writes==1);restored();
    memcpy(current,original,GPT1_BYTES);reset_model();model.wrong_read=1;
    assert(execute(GPT1_APPLY,&r)==GPT1_READBACK && model.writes==1);restored();
    /* An unrelated byte inside a mutable block is outside recovery scope. */
    memcpy(current,proposed,GPT1_BYTES);current[GPT1_BLOCK+8]^=1;reset_model();
    assert(execute(GPT1_RESTORE,&r)==GPT1_OUTSIDE && !model.writes);
    memcpy(current,proposed,GPT1_BYTES);current[0]^=1;reset_model();
    assert(execute(GPT1_RESTORE,&r)==GPT1_OUTSIDE && !model.writes);
    /* CRC-field tears in both copies have no exact surviving source. */
    memcpy(current,proposed,GPT1_BYTES);
    for(unsigned side=0;side<2;side++) {
        unsigned start=side?GPT1_PRIMARY:0,end=side?GPT1_BYTES:GPT1_PRIMARY;
        for(unsigned i=start;i<end;i++) if(original[i]!=proposed[i]) {
            unsigned v=0;while(v==original[i] || v==proposed[i])v++;
            current[i]=(uint8_t)v;break;
        }
    }
    reset_model();assert(execute(GPT1_RESTORE,&r)==GPT1_NO_COPY && !model.writes);
    printf("PASS apply_write_and_sync_faults=%u mixed_state_restores=%u restore_faults=%u negative_paths=6 device_effects=0\n",faults,mixed,restore_faults);
    return 0;
}
