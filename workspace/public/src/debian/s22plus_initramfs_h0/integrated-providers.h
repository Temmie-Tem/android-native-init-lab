/* libc port of the retained P317 pre-client provider predicate. The caller
 * requires all three exact DT/driver matches, no duplicates, and a deadline.
 * Device names are not guessed from DT names. No binding write is performed. */
struct di_provider { const char *root,*of_path,*driver; };
static int di_join(char out[PATH_MAX],const char *root,const char *name,const char *tail) {
    int n=snprintf(out,PATH_MAX,"%s%s%s",root,name,tail);
    return n<=0 || n>=PATH_MAX ? EOVERFLOW : 0;
}
static int di_provider_scan(const struct di_provider *spec) {
    DIR *directory=opendir(spec->root);if(!directory)return errno==ENOENT ? EAGAIN : fs1_error();
    unsigned count=0,matches=0;int error=0;char selected[PATH_MAX]={0};
    for(;;) {
        errno=0;struct dirent *entry=readdir(directory);
        if(!entry){if(errno)error=errno;break;}
        if(!strcmp(entry->d_name,".") || !strcmp(entry->d_name,".."))continue;
        if(++count>4096){error=EOVERFLOW;break;}
        char path[PATH_MAX],target[PATH_MAX];
        error=di_join(path,spec->root,entry->d_name,"/of_node");if(error)break;
        ssize_t n=readlink(path,target,sizeof(target)-1);
        if(n<0){if(errno==ENOENT)continue;error=fs1_error();break;}
        if(!n || (size_t)n>=sizeof(target)-1){error=EPROTO;break;}
        target[n]=0;size_t size=strlen(spec->of_path);
        if((size_t)n<size || strcmp(target+n-size,spec->of_path))continue;
        if(++matches>1){error=EEXIST;break;}
        error=di_join(selected,spec->root,entry->d_name,"/driver");if(error)break;
    }
    if(closedir(directory) && !error)error=fs1_error();
    if(error)return error;
    if(matches!=1)return EAGAIN;
    struct stat st;char target[PATH_MAX];
    if(lstat(selected,&st))return errno==ENOENT ? EAGAIN : fs1_error();
    if(!S_ISLNK(st.st_mode) || st.st_uid || st.st_gid)return EPROTO;
    ssize_t n=readlink(selected,target,sizeof(target)-1);
    if(n<=0 || (size_t)n>=sizeof(target)-1)return EPROTO;
    target[n]=0;char *base=strrchr(target,'/');
    if(!base || strcmp(base+1,spec->driver))return EXDEV;
    if(stat(selected,&st) || !S_ISDIR(st.st_mode) || st.st_uid || st.st_gid)return EPROTO;
    return 0;
}
