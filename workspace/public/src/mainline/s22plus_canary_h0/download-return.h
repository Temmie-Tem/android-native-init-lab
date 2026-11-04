/* Exact RAM Download control. Included only by the distinct admitted schema. */
#ifndef G0Q_DOWNLOAD_RETURN_H
#define G0Q_DOWNLOAD_RETURN_H
#include <linux/reboot.h>
#include <sys/syscall.h>

/* The bound platform driver can register this class device only after its
 * DT-selected NVMEM cell was acquired. The authenticated full live DT is also
 * checked by the host before control. This is not a write/readback guarantee. */
static int download_ready(void) {
#ifdef CANARY_H0_VM
    /* QEMU has no Samsung PMIC. The exact physical binding helper is separately
     * exercised with fixed filesystem fixtures; VM proves protocol and syscall. */
    return 1;
#else
    char data[64];size_t size;
    int e=read_small("/sys/class/reboot-mode/nvmem-reboot-mode/reboot_modes",data,sizeof(data),&size);
    static const char modes[]="recovery bootloader download\n";
    /* This exact kernel's show method returns size + emit(size-1,"\n"),
     * so kernfs exposes the final NUL as one byte too. Match its actual
     * output, rather than silently trimming or accepting arbitrary modes. */
    if(e||size!=sizeof(modes)||memcmp(data,modes,size))return 0;
    char *path=realpath("/sys/bus/platform/devices/reboot-mode/driver",NULL);
    if(!path)return 0;
    int match=!strcmp(path,"/sys/bus/platform/drivers/nvmem-reboot-mode");free(path);
    if(!match)return 0;
    path=realpath("/sys/bus/platform/devices/reboot-mode/of_node",NULL);
    if(!path)return 0;
    match=!strcmp(path,"/sys/firmware/devicetree/base/reboot-mode");free(path);
    if(!match)return 0;
    return 1;
#endif
}

static int download_finish(int client,const uint8_t response[G0Q_RESPONSE_SIZE]) {
    uint8_t command[88],auth[32],ack[120];
    int e=transfer(client,command,sizeof(command),0);if(e)return e;
    g_tag(auth,canary_key,canary_id,2,command,56);
    if(memcmp(command,"G0QDCQ1\0",8)||!g_equal(command+8,response+40,32)||
       !g_equal(command+40,response+72,16)||!g_equal(command+56,auth,32))return EACCES;
    if(now_ms()>=deadline)return ETIMEDOUT;
    if(!download_ready())return ENODEV;
    memcpy(ack,"G0QDCA1\0",8);memcpy(ack+8,canary_id,32);
    memcpy(ack+40,response+40,32);memcpy(ack+72,response+72,16);
    g_tag(ack+88,canary_key,canary_id,3,ack,88);
    if((e=transfer(client,ack,sizeof(ack),1)))return e;
    if(shutdown(client,SHUT_WR))return errno;
    /* EOF only settles this connection; it is neither verified receipt nor
     * authority. The authenticated control above already supplies selection.
     * Missing EOF, extra bytes or the original deadline prevent this syscall. */
    for(;;) {
        uint64_t now=now_ms();if(now>=deadline)return ETIMEDOUT;
        struct pollfd p={client,POLLIN,0};int rc=poll(&p,1,(int)(deadline-now));
        if(rc<0) {if(errno==EINTR)continue;return errno;}
        if(!rc)return ETIMEDOUT;
        uint8_t extra;ssize_t got=recv(client,&extra,1,0);
        if(got<0) {if(errno==EAGAIN||errno==EINTR)continue;return errno;}
        if(got)return EPROTO;
        break;
    }
    if(now_ms()>=deadline)return ETIMEDOUT;
    if(!download_ready())return ENODEV;
    dprintf(2,"G0Q_DOWNLOAD_RESTART2_PREPARED\n");
    /* Readiness and logging can block. Retain the original absolute deadline
     * at the effect, after those preparations, without another driver read. */
    if(now_ms()>=deadline)return ETIMEDOUT;
    syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,
            LINUX_REBOOT_CMD_RESTART2,"download");
    /* There is deliberately no retry or alternate reset after any return. */
    return errno?errno:EIO;
}
#endif
