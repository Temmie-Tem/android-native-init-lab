/* Real local SOCK_SEQPACKET boundary with the selected production wire header. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include "selected-wire.h"
int main(int argc,char **argv) {
    struct status_metrics m={.magic=RESIDENT_SAMPLE_MAGIC,.valid=3,.source=0,
        .sequence=1,.collected_ms=1000,.mem_total_kib=8192000,.mem_available_kib=4096000,.cpu_permille=300};
    struct status_metrics old={0};uint8_t run[16]={0};
    if(argc==2 && !strcmp(argv[1],"emit")) {
        if(!resident_sample_valid(&m,&old,0,2000,run))return 2;
        return fwrite(&m,1,sizeof(m),stdout)==sizeof(m)?0:3;
    }
    if(argc!=3 || strcmp(argv[1],"receive"))return 4;
    memset(&m,0,sizeof(m));
    ssize_t n=recv(atoi(argv[2]),&m,sizeof(m),MSG_TRUNC);
    puts(n==(ssize_t)sizeof(m)&&resident_sample_valid(&m,&old,0,2000,run)?"ACCEPT":"REJECT");
    return 0;
}
