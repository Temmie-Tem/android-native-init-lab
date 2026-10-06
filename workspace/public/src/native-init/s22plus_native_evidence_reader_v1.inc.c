/* Fixed-path, mountless ext4 reader. The only storage input is inherited fd3,
 * opened read-only by the exact-partition owner. No journal replay occurs. */
#include <ext2fs/ext2fs.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include "s22plus_native_evidence_seal_v1.h"

#define NE_LIMIT 24576U
#define NE_IO_LIMIT (64ULL*1024U*1024U)
#define NE_IO_CALLS 16384U
static uint8_t ne_output[NE_LIMIT];
static size_t ne_used;
static uint64_t ne_read_bytes;
static unsigned ne_read_calls,ne_write_attempts;
static struct struct_io_manager ne_manager;
static struct struct_io_channel ne_channel;

static void ne_put32(uint8_t *p,uint32_t value) {
    for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(value>>(8*i));
}
static void ne_put64(uint8_t *p,uint64_t value) {
    for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(value>>(8*i));
}
static uint8_t *ne_reserve(size_t n) {
    if(n>sizeof(ne_output)-ne_used)return NULL;
    uint8_t *p=ne_output+ne_used;memset(p,0,n);ne_used+=n;return p;
}
static errcode_t ne_open(const char *name,int flags,io_channel *out) {
    if(strcmp(name,"s22-inherited-readonly") || flags || ne_channel.refcount)return EINVAL;
    ne_channel=(struct struct_io_channel){.magic=EXT2_ET_MAGIC_IO_CHANNEL,
        .manager=&ne_manager,.block_size=1024,.refcount=1};
    *out=&ne_channel;return 0;
}
static errcode_t ne_close(io_channel c) {
    if(c!=&ne_channel || c->refcount!=1)return EINVAL;
    c->refcount=0;return 0;
}
static errcode_t ne_blocksize(io_channel c,int n) {
    if(c!=&ne_channel || (n!=1024 && n!=4096))return EINVAL;
    c->block_size=n;return 0;
}
static errcode_t ne_read64(io_channel c,unsigned long long block,int count,void *data) {
    if(c!=&ne_channel || count==INT_MIN || !count || block>FS1_BYTES/(unsigned)c->block_size)return EINVAL;
    uint64_t offset=block*(unsigned)c->block_size;
    uint64_t size=count<0 ? (uint64_t)(-count) : (uint64_t)count*(unsigned)c->block_size;
    if(size>1024U*1024U || offset>FS1_BYTES || size>FS1_BYTES-offset ||
       ne_read_calls>=NE_IO_CALLS || size>NE_IO_LIMIT-ne_read_bytes)return EFBIG;
    ++ne_read_calls;ne_read_bytes+=size;
    ssize_t n=pread(3,data,(size_t)size,(off_t)offset);
    return n==(ssize_t)size ? 0 : n<0 ? fs1_error() : EIO;
}
static errcode_t ne_read32(io_channel c,unsigned long block,int count,void *data) {
    return ne_read64(c,block,count,data);
}
static errcode_t ne_write64(io_channel c,unsigned long long b,int n,const void *p) {
    (void)c;(void)b;(void)n;(void)p;++ne_write_attempts;return EROFS;
}
static errcode_t ne_write32(io_channel c,unsigned long b,int n,const void *p) {
    return ne_write64(c,b,n,p);
}
static errcode_t ne_write_bytes(io_channel c,unsigned long b,int n,const void *p) {
    return ne_write64(c,b,n,p);
}
static errcode_t ne_flush(io_channel c) {
    (void)c;++ne_write_attempts;return EROFS;
}
static errcode_t ne_mutation(io_channel c,unsigned long long b,unsigned long long n) {
    (void)c;(void)b;(void)n;++ne_write_attempts;return EROFS;
}
static struct struct_io_manager ne_manager={.magic=EXT2_ET_MAGIC_IO_MANAGER,.name="s22-readonly-fd",
    .open=ne_open,.close=ne_close,.set_blksize=ne_blocksize,.read_blk=ne_read32,.read_blk64=ne_read64,
    .write_blk=ne_write32,.write_blk64=ne_write64,.write_byte=ne_write_bytes,.flush=ne_flush,
    .discard=ne_mutation,.zeroout=ne_mutation};

/* After privilege drop, a parser bug cannot open another input, write the
 * block descriptor, spawn work or change filesystem/kernel configuration. */
static int ne_filter(void) {
#define NE_ALLOW(n) BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,(n),0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)
    struct sock_filter code[]={
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AUDIT_ARCH_AARCH64,1,0),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_pread64,0,4),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,args[0])),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,3,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_write,0,5),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,args[0])),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,1,1,0),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,2,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
        NE_ALLOW(SYS_brk),NE_ALLOW(SYS_mmap),NE_ALLOW(SYS_munmap),NE_ALLOW(SYS_mprotect),
        NE_ALLOW(SYS_madvise),NE_ALLOW(SYS_futex),NE_ALLOW(SYS_getrandom),
        NE_ALLOW(SYS_clock_gettime),NE_ALLOW(SYS_rt_sigreturn),NE_ALLOW(SYS_rt_sigprocmask),
        NE_ALLOW(SYS_exit),NE_ALLOW(SYS_exit_group),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM)};
#undef NE_ALLOW
    struct sock_fprog program={.len=sizeof(code)/sizeof(code[0]),.filter=code};
    return prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&program) ? fs1_error() : 0;
}
static errcode_t ne_inode(ext2_filsys fs,ext2_ino_t ino,struct ext2_inode *inode) {
    if(ino<EXT2_ROOT_INO || ino>fs->super->s_inodes_count)return EPROTO;
    /* ext2fs_read_inode trusts the descriptor's inode-table location without
     * checking its CRC. Verify each used group before reading that inode. */
    dgrp_t group=ext2fs_group_of_ino(fs,ino);
    if(group>=fs->group_desc_count || !ext2fs_group_desc_csum_verify(fs,group))return EPROTO;
    return ext2fs_read_inode(fs,ino,inode);
}
static errcode_t ne_lookup(ext2_filsys fs,const char *path,ext2_ino_t *found,struct ext2_inode *inode) {
    char parts[256];if(!*path || path[0]=='/' || strlen(path)>=sizeof(parts))return EINVAL;
    strcpy(parts,path);ext2_ino_t dir=EXT2_ROOT_INO;char *part=parts;
    for(unsigned depth=0;depth<8;++depth) {
        errcode_t error=ne_inode(fs,dir,inode);if(error)return error;
        if(!LINUX_S_ISDIR(inode->i_mode) || inode_uid(*inode) || inode_gid(*inode) ||
           inode->i_mode&022 || inode->i_dtime)return EPROTO;
        char *slash=strchr(part,'/');if(slash)*slash=0;
        if(!*part || !strcmp(part,".") || !strcmp(part,".."))return EINVAL;
        error=ext2fs_lookup(fs,dir,part,strlen(part),NULL,found);if(error)return error;
        if(!slash)return ne_inode(fs,*found,inode);
        dir=*found;part=slash+1;
    }
    return ELOOP;
}
/* Each row is 96 bytes plus a bounded raw suffix. Paths come only from the
 * generated seal. Status: 0 read, 1 absent, 2 lookup/read error, 3 metadata,
 * 4 too large. A dirty home-block view never establishes non-execution. */
static int ne_file(ext2_filsys fs,unsigned index) {
    const struct ne_path *rule=&ne_paths[index];
    uint8_t *row=ne_reserve(96);if(!row)return EOVERFLOW;
    ne_put32(row,index);ext2_ino_t ino=0;struct ext2_inode inode={0};
    errcode_t error=ne_lookup(fs,rule->path,&ino,&inode);
    if(error) {ne_put32(row+4,error==EXT2_ET_FILE_NOT_FOUND ? 1 : 2);ne_put64(row+8,(uint64_t)error);return 0;}
    uint64_t size=EXT2_I_SIZE(&inode);
    ne_put32(row+16,ino);ne_put32(row+20,inode.i_mode);ne_put32(row+24,inode_uid(inode));
    ne_put32(row+28,inode_gid(inode));ne_put32(row+32,inode.i_links_count);ne_put32(row+36,inode.i_generation);
    ne_put64(row+40,size);
    if(inode.i_mode!=rule->mode || inode_uid(inode) || inode_gid(inode)!=rule->gid ||
       inode.i_links_count!=1 || inode.i_dtime) {ne_put32(row+4,3);return 0;}
    if(size>rule->maximum) {ne_put32(row+4,4);return 0;}
    uint32_t captured=size<rule->capture ? (uint32_t)size : rule->capture;
    uint64_t offset=size-captured;uint8_t *tail=ne_reserve(captured);if(!tail)return EOVERFLOW;
    ext2_file_t file=NULL;error=ext2fs_file_open(fs,ino,0,&file);
    uint8_t buffer[4096];uint64_t used=0;
    struct s22plus_max77705_runtime_sha256 h;s22plus_max77705_runtime_sha256_init(&h);
    while(!error && used<size) {
        unsigned want=size-used<sizeof(buffer) ? (unsigned)(size-used) : sizeof(buffer),got=0;
        error=ext2fs_file_read(file,buffer,want,&got);
        if(!error && got!=want)error=EIO;
        if(error)break;
        s22plus_max77705_runtime_sha256_update(&h,buffer,got);
        uint64_t begin=used>offset ? used : offset;
        if(used+got>begin)memcpy(tail+(begin-offset),buffer+(begin-used),(size_t)(used+got-begin));
        used+=got;
    }
    if(file) {errcode_t ended=ext2fs_file_close(file);if(!error)error=ended;}
    if(error) {ne_used-=captured;ne_put32(row+4,2);ne_put64(row+8,(uint64_t)error);return 0;}
    ne_put32(row+48,captured);ne_put64(row+56,offset);
    s22plus_max77705_runtime_sha256_final(&h,row+64);return 0;
}
static int ne_read_files(void) {
    int flags=fcntl(3,F_GETFL);struct stat st;
    if(flags<0 || (flags&O_ACCMODE)!=O_RDONLY || fstat(3,&st) || !S_ISBLK(st.st_mode))return EPROTO;
    int error=ne_filter();if(error)return error;
    ext2_filsys fs=NULL;
    errcode_t opened=ext2fs_open("s22-inherited-readonly",EXT2_FLAG_64BITS,0,0,&ne_manager,&fs);
    if(opened)return EPROTO;
    if(fs->blocksize!=4096 || ext2fs_blocks_count(fs->super)!=FS1_BLOCKS ||
       memcmp(fs->super->s_uuid,fs1_uuid,16) || fs->flags&EXT2_FLAG_RW) {ext2fs_free(fs);return EPROTO;}
    uint8_t *header=ne_reserve(32);if(!header){ext2fs_free(fs);return EOVERFLOW;}
    memcpy(header,"S22NE01\0",8);ne_put32(header+8,NE_PATH_COUNT);
    ne_put32(header+12,fs->super->s_state);ne_put32(header+16,!!(fs->super->s_feature_incompat&EXT3_FEATURE_INCOMPAT_RECOVER));
    ne_put32(header+20,fs->super->s_last_orphan);
    for(unsigned i=0;i<NE_PATH_COUNT && !error;++i)error=ne_file(fs,i);
    ext2fs_free(fs);
    if(error || ne_write_attempts)return error ? error : EROFS;
    uint8_t *end=ne_reserve(32);if(!end)return EOVERFLOW;
    memcpy(end,"S22NEND\0",8);ne_put64(end+8,ne_read_bytes);ne_put32(end+16,ne_read_calls);
    ne_put32(end+20,ne_write_attempts);ne_put32(end+24,(uint32_t)ne_used);
    return write(1,ne_output,ne_used)==(ssize_t)ne_used ? 0 : EIO;
}
