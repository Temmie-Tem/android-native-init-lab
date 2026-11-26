/* SPDX-License-Identifier: GPL-2.0-only */
/* Both exported functions run before a stack exists. The build checks every
 * emitted instruction. The read-only input remains unchanged between passes. */
#include <stdint.h>
#include "layout.h"

#define LEAF __attribute__((noinline))
#define INLINE static inline __attribute__((always_inline))
#define PHYS_END (1ULL << 48)

INLINE unsigned u32(const unsigned char *p)
{
    return (unsigned)p[0]<<24 | (unsigned)p[1]<<16 | (unsigned)p[2]<<8 | p[3];
}
INLINE uint64_t u64(const unsigned char *p)
{
    return (uint64_t)u32(p)<<32 | u32(p+4);
}
INLINE int eq(const unsigned char *p, const char *s)
{
    while (*s && *p==(unsigned char)*s) { ++s; ++p; }
    return !*s && !*p;
}
INLINE int valid(uint64_t a, uint64_t n)
{
    return n && a<PHYS_END && n<=PHYS_END-a;
}
INLINE int overlaps(uint64_t a, uint64_t end, uint64_t b, uint64_t limit)
{
    return a<limit && b<end;
}
INLINE int terminated(const unsigned char *p, unsigned start, unsigned end)
{
    unsigned i=start;
    while (i<end && i-start<=255 && p[i]) ++i;
    return i<end && i-start<=255 ? (int)i : -1;
}

LEAF int y2q_shape(const unsigned char *p)
{
    uint64_t a=(uintptr_t)p;
    if (a!=IN_FDT || (a&7) || u32(p)!=0xd00dfeed) return 0;
    unsigned n=u32(p+4), pos=u32(p+8), strs=u32(p+12), rsv=u32(p+16);
    unsigned names=u32(p+32), size=u32(p+36);
    if (n<40 || n>FDT_CAP || n>IN_RD-a || u32(p+20)!=17 ||
        u32(p+24)<16 || u32(p+24)>17 || rsv<40 || (rsv&7) ||
        rsv>pos || pos-rsv<16 || pos>n || (pos&3) || !size || (size&3) ||
        size>n-pos || strs<pos+size || strs>=n || !names || names>n-strs)
        return 0;
    for (;;) {
        if (pos-rsv<16) return 0;
        uint64_t lo=u64(p+rsv), len=u64(p+rsv+8);
        rsv+=16;
        if (!lo && !len) break;
        if (!valid(lo,len)) return 0;
    }
    unsigned end=pos+size, depth=0, seen=0, props=0;
    while (end-pos>=4) {
        unsigned token=u32(p+pos); pos+=4;
        if (token==1) {
            int last=terminated(p,pos,end);
            if (last<0 || depth==64 || (!depth && (seen || p[pos]))) return 0;
            pos=((unsigned)last+4)&~3U;
            ++depth; seen=props=1;
        } else if (token==2) {
            if (!depth) return 0;
            --depth; props=0;
        } else if (token==3) {
            if (!props || !depth || end-pos<8) return 0;
            unsigned len=u32(p+pos), off=u32(p+pos+4);
            pos+=8;
            if (len>end-pos || off>=names || terminated(p,strs+off,strs+names)<0)
                return 0;
            pos+=(len+3)&~3U;
        } else if (token==9) {
            return seen && !depth && pos==end;
        } else if (token!=4) return 0;
    }
    return 0;
}

/* Before stack setup. Match complete tokens and consume the entire property. */
INLINE int has_kona_compatible(const unsigned char *p, unsigned len)
{
    unsigned pos = 0, count = 0, found = 0;
    if (!len || len > 512) return 0;
    while (pos < len) {
        unsigned start = pos;
        if (++count > 16) return 0;
        while (pos < len && p[pos]) {
            if (p[pos] < 33 || p[pos] > 126 || pos - start >= 127) return 0;
            ++pos;
        }
        if (pos == start || pos == len) return 0;
        if (pos - start == sizeof("qcom,kona") - 1 && eq(p + start, "qcom,kona"))
            found = 1;
        ++pos;
    }
    return found;
}

INLINE int status_ok(const unsigned char *p,unsigned n)
{
    return (n==3 && eq(p,"ok")) || (n==5 && eq(p,"okay"));
}
INLINE int memory_name(const unsigned char *s)
{
    static const char name[]="memory";
    for (unsigned i=0;i<6;i++) if (s[i]!=(unsigned char)name[i]) return 0;
    return !s[6] || s[6]=='@';
}

/* Checks one complete interval and the unchanged FDT/initrd against the
 * input geometry. Multiple memory nodes and multiple reg tuples are valid. */
LEAF int y2q_interval(const unsigned char *p, uint64_t lo, uint64_t end)
{
    const uint64_t fp=(uintptr_t)p, fe=fp+u32(p+4);
    if (lo>=end || overlaps(lo,end,fp,fe) || overlaps(lo,end,IN_RD,IN_RD_END) ||
        overlaps(fp,fe,IN_RD,IN_RD_END)) return 0;
    unsigned pos=u32(p+16);
    while (u64(p+pos) || u64(p+pos+8)) {
        uint64_t a=u64(p+pos), b=a+u64(p+pos+8);
        if (overlaps(lo,end,a,b) || overlaps(fp,fe,a,b) || overlaps(IN_RD,IN_RD_END,a,b))
            return 0;
        pos+=16;
    }
    enum { OTHER, RAM, CHOSEN, RSV };
    unsigned depth=0, group=OTHER, root_flags=0, child_flags=0, mem=0, memlen=0, cover=0;
    pos=u32(p+8);
    for (;;) {
        unsigned tok=u32(p+pos); pos+=4;
        if (tok==1) {
            const unsigned char *name=p+pos;
            if (++depth==2) {
                child_flags=mem=memlen=0;
                if (eq(name,"chosen")) {
                    if (root_flags&4) return 0;
                    root_flags|=4; group=CHOSEN;
                } else if (eq(name,"reserved-memory")) {
                    if (root_flags&8) return 0;
                    root_flags|=8; group=RSV;
                } else group=memory_name(name)?RAM:OTHER;
            } else if (group==RSV) {
                if (depth>3) return 0;
                if (depth==3) child_flags=0;
            }
            while (p[pos]) pos++;
            pos=(pos+4)&~3U;
        } else if (tok==2) {
            if (depth==2 && group==RAM) {
                if (!(child_flags&1) || !memlen) return 0;
                if (!(child_flags&4)) {
                    for (unsigned i=mem;i<mem+memlen;i+=16) {
                        uint64_t a=u64(p+i), n=u64(p+i+8);
                        if (!n) continue;
                        if (!valid(a,n)) return 0;
                        if (a<=lo && end<=a+n) cover|=1;
                        if (a<=fp && fe<=a+n) cover|=2;
                        if (a<=IN_RD && IN_RD_END<=a+n) cover|=4;
                    }
                }
            }
            if (depth==3 && group==RSV && !child_flags) return 0;
            if (depth--==2) group=OTHER;
        } else if (tok==3) {
            unsigned n=u32(p+pos);
            const unsigned char *k=p+u32(p+12)+u32(p+pos+4);
            pos+=8;
            const unsigned char *v=p+pos;
            unsigned bit=0;
            if (depth==1 || (depth==2 && group==RSV)) {
                if (eq(k,"#address-cells")) bit=depth==1?1:16;
                if (eq(k,"#size-cells")) bit=depth==1?2:32;
                if (bit && (n!=4 || u32(v)!=2)) return 0;
                if (depth==2 && eq(k,"ranges")) { if (n) return 0; bit=64; }
                if (eq(k,"status") && !status_ok(v,n)) return 0;
                if (depth==1 && eq(k,"compatible")) {
                    if (!has_kona_compatible(v,n)) return 0;
                    bit=512;
                }
            } else if (depth==2 && eq(k,"device_type") && n==7 && eq(v,"memory")) {
                if (group!=RAM || (child_flags&1)) return 0;
                child_flags|=1;
            } else if (depth==2 && group==RAM) {
                if (eq(k,"linux,usable-memory")) return 0;
                if (eq(k,"reg")) {
                    if (memlen || !n || (n&15)) return 0;
                    mem=pos; memlen=n;
                } else if (eq(k,"status")) {
                    if (child_flags&2) return 0;
                    child_flags|=2;
                    if (!status_ok(v,n)) child_flags|=4;
                }
            } else if (depth==2 && group==CHOSEN) {
                if (eq(k,"linux,usable-memory-range") || (eq(k,"status") && !status_ok(v,n))) return 0;
                if (eq(k,"linux,initrd-start")) bit=128;
                if (eq(k,"linux,initrd-end")) bit=256;
                if (bit && ((n!=4 && n!=8) ||
                    (n==4?u32(v):u64(v))!=(bit==128?IN_RD:IN_RD_END))) return 0;
            } else if (depth==3 && group==RSV) {
                if (eq(k,"reg")) {
                    if ((child_flags&1) || !n || (n&15)) return 0;
                    child_flags|=1;
                    for (unsigned i=0;i<n;i+=16) {
                        uint64_t a=u64(v+i), size=u64(v+i+8);
                        if (!valid(a,size) || overlaps(lo,end,a,a+size) ||
                            overlaps(fp,fe,a,a+size) || overlaps(IN_RD,IN_RD_END,a,a+size))
                            return 0;
                    }
                } else if (eq(k,"size")) {
                    if ((child_flags&2) || n!=8 || !valid(0,u64(v))) return 0;
                    child_flags|=2;
                }
            }
            if (root_flags&bit) return 0;
            root_flags|=bit;
            pos+=(n+3)&~3U;
        } else if (tok==9) return cover==7 && root_flags==1023;
    }
}
