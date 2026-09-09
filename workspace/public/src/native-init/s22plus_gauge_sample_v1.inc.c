/* Parse only the fixed read-only provider record; missing data stays missing. */
struct gauge_sample {
    uint64_t sequence,start_ms,valid,soc_raw,voltage_raw,current_raw,soc_permille,voltage_uv;
    int64_t error,current_ua;
};
static int gauge_unsigned(const char **p,const char *key,uint64_t *value) {
    size_t n=strlen(key);if(strncmp(*p,key,n))return 0;*p+=n;
    return status_uint(p,value);
}
static int gauge_signed(const char **p,const char *key,int64_t *value) {
    size_t n=strlen(key);if(strncmp(*p,key,n))return 0;*p+=n;
    int negative=**p=='-';if(negative)++*p;uint64_t magnitude;
    if(!status_uint(p,&magnitude)||magnitude>INT32_MAX)return 0;
    *value=negative?-(int64_t)magnitude:(int64_t)magnitude;return 1;
}
static int gauge_parse(const char *p,struct gauge_sample *out) {
    struct gauge_sample s={0};
    if(!gauge_unsigned(&p,"S22FG1 seq=",&s.sequence)||
       !gauge_unsigned(&p," start_ms=",&s.start_ms)||
       !gauge_unsigned(&p," valid=",&s.valid)||
       !gauge_signed(&p," error=",&s.error)||
       !gauge_unsigned(&p," soc_raw=",&s.soc_raw)||
       !gauge_unsigned(&p," voltage_raw=",&s.voltage_raw)||
       !gauge_unsigned(&p," current_raw=",&s.current_raw)||
       !gauge_unsigned(&p," soc_permille=",&s.soc_permille)||
       !gauge_unsigned(&p," voltage_uv=",&s.voltage_uv)||
       !gauge_signed(&p," current_ua=",&s.current_ua)||strcmp(p,"\n"))return 0;
    if(!s.sequence||s.sequence>601||!s.start_ms||s.valid>7||s.error||
       s.soc_raw>65535||s.voltage_raw>65535||s.current_raw>65535)return 0;
    uint64_t soc=s.soc_raw*10/256;if(soc>1000)soc=1000;
    int64_t current=s.current_raw&0x8000?-(int64_t)((65536-s.current_raw)*15625*5/100):(int64_t)(s.current_raw*15625*5/100);
    if(s.soc_permille!=soc||s.voltage_uv!=s.voltage_raw*625/8||s.current_ua!=current)return 0;
    if((s.valid&2)&&(s.voltage_uv<2000000||s.voltage_uv>5000000))return 0;
    *out=s;return 1;
}
