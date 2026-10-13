/* Exact FYG8 stock logger readiness. Device name 8.samsung,kernel_log_buf
 * is present in the independently captured P418 and P424 probe records.
 * A loaded module alone is not driver binding or a readable proc backend.
 * This function performs observation only; the caller owns a finite wait. */
#ifndef S22PLUS_FYG8_LOGGER_BINDING_V1_H
#define S22PLUS_FYG8_LOGGER_BINDING_V1_H
#include <errno.h>
#include <sys/stat.h>

enum s22_logger_phase {
    S22_LOGGER_READY=0, S22_LOGGER_MODULE=1, S22_LOGGER_DRIVER_LINK=2,
    S22_LOGGER_DRIVER_TARGET=3, S22_LOGGER_LAST_KMSG=4, S22_LOGGER_AP_KLOG=5
};
#define S22_LOGGER_NEED_LAST 1U
#define S22_LOGGER_NEED_AP 2U
#define S22_LOGGER_BIND_PATH "/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf"

static int s22_logger_probe(unsigned required, unsigned *phase) {
    struct stat st;
    if(!phase || !required || (required & ~3U))return EINVAL;
    *phase=S22_LOGGER_MODULE;
    if(lstat("/sys/module/sec_log_buf",&st))return errno;
    if(!S_ISDIR(st.st_mode) || st.st_uid || st.st_gid)return EPROTO;
    *phase=S22_LOGGER_DRIVER_LINK;
    if(lstat(S22_LOGGER_BIND_PATH,&st))return errno;
    if(!S_ISLNK(st.st_mode) || st.st_uid || st.st_gid)return EPROTO;
    *phase=S22_LOGGER_DRIVER_TARGET;
    if(stat(S22_LOGGER_BIND_PATH,&st))return errno;
    if(!S_ISDIR(st.st_mode) || st.st_uid || st.st_gid)return EPROTO;
    if(required & S22_LOGGER_NEED_LAST) {
        *phase=S22_LOGGER_LAST_KMSG;
        if(lstat("/proc/last_kmsg",&st))return errno;
        if(!S_ISREG(st.st_mode) || st.st_uid || st.st_gid)return EPROTO;
    }
    if(required & S22_LOGGER_NEED_AP) {
        *phase=S22_LOGGER_AP_KLOG;
        if(lstat("/proc/ap_klog",&st))return errno;
        if(!S_ISREG(st.st_mode) || st.st_uid || st.st_gid)return EPROTO;
    }
    *phase=S22_LOGGER_READY;
    return 0;
}
#endif
