import struct, hashlib
BASE="tmp/wifi/v1331-esoc-disasm/"
img=open(BASE+"Image.stripped","rb").read()
o=open(BASE+"F2.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
n=len(img)
w("len=%d sha=%s"%(n,hashlib.sha256(img).hexdigest()[:16]))
def u16(p):return struct.unpack_from("<H",img,p)[0]
# Definitive token_table scan: find tt where 256 NUL-terminated printable tokens
# (cumulative offsets) are followed by a u16 array == those cumulative offsets.
found=0
i=n//4
end=n-2048
while i<end:
    # quick: candidate token0 start; require some printable then NUL within 40
    e=img.find(b"\x00",i,i+40)
    if e<0 or e==i:
        i+=1; continue
    # walk 256 tokens, build cumulative
    p=i; cum=[]; ok=True
    for k in range(256):
        cum.append(p-i)
        e=img.find(b"\x00",p,p+48)
        if e<0: ok=False; break
        # printable
        for c in img[p:e]:
            if c<0x09 or c>0x7e: ok=False; break
        if not ok: break
        p=e+1
    if not ok:
        i+=1; continue
    tt_end=p  # token_index should start here (maybe +pad)
    # verify u16 array at tt_end (try small pads) == cum
    for pad in (0,1,2,3,4,5,6,7):
        ti=tt_end+pad
        if ti+512>n: break
        match=True
        for k in range(256):
            if u16(ti+2*k)!=cum[k]: match=False; break
        if match:
            w("FOUND tt_start=0x%x ti=0x%x pad=%d tablesize=%d"%(i,ti,pad,cum[255]))
            sm=[]; q=i
            for k in range(20):
                e=img.find(b"\x00",q); sm.append(img[q:e].decode('latin1')); q=e+1
            w("tok0..19=%s"%"|".join(sm))
            found=1
            break
    if found: break
    i+=1
if not found: w("NOT FOUND")
w("done")
