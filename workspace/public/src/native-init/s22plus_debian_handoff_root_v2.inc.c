/* Prospective admission after P410's one writable lifetime. The immutable
 * archive still supplies every path, mode, owner, symlink and content hash.
 * Only declared data files may differ; no repair or journal replay occurs. */
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
                int fd=openat(parent,leaf,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);char count[3];
                if(fd<0)error=fs1_error();
                else {
                    if(read(fd,count,sizeof(count))!=2 || memcmp(count,"1\n",2))error=EPROTO;
                    if(close(fd) && !error)error=fs1_error();
                }
            }
            if(!error)++*extra;
        }
        if(close(parent) && !error)error=fs1_error();
        if(error)return error;
    }
    return 0;
}
