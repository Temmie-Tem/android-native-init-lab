import struct
BASE="tmp/wifi/v1331-esoc-disasm/"
img=open(BASE+"Image.stripped","rb").read()
o=open(BASE+"TT.txt","w",buffering=1)
def w(s):o.write(s+"\n");o.flush()
w("len=%d"%len(img))
for start in (0x1948bf0,):
    p=start;bad=-1
    for i in range(256):
        e=img.find(b"\x00",p,p+96)
        if e<0:
            w("tok%d NOFIND p=0x%x"%(i,p));bad=i;break
        ln=e-p
        nonpr=sum(1 for c in img[p:e] if c<0x09 or c>0x7e)
        if i<24:
            w("t%d off=0x%x ln=%d np=%d b0=%d"%(i,p,ln,nonpr,img[p] if ln else -1))
        if ln>48 or nonpr:
            w("t%d BAD ln=%d np=%d"%(i,ln,nonpr));bad=i
        p=e+1
    w("END start=0x%x after256=0x%x firstbad=%d"%(start,p,bad))
    # what's at p (should be token_index)
    for pad in range(0,10):
        w("ti@+%d=0x%x u16[0..4]=%s"%(pad,p+pad,[struct.unpack_from('<H',img,p+pad+2*k)[0] for k in range(5)]))
o.close()
