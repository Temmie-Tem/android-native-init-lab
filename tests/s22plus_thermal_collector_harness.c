#define _GNU_SOURCE
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static uint64_t test_now=2000;
static char test_sample[512];
static int test_clock(clockid_t id,struct timespec *out){
    assert(id==CLOCK_BOOTTIME);out->tv_sec=test_now/1000;out->tv_nsec=test_now%1000*1000000;return 0;
}
#define clock_gettime test_clock
#define main renderer_main
#undef _POSIX_C_SOURCE /* generated source declares the target's libc level */
#include "renderer.c"
#undef main
#undef clock_gettime
static int status_read(const char *path,char *out,size_t capacity,long fs){
    assert(!strcmp(path,"/sys/module/s22plus_thermal_telemetry/parameters/sample")&&fs==0x62656572L);
    size_t n=strlen(test_sample);assert(n<capacity);memcpy(out,test_sample,n+1);return 1;
}
int main(int argc,char **argv){
    assert(argc==2&&fgets(test_sample,sizeof(test_sample),stdin));
    assert(getchar()==EOF);
    struct resident_cpu_map map={0};
    struct status_metrics m={.magic=RESIDENT_SAMPLE_MAGIC,.source=1,.sequence=1,.collected_ms=1000};
    if(!strcmp(argv[1],"stale"))test_now=7001;
    if(!strcmp(argv[1],"future"))test_now=1000;
    if(!strcmp(argv[1],"before"))m.collected_ms=1001;
    resident_cpu_temperature(&map,&m);
    if(!strcmp(argv[1],"repeat")){
        m=(struct status_metrics){.magic=RESIDENT_SAMPLE_MAGIC,.source=1,.sequence=2,.collected_ms=1000};
        resident_cpu_temperature(&map,&m);
    }
    if(!strcmp(argv[1],"frame")){
        struct hud_snapshot v={.magic=RESIDENT_VIEW_MAGIC,.state=3,.sequence=1,.uptime_ms=2000};
        m.valid|=224;m.gauge_sequence=1;m.gauge_ms=1000;m.gauge_soc_permille=500;
        m.gauge_voltage_uv=4000000;m.gauge_current_ua=-100000;
        v.sample[1]=m;v.source_state[0]=v.source_state[1]=RS_RUNNING;
        v.sample[0]=(struct status_metrics){.sequence=1,.collected_ms=1000,.valid=3};
        resident_view=v;hud_record(&v);return 0;
    }
    printf("valid=%u mask=%u cpu_mc=%d battery_deci=%d\n",m.valid,m.cpu_mask,m.cpu_temp_mc,m.battery_temp_deci);
    return 0;
}
