#include "s22plus_debian_handoff_v1.h"
#include "s22plus_debian_handoff_seal_v1.h"
#ifndef S22_DEBIAN_FAULT
#define S22_DEBIAN_FAULT 0
#elif !defined(S22_ROOT_INSPECT_VIRT_TEST)
#error "Debian fault injection requires virtual discovery"
#endif
static void dh_request(unsigned kind,unsigned sequence,unsigned ack) {
    uint8_t frame[48],tag[32];sw_require(sw_bytes(3,frame,sizeof(frame),0));
    if(memcmp(frame,"S328",4) || frame[4]!=1 || frame[5]!=kind || frame[6]!=32 || frame[7] ||
       fs1_u32(frame+8)!=sequence || fs1_u32(frame+12)!=~sw_crc(frame+16,32,sw_crc(frame,12,~0U)))sw_stop(EPROTO);
    sw_tag(tag,kind,sequence,NULL,0);
    unsigned different=0;for(unsigned i=0;i<32;++i)different|=tag[i]^frame[16+i];
    if(different)sw_stop(EPROTO);
    uint32_t accepted=1;sw_require(sw_send(ack,sequence,&accepted,sizeof(accepted)));
}
static int dh_pin_init(void) {
    /* /sbin is the retained merged-/usr symlink. Pin its regular destination. */
    int fd=fs1_pin_file("/usr/sbin/init",dh_init_size,dh_init_sha256,true);
    if(fd<0)return fs1_error();
    struct stat st;int error=fstat(fd,&st) || (uint64_t)st.st_dev!=sw.root_device ? EPROTO : 0;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
