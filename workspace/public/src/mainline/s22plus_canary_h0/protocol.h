/* Legacy schemas are observations. The distinct Download schema additionally
 * requires its separately authenticated, same-boot control after base proof. */
#ifndef G0Q_RAM_CANARY_PROTOCOL_H
#define G0Q_RAM_CANARY_PROTOCOL_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "../../native-init/s22plus_fyg8_max77705_result_parser.inc.c"

#define G0Q_REQUEST_SIZE 72U
#ifdef CANARY_RC_CYCLE
#define G0Q_BODY_SIZE 352U
#define G0Q_REQUEST_MAGIC "G0QCRQ1\0"
#define G0Q_RESPONSE_MAGIC "G0QCRS1\0"
#define G0Q_DOMAIN "G0Q-DEBIAN-RC-SSH-RAM-v1"
#elif defined(CANARY_DOWNLOAD_RAM)
#define G0Q_BODY_SIZE 352U
#define G0Q_REQUEST_MAGIC "G0QNRQ1\0"
#define G0Q_RESPONSE_MAGIC "G0QNRS1\0"
#define G0Q_DOMAIN "G0Q-DEBIAN-DOWNLOAD-RAM-v1"
#elif defined(CANARY_DEBIAN_SSH)
#define G0Q_BODY_SIZE 352U
#define G0Q_REQUEST_MAGIC "G0QSRQ1\0"
#define G0Q_RESPONSE_MAGIC "G0QSRS1\0"
#define G0Q_DOMAIN "G0Q-DEBIAN-SSH-RAM-v1"
#elif defined(CANARY_DEBIAN_RAM)
#define G0Q_BODY_SIZE 352U
#define G0Q_REQUEST_MAGIC "G0QDRQ1\0"
#define G0Q_RESPONSE_MAGIC "G0QDRS1\0"
#define G0Q_DOMAIN "G0Q-DEBIAN-SYSVINIT-RAM-v1"
#else
#define G0Q_BODY_SIZE 256U
#define G0Q_REQUEST_MAGIC "G0QREQ1\0"
#define G0Q_RESPONSE_MAGIC "G0QRSP1\0"
#define G0Q_DOMAIN "G0Q-MAINLINE-RAM-CANARY-v1"
#endif
#define G0Q_RESPONSE_SIZE (G0Q_BODY_SIZE + 32U)
#define G0Q_FDT_LIMIT (2U * 1024U * 1024U)

static void g_put32(uint8_t *p, uint32_t x) {
    for(unsigned i=0;i<4;i++) p[i]=(uint8_t)(x>>(8*i));
}
static void g_put64(uint8_t *p, uint64_t x) {
    for(unsigned i=0;i<8;i++) p[i]=(uint8_t)(x>>(8*i));
}
static uint32_t g_u32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static int g_equal(const uint8_t *a,const uint8_t *b,size_t n) {
    unsigned d=0;for(size_t i=0;i<n;i++)d|=a[i]^b[i];return d==0;
}
static void g_hash(const void *p,size_t n,uint8_t out[32]) {
    struct s22plus_max77705_runtime_sha256 h;
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,p,n);
    s22plus_max77705_runtime_sha256_final(&h,out);
}
static void g_tag(uint8_t out[32],const uint8_t key[32],const uint8_t id[32],
                  unsigned response,const uint8_t *data,size_t size) {
    static const uint8_t domain[]=G0Q_DOMAIN;
    uint8_t pad[64],inner[32],kind=(uint8_t)response;
    struct s22plus_max77705_runtime_sha256 h;
    memset(pad,0x36,sizeof(pad));for(unsigned i=0;i<32;i++)pad[i]^=key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,domain,sizeof(domain)-1);
    s22plus_max77705_runtime_sha256_update(&h,id,32);
    s22plus_max77705_runtime_sha256_update(&h,&kind,1);
    s22plus_max77705_runtime_sha256_update(&h,data,size);
    s22plus_max77705_runtime_sha256_final(&h,inner);
    memset(pad,0x5c,sizeof(pad));for(unsigned i=0;i<32;i++)pad[i]^=key[i];
    s22plus_max77705_runtime_sha256_init(&h);
    s22plus_max77705_runtime_sha256_update(&h,pad,64);
    s22plus_max77705_runtime_sha256_update(&h,inner,32);
    s22plus_max77705_runtime_sha256_final(&h,out);
}
static int g_request(const uint8_t request[G0Q_REQUEST_SIZE],const uint8_t key[32],const uint8_t id[32]) {
    uint8_t tag[32];g_tag(tag,key,id,0,request,40);
    return memcmp(request,G0Q_REQUEST_MAGIC,8)==0 && g_equal(tag,request+40,32);
}
#endif
