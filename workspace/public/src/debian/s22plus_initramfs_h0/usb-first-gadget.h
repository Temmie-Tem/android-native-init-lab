/* The effectful subset of retained P399 p260/p282 USB bring-up. Trace and
 * register observers are not required to obtain an authenticated reply. */
#define USB_RETAINED_PROTOCOL_EXTERNAL
#include "usb-first-retained.h"
#include "usb-first-gates.h"
static int usb_stage(unsigned ordinal,const char *name) {
    char line[96];int n=snprintf(line,sizeof(line),"USBSTAGE %s\n",name);
    return n<=0 || (size_t)n>=sizeof(line)?EOVERFLOW:usb_retained(ordinal,line,(size_t)n);
}
static int usb_expect(const char *path,const char *wanted) {
    char text[160];int error=fs1_read_text(path,text,sizeof(text));if(error)return error;
    size_t size=strlen(text);if(size && text[size-1]=='\n')text[--size]=0;
    return strcmp(text,wanted)?EPROTO:0;
}
static int usb_set(const char *path,const char *value,const char *expected) {
    int error=write_fixed(path,value);return error?error:usb_expect(path,expected);
}
static int usb_gates(void) {
#ifdef EARLY_VM_TEST
    return 0;
#else
    uint64_t limit=now()+30000;
    for(;;) {
        bool ready=true;
        for(unsigned i=0;i<sizeof(usb_gates_paths)/sizeof(usb_gates_paths[0]);++i) {
            struct stat st;
            if(lstat(usb_gates_paths[i],&st)) {
                if(errno!=ENOENT)return fs1_error();
                ready=false;break;
            }
            if(!S_ISLNK(st.st_mode) || st.st_uid)return EPROTO;
            if(stat(usb_gates_paths[i],&st) || !S_ISDIR(st.st_mode) || st.st_uid)return EPROTO;
        }
        if(ready)return 0;
        if(now()>=limit || now()>=deadline)return ETIMEDOUT;
        struct timespec delay={0,100000000};if(nanosleep(&delay,NULL))return fs1_error();
    }
#endif
}
static int usb_first_gadget(void) {
    int error=usb_stage(200,"OBSERVER_BEGIN");if(error)return error;
    error=usb_gates();if(error)return error;
#ifndef EARLY_VM_TEST
    if(mkdir("/config",0755) || mount("configfs","/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))return fs1_error();
    if(fs1_empty_directory("/config/usb_gadget"))return EBUSY;
    static const char *dirs[]={"g1","g1/strings/0x409","g1/configs/b.1",
        "g1/configs/b.1/strings/0x409","g1/functions/acm.usb0"};
    char path[PATH_MAX];
    for(unsigned i=0;i<sizeof(dirs)/sizeof(dirs[0]);++i) {
        snprintf(path,sizeof(path),"/config/usb_gadget/%s",dirs[i]);if(mkdir(path,0755))return fs1_error();
    }
    static const char *names[]={"idVendor","idProduct","bcdUSB","bcdDevice","max_speed",
        "strings/0x409/serialnumber","strings/0x409/manufacturer","strings/0x409/product",
        "configs/b.1/strings/0x409/configuration","configs/b.1/bmAttributes","configs/b.1/MaxPower"};
    const char *values[]={"0x04e8","0x6861","0x0200","0x0003","high-speed",early_serial,
        "Linux","S22 Debian USB first","acm","0x80","500"};
    const char *expected[]={"0x04e8","0x6861","0x0200","0x0003","high-speed",early_serial,
        "Linux","S22 Debian USB first","acm","0x80","500"};
    for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i) {
        snprintf(path,sizeof(path),"/config/usb_gadget/g1/%s",names[i]);
        error=usb_set(path,values[i],expected[i]);if(error)return error;
    }
    if(symlink("../../functions/acm.usb0","/config/usb_gadget/g1/configs/b.1/acm.usb0"))return fs1_error();
    char target[128];ssize_t n=readlink("/config/usb_gadget/g1/configs/b.1/acm.usb0",target,sizeof(target)-1);
    if(n<=0 || (size_t)n>=sizeof(target)-1)return EPROTO;
    target[n]=0;
    if(strcmp(target,"../../../../usb_gadget/g1/functions/acm.usb0"))return EPROTO;
#endif
    return usb_stage(201,"GADGET_CREATED");
}
static int usb_first_bind(void) {
    int error=usb_stage(202,"TTY_RAW_ROLE_BEGIN");if(error)return error;
#ifndef EARLY_VM_TEST
    const char *role="/sys/devices/platform/soc/a600000.ssusb/mode";
    /* The successful native path required initial none, then wrote once. */
    if(usb_expect(role,"none"))return EPROTO;
    error=write_fixed(role,"peripheral");if(error)return error;
    uint64_t limit=now()+30000;
    while((error=usb_expect(role,"peripheral"))) {
        if(error!=EPROTO)return error;
        if(now()>=limit || now()>=deadline)return ETIMEDOUT;
        struct timespec delay={0,100000000};if(nanosleep(&delay,NULL))return fs1_error();
    }
    error=usb_gates();if(error)return error;
#endif
    error=usb_stage(203,"ROLE_READY_BIND_BEGIN");if(error)return error;
#ifndef EARLY_VM_TEST
    error=usb_set("/config/usb_gadget/g1/UDC","a600000.dwc3","a600000.dwc3");if(error)return error;
#endif
    return usb_stage(204,"UDC_BOUND");
}
