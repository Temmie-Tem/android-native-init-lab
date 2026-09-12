/* Kernel/OF/MMIO/IIO endpoints are fixtures; the included provider is exact. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "thermal_core.h"
typedef uint64_t u64,resource_size_t;
typedef uint32_t u32;
typedef int32_t s32;
#define __iomem
#define __init
#define __exit
#define U64_MAX UINT64_MAX
#define PAGE_SIZE 4096
#define EPROBE_DEFER 517
#define IIO_VAL_INT 1
#define IORESOURCE_MEM 0x200
#define DEFINE_MUTEX(n) struct mutex n={0}
#define MODULE_PARM_DESC(a,b)
#define MODULE_DESCRIPTION(a)
#define MODULE_LICENSE(a)
#define MODULE_DEVICE_TABLE(a,b)
#define module_param_cb(a,b,c,d) _Static_assert((d)==0444,"read-only parameter")
#define module_init(a)
#define module_exit(a)
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define scnprintf snprintf
struct mutex {int held;};
static int mutex_trylock(struct mutex *m){if(m->held)return 0;m->held=1;return 1;}
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;}
struct device_node {const char *name;int kind,index;};
struct device {struct device_node *of_node;};
struct platform_device {struct device dev;int bank;};
struct resource {resource_size_t start,end;};
struct of_phandle_args {struct device_node *np;int args_count;u32 args[4];};
struct of_device_id {const char *compatible;};
struct platform_driver {int (*probe)(struct platform_device *),(*remove)(struct platform_device *);
    struct {const char *name;const struct of_device_id *of_match_table;} driver;};
struct iio_channel {int unused;};
struct kernel_param {int unused;};
struct kernel_param_ops {int (*get)(char *,const struct kernel_param *);void *set;};
static struct device_node root={"/",0,0},zones={"/thermal-zones",1,0},battery={"battery",2,0},
    adc={"vadc@3100",3,0},channel={"wpc_thm",4,0},bn[2]={{"bank0",5,0},{"bank1",5,1}},cn[13];
static struct platform_device bp[2],bat;
static struct resource resource[2][2];
static struct iio_channel iio;
static u32 tm_words[2][128],srot_words[2][128];
static const char *scenario;
static u64 clock_ms=1000;
static unsigned mmio_reads,adc_reads,iio_gets,device_refs,channel_refs,register_calls;
static int adc_return=IIO_VAL_INT,adc_uv=522166,provider_missing,table_wrong,map_wrong;
static struct platform_driver *registered;
static int is_case(const char *s){return !strcmp(scenario,s);}
static u64 ktime_get_boottime(void){return clock_ms;}
static u64 ktime_to_ms(u64 value){return value;}
static resource_size_t resource_size(const struct resource *r){return r->end-r->start+1;}
static struct device_node *of_find_node_by_path(const char *p){
    if(!strcmp(p,"/"))return &root;
    if(!strcmp(p,"/thermal-zones"))return &zones;
    if(!strcmp(p,"/samsung_mobile_device/battery"))return &battery;
    if(!strcmp(p,"/soc/thermal-sensor@c263000"))return &bn[0];
    if(!strcmp(p,"/soc/thermal-sensor@c265000"))return &bn[1];
    assert(0);return NULL;
}
static void of_node_put(struct device_node *node){(void)node;}
static struct device_node *of_get_child_by_name(struct device_node *parent,const char *name){
    if(parent==&adc){assert(!strcmp(name,"wpc_thm"));return &channel;}
    assert(parent==&zones);
    for(unsigned i=0;i<13;i++)if(!strcmp(name,cn[i].name))return &cn[i];
    return NULL;
}
static int of_property_read_string(struct device_node *n,const char *p,const char **out){
    assert(n==&root&&!strcmp(p,"model"));
    *out=is_case("wrong-model")?"Samsung B0Q PROJECT (board-id,12)":"Samsung G0Q PROJECT (board-id,12)";return 0;
}
static int of_property_read_string_index(struct device_node *n,const char *p,int index,const char **out){
    assert(n==&battery&&!strcmp(p,"io-channel-names")&&index==0);*out="adc-temp";return 0;
}
static int of_device_is_compatible(struct device_node *n,const char *s){
    return (n==&battery&&!strcmp(s,"samsung,sec-battery"))||(n==&adc&&!strcmp(s,"qcom,spmi-adc7"));
}
static int of_property_read_u32(struct device_node *n,const char *p,u32 *out){
    if(n->kind==5){assert(!strcmp(p,"#qcom,sensors"));*out=16;return 0;}
    if(n==&battery){
        if(!strcmp(p,"battery,thermal_source"))*out=2;
        else{assert(!strcmp(p,"battery,temp_adc_type"));*out=1;}return 0;
    }
    if(n==&adc){assert(!strcmp(p,"reg"));*out=0x3100;return 0;}
    assert(n==&channel);
    if(!strcmp(p,"reg"))*out=is_case("wrong-channel")?0x148:0x14b;
    else if(!strcmp(p,"qcom,scale-fn-type"))*out=is_case("wrong-scale")?6:5;
    else{assert(!strcmp(p,"qcom,hw-settle-time"));*out=200;}return 0;
}
static void *of_find_property(struct device_node *n,const char *p,int *length){
    assert(n==&battery&&!strcmp(p,"battery,temp_offset")&&!length);return NULL;
}
static int of_property_count_u32_elems(struct device_node *n,const char *p){
    assert(n==&battery&&(!strcmp(p,"battery,temp_table_adc")||!strcmp(p,"battery,temp_table_data")));return 23;
}
static int of_property_read_u32_array(struct device_node *n,const char *p,u32 *out,size_t count){
    if(n==&channel){assert(!strcmp(p,"qcom,pre-scaling")&&count==2);out[0]=out[1]=1;return 0;}
    assert(n==&battery&&count==23);
    if(!strcmp(p,"battery,temp_table_adc")){for(unsigned i=0;i<23;i++)out[i]=s22_thermal_uv[i]+(table_wrong&&i==3);}
    else{assert(!strcmp(p,"battery,temp_table_data"));for(unsigned i=0;i<23;i++)out[i]=(u32)s22_thermal_deci[i];}
    return 0;
}
static int of_property_read_bool(struct device_node *n,const char *p){
    assert(n==&channel&&!strcmp(p,"qcom,ratiometric"));return 1;
}
static int of_parse_phandle_with_args(struct device_node *n,const char *p,const char *cells,int index,struct of_phandle_args *out){
    assert(index==0);out->args_count=1;
    if(n==&battery){assert(!strcmp(p,"io-channels")&&!strcmp(cells,"#io-channel-cells"));out->np=&adc;out->args[0]=0x14b;}
    else{assert(n->kind==6&&!strcmp(p,"thermal-sensors")&&!strcmp(cells,"#thermal-sensor-cells"));
        out->np=&bn[s22_thermal_cpus[n->index].bank];out->args[0]=s22_thermal_cpus[n->index].sensor+(map_wrong&&n->index==0);}
    return 0;
}
static struct resource *platform_get_resource(struct platform_device *p,unsigned type,unsigned index){
    assert(type==IORESOURCE_MEM&&p->bank>=0&&p->bank<2);return index<2?&resource[p->bank][index]:NULL;
}
static void *devm_ioremap_resource(struct device *dev,struct resource *r){
    unsigned bank=(unsigned)dev->of_node->index;
    if(r==&resource[bank][0])return tm_words[bank];
    assert(r==&resource[bank][1]);return srot_words[bank];
}
static u32 readl(const void *pointer){
    for(unsigned b=0;b<2;b++){
        uintptr_t p=(uintptr_t)pointer,t=(uintptr_t)tm_words[b],s=(uintptr_t)srot_words[b];
        if(p>=s&&p<s+sizeof(srot_words[b])){assert(p==s||p==s+4);mmio_reads++;return *(const u32*)p;}
        if(p>=t&&p<t+sizeof(tm_words[b])){
            int allowed=p==t+0xe4;
            for(unsigned i=0;i<13;i++)if(s22_thermal_cpus[i].bank==b&&p==t+0xa0+4*s22_thermal_cpus[i].sensor)allowed=1;
            assert(allowed);mmio_reads++;return *(const u32*)p;
        }
    }
    assert(0);return 0;
}
static struct platform_device *of_find_device_by_node(struct device_node *n){assert(n==&battery);device_refs++;return &bat;}
static void put_device(struct device *d){assert(d==&bat.dev&&device_refs);device_refs--;}
static struct iio_channel *iio_channel_get(struct device *d,const char *name){
    assert(d==&bat.dev&&!strcmp(name,"adc-temp"));iio_gets++;
    if(provider_missing)return ERR_PTR(-EPROBE_DEFER);
    channel_refs++;return &iio;
}
static void iio_channel_release(struct iio_channel *p){assert(p==&iio&&channel_refs);channel_refs--;}
static int iio_read_channel_processed(struct iio_channel *p,int *out){
    assert(p==&iio&&channel_refs&&device_refs);adc_reads++;clock_ms++;*out=adc_uv;return adc_return;
}
static int platform_driver_register(struct platform_driver *p){
    assert(!registered&&!strcmp(p->driver.name,"s22plus-thermal-telemetry"));
    registered=p;register_calls++;
    (void)p->probe(&bp[0]);if(!is_case("late-bank"))(void)p->probe(&bp[1]);return 0;
}
static void platform_driver_unregister(struct platform_driver *p){
    assert(registered==p);(void)p->remove(&bp[0]);(void)p->remove(&bp[1]);registered=NULL;
}
#include "provider-body.c"

int main(int argc,char **argv){
    assert(argc==2);scenario=argv[1];bat.dev.of_node=&battery;
    for(unsigned i=0;i<13;i++)cn[i]=(struct device_node){s22_thermal_cpus[i].name,6,(int)i};
    for(unsigned b=0;b<2;b++){
        bp[b]=(struct platform_device){.dev={.of_node=&bn[b]},.bank=(int)b};
        resource[b][0]=(struct resource){bank_tm[b],bank_tm[b]+0x1fe};
        resource[b][1]=(struct resource){bank_srot[b],bank_srot[b]+0x1fe};
        srot_words[b][0]=0x20060000;srot_words[b][1]=1;tm_words[b][0xe4/4]=1;
        for(unsigned i=0;i<16;i++)tm_words[b][0xa0/4+i]=(1U<<21)|(450+b*50+i);
    }
    if(is_case("wrong-model")){assert(thermal_init()==-ENODEV&&!mmio_reads&&!register_calls);return 0;}
    if(is_case("wrong-map"))map_wrong=1;
    if(is_case("wrong-resource"))resource[0][0].end++;
    if(is_case("wrong-version"))srot_words[0][0]=0x30000000;
    if(is_case("disabled"))srot_words[0][1]=0;
    if(is_case("wrong-table"))table_wrong=1;
    if(is_case("deferred"))provider_missing=1;
    assert(!thermal_init()&&register_calls==1&&!adc_reads);
    assert(sample_ops.get==sample_get&&!sample_ops.set&&diagnostic_ops.get==diagnostic_get&&!diagnostic_ops.set);
    char text[PAGE_SIZE],diag[PAGE_SIZE];unsigned reads=mmio_reads;
    assert(diagnostic_get(diag,NULL)>0&&mmio_reads==reads&&!adc_reads);
    thermal_lock.held=1;assert(sample_get(text,NULL)==-EAGAIN&&!adc_reads);thermal_lock.held=0;
    if(is_case("adc-error"))adc_return=-ETIMEDOUT;
    if(is_case("adc-wrong-format"))adc_return=0;
    if(is_case("adc-zero"))adc_uv=0;
    if(is_case("adc-too-high"))adc_uv=970783;
    if(is_case("negative"))adc_uv=(int)s22_thermal_uv[21];
    if(is_case("partial"))tm_words[1][0xa0/4+4]&=~(1U<<21);
    if(is_case("not-ready"))tm_words[0][0xe4/4]=tm_words[1][0xe4/4]=0;
    if(is_case("cpu-range"))for(unsigned b=0;b<2;b++)for(unsigned i=0;i<16;i++)tm_words[b][0xa0/4+i]=(1U<<21)|1501;
    assert(sample_get(text,NULL)>0&&!thermal_lock.held);
    if(is_case("emit")){fputs(text,stdout);thermal_exit();assert(!device_refs&&!channel_refs);return 0;}
    if(is_case("deferred")){
        assert(!adc_reads&&!device_refs&&!channel_refs&&strstr(text,"valid=1"));
        provider_missing=0;clock_ms+=1000;assert(sample_get(text,NULL)>0&&adc_reads==1&&strstr(text,"valid=3"));
    }else if(is_case("late-bank")){
        assert(strstr(text,"cpu_mask=511"));assert(!thermal_probe(&bp[1]));clock_ms+=1000;
        assert(sample_get(text,NULL)>0&&strstr(text,"cpu_mask=8191"));
    }else if(is_case("wrong-channel")||is_case("wrong-scale")||is_case("wrong-table")){
        assert(!adc_reads&&!device_refs&&!channel_refs&&strstr(text,"valid=1"));
    }else if(!strncmp(scenario,"adc-",4)){
        assert(adc_reads==1&&battery_stopped&&strstr(text,"valid=1"));clock_ms+=10000;
        assert(sample_get(text,NULL)>0&&adc_reads==1&&strstr(text,"valid=1"));
    }else if(is_case("negative"))assert(strstr(text,"battery_temp_deci=-150"));
    else if(is_case("partial"))assert(strstr(text,"cpu_mask=4095")&&strstr(text,"cpu_temp_mc=50300"));
    else if(is_case("not-ready")||is_case("cpu-range"))assert(strstr(text,"valid=2 cpu_mask=0 cpu_temp_mc=0"));
    else if(is_case("wrong-map")||is_case("wrong-resource")||is_case("wrong-version")||is_case("disabled"))
        assert(strstr(text,"cpu_mask=7680"));
    else assert(strstr(text,"valid=3 cpu_mask=8191 cpu_temp_mc=50400")&&strstr(text,"battery_temp_deci=250"));
    unsigned calls=adc_reads;reads=mmio_reads;
    assert(sample_get(text,NULL)==-EAGAIN&&adc_reads==calls&&mmio_reads==reads);
    assert(diagnostic_get(diag,NULL)>0&&adc_reads==calls&&mmio_reads==reads);
    clock_ms=last_start-1;assert(sample_get(text,NULL)==-EOVERFLOW&&adc_reads==calls);
    clock_ms=last_start+1000;sequence=U64_MAX;assert(sample_get(text,NULL)==-EOVERFLOW&&adc_reads==calls);
    thermal_exit();assert(!device_refs&&!channel_refs&&!banks[0].device&&!banks[1].device);
    puts("PASS exact provider and bounded failure behavior");return 0;
}
