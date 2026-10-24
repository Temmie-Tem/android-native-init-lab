/* Selected two-boot data boundary. No writer or phase retry lives here. */
#ifndef S22PLUS_DEBIAN_REBOOT_COMMON_V1_H
#define S22PLUS_DEBIAN_REBOOT_COMMON_V1_H
#include "s22plus_debian_reboot_seal_v1.h"
#include "early-seal.h"
#include "early-protocol.h"
_Static_assert(RB_BASE_COUNT<=65531U,"four RW setups must not wrap");
static unsigned rb_phase;
static uint8_t rb_early_nonce[32];
static int rb_valid_phase(unsigned phase) { return phase==1 || phase==2; }
static unsigned rb_before_early(unsigned phase) { return RB_BASE_COUNT+2*(phase-1); }
static unsigned rb_after_early(unsigned phase) { return RB_BASE_COUNT+2*phase-1; }
static unsigned rb_installed(unsigned phase) { return RB_BASE_COUNT+2*phase; }
static const char *rb_leaf(unsigned phase,unsigned runtime) {
    return strrchr(rb_paths[phase-1][runtime],'/')+1;
}
static int rb_boot(uint8_t digest[32]) {
    char text[38];int error=fs1_read_text("/proc/sys/kernel/random/boot_id",text,sizeof(text));
    if(error)return error;
    if(strlen(text)!=37 || text[36]!='\n')return EPROTO;
    for(unsigned i=0;i<36;++i) {
        if(i==8 || i==13 || i==18 || i==23) {if(text[i]!='-')return EPROTO;}
        else if(!((text[i]>='0' && text[i]<='9') || (text[i]>='a' && text[i]<='f')))return EPROTO;
    }
    early_hash(text,36,digest);return 0;
}
static int rb_admission_count(const uint8_t super[1024]) {
    unsigned count=fs1_u16(super+0x34);
#ifdef S22_AUTOBOOT_SECOND_ADMISSION
    return !rb_valid_phase(rb_phase) || count!=rb_after_early(rb_phase) ? EPROTO : 0;
#else
    if(count==RB_BASE_COUNT)rb_phase=1;
    else if(count==RB_BASE_COUNT+2)rb_phase=2;
    else return EPROTO;
    return 0;
#endif
}
static int rb_read_count(struct fs1_endpoint *endpoint,unsigned expected,bool clean) {
    int error=fs1_read_super(endpoint,false);if(error)return error;
    uint8_t copy[1024];memcpy(copy,endpoint->superblock,sizeof(copy));
    if(fs1_u16(copy+0x34)!=expected || fs1_u32(copy+0x3fc)!=fs1_crc32c(copy,0x3fc))return EPROTO;
    if(!clean) {
        if(fs1_u32(copy+0x60)!=(FS1_INCOMPAT|4U))return EPROTO;
        copy[0x60]&=~4U;
        uint32_t crc=fs1_crc32c(copy,0x3fc);
        for(unsigned i=0;i<4;++i)copy[0x3fc+i]=(uint8_t)(crc>>(8*i));
    }
    return fs1_superblock(copy,sizeof(copy),fs1_uuid,FS1_BLOCKS) ? 0 : EPROTO;
}
/* The source-authenticated early grammar is shared with the PID1 consumer.
 * The imported preparation body remains hash-bound to its measured producer. */
static int rb_early(const uint8_t *data,size_t size,unsigned phase) {
    if(!rb_valid_phase(phase) || size<256+14*128 || size>16384)return EPROTO;
    const uint8_t *proof=data+32;uint8_t tag[32],hash[32];
    unsigned log_size=early_u32(proof+12);uint64_t origin=fs1_u64(data+208),last=0;
    early_tag(tag,proof+16,0,0,data,224);
    if(memcmp(data,"S22FL04\0",8) || early_u32(data+8)!=4 || early_u32(data+12)!=256 ||
       memcmp(data+16,early_run,16) || memcmp(data+224,tag,32) ||
       early_u32(data+216)!=phase || early_u32(data+220)!=rb_after_early(phase) ||
       early_u32(proof)!=1 || early_u32(proof+4)<=1 || early_u32(proof+8) ||
       !log_size || log_size>16384-256-14*128 || size!=256+log_size+14*128 || origin>=300000 ||
       memcmp(proof+48,early_shell_hash,32) || memcmp(proof+80,early_init_hash,32) ||
       memcmp(proof+144,early_helper_hash,32))return EPROTO;
    early_hash(data+256,log_size,hash);if(memcmp(hash,proof+112,32))return EPROTO;
    const uint8_t *previous=data+224;
    for(unsigned i=0;i<14;++i) {
        const uint8_t *row=data+256+log_size+i*128;
        unsigned kind=i==0 ? 1 : i==13 ? 4 : i%2 ? 2 : 3;
        unsigned stage=i==0 || i==13 ? 0 : (i+1)/2;uint64_t elapsed=fs1_u64(row+16);
        early_tag(tag,proof+16,kind,i,row,96);
        if(memcmp(row,"S22FLR4\0",8) || early_u32(row+8)!=i || early_u32(row+12)!=kind ||
           early_u32(row+24)!=stage || early_u32(row+28) || elapsed<last || elapsed>=300000-origin ||
           memcmp(row+64,previous,32) || memcmp(row+96,tag,32))return EPROTO;
        for(unsigned j=32;j<64;++j)if(row[j])return EPROTO;
        last=elapsed;previous=row+96;
    }
    return 0;
}
static int rb_current_early(void) {
    int fd=open("/run/s22-debian/early",O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0)return fs1_error();
    struct stat st;struct statfs fs;uint8_t bytes[16384],boot[32],extra;
    int error=fstat(fd,&st) || fstatfs(fd,&fs) || fs.f_type!=0x01021994L ||
        st.st_mode!=(S_IFREG|0400) || st.st_uid || st.st_gid || st.st_nlink!=1 ||
        st.st_size<256 || st.st_size>16384 ? EPROTO : 0;
    if(!error && (read(fd,bytes,(size_t)st.st_size)!=st.st_size || read(fd,&extra,1)))error=EIO;
    if(close(fd) && !error)error=fs1_error();
    if(error)return error;
    unsigned phase=early_u32(bytes+216);
    if((error=rb_early(bytes,(size_t)st.st_size,phase)) || (error=rb_boot(boot)))return error;
    if(memcmp(boot,bytes+48,32))return EPROTO;
    early_hash(bytes,256,rb_early_nonce);rb_phase=phase;return 0;
}
#endif
