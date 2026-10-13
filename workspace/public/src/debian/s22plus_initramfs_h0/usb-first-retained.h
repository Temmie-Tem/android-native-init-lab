/* Fixed bounded printk records through the stock sec_log_buf owner. No
 * reserved-memory mapping, disk writer, panic, console reader or replay. */
#ifndef USB_RETAINED_PROTOCOL_EXTERNAL
#include "usb-first-key.h"
#ifndef EARLY_DOMAIN
#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-USB-FIRST-v1"
#endif
#include "early-protocol.h"
#endif
#include "checked-kmsg.h"
static int usb_retained(unsigned sequence,const char *event,size_t size) {
    if(!sequence || sequence>256 || !size || size>384 || event[size-1]!='\n')return EINVAL;
    char boot[38],line[768],hex[65],run[33];uint8_t boot_hash[32],mac[32];
    int error=fs1_read_text("/proc/sys/kernel/random/boot_id",boot,sizeof(boot));
    if(error || strlen(boot)!=37 || boot[36]!='\n')return EPROTO;
    boot[36]=0;early_hash(boot,36,boot_hash);
    early_tag(mac,boot_hash,240,sequence,event,size-1);
    for(unsigned i=0;i<16;++i)snprintf(run+2*i,3,"%02x",early_run[i]);
    for(unsigned i=0;i<32;++i)snprintf(hex+2*i,3,"%02x",mac[i]);
    int n=snprintf(line,sizeof(line),"<14>S22USB1 run=%s boot=%s seq=%u mac=%s %.*s\n",
        run,boot,sequence,hex,(int)size-1,event);
    if(n<0 || (size_t)n>=sizeof(line))return EOVERFLOW;
    return checked_kmsg(line,n);
}
