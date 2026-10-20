#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static char **values;
static unsigned online_reads;
static int fs1_read_text(const char *path,char *text,size_t capacity) {
    const char *value=NULL;
    if(!strcmp(path,"/sys/devices/system/cpu/online"))value=values[online_reads++ ? 3 : 1];
    else if(!strcmp(path,"/sys/bus/platform/devices/hypervisor:qcom,gh-watchdog/disable"))value=values[2];
    if(!value || !strcmp(value,"MISSING"))return ENOENT;
    if(strlen(value)>=capacity)return EOVERFLOW;
    strcpy(text,value);return 0;
}
#define S22_AUTOBOOT_SINGLECPU
#include "s22plus_autoboot_singlecpu_v1.h"
int main(int argc,char **argv) {
    if(argc!=4)return 64;
    values=argv;uint64_t value=0;int error=sc_observe(&value);
    if(!error && !sc_valid(value))return 65;
    printf("%d %llu %u\n",error,(unsigned long long)value,online_reads);
    return 0;
}
