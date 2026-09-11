/* Sysfs/procfs, clock and output endpoints are fixtures. All sensor selection,
 * parsing, sampling, range/freshness and provider conversions are production. */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/vfs.h>
#include <unistd.h>
static uint64_t fixture_clock=1000,fixture_sent,fixture_proc_reads,fixture_sys_reads;
static const char *scenario;
static int real_output;
static int metrics_clock(clockid_t,struct timespec *);
static int metrics_open(const char *,int,...);
static ssize_t metrics_read(int,void *,size_t);
static int metrics_close(int);
static int metrics_fs(int,struct statfs *);
static int metrics_sleep(const struct timespec *,struct timespec *);
static ssize_t metrics_send(int,const void *,size_t,int);
#define open metrics_open
#define read metrics_read
#define close metrics_close
#define fstatfs metrics_fs
#define nanosleep metrics_sleep
#define clock_gettime metrics_clock
#define send metrics_send
#define main renderer_main
#undef _POSIX_C_SOURCE /* host libc selected a newer level; generated source declares its own */
#include "renderer.c"
#undef main
#undef send
#undef clock_gettime
#undef nanosleep
#undef fstatfs
#undef close
#undef read
#undef open
#include "telemetry_core.h"
static unsigned bus_calls;
static int fixed_byte_test(void *unused,unsigned address,unsigned reg) {
    (void)unused;assert(address==0x66 && reg<=1);return reg?2:0x15;
}
static int fixed_word_test(void *unused,unsigned address,unsigned reg) {
    (void)unused;assert(address==0x36);bus_calls++;
    if(!strcmp(scenario,"gauge-error") && bus_calls==4)return -EIO;
    switch(reg){case 6:return 12800;case 9:return 51200;case 10:return 65408;default:assert(0);return 0;}
}
static const struct s22_telemetry_ops gauge_ops={fixed_byte_test,fixed_word_test};
static struct s22_telemetry_state gauge_state;
static int metrics_clock(clockid_t id,struct timespec *out) {
    assert(id==CLOCK_BOOTTIME);
    if(real_output)return clock_gettime(id,out);
    out->tv_sec=fixture_clock/1000;out->tv_nsec=fixture_clock%1000*1000000;return 0;
}
static int metrics_open(const char *path,int flags,...) {
    assert(!strcmp(path,"/proc/stat"));
    assert(flags==(O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK));return 9001;
}
static ssize_t metrics_read(int fd,void *out,size_t n) {
    assert(fd==9001);fixture_proc_reads++;
    int size=snprintf(out,n,"cpu %llu 0 %llu %llu 0 0 0 0\n",(unsigned long long)fixture_proc_reads*3,
        (unsigned long long)fixture_proc_reads,(unsigned long long)fixture_proc_reads*6);
    assert(size>0 && (size_t)size<n);return size;
}
static int metrics_fs(int fd,struct statfs *out){assert(fd==9001);memset(out,0,sizeof(*out));out->f_type=0x9fa0L;return 0;}
static int metrics_close(int fd){assert(fd==9001);return 0;}
static int metrics_sleep(const struct timespec *delay,struct timespec *remain) {
    assert(delay->tv_sec==1 && !delay->tv_nsec);
    if(real_output)return nanosleep(delay,remain);
    fixture_clock+=1000;return 0;
}
static int status_read(const char *path,char *out,size_t cap,long fs) {
    int size=-1;
    if(!strcmp(path,"/proc/meminfo")){
        assert(fs==0x9fa0L);size=snprintf(out,cap,"MemTotal: 8192000 kB\nMemAvailable: 4096000 kB\n");
    }else {
        assert(fs==0x62656572L);fixture_sys_reads++;
        if(strstr(path,"/battery/"))return 0;
        if(strstr(path,"/parameters/sample")){
            struct s22_telemetry_sample sample;s22_telemetry_read(&gauge_state,&gauge_ops,NULL,&sample);
            uint64_t stamp;assert(resident_clock(&stamp));
            size=snprintf(out,cap,"S22FGR1 seq=%llu start_ms=%llu valid=%u error=%d soc_raw=%u voltage_raw=%u current_raw=%u soc_permille=%u voltage_uv=%u current_ua=%d\n",
                sample.sequence,(unsigned long long)stamp,sample.valid,sample.error,sample.soc_raw,sample.voltage_raw,
                sample.current_raw,sample.soc_permille,sample.voltage_uv,sample.current_ua);
        }else {
            unsigned zone;char part[32];
            assert(sscanf(path,"/sys/class/thermal/thermal_zone%u/%31s",&zone,part)==2);
            if(!strcmp(scenario,"cpu-absent"))return 0;
            if(!strcmp(scenario,"cpu-duplicate") && zone==13)size=snprintf(out,cap,"%s",resident_cpu_types[0]);
            else if(zone>=13)return 0;
            else if(!strcmp(part,"type")){
                if(!strcmp(scenario,"cpu-wrong-type"))size=snprintf(out,cap,"battery\n");
                else if(!strcmp(scenario,"cpu-type-changed") && fixture_sent)size=snprintf(out,cap,"skin\n");
                else size=snprintf(out,cap,"%s",resident_cpu_types[zone]);
            }else {
                assert(!strcmp(part,"temp"));
                if(!strcmp(scenario,"cpu-malformed"))size=snprintf(out,cap,"48 C\n");
                else if(!strcmp(scenario,"cpu-range"))size=snprintf(out,cap,"150001\n");
                else if(!strcmp(scenario,"cpu-negative"))size=snprintf(out,cap,"-%u\n",5000+zone);
                else size=snprintf(out,cap,"%u\n",40000+1000*zone);
            }
        }
    }
    assert(size>0 && (size_t)size<cap);return 1;
}
static ssize_t metrics_send(int fd,const void *data,size_t size,int flags) {
    assert(fd==1 && size==sizeof(struct status_metrics) && flags==(MSG_DONTWAIT|MSG_NOSIGNAL));
    const struct status_metrics *m=data;fixture_sent++;
    assert(m->sequence==fixture_sent);
    static struct status_metrics previous;
    uint64_t now;assert(resident_clock(&now));
    assert(resident_sample_valid(m,&previous,m->source,now,m->run));previous=*m;
    if(!m->source){assert(!fixture_sys_reads && (m->valid&STATUS_MEM));if(fixture_sent>1)assert(m->cpu_permille==400);}
    else {
        assert(!fixture_proc_reads && m->cpu_expected==13);
        if(!strncmp(scenario,"cpu-",4) && strcmp(scenario,"cpu-duplicate") && strcmp(scenario,"cpu-negative") &&
           (strcmp(scenario,"cpu-type-changed") || fixture_sent>1))assert(!(m->valid&STATUS_CPU_TEMP));
        else if(!strcmp(scenario,"cpu-negative"))assert(m->cpu_temp_mc==-5000 && m->cpu_mask==8191);
        else if(!strcmp(scenario,"cpu-duplicate"))assert(m->cpu_temp_mc==52000 && m->cpu_mask==8190);
        else assert(m->cpu_temp_mc==52000 && m->cpu_mask==8191);
        if(!strcmp(scenario,"gauge-error") && fixture_sent>1){assert(!(m->valid&224));assert(bus_calls==4);}
        else assert((m->valid&224)==224 && m->gauge_sequence==fixture_sent);
    }
    if(real_output)return send(fd,data,size,flags);
    unsigned target=!strcmp(scenario,"long")?100000:4;
    if(fixture_sent==target){fprintf(stderr,"PASS actual collector samples=%llu ms=%llu cpu_mask=%u source=%u\n",
        (unsigned long long)fixture_sent,(unsigned long long)now,m->cpu_mask,m->source);exit(0);}
    return (ssize_t)size;
}
int main(int argc,char **argv) {
    assert(argc==3);scenario=argv[2];real_output=!strcmp(scenario,"ipc");
    assert(s22_telemetry_identity(&gauge_ops,NULL)==0);
    if(!strcmp(scenario,"log-backpressure")) {
        int pipefd[2];assert(pipe2(pipefd,O_NONBLOCK|O_CLOEXEC)==0);int saved=dup(2);assert(saved>=0);
        assert(dup2(pipefd[1],2)==2);char data[512];memset(data,'x',sizeof(data));
        while(write(pipefd[1],data,sizeof(data))==(ssize_t)sizeof(data)){}
        assert(errno==EAGAIN);resident_diagnostic_write("DROP\n",5);assert(resident_diagnostic_dropped==1);
        assert(read(pipefd[0],data,sizeof(data))==(ssize_t)sizeof(data));
        /* Drain the pipe before a new complete sub-PIPE_BUF record. */
        while(read(pipefd[0],data,sizeof(data))>0){}
        resident_diagnostic_write("RESUMED\n",8);assert(resident_diagnostic_dropped==1);
        assert(read(pipefd[0],data,sizeof(data))==8 && !memcmp(data,"RESUMED\n",8));
        assert(dup2(saved,2)==2);close(saved);close(pipefd[0]);close(pipefd[1]);
        puts("PASS bounded renderer diagnostic loss accounting and resumed delivery");return 0;
    }
    if(!strcmp(scenario,"provider-overflow")) {
        gauge_state.attempts=~0ULL-1;struct s22_telemetry_sample m;
        s22_telemetry_read(&gauge_state,&gauge_ops,NULL,&m);assert(!m.error && m.sequence==~0ULL && bus_calls==3);
        s22_telemetry_read(&gauge_state,&gauge_ops,NULL,&m);assert(m.error==-EOVERFLOW && bus_calls==3);
        puts("PASS provider counter exhausts before wrap or extra bus read");return 0;
    }
    return status_collect("42424242424242424242424242424242",(unsigned)atoi(argv[1]));
}
