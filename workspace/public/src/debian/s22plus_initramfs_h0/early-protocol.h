#ifndef S22_EARLY_PROTOCOL_V1_H
#define S22_EARLY_PROTOCOL_V1_H
/* Fixed H0/physical early-boot evidence protocol; no command executor. */
#define EARLY_REQUEST 48U
#define EARLY_PROOF 176U
#define EARLY_LOG 177U
#define EARLY_END 178U
#define EARLY_LIMIT 65536U
#define EARLY_CHUNK 768U
#define EARLY_TIMEOUT 300000ULL
#ifndef EARLY_DOMAIN
#define EARLY_DOMAIN "S22PLUS-FYG8-DEBIAN-EARLY-v1"
#endif
static const char early_domain[]=EARLY_DOMAIN;

static void early_put32(uint8_t *p,uint32_t value) {
    for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(value>>(i*8));
}
static uint32_t early_u32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static uint32_t early_crc(const uint8_t *p,size_t length,uint32_t crc) {
    for(size_t i=0;i<length;++i) {
        crc^=p[i];for(unsigned j=0;j<8;++j)crc=(crc>>1)^(0xedb88320U&-(crc&1U));
    }
    return crc;
}
static void early_hash(const void *data,size_t size,uint8_t out[32]) {
    struct s22plus_max77705_runtime_sha256 h;
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,data,size);
    s22plus_max77705_runtime_sha256_final(&h,out);
}
static void early_tag(uint8_t out[32],const uint8_t nonce[32],unsigned kind,
                      unsigned sequence,const void *data,size_t size) {
    uint8_t pad[64],inner[32],tail[5];struct s22plus_max77705_runtime_sha256 h;
    memset(pad,0x36,sizeof(pad));for(unsigned i=0;i<32;++i)pad[i]^=early_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,sizeof(pad));
    s22plus_max77705_runtime_sha256_update(&h,(const uint8_t *)early_domain,sizeof(early_domain)-1);
    s22plus_max77705_runtime_sha256_update(&h,early_run,sizeof(early_run));
    s22plus_max77705_runtime_sha256_update(&h,nonce,32);
    early_put32(tail,sequence);tail[4]=(uint8_t)kind;
    s22plus_max77705_runtime_sha256_update(&h,tail,sizeof(tail));
    s22plus_max77705_runtime_sha256_update(&h,data,size);
    s22plus_max77705_runtime_sha256_final(&h,inner);
    memset(pad,0x5c,sizeof(pad));for(unsigned i=0;i<32;++i)pad[i]^=early_key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,sizeof(pad));
    s22plus_max77705_runtime_sha256_update(&h,inner,sizeof(inner));
    s22plus_max77705_runtime_sha256_final(&h,out);
}

#endif
