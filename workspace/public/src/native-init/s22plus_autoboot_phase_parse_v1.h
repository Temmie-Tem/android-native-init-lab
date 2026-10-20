/* Fixed FYG8 trace text and anonymous rc dispatcher packet decoders.
 * Positive callsite observations only: text times are rounded microseconds.
 * No address, arbitrary event, path or memory fetch is exported. */
#ifndef S22_AUTOBOOT_PHASE_PARSE_V1_H
#define S22_AUTOBOOT_PHASE_PARSE_V1_H
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>

struct ap_event { uint64_t usec; unsigned id,pid,cpu; int target,rc; };
static int ap_unsigned(const char **at,uint64_t *out) {
    const char *p=*at;uint64_t value=0;unsigned count=0;
    while(*p>='0' && *p<='9') {
        if(++count>20 || value>(UINT64_MAX-(unsigned)(*p-'0'))/10)return EPROTO;
        value=value*10+(unsigned)(*p++-'0');
    }
    if(!count)return EPROTO;
    *at=p;*out=value;return 0;
}
static int ap_signed(const char **at,int *out) {
    const char *p=*at;int negative=*p=='-';if(negative)++p;
    uint64_t value;if(ap_unsigned(&p,&value) || value>(uint64_t)INT_MAX+(unsigned)negative)return EPROTO;
    *out=negative ? (int)(-(int64_t)value) : (int)value;*at=p;return 0;
}
static void ap_spaces(const char **p){while(**p==' ')++*p;}
static int ap_trace_line(const char *line,struct ap_event *event) {
    struct ap_event result={.target=-1};const char *bracket=strchr(line,'[');
    if(!bracket || bracket-line>96)return EPROTO;
    const char *dash=NULL;for(const char *p=line;p<bracket;++p)if(*p=='-')dash=p;
    if(!dash)return EPROTO;
    const char *p=dash+1;uint64_t value;
    if(ap_unsigned(&p,&value) || value>INT_MAX)return EPROTO;
    result.pid=(unsigned)value;ap_spaces(&p);if(p!=bracket)return EPROTO;
    ++p;if(ap_unsigned(&p,&value) || value>=8 || *p++!=']')return EPROTO;
    result.cpu=(unsigned)value;ap_spaces(&p);
    /* Standard context-info prints one flags token before the boot timestamp. */
    unsigned flags=0;while(*p && *p!=' ') {if(++flags>8)return EPROTO;++p;}
    if(flags<4)return EPROTO;
    ap_spaces(&p);
    uint64_t seconds;if(ap_unsigned(&p,&seconds) || seconds>300 || *p++!='.')return EPROTO;
    uint64_t fraction=0;for(unsigned i=0;i<6;++i) {
        if(*p<'0' || *p>'9')return EPROTO;
        fraction=fraction*10+(unsigned)(*p++-'0');
    }
    if(*p++!=':')return EPROTO;
    ap_spaces(&p);result.usec=seconds*1000000+fraction;
    unsigned id=0;
    for(unsigned i=0;i<AP_PROBE_COUNT;++i) {
        size_t size=strlen(ap_probes[i].name);
        if(!strncmp(p,ap_probes[i].name,size) && p[size]==':'){id=i+1;p+=size+1;break;}
    }
    if(!id)return EPROTO;
    result.id=id;ap_spaces(&p);
    if(*p++!='(')return EPROTO;
    const char *end=strchr(p,')');
    if(!end || end-p>256)return EPROTO;
    size_t symbol_size=strlen(ap_probes[id-1].symbol);
    if(strncmp(p,ap_probes[id-1].symbol,symbol_size))return EPROTO;
    p+=symbol_size;unsigned hex_digits=0;
    while((*p>='0' && *p<='9') || (*p>='a' && *p<='f')) {
        if(++hex_digits>8)return EPROTO;
        ++p;
    }
    if(!hex_digits || end-p!=(ptrdiff_t)strlen(ap_module_suffix) ||
       memcmp(p,ap_module_suffix,(size_t)(end-p)))return EPROTO;
    p=end+1;
    unsigned selected=ap_probes[id-1].fields;
    if(selected&1) {
        if(strncmp(p," cpu=",5))return EPROTO;
        p+=5;
        if(ap_signed(&p,&result.target) || result.target<0 || result.target>=8)return EPROTO;
    }
    if(selected&2) {
        if(strncmp(p," rc=",4))return EPROTO;
        p+=4;if(ap_signed(&p,&result.rc))return EPROTO;
    }
    if(strcmp(p,"\n"))return EPROTO;
    *event=result;return 0;
}
struct ap_packet { unsigned sequence,id; char kind; int result; };
static int ap_packet_parse(const char *text,struct ap_packet *packet) {
    struct ap_packet result={0};const char *p=text;uint64_t number;
    if(ap_unsigned(&p,&number) || !number || number>AP_SCRIPT_RECORD_CAP || *p++!=' ')return EPROTO;
    result.sequence=(unsigned)number;result.kind=*p++;
    if(!result.kind || !strchr("DBEX",result.kind) || *p++!=' ')return EPROTO;
    if(ap_unsigned(&p,&number) || number>AP_SCRIPT_COUNT || *p++!=' ')return EPROTO;
    result.id=(unsigned)number;if(ap_signed(&p,&result.result) || strcmp(p,"\n"))return EPROTO;
    if(result.kind=='B' || result.kind=='E') {
        if(!result.id || result.result<0 || result.result>255 || (result.kind=='B' && result.result))return EPROTO;
    } else if(result.id || result.result)return EPROTO;
    *packet=result;return 0;
}
/* kprobe_profile has bare event names; every selected name must appear once.
 * Hits may exceed decoded records (other instances and unretained events).
 * A deficit for one event cannot be hidden by another event's excess. */
static int ap_profile_parse(char *text,const unsigned decoded[AP_PROBE_COUNT],
        unsigned *mask,uint64_t *hits,uint64_t *misses) {
    *mask=0;*hits=*misses=0;char *save=NULL;
    size_t size=strlen(text);if(!size || text[size-1]!='\n')return EPROTO;
    for(char *line=strtok_r(text,"\n",&save);line;line=strtok_r(NULL,"\n",&save)) {
        const char *p=line;ap_spaces(&p);const char *end=p;while(*end && *end!=' ' && *end!='\t')++end;
        int selected=-1;
        for(unsigned i=0;i<AP_PROBE_COUNT;++i)
            if(strlen(ap_probes[i].name)==(size_t)(end-p) && !strncmp(p,ap_probes[i].name,end-p))selected=(int)i;
        if(selected<0)continue;
        p=end;while(*p==' ' || *p=='\t')++p;
        uint64_t hit,miss;if(ap_unsigned(&p,&hit))return EPROTO;
        while(*p==' ' || *p=='\t')++p;
        if(ap_unsigned(&p,&miss))return EPROTO;
        ap_spaces(&p);
        if(*p || (*mask&(1U<<selected)) || hit<decoded[selected] ||
           hit>UINT32_MAX-*hits || miss>UINT32_MAX-*misses)return EPROTO;
        *mask|=1U<<selected;*hits+=hit;*misses+=miss;
    }
    return *mask==(1U<<AP_PROBE_COUNT)-1 ? 0 : EPROTO;
}
static int ap_stats_parse(char *text,uint64_t *overrun,uint64_t *commit,uint64_t *dropped,uint64_t *remaining) {
    const char *names[]={"entries:","overrun:","commit overrun:","bytes:",
        "oldest event ts:","now ts:","dropped events:","read events:"};
    uint64_t values[8]={0};unsigned mask=0;char *save=NULL;
    size_t size=strlen(text);if(!size || text[size-1]!='\n')return EPROTO;
    for(char *line=strtok_r(text,"\n",&save);line;line=strtok_r(NULL,"\n",&save)) {
        unsigned found=0;
        for(unsigned i=0;i<8;++i)if(!strncmp(line,names[i],strlen(names[i]))) {
            const char *p=line+strlen(names[i]);ap_spaces(&p);uint64_t value;
            if(ap_unsigned(&p,&value) || value>UINT32_MAX || (mask&(1U<<i)))return EPROTO;
            if(i==4 || i==5) {
                if(*p++!='.')return EPROTO;
                for(unsigned j=0;j<6;++j)if(*p<'0' || *p++>'9')return EPROTO;
            }
            if(*p)return EPROTO;
            values[i]=value;mask|=1U<<i;found=1;
        }
        if(!found)return EPROTO;
    }
    if(mask!=255)return EPROTO;
    *overrun=values[1];*commit=values[2];*dropped=values[6];*remaining=values[0];return 0;
}
#endif
