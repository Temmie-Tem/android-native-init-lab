/* Prospective admission after P410's one writable lifetime. The immutable
 * archive still supplies every path, mode, owner, symlink and content hash.
 * Only declared data files may differ; no repair or journal replay occurs. */
#ifdef S22_DEBIAN_REBOOT
#include "s22plus_debian_reboot_root_v1.inc.c"
#endif
static int dh_mutable_stat(const struct dh_mutable *rule,const struct stat *st,dev_t device) {
    if(st->st_dev!=device || st->st_mode!=rule->mode || st->st_uid || st->st_gid!=rule->gid ||
       (S_ISDIR(st->st_mode) && st->st_nlink!=2) || (rule->archive && st->st_size%400) ||
       (!S_ISDIR(st->st_mode) && (st->st_nlink!=1 || st->st_size<0 ||
        (uint64_t)st->st_size<rule->minimum || (uint64_t)st->st_size>rule->maximum)))return EPROTO;
    return 0;
}
static int dh_mutable_archive(const char *path,const struct stat *st,dev_t device) {
    for(unsigned i=0;i<sizeof(dh_mutable)/sizeof(dh_mutable[0]);++i) {
        const struct dh_mutable *rule=dh_mutable+i;
        if(rule->archive && !strcmp(path,rule->path))return dh_mutable_stat(rule,st,device) ? -EPROTO : 1;
    }
    return 0;
}
static int dh_root_extras(int root,dev_t device,unsigned *extra) {
    *extra=0;
    for(unsigned i=0;i<sizeof(dh_mutable)/sizeof(dh_mutable[0]);++i) {
        const struct dh_mutable *rule=dh_mutable+i;if(rule->archive)continue;
        char leaf[NAME_MAX+1];int parent=ri_parent(root,device,rule->path,leaf);
        if(parent<0) {if(errno==ENOENT)continue;return fs1_error();}
        struct stat st;int error=0;
        if(fstatat(parent,leaf,&st,AT_SYMLINK_NOFOLLOW)) {if(errno!=ENOENT)error=fs1_error();}
        else {
            error=dh_mutable_stat(rule,&st,device);
            if(!error && rule->count) {
                int fd=openat(parent,leaf,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
#if defined(S22_DEBIAN_AUTOBOOT) || defined(S22_AUTOBOOT_HISTORY)
                char count[8]={0};
#else
                char count[3];
#endif
                if(fd<0)error=fs1_error();
                else {
#if defined(S22_DEBIAN_AUTOBOOT) || defined(S22_AUTOBOOT_HISTORY)
                    ssize_t n=read(fd,count,sizeof(count));unsigned value=0;
                    if(n<2 || n>6 || count[n-1]!='\n' || count[0]<'1' || count[0]>'9')error=EPROTO;
                    for(ssize_t j=0;!error && j<n-1;++j) {
                        if(count[j]<'0' || count[j]>'9')error=EPROTO;
                        else value=value*10+(unsigned)(count[j]-'0');
                    }
                    if(!error && (!value || value>=100000))error=EPROTO;
#ifdef S22_DEBIAN_REBOOT
                    if(!error && (!rb_valid_phase(rb_phase) || value>99997U+rb_phase))error=EPROTO;
#endif
#else
                    if(read(fd,count,sizeof(count))!=2 || memcmp(count,"1\n",2))error=EPROTO;
#endif
                    if(close(fd) && !error)error=fs1_error();
                }
            }
            if(!error)++*extra;
        }
        if(close(parent) && !error)error=fs1_error();
        if(error)return error;
    }
#if defined(S22_DEBIAN_AUTOBOOT) || defined(S22_AUTOBOOT_HISTORY)
    /* The historical row is already hash/metadata checked by ri_compare.
     * Its single-link property is additional to the archive table format. */
#ifdef S22_AUTOBOOT_HISTORY
    for(unsigned index=0;index<sizeof(ab_history_paths)/sizeof(ab_history_paths[0]);++index) {
    const char *path=ab_history_paths[index];
#else
    const char *path=ab_history_path;
#endif
    char leaf[NAME_MAX+1];int parent=ri_parent(root,device,path,leaf);
    if(parent<0)return fs1_error();
    struct stat historical;
    int error=fstatat(parent,leaf,&historical,AT_SYMLINK_NOFOLLOW) ||
        historical.st_dev!=device || !S_ISREG(historical.st_mode) || historical.st_nlink!=1 ? EPROTO : 0;
    if(close(parent) && !error)error=fs1_error();
    if(error)return error;
#ifdef S22_AUTOBOOT_HISTORY
    }
#endif
#endif
 #ifdef S22_DEBIAN_REBOOT
    int reboot_error=rb_root_extras(root,device,extra);
    if(reboot_error)return reboot_error;
 #endif
    return 0;
}
