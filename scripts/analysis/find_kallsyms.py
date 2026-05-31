import struct
BASE="tmp/wifi/v1331-esoc-disasm/"
img=open(BASE+"Image.stripped","rb").read()
o=open(BASE+"FK.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
n=len(img)
w("len=%d"%n)

def u16(b,p):return struct.unpack_from("<H",b,p)[0]

# Scan for kallsyms_token_index: 256 u16, [0]=0, strictly increasing, small steps.
cands=[]
i=0
while i < n-512:
    if img[i]==0 and img[i+1]==0:  # u16[0]==0 fast prefilter
        ok=True; prev=0
        p=i+2
        for k in range(1,256):
            v=u16(img,p); p+=2
            d=v-prev
            if d<1 or d>40: ok=False; break
            prev=v
        if ok and 200<=prev<=4000:
            cands.append((i,prev))
            if len(cands)<=20:
                w("ti_cand off=0x%x last=%d"%(i,prev))
            if len(cands)>=200: break
    i+=2
w("ti_cands=%d"%len(cands))

# For each candidate, token_table ends just before ti (token_table_start = ti - tablesize).
# Verify: string at (tt_start + index[k]) is token k for all k, and tokens printable.
for (ti,last) in cands:
    tablesize=None
    # token_table_start: scan back; table_size = last_index + strlen(last_token)+1.
    # We can locate tt_start by requiring img[tt_start-1]==0 (pad) and verify mapping.
    # Try tt_start in a small back-window.
    found=False
    for tt in range(ti-last-64, ti-last+8):
        if tt<0: continue
        good=True
        for k in range(0,256,7):  # sample every 7th token for speed
            idx=u16(img,ti+2*k)
            sp=tt+idx
            e=img.find(b"\x00",sp,sp+64)
            if e<0 or e-sp>48: good=False; break
            seg=img[sp:e]
            for c in seg:
                if c<0x09 or c>0x7e: good=False; break
            if not good: break
        if good:
            # full check first 32 tokens decode to non-empty-ish printable
            sample=[]
            p=tt
            for k in range(8):
                e=img.find(b"\x00",p,p+64)
                sample.append(img[p:e]); p=e+1
            w("MATCH ti=0x%x tt_start=0x%x last=%d toks=%s"%(ti,tt,last,b"|".join(sample)))
            found=True;break
    if found: break
w("done")
