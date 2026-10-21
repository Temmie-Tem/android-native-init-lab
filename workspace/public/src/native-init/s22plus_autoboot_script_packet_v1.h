/* Shared bounded anonymous dispatcher packet parser. */
#ifndef S22_AUTOBOOT_SCRIPT_PACKET_V1_H
#define S22_AUTOBOOT_SCRIPT_PACKET_V1_H
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
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
#endif
