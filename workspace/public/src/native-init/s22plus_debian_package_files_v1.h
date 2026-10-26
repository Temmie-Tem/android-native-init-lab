/* Exact predeclared package state, shared by protected admission and runtime.
 * No filesystem write, learned hash, repair, or package execution here. */
#ifndef S22PLUS_DEBIAN_PACKAGE_FILES_V1_H
#define S22PLUS_DEBIAN_PACKAGE_FILES_V1_H
#include "s22plus_debian_package_seal_v1.h"
static int pk_directory(int fd,dev_t device) {
    struct stat st;struct statfs fs;
    return fstat(fd,&st) || fstatfs(fd,&fs) || st.st_dev!=device || fs.f_type!=0xef53 ||
        st.st_mode!=(S_IFDIR|0755) || st.st_uid || st.st_gid || st.st_nlink<2 ? EPROTO : 0;
}
static int pk_parent(int root,dev_t device,const char *path,char leaf[NAME_MAX+1]) {
    char copy[PATH_MAX];size_t n=strlen(path);
    if(!n || n>=sizeof(copy) || path[0]=='/'){errno=EINVAL;return -1;}
    memcpy(copy,path,n+1);int fd=fcntl(root,F_DUPFD_CLOEXEC,3);
    if(fd<0)return -1;
    int error=pk_directory(fd,device);char *part=copy;
    for(unsigned depth=0;!error && depth<32;++depth) {
        char *slash=strchr(part,'/');if(slash)*slash=0;
        if(!*part || strlen(part)>NAME_MAX || !strcmp(part,".") || !strcmp(part,"..")){error=EINVAL;break;}
        if(!slash){strcpy(leaf,part);return fd;}
        int next=openat(fd,part,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if(next<0){error=fs1_error();break;}
        error=pk_directory(next,device);
        if(close(fd) && !error)error=fs1_error();
        fd=next;part=slash+1;
    }
    if(!error)error=EOVERFLOW;
    (void)close(fd);errno=error;return -1;
}
static int pk_file_at(int parent,const char *leaf,dev_t device,const struct pk_file *rule,bool after) {
    struct stat before,opened,end;uint8_t data[16384],digest[32],extra;
    if(fstatat(parent,leaf,&before,AT_SYMLINK_NOFOLLOW))return fs1_error();
    uint64_t size=after ? rule->size : rule->before_size;
    const uint8_t *wanted=after ? rule->sha : rule->before_sha;
    if(before.st_dev!=device || before.st_mode!=rule->mode || before.st_uid || before.st_gid ||
       before.st_nlink!=(S_ISDIR(rule->mode) ? 2U : 1U) ||
       (!S_ISDIR(rule->mode) && (before.st_size<0 || (uint64_t)before.st_size!=size || size>1024*1024)))return EPROTO;
    int fd=openat(parent,leaf,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC|(S_ISDIR(rule->mode)?O_DIRECTORY:0));
    if(fd<0)return fs1_error();
    int error=fstat(fd,&opened) || opened.st_dev!=before.st_dev || opened.st_ino!=before.st_ino ||
        opened.st_mode!=before.st_mode || opened.st_nlink!=before.st_nlink || opened.st_size!=before.st_size ? EPROTO : 0;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    uint64_t used=0;
    while(!error && S_ISREG(rule->mode) && used<size) {
        size_t amount=size-used<sizeof(data) ? (size_t)(size-used) : sizeof(data);
        ssize_t got=read(fd,data,amount);
        if(got<0 && errno==EINTR)continue;
        if(got<=0){error=EIO;break;}
        s22plus_max77705_runtime_sha256_update(&h,data,(size_t)got);used+=(uint64_t)got;
    }
    if(!error && S_ISREG(rule->mode)) {
        if(read(fd,&extra,1))error=EIO;
        s22plus_max77705_runtime_sha256_final(&h,digest);
        if(memcmp(digest,wanted,32))error=EPROTO;
    }
    if(!error && (fstat(fd,&end) || end.st_dev!=before.st_dev || end.st_ino!=before.st_ino ||
        end.st_mode!=before.st_mode || end.st_size!=before.st_size || end.st_nlink!=before.st_nlink ||
        end.st_mtim.tv_sec!=before.st_mtim.tv_sec || end.st_mtim.tv_nsec!=before.st_mtim.tv_nsec ||
        end.st_ctim.tv_sec!=before.st_ctim.tv_sec || end.st_ctim.tv_nsec!=before.st_ctim.tv_nsec))error=EPROTO;
    if(close(fd) && !error)error=fs1_error();
    return error;
}
static int pk_check_files(int root,dev_t device,bool after) {
    for(unsigned i=0;i<PK_ROWS;++i) {
        const struct pk_file *rule=pk_files+i;char leaf[NAME_MAX+1];
        int parent=pk_parent(root,device,rule->path,leaf),error=0;
        if(parent<0) {
            if(!after && !rule->existing && errno==ENOENT)continue;
            return fs1_error();
        }
        if(after || rule->existing)error=pk_file_at(parent,leaf,device,rule,after);
        else {
            struct stat st;
            if(!fstatat(parent,leaf,&st,AT_SYMLINK_NOFOLLOW))error=EEXIST;
            else if(errno!=ENOENT)error=fs1_error();
        }
        if(close(parent) && !error)error=fs1_error();
        if(error)return error;
    }
    return 0;
}
static int pk_absent(int root,dev_t device,const char *path) {
    char leaf[NAME_MAX+1];int parent=pk_parent(root,device,path,leaf);
    if(parent<0)return errno==ENOENT ? 0 : fs1_error();
    struct stat st;int error=0;
    if(!fstatat(parent,leaf,&st,AT_SYMLINK_NOFOLLOW))error=EEXIST;
    else if(errno!=ENOENT)error=fs1_error();
    if(close(parent) && !error)error=fs1_error();
    return error;
}
static int pk_transients_absent(int root,dev_t device) {
    const char *admin[]={"var/lib/dpkg/tmp.ci","var/lib/dpkg/status-new",
        "var/lib/dpkg/status-old-new","var/lib/dpkg/reassemble.deb","var/lib/dpkg/info/hello.list-new",
        "var/lib/dpkg/info/hello.md5sums-new"};
    for(unsigned i=0;i<sizeof(admin)/sizeof(admin[0]);++i) {
        int error=pk_absent(root,device,admin[i]);if(error)return error;
    }
    const char *suffix[]={".dpkg-new",".dpkg-tmp",".dpkg-old"};
    for(unsigned i=0;i<PK_ROWS;++i) {
        const struct pk_file *rule=pk_files+i;
        if(rule->existing)continue;
        for(unsigned j=0;j<sizeof(suffix)/sizeof(suffix[0]);++j) {
            char path[PATH_MAX];int size=snprintf(path,sizeof(path),"%s%s",rule->path,suffix[j]);
            if(size<0 || (size_t)size>=sizeof(path))return EOVERFLOW;
            int error=pk_absent(root,device,path);if(error)return error;
        }
    }
    return 0;
}
static int pk_archive(int parent,const char *path,const char *leaf,dev_t device) {
    if(rb_phase!=2)return 0;
    for(unsigned i=0;i<PK_ROWS;++i)if(pk_files[i].existing && !strcmp(path,pk_files[i].path)) {
        int error=pk_file_at(parent,leaf,device,pk_files+i,true);
        return error ? -error : 1;
    }
    return 0;
}
#endif
