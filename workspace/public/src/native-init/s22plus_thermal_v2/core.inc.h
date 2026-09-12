/* V2 extension to the frozen V1 arithmetic. CPU bits 0..12, GPU 13..14,
 * SoC DDR-region bit 15. A valid zero is distinct from an absent sample. */
#define S22_THERMAL_SENSOR_COUNT 16U
#define S22_THERMAL_LINE_CAP 768U
static const struct s22_thermal_cpu s22_thermal_extra[] = {
    {"gpuss-0",0,14}, {"gpuss-1",0,15}, {"ddr",1,9}
};
static inline const struct s22_thermal_cpu *s22_thermal_sensor(unsigned int i)
{
    return i < S22_THERMAL_CPU_COUNT ? &s22_thermal_cpus[i] :
        &s22_thermal_extra[i-S22_THERMAL_CPU_COUNT];
}
struct s22_thermal_data {
    unsigned long long sequence,start_ms,end_ms;
    unsigned int map_mask,mask,bound_mask,mapped_mask;
    int error[2];
    /* phase: 0 unseen, 1 retained probe snapshot, 2 this acquisition.
     * seen: bit0 VERSION, bit1 ENABLE, bit2 TRDY, bit3 selected statuses. */
    unsigned int phase[2],seen[2],version[2],enable[2],ready[2],status_valid[2];
    int temp_mc[S22_THERMAL_SENSOR_COUNT];
    int battery_uv,battery_deci,battery_error;
    unsigned int battery_valid;
};
static inline unsigned int s22_thermal_bank_mask(unsigned int bank)
{
    unsigned int i,mask=0;
    for(i=0;i<S22_THERMAL_SENSOR_COUNT;i++)
        if(s22_thermal_sensor(i)->bank==bank)mask|=1U<<i;
    return mask;
}
static inline int s22_thermal_max(const struct s22_thermal_data *s,
                                 unsigned int first,unsigned int count)
{
    unsigned int i,seen=0;int value=0;
    for(i=first;i<first+count;i++)if(s->mask&(1U<<i)) {
        if(!seen || s->temp_mc[i]>value)value=s->temp_mc[i];
        seen=1;
    }
    return value;
}
static inline int s22_thermal_data_valid(const struct s22_thermal_data *s)
{
    unsigned int i;
    if(!s->sequence || s->end_ms<s->start_ms || s->map_mask>65535U ||
       s->mask>65535U || (s->mask&~s->map_mask) || s->bound_mask>3U ||
       s->mapped_mask>3U || (s->bound_mask&~s->mapped_mask) || s->battery_valid>1U)
        return 0;
    for(i=0;i<2;i++) {
        unsigned int active=s->mask&s22_thermal_bank_mask(i),seen=s->seen[i];
        if(s->error[i]>0 || s->error[i]<-4095 || s->phase[i]>2U || seen>15U ||
           s->status_valid[i]>65535U || (!s->phase[i]&&seen) ||
           (s->phase[i]==2U && !(s->bound_mask&(1U<<i))) ||
           (!(seen&1U)&&s->version[i]) || (!(seen&2U)&&s->enable[i]) ||
           (!(seen&4U)&&s->ready[i]) || (!(seen&8U)&&s->status_valid[i]))return 0;
        if(active && (s->error[i] || s->phase[i]!=2U || seen!=15U ||
           !(s->bound_mask&(1U<<i)) || (s->version[i]>>28)!=2U ||
           !(s->enable[i]&1U) || !(s->ready[i]&1U)))return 0;
    }
    for(i=0;i<S22_THERMAL_SENSOR_COUNT;i++) {
        const struct s22_thermal_cpu *sensor=s22_thermal_sensor(i);
        if(s->mask&(1U<<i)) {
            if(s->temp_mc[i]<-40000 || s->temp_mc[i]>150000 ||
               !(s->status_valid[sensor->bank]&(1U<<sensor->sensor)))return 0;
        }else if(s->temp_mc[i])return 0;
    }
    if(s->battery_error>0 || s->battery_error<-4095)return 0;
    if(s->battery_valid) {
        int deci;
        if(s->battery_error || s22_thermal_battery_decode(s->battery_uv,&deci) ||
           deci!=s->battery_deci)return 0;
    }else if(!s->battery_error || s->battery_deci)return 0;
    return 1;
}
