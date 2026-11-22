/* SPDX-License-Identifier: GPL-2.0-only */
#include <libfdt.h>
#include <stdint.h>
#include <string.h>

/* The pre-stack entry admits the read-only inputs and the stack/output areas.
 * This stage works on a copy of the compiled y2q board description. */
#define MAX_BANKS 128
#define MAX_RANGES 192
/* Linux 6.18 drivers/of/of_private.h, MAX_RESERVED_REGIONS. */
#define MAX_DYNAMIC_POOLS 64
#define PHYS_END (1ULL << 48)
enum { STOCK = 1, BOARD = 2, NOMAP = 4 };

struct span { uint64_t a, b; unsigned flags; };
struct spans { struct span v[MAX_RANGES]; unsigned count; };

static int named(const void *dt, int node, const char *property, const char *value)
{
    int n;
    const char *p = fdt_getprop(dt, node, property, &n);
    return p && n == (int)strlen(value) + 1 && !memcmp(p, value, n);
}

static int present(const void *dt, int node, const char *prop)
{
    return fdt_getprop(dt, node, prop, NULL) != NULL;
}

static int enabled(const void *dt, int node)
{
    return !present(dt,node,"status") || named(dt,node,"status","ok") ||
           named(dt,node,"status","okay");
}

static uint64_t pair(const fdt32_t *p)
{
    return (uint64_t)fdt32_to_cpu(p[0]) << 32 | fdt32_to_cpu(p[1]);
}

static int cells2(const void *dt, int node, const char *key)
{
    int n;
    const fdt32_t *p = fdt_getprop(dt,node,key,&n);
    return p && n == 4 && fdt32_to_cpu(*p) == 2;
}

static int add_span(struct spans *list, uint64_t a, uint64_t size, unsigned flags)
{
    if (list->count == MAX_RANGES || !size || a >= PHYS_END || size > PHYS_END - a)
        return -1;
    list->v[list->count++] = (struct span){a, a + size, flags};
    return 0;
}

static int read_banks(const void *dt, struct spans *banks)
{
    int node;
    fdt_for_each_subnode(node,dt,0) {
        if (!named(dt,node,"device_type","memory") || !enabled(dt,node))
            continue;
        int len;
        const fdt32_t *reg = fdt_getprop(dt,node,"reg",&len);
        if (!reg || len <= 0 || len % 16 || present(dt,node,"linux,usable-memory"))
            return -1;
        for (int i=0; i<len/4; i+=4) {
            uint64_t size = pair(reg+i+2);
            if (size && (banks->count == MAX_BANKS || add_span(banks,pair(reg+i),size,0)))
                return -1;
        }
    }
    if (node != -FDT_ERR_NOTFOUND || !banks->count)
        return -1;
    for (unsigned i=0; i<banks->count; i++)
        for (unsigned j=0; j<i; j++)
            if (banks->v[i].a < banks->v[j].b && banks->v[j].a < banks->v[i].b)
                return -1;
    return 0;
}

static int update_memory(const void *stock, void *out, struct spans *banks)
{
    if (read_banks(stock,banks))
        return -1;
    fdt32_t reg[4*MAX_BANKS];
    for (unsigned i=0; i<banks->count; i++) {
        uint64_t a = banks->v[i].a, n = banks->v[i].b - a;
        reg[4*i]   = cpu_to_fdt32(a >> 32);
        reg[4*i+1] = cpu_to_fdt32((uint32_t)a);
        reg[4*i+2] = cpu_to_fdt32(n >> 32);
        reg[4*i+3] = cpu_to_fdt32((uint32_t)n);
    }
    int node = fdt_path_offset(out,"/memory@80000000");
    return node < 0 ? -1 : fdt_setprop(out,node,"reg",reg,16*banks->count);
}

static int read_fixed(const void *dt, unsigned flags, struct spans *list)
{
    int parent = fdt_path_offset(dt,"/reserved-memory"), len, child;
    if (parent < 0 || !enabled(dt,parent) || !cells2(dt,parent,"#address-cells") ||
        !cells2(dt,parent,"#size-cells") || !fdt_getprop(dt,parent,"ranges",&len) || len)
        return -1;
    fdt_for_each_subnode(child,dt,parent) {
        if (fdt_first_subnode(dt,child) != -FDT_ERR_NOTFOUND)
            return -1;
        const fdt32_t *reg = fdt_getprop(dt,child,"reg",&len);
        if (!reg) {
            if (len != -FDT_ERR_NOTFOUND || !present(dt,child,"size") || flags == BOARD)
                return -1;
            continue;
        }
        if (len <= 0 || len % 16 || (flags == BOARD && !enabled(dt,child)))
            return -1;
        unsigned mode = flags | (present(dt,child,"no-map") ? NOMAP : 0);
        for (int i=0; i<len/4; i+=4)
            if (add_span(list,pair(reg+i),pair(reg+i+2),mode))
                return -1;
    }
    return child == -FDT_ERR_NOTFOUND ? 0 : -1;
}

static int emit_fixed(void *out, uint64_t lo, uint64_t hi, int nomap)
{
    char name[sizeof("handoff-reserved@") + 16];
    const char prefix[] = "handoff-reserved@";
    memcpy(name,prefix,sizeof(prefix)-1);
    unsigned len = sizeof(prefix)-1;
    for (int shift=60; shift>=0; shift-=4) {
        unsigned digit = (lo >> shift) & 15;
        if (digit || shift==0 || len!=sizeof(prefix)-1)
            name[len++] = "0123456789abcdef"[digit];
    }
    name[len] = 0;
    int parent = fdt_path_offset(out,"/reserved-memory");
    int node = fdt_add_subnode(out,parent,name);
    uint64_t size = hi-lo;
    fdt32_t reg[] = {cpu_to_fdt32(lo>>32),cpu_to_fdt32((uint32_t)lo),
                     cpu_to_fdt32(size>>32),cpu_to_fdt32((uint32_t)size)};
    if (node < 0 || fdt_setprop(out,node,"reg",reg,sizeof(reg)))
        return -1;
    return nomap ? fdt_setprop(out,node,"no-map",NULL,0) : 0;
}

/* Partition the union at every endpoint. Existing board nodes keep their
 * names, phandles and attributes. Emit uncovered OEM intervals exactly once. */
static int merge_fixed(void *out, const struct spans *ranges)
{
    uint64_t points[2*MAX_RANGES];
    unsigned count=0;
    for (unsigned i=0; i<ranges->count; i++) {
        points[count++] = ranges->v[i].a;
        points[count++] = ranges->v[i].b;
    }
    for (unsigned i=1; i<count; i++) {
        uint64_t key=points[i];
        unsigned j=i;
        while (j && points[j-1]>key) { points[j]=points[j-1]; j--; }
        points[j]=key;
    }
    uint64_t run=0;
    int previous=-1;
    for (unsigned i=0; i<count; i++) {
        if (i+1<count && points[i]==points[i+1]) continue;
        unsigned vendor=0, board=0;
        for (unsigned j=0; j<ranges->count; j++) {
            const struct span *r=&ranges->v[j];
            if (r->a<=points[i] && points[i]<r->b) {
                if (r->flags & BOARD) board |= r->flags;
                else vendor |= r->flags;
            }
        }
        if ((vendor & NOMAP) && board && !(board & NOMAP)) return -1;
        int next=vendor && !board ? !!(vendor & NOMAP) : -1;
        if (next!=previous) {
            if (previous>=0 && emit_fixed(out,run,points[i],previous)) return -1;
            run=points[i]; previous=next;
        }
    }
    return 0;
}

static int geometry(const void *dt, int node, const char *prop, int cells)
{
    int n;
    const fdt32_t *v=fdt_getprop(dt,node,prop,&n);
    if (!v || n<=0 || n%(cells*4)) return -1;
    if (cells==2) return n==8 && pair(v) && pair(v)<PHYS_END ? 0 : -1;
    for (int i=0; i<n/4; i+=4) {
        uint64_t a=pair(v+i), size=pair(v+i+2);
        if (a>=PHYS_END || !size || size>PHYS_END-a) return -1;
    }
    return 0;
}

static int copy_pools(const void *stock, void *out)
{
    int parent=fdt_path_offset(stock,"/reserved-memory"), child;
    int pools[MAX_DYNAMIC_POOLS], count = 0;
    fdt_for_each_subnode(child,stock,parent) {
        if (!present(stock,child,"reg")) {
            if (count == MAX_DYNAMIC_POOLS) return -1;
            pools[count++] = child;
        }
    }
    if (child != -FDT_ERR_NOTFOUND) return -1;
    /* libfdt prepends children. Keep the incoming order in which Linux
     * considers dynamic allocation requests. */
    while (count) {
        child = pools[--count];
        if (geometry(stock,child,"size",2) ||
            (present(stock,child,"alignment") && geometry(stock,child,"alignment",2)) ||
            (present(stock,child,"alloc-ranges") && geometry(stock,child,"alloc-ranges",4)))
            return -1;
        if (present(stock,child,"compatible") &&
            !named(stock,child,"compatible","shared-dma-pool"))
            return -1;
        if (present(stock,child,"no-map") && present(stock,child,"reusable"))
            return -1;
        if (present(stock,child,"alignment")) {
            const fdt32_t *v = fdt_getprop(stock,child,"alignment",NULL);
            uint64_t alignment = pair(v);
            if (alignment & (alignment - 1)) return -1;
        }
        int n, dp=fdt_path_offset(out,"/reserved-memory");
        const char *name=fdt_get_name(stock,child,&n);
        if (!name || n<=0 || n>255) return -1;
        int copy=fdt_add_subnode(out,dp,name);
        if (copy<0) return -1;
        int prop;
        unsigned seen = 0;
        fdt_for_each_property_offset(prop,stock,child) {
            const char *key;
            const void *val=fdt_getprop_by_offset(stock,prop,&key,&n);
            if (!val || n<0) return -1;
            if (!strcmp(key,"phandle") || !strcmp(key,"linux,phandle")) continue;
            static const char allowed[] = "size\0alignment\0alloc-ranges\0no-map\0reusable\0"
                "compatible\0status\0linux,cma-default\0rbin_size\0ion,recyclable\0";
            const char *field = allowed;
            unsigned bit = 1;
            while (*field && strcmp(key,field)) {
                field += strlen(field) + 1;
                bit <<= 1;
            }
            if (!*field || (seen & bit)) return -1;
            seen |= bit;
            if ((!strcmp(key,"no-map") || !strcmp(key,"reusable") ||
                 !strcmp(key,"linux,cma-default") || !strcmp(key,"ion,recyclable")) && n)
                return -1;
            if (!strcmp(key,"rbin_size") && n != 4) return -1;
            if (fdt_setprop(out,copy,key,val,n))
                return -1;
        }
        if (prop != -FDT_ERR_NOTFOUND) return -1;
    }
    return 0;
}

static int chosen(const void *stock, void *out, uint64_t expected_size)
{
    int in=fdt_path_offset(stock,"/chosen"), dst=fdt_path_offset(out,"/chosen");
    if (in<0 || dst<0 || present(stock,in,"linux,usable-memory-range")) return -1;
    uint64_t ends[2];
    for (int i=0; i<2; i++) {
        int n;
        const char *key = i ? "linux,initrd-end" : "linux,initrd-start";
        const fdt32_t *v=fdt_getprop(stock,in,key,&n);
        if (!v || (n!=4 && n!=8) || fdt_setprop(out,dst,key,v,n)) return -1;
        ends[i]=n==8 ? pair(v) : fdt32_to_cpu(*v);
    }
    if (!ends[0] || ends[1]<=ends[0] || ends[1]>PHYS_END ||
        ends[1]-ends[0]!=expected_size) return -1;
    return fdt_setprop_string(out,dst,"bootargs","rdinit=/init");
}

#ifdef Y2Q_STAGE_EVIDENCE
#include "stage-geometry.h"
#endif

int y2q_compose(const void *stock, const void *board, void *out, int capacity,
                uint64_t fw_lo, uint64_t fw_len, uint64_t initrd_size)
{
    struct spans banks={0}, ranges={0};
    if (fdt_check_header(stock) || fdt_check_header(board) ||
        fdt_node_check_compatible(stock,0,"qcom,kona") ||
        fdt_node_check_compatible(board,0,"samsung,y2q") ||
        !enabled(stock,0) || !cells2(stock,0,"#address-cells") ||
        !cells2(stock,0,"#size-cells") || fdt_open_into(board,out,capacity))
        return -1;
    if (chosen(stock,out,initrd_size) || update_memory(stock,out,&banks) ||
        read_fixed(stock,STOCK,&ranges) || read_fixed(board,BOARD,&ranges) ||
        add_span(&ranges,fw_lo,fw_len,STOCK|NOMAP) || merge_fixed(out,&ranges) ||
        copy_pools(stock,out)) return -1;
    int total=fdt_num_mem_rsv(stock);
    if (total<0 || total>256) return -1;
    for (int i=0;i<total;i++) {
        uint64_t a,n;
        if (fdt_get_mem_rsv(stock,i,&a,&n) || a>=PHYS_END || !n || n>PHYS_END-a ||
            fdt_add_mem_rsv(out,a,n)) return -1;
    }
#ifdef Y2Q_STAGE_EVIDENCE
    if (y2q_record_permission(stock, out, &banks)) return -1;
#endif
    return fdt_pack(out);
}
