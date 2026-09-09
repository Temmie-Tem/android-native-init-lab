/* Fixed read-only system-status collector. Runs outside PID1 and DRM owner.
 * Native provider absence is unavailable, never evidence of zero usage. */
#include <ctype.h>
#include <limits.h>
#include <sys/vfs.h>
#define STATUS_MEM 1U
#define STATUS_CPU 2U
#define STATUS_CAP 4U
#define STATUS_CHARGE 8U
#define STATUS_TEMP 16U
#define STATUS_GAUGE_SOC 32U
#define STATUS_GAUGE_VOLTAGE 64U
#define STATUS_GAUGE_CURRENT 128U
struct status_metrics {
    uint32_t magic,sequence,valid,reserved;
    uint64_t collected_ms,mem_total_kib,mem_available_kib;
    uint32_t cpu_permille;
    int32_t battery_temp_deci;
    uint32_t battery_pct,charge;
    uint8_t run[16];
    uint64_t gauge_ms;
    uint32_t gauge_sequence,gauge_soc_permille,gauge_voltage_uv;
    int32_t gauge_current_ua;
};
_Static_assert(sizeof(struct status_metrics)==96,"metrics wire size");
struct status_cpu {uint64_t field[8];int valid;};
static int status_uint(const char **cursor,uint64_t *out) {
    const char *p=*cursor;uint64_t n=0;
    if(*p<'0'||*p>'9')return 0;
    do {unsigned d=(unsigned)(*p-'0');if(n>(UINT64_MAX-d)/10)return 0;n=n*10+d;++p;}while(*p>='0'&&*p<='9');
    *cursor=p;*out=n;return 1;
}
static int status_scalar(const char *p,int64_t *out) {
    int negative=*p=='-';if(negative)++p;uint64_t n;
    if(!status_uint(&p,&n)||n>INT64_MAX)return 0;
    if(*p=='\n')++p;
    if(*p)return 0;
    *out=negative?-(int64_t)n:(int64_t)n;return 1;
}
static int status_memory(const char *p,struct status_metrics *m) {
    unsigned seen=0;uint64_t values[2]={0};
    while(*p) {
        const char *end=strchr(p,'\n');if(!end)return 0;
        int key=!strncmp(p,"MemTotal:",9)?0:!strncmp(p,"MemAvailable:",13)?1:-1;
        if(key>=0) {
            if(seen&(1U<<key))return 0;
            seen|=1U<<key;
            const char *q=p+(key?13:9);while(q<end&&(*q==' '||*q=='\t'))++q;
            if(!status_uint(&q,&values[key]))return 0;
            while(q<end&&(*q==' '||*q=='\t'))++q;
            if(end-q!=2||memcmp(q,"kB",2))return 0;
        }
        p=end+1;
    }
    if(seen!=3||!values[0]||values[0]>(1ULL<<30)||values[1]>values[0])return 0;
    m->mem_total_kib=values[0];m->mem_available_kib=values[1];m->valid|=STATUS_MEM;return 1;
}
static int status_cpu_parse(const char *p,struct status_cpu *out) {
    struct status_cpu next={0};if(strncmp(p,"cpu ",4))return 0;p+=4;
    for(unsigned i=0;i<8;i++) {
        while(*p==' '||*p=='\t')++p;
        if(!status_uint(&p,&next.field[i]))return 0;
        if(*p!=' '&&*p!='\t'&&*p!='\n'&&*p)return 0;
    }
    /* guest counters, when present, are already included in user/nice. */
    unsigned extra=0;
    while(*p==' '||*p=='\t')++p;
    while(*p && *p!='\n') {
        uint64_t ignored;if(++extra>2||!status_uint(&p,&ignored))return 0;
        while(*p==' '||*p=='\t')++p;
    }
    if(*p!='\n')return 0;
    next.valid=1;*out=next;return 1;
}
static void status_cpu_sample(const char *text,struct status_cpu *previous,struct status_metrics *m) {
    struct status_cpu next={0};if(!status_cpu_parse(text,&next)){previous->valid=0;return;}
    if(previous->valid) {
        uint64_t total=0,idle=0;int valid=1;
        for(unsigned i=0;i<8;i++) {
            if(next.field[i]<previous->field[i]){valid=0;break;}
            uint64_t delta=next.field[i]-previous->field[i];
            if(delta>UINT64_MAX-total){valid=0;break;}total+=delta;
            if(i==3||i==4)idle+=delta;
        }
        if(valid&&total&&total<=UINT64_MAX/1000) {
            m->cpu_permille=(uint32_t)((total-idle)*1000/total);m->valid|=STATUS_CPU;
        }
    }
    *previous=next;
}
static int status_read(const char *path,char *text,size_t capacity,long filesystem) {
    int f=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);if(f<0)return 0;
    struct statfs fs;int okay=0;size_t used=0;
    if(fstatfs(f,&fs)||fs.f_type!=filesystem)goto done;
    while(used<capacity-1) {
        ssize_t n=read(f,text+used,capacity-1-used);
        if(n<0)goto done;
        if(!n){okay=1;break;}
        used+=(size_t)n;
    }
    if(!okay){char extra;okay=read(f,&extra,1)==0;}
    if(memchr(text,0,used))okay=0;
    text[used]=0;
done:
    close(f);return okay;
}
static void status_battery(struct status_metrics *m) {
    char text[64];int64_t value;
    if(!status_read("/sys/class/power_supply/battery/type",text,sizeof(text),0x62656572L)||strcmp(text,"Battery\n"))return;
    if(status_read("/sys/class/power_supply/battery/capacity",text,sizeof(text),0x62656572L)&&status_scalar(text,&value)&&value>=0&&value<=100){m->battery_pct=(uint32_t)value;m->valid|=STATUS_CAP;}
    if(status_read("/sys/class/power_supply/battery/temp",text,sizeof(text),0x62656572L)&&status_scalar(text,&value)&&value>=-500&&value<=1500){m->battery_temp_deci=(int32_t)value;m->valid|=STATUS_TEMP;}
    if(status_read("/sys/class/power_supply/battery/status",text,sizeof(text),0x62656572L)) {
        const char *names[]={"Unknown\n","Charging\n","Discharging\n","Not charging\n","Full\n"};
        for(unsigned i=0;i<5;i++)if(!strcmp(text,names[i])){m->charge=i;m->valid|=STATUS_CHARGE;break;}
    }
}
#include "s22plus_gauge_sample_v1.inc.c"

static int status_collect(const char *identity) {
    uint8_t run[16];if(strlen(identity)!=32)return 126;
    for(unsigned i=0;i<16;i++) {
        unsigned n=0;for(unsigned j=0;j<2;j++){char c=identity[2*i+j];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return 126;n=n*16+(unsigned)(c<='9'?c-'0':c-'a'+10);}run[i]=(uint8_t)n;
    }
    struct status_cpu previous={0};
    for(unsigned sequence=1;sequence<=601;sequence++) {
        struct timespec stamp;if(clock_gettime(CLOCK_MONOTONIC,&stamp))return 1;
        struct status_metrics m={.magic=0x32545353U,.sequence=sequence,.collected_ms=(uint64_t)stamp.tv_sec*1000+(uint64_t)stamp.tv_nsec/1000000};
        memcpy(m.run,run,16);char text[8192];
        if(status_read("/proc/meminfo",text,sizeof(text),0x9fa0L))(void)status_memory(text,&m);
        /* /proc/stat can exceed the fixed prefix. Read only its aggregate line. */
        int f=open("/proc/stat",O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);int valid=0;
        if(f>=0){struct statfs fs;if(!fstatfs(f,&fs)&&fs.f_type==0x9fa0L){ssize_t n=read(f,text,sizeof(text)-1);if(n>0&&!memchr(text,0,(size_t)n)){text[n]=0;char *end=strchr(text,'\n');if(end){end[1]=0;valid=1;}}}close(f);}
        if(valid)status_cpu_sample(text,&previous,&m);else previous.valid=0;
        status_battery(&m);
        if(status_read("/sys/module/s22plus_max77705_telemetry/parameters/sample",text,sizeof(text),0x62656572L)) {
            struct gauge_sample g;
            if(gauge_parse(text,&g)) {
                struct timespec end;
                if(!clock_gettime(CLOCK_MONOTONIC,&end)) {
                    uint64_t current=(uint64_t)end.tv_sec*1000+(uint64_t)end.tv_nsec/1000000;
                    if(g.start_ms<=current && current-g.start_ms<=5000) {
                        m.gauge_ms=g.start_ms;m.gauge_sequence=(uint32_t)g.sequence;
                        m.gauge_soc_permille=(uint32_t)g.soc_permille;m.gauge_voltage_uv=(uint32_t)g.voltage_uv;m.gauge_current_ua=(int32_t)g.current_ua;
                        m.valid|=(uint32_t)g.valid<<5;
                    }
                }
            }
        }
        ssize_t sent=send(STDOUT_FILENO,&m,sizeof(m),MSG_DONTWAIT|MSG_NOSIGNAL);
        if(sent!=(ssize_t)sizeof(m)&&!(sent<0&&(errno==EAGAIN||errno==EINTR)))return 1;
        struct timespec delay={.tv_sec=1};if(nanosleep(&delay,NULL)&&errno!=EINTR)return 1;
    }
    return 0;
}
