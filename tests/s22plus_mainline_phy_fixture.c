/* H0 only: selected driver C is included verbatim; hardware services are mocks. */
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libfdt.h>

typedef uint8_t u8;
typedef uint32_t u32;
typedef int32_t s32;
#define __iomem
#define BIT(n) (1U << (n))
#define GENMASK(h,l) (((~0U) << (l)) & ((~0U) >> (31-(h))))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define __ffs(x) __builtin_ctz(x)
#define dev_dbg(...) ((void)0)
#define dev_vdbg(...) ((void)0)
#define dev_err(...) ((void)0)
struct device_node { const void *blob; int offset; };
struct device { struct device_node *of_node; void *data; };
struct phy { struct device dev; void *data; };
struct clk_bulk_data { int unused; };
struct regulator_bulk_data { int unused; };
struct reset_control { int unused; };
enum phy_mode { PHY_MODE_INVALID, PHY_MODE_USB_HOST, PHY_MODE_USB_DEVICE };
struct of_device_id { const char *compatible; const void *data; };
static u32 mmio[128];
static struct { unsigned offset; u32 value; } writes[64];
static unsigned write_count, event_count, failure, deasserted;
static const char *events[32];
static void event(const char *s) { assert(event_count<ARRAY_SIZE(events)); events[event_count++]=s; }
static void *phy_get_drvdata(struct phy *p) { return p->data; }
static void *dev_get_drvdata(struct device *p) { return p->data; }
static u32 readl_relaxed(const void *p);
static void writel_relaxed(u32 v, void *p);
static const void *of_device_get_match_data(struct device *d);
static int of_property_read_s32(struct device_node *n,const char *name,s32 *value);
static int regulator_bulk_enable(unsigned n,struct regulator_bulk_data *p) {
    assert(n==3 && p); event("power+"); return failure==1?-EIO:0;
}
static int clk_bulk_prepare_enable(int n,struct clk_bulk_data *p) {
    assert(n==2 && p); event("clocks+"); return failure==2?-EIO:0;
}
static int reset_control_assert(struct reset_control *p) {
    assert(p); event("reset+"); return failure==3?-EIO:0;
}
static int reset_control_deassert(struct reset_control *p) {
    assert(p); event("reset-"); if(failure==4)return -EIO; deasserted=1; return 0;
}
static void usleep_range(unsigned a,unsigned z) { assert(a==100 && z==150); event("delay"); }
static void clk_bulk_disable_unprepare(int n,struct clk_bulk_data *p) {
    assert(n==2 && p); event("clocks-");
}
static void regulator_bulk_disable(unsigned n,struct regulator_bulk_data *p) {
    assert(n==3 && p); event("power-");
}

/* Generated from exact producer source, with each byte range recorded. */
#include "selected-phy.c"

static unsigned offset(const void *p) {
    uintptr_t a=(uintptr_t)p,b=(uintptr_t)mmio;
    assert(a>=b && a+4<=b+sizeof(mmio) && (a-b)%4==0);
    return (unsigned)(a-b);
}
static u32 readl_relaxed(const void *p) { return mmio[offset(p)/4]; }
static void writel_relaxed(u32 v,void *p) {
    unsigned a=offset(p); static const unsigned allowed[]={0x3c,0x50,0x54,0x58,0x5c,0x60,0x64,0x6c,0x70,0x74,0x78,0x94,0xa0};
    bool found=false;
    for(unsigned i=0;i<ARRAY_SIZE(allowed);i++)if(a==allowed[i])found=true;
    assert(found && deasserted && write_count<ARRAY_SIZE(writes));
    if(a>=0x6c && a<=0x78) {
        assert(mmio[0x94/4]&UTMI_PHY_CMN_CTRL_OVERRIDE_EN);
        assert(mmio[0x50/4]&POR);
    }
    writes[write_count].offset=a; writes[write_count++].value=v; mmio[a/4]=v;
}
static const void *of_device_get_match_data(struct device *d) {
    for(unsigned i=0;qcom_snps_hsphy_of_match_table[i].compatible;i++)
        if(!fdt_node_check_compatible(d->of_node->blob,d->of_node->offset,qcom_snps_hsphy_of_match_table[i].compatible))
            return qcom_snps_hsphy_of_match_table[i].data;
    return NULL;
}
static int of_property_read_s32(struct device_node *n,const char *name,s32 *value) {
    int len; const fdt32_t *p=fdt_getprop(n->blob,n->offset,name,&len);
    if(!p)return -ENOENT;
    assert(len==4); *value=(s32)fdt32_to_cpu(*p); return 0;
}
int main(int argc,char **argv) {
    assert(argc==4); u32 seed=(u32)strtoul(argv[2],NULL,0); failure=(unsigned)strtoul(argv[3],NULL,0); assert(failure<=4);
    FILE *f=fopen(argv[1],"rb"); assert(f); assert(!fseek(f,0,SEEK_END)); long len=ftell(f);
    assert(len>40 && len<2*1024*1024 && !fseek(f,0,SEEK_SET));
    void *blob=malloc((size_t)len); assert(blob && fread(blob,1,(size_t)len,f)==(size_t)len); assert(!fclose(f));
    assert(!fdt_check_header(blob) && fdt_totalsize(blob)==(unsigned long)len);
    int node=fdt_node_offset_by_compatible(blob,-1,"qcom,sm8450-usb-hs-phy");
    assert(node>=0 && fdt_node_offset_by_compatible(blob,node,"qcom,sm8450-usb-hs-phy")==-FDT_ERR_NOTFOUND);
    struct device_node dn={blob,node}; struct device dev={&dn,NULL}; struct phy phy={0};
    struct clk_bulk_data clocks[2]; struct reset_control reset;
    struct qcom_snps_hsphy h={.dev=&dev,.phy=&phy,.base=mmio,.num_clks=2,.clks=clocks,.phy_reset=&reset,.mode=PHY_MODE_USB_DEVICE};
    dev.data=phy.data=&h; assert(of_device_get_match_data(&dev)==sc7280_snps_7nm_phy);
    for(unsigned i=0;i<ARRAY_SIZE(mmio);i++)mmio[i]=seed;
    qcom_snps_hsphy_read_override_param_seq(&dev);
    unsigned present=0;
    for(unsigned i=0;sc7280_snps_7nm_phy[i].prop_name;i++) {
        const struct override_param_map *m=&sc7280_snps_7nm_phy[i]; s32 value;
        if(of_property_read_s32(&dn,m->prop_name,&value)) { assert(!h.update_seq_cfg[i].need_update); continue; }
        unsigned matches=0,index=0;
        for(unsigned j=0;j<m->table_size;j++)if(m->param_table[j].value==value){matches++;index=j;}
        /* A legitimate last-table value is allowed; unsupported fallthrough is not. */
        assert(matches==1 && h.update_seq_cfg[i].need_update);
        assert(h.update_seq_cfg[i].offset==m->reg_offset && h.update_seq_cfg[i].mask==m->param_mask);
        assert(h.update_seq_cfg[i].value==(m->param_table[index].reg_val<<__ffs(m->param_mask)));
        present++;
    }
    int ret=qcom_snps_hsphy_init(&phy);
    assert(ret==(failure?-EIO:0) && h.phy_initialized==!failure);
    if(failure)assert(write_count==0);
    printf("{\"seed\":%" PRIu32 ",\"failure\":%u,\"returncode\":%d,\"properties\":%u,\"writes\":[",seed,failure,ret,present);
    for(unsigned i=0;i<write_count;i++)printf("%s[%u,%" PRIu32 "]",i?",":"",writes[i].offset,writes[i].value);
    printf("],\"events\":[");
    for(unsigned i=0;i<event_count;i++)printf("%s\"%s\"",i?",":"",events[i]);
    printf("],\"final\":[%" PRIu32 ",%" PRIu32 ",%" PRIu32 ",%" PRIu32 ",%" PRIu32 "]}\n",mmio[0xa0/4],mmio[0x6c/4],mmio[0x70/4],mmio[0x74/4],mmio[0x78/4]);
    free(blob); return 0;
}
