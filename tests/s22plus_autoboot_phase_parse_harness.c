/* H0 only: execute the actual bounded target text decoders, no kernel effects. */
#define _GNU_SOURCE
#include <assert.h>
#include <stdio.h>
#include "s22plus_autoboot_phase_seal_v1.h"
#include "s22plus_autoboot_phase_parse_v1.h"
int main(int argc,char **argv) {
    assert(argc>=2);char text[16384];size_t n=fread(text,1,sizeof(text)-1,stdin);
    assert(!ferror(stdin) && n<sizeof(text)-1);text[n]=0;
    int error;
    if(!strcmp(argv[1],"trace")) {
        struct ap_event e={0};error=ap_trace_line(text,&e);
        printf("%d %llu %u %u %u %d %d\n",error,(unsigned long long)e.usec,e.id,e.pid,e.cpu,e.target,e.rc);
    } else if(!strcmp(argv[1],"packet")) {
        struct ap_packet p={0};error=ap_packet_parse(text,&p);
        printf("%d %u %u %u %d\n",error,p.sequence,p.id,(unsigned char)p.kind,p.result);
    } else if(!strcmp(argv[1],"profile")) {
        unsigned counts[AP_PROBE_COUNT]={0},mask=0;uint64_t hits=0,missed=0;
        if(argc==3)counts[0]=(unsigned)strtoul(argv[2],NULL,10);
        error=ap_profile_parse(text,counts,&mask,&hits,&missed);
        printf("%d %u %llu %llu\n",error,mask,(unsigned long long)hits,(unsigned long long)missed);
    } else {
        assert(!strcmp(argv[1],"stats"));uint64_t a=0,b=0,c=0,remaining=0;
        error=ap_stats_parse(text,&a,&b,&c,&remaining);
        printf("%d %llu %llu %llu\n",error,(unsigned long long)a,(unsigned long long)b,(unsigned long long)c);
    }
    return 0;
}
