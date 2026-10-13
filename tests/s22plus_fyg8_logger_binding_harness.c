/* Exercise the real physical probe against captured-name and broken-binding
 * filesystem fixtures. Only lstat/stat are replaced, never the predicate. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
static const char *fixture;
static int fixture_lstat(const char *path,struct stat *out) {
    memset(out,0,sizeof(*out));out->st_nlink=1;
    if(!strcmp(path,"/sys/module/sec_log_buf")) {
        if(!strcmp(fixture,"module-absent")){errno=ENOENT;return -1;}
        out->st_mode=S_IFDIR|0755;
    } else if(!strcmp(path,"/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf")) {
        if(!strcmp(fixture,"soc-only") || !strcmp(fixture,"driver-absent")){errno=ENOENT;return -1;}
        out->st_mode=(!strcmp(fixture,"driver-file") ? S_IFREG : S_IFLNK)|0777;
        if(!strcmp(fixture,"driver-owner"))out->st_uid=1000;
    } else if(!strcmp(path,"/proc/last_kmsg")) {
        if(!strcmp(fixture,"last-absent")){errno=ENOENT;return -1;}
        out->st_mode=(!strcmp(fixture,"last-symlink") ? S_IFLNK : S_IFREG)|0400;
    } else if(!strcmp(path,"/proc/ap_klog")) {
        if(!strcmp(fixture,"ap-absent")){errno=ENOENT;return -1;}
        out->st_mode=S_IFREG|0400;
    } else {errno=ENOENT;return -1;}
    return 0;
}
static int fixture_stat(const char *path,struct stat *out) {
    if(strcmp(path,"/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf"))return 99;
    if(!strcmp(fixture,"dangling")){errno=ENOENT;return -1;}
    memset(out,0,sizeof(*out));out->st_mode=(!strcmp(fixture,"target-file") ? S_IFREG : S_IFDIR)|0755;
    return 0;
}
#define lstat fixture_lstat
#define stat(path,out) fixture_stat(path,out)
#include "s22plus_fyg8_logger_binding_v1.h"
#undef lstat
#undef stat
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    fixture=argv[1];unsigned phase=99;
    int error=s22_logger_probe((unsigned)strtoul(argv[2],NULL,10),&phase);
    printf("%d %u\n",error,phase);
    return 0;
}
