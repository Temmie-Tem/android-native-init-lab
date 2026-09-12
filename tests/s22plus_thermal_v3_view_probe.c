/* Exercise the actual generated renderer snapshot reader with equal-size IPC. */
#define _GNU_SOURCE
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static int test_clock(clockid_t id,struct timespec *out) {
    assert(id==CLOCK_MONOTONIC || id==CLOCK_BOOTTIME);
    out->tv_sec=2;out->tv_nsec=0;return 0;
}
#define clock_gettime test_clock
#define main renderer_main
#undef _POSIX_C_SOURCE
#include "view-renderer.c"
#undef main
#undef clock_gettime
int main(int argc,char **argv) {
    assert(argc>=2);run_id=TEST_RUN;
    if(!strcmp(argv[1],"emit")) {
        struct hud_snapshot v={.magic=RESIDENT_VIEW_MAGIC,.state=3,.sequence=1,.uptime_ms=1000};
        for(unsigned i=0;i<16;i++) {
            unsigned byte;assert(sscanf(run_id+2*i,"%2x",&byte)==1);v.run[i]=(uint8_t)byte;
        }
        assert(fwrite(&v,1,sizeof(v),stdout)==sizeof(v));return 0;
    }
    assert(argc==3&&!strcmp(argv[1],"receive"));
    assert(dup2(atoi(argv[2]),STDIN_FILENO)==STDIN_FILENO);
    struct hud_snapshot v={0};assert(hud_snapshot_read(&v)==1);
    puts("ACCEPT");return 0;
}
