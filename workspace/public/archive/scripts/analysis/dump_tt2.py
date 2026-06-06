import struct
BASE="tmp/wifi/v1331-esoc-disasm/"
img=open(BASE+"Image.stripped","rb").read()
o=open(BASE+"TT2.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
ti=0x132ac88
idx=[struct.unpack_from("<H",img,ti+2*k)[0] for k in range(256)]
w("idx[0..12]=%s"%idx[:12])
w("idx[250..255]=%s"%idx[250:])
w("hexpre 0x%x: %s"%(ti-32,img[ti-32:ti].hex()))
w("hex@ti 0x%x: %s"%(ti,img[ti:ti+24].hex()))
# find tt_start: walk 256 NUL strings, must end exactly at ti
for tt in range(ti-1200, ti-200):
    p=tt
    for k in range(256):
        e=img.find(b"\x00",p,p+80)
        if e<0: p=-1; break
        p=e+1
    if p==ti:
        w("FORWARD MATCH tt_start=0x%x"%tt)
        # show real tokens
        q=tt;sm=[]
        for k in range(16):
            e=img.find(b"\x00",q);sm.append(img[q:e].decode('latin1'));q=e+1
        w("tok0..15=%s"%"|".join(sm))
        # cross-check idx
        bad=0
        for k in range(256):
            e=img.find(b"\x00",tt+idx[k])
            # token k length should match idx delta
        w("idx[1]-idx[0]=%d strlen(tok0)+1=%d"%(idx[1]-idx[0], len(sm[0])+1))
        break
else:
    w("NO FORWARD MATCH")
w("done")
