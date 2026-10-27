/* Fixed H0 codec fixture: real ARM64 producer/validator, no devices. */
#include <stdio.h>
#include <string.h>
#include "../workspace/public/src/mainline/s22plus_canary_h0/protocol.h"
int main(int argc,char **argv) {
    uint8_t key[32],id[32],buffer[G0Q_RESPONSE_SIZE];
    for(unsigned i=0;i<32;i++){key[i]=(uint8_t)i;id[i]=(uint8_t)(i+32);}
    if(argc!=2)return 90;
    if(!strcmp(argv[1],"request")) {
        if(fread(buffer,1,G0Q_REQUEST_SIZE,stdin)!=G0Q_REQUEST_SIZE||getchar()!=EOF)return 91;
        return g_request(buffer,key,id)?0:1;
    }
    if(strcmp(argv[1],"response"))return 92;
    if(fread(buffer,1,G0Q_BODY_SIZE,stdin)!=G0Q_BODY_SIZE||getchar()!=EOF)return 93;
    g_tag(buffer+256,key,id,1,buffer,256);
    return fwrite(buffer,1,sizeof(buffer),stdout)==sizeof(buffer)?0:94;
}
